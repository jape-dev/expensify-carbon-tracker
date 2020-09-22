"""Models for Carbon

Calculates carbon emissions from Expensify report and expense data.

TODO:
    * rename co2 column to co2e.

"""

from canopact.extensions import db
from flask import current_app
from lib.util_sqlalchemy import ResourceMixin


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
    co2 = db.Column(db.Float())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Carbon, self).__init__(**kwargs)

    @staticmethod
    def convert_to_carbon_air(distance, short=None, long=None, domestic=None):
        """Convert air distance to CO2 using the DEFRA emmisions factor.

        Notes:
            distance must be in the units km.

        Args:
            distance (float): distance in in km.
            short (float): emissions factor for short haul flights
                500km - 2500km.
            long (float): emissions factor for long haul flights > 2500km.
            domestic (float): emissions factors for domestic flights <= 500km.

        Returns:
            co2 (float): carbon emissions in kg.

        """
        if short is None:
            short = current_app.config['EF_AIR_SHORT']
        if long is None:
            long = current_app.config['EF_AIR_LONG']
        if domestic is None:
            domestic = current_app.config['EF_AIR_DOMESTIC']

        if distance > 0 and distance <= 500:
            co2 = distance * domestic
        elif distance > 500 and distance <= 2500:
            co2 = distance * short
        else:
            co2 = distance * long

        return co2

    @staticmethod
    def convert_to_carbon_bus(distance, local=None, coach=None):
        """Convert bus distance to CO2 using the DEFRA emmisions factor.

        Notes:
            distance must be in the units km.

        Args:
            distance (float): distance in in km.
            local (float): emissions factor for short distance <= 25km.
            coach (float): emissions factor for long distance > 25km.

        Returns:
            co2 (float): carbon emissions in kg.

        """
        if local is None:
            local = current_app.config['EF_BUS_LOCAL']
        if coach is None:
            coach = current_app.config['EF_BUS_COACH']

        if distance > 0 and distance <= 25:
            co2 = distance * local
        else:
            co2 = distance * coach

        return co2

    @staticmethod
    def convert_to_carbon_car(distance, factor=None):
        """Convert car distance to CO2 using the DEFRA emmisions factor.

        Notes:
            distance must be in the units km.

        Args:
            distance (float): distance in in km.
            factor (float): emissions factor.

        Returns:
            co2 (float): carbon emissions in kg.

        """
        if factor is None:
            factor = current_app.config['EF_CAR']

        co2 = distance * factor

        return co2

    @staticmethod
    def convert_to_carbon_taxi(distance, factor=None):
        """Convert taxi distance to CO2 using the DEFRA emmisions factor.

        Notes:
            distance must be in the units km.

        Args:
            distance (float): distance in in km.
            factor (float): emissions factor.

        Returns:
            co2 (float): carbon emissions in kg.

        """
        if factor is None:
            factor = current_app.config['EF_TAXI']

        co2 = distance * factor

        return co2

    @staticmethod
    def convert_to_carbon_train(distance, factor=None):
        """Convert train distance to CO2 using the DEFRA emmisions factor.

        Notes:
            distance must be in the units km.

        Args:
            distance (float): distance in in km.
            factor (float): emissions factor.

        Returns:
            co2 (float): carbon emissions in kg.

        """
        if factor is None:
            factor = current_app.config['EF_TRAIN']

        co2 = distance * factor

        return co2

    def convert_to_carbon(self, distance=None, category=None, **kwargs):
        """Wrapper function to convert distance to carbon.

        Args:
            distance (float): distance in in km.
            category (str): expense category.

        Sets:
            co2 (float): carbon in kg.

        """
        if distance is None:
            distance = self.distance
        if category is None:
            category = self.expense_category

        # No distance available if the route is invalid.
        if distance is None:
            return None

        if category == 'Car, Van and Travel Expenses: Air':
            co2 = Carbon.convert_to_carbon_air(distance, **kwargs)
        elif category == 'Car, Van and Travel Expenses: Bus':
            co2 = Carbon.convert_to_carbon_bus(distance, **kwargs)
        elif category in ['Car, Van and Travel Expenses: Car Hire',
                          'Car, Van and Travel Expenses: Fuel']:
            co2 = Carbon.convert_to_carbon_car(distance, **kwargs)
        elif category == 'Car, Van and Travel Expenses: Taxi':
            co2 = Carbon.convert_to_carbon_taxi(distance, **kwargs)
        elif category == 'Car, Van and Travel Expenses: Train':
            co2 = Carbon.convert_to_carbon_train(distance, **kwargs)
        else:
            raise ValueError(f"{category} is an invalid category. Must be "
                             f"one of Car, Van and Travel Expenses: <Taxi:"
                             f"'Air', 'Bus', 'Car Hire', 'Fuel', 'Taxi'"
                             f", 'Train'>")

        self.co2 = co2
