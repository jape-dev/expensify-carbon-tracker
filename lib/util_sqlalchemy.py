import datetime

import sqlalchemy
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from lib.util_datetime import tzware_datetime
from canopact.extensions import db


class AwareDateTime(TypeDecorator):
    """
    A DateTime type which can only store tz-aware DateTimes.

    Source:
      https://gist.github.com/inklesspen/90b554c864b99340747e
    """
    impl = DateTime(timezone=True)

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            raise ValueError('{!r} must be TZ-aware'.format(value))
        return value

    def __repr__(self):
        return 'AwareDateTime()'


class ResourceMixin(object):
    # Keep track when records are created and updated.
    created_on = db.Column(AwareDateTime(),
                           default=tzware_datetime)
    updated_on = db.Column(AwareDateTime(),
                           default=tzware_datetime,
                           onupdate=tzware_datetime)

    @classmethod
    def sort_by(cls, field, direction):
        """
        Validate the sort field and direction.

        :param field: Field name
        :type field: str
        :param direction: Direction
        :type direction: str
        :return: tuple
        """
        if field not in cls.__table__.columns:
            field = 'created_on'

        if direction not in ('asc', 'desc'):
            direction = 'asc'

        return field, direction

    @classmethod
    def get_bulk_action_ids(cls, scope, ids, omit_ids=[], query=''):
        """
        Determine which IDs are to be modified.

        :param scope: Affect all or only a subset of items
        :type scope: str
        :param ids: List of ids to be modified
        :type ids: list
        :param omit_ids: Remove 1 or more IDs from the list
        :type omit_ids: list
        :param query: Search query (if applicable)
        :type query: str
        :return: list
        """
        omit_ids = map(str, omit_ids)

        if scope == 'all_search_results':
            # Change the scope to go from selected ids to all search results.
            ids = cls.query.with_entities(cls.id).filter(cls.search(query))

            # SQLAlchemy returns back a list of tuples, we want a list of strs.
            ids = [str(item[0]) for item in ids]

        # Remove 1 or more items from the list, this could be useful in spots
        # where you may want to protect the current user from deleting themself
        # when bulk deleting user accounts.
        if omit_ids:
            ids = [id for id in ids if id not in omit_ids]

        return ids

    @classmethod
    def bulk_delete(cls, ids):
        """
        Delete 1 or more model instances.

        :param ids: List of ids to be deleted
        :type ids: list
        :return: Number of deleted instances
        """
        delete_count = cls.query.filter(cls.id.in_(ids)).delete(
            synchronize_session=False)
        db.session.commit()

        return delete_count

    def save(self):
        """
        Save a model instance.

        :return: Model instance
        """
        db.session.add(self)
        db.session.commit()

        return self

    def update_and_save(self, model, **kwargs):
        """Update record if id already exists.

        Save to table if it is a new record.

        Args:
            model (db.Model): SQLAlchemy Model instance.

        Example:
            self.update_and_save(Report, report_id=653)

        """
        # Get the record.
        row = db.session.query(model).filter_by(**kwargs)
        # Check if id is already in the table.
        exists = db.session.query(row.exists()).scalar()

        if exists:
            # Update the already existing record.
            attrs = self.__dict__.copy()
            try:
                row.update(attrs)
            except sqlalchemy.exc.InvalidRequestError:
                attrs.pop('_sa_instance_state', None)
                row.update(attrs)

            db.session.commit()
        else:
            # Add the new record to the table.
            self.save()

    def delete(self):
        """
        Delete a model instance.

        :return: db.session.commit()'s result
        """
        db.session.delete(self)
        return db.session.commit()

    def __str__(self):
        """
        Create a human readable version of a class instance.

        :return: self
        """
        obj_id = hex(id(self))
        columns = self.__table__.c.keys()

        values = ', '.join("%s=%r" % (n, getattr(self, n)) for n in columns)
        return '<%s %s(%s)>' % (obj_id, self.__class__.__name__, values)
