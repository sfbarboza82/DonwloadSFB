# -*- coding: utf-8 -*-
import os, time, webbrowser, threading, sys, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .constants import DONATION_EMAIL, GENERAL_CATEGORIES, CATEGORY_EXPANSIONS
from .util import resource_path, bundled_ffmpeg_path, bundled_ffprobe_path, bundled_ffplay_path
from .logging_utils import setup_logger
from .mb_api import mb_search_artists_by_genre, mb_search_recordings_by_artist, mb_search_recordings_by_title
from .general_search import search_youtube
from .worker import DownloadWorker
from . import storage

CHECKED = "✓"
UNCHECKED = ""

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DownloadSFB — Downloader Áudio/Vídeo (GUI)")
        try:
            self.iconbitmap(resource_path('files','app_icon.ico'))
        except Exception:
            pass
        try:
            self.state('zoomed')
        except Exception:
            try:
                self.attributes('-zoomed', True)
            except Exception:
                self.geometry("%dx%d+0+0" % (self.winfo_screenwidth(), self.winfo_screenheight()))

        self.worker = None
        self.last_general_query = None
        self.checked_mb = set()
        self.checked_gen = set()

        user_docs = os.path.join(os.path.expanduser("~"), "Documents")
        self.audio_out = tk.StringVar(value=os.path.join(user_docs, "DownloadSFB-Audio"))
        self.video_out = tk.StringVar(value=os.path.join(user_docs, "DownloadSFB-Video"))
        self.log_dir = tk.StringVar(value=os.path.join(user_docs, "DownloadSFB-Logs"))

        self.audio_bitrate_k = tk.IntVar(value=320)
        self.audio_sr = tk.IntVar(value=44100)
        self.audio_channels = tk.IntVar(value=2)
        self.video_mode = tk.StringVar(value="compat")
        self.video_codec = tk.StringVar(value="h264")
        self.video_max_h = tk.IntVar(value=480)
        self.video_fps = tk.IntVar(value=30)
        self.video_crf = tk.IntVar(value=23)
        self.video_preset = tk.StringVar(value="medium")
        self.video_audio_k = tk.IntVar(value=192)

        self.mb_limit_artists = tk.IntVar(value=10)
        self.mb_limit_tracks = tk.IntVar(value=10)
        self.auto_open_folder = tk.BooleanVar(value=True)
        self.last_downloaded_files = []

        self._build_ui()
        self.logger, self.log_path = setup_logger(self.log_dir.get(), self.txt_log, name="downloadsfb")
        self.logger.info("ffmpeg: %s", bundled_ffmpeg_path())
        self.logger.info("ffprobe: %s", bundled_ffprobe_path())
        self.logger.info("Aplicativo iniciado. Pastas padrão: Áudio=%s | Vídeo=%s | Logs=%s",
                         self.audio_out.get(), self.video_out.get(), self.log_dir.get())

    def _build_ui(self):
        frm_paths = ttk.LabelFrame(self, text="Pastas de Saída e Logs")
        frm_paths.pack(fill="x", padx=10, pady=8)
        def row(parent, label, var, browse_cmd, w=95):
            r = ttk.Frame(parent)
            ttk.Label(r, text=label, width=24).pack(side="left")
            ttk.Entry(r, textvariable=var, width=w).pack(side="left", fill="x", expand=True, padx=6)
            ttk.Button(r, text="Selecionar…", command=browse_cmd).pack(side="left")
            r.pack(fill="x", pady=2)
        row(frm_paths, "Destino Áudio:", self.audio_out, self.browse_audio_out)
        row(frm_paths, "Destino Vídeo:", self.video_out, self.browse_video_out)
        row(frm_paths, "Pasta de Logs:", self.log_dir, self.browse_log_dir)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=8)

        tab_search = ttk.Frame(self.nb)
        self.nb.add(tab_search, text="🎵 Música (Gênero/Artista/Título)")

        frm_genre = ttk.LabelFrame(tab_search, text="Por gênero/estilo (ex.: grunge, classic rock)")
        frm_genre.pack(fill="x", padx=8, pady=6)
        self.genre_var = tk.StringVar()
        ttk.Entry(frm_genre, textvariable=self.genre_var, width=40).pack(side="left", padx=6, pady=6)
        ttk.Button(frm_genre, text="Buscar artistas por gênero", command=self.search_by_genre).pack(side="left", padx=6)
        ttk.Label(frm_genre, text="Artistas:").pack(side="left", padx=(12,4))
        tk.Spinbox(frm_genre, from_=1, to=50, textvariable=self.mb_limit_artists, width=4).pack(side="left", padx=4)
        ttk.Label(frm_genre, text="Músicas/artista:").pack(side="left", padx=(12,4))
        tk.Spinbox(frm_genre, from_=1, to=50, textvariable=self.mb_limit_tracks, width=4).pack(side="left", padx=4)

        frm_artist = ttk.LabelFrame(tab_search, text="Por banda/artista/grupo (ex.: Nirvana, Pink Floyd)")
        frm_artist.pack(fill="x", padx=8, pady=6)
        self.artist_var = tk.StringVar()
        ttk.Entry(frm_artist, textvariable=self.artist_var, width=40).pack(side="left", padx=6, pady=6)
        ttk.Button(frm_artist, text="Buscar músicas do artista", command=self.search_by_artist).pack(side="left", padx=6)
        ttk.Label(frm_artist, text="Músicas:").pack(side="left", padx=(12,4))
        tk.Spinbox(frm_artist, from_=1, to=50, textvariable=self.mb_limit_tracks, width=4).pack(side="left", padx=4)

        frm_title = ttk.LabelFrame(tab_search, text="Por nome de música (ex.: Smells Like Teen Spirit)")
        frm_title.pack(fill="x", padx=8, pady=6)
        self.title_var = tk.StringVar()
        ttk.Entry(frm_title, textvariable=self.title_var, width=40).pack(side="left", padx=6, pady=6)
        ttk.Button(frm_title, text="Buscar por nome", command=self.search_by_title).pack(side="left", padx=6)
        ttk.Label(frm_title, text="Músicas:").pack(side="left", padx=(12,4))
        tk.Spinbox(frm_title, from_=1, to=50, textvariable=self.mb_limit_tracks, width=4).pack(side="left", padx=4)

        pr_mb = ttk.LabelFrame(tab_search, text="Progresso da busca (MusicBrainz)")
        pr_mb.pack(fill="x", padx=8, pady=(2,8))
        self.pg_mb = ttk.Progressbar(pr_mb, mode="indeterminate")
        self.pg_mb.pack(fill="x", padx=8, pady=6)
        self.lbl_mb = ttk.Label(pr_mb, text="Parado")
        self.lbl_mb.pack(fill="x", padx=8, pady=(0,6))

        cnt_mb = ttk.Frame(tab_search)
        cnt_mb.pack(fill="both", expand=True, padx=8, pady=6)
        cnt_mb.grid_rowconfigure(0, weight=1)
        cnt_mb.grid_columnconfigure(0, weight=1)

        res_frame = ttk.LabelFrame(cnt_mb, text="Resultados (marque itens ou use 'Marcar todos')")
        res_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0,6))
        self.tree = ttk.Treeview(res_frame, columns=("mark","artist","title","ytquery"),
                                 show="headings", height=12, selectmode="extended")
        self.tree.heading("mark", text="✔"); self.tree.column("mark", width=30, anchor="center")
        self.tree.heading("artist", text="Artista/Banda"); self.tree.column("artist", width=240, anchor="w", stretch=True)
        self.tree.heading("title", text="Música"); self.tree.column("title", width=420, anchor="w", stretch=True)
        self.tree.heading("ytquery", text="Consulta (YouTube)"); self.tree.column("ytquery", width=540, anchor="w", stretch=True)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(res_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.toggle_mark_mb)

        frm_actions_mb = ttk.LabelFrame(cnt_mb, text="Ações (Música)")
        frm_actions_mb.grid(row=1, column=0, sticky="ew", padx=0, pady=(0,0))
        row1 = ttk.Frame(frm_actions_mb); row1.pack(fill="x", pady=2)
        ttk.Button(row1, text="Marcar todos", command=self.mark_all_mb).pack(side="left", padx=4)
        ttk.Button(row1, text="Desmarcar todos", command=self.unmark_all_mb).pack(side="left", padx=4)
        ttk.Separator(row1, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(row1, text="Adicionar MARCADOS → Áudio", command=self.add_marked_mb_to_audio).pack(side="left", padx=4)
        ttk.Button(row1, text="Adicionar MARCADOS → Vídeo", command=self.add_marked_mb_to_video).pack(side="left", padx=4)
        ttk.Separator(row1, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(row1, text="Adicionar SELECIONADOS → Áudio", command=self.add_selected_to_audio).pack(side="left", padx=4)
        ttk.Button(row1, text="Adicionar SELECIONADOS → Vídeo", command=self.add_selected_to_video).pack(side="left", padx=4)
        ttk.Separator(row1, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(row1, text="Limpar", command=lambda: [self.tree.delete(*self.tree.get_children()), self.checked_mb.clear()]).pack(side="left", padx=4)

        tab_general = ttk.Frame(self.nb)
        self.nb.add(tab_general, text="📺 YouTube Pesquisar (Categorias)")

        top_general = ttk.LabelFrame(tab_general, text="Buscar por categoria")
        top_general.pack(fill="x", padx=8, pady=6)
        self.general_query_var = tk.StringVar()
        ttk.Label(top_general, text="Termos:").pack(side="left", padx=(8,4))
        ttk.Entry(top_general, textvariable=self.general_query_var, width=40).pack(side="left", padx=4, pady=6)
        ttk.Label(top_general, text="Categoria:").pack(side="left", padx=(12,4))
        self.general_category_var = tk.StringVar(value=GENERAL_CATEGORIES[0])
        ttk.Combobox(top_general, textvariable=self.general_category_var, values=GENERAL_CATEGORIES, width=22, state="readonly").pack(side="left", padx=4)
        ttk.Label(top_general, text="Resultados:").pack(side="left", padx=(12,4))
        self.general_limit_var = tk.IntVar(value=10)
        tk.Spinbox(top_general, from_=1, to=50, textvariable=self.general_limit_var, width=4).pack(side="left", padx=4)
        ttk.Button(top_general, text="Buscar no YouTube", command=self.search_general).pack(side="left", padx=12)

        pr_gen = ttk.LabelFrame(tab_general, text="Progresso da busca (YouTube)")
        pr_gen.pack(fill="x", padx=8, pady=(2,8))
        self.pg_gen = ttk.Progressbar(pr_gen, mode="indeterminate")
        self.pg_gen.pack(fill="x", padx=8, pady=6)
        self.lbl_gen = ttk.Label(pr_gen, text="Parado")
        self.lbl_gen.pack(fill="x", padx=8, pady=(0,6))

        cnt_gen = ttk.Frame(tab_general)
        cnt_gen.pack(fill="both", expand=True, padx=8, pady=6)
        cnt_gen.grid_rowconfigure(0, weight=1)
        cnt_gen.grid_columnconfigure(0, weight=1)

        res_general = ttk.LabelFrame(cnt_gen, text="Resultados (marque itens ou use 'Marcar todos')")
        res_general.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0,6))
        self.tree_general = ttk.Treeview(res_general, columns=("mark","title","channel","duration","url","ytquery"),
                                         show="headings", height=14, selectmode="extended")
        for col, label, w, anchor in [("mark","✔",34,"center"),("title","Título",520,"w"),("channel","Canal",260,"w"),
                                      ("duration","Duração",90,"center"),("url","URL",380,"w"),("ytquery","Consulta",340,"w")]:
            self.tree_general.heading(col, text=label)
            self.tree_general.column(col, width=w, anchor=anchor, stretch=(col in ("title","channel","url")))
        self.tree_general.pack(side="left", fill="both", expand=True)
        sbg = ttk.Scrollbar(res_general, orient="vertical", command=self.tree_general.yview)
        self.tree_general.configure(yscrollcommand=sbg.set)
        sbg.pack(side="right", fill="y")
        self.tree_general.bind("<Double-1>", self.toggle_mark_gen)

        btns_general = ttk.LabelFrame(cnt_gen, text="Ações (YouTube)")
        btns_general.grid(row=1, column=0, sticky="ew", padx=0, pady=(0,0))
        ttk.Button(btns_general, text="Marcar todos", command=self.mark_all_gen).pack(side="left", padx=4)
        ttk.Button(btns_general, text="Desmarcar todos", command=self.unmark_all_gen).pack(side="left", padx=4)
        ttk.Separator(btns_general, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(btns_general, text="Adicionar MARCADOS → Vídeo (arquivo único)", command=self.add_marked_gen_to_video).pack(side="left", padx=4)
        ttk.Button(btns_general, text="Adicionar MARCADOS → Áudio (arquivo único)", command=self.add_marked_gen_to_audio).pack(side="left", padx=4)
        ttk.Separator(btns_general, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(btns_general, text="Adicionar BUSCA a LISTA → Vídeo", command=self.add_general_search_as_list_video).pack(side="left", padx=12)
        ttk.Button(btns_general, text="Adicionar BUSCA a LISTA → Áudio", command=self.add_general_search_as_list_audio).pack(side="left", padx=4)
        ttk.Separator(btns_general, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(btns_general, text="Limpar", command=lambda: [self.tree_general.delete(*self.tree_general.get_children()), self.checked_gen.clear()]).pack(side="left", padx=12)

        tab_queues = ttk.Frame(self.nb)
        self.nb.add(tab_queues, text="🧺 Filas com TXT e URL (Áudio/Vídeo)")

        # --- Bloco: Adicionar URLs/Lista rapidamente ---
        add_box = ttk.LabelFrame(tab_queues, text="Adicionar URL(s) diretamente")
        add_box.pack(fill="x", padx=8, pady=(8,2))
        row1 = ttk.Frame(add_box); row1.pack(fill="x", padx=6, pady=6)
        ttk.Label(row1, text="URL única:").pack(side="left")
        self.single_url_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.single_url_var, width=70).pack(side="left", padx=6)
        ttk.Button(row1, text="→ Áudio", command=self.add_single_url_audio).pack(side="left", padx=(4,2))
        ttk.Button(row1, text="→ Vídeo", command=self.add_single_url_video).pack(side="left", padx=(2,6))
        ttk.Button(row1, text="Colar da Área de Transferência", command=self.paste_single_from_clipboard).pack(side="left", padx=6)

        row2 = ttk.Frame(add_box); row2.pack(fill="both", padx=6, pady=(0,6))
        ttk.Label(row2, text="Lista (uma por linha; aceita ytsearch / links http/https):").pack(anchor="w")
        self.txt_urls = tk.Text(row2, height=6)
        self.txt_urls.pack(fill="x", expand=True, pady=(4,4))
        btns_list = ttk.Frame(add_box); btns_list.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(btns_list, text="Adicionar lista → Áudio", command=lambda: self.add_list_urls(self.lst_audio)).pack(side="left", padx=4)
        ttk.Button(btns_list, text="Adicionar lista → Vídeo", command=lambda: self.add_list_urls(self.lst_video)).pack(side="left", padx=4)
        ttk.Button(btns_list, text="Colar lista", command=self.paste_list_from_clipboard).pack(side="left", padx=8)
        ttk.Button(btns_list, text="Limpar campo", command=lambda: self.txt_urls.delete("1.0","end")).pack(side="left", padx=4)
        ttk.Separator(tab_queues, orient="horizontal").pack(fill="x", padx=8, pady=(4,6))

        queues_top = ttk.Frame(tab_queues); queues_top.pack(fill="both", expand=True, padx=8, pady=6)
        audio_box = ttk.LabelFrame(queues_top, text="Fila de Áudio (ytsearch/links)")
        video_box = ttk.LabelFrame(queues_top, text="Fila de Vídeo (ytsearch/links)")
        audio_box.pack(side="left", fill="both", expand=True, padx=(0,4))
        video_box.pack(side="left", fill="both", expand=True, padx=(4,0))
        self.lst_audio = tk.Listbox(audio_box); self.lst_audio.pack(fill="both", expand=True, padx=4, pady=4)
        self.lst_video = tk.Listbox(video_box); self.lst_video.pack(fill="both", expand=True, padx=4, pady=4)
        btns_q = ttk.Frame(tab_queues); btns_q.pack(fill="x", padx=8, pady=6)
        ttk.Button(btns_q, text="Remover Selecionados (Áudio)", command=self.remove_audio).pack(side="left", padx=4)
        ttk.Button(btns_q, text="Remover Selecionados (Vídeo)", command=self.remove_video).pack(side="left", padx=4)
        ttk.Button(btns_q, text="Limpar Áudio", command=lambda: self.lst_audio.delete(0,"end")).pack(side="left", padx=4)
        ttk.Button(btns_q, text="Limpar Vídeo", command=lambda: self.lst_video.delete(0,"end")).pack(side="left", padx=4)
        ttk.Button(btns_q, text="Importar lista .txt → Áudio", command=lambda: self.import_txt(self.lst_audio)).pack(side="left", padx=10)
        ttk.Button(btns_q, text="Importar lista .txt → Vídeo", command=lambda: self.import_txt(self.lst_video)).pack(side="left", padx=4)
        ttk.Button(btns_q, text="Exportar Áudio → .txt", command=lambda: self.export_txt(self.lst_audio, "lista_audio.txt")).pack(side="left", padx=10)
        ttk.Button(btns_q, text="Exportar Vídeo → .txt", command=lambda: self.export_txt(self.lst_video, "lista_video.txt")).pack(side="left", padx=4)

        tab_quality = ttk.Frame(self.nb)
        self.nb.add(tab_quality, text="⚙️ Qualidade & Perfis")
        q_audio = ttk.LabelFrame(tab_quality, text="Áudio (MP3)")
        q_video = ttk.LabelFrame(tab_quality, text="Vídeo (MP4/H.264)")
        q_audio.pack(fill="x", padx=8, pady=(10,6))
        q_video.pack(fill="x", padx=8, pady=6)

        ttk.Label(q_audio, text="Bitrate (kbps):").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_audio, textvariable=self.audio_bitrate_k, values=[128,160,192,256,320], width=8, state="readonly").grid(row=0, column=1, padx=4, pady=6, sticky="w")
        ttk.Label(q_audio, text="Amostragem (Hz):").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_audio, textvariable=self.audio_sr, values=[44100,48000], width=10, state="readonly").grid(row=0, column=3, padx=4, pady=6, sticky="w")
        ttk.Label(q_audio, text="Canais:").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_audio, textvariable=self.audio_channels, values=[1,2], width=6, state="readonly").grid(row=0, column=5, padx=4, pady=6, sticky="w")

        ttk.Label(q_video, text="Modo:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_mode, values=["compat","reencode"], width=10, state="readonly").grid(row=0, column=1, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="Codec:").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_codec, values=["h264"], width=10, state="readonly").grid(row=0, column=3, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="Altura máx.:").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_max_h, values=[360,480,720], width=10, state="readonly").grid(row=1, column=1, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="FPS máx.:").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_fps, values=[24,25,30], width=10, state="readonly").grid(row=1, column=3, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="CRF (reencode):").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_crf, values=list(range(18,29)), width=10, state="readonly").grid(row=2, column=1, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="Preset (reencode):").grid(row=2, column=2, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_preset, values=["ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow"], width=12, state="readonly").grid(row=2, column=3, padx=4, pady=6, sticky="w")
        ttk.Label(q_video, text="AAC (kbps):").grid(row=2, column=4, padx=6, pady=6, sticky="w")
        ttk.Combobox(q_video, textvariable=self.video_audio_k, values=[128,160,192,256], width=10, state="readonly").grid(row=2, column=5, padx=4, pady=6, sticky="w")

        profile_frame = ttk.LabelFrame(tab_quality, text="Perfis rápidos")
        profile_frame.pack(fill="x", padx=8, pady=(6,10))
        ttk.Button(profile_frame, text="Aplicar perfil • Pioneer AVIC", command=self.apply_pioneer_profile).pack(side="left", padx=8, pady=6)
        ttk.Label(profile_frame, text="(480p/30 H.264 + AAC 192 kbps; MP3 320k/44.1kHz/2ch, modo compat)").pack(side="left", padx=6)

        actions = ttk.LabelFrame(tab_quality, text="Ações ao término")
        actions.pack(fill="x", padx=8, pady=(0,10))
        ttk.Checkbutton(actions, text="Abrir pasta automaticamente ao terminar", variable=self.auto_open_folder).pack(side="left", padx=8, pady=6)

        self.nb.add(self._build_donation_tab(self.nb), text="❤️ Doações (PIX/PayPal)")

        tab_run = ttk.Frame(self.nb)
        self.nb.add(tab_run, text="⬇️ Downloads & Status")
        top_run = ttk.Frame(tab_run); top_run.pack(fill="x", padx=8, pady=6)
        ttk.Button(top_run, text="Iniciar Download Áudio", command=self.start_audio).pack(side="left", padx=4)
        ttk.Button(top_run, text="Iniciar Download Vídeo", command=self.start_video).pack(side="left", padx=4)
        ttk.Button(top_run, text="Parar", command=self.stop_worker).pack(side="left", padx=12)
        ttk.Button(top_run, text="Abrir pasta Áudio", command=self.open_audio_folder).pack(side="left", padx=12)
        ttk.Button(top_run, text="Abrir pasta Vídeo", command=self.open_video_folder).pack(side="left", padx=6)
        ttk.Button(top_run, text="Abrir pasta de Logs", command=self.open_logs).pack(side="left", padx=12)
        ttk.Button(top_run, text="Reproduzir último arquivo (player interno)", command=self.play_last_downloaded).pack(side="left", padx=12)

        prog_frame = ttk.LabelFrame(tab_run, text="Progresso de Download")
        prog_frame.pack(fill="x", padx=8, pady=6)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill="x", padx=8, pady=6)
        self.lbl_status = ttk.Label(prog_frame, text="Aguardando…")
        self.lbl_status.pack(fill="x", padx=8, pady=(0,8))

        log_frame = ttk.LabelFrame(tab_run, text="Log ao vivo")
        log_frame.pack(fill="both", expand=True, padx=8, pady=6)
        self.txt_log = tk.Text(log_frame, height=12, state="disabled")
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")

    def _build_donation_tab(self, nb):
        tab_donate = ttk.Frame(nb)
        donate_frame = ttk.LabelFrame(tab_donate, text="Contribua para o projeto ❤️")
        donate_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(donate_frame, text="Qualquer valor ajuda a manter e evoluir a ferramenta. Obrigado!").pack(anchor="w", padx=8, pady=(6,2))
        pix_box = ttk.LabelFrame(tab_donate, text="PIX (chave e-mail)")
        pix_box.pack(fill="x", padx=10, pady=(4,10))
        ttk.Label(pix_box, text="Chave PIX: sfbarboza82@hotmail.com").pack(anchor="w", padx=8, pady=6)
        ttk.Button(pix_box, text="Copiar chave PIX", command=lambda: self.copy_to_clipboard("sfbarboza82@hotmail.com", "Chave PIX copiada!")).pack(anchor="w", padx=8, pady=(0,8))
        pp_box = ttk.LabelFrame(tab_donate, text="PayPal")
        pp_box.pack(fill="x", padx=10, pady=(0,10))
        ttk.Label(pp_box, text="E-mail do PayPal: sfbarboza82@hotmail.com").pack(anchor="w", padx=8, pady=6)
        btns_pp = ttk.Frame(pp_box); btns_pp.pack(fill="x", padx=6, pady=(0,10))
        ttk.Button(btns_pp, text="Copiar e-mail do PayPal", command=lambda: self.copy_to_clipboard("sfbarboza82@hotmail.com", "E-mail do PayPal copiado!")).pack(side="left", padx=6)
        ttk.Button(btns_pp, text="Abrir PayPal.com", command=lambda: webbrowser.open("https://www.paypal.com/")).pack(side="left", padx=6)
        ttk.Label(tab_donate, text="No PayPal, escolha “Enviar dinheiro” e cole o e-mail acima.").pack(anchor="w", padx=12, pady=(0,10))
        return tab_donate

    def copy_to_clipboard(self, text, msg_ok="Copiado!"):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
            messagebox.showinfo("Copiado", msg_ok)
        except Exception as e:
            messagebox.showerror("Erro", "Não foi possível copiar.\n%s" % e)

    def browse_audio_out(self):
        p = filedialog.askdirectory(title="Selecionar pasta de saída (Áudio)")
        if p:
            self.audio_out.set(p)
    def browse_video_out(self):
        p = filedialog.askdirectory(title="Selecionar pasta de saída (Vídeo)")
        if p:
            self.video_out.set(p)
    def browse_log_dir(self):
        p = filedialog.askdirectory(title="Selecionar pasta de Logs")
        if p:
            self.log_dir.set(p)
            self.logger, self.log_path = setup_logger(self.log_dir.get(), self.txt_log, name="downloadsfb")
            self.logger.info("Pasta de logs alterada para %s", self.log_dir.get())

    def apply_pioneer_profile(self):
        self.audio_bitrate_k.set(320)
        self.audio_sr.set(44100)
        self.audio_channels.set(2)
        self.video_mode.set("compat")
        self.video_codec.set("h264")
        self.video_max_h.set(480)
        self.video_fps.set(30)
        self.video_crf.set(23)
        self.video_preset.set("medium")
        self.video_audio_k.set(192)
        self.logger.info("Perfil 'Pioneer AVIC' aplicado.")

    def toggle_mark_mb(self, e=None):
        iid = self.tree.focus()
        if not iid:
            return
        cur = self.tree.set(iid, "mark")
        new = CHECKED if cur != CHECKED else UNCHECKED
        self.tree.set(iid, "mark", new)
        if new == CHECKED:
            self.checked_mb.add(iid)
        else:
            self.checked_mb.discard(iid)

    def mark_all_mb(self):
        for iid in self.tree.get_children():
            self.tree.set(iid, "mark", CHECKED)
            self.checked_mb.add(iid)

    def unmark_all_mb(self):
        for iid in self.tree.get_children():
            self.tree.set(iid, "mark", UNCHECKED)
        self.checked_mb.clear()

    def toggle_mark_gen(self, e=None):
        iid = self.tree_general.focus()
        if not iid:
            return
        cur = self.tree_general.set(iid, "mark")
        new = CHECKED if cur != CHECKED else UNCHECKED
        self.tree_general.set(iid, "mark", new)
        if new == CHECKED:
            self.checked_gen.add(iid)
        else:
            self.checked_gen.discard(iid)

    def mark_all_gen(self):
        for iid in self.tree_general.get_children():
            self.tree_general.set(iid, "mark", CHECKED)
            self.checked_gen.add(iid)

    def unmark_all_gen(self):
        for iid in self.tree_general.get_children():
            self.tree_general.set(iid, "mark", UNCHECKED)
        self.checked_gen.clear()

    def _insert_mb_pairs(self, pairs):
        for artist, title in pairs:
            ytq = "ytsearch1:%s - %s official" % (artist, title)
            self.tree.insert("", "end", values=(UNCHECKED, artist, title, ytq))
        self.logger.info("%s resultados adicionados (MusicBrainz).", len(pairs))

    def search_by_genre(self):
        genre = self.genre_var.get().strip()
        if not genre:
            messagebox.showwarning("Atenção","Informe um gênero (ex.: grunge)")
            return
        self.logger.info("Buscando artistas por gênero: %s", genre)
        self.pg_mb.start(10); self.lbl_mb.config(text="Buscando artistas…")
        def _task():
            try:
                arts = mb_search_artists_by_genre(genre, limit=int(self.mb_limit_artists.get() or 10))
                all_pairs = []
                for i, a in enumerate(arts, start=1):
                    self.lbl_mb.after(0, lambda i=i, a=a: self.lbl_mb.config(text="Coletando músicas de %s (%d/%d)…" % (a, i, len(arts))))
                    pairs = mb_search_recordings_by_artist(a, limit=int(self.mb_limit_tracks.get() or 3))
                    all_pairs.extend(pairs); time.sleep(0.5)
                self.after(0, lambda: self._insert_mb_pairs(all_pairs))
            except Exception as e:
                try:
                    self.logger.exception("Busca por gênero falhou: %s", e)
                except Exception:
                    pass
            finally:
                self.pg_mb.stop(); self.lbl_mb.config(text="Parado")
        threading.Thread(target=_task, daemon=True).start()

    def search_by_artist(self):
        artist = self.artist_var.get().strip()
        if not artist:
            messagebox.showwarning("Atenção","Informe um artista/banda")
            return
        self.logger.info("Buscando músicas do artista: %s", artist)
        self.pg_mb.start(10); self.lbl_mb.config(text="Buscando…")
        def _task():
            try:
                recs = mb_search_recordings_by_artist(artist, limit=int(self.mb_limit_tracks.get() or 10))
                self.after(0, lambda: self._insert_mb_pairs(recs))
            except Exception as e:
                try:
                    self.logger.exception("Busca por artista falhou: %s", e)
                except Exception:
                    pass
            finally:
                self.pg_mb.stop(); self.lbl_mb.config(text="Parado")
        threading.Thread(target=_task, daemon=True).start()

    def search_by_title(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Atenção","Informe o nome da música")
            return
        self.logger.info("Buscando por nome de música: %s", title)
        self.pg_mb.start(10); self.lbl_mb.config(text="Buscando…")
        def _task():
            try:
                recs = mb_search_recordings_by_title(title, limit=int(self.mb_limit_tracks.get() or 12))
                self.after(0, lambda: self._insert_mb_pairs(recs))
            except Exception as e:
                try:
                    self.logger.exception("Busca por título falhou: %s", e)
                except Exception:
                    pass
            finally:
                self.pg_mb.stop(); self.lbl_mb.config(text="Parado")
        threading.Thread(target=_task, daemon=True).start()

    def search_general(self):
        terms = self.general_query_var.get().strip()
        cat = self.general_category_var.get().strip()
        limit = max(1, min(int(self.general_limit_var.get() or 10), 50))
        if not terms:
            messagebox.showwarning("Atenção","Informe termos (ex.: história do rock)")
            return
        extras = CATEGORY_EXPANSIONS.get(cat, [])
        q = " ".join([terms] + extras).strip()
        self.last_general_query = "ytsearch%d:%s official" % (limit, q)
        self.logger.info("Preparando busca geral: %s", self.last_general_query)
        self.pg_gen.start(10); self.lbl_gen.config(text="Consultando YouTube…")
        def _task():
            results = search_youtube(self.logger, q + " official", limit=limit)
            def _insert():
                self.tree_general.delete(*self.tree_general.get_children())
                self.checked_gen.clear()
                for row in results:
                    self.tree_general.insert("", "end", values=(UNCHECKED,) + tuple(row))
                self.logger.info("%s resultados gerais adicionados.", len(results))
            self.after(0, _insert)
            self.pg_gen.stop(); self.lbl_gen.config(text="Parado")
        threading.Thread(target=_task, daemon=True).start()

    def _show_added_message(self, titulo, items):
        if not items:
            return
        n = len(items)
        preview = "\n".join("• " + s for s in items[:20])
        suffix = "" if n <= 20 else "\n… e mais %d itens." % (n - 20)
        messagebox.showinfo(titulo, "Foram adicionados %d itens:\n\n%s%s" % (n, preview, suffix))

    def add_marked_mb_to_audio(self):
        added = []
        for iid in self.tree.get_children():
            if self.tree.set(iid, "mark") == CHECKED:
                q = self.tree.set(iid, "ytquery")
                self.lst_audio.insert("end", q); added.append(q)
        self.logger.info("%s itens MARCADOS → Áudio.", len(added))
        self._show_added_message("Itens → Áudio (marcados)", added)

    def add_marked_mb_to_video(self):
        added = []
        for iid in self.tree.get_children():
            if self.tree.set(iid, "mark") == CHECKED:
                q = self.tree.set(iid, "ytquery").replace("official","official video")
                self.lst_video.insert("end", q); added.append(q)
        self.logger.info("%s itens MARCADOS → Vídeo.", len(added))
        self._show_added_message("Itens → Vídeo (marcados)", added)

    def add_selected_to_audio(self):
        sel = self.tree.selection(); added = []
        for iid in sel:
            q = self.tree.set(iid, "ytquery")
            self.lst_audio.insert("end", q); added.append(q)
        self.logger.info("%s itens SELECIONADOS → Áudio.", len(added))
        self._show_added_message("Itens → Áudio (selecionados)", added)

    def add_selected_to_video(self):
        sel = self.tree.selection(); added = []
        for iid in sel:
            q = self.tree.set(iid, "ytquery").replace("official","official video")
            self.lst_video.insert("end", q); added.append(q)
        self.logger.info("%s itens SELECIONADOS → Vídeo.", len(added))
        self._show_added_message("Itens → Vídeo (selecionados)", added)

    def add_marked_gen_to_video(self):
        added = []
        for iid in self.tree_general.get_children():
            if self.tree_general.set(iid, "mark") == CHECKED:
                url = self.tree_general.set(iid, "url")
                if url:
                    self.lst_video.insert("end", url); added.append(url)
        self.logger.info("%s itens MARCADOS → Vídeo.", len(added))
        self._show_added_message("Itens → Vídeo (marcados - geral)", added)

    def add_marked_gen_to_audio(self):
        added = []
        for iid in self.tree_general.get_children():
            if self.tree_general.set(iid, "mark") == CHECKED:
                url = self.tree_general.set(iid, "url")
                if url:
                    self.lst_audio.insert("end", url); added.append(url)
        self.logger.info("%s itens MARCADOS → Áudio.", len(added))
        self._show_added_message("Itens → Áudio (marcados - geral)", added)

    def add_general_search_as_list_video(self):
        if not self.last_general_query:
            messagebox.showinfo("Lista","Faça uma busca geral antes")
            return
        self.lst_video.insert("end", self.last_general_query)
        self._show_added_message("Busca como lista → Vídeo", [self.last_general_query])

    def add_general_search_as_list_audio(self):
        if not self.last_general_query:
            messagebox.showinfo("Lista","Faça uma busca geral antes")
            return
        self.lst_audio.insert("end", self.last_general_query)
        self._show_added_message("Busca como lista → Áudio", [self.last_general_query])

    def remove_audio(self):
        for i in reversed(self.lst_audio.curselection()):
            self.lst_audio.delete(i)
        self.logger.info("Itens removidos da fila de Áudio.")

    def remove_video(self):
        for i in reversed(self.lst_video.curselection()):
            self.lst_video.delete(i)
        self.logger.info("Itens removidos da fila de Vídeo.")

    def import_txt(self, listbox):
        p = filedialog.askopenfilename(title="Selecionar lista .txt", filetypes=[("Texto","*.txt")])
        if not p:
            return
        cnt = 0
        added = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                q = line.strip()
                if q:
                    listbox.insert("end", q); cnt += 1; added.append(q)
        self.logger.info("%s itens importados de %s", cnt, os.path.basename(p))
        self._show_added_message("Itens importados de %s" % os.path.basename(p), added)
    def _normalize_lines(self, text: str):
        parts = []
        for raw in text.replace("\r","\n").split("\n"):
            raw = raw.strip()
            if not raw:
                continue
            import re as _re
            for tok in _re.split(r"[;,]", raw):
                tok = tok.strip()
                if tok:
                    parts.append(tok)
        return parts

    def add_single_url_audio(self):
        s = (self.single_url_var.get() or "").strip()
        if not s:
            messagebox.showwarning("Atenção","Cole uma URL ou consulta (ytsearch…)")
            return
        self.lst_audio.insert("end", s)
        self.logger.info("Adicionado (Áudio): %s", s)
        messagebox.showinfo("Adicionado","1 item adicionado à fila de Áudio.")

    def add_single_url_video(self):
        s = (self.single_url_var.get() or "").strip()
        if not s:
            messagebox.showwarning("Atenção","Cole uma URL ou consulta (ytsearch…)")
            return
        self.lst_video.insert("end", s)
        self.logger.info("Adicionado (Vídeo): %s", s)
        messagebox.showinfo("Adicionado","1 item adicionado à fila de Vídeo.")

    def paste_single_from_clipboard(self):
        try:
            s = self.clipboard_get().strip()
        except Exception:
            s = ""
        if not s:
            messagebox.showwarning("Atenção","A área de transferência está vazia.")
            return
        self.single_url_var.set(s)

    def add_list_urls(self, listbox):
        text = self.txt_urls.get("1.0","end")
        items = self._normalize_lines(text)
        if not items:
            messagebox.showwarning("Atenção","Cole uma lista (uma por linha).")
            return
        for it in items:
            listbox.insert("end", it)
        self.logger.info("%s itens adicionados à fila.", len(items))
        try:
            self._show_added_message("Lista adicionada", items)
        except Exception:
            pass

    def paste_list_from_clipboard(self):
        try:
            s = self.clipboard_get()
        except Exception:
            s = ""
        if not s:
            messagebox.showwarning("Atenção","A área de transferência está vazia.")
            return
        self.txt_urls.delete("1.0","end")
        self.txt_urls.insert("1.0", s)

    def export_txt(self, listbox, default_name):
        try:
            p = filedialog.asksaveasfilename(title="Salvar lista como .txt",
                                             defaultextension=".txt",
                                             initialfile=default_name,
                                             filetypes=[("Texto","*.txt")])
            if not p:
                return
            with open(p, "w", encoding="utf-8") as f:
                for i in range(listbox.size()):
                    f.write((listbox.get(i) or "").strip() + "\n")
            self.logger.info("Lista exportada: %s", os.path.basename(p))
            messagebox.showinfo("Exportado", f"Lista salva em:\n{p}")
        except Exception as e:
            messagebox.showerror("Erro","Falha ao salvar lista:\n%s" % e)


    def _prepare_removable_destination(self, mode):
        try:
            drives = storage.list_removable_drives()
        except Exception as e:
            self.logger.warning("Falha ao listar dispositivos removíveis: %s", e)
            drives = []
        if not drives:
            return None
        if len(drives) == 1:
            d = drives[0]
        else:
            win = tk.Toplevel(self)
            win.title("Selecionar dispositivo removível")
            ttk.Label(win, text="Selecione o dispositivo onde deseja salvar os arquivos:").pack(padx=10, pady=8)
            var = tk.StringVar(value=f"{drives[0]['letter']}|{drives[0]['label']}|{drives[0]['fs']}")
            for dopt in drives:
                txt = f"{dopt['letter']} ({dopt['label'] or 'Sem rótulo'}) — {dopt['fs'] or '?'}"
                ttk.Radiobutton(win, text=txt, variable=var,
                                value=f"{dopt['letter']}|{dopt['label']}|{dopt['fs']}").pack(anchor="w", padx=12, pady=2)
            chosen = {"ok": False}
            def _ok(): chosen["ok"] = True; win.destroy()
            def _cancel(): chosen["ok"] = False; win.destroy()
            btns = ttk.Frame(win); btns.pack(fill="x", padx=10, pady=8)
            ttk.Button(btns, text="Usar", command=_ok).pack(side="left", padx=6)
            ttk.Button(btns, text="Cancelar", command=_cancel).pack(side="left", padx=6)
            win.transient(self); win.grab_set(); self.wait_window(win)
            if not chosen["ok"]:
                return None
            letter = (var.get().split("|", 1)[0]).rstrip(":")
            d = next((x for x in drives if x["letter"].startswith(letter)), drives[0])

        if not messagebox.askyesno(
            "Dispositivo detectado",
            f"Detectei o dispositivo {d['letter']} ({d.get('label') or 'Sem rótulo'}) — {d.get('fs') or '?'}.\n\nDeseja salvar os arquivos nesse dispositivo?"
        ):
            return None

        root = d["mount"]
        fs = d.get("fs") or storage.get_fs_type(root)
        if not storage.is_fat32(fs):
            if messagebox.askyesno(
                "Formato não compatível",
                f"O dispositivo {d['letter']} está em '{fs or '?'}'.\nDeseja FORMATAR em FAT32 agora?\n\n⚠️ ATENÇÃO: isso APAGA TODOS os dados do dispositivo."
            ):
                ok, out = storage.format_drive_fat32(d["letter"].rstrip(":"), label="DOWNLOADSFB")
                self.logger.info("Format FAT32 retorno=%s", ok)
                if not ok:
                    messagebox.showerror(
                        "Falha ao formatar",
                        "Não foi possível formatar o dispositivo.\nTente executar como Administrador ou formate manualmente.\n\nSaída:\n%s" % (out or "")
                    )
                    return None
            else:
                messagebox.showwarning("Atenção", "Seguindo sem formatar. Se o aparelho não reconhecer, tente formatar em FAT32.")
        else:
            if messagebox.askyesno(
                "Limpar conteúdo",
                f"O dispositivo {d['letter']} já está em FAT32.\nDeseja APAGAR TODOS os arquivos antes de adicionar os novos?"
            ):
                ok, errs = storage.clear_drive_contents(root, skip_system=True)
                if not ok and errs:
                    self.logger.warning("Erros ao limpar: %s", errs[:5])

        target_audio = os.path.join(root, "DownloadSFB-Audio")
        target_video = os.path.join(root, "DownloadSFB-Video")
        try:
            os.makedirs(target_audio, exist_ok=True)
            os.makedirs(target_video, exist_ok=True)
        except Exception as e:
            self.logger.error("Falha ao criar pastas no dispositivo: %s", e)
            return None

        if mode == "audio":
            self.audio_out.set(target_audio)
            return target_audio
        else:
            self.video_out.set(target_video)
            return target_video

    def set_progress(self, pct, speed, eta, stage, title):
        try:
            val = max(0.0, min(100.0, pct))
            self.progress["value"] = val
            spd = ("%.2f MB/s" % (speed/1024.0/1024.0)) if speed else "-"
            eta_s = ("%ds" % int(eta)) if eta else "-"
            self.lbl_status.configure(text="%s: %5.1f%% | %s | ETA %s | %s" % (stage, pct, spd, eta_s, (title or "")[:80]))
            self.update_idletasks()
        except Exception:
            pass

    def _quality_dict(self):
        return {
            "audio_bitrate_k": self.audio_bitrate_k.get(),
            "audio_sr": self.audio_sr.get(),
            "audio_channels": self.audio_channels.get(),
            "video_mode": self.video_mode.get(),
            "video_codec": self.video_codec.get(),
            "video_max_h": self.video_max_h.get(),
            "video_fps": self.video_fps.get(),
            "video_crf": self.video_crf.get(),
            "video_preset": self.video_preset.get(),
            "video_audio_k": self.video_audio_k.get(),
        }

    def open_folder(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro", "Não foi possível abrir a pasta:\n%s\n\n%s" % (path, e))

    def open_audio_folder(self):
        self.open_folder(self.audio_out.get())

    def open_video_folder(self):
        self.open_folder(self.video_out.get())

    def open_logs(self):
        self.open_folder(self.log_dir.get())

    def _on_worker_done(self, mode, files, ok, err, outdir):
        def _show():
            if files:
                try:
                    self.last_downloaded_files.extend(files)
                except Exception:
                    pass
                preview = "\n".join("• " + (os.path.relpath(f, outdir) if f.startswith(outdir) else os.path.basename(f)) for f in files[:20])
                suffix = "" if len(files) <= 20 else "\n… e mais %d arquivos." % (len(files) - 20)
                messagebox.showinfo("Concluído — %s" % mode.upper(),
                                    "Sucesso: %d | Falhas: %d\nPasta: %s\n\nArquivos baixados (%d):\n\n%s%s"
                                    % (ok, err, outdir, len(files), preview, suffix))
            else:
                messagebox.showinfo("Concluído — %s" % mode.upper(), "Sucesso: %d | Falhas: %d\nNenhum arquivo listado." % (ok, err))
            try:
                if self.auto_open_folder.get() or messagebox.askyesno("Concluído — %s" % mode.upper(), "Deseja abrir a pasta dos arquivos agora?"):
                    self.open_folder(outdir)
            except Exception:
                pass
        self.after(0, _show)

    def play_last_downloaded(self):
        if not self.last_downloaded_files:
            messagebox.showinfo("Player interno","Ainda não há arquivos nesta sessão.")
            return
        exe = bundled_ffplay_path()
        if not os.path.isfile(exe):
            messagebox.showerror("Player interno","ffplay.exe não encontrado no pacote.")
            return
        path = self.last_downloaded_files[-1]
        args = [exe, "-autoexit", path]
        ext = os.path.splitext(path)[1].lower()
        if ext in (".mp3",".m4a",".aac",".wav",".flac",".ogg"):
            args = [exe, "-autoexit", "-nodisp", path]
        try:
            subprocess.Popen(args)
        except Exception as e:
            messagebox.showerror("Player interno", "Falha ao iniciar player interno:\n%s" % e)

    def start_audio(self):
        if getattr(self,"worker",None) and self.worker.is_alive():
            messagebox.showinfo("Execução","Já existe uma execução em andamento.")
            return
        items = [self.lst_audio.get(i) for i in range(self.lst_audio.size())]
        if not items:
            messagebox.showwarning("Fila vazia","Adicione itens à fila de Áudio.")
            return
        dest = self._prepare_removable_destination("audio") or self.audio_out.get()
        self.logger.info("Iniciando Áudio com %s itens.", len(items))
        self.worker = DownloadWorker("audio", items, dest, self.logger, self.set_progress, self._quality_dict(), self._on_worker_done)
        self.worker.start()

    def start_video(self):
        if getattr(self,"worker",None) and self.worker.is_alive():
            messagebox.showinfo("Execução","Já existe uma execução em andamento.")
            return
        items = [self.lst_video.get(i) for i in range(self.lst_video.size())]
        if not items:
            messagebox.showwarning("Fila vazia","Adicione itens à fila de Vídeo.")
            return
        dest = self._prepare_removable_destination("video") or self.video_out.get()
        self.logger.info("Iniciando Vídeo com %s itens.", len(items))
        self.worker = DownloadWorker("video", items, dest, self.logger, self.set_progress, self._quality_dict(), self._on_worker_done)
        self.worker.start()

    def stop_worker(self):
        if getattr(self,"worker",None) and self.worker.is_alive():
            self.logger.info("Solicitando parada…")
            self.worker.stop()
        else:
            self.logger.info("Nenhuma execução ativa.")

def run_app():
    app = App()
    app.mainloop()
