import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from src.auth.security import create_otp, hash_otp, verify_otp
from src.database import db
from src.utils.config import OTP_EXPIRY_MINUTES, MAX_OTP_ATTEMPTS

try:
    from twilio.rest import Client
except Exception:
    Client = None

def send_email(to_email, otp):
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", username)

    if not all([host, username, password, sender]):
        return False, "SMTP email OTP is not configured."

    msg = EmailMessage()
    msg["Subject"] = "NEXUS RAG password reset OTP"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        f"Your NEXUS RAG OTP is {otp}. "
        f"It expires in {OTP_EXPIRY_MINUTES} minutes."
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        return True, "OTP sent to your email."
    except Exception as exc:
        return False, f"Email delivery failed: {exc}"

def send_sms(to_phone, otp):
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    sender = os.getenv("TWILIO_FROM_PHONE", "")

    if not Client or not all([sid, token, sender]):
        return False, "SMS OTP is not configured."

    try:
        client = Client(sid, token)
        client.messages.create(
            body=f"Your NEXUS RAG OTP is {otp}. "
                 f"It expires in {OTP_EXPIRY_MINUTES} minutes.",
            from_=sender,
            to=to_phone,
        )
        return True, "OTP sent to your phone."
    except Exception as exc:
        return False, f"SMS delivery failed: {exc}"

def issue_otp(user):
    otp = create_otp()
    otp_hash, otp_salt = hash_otp(otp)
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )
    db.save_otp(user["id"], otp_hash, otp_salt, expires.isoformat())

    if user["identifier_type"] == "email":
        return send_email(user["identifier"], otp)
    return send_sms(user["identifier"], otp)

def verify_reset_otp(user, otp):
    row = db.get_active_otp(user["id"])
    if not row:
        return False, "No active OTP. Request a new one."

    if row["attempts"] >= MAX_OTP_ATTEMPTS:
        return False, "Too many attempts. Request a new OTP."

    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires:
        return False, "OTP expired."

    if not verify_otp(otp.strip(), row["otp_hash"], row["otp_salt"]):
        db.increment_otp_attempt(row["id"])
        return False, "Incorrect OTP."

    db.consume_otp(row["id"])
    return True, "OTP verified."
