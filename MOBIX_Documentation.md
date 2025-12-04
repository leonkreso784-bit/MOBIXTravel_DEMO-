# MOBIX Travel Planner

## Dokumentacija i Test Plan

---

# 📖 Sadržaj

1. [O Projektu](#o-projektu)
2. [Arhitektura Sustava](#arhitektura-sustava)
3. [Tehnologije](#tehnologije)
4. [Funkcionalnosti](#funkcionalnosti)
5. [Test Scenariji](#test-scenariji)
6. [Poznata Ograničenja](#poznata-ograničenja)
7. [Demo Linkovi](#demo-linkovi)

---

# 1. O Projektu

**MOBIX Travel Planner** je inteligentni AI asistent za planiranje putovanja koji koristi napredne tehnologije umjetne inteligencije kako bi korisnicima pružio personalizirane preporuke za putovanja.

### Glavne karakteristike:

- **Multilingvalna podrška** - Razumije i odgovara na hrvatskom, engleskom, njemačkom i drugim jezicima
- **AI-powered preporuke** - Koristi OpenAI GPT-4o-mini za inteligentne razgovore
- **Real-time podaci** - Integracija s Google Places i Amadeus API-jem za aktualne informacije
- **Responzivan dizajn** - Optimiziran za desktop i mobilne uređaje
- **Personalizacija** - Mogućnost kreiranja korisničkog računa i spremanja putovanja

---

# 2. Arhitektura Sustava

## 2.1 Pregled arhitekture

MOBIX Travel koristi modernu **mikroservisnu arhitekturu** s jasnom separacijom između frontend i backend komponenti. Sustav je dizajniran za skalabilnost, pouzdanost i jednostavno održavanje.

### Glavni principi:
- **Separation of Concerns** - Frontend i backend su potpuno odvojeni
- **API-First Design** - Sva komunikacija ide preko REST API-ja
- **Cloud-Native** - Hostano na cloud platformama (Vercel + Railway)
- **Stateless Backend** - Backend ne čuva stanje sesije (osim u bazi)

## 2.2 Vizualni prikaz arhitekture

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              INTERNET                                          ║
║                         (Korisnici širom svijeta)                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
╔═══════════════════════════════╗   ╔═══════════════════════════════════════════╗
║      VERCEL CDN               ║   ║              RAILWAY                       ║
║      (Frontend)               ║   ║              (Backend)                     ║
║                               ║   ║                                           ║
║  ┌─────────────────────────┐  ║   ║  ┌───────────────────────────────────┐   ║
║  │      ui-chat/           │  ║   ║  │         FastAPI Server            │   ║
║  │                         │  ║   ║  │                                   │   ║
║  │  • index.html           │  ║   ║  │  app/                             │   ║
║  │  • css/                 │  ║   ║  │  ├── __init__.py (App setup)      │   ║
║  │    └── components/      │  ║   ║  │  ├── database.py (DB connection)  │   ║
║  │        ├── chat.css     │  ║   ║  │  ├── models.py (SQLAlchemy)       │   ║
║  │        ├── mobile.css   │  ║   ║  │  ├── schemas.py (Pydantic)        │   ║
║  │        └── ...          │  ║   ║  │  │                                │   ║
║  │  • js/                  │  ║   ║  │  ├── routers/                     │   ║
║  │    ├── config.js        │──╬───╬──│  │   ├── chat.py    (/api/chat)   │   ║
║  │    ├── app.js           │  ║   ║  │  │   ├── places.py  (/api/places) │   ║
║  │    ├── chat.js          │  ║   ║  │  │   ├── auth.py    (/api/auth)   │   ║
║  │    └── modules/         │  ║   ║  │  │   ├── planner.py (/api/planner)│   ║
║  │        ├── api.js       │  ║   ║  │  │   └── community.py             │   ║
║  │        ├── auth.js      │  ║   ║  │  │                                │   ║
║  │        └── ...          │  ║   ║  │  └── utils/                       │   ║
║  └─────────────────────────┘  ║   ║  │      ├── openai_client.py         │   ║
║                               ║   ║  │      ├── amadeus_client.py        │   ║
║  URL: mobix-travel-demo.      ║   ║  │      ├── intent.py                │   ║
║        vercel.app             ║   ║  │      ├── language.py              │   ║
╚═══════════════════════════════╝   ║  │      └── ...                      │   ║
                                    ║  └───────────────────────────────────┘   ║
                                    ║                                           ║
                                    ║  URL: web-production-7d58.up.railway.app  ║
                                    ╚═══════════════════════════════════════════╝
                                                        │
                    ┌───────────────┬───────────────────┼───────────────────┐
                    │               │                   │                   │
                    ▼               ▼                   ▼                   ▼
╔═══════════════════════╗ ╔═════════════════╗ ╔═════════════════╗ ╔═════════════════╗
║    PostgreSQL         ║ ║    OpenAI       ║ ║  Google Places  ║ ║    Amadeus      ║
║    (Railway)          ║ ║    API          ║ ║      API        ║ ║      API        ║
║                       ║ ║                 ║ ║                 ║ ║                 ║
║  Tablice:             ║ ║  Model:         ║ ║  Endpoints:     ║ ║  Endpoints:     ║
║  • users              ║ ║  GPT-4o-mini    ║ ║  • Place Search ║ ║  • Flight Offers║
║  • published_trips    ║ ║                 ║ ║  • Place Details║ ║  • Hotel Search ║
║                       ║ ║  Funkcije:      ║ ║  • Photos       ║ ║                 ║
║  Connection:          ║ ║  • Chat         ║ ║                 ║ ║  Env:           ║
║  shuttle.proxy.rlwy.  ║ ║  • Intent       ║ ║                 ║ ║  • Sandbox      ║
║  net:24193            ║ ║  • Language     ║ ║                 ║ ║  • Production   ║
╚═══════════════════════╝ ╚═════════════════╝ ╚═════════════════╝ ╚═════════════════╝
```

## 2.3 Detaljni tok podataka

### Primjer: Korisnik traži restorane u Zagrebu

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  1. KORISNIK                                                                  │
│     Upisuje: "Pronađi mi restorane u Zagrebu"                                │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  2. FRONTEND (JavaScript)                                                     │
│     • chat.js hvata input                                                     │
│     • api.js šalje POST request na /api/chat                                  │
│     • Headers: Content-Type: application/json                                 │
│     • Body: { "message": "Pronađi mi restorane u Zagrebu", "session_id": "x" }│
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ HTTPS POST
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  3. BACKEND - Router (chat.py)                                                │
│     • Prima request                                                           │
│     • Validira podatke (Pydantic schema)                                      │
│     • Poziva business logiku                                                  │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  4. BACKEND - Language Detection (language.py)                                │
│     • Detektira jezik: "HR" (Hrvatski)                                        │
│     • Sprema u kontekst za odgovor                                            │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  5. BACKEND - Intent Detection (intent.py + OpenAI)                           │
│     • Šalje prompt OpenAI-u                                                   │
│     • Dobiva: intent="places", category="restaurant", location="Zagreb"       │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  6. BACKEND - Google Places API                                               │
│     • Query: "restaurants in Zagreb"                                          │
│     • Dobiva: lista restorana s ocjenama, adresama, slikama                   │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  7. BACKEND - Response Formatting (formatters.py)                             │
│     • Formatira podatke u kartice                                             │
│     • Generira AI tekst odgovora na hrvatskom                                 │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  8. FRONTEND                                                                  │
│     • Prima JSON response                                                     │
│     • Renderira poruku + kartice restorana                                    │
│     • Korisnik vidi rezultate                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 2.4 Struktura baze podataka

```sql
-- Tablica korisnika
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    profile_image   VARCHAR(500),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Tablica objavljenih putovanja
CREATE TABLE published_trips (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    destination VARCHAR(255),
    trip_data   JSONB,           -- Fleksibilno spremanje podataka
    is_public   BOOLEAN DEFAULT true,
    likes       INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

## 2.5 Sigurnosne mjere

| Mjera | Implementacija |
|-------|----------------|
| **HTTPS** | Sva komunikacija je enkriptirana (TLS) |
| **JWT Tokens** | Autentifikacija korisnika s istekom tokena |
| **Password Hashing** | Bcrypt algoritam za lozinke |
| **CORS** | Konfiguriran za dozvoljene domene |
| **Environment Variables** | API ključevi nisu u kodu |
| **Input Validation** | Pydantic sheme za validaciju |

---

# 3. Tehnologije

## 3.1 Frontend

| Tehnologija | Verzija | Namjena |
|-------------|---------|---------|
| HTML5 | - | Struktura stranice |
| CSS3 | - | Stilizacija i responzivni dizajn |
| JavaScript | ES6+ | Interaktivnost i API komunikacija |
| Vercel | - | Hosting i CDN distribucija |

## 3.2 Backend

| Tehnologija | Verzija | Namjena |
|-------------|---------|---------|
| Python | 3.11 | Programski jezik |
| FastAPI | 0.115.0 | Web framework za REST API |
| Uvicorn | 0.30.6 | ASGI web server |
| SQLAlchemy | 2.0.23 | ORM za bazu podataka |
| Pydantic | 2.5.0 | Validacija podataka |
| JWT | - | Autentifikacija korisnika |

## 3.3 Baza podataka

| Tehnologija | Namjena |
|-------------|---------|
| PostgreSQL | Relacijska baza podataka |
| Railway Hosting | Cloud hosting baze |

## 3.4 Eksterni servisi

| Servis | Namjena |
|--------|---------|
| OpenAI GPT-4o-mini | AI razgovori i analiza teksta |
| Google Places API | Informacije o restoranima, hotelima, atrakcijama |
| Amadeus API | Pretraga letova i hotelskih cijena |

---

# 4. Funkcionalnosti

## 4.1 Implementirane funkcionalnosti

### ✅ AI Chat asistent
- Prirodni razgovor na više jezika (HR, EN, DE, i drugi)
- Automatska detekcija jezika korisnika
- Kontekstualno razumijevanje upita
- Personalizirane preporuke

### ✅ Pretraga lokacija
- Restorani s ocjenama, radnim vremenom i kontaktom
- Hoteli s cijenama i recenzijama
- Turističke atrakcije i znamenitosti
- Interaktivne kartice s detaljima

### ✅ Pretraga letova
- Real-time cijene od aviokompanija
- Direktni i letovi s presjedanjem
- Filtriranje po datumu i destinaciji
- Prikaz trajanja i broja presjedanja

### ✅ Korisnički računi
- Registracija s email adresom
- Sigurna prijava (JWT autentifikacija)
- Personalizirano iskustvo

### ✅ Spremanje putovanja (Travel Notes)
- Dodavanje omiljenih lokacija
- Organizacija putovanja
- Pristup s bilo kojeg uređaja (uz prijavu)

### ✅ Responzivan dizajn
- Optimizirano za desktop računala
- Prilagođeno za tablet uređaje
- Mobilna verzija s touch podrškom

---

# 5. Test Scenariji

## 5.1 Osnovna funkcionalnost chata

**Cilj:** Verificirati da AI asistent ispravno odgovara na upite

| Korak | Akcija | Očekivani rezultat |
|-------|--------|-------------------|
| 1 | Otvoriti aplikaciju | Prikazuje se početni ekran s video pozadinom |
| 2 | Kliknuti "Start Planning" | Otvara se chat sučelje |
| 3 | Upisati: "Pronađi mi restorane u Zagrebu" | AI vraća listu restorana s detaljima |
| 4 | Kliknuti na restoran | Otvara se Google Maps s lokacijom |

## 5.2 Multilingvalna podrška

**Cilj:** Verificirati da aplikacija podržava više jezika

| Korak | Upit | Očekivani jezik odgovora |
|-------|------|-------------------------|
| 1 | "Hoteli u Dubrovniku" | Hrvatski |
| 2 | "Best restaurants in Split" | Engleski |
| 3 | "Sehenswürdigkeiten in Zagreb" | Njemački |

## 5.3 Pretraga letova

**Cilj:** Verificirati funkcionalnost pretrage letova

| Korak | Akcija | Očekivani rezultat |
|-------|--------|-------------------|
| 1 | Upisati: "Let Zagreb Pariz 20. siječnja 2025." | Lista dostupnih letova |
| 2 | Pregledati rezultate | Prikazane cijene, trajanje, aviokompanija |
| 3 | Upisati: "Povratni let Zagreb London 25.-30.01.2025." | Povratni letovi s cijenama |

## 5.4 Registracija i prijava

**Cilj:** Verificirati sustav autentifikacije

| Korak | Akcija | Očekivani rezultat |
|-------|--------|-------------------|
| 1 | Kliknuti ikonu profila | Otvara se forma za prijavu |
| 2 | Odabrati "Register" | Forma za registraciju |
| 3 | Unijeti email i lozinku | Uspješna registracija |
| 4 | Prijaviti se | Uspješna prijava, prikazuje se profil |

## 5.5 Spremanje putovanja

**Cilj:** Verificirati Travel Notes funkcionalnost

| Korak | Akcija | Očekivani rezultat |
|-------|--------|-------------------|
| 1 | Pretražiti restorane | Lista rezultata |
| 2 | Kliknuti "Spremi" na rezultatu | Potvrda spremanja |
| 3 | Otvoriti Travel Notes | Spremljeni rezultat je vidljiv |

## 5.6 Mobilno testiranje

**Cilj:** Verificirati responzivni dizajn

| Korak | Akcija | Očekivani rezultat |
|-------|--------|-------------------|
| 1 | Otvoriti na mobilnom uređaju | Prilagođen prikaz |
| 2 | Video pozadina | Prikazuje se bez play buttona |
| 3 | Hamburger menu | Funkcionira ispravno |
| 4 | Chat na mobitelu | Tipkovnica ne remeti layout |

---

# 6. Poznata Ograničenja

> **⚠️ Napomena:** Ova verzija predstavlja Proof of Concept (PoC) demo aplikaciju. Aplikacija je u aktivnom razvoju i neke funkcionalnosti još nisu u potpunosti dovršene.

## 6.1 Ograničenja planiranja putovanja

### Planiranje putovanja (Trip Planning)
- **Status razvoja:** Funkcionalnost planiranja putovanja još nije u potpunosti dovršena. Trenutno se prikupljaju dodatni API ključevi i integracije koje će omogućiti kompleksnije planiranje
- **Ograničene mogućnosti:** AI asistent može dati osnovne preporuke, no detaljno planiranje višednevnih putovanja s preciznim itinerarom bit će dostupno u kasnijim verzijama
- **Preporuka:** Za sada koristite aplikaciju za pretragu pojedinačnih lokacija (restorani, hoteli, atrakcije) i letova

### Cijene letova i hotela
- **Točnost cijena:** Prikazane cijene letova i hotela dolaze iz Amadeus API-ja i mogu se razlikovati od stvarnih cijena na službenim stranicama. Cijene služe kao orijentir i mogu varirati ovisno o trenutku pretrage
- **Sandbox ograničenja:** Amadeus API koristi sandbox okruženje s ograničenim podacima, što može rezultirati nepotpunim rezultatima za neke destinacije
- **Preporuka:** Prije rezervacije uvijek provjerite cijenu na službenoj stranici aviokompanijei ili booking platforme

## 6.2 Ograničenja sesije i korisničkog iskustva

### Upravljanje sesijom
- **Spremanje chata:** Chat povijest se trenutno ne sprema trajno na server. U nekim slučajevima, prilikom osvježavanja stranice, može se dogoditi da se sesija djelomično zadrži dok se ponovno ne učita (fallback ponašanje)
- **Poruka zahvale:** Povremeno se nakon određenih akcija može pojaviti "Hvala na poruci" ili slična generička poruka - ovo je poznato ponašanje koje će biti optimizirano
- **Preporuka:** Za spremanje važnih informacija koristite Travel Notes funkcionalnost

### Korisnički profil
- **Profilna slika:** Upload profilne slike trenutno nije dostupan jer nije implementiran cloud storage (Cloudinary/AWS S3). Ova funkcionalnost je planirana za buduću verziju
- **Reset lozinke:** Funkcionalnost "Zaboravljena lozinka" putem emaila nije još implementirana
- **Uređivanje profila:** Promjena korisničkih podataka ima ograničene mogućnosti

## 6.3 Tehnička ograničenja

### API integracije
- **Google Places:** Neka mjesta možda nemaju sve informacije (slike, radno vrijeme, kontakt)
- **Amadeus API:** Sandbox verzija ima ograničen broj destinacija i letova
- **Rate limiting:** Nema implementiranog rate limitinga - prekomjerno korištenje može uzrokovati privremene probleme

### Kompatibilnost
- **Internet konekcija:** Aplikacija zahtijeva stabilnu internet vezu za sve funkcionalnosti
- **Preporučeni preglednici:** Chrome, Firefox, Edge. Safari može imati manja ograničenja s video pozadinom
- **iOS Safari:** Na nekim iOS uređajima video pozadina može imati ograničenja zbog Apple politika autoplay-a

### Poznati bugovi
- **Fallback sesije:** Prilikom mijenjanja ili osvježavanja sesije, može se dogoditi fallback na prethodno stanje
- **Dugački odgovori:** Kod kompleksnih upita, AI može trebati duže vrijeme za odgovor (do 10-15 sekundi)
- **Prazni rezultati:** Za manje poznate destinacije, rezultati pretrage mogu biti ograničeni ili prazni

## 6.4 Planirane nadogradnje

| Funkcionalnost | Status | Prioritet | Očekivano |
|----------------|--------|-----------|-----------|
| Potpuno planiranje putovanja | U razvoju | Visok | Q1 2025 |
| Dodatni API ključevi | U tijeku | Visok | Q1 2025 |
| Trajna chat povijest | Planirano | Visok | Q1 2025 |
| Točnije cijene (produkcijski API) | Planirano | Visok | Q1 2025 |
| Upload profilne slike | Planirano | Srednji | Q2 2025 |
| Reset lozinke putem emaila | Planirano | Srednji | Q2 2025 |
| Direktna rezervacija | Razmatranje | Nizak | TBD |
| Offline način rada | Razmatranje | Nizak | TBD |
| Mobilna aplikacija | Razmatranje | Nizak | TBD |

---

# 7. Demo Linkovi

## 7.1 Pristup aplikaciji

| Servis | URL | Opis |
|--------|-----|------|
| **Aplikacija** | https://mobix-travel-demo.vercel.app | Glavni link za pristup |
| **Backend API** | https://web-production-7d58.up.railway.app | REST API endpoint |
| **API Status** | https://web-production-7d58.up.railway.app/api | Provjera statusa |

## 7.2 Tehnička dokumentacija

| Resurs | URL |
|--------|-----|
| GitHub Repozitorij | https://github.com/leonkreso784-bit/MOBIXTravel_DEMO- |

---

