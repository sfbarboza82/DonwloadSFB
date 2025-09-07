# -*- coding: utf-8 -*-
import os
from datetime import datetime
import tkinter as tk

class TextHandler:
    def __init__(self, textbox: tk.Text):
        self.textbox = textbox

    def write(self, line: str):
        try:
            if not self.textbox or not self.textbox.winfo_exists():
                return
            self.textbox.configure(state="normal")
            self.textbox.insert("end", line.rstrip() + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        except Exception:
            pass

class Logger:
    def __init__(self, log_path: str, textbox: tk.Text = None, name: str = "app"):
        self.name = name
        self.log_path = log_path
        self.text_handler = TextHandler(textbox) if textbox else None

    def _emit(self, level: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} | {level:>6} | {msg}"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        if self.text_handler:
            self.text_handler.write(line)

    def info(self, msg, *args):
        self._emit("INFO", (msg % args) if args else str(msg))

    def warning(self, msg, *args):
        self._emit("WARN", (msg % args) if args else str(msg))

    def error(self, msg, *args):
        self._emit("ERRO", (msg % args) if args else str(msg))

    def exception(self, msg, *args):
        self._emit("ERRO", (msg % args) if args else str(msg))

class YTDLPLogger:
    def __init__(self, logger: Logger):
        self.l = logger
    def debug(self, msg):
        try:
            s = msg.decode("utf-8","ignore") if isinstance(msg, (bytes,bytearray)) else str(msg)
        except Exception:
            s = str(msg)
        self.l.info("[yt-dlp] %s", s)
    def warning(self, msg):
        try:
            s = msg.decode("utf-8","ignore") if isinstance(msg, (bytes,bytearray)) else str(msg)
        except Exception:
            s = str(msg)
        self.l.warning("[yt-dlp] %s", s)
    def error(self, msg):
        try:
            s = msg.decode("utf-8","ignore") if isinstance(msg, (bytes,bytearray)) else str(msg)
        except Exception:
            s = str(msg)
        self.l.error("[yt-dlp] %s", s)

def setup_logger(log_dir: str, textbox: tk.Text, name: str = "app"):
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(log_dir, f"session_{ts}.log")
    lg = Logger(log_path, textbox, name=name)
    lg.info("Logs iniciados: %s", log_path)
    return lg, log_path
