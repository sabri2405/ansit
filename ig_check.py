"""Check that the Instagram token in .env works and can publish. Publishes nothing.

Usage: python ig_check.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.instagram.com/v26.0"


def load_token():
    env = Path(__file__).with_name(".env")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("IG_TOKEN="):
            token = line.split("=", 1)[1].strip()
            if token:
                return token
    sys.exit("IG_TOKEN is empty in .env")


def get(path, token, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode({**params, "access_token": token})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err = json.load(e).get("error", {})
        sys.exit(f"Instagram refused ({e.code}): {err.get('message')}")


def main():
    token = load_token()
    me = get("me", token, fields="user_id,username,account_type,followers_count,media_count")
    print(f"Connected: @{me.get('username')}  type={me.get('account_type')}  "
          f"followers={me.get('followers_count')}  posts={me.get('media_count')}")
    if me.get("account_type") not in ("BUSINESS", "MEDIA_CREATOR"):
        print("Warning: the account must be a professional (Business or Creator) account to publish.")
    limit = get(f"{me['user_id']}/content_publishing_limit", token, fields="quota_usage,config")
    print("Publishing quota:", json.dumps(limit.get("data", limit), ensure_ascii=False))


if __name__ == "__main__":
    main()
