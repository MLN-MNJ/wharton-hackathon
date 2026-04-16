import json

def run_analytics():
    with open('bounties_db.json', 'r') as f:
        data = json.load(f)

    analytics_result = {
        "unique_amenity_count": 0,
        "unique_amenities": [],
        "properties": []
    }

    all_amenities = set()

    for prop in data:
        pid = prop.get("eg_property_id")
        
        amenity_analysis = prop.get("amenity_analysis", [])
        for a in amenity_analysis:
            name = a.get("amenity_name")
            if name:
                all_amenities.add(name.strip().lower())

        # Sort to find the highest score logic
        # We need 1 highest gap, 1 highest ambiguous, 1 highest stale
        gap_target = None
        ambiguous_target = None
        stale_target = None

        if amenity_analysis:
            gap_sorted = sorted(amenity_analysis, key=lambda x: float(x.get('gap_score', 0)), reverse=True)
            gap_target = gap_sorted[0].get('amenity_name') if gap_sorted else None
            
            amb_sorted = sorted(amenity_analysis, key=lambda x: float(x.get('ambiguity_score', 0)), reverse=True)
            ambiguous_target = amb_sorted[0].get('amenity_name') if amb_sorted else None
            
            stale_sorted = sorted(amenity_analysis, key=lambda x: float(x.get('staleness_score', 0)), reverse=True)
            stale_target = stale_sorted[0].get('amenity_name') if stale_sorted else None

        analytics_result["properties"].append({
            "eg_property_id": pid,
            "top_gap_amenity": gap_target,
            "top_ambiguous_amenity": ambiguous_target,
            "top_stale_amenity": stale_target
        })

    analytics_result["unique_amenity_count"] = len(all_amenities)
    analytics_result["unique_amenities"] = sorted(list(all_amenities))

    with open('analytics_output.json', 'w') as f:
        json.dump(analytics_result, f, indent=2)

    print("Analytics mathematically formulated and written to analytics_output.json")

if __name__ == '__main__':
    run_analytics()
