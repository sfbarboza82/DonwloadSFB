# -*- coding: utf-8 -*-
import requests

MB_BASE = "https://musicbrainz.org/ws/2"
MB_HEADERS = {"User-Agent": "YT-DLP-DownGUI/1.5 (contact: sfbarboza82@hotmail.com)"}
MB_TIMEOUT = 15

def mb_search_artists_by_genre(genre: str, limit: int = 10):
    q = f'tag:"{genre}"'
    params = {"query": q, "fmt": "json", "limit": limit}
    r = requests.get(f"{MB_BASE}/artist", params=params, headers=MB_HEADERS, timeout=MB_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return [a["name"] for a in data.get("artists", []) if "name" in a]

def mb_search_recordings_by_artist(artist: str, limit: int = 10):
    q = f'artist:"{artist}"'
    params = {"query": q, "fmt": "json", "limit": limit}
    r = requests.get(f"{MB_BASE}/recording", params=params, headers=MB_HEADERS, timeout=MB_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for rec in data.get("recordings", []):
        title = rec.get("title")
        if title: out.append((artist, title))
    return out

def mb_search_recordings_by_title(title: str, limit: int = 10):
    q = f'recording:"{title}"'
    params = {"query": q, "fmt": "json", "limit": limit}
    r = requests.get(f"{MB_BASE}/recording", params=params, headers=MB_HEADERS, timeout=MB_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for rec in data.get("recordings", []):
        t = rec.get("title")
        artist_credit = rec.get("artist-credit", [])
        artist_name = None
        if artist_credit and isinstance(artist_credit, list):
            ac0 = artist_credit[0]
            if isinstance(ac0, dict):
                artist_name = ac0.get("name") or artist_name
        out.append((artist_name or "Desconhecido", t))
    return out
