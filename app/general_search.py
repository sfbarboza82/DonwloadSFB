# -*- coding: utf-8 -*-
from .util import seconds_to_hms
from .logging_utils import YTDLPLogger

OFFICIAL_HINTS = ["official", "official video", "official audio", "music video"]
OFFICIAL_CHANNEL_HINTS = ["vevo", " - topic", "warner", "umg", "sony music", "rhino", "atlantic records",
                          "universal music", "bmg", "columbia records", "emi", "virgin records"]
NEGATIVE_HINTS = [
    "cover", "live", "lyrics", "letra", "remix", "tribute", "fan made", "parody",
    "official audio", "art track", "visualizer", "audio only", "static image"
]

def official_score(title: str, channel: str) -> int:
    t = (title or "").lower(); c = (channel or "").lower(); score = 0
    for h in OFFICIAL_HINTS:
        if h in t: score += 3 if "official video" in h or "official audio" in h else 2
    for h in OFFICIAL_CHANNEL_HINTS:
        if h in c: score += 3 if "vevo" in h or " - topic" in h else 1
    for h in NEGATIVE_HINTS:
        if h in t: score -= 2
    return score

def search_youtube(logger, query, limit=10):
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp (módulo) não encontrado. pip install yt-dlp"); return []
    logger.info("Buscando YouTube: %s", query)
    opts = {"skip_download": True, "quiet": True, "noplaylist": True, "extract_flat": False, "logger": YTDLPLogger(logger)}
    results = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            entries = info.get("entries") if isinstance(info, dict) else []
            if entries:
                for e in entries:
                    title = e.get("title") or "-"
                    channel = e.get("uploader") or e.get("channel") or "-"
                    duration = seconds_to_hms(e.get("duration"))
                    url = e.get("webpage_url") or e.get("url") or ""
                    vc = e.get("view_count") or 0
                    results.append((title, channel, duration, url, f"ytsearch1:{title} {channel}", vc, official_score(title, channel)))
    except Exception as e:
        logger.exception("Falha na busca geral: %s", e)
    results.sort(key=lambda r: (r[6], r[5]), reverse=True)
    return [(r[0], r[1], r[2], r[3], r[4]) for r in results]
