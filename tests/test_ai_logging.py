from app.rag.service import sanitize_for_log 
 
 
def test_email_is_redacted(): 
    result = sanitize_for_log("Contact john.doe@example.com") 
    assert "john.doe@example.com" not in result 
    assert "[REDACTED_EMAIL]" in result 
 
 
def test_phone_is_redacted(): 
    result = sanitize_for_log("Customer phone is 9876543210") 
    assert "9876543210" not in result 
    assert "[REDACTED_PHONE]" in result 
 
 
def test_long_numeric_identifier_is_redacted(): 
    result = sanitize_for_log("Customer ID 123456789012") 
    assert "123456789012" not in result 
    assert "[REDACTED_ID]" in result 