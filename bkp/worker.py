# -*- coding: utf-8 -*-
import os, threading
from .util import bundled_ffmpeg_path
from .logging_utils import YTDLPLogger

class DownloadWorker(threading.Thread):
    def __init__(self, mode, items, outdir, logger, progress_fn, quality_opts: dict, done_fn=None):
        super().__init__(daemon=True)
        self.mode = mode; self.items = items; self.outdir = outdir
        self.logger = logger; self.progress_fn = progress_fn
        self.quality = quality_opts or {}; self.done_fn = done_fn
        self._stop = threading.Event(); self.rc = 0; self._completed_files = []

    def stop(self): self._stop.set()

    def _likely_static_video(self, info_dict):
        try:
            title = (info_dict.get("title") or "").lower()
            channel = (info_dict.get("uploader") or info_dict.get("channel") or "").lower()
            bad_terms = ("official audio","art track","visualizer","audio only","static image")
            if any(t in title for t in bad_terms):
                return True
            if channel.endswith(" - topic"):
                return True

            fmts = info_dict.get("formats") or []
            if fmts and all((f.get("vcodec") == "none") for f in fmts):
                return True
            max_fps = 0.0
            for f in fmts:
                if f.get("vcodec") and f.get("vcodec") != "none":
                    fps = f.get("fps") or 0
                    try:
                        if fps and float(fps) > max_fps:
                            max_fps = float(fps)
                    except Exception:
                        pass
            return (max_fps and max_fps < 12)
        except Exception:
            return False

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.logger.error("yt-dlp (módulo) não encontrado. Instale: pip install yt-dlp"); self.rc=1; return
        ffmpeg_path = bundled_ffmpeg_path()
        if not os.path.isfile(ffmpeg_path):
            self.logger.error("ffmpeg não encontrado: %s", ffmpeg_path); self.rc=1; return

        os.makedirs(self.outdir, exist_ok=True)
        archive_path = os.path.join(self.outdir, "baixados.txt")

        def hook(d):
            try:
                st = d.get('status')
                if st == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    done = d.get('downloaded_bytes') or 0
                    speed = d.get('speed') or 0.0; eta = d.get('eta') or 0
                    pct = (done/total*100.0) if total else 0.0
                    title = d.get('info_dict', {}).get('title') or os.path.basename(d.get('filename','') or '')
                    self.progress_fn(pct, speed, eta, 'downloading', title)
                elif st == 'finished':
                    fn = d.get('filename','')
                    if fn: self._completed_files.append(fn)
                    self.progress_fn(100.0, 0.0, 0, 'finished', os.path.basename(fn))
                    self.logger.info("Baixado: %s", fn)
            except Exception:
                pass
            if self._stop.is_set(): raise yt_dlp.utils.DownloadError("Interrompido pelo usuário.")

        ff_dir = os.path.dirname(ffmpeg_path)
        common = {
            "ffmpeg_location": ff_dir, "progress_hooks":[hook], "logger": YTDLPLogger(self.logger),
            "restrictfilenames": True, "nocheckcertificate": True, "noplaylist": False,
            "outtmpl": os.path.join(self.outdir, "%(channel,uploader)s", "%(title)s.%(ext)s"),
            "download_archive": archive_path, "nooverwrites": False, "ignoreerrors": True,
            "ignore_no_formats_error": True,
            "concurrent_fragment_downloads": 3, "retries": 5, "fragment_retries": 10, "verbose": True,
        }

        if self.mode == "audio":
            a_k = str(self.quality.get("audio_bitrate_k", 320))
            a_sr = str(self.quality.get("audio_sr", 44100))
            a_ch = str(self.quality.get("audio_channels", 2))
            self.logger.info("[CFG][Áudio] bitrate=%sk, sr=%s, ch=%s", a_k, a_sr, a_ch)
            opts = {**common,
                "format":"bestaudio/best",
                "postprocessors":[
                    {"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":a_k},
                    {"key":"FFmpegMetadata"},{"key":"EmbedThumbnail"}
                ],
                "postprocessor_args":{"FFmpegExtractAudio":["-ar", a_sr, "-ac", a_ch]}
            }
        else:
            v_mode = self.quality.get("video_mode","compat")
            v_h = int(self.quality.get("video_max_h",480))
            v_fps = int(self.quality.get("video_fps",30))
            v_codec = self.quality.get("video_codec","h264").lower()
            v_aac_k = int(self.quality.get("video_audio_k",192))
            v_crf = int(self.quality.get("video_crf",23))
            v_preset = self.quality.get("video_preset","medium")
            self.logger.info("[CFG][Vídeo] mode=%s, codec=%s, max_h=%s, fps=%s, crf=%s, preset=%s, aac=%sk",
                             v_mode, v_codec, v_h, v_fps, v_crf, v_preset, v_aac_k)
            if v_mode == "compat":
                # Força áudio M4A/AAC para players Pioneer e aplica faststart no remux
                fmt = (
                    f"bv*[vcodec~='(?i)(?:avc1|h264|x264)'][fps>=12][height<={v_h}][fps<={v_fps}]"
                    f"+ba[ext=m4a]/b[ext=mp4][vcodec~='(?i)(?:avc1|h264|x264)'][fps>=12][height<={v_h}]"
                )
                opts = {**common, "format": fmt, "merge_output_format":"mp4",
                        "postprocessors":[{"key":"FFmpegVideoRemuxer","preferedformat":"mp4"},{"key":"FFmpegMetadata"}],
                        "postprocessor_args":{"FFmpegVideoRemuxer":["-movflags","+faststart"]}}
            else:
                # Converte garantindo H.264 + AAC e aplica faststart
                opts = {**common, "format":"bestvideo*+bestaudio/best",
                        "postprocessors":[{"key":"FFmpegVideoConvertor","preferedformat":"mp4"},{"key":"FFmpegMetadata"}],
                        "postprocessor_args":{"FFmpegVideoConvertor":[
                            "-vf", f"scale=-2:{v_h}", "-r", str(v_fps), "-c:v", "libx264",
                            "-crf", str(v_crf), "-preset", v_preset,
                            "-c:a", "aac", "-b:a", f"{v_aac_k}k",
                            "-movflags", "+faststart"
                        ]}}
        ok = err = 0
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                total = len(self.items); self.logger.info("Iniciando downloads (%s) — itens: %s", self.mode, total)
                for i, q in enumerate(self.items, start=1):
                    if self._stop.is_set(): raise yt_dlp.utils.DownloadError("Interrompido pelo usuário.")
                    self.logger.info("[%s/%s] %s", i, total, q)
                    try:
                        ie = ydl.extract_info(q, download=False)
                        if self.mode == "video" and self._likely_static_video(ie):
                            self.logger.info("Ignorando possível vídeo estático (fps baixo/áudio apenas): %s", ie.get("title") or q)
                            continue
                        ydl.process_ie_result(ie, download=True)
                        ok += 1
                    except Exception as e:
                        self.logger.exception("Falha: %s -> %s", q, e); err += 1
        except Exception as e:
            self.logger.exception("Execução interrompida: %s", e); self.rc=1
        else:
            self.logger.info("Concluído (%s). Sucesso: %s | Falhas: %s", self.mode, ok, err)
            if callable(self.done_fn):
                try: self.done_fn(self.mode, list(self._completed_files), ok, err, self.outdir)
                except Exception: pass
            self.rc=0
