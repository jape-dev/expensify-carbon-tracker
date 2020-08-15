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
from lib.util_sqlalchemy import ResourceMixin


class Route(ResourceMixin, db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    expense_category = db.Column(db.String(100))
    route_category = db.Column(db.String(100))
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
        if ';' not in description or description.count(';') != 2:
            raise ValueError("Description incorrectly formatted. Must be: "
                             "<origin>; <destination>;")

        # Split out the origin and destination into seperate strings.
        route = description.split(';')
        org = route[0]
        dst = route[1]

        return org, dst

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
    def create_routes(df, comment_col='expense_comment',
                      category_col='expense_category',
                      type_col='expense_type'):
        """Wrapper function to format route columns.

        Args:
            comment_col (str): column name that contains expense columns.
            category_col (str): column name that contains expense categories.

        Returns:
            df (pandas.DataFrame): dataframe containing new columns: origin,
                destination, exists and route category.

        """

        def apply_route_methods(row):
            """Helper function to apply methods from Routes to the `new` DataFrame.

            """
            if row[type_col] != 'expense':
                row['route_category'] = 'unit'
            else:
                org, dst = Route.split_orig_dest(row[comment_col])
                row['origin'] = org
                row['destination'] = dst
                exists = Route.check_route_exists(org, dst)
                row['exists'] = exists
                row['route_category'] = Route.get_route_type(row[category_col])

            return row

        df = df.apply(lambda row: apply_route_methods(row), axis=1)

        return df


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
            request = ''.join([url, f'units={unit}', f'&mode={mode}',
                               f'&origins={row[orig_col]}',
                               f'&destinations={row[dest_col]}', f'&key={key}']
                              )

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
        responses = [requests.get(u) for u in urls]
        jsons = [r.json() for r in responses]
        df['json'] = np.array(jsons)

        def parse_json(row):
            """Parses responses from the distance matrix api"""

            json = row['json']

            if json['status'] == 'OK':
                element = json['rows'][0]['elements'][0]
            else:
                print(f"Distance Matrix API request failed with status code:"
                      f"{json['status']}")
                return None

            if element['status'] == 'OK':
                distance = element['distance']['value']
            else:
                print(f"Distance Matrix API request failed with status code:"
                      f"{element['status']}")
                distance = None

            # Convert from metres into km.
            distance = distance / 1000

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
        responses = [requests.get(u) for u in urls]
        jsons = [r.json() for r in responses]
        df['json'] = np.array(jsons)

        def parse_json(row):
            """Parses responses from the distance24 api"""

            json = row['json']

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
    def calculate_distance(df, category_col="route_category"):
        """Wrapper function to calculate distance for routes.

        Args:
            df (pandas.DataFrame): contains routes for distance calculations.
            category_col (str): name of column containing route categories.

        Returns:
            distances (pandas.DataFrame): contains calculated distances.

        """
        cols = list(df)
        cols.append('distance')

        # Split dataframe into unit expenses, ground expenses and air expenses.
        unit = df[df[category_col] == 'unit']
        grnd = df[df[category_col] == 'ground']
        air = df[df[category_col] == 'air']

        print(f"{len(df)} expenses retrived.  {len(unit)} unit, {len(grnd)}"
              f" ground and {len(air)} air.")

        if len(unit) > 0:
            unit_distance = Distance.get_unit_distance(unit)
        else:
            unit_distance = pd.DataFrame(columns=cols, index=[0])

        if len(grnd) > 0:
            urls = Distance.get_ground_urls(grnd)
            ground_distance = Distance.calculate_ground_distance(urls)
        else:
            ground_distance = pd.DataFrame(columns=cols, index=[0])

        if len(air) > 0:
            air_urls = Distance.get_air_urls(air)
            air_distance = Distance.calculate_air_distance(air_urls)
        else:
            air_distance = pd.DataFrame(columns=cols, index=[0])

        distances = unit_distance.append([ground_distance, air_distance])

        # Remove any rows that contain a null id.
        distances = distances[distances[category_col].notna()]

        return distances
