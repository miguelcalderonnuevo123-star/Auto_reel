# 🎬 Auto_reel: Sistema 24/7 en la Nube (TikTok → Instagram Reels 1080x1920)

Bienvenido a la versión optimizada de **Auto_reel**, ahora corriendo de forma **100% autónoma en la nube** sin necesidad de tener ninguna computadora encendida.

---

## 📌 Resumen de Cambios y Estado Actual (11 Noviembre 2026)

### 1. ¿Por qué se cambió la configuración?
El sistema anterior corría un servidor continuo en GitHub Actions durante todo el día. Esto agotó los 2.000 minutos gratis mensuales en día y medio.

### 2. La Nueva Arquitectura (Sin Tarjeta y 100% Gratis)
* **Telegram Bot:** @Maykel0007_bot (Token: 8939773100:AAFU-dNMONlZ-7n7G9V7VDzsHmXmnJ-vIt4).
* **Cloudflare Worker (Webhook en la Nube 24/7):**
  * URL: https://wild-snowflake-a34c.maykellazaro60.workers.dev/
  * Atiende a Telegram de inmediato (menos de 1 segundo) sin gastar minutos ni requerir tarjeta de crédito.
* **Consumo de Minutos Blindado:**
  * **Modo Manual (3 Cuentas):** Cada vez que pegas un enlace de TikTok en Telegram y eliges la cuenta (@frutnovelas776, @novelas_frutosass o @frutnovelas777), GitHub despierta **únicamente 2 minutos** para renderizar y subir, y luego se apaga.
  * **Modo Automático (@novel_asanimadas):** GitHub despierta **solo 2 minutos** en 3 horarios del día (Hora Colombia: 9:00 AM, 2:00 PM y 7:00 PM), sube el video nuevo de @frutiverso3d y se apaga.
  * **Total mensual consumido:** ~720 minutos de los 2.000 disponibles. Te sobran más de 1.280 minutos al mes.

### 3. Optimizaciones y Correcciones Recientes
* **Corrección de Renderizado en FFmpeg:** Se corrigió el filtrado de drawtext para escapar : y caracteres especiales, evitando el error Invalid argument visto en títulos como PARTE 8: TODO.
* **Reducción de Timeout:** Blindado a 8 minutos máximos por ejecución en uto_reel.yml.
* **Dependencias 3x más rápidas:** Eliminado moviepy de equirements.txt, ahorrando 40 segundos por video.
* **Comentarios Virales Fijados:** Publicación y fijado automático (cl.comment_pin) con llamada a la acción dinámica según el número de parte.

---

## 🏠 INSTRUCCIONES PARA TU PC DE CASA (Al llegar del trabajo)

Tu PC de casa tiene configurada la ruta anterior (MayAn122/Auto_reel). Para sincronizar tu proyecto local con este nuevo repositorio, sigue estos pasos:

### Paso 1: Abrir la terminal
Abre PowerShell o Git Bash en la carpeta de tu proyecto:
`powershell
cd "C:\Users\piade\Desktop\Proyecto"
`

### Paso 2: Actualizar la dirección del repositorio en GitHub
Ejecuta este comando:
`powershell
git remote set-url origin https://github.com/May777p/Auto_reel.git
`

### Paso 3: Descargar todos los cambios nuevos
Ejecuta:
`powershell
git pull origin main
`

### Paso 4: ¡Listo!
* **No necesitas dejar tu PC de casa encendida ni scripts corriendo.**
* Tu bot funciona 24/7 desde la nube y lo manejas cómodamente desde tu celular con Telegram.

---

*Para ver la auditoría técnica completa paso a paso, consulta el archivo [AUDITORIA_CAMBIOS_AUTO_REEL.md](AUDITORIA_CAMBIOS_AUTO_REEL.md).*