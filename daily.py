"""Produce the next clip in content/queue.json, or move the queue forward after publishing.

Usage:
  python daily.py build     writes out/today.mp4, out/today_preview.mp4 and out/today.txt
  python daily.py build --still 500   writes one frame to out/still.png instead of the video
  python daily.py advance   marks the current item as published

Verse text comes from the Quran.com API (Uthmani script) and the per-ayah timings
from mp3quran.net, so no Quranic text is ever typed by hand. The clip itself is
drawn by the Remotion template in video/.
"""
import array
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
QUEUE = ROOT / "content" / "queue.json"
STATE = ROOT / "content" / "state.json"
BACKGROUNDS = ROOT / "content" / "backgrounds.json"
CAPTIONS = ROOT / "content" / "captions.json"
DOWNLOADS = ROOT / "downloads"
OUT = ROOT / "out"
VIDEO = ROOT / "video"
CLIP = VIDEO / "public" / "clip"

RECITER = 259
RECITER_NAME = "أحمد النفيس"
AUDIO_BASE = "https://cdn.mp3quran.net/audio/ahmad-nufais/r1/"
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

TRANSLATION = 20  # Saheeh International on Quran.com
MAX_PHRASE = 75  # characters, marks included: about two lines on screen
HAS_LETTER = re.compile("[ء-يٱ]")

LEAD_IN, TAIL, END_CARD = 0.25, 0.5, 2.2
NPX = "npx.cmd" if os.name == "nt" else "npx"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ansit-render/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_verses(surah, first, last):
    data = get_json(f"https://api.quran.com/api/v4/quran/verses/uthmani?chapter_number={surah}")
    text = {int(v["verse_key"].split(":")[1]): v["text_uthmani"] for v in data["verses"]}
    return [text[a] for a in range(first, last + 1)]


def fetch_timings(surah, first, last):
    data = get_json(f"https://mp3quran.net/api/v3/ayat_timing?surah={surah}&read={RECITER}")
    by_ayah = {t["ayah"]: (t["start_time"] / 1000, t["end_time"] / 1000) for t in data}
    return [by_ayah[a] for a in range(first, last + 1)]


def fetch_surah_name(surah):
    return get_json(f"https://api.quran.com/api/v4/chapters/{surah}?language=ar")["chapter"]["name_arabic"]


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


def caption(item, surah_name):
    first, last = (str(item[k]).translate(AR_DIGITS) for k in ("from", "to"))
    ayat = f"الآية {first}" if first == last else f"الآيات {first} - {last}"
    day = load(STATE)["next"]
    texts = load(CAPTIONS)
    line = texts["lines"][day % len(texts["lines"])]
    tags = " ".join(texts["fixed_tags"] + texts["rotating_tags"][day % len(texts["rotating_tags"])])
    return (f"{line}\n\n"
            f"سورة {surah_name} | {ayat}\n"
            f"بصوت الشيخ {RECITER_NAME}\n\n"
            f"{tags}\n")


def fetch_translations(surah, first, last):
    data = get_json(f"https://api.quran.com/api/v4/quran/translations/{TRANSLATION}?chapter_number={surah}")
    clean = [re.sub(r"<sup.*?</sup>|<[^>]+>", "", t["text"]).strip() for t in data["translations"]]
    return clean[first - 1:last]


def loudness(wav):
    """Loudness of the clip in 100 ms steps, used to find where the reciter pauses."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    samples = array.array("h", pcm)
    step = 800
    return [math.sqrt(sum(x * x for x in samples[i:i + step]) / step) for i in range(0, len(samples) - step, step)]


def split_verse(text, start, end, levels):
    """Cut a long verse into phrases: at pause marks when near, timed to the nearest dip in the recitation."""
    pieces = math.ceil(len(text) / MAX_PHRASE)
    if pieces == 1:
        return [(text, start, end)]
    tokens = text.split(" ")
    offsets = [sum(len(t) + 1 for t in tokens[:i]) for i in range(len(tokens) + 1)]
    cuts = []
    for n in range(1, pieces):
        target = len(text) * n / pieces
        # Never start a phrase on a bare pause mark, and favour the point just after one
        options = [i for i in range(1, len(tokens)) if HAS_LETTER.search(tokens[i])]
        cuts.append(min(options, key=lambda i: abs(offsets[i] - target) - (len(text) * 0.12 if not HAS_LETTER.search(tokens[i - 1]) else 0)))
    cuts = sorted(set(cuts))

    phrases, begin, begin_time = [], 0, start
    for cut in cuts:
        guess = start + (end - start) * offsets[cut] / len(text)
        lo, hi = int((guess - 1.0) * 10), int((guess + 1.0) * 10)
        window = range(max(lo, 0), min(hi, len(levels)))
        moment = min(window, key=lambda i: levels[i]) / 10 if window else guess
        phrases.append((" ".join(tokens[begin:cut]), begin_time, moment))
        begin, begin_time = cut, moment
    phrases.append((" ".join(tokens[begin:]), begin_time, end))
    return phrases


def pick_clip(theme, position):
    """Walk through a theme's clips day by day, so a scene comes back only after the whole theme has shown."""
    clips = load(BACKGROUNDS)[theme]
    return clips[(load(STATE)["next"] * 3 + position) % len(clips)]


def extract_scene(theme, position):
    """Remotion's video reader failed on repeated seeks, so footage goes in as numbered images."""
    clip = pick_clip(theme, position)
    key = f"{theme}-{clip['id']}"
    frames = CLIP / "bg" / key
    if not frames.exists():
        bg = download(clip["url"], DOWNLOADS / f"{key}.mp4")
        frames.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(bg), "-an", "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                        "-q:v", "3", str(frames / "%04d.jpg")], check=True)
    return key, len(list(frames.glob("*.jpg")))


def prepare(item):
    """Write the trimmed audio, scenes and props the Remotion template reads."""
    audio = download(f"{AUDIO_BASE}{item['surah']:03d}.mp3", DOWNLOADS / f"{item['surah']:03d}.mp3")

    verses = fetch_verses(item["surah"], item["from"], item["to"])
    timings = fetch_timings(item["surah"], item["from"], item["to"])
    clip_start = timings[0][0] - LEAD_IN
    audio_len = timings[-1][1] + TAIL - clip_start

    CLIP.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{clip_start:.3f}", "-t", f"{audio_len:.3f}", "-i", str(audio),
                    "-af", f"afade=t=in:st=0:d=0.2,afade=t=out:st={audio_len - 0.6:.2f}:d=0.6,"
                           "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100",
                    str(CLIP / "audio.wav")], check=True)
    levels = loudness(CLIP / "audio.wav")
    english = fetch_translations(item["surah"], item["from"], item["to"]) if item.get("en") else [None] * len(verses)

    phrases = []
    for i, (text, (s, e)) in enumerate(zip(verses, timings)):
        parts = split_verse(text, s - clip_start, e - clip_start, levels)
        for j, (part, ps, pe) in enumerate(parts):
            phrase = {"text": part, "start": round(ps, 3), "end": round(pe, 3)}
            if j == len(parts) - 1:
                phrase["number"] = str(item["from"] + i).translate(AR_DIGITS)
            if english[i]:
                phrase["translation"] = english[i]
            phrases.append(phrase)

    scenes = []
    for position, sc in enumerate(item["scenes"]):
        key, frames = extract_scene(sc["bg"], position)
        start = 0 if sc["from"] == item["from"] else round(timings[sc["from"] - item["from"]][0] - clip_start, 3)
        scenes.append({"key": key, "frames": frames, "start": start})

    props = {
        "reciter": RECITER_NAME,
        "phrases": phrases,
        "scenes": scenes,
        "look": item["look"],
        "audioEnd": round(audio_len, 3),
        "total": round(audio_len + END_CARD, 3),
    }
    (CLIP / "props.json").write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")


def build(still=None):
    item = current_item()
    surah_name = fetch_surah_name(item["surah"])
    prepare(item)
    OUT.mkdir(exist_ok=True)

    common = ["src/index.ts", "AyahClip"]
    props = "--props=public/clip/props.json"
    # Windows cannot launch the bundled browser from very long folder paths; point this at a copy
    browser = [f"--browser-executable={os.environ['ANSIT_BROWSER']}"] if "ANSIT_BROWSER" in os.environ else []
    if still is not None:
        subprocess.run([NPX, "remotion", "still", *common, "../out/still.png", props, f"--frame={still}", *browser],
                       check=True, cwd=VIDEO)
        return
    subprocess.run([NPX, "remotion", "render", *common, "../out/today.mp4", props, "--codec=h264",
                    "--video-bitrate=10M", "--audio-bitrate=192k", *browser], check=True, cwd=VIDEO)
    # Telegram bots cannot send files over 50 MB, so the review copy is a small one
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "today.mp4", "-vf", "scale=540:-2", "-c:v", "libx264",
                    "-crf", "28", "-preset", "fast", "-c:a", "aac", "-b:a", "96k", "today_preview.mp4"],
                   check=True, cwd=OUT)
    (OUT / "today.txt").write_text(caption(item, surah_name), encoding="utf-8")


def advance():
    state = load(STATE)
    state["next"] += 1
    STATE.write_text(json.dumps(state) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "advance":
        advance()
    else:
        build(int(sys.argv[3]) if len(sys.argv) > 3 else None)
