import datetime
import pytz


def tzware_datetime():
    """
    Return a timezone aware datetime.

    :return: Datetime
    """
    return datetime.datetime.now(pytz.utc)


def timedelta_months(months, compare_date=None):
    """
    Return a new datetime with a month offset applied.

    :param months: Amount of months to offset
    :type months: int
    :param compare_date: Date to compare at
    :type compare_date: date
    :return: datetime
    """
    if compare_date is None:
        compare_date = datetime.date.today()

    delta = months * 365 / 12
    compare_date_with_delta = compare_date + datetime.timedelta(delta)

    return compare_date_with_delta


def datediff_days(start, end):
    """
    Get the difference between two dates in days.

    Start (datetime.datetime): datetime to compare difference from.
    End (datetime.datetime): datetime to compare difference to.

    Returns:
        int: number of days between start and end.

    """
    if isinstance(start, datetime.datetime):
        d1 = start
    elif isinstance(start, str):
        d1 = datetime.datetime.strptime(start, "%Y-%m-%d")
    else:
        raise TypeError(f"start must be datetime.datetime or str")

    if isinstance(end, datetime.datetime):
        d2 = end
    elif isinstance(end, str):
        d2 = datetime.datetime.strptime(end, "%Y-%m-%d")
    else:
        raise TypeError(f"end must be datetime.datetime or str")

    return abs((d2 - d1).days)
