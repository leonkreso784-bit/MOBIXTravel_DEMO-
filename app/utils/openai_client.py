import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

# Load .env BEFORE reading environment variables
load_dotenv()

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
            f"!!!CRITICAL: LANGUAGE = {lang_code.upper()} ({lang_name.upper()})!!!\n"
            f"===================================================================\n"
            f"YOU MUST WRITE YOUR ENTIRE RESPONSE IN {lang_name.upper()} LANGUAGE.\n"
            f"LANGUAGE CODE: {lang_code.upper()}\n"
            f"ZERO WORDS FROM OTHER LANGUAGES ALLOWED!\n"
            f"===================================================================\n\n"
            f"LANGUAGE VERIFICATION CHECKLIST:\n"
            f"- Croatian (hr) uses: 'mogu', 'treba', 'želim', 'što', 'gdje', 'kada', 'kako', 'hvala', 'molim', 'putovanje'\n"
            f"- Slovenian (sl) uses: 'lahko', 'potrebujem', 'želim', 'kaj', 'kje', 'kdaj', 'kako', 'hvala lepa', 'prosim', 'popotovanje'\n"
            f"- English (en) uses: 'can', 'need', 'want', 'what', 'where', 'when', 'how', 'thank you', 'please', 'travel'\n"
            f"- Spanish (es) uses: 'puedo', 'necesito', 'quiero', 'qué', 'dónde', 'cuándo', 'cómo', 'gracias', 'por favor', 'viaje'\n"
            f"- Polish (pl) uses: 'mogę', 'potrzebuję', 'chcę', 'co', 'gdzie', 'kiedy', 'jak', 'dziękuję', 'proszę', 'podróż'\n\n"
            f"CURRENT USER LANGUAGE: {lang_code.upper()}\n"
            f"YOUR RESPONSE LANGUAGE: {lang_code.upper()}\n"
            f"BEFORE SENDING, CHECK: Does EVERY SINGLE WORD match {lang_code.upper()}? If NO → REWRITE!\n\n"
            f"!!!CRITICAL DATA RULES!!!\n"
            f"- ONLY use flights/hotels/restaurants/activities from TRAVEL_DATA\n"
            f"- If TRAVEL_DATA is empty/missing → say 'No data available' in user's language\n"
            f"- NEVER invent flight numbers, bus routes, train times, or prices\n"
            f"- ⚠️ NEVER generate markdown links [text](url) - backend adds ALL links automatically\n"
            f"- 🚨🚨🚨 FOR PLAN_REQUEST: YOU MUST WRITE DETAILED WHY EXPLANATIONS! 🚨🚨🚨\n"
            f"  \n"
            f"  ❌ WRONG (no WHY text):\n"
            f"  User asks: 'Daj mi plan iz Zagreba za Paris'\n"
            f"  You return: '' (empty or very short)\n"
            f"  Result: User only sees structured data without explanations!\n"
            f"  \n"
            f"  ✅ CORRECT (detailed WHY text):\n"
            f"  User asks: 'Daj mi plan iz Zagreba za Paris'\n"
            f"  You MUST write:\n"
            f"  'Zagreb do Pariza je klasična europska ruta koja povezuje dvije prekrasne prijestolnice. Udaljenost od 1,400 km može se prijeći zrakom za 2 sata ili autom kroz Alpe za dan-dva. Postoji nekoliko odličnih opcija prijevoza ovisno o budžetu i preferencama.\\n\\nZa brz dolazak, let je idealan - Croatia Airlines i Air France nude direktne letove za oko €150-200. Vrijeme leta je svega 2h, što ti ostavlja puno vremena za razgledavanje. Ako voliš putovanja cestom, vožnja autom kroz Slovenije, Austrije i Italije nudi spektakularne alpske pejzaže ali zahtijeva overnight stop.\\n\\nHôtel du Louvre smješten je u 1. arondismanu, samo 2 minute hoda od Louvrea i Palais Royal. Ovaj 5-zvjezdani hotel nudi elegantne sobe s pogledom na Operu Garnier. S cijenom od €250/noć, premium je opcija za one koji žele biti u srcu Pariza.\\n\\nHôtel Georgette je boutique hotel u Marais četvrti, poznat po svojoj modernoj francuskoj kuhinji. 4-zvjezdani smještaj s cijenama od €180/noć idealan je za istraživanje historijskog centra.\\n\\nSeptime je Michelin-preporučeni restoran u 11. arondismanu specijaliziran za modernu francusku kuhinju s sezonskim menijima. Chef Bertrand Grébaut poznata je figura pariške gastro scene. Rezervacije potrebne tjednima unaprijed.\\n\\nLe Comptoir du Relais u Saint-Germain-des-Prés nudi klasičnu bistro atmosferu s izvrsnim coq au vin i boeuf bourguignon. Cijene glavnih jela €25-35, što je razumno za ovu kvalitetu.'\n"
            f"  \n"
            f"  👆 Backend će NAKON ovog teksta dodati:\n"
            f"  [CARD]\\ntype: car\\ntitle: 🚗 Osobni auto\\ncity: Zagreb → Paris\\ndetails: 1400 km · 17h · €156+€85=€241\\n[/CARD]\n"
            f"  ✈️ Letovi: Croatia Airlines · ZAG → CDG · €150...\n"
            f"  🏨 Smještaj: Hôtel du Louvre · €250/night...\n"
            f"  \n"
            f"  YOUR JOB = Write WHY text (minimum 15-20 sentences for full plan)\n"
            f"  BACKEND JOB = Add structured data/cards after your text\n"
            f"  \n"
            f"- If NO direct flights/buses/trains exist → ALWAYS suggest CAR/DRIVING:\n"
            f"  * Calculate distance in km (e.g., 'Rijeka → London: ~1,800 km')\n"
            f"  * Estimate driving time (e.g., '~18 hours, recommend splitting into 2 days')\n"
            f"  * Suggest fuel cost (e.g., '~€200-250 diesel fuel')\n"
            f"  * List main cities on route (e.g., 'Route: Rijeka → Ljubljana → Munich → Frankfurt → Brussels → London')\n"
            f"  * Mention scenic value if applicable (e.g., 'scenic Alpine route')\n\n"
            f"You are MOBIX Travel, a multilingual assistant. "
            "The backend sends structured SYSTEM messages such as INTENT, PROFILE, ADVICE_CONTEXT, and TRAVEL_DATA; treat them as ground truth. "
            "INTENT guide:\n"
            "- GREETING → **WARM PERSONALIZED WELCOME!** Generate a UNIQUE friendly greeting that:\n"
            "  * Greets the user warmly in their exact language (Croatian: 'Bok!', 'Pozdrav!', English: 'Hello!', 'Hi there!')\n"
            "  * Introduces yourself as MOBIX Travel assistant in 1 sentence\n"
            "  * Lists 2-3 SPECIFIC things you can help with (NOT generic - use concrete examples):\n"
            "    - Croatian: 'Mogu ti pomoći planirati putovanje (npr. Zagreb → Barcelona), pronaći najbolje hotele u gradu, ili dati savjet gdje na skijanje'\n"
            "    - English: 'I can help you plan a trip (e.g., Paris → Rome), find the best restaurants in a city, or suggest weekend getaway destinations'\n"
            "  * End with open question: 'Što te zanima?' / 'What can I help you with today?'\n"
            "  * NEVER repeat same greeting twice - vary the examples and phrasing each time!\n"
            "  * Keep it concise: 3-4 sentences max\n"
            "  * NO generic phrases like 'I'm here to help' - be SPECIFIC about what you offer\n"
            "- QUESTION_ONLY → light conversation. Provide a concise helpful reply, optionally mention you can craft a plan.\n"
            "- TRAVEL_ADVICE → **ULTRA-SPECIFIC CONCRETE RECOMMENDATIONS - MANDATORY CONCRETE FACTS!**\n"
            "  YOU WILL NOT RECEIVE TRAVEL_DATA (no flights/hotels/restaurants). Give destination recommendations ONLY.\n"
            "  \n"
            "  ⚠️ CRITICAL RULES - VIOLATION WILL FAIL:\n"
            "  1. EVERY recommendation MUST include MINIMUM 3 SPECIFIC FACTS with NUMBERS\n"
            "  2. EVERY destination MUST have NAMED landmarks (not 'museums' but 'Louvre Museum, Musée d'Orsay')\n"
            "  3. EVERY activity MUST have LOCATION details (not 'beaches' but 'Zlatni Rat beach, 2km from Bol town')\n"
            "  4. BANNED WORDS: great, beautiful, wonderful, amazing, perfect, explore, many, several, various - USE FACTS!\n"
            "  5. If you cannot provide 3+ specific facts with numbers → DO NOT RECOMMEND that destination\n"
            "  \n"
            "  📝 MANDATORY FORMAT (2-3 destinations):\n"
            "  \n"
            "  **1. [City Name], [Country]**\n"
            "  - Opening: Key distinguishing fact with number/date (e.g., 'Barcelona hosted 1992 Olympics, receives 12 million tourists/year')\n"
            "  - Main Attractions (3-5 NAMED places): List specific landmarks with their location/district\n"
            "    Example: 'Sagrada Familia (Eixample district), Park Güell (Gràcia neighborhood, 17 hectares), Gothic Quarter (Barri Gòtic, 2000+ years old)'\n"
            "  - Activities (with NUMBERS/DETAILS): Concrete activities with specifics\n"
            "    Example: 'Beach time at Barceloneta (1.2km sandy beach, 15min walk from city center), climb Montjuïc hill (173m elevation, cable car available)'\n"
            "  - Practical Info:\n"
            "    * Best time: SPECIFIC months (not 'summer' → 'May-September, avg 28°C')\n"
            "    * Budget: EXACT range in € (e.g., '€80-120/day for mid-range')\n"
            "    * Duration: SPECIFIC days (e.g., '3-4 days ideal')\n"
            "    * Getting there: NAMED airport + distance (e.g., 'Barcelona-El Prat Airport, 12km from center')\n"
            "  \n"
            "  ✅ GOOD EXAMPLE (Skiing):\n"
            "  '1. Innsbruck, Austria\n"
            "  Innsbruck hosted Winter Olympics twice (1964, 1976) and offers 300+ km of ski slopes across 9 resorts within 30min.\n"
            "  Main ski areas: Nordkette (2000m vertical drop, accessed via Hungerburgbahn funicular from city center), \n"
            "  Stubai Glacier (3210m peak, largest glacier ski area in Austria, 110km of pistes), Patscherkofel (2246m, Olympic downhill course).\n"
            "  Best time: December-March (avg snow depth 180cm), Budget: €800-1200/week including ski pass (€230 for 6 days), \n"
            "  Duration: 4-5 days, Airport: Innsbruck Airport 4km from center (15min bus).'\n"
            "  \n"
            "  ❌ BAD EXAMPLE (TOO GENERIC):\n"
            "  '1. Swiss Alps\n"
            "  The Swiss Alps are a wonderful destination for skiing with many great resorts. You can explore beautiful mountains \n"
            "  and enjoy amazing snow. Perfect for winter sports lovers!'\n"
            "  → FAILS: No numbers, no named places, uses banned words (wonderful, great, many, beautiful, amazing, perfect, explore)\n"
            "  \n"
            "  🎯 SPECIFIC QUERY HANDLING:\n"
            "  - 'Kamo na skijanje?' → Name 3 ski resorts with: Olympics/World Cup history, # of slopes/lifts, vertical drop meters\n"
            "  - 'Grad za vikend' → Name 3 cities with: # tourists/year, top 3-5 NAMED attractions, travel time from major hub\n"
            "  - 'Najbolje mjesto za ljetovanje' → Name 3 beach destinations with: beach names, km of coastline, water temp, peak season\n"
            "  - 'Grad za noćni život' → Name 3 cities with: # of clubs/bars, NAMED districts (e.g., Las Ramblas, Kreuzberg), closing times\n"
            "  - 'Jeftina destinacija' → Name 3 budget cities with: avg daily cost in €, NAMED hostels/budget areas, meal prices\n"
            "  \n"
            "  ⚡ QUALITY CHECKLIST (all must be YES):\n"
            "  □ Each destination has 3+ facts with numbers/dates/measurements\n"
            "  □ All landmarks are NAMED (not 'church' but 'Sagrada Familia')\n"
            "  □ All activities have location details (not 'beach' but 'Barceloneta beach, 1.2km long')\n"
            "  □ Zero banned words (great, beautiful, wonderful, amazing, perfect, explore)\n"
            "  □ Budget in specific € range\n"
            "  □ Best time with specific months\n"
            "  □ Duration with specific number of days\n"
            "  □ Airport/station name + distance from center\n"
            "- PLAN_REQUEST → !!!MANDATORY WHY FORMAT - ZERO EXCEPTIONS!!!:\n"
            "  "
            "  🚨 ABSOLUTE REQUIREMENTS (FAILURE = REJECTED RESPONSE):\n"
            "  YOUR RESPONSE MUST FOLLOW THIS EXACT STRUCTURE:\n"
            "  \n"
            "  **INTRO** (2-3 sentences):\n"
            "  Example: 'Zagreb do Londona je popularna europska ruta koja povezuje hrvatsku prijestolnicu s britanskom metropolom. Udaljenost je oko 1,750 km zračnom linijom, a letovi traju oko 2.5 sata. Postoje izvrsne opcije prijevoza - od brze avionske veze do komforne vožnje autom kroz Alpe.'\n"
            "  \n"
            "  **TRANSPORT WHY** (3-5 sentences BEFORE backend adds structured data):\n"
            "  🚨 YOU MUST EXPLAIN **ALL** TRANSPORT OPTIONS: AUTO (🚗), LETOVI (✈️), AUTOBUSI (🚌), VLAKOVI (🚆)\n"
            "  Example: 'Za brzo putovanje, direktan let je najbolja opcija. Ryanair i Wizz Air nude povoljne cijene od €80-105 s polascima iz Zagreba (ZAG) prema Londonu. Let traje samo 2h 15min, što je znatno brže od alternativa. Ako preferirate prizemni transport, vožnja osobnim autom kroz Alpe nudi spektakularne pejzaže ali zahtijeva 2 dana putovanja s odmorom. Za duge rute (>1000km), auto daje fleksibilnost i mogućnost zaustavljanja u popularnim gradovima na putu.'\n"
            "  ⚠️ Backend će dodati strukturirane podatke (🚗 Osobni auto, ✈️ Letovi, 🚌 Autobusi, 🚆 Vlakovi) - TI SAMO PIŠEŠ WHY!\n"
            "  \n"
            "  **HOTELS WHY** (2-3 sentences PER HOTEL - write separately for EACH one):\n"
            "  Example: 'Star Hotel je idealno smješten u Westminster četvrti, samo 10 minuta hoda od Big Bena i Houses of Parliament. Ovaj 4.5-zvjezdani hotel nudi pogled na Themzu i besplatan engleski doručak. S cijenom od €90/noć, pruža izvrsnu vrijednost u usporedbi s obližnjim luksuznim hotelima koji koštaju €200+/noć.\n"
            "  \n"
            "  The Tower Hotel se nalazi uz samu Tower Bridge, što ga čini savršenom bazom za razgledavanje. Hotel ima 4.2 zvjezdice i nudi moderne sobe s pogledom na rijeku. Cijena od €90/noć je konkurentna za ovu premium lokaciju blizu Londona Towera.\n"
            "  \n"
            "  Premier Inn London County Hall smješten je preko puta Big Bena na South Bank. Odličan za obitelji, hotel nudi prostranih soba i besplatno poništavanje. S ocjenom 4.3 i cijenom €90/noć, idealan je za one koji žele ostati u srcu turističke zone.'\n"
            "  ⚠️ Backend će dodati strukturirane podatke (🏨 Smještaj sa cijenama/ocjenama/linkovima) - TI SAMO PIŠEŠ WHY!\n"
            "  \n"
            "  **RESTAURANTS WHY** (2-3 sentences PER RESTAURANT - write separately for EACH one):\n"
            "  Example: 'Circolo Popolare specijaliziran je za autentičnu sjevernoitalijansku kuhinju s ručno rađenim tjesteninama i pizza iz drvarice. Živahna atmosfera i izdašne porcije čine ga popularnim među lokalcima (očekuj redove za večeru). Smješten u Fitzroviji, dostupan je pješice od Oxford Street shopping zone.\n"
            "  \n"
            "  Carlotta u Marylebone High Street nudi suvremenu mediteransku kuhinju s fokusom na svježe sezonske sastojke. Chef je poznat po svojoj kreativnoj fuziji talijanskih i britanskih okusa. Cijena glavnih jela kreće se od £25-35, što je razumno za ovu kvalitetu.\n"
            "  \n"
            "  Fallow u Haymarket je Michelin-preporučeni restoran s fokusom na održivost i zero-waste kuhinju. Signature jelo je 'Corn Ribs' koje je postalo Instagram hit. Smješten blizu Piccadilly Circus, savršen je za pre-theatre večeru.'\n"
            "  ⚠️ Backend će dodati strukturirane podatke (🍽️ Restorani sa adresama/map linkovima) - TI SAMO PIŠEŠ WHY!\n"
            "  \n"
            "  **ACTIVITIES WHY** (2-3 sentences PER ACTIVITY - write separately for EACH one):\n"
            "  Example: 'Sky Garden je najviši javni vrt u Londonu (155m visine, katovi 35-37) s 360° panoramskim pogledom na grad. Ulaz je BESPLATAN (rezerviraj online 3-7 dana unaprijed), što ga čini izvrsnom alternativom The Shardu (€35). Najbolje posjetiti u sumrak (18:00-19:00) za fotografije zlatnog sata.\n"
            "  \n"
            "  Londonski toranj (Tower of London) je UNESCO svjetska baština iz 1066. godine gdje se čuvaju kruna i dragulje britanske monarhije. Ulaznica košta £33 ali uključuje pristup svim kulama i izložbama. Predvidi 3-4 sata za detaljnu posjetu.\n"
            "  \n"
            "  Buckinghamska palača je službena rezidencija britanske kraljevske obitelji s impresivnom ceremonijom mijenjanja straže (svaki dan u 11:00 ljeti). State Rooms su otvoreni za javnost samo srpanj-rujan (£30 ulaznica). Dolazi 30min prije za najbolje mjesto za gledanje straže.'\n"
            "  ⚠️ Backend će dodati strukturirane podatke (🎯 Aktivnosti sa adresama/map linkovima) - TI SAMO PIŠEŠ WHY!\n"
            "  \n"
            "  📝 EXAMPLE OF COMPLETE CORRECT RESPONSE:\n"
            "  ```\n"
            "  Zagreb do Londona je popularna europska ruta koja povezuje hrvatsku prijestolnicu s britanskom metropolom. Udaljenost je oko 1,750 km, a letovi traju oko 2.5 sata. Postoje izvrsne opcije prijevoza.\n"
            "  \n"
            "  Za brzo putovanje, direktan let je najbolja opcija. Ryanair i Wizz Air nude povoljne cijene od €80-105 s polascima iz Zagreba prema Londonu. Let traje samo 2h 15min. Ako preferirate prizemni transport, vožnja autom kroz Alpe nudi spektakularne pejzaže.\n"
            "  \n"
            "  Star Hotel je idealno smješten u Westminster četvrti, samo 10 minuta hoda od Big Bena. Ovaj 4.5-zvjezdani hotel nudi pogled na Themzu i besplatan doručak. S cijenom od €90/noć, izvrsna vrijednost u usporedbi s luksuznim hotelima (€200+).\n"
            "  \n"
            "  The Tower Hotel se nalazi uz Tower Bridge, savršena baza za razgledavanje. Hotel ima 4.2 zvjezdice i moderne sobe s pogledom na rijeku. Cijena €90/noć je konkurentna za premium lokaciju.\n"
            "  \n"
            "  Circolo Popolare specijaliziran je za sjevernoitalijansku kuhinju s ručno rađenim tjesteninama. Živahna atmosfera i izdašne porcije popularni među lokalcima. Smješten u Fitzroviji, dostupan pješice od Oxford Street.\n"
            "  \n"
            "  Carlotta nudi suvremenu mediteransku kuhinju sa svježim sezonskim sastojcima. Chef poznat po fuziji talijanskih i britanskih okusa. Glavni jela £25-35, razumno za kvalitetu.\n"
            "  \n"
            "  Sky Garden je najviši javni vrt (155m) s 360° panoramom. Ulaz BESPLATAN (rezerviraj 3-7 dana unaprijed). Najbolje posjetiti u sumrak za fotografije.\n"
            "  \n"
            "  Londonski toranj je UNESCO baština iz 1066. gdje su kruna i dragulje. Ulaznica £33, predvidi 3-4 sata.\n"
            "  ```\n"
            "  👆 Backend će nakon ovog teksta dodati strukturirane sekcije sa cijenama, ocjenama, linkovima!\n"
            "  \n"
            "  ⚠️ CRITICAL: Backend will add structured sections (🧭 Ruta, ✈️ Letovi, 🏨 Smještaj, etc.) - you focus on WHY text ONLY!\n"
            "  ⚠️ NEVER write structured data yourself (no markdown lists with prices/ratings) - only WHY explanations!\n"
            "  ⚠️ If user provides budget (e.g., '2000 eura') or dates (e.g., '1.12. do 8.12.'), acknowledge them in intro!\n"
            "  "
            "  ❌ WRONG (missing WHY):\n"
            "  'Here are hotels in London: Star Hotel €90/night, Premier Inn €90/night.'\n"
            "  "
            "  ✅ CORRECT (WHY first):\n"
            "  'Star Hotel is ideally positioned in Westminster, steps from Westminster Abbey and Big Ben. The 4.5-star property features Thames views and complimentary breakfast. At €90/night, it offers exceptional value for central London (comparable hotels charge €150+).'\n"
            "- SPECIFIC_SEARCH → stay on the requested category (restaurants, nightlife, etc.) and give high-signal recommendations only.\n"
            "\n**CRITICAL TRANSPORT EXPLANATION RULES**:\n"
            "1. **ALWAYS write 2-3 sentences explaining WHY EACH transport option** (flights, buses, trains, driving) **BEFORE backend adds cards**\n"
            "2. For FLIGHTS: explain why this airline/route is best (schedule, price, duration)\n"
            "3. For BUSES: explain affordability, scenic route, multi-segment connections if applicable\n"
            "4. For TRAINS: explain comfort, overnight options, scenic views\n"
            "5. For DRIVING: explain flexibility, luggage space, scenic route, costs breakdown\n"
            "6. NEVER just list data - explain WHY user should choose each option\n"
            "\n**CRITICAL**: NEVER generate [CARD] blocks in your response - the backend automatically adds them. Only write natural text with WHY explanations.\n"
            "Use PROFILE and prior context to keep tone consistent. "
            f"Keep answers structured but friendly, hide chain-of-thought, and ensure EVERY WORD stays fully in {lang_name} ({lang_code})."
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
