from lib.util_sqlalchemy import ResourceMixin, AwareDateTime
from lib.util_datetime import tzware_datetime
from canopact.extensions import db


class Report(ResourceMixin, db.Model):
    __tablename__ = 'reports'

    report_id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',
                                                  onupdate='CASCADE',
                                                  ondelete='CASCADE'),
                        index=True, nullable=False)

    # Last updated date
    update_datetime = db.Column(AwareDateTime())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Report, self).__init__(**kwargs)

    @classmethod
    def parse_report_from_list(cls, reports, r_num, user_id=None):
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
            'user_id': user_id
        }

        return report

    def save_and_update_report(self):
        """Commit the report and update the the table.

        :return: SQLAlchemy save result
        """
        self.update_datetime = tzware_datetime()

        return self.save()


class Expense(ResourceMixin, db.Model):
    __tablename__ = 'expenses'

    expense_id = db.Column(db.BigInteger, primary_key=True)

    # Relationships.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',
                                                  onupdate='CASCADE',
                                                  ondelete='CASCADE'),
                        index=True, nullable=False)

    report_id = db.Column(db.BigInteger, db.ForeignKey('reports.report_id',
                                                       onupdate='CASCADE',
                                                       ondelete='CASCADE'),
                          index=True, nullable=False)

    # Expense columns.
    expense_type = db.Column(db.String(8))
    expense_category = db.Column(db.String(100))
    expense_amount = db.Column(db.Float())
    expense_currency = db.Column(db.String(8))
    expense_comment = db.Column(db.String(100))
    expense_converted_amount = db.Column(db.Float())
    expense_created_date = db.Column(db.Date())
    expense_inserted_date = db.Column(db.Date())
    expense_merchant = db.Column(db.String(50))
    expense_modified_amount = db.Column(db.Float())
    expense_modified_created_date = db.Column(db.Date())
    expense_modified_merchant = db.Column(db.String(100))
    # expense_unit_count = db.Column(db.Integer())
    # expense_unit_rate = db.Column(db.Float())
    # expense_unit_unit = db.Column(db.Float())

    # Last updated date
    update_datetime = db.Column(AwareDateTime())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Expense, self).__init__(**kwargs)

    @classmethod
    def parse_expenses_from_list(cls, reports, r_num, user_id=None):
        """Parse and return the expenses fields from a report.

        Args:
            report (list): list of reports
            r_num (int): positonal index of report to parse.
            user_id (int): id of user.

        Returns:
            dict: keys value pairs of expense fields / information.
        """
        report = reports[r_num]
        data = report['report_expenses']
        report_id = report['report_id']

        # Get the length of the id value.
        num_expenses = len(data['expense_id'])
        user_ids = [user_id] * num_expenses
        report_ids = [report_id] * num_expenses

        expenses = {
            'expense_id': data['expense_id'],
            'user_id': user_ids,
            'report_id': report_ids,
            'expense_type': data['expense_type'],
            'expense_category': data['expense_category'],
            'expense_amount': data['expense_amount'],
            'expense_currency': data['expense_currency'],
            'expense_comment': data['expense_comment'],
            'expense_converted_amount': data['expense_converted_amount'],
            'expense_created_date': data['expense_created_date'],
            'expense_inserted_date': data['expense_inserted_date'],
            'expense_merchant': data['expense_merchant'],
            'expense_modified_amount': data['expense_modified_amount'],
            'expense_modified_created_date': data['expense_modified_created_date'],
            'expense_modified_merchant': data['expense_modified_merchant']
            # 'expense_unit_count': data['expense_unit_count'],
            # 'expense_unit_rate': data['expense_unit_rate'],
            # 'expense_unit_unit': data['expense_unit_unit']
        }

        return expenses

    @classmethod
    def parse_expense_from_report(cls, expenses, e_num):
        """Parse a single expense from a dictionary of multiple expenses.

        Args:
            expenses (dict): Dictionary of multiple expenses.
            e_num (int): positional index of expense in expenses.

        Returns:
            dict: single expense.
        """
        # Sist of tuples for each key value of the expense with index:`exp_num`
        indexed_pairs = [(k, v[e_num]) for (k, v) in expenses.items()]
        # Convert into a dictionary.
        dict_pairs = dict(indexed_pairs)

        return dict_pairs

    def save_and_update_expense(self):
        """
        Commit the report and update the the table.

        :return: SQLAlchemy save result
        """
        self.update_datetime = tzware_datetime()

        return self.save()
