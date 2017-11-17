import logging
from abc import ABCMeta, abstractmethod

from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.models import Contact
from r3sourcer.apps.core.service import factory

from .exceptions import SMSServiceError
from .helpers import get_sms, get_phone_number
from .models import SMSMessage, SMSTemplate


logger = logging.getLogger(__name__)


class BaseSMSService(metaclass=ABCMeta):

    _activity_service = None

    @property
    def activity_service(self):
        if self._activity_service is None:
            activity_service_class = getattr(
                settings, 'ACTIVITY_SERVICE_CLASS', None
            )
            if activity_service_class is None:
                self._activity_service = factory.get_instance('activity')
            else:
                self._activity_service = activity_service_class()
        return self._activity_service

    @transaction.atomic
    def send(self, to_number, text, from_number=None, related_obj=None, **kwargs):
        sender_contact = kwargs.get('sender_contact')
        try:
            sms_message = get_sms(from_number=from_number,
                                  to_number=to_number, text=text, **kwargs)

            sms_message.related_object = related_obj
            sms_message.save()

            if 'related_objs' in kwargs and isinstance(kwargs['related_objs'], (list, tuple)):
                sms_message.add_related_objects(*kwargs.pop('related_objs'))

            self.activity_service.on_new_sms_message(
                sms_message, sender_contact=sender_contact
            )

            self.process_sms_send(sms_message)

            logger.info("Message sent: sid={}; to_number={}".format(
                sms_message.sid, sms_message.to_number)
            )
        except SMSServiceError as e:
            sms_message.error_message = str(e)
            sms_message.save()

            ac = self.activity_service.on_new_sms_message(
                self, sender_contact=sender_contact
            )

            # get sms activity
            if ac:
                ac.activity = ac.create_activity(
                    _("Undelivered message"), _("Undelivered message"),
                    sms_message.sent_at, timezone.now()
                )
                ac.save(update_fields=['activity_id'])

    @transaction.atomic
    def send_tpl(self, to_number, tpl_name, from_number=None, related_obj=None,
                 **kwargs):
        try:
            template = SMSTemplate.objects.get(
                Q(name=tpl_name) | Q(slug=tpl_name)
            )
            message = template.compile(**kwargs)['text']
        except SMSTemplate.DoesNotExist:
            logger.exception('Cannot find template with name %s', tpl_name)
        else:
            self.send(to_number, message, from_number, related_obj, **kwargs)

    @abstractmethod
    def process_sms_send(self, sms_message):
        """
        Actually send SMS message

        should throws SMSServiceError if error occurred
        """
        pass  # pragma: no cover

    def fetch(self):
        try:
            sms_messages = self.process_sms_fetch()
        except SMSServiceError:
            logger.exception("Error occurred on SMS messages fetch")
        else:
            for sms_message in sms_messages:
                self._process_sms(sms_message)

    @transaction.atomic
    def _process_sms(self, sms_message):
        is_new_sms = not SMSMessage.objects.filter(
            sid=sms_message.sid, is_fetched=True
        ).exists()

        sms_message.is_fetched = True
        sms_message.save()

        if not is_new_sms:
            return

        logger.info(
            'Receive new message: type: %s; %s(%s)',
            sms_message.type, sms_message.id, sms_message
        )

        ac = self.activity_service.on_new_sms_message(sms_message)
        if sms_message.status == SMSMessage.STATUS_CHOICES.RECEIVED:
            sent_message = sms_message.get_sent_by_reply()
        else:
            sent_message = None

        if sms_message.type == SMSMessage.TYPE_CHOICES.SENT:
            # if it is new message, sent by another system (message not in local database),
            # then check delivered status after timeout by cron
            sms_message.check_delivered = True
            sms_message.save(update_fields=['check_delivered'])
        elif ac and sms_message.is_answer():
            self.process_sms_answer(sms_message, sent_message, ac)
        elif sms_message.is_stop_message():
            Contact.objects.filter(phone_mobile=sms_message.from_number).update(is_available=False)
            logger.info('Process stop message: {}'.format(sms_message.from_number))
        elif sms_message.is_start_message():
            Contact.objects.filter(phone_mobile=sms_message.from_number).update(is_available=True)
            logger.info('Process start message: {}'.format(sms_message.from_number))
        elif sms_message.is_login():
            contact = Contact.objects.filter(phone_mobile=sms_message.from_number).last()
            if contact:
                login_service = factory.get_instance('login')
                login_service.send_login_sms(contact)
                logger.info('Process login message: {}'.format(sms_message.from_number))
        elif not sms_message.is_answer() and ac:
            self.process_ambiguous_answer(sms_message, sent_message, ac)

    def process_sms_answer(self, sms_message, sent_message, sms_activity):
        logger.info("Sent reply message: {}. id: {}".format(
            sent_message, getattr(sent_message, 'id', '-'))
        )

        if not sms_message.has_contact_relation():
            logger.error("Can't find Contact with numbers: {}, {}".format(
                sms_message.from_number, sms_message.to_number)
            )
            return

        related_object = self._get_related_object(
            sms_message, sent_message, sms_activity
        )
        can_process = hasattr(related_object, 'process_sms_reply')
        positive = self._is_positive(sms_message, sms_activity)

        if sent_message:
            sms_message.add_related_objects(*sent_message.get_related_objects())
            sent_message.no_check_reply()
        elif sms_message.is_late_reply():
            sent_message = sms_message.get_sent_by_reply(check_reply=False)
            # add related object to late reply
            sms_message.add_related_objects(*sent_message.get_related_objects())
            sent_message.late_reply = sms_message
            sent_message.save(update_fields=['late_reply_id'])
            logger.info('Received late reply for message {}: sent: {}; reply: {};'.format(
                sent_message, sent_message.id, sms_message.id
            ))
        if can_process:
            logger.info('Run process_sms_reply. Related object: {}; Answer: {}'.format(
                related_object, positive
            ))
            related_object.process_sms_reply(
                sent_sms=sent_message, reply_sms=sms_message,
                positive=positive
            )

    def _get_related_object(self, sms_message, sent_message, sms_activity):
        related_object = None
        if sent_message:
            related_object = sent_message.related_object
            logger.info("Related object with sms: {}".format(
                related_object)
            )
        else:
            sms_activity.create_activity(
                _('Could not find sent SMS'), _('Could not find sent SMS'),
                sms_message.sent_at, timezone.now(),
                contact=sms_activity.to_contact
            )
        return related_object

    def _is_positive(self, sms_message, sms_activity):
        positive = None
        if sms_message.is_positive_answer():
            # TODO: implement positive handler
            positive = True
        elif sms_message.is_negative_answer():
            sms_activity.create_activity(
                _('Negative answer'), _('Negative answer'),
                sms_message.sent_at, timezone.now(),
                contact=sms_activity.to_contact
            )
            positive = False
        return positive

    def process_ambiguous_answer(self, sms_message, sent_message, sms_activity):
        # TODO: not sure if we should call sent_message.no_check_reply() here
        if sent_message:
            sms_message.add_related_objects(*sent_message.get_related_objects())
        sms_activity.create_activity(
            _('Ambiguous answer'), _('Ambiguous answer'),
            sms_message.sent_at, timezone.now(), contact=sms_activity.to_contact
        )
        if sms_activity.from_contact and sms_activity.to_contact:
            sms_data = {
                'full_name': str(sms_activity.from_contact),
                'phone_number': sms_message.from_number,
                'text': sms_message.text
            }
            template = "[[full_name]]: [[phone_number]]\n[[text]]"
            # TODO: compile template
            sms_text = template
            try:
                from_company_contact = sms_activity.from_contact.company_contact.last()
                from_number = None
                if from_company_contact:
                    company = from_company_contact.get_master_company()
                    from_number = get_phone_number(company and company[0])
                self.send(
                    sms_activity.to_contact.phone_mobile, sms_text, sms_activity.from_contact,
                    from_number=from_number, check_reply=False
                )
            except:
                pass

    @abstractmethod
    def process_sms_fetch(self):
        """
        Actually fetch SMS messages

        should throws SMSServiceError if error occurred
        """
        pass  # pragma: no cover

    @classmethod
    def get_sender_phones(self, contact):
        """
        Get sender phones
        """
        return []


class FakeSMSService(BaseSMSService):

    def process_sms_send(self, sms_message):
        sms_message.sid = 'FAKE_%s' % sms_message.id
        sms_message.save(update_fields=['sid'])

    def process_sms_fetch(self):
        res = []
        for sms in SMSMessage.objects.filter(is_fake=True):
            if not sms.sid.startswith('FAKE'):
                sms.sid = 'FAKE_%s' % sms.id
            sms.is_fake = False
            sms.save(update_fields=['sid', 'is_fake'])
            res.append(sms)
        return res
