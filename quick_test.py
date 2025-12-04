import requests

# Test 1: Pozdrav
print('='*60)
print('TEST 1: Pozdrav (GREETING)')
print('='*60)
resp = requests.post('http://127.0.0.1:8000/api/chat', json={'message': 'Bok!', 'session_id': 'test1'})
data = resp.json()
print(f"Intent: {data.get('intent')}")
print(f"Reply: {data.get('reply', '')[:400]}")
print()

# Test 2: Travel Plan
print('='*60)
print('TEST 2: Travel Plan (PLAN_REQUEST)')
print('='*60)
resp = requests.post('http://127.0.0.1:8000/api/chat', json={'message': 'Planiraj putovanje iz Zagreba u Pariz', 'session_id': 'test2'}, timeout=120)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:500]}")
else:
    data = resp.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Has cards: {'[CARD]' in data.get('reply', '')}")
    print(f"Reply length: {len(data.get('reply', ''))} chars")
    print(f"Reply preview: {data.get('reply', '')[:300]}...")
print()

# Test 3: Preporuke
print('='*60)
print('TEST 3: Preporuke (TRAVEL_ADVICE)')
print('='*60)
resp = requests.post('http://127.0.0.1:8000/api/chat', json={'message': 'Kamo na skijanje?', 'session_id': 'test3'}, timeout=120)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:500]}")
else:
    data = resp.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Has cards: {'[CARD]' in data.get('reply', '')}")
    print(f"Reply preview: {data.get('reply', '')[:400]}...")
print()

# Test 4: General question
print('='*60)
print('TEST 4: General Question')
print('='*60)
resp = requests.post('http://127.0.0.1:8000/api/chat', json={'message': 'Sto mozes napraviti?', 'session_id': 'test4'}, timeout=120)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:500]}")
else:
    data = resp.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Reply: {data.get('reply', '')[:400]}")
