"""Models for Carbon

Calculates carbon emissions from Expensify report and expense data.

"""

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
    def group_and_sum_emissions(user, agg='employee'):
        """Group and sum user emissions by the agg level.

        Args:
            user: (models.User): user to aggregate on.
            agg (str): 'employee' to aggregate by employee, 'company' to
                aggregate by company.

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

        if agg == 'company':

            users = db.session.query(User.id) \
                .filter(User.company_id == user.company_id).all()

            query = db.session.query(co2e, co2, ch4, n2o) \
                .join(Expense, Carbon.expense_id == Expense.expense_id) \
                .filter(Expense.user_id.in_(users)).all()
        elif agg == 'employee':
            query = db.session.query(co2e, co2, ch4, n2o) \
                .join(Expense, Carbon.expense_id == Expense.expense_id) \
                .filter(Expense.user_id == user.id).all()
        else:
            raise ValueError("agg must be 'user' or 'company'")

        values = query[0]
        print(values)

        results = {
            'co2e': round(values[0], 3),
            'co2': round(values[1], 3),
            'ch4': round(values[2], 3),
            'n2o': round(values[3], 3)
        }

        return results
