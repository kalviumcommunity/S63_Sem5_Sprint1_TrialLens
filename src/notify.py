import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv


def send_report_email(recipient: str, report_text: str) -> dict:
    """
    Sends a summary report via email using SMTP.
    Requires .env configuration:
    - SMTP_SERVER
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD

    Returns a dict with 'status' and 'message'.
    """
    load_dotenv()

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        return {
            "status": "not_configured",
            "message": "Email sending not configured — showing what would be sent:\n\n"
            + report_text,
        }

    try:
        msg = EmailMessage()
        msg.set_content(report_text)
        msg["Subject"] = "TrialLens Summary Report"
        msg["From"] = smtp_user
        msg["To"] = recipient

        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return {
            "status": "success",
            "message": f"Report successfully sent to {recipient}",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {e}"}

if __name__ == "__main__":
    load_dotenv()
    print("Environment variables loaded:")
    for var in ["SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]:
        val = os.getenv(var)
        status = "SET (value hidden)" if val else "NOT SET"
        print(f"  {var}: {status}")
