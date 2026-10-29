import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("BREVO_SMTP_HOST")
SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN")
SMTP_KEY = os.getenv("BREVO_SMTP_KEY")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

# Send the test email to your own verified inbox.
RECIPIENT_EMAIL = SENDER_EMAIL

required = {
    "BREVO_SMTP_HOST": SMTP_HOST,
    "BREVO_SMTP_LOGIN": SMTP_LOGIN,
    "BREVO_SMTP_KEY": SMTP_KEY,
    "BREVO_SENDER_EMAIL": SENDER_EMAIL,
}

missing = [name for name, value in required.items() if not value]

if missing:
    raise RuntimeError(
        "Missing environment variables: " + ", ".join(missing)
    )

if any(
    value.startswith("your_")
    for value in [SMTP_LOGIN, SMTP_KEY, SENDER_EMAIL]
):
    raise RuntimeError("Replace placeholder values in your .env file.")

msg = EmailMessage()
msg["Subject"] = "Diagnora - Email Configuration Test"
msg["From"] = SENDER_EMAIL
msg["To"] = RECIPIENT_EMAIL
msg.set_content(
    "Hello!\n\n"
    "This is a test email from Diagnora.\n"
    "Brevo SMTP configuration is working if you received this message.\n\n"
    "Diagnora Team"
)

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_KEY)
        server.send_message(msg)

    print("SUCCESS: Test email sent. Check your inbox and spam folder.")

except Exception as exc:
    print(f"EMAIL TEST FAILED: {type(exc).__name__}: {exc}")