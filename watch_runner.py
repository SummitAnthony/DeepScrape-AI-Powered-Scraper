"""Cron-friendly batch runner: re-check every watched URL and report changes.

Usage:  python watch_runner.py
Add to cron/Task Scheduler to monitor pages on a schedule.
"""
import logging

from watch import WatchStore, check_url, DB_PATH
from notify import load_webhook_url, notify_webhook, format_change_message, WEBHOOK_ENV

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def watched_urls(db_path=DB_PATH):
    """List every URL currently being watched."""
    store = WatchStore(db_path)
    try:
        return store.distinct_urls()
    finally:
        store.close()


def run_batch(db_path=DB_PATH, on_change=None):
    """Re-check every watched URL. Returns a summary dict; calls on_change(url, result)
    for each changed page."""
    urls = watched_urls(db_path)
    summary = {"checked": 0, "changed": 0, "errors": 0, "changes": []}
    for url in urls:
        summary["checked"] += 1
        try:
            result = check_url(url, db_path=db_path)
        except Exception as e:
            summary["errors"] += 1
            logger.error(f"Check failed for {url}: {str(e)}")
            continue
        if result.get("changed"):
            summary["changed"] += 1
            summary["changes"].append({"url": url, "result": result})
            logger.info(f"CHANGED: {url} (+{len(result['added'])}/-{len(result['removed'])})")
            if on_change:
                on_change(url, result)
    return summary


def main():
    # If a webhook is configured, alert on every detected change.
    webhook_url = load_webhook_url()

    def on_change(url, result):
        if webhook_url:
            sent = notify_webhook(webhook_url, format_change_message(url, result))
            logger.info(f"Webhook {'sent' if sent else 'FAILED'} for {url}")

    summary = run_batch(on_change=on_change)
    print(f"Checked {summary['checked']} URLs — {summary['changed']} changed, {summary['errors']} errors")
    for change in summary["changes"]:
        r = change["result"]
        print(f"  🔔 {change['url']}: +{len(r['added'])} / -{len(r['removed'])} lines")
    if summary["changed"] and not webhook_url:
        print(f"  (set {WEBHOOK_ENV} to get webhook alerts)")


if __name__ == "__main__":
    main()
