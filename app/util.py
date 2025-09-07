# -*- coding: utf-8 -*-
import os, sys

def resource_path(*parts) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS  # type: ignore
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)

def bundled_ffmpeg_path() -> str:
    p = resource_path("bin","ffmpeg.exe")
    return p if os.path.isfile(p) else resource_path("ffmpeg.exe")

def bundled_ffprobe_path() -> str:
    p = resource_path("bin","ffprobe.exe")
    return p if os.path.isfile(p) else resource_path("ffprobe.exe")

def bundled_ffplay_path() -> str:
    p = resource_path("bin","ffplay.exe")
    return p if os.path.isfile(p) else resource_path("ffplay.exe")

def seconds_to_hms(s: int) -> str:
    try: s = int(s)
    except Exception: return "-"
    h, r = divmod(s, 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
