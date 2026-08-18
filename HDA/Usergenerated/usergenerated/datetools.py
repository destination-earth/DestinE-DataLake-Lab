from datetime import datetime


def is_same_day(datetime1: datetime, datetime2: datetime) -> bool:
    """
    Check if two datetime objects represent the same calendar day.
    
    Parameters:
        datetime1: The first datetime object.
        datetime2: The second datetime object.
    
    Returns:
        True if both datetime objects are from the same day, False otherwise.
    """
    return datetime1.date() == datetime2.date()
