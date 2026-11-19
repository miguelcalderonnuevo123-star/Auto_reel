# -*- coding: utf-8 -*-
"""
planificador.py — Piloto automático diario por cuenta (solo librería estándar, arranca en <1 s).

Lo ejecuta GitHub Actions cada 30 min (cron). Decide si ALGUNA cuenta activa "toca" publicar ahora
según su plan del día (N horarios repartidos con jitter aleatorio dentro de una ventana horaria) y
escribe `cuenta=<id>` en $GITHUB_OUTPUT (vacío = no hacer nada, el resto del workflow se omite).

Configuración en cuentas_granja.json (bloque opcional "auto_diario"):
  {
    "auto_diario": {"activo": true, "zona_utc": -5, "ventana": [9, 22], "posts_por_dia": 2,
                    "min_gap_min": 90, "reintento_min": 25},
    "cuentas": { "mi_cuenta": {"activa": true, "auto_diario": true, "posts_por_dia": 3, ...} }
  }
Por cuenta se puede poner "auto_diario": false para excluirla, o "posts_por_dia" propio.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
GRANJA_PATH = os.path.join(BASE, "cuentas_granja.json")
HISTORIAL_PATH = os.path.join(BASE, "historial_bot.json")

DEFAULTS = {
    "activo": True,
    "zona_utc": -5,
    "ventana": [9, 22],
    "posts_por_dia": 2,
    "min_gap_min": 90,
    "reintento_min": 25,
    "max_posts_global": 0,
}


def _leer_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def cargar_config():
    data = _leer_json(GRANJA_PATH, {})
    cfg = dict(DEFAULTS)
    cfg.update(data.get("auto_diario") or {})
    return cfg, (data.get("cuentas") or {})


def slots_del_dia(cid, indice, fecha_local, n, ventana):
    """Horarios (datetime local sin tz) del día para una cuenta: repartidos + jitter estable por día/cuenta."""
    ini_h, fin_h = float(ventana[0]), float(ventana[1])
    inicio = datetime(fecha_local.year, fecha_local.month, fecha_local.day) + timedelta(hours=ini_h)
    fin = datetime(fecha_local.year, fecha_local.month, fecha_local.day) + timedelta(hours=fin_h)
    span_min = (fin - inicio).total_seconds() / 60.0
    slots = []
    for i in range(n):
        rng = random.Random(f"{fecha_local.isoformat()}|{cid}|{i}")
        centro = span_min * (i + 0.5) / n
        t = inicio + timedelta(minutes=centro + rng.randint(-25, 25) + indice * 9)
        t = min(max(t, inicio), fin - timedelta(minutes=30))
        slots.append(t)
    return sorted(slots)


def publicaciones_hoy(historial, cid, fecha_local, offset_h):
    n = 0
    for h in historial.get("history") or []:
        if cid not in (h.get("accounts") or []):
            continue
        try:
            dt = datetime.strptime(h.get("date", ""), "%Y-%m-%d %H:%M:%S") + timedelta(hours=offset_h)
        except Exception:
            continue
        if dt.date() == fecha_local and (h.get("ig_link") or "").strip():
            n += 1
    return n


def elegir_cuenta(marcar_intento=True, ahora_utc=None):
    cfg, granja = cargar_config()
    if not cfg.get("activo", True):
        return "", "auto_diario desactivado en cuentas_granja.json"

    # Solo activar piloto automático si el usuario dejó videos en cola_videos.txt (evita publicar videos al azar)
    cola_path = os.path.join(BASE, "cola_videos.txt")
    tiene_cola = False
    if os.path.exists(cola_path):
        try:
            with open(cola_path, "r", encoding="utf-8") as fc:
                tiene_cola = any(ln.strip() and not ln.strip().startswith("#") and "tiktok.com" in ln for ln in fc)
        except Exception:
            pass
    if not tiene_cola:
        return "", "cola_videos.txt vacía (control manual activo, 0 minutos gastados)"

    historial = _leer_json(HISTORIAL_PATH, {})
    ahora_utc = ahora_utc or datetime.now(timezone.utc).replace(tzinfo=None)
    off = float(cfg["zona_utc"])
    ahora_local = ahora_utc + timedelta(hours=off)
    hoy = ahora_local.date()
    estado_all = historial.setdefault("auto_diario_estado", {})
    last_up = historial.get("last_upload_by_account") or {}

    # Mejora #13: Límite global diario de posts en la granja
    global_limit = int(cfg.get("max_posts_global") or 0)
    if global_limit > 0:
        total_hoy = sum(publicaciones_hoy(historial, c_id, hoy, off) for c_id in granja.keys())
        if total_hoy >= global_limit:
            return "", f"Límite global diario alcanzado ({total_hoy}/{global_limit} posts hoy)"

    candidatas = []
    for idx, (cid, c) in enumerate(granja.items()):
        if not c.get("activa", False) or not c.get("auto_diario", True):
            continue
        # Cuenta pausada por challenge / sesión caída (se limpia sola al vencer o con /login)
        try:
            if float((historial.get("pausa_cuentas") or {}).get(cid, 0)) > ahora_utc.replace(tzinfo=timezone.utc).timestamp():
                continue
        except Exception:
            pass
        n = int(c.get("posts_por_dia", cfg["posts_por_dia"]))
        if n <= 0:
            continue
        # Calentamiento progresivo para cuentas nuevas
        first_seen = (historial.get("account_first_seen") or {}).get(cid)
        if first_seen:
            try:
                dias_activa = (ahora_utc.timestamp() - float(first_seen)) / 86400.0
                if dias_activa < 3:
                    n = min(n, 1)
                elif dias_activa < 7:
                    n = min(n, 2)
            except Exception:
                pass

        # Mejora #13: Límite estricto por cuenta (evita sobrepasar cuota de publicaciones/día)
        max_cuenta = int(c.get("max_posts_dia") or n)
        hechos = publicaciones_hoy(historial, cid, hoy, off)
        if hechos >= max_cuenta:
            continue

        slots = slots_del_dia(cid, idx, hoy, n, cfg["ventana"])
        vencidos = sum(1 for s in slots if s <= ahora_local)
        pendientes = vencidos - hechos
        if pendientes <= 0:
            continue

        # Espacio mínimo desde la última subida de esa cuenta
        try:
            if ahora_utc.timestamp() - float(last_up.get(cid, 0)) < cfg["min_gap_min"] * 60:
                continue
        except Exception:
            pass

        # Límite de reintentos diarios (evita bucles si falla la descarga/sesión)
        est = estado_all.get(cid) or {}
        if est.get("fecha") != hoy.isoformat():
            est = {"fecha": hoy.isoformat(), "intentos": 0, "ultimo": 0}
        if est["intentos"] >= n * 2 + 2:
            continue
        if ahora_utc.timestamp() - float(est.get("ultimo", 0)) < cfg["reintento_min"] * 60:
            continue

        candidatas.append((pendientes, -idx, cid, est))

    if not candidatas:
        return "", f"Nadie toca ahora ({ahora_local:%Y-%m-%d %H:%M} hora local)"

    candidatas.sort(reverse=True)
    _, _, cid, est = candidatas[0]
    est["intentos"] += 1
    est["ultimo"] = ahora_utc.replace(tzinfo=timezone.utc).timestamp()
    if marcar_intento:
        estado_all[cid] = est
        with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
    return cid, f"Toca publicar en @{cid} (intento {est['intentos']} de hoy)"


def main():
    dry = "--dry" in sys.argv
    cid, motivo = elegir_cuenta(marcar_intento=not dry)
    print(f"[planificador] {motivo}")
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"cuenta={cid}\n")
    else:
        print(f"cuenta={cid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
