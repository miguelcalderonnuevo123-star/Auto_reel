# -*- coding: utf-8 -*-
"""
BOT_NUBE.py — Motor completo TikTok -> AUTO_REEL -> Instagram Reels.
Incluye:
- [Mejora 1] Bandeja de Telegram (lee links enviados a tu bot de Telegram @Maykel0007_bot y te avisa al publicar).
- [Mejora 2] Cola de videos (cola_videos.txt) para ir soltando de a 1 video en tus Horas Pico.
- [Mejora 4] Portada (Miniatura) automática: toma un fotograma limpio del segundo 3.5, le estampa el título y lo sube como portada oficial del Reel.
- [Mejora 6] Tapado inteligente de marca de agua (AUTO / ARRIBA / ABAJO / NO) con tu placa dorada @frutnovelas776.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import AUTO_REEL

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE, "assets")
HISTORIAL_PATH = os.path.join(BASE, "historial_bot.json")
COLA_PATH = os.path.join(BASE, "cola_videos.txt")
GRANJA_PATH = os.path.join(BASE, "cuentas_granja.json")
COOKIES_IG_LOCAL = os.path.join(BASE, "refs", "cookies_insta.txt")
COOKIES_IG_ALT = r"C:\Users\piade\Desktop\Descargar videos gratis\cookies_insta.txt"
TOKEN_TG_LOCAL = r"C:\Users\piade\Desktop\Descargar videos gratis\token_insta.txt"

TIKTOK_USER_URL = os.environ.get("TIKTOK_USER_URL", "https://www.tiktok.com/@helloword.visuals").strip()
TIKTOK_CHANNEL_ID = os.environ.get(
    "TIKTOK_CHANNEL_ID",
    "MS4wLjABAAAACLle2hko75dXsCGmRLFp0i-pA-FOH-Ds8uJ7Nr7ETr6Mt22MsXZYMKxKmRjH3R7K",
).strip()

DEFAULT_HASHTAGS = ["#frutinovelas", "#fruit", "#foodstory", "#partii", "#capibara"]
DEFAULT_HOOK_FALLBACK = "HISTORIA COMPLETA"
BADGE_TEXT = os.environ.get("BADGE_TEXT", "@frutnovelas776").strip()

IG_DEVICE = {
    "android_version": 30,
    "android_release": "11",
    "dpi": "420dpi",
    "resolution": "1080x2400",
    "manufacturer": "samsung",
    "device": "SM-A525F",
    "model": "Galaxy A52",
    "cpu": "universal",
}


# ============================================================
#   HISTORIAL Y COLA DE VIDEOS (MEJORA 2)
# ============================================================

def cargar_granja():
    """Carga la configuración de cuentas de cuentas_granja.json."""
    if os.path.exists(GRANJA_PATH):
        try:
            with open(GRANJA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "cuentas" in data:
                    return data["cuentas"]
        except Exception as e:
            print(f"  Aviso leyendo cuentas_granja.json: {e}")
    return {
        "cuenta1": {
            "activa": True,
            "nombre": "Frutinovelas Principal",
            "secret_sessionid": "IG_SESSIONID",
            "tiktok_source_url": TIKTOK_USER_URL,
            "tiktok_channel_id": TIKTOK_CHANNEL_ID,
            "auto_monitor": False,
            "hashtags_default": DEFAULT_HASHTAGS,
            "cta": AUTO_REEL.CTA,
            "estilo_unico": {
                "zoom_w": 1090,
                "zoom_h": 1939,
                "cta_color": "yellow",
                "speed_factor": 1.0,
                "trim_start": 0.0,
            },
            "device": IG_DEVICE,
            "proxy": "",
        }
    }


def cargar_historial():
    if os.path.exists(HISTORIAL_PATH):
        try:
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  Aviso: no se pudo leer historial_bot.json ({e}), iniciando estructura limpia.")
    return {
        "account_url": TIKTOK_USER_URL,
        "channel_id": TIKTOK_CHANNEL_ID,
        "processed_ids": [],
        "series_counts": {},
        "telegram_last_update_id": 0,
        "telegram_chat_id": None,
        "history": [],
    }


def guardar_historial(data):
    if isinstance(data, dict):
        if isinstance(data.get("processed_ids"), list):
            data["processed_ids"] = data["processed_ids"][:500]
        if isinstance(data.get("huellas_videos"), list):
            data["huellas_videos"] = data["huellas_videos"][:300]
        if isinstance(data.get("history"), list):
            data["history"] = data["history"][:150]
        if isinstance(data.get("series_counts"), dict) and len(data["series_counts"]) > 300:
            items_sc = list(data["series_counts"].items())[-300:]
            data["series_counts"] = dict(items_sc)
    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def leer_cola_videos():
    """Lee cola_videos.txt. Cada línea puede ser 'URL' o 'URL | HOOK PERSONALIZADO'."""
    if not os.path.exists(COLA_PATH):
        return []
    items = []
    with open(COLA_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            partes = [p.strip() for p in line.split("|", 1)]
            url = partes[0]
            hook = partes[1] if len(partes) > 1 else ""
            if "tiktok.com" in url:
                items.append({"url": url, "hook": hook, "raw_line": line})
    return items


def quitar_de_cola(url_procesada):
    """Elimina de cola_videos.txt el link ya subido."""
    if not os.path.exists(COLA_PATH):
        return
    nuevas = []
    quitado = False
    with open(COLA_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not quitado and line and not line.startswith("#") and url_procesada in line:
                quitado = True
                continue
            nuevas.append(raw.rstrip("\r\n"))
    with open(COLA_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(nuevas) + ("\n" if nuevas else ""))


def agregar_a_cola(url, hook=""):
    linea = f"{url} | {hook}".strip(" |")
    with open(COLA_PATH, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ============================================================
#   INTEGRACIÓN CON TELEGRAM (MEJORA 1)
# ============================================================

def obtener_token_telegram():
    tok = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not tok and os.path.exists(TOKEN_TG_LOCAL):
        try:
            tok = open(TOKEN_TG_LOCAL, encoding="utf-8").read().strip()
        except Exception:
            pass
    return tok


def enviar_mensaje_telegram(chat_id, texto, botones=None):
    tok = obtener_token_telegram()
    if not tok or not chat_id:
        return None
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": False}
    if botones:
        payload["reply_markup"] = {"inline_keyboard": botones}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json=payload,
            timeout=15,
        )
        if r.status_code != 200:
            payload.pop("parse_mode", None)
            r = requests.post(
                f"https://api.telegram.org/bot{tok}/sendMessage",
                json=payload,
                timeout=15,
            )
        if r.status_code == 200:
            return ((r.json() or {}).get("result") or {}).get("message_id")
    except Exception as e:
        print(f"  Aviso Telegram: {e}")
    return None


def borrar_mensaje_telegram(chat_id, message_id):
    tok = obtener_token_telegram()
    if not tok or not chat_id or not message_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{tok}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=10,
        )
    except Exception:
        pass


def enviar_video_telegram(chat_id, video_path, caption="", botones=None):
    """
    Envía un video renderizado en HD a Telegram con soporte de streaming y botones de acción.
    Si el video excede el límite estricto de Telegram (50 MB), lo comprime de forma ultrarrápida.
    """
    tok = obtener_token_telegram()
    if not tok or not chat_id or not os.path.exists(video_path):
        return False

    tam_mb = os.path.getsize(video_path) / (1024 * 1024)
    video_final = video_path
    video_comprimido_temp = None

    if tam_mb > 45.0:
        print(f"  ⚠️ Video de {tam_mb:.1f} MB supera el límite seguro de Telegram (45 MB). Comprimiendo...")
        video_comprimido_temp = video_path + ".tg_opt.mp4"
        dur_v = AUTO_REEL.get_duration(video_path) or 60.0
        target_bitrate = max(500, min(2200, int((36 * 8 * 1024) / max(dur_v, 10)) - 96))
        cmd_c = [
            AUTO_REEL.FFMPEG, "-y", "-i", video_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-b:v", f"{target_bitrate}k", "-maxrate", f"{target_bitrate + 200}k", "-bufsize", "4000k",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", video_comprimido_temp
        ]
        AUTO_REEL.run(cmd_c, timeout=90)
        if os.path.exists(video_comprimido_temp) and os.path.getsize(video_comprimido_temp) > 0:
            video_final = video_comprimido_temp
            print(f"  ✅ Optimizado para Telegram: {os.path.getsize(video_final)/(1024*1024):.1f} MB (bitrate: {target_bitrate}k)")

    url = f"https://api.telegram.org/bot{tok}/sendVideo"
    data = {
        "chat_id": chat_id,
        "caption": caption[:1024],  # Límite de caption en Telegram
        "parse_mode": "HTML",
        "supports_streaming": "true"
    }
    if botones:
        data["reply_markup"] = json.dumps({"inline_keyboard": botones})
    try:
        with open(video_final, "rb") as f:
            r = requests.post(url, data=data, files={"video": f}, timeout=180)
        if r.status_code == 200:
            print("  ✅ Video entregado con éxito a Telegram.")
            if video_comprimido_temp and os.path.exists(video_comprimido_temp):
                try:
                    os.remove(video_comprimido_temp)
                except Exception:
                    pass
            return True
        else:
            print(f"  Aviso Telegram sendVideo (HTTP {r.status_code}): {r.text}")
            # Respaldo garantizado por texto si el video no cupo en Telegram
            if caption and chat_id:
                print("  Enviando mensaje de respaldo por texto a Telegram...")
                enviar_mensaje_telegram(chat_id, caption, botones=botones)
            return False
    except Exception as e:
        print(f"  Error enviando video a Telegram: {e}")
        if caption and chat_id:
            enviar_mensaje_telegram(chat_id, caption, botones=botones)
        return False


def revisar_bandeja_telegram(historial):
    """
    Lee mensajes y toques de botones en tu bot de Telegram (@Maykel0007_bot) desde la nube:
    - Cuando pegas solo el link de TikTok -> te muestra 2 botones claros:
        [ 🍓 Subir a @frutnovelas776 ]
        [ 🍍 Subir a @novelas_frutosass ]
    - Cuando tocas uno de los dos botones -> sube ese video inmediatamente a la cuenta elegida.
    """
    tok = obtener_token_telegram()
    if not tok:
        return None, "", "frutnovelas776"

    offset = int(historial.get("telegram_last_update_id") or 0) + 1
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{tok}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=15,
        )
        data = r.json()
        if not data.get("ok"):
            return None, "", "frutnovelas776"
    except Exception as e:
        print(f"  Aviso consultando Telegram: {e}")
        return None, "", "frutnovelas776"

    acciones_listas = []
    links_esperando_boton = []
    respondio_start = False

    for upd in data.get("result", []):
        upd_id = upd.get("update_id", 0)
        if upd_id >= offset:
            historial["telegram_last_update_id"] = upd_id

        # 1) Si el usuario tocó uno de los botones de cuenta
        if "callback_query" in upd:
            cq = upd["callback_query"]
            cq_id = cq.get("id")
            msg_cq = cq.get("message") or {}
            chat_id = (msg_cq.get("chat") or {}).get("id")
            if chat_id:
                historial["telegram_chat_id"] = chat_id
            try:
                requests.post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", json={"callback_query_id": cq_id}, timeout=10)
            except Exception:
                pass

            cb_data = cq.get("data") or ""
            if cb_data.startswith("subir:"):
                cuenta_elegida = cb_data.split(":", 1)[1].strip()
                pend = historial.get("telegram_pending_video") or {}
                url_pend = pend.get("url") or ""
                hook_pend = pend.get("hook") or ""
                if url_pend:
                    acciones_listas.append((url_pend, hook_pend, cuenta_elegida, chat_id))
                    historial["telegram_pending_video"] = None
            continue

        # 2) Si el usuario envió un mensaje de texto
        msg = upd.get("message") or upd.get("edited_message") or {}
        txt = (msg.get("text") or "").strip()
        chat_id = (msg.get("chat") or {}).get("id")
        if chat_id:
            historial["telegram_chat_id"] = chat_id

        if txt.startswith("/start") and chat_id and not respondio_start:
            enviar_mensaje_telegram(
                chat_id,
                "☁️ ¡Bot en la Nube conectado a tus 2 cuentas!\n\n"
                "Solo pégame cualquier link de TikTok aquí y te saldrán los 2 botones:\n"
                "🍓 @frutnovelas776\n"
                "🍍 @novelas_frutosass\n\n"
                "¡Tocas el botón de la cuenta donde lo quieras subir y listo!"
            )
            respondio_start = True
            guardar_historial(historial)

        if "tiktok.com" in txt:
            partes = [p.strip() for p in txt.split("|", 1)]
            m_url = re.search(r"(https?://[^\s]+tiktok\.com[^\s]+)", partes[0])
            if m_url:
                url_tk = m_url.group(1)
                hook_tk = partes[1] if len(partes) > 1 else ""
                links_esperando_boton.append((url_tk, hook_tk, chat_id))

    if acciones_listas:
        guardar_historial(historial)
        primero_url, primero_hook, primero_cuenta, chat_id = acciones_listas[0]
        for extra_url, extra_hook, extra_cuenta, _ in acciones_listas[1:]:
            agregar_a_cola(f"{extra_cuenta} {extra_url}", extra_hook)
        enviar_mensaje_telegram(
            chat_id,
            f"🚀 Subiendo tu video a @{primero_cuenta}...\n{primero_url}\n\nTe aviso en 1-2 minutos con el link del Reel."
        )
        return primero_url, primero_hook, primero_cuenta

    if links_esperando_boton:
        ult_url, ult_hook, chat_id = links_esperando_boton[-1]
        historial["telegram_pending_video"] = {"url": ult_url, "hook": ult_hook}
        guardar_historial(historial)
        botones = [
            [{"text": "🍓 Subir a @frutnovelas776", "callback_data": "subir:frutnovelas776"}],
            [{"text": "🍍 Subir a @novelas_frutosass", "callback_data": "subir:novelas_frutosass"}],
        ]
        hook_info = f"\n📌 Hook: {ult_hook}" if ult_hook else "\n📌 Hook: Automático de la descripción"
        enviar_mensaje_telegram(
            chat_id,
            f"🎬 Video recibido:\n{ult_url}{hook_info}\n\n👇 ¿A cuál de tus cuentas lo quieres subir?",
            botones=botones,
        )
        return None, "", "frutnovelas776"

    return None, "", "frutnovelas776"


# ============================================================
#   TAPADO INTELIGENTE DE MARCA DE AGUA (MEJORA 6)
# ============================================================

def crear_placa_dorada(texto=None):
    """Crea una placa estética y personalizada con el nombre de la cuenta para tapar marcas ajenas."""
    texto = (texto or BADGE_TEXT).strip()
    if not texto.startswith("@"):
        texto = f"@{texto}"
    w, h = 360, 56
    badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=10, fill=(18, 16, 14, 255), outline=(255, 200, 40, 255), width=2)

    font_path = r"C:\Windows\Fonts\arialbd.ttf" if os.name == "nt" else os.path.join(ASSETS_DIR, "arialbd.ttf")
    try:
        font = ImageFont.truetype(font_path, 28)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), texto, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = (h - th) // 2 - 2
    draw.text((tx, ty), texto, font=font, fill=(255, 230, 100, 255))

    temp_badge = os.path.join(tempfile.gettempdir(), f"badge_{re.sub(r'[^a-zA-Z0-9]', '', texto)}.png")
    badge.save(temp_badge)
    return temp_badge


def detectar_posicion_marca(video_path, modo_marca="auto"):
    """
    Devuelve (x, y, descripcion) sobre lienzo 1080x1920 o None si modo_marca == 'no'.
    Modos: 'auto', 'arriba', 'abajo', 'no'
    """
    modo = (modo_marca or "auto").strip().lower()
    if modo in ("no", "none", "false", "0", "off"):
        return None

    if modo == "arriba":
        return 650, 320, "ARRIBA (Forzado)"
    if modo == "abajo":
        return 360, 1460, "ABAJO (Forzado)"

    # Modo 'auto': usa OpenCV y las plantillas en assets/ si están disponibles
    try:
        import cv2
        t_fruti_path = os.path.join(ASSETS_DIR, "frutirealidades.png")
        t_cartoon_path = os.path.join(ASSETS_DIR, "fruticartoon.png")
        if os.path.exists(t_fruti_path) and os.path.exists(t_cartoon_path):
            temp_jpg = os.path.join(tempfile.gettempdir(), "frame_detect_wm.jpg")
            subprocess.run(
                [AUTO_REEL.FFMPEG, "-y", "-ss", "6", "-i", video_path, "-vf", "scale=1080:1920", "-vframes", "1", "-q:v", "2", temp_jpg],
                capture_output=True,
            )
            if os.path.exists(temp_jpg):
                frame = cv2.imread(temp_jpg, cv2.IMREAD_GRAYSCALE)
                t_fruti = cv2.imread(t_fruti_path, cv2.IMREAD_GRAYSCALE)
                t_cartoon = cv2.imread(t_cartoon_path, cv2.IMREAD_GRAYSCALE)
                try:
                    os.remove(temp_jpg)
                except Exception:
                    pass
                if frame is not None and t_fruti is not None and t_cartoon is not None:
                    h, w = frame.shape
                    res_t = cv2.matchTemplate(frame[0:int(h * 0.4), int(w * 0.3):w], t_fruti, cv2.TM_CCOEFF_NORMED)
                    st = cv2.minMaxLoc(res_t)[1]
                    res_b = cv2.matchTemplate(frame[int(h * 0.6):h, int(w * 0.1):int(w * 0.9)], t_cartoon, cv2.TM_CCOEFF_NORMED)
                    sb = cv2.minMaxLoc(res_b)[1]
                    if st > 0.45 and st > sb:
                        return 650, 320, f"ARRIBA (Detectada {int(st*100)}%)"
                    elif sb > 0.40:
                        return 360, 1460, f"ABAJO (Detectada {int(sb*100)}%)"
    except Exception:
        pass

    return None


def aplicar_placa_marca(video_path, modo_marca="auto", badge_text=None):
    """Si detecta marca de agua (o si el modo es forzado), estampa la placa personalizada con la cuenta actual."""
    pos = detectar_posicion_marca(video_path, modo_marca)
    if not pos:
        print("  Marca de agua: No se detectó marca externa. Video limpio.")
        return False

    nombre_badge = (badge_text or BADGE_TEXT).strip()
    x, y, desc_pos = pos
    print(f"  Tapando marca de agua en posición {desc_pos} (X={x}, Y={y}) con placa propia {nombre_badge}...")
    badge_png = crear_placa_dorada(nombre_badge)
    tmp_out = video_path + ".wm.mp4"

    cmd = [
        AUTO_REEL.FFMPEG, "-y",
        "-i", video_path,
        "-i", badge_png,
        "-filter_complex", f"[0:v][1:v]overlay={x}:{y}[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        tmp_out,
    ]
    rc, _ = AUTO_REEL.run_ff(cmd)
    if rc == 0 and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 10000:
        os.replace(tmp_out, video_path)
        print(f"  Placa dorada {nombre_badge} aplicada con éxito.")
        try:
            os.remove(badge_png)
        except Exception:
            pass
        return True
    return False


# ============================================================
#   PORTADAS DRAMÁTICAS CON "FRAME HUNTER"
# ============================================================

def cazar_mejor_fotograma(video_path, dur, min_t=1.0):
    """
    FRAME HUNTER: Escanea múltiples fotogramas candidatos entre min_t y min(7.0s, dur*0.8)
    y selecciona el fotograma con mayor nitidez, expresividad y riqueza de color,
    descartando fundidos a negro, tomas borrosas o pantallas vacías.
    """
    from PIL import ImageFilter, ImageStat

    # Generar candidatos clave bien distribuidos (velocidad turbo)
    t_min = max(min_t, min(2.0, dur * 0.10))
    t_max = min(max(4.0, dur * 0.60), max(t_min + 1.0, dur - 4.0))
    paso = (t_max - t_min) / 3.0 if t_max > t_min else 0.5
    candidatos = [round(t_min + i * paso, 2) for i in range(4)]

    mejor_t = 3.5
    mejor_puntaje = -1.0

    for t in candidatos:
        tmp_frame = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp_frame.close()
        try:
            cmd = [
                AUTO_REEL.FFMPEG, "-y",
                "-ss", str(t),
                "-i", video_path,
                "-vframes", "1",
                "-s", "360x640",
                "-q:v", "3",
                tmp_frame.name
            ]
            AUTO_REEL.run(cmd, timeout=10)
            if os.path.exists(tmp_frame.name) and os.path.getsize(tmp_frame.name) > 1000:
                with Image.open(tmp_frame.name) as im:
                    stat = ImageStat.Stat(im)
                    # Brillo promedio
                    brillo = sum(stat.mean) / 3.0
                    # Penalizar extremos (muy oscuro < 35 o muy quemado > 230)
                    if brillo < 35 or brillo > 230:
                        factor_brillo = 0.15
                    else:
                        factor_brillo = 1.0 - (abs(brillo - 128) / 128.0) * 0.35

                    # Riqueza de color y contraste
                    color_score = sum(stat.stddev) / 3.0

                    # Nitidez de bordes (caras, ojos, expresiones faciales)
                    edges = im.filter(ImageFilter.FIND_EDGES)
                    edge_stat = ImageStat.Stat(edges)
                    edge_score = sum(edge_stat.mean) / 3.0

                    puntaje = (color_score * 1.5 + edge_score * 2.5) * factor_brillo

                    if puntaje > mejor_puntaje:
                        mejor_puntaje = puntaje
                        mejor_t = t
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_frame.name):
                try:
                    os.remove(tmp_frame.name)
                except Exception:
                    pass

    print(f"  🎯 Frame Hunter seleccionó el fotograma más expresivo en t={mejor_t:.2f}s (puntaje: {mejor_puntaje:.1f})")
    return mejor_t


# ============================================================
#   ESTILOS VIRALES DINÁMICOS (ROTACIÓN POR PUBLICACIÓN)
# ============================================================
ESTILOS_VIRALES = [
    {
        "name": "Dorado Viral",
        "font": "impact.ttf",
        "accent_hex": "#FFE600",
        "fill": (15, 15, 20, 215),
        "outline": (255, 215, 0, 255),
        "accent": (255, 230, 40, 255),
    },
    {
        "name": "Cyber Cyan",
        "font": "trebucbd.ttf",
        "accent_hex": "#00F0FF",
        "fill": (10, 20, 35, 215),
        "outline": (0, 235, 255, 255),
        "accent": (0, 240, 255, 255),
    },
    {
        "name": "Lima Neon",
        "font": "arialbd.ttf",
        "accent_hex": "#39FF14",
        "fill": (5, 25, 15, 215),
        "outline": (57, 255, 20, 255),
        "accent": (57, 255, 20, 255),
    },
    {
        "name": "Fuego Coral",
        "font": "impact.ttf",
        "accent_hex": "#FF5252",
        "fill": (28, 12, 12, 215),
        "outline": (255, 82, 82, 255),
        "accent": (255, 82, 82, 255),
    },
    {
        "name": "Magenta Neon",
        "font": "segoeuib.ttf",
        "accent_hex": "#D946EF",
        "fill": (25, 10, 35, 215),
        "outline": (217, 70, 239, 255),
        "accent": (255, 0, 127, 255),
    },
]


def obtener_siguiente_estilo(cuenta_id, historial=None):
    """
    Calcula el siguiente estilo viral (fuente + paleta) para una cuenta específica,
    garantizando que publicaciones consecutivas de la misma cuenta NUNCA se repitan.
    """
    historial = historial if isinstance(historial, dict) else {}
    posts_cuenta = sum(
        1 for h in (historial.get("history") or [])
        if cuenta_id in (h.get("accounts") or [])
    )
    rot_offset = int((historial.get("account_style_rot") or {}).get(cuenta_id, 0))
    idx = (posts_cuenta + rot_offset) % len(ESTILOS_VIRALES)

    # Avanzar el offset para la siguiente publicación de esta cuenta
    if "account_style_rot" not in historial or not isinstance(historial["account_style_rot"], dict):
        historial["account_style_rot"] = {}
    historial["account_style_rot"][cuenta_id] = rot_offset + 1

    return ESTILOS_VIRALES[idx]


def generar_portada_reel(video_path, hook_txt, dur, estilo_idx=0, raw_video_path=None, cfg_cuenta=None, cuenta_id=None, estilo_rotativo=None):
    """
    Usa Frame Hunter sobre el video limpio (sin textos duplicados) y estampa
    un título de alto impacto en el tercio superior de la zona 1:1 de Instagram.
    Deja el centro completamente libre para no tapar los rostros de los personajes.
    Aplica tipografía y paleta viral rotativa coordinada con el video.
    Devuelve la ruta del archivo .jpg.
    """
    video_origen = raw_video_path if (raw_video_path and os.path.exists(raw_video_path)) else video_path
    min_seg = 1.0 if (video_origen == raw_video_path) else 2.6
    t_captura = cazar_mejor_fotograma(video_origen, dur, min_t=min_seg)
    cover_jpg = video_path + ".cover.jpg"

    cmd = [
        AUTO_REEL.FFMPEG, "-y",
        "-ss", f"{t_captura:.2f}",
        "-i", video_origen,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-vframes", "1",
        "-q:v", "2",
        cover_jpg,
    ]
    AUTO_REEL.run(cmd, timeout=30)
    if not os.path.exists(cover_jpg):
        return None

    try:
        img = Image.open(cover_jpg).convert("RGBA")
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. Resolver tema y fuente rotativa coordinada
        if estilo_rotativo and isinstance(estilo_rotativo, dict):
            cfg_estilo = {
                "fill": tuple(estilo_rotativo.get("fill", (15, 15, 20, 215))),
                "outline": tuple(estilo_rotativo.get("outline", (255, 215, 0, 255))),
                "accent": tuple(estilo_rotativo.get("accent", (255, 230, 40, 255))),
                "name": estilo_rotativo.get("name", "Viral"),
            }
            font_file = estilo_rotativo.get("font") or "arialbd.ttf"
        else:
            estilo_sel = ESTILOS_VIRALES[estilo_idx % len(ESTILOS_VIRALES)]
            cfg_estilo = estilo_sel
            font_file = estilo_sel.get("font") or "arialbd.ttf"

        font_path = os.path.join(ASSETS_DIR, font_file)
        if not os.path.exists(font_path) and os.name == "nt":
            p_win = os.path.join(r"C:\Windows\Fonts", font_file)
            if os.path.exists(p_win):
                font_path = p_win
        if not os.path.exists(font_path):
            font_path = os.path.join(ASSETS_DIR, "arialbd.ttf")

        lineas = [l.strip() for l in hook_txt.split("|") if l.strip()]
        if not lineas:
            lineas = ["NUEVA HISTORIA"]

        # Auto-escala dinámica: fuente grande (78px) para máxima legibilidad en móviles
        fs = 78
        font = None
        max_tw = 0
        while fs >= 46:
            try:
                font = ImageFont.truetype(font_path, fs)
            except Exception:
                font = ImageFont.load_default()
                break
            max_tw = max((draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0] for ln in lineas), default=0)
            if max_tw <= 900 or fs <= 46:
                break
            fs -= 2

        # Ubicación estratégica: Tercio superior de la zona 1:1 de Instagram (zona 1:1 va de y=420 a 1500)
        # y_start = 510 garantiza que el título sea 100% visible en el feed y cuadrícula,
        # pero deja el centro (y=670 a 1450) completamente libre para las caras y expresiones de los personajes.
        line_h = int(fs * 1.3)
        total_h = len(lineas) * line_h
        y_start = 500

        pad_x, pad_y = 55, 25
        box_x1 = max(30, (w - max_tw) // 2 - pad_x)
        box_x2 = min(w - 30, (w + max_tw) // 2 + pad_x)
        box_y1 = y_start - pad_y
        box_y2 = y_start + total_h + pad_y - 10

        draw.rounded_rectangle(
            [box_x1, box_y1, box_x2, box_y2],
            radius=22,
            fill=cfg_estilo["fill"],
            outline=cfg_estilo["outline"],
            width=5,
        )

        for i, ln in enumerate(lineas):
            bb = draw.textbbox((0, 0), ln, font=font)
            tw = bb[2] - bb[0]
            tx = (w - tw) // 2
            ty = y_start + i * line_h
            color_txt = (255, 255, 255, 255) if i == 0 else cfg_estilo["accent"]
            draw.text((tx, ty), ln, font=font, fill=color_txt, stroke_width=7, stroke_fill=(0, 0, 0, 255))

        final_img = Image.alpha_composite(img, overlay).convert("RGB")
        final_img.save(cover_jpg, "JPEG", quality=94)
        print(f"  Portada estilo {cfg_estilo['name']} generada (t={t_captura:.2f}s): {os.path.basename(cover_jpg)}")
        return cover_jpg
    except Exception as e:
        print(f"  Aviso generando miniatura: {e}")
        return cover_jpg if os.path.exists(cover_jpg) else None


def generar_fondo_historia_hd(video_path, cover_path=None):
    """
    Genera un fondo vertical 9:16 (1080x1920) cinematográfico con desenfoque suave,
    viñeta oscura y un botón visual "VER REEL COMPLETO AQUÍ" para garantizar que
    todos los seguidores sepan exactamente dónde tocar.
    """
    src_input = cover_path if (cover_path and os.path.exists(cover_path)) else video_path
    if not src_input or not os.path.exists(src_input):
        return None
    out_bg = src_input + ".story_bg.jpg"
    is_video = str(src_input).lower().endswith(('.mp4', '.mov', '.mkv', '.webm'))
    cmd = [AUTO_REEL.FFMPEG, "-y"]
    if is_video:
        cmd.extend(["-ss", "1.0", "-i", src_input, "-vframes", "1"])
    else:
        cmd.extend(["-i", src_input])
    cmd.extend([
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill",
        out_bg
    ])
    rc, _ = AUTO_REEL.run(cmd, timeout=20)
    if rc == 0 and os.path.exists(out_bg) and os.path.getsize(out_bg) > 5000:
        # Dibujar cartel superior y botón interactivo "VER REEL COMPLETO AQUÍ"
        try:
            from PIL import Image, ImageDraw, ImageFont
            im = Image.open(out_bg).convert("RGB")
            draw = ImageDraw.Draw(im)

            font_path = "assets/arial.ttf"
            for f_cand in ["assets/segoeuib.ttf", "assets/impact.ttf", "assets/trebucbd.ttf", "assets/arial.ttf"]:
                if os.path.exists(f_cand):
                    font_path = f_cand
                    break

            try:
                font_pill = ImageFont.truetype(font_path, 40)
                font_top = ImageFont.truetype(font_path, 34)
            except Exception:
                font_pill = ImageFont.load_default()
                font_top = ImageFont.load_default()

            # 1. Cartel superior limpio (sin emojis que generen cuadritos [])
            txt_top = "NUEVO REEL COMPLETO"
            bbox_top = draw.textbbox((0, 0), txt_top, font=font_top)
            w_top = bbox_top[2] - bbox_top[0]
            x_top = (1080 - w_top) // 2
            draw.text((x_top, 110), txt_top, font=font_top, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))

            # 2. Botón inferior destacado: "VER REEL COMPLETO EN EL PERFIL"
            txt_pill = "VER REEL COMPLETO EN EL PERFIL"
            try:
                font_pill = ImageFont.truetype(font_path, 36)
            except Exception:
                pass
            bbox_pill = draw.textbbox((0, 0), txt_pill, font=font_pill)
            w_pill = bbox_pill[2] - bbox_pill[0]
            h_pill = bbox_pill[3] - bbox_pill[1]

            pill_w = w_pill + 80
            pill_h = h_pill + 40
            pill_x1 = (1080 - pill_w) // 2
            pill_y1 = 1580
            pill_x2 = pill_x1 + pill_w
            pill_y2 = pill_y1 + pill_h

            draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=24, fill=(215, 25, 45), outline=(255, 255, 255), width=4)
            draw.text(((1080 - w_pill) // 2, pill_y1 + 18), txt_pill, font=font_pill, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))

            im.save(out_bg, quality=95)
        except Exception as e_draw:
            print(f"  Aviso agregando texto al fondo de historia: {e_draw}")
        return out_bg
    return cover_path if (cover_path and os.path.exists(cover_path)) else None


def generar_teaser_historia(video_path, dur_seg=15.0):
    """
    Crea un video teaser de 15 segundos con audio optimizado a 1080x1920 para Historias de Instagram.
    Incluye cartel superior '★ NUEVO REEL DISPONIBLE ★' y botón inferior '▶ VER REEL COMPLETO AQUÍ ◀'.
    """
    if not video_path or not os.path.exists(video_path):
        return None
    teaser_path = video_path + ".teaser.mp4"
    overlay_path = video_path + ".overlay_story.png"
    t_clip = min(15.0, float(dur_seg) if dur_seg and float(dur_seg) > 5.0 else 15.0)

    try:
        # 1. Diseñar overlay gráfico transparente de 1080x1920 con tipografía nítida
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        font_path = os.path.join(ASSETS_DIR, "segoeuib.ttf")
        if not os.path.exists(font_path):
            font_path = os.path.join(ASSETS_DIR, "arialbd.ttf")
        if not os.path.exists(font_path) and os.name == "nt":
            font_path = r"C:\Windows\Fonts\arialbd.ttf"

        try:
            font_top = ImageFont.truetype(font_path, 38)
            font_bot = ImageFont.truetype(font_path, 36)
        except Exception:
            font_top = ImageFont.load_default()
            font_bot = ImageFont.load_default()

        # Placa superior limpia (sin símbolos que generen caracteres vacíos [])
        txt_top = "NUEVO REEL COMPLETO"
        bb_top = draw.textbbox((0, 0), txt_top, font=font_top)
        tw_top = bb_top[2] - bb_top[0]
        th_top = bb_top[3] - bb_top[1]
        bx0 = (1080 - tw_top) // 2 - 32
        by0 = 110
        bx1 = bx0 + tw_top + 64
        by1 = by0 + th_top + 24
        # Sombra suave
        draw.rounded_rectangle([bx0 + 2, by0 + 3, bx1 + 2, by1 + 3], radius=18, fill=(0, 0, 0, 140))
        # Placa oscura con borde dorado
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=(15, 20, 35, 230), outline=(255, 215, 0, 255), width=3)
        draw.text(((1080 - tw_top) // 2, by0 + 10), txt_top, fill=(255, 235, 80, 255), font=font_top)

        # Botón inferior: VER REEL COMPLETO EN EL PERFIL
        txt_bot = "VER REEL COMPLETO EN EL PERFIL"
        bb_bot = draw.textbbox((0, 0), txt_bot, font=font_bot)
        tw_bot = bb_bot[2] - bb_bot[0]
        th_bot = bb_bot[3] - bb_bot[1]
        b_bx0 = (1080 - tw_bot) // 2 - 42
        b_by0 = 1585
        b_bx1 = b_bx0 + tw_bot + 84
        b_by1 = b_by0 + th_bot + 32
        # Sombra
        draw.rounded_rectangle([b_bx0 + 3, b_by0 + 4, b_bx1 + 3, b_by1 + 4], radius=26, fill=(0, 0, 0, 160))
        # Botón carmesí vivo con borde blanco
        draw.rounded_rectangle([b_bx0, b_by0, b_bx1, b_by1], radius=26, fill=(220, 25, 45, 240), outline=(255, 255, 255, 255), width=3)
        draw.text(((1080 - tw_bot) // 2, b_by0 + 14), txt_bot, fill=(255, 255, 255, 255), font=font_bot)

        img.save(overlay_path, "PNG")

        # 2. Cortar 15s con audio desde t=2.6s (evita encimar el cartel superior sobre el Hook inicial de 0-2.5s)
        dur_real = AUTO_REEL.get_duration(video_path) or 30.0
        t_start = 2.6 if dur_real >= 18.0 else 0.0
        t_clip = min(15.0, max(5.0, dur_real - t_start))

        filter_str = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2[base];"
            "[base][1:v]overlay=0:0[v]"
        )
        cmd = [
            AUTO_REEL.FFMPEG, "-y",
            "-i", video_path,
            "-i", overlay_path,
            "-ss", f"{t_start:.1f}",
            "-t", f"{t_clip:.1f}",
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-maxrate", "2500k", "-bufsize", "3800k",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            teaser_path
        ]
        rc, _ = AUTO_REEL.run(cmd, timeout=45)
        if rc == 0 and os.path.exists(teaser_path) and os.path.getsize(teaser_path) > 10000:
            # 3. Generar miniatura JPG para instagrapi con FFmpeg (evita depender de MoviePy en la nube)
            thumb_path = teaser_path + ".thumb.jpg"
            cmd_thumb = [
                AUTO_REEL.FFMPEG, "-y",
                "-ss", "0.5",
                "-i", teaser_path,
                "-vframes", "1",
                "-q:v", "2",
                thumb_path
            ]
            AUTO_REEL.run(cmd_thumb, timeout=10)
            return teaser_path
    except Exception as e:
        print(f"  Aviso generando teaser de historia: {e}")
    finally:
        if os.path.exists(overlay_path):
            try:
                os.remove(overlay_path)
            except Exception:
                pass
    return None


# ============================================================
#   BÚSQUEDA Y ANÁLISIS DE TIKTOK
# ============================================================

def preparar_cookies_tiktok_nube():
    env_cookies = os.environ.get("TIKTOK_COOKIES", "").strip()
    if env_cookies:
        os.makedirs(AUTO_REEL.REFS, exist_ok=True)
        with open(AUTO_REEL.COOKIES, "w", encoding="utf-8", newline="\n") as f:
            f.write(env_cookies + "\n")
        print("  Cookies de TikTok cargadas desde variable de entorno.")


def obtener_videos_recientes(max_videos=15, user_url=None, channel_id=None, min_dur_sec=30):
    u_url = (user_url if user_url is not None else TIKTOK_USER_URL).strip()
    c_id = (channel_id if channel_id is not None else TIKTOK_CHANNEL_ID).strip()

    # 1) Intento ultrarrápido con TikWM API (tarda 1-2s en la nube y trae duración para filtrar >= 30s)
    m_user = re.search(r"tiktok\.com/@([A-Za-z0-9_.-]+)", u_url)
    if m_user:
        tk_handle = m_user.group(1)
        try:
            r = requests.post(
                "https://www.tikwm.com/api/user/posts",
                data={"unique_id": f"@{tk_handle}", "count": str(max(max_videos, 20))},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            posts = ((r.json() or {}).get("data") or {}).get("videos") or []
            videos_tkwm = []
            for p in posts:
                vid_id = str(p.get("video_id") or p.get("id") or "").strip()
                dur_v = int(p.get("duration") or 0)
                if not vid_id:
                    continue
                if min_dur_sec and dur_v > 0 and dur_v < min_dur_sec:
                    continue
                videos_tkwm.append({
                    "id": vid_id,
                    "url": f"https://www.tiktok.com/@{tk_handle}/video/{vid_id}",
                    "description": (p.get("title") or "").strip(),
                    "timestamp": int(p.get("create_time") or 0),
                    "duration": dur_v,
                })
            if videos_tkwm:
                print(f"  [TikWM] Se encontraron {len(videos_tkwm)} videos válidos (>={min_dur_sec}s) en @{tk_handle}.")
                return videos_tkwm[:max_videos]
        except Exception as e:
            print(f"  Aviso TikWM user/posts: {e}")

    targets = []
    if c_id:
        targets.append(f"tiktokuser:{c_id}")
    if u_url:
        targets.append(u_url)

    for target in targets:
        for usar_cookies in ([False, True] if os.path.exists(AUTO_REEL.COOKIES) else [False]):
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--flat-playlist",
                "--playlist-end", str(max_videos),
                "--dump-json",
            ]
            if usar_cookies:
                cmd += ["--cookies", AUTO_REEL.COOKIES]
            cmd.append(target)

            tag_c = "con cookies" if usar_cookies else "sin cookies"
            print(f"  Consultando perfil de TikTok ({target[:35]}... {tag_c})...")
            rc, out = AUTO_REEL.run(cmd, timeout=120)
            videos = []
            for line in out.splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                    vid_id = str(obj.get("id") or "").strip()
                    if not vid_id:
                        continue
                    url = obj.get("webpage_url") or obj.get("url") or f"https://www.tiktok.com/@helloword.visuals/video/{vid_id}"
                    desc = (obj.get("description") or obj.get("title") or "").strip()
                    ts = obj.get("timestamp") or 0
                    videos.append({
                        "id": vid_id,
                        "url": url,
                        "description": desc,
                        "timestamp": ts,
                    })
                except Exception:
                    continue

            if videos:
                print(f"  Se encontraron {len(videos)} videos recientes en el perfil.")
                return videos

    print("  Usando navegador Playwright de respaldo para leer el perfil de TikTok...")
    try:
        from playwright.sync_api import sync_playwright
        videos_pw = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            def interceptar_item_list(response):
                if "/api/post/item_list" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        for item in data.get("itemList", []):
                            vid_id = str(item.get("id") or "").strip()
                            if vid_id and not any(v["id"] == vid_id for v in videos_pw):
                                videos_pw.append({
                                    "id": vid_id,
                                    "url": f"https://www.tiktok.com/@helloword.visuals/video/{vid_id}",
                                    "description": (item.get("desc") or "").strip(),
                                    "timestamp": int(item.get("createTime") or 0),
                                })
                    except Exception:
                        pass

            page.on("response", interceptar_item_list)
            page.goto(TIKTOK_USER_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)
            browser.close()

        if videos_pw:
            print(f"  Se encontraron {len(videos_pw)} videos recientes mediante Playwright.")
            return videos_pw[:max_videos]
    except Exception as e:
        print(f"  Aviso en respaldo Playwright: {e}")

    return []


def obtener_info_video_directo(url):
    m = re.search(r"/video/(\d+)", url)
    vid_id = m.group(1) if m else str(int(time.time()))

    # En la nube (GitHub Actions), consultar primero TikWM API (tarda 1 segundo frente a los 15s de yt-dlp)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            r = requests.post(
                "https://www.tikwm.com/api/",
                data={"url": url, "hd": "1"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            info = (r.json() or {}).get("data") or {}
            if info:
                return {
                    "id": str(info.get("id") or vid_id),
                    "url": url,
                    "description": (info.get("title") or "").strip(),
                    "timestamp": int(info.get("create_time") or time.time()),
                }
        except Exception:
            pass

    for usar_cookies in ([False, True] if os.path.exists(AUTO_REEL.COOKIES) else [False]):
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-playlist"]
        if usar_cookies:
            cmd += ["--cookies", AUTO_REEL.COOKIES]
        cmd.append(url)
        rc, out = AUTO_REEL.run(cmd, timeout=60)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                    return {
                        "id": str(obj.get("id") or vid_id),
                        "url": obj.get("webpage_url") or url,
                        "description": (obj.get("description") or obj.get("title") or "").strip(),
                        "timestamp": obj.get("timestamp") or int(time.time()),
                    }
                except Exception:
                    pass

    # Respaldo con TikWM API para extraer título/descripción si yt-dlp fue bloqueado
    try:
        r = requests.post(
            "https://www.tikwm.com/api/",
            data={"url": url, "hd": "1"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        info = (r.json() or {}).get("data") or {}
        if info:
            return {
                "id": str(info.get("id") or vid_id),
                "url": url,
                "description": (info.get("title") or "").strip(),
                "timestamp": int(info.get("create_time") or time.time()),
            }
    except Exception:
        pass

    # Respaldo 2 con LoveTik API si TikWM también falló
    try:
        r_lt = requests.post(
            "https://lovetik.com/api/ajax/search",
            data={"query": url},
            headers={"User-Agent": "Mozilla/5.0", "Origin": "https://lovetik.com", "Referer": "https://lovetik.com/"},
            timeout=15,
        )
        info_lt = r_lt.json() or {}
        if info_lt.get("desc") or info_lt.get("vid"):
            return {
                "id": str(info_lt.get("vid") or vid_id),
                "url": url,
                "description": (info_lt.get("desc") or "").strip(),
                "timestamp": int(time.time()),
            }
    except Exception:
        pass

    return {
        "id": vid_id,
        "url": url,
        "description": "",
        "timestamp": int(time.time()),
    }


def formatear_hook_dos_lineas(texto_limpio):
    if "|" in texto_limpio:
        return "|".join(p.strip().upper() for p in texto_limpio.split("|") if p.strip())
    palabras = texto_limpio.upper().split()
    if not palabras:
        return DEFAULT_HOOK_FALLBACK
    texto_unido = " ".join(palabras)
    if len(texto_unido) <= 22 or len(palabras) <= 3:
        return texto_unido

    palabras_colgantes = {"POR", "DE", "PARA", "EN", "CON", "QUE", "A", "Y", "O", "UN", "UNA", "EL", "LA", "LOS", "LAS", "DEL", "AL", "SU", "SUS", "ERA", "ES", "FUE"}
    mejor_corte = len(palabras) // 2
    menor_dif = 999
    for i in range(1, len(palabras)):
        l1 = " ".join(palabras[:i])
        l2 = " ".join(palabras[i:])
        dif = abs(len(l1) - len(l2))
        if palabras[i - 1] in palabras_colgantes:
            dif += 6
        if dif < menor_dif:
            menor_dif = dif
            mejor_corte = i

    return f"{' '.join(palabras[:mejor_corte])}|{' '.join(palabras[mejor_corte:])}"


def analizar_descripcion_tiktok(raw_desc, series_counts, custom_hook="", hashtags_cuenta=None, semilla="", cuenta_id=""):
    from hook_utils import generar_hook_inteligente, limpiar_texto_descripcion, generar_copy_reel_con_gemini

    hashtags_base = hashtags_cuenta if hashtags_cuenta else DEFAULT_HASHTAGS
    texto_limpio = limpiar_texto_descripcion(raw_desc)

    # Seguridad: si el custom_hook viene con la etiqueta de interfaz, descartarlo para leer el título real
    if custom_hook and any(w in custom_hook.lower() for w in ("automático", "automatico", "inteligente")):
        custom_hook = ""

    if custom_hook:
        serie_base = custom_hook.replace("|", " ").strip().upper()
        hook_txt = formatear_hook_dos_lineas(custom_hook)
    else:
        hook_auto, origen_hook = generar_hook_inteligente(raw_desc, semilla=semilla)
        print(f"  Hook inteligente ({origen_hook}): {hook_auto}")
        serie_base = hook_auto.replace("|", " ").strip().upper()
        hook_txt = formatear_hook_dos_lineas(hook_auto)
        if origen_hook != "descripcion":
            texto_limpio = hook_auto.replace("|", " ").capitalize()

    clave_serie = serie_base.lower()
    parte_num = series_counts.get(clave_serie, 0) + 1

    m_parte = re.search(r"\bparte?\s*(\d+)\b", texto_limpio, re.IGNORECASE)
    es_final = bool(re.search(r"\b(final|desenlace|termina|completa|completo)\b", raw_desc + " " + texto_limpio, re.IGNORECASE))
    tiene_partes = bool(m_parte) and not es_final
    if m_parte:
        parte_num = int(m_parte.group(1))
    else:
        parte_num = 1

    # Generación de Copy SEO con Gemini IA y combinación de hashtags inteligentes
    caption_ig = generar_copy_reel_con_gemini(
        raw_desc,
        hook=hook_txt,
        cuenta_id=cuenta_id,
        hashtags_base=hashtags_base
    )
    serie_archivo = re.sub(r'[<>:"/\\|?*]', "", serie_base)[:40].strip() or "HISTORIA"

    return {
        "serie_key": clave_serie,
        "serie_archivo": serie_archivo,
        "parte": parte_num,
        "tiene_partes": tiene_partes,
        "hook": hook_txt,
        "caption_ig": caption_ig,
    }


# ============================================================
#   SUBIDA A INSTAGRAM CON PORTADA (MEJORA 4)
# ============================================================

def extraer_sessionid_de_archivo(ruta):
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        for line in contenido.splitlines():
            if "sessionid" in line and not line.strip().startswith("#"):
                partes = line.strip().split("\t")
                if len(partes) >= 7 and partes[5] == "sessionid":
                    return urllib.parse.unquote(partes[6].strip())
        m = re.search(r"sessionid\s*[=\t:]\s*([^\s;]+)", contenido)
        if m:
            return urllib.parse.unquote(m.group(1).strip())
    except Exception:
        pass
    return None


def obtener_credenciales_ig(secret_env_name="IG_SESSIONID", historial=None, cuenta_id="frutnovelas776"):
    sid = os.environ.get(secret_env_name, "").strip()
    if sid:
        sid = urllib.parse.unquote(sid)
    if not sid and historial is not None:
        sid = (historial.get("ig_sessions") or {}).get(cuenta_id, "").strip()
    if not sid and secret_env_name == "IG_SESSIONID":
        sid = extraer_sessionid_de_archivo(COOKIES_IG_LOCAL) or extraer_sessionid_de_archivo(COOKIES_IG_ALT)
    user = os.environ.get("IG_USERNAME", "").strip()
    pwd = os.environ.get("IG_PASSWORD", "").strip()
    settings_json = os.environ.get("IG_SETTINGS_JSON", "").strip()
    return sid, user, pwd, settings_json


def generar_comentario_viral(parte_num=1, custom_comment="", tiene_partes=False, hook="", raw_desc="", cuenta_id=""):
    """
    Genera un comentario altamente interactivo y 100% relevante al video:
    - Primero intenta generar con Google Gemini IA analizando la descripción, gancho y nicho de la cuenta (ej: reflexiones cristianas).
    - Si no hay IA o falla, utiliza plantillas contextuales coherentes con la temática de la cuenta.
    - Respeta si la historia es completa (no promete Parte 2 falsamente) o serializada.
    """
    import random
    from hook_utils import generar_comentario_con_gemini, limpiar_texto_descripcion

    # 1) Intentar generar con Google Gemini IA contextual adaptado al nicho
    try:
        gemini_comentario = generar_comentario_con_gemini(raw_desc, hook=hook, parte_num=parte_num, tiene_partes=tiene_partes, cuenta_id=cuenta_id)
        if gemini_comentario and len(gemini_comentario) >= 15:
            print(f"  🤖 Auto-comentario generado con Gemini IA ({cuenta_id}): {gemini_comentario}")
            return gemini_comentario
    except Exception as e:
        print(f"  [Auto-Comentario IA] Fallback a plantillas contextuadas: {e}")

    parte_num = int(parte_num or 1)
    sig_parte = parte_num + 1

    # 2) Fallback Contextual por Nicho
    es_biblia = any(k in (cuenta_id or "").lower() for k in ["biblia", "cristian", "dios", "fe", "reflexion", "amen"])

    if es_biblia:
        plantillas = [
            "Que esta palabra les dé mucha paz hoy. Amén 🙏",
            "A veces Dios permite pruebas para enseñarnos algo más grande. Un abrazo a todos ❤️",
            "Un recordatorio que necesitaba escuchar hoy... Dios los bendiga ✨",
            "La fe mueve montañas cuando más lo necesitamos. Amén 🙏✨",
            "Dios nunca llega tarde ni temprano, siempre a tiempo. Bendiciones a todos 🙏",
            "Que Dios guarde a sus familias en este día. Amén ❤️"
        ]
    elif not tiene_partes:
        plantillas = [
            "Confirmamos que lo del final nadie se lo esperaba? 😂",
            "No sé si ponerme de un lado o del otro sinceramente 💀",
            "Díganme que no fui el único que se quedó pensando en lo que pasó al final 👀",
            "Yo en su lugar creo que no habría aguantado tanto jajaja",
            "El que notó el detalle del principio entendió todo 😂",
            "Digan lo que quieran pero al final tenía razón 😂",
            "Qué opinan ustedes de cómo terminó todo? 🤔",
            "El verdadero giro inesperado al final 😳",
            "Sinceramente me dejó pensando...",
            "A ver quién es el primero que adivina qué pasó ahí 😂"
        ]
    elif parte_num == 1:
        plantillas = [
            "Ya estoy terminando de editar la siguiente parte, en un rato la subo 👀",
            "La que se viene ahora está todavía más fuerte jajaja 😂",
            "Qué creen que pase ahora? 👀 En un rato subo la continuación",
            "No se imaginan lo que pasa en la siguiente parte 😳",
            "Terminando de cargar la continuación, atentos que ya casi sale 🔥"
        ]
    else:
        plantillas = [
            "Esto se puso todavía más intenso de lo que esperaba 😳",
            "Quién más se quedó con la intriga al final? 👀",
            "Ya casi tengo lista la continuación, un momento y la subo 🙏",
            "Ustedes qué habrían hecho en ese momento? 😂",
            "El final de esta parte me dejó sin palabras 💀"
        ]

    default_antiguo = "¿Qué harías tú en su lugar? 😱👇 Sígueme porque ya estoy subiendo la siguiente parte 🔥"
    if custom_comment and (custom_comment.strip() == default_antiguo.strip() or custom_comment.strip().lower() in ("auto", "dinamico", "dinámico")):
        return random.choice(plantillas)

    if custom_comment and "{parte}" in custom_comment.lower():
        if tiene_partes:
            return custom_comment.replace("{parte}", f"PARTE {sig_parte}").replace("{sig}", str(sig_parte))
        else:
            return random.choice(plantillas)

    if custom_comment and custom_comment.strip() != default_antiguo.strip() and random.random() < 0.4:
        return custom_comment

    return random.choice(plantillas)


def huella_video(src, dur):
    """Huella perceptual (dHash 8x8 de 3 fotogramas) con FFmpeg. Gratis, sin librerías extra."""
    import subprocess
    huellas = []
    for frac in (0.15, 0.5, 0.85):
        t = max(0.0, dur * frac)
        try:
            r = subprocess.run(
                [AUTO_REEL.FFMPEG, "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                 "-vf", "scale=9:8:flags=area,format=gray", "-f", "rawvideo", "-"],
                capture_output=True, timeout=60,
            )
            px = r.stdout
            if len(px) < 72:
                continue
            bits = 0
            for fila in range(8):
                for col in range(8):
                    bits = (bits << 1) | (1 if px[fila * 9 + col] > px[fila * 9 + col + 1] else 0)
            huellas.append(bits)
        except Exception:
            pass
    return huellas


def buscar_duplicado(historial, huellas):
    """Devuelve la entrada previa si el video es casi idéntico (promedio <=5 bits y máximo <=12 por fotograma)."""
    if len(huellas) < 3:
        return None
    for prev in historial.get("huellas_videos", []):
        hp = prev.get("h") or []
        if len(hp) != len(huellas):
            continue
        dists = [bin(a ^ b).count("1") for a, b in zip(huellas, hp)]
        if sum(dists) / len(dists) <= 5 and max(dists) <= 12:
            historial["duplicates_blocked"] = int(historial.get("duplicates_blocked", 0)) + 1
            return prev
    return None


def pausar_cuenta(historial, cuenta_id, horas=24):
    """Pausa una cuenta en el piloto automático (tras challenge/sesión caída). Se limpia sola o con /login."""
    if historial is None:
        return
    historial.setdefault("pausa_cuentas", {})[cuenta_id] = time.time() + horas * 3600
    try:
        guardar_historial(historial)
    except Exception:
        pass


def subir_reel_instagram(video_path, caption, cover_path=None, historial=None, cuenta_id="cuenta1", cfg_cuenta=None, chat_id_override=None, parte_num=1, tiene_partes=False, hook="", raw_desc=""):
    """
    Sube el Reel a la cuenta indicada de la granja reutilizando de forma aislada
    su teléfono virtual (device), proxy opcional y su huella persistente en historial_bot.json.
    """
    from instagrapi import Client

    cfg_cuenta = cfg_cuenta or {}
    nombre_cuenta = cfg_cuenta.get("nombre") or f"@{cuenta_id}"
    secret_name = cfg_cuenta.get("secret_sessionid") or "IG_SESSIONID"
    device_cfg = cfg_cuenta.get("device") or IG_DEVICE
    proxy_url = (cfg_cuenta.get("proxy") or "").strip() or None
    chat_id_tg = chat_id_override or cfg_cuenta.get("owner_chat_id") or (historial or {}).get("telegram_chat_id")

    sid, user, pwd, settings_json = obtener_credenciales_ig(secret_name, historial=historial, cuenta_id=cuenta_id)
    if not sid and not (user and pwd):
        msg_err = f"🔑 [{nombre_cuenta}] Falta configurar el Secret `{secret_name}` en tu GitHub Secrets."
        print(f"  {msg_err}")
        enviar_mensaje_telegram(chat_id_tg, msg_err)
        return False

    cl = Client(delay_range=[2.3, 4.8], proxy=proxy_url)
    try:
        cl.set_device(dict(device_cfg))
    except Exception:
        pass

    identities = (historial.get("ig_identities") or {}) if historial is not None else {}
    if historial is not None and sid:
        ig_saved = identities.get(cuenta_id) or (historial.get("ig_identity") if cuenta_id in ("cuenta1", "frutnovelas776") else {}) or {}
        if isinstance(ig_saved, dict) and ig_saved.get("sid_prefix") == sid[:16] and ig_saved.get("settings"):
            try:
                cl.set_settings(ig_saved["settings"])
                print(f"  [{cuenta_id}] Identidad persistente ({device_cfg.get('model', 'Android')}) restaurada.")
            except Exception:
                pass
    elif settings_json:
        try:
            cl.set_settings(json.loads(settings_json))
        except Exception:
            pass

    conectado = False
    error_login = ""
    if sid:
        try:
            print(f"  [{cuenta_id}] Iniciando sesión en Instagram ({nombre_cuenta})...")
            cl.login_by_sessionid(sid)
            conectado = True
            if historial is not None:
                try:
                    settings_actuales = cl.get_settings()
                    settings_limpios = {
                        k: v for k, v in settings_actuales.items()
                        if k in ("uuids", "device_settings", "user_agent", "country", "country_code", "locale", "timezone_offset")
                    }
                    historial.setdefault("ig_identities", {})[cuenta_id] = {
                        "sid_prefix": sid[:16],
                        "settings": settings_limpios,
                    }
                    guardar_historial(historial)
                except Exception:
                    pass
        except Exception as e:
            error_login = str(e)
            print(f"  [{cuenta_id}] Aviso: falló login_by_sessionid principal ({e}).")
            # Auto-respaldo: si en historial_bot.json hay una sesión distinta recién renovada, probarla antes de fallar
            sid_backup = urllib.parse.unquote(((historial or {}).get("ig_sessions") or {}).get(cuenta_id, "").strip())
            if sid_backup and sid_backup != sid:
                try:
                    print(f"  [{cuenta_id}] Probando sesión de respaldo guardada en historial_bot.json...")
                    cl.login_by_sessionid(sid_backup)
                    conectado = True
                    sid = sid_backup
                    print(f"  [{cuenta_id}] ✅ Sesión de respaldo conectada con éxito.")
                except Exception as e_bk:
                    error_login = str(e_bk)
                    print(f"  [{cuenta_id}] Aviso: también falló sesión de respaldo ({e_bk}).")

    if not conectado and user and pwd:
        try:
            cl.login(user, pwd)
            conectado = True
        except Exception as e:
            error_login = str(e)
            print(f"  [{cuenta_id}] ERROR iniciando sesión: {e}")

    if not conectado:
        alerta = (
            f"🚨 ALERTA DE SESIÓN CADUCADA EN {nombre_cuenta}\n\n"
            f"Instagram rechazó la sesión ({error_login[:140]}).\n\n"
            f"🛠️ Cómo renovarla al instante desde Telegram:\n"
            f"1) Envía /login o toca 🔐 Renovar Sesión en el menú del bot.\n"
            f"2) Ingresa tu usuario/contraseña o sessionid (si pide 2FA, responde con el código de 6 dígitos aquí mismo).\n\n"
            f"💡 Alternativa PC: ejecuta EXTRAER_SESION_IG.bat y actualiza `{secret_name}`.\n\n"
            f"⏸️ Pausé {nombre_cuenta} 24 h en el piloto automático (se reactiva sola o al renovar con /login)."
        )
        pausar_cuenta(historial, cuenta_id, 24)
        enviar_mensaje_telegram(chat_id_tg, alerta)
        return False

    print(f"  [{cuenta_id}] Subiendo Reel a Instagram: {os.path.basename(video_path)}...")
    print(f"  [{cuenta_id}] Descripción: {caption}")

    kwargs = {"path": Path(video_path), "caption": caption}
    if cover_path and os.path.exists(cover_path):
        kwargs["thumbnail"] = Path(cover_path)
        print(f"  [{cuenta_id}] Portada personalizada adjunta: {os.path.basename(cover_path)}")

    # Reintento inteligente de subida (hasta 3 intentos con espera de 30s si hay fallo temporal)
    ultimo_err = ""
    for intento in range(1, 4):
        try:
            if intento > 1:
                print(f"  [{cuenta_id}] Reintentando subida a Instagram (intento {intento}/3)...")
            media = cl.clip_upload(**kwargs)
            pk = getattr(media, "pk", None) or getattr(media, "id", "OK")
            code = getattr(media, "code", "")
            link = f"https://www.instagram.com/reel/{code}/" if code else f"ID: {pk}"
            print(f"  [{cuenta_id}] SUBIDO CON ÉXITO A INSTAGRAM: {link}")

            # [Mejora 1, 2 y 4] Auto-Comentario Viral Dinámico + Fijar arriba (Pin Comment)
            comentario_cfg = (cfg_cuenta.get("auto_comment") or "").strip()
            if comentario_cfg.lower() not in ("no", "off", "none", "0") and pk and pk != "OK":
                try:
                    time.sleep(3.5)
                    comentario_auto = generar_comentario_viral(
                        parte_num=parte_num,
                        custom_comment=comentario_cfg,
                        tiene_partes=tiene_partes,
                        hook=hook,
                        raw_desc=raw_desc or caption,
                        cuenta_id=cuenta_id
                    )
                    comment_obj = cl.media_comment(str(pk), comentario_auto)
                    c_pk = getattr(comment_obj, "pk", None) or getattr(comment_obj, "id", None)
                    print(f"  [{cuenta_id}] 💬 Auto-comentario viral publicado: {comentario_auto}")

                    # Fijar el comentario arriba (Pin Comment) para máxima visibilidad
                    if c_pk:
                        try:
                            time.sleep(1.5)
                            try:
                                cl.comment_pin(str(pk), str(c_pk))
                            except TypeError:
                                cl.comment_pin(str(c_pk))
                            print(f"  [{cuenta_id}] 📌 Comentario fijado arriba exitosamente.")
                        except Exception as e_pin:
                            print(f"  [{cuenta_id}] Aviso fijando comentario: {e_pin}")
                except Exception as ec:
                    print(f"  [{cuenta_id}] Aviso publicando auto-comentario: {ec}")

            # [Mejora Viral] Auto-Compartir Reel en Historia: VIDEO real de 15 segundos con audio + Link Sticker
            auto_story = cfg_cuenta.get("auto_story", True)
            if auto_story and pk and pk != "OK":
                try:
                    time.sleep(3.5)
                    from instagrapi.types import StoryLink
                    print(f"  [{cuenta_id}] 📲 Creando video teaser de 15 segundos con audio para la Historia...")
                    media_pk_int = int(cl.media_pk(str(pk)))

                    shortcode = code or ""
                    if not shortcode:
                        try:
                            shortcode = cl.media_code_from_pk(media_pk_int)
                        except Exception:
                            shortcode = ""
                    reel_url = f"https://www.instagram.com/reel/{shortcode}/" if shortcode else (link if str(link).startswith("http") else "https://www.instagram.com/")

                    # 1. Generar video real de 15s con audio y banners visuales ("NUEVO REEL" + "VER REEL COMPLETO")
                    teaser_vid = generar_teaser_historia(video_path, dur_seg=15.0)
                    thumb_vid = (teaser_vid + ".thumb.jpg") if teaser_vid else None
                    story_res = None

                    if teaser_vid and os.path.exists(teaser_vid):
                        print(f"  [{cuenta_id}] 🎬 Subiendo video teaser de 15s a Historias con Link Sticker interactivo...")
                        try:
                            upload_kwargs = {
                                "caption": "👆 Toca para ver el Reel completo",
                                "links": [StoryLink(webUri=reel_url, x=0.5, y=0.85)],
                            }
                            if thumb_vid and os.path.exists(thumb_vid):
                                upload_kwargs["thumbnail"] = Path(thumb_vid)
                            elif cover_path and os.path.exists(cover_path):
                                upload_kwargs["thumbnail"] = Path(cover_path)

                            story_res = cl.video_upload_to_story(
                                Path(teaser_vid),
                                **upload_kwargs
                            )
                        except Exception as e_v_story:
                            print(f"  [{cuenta_id}] Aviso al subir video de historia ({e_v_story}), probando respaldo con foto...")
                            bg_hd = generar_fondo_historia_hd(video_path, cover_path)
                            bg_path = Path(bg_hd) if (bg_hd and os.path.exists(bg_hd)) else (Path(cover_path) if (cover_path and os.path.exists(cover_path)) else None)
                            if bg_path:
                                story_res = cl.photo_upload_to_story(
                                    bg_path,
                                    caption="👆 Toca para ver el Reel completo",
                                    links=[StoryLink(webUri=reel_url, x=0.5, y=0.85)]
                                )
                            if bg_hd and os.path.exists(bg_hd) and bg_hd != cover_path:
                                try:
                                    os.remove(bg_hd)
                                except Exception:
                                    pass
                        finally:
                            if teaser_vid and os.path.exists(teaser_vid):
                                try:
                                    os.remove(teaser_vid)
                                except Exception:
                                    pass
                            if thumb_vid and os.path.exists(thumb_vid):
                                try:
                                    os.remove(thumb_vid)
                                except Exception:
                                    pass
                    else:
                        print(f"  [{cuenta_id}] Aviso: no se pudo generar el video teaser de 15s.")

                    story_pk = getattr(story_res, "pk", None) or getattr(story_res, "id", "OK")
                    print(f"  [{cuenta_id}] ✅ Historia en video de 15s publicada con éxito (Story ID: {story_pk})")
                except Exception as e_story:
                    print(f"  [{cuenta_id}] Aviso al compartir en Historia: {e_story}")

            return link
        except Exception as e:
            ultimo_err = str(e)
            err_low = ultimo_err.lower()
            print(f"  [{cuenta_id}] Error en intento {intento}/3 al subir Reel: {ultimo_err}")

            # Si el error es de sesión caducada / challenge / login_required, no sirve reintentar: avisar al instante
            if any(k in err_low for k in ("login_required", "challenge", "checkpoint", "not logged", "session", "logout", "feedback_required")):
                alerta = (
                    f"🚨 ALERTA EN {nombre_cuenta} (`{secret_name}`)\n\n"
                    f"Instagram bloqueó o pidió verificación durante la subida:\n`{ultimo_err[:180]}`\n\n"
                    f"🛠️ Cómo resolverlo desde Telegram:\n"
                    f"1) Si es verificación/checkpoint, confirma 'Fui yo' en tu app de Instagram.\n"
                    f"2) Luego renueva la sesión desde el bot con /login (soporta 2FA aquí mismo en Telegram) o actualiza `{secret_name}`.\n\n"
                    f"⏸️ Pausé {nombre_cuenta} 24 h en el piloto automático para proteger la cuenta (se reactiva sola o al renovar con /login)."
                )
                pausar_cuenta(historial, cuenta_id, 24)
                enviar_mensaje_telegram(chat_id_tg, alerta)
                return False

            if intento < 3:
                print(f"  [{cuenta_id}] Esperando 30 segundos antes de reintentar...")
                time.sleep(30)

    enviar_mensaje_telegram(
        chat_id_tg,
        f"⚠️ [{nombre_cuenta}] Fallaron los 3 intentos de subida a Instagram por error de red/servidor:\n`{ultimo_err[:180]}`"
    )
    return False


# ============================================================
#   FLUJO PRINCIPAL
# ============================================================

def main():
    modo_solo_render = "--no-upload" in sys.argv
    forzar_ultimo = "--force-latest" in sys.argv
    sincronizar_actuales = "--sync-only" in sys.argv
    modo_previa = "--previa" in sys.argv or os.environ.get("ACTION_MODE", "").strip().lower() == "preview"
    auto_diario = "--auto-diario" in sys.argv
    if "--reporte" in sys.argv:
        import reporte_diario
        return reporte_diario.main()
    url_manual = os.environ.get("MANUAL_URL", "").strip()
    hook_manual = os.environ.get("MANUAL_HOOK", "").strip()
    modo_marca = os.environ.get("WATERMARK_POS", "auto").strip() or "auto"
    cuenta_objetivo = os.environ.get("TARGET_ACCOUNT", "frutnovelas776").strip().lower() or "frutnovelas776"
    # Compatibilidad con alias antiguos
    if cuenta_objetivo == "cuenta1":
        cuenta_objetivo = "frutnovelas776"
    elif cuenta_objetivo == "cuenta2":
        cuenta_objetivo = "novelas_frutosass"

    cuenta_cli_explicita = False
    for i, arg in enumerate(sys.argv):
        if arg == "--url" and i + 1 < len(sys.argv):
            url_manual = sys.argv[i + 1].strip()
        elif arg == "--hook" and i + 1 < len(sys.argv):
            hook_manual = sys.argv[i + 1].strip()
        elif arg == "--marca" and i + 1 < len(sys.argv):
            modo_marca = sys.argv[i + 1].strip()
        elif arg == "--cuenta" and i + 1 < len(sys.argv):
            cuenta_objetivo = sys.argv[i + 1].strip().lower()
            cuenta_cli_explicita = True
        elif arg == "--chat-id" and i + 1 < len(sys.argv):
            try:
                chat_id_cli = int(sys.argv[i + 1].strip())
            except Exception:
                chat_id_cli = None
    if "chat_id_cli" not in locals():
        chat_id_cli = None

    if auto_diario and not cuenta_cli_explicita and not url_manual:
        try:
            import planificador
            cid_plan, motivo_plan = planificador.elegir_cuenta(marcar_intento=True)
            print(f"  [Planificador Inteligente] {motivo_plan}")
            if not cid_plan:
                return 0
            cuenta_objetivo = cid_plan
        except Exception as e_plan:
            print(f"  Aviso consultando planificador: {e_plan}")

    print("=" * 65)
    print(f"  GRANJA TIKTOK -> AUTO_REEL -> INSTAGRAM ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 65)

    preparar_cookies_tiktok_nube()
    granja = cargar_granja()
    historial = cargar_historial()
    procesados = set(str(x) for x in historial.get("processed_ids", []))
    series_counts = historial.get("series_counts", {})

    # Si lo llama el escuchador de Telegram (--chat-id), NO leer la bandeja de Telegram ni la cola
    # (el escuchador ya está leyendo Telegram en vivo; leerla aquí le robaría los mensajes)
    llamado_desde_escuchador = bool(chat_id_cli)

    # 1) Si no pasó link directo por botón, revisar si mandó link a su Bot de Telegram (Mejora 1)
    if not url_manual and not sincronizar_actuales and not llamado_desde_escuchador and not auto_diario:
        tg_url, tg_hook, tg_cuenta = revisar_bandeja_telegram(historial)
        if tg_url:
            url_manual = tg_url
            if tg_hook and not hook_manual:
                hook_manual = tg_hook
            if tg_cuenta:
                cuenta_objetivo = tg_cuenta
            print(f"  Link recibido desde Telegram para [{cuenta_objetivo.upper()}]: {url_manual}")
    elif url_manual == "__PENDING__":
        pend = historial.get("telegram_pending_video") or {}
        url_manual = (pend.get("url") or "").strip()
        if not hook_manual:
            hook_manual = (pend.get("hook") or "").strip()
        print(f"  Recuperando video pendiente de Telegram para [{cuenta_objetivo.upper()}]: {url_manual}")

    # 2) Si tampoco había mensaje nuevo en Telegram, revisar cola_videos.txt (Mejora 2)
    viene_de_cola = False
    raw_cola_url = ""
    if not url_manual and not sincronizar_actuales and not llamado_desde_escuchador:
        cola = leer_cola_videos()
        if auto_diario:
            cola = [c for c in cola if not re.match(r"^(todas|cuenta\d+)\s+https?://", c["url"], re.IGNORECASE)]
        if cola:
            raw_cola_url = cola[0]["url"]
            m_c = re.match(r"^(todas|cuenta\d+)\s+(https?://.+)$", raw_cola_url, re.IGNORECASE)
            if m_c:
                cuenta_objetivo = m_c.group(1).lower()
                url_manual = m_c.group(2).strip()
            else:
                url_manual = raw_cola_url
            if cola[0]["hook"] and not hook_manual:
                hook_manual = cola[0]["hook"]
            viene_de_cola = True
            print(f"  Tomando siguiente video de cola_videos.txt ({len(cola)} en cola) para [{cuenta_objetivo.upper()}]: {url_manual}")

    # 3) Determinar el video a procesar (usando la fuente de TikTok propia de la cuenta seleccionada)
    cfg_seleccionada = granja.get(cuenta_objetivo) or granja.get("cuenta1") or {}
    solo_telegram_y_cola = "--only-queue-or-tg" in sys.argv
    if url_manual:
        print(f"  Procesando video elegido para [{cuenta_objetivo.upper()}] -> {url_manual}")
        elegido = obtener_info_video_directo(url_manual)
        if not modo_previa and not modo_solo_render and cuenta_objetivo not in ("todas", "all"):
            vid_chk = str(elegido.get("id") or "")
            for h_item in (historial.get("history") or []):
                if str(h_item.get("id") or "") == vid_chk and cuenta_objetivo in (h_item.get("accounts") or []) and h_item.get("ig_link"):
                    chat_dup = chat_id_cli or cfg_seleccionada.get("owner_chat_id") or historial.get("telegram_chat_id")
                    msg_dup = (
                        f"🛡️ <b>Escudo Anti-Duplicados:</b> Este video (ID <code>{vid_chk}</code>) ya fue publicado anteriormente en <b>@{cuenta_objetivo}</b>.\n\n"
                        f"🔗 <b>Publicación existente:</b>\n{h_item.get('ig_link')}\n\n"
                        f"💡 <i>Si deseas subirlo a otra cuenta distinta de tu granja, selecciónala en los botones.</i>"
                    )
                    print(f"  [Anti-Duplicados] Video {vid_chk} ya publicado en @{cuenta_objetivo}. Omitiendo doble subida.")
                    if chat_dup:
                        enviar_mensaje_telegram(chat_dup, msg_dup)
                    if viene_de_cola:
                        quitar_de_cola(raw_cola_url or url_manual)
                    return 0
        pendientes = [elegido]
    elif solo_telegram_y_cola:
        print("  Revisión en la nube: No enviaste links nuevos a Telegram ni hay pendientes en cola_videos.txt. Saliendo sin descargar nada.")
        return 0
    else:
        videos = obtener_videos_recientes(
            max_videos=30 if sincronizar_actuales else 15,
            user_url=cfg_seleccionada.get("tiktok_source_url") or TIKTOK_USER_URL,
            channel_id=cfg_seleccionada.get("tiktok_channel_id") or "",
        )
        if not videos:
            print("  No se obtuvieron videos en esta revisión. Saliendo.")
            if llamado_desde_escuchador:
                enviar_mensaje_telegram(
                    chat_id_cli,
                    f"⚠️ [@{cuenta_objetivo}] No pude leer videos de {cfg_seleccionada.get('tiktok_source_url', '')}. Reintento en el próximo turno."
                )
            return 0

        if sincronizar_actuales:
            nuevos_sync = 0
            for v in videos:
                if v["id"] not in procesados:
                    historial.setdefault("processed_ids", []).append(v["id"])
                    procesados.add(v["id"])
                    nuevos_sync += 1
            guardar_historial(historial)
            print(f"  Sincronización completada: {nuevos_sync} videos marcados como vistos (Total: {len(procesados)}).")
            return 0

        if forzar_ultimo:
            pendientes = [videos[0]]
        else:
            pendientes = [v for v in videos if v["id"] not in procesados]
            # Varias fuentes de TikTok por cuenta: "tiktok_sources": [url1, url2, ...] (se prueban en orden)
            extras = [u.strip() for u in (cfg_seleccionada.get("tiktok_sources") or []) if u and u.strip()]
            fuente_actual = (cfg_seleccionada.get("tiktok_source_url") or "").strip()
            if not pendientes and auto_diario:
                for u_extra in extras:
                    if u_extra == fuente_actual:
                        continue
                    print(f"  Sin videos nuevos; probando otra fuente de la cuenta: {u_extra}")
                    videos_x = obtener_videos_recientes(max_videos=15, user_url=u_extra, channel_id="")
                    pendientes = [v for v in videos_x if v["id"] not in procesados]
                    if pendientes:
                        break

        if not pendientes:
            print("  No hay videos pendientes en cola ni nuevos en el perfil.")
            if auto_diario:
                enviar_mensaje_telegram(
                    cfg_seleccionada.get("owner_chat_id") or historial.get("telegram_chat_id"),
                    f"🚨 [@{cuenta_objetivo}] Le tocaba publicar pero NO quedan videos nuevos (+30s). "
                    f"Agrega links a cola_videos.txt o configura `tiktok_source_url` para esa cuenta."
                )
            if llamado_desde_escuchador:
                enviar_mensaje_telegram(
                    chat_id_cli,
                    f"ℹ️ [@{cuenta_objetivo}] Ya subí todos los videos recientes (+30s) de {cfg_seleccionada.get('tiktok_source_url', '')}. "
                    f"Espero a que ese canal publique nuevos."
                )
            return 0

        pendientes.sort(key=lambda x: (x.get("timestamp") or 0, x["id"]))
        elegido = pendientes[0]
        if auto_diario and len(pendientes) <= 3:
            enviar_mensaje_telegram(
                cfg_seleccionada.get("owner_chat_id") or historial.get("telegram_chat_id"),
                f"⚠️ Suministro bajo: después de este Reel quedan solo {len(pendientes) - 1} video(s) nuevo(s) para @{cuenta_objetivo}. "
                f"Agrega fuentes de TikTok o links a la cola."
            )

    vid_id = elegido["id"]
    url = elegido["url"]
    raw_desc = elegido["description"]

    info = analizar_descripcion_tiktok(
        raw_desc,
        series_counts,
        custom_hook=hook_manual,
        hashtags_cuenta=cfg_seleccionada.get("hashtags_default"),
        semilla=vid_id,
        cuenta_id=cuenta_objetivo,
    )
    print("-" * 65)
    print(f"  ID TikTok  : {vid_id}")
    print(f"  URL        : {url}")
    print(f"  Desc orig. : {raw_desc}")
    print(f"  Hook Video : {info['hook']}")
    print(f"  Caption IG : {info['caption_ig']}")
    print(f"  Modo Marca : {modo_marca}")
    print("-" * 65)

    os.makedirs(AUTO_REEL.REFS, exist_ok=True)
    os.makedirs(AUTO_REEL.OUT_DIR, exist_ok=True)

    chat_id_tg = chat_id_cli or cfg_seleccionada.get("owner_chat_id") or historial.get("telegram_chat_id")

    # [Mejora 3] Pre-Flight Check: Verificar credenciales de Instagram ANTES de renderizar
    cuentas_a_verificar = [cuenta_objetivo] if cuenta_objetivo not in ("todas", "all") else [k for k, v in granja.items() if v.get("activa", False)]
    for cid_chk in cuentas_a_verificar[:1]:
        cfg_chk = granja.get(cid_chk) or {}
        sec_name = cfg_chk.get("secret_sessionid") or "IG_SESSIONID"
        sid_chk, u_chk, p_chk, _ = obtener_credenciales_ig(sec_name, historial=historial, cuenta_id=cid_chk)
        if not sid_chk and not (u_chk and p_chk):
            msg_err = f"🚨 [@{cid_chk}] Sesión de Instagram no disponible en `{sec_name}`. Abortando para no gastar minutos."
            print(f"  {msg_err}")
            if chat_id_tg:
                enviar_mensaje_telegram(chat_id_tg, msg_err)
            return 1

    # Paso A: Descargar con AUTO_REEL (usando vid_id para cachear links cortos vt.tiktok.com)
    slug = AUTO_REEL.slug_from_url(url, vid_id=vid_id)
    src = AUTO_REEL.download(url, slug)
    if not src:
        msg_e = f"❌ No se pudo descargar el video de TikTok ({url}). Verifica que el link sea válido."
        print(f"  {msg_e}")
        enviar_mensaje_telegram(chat_id_tg, msg_e)
        return 1

    # Paso B: Medir duración y metadatos del video fuente (Quality Gate)
    v_meta = AUTO_REEL.get_video_meta(src) if hasattr(AUTO_REEL, "get_video_meta") else {}
    dur = (v_meta.get("duration") if v_meta else None) or AUTO_REEL.get_duration(src)
    if not dur:
        msg_e = "❌ No se pudo medir la duración del video con FFmpeg."
        print(f"  {msg_e}")
        enviar_mensaje_telegram(chat_id_tg, msg_e)
        return 1
    print(f"  Duración medida: {dur:.1f} s | Vertical: {v_meta.get('is_vertical', True)} | Audio: {v_meta.get('has_audio', True)}")

    # Detección de duplicados por contenido (aunque venga de otro canal o con otro ID)
    huellas = huella_video(src, dur)
    dup = buscar_duplicado(historial, huellas)
    if dup:
        aviso_dup = f"♻️ Este video es casi idéntico a uno ya publicado (ID {dup.get('id')}). "
        if auto_diario:
            if vid_id not in procesados:
                historial.setdefault("processed_ids", []).insert(0, vid_id)
            guardar_historial(historial)
            if viene_de_cola:
                quitar_de_cola(raw_cola_url or url_manual)
            enviar_mensaje_telegram(chat_id_tg, aviso_dup + "Lo salté y probaré con otro en el próximo turno.")
            print("  Duplicado por contenido: omitido.")
            return 0
        enviar_mensaje_telegram(chat_id_tg, aviso_dup + "Como lo pediste tú, continúo igualmente.")
    msg_render_id = enviar_mensaje_telegram(
        chat_id_tg,
        f"📥 Video descargado ({dur:.0f}s) | Hook: {info['hook']}\n🎬 Renderizando 1080x1920 con FFmpeg en la nube..."
    )

    # Determinar qué cuentas de la granja van a recibir este video (filtrando por dueño si viene de Telegram)
    cuenta_fallback = next((k for k, v in granja.items() if v.get("activa", False)), next(iter(granja.keys()), "frutnovelas776"))
    if cuenta_objetivo in ("todas", "all"):
        if chat_id_cli:
            cuentas_a_subir = [
                k for k, v in granja.items()
                if v.get("activa", False) and int(v.get("owner_chat_id") or 8804356608) == int(chat_id_cli)
            ]
        else:
            cuentas_a_subir = [k for k, v in granja.items() if v.get("activa", False)]
        if not cuentas_a_subir:
            cuentas_a_subir = [cuenta_fallback]
    else:
        if cuenta_objetivo in granja:
            cuentas_a_subir = [cuenta_objetivo]
        else:
            match_alias = next(
                (k for k, v in granja.items() if (v.get("nombre") or "").strip().lstrip("@").lower() == cuenta_objetivo.lstrip("@")),
                None
            )
            cuentas_a_subir = [match_alias or cuenta_fallback]

    links_publicados = []
    archivos_temporales = [src]

    for idx_c, cid in enumerate(cuentas_a_subir):
        cfg_c = granja.get(cid) or {}
        estilo = cfg_c.get("estilo_unico") or {}
        cta_cuenta = cfg_c.get("cta") or AUTO_REEL.CTA

        # Obtenemos el estilo rotativo dinámico para este post de esta cuenta (anti-repetición)
        estilo_post = obtener_siguiente_estilo(cid, historial)
        print(f"\n  >>> Procesando copia única para [{cid.upper()}] ({cfg_c.get('nombre', cid)}) | Estilo: {estilo_post['name']} ({estilo_post['font']}, {estilo_post['accent_hex']})...")
        nombre = f"REEL_{cid}_{info['serie_archivo']}" + ("" if info["parte"] in (0, 1) else f" parte {info['parte']}")
        out_path = os.path.join(AUTO_REEL.OUT_DIR, nombre + ".mp4")
        archivos_temporales.append(out_path)

        ok = AUTO_REEL.render(
            src, dur, info["hook"], cta_cuenta, out_path,
            zoom_w=estilo.get("zoom_w", 1090),
            zoom_h=estilo.get("zoom_h", 1939),
            cta_color=estilo_post["accent_hex"],
            font_file=estilo_post["font"],
            speed_factor=estilo.get("speed_factor", 1.0),
            trim_start=estilo.get("trim_start", 0.0),
            is_vertical=v_meta.get("is_vertical", True),
            has_audio=v_meta.get("has_audio", True),
        )
        if not ok:
            print(f"  [{cid}] ERROR durante el renderizado con FFmpeg.")
            continue

        badge_cuenta = cfg_c.get("nombre") or cid
        if aplicar_placa_marca(out_path, modo_marca=modo_marca, badge_text=badge_cuenta):
            AUTO_REEL.limpiar_metadatos(out_path)
        # Portada con la identidad visual rotativa coordinada con el video
        cover_jpg = generar_portada_reel(
            out_path, info["hook"], dur,
            estilo_idx=idx_c, raw_video_path=src,
            cfg_cuenta=cfg_c, cuenta_id=cid,
            estilo_rotativo=estilo_post
        )
        archivos_temporales.extend([cover_jpg, out_path + ".jpg"])

        if modo_previa:
            print(f"  🎬 MODO PREVIA: Enviando video terminado a Telegram ({chat_id_tg})...")
            caption_previa = (
                f"╔════════════════════════════════╗\n"
                f"   🎬 VISTA PREVIA LISTA PARA REVISAR\n"
                f"╚════════════════════════════════╝\n"
                f"📌 <b>Hook Personalizado:</b> {info['hook']}\n"
                f"⏱️ <b>Duración:</b> {dur:.1f}s | <b>Formato:</b> 1080x1920 HD\n"
                f"🎯 <b>Portada:</b> Frame Hunter seleccionada\n"
                f"🔗 <b>Fuente:</b> {url}\n\n"
                f"👇 <b>¿Te gusta el resultado? Elige la cuenta para publicarlo:</b>"
            )
            emojis_btn = ["🍓", "🍍", "🍉", "🍇", "🍊", "🍒", "🥝", "🍑", "🥭", "🍏"]
            cuentas_disp = [
                (k_c, v_c) for k_c, v_c in granja.items()
                if v_c.get("activa", False) and (not chat_id_tg or str(v_c.get("owner_chat_id", "")) == str(chat_id_tg))
            ]
            if not cuentas_disp:
                cuentas_disp = [(k_c, v_c) for k_c, v_c in granja.items() if v_c.get("activa", False)]
            if not cuentas_disp:
                cuentas_disp = list(granja.items())[:4]

            botones_aprobacion = []
            fila_actual = []
            for idx_b, (k_c, v_c) in enumerate(cuentas_disp):
                em = emojis_btn[idx_b % len(emojis_btn)]
                nom_b = v_c.get("nombre") or f"@{k_c}"
                fila_actual.append({"text": f"{em} {nom_b}", "callback_data": f"subir:{k_c}"})
                if len(fila_actual) == 2:
                    botones_aprobacion.append(fila_actual)
                    fila_actual = []
            if fila_actual:
                botones_aprobacion.append(fila_actual)
            botones_aprobacion.append([{"text": "🗑️ Descartar Video", "callback_data": "cancelar"}])
            ok_tg = enviar_video_telegram(
                chat_id_tg,
                out_path,
                caption=caption_previa,
                botones=botones_aprobacion
            )
            borrar_mensaje_telegram(chat_id_tg, msg_render_id)
            if ok_tg:
                print("  ✅ Video de vista previa enviado a Telegram con éxito.")
            else:
                print("  ⚠️ Falló el envío del video a Telegram.")
            return 0

        if not modo_solo_render:
            if idx_c > 0:
                print("  Pausa de seguridad entre cuentas de la granja (12 s)...")
                time.sleep(12)

            # Espaciador Anti-Spam (Cooldown) por cuenta
            last_uploads = historial.setdefault("last_upload_by_account", {})
            last_ts = last_uploads.get(cid)
            if last_ts:
                try:
                    elapsed = time.time() - float(last_ts)
                    if 0 <= elapsed < 120:
                        wait_s = int(120 - elapsed)
                        print(f"  ⏳ Cooldown anti-spam para {cid}: esperando {wait_s}s...")
                        time.sleep(wait_s)
                    elif 0 <= elapsed < 900 and chat_id_tg:
                        mins = max(1, int(elapsed // 60))
                        enviar_mensaje_telegram(
                            chat_id_tg,
                            f"⏳ Aviso anti-spam: {cfg_c.get('nombre', cid)} publicó hace {mins} min. Se recomienda esperar 15-20 min entre Reels por cuenta para cuidar el alcance."
                        )
                except Exception:
                    pass

            # Mejora #13: Verificar límite de publicaciones por cuenta por día (Anti-Spam)
            max_dia = int(cfg_c.get("max_posts_dia") or cfg_c.get("posts_por_dia") or 15)
            hoy_str = datetime.now().strftime("%Y-%m-%d")
            posts_hoy_cuenta = sum(
                1 for h in (historial.get("history") or [])
                if cid in (h.get("accounts") or []) and str(h.get("date", "")).startswith(hoy_str) and h.get("ig_link")
            )
            if posts_hoy_cuenta >= max_dia:
                alerta_limite = f"🛑 @{cid} ya alcanzó su límite diario de {max_dia} posts hoy ({posts_hoy_cuenta}/{max_dia}). Subida omitida para cuidar la cuenta."
                print(f"  {alerta_limite}")
                if chat_id_tg:
                    enviar_mensaje_telegram(chat_id_tg, alerta_limite)
                continue

            ig_link = subir_reel_instagram(
                out_path, info["caption_ig"], cover_path=cover_jpg,
                historial=historial, cuenta_id=cid, cfg_cuenta=cfg_c,
                chat_id_override=chat_id_tg,
                parte_num=info.get("parte", 1),
                tiene_partes=info.get("tiene_partes", False),
                hook=info.get("hook", ""),
                raw_desc=raw_desc,
            )
            if ig_link:
                last_uploads[cid] = time.time()
                first_seen = historial.setdefault("account_first_seen", {})
                if cid not in first_seen:
                    first_seen[cid] = time.time()
                links_publicados.append(f"• {cfg_c.get('nombre', cid)}: {ig_link}")
                if chat_id_tg:
                    caption_subido = (
                        f"🎉 <b>¡Reel publicado en {cfg_c.get('nombre', cid)}!</b>\n\n"
                        f"📌 <b>Hook:</b> {info['hook']}\n"
                        f"🔗 <b>Enlace IG:</b> {ig_link}\n\n"
                        f"📝 <b>Copy:</b>\n{info['caption_ig']}\n\n"
                        f"📥 <i>Aquí tienes tu copia en HD guardada en Telegram.</i>"
                    )
                    ok_envio = enviar_video_telegram(chat_id_tg, out_path, caption=caption_subido)
                    if not ok_envio and chat_id_tg:
                        enviar_mensaje_telegram(
                            chat_id_tg,
                            f"🎉 <b>¡Reel publicado en {cfg_c.get('nombre', cid)}!</b>\n\n"
                            f"📌 <b>Hook:</b> {info['hook']}\n"
                            f"🔗 <b>Enlace IG:</b> {ig_link}\n\n"
                            f"📝 <b>Copy:</b>\n{info['caption_ig']}\n\n"
                            f"ℹ️ <i>(El archivo pesaba más de 50 MB para enviarlo como video en Telegram, pero ya está publicado y 100% visible en tu Instagram).</i>"
                        )
            else:
                if chat_id_tg:
                    caption_fallo = (
                        f"⚠️ <b>No se pudo subir automáticamente a {cfg_c.get('nombre', cid)}</b>\n\n"
                        f"📌 <b>Hook:</b> {info['hook']}\n"
                        f"📝 <b>Copy:</b>\n{info['caption_ig']}\n\n"
                        f"📲 <b>¡Usa el Plan B en 5 segundos!</b>\n"
                        f"1) Toca este video y dale a <b>Compartir ➡️ Instagram</b>.\n"
                        f"2) Pega el texto de arriba y pulsa Publicar."
                    )
                    enviar_video_telegram(chat_id_tg, out_path, caption=caption_fallo)
        else:
            links_publicados.append(f"• {cfg_c.get('nombre', cid)}: SOLO_RENDER ({out_path})")

    borrar_mensaje_telegram(chat_id_tg, msg_render_id)

    if not links_publicados:
        return 1

    if viene_de_cola:
        quitar_de_cola(raw_cola_url or url_manual)

    resumen_links = "\n".join(links_publicados)
    # Solo enviar resumen global si se publicó en lote a más de 1 cuenta (evita duplicar la notificación individual)
    if chat_id_tg and not modo_solo_render and len(links_publicados) > 1:
        enviar_mensaje_telegram(
            chat_id_tg,
            f"✅ ¡Reel publicado en la Granja ({len(links_publicados)} cuentas)!\n\n📌 Hook: {info['hook']}\n📝 Copy: {info['caption_ig']}\n\n🔗 Publicaciones:\n{resumen_links}"
        )

    if vid_id not in procesados:
        historial.setdefault("processed_ids", []).insert(0, vid_id)
    historial["processed_ids"] = historial.get("processed_ids", [])[:500]
    if huellas:
        # Mejora #7: Guardado persistente de huellas enriquecidas con timestamp
        historial.setdefault("huellas_videos", []).insert(0, {
            "id": vid_id,
            "h": huellas,
            "ts": int(time.time()),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        historial["huellas_videos"] = historial["huellas_videos"][:500]
    series_counts[info["serie_key"]] = info["parte"]
    historial["series_counts"] = series_counts
    historial.setdefault("history", []).insert(0, {
        "id": vid_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": raw_desc,
        "hook": info["hook"],
        "caption_ig": info["caption_ig"],
        "accounts": cuentas_a_subir,
        "ig_link": " | ".join(links_publicados),
    })
    historial["history"] = historial["history"][:200]
    guardar_historial(historial)

    if os.environ.get("GITHUB_ACTIONS") == "true":
        for f_tmp in archivos_temporales:
            if f_tmp and os.path.exists(f_tmp):
                try:
                    os.remove(f_tmp)
                except Exception:
                    pass

    print("=" * 65)
    print("  PROCESO COMPLETADO CON ÉXITO")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
