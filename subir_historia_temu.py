# -*- coding: utf-8 -*-
"""
subir_historia_temu.py — Sube la Historia de Temu Black Friday a Instagram
con el Sticker de Enlace oficial colocado exactamente sobre el botón de acción.
"""

import os
import sys
import json
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import BOT_NUBE
from instagrapi import Client
from instagrapi.types import StoryLink

IMG_PATH = r"C:\Users\piade\Desktop\HISTORIA_TEMU_BLACK_FRIDAY.png"
URL_TEMU = "https://temu.to/k/gltnyhsrjiw"

def subir_a_cuenta(cuenta_id):
    if not os.path.exists(IMG_PATH):
        print(f"❌ Error: No se encontró la imagen en {IMG_PATH}")
        return False

    granja = BOT_NUBE.cargar_granja()
    cfg_cuenta = granja.get(cuenta_id, {})
    nombre = cfg_cuenta.get("nombre", f"@{cuenta_id}")
    secret_name = cfg_cuenta.get("secret_sessionid", "IG_SESSIONID")
    device_cfg = cfg_cuenta.get("device", BOT_NUBE.IG_DEVICE)
    historial = BOT_NUBE.cargar_historial()

    sid, user, pwd, settings_json = BOT_NUBE.obtener_credenciales_ig(secret_name, historial=historial, cuenta_id=cuenta_id)
    if not sid and not (user and pwd):
        print(f"❌ No se encontraron credenciales para {nombre}")
        return False

    print(f"\n🔐 Conectando a {nombre}...")
    cl = Client(delay_range=[1.5, 3.0])
    try:
        cl.set_device(dict(device_cfg))
    except Exception:
        pass

    # Restaurar identidad si existe
    identities = historial.get("ig_identities") or {}
    saved_id = identities.get(cuenta_id) or {}
    if isinstance(saved_id, dict) and saved_id.get("sid_prefix") == sid[:16] and saved_id.get("settings"):
        try:
            cl.set_settings(saved_id["settings"])
        except Exception:
            pass

    try:
        cl.login_by_sessionid(sid)
        print(f"✅ Sesión iniciada con éxito en {nombre}")
    except Exception as e:
        print(f"❌ Falló inicio de sesión en {nombre}: {e}")
        return False

    print(f"📲 Subiendo Historia a {nombre} con Link Sticker oficial ({URL_TEMU})...")
    try:
        # y=0.643 corresponde a 1235px de 1920px (justo sobre el botón rojo equilibrado)
        story = cl.photo_upload_to_story(
            Path(IMG_PATH),
            caption="RECLAMAR 40% OFF AQUÍ",
            links=[StoryLink(webUri=URL_TEMU, x=0.5, y=0.643)],
        )
        pk = getattr(story, "pk", None) or getattr(story, "id", "OK")
        print(f"🎉 ¡HISTORIA PUBLICADA CON ÉXITO EN {nombre}! (Story ID: {pk})")

        # Notificar a Telegram
        try:
            chat_id = 8804356608
            BOT_NUBE.enviar_mensaje_telegram(
                chat_id,
                f"🛍️ <b>¡Historia de Temu Black Friday publicada!</b>\n\n"
                f"👤 <b>Cuenta:</b> {nombre}\n"
                f"🔗 <b>Enlace de Afiliado:</b> {URL_TEMU}\n"
                f"🎟️ <b>Código:</b> <code>alf607795</code>"
            )
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"❌ Error al subir la historia: {e}")
        return False

def menu():
    print("=" * 60)
    print("   🛍️ PUBLICADOR DE HISTORIA TEMU BLACK FRIDAY")
    print("=" * 60)
    print("Cuentas disponibles:")
    print("  [1] 🍓 @frutnovelas776")
    print("  [2] 🍍 @novelas_frutosass")
    print("  [3] 🍉 @frutnovelas777")
    print("  [4] 🍇 @novel_asanimadas")
    print("  [5] 📖 @bibliareflexiones.a")
    print("  [6] 🚀 Publicar en TODAS las cuentas a la vez")
    print("  [0] Salir")
    print("=" * 60)

    if len(sys.argv) > 1:
        elec = sys.argv[1].strip()
    else:
        elec = input("\n👉 Elige el número de la cuenta donde subirla: ").strip()

    mapa = {
        "1": ["frutnovelas776"],
        "2": ["novelas_frutosass"],
        "3": ["frutnovelas777"],
        "4": ["novel_asanimadas"],
        "5": ["bibliareflexiones_a"],
        "6": ["frutnovelas776", "novelas_frutosass", "frutnovelas777", "novel_asanimadas", "bibliareflexiones_a"],
    }

    cuentas = mapa.get(elec)
    if not cuentas:
        print("Operación cancelada.")
        return

    for cid in cuentas:
        subir_a_cuenta(cid)
        if len(cuentas) > 1:
            time.sleep(5)

if __name__ == "__main__":
    menu()
