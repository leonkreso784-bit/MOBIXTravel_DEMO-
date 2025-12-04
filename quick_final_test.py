"""Quick test za provjeru Google Places integracije"""
import requests

BASE_URL = "https://web-production-7d58.up.railway.app"

def test_query(message):
    print(f"\n{'='*70}")
    print(f"PITANJE: {message}")
    print(f"{'='*70}")
    
    resp = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": message, "session_id": f"final-test-{hash(message)}"},
        timeout=30
    )
    data = resp.json()
    
    print(f"INTENT: {data.get('intent')}")
    print(f"CATEGORY: {data.get('category', 'N/A')}")
    print(f"CITY: {data.get('city', 'N/A')}")
    print()
    print("ODGOVOR:")
    print(data.get('reply', 'No reply'))
    print()
    
    if data.get('places'):
        print("📍 GOOGLE PLACES PODACI (STVARNA MJESTA):")
        for p in data.get('places', []):
            print(f"  ✓ {p.get('name')} ({p.get('rating')}⭐) - {p.get('address')}")
        return True
    return False

# Test
tests = [
    "Koje su najbolje slastičarnice u Opatiji?",
    "Preporuči mi pizzerije u Rijeci",
    "Tražim dobre kafiće u Zagrebu",
    "Best restaurants in Dubrovnik?",
]

print("\n" + "🔍"*35)
print("FINALNI TEST GOOGLE PLACES INTEGRACIJE")
print("🔍"*35)

has_google = []
for t in tests:
    has_google.append(test_query(t))

print(f"\n{'='*70}")
print(f"REZULTAT: {sum(has_google)}/{len(tests)} upita koriste Google Places")
print(f"{'='*70}")
