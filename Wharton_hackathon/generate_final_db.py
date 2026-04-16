import json
import os
import urllib.request
import urllib.error
import time

from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set — add it to your .env file")

def call_gemini(prompt_text):
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt_text}]
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    })
    
    for i in range(10):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode('utf-8'))
                return res['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            print(f"  [HTTPError]: {e.code} - {err_msg[:400]}")
            if e.code in [429, 503]:
                print(f"  -> Over quota (429), waiting {20 * (i + 1)} seconds before retry...")
                time.sleep(20 * (i + 1))
            else:
                break
        except Exception as e:
            print(f"  [General Exception]: {e}")
            time.sleep(5)
    return None

def main():
    if not os.path.exists("new_bounties_db.json"):
        print("Missing DB file.")
        return
        
    with open("new_bounties_db.json", "r") as f:
        data = json.load(f)
        
    output_file = "physical_landmarks_db.json"
    results = []
    
    for idx, prop in enumerate(data, 1):
        pid = prop.get("eg_property_id")
        print(f"[{idx}/{len(data)}] Generating Final Hybrid DB: {pid}")
        
        # We process the buckets purely to identify 'frontend_name' and static questions.
        # Then we rank the sub-features and assign math natively!
        
        # Gather all bucket scores globally
        all_buckets = []
        for b_idx, bucket in enumerate(prop.get('buckets', [])):
            total_b_score = sum([sub.get('gap_score', 0) + sub.get('ambiguity_score', 0) + sub.get('staleness_score', 0) for sub in bucket.get('sub_features', [])])
            bucket['bounty_priority_score'] = total_b_score
            all_buckets.append((total_b_score, b_idx))
                
        # Sort buckets by score descending
        all_buckets.sort(key=lambda x: x[0], reverse=True)
        
        # Reset bucket logic
        for bucket in prop.get('buckets', []):
            bucket['allocated_points'] = 0
                
        # Flawless Point Distribution Algorithm for Buckets
        math_dist = []
        target = 950
        num_items = len(all_buckets)
        
        for i in range(num_items):
            if target >= 50:
                math_dist.append(50)
                target -= 50
            else:
                math_dist.append(0)
                
        # Inject cascading variability natively for 3D UI scaling
        distribution_weights = [0.5, 0.25, 0.15, 0.1]
        remaining = target
        for i in range(min(len(distribution_weights), num_items)):
             # Calculate percentage share and strictly snap to nearest multiple of 50
             share = int(target * distribution_weights[i])
             share = (share // 50) * 50
             if share > remaining:
                 share = remaining
             math_dist[i] += share
             remaining -= share
                
        # Dump any leftover remainder rigorously to the top bucket
        if num_items > 0:
            math_dist[0] += remaining
            
        for i, dist in enumerate(math_dist):
             _, b_idx = all_buckets[i]
             prop['buckets'][b_idx]['allocated_points'] = dist
                
        # Append "Other" and "Miscellaneous" abstract buckets natively
        prop['buckets'].append({
            "bucket_name": "Other",
            "frontend_name": "Other",
            "allocated_points": 25,
            "static_question": "Is there anything else you'd like to share about the property?"
        })
        prop['buckets'].append({
            "bucket_name": "Miscellaneous",
            "frontend_name": "Miscellaneous",
            "allocated_points": 25,
            "static_question": "Do you have any miscellaneous details to add?"
        })
            
        # Call LLM just to generate `frontend_name` and `static_question`!
        prompt = f"""You are a UI data generator.
Given this Property layout containing abstract 'bucket_name', provide:
1. `frontend_name`: A flat, 1-2 word physical location name suitable for a 3D building map.
2. `static_question`: A single engaging, 1-sentence question asking the user to review this specific physical area to help fill in data gaps.

Input Property Layout:
{json.dumps(prop)}

OUTPUT FORMAT (JSON ARRAY ONLY, EXACTLY MATCHING THE BUCKET ORDER):
[
  {{
    "bucket_name": "Room & In-room Amenities",
    "frontend_name": "Bedrooms",
    "static_question": "How comfortable was the bed and overall cleanliness during your stay?"
  }}
]
"""
        res_json = call_gemini(prompt)
        if res_json:
            try:
                res_clean = res_json.replace('```json', '').replace('```', '').strip()
                parsed_translation = json.loads(res_clean)
                
                # Merge translation back
                for i, bucket in enumerate(prop.get('buckets', [])):
                    if i < len(parsed_translation):
                        trans_bucket = parsed_translation[i]
                        bucket['frontend_name'] = trans_bucket.get('frontend_name', bucket.get('bucket_name'))
                        if 'static_question' not in bucket:
                            bucket['static_question'] = trans_bucket.get('static_question', "Can you tell us more about this area?")
                        
                # UI-Sleek Scrubber -> ABSOLUTELY PURGE SUB_FEATURES
                for bucket in prop.get('buckets', []):
                    bucket.pop('mapped_amenities', None)
                    bucket.pop('sub_features', None) # Erase nested items entirely
                                
                results.append(prop)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                print(f"  -> Generated final map with original buckets preserved + frontend_names + math.")
            except Exception as e:
                print(f"  -> Parse Error: {e}")
        else:
            print("  -> Failed to reach Gemini API.")
            
    print("Done! Data beautifully mapped in physical_landmarks_db.json.")

if __name__ == "__main__":
    main()
