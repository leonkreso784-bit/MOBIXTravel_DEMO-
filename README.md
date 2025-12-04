# MOBIX — AI Travel Planner

A FastAPI backend with modern UI for AI travel planning: intelligent chat (OpenAI GPT-4), real-time flight and hotel search (Amadeus + Google fallback), places/maps (Google), and a powerful itinerary planner.

## Features

- **Smart Chat**: AI-powered travel assistant with intent detection and context memory
- **Multi-API Integration**: Amadeus (primary) for flights/hotels with Google fallback
- **Travel Planning**: Comprehensive trip planning with transportation, accommodation, activities
- **User Profiles**: Full authentication with JWT, profile management, travel preferences
- **Itinerary Planner**: Save, edit, and manage travel plans with day-by-day organization

## Requirements

- Python 3.10+
- PostgreSQL database
- Internet access for external APIs (OpenAI, Amadeus, Google)

## Configure

Create a `.env` file in the project root with the following keys:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

# Google APIs (Places, Maps, Geocoding)
GOOGLE_API_KEY=your_google_key

# Amadeus Travel APIs (flights & hotels)
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
AMADEUS_ENV=production  # or "test" for sandbox

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mobix_db
```

### API Setup Notes

- **Amadeus**: Sign up at [developers.amadeus.com](https://developers.amadeus.com) for flight and hotel search APIs
- **Google**: Enable Places API, Geocoding API, and Maps JavaScript API at [console.cloud.google.com](https://console.cloud.google.com)
- **OpenAI**: Get API key from [platform.openai.com](https://platform.openai.com)

## Install

```powershell
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open the UI:

- http://127.0.0.1:8000/ui

## Windows quick start

If you have a local virtual environment at `.venv` (recommended), activate it first so the right Python and packages are used:

```powershell
# From the project root
.\.venv\Scripts\Activate.ps1

# Install deps (first time)
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Alternatively, you can run Uvicorn via the virtualenv Python without activating the shell environment:

```powershell
C:\Users\leonk\mobix\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

## Troubleshooting

- If the server exits immediately or you see `ModuleNotFoundError` for FastAPI/Uvicorn, make sure you're using the `.venv` interpreter (see the commands above).
- If port 8000 is in use, change `--port 8001` (or another free port) and open the UI at that port.
- When testing endpoints from the same terminal, avoid interrupting the running server. Either open a new terminal for `Invoke-WebRequest`/`curl` or run quick checks from a separate process.
- Open API docs at http://127.0.0.1:8000/docs to interactively try endpoints.

## Endpoints

- `GET /` → serves `ui/index.html` if present
- `GET /v1/health` → status with masked keys
- `POST /chat` → chat with mixed AI + Google + Amadeus features
- `GET /maps/static` → returns a Google Static Maps URL for given params
- `GET /places/search?query=...` → Places search (Google Places v1)
- `GET /weather?place=...` → simple current weather via Open-Meteo
- `GET /traffic?origin=...&destination=...` → directions + traffic summary
- `GET /reverse?lat=...&lng=...` → reverse geocode (city/address)
- `GET /flights/token` → Amadeus OAuth token (demo)
- `GET /flights/search` → Amadeus flight-offers search
- `POST /plan` → simple itinerary generator
- `POST /session/reset/{id}` → forget session memory

## Notes

- The demo Google/Amadeus calls are limited; for production use your own keys and handle quotas and billing.
- The UI (`ui/index.html`) loads `ui/main.js` and `ui/styles.css` and targets the same origin. If you proxy or host separately, set `window.__MOBIX_API_BASE__` ahead of `main.js` to point to your backend origin.
