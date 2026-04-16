import csv
import json
import os
import urllib.request
import urllib.error
import time

API_KEY = "AIzaSyBP6Gf24N4o0QyrypTU6-vrd6Ry-wcm9DQ"
if not API_KEY:
    print("Error: API Key is missing.")
    exit(1)

def call_gemini(prompt_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
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

    output_file = 'bounties_db.json'
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
            print(f"[{idx}/{len(properties)}] Skipping already processed property: {pid}")
            continue

        print(f"[{idx}/{len(properties)}] Processing property: {pid}")
        revs = reviews_by_prop.get(pid, [])
        
        # We will pass max 50 reviews to keep within massive context windows comfortably
        # and keep the generation tightly bound.
        prompt = f"""You are a data evaluation engine for a hackathon.
We are building a dynamic review collection system that gamifies information gaps.
Evaluate the amenities for the given property based on these exact criteria:
1. Gap (0.0-1.0): How infrequently is this amenity mentioned? Even if mentioned a few times, if it's rarely discussed relative to others, give it a medium score (0.3-0.8). Only use 0.0 if it is extremely widely reviewed.
2. Staleness (0.0-1.0): How long has it been since a detailed review was left about this? Even if there are a few recent mentions, if the bulk is old, give it a medium score (0.3-0.7).
3. Ambiguity (0.0-1.0): Are there minor mixed opinions or just neutral/vague feelings? Don't be too strict. If people just say 'it was okay' or opinions slightly differ, assign 0.3-0.7. Avoid 0.0 unless opinions are absolutely 100% unanimous.

Allocate exactly 1000 'allocated_points' across all amenities in 'amenity_analysis' in multiples of 50. Give the most points to the amenities with the highest gap, ambiguity, or staleness scores.

PROPERTY CLAIMS/INFO:
City/Country: {prop.get('city')}, {prop.get('country')}
Star Rating: {prop.get('star_rating')}
Popular Amenities: {prop.get('popular_amenities_list')}
Accessibility: {prop.get('property_amenity_accessibility')}
Food and Drink: {prop.get('property_amenity_food_and_drink')}
Things to Do: {prop.get('property_amenity_things_to_do')}

RAW REVIEWS (JSON):
{json.dumps(revs[:50])}

Output STRICTLY this JSON format and nothing else. Ensure evidence_reviews is an array of direct quotes from the reviews showing why this score was given.
{{
  "eg_property_id": "{pid}",
  "location": {{
    "city": "{prop.get('city')}",
    "province": "{prop.get('province')}",
    "country": "{prop.get('country')}",
    "star_rating": "{prop.get('star_rating')}"
  }},
  "property_summary": {{
    "guestrating_avg_expedia": "{prop.get('guestrating_avg_expedia')}",
    "n_reviews_total": {len(revs)},
    "total_points_budget": 1000,
    "points_unit": 50
  }},
  "amenity_analysis": [
    {{
      "amenity_name": "<string (e.g. WiFi, Pool)>",
      "listing_present": "<boolean>",
      "gap_score": <float 0.0-1.0>,
      "ambiguity_score": <float 0.0-1.0>,
      "staleness_score": <float 0.0-1.0>,
      "allocated_points": <integer multiple of 50>,
      "evidence_reviews": ["<quote1>", "<quote2>"]
    }}
  ],
  "gap_targets": [ {{ "amenity_name": "...", "gap_score": 0.0, "allocated_points": 50 }} ],
  "ambiguous_targets": [ {{ "amenity_name": "...", "ambiguity_score": 0.0, "allocated_points": 50 }} ],
  "stale_targets": [ {{ "amenity_name": "...", "staleness_score": 0.0, "allocated_points": 50 }} ]
}}
"""
        res_json = call_gemini(prompt)
        if res_json:
            try:
                parsed = json.loads(res_json)
                results.append(parsed)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                print(f"  -> Successfully generated analysis and auto-saved to DB.")
            except Exception as e:
                print(f"  -> Failed to parse JSON: {e}")
                print(f"  -> Raw output: {res_json[:200]}")
        else:
            print(f"  -> Failed to get successful API response. API Key might be expired/quota reached.")
            print("  -> Stopping execution so you can update API key.")
            break

    print(f"\nOptimization Complete! Bounties successfully saved to {output_file}")

if __name__ == "__main__":
    main()
