"""Models for Expense.

Author: James Patten
First Build: May 2020

Examples:
    from canopact.blueprints.carbon.models.expense import Expense
    e = Expense()

"""
from canopact.extensions import db
from canopact.blueprints.carbon.models.carbon import Carbon
from canopact.blueprints.carbon.models.route import Route
from sqlalchemy import exists
import pandas as pd
from lib.util_sqlalchemy import ResourceMixin


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

    routes = db.relationship(Route, backref="parent",
                             passive_deletes=True)

    # Expense columns.
    expense_type = db.Column(db.String(50))
    expense_category = db.Column(db.String(100))
    expense_amount = db.Column(db.Float())
    expense_currency = db.Column(db.String(50))
    expense_comment = db.Column(db.String(100))
    expense_converted_amount = db.Column(db.Float())
    expense_created_date = db.Column(db.Date())
    expense_inserted_date = db.Column(db.Date())
    expense_merchant = db.Column(db.String(50))
    expense_modified_amount = db.Column(db.Float())
    expense_modified_created_date = db.Column(db.Date())
    expense_modified_merchant = db.Column(db.String(100))
    expense_unit_count = db.Column(db.Integer())
    expense_unit_rate = db.Column(db.Float())
    expense_unit_unit = db.Column(db.String(10))
    travel_expense = db.Column(db.Integer())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Expense, self).__init__(**kwargs)
        self.travel_expense = self.is_travel_expense()

    @staticmethod
    def parse_expenses_from_list(reports, r_num, user_id=None):
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
            'expense_modified_created_date':
                data['expense_modified_created_date'],
            'expense_modified_merchant': data['expense_modified_merchant'],
            'expense_unit_count': data['expense_unit_count'],
            'expense_unit_rate': data['expense_unit_rate'],
            'expense_unit_unit': data['expense_unit_unit']
        }

        return expenses

    @staticmethod
    def parse_expense_from_report(expenses, e_num):
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

        # Replace empty values with None.
        for k, v in dict_pairs.items():
            if v == '':
                dict_pairs[k] = None

        return dict_pairs

    def is_travel_expense(self, categories=[
                                    'Car, Van and Travel Expenses: Air',
                                    'Car, Van and Travel Expenses: Bus',
                                    'Car, Van and Travel Expenses: Car Hire',
                                    'Car, Van and Travel Expenses: Fuel',
                                    'Car, Van and Travel Expenses: Taxi',
                                    'Car, Van and Travel Expenses: Train']):
        """Checks whether expense is in one of the required `categories`.

        Args:
            categories (list): valid travel expense categories.

        Returns:
            travel_expense (int): 1 if a travel expense, 0 otherwise.

        """
        if self.expense_category in categories:
            travel_expense = 1
        else:
            travel_expense = 0

        return travel_expense

    @staticmethod
    def get_new_expenses():
        """Retrieve expenses that do not yet have carbon calculated.

        Checks to see if expense id exists in the carbon table.

        Returns:
            ids (list): expense ids which are not in the carbon table.

        """
        # Get expenses that are travel expenses but not already in
        # the `carbon` table.
        expenses = db.session.query(Expense) \
                     .filter(Expense.travel_expense == 1) \
                     .filter(~exists().where(
                         Carbon.expense_id == Expense.expense_id))

        df = pd.DataFrame(columns=['expense_id', 'expense_type',
                                   'expense_category', 'expense_comment',
                                   'expense_unit_count', 'expense_unit_unit'])

        for expense in expenses:
            row = {
                'expense_id': expense.expense_id,
                'expense_type': expense.expense_type,
                'expense_category': expense.expense_category,
                'expense_comment': expense.expense_comment,
                'expense_unit_count': expense.expense_unit_count,
                'expense_unit_unit': expense.expense_unit_unit
            }

            df = df.append(row, ignore_index=True)

        if len(df) == 0:
            df = None

        return df
