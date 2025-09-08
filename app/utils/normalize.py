import re
from typing import Optional
import phonenumbers


def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip().lower()
    # basic sanity check
    return email if "@" in email and "." in email.split("@")[-1] else None


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    s = phone.strip()
    # Try to parse as international; if not, assume no region and return digits
    try:
        num = phonenumbers.parse(s, None)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    s = re.sub(r"\D", "", s)
    return s or None


def normalize_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    cleaned = " ".join(part for part in name.replace("_", " ").split() if part)
    return cleaned.title() if cleaned else None

