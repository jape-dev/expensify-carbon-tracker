import datetime
import pytz

from canopact.blueprints.company.models import Company


class TestCompany():
    def test_expire_free_trials(self, session, companies):
        """Test for Company.expire_free_trials()"""
        may_29_2015 = datetime.datetime(2015, 5, 29, 0, 0, 0)
        may_29_2015 = pytz.utc.localize(may_29_2015)

        june_29_2015 = datetime.datetime(2015, 6, 29, 0, 0, 0)
        june_29_2015 = pytz.utc.localize(june_29_2015)

        Company.expire_free_trials(june_29_2015)

        company1 = Company.query.get(1)
        assert company1.trial_active is False

        company2 = Company.query.get(2)
        assert company2.trial_active is True

        company3 = Company.query.get(3)
        assert company3.trial_active is False
