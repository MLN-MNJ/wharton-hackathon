"""
update_databases.py — End-to-End Feedback Loop

Reads gamified_responses.json and updates the source databases:
  1. new_bounties_db.json  → reduces gap/ambiguity scores, appends evidence
  2. physical_landmarks_db.json → recalculates bounty_priority_score + redistributes points

Usage:
  python3 update_databases.py                        # process all pending entries
  Called automatically from app.py after each conversation
"""

import json
import os
import shutil
from datetime import datetime


# ─── Config ──────────────────────────────────────────────────────────────
BOUNTIES_PATH = "new_bounties_db.json"
LANDMARKS_PATH = "physical_landmarks_db.json"
RESPONSES_PATH = "gamified_responses.json"
PROCESSED_PATH = "gamified_responses_processed.json"

GAP_DECAY = 0.7         # 30% reduction per new evidence
AMBIGUITY_DECAY = 0.6   # 40% reduction when conflict resolved
STALENESS_DECAY = 0.8   # 20% reduction (fresh data arrived)

VARIABILITY_DIST = [400, 250, 150, 100, 50, 25, 25]


# ─── Helpers ─────────────────────────────────────────────────────────────

def backup_file(path):
    """Create a timestamped backup before modifying."""
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.replace(".json", f"_backup_{ts}.json")
        shutil.copy2(path, backup)
        print(f"  📦 Backup: {backup}")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_responses():
    """Load newline-delimited JSON entries from gamified_responses.json."""
    entries = []
    if not os.path.exists(RESPONSES_PATH):
        return entries
    with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def parse_findings(entry):
    """Parse the findings field (may be a JSON string or dict)."""
    findings = entry.get("findings", {})
    if isinstance(findings, str):
        try:
            findings = json.loads(findings)
        except json.JSONDecodeError:
            return {}
    return findings


# ─── Part A: Update Bounties (Scores) ────────────────────────────────────

def update_bounties(bounties_data, entries):
    """
    For each verdict and cross-landmark discovery:
    - Find matching property + bucket + sub_feature
    - Decay gap_score, ambiguity_score, staleness_score
    - Append discovery text to evidence_reviews
    """
    # Build a fast lookup: {property_id: {bucket_name: {sub_feature_name: sub_obj}}}
    lookup = {}
    for prop in bounties_data:
        pid = prop["eg_property_id"]
        lookup[pid] = {}
        for bucket in prop.get("buckets", []):
            bname = bucket["bucket_name"]
            lookup[pid][bname] = {}
            for sf in bucket.get("sub_features", []):
                lookup[pid][bname][sf["sub_feature_name"]] = sf

    updates_applied = 0

    for entry in entries:
        pid = entry.get("eg_property_id")
        if pid not in lookup:
            continue

        findings = parse_findings(entry)
        landmark_frontend = entry.get("landmark", "")

        # Process primary verdicts
        for verdict in findings.get("verdicts", []):
            sf_name = verdict.get("sub_feature", "")
            discovery = verdict.get("discovery", "")
            resolved = verdict.get("resolved_conflict", False)
            sentiment = verdict.get("sentiment", "neutral")

            # Sentiment → score delta
            sentiment_delta = {"positive": +0.1, "negative": -0.1, "neutral": 0.0}.get(sentiment, 0.0)

            # Search across all buckets for matching sub_feature
            for bname, sfs in lookup[pid].items():
                if sf_name in sfs:
                    sf = sfs[sf_name]
                    sf["gap_score"] = round(sf.get("gap_score", 0) * GAP_DECAY, 3)
                    sf["staleness_score"] = round(sf.get("staleness_score", 0) * STALENESS_DECAY, 3)
                    if resolved:
                        sf["ambiguity_score"] = round(sf.get("ambiguity_score", 0) * AMBIGUITY_DECAY, 3)
                    # Update sentiment score (clamped 0.0–1.0)
                    current_sentiment = sf.get("sentiment_score", 0.5)
                    sf["sentiment_score"] = round(max(0.0, min(1.0, current_sentiment + sentiment_delta)), 3)
                    if discovery and discovery not in sf.get("evidence_reviews", []):
                        sf.setdefault("evidence_reviews", []).append(discovery)
                    updates_applied += 1
                    print(f"  ✅ Updated [{bname}] → {sf_name} (gap: {sf['gap_score']}, sentiment: {sf['sentiment_score']})")
                    break

        # Process cross-landmark discoveries
        for cross in findings.get("cross_landmark_discoveries", []):
            area_name = cross.get("area_name", "")
            fact = cross.get("fact_captured", "")

            # Try to match area_name to a bucket (could be frontend name or bucket name)
            for bname, sfs in lookup[pid].items():
                if area_name.lower() in bname.lower() or bname.lower() in area_name.lower():
                    # Apply decay to all sub-features in the matched bucket
                    for sf_name, sf in sfs.items():
                        sf["gap_score"] = round(sf.get("gap_score", 0) * GAP_DECAY, 3)
                        sf["staleness_score"] = round(sf.get("staleness_score", 0) * STALENESS_DECAY, 3)
                        if fact and fact not in sf.get("evidence_reviews", []):
                            sf.setdefault("evidence_reviews", []).append(fact)
                    updates_applied += 1
                    print(f"  🔀 Cross-update [{bname}] from '{area_name}' discovery")
                    break

        # Process freehand classifications 
        for fh in findings.get("freehand_classifications", []):
            mapped_bucket = fh.get("mapped_bucket", "")
            fact = fh.get("fact", "")

            for bname, sfs in lookup[pid].items():
                if mapped_bucket.lower() in bname.lower() or bname.lower() in mapped_bucket.lower():
                    for sf_name, sf in sfs.items():
                        sf["gap_score"] = round(sf.get("gap_score", 0) * GAP_DECAY, 3)
                        sf["staleness_score"] = round(sf.get("staleness_score", 0) * STALENESS_DECAY, 3)
                        if fact and fact not in sf.get("evidence_reviews", []):
                            sf.setdefault("evidence_reviews", []).append(fact)
                    updates_applied += 1
                    print(f"  🆓 Freehand update [{bname}] → '{fact[:50]}...'")
                    break

    return updates_applied


# ─── Part B: Recalculate Landmarks (Points & Scores) ─────────────────────

def recalculate_landmarks(landmarks_data, bounties_data):
    """
    For each property in physical_landmarks_db.json:
    - Recalculate bounty_priority_score from the updated sub-feature scores
    - Redistribute allocated_points using the variability distribution
    """
    # Build bounties lookup: {pid: {bucket_name: [sub_features]}}
    bounty_lookup = {}
    for prop in bounties_data:
        pid = prop["eg_property_id"]
        bounty_lookup[pid] = {}
        for bucket in prop.get("buckets", []):
            bounty_lookup[pid][bucket["bucket_name"]] = bucket.get("sub_features", [])

    for prop in landmarks_data:
        pid = prop["eg_property_id"]
        if pid not in bounty_lookup:
            continue

        scorable_buckets = []

        for bucket in prop.get("buckets", []):
            bname = bucket["bucket_name"]
            if bname in bounty_lookup[pid]:
                sfs = bounty_lookup[pid][bname]
                # Aggregate: sum of gap + ambiguity + staleness across sub-features
                total_score = 0
                for sf in sfs:
                    total_score += sf.get("gap_score", 0) + sf.get("ambiguity_score", 0) + sf.get("staleness_score", 0)
                avg_score = round(total_score / max(len(sfs), 1), 2)
                bucket["bounty_priority_score"] = avg_score
                scorable_buckets.append(bucket)
            else:
                # Filler buckets like "Other", "Miscellaneous"
                bucket.setdefault("bounty_priority_score", 0)

        # Sort scorable buckets by priority (highest = most gaps)
        scorable_buckets.sort(key=lambda x: x.get("bounty_priority_score", 0), reverse=True)

        # Redistribute points
        all_buckets = prop.get("buckets", [])
        # First, assign points to scorable buckets
        for i, bucket in enumerate(scorable_buckets):
            if i < len(VARIABILITY_DIST):
                bucket["allocated_points"] = VARIABILITY_DIST[i]
            else:
                bucket["allocated_points"] = 0

        # Non-scorable buckets get minimum points
        for bucket in all_buckets:
            if bucket not in scorable_buckets:
                bucket["allocated_points"] = 25

        print(f"  📊 Recalculated points for property {pid[:16]}...")


# ─── Main Entry Point ────────────────────────────────────────────────────

def run_update():
    """Main function — can be called from app.py or run standalone."""
    print("\n🔄 Starting Database Update Pipeline...")

    entries = load_responses()
    if not entries:
        print("  ⚠️  No new responses to process.")
        return 0

    print(f"  📋 Found {len(entries)} conversation entries to process.")

    # Load databases
    bounties_data = load_json(BOUNTIES_PATH)
    landmarks_data = load_json(LANDMARKS_PATH)

    # Create backups
    backup_file(BOUNTIES_PATH)
    backup_file(LANDMARKS_PATH)

    # Part A: Update scores
    print("\n--- Part A: Updating Bounty Scores ---")
    updates = update_bounties(bounties_data, entries)
    print(f"  Total score updates applied: {updates}")

    # Part B: Recalculate landmarks
    print("\n--- Part B: Recalculating Landmark Points ---")
    recalculate_landmarks(landmarks_data, bounties_data)

    # Save updated databases
    save_json(BOUNTIES_PATH, bounties_data)
    save_json(LANDMARKS_PATH, landmarks_data)
    print(f"\n  💾 Saved updated {BOUNTIES_PATH}")
    print(f"  💾 Saved updated {LANDMARKS_PATH}")

    # Move processed responses to archive
    processed = []
    if os.path.exists(PROCESSED_PATH):
        try:
            with open(PROCESSED_PATH, "r") as f:
                processed = [json.loads(l) for l in f if l.strip()]
        except:
            processed = []

    with open(PROCESSED_PATH, "a") as f:
        for entry in entries:
            json.dump(entry, f)
            f.write("\n")

    # Clear the active responses file
    with open(RESPONSES_PATH, "w") as f:
        f.write("")

    print(f"\n✅ Pipeline complete! {updates} updates applied. Responses archived.")
    return updates


if __name__ == "__main__":
    run_update()
