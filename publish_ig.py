"""Publish a Reel to Instagram from a public video URL.

Usage: IG_TOKEN=... python publish_ig.py <video_url> <caption_file>
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.instagram.com/v26.0"
POLL_SECONDS = 10
POLL_LIMIT = 90


def call(path, token, data=None, **params):
    query = urllib.parse.urlencode({**params, "access_token": token})
    body = urllib.parse.urlencode(data).encode() if data else None
    try:
        with urllib.request.urlopen(f"{API}/{path}?{query}", data=body, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err = json.load(e).get("error", {})
        sys.exit(f"Instagram refused ({e.code}): {err.get('message')}")


def main():
    video_url, caption_file = sys.argv[1:3]
    token = os.environ["IG_TOKEN"]
    caption = Path(caption_file).read_text(encoding="utf-8")

    user_id = call("me", token, fields="user_id")["user_id"]
    container = call(f"{user_id}/media", token, data={
        "media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": "true"})["id"]

    for _ in range(POLL_LIMIT):
        status = call(container, token, fields="status_code,status")
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram could not process the video: {status.get('status')}")
        time.sleep(POLL_SECONDS)
    else:
        sys.exit("Instagram did not finish processing the video in time")

    media_id = call(f"{user_id}/media_publish", token, data={"creation_id": container})["id"]
    print("Published:", call(media_id, token, fields="permalink").get("permalink"))


if __name__ == "__main__":
    main()
