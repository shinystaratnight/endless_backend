class TestSMSBalance:
    def test_substract_sms_cost(self, client, user, company, relationship):
        sms_balance = company.sms_balance
        sms_balance.balance = 100
        sms_balance.save()
        sms_balance.substract_sms_cost(3)

        assert sms_balance.balance == 99.76

    def test_substract_sms_cost_with_discount(self, client, user, company, relationship):
        sms_balance = company.sms_balance
        sms_balance.balance = 100
        sms_balance.discount = 7
        sms_balance.save()
        sms_balance.substract_sms_cost(3)

        assert sms_balance.balance == 99.7768

    def test_top_up_limit(self, client, user, company, relationship):
        initial_balance = 20
        sms_balance = company.sms_balance
        sms_balance.balance = 20
        sms_balance.top_up_limit = 20
        sms_balance.save()

        assert sms_balance.balance == initial_balance + sms_balance.top_up_amount
