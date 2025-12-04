import json
import os
import re
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..utils.openai_client import OpenAIClient
from ..utils.intent import IntentDetector, is_greeting
from ..utils.session import (
    get_session_history,
    get_session_memory,
    append_history,
    update_memory,
)
from ..utils.categories import (
    detect_category,
    search_places,
    get_category_query,
    get_category_label,
    get_category_card_type,
)
from ..utils.travel_bundle import build_travel_bundle, build_return_bundle, serialize_bundle, cards_from_bundle
from ..utils.formatters import format_specific_search_response, format_travel_plan
from ..database import get_db
from ..models import User
from ..utils.auth import decode_access_token
from ..utils.language import detect_language, get_greeting_text
from ..utils.geocode import reverse_geocode

try:
    from travel_planner import detect_travel_request, normalize_croatian_city  # type: ignore
except Exception:
    # Fallback implementations if travel_planner not available
    def detect_travel_request(message: str) -> Dict[str, Any]:  # type: ignore
        return {}
    
    def normalize_croatian_city(city: str) -> str:  # type: ignore
        return city.strip().title()

router = APIRouter(prefix="/api", tags=["chat"])
openai_client = OpenAIClient()
intent_detector = IntentDetector(openai_client)


class ChatPayload(BaseModel):
    message: str
    session_id: str


class SessionMemoryPayload(BaseModel):
    session_id: str
    memory: Dict[str, Any]


class ResolveLocationPayload(BaseModel):
    session_id: str
    lat: float
    lng: float
    language_code: Optional[str] = "en"


COUNTRY_KEYWORDS = {
    "croatia": "Croatia",
    "hrvatska": "Croatia",
    "slovenia": "Slovenia",
    "slovenija": "Slovenia",
    "germany": "Germany",
    "deutschland": "Germany",
    "italy": "Italy",
    "italija": "Italy",
    "spain": "Spain",
    "španjolska": "Spain",
    "france": "France",
    "francuska": "France",
}

PROFILE_PATTERNS = [
    (re.compile(r"\b(?:i[' ]?m|i am|im)\s+from\s+([a-zčćšđž ČĆŠĐŽ-]+)", re.IGNORECASE), "home_city"),
    (re.compile(r"\b(?:based|living)\s+in\s+([a-zčćšđž ČĆŠĐŽ-]+)", re.IGNORECASE), "home_city"),
    (re.compile(r"\b(?:ja\s+sam|živim|dolazim)\s+iz\s+([a-zčćšđž ČĆŠĐŽ-]+)", re.IGNORECASE), "home_city"),
    (re.compile(r"\b(?:živim|nalazim se)\s+u\s+([a-zčćšđž ČĆŠĐŽ-]+)", re.IGNORECASE), "home_city"),
    (re.compile(r"\b(?:sem|živim)\s+v\s+([a-zčćšđž ČĆŠĐŽ-]+)", re.IGNORECASE), "home_city"),
]

INTEREST_KEYWORDS = {
    "skiing": ["ski", "skij", "skija", "skijanje"],
    "winter": ["snow", "snijeg", "zima"],
    "beach": ["beach", "plaž", "sun"],
    "culture": ["museum", "muzej", "heritage"],
}


def _clean_location_value(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Zčćšđž ČĆŠĐŽ-]", " ", value or "").strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return normalize_croatian_city(cleaned) if cleaned else ""


def extract_profile_metadata(message: str) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    text = (message or "").strip()
    if not text:
        return updates
    for pattern, key in PROFILE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw_value = _clean_location_value(match.group(1))
        if not raw_value:
            continue
        normalized = raw_value.lower()
        country = COUNTRY_KEYWORDS.get(normalized)
        if country:
            updates["home_country"] = country
        elif key == "home_city":
            updates["home_city"] = raw_value.title()
    return updates


def detect_interest_tag(message: str) -> Optional[str]:
    lowered = (message or "").lower()
    for label, keywords in INTEREST_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def build_advice_context(profile: Dict[str, Any], origin: Optional[str], destination: Optional[str]) -> str:
    bits: List[str] = []
    home_city = profile.get("home_city") or origin
    if home_city:
        bits.append(f"home_city={home_city}")
    home_country = profile.get("home_country")
    if home_country:
        bits.append(f"home_country={home_country}")
    interests = profile.get("interests")
    if interests:
        bits.append("interests=" + ", ".join(interests))
    if destination:
        bits.append(f"current_topic={destination}")
    return " | ".join(bits)


def _should_update_language(prev_code: Optional[str], new_code: str, message: str) -> bool:
    if not prev_code:
        return True
    if not new_code or new_code == prev_code:
        return False
    if is_greeting(message):
        return False
    stripped = (message or "").strip()
    if len(stripped) < 4:
        return False
    if len(stripped.split()) <= 1 and stripped.lower() in {"hi", "hey", "hello", "hola", "bok", "pozdrav", "ciao", "servus", "привіт", "привітання", "вітаю"}:
        return False
    return True


def _extract_city(message: str, pattern: str) -> str:
    match = re.search(pattern, message, flags=re.IGNORECASE)
    if not match:
        return ""
    city = match.group(1).strip()
    city = re.sub(r"[^a-zA-Zčćšđž ČĆŠĐŽ-]", "", city)
    return city


def detect_origin(message: str) -> str:
    for pattern in [r"from\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)", r"iz\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)"]:
        city = _extract_city(message, pattern)
        if city:
            return city
    return ""


def detect_destination(message: str) -> str:
    for pattern in [
        r"to\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)",
        r"u\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)",
        r"za\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)",
        r"prema\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)",
        r"in\s+([a-zA-Zčćšđž ČĆŠĐŽ-]+)",
    ]:
        city = _extract_city(message, pattern)
        if city:
            return city
    return ""


def is_return_trip_request(message: str) -> bool:
    """
    Detect if user is asking for a return trip plan (going home).
    Keywords: povratak, return, nazad, back, put kući, going home, etc.
    """
    message_lower = message.lower()
    
    # Croatian/Slovenian return keywords
    croatian_keywords = [
        "povratak", "povratka", "povratni", "nazad", "natrag", 
        "put kuć", "put doma", "vraćam se", "vračam se",
        "kako se vratiti", "kako se vračat", "kući", "doma"
    ]
    
    # English return keywords
    english_keywords = [
        "return trip", "way back", "going back", "get back",
        "return home", "going home", "back home", "trip back"
    ]
    
    all_keywords = croatian_keywords + english_keywords
    
    return any(keyword in message_lower for keyword in all_keywords)


def is_round_trip_request(message: str) -> bool:
    """
    Detect if user is asking for a round trip (outbound + return in same request).
    Keywords: sa povratkom, with return, round trip, return flight included, etc.
    """
    message_lower = message.lower()
    
    # Croatian round trip keywords
    croatian_round_trip = [
        "sa povratkom", "s povratkom", "i povratak", "i povratkom",
        "povratna karta", "povratne karte", "tamo i nazad", "tamo-nazad",
        "u oba smjera", "obostrano"
    ]
    
    # English round trip keywords  
    english_round_trip = [
        "round trip", "round-trip", "roundtrip", "with return",
        "return included", "both ways", "there and back", "two-way"
    ]
    
    # German round trip keywords
    german_round_trip = [
        "hin und zurück", "rundreise", "mit rückflug"
    ]
    
    all_round_trip = croatian_round_trip + english_round_trip + german_round_trip
    
    return any(keyword in message_lower for keyword in all_round_trip)


@router.post("/chat")
async def chat(
    payload: ChatPayload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    message = payload.message.strip()
    session_id = payload.session_id.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    # Try to get authenticated user (optional)
    authenticated_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload_data = decode_access_token(token)
            if payload_data and "sub" in payload_data:
                user_id = payload_data["sub"]
                authenticated_user = db.query(User).filter(User.id == user_id).first()
        except:
            pass  # Continue without auth if token is invalid
    
    history = get_session_history(session_id)
    session_memory = get_session_memory(session_id)

    memory_updates: Dict[str, Any] = {}
    
    # CRITICAL: Always use fresh language detection to avoid mixing
    detected_tag, detected_code = detect_language(message, None)
    language_code = detected_code
    language_tag = detected_tag
    
    # Always update memory with fresh detected language
    memory_updates["language_code"] = language_code
    memory_updates["language_tag"] = language_tag

    profile = dict(session_memory.get("profile") or {})
    
    # CRITICAL: Merge authenticated user data into profile if available
    if authenticated_user:
        # Override profile with actual user data from database
        if authenticated_user.full_name:
            profile["full_name"] = authenticated_user.full_name
        if authenticated_user.gender:
            profile["gender"] = authenticated_user.gender
        if authenticated_user.date_of_birth:
            profile["date_of_birth"] = authenticated_user.date_of_birth.isoformat()
        if authenticated_user.country:
            profile["country"] = authenticated_user.country
            profile["home_city"] = authenticated_user.country  # Fallback
        if authenticated_user.interests:
            profile["interests"] = authenticated_user.interests
        if authenticated_user.travel_frequency:
            profile["travel_frequency"] = authenticated_user.travel_frequency
        if authenticated_user.budget:
            profile["budget"] = authenticated_user.budget
        if authenticated_user.travel_reasons:
            profile["travel_reasons"] = authenticated_user.travel_reasons
    
    profile_updates = extract_profile_metadata(message)
    interest_tag = detect_interest_tag(message)
    profile_changed = False
    for key, value in profile_updates.items():
        if value and profile.get(key) != value:
            profile[key] = value
            profile_changed = True
    if interest_tag:
        interests = list(profile.get("interests") or [])
        if interest_tag not in interests:
            interests.append(interest_tag)
            profile["interests"] = interests
            profile_changed = True
    if profile_changed:
        memory_updates["profile"] = profile

    if memory_updates:
        session_memory = update_memory(session_id, memory_updates)
    if not profile:
        profile = dict(session_memory.get("profile") or {})

    # Import small talk detection
    from ..utils.intent import is_small_talk
    from ..utils.language import get_small_talk_text
    
    # Fast greeting/small talk response without GPT (instant reply)
    if is_greeting(message):
        # Check if it's small talk (how are you, what's up, etc.) vs simple greeting
        if is_small_talk(message):
            reply = get_small_talk_text(language_code)
        else:
            reply = get_greeting_text(language_code)
        append_history(session_id, message, reply)
        return {"reply": reply, "intent": "GREETING"}
    
    # PROFILE_QUESTION - User asking about their profile (no CARD blocks)
    from ..utils.intent import is_profile_question
    if is_profile_question(message):
        profile_messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"You are MOBIX, a friendly travel assistant. Answer in {language_tag}. "
                    f"User is asking about their profile/information YOU know about them. "
                    f"Respond naturally and conversationally about what you know from their profile. "
                    f"Be friendly and concise (2-4 sentences). Use emojis sparingly for warmth. "
                    f"If profile is empty/limited, acknowledge this politely."
                ),
            }
        ]
        
        # Add user profile context
        if profile:
            profile_messages.append({"role": "system", "content": f"USER_PROFILE: {json.dumps(profile, ensure_ascii=False)}"})
        else:
            profile_messages.append({"role": "system", "content": "USER_PROFILE: No profile data available yet."})
        
        profile_messages.extend(history[-5:])
        profile_messages.append({"role": "user", "content": message})
        
        ai_reply = await openai_client.chat(profile_messages, language_tag, language_code, max_tokens=600)
        
        append_history(session_id, message, ai_reply)
        return {"reply": ai_reply, "intent": "PROFILE_QUESTION"}

    travel_request = detect_travel_request(message) or {}
    
    # Extract dates and budget from travel_request (with safe defaults)
    dates_info = travel_request.get("dates") or {}
    departure_date = dates_info.get("departure") if dates_info else None
    return_date = dates_info.get("return") if dates_info else None
    budget_amount = travel_request.get("budget")

    intent_type = await intent_detector.classify(message, history, language_tag)
    print(f"[MOBIX DEBUG] Message: '{message[:50]}...' -> Intent: {intent_type}")
    
    # GENERAL_QUESTION - User asking general questions (no CARD blocks)
    if intent_type == "GENERAL_QUESTION":
        general_messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"You are MOBIX, a friendly travel assistant. Answer in {language_tag}. "
                    f"User is asking a general travel question. Provide helpful, accurate information. "
                    f"Be concise but thorough (4-6 sentences max). Use emojis sparingly. "
                    f"If you reference previous context (like 'that hotel' or 'the trip we discussed'), "
                    f"use session memory. NO CARD BLOCKS - just conversational answer."
                ),
            }
        ]
        
        # Add session memory context for follow-up questions
        if session_memory:
            context_parts = []
            if session_memory.get("last_destination"):
                context_parts.append(f"Last discussed destination: {session_memory['last_destination']}")
            if session_memory.get("last_origin"):
                context_parts.append(f"from {session_memory['last_origin']}")
            if context_parts:
                general_messages.append({"role": "system", "content": f"CONTEXT: {' '.join(context_parts)}"})
        
        general_messages.extend(history[-8:])
        general_messages.append({"role": "user", "content": message})
        
        ai_reply = await openai_client.chat(general_messages, language_tag, language_code, max_tokens=1000)
        
        append_history(session_id, message, ai_reply)
        return {"reply": ai_reply, "intent": "GENERAL_QUESTION"}

    # Use GPT to extract origin/destination for complex queries (e.g., "iz Omišlja na otoku Krku u Atenu")
    origin_hint = travel_request.get("origin")
    destination = travel_request.get("destination")
    
    # ONLY extract cities for PLAN_REQUEST - skip for GENERAL_QUESTION, GREETING, etc.
    if intent_type == "PLAN_REQUEST":
        # If travel_planner didn't find origin/destination, try GPT extraction
        if not origin_hint or not destination:
            gpt_extract = await openai_client.extract_travel_locations(message, language_tag)
            if gpt_extract:
                if not origin_hint and gpt_extract.get("origin"):
                    origin_hint = gpt_extract["origin"]
                if not destination and gpt_extract.get("destination"):
                    destination = gpt_extract["destination"]
        
        # Fallback to regex and memory for origin
        if not origin_hint:
            origin_hint = (
                detect_origin(message)
                or session_memory.get("current_location")
                or profile.get("home_city")
            )
        
        # Fallback to regex for destination
        if not destination:
            destination = detect_destination(message)
        
        # Only use memory for follow-up questions about existing PLAN_REQUEST, NOT for new advice/search queries
        # This prevents "Kamo na skijanje?" from using Barcelona memory and becoming a PLAN_REQUEST
        # Also prevents "Koliko dana trebam?" after TRAVEL_ADVICE from pulling old PLAN_REQUEST memory
        last_intent = session_memory.get("last_plan_type")
        if not destination and session_memory.get("last_destination"):
            # Only apply memory if:
            # 1. Current intent is not TRAVEL_ADVICE or SPECIFIC_SEARCH (those are new queries), AND
            # 2. Last intent was PLAN_REQUEST or QUESTION_ONLY (continuing a plan conversation)
            if intent_type not in ("TRAVEL_ADVICE", "SPECIFIC_SEARCH"):
                if last_intent in ("PLAN_REQUEST", "QUESTION_ONLY"):
                    destination = session_memory.get("last_destination")
                    origin_hint = origin_hint or session_memory.get("last_origin")
    
    origin_city = normalize_croatian_city(origin_hint) if origin_hint else None
    destination_city = normalize_croatian_city(destination) if destination else None
    travel_context: Dict[str, Any] = dict(travel_request)
    
    # Update travel context with dates and budget if provided
    if departure_date:
        travel_context["departure_date"] = departure_date
    if return_date:
        travel_context["return_date"] = return_date
    if budget_amount:
        travel_context["budget"] = budget_amount
    
    if origin_city:
        travel_context["origin"] = origin_city
    if destination_city:
        travel_context["destination"] = destination_city
    # Only override intent if we have BOTH cities AND intent is not already special type
    # This prevents "Guten Tag" from becoming PLAN_REQUEST when detected as greeting
    # Also prevents "What can you do" from becoming PLAN_REQUEST if it accidentally parsed cities
    if origin_city and destination_city and intent_type not in ("GREETING", "PROFILE_QUESTION", "GENERAL_QUESTION"):
        intent_type = "PLAN_REQUEST"
    if interest_tag:
        preferences = list(travel_context.get("preferences") or [])
        if interest_tag not in preferences:
            preferences.append(interest_tag)
            travel_context["preferences"] = preferences
    google_key = (os.getenv("GOOGLE_API_KEY") or "").strip()

    # Build search results for SPECIFIC_SEARCH but let GPT explain WHY
    search_results = None
    if intent_type == "SPECIFIC_SEARCH":
        category = detect_category(message)
        # Try to extract city from message, fallback to context
        city = destination_city or origin_city or ""
        # If no city detected, try to extract from message patterns like "u Budimpesti", "in Paris"
        if not city:
            import re
            from ..utils.intent import NOT_CITY_WORDS
            city_patterns = [
                r'\bu\s+([A-ZČĆŠĐŽ][a-zčćšđžA-ZČĆŠĐŽ]+)',  # "u Budimpesti" - must start with capital
                r'\bin\s+([A-Z][a-zA-Z]+)',  # "in Paris" - must start with capital
                r'\bà\s+([A-Z][a-zA-Z]+)',  # "à Paris"
                r'\ben\s+([A-Z][a-zA-Z]+)',  # "en Madrid"
            ]
            for pattern in city_patterns:
                match = re.search(pattern, message)
                if match:
                    candidate = match.group(1)
                    # Make sure it's not a blacklisted word
                    if candidate.lower() not in NOT_CITY_WORDS:
                        city = candidate.title()
                        break
        
        # IMPORTANT: Only search for places if we have a REAL city
        # Without a real city, we would get irrelevant default results
        if city:
            places = await search_places(
                get_category_query(category),
                city,
                language_code=language_code,
                google_key=google_key,
            )
            # Store results to append after GPT response
            search_results = {
                "category": category,
                "city": city,
                "places": places
            }
        # If no city, search_results stays None and no cards will be added

    travel_bundle = None
    return_bundle = None  # For round trips
    budget_hint = travel_context.get("budget")
    
    # Check if this is a return trip request (going home only)
    is_return_request = is_return_trip_request(message)
    # Check if this is a round trip request (outbound + return in same request)
    is_round_trip = is_round_trip_request(message)
    
    # IMPORTANT: For any PLAN_REQUEST, we ALWAYS include return trip
    # This is standard travel planning behavior
    always_include_return = intent_type == "PLAN_REQUEST" and origin_city and destination_city and not is_return_request
    
    # For return trips (going home), swap origin and destination
    if is_return_request and not is_round_trip:
        # User wants to go back home from destination
        # Swap: origin becomes where they are now, destination becomes home
        if origin_city and destination_city:
            # If both cities mentioned, swap them
            origin_city, destination_city = destination_city, origin_city
        elif destination_city and session_memory.get("last_origin"):
            # If only destination mentioned, use last origin as new destination (home)
            origin_city = destination_city
            destination_city = session_memory.get("last_origin")
        elif session_memory.get("last_destination") and session_memory.get("last_origin"):
            # Use session memory for return trip: last_destination → last_origin
            origin_city = session_memory.get("last_destination")
            destination_city = session_memory.get("last_origin")
    
    # Only build travel bundle for PLAN_REQUEST with clear destination
    # TRAVEL_ADVICE should give suggestions, not full plans
    if intent_type == "PLAN_REQUEST" and origin_city and destination_city:
        # Check if this is a return trip request
        if is_return_request and not is_round_trip:
            # Build RETURN-ONLY bundle (transportation only, no hotels/activities)
            travel_bundle = await build_return_bundle(
                origin_city,
                destination_city,
                {"google": google_key},
                budget_hint,
                language_code,
                travel_context,
            )
        else:
            # Build full travel bundle (transportation + hotels + activities)
            travel_bundle = await build_travel_bundle(
                origin_city,
                destination_city,
                {"google": google_key},
                budget_hint,
                language_code,
                travel_context,
            )
            
            # ALWAYS build return bundle for PLAN_REQUEST (not just when explicitly requested)
            # This is standard travel planning - always show both outbound and return options
            if is_round_trip or always_include_return:
                return_bundle = await build_return_bundle(
                    destination_city,  # Start from destination
                    origin_city,       # Return to origin
                    {"google": google_key},
                    budget_hint,
                    language_code,
                    travel_context,
                )
    
    messages: List[Dict[str, str]] = []
    messages = [{"role": "system", "content": f"INTENT: {intent_type}"}]
    
    # Add return trip instruction for return-only requests (not round trips)
    if is_return_request and not is_round_trip and intent_type == "PLAN_REQUEST":
        messages.append({"role": "system", "content": (
            f"RETURN_TRIP_MODE: User requested a RETURN trip from {origin_city} back to {destination_city}. "
            f"Focus ONLY on transportation options (flights, buses, trains, driving). "
            f"DO NOT suggest hotels, restaurants, or activities - user is going home. "
            f"Keep response brief and focused on getting home efficiently."
        )})
    
    # For all PLAN_REQUEST trips (whether explicitly round trip or not), return is always included
    if (is_round_trip or always_include_return) and intent_type == "PLAN_REQUEST":
        messages.append({"role": "system", "content": (
            f"COMPLETE_TRAVEL_PLAN: This is a complete travel plan from {origin_city} to {destination_city}. "
            f"The backend AUTOMATICALLY includes BOTH outbound AND return trip options. "
            f"Outbound section shows: transport, hotels, restaurants, activities. "
            f"Return section (🔄 Povratak) shows: transport options only. "
            f"In your intro, mention this is a complete plan with return included. "
            f"DO NOT ask if they want a return trip - IT IS ALREADY INCLUDED AUTOMATICALLY!"
        )})
    
    # Add user-provided dates and budget (CRITICAL for GPT to acknowledge them)
    user_info_parts = []
    if departure_date:
        # Format date nicely: "2026-01-30" → "30 January 2026"
        from datetime import datetime
        try:
            dt = datetime.strptime(departure_date, "%Y-%m-%d")
            formatted_departure = dt.strftime("%d.%m.%Y")
            user_info_parts.append(f"Departure: {formatted_departure}")
        except:
            user_info_parts.append(f"Departure: {departure_date}")
    if return_date:
        try:
            dt = datetime.strptime(return_date, "%Y-%m-%d")
            formatted_return = dt.strftime("%d.%m.%Y")
            user_info_parts.append(f"Return: {formatted_return}")
        except:
            user_info_parts.append(f"Return: {return_date}")
    if budget_amount:
        user_info_parts.append(f"Budget: €{budget_amount}")
    if user_info_parts:
        messages.append({"role": "system", "content": f"USER_INFO: {', '.join(user_info_parts)} - YOU MUST acknowledge these dates in your intro! User asked for travel from {departure_date} to {return_date}."})
    
    # Special handling for Croatian to avoid Slovenian mixing
    lang_instruction = f"CRITICAL_LANGUAGE_RULE: User speaks {language_code.upper()} ({language_tag}). YOU MUST respond 100% in {language_tag}. NEVER use Spanish/English/other languages."
    if language_code == "hr":
        lang_instruction += " Write in CROATIAN ONLY - use 'za' not 'za', 'oko' not 'približno', 'vjerojatno' not 'verjetno'."
    
    messages.append({"role": "system", "content": lang_instruction})
    
    # QUALITY & FORMATTING RULES - NEW!
    quality_rules = (
        "QUALITY_STANDARDS:\n"
        "1. RATINGS: Only recommend places with 4.3+ stars (Google/TripAdvisor)\n"
        "2. VERIFICATION: Verify all places are currently open and operational\n"
        "3. RECENCY: Prefer recently reviewed places (last 6 months)\n"
        "4. AUTHENTICITY: Include local hidden gems, not just tourist traps\n"
        "5. BUDGET ACCURACY: Match price range exactly to user's budget\n\n"
        "FORMATTING_RULES:\n"
        "1. Use clear headings with emojis (🚗 Transport | 🏨 Accommodation | 🍽️ Dining | 🎭 Activities)\n"
        "2. Write in short, scannable paragraphs (3-4 sentences max)\n"
        "3. Use bullet points for quick tips\n"
        "4. Bold important info like prices, timings, booking links\n"
        "5. Add helpful context: opening hours, best times to visit, insider tips\n"
        "6. Include specific details: exact addresses, phone numbers, booking websites\n"
        "7. Structure: Brief intro → Detailed recommendations → Practical tips → Call to action\n\n"
        "TONE:\n"
        "- Friendly and enthusiastic, but not over-the-top\n"
        "- Professional yet conversational\n"
        "- Helpful like a knowledgeable local friend\n"
        "- Confidence in recommendations (avoid 'maybe', 'might')\n"
        "- Use specific details to build trust"
    )
    messages.append({"role": "system", "content": quality_rules})
    
    # CRITICAL: Send COMPLETE user profile to GPT for personalized recommendations
    if profile:
        # Build detailed user context from profile
        user_context_parts = []
        
        # Basic info
        home_city = profile.get("home_city")
        if home_city:
            user_context_parts.append(f"Lives in: {home_city}")
        
        # Age calculation from date_of_birth
        dob_str = profile.get("date_of_birth")
        if dob_str:
            try:
                from datetime import datetime
                dob = datetime.fromisoformat(dob_str.split('T')[0])
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                user_context_parts.append(f"Age: {age} years old")
            except:
                pass
        
        # Travel preferences
        interests = profile.get("interests")
        if interests:
            if isinstance(interests, list):
                user_context_parts.append(f"Interests: {', '.join(interests)}")
            else:
                user_context_parts.append(f"Interests: {interests}")
        
        travel_reasons = profile.get("travel_reasons")
        if travel_reasons:
            user_context_parts.append(f"Travel motivation: {travel_reasons}")
        
        budget = profile.get("budget")
        if budget:
            user_context_parts.append(f"Budget preference: {budget}")
        
        travel_frequency = profile.get("travel_frequency")
        if travel_frequency:
            user_context_parts.append(f"Travel frequency: {travel_frequency}")
        
        gender = profile.get("gender")
        if gender:
            user_context_parts.append(f"Gender: {gender}")
        
        # Send enriched profile to GPT
        if user_context_parts:
            user_profile_text = " | ".join(user_context_parts)
            messages.append({"role": "system", "content": (
                f"USER_PROFILE: {user_profile_text}\n\n"
                f"PERSONALIZATION_RULE: Use this profile information to tailor ALL recommendations. "
                f"Consider user's age, interests, budget, and travel motivations when suggesting destinations, "
                f"activities, hotels, and restaurants. Make recommendations feel personally crafted for THIS user."
            )})
        else:
            # Fallback to basic profile
            messages.append({"role": "system", "content": f"PROFILE: {json.dumps(profile, ensure_ascii=False)}"})
    
    # Add context about last destination for follow-up questions
    if session_memory.get("last_destination") and not travel_bundle:
        messages.append({"role": "system", "content": f"CONTEXT: Last discussed destination was {session_memory.get('last_destination')} from {session_memory.get('last_origin', 'user location')}. User may be asking follow-up questions about this trip."})
    
    if travel_bundle:
        messages.append({"role": "system", "content": f"TRAVEL_DATA: {serialize_bundle(travel_bundle)}"})
        
        # Get distance info - handle None for cross-continental routes
        driving_info = travel_bundle.get('driving') or {}
        distance_km = driving_info.get('distance_km', '?')
        
        # Build context about available options for GPT
        has_flights = bool(travel_bundle.get("flights"))
        has_trains = bool(travel_bundle.get("trains"))
        has_buses = bool(travel_bundle.get("buses"))
        has_driving = bool(travel_bundle.get("driving"))
        has_hotels = bool(travel_bundle.get("hotels"))
        has_restaurants = bool(travel_bundle.get("restaurants"))
        has_activities = bool(travel_bundle.get("activities"))
        
        # ENHANCED: GPT writes engaging narrative BEFORE cards appear
        messages.append({"role": "system", "content": (
            f"PLAN_REQUEST_INSTRUCTIONS:\n\n"
            f"You are creating a COMPLETE travel plan from {travel_bundle.get('origin')} to {travel_bundle.get('destination')} ({distance_km} km).\n\n"
            f"WRITE A DETAILED NARRATIVE in {language_tag} that explains your recommendations. Structure:\n\n"
            f"📍 **INTRO** (2-3 sentences):\n"
            f"- Mention the route and distance\n"
            f"- Set the scene - what makes this journey interesting\n\n"
            f"🚗 **TRANSPORT SECTION** (write this BEFORE transport cards appear):\n"
            f"- Explain which transport options are available and WHY each might suit different travelers\n"
            f"- {'✈️ Flights available - mention that flying is fastest' if has_flights else ''}\n"
            f"- {'🚆 Trains available - mention scenic routes or overnight options' if has_trains else ''}\n"
            f"- {'🚌 Buses available - mention budget-friendly option' if has_buses else ''}\n"
            f"- {'🚗 Driving possible - mention road trip experience, flexibility' if has_driving else ''}\n"
            f"- Give your RECOMMENDATION: which option is best for most travelers and why\n\n"
            f"🏨 **ACCOMMODATION SECTION** (write this BEFORE hotel cards appear):\n"
            f"- {'Explain the hotel selection - mix of budget, mid-range, luxury' if has_hotels else 'Skip this section'}\n"
            f"- Mention what neighborhoods/areas are best to stay in\n"
            f"- Give a price range overview\n\n"
            f"🍽️ **DINING SECTION** (write this BEFORE restaurant cards appear):\n"
            f"- {'Describe the food scene and your restaurant picks' if has_restaurants else 'Skip this section'}\n"
            f"- Mention local specialties to try\n"
            f"- Mix of cuisines and price points\n\n"
            f"🎯 **ACTIVITIES SECTION** (write this BEFORE activity cards appear):\n"
            f"- {'Explain why you chose these attractions' if has_activities else 'Skip this section'}\n"
            f"- Mix of iconic landmarks and hidden gems\n"
            f"- Practical tips (best time to visit, book ahead, etc.)\n\n"
            f"IMPORTANT FORMATTING:\n"
            f"- Use section headers with emojis: 🧭 Ruta, ✈️ Letovi, 🚗 Vožnja, 🏨 Smještaj, 🍽️ Restorani, 🎯 Aktivnosti\n"
            f"- Write 3-5 sentences per section explaining WHY these options\n"
            f"- Be enthusiastic but informative\n"
            f"- The CARD blocks will be added AUTOMATICALLY after your text by the backend\n"
            f"- DO NOT create your own [CARD] blocks - backend handles that!\n"
            f"- End with a helpful summary or travel tip"
        )})
        
        # Add note if no flights (short routes)
        if not travel_bundle.get("flights") and driving_info:
            driving_km = driving_info.get("distance_km", 0)
            if driving_km and driving_km < 300:
                messages.append({"role": "system", "content": (
                    f"NOTE: This is a SHORT route ({driving_km}km). "
                    f"In your intro, mention that car/bus is more practical than flying for this distance. "
                    f"Suggest car or bus as primary options."
                )})
    
    if search_results:
        # Add search results for SPECIFIC_SEARCH so GPT can explain WHY each place
        places_summary = json.dumps([{
            "name": p.get("name"),
            "rating": p.get("rating"),
            "address": p.get("address")
        } for p in search_results["places"][:5]], ensure_ascii=False)
        messages.append({"role": "system", "content": f"SEARCH_RESULTS: Found {len(search_results['places'])} {search_results['category']} in {search_results['city']}. Top places: {places_summary}. YOU MUST write 2-3 sentences WHY EACH place is recommended BEFORE the backend adds structured data."})
    
    if intent_type == "TRAVEL_ADVICE":
        # CRITICAL: User is asking WHERE to go, not HOW to get there
        # Provide 3-5 destination recommendations with detailed explanations
        advice_context = build_advice_context(profile, origin_city, destination_city)
        
        # Add seasonal and budget context
        from datetime import datetime
        current_month = datetime.now().month
        season = "winter" if current_month in [12, 1, 2] else "spring" if current_month in [3, 4, 5] else "summer" if current_month in [6, 7, 8] else "autumn"
        
        # Build context about WHERE user is asking from
        user_location_context = ""
        if origin_city or profile.get("home_city"):
            user_home = origin_city or profile.get("home_city")
            user_location_context = f"User lives in/is from: {user_home}. "
            # Check if asking for domestic recommendations
            domestic_keywords = ["inside my country", "within", "u hrvatskoj", "po hrvatskoj", "domestic", "vikend", "weekend getaway"]
            is_domestic_request = any(kw in message.lower() for kw in domestic_keywords)
            if is_domestic_request:
                user_location_context += f"User wants DOMESTIC recommendations (within same country as {user_home}). DO NOT recommend {user_home} or nearby towns - they already live there! "
        
        messages.append({"role": "system", "content": (
            f"TRAVEL_ADVICE_MODE: User is asking for destination recommendations (WHERE to go).\n"
            f"Context: {user_location_context}{advice_context if advice_context else 'User location unknown'}\n"
            f"Current season: {season} - Recommend destinations that are BEST in this season!\n\n"
            f"YOUR TASK:\n"
            f"1. Suggest 3-5 specific cities/destinations perfect for their request AND current season\n"
            f"2. For EACH destination, write a detailed paragraph (4-5 sentences) explaining:\n"
            f"   - WHY this destination is perfect for them RIGHT NOW (seasonal considerations)\n"
            f"   - What makes it special/unique (cultural, natural, urban attractions)\n"
            f"   - Best things to do there (mix of must-sees and hidden gems)\n"
            f"   - Approximate budget range (transportation + accommodation + daily expenses)\n"
            f"   - INSIDER TIP: One local secret or travel hack for this destination\n"
            f"3. Consider user's profile: age, interests, budget level, travel frequency\n"
            f"4. Use enthusiastic, engaging language in {language_tag}\n"
            f"5. Add emojis for visual appeal: 🏖️ beach, 🏔️ mountains, 🏛️ culture, 🍷 food, 🎭 events\n"
            f"6. After suggestions, ask which destination interests them most\n\n"
            f"QUALITY STANDARDS:\n"
            f"- Only recommend places you're confident about with accurate info\n"
            f"- Include mix of popular and off-the-beaten-path destinations\n"
            f"- Be realistic about costs - don't lowball budget estimates\n"
            f"- Mention any visa requirements, safety concerns, or travel restrictions\n"
            f"- If user wants domestic recommendations, suggest places WITHIN their country but FAR from home\n\n"
            f"DO NOT provide travel plans, routes, transportation details, or CARD blocks - just recommend destinations with compelling reasons!"
        )})
    
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": message})

    # Increase max_tokens for PLAN_REQUEST and TRAVEL_ADVICE to allow full explanations
    max_tokens = 2500 if intent_type in ("PLAN_REQUEST", "TRAVEL_ADVICE") else 1800
    ai_reply = await openai_client.chat(messages, language_tag, language_code, max_tokens=max_tokens)
    
    # Clean up asterisks from GPT output (** and ***)
    ai_reply = ai_reply.replace("***", "").replace("**", "")
    
    # Append structured data based on intent type
    if travel_bundle and intent_type == "PLAN_REQUEST":
        # Travel plan: Add structured route, flights, hotels, etc.
        plan_text = format_travel_plan(travel_bundle, language_code)
        ai_reply = f"{ai_reply}\n\n{plan_text}".strip()
        
        # ALWAYS add return bundle for complete travel plans (standard behavior)
        if return_bundle and (is_round_trip or always_include_return):
            # Add section header for return trip
            return_header = {
                "hr": "\n\n---\n\n## 🔄 Povratak\n",
                "en": "\n\n---\n\n## 🔄 Return Trip\n",
                "de": "\n\n---\n\n## 🔄 Rückreise\n",
                "sl": "\n\n---\n\n## 🔄 Povratek\n",
            }
            header = return_header.get(language_code, return_header["en"])
            return_plan_text = format_travel_plan(return_bundle, language_code)
            ai_reply = f"{ai_reply}{header}{return_plan_text}".strip()
        
        # Track last destination for follow-up questions like "Koliko to košta?"
        if destination_city:
            update_memory(session_id, {
                "last_destination": destination_city,
                "last_origin": origin_city or "",
                "last_plan_type": intent_type
            })
    elif search_results and intent_type == "SPECIFIC_SEARCH":
        # Specific search: Append CARD blocks with Google Maps links and Add to Planner buttons
        category = search_results.get("category", "places")
        city = search_results.get("city", "")
        places = search_results.get("places", [])
        
        # Generate card blocks for frontend to display with proper icons and links
        from ..utils.formatters import cards_from_places
        category_card_type = get_category_card_type(category)
        cards_text = cards_from_places(category_card_type, city, places)
        
        if cards_text:
            # Append cards after GPT's explanation
            ai_reply += "\n\n" + cards_text
    
    # Clear destination context for advice/search queries
    if intent_type in ["TRAVEL_ADVICE", "SPECIFIC_SEARCH"]:
        # Clear previous destination context when giving new advice
        update_memory(session_id, {
            "last_destination": None,
            "last_origin": None,
            "last_plan_type": intent_type  # Update to current intent type
        })

    append_history(session_id, message, ai_reply)
    return {"reply": ai_reply, "intent": intent_type}


@router.post("/session/memory")
async def update_session_memory(payload: SessionMemoryPayload):
    memory = update_memory(payload.session_id, payload.memory)
    return {"session_id": payload.session_id, "memory": memory}


@router.post("/session/resolve-location")
async def resolve_location(payload: ResolveLocationPayload):
    geo = await reverse_geocode(payload.lat, payload.lng, payload.language_code or "en")
    memory = update_memory(payload.session_id, {"current_location": geo.get("city")})
    return {"session_id": payload.session_id, "geo": geo, "memory": memory}
