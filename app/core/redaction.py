import re


def redact_sensitive_text(value: str) -> str:
    """Redact common email, phone, and Indian identity-number patterns before logging."""
    sanitized = value
    sanitized = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\b(?:\+91[-.\s]?)?[6-9]\d{9}\b", "[REDACTED_PHONE]", sanitized)
    sanitized = re.sub(r"\b\d{10,12}\b", "[REDACTED_ID]", sanitized)
    sanitized = re.sub(r"\b\d{4}[-\s]\d{4}[-\s]\d{4}\b", "[REDACTED_ID]", sanitized)
    sanitized = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[REDACTED_ID]", sanitized, flags=re.IGNORECASE)
    return sanitized
