from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

import requests


def send_notification(message: str, title: str = "每日学术雷达") -> dict[str, Any]:
    channel = os.getenv("NOTIFY_CHANNEL", "ntfy").strip().lower()
    if channel == "ntfy":
        return _send_ntfy(message, title)
    if channel == "telegram":
        return _send_telegram(message)
    if channel == "pushover":
        return _send_pushover(message, title)
    if channel == "feishu":
        return _send_feishu(message, title)
    if channel == "email":
        return _send_email(message, title)
    return {"sent": False, "channel": channel, "reason": f"未知推送渠道: {channel}"}


def _send_ntfy(message: str, title: str) -> dict[str, Any]:
    topic = os.getenv("NTFY_TOPIC", "").strip()
    server = os.getenv("NTFY_SERVER", "https://ntfy.sh").strip().rstrip("/")
    if not topic:
        return {"sent": False, "channel": "ntfy", "reason": "未配置 NTFY_TOPIC"}
    url = f"{server}/{topic}"
    try:
        response = requests.post(
            url,
            data=message.encode("utf-8"),
            headers={"Title": title.encode("utf-8"), "Tags": "books"},
            timeout=30,
        )
        response.raise_for_status()
        return {"sent": True, "channel": "ntfy", "status_code": response.status_code}
    except Exception as exc:
        logging.exception("ntfy push failed")
        return {"sent": False, "channel": "ntfy", "reason": str(exc)}


def _send_telegram(message: str) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"sent": False, "channel": "telegram", "reason": "未配置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID"}
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=30,
        )
        response.raise_for_status()
        return {"sent": True, "channel": "telegram", "status_code": response.status_code}
    except Exception as exc:
        logging.exception("Telegram push failed")
        return {"sent": False, "channel": "telegram", "reason": str(exc)}


def _send_pushover(message: str, title: str) -> dict[str, Any]:
    user_key = os.getenv("PUSHOVER_USER_KEY", "").strip()
    api_token = os.getenv("PUSHOVER_API_TOKEN", "").strip()
    if not user_key or not api_token:
        return {"sent": False, "channel": "pushover", "reason": "未配置 PUSHOVER_USER_KEY 或 PUSHOVER_API_TOKEN"}
    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": api_token, "user": user_key, "title": title, "message": message},
            timeout=30,
        )
        response.raise_for_status()
        return {"sent": True, "channel": "pushover", "status_code": response.status_code}
    except Exception as exc:
        logging.exception("Pushover push failed")
        return {"sent": False, "channel": "pushover", "reason": str(exc)}


def _send_feishu(message: str, title: str) -> dict[str, Any]:
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.getenv("FEISHU_SECRET", "").strip()
    if not webhook_url:
        return {"sent": False, "channel": "feishu", "reason": "未配置 FEISHU_WEBHOOK_URL"}

    payload: dict[str, Any] = _feishu_payload(message, title)
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = _feishu_sign(secret, timestamp)

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        code = data.get("code", data.get("StatusCode", 0))
        if code not in (0, "0"):
            return {"sent": False, "channel": "feishu", "reason": data}
        return {"sent": True, "channel": "feishu", "status_code": response.status_code}
    except Exception as exc:
        logging.exception("Feishu push failed")
        return {"sent": False, "channel": "feishu", "reason": str(exc)}


def _feishu_payload(message: str, title: str) -> dict[str, Any]:
    content: list[list[dict[str, str]]] = []
    for line in message[:14000].splitlines():
        if not line.strip():
            content.append([{"tag": "text", "text": " "}])
            continue
        content.append([{"tag": "text", "text": line}])
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content or [[{"tag": "text", "text": message[:12000]}]],
                }
            }
        },
    }


def _feishu_sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"),
        b"",
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _send_email(message: str, title: str) -> dict[str, Any]:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        return {"sent": False, "channel": "email", "reason": f"缺少配置: {', '.join(missing)}"}
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = os.getenv("EMAIL_TO")
    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            server.send_message(msg)
        return {"sent": True, "channel": "email"}
    except Exception as exc:
        logging.exception("Email push failed")
        return {"sent": False, "channel": "email", "reason": str(exc)}
