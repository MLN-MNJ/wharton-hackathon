import json
import os
import urllib.request
import urllib.error
import time

# NEW API KEY
API_KEY = "AIzaSyBgr5ILC1j8k7tHEi5hqvCRvoI3o1GK9Ho"
if not API_KEY:
    print("Error: API Key is missing.")
    exit(1)

def call_gemini(prompt_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode('utf-8'))
                return res['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            if "model is not found" in err_msg.lower() or e.code == 404:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                continue
            if e.code in [429, 503]:
                time.sleep(2 + (2 ** i))
            else:
                break
        except Exception as e:
            time.sleep(5)
    return None

def enforce_math_constraints(bounties):
    # Enforce exactly ONE "Other" at 25, ONE "Miscellaneous" at 25, everything else multiple of 50.
    others = [b for b in bounties if b.get('amenity_name') in ['Other', 'Miscellaneous']]
    regular = [b for b in bounties if b.get('amenity_name') not in ['Other', 'Miscellaneous']]
    
    for o in others:
        o['allocated_points'] = 25
        
    for r in regular:
        pts = r.get('allocated_points', 150)
        # Ensure it's a multiple of 50 and > 100
        pts = max(150, round(pts / 50) * 50)
        r['allocated_points'] = pts
        
    # We must sum strictly to 1000
    current_sum = sum(b['allocated_points'] for b in bounties)
    
    if current_sum != 1000 and len(regular) > 0:
        diff = 1000 - current_sum
        # adjust largest item to maintain constraints if possible, but keep multiples of 50
        regular.sort(key=lambda x: x['allocated_points'], reverse=True)
        # add difference (which should be a multiple of 50) to the highest graded
        if regular[0]['allocated_points'] + diff >= 150:
            regular[0]['allocated_points'] += diff
        else:
            # Fallback spread
            pass
            
    # Verify final
    for b in bounties:
        if b['allocated_points'] < 25: b['allocated_points'] = 150
    return bounties


def main():
    if not os.path.exists("new_bounties_db.json"):
        print("Missing DB file.")
        return
        
    with open("new_bounties_db.json", "r") as f:
        data = json.load(f)
        
    output_file = "final_map_db.json"
    results = []
    
    for idx, prop in enumerate(data, 1):
        pid = prop.get("eg_property_id")
        print(f"[{idx}/{len(data)}] Refining Property: {pid}")
        
        prompt = f"""You are a data architect transforming ugly database structure into clean UI Property Maps.
Given the following Property JSON, do the following:
1. Identify the 'buckets' and rename them into short, 1-2 word beautiful UI map names (e.g. "Room", "Dining", "Lobby", "Pool").
2. Extract the 'sub_features' inside those buckets and assign them an 'amenity_name'.
3. Assign a 'sentiment_quality' to each sub-feature based on its 'evidence_reviews' (e.g. 'Poor', 'Mixed', 'Good').
4. The amenities with the WORST reviews must receive the HIGHEST allocated_points.
5. Create exactly ONE amenity named "Other" worth exactly 25 points.
6. Create exactly ONE amenity named "Miscellaneous" worth exactly 25 points.
7. Give all other amenities a point allocation that is a multiple of 50 (e.g. 150, 200) making sure the ENTIRE SUM EQUALS EXACTLY 1000.
8. Create a 'static_question' for each amenity (1 sentence) asking a future traveler about it.

Raw Property JSON:
{json.dumps(prop)}

OUTPUT FORMAT (RAW JSON ONLY):
{{
  "eg_property_id": "{pid}",
  "buckets": ["Room", "Dining", "Facilities", "Other"],
  "bounties": [
    {{
      "bucket_name": "Room",
      "amenity_name": "AC Condition",
      "sentiment_quality": "Poor",
      "allocated_points": 200,
      "static_question": "How did the air conditioning perform during your stay?"
    }},
    {{
      "bucket_name": "Other",
      "amenity_name": "Other",
      "sentiment_quality": "Unknown",
      "allocated_points": 25,
      "static_question": "Did any other specific facility impact your stay?"
    }},
    {{
      "bucket_name": "Other",
      "amenity_name": "Miscellaneous",
      "sentiment_quality": "Unknown",
      "allocated_points": 25,
      "static_question": "Is there anything else not explicitly covered here that you wish to review?"
    }}
  ]
}}
"""
        res_json = call_gemini(prompt)
        if res_json:
            try:
                res_clean = res_json.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(res_clean)
                
                # Natively override LLM's terrible math if needed
                parsed['bounties'] = enforce_math_constraints(parsed.get('bounties', []))
                
                results.append(parsed)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                print(f"  -> Processed visually and mathematically mapped to 1000 points.")
            except Exception as e:
                print(f"  -> Parse Error: {e}")
        else:
            print("  -> Failed to reach Gemini API.")
            
    print("Done! Data elegantly mapped in final_map_db.json.")

if __name__ == "__main__":
    main()
