from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta

# Password hashing context with bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def format_time(dt: datetime) -> str:
    if not dt:
        return None
    now = datetime.utcnow()
    if dt.date() == now.date():
        return dt.strftime("%I:%M %p")
    elif (now.date() - dt.date()).days == 1:
        return "Yesterday"
    elif (now - dt).days < 7:
        return dt.strftime("%A")  # Monday, etc.
    else:
        return dt.strftime("%m/%d/%y")


# Helper: human-readable time difference
def human_readable_time_diff(past_time):
    now = datetime.utcnow()
    diff = now - past_time
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} days ago"
    else:
        return past_time.strftime("%Y-%m-%d")

