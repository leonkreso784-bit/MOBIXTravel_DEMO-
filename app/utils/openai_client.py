import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

# Load .env only if it exists (for local development)
# On Railway/production, env vars are set directly
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)

try:
    from .ultimate_detector import ultimate_detect
except ImportError:  # pragma: no cover
    ultimate_detect = None  # type: ignore

from .language import get_greeting_text

GREETING_TOKENS = {
    "hi",
    "hi!",
    "hello",
    "hello!",
    "hey",
    "hey!",
    "hola",
    "hola!",
    "bok",
    "bok!",
    "pozdrav",
    "pozdrav!",
    "ciao",
    "ciao!",
    "servus",
    "servus!",
    "zdravo",
    "zdravo!",
    "hallo",
    "hallo!",
    "bonjour",
    "bonjour!",
    "привіт",
    "привіт!",
    "привітання",
    "привітання!",
    "вітаю",
    "вітаю!",
}

TRAVEL_HINTS = (
    "putovan",
    "plan putovanja",
    "itiner",
    "itinerary",
    "ruta",
    "route",
    "trip",
    "travel",
    "journey",
    "flight",
    "let",
    "hotel",
    "smještaj",
    "budžet",
    "budget",
    "bus",
    "vlak",
    "train",
    "maršrut",
    "маршрут",
    "подорож",
    "podoroz",
)

PLAN_HINTS = (
    "plan",
    "itinerary",
    "planiraj",
    "isplaniraj",
    "napravi plan",
    "maršrut",
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

def _looks_like_greeting(message: str) -> bool:
    """Check if message is a PURE greeting only (hello, hi, bok, etc.)"""
    text = (message or "").strip().lower()
    return text in GREETING_TOKENS


def _has_route_hint(text: str) -> bool:
    return any(token in text for token in ROUTE_HINT_TOKENS)


def _has_travel_hint(text: str) -> bool:
    return any(hint in text for hint in TRAVEL_HINTS)


def _has_plan_hint(text: str) -> bool:
    return any(hint in text for hint in PLAN_HINTS)


class OpenAIClient:
    """Lightweight OpenAI Chat Completions wrapper with shared system prompt."""

    def __init__(self) -> None:
        self.api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        self.enabled = bool(self.api_key)
        self.model = (os.getenv("OPENAI_MODEL") or "gpt-4o").strip()
        if not self.model:
            self.model = "gpt-4o"
        self.project = os.getenv("OPENAI_PROJECT")
        self.organization = os.getenv("OPENAI_ORG")
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        if self.project:
            headers["OpenAI-Project"] = self.project
        return headers

    def _build_system_prompt(self, language_tag: str, language_code: str) -> str:
        lang_name = (language_tag or "ENGLISH").split("(")[0].strip() or "English"
        lang_code = (language_code or "en").lower()
        return (
            f"🌍 MOBIX TRAVEL ASSISTANT\n"
            f"========================\n\n"
            f"⚠️ CRITICAL: Respond ONLY in {lang_name.upper()} ({lang_code.upper()})!\n\n"
            f"You are MOBIX Travel, a friendly and knowledgeable travel assistant.\n\n"
            f"INTENT HANDLING:\n"
            f"----------------\n"
            f"1. GREETING → Generate a warm, personalized welcome. Introduce yourself briefly, "
            f"mention 2-3 specific things you can help with (trip planning, finding hotels/restaurants, "
            f"destination advice). End with an open question. Use 1-2 emojis. Keep it 3-4 sentences.\n\n"
            f"2. QUESTION_ONLY → Light conversation or factual Q&A. Give concise, helpful responses. "
            f"Optionally mention you can create a full travel plan if relevant.\n\n"
            f"3. TRAVEL_ADVICE → User wants destination RECOMMENDATIONS (where to go). "
            f"Suggest 2-3 specific destinations with:\n"
            f"   • Why it's perfect for them\n"
            f"   • Top 3-5 NAMED attractions\n"
            f"   • Best time to visit (specific months)\n"
            f"   • Budget estimate (€ range)\n"
            f"   • Insider tips\n"
            f"   DO NOT include transport/booking details - just recommendations!\n\n"
            f"4. PLAN_REQUEST → Full travel itinerary. Write engaging WHY explanations for:\n"
            f"   • Transport options (flights, trains, buses, driving)\n"
            f"   • Hotels (why each is recommended)\n"
            f"   • Restaurants (cuisine, atmosphere, location)\n"
            f"   • Activities (why they're worth visiting)\n"
            f"   Backend adds structured CARD blocks - you write the narrative!\n\n"
            f"5. SPECIFIC_SEARCH → Category search (restaurants, hotels, etc.). Write 2-3 sentences "
            f"WHY each place is recommended. Backend adds structured data after.\n\n"
            f"CRITICAL RULES:\n"
            f"--------------\n"
            f"• Use ONLY data from TRAVEL_DATA if provided - never invent flight numbers or prices\n"
            f"• NEVER generate [CARD] blocks - backend adds them automatically\n"
            f"• NEVER generate markdown links [text](url) - backend adds all links\n"
            f"• If no data available, say so politely in user's language\n"
            f"• Be helpful, friendly, and specific - avoid generic phrases\n"
            f"• Every word must be in {lang_name.upper()} language!"
        )

    def _build_intent_prompt(self, language_tag: str) -> str:
        return (
            f"You classify intents for MOBIX Travel. The user may speak {language_tag}, but your reply MUST be one of these uppercase English tokens: "
            "QUESTION_ONLY, TRAVEL_ADVICE, PLAN_REQUEST, SPECIFIC_SEARCH."
            "QUESTION_ONLY = small talk or factual Q&A. "
            "TRAVEL_ADVICE = the user wants inspiration or destination ideas but not a full plan. "
            "PLAN_REQUEST = an explicit request to build an itinerary or organize the trip. "
            "SPECIFIC_SEARCH = a targeted list (restaurants, clubs, cafes, etc.). "
            "Respond with ONLY the chosen token."
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        language_tag: str,
        language_code: str = "en",
        temperature: float = 0.7,
        max_tokens: int = 1800,
    ) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": self._build_system_prompt(language_tag, language_code)}] + messages,
        }

        if not self.enabled:
            return self._fallback_chat(messages, language_tag, language_code)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.endpoint, json=payload, headers=self._build_headers())
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError:
            return self._fallback_chat(messages, language_tag, language_code)

    async def classify_intent(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        language_tag: str = "ENGLISH (EN)",
    ) -> str:
        """Zero-shot classifier using OpenAI."""
        if not history:
            history = []
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": self._build_intent_prompt(language_tag),
            }
        ]
        messages.extend(history[-4:])
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 5,
            "messages": messages,
        }
        if not self.enabled:
            return self._fallback_intent(message)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.endpoint, json=payload, headers=self._build_headers())
                response.raise_for_status()
                data = response.json()
                intent = data["choices"][0]["message"]["content"].strip().upper()
                if intent not in {"QUESTION_ONLY", "TRAVEL_ADVICE", "PLAN_REQUEST", "SPECIFIC_SEARCH"}:
                    return "QUESTION_ONLY"
                return intent
        except httpx.HTTPError:
            return self._fallback_intent(message)

    async def extract_travel_locations(
        self,
        message: str,
        language_tag: str = "ENGLISH (EN)",
    ) -> Dict[str, Optional[str]]:
        """Extract origin and destination cities from complex travel queries using GPT."""
        prompt = (
            f"Extract ONLY the origin city and destination city from this travel query. "
            f"User language: {language_tag}. "
            f"Return JSON format: {{\"origin\": \"City Name\", \"destination\": \"City Name\"}}. "
            f"If origin is not mentioned, set to null. If destination is not mentioned, set to null. "
            f"CRITICAL: If city name includes island/region info (e.g., 'Omišlja na otoku Krku'), keep FULL name including island. "
            f"DO NOT shorten to similar-sounding cities. Omišalj (Krk island) ≠ Omiš (Dalmatia)!\n"
            f"Examples:\n"
            f"'Želim otputovati iz Omišlja na otoku Krku u Atenu' → {{\"origin\": \"Omišalj, otok Krk\", \"destination\": \"Athens\"}}\n"
            f"'Plan iz Zagreba za London' → {{\"origin\": \"Zagreb\", \"destination\": \"London\"}}\n"
            f"'Iz Rijeke u Pulu' → {{\"origin\": \"Rijeka\", \"destination\": \"Pula\"}}\n"
            f"'Koliko košta let za Pariz?' → {{\"origin\": null, \"destination\": \"Paris\"}}\n"
            f"'Kamo na skijanje?' → {{\"origin\": null, \"destination\": null}}\n"
            f"\nQuery: '{message}'\n"
            f"Return ONLY the JSON, no other text."
        )
        
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if not self.enabled:
            return {"origin": None, "destination": None}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self.endpoint, json=payload, headers=self._build_headers())
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Parse JSON response
                import json
                result = json.loads(content)
                return {
                    "origin": result.get("origin"),
                    "destination": result.get("destination")
                }
        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            return {"origin": None, "destination": None}

    def _fallback_intent(self, message: str) -> str:
        text = (message or "").strip()
        if not text:
            return "QUESTION_ONLY"

        lowered = text.lower()
        if _looks_like_greeting(lowered):
            return "GREETING"

        detection: Dict[str, Any] = {}
        if ultimate_detect and _has_route_hint(lowered):
            try:
                detection = ultimate_detect(text) or {}
            except Exception:
                detection = {}

        dates = detection.get("dates") or {}
        has_departure = bool(dates.get("departure"))
        has_return = bool(dates.get("return"))
        origin = detection.get("origin")
        destination = detection.get("destination")
        route_ready = bool(origin and destination)
        has_city_signal = bool(origin or destination)
        detector_travel = bool(detection.get("is_travel"))

        tokens = [token for token in re.split(r"\s+", text) if token]
        word_count = len(tokens)
        has_question = "?" in text
        list_layout = bool(re.search(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])", text))
        segmented = list_layout or text.count("\n") > 0
        punctuation_density = sum(text.count(ch) for ch in ",;/|") / max(len(text), 1)
        uppercase_ratio = sum(1 for token in tokens if token.isupper() and len(token) > 1) / max(word_count, 1)

        travel_hint = _has_travel_hint(lowered)
        plan_hint = _has_plan_hint(lowered)

        # 1) Route detection beats everything
        if route_ready:
            return "PLAN_REQUEST"
        if has_city_signal and (plan_hint or travel_hint):
            return "PLAN_REQUEST"
        if plan_hint and (travel_hint or word_count > 25):
            return "PLAN_REQUEST"

        # 2) Travel intent (advice) before fallback
        if travel_hint or detector_travel or has_departure or has_return:
            return "TRAVEL_ADVICE"

        # 3) Specific search formatting signals
        if list_layout or (punctuation_density > 0.08 and word_count < 120) or uppercase_ratio > 0.25:
            return "SPECIFIC_SEARCH"

        # 4) Questions / small talk
        if has_question or word_count < 18:
            return "QUESTION_ONLY"

        if segmented:
            return "TRAVEL_ADVICE"

        return "QUESTION_ONLY"

    def _fallback_chat(self, messages: List[Dict[str, str]], language_tag: str, language_code: str) -> str:
        intent, bundle, user_text = self._extract_metadata(messages)
        lang_code = (language_code or "").strip() or self._language_code(language_tag)
        if intent == "PLAN_REQUEST":
            return self._plan_summary(lang_code, bundle)
        if intent == "GREETING":
            return get_greeting_text(lang_code or "en")
        return self._question_summary(lang_code, user_text)

    def _extract_metadata(self, messages: List[Dict[str, str]]) -> Tuple[str, Optional[Dict[str, Any]], str]:
        intent = "QUESTION_ONLY"
        travel_bundle = None
        for msg in messages:
            if msg["role"] != "system":
                continue
            content = msg.get("content", "")
            if content.startswith("INTENT:"):
                intent = content.split(":", 1)[1].strip().upper()
            elif content.startswith("TRAVEL_DATA:"):
                data = content.split(":", 1)[1].strip()
                try:
                    travel_bundle = json.loads(data)
                except json.JSONDecodeError:
                    travel_bundle = None
        user_text = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_text = msg.get("content", "").strip()
                break
        return intent, travel_bundle, user_text

    def _language_code(self, language_tag: str) -> str:
        mapping = {
            "CROATIAN": "hr",
            "SLOVENIAN": "sl",
            "GERMAN": "de",
            "ITALIAN": "it",
            "SPANISH": "es",
            "FRENCH": "fr",
        }
        for token, code in mapping.items():
            if language_tag.upper().startswith(token):
                return code
        return "en"

    def _plan_summary(self, language_code: str, bundle: Optional[Dict[str, Any]]) -> str:
        origin = ((bundle or {}).get("origin") or "tvoje polazište").title()
        destination = ((bundle or {}).get("destination") or "odabranu destinaciju").title()
        templates = {
            "hr": f"Pripremio sam pregled puta iz {origin} prema {destination}. U nastavku ćeš vidjeti detaljan itinerar i kartice spremne za MOBIX Planner.",
            "sl": f"Pripravil sem pregled poti iz {origin} do {destination}. V nadaljevanju te čaka celoten načrt in kartice za MOBIX Planner.",
            "de": f"Ich habe eine Übersicht für die Reise von {origin} nach {destination} zusammengestellt. Unten findest du den detaillierten Plan und die Karten für deinen MOBIX Planner.",
            "it": f"Ho preparato una panoramica del viaggio da {origin} a {destination}. Qui sotto troverai l’itinerario dettagliato e le card pronte per il tuo MOBIX Planner.",
            "es": f"Ya tengo un resumen del viaje de {origin} a {destination}. Revisa debajo el itinerario completo y las tarjetas listas para tu MOBIX Planner.",
            "fr": f"J’ai préparé un aperçu du trajet de {origin} vers {destination}. Tu verras ensuite l’itinéraire détaillé et les cartes prêtes pour ton MOBIX Planner.",
            "en": f"Here’s a concise briefing for the trip from {origin} to {destination}. Below you’ll find the detailed itinerary plus cards ready for your MOBIX Travel Planner.",
        }
        return templates.get(language_code, templates["en"])

    def _question_summary(self, language_code: str, user_text: str) -> str:
        cleaned = (user_text or "").strip()
        lang_code = language_code or "en"

        # Check for simple greeting (pure greetings only)
        if _looks_like_greeting(cleaned):
            return get_greeting_text(lang_code)
        if not cleaned:
            cleaned = "tvoje pitanje"
        templates = {
            "hr": f"Evo brzog savjeta za \"{cleaned}\": fokusiraj se na jedan ili dva grada, kombiniraj lokalnu hranu i znamenitosti pa mi reci želiš li detaljniji plan.",
            "sl": f"Hiter namig za \"{cleaned}\": izberi osrednjo destinacijo, združi kulinariko in znamenitosti ter mi sporoči, če želiš celoten načrt.",
            "de": f"Kurzer Tipp zu \"{cleaned}\": konzentriere dich auf ein harmonisches Städte-Duo, plane Kulinarik und Highlights und sag mir, wenn du einen detaillierten Plan brauchst.",
            "it": f"Suggerimento rapido per \"{cleaned}\": scegli un quartiere come base, alterna cucina locale e attrazioni e dimmi se vuoi che lo trasformi in un itinerario completo.",
            "es": f"Consejo rápido para \"{cleaned}\": elige una base, combina gastronomía local con imprescindibles y dime si quieres que lo convierta en un plan completo.",
            "fr": f"Astuce express pour \"{cleaned}\": choisis une base, mélange gastronomie et activités, puis dis-moi si tu veux un plan structuré.",
            "en": f"Quick idea for \"{cleaned}\": pick a base city, weave in food plus must-sees, and let me know if you’d like me to expand it into a full plan.",
        }
        return templates.get(lang_code, templates["en"])
