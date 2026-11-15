# -*- coding: utf-8 -*-
"""
escuchador_telegram_nube.py — Corre en los servidores de GitHub Actions en bucle continuo
haciendo long-polling en tiempo real a Telegram (@Maykel0007_bot).
Así tu bot de Telegram responde en MENOS DE 1 SEGUNDO con tu PC totalmente apagada.

Incluye:
- Modo Multi-Usuario por chat_id (tú y tu amiga tienen cuentas y botones 100% separados).
- [Mejora 1] Auto-Comentario automático en cada Reel recién subido (configurable por cuenta).
- [Mejora 2] Envío por Lote: pega 2, 5 o 10 links de TikTok juntos en un solo mensaje y el bot
  los procesa y sube todos en orden (numerando PARTE 1, PARTE 2... si le pones un Hook base).
- [Mejora 4] Panel interactivo "⚙️ Configurar Cuentas" en Telegram para cambiar el CTA amarillo,
  los Hashtags, el Auto-Comentario o quitar una cuenta sin tocar código.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_PATH = os.path.join(BASE, "historial_bot.json")
GRANJA_PATH = os.path.join(BASE, "cuentas_granja.json")
TOKEN_TG_LOCAL = r"C:\Users\piade\Desktop\Descargar videos gratis\token_insta.txt"

OWNER_DEFAULT_CHAT_ID = 8804356608
DEFAULT_AUTO_COMMENT = "¿Qué harías tú en su lugar? 😱👇 Sígueme porque ya estoy subiendo la siguiente parte 🔥"

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
if not TOKEN and os.path.exists(TOKEN_TG_LOCAL):
    try:
        TOKEN = open(TOKEN_TG_LOCAL, encoding="utf-8").read().strip()
    except Exception:
        pass

API = f"https://api.telegram.org/bot{TOKEN}"

DISPOSITIVOS_POOL = [
    {"android_version": 33, "android_release": "13", "dpi": "420dpi", "resolution": "1080x2400", "manufacturer": "motorola", "device": "bangkk", "model": "moto g84 5G", "cpu": "qcom"},
    {"android_version": 32, "android_release": "12", "dpi": "450dpi", "resolution": "1080x2340", "manufacturer": "samsung", "device": "o1s", "model": "Galaxy S21 5G", "cpu": "exynos2100"},
    {"android_version": 34, "android_release": "14", "dpi": "440dpi", "resolution": "1080x2400", "manufacturer": "xiaomi", "device": "garnet", "model": "Redmi Note 13 Pro", "cpu": "qcom"},
    {"android_version": 33, "android_release": "13", "dpi": "420dpi", "resolution": "1080x2400", "manufacturer": "google", "device": "panther", "model": "Pixel 7", "cpu": "tensor"},
    {"android_version": 31, "android_release": "12", "dpi": "480dpi", "resolution": "1080x2400", "manufacturer": "oneplus", "device": "lemonade", "model": "OnePlus 9", "cpu": "qcom"},
    {"android_version": 34, "android_release": "14", "dpi": "450dpi", "resolution": "1080x2340", "manufacturer": "samsung", "device": "dm1q", "model": "Galaxy S23", "cpu": "qcom"},
    {"android_version": 34, "android_release": "14", "dpi": "440dpi", "resolution": "1220x2712", "manufacturer": "xiaomi", "device": "duchamp", "model": "POCO X6 Pro 5G", "cpu": "mt6897"},
    {"android_version": 33, "android_release": "13", "dpi": "480dpi", "resolution": "1080x2412", "manufacturer": "realme", "device": "RE58B2", "model": "RMX3771", "cpu": "mt6877"},
    {"android_version": 34, "android_release": "14", "dpi": "420dpi", "resolution": "1080x2412", "manufacturer": "nothing", "device": "Pong", "model": "A065", "cpu": "qcom"},
    {"android_version": 33, "android_release": "13", "dpi": "420dpi", "resolution": "1080x2520", "manufacturer": "sony", "device": "pdx235", "model": "XQ-DC54", "cpu": "qcom"},
    {"android_version": 34, "android_release": "14", "dpi": "420dpi", "resolution": "1080x2400", "manufacturer": "vivo", "device": "V2307", "model": "V29 5G", "cpu": "qcom"},
    {"android_version": 33, "android_release": "13", "dpi": "440dpi", "resolution": "1080x2400", "manufacturer": "oppo", "device": "OP5958L1", "model": "CPH2531", "cpu": "mt6877"},
]

ICONOS_CUENTAS = ["🍓", "🍍", "🍉", "🍇", "🍊", "🥭", "🍒", "🥝", "🍑", "🍏", "🫐", "🍋"]


def cargar_historial():
    if os.path.exists(HISTORIAL_PATH):
        try:
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"telegram_last_update_id": 0, "telegram_chat_id": None, "users_state": {}}


def guardar_historial(data):
    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def estado_usuario(historial, chat_id):
    users = historial.setdefault("users_state", {})
    key = str(chat_id)
    if key not in users or not isinstance(users[key], dict):
        users[key] = {
            "pending_video": None,
            "waiting_hook": False,
            "waiting_account": False,
            "waiting_cfg_field": None,  # {"cuenta": cid, "campo": "cta"|"hashtags"|"comment"}
        }
    return users[key]


def cargar_granja():
    if os.path.exists(GRANJA_PATH):
        try:
            with open(GRANJA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cuentas": {}}


def guardar_granja(data):
    with open(GRANJA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cuentas_del_usuario(chat_id):
    """Devuelve solo las cuentas activas que pertenecen a este chat_id de Telegram."""
    granja_data = cargar_granja().get("cuentas") or {}
    propias = {}
    for k, v in granja_data.items():
        if not v.get("activa", True):
            continue
        owner = int(v.get("owner_chat_id") or OWNER_DEFAULT_CHAT_ID)
        if owner == int(chat_id):
            propias[k] = v
    return propias


def sincronizar_git():
    """Guarda los cambios de cuentas_granja.json e historial_bot.json en el repositorio privado."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "user.name", "AutoReel Bot"], cwd=BASE)
            subprocess.run(["git", "config", "user.email", "bot@autoreel.local"], cwd=BASE)
            subprocess.run(["git", "add", "cuentas_granja.json", "historial_bot.json"], cwd=BASE)
            subprocess.run(["git", "commit", "-m", "chore: actualizar cuentas de la granja desde Telegram [skip ci]"], cwd=BASE)
            subprocess.run(["git", "pull", "--rebase"], cwd=BASE)
            subprocess.run(["git", "push"], cwd=BASE)
        except Exception as e:
            print(f"Aviso git sync: {e}")


def tg_send(chat_id, text, botones=None):
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if botones:
        payload["reply_markup"] = {"inline_keyboard": botones}
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        print(f"Error sendMessage: {e}")


def tg_edit(chat_id, message_id, text, botones=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "disable_web_page_preview": True}
    if botones:
        payload["reply_markup"] = {"inline_keyboard": botones}
    try:
        requests.post(f"{API}/editMessageText", json=payload, timeout=15)
    except Exception:
        pass


def obtener_preview_titulo_tiktok(url):
    try:
        r = requests.post(
            "https://www.tikwm.com/api/",
            data={"url": url, "hd": "1"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        info = (r.json() or {}).get("data") or {}
        desc = (info.get("title") or "").strip()
        from hook_utils import generar_hook_inteligente
        hook_prev, _ = generar_hook_inteligente(desc, semilla=str(info.get("id") or url))
        return desc, hook_prev.replace("|", " / ")
    except Exception:
        pass
    return "", "AUTOMÁTICO DE LA DESCRIPCIÓN"


def conteo_hoy_por_cuenta():
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    hist = cargar_historial().get("history") or []
    conteo = {}
    for item in hist:
        if str(item.get("date", "")).startswith(hoy):
            for acc in (item.get("accounts") or []):
                conteo[acc] = conteo.get(acc, 0) + 1
    return conteo


def botones_seleccion_cuenta(chat_id, cantidad_videos=1):
    propias = cuentas_del_usuario(chat_id)
    botones = []
    activas = list(propias.keys())
    prefijo_lote = f"({cantidad_videos} vids) " if cantidad_videos > 1 else ""
    conteo_hoy = conteo_hoy_por_cuenta()

    items_botones = []
    for i, cid in enumerate(activas):
        icono = ICONOS_CUENTAS[i % len(ICONOS_CUENTAS)]
        nombre = propias[cid].get("nombre") or f"@{cid}"
        n_hoy = conteo_hoy.get(cid, 0)
        tag_hoy = f" [{n_hoy} hoy]"
        texto_btn = f"{icono} {nombre}{tag_hoy}" if len(activas) >= 4 else f"{icono} Subir {prefijo_lote}a {nombre}{tag_hoy}"
        items_botones.append({"text": texto_btn, "callback_data": f"subir:{cid}"})

    # Si tiene 4 o más cuentas (hasta 10+), mostrar en 2 columnas compactas
    if len(items_botones) >= 4:
        for i in range(0, len(items_botones), 2):
             botones.append(items_botones[i:i + 2])
    else:
        for b in items_botones:
            botones.append([b])

    if activas:
        botones.append([
            {"text": "✏️ Cambiar Hook", "callback_data": "cambiar_hook"},
            {"text": "⚙️ Configurar Cuentas", "callback_data": "menu_config"},
        ])
        botones.append([{"text": "➕ Agregar Cuenta IG", "callback_data": "agregar_cuenta"}])
    else:
        botones.append([{"text": "➕ Agregar Mi Cuenta de Instagram", "callback_data": "agregar_cuenta"}])
    return botones


def mostrar_menu_video(chat_id, urls_lista, hook_tk="", auto_hook_preview="", msg_id=None):
    propias = cuentas_del_usuario(chat_id)
    if isinstance(urls_lista, str):
        urls_lista = [urls_lista]
    n_vids = len(urls_lista)

    if n_vids > 1:
        if hook_tk:
            linea_hook = f"📌 Hook del lote: {hook_tk.upper()} | PARTE 1..{n_vids}"
        else:
            linea_hook = "📌 Hook: Automático de la descripción de cada video"
        resumen_urls = "\n".join([f"{i+1}️⃣ {u}" for i, u in enumerate(urls_lista[:8])])
        if n_vids > 8:
            resumen_urls += f"\n... y {n_vids - 8} más"
        encabezado = f"📚 ¡Lote de {n_vids} videos listo para procesar!\n{resumen_urls}"
    else:
        if hook_tk:
            linea_hook = f"📌 Hook personalizado: {hook_tk.upper()}"
        elif auto_hook_preview:
            linea_hook = f"📌 Hook detectado: {auto_hook_preview}"
        else:
            linea_hook = "📌 Hook: Automático de la descripción"
        encabezado = f"🎬 Video listo para procesar:\n{urls_lista[0]}"

    if not propias:
        texto = (
            f"{encabezado}\n\n"
            f"{linea_hook}\n\n"
            f"⚠️ Aún no has vinculado tu cuenta de Instagram.\n"
            f"👇 Toca el botón de abajo para conectar tu primera cuenta y subir el video:"
        )
    else:
        texto = (
            f"{encabezado}\n\n"
            f"{linea_hook}\n\n"
            f"👇 Toca a cuál de tus cuentas quieres subirlo (o cámbiale el Hook):"
        )

    botones = botones_seleccion_cuenta(chat_id, cantidad_videos=n_vids)
    if msg_id:
        tg_edit(chat_id, msg_id, texto, botones=botones)
    else:
        tg_send(chat_id, texto, botones=botones)


def mostrar_panel_config_cuentas(chat_id, msg_id=None):
    propias = cuentas_del_usuario(chat_id)
    if not propias:
        texto = "⚠️ Aún no tienes cuentas conectadas. Toca abajo para agregar la primera:"
        botones = [[{"text": "➕ Agregar Mi Cuenta de Instagram", "callback_data": "agregar_cuenta"}]]
    else:
        texto = (
            "⚙️ CONFIGURAR TUS CUENTAS DE INSTAGRAM\n\n"
            "Toca la cuenta que quieras personalizar (CTA amarillo, Hashtags, Auto-Comentario o quitarla):"
        )
        botones = []
        for i, (cid, cfg) in enumerate(propias.items()):
            icono = ICONOS_CUENTAS[i % len(ICONOS_CUENTAS)]
            nombre = cfg.get("nombre") or f"@{cid}"
            botones.append([{"text": f"{icono} Configurar {nombre}", "callback_data": f"cfg_acc:{cid}"}])
        botones.append([{"text": "➕ Agregar Nueva Cuenta IG", "callback_data": "agregar_cuenta"}])

    if msg_id:
        tg_edit(chat_id, msg_id, texto, botones=botones)
    else:
        tg_send(chat_id, texto, botones=botones)


def mostrar_detalle_cuenta(chat_id, cid, msg_id=None):
    propias = cuentas_del_usuario(chat_id)
    if cid not in propias:
        tg_send(chat_id, "⚠️ Esa cuenta no existe o no pertenece a tu perfil.")
        return

    cfg = propias[cid]
    nombre = cfg.get("nombre") or f"@{cid}"
    cta = cfg.get("cta") or "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA"
    hashes = " ".join(cfg.get("hashtags_default") or ["#frutinovelas", "#fruit"])
    comm = cfg.get("auto_comment") or "Desactivado"
    auto_on = bool(cfg.get("auto_monitor", False))
    tk_src = cfg.get("tiktok_source_url") or "https://www.tiktok.com/@helloword.visuals"
    estado_auto_txt = "🟢 ACTIVADO (8:00 AM y 3:00 PM Col)" if auto_on else "⚪ DESACTIVADO (Solo manual)"
    texto_btn_auto = "🛑 Apagar Piloto Automático" if auto_on else "🤖 Encender Piloto Automático (8am y 3pm)"

    texto = (
        f"⚙️ Ajustes de {nombre}\n\n"
        f"🤖 Piloto Automático:\n`{estado_auto_txt}`\n\n"
        f"🔗 Canal TikTok Fuente (para modo automático):\n`{tk_src}`\n\n"
        f"🟡 CTA (Texto abajo):\n`{cta}`\n\n"
        f"#️⃣ Hashtags:\n`{hashes}`\n\n"
        f"💬 Auto-Comentario en cada Reel:\n`{comm}`\n\n"
        f"👇 ¿Qué quieres hacer en {nombre}?"
    )
    botones = [
        [{"text": texto_btn_auto, "callback_data": f"toggle_auto:{cid}"}],
        [{"text": "⚡ Probar 1 Subida Automática Ahora", "callback_data": f"test_auto:{cid}"}],
        [{"text": "🔗 Cambiar Canal TikTok Fuente", "callback_data": f"edit_tk_src:{cid}"}],
        [{"text": "🟡 Cambiar CTA (Texto abajo)", "callback_data": f"edit_cta:{cid}"}],
        [{"text": "#️⃣ Cambiar Hashtags", "callback_data": f"edit_hash:{cid}"}],
        [{"text": "💬 Cambiar Auto-Comentario", "callback_data": f"edit_comm:{cid}"}],
        [{"text": "🗑️ Quitar esta cuenta", "callback_data": f"del_acc:{cid}"}],
        [{"text": "🔙 Volver a mis cuentas", "callback_data": "menu_config"}],
    ]
    if msg_id:
        tg_edit(chat_id, msg_id, texto, botones=botones)
    else:
        tg_send(chat_id, texto, botones=botones)


def ejecutar_subida_automatica_cuenta(cid, chat_id, etiqueta_turno="AUTO"):
    granja_data = cargar_granja().get("cuentas") or {}
    cfg = granja_data.get(cid) or {}
    tk_src = cfg.get("tiktok_source_url") or "https://www.tiktok.com/@helloword.visuals"
    tg_send(
        chat_id,
        f"🤖 **[{etiqueta_turno}] Piloto Automático en @{cid}**\n"
        f"🔍 Buscando un video nuevo (+30s) en `{tk_src}` para editarlo y subirlo solo..."
    )
    cmd = [
        sys.executable, "-u",
        os.path.join(BASE, "BOT_NUBE.py"),
        "--cuenta", cid,
        "--marca", "no",
        "--chat-id", str(chat_id),
    ]
    proc = subprocess.run(
        cmd,
        cwd=BASE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    if proc.returncode == 0:
        sincronizar_git()
        return True
    else:
        ultimas = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-10:])
        tg_send(chat_id, f"⚠️ Aviso en Piloto Automático de @{cid}:\n`{ultimas[:600]}`")
        return False


def revisar_turnos_piloto_automatico(ultimo_intento_por_cuenta):
    import hashlib
    from datetime import datetime, timezone, timedelta
    ahora_local = datetime.now(timezone.utc) - timedelta(hours=5)
    hora = ahora_local.hour
    minuto = ahora_local.minute
    hoy_str = ahora_local.strftime("%Y-%m-%d")

    granja_data = cargar_granja().get("cuentas") or {}
    conteo_hoy = conteo_hoy_por_cuenta()

    for cid, cfg in granja_data.items():
        if not cfg.get("activa", True) or not cfg.get("auto_monitor", False):
            continue
        n_hoy = conteo_hoy.get(cid, 0)
        if n_hoy >= 2:
            continue

        # Jitter humano pseudo-aleatorio único por cuenta y por día (entre 5 y 24 minutos)
        # Así el bot nunca publica a la misma hora exacta cada día
        semilla_jitter = f"{cid}_{hoy_str}_{n_hoy + 1}"
        hash_val = int(hashlib.md5(semilla_jitter.encode("utf-8")).hexdigest(), 16)
        minuto_objetivo = 5 + (hash_val % 20)  # Minuto entre :05 y :24

        # Turno 1: alrededor de las 8:00 AM (entre 8:05 y 8:24) si lleva 0 videos hoy
        # Turno 2: alrededor de las 3:00 PM (entre 15:05 y 15:24) si lleva 1 video hoy
        es_turno_1 = (hora == 8 and minuto >= minuto_objetivo and n_hoy == 0) or (hora > 8 and n_hoy == 0)
        es_turno_2 = (hora == 15 and minuto >= minuto_objetivo and n_hoy == 1) or (hora > 15 and n_hoy == 1)

        debe_subir = es_turno_1 or es_turno_2
        if not debe_subir:
            continue

        clave_intento = f"{cid}_{hoy_str}_turno_{n_hoy + 1}"
        if time.time() - ultimo_intento_por_cuenta.get(clave_intento, 0) < 3600:
            continue

        ultimo_intento_por_cuenta[clave_intento] = time.time()
        owner_chat = int(cfg.get("owner_chat_id") or OWNER_DEFAULT_CHAT_ID)
        ejecutar_subida_automatica_cuenta(cid, owner_chat, etiqueta_turno=f"AUTO {n_hoy + 1}/2 HOY")


def registrar_nueva_cuenta_desde_telegram(chat_id, texto_credencial, historial, codigo_2fa=""):
    from instagrapi import Client

    raw = urllib.parse.unquote(texto_credencial.strip())
    granja_full = cargar_granja()
    cuentas = granja_full.setdefault("cuentas", {})
    device_nuevo = DISPOSITIVOS_POOL[len(cuentas) % len(DISPOSITIVOS_POOL)]

    tg_send(chat_id, "🔍 Conectando con Instagram desde tu teléfono virtual...")

    cl = Client(delay_range=[2, 4])
    cl.password_encrypt = lambda pwd: f"#PWD_INSTAGRAM:0:{int(time.time())}:{pwd}"
    try:
        cl.set_device(dict(device_nuevo))
        if ":" in raw and len(raw.split(":")) == 2 and not raw[0].isdigit():
            u, p = raw.split(":", 1)
            u_clean, p_clean = u.strip().lstrip("@"), p.strip()
            if codigo_2fa:
                cl.login(u_clean, p_clean, verification_code=codigo_2fa.strip())
            else:
                cl.login(u_clean, p_clean)
            sid_final = cl.sessionid
        else:
            sid_final = raw
            cl.login_by_sessionid(sid_final)

        info_acc = cl.account_info()
        username = info_acc.username.strip().lower()
    except Exception as e:
        err_str = str(e)
        err_low = err_str.lower()
        u_state = estado_usuario(historial, chat_id)
        u_state["waiting_account"] = True

        # Si era usuario:contraseña, guardarlo para que pueda aprobar en su teléfono o mandar el código de 6 dígitos
        if ":" in raw and not raw[0].isdigit():
            u_state["pending_ig_creds"] = raw
            guardar_historial(historial)
            if any(k in err_low for k in ("challenge", "two-factor", "two_factor", "verification", "checkpoint", "code")):
                tg_send(
                    chat_id,
                    "📲 **CONFIRMACIÓN EN TU TELÉFONO**\n\n"
                    "Instagram envió un aviso de seguridad a tu celular:\n"
                    "1️⃣ Abre tu app de Instagram en el teléfono: si te sale *'¿Intentaste iniciar sesión?'*, toca **'Sí, fui yo' / 'Aprobar'** y luego toca el botón verde de abajo.\n"
                    "2️⃣ O si te llegó un **código de 6 dígitos** por SMS/Correo, escríbelo aquí mismo:",
                    botones=[[{"text": "✅ Ya aprobé 'Sí, fui yo' en mi teléfono", "callback_data": "reintentar_login_ig"}]]
                )
                return False

        guardar_historial(historial)
        tg_send(
            chat_id,
            f"❌ Instagram respondió:\n`{err_str[:180]}`\n\n"
            f"👉 Revisa que la contraseña sea correcta (escríbela de nuevo aquí) o si te salió un aviso en la app de Instagram de tu teléfono, dale a **'Sí, fui yo'** y toca el botón de abajo:",
            botones=[[{"text": "🔄 Ya aprobé en mi teléfono, reintentar", "callback_data": "reintentar_login_ig"}]] if u_state.get("pending_ig_creds") else None
        )
        return False

    num_cuenta = len(cuentas) + 1
    secret_slot = f"IG_SESSIONID_{num_cuenta}"
    cuentas[username] = {
        "activa": True,
        "owner_chat_id": int(chat_id),
        "nombre": f"@{username}",
        "secret_sessionid": secret_slot,
        "tiktok_source_url": "",
        "tiktok_channel_id": "",
        "auto_monitor": False,
        "hashtags_default": ["#frutinovelas", "#fruit", "#foodstory", "#partii", "#capibara"],
        "cta": "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
        "auto_comment": DEFAULT_AUTO_COMMENT,
        "estilo_unico": {
            "zoom_w": 1090,
            "zoom_h": 1939,
            "cta_color": "yellow",
            "speed_factor": 1.0,
            "trim_start": 0.0,
        },
        "device": device_nuevo,
        "proxy": "",
    }
    guardar_granja(granja_full)

    historial.setdefault("ig_sessions", {})[username] = sid_final
    try:
        settings_actuales = cl.get_settings()
        settings_limpios = {
            k: v for k, v in settings_actuales.items()
            if k in ("uuids", "device_settings", "user_agent", "country", "country_code", "locale", "timezone_offset")
        }
        historial.setdefault("ig_identities", {})[username] = {
            "sid_prefix": sid_final[:16],
            "settings": settings_limpios,
        }
    except Exception:
        pass
    guardar_historial(historial)
    sincronizar_git()

    tg_send(
        chat_id,
        f"✅ ¡Cuenta agregada con éxito a tu perfil!\n\n"
        f"👤 Cuenta: @{username}\n"
        f"📱 Teléfono Virtual asignado: {device_nuevo['manufacturer'].title()} {device_nuevo['model']}\n\n"
        f"¡Ya aparece en tus botones cada vez que envíes un link de TikTok!"
    )

    u_state = estado_usuario(historial, chat_id)
    pend = u_state.get("pending_video") or {}
    urls_pend = pend.get("urls") or ([pend["url"]] if pend.get("url") else [])
    if urls_pend:
        mostrar_menu_video(
            chat_id,
            urls_pend,
            hook_tk=pend.get("hook", ""),
            auto_hook_preview=pend.get("auto_preview", ""),
        )
    return True


def main():
    if not TOKEN:
        print("Falta TELEGRAM_TOKEN.")
        return 1

    max_seconds = int(os.environ.get("LISTENER_DURATION_SEC", "3100"))
    t_inicio = time.time()

    historial = cargar_historial()
    offset = int(historial.get("telegram_last_update_id") or 0) + 1
    ultimo_check_auto = 0
    ultimo_intento_por_cuenta = {}

    print(f"Escuchador Multi-Usuario de Telegram en la Nube activo (duración del turno: {max_seconds}s)...")

    while time.time() - t_inicio < max_seconds:
        try:
            if time.time() - ultimo_check_auto > 180:
                ultimo_check_auto = time.time()
                revisar_turnos_piloto_automatico(ultimo_intento_por_cuenta)

            r = requests.get(
                f"{API}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35,
            )
            data = r.json()
            if not data.get("ok"):
                time.sleep(3)
                continue

            for upd in data.get("result", []):
                upd_id = upd.get("update_id", 0)
                offset = upd_id + 1
                historial = cargar_historial()
                historial["telegram_last_update_id"] = upd_id

                # Caso 1: Tocó un botón
                if "callback_query" in upd:
                    cq = upd["callback_query"]
                    cq_id = cq.get("id")
                    msg_cq = cq.get("message") or {}
                    msg_id = msg_cq.get("message_id")
                    chat_id = (msg_cq.get("chat") or {}).get("id")
                    if not chat_id:
                        continue

                    u_state = estado_usuario(historial, chat_id)
                    try:
                        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cq_id}, timeout=10)
                    except Exception:
                        pass

                    cb = cq.get("data") or ""

                    if cb == "reintentar_login_ig":
                        creds = u_state.get("pending_ig_creds") or ""
                        if creds:
                            u_state["waiting_account"] = False
                            guardar_historial(historial)
                            registrar_nueva_cuenta_desde_telegram(chat_id, creds, historial)
                        else:
                            tg_send(chat_id, "⚠️ Primero envía tu usuario y contraseña.")
                        continue

                    if cb == "agregar_cuenta":
                        u_state["waiting_account"] = True
                        u_state["waiting_hook"] = False
                        u_state["waiting_cfg_field"] = None
                        u_state["pending_ig_user"] = None
                        u_state["pending_ig_creds"] = None
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            "📱 **CONECTAR CUENTA DESDE TU TELÉFONO**\n\n"
                            "Escribe aquí el **nombre de usuario** de tu cuenta de Instagram (ej: `Frutnovelas777`):"
                        )
                        continue

                    if cb == "menu_config":
                        u_state["waiting_cfg_field"] = None
                        guardar_historial(historial)
                        mostrar_panel_config_cuentas(chat_id, msg_id=msg_id)
                        continue

                    if cb.startswith("cfg_acc:"):
                        cid = cb.split(":", 1)[1].strip()
                        u_state["waiting_cfg_field"] = None
                        guardar_historial(historial)
                        mostrar_detalle_cuenta(chat_id, cid, msg_id=msg_id)
                        continue

                    if cb.startswith("toggle_auto:"):
                        cid = cb.split(":", 1)[1].strip()
                        propias = cuentas_del_usuario(chat_id)
                        if cid in propias:
                            granja_full = cargar_granja()
                            cfg_acc = granja_full.get("cuentas", {}).get(cid)
                            if cfg_acc is not None:
                                nuevo_estado = not bool(cfg_acc.get("auto_monitor", False))
                                cfg_acc["auto_monitor"] = nuevo_estado
                                if not cfg_acc.get("tiktok_source_url"):
                                    cfg_acc["tiktok_source_url"] = "https://www.tiktok.com/@helloword.visuals"
                                guardar_granja(granja_full)
                                sincronizar_git()
                            mostrar_detalle_cuenta(chat_id, cid, msg_id=msg_id)
                        continue

                    if cb.startswith("test_auto:"):
                        cid = cb.split(":", 1)[1].strip()
                        propias = cuentas_del_usuario(chat_id)
                        if cid in propias:
                            ejecutar_subida_automatica_cuenta(cid, chat_id, etiqueta_turno="PRUEBA EN VIVO")
                        continue

                    if cb.startswith("edit_tk_src:"):
                        cid = cb.split(":", 1)[1].strip()
                        u_state["waiting_cfg_field"] = {"cuenta": cid, "campo": "tiktok_source"}
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            f"🔗 Pégame aquí el link del perfil de TikTok (o el `@usuario` de TikTok) de donde quieres que `@{cid}` saque sus videos automáticamente:\n"
                            f"(Ej: `https://www.tiktok.com/@helloword.visuals`)"
                        )
                        continue

                    if cb.startswith("edit_cta:"):
                        cid = cb.split(":", 1)[1].strip()
                        u_state["waiting_cfg_field"] = {"cuenta": cid, "campo": "cta"}
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            f"🟡 Escribe el nuevo texto para el CTA de @{cid} (el texto amarillo de abajo):\n"
                            f"(Usa `|` para partir en dos renglones, ej: `SÍGUEME PARA VER|LA PARTE 2`)"
                        )
                        continue

                    if cb.startswith("edit_hash:"):
                        cid = cb.split(":", 1)[1].strip()
                        u_state["waiting_cfg_field"] = {"cuenta": cid, "campo": "hashtags"}
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            f"#️⃣ Escribe los nuevos Hashtags por defecto para @{cid} separados por espacio:\n"
                            f"(Ej: `#frutinovelas #historias #reels #viral #parati`)"
                        )
                        continue

                    if cb.startswith("edit_comm:"):
                        cid = cb.split(":", 1)[1].strip()
                        u_state["waiting_cfg_field"] = {"cuenta": cid, "campo": "comment"}
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            f"💬 Escribe el nuevo Auto-Comentario que se publicará automáticamente en cada Reel de @{cid}:\n"
                            f"(O escribe `no` si quieres desactivar el auto-comentario en esta cuenta)"
                        )
                        continue

                    if cb.startswith("del_acc:"):
                        cid = cb.split(":", 1)[1].strip()
                        propias = cuentas_del_usuario(chat_id)
                        if cid in propias:
                            granja_full = cargar_granja()
                            if cid in granja_full.get("cuentas", {}):
                                granja_full["cuentas"][cid]["activa"] = False
                                guardar_granja(granja_full)
                                sincronizar_git()
                            tg_send(chat_id, f"🗑️ La cuenta @{cid} fue quitada de tus botones.")
                            mostrar_panel_config_cuentas(chat_id)
                        continue

                    if cb == "cambiar_hook":
                        pend = u_state.get("pending_video") or {}
                        urls_pend = pend.get("urls") or ([pend["url"]] if pend.get("url") else [])
                        if not urls_pend:
                            tg_send(chat_id, "⚠️ Primero envíame uno o varios links de TikTok.")
                            continue
                        u_state["waiting_hook"] = True
                        u_state["waiting_account"] = False
                        u_state["waiting_cfg_field"] = None
                        guardar_historial(historial)
                        if len(urls_pend) > 1:
                            tg_send(
                                chat_id,
                                f"✏️ Escribe el título base para este lote de {len(urls_pend)} videos:\n"
                                f"(Yo le agregaré automáticamente `|PARTE 1`, `|PARTE 2`... a cada video)"
                            )
                        else:
                            tg_send(
                                chat_id,
                                "✏️ Escribe ahora el texto que quieres que salga arriba en el Hook:\n"
                                "(Tip: si quieres 2 líneas usa `|` en medio, ej: `EL JABÓN|LA ISLA`)"
                            )
                        continue

                    if cb.startswith("subir:"):
                        u_state["waiting_hook"] = False
                        u_state["waiting_account"] = False
                        u_state["waiting_cfg_field"] = None
                        cuenta = cb.split(":", 1)[1].strip()
                        pend = u_state.get("pending_video") or {}
                        urls_vid = pend.get("urls") or ([pend["url"]] if pend.get("url") else [])
                        hook_vid = (pend.get("hook") or "").strip()
                        if not urls_vid:
                            tg_send(chat_id, "⚠️ Primero envíame un link de TikTok.")
                            continue

                        propias = cuentas_del_usuario(chat_id)
                        if cuenta != "todas" and cuenta not in propias:
                            tg_send(chat_id, "⚠️ Esa cuenta no pertenece a tu perfil.")
                            continue

                        u_state["pending_video"] = None
                        guardar_historial(historial)

                        etiqueta_cuenta = "TODAS TUS CUENTAS" if cuenta == "todas" else f"@{cuenta}"
                        total_lote = len(urls_vid)

                        if total_lote == 1:
                            hook_mostrar = hook_vid.upper() if hook_vid else (pend.get("auto_preview") or "Automático")
                            tg_edit(
                                chat_id,
                                msg_id,
                                f"⚡ ¡Orden recibida al instante!\n"
                                f"🎬 Video: {urls_vid[0]}\n"
                                f"📌 Hook: {hook_mostrar}\n"
                                f"📲 Destino: {etiqueta_cuenta}\n\n"
                                f"⏳ Descargando, editando con AUTO_REEL (1080x1920 + portada) y subiendo a Instagram..."
                            )
                        else:
                            tg_edit(
                                chat_id,
                                msg_id,
                                f"📚 ¡Iniciando subida por lote de {total_lote} videos a {etiqueta_cuenta}!\n\n"
                                f"⏳ Los iré descargando, renderizando en 1080x1920 y publicando en orden con pausa anti-bloqueo entre cada uno..."
                            )

                        for idx_v, u_item in enumerate(urls_vid, 1):
                            if total_lote > 1:
                                if hook_vid:
                                    base_limpia = hook_vid.split("|")[0].strip().upper()
                                    hook_item = f"{base_limpia}|PARTE {idx_v}"
                                else:
                                    hook_item = ""
                                tg_send(
                                    chat_id,
                                    f"🎬 Procesando video {idx_v} de {total_lote} para {etiqueta_cuenta}:\n{u_item}"
                                )
                            else:
                                hook_item = hook_vid

                            cmd = [
                                sys.executable, "-u",
                                os.path.join(BASE, "BOT_NUBE.py"),
                                "--url", u_item,
                                "--cuenta", cuenta,
                                "--marca", "no",
                                "--chat-id", str(chat_id),
                            ]
                            if hook_item:
                                cmd += ["--hook", hook_item]

                            proc = subprocess.run(
                                cmd,
                                cwd=BASE,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                            )
                            print(proc.stdout)
                            if proc.stderr:
                                print(proc.stderr)
                            if proc.returncode != 0:
                                ultimas = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-12:])
                                tg_send(
                                    chat_id,
                                    f"❌ Error en el video {idx_v}/{total_lote}:\n\n{ultimas[:800]}"
                                )
                            else:
                                sincronizar_git()

                            if idx_v < total_lote:
                                time.sleep(20)

                        if total_lote > 1:
                            tg_send(chat_id, f"🎉 ¡Lote completo de {total_lote} videos procesado en {etiqueta_cuenta}!")
                    continue

                # Caso 2: Envió un mensaje de texto
                msg = upd.get("message") or upd.get("edited_message") or {}
                txt = (msg.get("text") or "").strip()
                chat_id = (msg.get("chat") or {}).get("id")
                if not chat_id:
                    continue

                u_state = estado_usuario(historial, chat_id)

                if txt.startswith("/start") or txt.startswith("/cuentas") or txt.startswith("/config"):
                    u_state["waiting_hook"] = False
                    u_state["waiting_account"] = False
                    u_state["waiting_cfg_field"] = None
                    guardar_historial(historial)
                    propias = cuentas_del_usuario(chat_id)
                    cuentas_activas = [v.get("nombre", f"@{k}") for k, v in propias.items()]
                    if cuentas_activas:
                        lista_c = "\n".join([f"• {c}" for c in cuentas_activas])
                        tg_send(
                            chat_id,
                            f"⚡ ¡Tu Bot de Reels en la Nube está activo!\n\n"
                            f"📲 Tus cuentas conectadas ({len(cuentas_activas)}):\n{lista_c}\n\n"
                            f"• Pégame 1 link de TikTok (o pega varios links juntos en un mismo mensaje para subirlos por lote).\n"
                            f"• Toca abajo para configurar tus textos o sumar otra cuenta:",
                            botones=[
                                [{"text": "⚙️ Configurar Cuentas (CTA / Hashtags / Comentario)", "callback_data": "menu_config"}],
                                [{"text": "➕ Agregar Otra Cuenta IG", "callback_data": "agregar_cuenta"}],
                            ]
                        )
                    else:
                        tg_send(
                            chat_id,
                            "👋 ¡Bienvenida/o al Bot Automático de Reels en la Nube!\n\n"
                            "Aquí puedes convertir cualquier video de TikTok a formato Reel 1080x1920 con Hook, CTA, audio limpio, portada automática y auto-comentario, y subirlo directo a tu Instagram.\n\n"
                            "👇 Primero toca el botón de abajo para conectar tu cuenta de Instagram:",
                            botones=[[{"text": "➕ Agregar Mi Cuenta de Instagram", "callback_data": "agregar_cuenta"}]]
                        )
                    continue

                # Si estaba editando un campo de configuración de su cuenta (Mejora 4 + Canal TikTok Fuente)
                cfg_wait = u_state.get("waiting_cfg_field")
                if cfg_wait and txt:
                    cid = cfg_wait.get("cuenta")
                    campo = cfg_wait.get("campo")
                    u_state["waiting_cfg_field"] = None
                    guardar_historial(historial)

                    propias = cuentas_del_usuario(chat_id)
                    if cid in propias:
                        granja_full = cargar_granja()
                        cfg_acc = granja_full.get("cuentas", {}).get(cid)
                        if cfg_acc is not None:
                            if campo == "cta":
                                cfg_acc["cta"] = txt.strip().upper()
                                msg_ok = f"✅ CTA de @{cid} actualizado a:\n`{cfg_acc['cta']}`"
                            elif campo == "hashtags":
                                palabras = [
                                    (w if w.startswith("#") else f"#{w}")
                                    for w in re.split(r"[\s,]+", txt.strip()) if w.strip()
                                ]
                                cfg_acc["hashtags_default"] = palabras[:8] or ["#reels"]
                                msg_ok = f"✅ Hashtags de @{cid} actualizados a:\n`{' '.join(cfg_acc['hashtags_default'])}`"
                            elif campo == "comment":
                                if txt.strip().lower() in ("no", "off", "0", "ninguno"):
                                    cfg_acc["auto_comment"] = ""
                                    msg_ok = f"✅ Auto-Comentario desactivado en @{cid}."
                                else:
                                    cfg_acc["auto_comment"] = txt.strip()
                                    msg_ok = f"✅ Auto-Comentario de @{cid} actualizado a:\n`{cfg_acc['auto_comment']}`"
                            elif campo == "tiktok_source":
                                raw_tk = txt.strip()
                                if "tiktok.com" not in raw_tk:
                                    handle = raw_tk.lstrip("@").strip()
                                    raw_tk = f"https://www.tiktok.com/@{handle}"
                                cfg_acc["tiktok_source_url"] = raw_tk
                                cfg_acc["tiktok_channel_id"] = ""
                                msg_ok = f"✅ Canal de TikTok fuente para @{cid} actualizado a:\n`{raw_tk}`"
                            else:
                                msg_ok = "✅ Guardado."
                            guardar_granja(granja_full)
                            sincronizar_git()
                            tg_send(chat_id, msg_ok)
                            mostrar_detalle_cuenta(chat_id, cid)
                    continue

                # Si envió uno o varios links de TikTok (Soporte individual + Lotes Mejora 2)
                if "tiktok.com" in txt:
                    u_state["waiting_hook"] = False
                    u_state["waiting_account"] = False
                    u_state["waiting_cfg_field"] = None

                    todas_urls = re.findall(r"https?://[^\s|]+tiktok\.com[^\s|]+", txt)
                    urls_limpias = []
                    for u in todas_urls:
                        if u not in urls_limpias:
                            urls_limpias.append(u)

                    if urls_limpias:
                        hook_tk = ""
                        if "|" in txt and len(urls_limpias) == 1:
                            hook_tk = txt.split("|", 1)[1].strip()

                        _, auto_prev = obtener_preview_titulo_tiktok(urls_limpias[0]) if (len(urls_limpias) == 1 and not hook_tk) else ("", "")
                        pend = {
                            "url": urls_limpias[0],
                            "urls": urls_limpias,
                            "hook": hook_tk,
                            "auto_preview": auto_prev,
                        }
                        u_state["pending_video"] = pend
                        guardar_historial(historial)
                        mostrar_menu_video(chat_id, urls_limpias, hook_tk=hook_tk, auto_hook_preview=auto_prev)
                    continue

                # Si estaba esperando el sessionid o usuario:clave de una cuenta nueva
                if u_state.get("waiting_account") and txt:
                    texto_limpio = txt.strip()
                    # Si ya había enviado usuario:contraseña y ahora envía el código de 6 dígitos
                    if u_state.get("pending_ig_creds") and re.fullmatch(r"\d{4,8}", texto_limpio.replace(" ", "")):
                        creds = u_state["pending_ig_creds"]
                        u_state["waiting_account"] = False
                        u_state["pending_ig_creds"] = None
                        guardar_historial(historial)
                        registrar_nueva_cuenta_desde_telegram(chat_id, creds, historial, codigo_2fa=texto_limpio.replace(" ", ""))
                        continue

                    es_sessionid = (":" in texto_limpio and texto_limpio[0].isdigit()) or ("%3A" in texto_limpio) or (len(texto_limpio) > 35 and " " not in texto_limpio)
                    if ":" not in texto_limpio and not es_sessionid and not u_state.get("pending_ig_user"):
                        u_state["pending_ig_user"] = texto_limpio.lstrip("@").strip()
                        guardar_historial(historial)
                        tg_send(
                            chat_id,
                            f"👤 Usuario detectado: `@{u_state['pending_ig_user']}`\n\n"
                            f"🔑 Ahora escribe en el siguiente mensaje la **contraseña** de `@{u_state['pending_ig_user']}`:"
                        )
                        continue

                    if u_state.get("pending_ig_user") and ":" not in texto_limpio and not es_sessionid:
                        credencial_completa = f"{u_state['pending_ig_user']}:{texto_limpio}"
                    else:
                        credencial_completa = texto_limpio

                    u_state["waiting_account"] = False
                    u_state["pending_ig_user"] = None
                    guardar_historial(historial)
                    registrar_nueva_cuenta_desde_telegram(chat_id, credencial_completa, historial)
                    continue

                # Si estaba esperando que el usuario escribiera el nuevo Hook
                if u_state.get("waiting_hook") and txt:
                    pend = u_state.get("pending_video") or {}
                    urls_tk = pend.get("urls") or ([pend["url"]] if pend.get("url") else [])
                    if urls_tk:
                        u_state["waiting_hook"] = False
                        pend["hook"] = txt.strip()
                        u_state["pending_video"] = pend
                        guardar_historial(historial)
                        mostrar_menu_video(chat_id, urls_tk, hook_tk=pend["hook"])
                        continue

                guardar_historial(historial)

        except Exception:
            time.sleep(2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
