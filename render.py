"""Render one Ansit (أنصِت) Quran clip: verses timed to the recitation over a nature background.

Usage:
  python render.py --surah 55 --from 19 --to 27 --audio downloads/055.mp3 \
      --bg downloads/sea.mp4 --out out/rahman_19-27.mp4 [--look stroke|band] [--font "Amiri Quran"]

  Add --preview 2,28,44 to write still frames at those seconds instead of the full video.

Verse text comes from the Quran.com API (Uthmani script) and the per-ayah timings
from mp3quran.net for the chosen reciter, so no Quranic text is ever typed by hand.
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

RECITERS = {259: "أحمد النفيس", 107: "محمد اللحيدان"}
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# Brand colours in ASS order (&HAABBGGRR)
PARCH = "&H00D4E8F2"
BRASS = "&H0061A8C9"
SOFT = "&H22C4DCE7"
NIGHT = "&H00171A0F"

W, H = 1080, 1920
LEAD_IN, TAIL = 0.25, 0.5
BAND_H = 720

# How the verse is set apart from the footage
LOOKS = {
    # thick soft dark stroke around every letter, no box
    "stroke": {"outline": 9, "shadow": 6, "outline_col": "&H18171A0F", "back_col": "&H60000000", "blur": 3},
    # soft dark band behind the verse, letters only lightly shadowed
    "band": {"outline": 0, "shadow": 2, "outline_col": NIGHT, "back_col": "&H90000000", "blur": 0},
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ansit-render/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_verses(surah, first, last):
    data = get_json(f"https://api.quran.com/api/v4/quran/verses/uthmani?chapter_number={surah}")
    text = {int(v["verse_key"].split(":")[1]): v["text_uthmani"] for v in data["verses"]}
    return [text[a] for a in range(first, last + 1)]


def fetch_timings(surah, first, last, reciter):
    data = get_json(f"https://mp3quran.net/api/v3/ayat_timing?surah={surah}&read={reciter}")
    by_ayah = {t["ayah"]: (t["start_time"] / 1000, t["end_time"] / 1000) for t in data}
    return [by_ayah[a] for a in range(first, last + 1)]


def fetch_surah_name(surah):
    data = get_json(f"https://api.quran.com/api/v4/chapters/{surah}?language=ar")
    return data["chapter"]["name_arabic"]


def ts(sec):
    cs = round(sec * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def build_ass(verses, timings, first, surah_name, reciter_name, clip_start, duration, look, font, size):
    lk = LOOKS[look]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ayah,{font},{size},{PARCH},{PARCH},{lk['outline_col']},{lk['back_col']},0,0,0,0,100,100,0,0,1,{lk['outline']},{lk['shadow']},5,100,100,0,1
Style: Surah,El Messiri,46,{SOFT},{SOFT},{NIGHT},&H80000000,0,0,0,0,100,100,0,0,1,2,1,9,80,80,170,1
Style: Brand,Aref Ruqaa,72,{BRASS},{BRASS},{NIGHT},&H80000000,1,0,0,0,100,100,0,0,1,2,1,7,80,80,150,1
Style: Reciter,El Messiri,62,{BRASS},{BRASS},{NIGHT},&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,80,80,480,1
Style: Num,El Messiri,40,{SOFT},{SOFT},{NIGHT},&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    end = ts(duration)
    lines = [
        f"Dialogue: 0,0:00:00.00,{end},Surah,,0,0,0,,{{\\fad(400,400)}}سورة {surah_name}",
        f"Dialogue: 0,0:00:00.00,{end},Brand,,0,0,0,,{{\\fad(400,400)}}أنصِت",
        f"Dialogue: 0,0:00:00.00,{end},Reciter,,0,0,0,,{{\\fad(400,400)}}{reciter_name}",
    ]
    # Each verse fades in while easing from 96% to full size
    enter = f"\\fad(250,200)\\blur{lk['blur']}\\fscx96\\fscy96\\t(0,350,\\fscx100\\fscy100)"
    for i, (text, (s, e)) in enumerate(zip(verses, timings)):
        s, e = max(0.0, s - clip_start), min(duration, e - clip_start)
        num = str(first + i).translate(AR_DIGITS)
        lines.append(f"Dialogue: 1,{ts(s)},{ts(e)},Ayah,,0,0,0,,{{{enter}}}{text}")
        lines.append(f"Dialogue: 1,{ts(s)},{ts(e)},Num,,0,0,0,,{{\\fad(250,200)}}الآية {num}")
    return head + "\n".join(lines) + "\n"


def make_loop(bg, workdir):
    """Cross-fade the clip's tail into its head once, so it can repeat with no visible jump."""
    loop = workdir / (Path(bg).stem + ".loop.mp4")
    if loop.exists():
        return loop
    length = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", bg],
        capture_output=True, text=True, check=True).stdout)
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1,split[a][b];"
        f"[a]trim=start=1:end={length:.3f},setpts=PTS-STARTPTS[body];"
        "[b]trim=start=0:end=1,setpts=PTS-STARTPTS[head];"
        f"[body][head]xfade=transition=fade:duration=1:offset={length - 2:.3f}[v]"
    )
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", bg, "-filter_complex", fc, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(loop)], check=True)
    return loop


def make_band(workdir):
    """Night-coloured band that fades out towards its top and bottom edges."""
    band = workdir / "band.png"
    if band.exists():
        return band
    fade = 220
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x0F1A17:s={W}x{BAND_H}:d=1",
        "-vf", f"format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='215*pow(min(1,min(Y,H-1-Y)/{fade}),1.3)'",
        "-frames:v", "1", str(band)], check=True)
    return band


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--surah", type=int, required=True)
    p.add_argument("--from", dest="first", type=int, required=True)
    p.add_argument("--to", dest="last", type=int, required=True)
    p.add_argument("--reciter", type=int, default=259)
    p.add_argument("--audio", required=True, help="full-surah mp3 matching the reciter's timings")
    p.add_argument("--bg", required=True, help="vertical background video")
    p.add_argument("--out", required=True)
    p.add_argument("--fonts", default="fonts")
    p.add_argument("--look", choices=LOOKS, default="band")
    p.add_argument("--font", default="Scheherazade New", help="font for the verse text")
    p.add_argument("--size", type=int, help="verse font size; chosen from the longest verse when omitted")
    p.add_argument("--preview", help="comma-separated seconds; writes PNG frames instead of the video")
    a = p.parse_args()

    verses = fetch_verses(a.surah, a.first, a.last)
    timings = fetch_timings(a.surah, a.first, a.last, a.reciter)
    surah_name = fetch_surah_name(a.surah)

    clip_start = timings[0][0] - LEAD_IN
    duration = timings[-1][1] + TAIL - clip_start

    # Long verses step down in size so they stay inside the band
    longest = max(len(v) for v in verses)
    size = a.size or (150 if longest <= 80 else 124 if longest <= 140 else 104)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ass = out.with_suffix(".ass")
    ass.write_text(build_ass(verses, timings, a.first, surah_name, RECITERS.get(a.reciter, ""),
                             clip_start, duration, a.look, a.font, size), encoding="utf-8")

    bg_loop = make_loop(a.bg, out.parent)
    inputs = ["-stream_loop", "-1", "-i", str(bg_loop), "-i", a.audio]

    # Background darkened slightly so the verse reads clearly.
    # The subtitles filter path is relative because Windows drive letters break its option parser.
    vf = (
        f"[0:v]trim=duration={duration:.2f},setpts=PTS-STARTPTS,"
        "eq=brightness=-0.03:saturation=0.9,vignette=PI/5,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=0x0F1A17@0.18:t=fill[bg];"
    )
    if a.look == "band":
        inputs += ["-loop", "1", "-i", str(make_band(out.parent))]
        vf += f"[bg][2:v]overlay=0:{(H - BAND_H) // 2}:shortest=1[bg];"
    vf += (
        f"[bg]subtitles={ass.as_posix()}:fontsdir={Path(a.fonts).as_posix()},"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={duration - 0.6:.2f}:d=0.6[v]"
    )

    if a.preview:
        for t in a.preview.split(","):
            png = out.with_name(f"{out.stem}_{t}s.png")
            subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", vf, "-map", "[v]",
                            "-ss", t, "-frames:v", "1", str(png)], check=True)
            print(png)
        return

    af = (
        f"[1:a]atrim=start={clip_start:.2f}:duration={duration:.2f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.3,afade=t=out:st={duration - 0.7:.2f}:d=0.7,"
        "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]", "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    print(f"{out}  ({duration:.1f}s, {surah_name} {a.first}-{a.last})")


if __name__ == "__main__":
    main()
