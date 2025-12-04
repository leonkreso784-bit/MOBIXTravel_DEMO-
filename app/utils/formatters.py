from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

try:
    from travel_planner import normalize_croatian_city, resolve_primary_airport_city, get_airport_code  # type: ignore
except Exception:
    # Fallback implementations if travel_planner not available
    def normalize_croatian_city(city: str) -> str:  # type: ignore
        return city.strip().title()
    
    def resolve_primary_airport_city(city: str) -> str:  # type: ignore
        return city.strip().title()
    
    def get_airport_code(city: str) -> Optional[str]:  # type: ignore
        return None

from .cards import cards_from_places


def _format_flight_time(iso_time: str) -> str:
    """Format ISO datetime to readable format: 'Dec 7, 18:40'"""
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %H:%M")
    except:
        return iso_time


PLAN_LABELS: Dict[str, Dict[str, str]] = {
    "en": {"route": "Route", "budget": "Budget", "dates": "Dates", "preferences": "Preferences", "ground": "Getting there", "flights": "Flights", "buses": "Buses", "trains": "Trains", "hotels": "Hotels", "restaurants": "Restaurants", "activities": "Activities", "links": "Useful links", "unknown": "your city"},
    "hr": {"route": "Ruta", "budget": "Budžet", "dates": "Datumi", "preferences": "Preferencije", "ground": "Polazak", "flights": "Letovi", "buses": "Autobusi", "trains": "Vlakovi", "hotels": "Smještaj", "restaurants": "Restorani", "activities": "Aktivnosti", "links": "Korisni linkovi", "unknown": "tvoj grad"},
    "sl": {"route": "Relacija", "budget": "Proračun", "dates": "Datumi", "preferences": "Preference", "ground": "Odhod", "flights": "Leti", "buses": "Avtobusi", "trains": "Vlaki", "hotels": "Namestitev", "restaurants": "Restavracije", "activities": "Aktivnosti", "links": "Uporabne povezave", "unknown": "tvoje mesto"},
    "de": {"route": "Route", "budget": "Budget", "dates": "Daten", "preferences": "Vorlieben", "ground": "Anreise", "flights": "Flüge", "buses": "Busse", "trains": "Züge", "hotels": "Unterkünfte", "restaurants": "Restaurants", "activities": "Aktivitäten", "links": "Nützliche Links", "unknown": "deine Stadt"},
    "it": {"route": "Percorso", "budget": "Budget", "dates": "Date", "preferences": "Preferenze", "ground": "Partenza", "flights": "Voli", "buses": "Autobus", "trains": "Treni", "hotels": "Alloggi", "restaurants": "Ristoranti", "activities": "Attività", "links": "Link utili", "unknown": "la tua città"},
    "es": {"route": "Ruta", "budget": "Presupuesto", "dates": "Fechas", "preferences": "Preferencias", "ground": "Salida", "flights": "Vuelos", "buses": "Autobuses", "trains": "Trenes", "hotels": "Alojamientos", "restaurants": "Restaurantes", "activities": "Actividades", "links": "Enlaces útiles", "unknown": "tu ciudad"},
    "fr": {"route": "Trajet", "budget": "Budget", "dates": "Dates", "preferences": "Préférences", "ground": "Départ", "flights": "Vols", "buses": "Bus", "trains": "Trains", "hotels": "Hébergements", "restaurants": "Restaurants", "activities": "Activités", "links": "Liens utiles", "unknown": "votre ville"},
}

SECTION_LABELS: Dict[str, Dict[str, str]] = {
    "en": {
        "route": "🧭 Route",
        "flights": "✈️ Flights",
        "buses": "🚌 Buses",
        "trains": "🚆 Trains",
        "accommodation": "🏨 Accommodation",
        "restaurants": "🍽️ Restaurants",
        "activities": "🎯 Activities",
        "links": "🔗 Useful links",
    },
    "hr": {
        "route": "🧭 Ruta",
        "flights": "✈️ Letovi",
        "buses": "🚌 Autobusi",
        "trains": "🚆 Vlakovi",
        "accommodation": "🏨 Smještaj",
        "restaurants": "🍽️ Restorani",
        "activities": "🎯 Aktivnosti",
        "links": "🔗 Korisni linkovi",
    },
    "sl": {
        "route": "🧭 Relacija",
        "flights": "✈️ Leti",
        "buses": "🚌 Avtobusi",
        "trains": "🚆 Vlaki",
        "accommodation": "🏨 Nastanitev",
        "restaurants": "🍽️ Restavracije",
        "activities": "🎯 Aktivnosti",
        "links": "🔗 Uporabne povezave",
    },
    "de": {
        "route": "🧭 Route",
        "flights": "✈️ Flüge",
        "buses": "🚌 Busse",
        "trains": "🚆 Züge",
        "accommodation": "🏨 Unterkünfte",
        "restaurants": "🍽️ Restaurants",
        "activities": "🎯 Aktivitäten",
        "links": "🔗 Nützliche Links",
    },
    "it": {
        "route": "🧭 Percorso",
        "flights": "✈️ Voli",
        "buses": "🚌 Autobus",
        "trains": "🚆 Treni",
        "accommodation": "🏨 Alloggi",
        "restaurants": "🍽️ Ristoranti",
        "activities": "🎯 Attività",
        "links": "🔗 Link utili",
    },
    "es": {
        "route": "🧭 Ruta",
        "flights": "✈️ Vuelos",
        "buses": "🚌 Autobuses",
        "trains": "🚆 Trenes",
        "accommodation": "🏨 Alojamiento",
        "restaurants": "🍽️ Restaurantes",
        "activities": "🎯 Actividades",
        "links": "🔗 Enlaces útiles",
    },
    "fr": {
        "route": "🧭 Trajet",
        "flights": "✈️ Vols",
        "buses": "🚌 Bus",
        "trains": "🚆 Trains",
        "accommodation": "🏨 Hébergements",
        "restaurants": "🍽️ Restaurants",
        "activities": "🎯 Activités",
        "links": "🔗 Liens utiles",
    },
}

EMPTY_SECTION_TEXT: Dict[str, Dict[str, str]] = {
    "en": {
        "flights": "No flights found yet. Use the links below for live options.",
        "buses": "No direct buses detected. Check Rome2Rio for current schedules.",
        "trains": "No trains were generated for this leg. Combine with Rome2Rio if needed.",
        "accommodation": "No accommodation picks yet—Booking and Airbnb links are ready below.",
        "restaurants": "No restaurants surfaced. Browse local spots via Maps when you arrive.",
        "activities": "No specific activities listed yet. Use local tips or Google for inspiration.",
    },
    "hr": {
        "flights": "Još nema letova – provjeri linkove ispod za aktualne opcije.",
        "buses": "Nema izravnih autobusa. Pogledaj Rome2Rio za rasporede.",
        "trains": "Nisu pronađeni vlakovi za ovu relaciju. Kombiniraj s Rome2Rio ako trebaš.",
        "accommodation": "Smještaj nije odabran – Booking i Airbnb linkovi su spremni ispod.",
        "restaurants": "Restorani nisu istaknuti. Pretraži lokalnu ponudu kad stigneš.",
        "activities": "Aktivnosti još nisu izdvojene. Potraži ideje kroz karte i blogove.",
    },
    "sl": {
        "flights": "Ni najdenih letov – preveri spodnje povezave.",
        "buses": "Ni neposrednih avtobusov. Poglej Rome2Rio za vozne rede.",
        "trains": "Vlakov za to relacijo ni, kombiniraj z Rome2Rio.",
        "accommodation": "Nastanitev ni izbrana – Booking in Airbnb povezave so spodaj.",
        "restaurants": "Restavracije niso izpostavljene. Razišči lokalne predloge na kraju.",
        "activities": "Aktivnosti trenutno manjkajo. Uporabi lokalne nasvete ali Google.",
    },
    "de": {
        "flights": "Keine Flüge gefunden – nutze die Links unten für Live-Angebote.",
        "buses": "Keine direkten Busse entdeckt. Sieh dir Rome2Rio an.",
        "trains": "Keine Züge generiert. Kombiniere die Reise mit Rome2Rio.",
        "accommodation": "Noch keine Unterkünfte – Booking und Airbnb stehen bereit.",
        "restaurants": "Keine Restaurants gelistet. Schau vor Ort nach Empfehlungen.",
        "activities": "Keine Aktivitäten aufgeführt. Nutze lokale Tipps oder Google.",
    },
    "it": {
        "flights": "Nessun volo trovato: usa i link qui sotto.",
        "buses": "Nessun autobus diretto. Controlla Rome2Rio per gli orari.",
        "trains": "Nessun treno generato. Combina con Rome2Rio se serve.",
        "accommodation": "Nessun alloggio selezionato: Booking e Airbnb sono pronti sotto.",
        "restaurants": "Nessun ristorante evidenziato. Scopri i locali una volta arrivato.",
        "activities": "Nessuna attività elencata. Usa blog o consigli locali.",
    },
    "es": {
        "flights": "No se encontraron vuelos. Usa los enlaces inferiores.",
        "buses": "No hay buses directos. Revisa Rome2Rio para horarios.",
        "trains": "No se generaron trenes. Combina con Rome2Rio si es necesario.",
        "accommodation": "Sin alojamientos destacados: Booking y Airbnb están abajo.",
        "restaurants": "No aparecieron restaurantes. Busca opciones al llegar.",
        "activities": "No hay actividades listadas aún. Inspírate con guías o Google.",
    },
    "fr": {
        "flights": "Aucun vol trouvé pour l’instant. Utilise les liens ci-dessous.",
        "buses": "Pas de bus directs. Consulte Rome2Rio pour les horaires.",
        "trains": "Aucun train généré. Combine avec Rome2Rio si besoin.",
        "accommodation": "Pas d’hébergement sélectionné – Booking et Airbnb t’attendent plus bas.",
        "restaurants": "Aucun restaurant listé. Découvre les adresses sur place.",
        "activities": "Pas d’activités mentionnées pour l’instant. Inspire-toi via des blogs ou Google.",
    },
}


def _language_key(language_code: str) -> str:
    return (language_code or "en").split("-")[0][:2].lower()


def _label(language_code: str, key: str) -> str:
    lang = _language_key(language_code)
    mapping = PLAN_LABELS.get(lang, PLAN_LABELS["en"])
    return mapping.get(key, PLAN_LABELS["en"].get(key, key))


def _section_label(language_code: str, key: str) -> str:
    lang = _language_key(language_code)
    mapping = SECTION_LABELS.get(lang, SECTION_LABELS["en"])
    return mapping.get(key, SECTION_LABELS["en"].get(key, key.title()))


def _empty_section_text(language_code: str, key: str) -> str:
    lang = _language_key(language_code)
    mapping = EMPTY_SECTION_TEXT.get(lang, EMPTY_SECTION_TEXT["en"])
    return mapping.get(key, EMPTY_SECTION_TEXT["en"].get(key, "No data yet."))


def format_link(icon: str, label: str, url: Optional[str]) -> str:
    if not url:
        return ""
    clean_label = label.strip()
    if clean_label.startswith(icon):
        clean_label = clean_label[len(icon):].strip()
    return f"[{icon} {clean_label}]({url})"


def _get_link_text(key: str, language_code: str, **kwargs) -> str:
    lang_key = (language_code or "en").lower()[:2]
    templates = {
        "book_flight": {
            "hr": lambda airline: f"Rezerviraj {airline} let",
            "en": lambda airline: f"Book {airline} flight",
            "de": lambda airline: f"Buche {airline} Flug",
            "it": lambda airline: f"Prenota volo {airline}",
            "es": lambda airline: f"Reservar vuelo {airline}",
            "fr": lambda airline: f"Réserver vol {airline}",
            "sl": lambda airline: f"Rezerviraj let {airline}",
        },
        "buy_ticket": {
            "hr": lambda company: f"Kupi kartu ({company})",
            "en": lambda company: f"Buy ticket ({company})",
            "de": lambda company: f"Ticket kaufen ({company})",
            "it": lambda company: f"Acquista biglietto ({company})",
            "es": lambda company: f"Comprar billete ({company})",
            "fr": lambda company: f"Acheter billet ({company})",
            "sl": lambda company: f"Kupi vozovnico ({company})",
        },
        "trains": {
            "hr": lambda origin, dest: f"Vlakovi {origin} → {dest}",
            "en": lambda origin, dest: f"Trains {origin} → {dest}",
            "de": lambda origin, dest: f"Züge {origin} → {dest}",
            "it": lambda origin, dest: f"Treni {origin} → {dest}",
            "es": lambda origin, dest: f"Trenes {origin} → {dest}",
            "fr": lambda origin, dest: f"Trains {origin} → {dest}",
            "sl": lambda origin, dest: f"Vlaki {origin} → {dest}",
        },
        "book_accommodation": {
            "hr": lambda name: f"Rezerviraj smještaj ({name})",
            "en": lambda name: f"Book accommodation ({name})",
            "de": lambda name: f"Unterkunft buchen ({name})",
            "it": lambda name: f"Prenota alloggio ({name})",
            "es": lambda name: f"Reservar alojamiento ({name})",
            "fr": lambda name: f"Réserver hébergement ({name})",
            "sl": lambda name: f"Rezerviraj namestitev ({name})",
        },
        "google_flights": {
            "hr": lambda codes: f"Google Flights ({codes})",
            "en": lambda codes: f"Google Flights ({codes})",
            "de": lambda codes: f"Google Flüge ({codes})",
            "it": lambda codes: f"Google Voli ({codes})",
            "es": lambda codes: f"Google Vuelos ({codes})",
            "fr": lambda codes: f"Google Vols ({codes})",
            "sl": lambda codes: f"Google Leti ({codes})",
        },
        "airbnb": {
            "hr": lambda dest: f"Airbnb u {dest}",
            "en": lambda dest: f"Airbnb in {dest}",
            "de": lambda dest: f"Airbnb in {dest}",
            "it": lambda dest: f"Airbnb a {dest}",
            "es": lambda dest: f"Airbnb en {dest}",
            "fr": lambda dest: f"Airbnb à {dest}",
            "sl": lambda dest: f"Airbnb v {dest}",
        },
    }
    template_dict = templates.get(key, {})
    template_fn = template_dict.get(lang_key, template_dict.get("en"))
    if template_fn:
        return template_fn(**kwargs)
    return str(kwargs.get(next(iter(kwargs)), "")) if kwargs else ""


def _format_preferences(preferences: Optional[List[str]]) -> str:
    if not preferences:
        return ""
    cleaned: List[str] = []
    for pref in preferences:
        if not pref:
            continue
        candidate = pref.replace("_", " ").strip()
        if not candidate:
            continue
        cleaned.append(candidate[:1].upper() + candidate[1:])
    return ", ".join(cleaned)


def _primary_transport_mode(bundle: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    flights = bundle.get("flights") or []
    trains = bundle.get("trains") or []
    buses = bundle.get("buses") or []
    if flights:
        return "flight", flights[0].get("duration") or flights[0].get("return_date")
    if trains:
        return "train", trains[0].get("duration")
    if buses:
        return "bus", buses[0].get("duration")
    return "flex", None


def _build_summary_text(bundle: Dict[str, Any], language_code: str, origin: str, destination: str) -> str:
    mode, duration_hint = _primary_transport_mode(bundle)
    lang = _language_key(language_code)
    mode_sentences = {
        "flight": {
            "en": "We'll lean on a quick flight for the longest stretch so you land fresh.",
            "hr": "Osnovu čini brzi let kako bi stigao odmoran.",
        },
        "train": {
            "en": "A comfortable train ride anchors the itinerary for a scenic arrival.",
            "hr": "U središtu je udobna vožnja vlakom za ugodan dolazak.",
        },
        "bus": {
            "en": "Express buses keep the budget tight while still arriving on time.",
            "hr": "Ekspresni autobusi čuvaju budžet, a dolaziš na vrijeme.",
        },
        "flex": {
            "en": "Pick the transport leg that fits your timing—options are below.",
            "hr": "Odaberi prijevoz koji ti najbolje paše – opcije su ispod.",
        },
    }
    duration_sentences = {
        "en": f"The key leg takes about {duration_hint or 'a comfortable travel day'}, so plan buffers for check-in and transfers.",
        "hr": f"Glavna dionica traje oko {duration_hint or 'jednog putnog dana'}, zato ostavi malo rezerve za prijavu i transfere.",
    }
    closing_sentences = {
        "en": "You'll get flights, ground transport, stays, food, activities, and useful links in order so you can book immediately.",
        "hr": "U nastavku slijede letovi, kopneni prijevoz, smještaj, hrana, aktivnosti i korisni linkovi da sve brzo rezerviraš.",
    }
    localized_mode = mode_sentences.get(mode, mode_sentences["flex"]).get(lang, mode_sentences[mode]["en"])
    localized_duration = duration_sentences.get(lang, duration_sentences["en"])
    localized_closing = closing_sentences.get(lang, closing_sentences["en"])
    opening = {
        "en": f"Travel plan: {origin.title()} → {destination.title()}.",
        "hr": f"Plan putovanja: {origin.title()} → {destination.title()}.",
    }.get(lang, f"Travel plan: {origin.title()} → {destination.title()}.")
    sentences = [opening, localized_mode]
    if duration_hint:
        sentences.append(localized_duration)
    sentences.append(localized_closing)
    return " ".join(sentence for sentence in sentences if sentence)


def format_specific_search_response(category_label: str, city: str, places: List[Dict[str, Any]], card_type: str = "poi") -> str:
    """Format places search results into readable text with cards."""
    if not places:
        return f"No {category_label} found in {city}."
        
    lines = [f"Top {category_label} in {city}:", ""]
    for idx, place in enumerate(places, start=1):
        name = place.get('name', 'Unknown')
        rating = place.get("rating")
        address = place.get("address", "")
        line = f"{name}"
        if rating:
            line += f" · ⭐ {rating}"
        lines.append(line)
        if address:
            lines.append(f"{address}")
        maps_url = place.get("maps_url")
        if maps_url:
            maps_link = format_link("📍", "Open in Maps", maps_url)
            if maps_link:
                lines.append(f"{maps_link}")
        lines.append("")
        
    # Generate CARD blocks (backend adds these, not duplicated by GPT)
    cards_block = cards_from_places(card_type, city, places)
    if cards_block:
        lines.extend(["", cards_block])
    return "\n".join(line for line in lines if line is not None).strip()


def build_departure_instructions(bundle: Dict[str, Any], language_code: str = "hr") -> str:
    origin_raw = (bundle.get("origin") or "").strip()
    destination_raw = (bundle.get("destination") or "").strip()
    if not origin_raw or not destination_raw:
        return ""

    origin = normalize_croatian_city(origin_raw)
    destination = normalize_croatian_city(destination_raw)
    origin_city = resolve_primary_airport_city(origin)
    destination_city = resolve_primary_airport_city(destination)
    origin_code = get_airport_code(origin_city)
    lang_key = (language_code or "en").lower()[:2]

    sentences: List[str] = []
    flights = bundle.get("flights") or []
    if flights:
        flight = flights[0]
        dep_date = flight.get("departure_date")
        airline = flight.get("airline")
        duration = flight.get("duration")
        ret_date = flight.get("return_date")

        departure_texts = {
            "hr": f"Kreni iz {origin.title()} prema {origin_city.title()} aerodromu ({origin_code or 'glavni terminal'}) barem 2 sata prije polijetanja {airline} leta {dep_date}.",
            "en": f"Leave from {origin.title()} to {origin_city.title()} airport ({origin_code or 'main terminal'}) at least 2 hours before {airline} flight departure on {dep_date}.",
            "de": f"Fahre von {origin.title()} zum {origin_city.title()} Flughafen ({origin_code or 'Hauptterminal'}) mindestens 2 Stunden vor Abflug des {airline} Fluges am {dep_date}.",
            "it": f"Parti da {origin.title()} per l'aeroporto di {origin_city.title()} ({origin_code or 'terminal principale'}) almeno 2 ore prima della partenza del volo {airline} il {dep_date}.",
            "es": f"Sal de {origin.title()} hacia el aeropuerto de {origin_city.title()} ({origin_code or 'terminal principal'}) al menos 2 horas antes de la salida del vuelo {airline} el {dep_date}.",
            "fr": f"Pars de {origin.title()} vers l'aéroport de {origin_city.title()} ({origin_code or 'terminal principal'}) au moins 2 heures avant le départ du vol {airline} le {dep_date}.",
            "sl": f"Odpelji se iz {origin.title()} proti letališču {origin_city.title()} ({origin_code or 'glavni terminal'}) vsaj 2 uri pred odhodom leta {airline} {dep_date}.",
        }
        sentences.append(departure_texts.get(lang_key, departure_texts["en"]))

        duration_texts = {
            "hr": f"Let traje oko {duration} pa ćeš nakon slijetanja imati dovoljno vremena za transfer do centra {destination.title()}.",
            "en": f"The flight takes about {duration}, giving you enough time after landing for transfer to {destination.title()} center.",
            "de": f"Der Flug dauert etwa {duration}, sodass du nach der Landung genug Zeit für den Transfer ins Zentrum von {destination.title()} hast.",
            "it": f"Il volo dura circa {duration}, dandoti abbastanza tempo dopo l'atterraggio per il trasferimento al centro di {destination.title()}.",
            "es": f"El vuelo dura aproximadamente {duration}, dándote suficiente tiempo después del aterrizaje para el traslado al centro de {destination.title()}.",
            "fr": f"Le vol dure environ {duration}, te donnant assez de temps après l'atterrissage pour le transfert vers le centre de {destination.title()}.",
            "sl": f"Let traja približno {duration}, kar ti po pristanku da dovolj časa za prenos v center {destination.title()}.",
        }
        sentences.append(duration_texts.get(lang_key, duration_texts["en"]))

        if ret_date:
            checkin_texts = {
                "hr": f"Odmah napravi online check-in i zabilježi povratak {ret_date} kako bi kasnije sve prošlo bez stresa.",
                "en": f"Do online check-in right away and note the return date {ret_date} to keep everything stress-free later.",
                "de": f"Mache sofort den Online-Check-in und notiere das Rückflugdatum {ret_date}, damit später alles stressfrei läuft.",
                "it": f"Fai subito il check-in online e annota la data di ritorno {ret_date} per mantenere tutto senza stress in seguito.",
                "es": f"Haz el check-in online de inmediato y anota la fecha de regreso {ret_date} para mantener todo sin estrés más tarde.",
                "fr": f"Fais l'enregistrement en ligne tout de suite et note la date de retour {ret_date} pour que tout se passe sans stress plus tard.",
                "sl": f"Takoj opravi spletno prijavo in zabeleži datum vrnitve {ret_date}, da bo kasneje vse brez stresa.",
            }
            sentences.append(checkin_texts.get(lang_key, checkin_texts["en"]))
    else:
        early_texts = {
            "hr": f"Kreni iz {origin.title()} dovoljno rano da se bez žurbe ukrcaš na prijevoz za {destination.title()}.",
            "en": f"Leave from {origin.title()} early enough to board your transport to {destination.title()} without rushing.",
            "de": f"Fahre früh genug von {origin.title()} ab, um ohne Eile in dein Verkehrsmittel nach {destination.title()} einzusteigen.",
            "it": f"Parti da {origin.title()} abbastanza presto per salire sul tuo mezzo di trasporto per {destination.title()} senza fretta.",
            "es": f"Sal de {origin.title()} con suficiente antelación para abordar tu transporte a {destination.title()} sin prisas.",
            "fr": f"Pars de {origin.title()} assez tôt pour monter dans ton transport vers {destination.title()} sans te presser.",
            "sl": f"Odpelji se iz {origin.title()} dovolj zgodaj, da se brez naglice vkrcaš na prevoz do {destination.title()}.",
        }
        sentences.append(early_texts.get(lang_key, early_texts["en"]))

    buses = bundle.get("buses") or []
    if buses:
        bus = buses[0]
        arrival_value = bus.get("arrival") or destination.title()
        bus_texts = {
            "hr": f"Ako biraš kopneni put, {bus['company']} polazi u {bus['departure']} s glavnog kolodvora i stiže oko {arrival_value} (trajanje {bus.get('duration', '10h')}).",
            "en": f"If you choose the land route, {bus['company']} departs at {bus['departure']} from the main station and arrives around {arrival_value} (duration {bus.get('duration', '10h')}).",
            "de": f"Wenn du die Landroute wählst, fährt {bus['company']} um {bus['departure']} vom Hauptbahnhof ab und kommt gegen {arrival_value} an (Dauer {bus.get('duration', '10h')}).",
            "it": f"Se scegli la via terrestre, {bus['company']} parte alle {bus['departure']} dalla stazione principale e arriva intorno alle {arrival_value} (durata {bus.get('duration', '10h')}).",
            "es": f"Si eliges la ruta terrestre, {bus['company']} sale a las {bus['departure']} de la estación principal y llega alrededor de las {arrival_value} (duración {bus.get('duration', '10h')}).",
            "fr": f"Si tu choisis la voie terrestre, {bus['company']} part à {bus['departure']} de la gare principale et arrive vers {arrival_value} (durée {bus.get('duration', '10h')}).",
            "sl": f"Če izbereš kopensko pot, {bus['company']} odpelje ob {bus['departure']} z glavne postaje in prispe okoli {arrival_value} (trajanje {bus.get('duration', '10h')}).",
        }
        sentences.append(bus_texts.get(lang_key, bus_texts["en"]))

    train_link = bundle.get("links", {}).get("train")
    if train_link:
        train_texts = {
            "hr": "Provjeri i vlakove za kombinaciju noćnog putovanja i jutarnjeg leta ako želiš više fleksibilnosti.",
            "en": "Also check trains for a combination of overnight travel and morning flight if you want more flexibility.",
            "de": "Prüfe auch Züge für eine Kombination aus nächtlicher Reise und Morgenflug, wenn du mehr Flexibilität möchtest.",
            "it": "Controlla anche i treni per una combinazione di viaggio notturno e volo mattutino se vuoi più flessibilità.",
            "es": "También revisa los trenes para una combinación de viaje nocturno y vuelo matutino si quieres más flexibilidad.",
            "fr": "Vérifie aussi les trains pour une combinaison de voyage de nuit et de vol matinal si tu veux plus de flexibilité.",
            "sl": "Preveri tudi vlake za kombinacijo nočnega potovanja in jutranjega leta, če želiš več prožnosti.",
        }
        sentences.append(train_texts.get(lang_key, train_texts["en"]))

    packing_texts = {
        "hr": "Spakiraj dokumente i ograničenja prtljage dan ranije te stigni barem 30 minuta prije ukrcaja.",
        "en": "Pack documents and check baggage restrictions a day early and arrive at least 30 minutes before boarding.",
        "de": "Packe Dokumente und prüfe Gepäckbeschränkungen einen Tag vorher und komme mindestens 30 Minuten vor dem Einstieg an.",
        "it": "Prepara documenti e controlla le restrizioni sui bagagli un giorno prima e arriva almeno 30 minuti prima dell'imbarco.",
        "es": "Empaca documentos y verifica las restricciones de equipaje un día antes y llega al menos 30 minutos antes del embarque.",
        "fr": "Prépare les documents et vérifie les restrictions de bagages un jour à l'avance et arrive au moins 30 minutes avant l'embarquement.",
        "sl": "Spakiraj dokumente in preveri omejitve prtljage dan prej ter prispej vsaj 30 minut pred vkrcanjem.",
    }
    sentences.append(packing_texts.get(lang_key, packing_texts["en"]))

    coffee_texts = {
        "hr": "Uhvati kavu ili grickalicu na terminalu kako bi opušteno ušao u putovanje.",
        "en": "Grab a coffee or snack at the terminal to start your journey relaxed.",
        "de": "Hol dir einen Kaffee oder Snack am Terminal, um entspannt in die Reise zu starten.",
        "it": "Prendi un caffè o uno spuntino al terminal per iniziare il viaggio rilassato.",
        "es": "Toma un café o un bocadillo en la terminal para comenzar tu viaje relajado.",
        "fr": "Prends un café ou une collation au terminal pour commencer ton voyage détendu.",
        "sl": "Vzemi kavo ali prigrizek na terminalu, da sproščeno začneš potovanje.",
    }
    sentences.append(coffee_texts.get(lang_key, coffee_texts["en"]))

    unique_sentences = [s for s in sentences if s]
    if len(unique_sentences) < 4:
        offline_texts = {
            "hr": "Podesi offline karte i provjeri vremensku prognozu za polazak i dolazak.",
            "en": "Set up offline maps and check the weather forecast for departure and arrival.",
            "de": "Richte Offline-Karten ein und prüfe die Wettervorhersage für Abfahrt und Ankunft.",
            "it": "Configura le mappe offline e controlla le previsioni meteo per partenza e arrivo.",
            "es": "Configura mapas sin conexión y verifica el pronóstico del tiempo para la salida y llegada.",
            "fr": "Configure les cartes hors ligne et vérifie les prévisions météo pour le départ et l'arrivée.",
            "sl": "Nastavi karte brez povezave in preveri vremensko napoved za odhod in prihod.",
        }
        unique_sentences.append(offline_texts.get(lang_key, offline_texts["en"]))

    return " ".join(unique_sentences[:6])


def format_travel_plan(bundle: Dict[str, Any], language_code: str) -> str:
    """Format clean structured travel plan with clickable links (NO duplicates - OpenAI provides WHY explanations)"""
    if not bundle:
        return ""

    origin_raw = bundle.get("origin")
    destination_raw = bundle.get("destination")
    origin = normalize_croatian_city(origin_raw or _label(language_code, "unknown"))
    destination = normalize_croatian_city(destination_raw or _label(language_code, "unknown"))
    preferences = _format_preferences(bundle.get("preferences"))
    
    # Check if this is a return trip (transport only, no hotels/activities)
    is_return_trip = bundle.get("is_return_trip", False)

    origin_airport_city = resolve_primary_airport_city(origin_raw or origin)
    destination_airport_city = resolve_primary_airport_city(destination_raw or destination)
    origin_code = get_airport_code(origin_airport_city)
    destination_code = get_airport_code(destination_airport_city)

    flights = bundle.get("flights") or []
    buses = bundle.get("buses") or []
    trains = bundle.get("trains") or []
    driving = bundle.get("driving")
    hotels = bundle.get("hotels") or []
    restaurants = bundle.get("restaurants") or []
    activities = bundle.get("activities") or []
    links_section = bundle.get("links", {})

    lines: List[str] = []
    
    # Basic route info
    lines.append(f"{_section_label(language_code, 'route')}: {origin.title()} → {destination.title()}")
    
    # Optional preferences
    if preferences:
        lines.append("")
        lines.append(f"🎯 {_label(language_code, 'preferences')}: {preferences}")

    # DRIVING - CARD block for planner (if available)
    if driving:
        distance = driving.get("distance_km", "?")
        duration = driving.get("duration", "?")
        fuel_cost = driving.get("fuel_cost", "?")
        toll_cost = driving.get("toll_cost", 0)
        total_cost = driving.get("total_cost", "?")
        maps_link = driving.get("link", "")
        
        # Build CARD block for driving option (NO text description - GPT provides that)
        lines.append("")
        lines.append("[CARD]")
        lines.append("type: car")
        lines.append(f"title: 🚗 Osobni auto")
        lines.append(f"city: {origin.title()} → {destination.title()}")
        lines.append(f"details: {distance} km · {duration} · Gorivo €{fuel_cost} + Cestarina €{toll_cost} = €{total_cost}")
        lines.append(f"link: {maps_link}")
        # Add to planner data
        car_json = json.dumps({
            "type": "transport",
            "mode": "car",
            "route": f"{origin.title()} → {destination.title()}",
            "distance": distance,
            "duration": duration,
            "cost": total_cost,
            "link": maps_link
        })
        lines.append(f"data: {car_json}")
        lines.append("[/CARD]")

    # FLIGHTS - CARD blocks (only show if we have flights!)
    if flights:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'flights')}:")
        for flight in flights[:3]:  # Show top 3 flights
            # Get airports (use departure/arrival airport if available, otherwise use city codes)
            flight_origin = flight.get("departure_airport") or (flight.get("origin") or origin_code or origin_airport_city or origin).upper()
            flight_dest = flight.get("arrival_airport") or (flight.get("destination") or destination_code or destination_airport_city or destination).upper()
            
            airline = flight.get('airline', 'Flight')
            price = flight.get('price', '?')
            duration = flight.get('duration', '?')
            stops = flight.get('stops', 0)
            
            # Format times nicely
            departure_time = flight.get('departure_time', '')
            arrival_time = flight.get('arrival_time', '')
            
            if departure_time and arrival_time:
                # Format as "Dec 7 18:40 → Dec 8 09:10"
                dep_formatted = _format_flight_time(departure_time)
                arr_formatted = _format_flight_time(arrival_time)
                time_display = f"{dep_formatted} → {arr_formatted}"
            else:
                # Fallback to departure/return dates
                departure_date = flight.get('departure_date', '?')
                return_date = flight.get('return_date', '?')
                time_display = f"{departure_date} → {return_date}"
            
            stops_text = f" · {stops} stop{'s' if stops > 1 else ''}" if stops > 0 else " · Direct"
            link_url = flight.get("link") or links_section.get("google_flights")
            
            lines.append("[CARD]")
            lines.append("type: plane")
            lines.append(f"title: ✈️ {flight_origin} → {flight_dest}")
            lines.append(f"city: {airline} · {flight_origin} → {flight_dest}")
            lines.append(f"details: €{price} · {time_display} · {duration}{stops_text}")
            lines.append(f"link: {link_url}")
            # Add to planner data
            flight_json = json.dumps({
                "type": "transport",
                "mode": "plane",
                "airline": airline,
                "route": f"{flight_origin} → {flight_dest}",
                "price": price,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "duration": duration,
                "stops": stops,
                "link": link_url
            })
            lines.append(f"data: {flight_json}")
            lines.append("[/CARD]")

    # BUSES - CARD blocks with multi-segment support (OpenAI explains WHY before backend adds card)
    if buses:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'buses')}:")
        for bus in buses:
            route = bus.get('route', f"{bus.get('company')}")
            company = bus.get('company', 'Bus')
            departure = bus.get('departure', '?')
            arrival = bus.get('arrival', '?')
            price_text = f"€{bus['price']}" if bus.get('price') else "—"
            duration = bus.get('duration', '—')
            note = bus.get('note', '')
            link_url = bus.get("link", "")
            
            lines.append("[CARD]")
            lines.append("type: bus")
            lines.append(f"title: 🚌 {company}")
            lines.append(f"city: {route if bus.get('segments', 1) > 1 else f'{departure} → {arrival}'}")
            lines.append(f"details: {price_text} · {duration}{' · ' + note if note else ''}")
            lines.append(f"link: {link_url}")
            # Add to planner data
            bus_json = json.dumps({
                "type": "transport",
                "mode": "bus",
                "company": company,
                "route": route,
                "departure": departure,
                "arrival": arrival,
                "price": bus.get('price'),
                "duration": duration,
                "link": link_url
            })
            lines.append(f"data: {bus_json}")
            lines.append("[/CARD]")

    # TRAINS - CARD blocks with operator details (OpenAI explains WHY before backend adds card)
    if trains:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'trains')}:")
        for train in trains[:1]:
            operator = train.get('operator', 'Train')
            departure = train.get('departure', '?')
            arrival = train.get('arrival', '?')
            price = train.get('price', '?')
            duration = train.get('duration', '—')
            link_url = train.get("link") or links_section.get("train")
            
            lines.append("[CARD]")
            lines.append("type: train")
            lines.append(f"title: 🚆 {operator}")
            lines.append(f"city: {departure} → {arrival}")
            lines.append(f"details: €{price} · {duration}")
            lines.append(f"link: {link_url}")
            # Add to planner data
            train_json = json.dumps({
                "type": "transport",
                "mode": "train",
                "operator": operator,
                "route": f"{departure} → {arrival}",
                "price": price,
                "duration": duration,
                "link": link_url
            })
            lines.append(f"data: {train_json}")
            lines.append("[/CARD]")

    # HOTELS - CARD blocks (SKIP for return trips - user is going home!)
    if not is_return_trip and hotels:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'accommodation')}:")
        # GPT already wrote detailed explanation, just add cards
        lines.append("")
        
        for idx, hotel in enumerate(hotels[:3]):
            price = hotel.get("price_per_night")
            price_note = hotel.get("price_note")
            # Show price with note if it's an estimate
            if price_note:
                price_text = f"~€{price}/noć"
            else:
                price_text = f"€{price}/noć" if price else "Cijena na upit"
            rating = hotel.get("rating")
            rating_text = f"⭐ {rating:.1f}" if isinstance(rating, (int, float)) else ""
            name = hotel.get('name', 'Hotel')
            address = hotel.get('address', destination)
            
            # Use hotel's Google Maps link
            link_url = hotel.get("link")
            
            # Build CARD block for hotel - price in details!
            lines.append("[CARD]")
            lines.append("type: hotel")
            lines.append(f"title: 🏨 {name}")
            lines.append(f"city: {address}")
            lines.append(f"details: {price_text} · {rating_text}")
            if link_url:
                lines.append(f"link: {link_url}")
            
            # Add to planner data
            hotel_json = json.dumps({
                "type": "hotel",
                "name": name,
                "price": price,
                "rating": rating,
                "link": link_url,
                "address": address
            })
            lines.append(f"data: {hotel_json}")
            lines.append("[/CARD]")

    # RESTAURANTS - CARD blocks (SKIP for return trips!)
    if not is_return_trip and restaurants:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'restaurants')}:")
        for place in restaurants[:3]:
            name = place.get('name', 'Restaurant')
            address = place.get('address', 'city center')
            maps_url = place.get("maps_url")
            rating = place.get('rating')
            price_level = place.get('price_level')  # Google returns 1-4
            
            # Convert price_level to € symbols and estimate meal cost
            if price_level:
                price_text = "€" * int(price_level)
                # Estimate cost per person based on price level
                estimated_meal_cost = {1: 15, 2: 25, 3: 45, 4: 80}.get(int(price_level), 25)
            else:
                price_text = "€€"  # default mid-range
                estimated_meal_cost = 25
            
            lines.append("[CARD]")
            lines.append("type: restaurant")
            lines.append(f"title: 🍽️ {name}")
            lines.append(f"city: {address}")
            rating_text = f"⭐ {rating:.1f}" if isinstance(rating, (int, float)) and rating else ""
            lines.append(f"details: {price_text} (~€{estimated_meal_cost}/os) · {rating_text}")
            if maps_url:
                lines.append(f"link: {maps_url}")
            
            # Add to planner data WITH estimated price for cost calculation
            restaurant_json = json.dumps({
                "type": "restaurant",
                "name": name,
                "address": address,
                "maps_url": maps_url,
                "rating": rating,
                "price": estimated_meal_cost,  # For planner cost calculation
                "price_level": price_level
            })
            lines.append(f"data: {restaurant_json}")
            lines.append("[/CARD]")

    # ACTIVITIES - CARD blocks (SKIP for return trips!)
    if not is_return_trip and activities:
        lines.append("")
        lines.append(f"{_section_label(language_code, 'activities')}:")
        for act in activities[:3]:
            name = act.get('name', 'Activity')
            address = act.get('address', 'city center')
            maps_url = act.get("maps_url")
            rating = act.get('rating')
            entry_fee = act.get('entry_fee') or act.get('price')  # Some APIs return price
            
            # Build details with price if available
            rating_text = f"⭐ {rating:.1f}" if isinstance(rating, (int, float)) and rating else ""
            if entry_fee:
                price_text = f"€{entry_fee}"
                details = f"{price_text} · {rating_text}" if rating_text else price_text
                estimated_cost = int(entry_fee)
            else:
                details = rating_text if rating_text else "Besplatan ulaz"
                estimated_cost = 0  # Free attraction
            
            lines.append("[CARD]")
            lines.append("type: activity")
            lines.append(f"title: 🎯 {name}")
            lines.append(f"city: {address}")
            lines.append(f"details: {details}")
            if maps_url:
                lines.append(f"link: {maps_url}")
            
            # Add to planner data WITH price for cost calculation
            activity_json = json.dumps({
                "type": "activity",
                "name": name,
                "address": address,
                "maps_url": maps_url,
                "rating": rating,
                "price": estimated_cost  # For planner cost calculation
            })
            lines.append(f"data: {activity_json}")
            lines.append("[/CARD]")

    # USEFUL LINKS - clean icon links only (no text descriptions)
    lines.append("")
    lines.append(f"{_section_label(language_code, 'links')}:")
    
    google_flights_url = links_section.get("google_flights")
    if google_flights_url:
        lines.append(f"- [✈️ Google Flights]({google_flights_url})")
    
    booking_url = links_section.get("booking")
    if booking_url:
        lines.append(f"- [🏨 Booking.com]({booking_url})")
    
    airbnb_url = links_section.get("airbnb")
    if airbnb_url:
        lines.append(f"- [🏡 Airbnb]({airbnb_url})")
    
    rome2rio_url = links_section.get("rome2rio")
    if rome2rio_url:
        lines.append(f"- [🧭 Rome2Rio]({rome2rio_url})")

    return "\n".join(line.rstrip() for line in lines if line is not None)
