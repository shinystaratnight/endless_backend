import decimal
import logging


from django.utils import timezone
from django.utils.decorators import method_decorator
from django.conf import settings
from django.db.models import Q


from r3sourcer.apps.pricing.models import PriceListRate
from .models import MYOBSyncObject
from .helpers import get_myob_client
from .mappers import InvoiceMapper, PayslipMapper, ActivityMapper


log = logging.getLogger(__name__)


def myob_enabled_mode(func):
    def fake_handler(*args, **kwargs):
        pass

    def wrapper(*args, **kwargs):
        if settings.ENABLED_MYOB_WORKING:
            return func(*args, **kwargs)
        return fake_handler(*args, **kwargs)

    return wrapper


class BaseSync:
    mapper_class = None
    mapper = None

    resource = None

    required_put_keys = ('UID', 'RowVersion', 'DisplayID')

    def __init__(self, myob_client=None, company=None, cf_id=None):
        self.client = myob_client or get_myob_client(cf_id=cf_id, company=company)
        if self.client is None:
            return

        self.client.init_api()

        self.company = company or self.client.cf_data.company

        if not self.mapper:
            self.mapper = self.mapper_class and self.mapper_class()

        self.resource = self._get_resource()

    def _update_sync_object(self, instance, legacy_number=None,
                            direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.myob):
        sync_obj = self._get_sync_object(instance, direction=direction)

        created = False
        if not sync_obj:
            sync_obj = MYOBSyncObject.objects.create(
                app=self.app,
                model=self.model,
                record=instance.id,
            )
            created = True

        if not created:
            sync_obj.synced_at = timezone.now()
        if self.company:
            sync_obj.company = self.company
        if legacy_number:
            sync_obj.legacy_myob_card_number = legacy_number
        if direction:
            sync_obj.direction = direction

        sync_obj.save()

    def _get_sync_objects_for_type(
            self, direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.myob):
        sync_obj_qs = MYOBSyncObject.objects.filter(
            app=self.app,
            model=self.model,
            direction=direction
        )

        if self.company:
            qry = Q(company=self.company)
            if not self.company.parent:
                qry |= Q(company__isnull=True)
        else:
            qry = Q(company__isnull=True) | Q(company__parent__isnull=True)

        return sync_obj_qs.filter(qry)

    def _get_sync_object(self, instance,
                         direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.myob):
        """
        Return MYOBSyncObject instance by object.

        :param instance: object Model subclass
        :param direction: str MYOBSyncObject.SYNC_DIRECTION_CHOICES
        :return: instance of MYOBSyncObject
        """

        sync_obj_qs = self._get_sync_objects_for_type(direction)
        return sync_obj_qs.filter(record=instance.id).first()

    def _is_synced(self, instance, sync_obj=None):
        """
        Check if object was synced.

        :param instance: object Model subclass
        :param sync_obj: object MYOBSyncObject
        :return: bool or None
        """

        if not sync_obj:
            sync_obj = self._get_sync_object(instance)

        if sync_obj:
            return instance.updated_at <= sync_obj.synced_at
        return

    def _is_synced_from_myob(self, instance, sync_obj=None):
        if not sync_obj:
            sync_obj = self._get_sync_object(
                instance,
                direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.django
            )

        if sync_obj:
            return instance.updated_at >= sync_obj.synced_at
        return

    def _get_object(self, params, resource=None, single=False):
        """
        Search remote resources from myob service.

        :param params: dict Search fields
        :param resource: object MYOBSyncObject
        :param single: bool Use for search single object
        :return: dict, list or None
        """

        resource = resource or self.resource
        resp = resource.get(raw_resp=True, params=params)

        try:
            resp = resp.json(parse_float=decimal.Decimal)
        except ValueError:
            log.warning('[MYOB API] Response error %s: %s',
                        resp.status_code, resp.text)
            return

        if 'Errors' in resp:
            for error in resp['Errors']:
                log.warning('[MYOB API] params: %s, error: %s',
                            params, error['Message'])
            return
        if single:
            return resp['Items'][0] if resp['Count'] else None
        return resp

    def _get_object_by_field(self, card_number, resource=None,
                             myob_field='DisplayID', single=False):
        if card_number is None:
            return
        return self._get_object(
            {"$filter": "{} eq '{}'".format(
                myob_field, card_number.replace("'", "''"))},
            resource=resource, single=single
        )

    def _get_resource(self):
        return None

    def _get_data_to_update(self, existing, new, deep=False, if_not_exists=None):
        if_not_exists = if_not_exists or []
        for key, value in existing.items():
            if not value:
                continue
            if key in self.required_put_keys:
                new[key] = value
                continue
            if key in if_not_exists and key not in new:
                new[key] = value
                continue

            if key in new or deep:
                if isinstance(value, dict):
                    if deep and value.get('UID'):
                        if key not in new:
                            new[key] = {'UID': value['UID']}
                    else:
                        new_data = self._get_data_to_update(
                            value, new.get(key, {}), True, if_not_exists=if_not_exists
                        )
                        new[key] = new_data
                elif isinstance(value, list):
                    new_data = self._get_list_data_to_update(
                        value, new.get(key, [])
                    )
                    new[key] = new_data
                elif new.get(key) is None or new.get(key) == '':
                    new[key] = value

        return new

    def _get_list_data_to_update(self, existing, new):
        if len(existing) == 0:
            return new
        result = new.copy()

        if not isinstance(existing[0], dict):
            return result

        add_only_param = False
        if existing[0].get('UID'):
            param = 'UID'
            add_only_param = True
        elif existing[0].get('Location'):
            param = 'Location'
        else:
            return result

        new_items = dict(map(lambda x: (x.get(param), x), result))
        for item in existing:
            existing_key = item[param]
            if existing_key not in new_items:
                result.append(
                    {param: existing_key} if add_only_param else item
                )
            elif not add_only_param:
                new_item = new_items[existing_key]
                new_item.update(self._get_data_to_update(item, new_item, True))

        return result

    def _sync_to(self, instance, sync_obj=None):
        raise NotImplementedError()

    def _get_myob_existing_resp(self, instance, myob_card_number,
                                sync_obj=None, field_name='DisplayID',
                                resource=None):
        """
        Search remote resource by field.

        :param instance: Model subclass instance
        :param myob_card_number: str Remote ID (DisplayID)
        :param sync_obj: MYOBSyncObject instance
        :param field_name: str Field name for filtering
        :param resource: class self.client.api
        :return:
        """

        old_myob_card_number = sync_obj and sync_obj.legacy_myob_card_number
        if old_myob_card_number:
            myob_card_number = old_myob_card_number

        myob_resp = self._get_object_by_field(myob_card_number,
                                              myob_field=field_name,
                                              resource=resource)
        if not myob_resp or not myob_resp['Count']:
            old_myob_card = self._find_old_myob_card(
                instance, resource=resource)
            if old_myob_card:
                myob_resp = old_myob_card
                if myob_resp['Count']:
                    myob_card_number = old_myob_card['Items'][0][field_name]
                    old_myob_card_number = myob_card_number

        return myob_card_number, old_myob_card_number, myob_resp

    def _find_old_myob_card(self, instance, resource=None):
        raise NotImplementedError()

    @method_decorator(myob_enabled_mode)
    def sync_to_myob(self, instance):
        if self.client is None:
            log.info('MYOB client is not defined')
            return

        cf_data = self.client.cf_data
        if not cf_data.is_enabled():
            log.warning('%s Company File is not enabled',
                        str(cf_data.company_file))
            return

        sync_obj = self._get_sync_object(instance)
        if sync_obj and self._is_synced(instance, sync_obj=sync_obj):
            return

        res = self._sync_to(instance, sync_obj)
        if res:
            self._update_sync_object(instance)

    def sync_from_myob(self):
        raise NotImplementedError()


class PaymentSync(BaseSync):

    def _get_resource(self):
        return self.client.api.GeneralLedger.GeneralJournal

    def _get_tax_code(self, code):
        return self._get_object_by_field(
            code, self.client.api.GeneralLedger.TaxCode, 'Code', True
        )

    def _get_account(self, display_id):
        return self._get_object_by_field(
            display_id, self.client.api.GeneralLedger.Account, single=True
        )


class InvoiceSync(PaymentSync):
    app = "core"
    model = "Invoice"
    mapper_class = InvoiceMapper

    def _get_resource(self):
        return self.client.api.Sale.Invoice.TimeBilling

    def _get_tax_codes(self):
        gst_code = self._get_object_by_field('GST', self.client.api.GeneralLedger.TaxCode, 'Code', True)
        gnr_code = self._get_object_by_field('GNR', self.client.api.GeneralLedger.TaxCode, 'Code', True)
        return {"GST": gst_code['UID'], "GNR": gnr_code['UID']}

    def _find_old_myob_card(self, invoice, resource=None):
        return self._get_object_by_field(
            invoice.myob_number.lower(),
            resource=resource,
        )

    def _create_or_update_activities(self, invoice, tax_codes):
        activities = dict()

        for invoice_line in invoice.invoice_lines.all():
            activity_mapper = ActivityMapper()
            vacancy = invoice_line.timesheet.vacancy_offer.vacancy
            skill = vacancy.position
            activity_display_id = str(vacancy.id)[:30]
            position_parts = vacancy.position.name.split(' ')
            price_list = invoice.customer_company.price_lists.get(effective=True)
            rate = PriceListRate.objects.filter(price_list=price_list, skill=skill)
            name = ' '.join([part[:4] for part in position_parts])
            income_account_resp = self._get_object_by_field(
                '4-1000',
                resource=self.client.api.GeneralLedger.Account,
                single=True
            )

            data = activity_mapper.map_to_myob(
                activity_display_id,
                name[:30],
                ActivityMapper.TYPE_HOURLY,
                ActivityMapper.STATUS_CHARGEABLE,
                rate=rate,
                tax_code=tax_codes[invoice_line.vat.name],
                income_account=income_account_resp['UID'],
                description='{} {}'.format(vacancy.position, rate if rate else 'Base Rate')
            )
            activity_response = self._get_object_by_field(activity_display_id,
                                                          self.client.api.TimeBilling.Activity,
                                                          single=True)

            if not activity_response:
                self.client.api.TimeBilling.Activity.post(json=data, raw_resp=True)
                activity_response = self._get_object_by_field(activity_display_id,
                                                              self.client.api.TimeBilling.Activity,
                                                              single=True)

            activities.update({invoice_line.id: activity_response['UID']})

        return activities

    def _sync_to(self, invoice, sync_obj=None):
        tax_codes = self._get_tax_codes()
        params = {"$filter": "CompanyName eq '%s'" % invoice.customer_company.name}
        customer_data = self.client.api.Contact.Customer.get(params=params)
        customer_uid = customer_data['Items'][0]['UID']
        activities = self._create_or_update_activities(invoice, tax_codes)

        data = self.mapper.map_to_myob(invoice, customer_uid, tax_codes, activities)
        resp = self.resource.post(json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            log.info('Invoice %s synced' % invoice.id)
        else:
            log.warning("[MYOB API] Invoice %s: %s", invoice.id, resp.text)
            return False

        return True


class PayslipSync(PaymentSync):
    app = "hr"
    model = "Payslip"
    mapper_class = PayslipMapper

    def _find_old_myob_card(self, payslip, resource=None):
        return self._get_object_by_field(
            payslip.myob_number.lower(),
            resource=resource,
        )

    def _sync_to(self, payslip, sync_obj=None):
        myob_tax = self._get_tax_code('GST')
        myob_account_wages = self._get_account('6-5130')
        myob_account_pay = self._get_account('1-1190')

        myob_account_payg = None
        if payslip.get_payg_pay() > decimal.Decimal():
            myob_account_payg = self._get_account('2-1420')

        myob_account_superann_credit = None
        myob_account_superann_debit = None
        if payslip.get_superannuation_pay() > decimal.Decimal():
            myob_account_superann_credit = self._get_account('2-1415')
            myob_account_superann_debit = self._get_account('6-5120')

        data = self.mapper.map_to_myob(
            payslip, myob_tax, myob_account_wages, myob_account_pay,
            myob_account_payg, myob_account_superann_debit,
            myob_account_superann_credit
        )

        resp = self.resource.post(json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            log.info('Payslip %s synced' % payslip.id)
        else:
            log.warning("[MYOB API] Payslip %s: %s", payslip.id, resp.text)
            return False

        return True
