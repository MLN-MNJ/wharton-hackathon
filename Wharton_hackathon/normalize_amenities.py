import json

# As an LLM, I have analyzed the 50 unique items and built this normalization dictionary
# to fix all inconsistencies (underscores, plurals, aliases).
NORMALIZATION_MAP = {
    "ac": "AC",
    "air conditioning": "AC",
    "accessibility (braille/wheelchair access)": "Accessibility",
    "accessibility (elevator/grab bars)": "Accessibility",
    "accessibility (grab bars, stair-free path)": "Accessibility",
    "accessibility (no elevators/handrails)": "Accessibility",
    "accessibility (stairs only)": "Accessibility",
    "accessibility features": "Accessibility",
    "wheelchair accessible": "Accessibility",
    "bar": "Bar",
    "barbecue/grills": "Barbecue/Outdoor",
    "outdoor space & barbecue": "Barbecue/Outdoor",
    "outdoor_space": "Barbecue/Outdoor",
    "bicycle rentals": "Bicycle Rentals",
    "bowling alley & table tennis": "Bowling Alley & Table Tennis",
    "breakfast": "Breakfast",
    "breakfast available": "Breakfast",
    "breakfast included": "Breakfast",
    "breakfast_available": "Breakfast",
    "breakfast_included": "Breakfast",
    "restaurant & breakfast": "Restaurant & Breakfast",
    "business services": "Business Services",
    "business_services": "Business Services",
    "crib": "Crib",
    "elevator": "Elevator",
    "elevators": "Elevator",
    "fitness center": "Fitness Center",
    "fitness equipment": "Fitness Center",
    "free daily reception": "Free Daily Reception",
    "free parking": "Free Parking",
    "free_parking": "Free Parking",
    "front desk (24-hour)": "24-Hour Front Desk",
    "frontdesk 24-hour": "24-Hour Front Desk",
    "frontdesk_24_hour": "24-Hour Front Desk",
    "golf course": "Golf Course",
    "heater": "Heater",
    "housekeeping": "Housekeeping",
    "internet": "Internet",
    "kitchen": "Kitchen",
    "laundry": "Laundry",
    "microwave": "Microwave",
    "no_smoking": "No Smoking",
    "pool": "Pool",
    "restaurant": "Restaurant",
    "room service": "Room Service",
    "soundproof room": "Soundproof Rooms",
    "soundproof rooms": "Soundproof Rooms",
    "spa": "Spa",
    "toys": "Toys",
    "tv": "TV"
}

def normalize_name(name):
    if not name: return name
    cleaned = name.strip().lower()
    return NORMALIZATION_MAP.get(cleaned, name.strip().title())

def propagate_changes():
    with open('bounties_db.json', 'r') as f:
        data = json.load(f)

    for prop in data:
        # Normalize amenity_analysis array
        for item in prop.get("amenity_analysis", []):
            old_name = item.get("amenity_name")
            if old_name:
                item["amenity_name"] = normalize_name(old_name)

        # Normalize target arrays
        for target in prop.get("gap_targets", []):
            if "amenity_name" in target:
                target["amenity_name"] = normalize_name(target["amenity_name"])
                
        for target in prop.get("ambiguous_targets", []):
            if "amenity_name" in target:
                target["amenity_name"] = normalize_name(target["amenity_name"])
                
        for target in prop.get("stale_targets", []):
            if "amenity_name" in target:
                target["amenity_name"] = normalize_name(target["amenity_name"])

    with open('bounties_db.json', 'w') as f:
        json.dump(data, f, indent=2)

    print("Successfully propagated normalized amenity names across bounties_db.json!")

if __name__ == '__main__':
    propagate_changes()
