from django.utils.functional import cached_property
from django.views.generic import FormView
from django.contrib import messages

from r3sourcer.apps.sms_interface.mixins import MessageView
from .forms import SMSForm
from .services import TwilioSMSService


class SMSDialogTemplateView(MessageView, FormView):

    form_class = SMSForm
    template_name = "base-message-template.html"

    sender_value_field = 'get_phone'
    recipient_field = 'phone_mobile'
    message_type = 'sms'

    @cached_property
    def get_sender_choices(self):

        phones = TwilioSMSService.get_sender_phones(self.request.user.contact)
        choices = []

        for phone in phones:
            item = (phone.id, "{company} {phone_number}".format(company=phone.company, phone_number=phone.phone_number))
            choices.append(item)

        return choices

    def get_sender(self):
        sender = self.request.POST['sender_user']
        return dict(self.get_sender_choices)[sender]

    def form_valid(self, form):

        for recipient in self.get_recipients():
            params = self.get_url_params()
            params.update(self.get_extra_params(recipient))
            params.update(self.get_json_params(form.cleaned_data['params']))

            sender_contact = self.get_sender()

            try:
                TwilioSMSService.send(
                        recipient.phone_mobile,
                        form.cleaned_data['body'],
                        sender_contact.phone_mobile,
                        sender_contact=sender_contact,
                        **params
                )
            except Exception as e:
                messages.add_message(self.request, messages.ERROR, self.ERROR_SENDING_MESSAGE % (
                    e, recipient, recipient.phone_mobile))
            else:
                messages.add_message(self.request, messages.SUCCESS, self.SUCCESS_SENDING % (
                    recipient, recipient.phone_mobile))
        return super(SMSDialogTemplateView, self).form_valid(form)
