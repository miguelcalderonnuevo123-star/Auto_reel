# -*- coding: utf-8 -*-
"""
login_telegram.py — Inicia sesión en Instagram desde Telegram (soporta contraseña y Playwright Headless,
o guardado directo de sessionid), maneja 2FA interactivo con Telegram, y actualiza automáticamente
el Secret de GitHub Actions y el historial.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import requests
from nacl import encoding, public

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
GRANJA_PATH = os.path.join(BASE, "cuentas_granja.json")
HISTORIAL_PATH = os.path.join(BASE, "historial_bot.json")

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "May777p/Auto_reel")
GITHUB_TOKEN = os.environ.get("PAT_GITHUB") or os.environ.get("GITHUB_TOKEN", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

SECRET_MAP = {
    "frutnovelas776": "IG_SESSIONID",
    "novelas_frutosass": "IG_SESSIONID_2",
    "frutnovelas777": "IG_SESSIONID_3",
    "novel_asanimadas": "IG_SESSIONID_4",
    "frutastorias_tv": "IG_SESSIONID_5",
    "historias_frutales_hd": "IG_SESSIONID_6",
    "fruticuentos_oficial": "IG_SESSIONID_7",
    "novelas_frutas_pro": "IG_SESSIONID_8",
    "frutidramas_top": "IG_SESSIONID_9",
    "reino_frutosas": "IG_SESSIONID_10",
}

NUMERO_A_CUENTA = {
    "1": "frutnovelas776",
    "2": "novelas_frutosass",
    "3": "frutnovelas777",
    "4": "novel_asanimadas",
    "5": "frutastorias_tv",
    "6": "historias_frutales_hd",
    "7": "fruticuentos_oficial",
    "8": "novelas_frutas_pro",
    "9": "frutidramas_top",
    "10": "reino_frutosas"
}

def normalizar_cuenta(acc_str):
    acc = acc_str.strip().lower().replace("@", "")
    return NUMERO_A_CUENTA.get(acc, acc)

def enviar_telegram(chat_id, texto):
    if not TELEGRAM_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error Telegram: {e}")

def esperar_codigo_telegram(chat_id, account="", timeout_segundos=180, codigo_previo=""):
    start_time = time.time()
    last_update_id = 0
    worker_webhook = "https://wild-snowflake-a34c.maykellazaro60.workers.dev/"
    worker_url = f"{worker_webhook}2fa"
    s = requests.Session()

    # Desactivar temporalmente el webhook para recibir los mensajes en tiempo real vía getUpdates sin desfase ni pérdida de isolate
    webhook_liberado = False
    try:
        r_del = s.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook", timeout=5).json()
        if r_del.get("ok"):
            webhook_liberado = True
            print("  ✅ Webhook liberado temporalmente: escuchando 2FA en tiempo real directamente de Telegram.")
    except Exception as e_del:
        print(f"  Aviso al liberar webhook: {e_del}")

    try:
        # Obtener offset inicial
        try:
            r_init = s.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=5).json()
            updates_init = r_init.get("result", [])
            if updates_init:
                last_update_id = updates_init[-1]["update_id"]
        except Exception:
            pass

        while time.time() - start_time < timeout_segundos:
            # 1. Escuchar directamente de Telegram (Long-polling ultra veloz de 3s)
            try:
                r = s.get(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                    params={"offset": last_update_id + 1, "timeout": 3},
                    timeout=8
                ).json()
                for upd in r.get("result", []):
                    last_update_id = max(last_update_id, upd["update_id"])
                    m = upd.get("message") or {}
                    if str(m.get("chat", {}).get("id")) == str(chat_id):
                        txt = (m.get("text") or "").strip()
                        m_code = re.search(r"\b(\d{6})\b", txt)
                        if m_code:
                            code = m_code.group(1)
                            if code != codigo_previo:
                                print(f"  ⚡ Código 2FA recibido directamente desde Telegram: {code}")
                                # Borrar el código del chat por privacidad
                                if m.get("message_id"):
                                    try:
                                        s.post(
                                            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage",
                                            json={"chat_id": chat_id, "message_id": m["message_id"]},
                                            timeout=3
                                        )
                                    except Exception:
                                        pass
                                enviar_telegram(chat_id, f"⚡ Código recibido: <code>{code}</code>. Validando con Instagram al instante...")
                                return code
            except Exception as e_upd:
                pass

            # 2. Consultar también el Cloudflare Worker (por si algún webhook entró antes de liberar)
            try:
                r_cf = s.get(worker_url, params={"account": account}, timeout=3)
                if r_cf.status_code == 200:
                    data_cf = r_cf.json()
                    if data_cf.get("ok") and data_cf.get("code"):
                        code = str(data_cf["code"]).strip()
                        if code != codigo_previo:
                            print(f"  ⚡ Código 2FA recibido desde Cloudflare Worker: {code}")
                            enviar_telegram(chat_id, f"⚡ Código recibido: <code>{code}</code>. Validando con Instagram al instante...")
                            return code
            except Exception:
                pass

            time.sleep(0.5)

        print("  Tiempo de espera agotado para el código 2FA.")
        enviar_telegram(chat_id, "⏱️ <b>Tiempo de espera agotado</b>. No se recibió el código de 6 dígitos. Intenta de nuevo.")
        return ""
    finally:
        # Siempre restaurar el webhook de Cloudflare al terminar
        if webhook_liberado:
            try:
                r_set = s.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                    json={"url": worker_webhook},
                    timeout=5
                ).json()
                if r_set.get("ok"):
                    print("  ✅ Webhook de Cloudflare restaurado exitosamente.")
            except Exception as e_set:
                print(f"  Error restaurando webhook: {e_set}")

def guardar_secret_github(secret_name, secret_val):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AutoReel-Bot"
    }
    url_key = f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key"
    r = requests.get(url_key, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"Error obteniendo public-key de GitHub: {r.status_code} {r.text}")
        return False
    key_data = r.json()
    public_key = public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder)
    key_id = key_data["key_id"]

    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_val.encode("utf-8"))
    encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

    url_put = f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/{secret_name}"
    payload = {"encrypted_value": encrypted_b64, "key_id": key_id}
    r_put = requests.put(url_put, headers=headers, json=payload, timeout=15)
    return r_put.status_code in (201, 204)

def login_instagrapi(username, password, chat_id, account=""):
    """
    Intento principal de login: usa la API móvil de Instagram (Android) emulando
    el dispositivo configurado en cuentas_granja.json (ej. Xiaomi Redmi Note 11).
    Evita bloqueos de cookies web y ventanas emergentes del navegador.
    """
    try:
        from instagrapi import Client
        from instagrapi.exceptions import (
            TwoFactorRequired, BadPassword, ChallengeRequired,
            PleaseWaitFewMinutes, LoginRequired
        )
    except ImportError:
        print("instagrapi no disponible en este entorno.")
        return None

    print(f"📱 Iniciando login instagrapi (API Móvil) para @{username}...")
    try:
        cl = Client(delay_range=[1.5, 3.5])

        # Cargar configuración de dispositivo si existe en cuentas_granja.json
        if os.path.exists(GRANJA_PATH):
            try:
                with open(GRANJA_PATH, "r", encoding="utf-8") as f:
                    cfg_granja = json.load(f).get("cuentas", {}).get(account, {})
                    device_cfg = cfg_granja.get("device")
                    if device_cfg:
                        print(f"  Configurando dispositivo virtual {device_cfg.get('manufacturer', '')} {device_cfg.get('model', '')}...")
                        cl.set_device(dict(device_cfg))
            except Exception as e_dev:
                print(f"  Aviso al configurar device: {e_dev}")

        # Intentar login
        login_ok = False
        try:
            def challenge_handler(u_name, choice):
                print(f"  Instagram solicita reto ({choice.name})...")
                enviar_telegram(
                    chat_id,
                    f"📲 <b>RETO DE SEGURIDAD ({choice.name})</b>\n\n"
                    f"Instagram envió un código para verificar <b>@{u_name}</b>.\n"
                    f"👉 <b>Escribe el código aquí en Telegram:</b>"
                )
                return esperar_codigo_telegram(chat_id, account=account, timeout_segundos=120)

            cl.challenge_code_handler = challenge_handler
            cl.login(username, password)
            login_ok = True
        except TwoFactorRequired:
            print("  Instagram requiere autenticación de 2 factores (2FA)...")
            enviar_telegram(
                chat_id,
                f"📲 <b>CÓDIGO DE SEGURIDAD 2FA REQUERIDO</b>\n\n"
                f"Instagram solicita verificación de 2 pasos para <b>@{username}</b>.\n\n"
                f"⚡ <b>¡RÁPIDO!</b> Los códigos de tu Authenticator app rotan cada 30s.\n"
                f"👉 <b>Escribe el código de 6 dígitos aquí abajo de inmediato:</b>"
            )
            ultimo_codigo = ""
            for intento_2fa in range(1, 3):
                codigo = esperar_codigo_telegram(chat_id, account=account, timeout_segundos=120, codigo_previo=ultimo_codigo)
                if not codigo:
                    print("  No se recibió código 2FA dentro del tiempo límite.")
                    return None
                ultimo_codigo = codigo
                print(f"  Validando código 2FA en Instagram (intento {intento_2fa}): {codigo}...")
                try:
                    # En instagrapi el 2FA se valida pasando verification_code al método login
                    cl.login(username, password, verification_code=codigo)
                    login_ok = True
                    print("  ✅ 2FA validado con éxito!")
                    break
                except Exception as e_2fa:
                    print(f"  Aviso al validar 2FA: {e_2fa}")
                    if intento_2fa < 2:
                        enviar_telegram(
                            chat_id,
                            f"⚠️ <b>El código anterior ya expiró o fue inválido.</b>\n\n"
                            f"Espera que tu app genere uno nuevo (con los 30s completos) y <b>escríbelo aquí rápido:</b>"
                        )
                    else:
                        enviar_telegram(chat_id, "❌ No se pudo validar el código 2FA tras 2 intentos. Intenta de nuevo desde el menú.")
                        return None
        except BadPassword:
            print("  Error: Contraseña incorrecta en Instagram.")
            enviar_telegram(chat_id, f"❌ <b>Contraseña incorrecta</b> para @{username}. Por favor verifica tus credenciales.")
            return "BAD_PASSWORD"
        except ChallengeRequired as e_ch:
            print(f"  Instagram solicita verificación de seguridad (Challenge): {e_ch}")
            return None
        except Exception as e_log:
            print(f"  Aviso en cl.login: {e_log}")
            return None

        if not login_ok:
            return None

        sid = cl.sessionid
        if sid:
            print(f"  ✅ Login móvil exitoso. sessionid obtenido (longitud: {len(sid)})")
            return sid
        else:
            print("  Aviso: login instagrapi completado pero sessionid está vacío.")
            return None
    except Exception as e:
        print(f"Error general en login_instagrapi: {e}")
        return None

def login_playwright(username, password, chat_id, account=""):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright no disponible.")
        return None

    print(f"Iniciando navegador Playwright (Fallback Web) para @{username}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="es-ES",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.goto("https://www.instagram.com/accounts/login/", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # Aceptar o rechazar cookies con todos los patrones posibles (Español e Inglés)
            cookie_buttons = [
                'button:has-text("Decline optional cookies")',
                'button:has-text("Rechazar cookies opcionales")',
                'button:has-text("Allow all cookies")',
                'button:has-text("Permitir todas las cookies")',
                'button:has-text("Aceptar todas")',
                'button:has-text("Aceptar")',
                'button:has-text("Allow")',
                'button:has-text("Permitir cookies necesarias")',
                'button:has-text("Only allow essential cookies")',
                'div[role="dialog"] button:first-child',
                'div[role="dialog"] button:last-child',
            ]
            for sel in cookie_buttons:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1200):
                        print(f"  Pulsando botón de cookies: {sel}")
                        btn.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    pass

            # Localizar campo de usuario con selectores flexibles
            user_input = None
            for u_sel in ['input[name="username"]', 'input[name="emailOrPhone"]', 'input[type="text"]']:
                try:
                    loc = page.locator(u_sel).first
                    if loc.is_visible(timeout=4000):
                        user_input = loc
                        break
                except Exception:
                    pass

            if not user_input:
                try:
                    page.wait_for_selector('input[name="username"]', timeout=20000)
                    user_input = page.locator('input[name="username"]').first
                except Exception as e_wait:
                    print(f"  Selector de usuario no encontrado: {e_wait}")
                    print(f"  URL: {page.url} | Título: {page.title()}")
                    browser.close()
                    return None

            user_input.fill(username)
            page.wait_for_timeout(1000)

            # Localizar campo de contraseña con selectores flexibles
            pwd_input = None
            for p_sel in ['input[name="password"]', 'input[type="password"]']:
                try:
                    loc_p = page.locator(p_sel).first
                    if loc_p.is_visible(timeout=5000):
                        pwd_input = loc_p
                        break
                except Exception:
                    pass

            if not pwd_input:
                try:
                    page.wait_for_selector('input[type="password"], input[name="password"]', timeout=15000)
                    pwd_input = page.locator('input[type="password"], input[name="password"]').first
                except Exception as e_p_wait:
                    print(f"  Selector de contraseña no encontrado: {e_p_wait}")
                    browser.close()
                    return None

            pwd_input.fill(password)
            page.wait_for_timeout(500)
            page.click('button[type="submit"]')

            # Esperar navegación o reto de seguridad
            page.wait_for_timeout(7000)

            # Verificar si pide 2FA o código SMS
            es_2fa = False
            try:
                if page.locator('input[name="verificationCode"]').is_visible(timeout=2000) or page.locator('input[type="tel"]').is_visible(timeout=1000):
                    es_2fa = True
                elif "two_factor" in page.url or "challenge" in page.url:
                    es_2fa = True
            except Exception:
                pass

            if es_2fa:
                enviar_telegram(
                    chat_id,
                    f"📲 <b>CÓDIGO DE SEGURIDAD 2FA / SMS REQUERIDO</b>\n\n"
                    f"Instagram envió un código a tu teléfono o app para <b>@{username}</b>.\n\n"
                    f"👉 <b>Escribe el código de 6 dígitos aquí en Telegram para continuar:</b>"
                )
                codigo = esperar_codigo_telegram(chat_id, account=account)
                if codigo:
                    try:
                        inp = page.locator('input[name="verificationCode"]').first
                        if not inp.is_visible(timeout=1000):
                            inp = page.locator('input[type="tel"]').first
                        inp.fill(codigo)
                        page.click('button[type="button"]:has-text("Confirmar"), button:has-text("Enviar"), button[type="submit"]')
                        page.wait_for_timeout(6000)
                    except Exception as e_code:
                        print(f"Error introduciendo código: {e_code}")
                else:
                    browser.close()
                    return None

            # Extraer cookies
            cookies = context.cookies()
            for c in cookies:
                if c.get("name") == "sessionid":
                    sid = c.get("value")
                    browser.close()
                    return sid

            # Verificar si hubo error de contraseña
            try:
                err_el = page.locator('#slfErrorAlert')
                if err_el.is_visible(timeout=1500):
                    err_txt = err_el.text_content()
                    enviar_telegram(chat_id, f"❌ <b>Error de Instagram:</b> {err_txt}")
            except Exception:
                pass

            browser.close()
            return None
    except Exception as e:
        print(f"Error en login Playwright: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--sessionid", default="")
    parser.add_argument("--gemini-key", default="")
    parser.add_argument("--chat-id", required=True)
    args = parser.parse_args()

    account = normalizar_cuenta(args.account)
    username = (args.username or account).strip().lstrip("@")
    password = (args.password or "").strip()
    sessionid = (args.sessionid or "").strip()
    gemini_key = (args.gemini_key or "").strip()
    chat_id = args.chat_id.strip()

    # CASO 0: Guardar clave de Gemini IA
    if account in ("gemini", "ia") or gemini_key:
        key = gemini_key or sessionid or password
        if not key:
            enviar_telegram(chat_id, "❌ Error: La clave de Gemini no puede estar vacía.")
            return 1
        enviar_telegram(chat_id, "⏳ <b>Guardando Gemini API Key en GitHub Secrets...</b>")
        ok = guardar_secret_github("GEMINI_API_KEY", key)
        if ok:
            msg_exito = (
                f"╔════════════════════════════════╗\n"
                f"   🤖 ¡GEMINI IA CONECTADO CON ÉXITO!\n"
                f"╚════════════════════════════════╝\n"
                f"🧠 <b>Modelo:</b> Google Gemini 1.5 Flash\n"
                f"🔒 <b>Secret:</b> <code>GEMINI_API_KEY</code>\n"
                f"🟢 <b>Estado:</b> Ganchos y títulos automáticos activos\n\n"
                f"✨ A partir de ahora, cada Reel procesado usará Inteligencia Artificial para redactar títulos y ganchos de alta retención."
            )
            enviar_telegram(chat_id, msg_exito)
            return 0
        else:
            enviar_telegram(chat_id, "❌ Error guardando el secret <code>GEMINI_API_KEY</code> en GitHub.")
            return 1

    secret_name = SECRET_MAP.get(account, f"IG_SESSIONID_{account}")

    # CASO 1: Pegó el sessionid directamente
    if sessionid:
        enviar_telegram(chat_id, f"⏳ <b>Guardando sesión directa para @{account}...</b>")
        ok = guardar_secret_github(secret_name, sessionid)
        if ok:
            # Guardar en historial local
            if os.path.exists(HISTORIAL_PATH):
                try:
                    with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                        hist = json.load(f)
                    hist.setdefault("ig_sessions", {})[account] = sessionid
                    hist.setdefault("pausa_cuentas", {}).pop(account, None)
                    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
                        json.dump(hist, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            msg_exito = (
                f"╔════════════════════════════════╗\n"
                f"   ✅ ¡SESIÓN GUARDADA CON ÉXITO!\n"
                f"╚════════════════════════════════╝\n"
                f"👤 <b>Cuenta:</b> @{account}\n"
                f"🔒 <b>Secret:</b> <code>{secret_name}</code>\n"
                f"🟢 <b>Estado:</b> Lista para publicar automáticamente"
            )
            enviar_telegram(chat_id, msg_exito)
            return 0
        else:
            enviar_telegram(chat_id, f"❌ Error guardando el secret <code>{secret_name}</code> en GitHub.")
            return 1

    # CASO 2: Iniciar sesión con contraseña (API móvil emulada + fallback navegador)
    if password:
        enviar_telegram(
            chat_id,
            f"⏳ <b>INICIANDO SESIÓN EN @{username}...</b>\n"
            f"📱 Conectando emulador móvil en la nube...\n"
            f"<i>Si Instagram pide código de seguridad (2FA), te avisaré por aquí.</i>"
        )

        # 1. Intentar primero con instagrapi (API Oficial de Android, sin bloqueos de cookies web)
        sid = login_instagrapi(username, password, chat_id, account=account)
        if sid == "BAD_PASSWORD":
            return 1

        # 2. Si instagrapi no pudo completar (ej. challenge web o bloqueo de IP móvil), fallback a Playwright
        if not sid:
            print("Login móvil no completado. Intentando fallback con navegador Chromium...")
            enviar_telegram(
                chat_id,
                f"🔄 Verificando vía navegador alternativo en la nube..."
            )
            sid = login_playwright(username, password, chat_id, account=account)

        if sid:
            guardar_secret_github(secret_name, sid)
            if os.path.exists(HISTORIAL_PATH):
                try:
                    with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                        hist = json.load(f)
                    hist.setdefault("ig_sessions", {})[account] = sid
                    hist.setdefault("pausa_cuentas", {}).pop(account, None)
                    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
                        json.dump(hist, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            msg_exito = (
                f"╔════════════════════════════════╗\n"
                f"   🎉 ¡LOGIN EXITOSO EN LA NUBE!\n"
                f"╚════════════════════════════════╝\n"
                f"👤 <b>Cuenta:</b> @{username}\n"
                f"🔒 <b>Secret Renovado:</b> <code>{secret_name}</code>\n"
                f"🟢 <b>Estado:</b> 100% Conectada y Operativa\n\n"
                f"🚀 Ya puedes seguir subiendo Reels normalmente."
            )
            enviar_telegram(chat_id, msg_exito)
            return 0
        else:
            enviar_telegram(
                chat_id,
                f"⚠️ <b>No se pudo completar el login automático para @{username}.</b>\n\n"
                f"Recuerda que si estás de viaje, puedes usar el <b>Plan B</b>:\n"
                f"👉 Pega el link de TikTok, recibe el video en Telegram y pulsa <b>Compartir ➡️ Instagram</b>."
            )
            return 1

    enviar_telegram(chat_id, "⚠️ No se proporcionó contraseña ni sessionid.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
