"""Save links the owner sent to the Telegram bot into content/inspiration.txt.

Telegram keeps bot messages for 24 hours, so this runs every few hours.
Usage: TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python collect_links.py
"""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
LINKS = ROOT / "content" / "inspiration.txt"
OFFSET = ROOT / "content" / "telegram_offset.txt"


def main():
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], int(os.environ["TELEGRAM_CHAT_ID"])
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    query = urllib.parse.urlencode({"offset": offset, "allowed_updates": '["message"]'})
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates?{query}", timeout=30) as r:
        updates = json.load(r)["result"]

    links = []
    for update in updates:
        message = update.get("message", {})
        # Anyone can message a public bot; only the owner's links count
        if message.get("chat", {}).get("id") == chat:
            links += re.findall(r"https?://\S+", message.get("text", "") + " " + message.get("caption", ""))

    if links:
        with LINKS.open("a", encoding="utf-8") as f:
            f.write("\n".join(links) + "\n")
    if updates:
        OFFSET.write_text(str(updates[-1]["update_id"] + 1))
    print(f"{len(links)} new links")


if __name__ == "__main__":
    main()
