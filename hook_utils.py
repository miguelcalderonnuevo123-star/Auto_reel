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
    "minidrama", "leccion", "lección", "shorts", "paratiiiiiiiiiii"
}

PALABRAS_COLGANTES = {
    "por", "de", "para", "en", "con", "que", "a", "y", "o", "un", "una", "unos", "unas",
    "el", "la", "los", "las", "del", "al", "su", "sus", "como", "pero", "sin", "se",
    "era", "es", "fue", "eran", "cuando", "donde", "si", "porque", "le", "lo", "me", "te", "nos",
    "yo", "tú", "tu", "él", "ella", "ellos", "ellas", "mi", "mis", "ti"
}

PLANTILLAS_CON_TEMA = [
    "{X}|NADIE ESPERABA ESTE FINAL",
    "LA HISTORIA DE|{X}",
    "{X}|ESTO SE PUSO SERIO",
    "LO QUE LE PASÓ A|{X}",
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
    "ESPERA EL FINAL|NO TE LO PIERDAS",
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
            "maxOutputTokens": 35
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key
    }

    # Modelos compatibles con la nueva API de Google AI Studio en orden de velocidad y cuota
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

    for mod in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand = data["candidates"][0]["content"]["parts"][0]["text"].strip()
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


def limpiar_texto_descripcion(raw_desc):
    """Quita hashtags, @menciones, enlaces, emojis y prefijos como 'Episodio 1:', 'Parte 2:'."""
    t = raw_desc or ""
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"#\w+", "", t)
    t = re.sub(r"(?i)\b(respuesta\s+a|respondiendo\s+a|replying\s+to|responder\s+a)\s+@?[\w.]+", "", t)
    t = re.sub(r"@[\w.]+", "", t)
    t = _EMOJI_RE.sub(" ", t)
    # Quitar prefijos que no aportan valor al gancho
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
        base = h.lstrip("#").lower()
        if base in HASHTAGS_GENERICOS or len(base) < 4:
            continue
        if re.fullmatch(r"(parte|part)\d*", base):
            continue
        palabras = _hashtag_a_palabras(h)
        if palabras and len(palabras) <= 24:
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

    # 1. Si hay exclamación ¡...!, tomarla con prioridad
    m_exc = re.search(r"[¡!]([^!]+)[!]", t)
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

    # 4. Limitar a máximo 6 palabras con significado
    palabras = frase.split()
    if len(palabras) > 6:
        palabras = palabras[:6]

    # 5. Evitar terminar en palabras colgantes (preposiciones, conjunciones, pronombres sueltos)
    while palabras and palabras[-1].lower() in PALABRAS_COLGANTES:
        palabras.pop()

    if not palabras or len(palabras) < 2:
        palabras = [w for w in re.sub(r'[¡!¿?\"\'“”]', '', t).split() if w][:5]
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
    if len(letras) >= 2 or (len(letras) == 1 and len(letras[0]) >= 5):
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
            "maxOutputTokens": 60
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key
    }

    modelos = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

    for mod in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                cand = cand.replace('"', '').replace("'", '').replace("`", "").strip()
                cand = " ".join(cand.split())
                if len(cand) >= 15:
                    return cand
        except Exception:
            continue

    return None

