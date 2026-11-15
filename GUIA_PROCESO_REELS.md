# Guía: cómo se hacen los reels (TikTok → MP4 vertical 1080x1920)

Documento para que otra IA (o una persona) reproduzca el proceso exacto.
Todo se ejecuta en Windows con PowerShell. Rutas fijas de esta máquina.

---

## MODO RÁPIDO (automático)

**Doble clic en `HACER_REEL.bat`** (en `C:\Users\piade\Desktop\Proyecto`).
Te pide tres cosas y hace todo solo:

1. Link del video
2. Nombre de la serie
3. Número de parte (Enter = 1)

Al terminar el video queda en `Reels_Listos` con el nombre final. La ventana
no se cierra hasta que pulses una tecla.

`AUTO_REEL.py` es el motor: descarga, mide duración, renderiza y guarda con el
nombre final. También se puede usar sin el .bat editando el bloque `CONFIG`
del principio:

```python
URL   = "https://www.tiktok.com/@usuario/video/123456789"
SERIE = "LA TRENZA"
PARTE = 7        # 1 = primera parte (sin "parte N" en el nombre)
HOOK  = ""       # vacío = usa SERIE; con "|" para dos líneas
```

y ejecutar:

```powershell
& "C:\Users\piade\AppData\Local\Programs\Python311\python.exe" -u "C:\Users\piade\Desktop\Proyecto\AUTO_REEL.py"
```

o sin editar nada:

```powershell
python AUTO_REEL.py "URL" "LA TRENZA" 7
```

Resultado directo: `C:\Users\piade\Desktop\Reels_Listos\REEL_LA TRENZA parte 7.mp4`.

Los pasos manuales de abajo quedan como referencia de lo que hace por dentro.

---

## 0. Rutas y programas

| Cosa | Ruta |
|---|---|
| Python | `C:\Users\piade\AppData\Local\Programs\Python311\python.exe` |
| FFmpeg | `C:\Users\piade\AppData\Local\Programs\Python311\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` |
| Script de render | `C:\Users\piade\Desktop\Proyecto\PLANTILLA_REEL.py` |
| Videos fuente | `C:\Users\piade\Desktop\Proyecto\refs\` |
| Salida final | `C:\Users\piade\Desktop\Reels_Listos\` |
| Whoosh | `C:\Users\piade\.cache\music\pixabay2.mp3` |
| Cookies TikTok | `C:\Users\piade\Desktop\Proyecto\refs\cookies.txt` |
| Logs | `C:\Users\piade\AppData\Local\Temp\opencode\` |

Requisitos: `yt-dlp`, `playwright` (para cookies), `cryptography`.

---

## 1. Descargar el video

```powershell
python -m yt_dlp --no-progress --retries 5 --cookies "C:\Users\piade\Desktop\Proyecto\refs\cookies.txt" `
  -f "bv*+ba/b" `
  -o "C:\Users\piade\Desktop\Proyecto\refs\NOMBRE.%(ext)s" `
  "https://www.tiktok.com/@usuario/video/ID"
```

- `NOMBRE` = identificador corto y único (ej. `trenza7`, `humillaron3`).
- Sale `refs\NOMBRE.mp4`.

### 1.a Si TikTok da 403
Es transitorio. Esperar 45–60 s y reintentar (2–3 veces). No cambiar nada más.

### 1.b Si dice "This post may not be comfortable... Log in for access"
El video es sensible y exige sesión. Usar cookies de **Brave** (es el navegador donde el usuario tiene TikTok abierto).

**Cómo se obtienen las cookies (una vez):**

1. Cerrar Brave: `Get-Process brave | Stop-Process -Force`
2. Lanzar Brave con puerto de depuración y leer las cookies ya descifradas por el propio navegador
   (las cookies modernas son `v20`, cifradas con "app-bound encryption"; DPAPI a mano NO sirve):

```python
# brave_cdp_cookies.py
import subprocess, time, os, urllib.request
from playwright.sync_api import sync_playwright

BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
UDD   = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
OUT   = r"C:\Users\piade\Desktop\Proyecto\refs\cookies.txt"
PORT  = 9333

proc = subprocess.Popen([BRAVE, f"--remote-debugging-port={PORT}",
                         f"--user-data-dir={UDD}", "--no-first-run", "about:blank"])
for _ in range(60):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1).read(); break
    except Exception:
        time.sleep(1)

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    tk = [c for c in ctx.cookies() if "tiktok" in c["domain"]]
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in tk:
        exp = int(c.get("expires") or 0)
        lines.append("\t".join([
            c["domain"], "TRUE" if c["domain"].startswith(".") else "FALSE",
            c.get("path") or "/", "TRUE" if c.get("secure") else "FALSE",
            str(max(exp, 0)), c["name"], c["value"]]))
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("COOKIES_OK", len(tk))
    b.close()
proc.terminate()
```

3. Ejecutar `python brave_cdp_cookies.py` y volver a descargar con `--cookies ...`.
4. Las cookies caducan: si vuelve el error de login, repetir este paso.

---

## 2. Medir la duración

```powershell
$ff = (Get-ChildItem "C:\Users\piade\AppData\Local\Programs\Python311\Lib\site-packages\imageio_ffmpeg\binaries\*.exe").FullName
& $ff -i "C:\Users\piade\Desktop\Proyecto\refs\NOMBRE.mp4" 2>&1 | Select-String "Duration"
```

De ahí sale `duration` para el script (segundos, con 1 decimal).
Si el video es muy largo (>2 min) se puede subir entero; el usuario dirá si quiere partes.

---

## 3. Configurar `PLANTILLA_REEL.py`

Se edita **solo** la lista `CLIPS` (líneas ~44-46). Cada elemento:

```python
{"part_num": 41,
 "src": r"C:\Users\piade\Desktop\Proyecto\refs\trenza7.mp4",
 "start": 0,
 "duration": 67.0,
 "hook": "LA TRENZA",
 "cta": "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA"},
```

- `part_num`: número **único** (si se repite, se pisa el archivo de salida). Van por 41.
- `start`: segundo de inicio (normalmente 0).
- `hook`: texto de arriba (0–2.5 s). El `|` separa dos líneas.
- `cta`: texto de abajo (últimos 3.5 s). El `|` separa dos líneas.

**Regla de oro de edición:** usar la herramienta de edición de texto (UTF-8), nunca
`Get-Content -Raw | Set-Content -Encoding UTF8` (rompe tildes: `SE SENTÃA`).

---

## 4. Qué hace el script (para replicarlo en otro lado)

Salida: `Reels_Listos\REEL_Cocardo parte {part}.mp4` (luego se renombra a mano).

**Video:**
```
scale=1090:1939:flags=bicubic, crop=1080:1920
+ hook (drawtext, Arial Bold 65px, blanco, borde negro 6, y=140 + i*81, t 0–2.5)
+ cta  (drawtext, Arial Bold 70px, amarillo, borde negro 7, y=h-430 + i*84, t dur-3.5–dur)
```

**Audio:**
```
[0:a] loudnorm=I=-14:TP=-1.0:LRA=7
[1:a] adelay=200|200, volume=0.35
amix=inputs=2:duration=first
```

**Codificación:** intenta `h264_amf -quality speed -b:v 8M`; si falla, `libx264 -preset ultrafast -crf 20`.
Audio AAC 192k 44.1k. `-movflags +faststart`. Metadatos vacíos (`-map_metadata -1` + `title=`, `comment=`, `encoder=`).

**Comando equivalente (una parte):**
```powershell
& $ff -y -ss 0 -t 67.0 -i "refs\trenza7.mp4" -i "C:\Users\piade\.cache\music\pixabay2.mp3" `
 -filter_complex "[0:v]scale=1090:1939:flags=bicubic,crop=1080:1920,drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='LA TRENZA':fontsize=65:fontcolor=white:borderw=6:bordercolor=black:x=(w-text_w)/2:y=140:enable='between(t,0,2.5)',drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='SÍGUEME PARA DESCUBRIR':fontsize=70:fontcolor=yellow:borderw=7:bordercolor=black:x=(w-text_w)/2:y=h-430:enable='between(t,63.5,67.0)',drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='LA PRÓXIMA HISTORIA':fontsize=70:fontcolor=yellow:borderw=7:bordercolor=black:x=(w-text_w)/2:y=h-346:enable='between(t,63.5,67.0)'[v];[0:a]loudnorm=I=-14:TP=-1.0:LRA=7[av];[1:a]adelay=200|200,volume=0.35[sfx];[av][sfx]amix=inputs=2:duration=first:dropout_transition=1[a]" `
 -map "[v]" -map "[a]" -map_metadata -1 -metadata title= -metadata comment= -metadata encoder= `
 -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -ar 44100 -movflags +faststart `
 "salida.mp4"
```

---

## 5. Lanzar el render

El shell de la herramienta corta comandos largos (~200 s) y puede matar el proceso.
Dos opciones que funcionan:

**A) En segundo plano gestionado** (recomendado):
```powershell
& "C:\Users\piade\AppData\Local\Programs\Python311\python.exe" -u "C:\Users\piade\Desktop\Proyecto\PLANTILLA_REEL.py" *> "C:\Users\piade\AppData\Local\Temp\opencode\NOMBRE.log"
```

**B) Totalmente desacoplado** (sobrevive al cierre del shell):
```powershell
$cmd = 'cmd /c ""C:\Users\piade\AppData\Local\Programs\Python311\python.exe" -u "C:\Users\piade\Desktop\Proyecto\PLANTILLA_REEL.py" > "C:\...\NOMBRE.log" 2>&1"'
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd}
```

Duración típica: 1–3 min por minuto de video (GPU/CPU).

---

## 6. Renombrar la salida

Windows bloquea el archivo unos segundos. Usar bucle de reintentos:

```powershell
1..20 | ForEach-Object {
  try {
    Rename-Item "C:\Users\piade\Desktop\Reels_Listos\REEL_Cocardo parte 41.mp4" `
                "REEL_LA TRENZA parte 7.mp4" -Force -ErrorAction Stop
    break
  } catch { Start-Sleep 4 }
}
```

**Nomenclatura:**
- Primera parte de una serie: `REEL_<SERIE>.mp4`
- Siguientes: `REEL_<SERIE> parte N.mp4`
- Sin tildes raras ni símbolos; el nombre lo dicta el usuario.

---

## 7. Verificación rápida

```powershell
Get-ChildItem "C:\Users\piade\Desktop\Reels_Listos\" -Filter "*SERIE*" |
  ForEach-Object { $_.Name + " | " + [math]::Round($_.Length/1MB,1) + " MB" }
```

Comprobar duración con ffmpeg (`Duration`) y que el tamaño sea razonable
(~50–160 MB según largo).

---

## 8. Problemas conocidos

| Síntoma | Causa / solución |
|---|---|
| `403 Forbidden` | Transitorio: esperar 45–60 s y reintentar. |
| "Log in for access" | Video sensible: regenerar `cookies.txt` desde Brave (paso 1.b). |
| `Failed to decrypt with DPAPI` | Cookies `v20`; no sirve DPAPI. Usar el script CDP. |
| Archivo de 0 MB | El render se cortó. Borrarlo y relanzar. |
| `Rename-Item` falla | Archivo bloqueado: bucle con `Start-Sleep`. |
| Tildes rotas | Se usó `Set-Content -Encoding UTF8`; editar con herramienta UTF-8. |
| Render eterno | `ffmpeg` con `stdout=PIPE` se bloquea; el script usa archivo temporal. |
