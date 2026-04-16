import json
import os
import urllib.request
import urllib.error
import time

# Final Hackathon Key
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

def apply_strict_scoring(landmarks):
    # Sort the landmarks by bounty_priority_score (highest score means worst data/biggest gaps).
    landmarks.sort(key=lambda x: x.get('bounty_priority_score', 0.0), reverse=True)
    
    # We strictly enforce 7 landmarks mapping to sum of 1000
    variability_dist = [400, 250, 150, 100, 50, 25, 25]
    
    for i, landmark in enumerate(landmarks):
        if i < len(variability_dist):
            landmark['allocated_points'] = variability_dist[i]
        else:
            landmark['allocated_points'] = 0
            
    # keep only the top 7 if LLM generated more
    return landmarks[:7]


def main():
    if not os.path.exists("new_bounties_db.json"):
        print("Missing DB file: new_bounties_db.json")
        return
        
    with open("new_bounties_db.json", "r") as f:
        data = json.load(f)
        
    output_file = "physical_landmarks_db.json"
    results = []
    
    for idx, prop in enumerate(data, 1):
        pid = prop.get("eg_property_id")
        print(f"[{idx}/{len(data)}] Flattening Property to Physical Landmarks Map: {pid}")
        
        prompt = f"""You are a strict data formatter for a 3D User Interface map.
Given the Property JSON (which contains abstract buckets and sub-features), you must FLATTEN it.

RULES:
1. Discard all abstract concepts like "Room", "Dining", "Facilities", "Overall".
2. Extract EXACTLY 7 DISTINCT PHYSICAL LANDMARKS that could visibly exist on a 3D isometric building map. Examples: "Swimming Pool", "Lobby", "Restaurant", "Tennis Court", "Elevator Bank", "Parking Lot", "Gym", "Bar", "Spa", "Entrance".
3. Examine the `gap_score`, `ambiguity_score`, and `staleness_score` of the sub-features associated with each physical landmark from the input. Compute an aggregate `bounty_priority_score` (a float from 0.0 to 3.0) by summing these three scores. Landmarks with higher sums represent missing or older data.
4. Generate a 'static_question' trying to resolve any missing information for that physical space.
5. Provide NO POINTS. The math will be calculated natively.

Raw Input: 
{json.dumps(prop)}

OUTPUT FORMAT STRICT JSON ARRAY:
[
  {{
    "name": "Bar & Restaurant",
    "bounty_priority_score": 2.4,
    "static_question": "Was the service at the Bar fast enough for you?"
  }},
  {{
    "name": "Swimming Pool",
    "bounty_priority_score": 1.2,
    "static_question": "Was the Swimming Pool area well heated?"
  }}
]"""
        res_json = call_gemini(prompt)
        if res_json:
            try:
                res_clean = res_json.replace('```json', '').replace('```', '').strip()
                parsed_landmarks = json.loads(res_clean)
                
                # Apply flawless 1000 point math validation
                scored_landmarks = apply_strict_scoring(parsed_landmarks)
                
                final_obj = {
                    "eg_property_id": pid,
                    "landmarks": scored_landmarks
                }
                
                results.append(final_obj)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                print(f"  -> Generated perfect flat UI landmarks with math constraints.")
            except Exception as e:
                print(f"  -> Parse Error: {e}")
        else:
            print("  -> Failed to reach Gemini API.")
            
    print("Done! Data physically mapped in physical_landmarks_db.json.")

if __name__ == "__main__":
    main()
