from typing import Any, Dict, List, Optional

try:
    from .ultimate_detector import ultimate_detect
except ImportError:  # pragma: no cover
    ultimate_detect = None  # type: ignore

try:
    from travel_planner import detect_travel_request as planner_detect
except ImportError:  # pragma: no cover
    planner_detect = None  # type: ignore

from .openai_client import OpenAIClient

GREETING_PHRASES = {
    # Croatian - ONLY pure greetings
    "pozdrav", "bok", "cao", "ćao", "hej", "zdravo", "dobar dan", "dobro jutro", "dobra večer",
    # Slovenian
    "živjo", "zivjo", "dober dan", "dobro jutro",
    # English - ONLY pure greetings
    "hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening",
    # Spanish
    "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
    # Italian
    "ciao", "buongiorno", "buonasera", "salve",
    # German
    "hallo", "guten tag", "guten morgen", "guten abend", "servus", "grüß gott", "gruss gott",
    # French
    "bonjour", "salut", "bonsoir",
    # Ukrainian
    "привіт", "привітання", "вітаю", "доброго дня", "добрий день",
}

# REMOVED SMALL_TALK_PHRASES - these should go to GPT for natural responses
# Questions like "how are you", "who are you", "thanks" need intelligent responses

TRAVEL_KEYWORDS = {
    "putovanje",
    "put",
    "putuj",
    "plan putovanja",
    "planiraj",
    "isplaniraj",
    "napravi plan",
    "napravit plan",
    "ruta",
    "rutu",
    "itinerar",
    "trip",
    "travel",
    "let",
    "hotel",
    "ski",
    "skij",
    "destin",
    "savjet",
    "advice",
    "recommend",
    "podoroz",
    "подорож",
    "маршрут",
    "treba mi",
    "trebam",
    "ne znam",
    "negdje",
    "negdi",
}

# Keywords that indicate user is asking for ADVICE (where to go)
ADVICE_KEYWORDS = {
    # Croatian
    "preporuč", "preporuci", "preporuka", "preporuke",
    "savjet", "savjeti", "savjetuj",
    "daj ideju", "daj mi ideju", "imam ideju", "ideju",
    "daj mi", "možeš li mi dati", "mozes li mi dati",  # "daj mi golf terene"
    "kamo", "kamo da", "kuda", "gdje", "di",
    "što preporučuješ", "sta preporucujes",
    "negdje", "negdi", "neki grad", "neku destinaciju",
    "ne znam gdje", "ne znam kamo", "neznam gdje",
    "treba mi", "trebam", "želim otić", "zelim otic",
    "mozes li mi napravit", "možeš li mi napraviti",
    "vikend", "weekend", "vikend izlet", "weekend getaway",
    "unutar države", "unutar hrvatske", "u hrvatskoj", "po hrvatskoj",
    "inside my country", "in my country", "within croatia",
    "looking for", "tražim", "trazim", "iščem", "iscem",
    # Generic location requests (where there's no specific city)
    "toplijim krajevima", "hladnijim krajevima", "warm places", "cold places",
    "warm countries", "cold countries", "toplije zemlje", "hladnije zemlje",
    "u toplijim", "u hladnijim", "in warmer", "in colder",
    "topla mjesta", "hladna mjesta", "topla europa", "warm europe",
    "u europi", "in europe", "po europi", "across europe",
    "u prosincu", "u siječnju", "u veljači", "in december", "in january", "in february",
    "tijekom zime", "during winter", "this winter", "ove zime",
    # English  
    "recommend", "recommendation", "suggest", "suggestion",
    "advice", "where should", "where to", "where can",
    "give me idea", "any idea", "ideas",
    "give me some", "show me some",  # "give me some golf courses"
    "somewhere", "any place", "which city", "which destination",
    "don't know where", "need help", "help me plan",
    "can you make", "could you create",
    "weekend trip", "getaway", "short trip", "day trip",
    "nearby", "close by", "around", "near me",
    # Slovenian
    "priporodi", "priporočilo", "kam", "kje",
    "vikend izlet", "v sloveniji", "po sloveniji",
}

# Keywords for questions about user profile
PROFILE_QUESTION_KEYWORDS = {
    # Croatian
    "što znaš", "sta znas", "znaš li", "znas li",
    "što imaš", "sta imas", "imaš li", "imas li",
    "o meni", "za mene", "moj profil", "moje informacije",
    "tko sam", "ko sam", "što ti je poznato", "sta ti je poznato",
    "kakav sam", "kakva sam", "moji podaci",
    # English
    "what do you know", "what you know", "do you know",
    "about me", "my profile", "my information", "my data",
    "who am i", "what is known", "tell me about myself",
    # Slovenian
    "kaj veš", "o meni", "moj profil",
}

# Keywords for general questions (not requiring travel plan)
GENERAL_QUESTION_KEYWORDS = {
    # Croatian
    "koliko", "kolko", "cijena", "cena", "košta", "kosta",
    "koliko stoji", "koliko vrijedi", "koliko traje",
    "kada", "kad", "koliko dugo", "u koliko sati",
    "što je", "sta je", "kako", "zašto", "zasto",
    "može li", "moze li", "da li", "dal",
    "vrijeme", "vreme", "temperatura", "klima",
    "viza", "dokument", "pasoš", "pasos",
    "trebam li vizu", "trebam vizu", "treba mi viza",
    "što možeš", "sta mozes", "što umiješ", "sta umjes",
    "što možeš napraviti", "sta mozes napravit",
    "kako mi možeš", "kako mi mozes", "pomoć", "pomoc",
    # English
    "how much", "what is the price", "cost", "costs",
    "when", "how long", "what time",
    "what is", "how", "why", "can i", "is it",
    "weather", "temperature", "climate",
    "visa", "passport", "document",
    "do i need a visa", "need a visa", "visa requirements",
    "what can you", "what do you", "what are you",
    "can you do", "what can you do", "how can you help",
    "help me", "what features", "what capabilities",
    "tell me what", "explain what",
}

# Keywords for SPECIFIC_SEARCH (searching for specific category in a city)
SPECIFIC_SEARCH_KEYWORDS = {
    # Croatian
    "restorani", "restoran", "restorane",
    "hoteli", "hotel", "hotele", "smještaj", "smjestaj",
    "kafići", "kafici", "kafić", "kafic", "kavane", "kavana",
    "klubovi", "klub", "klubove", "noćni život", "nocni zivot", "izlazak", "izlazaka",
    "atrakcije", "atrakcija", "znamenitosti", "znamenitost",
    "aktivnosti", "aktivnost", "što raditi", "sta raditi", "što vidjeti", "sta vidjeti",
    "barovi", "bar", "barove",
    "plaže", "plaza", "plaze",
    "muzeji", "muzej", "muzeje",
    "parkovi", "park", "parkove",
    "pokaži", "pokazi", "prikaži", "prikazi",
    "mjesta", "mjesto", "lokacije", "lokacija",
    # English
    "restaurants", "restaurant",
    "hotels", "hotel", "accommodation", "accommodations",
    "cafes", "cafe", "coffee shops",
    "clubs", "club", "nightlife", "nightclubs", "bars", "bar",
    "attractions", "attraction", "sights", "sightseeing",
    "activities", "activity", "things to do", "what to do",
    "beaches", "beach",
    "museums", "museum",
    "parks", "park",
    "show me", "find me", "list", "best", "top",
    # Must see / places patterns
    "must see", "must-see", "must visit", "must-visit",
    "places to visit", "places to see", "places in",
    "landmarks", "landmark", "tourist spots", "tourist attractions",
    "points of interest", "poi",
    "destinations", "destination",
    "popular places", "famous places", "iconic places",
    # What to see/do patterns
    "what to see", "what to visit", "what to explore",
    "where to go", "where to visit",
    "worth seeing", "worth visiting",
    "to see in", "to visit in", "to explore in",
    "see in", "visit in", "explore in",
    # Slovenian
    "restavracije", "restavracija",
    "hoteli", "hotel", "nastanitev",
    "kavarne", "kavarna",
    "klubi", "klub", "nočno življenje",
}

# City location patterns for SPECIFIC_SEARCH
# IMPORTANT: These patterns should extract PROPER NOUNS (capitalized city names)
CITY_LOCATION_PATTERNS = [
    r'\bu\s+([A-ZČĆŠĐŽ][a-zčćšđžA-ZČĆŠĐŽ]*)',  # "u Zagrebu", "u Opatiji" - must start with capital
    r'\bin\s+([A-Z][a-zA-Z]*)',  # "in Paris" - must start with capital
    r'\bv\s+([A-ZČĆŠĐŽ][a-zčćšđžA-ZČĆŠĐŽ]*)',  # "v Ljubljani" (Slovenian) - must start with capital
]

# Words that look like cities but are NOT (common words that might follow "u", "in", etc.)
NOT_CITY_WORDS = {
    # Croatian common words that might match city patterns
    "nekim", "svim", "toplijim", "hladnijim", "bližim", "daljim", "većim", "manjim",
    "lipšim", "ljepšim", "boljem", "bolji", "gorem", "gorim", "svakom", "nekom",
    "nekoj", "svakoj", "mojoj", "tvojoj", "njegovoj", "njezinom", "našem", "vašem",
    "jednom", "drugom", "trećem", "prvom", "zadnjem", "prošlom", "sljedećem",
    "ovom", "tom", "onom", "kojem", "čemu", "čime", "kome", "kom",
    "topim", "toplim", "hladnim", "lijepim", "lepim",
    # English common words
    "some", "any", "warm", "warmer", "cold", "colder", "close", "closer", "far",
    "bigger", "smaller", "better", "best", "nicer", "most", "every", "each",
    "this", "that", "these", "those", "other", "another", "certain", "various",
    "general", "particular", "specific", "different", "similar", "nearby", "remote",
    "december", "january", "february", "winter", "summer", "spring", "autumn",
    "prosinca", "siječnja", "veljače", "zimi", "ljeti", "proljeće", "jesen",
    # Generic location words (not specific cities)
    "country", "region", "area", "place", "places", "location", "destination",
    "krajevima", "mjestima", "zemljama", "regijama", "područjima", "destinacijama",
    # Generic regions/continents (NOT specific cities)
    "europe", "europa", "europi", "asia", "azija", "aziji", "africa", "afrika", "africi",
    "america", "amerika", "americi", "australia", "australija", "australiji",
    "mediterranean", "mediteran", "mediteranu", "balkans", "balkan", "balkanu",
    "scandinavia", "skandinavija", "skandinaviji", "caribbean", "karibe", "karibima",
    "world", "svijet", "svijetu", "global", "worldwide",
}

PLAN_TRIGGER_SUBSTRINGS = (
    "plan",
    "planiram",
    "planning",
    "putovan",
    "putovanje",
    "trip",
    "travel from",
    "traveling from",
    "travelling from",
    "itinerar",
    "itinerary",
    "ruta",
    "route",
    "want to go from",
    "want to travel",
    "going from",
    "маршрут",
)

ROUTE_HINT_TOKENS = (
    " from ",
    " iz ",
    " za ",
    " u ",
    " to ",
    " prema ",
    " -> ",
    "→",
)


def is_greeting(message: str) -> bool:
    """
    Check if message is a PURE greeting (hello, bok, hola, etc.).
    
    IMPORTANT: This should ONLY match simple greetings, NOT:
    - Questions (how are you, who are you, what can you do)
    - Thanks (hvala, thanks, gracias)
    - Goodbyes (bye, doviđenja)
    
    Those should go to GPT for natural, intelligent responses.
    """
    text = (message or "").strip().lower()
    # Remove common punctuation
    text = text.rstrip("!?.,:;")
    
    # Check exact match for pure greetings
    if text in GREETING_PHRASES:
        return True
    
    # Check if message is ONLY a greeting word (no other words)
    # This catches variations like "Hello!" or "Bok!!!"
    words = text.split()
    if len(words) == 1:
        word = words[0].rstrip("!?.,:;")
        if word in GREETING_PHRASES:
            return True
    
    # Check multi-word greetings like "guten tag", "buenos dias", "dobar dan"
    if len(words) == 2:
        phrase = " ".join(words)
        if phrase in GREETING_PHRASES:
            return True
        # Also check without punctuation
        phrase_clean = words[0].rstrip("!?.,:;") + " " + words[1].rstrip("!?.,:;")
        if phrase_clean in GREETING_PHRASES:
            return True
    
    # IMPORTANT: If message starts with greeting BUT contains more content, let GPT handle it
    # Example: "Pozdrav treba mi plan putovanja..." → NOT a greeting (it's a travel request)
    # Example: "Hello, how are you?" → NOT a pure greeting (needs GPT response)
    if len(words) > 2:
        first_word = words[0].rstrip("!?.,:;")
        if first_word in GREETING_PHRASES:
            # This is a greeting + something else - let GPT handle it naturally
            return False
    
    return False


def message_contains_travel_keywords(message: str) -> bool:
    text = (message or "").lower()
    return any(keyword in text for keyword in TRAVEL_KEYWORDS)


def is_asking_for_advice(message: str) -> bool:
    """Check if user is asking WHERE to go (advice) vs HOW to get from A to B (plan)."""
    text = (message or "").lower()
    return any(keyword in text for keyword in ADVICE_KEYWORDS)


def is_profile_question(message: str) -> bool:
    """Check if user is asking about their own profile/info."""
    text = (message or "").lower()
    return any(keyword in text for keyword in PROFILE_QUESTION_KEYWORDS)


def is_general_question(message: str) -> bool:
    """Check if user is asking general question (not requiring travel plan)."""
    import re
    text = (message or "").lower()
    # Check for profile questions first
    if is_profile_question(text):
        return True
    # Check for capabilities/help questions
    capabilities_phrases = [
        "what can you do", "what do you do", "what are you",
        "can you help", "how can you help", "help me",
        "što možeš", "sta mozes", "što umiješ", "kako mi možeš",
        "možeš li mi pomoći", "mozes li mi pomoci",
    ]
    for phrase in capabilities_phrases:
        if phrase in text:
            return True
    # Check for general question keywords with word boundary for short words
    # This prevents "show" from matching "how"
    for keyword in GENERAL_QUESTION_KEYWORDS:
        if len(keyword) <= 4:
            # Use word boundary for short keywords
            if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                return True
        else:
            # Longer phrases can use simple substring match
            if keyword in text:
                return True
    return False


def is_specific_search(message: str) -> bool:
    """Check if user is searching for specific category (restaurants, hotels, etc.) in a SPECIFIC city.
    
    IMPORTANT: This should return True ONLY when user asks about a SPECIFIC city.
    "restaurants in Paris" → True (specific city)
    "golf courses in warm places" → False (not a specific city)
    """
    import re
    text = (message or "").lower()
    
    # Check if message contains specific search keywords
    has_search_keyword = any(keyword in text for keyword in SPECIFIC_SEARCH_KEYWORDS)
    if not has_search_keyword:
        return False
    
    # Check if message contains city location pattern with PROPER city name
    extracted_city = None
    for pattern in CITY_LOCATION_PATTERNS:
        # Do NOT use IGNORECASE - we want to match capitalized city names only
        match = re.search(pattern, message)
        if match:
            candidate = match.group(1)
            # Check if this is actually a city (not a common word)
            if candidate.lower() not in NOT_CITY_WORDS:
                extracted_city = candidate
                break
    
    if extracted_city:
        return True
    
    # Also check for common city name patterns without preposition
    # e.g., "restorani Opatija", "hotels Paris"
    words = message.split()
    for i, word in enumerate(words):
        word_lower = word.lower().rstrip('.,!?')
        if word_lower in SPECIFIC_SEARCH_KEYWORDS:
            # Check if next word is capitalized (likely a city)
            if i + 1 < len(words):
                next_word = words[i + 1].rstrip('.,!?')
                if next_word and next_word[0].isupper():
                    # Make sure it's not a blacklisted word
                    if next_word.lower() not in NOT_CITY_WORDS:
                        return True
    
    return False


def _has_plan_trigger(message: str) -> bool:
    text = (message or "").lower()
    return any(trigger in text for trigger in PLAN_TRIGGER_SUBSTRINGS)


def _should_run_route_detection(message: str) -> bool:
    text = (message or "").lower()
    if not text:
        return False
    return any(token in text for token in ROUTE_HINT_TOKENS)


# Blacklist of common phrases that should NOT be treated as destinations
INVALID_DESTINATION_PHRASES = {
    "go to", "goto", "travel to", "fly to", "drive to", "head to", "get to",
    "go", "travel", "fly", "drive", "head", "get", "visit", "visiting",
    "there", "here", "somewhere", "anywhere", "nowhere", "everywhere",
    "the", "a", "an", "it", "this", "that", "them", "one", "ones",
    "cheapest", "cheap", "expensive", "best", "worst", "fastest", "slowest",
    "would", "could", "should", "might", "may", "can", "will",
}


def _is_valid_destination(dest: Optional[str]) -> bool:
    """Check if a destination is a valid city/place name, not a verb phrase."""
    if not dest:
        return False
    dest_lower = dest.strip().lower()
    # Reject if it's in our blacklist
    if dest_lower in INVALID_DESTINATION_PHRASES:
        return False
    # Reject if it's too short (less than 2 chars)
    if len(dest_lower) < 2:
        return False
    # Reject if it starts with common prepositions that got attached
    if dest_lower.startswith(("to ", "from ", "the ", "a ")):
        return False
    return True


def _extract_route_signals(message: str) -> Dict[str, Optional[str]]:
    detection: Dict[str, Any] = {}
    if ultimate_detect:
        try:
            detection = ultimate_detect(message) or {}
        except Exception:
            detection = {}
    if not detection and planner_detect:
        try:
            detection = planner_detect(message) or {}
        except Exception:
            detection = {}
    origin = detection.get("origin") or detection.get("origin_city") or detection.get("origin_guess")
    destination = detection.get("destination") or detection.get("destination_city") or detection.get("destination_guess")
    
    # Filter out invalid destinations (like "go to", "travel to", etc.)
    if not _is_valid_destination(origin):
        origin = None
    if not _is_valid_destination(destination):
        destination = None
    
    return {"origin": origin, "destination": destination}


class IntentDetector:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def classify(self, message: str, history: List[Dict[str, str]], language_tag: str) -> str:
        """
        SIMPLIFIED INTENT DETECTION - Only 3 categories:
        1. GREETING - Pure greetings (bok, hello, hi)
        2. PLAN_REQUEST - Has origin + destination for travel planning
        3. CHAT - Everything else goes to GPT for intelligent response
        """
        
        # PRIORITY 1: Check if it's a greeting
        if is_greeting(message):
            return "GREETING"
        
        # PRIORITY 2: Check for PLAN_REQUEST with explicit route
        # "Planiram putovanje iz Lisabona u Madrid" → PLAN_REQUEST
        # "I want to travel from Vienna to Prague" → PLAN_REQUEST
        route_signals = _extract_route_signals(message)
        origin = route_signals.get("origin")
        destination = route_signals.get("destination")
        
        # If BOTH origin and destination detected, it's a PLAN_REQUEST
        if origin and destination:
            return "PLAN_REQUEST"
        
        # If has plan trigger + at least one location, it's a PLAN_REQUEST
        if _has_plan_trigger(message) and (origin or destination):
            return "PLAN_REQUEST"
        
        # Explicit plan trigger without locations → still plan request (will ask for details)
        if _has_plan_trigger(message):
            return "PLAN_REQUEST"
        
        # EVERYTHING ELSE → CHAT (GPT handles it intelligently)
        # This includes: "tko si ti", "što radiš", "kako si", travel advice, 
        # recommendations, general questions, etc.
        return "CHAT"
