from datetime import datetime

def format_date(date_obj):
    """Format a date object as MM/DD/YYYY"""
    if date_obj:
        return date_obj.strftime('%m/%d/%Y')
    return 'N/A'

def calculate_age(birth_date):
    """Calculate age from birth date"""
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age
