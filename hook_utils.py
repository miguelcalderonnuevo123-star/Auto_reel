# -*- coding: utf-8 -*-
"""
hook_utils.py — Genera un Hook inteligente, dramático e intrigante para Frutinovelas:
- Elimina prefijos basura como 'EPISODIO 1:', 'PARTE 2-', 'Capítulo 5:', etc.
- Extrae la frase de mayor impacto (exclamaciones o primera idea completa).
- Evita que las frases queden cortadas a la mitad en palabras colgantes ('POR', 'DE', 'QUE', etc.).
- Divide automáticamente en 2 líneas perfectamente balanceadas para 1080x1920 vertical.
"""

import hashlib
import json
import os
import re
import urllib.request

HASHTAGS_GENERICOS = {
    "fyp", "fy", "fypシ", "fypage", "foryou", "foryoupage", "parati", "paratii", "paratí",
    "viral", "viralvideo", "virales", "tiktok", "tiktoker", "trending", "trend", "tendencia",
    "capcut", "ia", "ai", "3d", "animation", "animacion", "animación", "animated", "xyzbca",
    "frutinovelas", "frutinovela", "fruit", "fruits", "fruta", "frutas", "foodstory",
    "partii", "parte", "part", "parte1", "parte2", "parte3", "capibara", "historia", "historias",
    "storytime", "story", "novela", "novelas", "reels", "reel", "explore", "explorar",
    "humor", "comedia", "drama", "funny", "meme", "memes", "edit", "video", "videos",
    "frutiverso", "frutiverso3d", "aiart", "aivideo", "iavideo", "cartoon", "dibujos",
    "minidrama", "leccion", "lección", "shorts", "paratiiiiiiiiiii", "animacion3d", "historiasdefrutas",
    "cuentos3d", "historias3d", "animaciones", "videoviral", "reelviral", "viralreels",
    "cuentos", "cuento", "fabula", "fabulas", "audiolibro", "audio", "music", "song"
}

PALABRAS_CLAVE_GENERICAS = {
    "animacion", "animada", "animado", "animation", "animated", "3d", "ia", "ai",
    "historia", "historias", "story", "storytime", "novela", "novelas", "fruti", "fruta", "frutas",
    "tiktok", "tiktoker", "parati", "fyp", "foryou", "viral", "trend", "trending", "tendencia",
    "capcut", "edit", "video", "videos", "short", "shorts", "reel", "reels", "explore",
    "humor", "comedia", "drama", "funny", "meme", "memes", "dibujo", "dibujos", "cartoon",
    "cuento", "cuentos", "fabula", "fabulas", "leccion", "minidrama", "xyzbca", "capibara",
    "paratii", "foryoupage"
}

PALABRAS_COLGANTES = {
    "por", "de", "para", "en", "con", "que", "a", "y", "o", "un", "una", "unos", "unas",
    "el", "la", "los", "las", "del", "al", "su", "sus", "como", "pero", "sin", "se",
    "era", "es", "fue", "eran", "cuando", "donde", "si", "porque", "le", "lo", "me", "te", "nos",
    "yo", "tú", "tu", "él", "ella", "ellos", "ellas", "mi", "mis", "ti"
}

PLANTILLAS_CON_TEMA = [
    "{X}|EL FINAL TE SORPRENDERÁ",
    "LA VERDAD SOBRE|{X}",
    "{X}|NADIE ESPERABA ESTO",
    "EL CASO DE|{X}",
    "{X}|MIRA HASTA EL FINAL",
]

PLANTILLAS_GENERICAS = [
    "NADIE ESPERABA|ESTE FINAL",
    "MIRA LO QUE|PASÓ AL FINAL",
    "ESTO SE PUSO|MUY SERIO",
    "NO VAS A CREER|LO QUE HIZO",
    "EL FINAL TE VA|A SORPRENDER",
    "¿QUÉ HARÍAS TÚ|EN SU LUGAR?",
    "NADIE LE CREYÓ|HASTA QUE PASÓ ESTO",
    "ESPERA AL FINAL|NO TE LO PIERDAS",
    "MIRA HASTA EL FINAL|VALE LA PENA",
    "EL KARMA EXISTE|Y ESTO LO DEMUESTRA",
    "PENSÓ QUE NADIE|LO ESTABA VIENDO",
    "NUNCA JUZGUES|ANTES DE TIEMPO",
    "¿FUE JUSTO ESTO?|MIRA LO QUE PASÓ",
    "UN GIRO QUE|NADIE ESPERABA",
    "LO QUE DESCUBRIÓ|CAMBIÓ TODO",
    "ESTO SE SALIÓ|DE CONTROL",
]

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D]+",
    flags=re.UNICODE,
)


def generar_hook_con_gemini(raw_desc, api_key=None):
    """
    Usa Google Gemini para transformar la descripción del video en un gancho viral irresistible
    en 2 líneas balanceadas separadas por '|' (máximo 4 palabras por línea).
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None

    texto = limpiar_texto_descripcion(raw_desc)
    if not texto or len(texto) < 4:
        return None

    prompt = (
        "Eres un editor viral de Instagram Reels y TikTok experto en Frutinovelas, fábulas 3D y minidramas animados.\n"
        f"Texto base del video: \"{texto}\"\n\n"
        "Crea un título/hook ultra intrigante, de alta tensión o karma que enganche en el segundo 1.\n"
        "REGLAS ESTRICTAS:\n"
        "1. Devuelve EXACTAMENTE 2 LÍNEAS separadas por '|' (Ejemplo: NADIE ESPERABA|ESTE FINAL).\n"
        "2. Máximo 2 a 3 palabras por línea (frases ultra cortas, directas y potentes, de 3 a 5 palabras en total, para que el texto sea gigante y muy fácil de leer en la pantalla del móvil).\n"
        "3. Todo en MAYÚSCULAS y en ESPAÑOL.\n"
        "4. No dejes oraciones a la mitad ni termines en palabras como 'DE', 'POR', 'QUE', 'EN', 'EL'.\n"
        "5. Cero emojis, cero comillas, cero prefijos como 'EPISODIO' o 'PARTE'.\n"
        "6. Responde ÚNICAMENTE las dos líneas con el '|', nada más."
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 600
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    # Modelos compatibles con la API de Google AI Studio en orden de velocidad y cuota
    modelos = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]

    for mod in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parts = data["candidates"][0]["content"]["parts"]
                text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                cand = (text_parts[-1] if text_parts else parts[-1].get("text", "")).strip()
                cand = cand.replace('"', '').replace("'", '').replace("`", "").strip()
                if "\n" in cand and "|" not in cand:
                    lines = [l.strip() for l in cand.split("\n") if l.strip()]
                    if len(lines) >= 2:
                        cand = f"{lines[0]}|{lines[1]}"
                if "|" in cand:
                    partes = [p.strip().upper() for p in cand.split("|") if p.strip()]
                    if len(partes) >= 2:
                        p1 = " ".join(partes[0].split()[:5])
                        p2 = " ".join(partes[1].split()[:5])
                        # Limpiar palabras colgantes al final
                        p2_words = p2.split()
                        while p2_words and p2_words[-1].lower() in PALABRAS_COLGANTES:
                            p2_words.pop()
                        if p2_words:
                            p2 = " ".join(p2_words)
                        return f"{p1}|{p2}"
        except Exception as e:
            # Si el modelo actual da error, probar con el siguiente
            continue

    return None


def es_hashtag_generico(tag):
    """Detecta si un hashtag es una etiqueta técnica, genérica o de nicho que no debe usarse como título."""
    b = tag.lstrip("#").lower().strip()
    if len(b) < 3 or b in HASHTAGS_GENERICOS:
        return True
    if re.fullmatch(r"(parte|part|cap|capitulo|ep|episodio)\d*", b):
        return True
    for kw in PALABRAS_CLAVE_GENERICAS:
        if kw in b:
            return True
    return False


def limpiar_texto_descripcion(raw_desc):
    """Quita hashtags, @menciones, enlaces, emojis y prefijos de relleno (POV, Episodio, Como cuando, etc.)."""
    t = raw_desc or ""
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"#\w+", "", t)
    t = re.sub(r"(?i)\b(respuesta\s+a|respondiendo\s+a|replying\s+to|responder\s+a)\s+@?[\w.]+", "", t)
    t = re.sub(r"@[\w.]+", "", t)
    t = _EMOJI_RE.sub(" ", t)

    # Quitar prefijos que arruinan el gancho
    t = re.sub(r"^(?:pov|pov:)\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(?:como\s+cuando|cuándo\s+tú|cuando\s+tu|cuando)\s+", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(?:bueno\s+)?(?:chicos|amigos|gente|oigan|hola)\b.*?[,:]\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(?:hoy\s+les\s+(?:traigo|muestro|cuento))\b.*?[,:]?\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(?:en\s+este\s+video|en\s+este\s+clip|miren\s+este\s+video)\b.*?[,:]?\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(?:episodio|capitulo|capítulo|cap|parte|part|p|video)\s*\d+[\s:\-–—|]*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s+", " ", t).strip(" -_.,:;¡!¿?|~")
    return t


def _hashtag_a_palabras(tag):
    tag = tag.lstrip("#")
    tag = tag.replace("_", " ")
    tag = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", tag)
    tag = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", tag)
    return re.sub(r"\s+", " ", tag).strip().upper()


def tema_desde_hashtags(raw_desc):
    for h in re.findall(r"#\w+", raw_desc or ""):
        if es_hashtag_generico(h):
            continue
        palabras = _hashtag_a_palabras(h)
        words = palabras.split()
        if palabras and 1 <= len(words) <= 3 and len(palabras) <= 20:
            return palabras
    return ""


def recortar_hook_inteligente(texto):
    """
    Extrae la mejor frase de impacto sin cortar palabras a medias ni dejar conectores colgantes.
    Retorna el hook formateado en 1 o 2 líneas con '|'.
    """
    t = limpiar_texto_descripcion(texto)
    if not t:
        return "HISTORIA INCREÍBLE|MIRA EL FINAL"

    # 1. Si hay exclamación ¡...! o pregunta ¿...?, tomarla con prioridad
    m_exc = re.search(r"[¡!¿?]([^!?]+)[!?]", t)
    if m_exc and len(m_exc.group(1).split()) >= 3:
        frase = m_exc.group(1).strip()
    else:
        # Dividir por pausas fuertes: puntos, elipsis, guiones, dos puntos, saltos
        partes = re.split(r"[.!?…\n\r–—]|(?:\s*-\s*)", t)
        partes = [p.strip() for p in partes if p.strip()]
        frase = partes[0] if partes else t

    # 2. Si la frase tiene conectores que inician una segunda oración
    m_conn = re.split(r"\b(pero|hasta que|cuando de pronto|y encontraron|y nadie|y descubrió|si yo|si tu|si tú)\b", frase, flags=re.IGNORECASE)
    if m_conn and len(m_conn[0].split()) >= 3:
        frase = m_conn[0].strip()

    # 3. Limpiar signos de puntuación restantes
    frase = re.sub(r'[¡!¿?\"\'“”]', '', frase).strip()

    # 4. Limitar a máximo 7-8 palabras para mantener la idea completa sin mutilarla
    palabras = frase.split()
    if len(palabras) > 8:
        palabras = palabras[:8]

    # 5. Evitar terminar en palabras colgantes
    while palabras and palabras[-1].lower() in PALABRAS_COLGANTES:
        palabras.pop()

    if not palabras or len(palabras) < 2:
        palabras = [w for w in re.sub(r'[¡!¿?\"\'“”]', '', t).split() if w][:6]
        while palabras and palabras[-1].lower() in PALABRAS_COLGANTES:
            palabras.pop()

    # 6. Partir en 2 líneas de forma equilibrada
    texto_final = " ".join(palabras).upper()
    if len(palabras) <= 3 and len(texto_final) <= 22:
        return texto_final

    mejor_corte = 1
    menor_dif = 999
    for i in range(1, len(palabras)):
        l1 = " ".join(palabras[:i])
        l2 = " ".join(palabras[i:])
        dif = abs(len(l1) - len(l2))
        # Penalizar si la primera línea termina en palabra colgante
        if palabras[i - 1].lower() in PALABRAS_COLGANTES:
            dif += 6
        if dif < menor_dif:
            menor_dif = dif
            mejor_corte = i

    linea1 = " ".join(palabras[:mejor_corte]).upper()
    linea2 = " ".join(palabras[mejor_corte:]).upper()
    return f"{linea1}|{linea2}"


def _elegir(lista, semilla):
    h = int(hashlib.md5(str(semilla).encode("utf-8")).hexdigest(), 16)
    return lista[h % len(lista)]


def generar_hook_inteligente(raw_desc, semilla="", api_key=None):
    """
    Devuelve (hook_texto, origen) donde origen es 'gemini_ia', 'descripcion', 'hashtag' o 'gancho'.
    El hook viene listo con '|' para 2 líneas armónicas.
    """
    # 0. Intentar generar gancho viral con Google Gemini si hay API Key
    hook_ai = generar_hook_con_gemini(raw_desc, api_key=api_key)
    if hook_ai:
        return hook_ai, "gemini_ia"

    texto = limpiar_texto_descripcion(raw_desc)
    letras = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{2,}", texto)
    if len(letras) >= 3 or (len(letras) == 2 and len(" ".join(letras)) >= 10):
        return recortar_hook_inteligente(raw_desc), "descripcion"

    tema = tema_desde_hashtags(raw_desc)
    semilla = semilla or raw_desc or "x"
    if tema:
        return _elegir(PLANTILLAS_CON_TEMA, semilla).replace("{X}", tema), "hashtag"

    return _elegir(PLANTILLAS_GENERICAS, semilla), "gancho"


def generar_comentario_con_gemini(raw_desc, hook="", parte_num=1, tiene_partes=False, api_key=None, cuenta_id=""):
    """
    Usa Google Gemini para generar un comentario fijado (pinned comment) interactivo,
    100% RELACIONADO con la historia o mensaje del video, adaptado al nicho de la cuenta
    (ej: reflexiones cristianas/bíblicas si es @bibliareflexiones.a).
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None

    texto = limpiar_texto_descripcion(raw_desc)
    contexto_lineas = []
    if hook:
        contexto_lineas.append(f"Título del video: {hook.replace('|', ' ')}")
    if texto:
        contexto_lineas.append(f"Trama / Descripción: {texto}")

    if not contexto_lineas:
        return None

    contexto_str = "\n".join(contexto_lineas)
    serial_str = f"Es la Parte {parte_num} de una serie continuada." if tiene_partes else "Es una historia COMPLETA autoconclusiva (NO tiene Parte 2)."

    es_biblia = any(k in (cuenta_id or "").lower() for k in ["biblia", "cristian", "dios", "fe", "reflexion", "amen"])

    if es_biblia:
        prompt = (
            "Eres un redactor experto en reflexiones cristianas y mensajes de fe bíblica para Instagram Reels de la cuenta @bibliareflexiones.a.\n"
            f"Datos del video:\n{contexto_str}\n\n"
            "Crea 1 SOLO comentario fijado inspirador y muy participativo para los seguidores de este video.\n"
            "REGLAS CRÍTICAS:\n"
            "1. El comentario DEBE conectar con el mensaje de fe, esperanza, perdón o amor de Dios mostrado en este video específico.\n"
            "2. Invita con calidez a la comunidad a escribir 'Amén' si creen en esta promesa, a reflexionar o a compartir una oración.\n"
            "3. Tono: Cálido, inspirador, respetuoso y lleno de fe (ejemplos: '¿Qué enseñanza deja esta palabra en tu vida hoy? Escribe Amén si confías en los planes de Dios 🙏✨', 'Si esta reflexión tocó tu corazón, deja tu Amén y compártela con alguien que necesite esperanza hoy ❤️📖').\n"
            "4. Longitud máxima: 1 o 2 frases cortas y naturales (máximo 22 palabras).\n"
            "5. Usa emojis de bendición y fe (🙏, ✨, 📖, 🕊️, ❤️, 👇).\n"
            "6. Responde ÚNICAMENTE el texto exacto del comentario en español, sin comillas ni explicaciones."
        )
    else:
        prompt = (
            "Eres un experto en redactar comentarios virales fijados para Instagram Reels de historias animadas.\n"
            f"Datos del video:\n{contexto_str}\n"
            f"Tipo de video: {serial_str}\n\n"
            "Crea 1 SOLO comentario fijado para abrir debate entre los espectadores de este video.\n"
            "REGLAS CRÍTICAS:\n"
            "1. El comentario DEBE referirse DIRECTAMENTE a lo que pasa en este video específico (menciona la situación, el conflicto o los personajes de la historia, NUNCA uses preguntas genéricas de frutas como fresa o manzana si no trata de eso).\n"
            "2. Haz una pregunta picante o moral que obligue a la gente a responder en los comentarios (ej: '¿Crees que hizo lo correcto al ocultarlo?', '¿Qué habrías hecho tú cuando...?').\n"
            "3. Longitud máxima: 1 o 2 frases cortas y naturales (máximo 22 palabras).\n"
            "4. Incluye 1 o 2 emojis naturales (😱, 😳, 🤔, 👇, 🔥, 👀).\n"
            "5. Si tiene partes: invita al final a comentar la parte siguiente (ej: 'Comenta si quieres ver cómo termina 👇').\n"
            "6. Si NO tiene partes: NO inventes 'Parte 2' ni 'continuación'. Pregunta sobre la moraleja o el final.\n"
            "7. Responde ÚNICAMENTE el texto exacto del comentario en español, sin comillas ni explicaciones."
        )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 600
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    modelos = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]

    for mod in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parts = data["candidates"][0]["content"]["parts"]
                text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                cand = (text_parts[-1] if text_parts else parts[-1].get("text", "")).strip()
                cand = cand.replace('"', '').replace("'", '').replace("`", "").strip()
                cand = " ".join(cand.split())
                if len(cand) >= 15:
                    return cand
        except Exception:
            continue

    return None


def generar_copy_reel_con_gemini(raw_desc, hook="", cuenta_id="", hashtags_base=None, api_key=None):
    """
    Genera una descripción (Copy) para Instagram Reels con Google Gemini IA optimizada para SEO y retención.
    Devuelve un texto cautivador de 2-3 líneas con pregunta para debate + hashtags combinados.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    texto = limpiar_texto_descripcion(raw_desc)
    hook_limpio = (hook or "").replace("|", " ").strip()

    # 1. Extraer hashtags dinámicos según el tema
    hashtags_base = list(hashtags_base or ["#reels", "#viral", "#parati"])
    hashtags_encontrados = re.findall(r"#\w+", raw_desc or "")

    # Extraer palabras temáticas de la descripción (ej: frutas o emociones) usando límites de palabra (\b)
    temas_extra = []
    palabras_desc = (texto + " " + hook_limpio).lower()
    for kw in ["fresa", "manzana", "sandia", "aguacate", "platano", "limon", "naranja", "pera", "uva", "capibara", "amor", "traicion", "desamor", "humor", "reflexion", "fe", "dios", "milagro", "familia", "amigos", "secreto"]:
        if re.search(r"\b" + re.escape(kw) + r"\b", palabras_desc):
            temas_extra.append(f"#{kw}")

    # Filtrar hashtags encontrados para no meter etiquetas técnicas o de relleno
    hashtags_limpios = [h for h in hashtags_encontrados if not es_hashtag_generico(h)]
    if not hashtags_limpios:
        hashtags_limpios = [h for h in hashtags_encontrados if len(h) <= 12 and not any(k in h.lower() for k in ["animacion", "3d", "historia"])]

    # Combinar hashtags: 3 fijos de la cuenta + hasta 2 temáticos dinámicos
    tags_finales = []
    for h in hashtags_base[:3] + temas_extra[:2] + hashtags_limpios[:2]:
        if h.lower() not in [x.lower() for x in tags_finales]:
            tags_finales.append(h)
        if len(tags_finales) >= 5:
            break
    tags_str = " ".join(tags_finales)

    # 2. Generar cuerpo con Gemini IA si hay clave
    cuerpo_copy = None
    if key and (hook_limpio or texto):
        es_biblia = any(k in (cuenta_id or "").lower() for k in ["biblia", "cristian", "dios", "fe", "reflexion"])
        contexto = f"Título: {hook_limpio}\nTrama: {texto}"

        if es_biblia:
            prompt = (
                "Eres un redactor experto en Instagram Reels cristianos para @bibliareflexiones.a.\n"
                f"Datos:\n{contexto}\n\n"
                "Escribe una descripción breve (máximo 2 a 3 líneas) inspiradora sobre esta reflexión.\n"
                "REGLAS:\n"
                "1. Conecta con el mensaje de fe o esperanza del video.\n"
                "2. Termina con una pregunta cálida o invitación a dejar su 'Amén' en comentarios.\n"
                "3. Incluye 2 emojis de bendición (🙏, ✨, 📖, ❤️).\n"
                "4. NO pongas hashtags en tu respuesta.\n"
                "5. Responde ÚNICAMENTE el texto en español, sin comillas."
            )
        else:
            prompt = (
                "Eres un redactor experto en Instagram Reels de historias virales y animadas.\n"
                f"Datos:\n{contexto}\n\n"
                "Escribe una descripción corta (máximo 2 a 3 líneas) llena de intriga sobre este video.\n"
                "REGLAS:\n"
                "1. Resume la situación dramática o curiosa sin dar spoilers del final.\n"
                "2. Termina con una pregunta directa para que los espectadores comenten (ej: '¿Qué habrías hecho tú? Te leo en comentarios 👇').\n"
                "3. Incluye 2 emojis naturales (👀, 😱, 🤔, 👇, 🔥).\n"
                "4. NO pongas hashtags en tu respuesta.\n"
                "5. Responde ÚNICAMENTE el texto en español, sin comillas."
            )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
        }
        headers = {"Content-Type": "application/json"}
        modelos = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
        for mod in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    parts = data["candidates"][0]["content"]["parts"]
                    text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                    cand = (text_parts[-1] if text_parts else parts[-1].get("text", "")).strip()
                    cand = cand.replace('"', '').replace("`", "").strip()
                    if len(cand) >= 20:
                        cuerpo_copy = cand
                        break
            except Exception:
                continue

    # 3. Fallback inteligente si Gemini no está o falla
    if not cuerpo_copy:
        t_base = hook_limpio if hook_limpio else (texto or "Una historia impactante")
        if t_base.isupper():
            palabras_t = t_base.lower().split()
            if palabras_t:
                palabras_t[0] = palabras_t[0].capitalize()
                titulo = " ".join(palabras_t).rstrip(".")
            else:
                titulo = "Una historia impactante"
        else:
            titulo = t_base.strip().rstrip(".")

        es_biblia = any(k in (cuenta_id or "").lower() for k in ["biblia", "cristian", "dios", "fe", "reflexion"])
        if es_biblia:
            cuerpo_copy = f"✨ Reflexión: {titulo}.\n\n¿Qué enseñanza deja esta palabra en tu corazón hoy? Déjanos tu Amén en los comentarios 🙏👇"
        else:
            cuerpo_copy = f"🎬 {titulo}.\n\nLas cosas no siempre son lo que parecen... ¿Qué habrías hecho tú en esta situación? Te leo abajo 👇👀"

    return f"{cuerpo_copy}\n\n{tags_str}".strip()

