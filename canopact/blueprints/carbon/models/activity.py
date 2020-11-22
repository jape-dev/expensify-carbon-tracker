"""Models for Activity.

Author: James Patten
First Build: Nov 2020

"""

from canopact.extensions import db
from lib.util_sqlalchemy import ResourceMixin
from simple_salesforce import Salesforce


class Activity(ResourceMixin, db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.String(128), primary_key=True)

    # Relationships.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',
                                                  onupdate='CASCADE',
                                                  ondelete='CASCADE'),
                        index=True, nullable=False)

    activity_date = db.Column(db.Date())
    activity_type = db.Column(db.String(128))
    location = db.Column(db.String(128))
    description = db.Column(db.String(128))

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Activity, self).__init__(**kwargs)

    def get_events(self, user_id=None, qry=None):
        """Get fields from the Event object.

        Arguments:
            qry (str): SOQL query to be executed to retrive events.

        Returns:
            events: (pandas.DataFrame): user's events records returned
                from the Salesforce API via simple_salesforce.

        """
        from canopact.blueprints.user.models import User

        if not user_id:
            user_id = self.user_id

        if not qry:
            qry = ("SELECT Id, ActivityDate, Type, Location, "
                   "Description FROM Event")

        # Get the User instance url and session id
        u = User.query.get(user_id)
        url, session = u.update_salesforce_token()
        sf = Salesforce(instance_url=url, session_id=session)

        # Retrieve the event records from the API.
        events = sf.query(qry)

        return events

    @staticmethod
    def rename_event_keys(event):
        """Renames event keys from the Salesforce API.

        Args:
            event(collections.OrederedDict): event record returned via
                Sales for API via the simple_salesforce package.

        Returns:
            renamed (dict): dictionary with renamed keys.
        """

        renamed = {'id': event['Id'],
                   'activity_date': event['ActivityDate'],
                   'activity_type': event['Type'],
                   'location': event['Location'],
                   'description': event['Description']
                   }

        return renamed
