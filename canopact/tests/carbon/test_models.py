"""Tests for carbon models"""

from canopact.blueprints.carbon.models.carbon import Carbon
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.carbon.models.route import Route
from canopact.blueprints.carbon.models.route import Distance
from pandas.testing import assert_frame_equal, assert_series_equal
import pandas as pd
import pytest


class TestExpense():
    def test_is_travel_expense(self, expense_instance):
        """Test for Expense.is_travel_expense().

        Args:
            expense_instance (reports.Expense): instance of Expense.

        """
        assert expense_instance.travel_expense == 1

        # Update the expense category to a non-travel category.
        non_travel_attr = {
            'expense_id': 1,
            'user_id': 1,
            'report_id': 1,
            'expense_type': 'Expense',
            'expense_category': 'Food'
        }
        non_travel_expense = Expense(**non_travel_attr)

        assert non_travel_expense.travel_expense == 0

    def test_get_new_expenses(self, reports, expenses, carbons):
        """Test for Expense.get_new_expenses()

        Args:
            reports (pytest.fixture): fixture for reports using test db.
            expenses (pytest.fixture): fixture for reports using test db.
            carbons (pytest.fixture): fixture for reports using test db.

        """
        row = {
            'expense_id': 3,
            'expense_type': 'expense',
            'expense_category': 'Car, Van and Travel Expenses: Taxi',
            'expense_comment': 'Blackfriars, London; Shoreditch, London;',
            'expense_unit_count': None,
            'expense_unit_unit': None
        }

        expected_df = pd.DataFrame(data=row, index=[0])
        actual_df = Expense.get_new_expenses()

        assert_frame_equal(expected_df, actual_df,  check_dtype=False)


class TestRoute():
    def test_split_orig_dest(self):
        """Test for Route.split_orig_dest()"""
        desc = "Harrow, London; Old Trafford, Manchester;"
        org, dst = Route.split_orig_dest(desc)
        assert org == "Harrow, London"
        assert dst == " Old Trafford, Manchester"

        with pytest.raises(ValueError) as err:
            desc = "Harrow, London to Old Trafford, Manchester;"
            Route.split_orig_dest(desc)
            assert err.type == ValueError

    def test_check_route_exists(self, routes):
        """Test for Route.check_route_exists()

        Args:
            routes (pytest.fixture): routes table using test db.

        """
        orig = "Harrow, London"
        dest = "Wembley, London"
        exists = Route.check_route_exists(orig, dest)
        assert exists is True

        orig = "Harrow, London"
        dest = "Old Trafford, Manchester"
        exists = Route.check_route_exists(orig, dest)
        assert exists is False

    def test_create_routes(self, expenses, carbons):
        """Test for Route.create_routes().

        Args:
            expenses (pytest.fixture): expenses table using test db.
            carbons (pytest.fixture): carbons table using test db.

        """
        cols = {
            'expense_id': 1,
            'user_id': 1,
            'report_id': 1,
            'expense_type': 'expense',
            'expense_category': 'Car, Van and Travel Expenses: Air',
            'expense_comment': "Blackfriars, London; Shoreditch, London;"
        }

        new_cols = {
            'origin': 'Blackfriars, London',
            'destination': ' Shoreditch, London',
            'exists': False,
            'route_category': 'air',
            'distance': None
        }

        expense = pd.DataFrame(cols, index=[0])
        all_cols = {**cols, **new_cols}
        new_expense = pd.DataFrame(all_cols, index=[0])
        actual_df = Route.create_routes(expense)

        assert_frame_equal(new_expense, actual_df)


class TestDistance():
    def test_get_ground_urls(self, distance_df):
        """Test for Distance.get_distance_urls()."""
        df = distance_df[['expense_id', 'origin', 'destination']]

        df_urls = Distance.get_ground_urls(df, key="fake123")

        assert_frame_equal(distance_df, df_urls)

    def test_calculate_ground_distance(self, monkeypatch, distance_df,
                                       mock_ground_api_response):
        """Test for Distance.calculate_ground_disance()"""
        monkeypatch.setattr("requests.get", mock_ground_api_response)

        df_distance = Distance.calculate_ground_distance(distance_df)

        expected_distances = pd.Series([5.611, 1934.3], name="distance")

        assert_series_equal(df_distance['distance'], expected_distances)

    def test_get_air_urls(self, air_df):
        """Test for Distance.get_distance_urls()."""
        df = air_df[['expense_id', 'origin', 'destination']]

        df_urls = Distance.get_air_urls(df)

        assert_frame_equal(air_df, df_urls)

    def test_calculate_air_distance(self, air_df):
        """Test for Distance.calculate_ground_disance()"""

        df_distance = Distance.calculate_air_distance(air_df)

        expected_distances = pd.Series([256, 40], name="distance")

        assert_series_equal(df_distance['distance'], expected_distances)


class TestCarbon():
    def test_convert_to_carbon_air(self):
        expected_co2 = 85.5415
        actual_co2 = Carbon.convert_to_carbon_air(distance=550)

        assert expected_co2 == actual_co2
