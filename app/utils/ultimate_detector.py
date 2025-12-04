from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from langdetect import detect, LangDetectException

try:
    from fuzzy_city_matcher import smart_normalize_city
except ImportError:  # pragma: no cover
    def smart_normalize_city(value: str) -> str:  # type: ignore
        return (value or "").strip().title()


LANGUAGE_OVERRIDES = {"sr": "hr", "bs": "hr", "me": "hr"}

ROUTE_PATTERNS = (
    re.compile(r"\bod\s+(?P<origin>.+?)\s+do\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\biz\s+(?P<origin>.+?)\s+v\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\bfrom\s+(?P<origin>.+?)\s+to\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\biz\s+(?P<origin>.+?)\s+(?:u|za|prema|do)\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    # NEW: Reverse order pattern "u/za/to DESTINATION iz/from ORIGIN"
    # Handles: "put u Barcelona iz Milana", "trip to Paris from London"
    re.compile(r"\b(?:u|za|to)\s+(?P<destination>.+?)\s+(?:iz|from)\s+(?P<origin>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\bde\s+(?P<origin>.+?)\s+(?:a|hasta|vers)\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\bvon\s+(?P<origin>.+?)\s+nach\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    re.compile(r"\bda\s+(?P<origin>.+?)\s+(?:a|per)\s+(?P<destination>.+?)(?=[,.!?]|$)", re.IGNORECASE),
    # NEW: Match "CITY do/to CITY" without prefix (e.g., "Omišalj do Atene")
    re.compile(r"\b(?P<origin>[A-ZČĆŠĐŽ][a-zčćšđž]+(?:\s+[A-ZČĆŠĐŽ][a-zčćšđž]+)?)\s+(?:do|to)\s+(?P<destination>[A-ZČĆŠĐŽ][a-zčćšđž]+(?:\s+[A-ZČĆŠĐŽ][a-zčćšđž]+)?)", re.IGNORECASE),
)

ARROW_PATTERN = re.compile(r"(?P<origin>[\w\s]+?)\s*(?:-+|->|→)\s*(?P<destination>[\w\s]+?)")
CAPITAL_PAIR_PATTERN = re.compile(r"\b([A-Z][\w']+(?:\s+[A-Z][\w']+)?)\s+([A-Z][\w']+(?:\s+[A-Z][\w']+)?)\b")

DATE_ISO_PATTERN = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
DATE_EU_PATTERN = re.compile(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?")

CUT_MARKER_PATTERN = re.compile(r"\b(?:od|do|from|until|till|hasta|pour|per)\b", re.IGNORECASE)

# BLACKLIST: Common words that are NOT cities (prevent false positives)
CITY_BLACKLIST = {
    # English common words
    "do", "for", "me", "you", "us", "we", "they", "can", "what", "how", "when", "where",
    "help", "the", "and", "but", "with", "from", "this", "that", "have", "has", "had",
    "will", "would", "could", "should", "may", "might", "must", "need", "want", "get",
    "make", "know", "think", "take", "see", "come", "use", "find", "give", "tell",
    "inside", "outside", "within", "country", "somewhere", "anywhere", "everywhere",
    "weekend", "getaway", "looking", "live", "my", "your", "our", "their",
    # Time-related words
    "today", "tomorrow", "yesterday", "next", "last", "week", "month", "year",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "danas", "sutra", "jučer", "jucer", "sljedeći", "sljedeci", "prošli", "prosli",
    "tjedan", "mjesec", "godina", "ponedjeljak", "utorak", "srijeda", "četvrtak", "petak", "subota", "nedjelja",
    # Croatian/Slovenian common words
    "sta", "što", "kako", "kada", "gdje", "tko", "ko", "zašto", "zasto",
    "može", "moze", "mogu", "treba", "trebam", "hoću", "hoce", "želim", "zelim",
    "idem", "ići", "ici", "otići", "otic", "putovati", "putovanje",
    "unutar", "države", "država", "negdje", "negdi", "vikend", "živim", "zivim",
    # Travel-related but not cities
    "flight", "hotel", "bus", "train", "car", "plane", "trip", "travel", "journey",
    "let", "auto", "autobus", "vlak", "smještaj", "smjestaj",
    # COUNTRIES (not valid as specific origins/destinations for route planning)
    "croatia", "hrvatska", "slovenia", "slovenija", "germany", "njemačka", "njemacka",
    "italy", "italija", "austria", "austrija", "hungary", "mađarska", "madjarska",
    "france", "francuska", "spain", "španjolska", "spanjolska", "portugal",
    "greece", "grčka", "grcka", "serbia", "srbija", "bosnia", "bosna",
    "montenegro", "crna gora", "albania", "albanija", "romania", "rumunjska",
    "bulgaria", "bugarska", "czech", "češka", "ceska", "poland", "poljska",
    "netherlands", "nizozemska", "belgium", "belgija", "switzerland", "švicarska", "svicarska",
    "uk", "united kingdom", "england", "engleska", "scotland", "škotska", "skotska",
    "ireland", "irska", "usa", "united states", "america", "amerika",
}


def _detect_language_code(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "en"
    try:
        detected = detect(text)
    except LangDetectException:
        detected = "en"
    code = (detected or "en").lower()
    return LANGUAGE_OVERRIDES.get(code, code)


def _trim_segment(segment: str) -> str:
    parts = CUT_MARKER_PATTERN.split(segment, maxsplit=1)
    return parts[0].strip(" ,.") if parts else segment.strip(" ,.")


def _normalize_city(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = _trim_segment(raw)
    # Extra spaces cleanup
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if not cleaned:
        return None
    # CRITICAL: Reject if it looks like a date (e.g., "30.1", "5.2", "12-05")
    if re.match(r'^\d{1,2}[./-]\d{1,2}$', cleaned.strip()):
        return None
    # Also reject if it's ONLY digits (e.g., "5", "30")
    if re.match(r'^\d+$', cleaned.strip()):
        return None
    # CRITICAL: Remove blacklisted words from the end (e.g., "Madrid Sljedeći Tjedan" → "Madrid")
    words = cleaned.split()
    while words and words[-1].lower() in CITY_BLACKLIST:
        words.pop()
    if not words:
        return None
    cleaned = " ".join(words)
    # BLACKLIST: Reject common words that are NOT cities
    cleaned_lower = cleaned.lower().strip()
    if cleaned_lower in CITY_BLACKLIST:
        return None
    # Also check multi-word phrases (e.g., "Do For Me" → check each word)
    if all(word.lower() in CITY_BLACKLIST for word in words):
        return None
    normalized = smart_normalize_city(cleaned)
    return normalized.title() if normalized else cleaned.title()


def _extract_route(message: str) -> Tuple[Optional[str], Optional[str]]:
    # STEP 1: Remove parentheses with island/region names FIRST
    # Example: "Omišalj (Otok Krk) do Atene" → "Omišalj do Atene"
    cleaned_message = re.sub(r'\s*\([^)]+\)', ' ', message)
    
    # STEP 2: Remove date patterns to avoid matching them as cities
    # Pattern: "od 30.1 do 5.2", "30.1-5.2", "30.1 - 3.2", etc.
    cleaned_message = re.sub(r'\b(?:od|from)?\s*\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\s*(?:-|do|to|till|until)?\s*\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\s*(?:godine|year)?\b', ' ', cleaned_message, flags=re.IGNORECASE)
    
    # STEP 2.5: Clean up multiple spaces left by removals
    cleaned_message = re.sub(r'\s+', ' ', cleaned_message).strip()
    
    # STEP 3: Extract origin and destination
    for pattern in ROUTE_PATTERNS:
        match = pattern.search(cleaned_message)
        if match:
            origin_raw = match.group("origin").strip()
            dest_raw = match.group("destination").strip()
            # CRITICAL: Skip if matched strings look like dates (e.g., "30.1", "5.2", "30", "5")
            # Check for: starts with digit AND (has dot/slash OR is pure number OR is short number)
            is_date_origin = bool(re.match(r'^\d', origin_raw)) and (
                '.' in origin_raw or '/' in origin_raw or '-' in origin_raw or len(origin_raw) <= 2
            )
            is_date_dest = bool(re.match(r'^\d', dest_raw)) and (
                '.' in dest_raw or '/' in dest_raw or '-' in dest_raw or len(dest_raw) <= 2
            )
            if is_date_origin or is_date_dest:
                continue  # Skip this match, try next pattern
            origin = _normalize_city(origin_raw)
            destination = _normalize_city(dest_raw)
            if origin or destination:
                return origin, destination
    arrow_match = ARROW_PATTERN.search(cleaned_message)
    if arrow_match:
        origin_raw = arrow_match.group("origin").strip()
        dest_raw = arrow_match.group("destination").strip()
        # CRITICAL: Skip if looks like dates
        is_date_origin = bool(re.match(r'^\d', origin_raw)) and (
            '.' in origin_raw or '/' in origin_raw or '-' in origin_raw or len(origin_raw) <= 2
        )
        is_date_dest = bool(re.match(r'^\d', dest_raw)) and (
            '.' in dest_raw or '/' in dest_raw or '-' in dest_raw or len(dest_raw) <= 2
        )
        if not is_date_origin and not is_date_dest:
            origin = _normalize_city(origin_raw)
            destination = _normalize_city(dest_raw)
            return origin, destination
    simple_pair = CAPITAL_PAIR_PATTERN.search(cleaned_message)
    if simple_pair:
        origin_raw = simple_pair.group(1).strip()
        dest_raw = simple_pair.group(2).strip()
        # CRITICAL: Skip if looks like dates
        is_date_origin = bool(re.match(r'^\d', origin_raw)) and (
            '.' in origin_raw or '/' in origin_raw or '-' in origin_raw or len(origin_raw) <= 2
        )
        is_date_dest = bool(re.match(r'^\d', dest_raw)) and (
            '.' in dest_raw or '/' in dest_raw or '-' in dest_raw or len(dest_raw) <= 2
        )
        if not is_date_origin and not is_date_dest:
            origin = _normalize_city(origin_raw)
            destination = _normalize_city(dest_raw)
            if origin == destination:
                destination = None
            return origin, destination
    return None, None


def _safe_iso(year: int, month: int, day: int) -> Optional[str]:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _parse_dates(message: str) -> Dict[str, Optional[str]]:
    ordered: list[str] = []
    for year, month, day in DATE_ISO_PATTERN.findall(message):
        iso_candidate = _safe_iso(int(year), int(month), int(day))
        if iso_candidate and iso_candidate not in ordered:
            ordered.append(iso_candidate)
    
    today = datetime.utcnow().date()
    current_year = today.year
    
    for day, month, raw_year in DATE_EU_PATTERN.findall(message):
        numeric_year = int(raw_year) if raw_year else current_year
        if numeric_year < 100:
            numeric_year += 2000
        iso_candidate = _safe_iso(numeric_year, int(month), int(day))
        
        # SMART FIX: If date is in the past, assume user means next year
        if iso_candidate:
            candidate_date = datetime.fromisoformat(iso_candidate).date()
            if candidate_date < today:
                # Try next year
                iso_candidate = _safe_iso(numeric_year + 1, int(month), int(day))
        
        if iso_candidate and iso_candidate not in ordered:
            ordered.append(iso_candidate)
    
    departure = ordered[0] if ordered else None
    return_date = ordered[1] if len(ordered) > 1 else None
    return {"departure": departure, "return": return_date}


def _trip_type(dates: Dict[str, Optional[str]]) -> str:
    if dates.get("departure") and dates.get("return"):
        return "round_trip"
    if dates.get("departure") and not dates.get("return"):
        return "one_way"
    return "unknown"


BUDGET_PATTERN = re.compile(r"(\d+)\s*(?:eur[oa]?s?|\u20ac|\$|dollars?|kuna?|kn)", re.IGNORECASE)


def _parse_budget(message: str) -> Optional[int]:
    """Extract budget from message (e.g., '2000 eura', '€500', '$1000')"""
    match = BUDGET_PATTERN.search(message)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def _looks_like_travel(message: str, origin: Optional[str], destination: Optional[str], dates: Dict[str, Optional[str]]) -> bool:
    if origin or destination:
        return True
    if dates.get("departure") or dates.get("return"):
        return True
    return bool(ARROW_PATTERN.search(message))


def is_travel_query_smart(message: str) -> Dict[str, Any]:
    text = message or ""
    language = _detect_language_code(text)
    origin, destination = _extract_route(text)
    dates = _parse_dates(text)
    budget = _parse_budget(text)
    detection = {
        "language": language,
        "language_code": language,
        "origin": origin,
        "destination": destination,
        "origin_country": None,
        "destination_country": None,
        "dates": dates,
        "budget": budget,
        "trip_type": _trip_type(dates),
        "is_travel": _looks_like_travel(text, origin, destination, dates),
    }
    print(
        "[ultimate_detect] language={language} origin={origin} destination={destination} trip_type={trip_type} budget={budget}".format(
            **{k: detection.get(k) for k in ("language", "origin", "destination", "trip_type", "budget")}
        )
    )
    return detection


def ultimate_detect(message: str) -> Dict[str, Any]:
    return is_travel_query_smart(message)
