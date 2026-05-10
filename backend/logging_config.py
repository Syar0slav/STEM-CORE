"""Структуровані події без PII у plain text (ідентифікатори — суфікси або хеші)."""

import hashlib
import json
import logging
import sys


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)


audit_log = logging.getLogger("stem.audit")


def email_fingerprint(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:16]


def account_suffix(user_id) -> str:
    s = str(user_id)
    return s[-10:] if len(s) >= 10 else s


def log_auth_event(
    kind: str,
    *,
    ok: bool,
    key: str,
    request_id: str | None = None,
) -> None:
    from config import settings

    rid = request_id or "-"
    if settings.audit_json:
        audit_log.info(
            json.dumps(
                {"event": kind, "ok": ok, "key": key, "request_id": rid},
                ensure_ascii=False,
            )
        )
    else:
        audit_log.info("event=%s ok=%s key=%s rid=%s", kind, ok, key, rid)
