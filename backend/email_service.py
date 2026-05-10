"""Надсилання листа підтвердження email (SMTP). Якщо smtp_host порожній — лист не надсилається."""

import logging
import smtplib
from email.message import EmailMessage

from config import settings

log = logging.getLogger(__name__)


def send_verification_email(to_email: str, verify_link: str) -> bool:
    if not (settings.smtp_host or "").strip():
        log.info("SMTP не налаштовано — лист підтвердження не надіслано")
        return False
    msg = EmailMessage()
    msg["Subject"] = "Підтвердження реєстрації — STEM Diagnostic"
    msg["From"] = settings.smtp_from or settings.smtp_user or "noreply@localhost"
    msg["To"] = to_email
    msg.set_content(
        f"Вітаємо!\n\n"
        f"Щоб підтвердити email, перейдіть за посиланням:\n{verify_link}\n\n"
        f"Якщо ви не реєструвалися — проігноруйте цей лист.\n"
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except OSError as e:
        log.warning("Не вдалося надіслати лист підтвердження: %s", e)
        return False
