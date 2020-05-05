from lib.util_sqlalchemy import ResourceMixin, AwareDateTime
from lib.util_datetime import tzware_datetime
from canopact.extensions import db


class Report(ResourceMixin, db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',
                                                  onupdate='CASCADE',
                                                  ondelete='CASCADE'),
                        index=True, nullable=False)

    # Report Details
    report_count = db.Column(db.Integer())

    # Last updated date
    update_datetime = db.Column(AwareDateTime())

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Report, self).__init__(**kwargs)

    def save_and_update_report(self):
        """
        Commit the report and update the the table.

        :return: SQLAlchemy save result
        """
        self.update_datetime = tzware_datetime()

        return self.save()
