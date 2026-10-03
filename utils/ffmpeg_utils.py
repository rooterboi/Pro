"""
Video-teaser (30 soniya) qirqish mantiqi — ffmpeg-python orqali.

Algoritm:
 1. ffprobe bilan video davomiyligi aniqlanadi.
 2. Kino boshi (titrlar) va oxiri (yakun) tashlab yuboriladi: 5 ta nomzod oyna
    (20%, 35%, 50%, 65%, 80%) tanlanadi.
 3. Har bir oynaning o'rtacha ovoz balandligi `volumedetect` filtri bilan o'lchanadi.
    Eng baland ovozli oyna = eng "jonli" (jang/portlash/dialog avjida) joy deb olinadi.
 4. Audio bo'lmasa yoki o'lchab bo'lmasa — 35% joyidan qirqiladi.
 5. Tanlangan joydan 30 soniya qirqilib, 720p gacha kichraytiriladi va
    Telegram uchun optimal (H.264 + AAC + faststart) formatda kodlanadi.
"""
import asyncio
import logging
import re
import shutil

import ffmpeg

log = logging.getLogger(__name__)

CANDIDATES = (0.20, 0.35, 0.50, 0.65, 0.80)
SILENT = -91.0


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe_duration(path: str) -> float:
    return float(ffmpeg.probe(path)["format"]["duration"])


def mean_volume(path: str, start: float, length: float) -> float:
    try:
        _, err = (
            ffmpeg.input(path, ss=start, t=length)
            .audio.filter("volumedetect")
            .output("-", format="null")
            .run(capture_stdout=True, capture_stderr=True)
        )
        m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", err.decode(errors="ignore"))
        return float(m.group(1)) if m else SILENT
    except ffmpeg.Error:
        return SILENT


def pick_start(path: str, duration: float, seconds: int) -> float:
    if duration <= seconds + 5:
        return 0.0
    limit = max(duration - seconds - 1, 0)
    starts = [min(duration * p, limit) for p in CANDIDATES]
    scores = [mean_volume(path, s, seconds) for s in starts]
    best = max(scores)
    if best <= SILENT + 1:
        return starts[1]
    return starts[scores.index(best)]


def cut_teaser(src: str, dst: str, seconds: int = 30) -> float:
    """Sinxron funksiya. Qirqilgan joy boshlanish vaqtini (sekund) qaytaradi."""
    duration = probe_duration(src)
    start = pick_start(src, duration, seconds)
    (
        ffmpeg.input(src, ss=start, t=seconds)
        .output(
            dst,
            vcodec="libx264", acodec="aac", preset="veryfast", crf=26,
            vf="scale='min(720,iw)':-2", pix_fmt="yuv420p",
            movflags="+faststart", **{"b:a": "96k"},
        )
        .overwrite_output()
        .run(quiet=True)
    )
    log.info("Teaser: start=%.1fs len=%ss", start, seconds)
    return start


async def make_teaser(src: str, dst: str, seconds: int = 30) -> float:
    return await asyncio.to_thread(cut_teaser, src, dst, seconds)
