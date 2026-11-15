import os, subprocess, sys, time, tempfile
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run_ff(cmd):
    tmp = tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False,
                                      encoding='utf-8', errors='replace')
    p = subprocess.Popen(cmd, stdout=tmp, stderr=subprocess.STDOUT)
    while p.poll() is None:
        time.sleep(1)
        print(".", end="", flush=True)
    print("", flush=True)
    tmp.close()
    out = ""
    try:
        with open(tmp.name, encoding='utf-8', errors='replace') as fh:
            out = fh.read()
    except Exception:
        pass
    os.remove(tmp.name)
    return p.returncode, out

# ============================================================
#   CONFIGURACION — CAMBIA SOLO ESTA SECCION
# ============================================================

# Archivo fuente por defecto (se usa si un clip no define "src")
SRC = r"C:\Users\piade\Desktop\Proyecto\refs\tiktok_ZSbctDnca.mp4"

# Carpeta de salida
OUT_DIR = r"C:\Users\piade\Desktop\Reels_Listos"

# Woosh de entrada (sonido de efecto)
WHOOSH = r"C:\Users\piade\.cache\music\pixabay2.mp3"

# Lista de clips a generar
# Cada clip tiene:
#   part_num  → numero de parte (para el nombre del archivo)
#   src       → (opcional) video fuente de este clip
#   start     → segundo de inicio en el video fuente
#   duration  → duracion en segundos de este clip
#   hook      → texto del gancho (aparece primero 2.5s arriba)
#   cta       → texto del call to action (aparece ultimos 3.5s abajo)
CLIPS = [
    {"part_num": 41, "src": r"C:\Users\piade\Desktop\Proyecto\refs\trenza7.mp4", "start": 0, "duration": 67.0, "hook": "LA TRENZA", "cta": "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA"},
]

# ============================================================
#   NO TOQUES NADA DEBAJO DE ESTA LINEA
# ============================================================

FFMPEG  = r"C:\Users\piade\AppData\Local\Programs\Python311\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
FONT    = "C\\:/Windows/Fonts/arialbd.ttf"
TARGET_W, TARGET_H = 1080, 1920

os.makedirs(OUT_DIR, exist_ok=True)

for cfg in CLIPS:
    part      = cfg["part_num"]
    src       = cfg.get("src", SRC)
    ss        = cfg["start"]
    dur       = cfg["duration"]
    hook_txt  = cfg["hook"].replace("'", "\\'")
    cta_txt   = cfg["cta"].replace("'", "\\'")
    t_cta     = dur - 3.5

    out_video = os.path.join(OUT_DIR, f"REEL_Cocardo parte {part}.mp4")
    out_copy  = os.path.join(OUT_DIR, f"REEL_Cocardo parte {part}_COPY.txt")

    print(f"\n========================================")
    print(f"  Parte {part}: '{cfg['hook']}'")
    print(f"  Inicio: {ss}s | Duracion: {dur}s")
    print(f"========================================")

    hook_lines = [l.strip() for l in cfg["hook"].split("|") if l.strip()]
    HOOK_FS = 65
    hook_filt = ""
    for i, line in enumerate(hook_lines):
        lt = line.replace("'", "\\'")
        hook_filt += (
            f"drawtext=fontfile='{FONT}':text='{lt}'"
            f":fontsize={HOOK_FS}:fontcolor=white:borderw=6:bordercolor=black"
            f":x=(w-text_w)/2:y={140 + i * (HOOK_FS + 16)}"
            f":enable='between(t,0,2.5)',"
        )

    cta_lines = [l.strip() for l in cfg["cta"].split("|") if l.strip()]
    CTA_FS = 70
    cta_filt = ""
    for i, line in enumerate(cta_lines):
        ct = line.replace("'", "\\'")
        cta_filt += (
            f"drawtext=fontfile='{FONT}':text='{ct}'"
            f":fontsize={CTA_FS}:fontcolor=yellow:borderw=7:bordercolor=black"
            f":x=(w-text_w)/2:y=h-430+{i * (CTA_FS + 14)}"
            f":enable='between(t,{t_cta},{dur})',"
        )
    cta_filt = cta_filt.rstrip(",")

    vf = (
        f"scale=1090:1939:flags=bicubic,"
        f"crop={TARGET_W}:{TARGET_H},"
        + hook_filt +
        cta_filt
    )

    fc = (
        f"[0:v]{vf}[v];"
        f"[0:a]loudnorm=I=-14:TP=-1.0:LRA=7[av];"
        f"[1:a]adelay=200|200,volume=0.35[sfx];"
        f"[av][sfx]amix=inputs=2:duration=first:dropout_transition=1[a]"
    )

    # Intento 1: GPU AMD
    cmd = [
        FFMPEG, "-y",
        "-ss", str(ss), "-t", str(dur),
        "-i", src,
        "-i", WHOOSH,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-map_metadata", "-1",
        "-metadata", "title=",
        "-metadata", "comment=",
        "-metadata", "encoder=",
        "-c:v", "h264_amf", "-quality", "speed", "-b:v", "8M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        out_video
    ]

    rc, r_out = run_ff(cmd)

    # Intento 2: CPU fallback si GPU falla
    if rc != 0:
        print("  GPU no disponible, usando CPU...")
        cmd_cpu = [
            FFMPEG, "-y",
            "-ss", str(ss), "-t", str(dur),
            "-i", src,
            "-i", WHOOSH,
            "-filter_complex", fc,
            "-map", "[v]", "-map", "[a]",
            "-map_metadata", "-1",
            "-metadata", "title=",
            "-metadata", "comment=",
            "-metadata", "encoder=",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-movflags", "+faststart",
            out_video
        ]
        rc, r_out = run_ff(cmd_cpu)

    if rc == 0 and os.path.exists(out_video):
        mb = os.path.getsize(out_video) / 1024 / 1024
        print(f"  LISTO: {mb:.1f} MB -> {os.path.basename(out_video)}")

        copy_text = f"""====================================================
COPIA Y PEGA ESTO EN LA DESCRIPCION:
====================================================

Que crees que va a pasar? Comentalo abajo

Comenta "PARTE {part + 1}" para ver el siguiente capitulo

Sigue la cuenta para no perderte ningun capitulo

.
.
#frutinovelas #historias #drama #novela #series #animacion #reels #parati #viral
====================================================
"""
        with open(out_copy, "w", encoding="utf-8") as f:
            f.write(copy_text)
        print(f"  Copy listo -> {os.path.basename(out_copy)}")
    else:
        print(f"  ERROR en Parte {part}:")
        print(r_out[-800:])

print("\n¡TODOS LOS REELS LISTOS!")
