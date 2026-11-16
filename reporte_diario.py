# -*- coding: utf-8 -*-
"""
reporte_diario.py — Chequeo de salud de sesiones + resumen de 24 h por Telegram.
Se ejecuta una vez al día desde GitHub Actions (BOT_NUBE.py --reporte).
"""

import time
from datetime import datetime, timedelta

import BOT_NUBE as BOT


def _salud_cuenta(cid, cfg, historial):
    secret = cfg.get("secret_sessionid") or "IG_SESSIONID"
    sid, _u, _p, _s = BOT.obtener_credenciales_ig(secret, historial=historial, cuenta_id=cid)
    if not sid:
        return False, f"sin sesión (`{secret}` vacío)"
    try:
        from instagrapi import Client
        proxy = (cfg.get("proxy") or "").strip() or None
        cl = Client(delay_range=[1, 3], proxy=proxy)
        try:
            cl.set_device(dict(cfg.get("device") or BOT.IG_DEVICE))
        except Exception:
            pass
        guardada = (historial.get("ig_identities") or {}).get(cid) or {}
        if guardada.get("sid_prefix") == sid[:16] and guardada.get("settings"):
            try:
                cl.set_settings(guardada["settings"])
            except Exception:
                pass
        cl.login_by_sessionid(sid)
        return True, "sesión OK"
    except Exception as e:
        return False, f"sesión caída ({str(e)[:70]})"


def main():
    granja = BOT.cargar_granja()
    historial = BOT.cargar_historial()
    cfg_auto = {}
    try:
        import json
        with open(BOT.GRANJA_PATH, "r", encoding="utf-8") as f:
            cfg_auto = json.load(f).get("auto_diario") or {}
    except Exception:
        pass
    off = float(cfg_auto.get("zona_utc", -5))
    ahora_utc = datetime.utcnow()
    desde = ahora_utc - timedelta(hours=24)

    conteo = {}
    for h in historial.get("history") or []:
        try:
            dt = datetime.strptime(h.get("date", ""), "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if dt >= desde and (h.get("ig_link") or "").strip():
            for a in h.get("accounts") or []:
                conteo[a] = conteo.get(a, 0) + 1

    lineas = []
    caidas = []
    for cid, cfg in granja.items():
        if not cfg.get("activa", False):
            continue
        ok, detalle = _salud_cuenta(cid, cfg, historial)
        icono = "✅" if ok else "🔴"
        lineas.append(f"{icono} @{cid}: {conteo.get(cid, 0)} Reel(s) en 24 h — {detalle}")
        if not ok:
            caidas.append(cid)
        time.sleep(2)

    cola = len(BOT.leer_cola_videos())
    local = ahora_utc + timedelta(hours=off)
    msg = (
        f"📊 Reporte diario de la Granja ({local:%d/%m %H:%M})\n\n"
        + "\n".join(lineas)
        + f"\n\n📥 Videos en cola manual: {cola}"
        + f"\n🎬 Total publicados en 24 h: {sum(conteo.values())}"
    )
    if caidas:
        msg += (
            "\n\n🚨 <b>ALERTA DE SESIÓN:</b> Renueva estas cuentas antes de la próxima publicación:\n"
            + "\n".join(f"• <b>@{c}</b> (Usa <code>/login {c}</code> o <code>/sesion {c}</code>)" for c in caidas)
        )
        msg_alerta = (
            "🚨 <b>ALERTA CRÍTICA: SESIÓN DE INSTAGRAM CADUCADA</b>\n\n"
            f"Se detectaron <b>{len(caidas)}</b> cuenta(s) con sesión desconectada o expirada:\n"
            + "\n".join([f"• <b>@{c}</b>" for c in caidas])
            + "\n\n👉 <i>Para reconectar de inmediato sin abrir la PC, usa el comando <code>/conectar</code> o presiona '🔑 Conectar Cuenta' en el menú.</i>"
        )
        BOT.enviar_mensaje_telegram(chat_id, msg_alerta)
    chat_id = historial.get("telegram_chat_id")
    for cfg in granja.values():
        chat_id = chat_id or cfg.get("owner_chat_id")
    chat_id = chat_id or 8804356608
    BOT.enviar_mensaje_telegram(chat_id, msg)
    print(msg)
    return 0
