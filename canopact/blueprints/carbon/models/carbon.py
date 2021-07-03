"""Models for Carbon

Calculates carbon emissions from Expensify report and expense data.

"""

import calendar
import datetime
from dateutil.relativedelta import relativedelta
import math

from canopact.extensions import db
from flask import current_app
from lib.util_sqlalchemy import ResourceMixin
from sqlalchemy import func


class Carbon(ResourceMixin, db.Model):
    __tablename__ = 'carbon'

    id = db.Column(db.Integer, primary_key=True)

    # Relationships
    expense_id = db.Column(db.BigInteger, db.ForeignKey('expenses.expense_id',
                                                        onupdate='CASCADE',
                                                        ondelete='CASCADE'),
                           index=True, nullable=False)
    expense_category = db.Column(db.String(100))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    distance = db.Column(db.Float())
    co2e = db.Column(db.Float())
    co2 = db.Column(db.Float())
    ch4 = db.Column(db.Float())
    n2o = db.Column(db.Float())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Carbon, self).__init__(**kwargs)

    @staticmethod
    def convert(distance, mode, factors=None):
        """Convert distance into greenhouse emissions.

        Args:
            distance (float): distance in in km.
            factors (dict): emissions factors.

        Notes:
            * distance must be in the units km.
            * if factors is None, the DEFRA emission factors will be used.

        Returns:
            emissions (dict): co2e, co2, ch4 and n2o emissions.

        """
        if factors is None:
            factors = current_app.config['DEFRA_EMISSION_FACTORS']

        emissions = {}

        for e, f in factors.items():
            try:
                factor = f[mode]
            except KeyError:
                if mode == 'air':
                    err = f'Use convert_to_emissions_air() for air modes.'
                elif mode == 'bus':
                    err = 'Use convert_to_emissions_bus() for bus modes.'
                else:
                    err = (f'Could not find {mode} in `factors`. Should be in:'
                           f' [car, taxi, train]')
                raise KeyError(err)

            em = distance * factor
            emissions[e] = em

        return emissions

    @staticmethod
    def convert_air(distance, factors):
        """Convert distance for flight travel into greenhouse emissions.

        Args:
            distance (float): distance in in km.
            factors (dict): emissions factors.

        Notes:
            distance must be in the units km.
            short: emissions factor for short haul flights
                500km - 2500km.
            long emissions: factor for long haul flights > 2500km.
            domestic: emissions factors for domestic flights <= 500km.

        Returns:
            emissions (dict): co2e, co2, ch4 and n2o emissions.

        """
        if factors is None:
            factors = current_app.config['DEFRA_EMISSION_FACTORS']

        emissions = {}

        for e, f in factors.items():
            air = f['air']
            long = air['long']
            short = air['short']
            domestic = air['domestic']

            if distance > 0 and distance <= 500:
                em = distance * domestic
            elif distance > 500 and distance <= 2500:
                em = distance * short
            else:
                em = distance * long

            emissions[e] = em

        return emissions

    @staticmethod
    def convert_bus(distance, factors):
        """Convert distance for bus travel into greenhouse emissions.

        Args:
            distance (float): distance in in km.
            factors (dict): emissions factors.

        Notes:
            distance must be in the units km.
            local: emissions factor for short distance <= 25km.
            coach: emissions factor for long distance > 25km.

        Returns:
            emissions (dict): co2e, co2, ch4 and n2o emissions.

        """
        if factors is None:
            factors = current_app.config['DEFRA_EMISSION_FACTORS']

        emissions = {}

        for e, f in factors.items():
            bus = f['bus']
            local = bus['local']
            coach = bus['coach']

            if distance > 0 and distance <= 25:
                em = distance * local
            else:
                em = distance * coach

            emissions[e] = em

        return emissions

    @staticmethod
    def get_travel_mode(category):
        """Helper function to convert Expensify category into EF mode.

        Args:
            category (str): Expensify category.

        Returns:
            mode (str): travel mode for emission factors.

        """
        if category in ['Car, Van and Travel Expenses: Car Hire',
                        'Car, Van and Travel Expenses: Fuel']:
            mode = 'car'
        elif category == 'Car, Van and Travel Expenses: Taxi':
            mode = 'taxi'
        elif category == 'Car, Van and Travel Expenses: Train':
            mode = 'train'
        else:
            mode = None

        return mode

    @classmethod
    def emissions(cls, distance=None, category=None, factors=None, **kwargs):
        """Factory method to convert distance to greenhouse emissions.

        Args:
            distance (float): distance in in km.
            category (str): expense category.
            factors (dict): emissions factors.

        Returns
            carbon.Carbon: instantiated Carbon class.

        """
        if factors is None:
            factors = current_app.config['DEFRA_EMISSION_FACTORS']
        if distance is None:
            distance = kwargs.get('distance')
            kwargs.pop('distance')
        if category is None:
            category = kwargs.get('expense_category')

        mode = Carbon.get_travel_mode(category)

        if mode is None:
            if category == 'Car, Van and Travel Expenses: Air':
                ems = Carbon.convert_air(distance, factors)
            elif category == 'Car, Van and Travel Expenses: Bus':
                ems = Carbon.convert_bus(distance, factors)
            else:
                raise ValueError(f"{category} is an invalid category. Must be "
                                 f"one of Car, Van and Travel Expenses:<'Taxi'"
                                 f", 'Air', 'Bus', 'Car Hire', 'Fuel', 'Taxi'"
                                 f", 'Train'>.")
        else:
            ems = Carbon.convert(distance, mode, factors)

        return cls(distance=distance, **kwargs, **ems)

    @staticmethod
    def group_and_sum_emissions(user, agg='employee', prev_month=False,
                                **kwargs):
        """Group and sum emissions by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.
            prev_month (bool): if true, apply month offset of one month.

        Returns:
            results (dict): dictionary of different emissions grouped by agg.

        """
        # Prevent circular import.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.user.models import User

        co2e = func.sum(Carbon.co2e)
        co2 = func.sum(Carbon.co2)
        ch4 = func.sum(Carbon.ch4)
        n2o = func.sum(Carbon.n2o)

        if prev_month:
            start = Carbon.get_prev_months_date(prev_months=1, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=1, first=False,
                                              **kwargs)
        else:
            start = Carbon.get_prev_months_date(prev_months=0, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=0, first=False,
                                              **kwargs)

        if agg == 'company':

            users = db.session.query(User.id) \
                .filter(User.company_id == user.company_id).all()

            query = db.session.query(co2e, co2, ch4, n2o) \
                .join(Expense, Carbon.expense_id == Expense.expense_id) \
                .filter(Expense.user_id.in_(users)) \
                .filter(Expense.expense_created_date >= start) \
                .filter(Expense.expense_created_date <= end) \
                .all()
        elif agg == 'employee':
            query = db.session.query(co2e, co2, ch4, n2o) \
                .join(Expense, Carbon.expense_id == Expense.expense_id) \
                .filter(Expense.user_id == user.id) \
                .filter(Expense.expense_created_date >= start) \
                .filter(Expense.expense_created_date <= end) \
                .all()
        else:
            raise ValueError("agg must be 'user' or 'company'")

        values = query[0]

        results = {
            'co2e': Carbon.round_to_n(values[0], 2),
            'co2': Carbon.round_to_n(values[1], 2),
            'ch4': Carbon.round_to_n(values[2], 2),
            'n2o': Carbon.round_to_n(values[3], 2)
        }

        return results

    @staticmethod
    def group_and_sum_distance(user, agg='employee', prev_month=False,
                               **kwargs):
        """Group and sum distance travelled in km by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.
            prev_month (bool): if true, apply month offset of one month.

        Returns:
            results (dict): sum of distances  grouped by agg.

        """
        # Prevent circular import.
        from canopact.blueprints.carbon.models.route import Route
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.user.models import User

        if prev_month:
            start = Carbon.get_prev_months_date(prev_months=1, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=1, first=False,
                                              **kwargs)
        else:
            start = Carbon.get_prev_months_date(prev_months=0, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=0, first=False,
                                              **kwargs)

        distance = func.sum(Route.distance)

        if agg == 'company':

            users = db.session.query(User.id) \
                .filter(User.company_id == user.company_id).all()

            query = db.session.query(distance) \
                .join(Expense, Route.expense_id == Expense.expense_id) \
                .filter(Expense.user_id.in_(users)) \
                .filter(Expense.expense_created_date >= start) \
                .filter(Expense.expense_created_date <= end) \
                .all()
        elif agg == 'employee':
            query = db.session.query(distance) \
                .join(Expense, Route.expense_id == Expense.expense_id) \
                .filter(Expense.user_id == user.id).all()
        else:
            raise ValueError("agg must be 'user' or 'company'")

        values = query[0]

        results = {
            'distance': Carbon.round_to_n(values[0], 2),
        }

        return results

    @staticmethod
    def group_and_count_journeys(user, agg='employee', prev_month=False,
                                 **kwargs):
        """Group and count number of journeys by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.
            prev_month (bool): if true, apply month offset of one month.

        Returns:
            results (dict): count of journeys grouped by agg.

        """
        # Prevent circular import.
        from canopact.blueprints.carbon.models.route import Route
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.user.models import User

        if prev_month:
            start = Carbon.get_prev_months_date(prev_months=1, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=1, first=False,
                                              **kwargs)
        else:
            start = Carbon.get_prev_months_date(prev_months=0, first=True,
                                                **kwargs)
            end = Carbon.get_prev_months_date(prev_months=0, first=False,
                                              **kwargs)

        journeys = func.count(Route.id)

        if agg == 'company':

            users = db.session.query(User.id) \
                .filter(User.company_id == user.company_id).all()

            query = db.session.query(journeys) \
                .join(Expense, Route.expense_id == Expense.expense_id) \
                .filter(Expense.user_id.in_(users)) \
                .filter(Route.invalid == 0) \
                .filter(Expense.expense_created_date >= start) \
                .filter(Expense.expense_created_date <= end) \
                .all()
        elif agg == 'employee':
            query = db.session.query(journeys) \
                .join(Expense, Route.expense_id == Expense.expense_id) \
                .filter(Expense.user_id == user.id) \
                .filter(Route.invalid == 0) \
                .filter(Expense.expense_created_date >= start) \
                .filter(Expense.expense_created_date <= end) \
                .all()
        else:
            raise ValueError("agg must be 'user' or 'company'")

        values = query[0]

        results = {
            'journeys': Carbon.round_to_n(values[0], 2),
        }

        return results

    @staticmethod
    def group_and_sum_emissions_monthly(user, agg='employee', prev_months=6,
                                        **kwargs):
        """Group and sum emissions for each month by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.

        Returns:
            results (dict): dictionary of different emissions grouped by agg.

        """
        # Prevent circular imports.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.carbon import Carbon

        start = Carbon.get_prev_months_date(prev_months, **kwargs)
        end = Carbon.get_prev_months_date(prev_months=0, first=False, **kwargs)

        # Group the journeys by the months
        sums = func.sum(Carbon.co2e)
        months = func.extract("month", Expense.expense_created_date)

        # Query database.
        carbon = db.session.query(months, sums) \
            .join(Carbon, Expense.expense_id == Carbon.expense_id) \
            .filter(Expense.expense_created_date >= start) \
            .filter(Expense.expense_created_date <= end) \
            .filter(Expense.user_id == user.id) \
            .group_by(months).all()

        # Get monthly labels.
        labels = Carbon.get_month_labels(prev_months, **kwargs)

        # Map data to labels.
        carbon = Carbon.month_num_to_string(carbon, order=labels)

        # Extract values and map to a dictionary.
        values = [Carbon.round_to_n(v[1], 2) for v in carbon]

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Emissions',
                'data': values
            }]
        }

        return data

    @staticmethod
    def group_and_count_journeys_monthly(user, agg='employee', prev_months=6,
                                         **kwargs):
        """Group and count journeys for each month by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by.
            prev_months (int): how many previous months to aggregate by.

        Returns:
            data (dict): dictionary of different journeys grouped by agg.

        """
        # Prevent circular imports.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.route import Route

        start = Carbon.get_prev_months_date(prev_months, **kwargs)
        end = Carbon.get_prev_months_date(prev_months=0, first=False, **kwargs)

        # Group the journeys by the months
        counts = func.count(Route.id)
        months = func.extract("month", Expense.expense_created_date)

        # Query database.
        routes = db.session.query(months, counts) \
            .join(Route, Expense.expense_id == Route.expense_id) \
            .filter(Expense.expense_created_date >= start) \
            .filter(Expense.expense_created_date <= end) \
            .filter(Route.invalid == 0) \
            .filter(Expense.user_id == user.id) \
            .group_by(months).all()

        # Get monthly labels.
        labels = Carbon.get_month_labels(prev_months, **kwargs)

        # Map labels to values.
        routes = Carbon.month_num_to_string(routes, order=labels)

        # Extract values and map to a dictionary.
        values = [v[1] for v in routes]

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Journeys',
                'data': values
            }]
        }

        return data

    @staticmethod
    def group_and_sum_distance_monthly(user, agg='employee', prev_months=6,
                                       **kwargs):
        """Group and sum distance for each month by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by.
            prev_months (int): how many previous months to aggregate by.

        Returns:
            data (dict): dictionary of different distances grouped by agg.

        """
        # Prevent circular imports.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.route import Route

        start = Carbon.get_prev_months_date(prev_months, **kwargs)

        # Group the journeys by the months
        counts = func.sum(Route.distance)
        months = func.extract("month", Expense.expense_created_date)

        # Query database.
        routes = db.session.query(months, counts) \
            .join(Route, Expense.expense_id == Route.expense_id) \
            .filter(Expense.expense_created_date >= start) \
            .filter(Route.invalid == 0) \
            .filter(Expense.user_id == user.id) \
            .group_by(months).all()

        # Get monthly labels.
        labels = Carbon.get_month_labels(prev_months)

        # Map labels to values.
        routes = Carbon.month_num_to_string(routes, order=labels)

        # Extract values and map to a dictionary.
        values = [v[1] if v[1] is not None else 0 for v in routes]

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Distance',
                'data': values
            }]
        }

        return data

    @staticmethod
    def group_and_count_transport(user, agg='employee', as_list=False,
                                  **kwargs):
        """Counts the number of journeys for each transport type.

        user: (models.User): user to aggregate on.
        agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by.
        as_list (bool): True to return data as lift of tuples, else return as
            dict.

        Returns:
            data (dict): dictionary of different transport grouped by agg.

        """
        # Prevent circular imports.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.route import Route

        counts = func.count(Route.id)

        start = Carbon.get_prev_months_date(prev_months=0, first=True,
                                            **kwargs)
        end = Carbon.get_prev_months_date(prev_months=0, first=False, **kwargs)

        # Query database.
        transports = db.session.query(Route.expense_category, counts) \
            .join(Expense, Route.expense_id == Expense.expense_id) \
            .filter(Route.invalid == 0) \
            .filter(Expense.user_id == user.id) \
            .filter(Expense.expense_created_date >= start) \
            .filter(Expense.expense_created_date <= end) \
            .group_by(Route.expense_category) \
            .order_by(counts.desc()) \
            .all()

        # Add percentages to the list.
        transports = Carbon.calculate_group_percentages(transports)

        if as_list:
            return transports

        # Seperate tuples into seperate lists.
        labels = [v[0] for v in transports]
        counts = [v[1] for v in transports]
        percentages = [v[2] for v in transports]

        data = {
            'labels': labels,
            'data': {
                'counts': counts,
                'percentages': percentages
            }
        }

        return data

    @staticmethod
    def group_and_count_routes(user, agg='employee', as_list=False, **kwargs):
        """Counts the number of journeys for each origin/destination pairing.

        user: (models.User): user to aggregate on.
        agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by.
        as_list (bool): True to return data as lift of tuples, else return as
            dict.

        Returns:
            data (dict): dictionary of different routes grouped by agg.

        """
        # Prevent circular import.
        from canopact.blueprints.carbon.models.expense import Expense
        from canopact.blueprints.carbon.models.route import Route

        start = Carbon.get_prev_months_date(prev_months=0, first=True,
                                            **kwargs)
        end = Carbon.get_prev_months_date(prev_months=0, first=False, **kwargs)

        counts = func.count(Route.id)

        # Query database.
        routes = db.session.query(Route.origin, Route.destination, counts) \
            .join(Expense, Route.expense_id == Expense.expense_id) \
            .filter(Route.invalid == 0) \
            .filter(Route.route_category != 'unit') \
            .filter(Expense.user_id == user.id) \
            .filter(Expense.expense_created_date >= start) \
            .filter(Expense.expense_created_date <= end) \
            .group_by(Route.origin, Route.destination) \
            .order_by(counts.desc()) \
            .all()

        # Add percentages to the list.
        routes = Carbon.calculate_group_percentages(routes, value_index=2)

        if as_list:
            return routes

        # Seperate tuples into seperate lists.
        origins = [v[0] for v in routes]
        destinations = [v[1] for v in routes]
        counts = [v[2] for v in routes]
        percentages = [v[3] for v in routes]

        data = {
            'labels': None,
            'data': {
                'origins': origins,
                'destinations': destinations,
                'counts': counts,
                'percentages': percentages
            }
        }

        return data

    @staticmethod
    def emissions_per_distance(user, agg='employee', prev_month=False,
                               **kwargs):
        """
        Gets the emissons in kg divided by the number of km travelled.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.
            prev_month (bool): if true, apply month offset of one month.

        Returns:
            data (dict): dictionary of emissions grouped by agg.

        """
        emissions = Carbon.group_and_sum_emissions(user, agg,
                                                   prev_month=prev_month,
                                                   **kwargs)
        distance = Carbon.group_and_sum_distance(user, agg,
                                                 prev_month=prev_month,
                                                 **kwargs)
        distance = distance['distance']

        results = {k: Carbon.round_to_n(v / distance, 2) if distance != 0
                   else 0 for k, v in emissions.items()}

        return results

    @staticmethod
    def emissions_per_journeys(user, agg='employee', prev_month=False,
                               **kwargs):
        """
        Gets the emissons in kg divided by the number of journeys.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.

        Returns:
            data (dict): dictionary of different routes grouped by agg.

        """
        emissions = Carbon.group_and_sum_emissions(user, agg,
                                                   prev_month=prev_month,
                                                   **kwargs)
        journeys = Carbon.group_and_count_journeys(user, agg,
                                                   prev_month=prev_month,
                                                   **kwargs)
        journeys = journeys['journeys']

        results = {k: Carbon.round_to_n(v / journeys, 2) if journeys != 0
                   else 0 for k, v in emissions.items()}

        return results

    @staticmethod
    def emissions_metrics(user, agg="employee", prev_month=False, **kwargs):
        """Wrapper function to produce emissions metrics:
            * current month's emissions.
            * previous month's emissions.
            * percentage change between current and previous month.

        Calls:
            * Carbon.group_and_sum_emissions()
            * Carbon.group_and_sum_emissions()

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.
            prev_month (bool): if true, apply month offset of one month.

        Returns
            tuple: emissions for current month, previous month and percentage
                difference.
        """
        current = Carbon.group_and_sum_emissions(user, agg=agg, **kwargs)
        previous = Carbon.group_and_sum_emissions(user, agg=agg,
                                                  prev_month=True, **kwargs)
        change = Carbon.emissions_percentage_diff(current, previous)

        return current, previous, change

    @staticmethod
    def emissions_metrics_monthly(user, agg='employee', prev_months=6,
                                  emissions=None, journeys=None,
                                  distances=None, **kwargs):
        """Calculate kpi metrics each month aggregated by the agg level.

        metrics include:
            * monthly emissions kg
            * monthly emissions per distance kg / km
            * monthly emissions per journey kg / journey

        Calls:
            * Carbon.group_and_sum_emissions_monthly()
            * Carbon.group_and_count_journeys_monthly()
            * Carbon.group_and_sum_distance_monthly()

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by.
            prev_months (int): how many previous months to aggregate by.
            emissions (list): monthly emissions values.

        Returns:
            data (dict): dictionary of different distances grouped by agg.

        """
        if not emissions:
            emissions = \
                Carbon.group_and_sum_emissions_monthly(user, agg=agg,
                                                       prev_months=prev_months,
                                                       **kwargs)
        em_values = emissions['datasets'][0]['data']

        if not journeys:
            journeys = Carbon. \
                group_and_count_journeys_monthly(user, agg=agg,
                                                 prev_months=prev_months,
                                                 **kwargs)

        jny_values = journeys['datasets'][0]['data']

        if not distances:
            distances = \
                Carbon.group_and_sum_distance_monthly(user, agg=agg,
                                                      prev_months=prev_months,
                                                      **kwargs)
        dst_values = distances['datasets'][0]['data']

        em_per_jrny = [Carbon.round_to_n(int(e)/int(j), 2) if j != 0 else 0
                       for e, j in zip(em_values, jny_values)]
        em_per_dst = [Carbon.round_to_n(int(e)/int(d), 2) if d != 0 else 0
                      for e, d in zip(em_values, dst_values)]

        data = {
            'labels': emissions['labels'],
            'datasets': {
                'emissions': {"data": {"datasets": [{"data": em_values}]}},
                'per_journey': {"data": {"datasets": [{"data": em_per_jrny}]}},
                'per_km': {"data": {"datasets": [{"data": em_per_dst}]}}
            }
        }

        return data

    @staticmethod
    def per_journeys_metrics(user, agg="employee", **kwargs):
        """Wrapper function to produce emissions metrics:
            * current month's emissions per journey.
            * previous month's emissions per journey.
            * percentage change between current and previous month.

        Calls:
            * Carbon.emissions_per_journeys()
            * Carbon.emissions_per_journeys()
            * Carbon.emissions_percentage_diff()

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.

        Returns
            tuple: emissions for current month, previous month and percentage
                difference.

        """
        current = Carbon.emissions_per_journeys(user, agg=agg, **kwargs)
        previous = Carbon.emissions_per_journeys(user, agg=agg,
                                                 prev_month=True, **kwargs)
        change = Carbon.emissions_percentage_diff(current, previous)

        return current, previous, change

    @staticmethod
    def per_distance_metrics(user, agg="employee", **kwargs):
        """Wrapper function to produce emissions metrics:
            * current month's emissions per distance.
            * previous month's emissions per distance.
            * percentage change between current and previous month.

        Calls:
            * Carbon.emissions_per_distance()
            * Carbon.emissions_per_distance()
            * Carbon.emissions_percentage_diff()

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.

        Returns
            tuple: emissions for current month, previous month and percentage
                difference.

        """
        current = Carbon.emissions_per_distance(user, agg=agg, **kwargs)
        previous = Carbon.emissions_per_distance(user, agg=agg,
                                                 prev_month=True, **kwargs)
        change = Carbon.emissions_percentage_diff(current, previous)

        return current, previous, change

    @staticmethod
    def emissions_percentage_diff(base, compare):
        """Calculate the percentage difference between twos sets of emmissions

        base (dict): emissions to to calculate percentage change to.
        compare (dict): emissions to to calculate percentage from.

        Returns:
            results (dict): emissions with percentage differences.

        """

        def handle_zeros(k):
            """Selector function to handle cases where base values are zero.

            """
            if base[k] == 0:
                if compare.get(k) == 0:
                    return 0
                else:
                    return - 100
            else:
                return Carbon.round_to_n(100 * ((base[k] - compare.get(k))
                                         / base[k]), 2)

        results = {k: handle_zeros(k) for k in base}

        return results

    @staticmethod
    def get_month_labels(n, reverse=True, date=None):
        """Get list of month abbreviation for previous `n` months.

        Args:
            n (int): number of months back from current month to include
                in labels.
            reverse (bool): True to reverse list to start with earliest month.
            date (datetime.date) latest date to compare from.

        Returns:
            labels (list): list of month abbreviations. E.g.
                ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        """
        double_months_list = calendar.month_abbr[1:] * 2

        if date:
            today_month = date.month + 12
        else:
            today_month = datetime.datetime.now().month + 12

        first_month = today_month - n
        labels = double_months_list[first_month:today_month][::-1]

        if reverse:
            labels.reverse()

        return labels

    @staticmethod
    def month_num_to_string(data, abbr=True, order=None):
        """Converts month number into string.

        Args:
            data (list): list of tuples containing month integer and values.
                E.g. [(3, 12.0), (1, 7.0), (12, 8.0), (1, 6.0)]
            abbr (bool): True to convert to abbreviation (e.g. Jan), else will
                convert to full name (January).
            order (list): reorder the list to follow a specific order of
                months.

        Returns:
            list: updated tuples with month in string format

        """
        # Iterate through each tuple in the list.
        for i, t in enumerate(data):
            li = list(t)  # Convert to list as tuples are immutable.
            v = int(li[0])

            # Convert month number into name or abbreviation.
            if abbr:
                li[0] = calendar.month_abbr[v]
            else:
                li[0] = calendar.month_name[v]

            t = tuple(li)  # Convert back to list.

            # Overwrite original tuple in the list.
            data[i] = t

        # Reorder tuples in list by matching indexes of another list.
        if order:
            keys = [m[0] for m in data]
            for t in order:
                if t not in keys:
                    data.append((t, 0))

            # Match indexes of `order` list.
            d = {v: i for i, v in enumerate(order)}
            data = [m for m in data if m[0] in order]
            data = sorted(data, key=lambda x: d[x[0]])

        return data

    @staticmethod
    def calculate_group_percentages(data, value_index=1, decimals=1):
        """Calculate the percentages of the sums/counts for each group.

        Args:
            data (list): list of tuples contatining the group and value. E.g.
                [('Train', 2), ('Fuel', 5)]
            value_index (int): index in each tuple that contains the value.
            decimals (int): number of decimal places to round percentage to.

        Returns:
            data (list): list of tuples with another element containing the
                percentage. E.g. [('Train', 2, 29), ('Fuel', 5, 71)]

        """
        # Get the total of all the values from each tuple in the list.
        values = [v[value_index] for v in data]
        total = sum(values)

        # Add a new element tp
        for i, t in enumerate(data):
            value = t[value_index]
            percent = Carbon.round_to_n(((value / total) * 100), decimals)
            t = (*t, percent)
            data[i] = t

        return data

    @staticmethod
    def get_prev_months_date(prev_months, date=None, first=True, **kwargs):
        """Get the date for a given number of months ago.

        prev_months (int): number of previos months to take differenc from.
        date (datetime.date): date to start from.
        first (bool): True to return first of the month, else return day
            of prev_months back from current day.

        Returns:
            start (datetime.date): date `prev_months` ago.

        """

        # Filter records for to only include date range of prev_months.
        if not date:
            start = datetime.date.today() + relativedelta(months=-prev_months)
        else:
            start = date + relativedelta(months=-prev_months)

        if first:
            start = start.replace(day=1)

        return start

    @staticmethod
    def round_to_n(x, n):
        """Rounds number to n significant figures

        Args:
            x (float): number to be rounded.
            n (int): number of significant figures to round to.

        Returns:
            float: x rounded to n significant figures

        """
        if x is None:
            return 0
        elif x == 0:
            return x
        elif x < 1 and x > 0:
            return round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))
        else:
            return round(x, n)
