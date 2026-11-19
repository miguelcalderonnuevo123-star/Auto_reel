# -*- coding: utf-8 -*-
"""
AUTO_REEL.py — pega el link y hace todo.

Uso rapido (edita solo el bloque CONFIG de abajo):

    URL   = "https://www.tiktok.com/@usuario/video/123456789"
    SERIE = "LA TRENZA"
    PARTE = 7          # 1 = primera parte (sin "parte N" en el nombre)

Tambien acepta argumentos:

    python AUTO_REEL.py "URL" "SERIE" [PARTE]

Hace: descarga (con cookies si hacen falta) -> mide duracion ->
render 1080x1920 con hook + CTA + whoosh + loudnorm -> guarda en
Reels_Listos con el nombre final. Sin renombrar a mano.
"""

import os
import re
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
#   CONFIG — cambia solo esto
# ============================================================

URL = ""
SERIE = ""
PARTE = 1
HOOK = ""  # vacio = usa SERIE. Usa "|" para dos lineas: "ME HUMILLARON|POR POBRE"
CTA = "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA"

# ============================================================

import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(BASE, "refs")
OUT_DIR = r"C:\Users\piade\Desktop\Reels_Listos" if os.name == "nt" and os.path.exists(r"C:\Users\piade\Desktop") else os.path.join(BASE, "Reels_Listos")
COOKIES = os.path.join(REFS, "cookies.txt")

_WHOOSH_WIN = r"C:\Users\piade\.cache\music\pixabay2.mp3"
WHOOSH = _WHOOSH_WIN if os.path.exists(_WHOOSH_WIN) else os.path.join(BASE, "assets", "pixabay2.mp3")

def _resolver_ffmpeg():
    win_bin = r"C:\Users\piade\AppData\Local\Programs\Python311\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
    if os.path.exists(win_bin):
        return win_bin
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = _resolver_ffmpeg()

if os.name == "nt" and os.path.exists(r"C:\Windows\Fonts\arialbd.ttf"):
    FONT = "C\\:/Windows/Fonts/arialbd.ttf"
else:
    FONT = os.path.join(BASE, "assets", "arialbd.ttf").replace("\\", "/").replace(":", "\\:")


def get_font_file(font_name="arialbd.ttf"):
    """Resuelve la ruta para ffmpeg drawtext priorizando assets/ para compatibilidad con Linux y Windows."""
    if not font_name:
        font_name = "arialbd.ttf"
    p_assets = os.path.join(BASE, "assets", font_name)
    if os.path.exists(p_assets):
        return p_assets.replace("\\", "/").replace(":", "\\:")
    if os.name == "nt":
        p_win = os.path.join(r"C:\Windows\Fonts", font_name)
        if os.path.exists(p_win):
            return p_win.replace("\\", "/").replace(":", "\\:")
    return FONT

TARGET_W, TARGET_H = 1080, 1920
HOOK_FS = 65
CTA_FS = 70


def run(cmd, timeout=None):
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def run_ff(cmd, timeout=180):
    """ffmpeg con salida a archivo temporal (evita bloqueos por pipe lleno) y timeout de seguridad."""
    tmp = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False,
                                      encoding="utf-8", errors="replace")
    p = subprocess.Popen(cmd, stdout=tmp, stderr=subprocess.STDOUT)
    t0 = time.time()
    timed_out = False
    ticks = 0
    while p.poll() is None:
        if timeout and (time.time() - t0) > timeout:
            timed_out = True
            try:
                p.kill()
            except Exception:
                pass
            break
        time.sleep(0.15)
        ticks += 1
        if ticks % 7 == 0:
            print(".", end="", flush=True)
    print("", flush=True)
    tmp.close()
    out = ""
    try:
        with open(tmp.name, encoding="utf-8", errors="replace") as fh:
            out = fh.read()
    except Exception:
        pass
    try:
        os.remove(tmp.name)
    except Exception:
        pass
    if timed_out:
        return 124, out + "\n[ERROR] FFmpeg superó el tiempo límite de seguridad (180s)."
    return p.returncode, out


def slug_from_url(url, vid_id=None):
    if vid_id and str(vid_id).strip():
        clean_id = re.sub(r"[^A-Za-z0-9_-]", "", str(vid_id).strip())
        if clean_id:
            return "tt_" + clean_id
    m = re.search(r"/video/(\d+)", url or "")
    if m:
        return "tt_" + m.group(1)
    m_short = re.search(r"tiktok\.com/(?:t/)?([A-Za-z0-9_-]{6,})", url or "")
    if m_short:
        return "tt_" + m_short.group(1)
    return "tt_" + str(int(time.time()))


def descargar_respaldo_tikwm(url, dest):
    """
    Motor de respaldo (TikWM API) para descargar el MP4 en HD sin marca de agua
    cuando yt-dlp falla en la nube (por ejemplo IP bloqueada con 403 o video sensible).
    """
    import json
    import urllib.parse
    import urllib.request

    print("  Probando motor de respaldo 2 (TikWM HD sin marca de agua)...")
    try:
        api_url = "https://www.tikwm.com/api/"
        data = urllib.parse.urlencode({"url": url, "hd": "1"}).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8", errors="ignore"))

        info = res.get("data") or {}
        play_url = info.get("hdplay") or info.get("play") or info.get("wmplay")
        if not play_url:
            return None
        if play_url.startswith("/"):
            play_url = "https://www.tikwm.com" + play_url

        req_vid = urllib.request.Request(
            play_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req_vid, timeout=90) as r_vid, open(dest, "wb") as f_out:
            while True:
                chunk = r_vid.read(65536)
                if not chunk:
                    break
                f_out.write(chunk)

        if os.path.exists(dest) and os.path.getsize(dest) > 100000:
            mb = os.path.getsize(dest) / 1024 / 1024
            print(f"  Descargado con TikWM: {os.path.basename(dest)} ({mb:.1f} MB)")
            return dest
    except Exception as e:
        print(f"  Aviso en motor TikWM: {e}")
    return None


def descargar_respaldo_espejo(url, dest):
    """
    Segundo motor espejo de respaldo (LoveTik / TiklyDown) sin marca de agua
    si tanto yt-dlp como TikWM fallan o sufren límite temporal de peticiones.
    """
    import json
    import urllib.parse
    import urllib.request

    print("  Probando motor de respaldo 3 (Servidor Espejo HD sin marca de agua)...")
    espejos = [
        (
            "LoveTik",
            "https://lovetik.com/api/ajax/search",
            urllib.parse.urlencode({"query": url}).encode("utf-8"),
            lambda d: next(
                (x.get("a") for x in (d.get("links") or []) if x.get("a") and "mp3" not in str(x.get("t", "")).lower()),
                None
            ),
        ),
        (
            "TiklyDown",
            f"https://api.tiklydown.eu.org/api/download?url={urllib.parse.quote(url, safe='')}",
            None,
            lambda d: (d.get("video") or {}).get("noWatermark") or (d.get("video") or {}).get("watermark"),
        ),
    ]

    for nombre_esp, api_url, body_data, extractor in espejos:
        try:
            req = urllib.request.Request(
                api_url,
                data=body_data,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Origin": "https://lovetik.com",
                    "Referer": "https://lovetik.com/",
                },
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                res = json.loads(resp.read().decode("utf-8", errors="ignore"))

            play_url = extractor(res)
            if not play_url:
                continue

            req_vid = urllib.request.Request(
                play_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req_vid, timeout=90) as r_vid, open(dest, "wb") as f_out:
                while True:
                    chunk = r_vid.read(65536)
                    if not chunk:
                        break
                    f_out.write(chunk)

            if os.path.exists(dest) and os.path.getsize(dest) > 100000:
                mb = os.path.getsize(dest) / 1024 / 1024
                print(f"  Descargado con espejo {nombre_esp}: {os.path.basename(dest)} ({mb:.1f} MB)")
                return dest
        except Exception as e_esp:
            print(f"  Aviso en espejo {nombre_esp}: {e_esp}")
            continue
    return None


def download(url, slug, direct_play_url=None):
    """Descarga a refs\\slug.mp4 reutilizando direct_play_url instantáneo o cuádruple motor. Devuelve la ruta o None."""
    dest = os.path.join(REFS, slug + ".mp4")
    if os.path.exists(dest) and os.path.getsize(dest) > 100000:
        print(f"  Ya descargado: {os.path.basename(dest)}")
        return dest

    # Motor 0 (Turbo Instantáneo): Si obtener_info_video_directo ya obtuvo el link MP4 de TikWM/LoveTik, descargarlo sin doble llamada API
    if direct_play_url:
        try:
            import urllib.request
            print("  ⚡ Descarga Turbo Directa (reutilizando stream MP4 sin doble consulta API)...")
            req_vid = urllib.request.Request(
                direct_play_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req_vid, timeout=90) as r_vid, open(dest, "wb") as f_out:
                while True:
                    chunk = r_vid.read(65536)
                    if not chunk:
                        break
                    f_out.write(chunk)
            if os.path.exists(dest) and os.path.getsize(dest) > 100000:
                mb = os.path.getsize(dest) / 1024 / 1024
                print(f"  Descargado en modo Turbo: {os.path.basename(dest)} ({mb:.1f} MB)")
                return dest
        except Exception as e_fast:
            print(f"  Aviso en descarga Turbo Directa: {e_fast}")

    out_tpl = os.path.join(REFS, slug + ".%(ext)s")
    # En la nube (GitHub Actions), TikWM HD descarga directo en 3 segundos sin sufrir el bloqueo/reintentos de yt-dlp
    if os.environ.get("GITHUB_ACTIONS") == "true":
        res_fast = descargar_respaldo_tikwm(url, dest)
        if res_fast:
            return res_fast

    for intento in range(1, 3):
        cmd = [sys.executable, "-m", "yt_dlp", "--no-progress",
               "--retries", "3", "-f", "b/download/h264_720p_1072433-0/bv*+ba", "-o", out_tpl]
        if os.path.exists(COOKIES) and intento == 1:
            cmd += ["--cookies", COOKIES]
        cmd.append(url)

        print(f"  Descargando con yt-dlp (intento {intento})...")
        rc, out = run(cmd)

        if rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 100000:
            mb = os.path.getsize(dest) / 1024 / 1024
            print(f"  Descargado: {os.path.basename(dest)} ({mb:.1f} MB)")
            return dest

        if "403" in out or "Forbidden" in out or "Log in for access" in out or "comfortable" in out:
            print("  yt-dlp recibió bloqueo/restricción de TikTok. Saltando a motor de respaldo...")
            break

    # Motor 2: TikWM HD API (no sufre bloqueo 403 en IPs de GitHub Actions ni pide cookies para videos sensibles)
    res_tikwm = descargar_respaldo_tikwm(url, dest)
    if res_tikwm:
        return res_tikwm

    # Motor 3: Servidores Espejo (LoveTik / TiklyDown)
    res_esp = descargar_respaldo_espejo(url, dest)
    if res_esp:
        return res_esp

    return None


def get_video_meta(path):
    """Obtiene metadatos tecnicos: duracion, dimensiones, audio y orientacion."""
    rc, out = run([FFMPEG, "-i", path])
    meta = {
        "duration": None,
        "width": 0,
        "height": 0,
        "has_audio": False,
        "is_vertical": True,
        "aspect_ratio": 9 / 16,
    }
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out)
    if m_dur:
        h, mi, s = int(m_dur.group(1)), int(m_dur.group(2)), float(m_dur.group(3))
        meta["duration"] = h * 3600 + mi * 60 + s

    m_vid = re.search(r"Video:.*?\b(\d{3,5})x(\d{3,5})\b", out)
    if m_vid:
        w, h = int(m_vid.group(1)), int(m_vid.group(2))
        meta["width"] = w
        meta["height"] = h
        if h > 0:
            meta["aspect_ratio"] = w / h
            meta["is_vertical"] = (h >= w)

    if re.search(r"Audio:\s*[a-zA-Z0-9_]+", out):
        meta["has_audio"] = True

    m_bit = re.search(r"bitrate:\s*(\d+)\s*kb/s", out)
    if m_bit:
        meta["bitrate_kbps"] = int(m_bit.group(1))
    else:
        meta["bitrate_kbps"] = 0

    return meta


def get_duration(path):
    meta = get_video_meta(path)
    return meta.get("duration")


def build_filters(dur, hook, cta, zoom_w=1090, zoom_h=1939, cta_color="yellow", speed_factor=1.0, is_vertical=True, font_file="arialbd.ttf", has_audio=True):
    import random

    # Mejora 1: Micro-aceleración dinámica anti-detección (1.03x a 1.06x)
    # Aumenta retención en los primeros segundos y modifica hashes únicos de audio y video
    if speed_factor is None or abs(speed_factor - 1.0) < 0.005:
        speed_factor = round(random.uniform(1.03, 1.06), 3)

    # Mejora 4: Rotación dinámica de colores de CTA y fuentes de alto impacto
    PALETA_VIRAL = ["#FFE600", "#00F0FF", "#39FF14", "#FF5252", "#D946EF"]
    FUENTES_VIRALES = ["impact.ttf", "trebucbd.ttf", "arialbd.ttf", "segoeuib.ttf"]

    if not cta_color or cta_color in ("yellow", "gold"):
        cta_color = random.choice(PALETA_VIRAL)

    if not font_file:
        font_file = random.choice(FUENTES_VIRALES)

    font_p = get_font_file(font_file)
    hook_lines = [l.strip() for l in hook.split("|") if l.strip()]
    # Auto-escala dinámica del tamaño de letra para que títulos largos nunca se salgan de pantalla
    max_len_hook = max((len(l) for l in hook_lines), default=0)
    if max_len_hook > 24:
        hook_fs = 46
    elif max_len_hook > 18:
        hook_fs = 54
    else:
        hook_fs = 62

    hook_filt = ""
    for i, line in enumerate(hook_lines):
        lt = line.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")
        # Línea 1 en blanco puro; Línea 2 y siguientes en color de acento de alto impacto
        color_linea = "white" if i == 0 else cta_color
        hook_filt += (
            f"drawtext=fontfile='{font_p}':text='{lt}'"
            f":fontsize={hook_fs}:fontcolor={color_linea}:borderw=6:bordercolor=black"
            f":x=(w-text_w)/2:y={140 + i * (hook_fs + 16)}"
            f":enable='between(t,0,2.5)',"
        )

    # CTA estrictamente para los últimos 3 segundos del video hasta el final absoluto
    t_cta = max(0.0, dur - 3.0)

    # Si el CTA no viene dividido con '|' y tiene más de 18 caracteres, dividir en 2 líneas simétricas
    cta_limpio = cta.strip()
    if "|" not in cta_limpio and len(cta_limpio) > 18:
        palabras_cta = cta_limpio.split()
        mitad_cta = len(palabras_cta) // 2
        cta_limpio = f"{' '.join(palabras_cta[:mitad_cta])}|{' '.join(palabras_cta[mitad_cta:])}"

    cta_lines = [l.strip() for l in cta_limpio.split("|") if l.strip()]
    max_len_cta = max((len(l) for l in cta_lines), default=0)
    if max_len_cta > 24:
        cta_fs = 48
    elif max_len_cta > 18:
        cta_fs = 56
    else:
        cta_fs = 64

    cta_filt = ""
    for i, line in enumerate(cta_lines):
        ct = line.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")
        # Línea 1 blanca si son 2 líneas; Línea 2 y siguientes en cta_color (o todo en cta_color si es 1 línea)
        color_cta = "white" if (i == 0 and len(cta_lines) > 1) else cta_color
        cta_filt += (
            f"drawtext=fontfile='{font_p}':text='{ct}'"
            f":fontsize={cta_fs}:fontcolor={color_cta}:borderw=6:bordercolor=black"
            f":x=(w-text_w)/2:y=h-400+{i * (cta_fs + 14)}"
            f":enable='gte(t,{t_cta:.2f})',"
        )
    cta_filt = cta_filt.rstrip(",")

    pts_filt = f",setpts={1.0/speed_factor:.4f}*PTS" if abs(speed_factor - 1.0) > 0.001 else ""
    atempo_filt = f"atempo={speed_factor:.4f}," if abs(speed_factor - 1.0) > 0.001 else ""

    # Capa 1 Anti-Detección: Desplazamiento dinámico de coordenadas (Pixel Jitter)
    # Agrandamos ligeramente con margen seguro para cortar con desplazamiento aleatorio
    eff_zoom_w = max(int(zoom_w or 1090), 1100)
    eff_zoom_h = max(int(zoom_h or 1939), 1956)
    extra_w = max(0, eff_zoom_w - TARGET_W)
    extra_h = max(0, eff_zoom_h - TARGET_H)
    base_x = extra_w // 2
    base_y = extra_h // 2
    jitter_x = max(0, min(extra_w, base_x + random.randint(-5, 5)))
    jitter_y = max(0, min(extra_h, base_y + random.randint(-8, 8)))

    # Capa 2 Anti-Detección: Alteración sutil de colorimetría (Color Shift / Gamma)
    c_contrast = round(random.uniform(1.025, 1.045), 3)
    c_brightness = round(random.uniform(0.005, 0.012), 3)
    c_saturation = round(random.uniform(1.03, 1.06), 3)
    c_gamma = round(random.uniform(0.99, 1.015), 3)
    eq_filt = f"eq=contrast={c_contrast}:brightness={c_brightness}:saturation={c_saturation}:gamma={c_gamma},"

    # Capa 3 Anti-Detección: Micro-ruido temporal de sensor (Micro-Grain Dithering)
    # 1.5% de grano de sensor que rompe el hash perceptual por bloques de Meta
    noise_filt = "noise=alls=2:allf=t+u,"

    # En la nube (Linux sin GPU), bilinear es 3x más rápido que bicubic y afir/volume es instantáneo frente a loudnorm de 2 pasadas
    scale_flag = "bilinear" if os.name != "nt" else "bicubic"
    audio_norm = "dynaudnorm=f=150:g=15" if os.name != "nt" else "loudnorm=I=-14:TP=-1.0:LRA=7"

    if is_vertical:
        vf = (f"scale={eff_zoom_w}:{eff_zoom_h}:flags={scale_flag},"
              f"crop={TARGET_W}:{TARGET_H}:{jitter_x}:{jitter_y},"
              + eq_filt + noise_filt + hook_filt + cta_filt + pts_filt)
        v_chain = f"[0:v]{vf}[v];"
    else:
        bg = f"[v_bg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase:flags={scale_flag},crop={TARGET_W}:{TARGET_H},boxblur=25:5[bg];"
        fg = f"[v_fg]scale={TARGET_W}:-2:flags={scale_flag}[fg];"
        ov = f"[bg][fg]overlay=0:(H-h)/2,{eq_filt}{noise_filt}{hook_filt}{cta_filt}{pts_filt}[v];"
        v_chain = f"[0:v]split=2[v_bg][v_fg];{bg}{fg}{ov}"
    if has_audio:
        a_chain = f"[0:a]{atempo_filt}{audio_norm}[a]"
    else:
        dur_out = max(1.0, float(dur or 30.0) / max(0.5, float(speed_factor or 1.0)))
        a_chain = f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=0:{dur_out:.2f}[a]"
    return f"{v_chain}{a_chain}"


def limpiar_metadatos(path):
    """Quita TODO metadato (incluido encoder de ffmpeg) con un remux rapido."""
    tmp = path + ".clean.mp4"
    cmd = [FFMPEG, "-y", "-i", path, "-map", "0", "-c", "copy",
           "-map_metadata", "-1", "-fflags", "+bitexact",
           "-flags:v", "+bitexact", "-flags:a", "+bitexact",
           "-metadata:s:v:0", "encoder=", "-metadata:s:a:0", "encoder=",
           "-metadata", "encoder=", "-metadata", "title=", "-metadata", "comment=",
           "-movflags", "+faststart", tmp]
    rc, out = run(cmd)
    if rc == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        os.replace(tmp, path)
        return True
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except Exception:
            pass
    print("  Aviso: no se pudieron limpiar los metadatos.")
    return False


def render(src, dur, hook, cta, out_path, zoom_w=1090, zoom_h=1939, cta_color="yellow", speed_factor=1.0, trim_start=0.0, is_vertical=True, font_file="arialbd.ttf", has_audio=True):
    fc = build_filters(dur, hook, cta, zoom_w=zoom_w, zoom_h=zoom_h, cta_color=cta_color, speed_factor=speed_factor, is_vertical=is_vertical, font_file=font_file, has_audio=has_audio)
    import random
    # Capa 4 Anti-Detección: Desincronización de cadencia de fotogramas (FPS Drift)
    fps_val = random.choice(["29.97", "30.03", "29.98", "30.02"])
    # Procesar el video completo al 100% de inicio a fin con limpieza bitexact de metadatos integrada en 1 sola pasada
    common = [
        FFMPEG, "-y",
        "-i", src,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-map_metadata", "-1",
        "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-metadata:s:v:0", "encoder=", "-metadata:s:a:0", "encoder=",
        "-metadata", "title=", "-metadata", "comment=", "-metadata", "encoder=",
        "-pix_fmt", "yuv420p", "-r", fps_val,
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
        out_path,
    ]

    # 1) En Windows intentar GPU AMD; en Linux ir directo a CPU ultrafast sin perder tiempo intentando abrir GPU
    rc = 1
    out = ""
    if os.name == "nt":
        cmd = common[:]
        # Modo eco-friendly: bitrate 3500k y maxrate 4200k óptimo para Reels 1080x1920
        cmd[cmd.index("-pix_fmt"):cmd.index("-pix_fmt")] = [
            "-c:v", "h264_amf", "-quality", "speed", "-b:v", "3500k", "-maxrate", "4200k", "-bufsize", "6000k"]
        rc, out = run_ff(cmd)

    # Estándar VBV Constrained CRF Turbo para Reels: peso ligero (~16-20 MB) y máxima nitidez HD en celulares
    dur_seg = max(float(dur or 30.0), 10.0)
    max_kbps = min(2100, max(1100, int((24 * 8 * 1024) / dur_seg) - 128))
    maxrate_str = f"{max_kbps}k"
    bufsize_str = f"{int(max_kbps * 1.52)}k"

    # 2) CPU (Modo Turbo VBV Constrained CRF: -crf 24 sin -b:v conflictivo)
    if rc != 0 or not os.path.exists(out_path):
        if os.name == "nt":
            print("  GPU no disponible, usando CPU...")
        cmd = common[:]
        is_cloud = os.environ.get("GITHUB_ACTIONS") == "true" or os.name != "nt"
        preset_val = "ultrafast" if is_cloud else "veryfast"
        crf_val = "24"
        cmd[cmd.index("-pix_fmt"):cmd.index("-pix_fmt")] = [
            "-c:v", "libx264", "-preset", preset_val, "-tune", "fastdecode",
            "-crf", crf_val, "-maxrate", maxrate_str, "-bufsize", bufsize_str, "-threads", "0"
        ]
        rc, out = run_ff(cmd)

    # 3) Si en Linux falló por el formato de ruta de la fuente en drawtext, reintentar con ruta relativa
    if (rc != 0 or not os.path.exists(out_path)) and os.name != "nt":
        print("  Reintentando render en Linux con fontfile relativo...")
        fc_rel = fc.replace(f"fontfile='{FONT}'", "fontfile='assets/arialbd.ttf'")
        cmd = common[:]
        cmd[cmd.index("-filter_complex") + 1] = fc_rel
        cmd[cmd.index("-pix_fmt"):cmd.index("-pix_fmt")] = [
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
            "-maxrate", maxrate_str, "-bufsize", bufsize_str, "-threads", "0"
        ]
        rc, out = run_ff(cmd)

    if rc == 0 and os.path.exists(out_path):
        mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"  LISTO: {os.path.basename(out_path)} ({mb:.1f} MB)")
        return True
    print("  ERROR de render:")
    print(out[-800:])
    return False


def generar_cover(video_path, out_cover_path, segundo=1.5):
    """Extrae un fotograma clave de alta calidad para portada/cover del Reel en 1080x1920."""
    try:
        cmd = [
            FFMPEG, "-y", "-ss", f"{segundo:.2f}", "-i", video_path,
            "-vframes", "1", "-q:v", "2", out_cover_path
        ]
        rc, _ = run(cmd)
        if rc == 0 and os.path.exists(out_cover_path) and os.path.getsize(out_cover_path) > 1000:
            return out_cover_path
    except Exception as e:
        print(f"  Aviso al generar cover: {e}")
    return None


def main():
    url, serie, parte, hook, cta = URL.strip(), SERIE.strip(), PARTE, HOOK.strip(), CTA
    interactivo = len(sys.argv) == 1

    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        serie = sys.argv[2]
    if len(sys.argv) > 3:
        try:
            parte = int(sys.argv[3])
        except ValueError:
            parte = 1

    if interactivo and (not url or not serie):
        print("=" * 50)
        print("  HACER REEL")
        print("=" * 50)
        url = input("  Link del video: ").strip()
        serie = input("  Nombre de la serie: ").strip()
        p = input("  Numero de parte (Enter = 1): ").strip()
        parte = int(p) if p.isdigit() else 1

    if not url or not serie:
        print("Falta URL o SERIE. Edita el bloque CONFIG o pasa argumentos:")
        print('  python AUTO_REEL.py "URL" "SERIE" [PARTE]')
        if interactivo:
            input("\nPresiona Enter para cerrar...")
        return 2

    os.makedirs(REFS, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print(f"  Serie: {serie} | Parte: {parte}")
    print(f"  URL: {url}")
    print("=" * 60)

    src = download(url, slug_from_url(url))
    if not src:
        print("No se pudo descargar. Fin.")
        return 1

    dur = get_duration(src)
    if not dur:
        print("No se pudo leer la duracion.")
        return 1
    print(f"  Duracion: {dur:.1f} s")

    nombre = f"REEL_{serie}" + ("" if parte in (0, 1) else f" parte {parte}")
    out_path = os.path.join(OUT_DIR, nombre + ".mp4")

    hook_txt = hook or serie.upper()
    ok = render(src, dur, hook_txt, cta, out_path)
    if not ok:
        return 1

    print("\nArchivo final:")
    print(f"  {out_path}")
    return 0


if __name__ == "__main__":
    try:
        _code = main()
    except Exception as _e:
        print("ERROR:", _e)
        _code = 1
    if len(sys.argv) == 1:
        try:
            input("\nPresiona Enter para cerrar...")
        except Exception:
            pass
    sys.exit(_code)
