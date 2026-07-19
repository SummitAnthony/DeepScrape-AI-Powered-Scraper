"""Webhook notifications: alert Slack/Discord/generic endpoints when a watched page changes."""
import logging
import os

import requests

logger = logging.getLogger(__name__)

WEBHOOK_ENV = "DEEPSCRAPE_WEBHOOK_URL"


def load_webhook_url():
    """Read the webhook URL from the DEEPSCRAPE_WEBHOOK_URL env var, or None."""
    return os.environ.get(WEBHOOK_ENV) or None


def format_change_message(url, result, max_lines=8):
    """Build a human-readable change message from a watch check result."""
    added = result.get("added", [])
    removed = result.get("removed", [])
    lines = [f"🔔 Page changed: {url}", f"(+{len(added)} / -{len(removed)} lines)"]
    for line in added[:max_lines]:
        lines.append(f"+ {line}")
    for line in removed[:max_lines]:
        lines.append(f"- {line}")
    return "\n".join(lines)


def notify_webhook(webhook_url, message, timeout=10):
    """POST a message to a webhook. Payload carries both Slack ('text') and
    Discord ('content') keys so either platform accepts it. Returns True on success."""
    if not webhook_url:
        return False
    try:
        response = requests.post(webhook_url, json={"text": message, "content": message}, timeout=timeout)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Webhook notification failed: {str(e)}")
        return False
