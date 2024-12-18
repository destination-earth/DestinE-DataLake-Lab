from datetime import datetime


# def convert_to_datetime_midnight(date_string):
#     # Parse the string to a datetime object
#     dt = datetime.strptime(date_string, "%Y%m%dT%H%M%S")

#     # Create a new datetime object with the time set to 00:00:00
#     dt_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)

#     return dt_midnight


def is_same_day(datetime1, datetime2):
    """
    Check if two datetime objects represent the same calendar day.
    Parameters: datetime1 (datetime): The first datetime object.
    datetime2 (datetime): The second datetime object.
    Returns: bool: True if both datetime objects are from the same day, False otherwise.
    """
    return datetime1.date() == datetime2.date()
