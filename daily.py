"""Produce the next clip in content/queue.json, or move the queue forward after publishing.

Usage:
  python daily.py build     writes out/today.mp4, out/today_preview.mp4 and out/today.txt
  python daily.py advance   marks the current item as published
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from render import RECITERS, fetch_surah_name

ROOT = Path(__file__).parent
QUEUE = ROOT / "content" / "queue.json"
STATE = ROOT / "content" / "state.json"
BACKGROUNDS = ROOT / "content" / "backgrounds.json"
DOWNLOADS = ROOT / "downloads"
OUT = ROOT / "out"

RECITER = 259
AUDIO_BASE = "https://cdn.mp3quran.net/audio/ahmad-nufais/r1/"
HASHTAGS = "#قرآن #تلاوة #القرآن_الكريم #تلاوات_خاشعة #أنصت"
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def current_item():
    queue = load(QUEUE)
    return queue[load(STATE)["next"] % len(queue)]


def download(url, dest):
    if dest.exists():
        return dest
    dest.parent.mkdir(exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())
    return dest


def caption(item):
    first, last = (str(item[k]).translate(AR_DIGITS) for k in ("from", "to"))
    ayat = f"الآية {first}" if first == last else f"الآيات {first} - {last}"
    return (f"سورة {fetch_surah_name(item['surah'])} | {ayat}\n"
            f"بصوت الشيخ {RECITERS[RECITER]}\n\n"
            f"أنصِت.. لعلّك تُرحم\n\n{HASHTAGS}\n")


def build():
    item = current_item()
    audio = download(f"{AUDIO_BASE}{item['surah']:03d}.mp3", DOWNLOADS / f"{item['surah']:03d}.mp3")
    bg = download(load(BACKGROUNDS)[item["bg"]], DOWNLOADS / f"{item['bg']}.mp4")

    # Relative paths: the subtitles filter cannot parse Windows drive letters
    video = "out/today.mp4"
    subprocess.run([sys.executable, "render.py", "--surah", str(item["surah"]), "--from", str(item["from"]),
                    "--to", str(item["to"]), "--reciter", str(RECITER), "--audio", audio.relative_to(ROOT).as_posix(),
                    "--bg", bg.relative_to(ROOT).as_posix(), "--out", video], check=True, cwd=ROOT)
    # Telegram bots cannot send files over 50 MB, so the review copy is a small one
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf", "scale=540:-2", "-c:v", "libx264",
                    "-crf", "28", "-preset", "fast", "-c:a", "aac", "-b:a", "96k", "out/today_preview.mp4"],
                   check=True, cwd=ROOT)
    (OUT / "today.txt").write_text(caption(item), encoding="utf-8")


def advance():
    state = load(STATE)
    state["next"] += 1
    STATE.write_text(json.dumps(state) + "\n", encoding="utf-8")


if __name__ == "__main__":
    {"build": build, "advance": advance}[sys.argv[1]]()
