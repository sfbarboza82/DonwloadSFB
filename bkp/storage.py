# -*- coding: utf-8 -*-
"""
Detecção de dispositivos removíveis (pendrive/SD), checagem FAT32,
formatar (AVISO: apaga tudo!), e limpeza do conteúdo.
"""
import os, sys, ctypes, subprocess, shutil, string

DRIVE_REMOVABLE = 2

def _is_windows():
    return os.name == "nt"

def list_removable_drives():
    drives = []
    if not _is_windows():
        return drives
    GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
    GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        dtype = GetDriveTypeW(ctypes.c_wchar_p(root))
        if dtype == DRIVE_REMOVABLE:
            vol_name_buf = ctypes.create_unicode_buffer(256)
            fs_name_buf = ctypes.create_unicode_buffer(256)
            serial_num = ctypes.c_uint(0)
            max_comp_name_len = ctypes.c_uint(0)
            file_sys_flags = ctypes.c_uint(0)
            ok = GetVolumeInformationW(
                ctypes.c_wchar_p(root),
                vol_name_buf, ctypes.sizeof(vol_name_buf),
                ctypes.byref(serial_num),
                ctypes.byref(max_comp_name_len),
                ctypes.byref(file_sys_flags),
                fs_name_buf, ctypes.sizeof(fs_name_buf)
            )
            label = vol_name_buf.value if ok else ""
            fs = fs_name_buf.value if ok else ""
            drives.append({"letter": f"{letter}:", "mount": root, "label": label, "fs": fs, "type": dtype})
    return drives

def get_fs_type(path_root):
    if not _is_windows():
        return ""
    GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
    vol_name_buf = ctypes.create_unicode_buffer(256)
    fs_name_buf = ctypes.create_unicode_buffer(256)
    serial_num = ctypes.c_uint(0)
    max_comp_name_len = ctypes.c_uint(0)
    file_sys_flags = ctypes.c_uint(0)
    ok = GetVolumeInformationW(
        ctypes.c_wchar_p(path_root),
        vol_name_buf, ctypes.sizeof(vol_name_buf),
        ctypes.byref(serial_num),
        ctypes.byref(max_comp_name_len),
        ctypes.byref(file_sys_flags),
        fs_name_buf, ctypes.sizeof(fs_name_buf)
    )
    return fs_name_buf.value if ok else ""

def is_fat32(fs_name):
    return (fs_name or "").upper() == "FAT32"

def format_drive_fat32(letter, label="DOWNLOADSFB", quick=True, timeout=900):
    if not _is_windows():
        return False, "Formato suportado apenas no Windows."
    drive = f"{letter}:" if len(letter) == 1 else letter.rstrip("\\")
    args = [
        "cmd.exe", "/c",
        f'echo Y| format {drive} /FS:FAT32 {" /Q" if quick else ""} /V:{label} /Y'
    ]
    try:
        proc = subprocess.Popen(" ".join(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out, _ = proc.communicate(timeout=timeout)
        txt = out.decode("utf-8", errors="ignore")
        ok = proc.returncode == 0 or ("Format complete" in txt or "A formatação foi concluída" in txt)
        return ok, txt
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "Timeout ao formatar (para >32GB o FAT32 nativo pode falhar)."
    except Exception as e:
        return False, str(e)

def clear_drive_contents(root, skip_system=True):
    errs = []
    try:
        for name in os.listdir(root):
            if skip_system and name.lower() in ("system volume information", "$recycle.bin"):
                continue
            p = os.path.join(root, name)
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    try:
                        os.remove(p)
                    except Exception:
                        shutil.rmtree(p, ignore_errors=True)
            except Exception as e:
                errs.append(f"{name}: {e}")
        return len(errs) == 0, errs
    except Exception as e:
        errs.append(str(e))
        return False, errs
