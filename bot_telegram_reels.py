# -*- coding: utf-8 -*-
"""
bot_telegram_reels.py — Bot interactivo en vivo (@Maykel0007_bot) para controlar tus Reels desde Telegram.
Escucha 24/7 tus mensajes en Telegram:
- Comando /start -> Menú de bienvenida y estado.
- Cuando le pegas cualquier link de TikTok -> Te muestra botones para:
  1) Subir AHORA MISMO (con Hook automático de la descripción)
  2) Escribir tú el Hook antes de subirlo
  3) Elegir si tapar marca de agua (Auto / Arriba / Abajo / No)
  4) Guardar en la cola (cola_videos.txt)
"""

import json
import os
import re
import subprocess
import sys
import time
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = r"C:\Users\piade\Desktop\Descargar videos gratis\token_insta.txt"
HISTORIAL_PATH = os.path.join(BASE, "historial_bot.json")
COLA_PATH = os.path.join(BASE, "cola_videos.txt")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
if not TOKEN and os.path.exists(TOKEN_FILE):
    TOKEN = open(TOKEN_FILE, encoding="utf-8").read().strip()

API = f"https://api.telegram.org/bot{TOKEN}"

# Estado en memoria por chat_id
SESIONES = {}


def tg_post(method, payload):
    try:
        r = requests.post(f"{API}/{method}", json=payload, timeout=20)
        return r.json()
    except Exception as e:
        print(f"Error Telegram ({method}): {e}")
        return {}


def send_msg(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return tg_post("sendMessage", payload)


def edit_msg(chat_id, message_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return tg_post("editMessageText", payload)


def guardar_chat_id(chat_id):
    try:
        data = {}
        if os.path.exists(HISTORIAL_PATH):
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["telegram_chat_id"] = chat_id
        with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def menu_video(chat_id, url, hook="", marca="auto", msg_id=None):
    hook_txt = hook if hook else "(Automático de la descripción de TikTok)"
    texto = (
        f"🎬 Video de TikTok listo para procesar:\n{url}\n\n"
        f"📌 Hook arriba: {hook_txt}\n"
        f"🏷️ Tapar marca (@frutnovelas776): {marca.upper()}\n\n"
        f"¿Qué quieres hacer?"
    )
    botones = [
        [{"text": "🚀 SUBIR A INSTAGRAM AHORA", "callback_data": "subir_ahora"}],
        [
            {"text": "✏️ Cambiar Hook", "callback_data": "pedir_hook"},
            {"text": f"🏷️ Marca: {marca.upper()}", "callback_data": "cambiar_marca"},
        ],
        [{"text": "📥 Guardar en Cola (cola_videos.txt)", "callback_data": "guardar_cola"}],
    ]
    if msg_id:
        edit_msg(chat_id, msg_id, texto, botones)
    else:
        send_msg(chat_id, texto, botones)


def ejecutar_subida(chat_id, url, hook, marca):
    send_msg(
        chat_id,
        f"⏳ Descargando, renderizando con AUTO_REEL (portada + audio + marca: {marca}) y subiendo a tu Instagram...\n"
        f"Te avisaré por aquí en 1-2 minutos apenas esté publicado."
    )
    cmd = [
        sys.executable, "-u",
        os.path.join(BASE, "BOT_NUBE.py"),
        "--url", url,
        "--marca", marca,
    ]
    if hook:
        cmd += ["--hook", hook]

    # Ejecutar en proceso hijo sin bloquear el bot
    subprocess.Popen(cmd, cwd=BASE)


def procesar_update(upd):
    if "message" in upd:
        msg = upd["message"]
        chat_id = msg["chat"]["id"]
        txt = (msg.get("text") or "").strip()
        guardar_chat_id(chat_id)

        st = SESIONES.setdefault(chat_id, {"url": "", "hook": "", "marca": "auto", "esperando_hook": False})

        if txt.startswith("/start") or txt.startswith("/ayuda"):
            st["esperando_hook"] = False
            send_msg(
                chat_id,
                "👋 ¡Hola! Soy tu Bot de AUTO_REEL para Instagram.\n\n"
                "✅ Mándame cualquier link de TikTok por aquí y te mostraré los botones para:\n"
                "• Subirlo ahora mismo a tu Instagram Reels\n"
                "• Ponerle el Hook automático o escribir uno tú\n"
                "• Tapar marca de agua (@frutnovelas776)\n"
                "• O meterlo a la cola\n\n"
                "📎 ¡Pega un link de TikTok para empezar!",
                buttons=[[
                    {"text": "🔥 Subir el más nuevo de @helloword.visuals", "callback_data": "subir_helloword"}
                ]]
            )
            return

        if st.get("esperando_hook") and st.get("url") and "tiktok.com" not in txt:
            st["hook"] = txt
            st["esperando_hook"] = False
            menu_video(chat_id, st["url"], st["hook"], st["marca"])
            return

        m_url = re.search(r"(https?://[^\s]+tiktok\.com[^\s]+)", txt)
        if m_url:
            st["url"] = m_url.group(1)
            partes = [p.strip() for p in txt.split("|", 1)]
            st["hook"] = partes[1] if len(partes) > 1 else ""
            st["esperando_hook"] = False
            menu_video(chat_id, st["url"], st["hook"], st["marca"])
            return

        send_msg(chat_id, "📎 Envíame un link de TikTok (ej. https://www.tiktok.com/...) o escribe /start.")

    elif "callback_query" in upd:
        cq = upd["callback_query"]
        cq_id = cq["id"]
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        data = cq.get("data", "")
        tg_post("answerCallbackQuery", {"callback_query_id": cq_id})

        st = SESIONES.setdefault(chat_id, {"url": "", "hook": "", "marca": "auto", "esperando_hook": False})

        if data == "subir_helloword":
            send_msg(chat_id, "🔍 Buscando el siguiente video nuevo de @helloword.visuals y subiéndolo a Instagram...")
            subprocess.Popen([sys.executable, "-u", os.path.join(BASE, "BOT_NUBE.py")], cwd=BASE)
            return

        if not st.get("url"):
            send_msg(chat_id, "⚠️ Primero envíame un link de TikTok.")
            return

        if data == "cambiar_marca":
            orden = ["auto", "arriba", "abajo", "no"]
            idx = (orden.index(st["marca"]) + 1) % len(orden) if st["marca"] in orden else 0
            st["marca"] = orden[idx]
            menu_video(chat_id, st["url"], st["hook"], st["marca"], msg_id=msg_id)

        elif data == "pedir_hook":
            st["esperando_hook"] = True
            send_msg(chat_id, "✏️ Escribe ahora el texto que quieres que salga arriba en el Hook (puedes usar | para separar 2 líneas):")

        elif data == "guardar_cola":
            linea = f"{st['url']} | {st['hook']}".strip(" |")
            with open(COLA_PATH, "a", encoding="utf-8") as f:
                f.write(linea + "\n")
            edit_msg(chat_id, msg_id, f"📥 Guardado en cola_videos.txt:\n{linea}")

        elif data == "subir_ahora":
            edit_msg(chat_id, msg_id, f"🚀 Iniciando proceso para:\n{st['url']}")
            ejecutar_subida(chat_id, st["url"], st["hook"], st["marca"])


def main():
    print("=" * 60)
    print("  BOT DE TELEGRAM @Maykel0007_bot ENCENDIDO Y ESCUCHANDO")
    print("=" * 60)
    offset = 0
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 25}, timeout=35)
            res = r.json()
            if res.get("ok"):
                for upd in res.get("result", []):
                    offset = upd["update_id"] + 1
                    procesar_update(upd)
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(3)


if __name__ == "__main__":
    main()
