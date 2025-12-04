from __future__ import annotations

from typing import Optional, Tuple

from langdetect import detect, LangDetectException

LANGUAGE_METADATA = {
    "hr": {
        "tag": "CROATIAN (HR)",
        "greeting": "Bok! 👋 Ja sam tvoj MOBIX asistent. Reci mi trebaš li plan putovanja, savjet ili samo ideje?",
        "small_talk": "Odlično sam, hvala što pitaš! 😊 Ja sam MOBIX, tvoj asistent za putovanja. Kako ti mogu pomoći danas? Trebaš plan puta, savjete za destinaciju ili nešto drugo?",
        "plan_invite": "💡 Želiš li da ti ovo pretvorim u strukturirani plan putovanja koji možeš spremiti u tvoj MOBIX Travel Planner?",
        "keywords": ["bok", "pozdrav", "putova", "želim", "molim", "hrvats", "treba", "rijeka", "zagreb"],
        # Strong Croatian-only markers for short phrases
        "strong_markers": ["tko", "što", "gdje", "koliko", "mogu", "želim", "treba", "hvala", "molim", "kako si", "tko si"],
    },
    "sl": {
        "tag": "SLOVENIAN (SL)",
        "greeting": "Živjo! 👋 Tukaj MOBIX. Naj ti pripravim potovalni nasvet ali načrt?",
        "small_talk": "Super sem, hvala za vprašanje! 😊 Sem MOBIX, tvoj potovalni asistent. Kako ti lahko pomagam danes? Rabiš načrt poti, nasvete za destinacijo ali kaj drugega?",
        "plan_invite": "💡 Želiš, da ti to pretvorim v strukturiran potovalni načrt, ki ga lahko shraniš v svoj MOBIX Travel Planner?",
        "keywords": ["živjo", "potujem", "sloven", "rabim načrt"],
        # Strong Slovenian-only markers for short phrases
        "strong_markers": ["kaj", "kje", "kdaj", "lahko", "potrebujem", "hvala lepa", "prosim", "kako si", "kdo si"],
    },
    "de": {
        "tag": "GERMAN (DE)",
        "greeting": "Hallo! 👋 Ich bin dein MOBIX Reiseassistent. Brauchst du Ideen, Tipps oder einen Reiseplan?",
        "small_talk": "Mir geht's prima, danke der Nachfrage! 😊 Ich bin MOBIX, dein Reiseassistent. Wie kann ich dir heute helfen? Brauchst du einen Reiseplan, Tipps für ein Ziel oder etwas anderes?",
        "plan_invite": "💡 Soll ich dir das in einen strukturierten Reiseplan umwandeln, den du in deinem MOBIX Travel Planner speichern kannst?",
        "keywords": ["hallo", "reise", "brauche", "flug", "günstig"],
    },
    "it": {
        "tag": "ITALIAN (IT)",
        "greeting": "Ciao! 👋 Sono il tuo assistente di viaggio MOBIX. Vuoi idee, consigli o un piano completo?",
        "small_talk": "Sto benissimo, grazie per avermelo chiesto! 😊 Sono MOBIX, il tuo assistente di viaggio. Come posso aiutarti oggi? Hai bisogno di un piano di viaggio, consigli per una destinazione o qualcos'altro?",
        "plan_invite": "💡 Vuoi che trasformi questo in un piano di viaggio strutturato che puoi salvare nel tuo MOBIX Travel Planner?",
        "keywords": ["ciao", "viaggio", "piano", "consiglio", "ital"],
    },
    "es": {
        "tag": "SPANISH (ES)",
        "greeting": "¡Hola! 👋 Soy tu asistente MOBIX. ¿Quieres un plan, un consejo o unas ideas?",
        "small_talk": "¡Estoy genial, gracias por preguntar! 😊 Soy MOBIX, tu asistente de viajes. ¿Cómo puedo ayudarte hoy? ¿Necesitas un plan de viaje, consejos para un destino o algo más?",
        "plan_invite": "💡 ¿Quieres que convierta esto en un plan de viaje estructurado que puedas guardar en tu MOBIX Travel Planner?",
        "keywords": ["hola", "viaje", "plan", "consejo", "espa"],
    },
    "fr": {
        "tag": "FRENCH (FR)",
        "greeting": "Salut! 👋 Ici MOBIX. Tu veux des idées voyage, des conseils ou un plan détaillé?",
        "small_talk": "Je vais très bien, merci de demander! 😊 Je suis MOBIX, ton assistant de voyage. Comment puis-je t'aider aujourd'hui? Tu as besoin d'un plan de voyage, de conseils pour une destination ou autre chose?",
        "plan_invite": "💡 Veux-tu que je transforme cela en un plan de voyage structuré que tu peux enregistrer dans ton MOBIX Travel Planner ?",
        "keywords": ["bonjour", "salut", "voyage", "itineraire", "fran"],
    },
    "uk": {
        "tag": "UKRAINIAN (UK)",
        "greeting": "Привіт! 👋 Я твій асистент MOBIX. Хочеш повний маршрут, пораду чи просто ідеї?",
        "small_talk": "Все чудово, дякую що питаєш! 😊 Я MOBIX, твій асистент для подорожей. Як я можу допомогти тобі сьогодні? Потрібен план подорожі, поради щодо напрямку чи щось інше?",
        "plan_invite": "💡 Хочеш, щоб я перетворив це на структурований маршрут для твого MOBIX Travel Planner?",
        "keywords": ["привіт", "привітання", "маршрут", "подорож"],
    },
    "en": {
        "tag": "ENGLISH (EN)",
        "greeting": "Hi! 👋 I'm your MOBIX assistant. Do you want a travel plan, a tip, or just ideas?",
        "small_talk": "I'm doing great, thanks for asking! 😊 I'm MOBIX, your travel assistant. How can I help you today? Do you need a travel plan, destination tips, or something else?",
        "plan_invite": "💡 Do you want me to turn this into a structured travel plan you can save to your MOBIX Travel Planner?",
        "keywords": ["hello", "hi", "trip", "travel", "plan"],
        # Strong English-only markers for short phrases
        "strong_markers": ["how do", "what's", "who are", "can you", "do you", "i want", "i need", "tell me"],
    },
}

LANGUAGE_ALIASES = {
    "sr": "hr",
    "bs": "hr",
    "me": "hr",
    "pt": "es",
    "pt-br": "es",
    "ua": "uk",
}

SPECIAL_CHAR_HINTS = [
    ("hr", {"č", "ć", "đ"}),
    ("sl", {"ž", "š"}),
]

SUPPORTED_CODES = set(LANGUAGE_METADATA.keys())

GENERIC_LANGUAGE_NAMES = {
    "en": "English",
    "hr": "Croatian",
    "sl": "Slovenian",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "pl": "Polish",
    "nl": "Dutch",
    "sv": "Swedish",
    "fi": "Finnish",
    "da": "Danish",
    "no": "Norwegian",
    "hu": "Hungarian",
    "cs": "Czech",
    "sk": "Slovak",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "sr": "Serbian",
    "bs": "Bosnian",
    "me": "Montenegrin",
    "el": "Greek",
    "ru": "Russian",
    "uk": "Ukrainian",
    "tr": "Turkish",
    "ar": "Arabic",
    "he": "Hebrew",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
}

SCRIPT_HINTS = {
    "ru": [(0x0400, 0x04FF)],
    "uk": [(0x0400, 0x04FF)],
    "bg": [(0x0400, 0x04FF)],
    "el": [(0x0370, 0x03FF)],
    "he": [(0x0590, 0x05FF)],
    "ar": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "hi": [(0x0900, 0x097F)],
    "bn": [(0x0980, 0x09FF)],
    "ta": [(0x0B80, 0x0BFF)],
    "th": [(0x0E00, 0x0E7F)],
    "ko": [(0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF)],
    "ja": [(0x3040, 0x30FF), (0x31F0, 0x31FF)],
    "zh": [(0x4E00, 0x9FFF)],
}


def _normalize_code(raw_code: Optional[str]) -> str:
    if not raw_code:
        return "en"
    code = raw_code.lower()
    code = LANGUAGE_ALIASES.get(code, code)
    if len(code) > 2 and code[:2] in SUPPORTED_CODES:
        code = code[:2]
    return code


def _language_name(code: str) -> str:
    return GENERIC_LANGUAGE_NAMES.get(code, code.upper())


def _metadata(code: str) -> dict:
    normalized = _normalize_code(code)
    if normalized in SUPPORTED_CODES:
        return LANGUAGE_METADATA[normalized]
    fallback = dict(LANGUAGE_METADATA["en"])
    fallback["tag"] = f"{_language_name(normalized).upper()} ({normalized.upper()})"
    return fallback


def _detect_script_language(text: str) -> Optional[str]:
    for ch in text:
        code_point = ord(ch)
        for lang_code, ranges in SCRIPT_HINTS.items():
            for start, end in ranges:
                if start <= code_point <= end:
                    return lang_code
    return None


def detect_language(message: str, preferred_code: Optional[str] = None) -> Tuple[str, str]:
    text = (message or "").strip()
    fallback_code = _normalize_code(preferred_code)
    if not text:
        meta = _metadata(fallback_code)
        return meta["tag"], fallback_code

    lowered = text.lower()
    
    # PRIORITY 0: STRONG ENGLISH DETECTION (most common travel queries)
    # These are common English travel phrases that langdetect often misclassifies
    english_travel_words = (
        "best", "top", "find", "search", "looking", "show", "recommend",
        "must", "see", "visit", "explore", "places", "destinations",
        "hotels", "flights", "restaurants", "things", "activities", "attractions",
        "trip", "travel", "tour", "itinerary", "plan", "guide",
        "from", "to", "in", "at", "for", "the", "a", "an", "of", "and", "or",
        "cheap", "affordable", "luxury", "budget", "expensive", "free",
        "weekend", "week", "day", "days", "night", "morning", "evening",
        "book", "booking", "reserve", "reservation",
        "what", "where", "when", "how", "why", "which", "who",
        "good", "great", "nice", "beautiful", "amazing", "awesome",
        "near", "close", "around", "nearby", "downtown"
    )
    # Count English words
    words = lowered.split()
    english_word_count = sum(1 for word in words if word.strip(".,!?") in english_travel_words)
    # If more than 30% of words are common English travel words, it's English
    if len(words) > 0 and english_word_count / len(words) >= 0.3:
        meta = _metadata("en")
        return meta["tag"], "en"
    
    # PRIORITY 0.5: Detect German, French, Spanish, Italian BEFORE langdetect can misclassify
    german_signals = ("wie", "was", "wer", "ist", "bist", "hast", "kannst", "guten", "tag", "morgen", "abend", "danke", "bitte", "ich", "du", "sie", "schön", "schon", "nach", "von", "für", "auf", "mit")
    french_signals = ("comment", "ça", "ca", "est", "est-ce", "que", "qui", "quoi", "où", "ou", "merci", "bonjour", "bonsoir", "salut", "je", "tu", "nous", "vous", "très", "tres", "bien", "mal", "oui", "non", "avec", "pour", "dans")
    spanish_signals = ("cómo", "como", "qué", "que", "quién", "quien", "dónde", "donde", "gracias", "hola", "buenos", "buenas", "yo", "tú", "tu", "usted", "muy", "bien", "mal", "sí", "si", "no", "con", "para", "en")
    italian_signals = ("come", "cosa", "chi", "dove", "quando", "grazie", "ciao", "buon", "buona", "io", "tu", "lei", "molto", "bene", "male", "sì", "si", "no", "con", "per", "in")
    
    words_set = set(lowered.split())
    german_count = sum(1 for w in words_set if w in german_signals)
    french_count = sum(1 for w in words_set if w in french_signals)
    spanish_count = sum(1 for w in words_set if w in spanish_signals)
    italian_count = sum(1 for w in words_set if w in italian_signals)
    
    # If 2+ words match a language, detect it
    if german_count >= 2:
        meta = _metadata("de")
        return meta["tag"], "de"
    if french_count >= 2:
        meta = _metadata("fr")
        return meta["tag"], "fr"
    if spanish_count >= 2:
        meta = _metadata("es")
        return meta["tag"], "es"
    if italian_count >= 2:
        meta = _metadata("it")
        return meta["tag"], "it"
    
    # Single-word detection for greetings
    german_greetings = {"hallo", "guten", "tag", "morgen", "abend", "servus", "danke"}
    french_greetings = {"bonjour", "bonsoir", "salut", "merci"}
    spanish_greetings = {"hola", "gracias", "buenos", "buenas"}
    italian_greetings = {"ciao", "buongiorno", "buonasera", "grazie", "salve"}
    
    if words_set & german_greetings:
        meta = _metadata("de")
        return meta["tag"], "de"
    if words_set & french_greetings:
        meta = _metadata("fr")
        return meta["tag"], "fr"
    if words_set & spanish_greetings:
        meta = _metadata("es")
        return meta["tag"], "es"
    if words_set & italian_greetings:
        meta = _metadata("it")
        return meta["tag"], "it"
    
    # PRIORITY 1: Check strong markers FIRST (for short phrases like "Kako si?", "Tko si ti?")
    for code, data in LANGUAGE_METADATA.items():
        strong_markers = data.get("strong_markers", [])
        for marker in strong_markers:
            if marker in lowered:
                meta = _metadata(code)
                return meta["tag"], code
    
    # PRIORITY 2: English-specific hints (phrases)
    english_hints = (
        "please", "travel plan", "make a travel", "itinerary", "trip from", "plan from",
        "best hotels", "find flights", "things to do", "what to do", "where to",
        "how to get", "i want to", "i need", "can you", "could you", "help me",
        "looking for", "searching for", "recommend", "suggestion"
    )
    if any(hint in lowered for hint in english_hints):
        meta = _metadata("en")
        return meta["tag"], "en"

    # PRIORITY 3: Croatian-specific detection (NOT Slovenian)
    croatian_hints = (
        "hvala ti", "hvala vam", "molim te", "molim vas", "dobar dan",
        "dobro jutro", "treba mi", "želim", "htio bih", "možda", "odmor",
        "što", "gdje", "kada", "koliko dugo", "za vikend", "izlet", "putovanje",
        "savjete", "preporuku", "prijedlog", "pitanje", "informacije",
        "napravi", "planiram", "idem", "trebam", "možeš", "hoću",
        "planiraj", "napravi mi", "od", "do", "iz", "u", "mi put"
    )
    if any(hint in lowered for hint in croatian_hints):
        meta = _metadata("hr")
        return meta["tag"], "hr"
    
    # PRIORITY 4: Slovenian-specific detection (NOT Croatian)
    slovenian_hints = (
        "potrebujem", "načrt", "prosim", "hvala lepa", "dober dan", 
        "dobro jutro", "lahko", "želim", "bi rad", "mogoče", "počitnice",
        "kaj", "kje", "kdaj", "kako dolgo", "za vikend", "izlet", "popotovanje",
        "nasvete", "priporočilo", "namig", "vprašanje", "informacije"
    )
    if any(hint in lowered for hint in slovenian_hints):
        meta = _metadata("sl")
        return meta["tag"], "sl"

    for code, data in LANGUAGE_METADATA.items():
        for keyword in data.get("keywords", []):
            if keyword and keyword in lowered:
                meta = _metadata(code)
                return meta["tag"], code

    for code, chars in SPECIAL_CHAR_HINTS:
        if any(char in lowered for char in chars):
            meta = _metadata(code)
            return meta["tag"], code

    script_code = _detect_script_language(text)
    if script_code:
        meta = _metadata(script_code)
        return meta["tag"], _normalize_code(script_code)

    if len(text) < 6 and fallback_code:
        meta = _metadata(fallback_code)
        return meta["tag"], fallback_code

    try:
        detected = detect(text)
    except LangDetectException:
        detected = fallback_code or "en"

    normalized = _normalize_code(detected or fallback_code)
    meta = _metadata(normalized)
    if preferred_code and normalized not in {preferred_code, fallback_code}:
        return meta["tag"], normalized
    return meta["tag"], normalized


def get_greeting_text(language_code: str) -> str:
    meta = _metadata(_normalize_code(language_code))
    return meta["greeting"]


def get_small_talk_text(language_code: str) -> str:
    """Get small talk response for the given language (e.g., reply to 'how are you')."""
    meta = _metadata(_normalize_code(language_code))
    return meta.get("small_talk", meta["greeting"])


def get_plan_invite(language_code: str) -> str:
    meta = _metadata(_normalize_code(language_code))
    return meta["plan_invite"]


__all__ = [
    "detect_language",
    "get_greeting_text",
    "get_small_talk_text",
    "get_plan_invite",
    "LANGUAGE_METADATA",
]
