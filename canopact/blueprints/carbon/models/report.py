"""Models for Report.

Author: James Patten
First Build: May 2020

Examples:
    from canopact.blueprints.carbon.models.report import Report
    from canopact.blueprints.carbon.models.expense import Expense
    r = Report()
    e = Expense()

"""
from canopact.extensions import db
from lib.util_sqlalchemy import ResourceMixin
from canopact.blueprints.carbon.models.expense import Expense
from vendors import expensify


class Report(ResourceMixin, db.Model):
    __tablename__ = 'reports'

    report_id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',
                                                  onupdate='CASCADE',
                                                  ondelete='CASCADE'),
                        index=True, nullable=False)
    # Columns.
    report_name = db.Column(db.String(100))

    expenses = db.relationship(Expense, backref="parent",
                               passive_deletes=True)

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Report, self).__init__(**kwargs)

    @staticmethod
    def fetch_expensify_reports(User, user_ids):
        """Fetch Expensify reports.

        Args:
            user_ids (list): list of user ids.

        Returns:
            dict: user_id and report list as key value pairs.

        """
        user_reports = {}
        for uid in user_ids:
            user = User.query.get(uid)

            # Get user Expensify API credentials.
            partnerUserID = user.expensify_id
            partnerUserSecret = user.expensify_secret

            # Get all reports from Expensify Integration Server.
            report_list = expensify.main(partnerUserID, partnerUserSecret)

            # Append id as key and report list as value in dict.
            user_reports[uid] = report_list

        return user_reports

    @staticmethod
    def parse_report_from_list(reports, r_num, user_id=None):
        """Parse and return the expenses fields from a report.

        Args:
            reports (list): list of reports.
            r_num (int): positional index of report to parse.
            user_id (int): id of user.

        Returns:
            dict: keys value pairs of report fields / information.
        """
        data = reports[r_num]

        report = {
            'report_id': data['report_id'],
            'user_id': user_id,
            'report_name': data['report_name']
        }

        return report
