"""Models for routes

Author: James Patten
First Build: May 2020

"""

from flask import current_app
from canopact.extensions import db
import pandas as pd
import numpy as np
import requests
import sqlalchemy
from sqlalchemy import or_
from lib.util_sqlalchemy import ResourceMixin


class Route(ResourceMixin, db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    expense_id = db.Column(db.BigInteger, db.ForeignKey('expenses.expense_id',
                                                        onupdate='CASCADE',
                                                        ondelete='CASCADE'),
                           index=True, nullable=False)

    # Route columns.
    expense_category = db.Column(db.String(100))
    route_category = db.Column(db.String(100))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    return_type = db.Column(db.String(10))
    invalid = db.Column(db.Integer())
    distance = db.Column(db.Float())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Route, self).__init__(**kwargs)

    @staticmethod
    def split_orig_dest(description):
        """Splits description into origin and destination.

        Validation is done by checking description is of format:
        <origin>; <destination>;.

        Args:
            description (str): description line from the expense.

        Returns:
            tuple: origin and destination strings.

        """
        try:
            if ';' not in description or description.count(';') != 2:
                raise ValueError("Description incorrectly formatted. Must be: "
                                 "<origin>; <destination>;")
        except TypeError as e:
            raise TypeError(e)

        # Split out the origin and destination into seperate strings.
        route = description.split(';')
        org = route[0]
        dst = route[1]
        type = route[2]

        return org, dst, type

    @staticmethod
    def check_route_exists(orig, dest):
        """Check if combination of origin/destination alreasy exists

        Args:
            orig (str): origin address.
            dest (str): destination address.

        Returns:
            bool: True if route already exists, False otherwise.

        """
        try:
            routes = db.session.query(Route.id) \
                    .filter(Route.origin == orig) \
                    .filter(Route.destination == dest)
            ids = [u[0] for u in routes]
        except sqlalchemy.exc.ProgrammingError:
            db.session.rollback()
            print('routes have not been initialised yet')
            # routes table has not been initialised yet.
            return False

        if len(ids) > 0:
            return True
        else:
            return False

    @staticmethod
    def get_route_type(category, air_cats=[
                        'Car, Van and Travel Expenses: Air'],
                       ground_cats=[
                                    'Car, Van and Travel Expenses: Bus',
                                    'Car, Van and Travel Expenses: Car Hire',
                                    'Car, Van and Travel Expenses: Fuel',
                                    'Car, Van and Travel Expenses: Taxi',
                                    'Car, Van and Travel Expenses: Train']):
        """Categorises expense category into 'air' or 'ground' modes of travel.

        Args:
            category (str): expense_category.
            air_cats (list): categories for air modes of travel.
            ground_cats (list): categories for ground modes of travel.

        Raises:
            ValueError: if category not in `air_cats` or `ground_cats`.

        Returns:
            str: air or ground depending on the category.
        """
        if category in air_cats:
            return 'air'
        elif category in ground_cats:
            return 'ground'
        else:
            raise ValueError(f"{category} not in {air_cats} or {ground_cats}")

    @staticmethod
    def get_ammended_routes():
        """Get routes that have had their origin/destination updated.

        These routes still need to have a distance calculated for them.

        """
        routes = db.session.query(Route) \
                   .filter(Route.origin.isnot(None)) \
                   .filter(Route.destination.isnot(None)) \
                   .filter(Route.distance.is_(None))

        df = pd.DataFrame(columns=['id', 'expense_id', 'expense_category'
                                   'route_category', 'origin', 'destination',
                                   'return_type', 'exists'])

        for route in routes:
            row = {
                'id': route.id,
                'expense_id': route.expense_id,
                'expense_category': route.expense_category,
                'route_category': route.route_category,
                'origin': route.origin,
                'destination': route.destination,
                'return_type': route.return_type,
                'exists': False
            }

            df = df.append(row, ignore_index=True)

        if len(df) == 0:
            df = None

        return df

    @staticmethod
    def create_routes(df=None, comment_col='expense_comment',
                      category_col='expense_category',
                      type_col='expense_type', ammend=True):
        """Wrapper function to format route columns.

        Args:
            comment_col (str): column name that contains expense columns.
            category_col (str): column name that contains expense categories.
            ammend (bool): if True, append routes that have been ammended to
                the DataFrame.

        Returns:
            df (pandas.DataFrame): dataframe containing new columns: origin,
                destination, exists and route category.

        """

        def apply_route_methods(row):
            """Helper function to apply methods from Routes to the `new` DataFrame.

            Returns
                row (pd.DataFrame): row containing updated route fields.
            """
            row['id'] = None

            if row[type_col] != 'expense':
                row['route_category'] = 'unit'
            else:
                try:
                    org, dst, type = Route.split_orig_dest(row[comment_col])
                except(ValueError, TypeError):
                    org, dst, type = None, None, None

                row['origin'] = org
                row['destination'] = dst
                row['return_type'] = type
                exists = Route.check_route_exists(org, dst)
                row['exists'] = exists
                row['route_category'] = Route.get_route_type(row[category_col])
                row['distance'] = None

            return row

        if df is not None:
            df = df.apply(lambda row: apply_route_methods(row), axis=1)

        if ammend:
            # Append on the ammended routes to the new routes.
            ammended = Route.get_ammended_routes()
        else:
            ammended = None

        if df is not None and ammended is not None:
            df = df.append(ammended, ignore_index=True)
        elif df is None and ammended is not None:
            df = ammended
        elif df is None and ammended is None:
            df = None
        else:
            df = df

        return df

    @classmethod
    def search(cls, query):
        """
        Search a resource by 1 or more fields.

        :param query: Search query
        :type query: str
        :return: SQLAlchemy filter
        """
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.report import Report

        if not query:
            return ''

        search_query = '%{0}%'.format(query)
        search_chain = (Report.report_name.ilike(search_query),
                        Expense.expense_merchant.ilike(search_query),
                        Expense.expense_comment.ilike(search_query),
                        Expense.expense_category.ilike(search_query))

        return or_(*search_chain)


class Distance():
    """Contains related methods for distance calculations."""

    @staticmethod
    def get_ground_urls(df, orig_col='origin', dest_col='destination',
                        unit='metric', mode='driving', url=None,  key=None):
        """ Create urls for distance matrix api requests.

        Checks if origin/destination pairing is new and builds url if new.

        Args:
            df (pandas.DataFrame): contains origin and destination addresses
                to have urls built for them.
            orig_col (str): name of origin column in df.
            dest_col (str): name of destination column in df.
            unit (str): unit of distance to include in url.
            mode (str): travel mode: can be 'driving' or 'transit'.
            url (str): base url for api.
            key (str): api key.

        Returns:
            df (pandas.DataFrame): with new column `url`.

        """
        if url is None:
            url = current_app.config['DISTANCE_URL']
        if key is None:
            key = current_app.config['DISTANCE_KEY']

        def build_url(row):
            """Helper function to build urls."""

            if row[orig_col] is None or row[dest_col] is None:
                request = None
            else:
                request = ''.join([url, f'units={unit}', f'&mode={mode}',
                                   f'&origins={row[orig_col]}',
                                   f'&destinations={row[dest_col]}',
                                   f'&key={key}'])

            return request

        df['url'] = df.apply(lambda row: build_url(row), axis=1)

        return df

    @staticmethod
    def calculate_ground_distance(df, url_col='url'):
        """Calculates distance for ground modes of Travel.

        Distance calculation is made by the Google Maps Distance Matrix API.

        Notes:
            Requires each url to only request one element.

        Args:
            df (pandas.DataFrame): dataframe for making requests on.
            url_col (str): column name that contains urls for api request.

        Returns:
            df (pandas.DataFrame): with new column `distance`.

        """
        urls = df[url_col].tolist()
        responses = [requests.get(u) if u is not None else None for u in urls]
        jsons = [r.json() if r is not None else None for r in responses]
        df['json'] = np.array(jsons)

        def parse_json(row):
            """Parses responses from the distance matrix api"""

            json = row['json']

            if json is None:
                return None

            if json['status'] == 'OK':
                element = json['rows'][0]['elements'][0]
            else:
                print(f"Distance Matrix API request failed with status code:"
                      f"{json['status']}")
                return None

            if element['status'] == 'OK':
                distance = element['distance']['value']
                # Convert from metres into km.
                distance = distance / 1000
            else:
                print(f"Distance Matrix API request failed with status code:"
                      f"{element['status']}")
                distance = None

            return distance

        df['distance'] = df.apply(lambda row: parse_json(row), axis=1)

        return df

    @staticmethod
    def get_air_urls(df, orig_col='origin', dest_col='destination', url=None):
        """Creates urls for distance24.org api requests.

        Args:
            df (pandas.DataFrame): contains origin and destination addresses
                to have urls built for them.
            orig_col (str): name of origin column in df.
            dest_col (str): name of destination column in df.
            url (str): base url for api.

        Returns:
            df (pandas.DataFrame): with new column `url`.

        """
        if url is None:
            url = current_app.config['DISTANCE_24_URL']

        def build_url(row):
            """Helper function to build urls."""
            if row[orig_col] is None or row[dest_col] is None:
                request = None
            else:
                stops = f"{row[orig_col]}|{row[dest_col].lstrip()}"
                request = ''.join([url, f"stops={stops}"])

            return request

        df['url'] = df.apply(lambda row: build_url(row), axis=1)

        return df

    @staticmethod
    def calculate_air_distance(df, url_col='url'):
        """Calculates distance travlled for flights using distance24.org.

        Args:
            df (pandas.DataFrame): dataframe for making requests on.
            url_col (str): column name that contains urls for api request.

        Returns:
            df (pandas.DataFrame): with new column `distance`.

        """
        urls = df[url_col].tolist()
        responses = [requests.get(u) if u is not None else None for u in urls]
        jsons = [r.json() if r is not None else None for r in responses]
        df['json'] = np.array(jsons)

        def parse_json(row):
            """Parses responses from the distance24 api"""

            json = row['json']

            if json is None:
                return None

            if len(json['distances']) > 0:
                distance = json['distance']
            else:
                print(f"Distance24 API request failed with status: "
                      f"invalid stops.")
                distance = None

            return distance

        df['distance'] = df.apply(lambda row: parse_json(row), axis=1)

        return df

    @staticmethod
    def get_unit_distance(df, distance_col='expense_unit_count',
                          unit_col='expense_unit_unit'):
        """Retrieve the distance from 'distance' expense reports.

        Args:
            df (pandas.DataFrame): contains distance expense reports.
            distance_col (str): name of column that contains distance amount.
            unit_col (str): name of column that contains distance_units.

        Returns:
            df (pandas.DataFrame): with new column `distance`.

        """

        def convert_distance(row):
            """Helper function to convert distance into correct unit."""
            if row[unit_col] == 'mi':
                distance = row[distance_col] * 1.609
            else:
                distance = row[distance_col]

            return distance

        df['distance'] = df.apply(lambda row: convert_distance(row), axis=1)

        return df

    @staticmethod
    def return_distance(df, type_col='return_type',
                        distance_col='distance'):
        """Helper function to double distance for return trips.

        Args:
            df (pandas.DataFrame): row containing routes.

        Returns:
            df (pandas.DataFrame): row with updated distance if route
                is a rturn trip.

        """

        def double(row):
            """Helper function to double distance if route is a  return trip.

            First checks is return_type col is null.

            """
            type = row[type_col]

            if type is not None or type != np.NaN:
                type = str(type)
                if 'r' in type or 'R' in type:
                    distance = row[distance_col] * 2
                else:
                    distance = row[distance_col]
            else:
                distance = row[distance_col]

            return distance

        df[distance_col] = df.apply(lambda row: double(row), axis=1)

        return df

    @staticmethod
    def calculate_distance(df, category_col="route_category"):
        """Wrapper function to calculate distance for routes.

        Args:
            df (pandas.DataFrame): contains routes for distance calculations.
            category_col (str): name of column containing route categories.

        Returns:
            distances (pandas.DataFrame): contains calculated distances.

        """
        cols = list(df)

        # Split dataframe into unit expenses, ground expenses and air expenses.
        unit = df[df[category_col] == 'unit']
        grnd = df[df[category_col] == 'ground']
        air = df[df[category_col] == 'air']

        print(f"{len(df)} routes retrived. {len(unit)} unit, {len(grnd)}"
              f" ground and {len(air)} air.")

        if len(unit) > 0:
            unit_distance = Distance.get_unit_distance(unit)
        else:
            unit_distance = pd.DataFrame(columns=cols, index=[0])

        if len(grnd) > 0:
            urls = Distance.get_ground_urls(grnd)
            ground_distance = Distance.calculate_ground_distance(urls)
            # Remove unrequired columns.
            ground_distance.drop(['url', 'json'], axis=1, errors='ignore',
                                 inplace=True)
        else:
            ground_distance = pd.DataFrame(columns=cols, index=[0])

        if len(air) > 0:
            air_urls = Distance.get_air_urls(air)
            air_distance = Distance.calculate_air_distance(air_urls)
            # Remove unrequired columns.
            air_distance.drop(['url', 'json'], axis=1, errors='ignore',
                              inplace=True)
        else:
            air_distance = pd.DataFrame(columns=cols, index=[0])

        distances = unit_distance.append([ground_distance, air_distance])

        # Double the distances for return trips.
        distances = Distance.return_distance(distances)

        # Add the invalid marker for any routes that don't have a distance.
        distances['invalid'] = [1 if d is None else 0 for d in
                                distances['distance']]

        # Remove any rows that contain a null id.
        distances = distances[distances[category_col].notna()]

        return distances
