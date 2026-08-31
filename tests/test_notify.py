import os
from src.notify import send_report_email

def test_send_report_email_not_configured(monkeypatch):
    # Clear any environment variables that might be set to ensure we trigger the unconfigured state
    monkeypatch.delenv("SMTP_SERVER", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    
    recipient = "test@example.com"
    report_text = "This is a test report."
    
    result = send_report_email(recipient, report_text)
    
    assert result["status"] == "not_configured"
    assert "Email sending not configured" in result["message"]
    assert report_text in result["message"]
