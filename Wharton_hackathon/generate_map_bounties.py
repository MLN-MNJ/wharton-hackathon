import csv
import json
import os
import urllib.request
import urllib.error
import time

# NEW API KEY AS REQUESTED!
API_KEY = "AIzaSyAwbwT29Dl2zZYExvKCc1-peForO4vwirs"
if not API_KEY:
    print("Error: API Key is missing.")
    exit(1)

def call_gemini(prompt_text):
    # Endpoint using gemini-2.5-flash (fallback automatically happens locally if 2.5 is unavailable depending on the routing, otherwise we manually fallback to flash-latest)
    # We will try flash-latest because the 2.5 string is technically mostly deployed as gemini-2.5-flash inside vertex, but we'll try it here.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    for i in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode('utf-8'))
                return res['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            if "model is not found" in err_msg.lower() or e.code == 404:
                print(f"  [HTTPError]: 404 - gemini-2.5-flash unavailable via this endpoint. Falling back to gemini-flash-latest...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                continue
                
            print(f"  [HTTPError]: {e.code} - {err_msg[:100]}...")
            if e.code in [429, 503]:
                wait_time = 2 + (2 ** i)
                print(f"  -> Retrying in {wait_time} seconds (Attempt {i+1}/8)...")
                time.sleep(wait_time)
            else:
                break
        except Exception as e:
            print(f"  [Error]: {e}")
            time.sleep(5)
    return None

def main():
    print("Loading datasets...")
    properties = {}
    with open('Description_PROC.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            properties[row['eg_property_id']] = row

    reviews_by_prop = {}
    with open('Reviews_PROC.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['eg_property_id']
            if pid not in reviews_by_prop:
                reviews_by_prop[pid] = []
            reviews_by_prop[pid].append({
                "date": row['acquisition_date'],
                "rating": row['rating'],
                "title": row['review_title'],
                "text": row['review_text']
            })

    output_file = 'new_bounties_db.json'
    results = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"Loaded {len(results)} previously processed properties.")
        except Exception as e:
            print(f"Could not load previous DB: {e}")
            results = []

    processed_ids = {r.get('eg_property_id') for r in results if isinstance(r, dict)}

    for idx, (pid, prop) in enumerate(properties.items(), 1):
        if pid in processed_ids:
            continue

        print(f"[{idx}/{len(properties)}] Processing property for Map Buckets: {pid}")
        revs = reviews_by_prop.get(pid, [])
        
        prompt = f"""You are a data hierarchy engine for a 3D UI Property Map.
Your goal is to bucket all of a property's known amenities into broadly accessible spatial locations, and extract review-specific sub-features for those spatial buckets.

STEP 1: SPATIAL BUCKETS
Based on the RAW REVIEWS and PROPERTY AMENITIES, categorize the amenities into EXACTLY 4 to 5 high-level UI buckets (e.g., "Room", "Restaurant/Dining", "Lobby/Services", "Pool & Recreation", "Gym/Fitness"). 
A bucket should represent a real physical or structural concept of the hotel. Map any smaller amenities into these buckets (e.g. AC and TV map into "Room").

STEP 2: SUB-FEATURES & SCORING
Instead of scoring the top level buckets, generate 2-4 "sub-features" for each bucket that users ACTUALLY mention in the reviews. 
For example, if the bucket is "Restaurant", sub-features could be "breakfast timing", "service speed", etc.
For each sub-feature, provide:
1. Gap Score (0.0-1.0): How much missing info is there? (1.0 = nobody mentions it, 0.0 = it is documented highly).
2. Staleness Score (0.0-1.0): How old is the review info?
3. Ambiguity Score (0.0-1.0): Are there conflicting views in the reviews regarding this sub-feature?

Allocate exactly 1000 'allocated_points' across all SUB-FEATURES (multiples of 50) based on which sub-features have the highest UI bounty gaps.

PROPERTY CLAIMS/INFO:
Popular Amenities: {prop.get('popular_amenities_list')}
Accessibility: {prop.get('property_amenity_accessibility')}
Food and Drink: {prop.get('property_amenity_food_and_drink')}
Things to Do: {prop.get('property_amenity_things_to_do')}

RAW REVIEWS EXCERPTS (JSON):
{json.dumps(revs[:50])}

Output STRICTLY this JSON format and nothing else. Output raw JSON without markdown formatting.
{{
  "eg_property_id": "{pid}",
  "location": {{
    "city": "{prop.get('city')}",
    "star_rating": "{prop.get('star_rating')}"
  }},
  "buckets": [
    {{
      "bucket_name": "<string (e.g. Room)>",
      "mapped_amenities": ["<string>", "<string>"],
      "sub_features": [
        {{
          "sub_feature_name": "<string (e.g. AC noise levels)>",
          "gap_score": <float 0.0-1.0>,
          "ambiguity_score": <float 0.0-1.0>,
          "staleness_score": <float 0.0-1.0>,
          "allocated_points": <integer multiple of 50>,
          "evidence_reviews": ["<quote from raw reviews, or empty array if Gap=1.0>"]
        }}
      ]
    }}
  ]
}}
"""
        res_json = call_gemini(prompt)
        if res_json:
            try:
                # Cleanup potential markdown wrap accidentally returned
                res_clean = res_json.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(res_clean)
                results.append(parsed)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                print(f"  -> Successfully generated Map analysis and auto-saved to DB.")
            except Exception as e:
                print(f"  -> Failed to parse JSON: {e}")
        else:
            print(f"  -> Failed to get successful API response.")
            break

    print(f"\nMap Bounties fully generated to {output_file}")

if __name__ == "__main__":
    main()
