# DonwloadSFB
Download audio or video files from the internet
# DownloadSFB — Audio/Video Downloader (GUI)

> **Download audio (MP3) and video (MP4/H.264) from YouTube with a simple desktop interface, queues, quality profiles, USB support, and multi‑language UI.**

---

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Architecture & Modules](#architecture--modules)
* [Requirements](#requirements)
* [Installation](#installation)
* [How to Use](#how-to-use)
* [Quality (Audio/Video)](#quality-audiovideo)
* [USB / Removable Device Flow](#usb--removable-device-flow)
* [Languages (PT/EN/ES)](#languages-ptenes)
* [Logs & Output Locations](#logs--output-locations)
* [Starting New Downloads After Finish](#starting-new-downloads-after-finish)
* [Troubleshooting](#troubleshooting)

---

## Overview

**DownloadSFB** is a desktop application (Tkinter) that downloads **audio** and **video** from YouTube using `yt-dlp` and `ffmpeg`. It shows live progress, writes detailed logs, supports MusicBrainz‑powered searches (genre/artist/track), has a category‑based general YouTube search, queue management (URLs and `ytsearch:`), and flexible audio/video quality options. Work is executed by a dedicated background thread (**DownloadWorker**) that orchestrates `yt-dlp`, progress hooks, and post‑processing via `ffmpeg`.

---

## Features

* **Audio (MP3) downloads** with configurable bitrate (kbps), sample rate (Hz), and channel count; converted via `ffmpeg` post‑processing.
* **Video (MP4/H.264) downloads** with configurable mode (compat), max height, max FPS, codec, CRF, and preset.
* **Live progress** (percent, speed, ETA) and a list of completed items via `yt-dlp` hooks.
* **Search**

  * **MusicBrainz**: by genre/style, by artist/band, or by song title; results generate precise YouTube queries.
  * **YouTube (general)**: by **category** (Documentaries, Tutorials, etc.) + free‑text terms; categories automatically expand the query strings.
* **Queues** (URL and `ytsearch:`): import/export `.txt`, add multiple items at once, and combine with search results.
* **Destination folders** for Audio/Video and a **Logs** folder, with sensible defaults (user Documents).
* **`ffmpeg` detection** (bundled or system PATH) and `yt-dlp` availability checks with clear error messages.
* **USB / removable device support**: detects drives, verifies filesystem, can format to FAT32, and optionally **wipe contents** before copying.
* **Choice on USB action** (new): when a USB device is recognized you can choose **Format (erase all)**, **Only add** (keep existing files, just copy new ones), or **Cancel**.
* **Multi‑language UI**: Portuguese, English, and Spanish; on‑the‑fly language switching across the entire interface (tabs, labels, message boxes, table headers, category names, etc.).
* **Restart without closing**: after a download finishes you can immediately start another (state resets automatically), plus a **Reset session** button for manual reset.

---

## Architecture & Modules

* **`gui.py`** — Tkinter application (windows, tabs, lists, buttons, dialogs); integrates MusicBrainz and YouTube search, manages destinations and logs, handles the worker lifecycle, and implements the removable device flow.
* **`worker.py`** — `DownloadWorker` thread that builds `yt-dlp` options, wires the bundled/system `ffmpeg`, handles progress hooks, and runs audio/video post‑processing; writes detailed logs and returns completion status.
* **`constants.py`** — General categories, category expansions for YouTube search, and language mappings for category display labels.
* **`i18n.py`** — Translation dictionaries (PT→EN/ES) and helpers: `set_language(lang)`, `get_language()`, `tr(string)`.
* **`mb_api.py`** — MusicBrainz helpers (genre → artists, artist → tracks, track lookups).
* **`general_search.py`** — YouTube query builder & search logic (including category expansions).
* **`logging_utils.py`** — Logger setup and `yt-dlp` integration for unified console/file logging.
* **`util.py`** — Utilities (paths, environment, bundled `ffmpeg` resolution, OS helpers).
* **`storage.py`** — Removable drive detection (letter, label, fs), filesystem checks, FAT32 format, and safe wipe helpers.
* **`DownloadSFBarboza.py`** — Entry point that launches the GUI (`run_app()`).

---

## Requirements

* **Python 3.x**
* **Packages**: `yt-dlp`
* **`ffmpeg`** available either as a bundled binary (preferred) or on system PATH

> If you don’t have them: `pip install yt-dlp` and install/provide `ffmpeg` (or place the bundled binary where `util.py` expects).

---

## Installation

1. **Clone/extract** the project into a local folder.
2. (Optional) **Create & activate a virtual environment**.
3. **Install Python dependencies**:

   ```bash
   pip install yt-dlp
   ```
4. Ensure **`ffmpeg`** is available (bundled or on PATH).

---

## How to Use

1. **Run the application** (GUI). The main window opens with tabs for Music, YouTube (general), direct URLs & queues, quality, donations, and downloads/status.
2. In **Output & Logs** (top of the window), adjust:

   * **Audio destination** and **Video destination** (defaults to subfolders under your Documents folder).
   * **Logs folder**.
3. **Add items** to your queues:

   * **Music (MusicBrainz)**: search by **genre**, **artist/band**, or **song title**; check the results and add the checked/selected items to Audio or Video queues.
   * **YouTube (general)**: pick a **category**, enter **terms**, and search; add results to Audio/Video queues, or add the entire search as a list.
   * **Direct URL / Lists**: paste a single URL, paste a multiline list (one per line; supports `ytsearch:` and `http/https`), import from `.txt`, or export your queues to `.txt`.
4. **Set Quality** for Audio and/or Video (see below).
5. Click **Start Audio Download** or **Start Video Download**, then monitor **Download progress** and the **Live log** section.

---

## Quality (Audio/Video)

* **Audio (MP3)**

  * **Bitrate (kbps)**, **Sample rate (Hz)**, **Channels**
  * Post‑processing chain includes extraction, metadata, and optional thumbnail embedding handled by `yt-dlp`/`ffmpeg`.
* **Video (MP4/H.264)**

  * **Mode (compat)**, **Max height (p)**, **Max FPS**, **Codec**, **CRF**, **Preset**
  * `yt-dlp` selects appropriate formats; re‑encoding parameters (CRF/preset) apply when re‑muxing/re‑encode is needed.

> Quick profile included: **Pioneer AVIC** (480p/30 H.264 + AAC 192 kbps; MP3 320k/44.1 kHz/2ch, compat mode).

---

## USB / Removable Device Flow

When you choose to save to a removable device:

1. The app **lists available devices** and asks you to pick the target.
2. It confirms the device you selected (drive letter, label, filesystem).
3. **Action choice** dialog (new):

   * **Format (erase all)** — formats the drive to **FAT32** and wipes all contents. Use this for maximum compatibility.
   * **Only add** — keeps existing files and **only copies new items** (no format, no wipe).
   * **Cancel** — aborts device selection.
4. If you choose **Format**, the app runs a FAT32 format and proceeds to copy the new files.
5. If you choose **Only add**, the app **skips format and skip wipe**, copying only the selected downloads.
6. In legacy flows (when skipping the new dialog), the app may still ask whether to format to FAT32 (if the filesystem is incompatible) or to **wipe contents** before copying — those original prompts and logs are still preserved.

All operations are logged, and any errors will show actionable messages (e.g., try as Administrator or format manually).

---

## Languages (PT/EN/ES)

* Language selector at the top of the window (**Language / Idioma**). Choose **Português**, **English**, or **Español**.
* Click **Apply language** to re‑translate the entire interface on the fly (tabs, labels, dialogs, table headers). You can switch languages any time; the translation is reapplied using internal PT baselines to avoid stale keys.
* Category names are displayed in the chosen language but mapped internally to canonical PT keys (so your existing logic and expansions remain intact).

---

## Logs & Output Locations

* **Logs** are written to the configured Logs folder and displayed live in the Downloads & Status tab.
* **Output**

  * Audio/Video files: by default saved under subfolders in **Documents** (you can change destinations at the top of the window).
  * The worker keeps a small registry of recently downloaded items to avoid duplicates within a run.

---

## Starting New Downloads After Finish

* After a download finishes, the application **resets its state** automatically so you can start another download immediately.
* There is also a **Reset session** button in the Downloads & Status tab if you want to manually reset the UI at any time.
* Internally, the GUI releases the previous worker thread reference when it is no longer alive, and status labels return to **Waiting…** so the **Start** buttons are immediately available again.

---

## Troubleshooting

* **`yt-dlp` not found**: install with `pip install yt-dlp`.
* **`ffmpeg` not found**: put the binary on PATH or provide the bundled executable where the app expects it.
* **USB not recognized or format failed**: you’ll see detailed messages in the UI/logs; try running as Administrator or formatting manually if required.
* **Permissions**: on some systems, writing to certain folders or formatting drives may require elevated privileges.

---

**Need an English or Spanish version of this README bundled with releases?** Open an issue or let us know and we’ll include localized README files alongside the PT one.
