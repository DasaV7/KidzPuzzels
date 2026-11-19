import smtplib
from email.message import EmailMessage

import streamlit as st


def send_email_notification(recipient_email: str, youtube_url: str, video_title: str) -> bool:
    """Notify the requesting user and configured admin after an upload."""
    sender = st.secrets.get("EMAIL_ADDRESS")
    password = st.secrets.get("EMAIL_PASSWORD")
    if not sender or not password:
        raise RuntimeError("Set EMAIL_ADDRESS and EMAIL_PASSWORD in Streamlit secrets to enable email notifications.")

    recipients = []
    for address in (recipient_email, st.secrets.get("ADMIN_EMAIL", sender)):
        address = str(address or "").strip()
        if address and address.casefold() not in [item.casefold() for item in recipients]:
            recipients.append(address)
    if not recipients:
        raise ValueError("At least one notification recipient email is required.")

    message = EmailMessage()
    message["Subject"] = f"Your kids puzzle video is ready: {video_title}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(
        f"Hello,\n\nYour kids puzzle video has been created and uploaded.\n\n"
        f"Title: {video_title}\nWatch: {youtube_url}\n\n"
        "Thank you,\nKids Puzzle Video Generator\n"
    )
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)
    return True
