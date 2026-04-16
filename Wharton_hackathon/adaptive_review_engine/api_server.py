"""
GapQuest API Server — FastAPI bridge between React frontend and AI survey engine.
Provides chat/start, chat/respond, chat/extract endpoints.
"""
import os
import json
import uuid
import csv
import pickle
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ── Absolute base directory (always the folder containing this file) ───────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.dirname(BASE_DIR)   # one level up: Wharton_hackathon/

def base(filename):
    """Resolve a filename relative to this script's directory (adaptive_review_engine/)."""
    return os.path.join(BASE_DIR, filename)

# Single source of truth for gamified_responses.json — root directory
RESPONSES_FILE = os.path.join(ROOT_DIR, "gamified_responses.json")

# ── Load environment ──────────────────────────────────────────────────────
load_dotenv(base(".env"))
load_dotenv()  # also try CWD
api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env")
os.environ["OPENAI_API_KEY"] = api_key

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(title="GapQuest AI Survey API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load databases ────────────────────────────────────────────────────────
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

landmarks_db = load_json(base("physical_landmarks_db.json"))
bounties_db  = load_json(base("new_bounties_db.json"))

landmark_map = {p["eg_property_id"]: p for p in landmarks_db}
gap_map      = {p["eg_property_id"]: p for p in bounties_db}

# ── Gap ID → bucket name mapping ──────────────────────────────────────────
GAP_TO_BUCKET = {
    "pool": "Recreation",
    "dining": "Dining",
    "services": "Services",
    "rooms": "Bedrooms",
    "something-else": "Other",
    "facilities": "Facilities",
    "lobby": "Lobby",
}

# Property ID mapping: React id → eg_property_id
PROP_ID_MAP = {
    "resort": "db38b19b897dbece3e34919c662b3fd66d23b615395d11fb69264dd3a9b17723",
    "hotel":  "3b984f3ba8df55b2609a1e33fd694cf8407842e1d833c9b4d993b07fc83a2820",
}

# ── Session store — persisted to disk so reloads don't lose sessions ──────
SESSIONS_FILE = base("_sessions.pkl")

def _load_sessions():
    try:
        with open(SESSIONS_FILE, "rb") as f:
            data = pickle.load(f)
        # Drop stale entries that are missing required keys
        return {k: v for k, v in data.items() if "bucket_name" in v}
    except Exception:
        return {}

def _save_sessions(s):
    try:
        # Pickle can't serialise the live LLM object; store everything except it
        slim = {}
        for sid, sess in s.items():
            slim[sid] = {k: v for k, v in sess.items() if k != "llm"}
        with open(SESSIONS_FILE, "wb") as f:
            pickle.dump(slim, f)
    except Exception:
        pass

sessions = _load_sessions()

# ── Helpers ────────────────────────────────────────────────────────────────
def retrieve_bucket_context(gap_data):
    """Build context string from bounties DB for the LLM."""
    if not gap_data:
        return "No specific data gaps identified for this area."
    context = []
    for sub in gap_data.get("sub_features", []):
        sub_name = sub.get("sub_feature_name")
        gap = sub.get("gap_score", 0)
        amb = sub.get("ambiguity_score", 0)
        stale = sub.get("staleness_score", 0)
        evidence = sub.get("evidence_reviews", [])
        status = []
        if gap > 0.4: status.append("Insufficient recent data")
        if amb > 0.5: status.append("Conflicting guest opinions detected")
        if stale > 0.3: status.append("Historical data may be outdated")
        status_str = ", ".join(status) if status else "Generally stable"
        evidence_str = " | ".join(evidence[:3]) if evidence else "No recent reviews"
        context.append(
            f"### Sub-Feature: {sub_name}\n"
            f"- Status: {status_str}\n"
            f"- Clues: {evidence_str}\n"
            f"- TARGETS FOR DISCOVERY: Needs info on {sub_name.lower()} specifics."
        )
    return "\n\n".join(context)


def build_conversation(bucket_name, bucket_context, static_question, alternative_areas):
    """Create an LLM + system prompt for a session."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.4)
    system_prompt = f"""You are a professional hotel feedback assistant collecting structured guest reviews.

Your role: ask clear, neutral, targeted questions to gather specific information about the guest's experience.

AREA OF FOCUS: {bucket_name}
OTHER PROPERTY AREAS: {alternative_areas}

INTERNAL CONTEXT — use to guide what details to ask about. Never reference these terms to the guest:
{bucket_context}

STRICT TONE RULES:
1. Professional and neutral. No emotional language whatsoever.
2. BANNED phrases: "That's great", "Wonderful", "I'm glad", "Thank you for sharing", "Lovely",
   "Absolutely", "Of course!", "I'd love to", "So glad", "Fantastic", "Amazing", "Sounds like",
   "Great to hear", "Noted with appreciation"
3. BANNED internal terms: "data", "record", "gap", "conflict", "validate", "bounty", "survey",
   "questionnaire", "form", "submission", "capture", "extract"
4. No acknowledgment sentences before the question. Go straight to the question.
5. If guest goes off-topic: "Let's keep focused on {bucket_name}. [restate question]"

Output ONLY your next question. One question only. Under 25 words. No preamble, no reaction."""
    return llm, system_prompt


def call_llm(llm, system_prompt, history, user_input):
    """Call LLM with full conversation history + new user input."""
    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        if msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
        else:
            messages.append(HumanMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_input))
    return llm.invoke(messages).content


# ── Request/Response models ───────────────────────────────────────────────
class ChatStartRequest(BaseModel):
    property_id: str  # React property id, e.g. "resort"
    gap_id: str       # React gap id, e.g. "pool"

class ChatStartResponse(BaseModel):
    session_id: str
    question: str
    step: int
    bucket_name: str

class ChatRespondRequest(BaseModel):
    session_id: str
    user_message: str

class ChatRespondResponse(BaseModel):
    response: str
    step: int
    is_complete: bool

class ChatExtractRequest(BaseModel):
    session_id: str

class ChatExtractResponse(BaseModel):
    findings: dict
    db_updates: int


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/chat/start", response_model=ChatStartResponse)
def chat_start(req: ChatStartRequest):
    """Initialize a conversational review session for a specific gap."""

    # Resolve IDs
    eg_prop_id = PROP_ID_MAP.get(req.property_id)
    if not eg_prop_id:
        raise HTTPException(400, f"Unknown property_id: {req.property_id}")

    bucket_name = GAP_TO_BUCKET.get(req.gap_id, req.gap_id)

    # Find bucket data
    prop_data = landmark_map.get(eg_prop_id)
    if not prop_data:
        raise HTTPException(404, f"Property not found: {eg_prop_id}")

    bucket_data = next(
        (b for b in prop_data.get("buckets", [])
         if b["frontend_name"] == bucket_name or b.get("bucket_name") == bucket_name),
        None
    )

    # Get gap context from bounties DB
    gap_entry = gap_map.get(eg_prop_id)
    gap_bucket = None
    if gap_entry:
        gap_bucket = next(
            (b for b in gap_entry.get("buckets", [])
             if b.get("bucket_name") == (bucket_data.get("bucket_name", "") if bucket_data else "")),
            None
        )

    bucket_context = retrieve_bucket_context(gap_bucket)
    static_question = bucket_data.get("static_question", f"How was your experience with the {bucket_name}?") if bucket_data else f"How was your experience with the {bucket_name}?"

    # Get alternative areas for pivoting
    all_areas = [b["frontend_name"] for b in prop_data.get("buckets", [])]
    alt_areas = [a for a in all_areas if a != bucket_name]
    alt_str = ", ".join(alt_areas) if alt_areas else "None available"

    # Build conversation
    llm, system_prompt = build_conversation(bucket_name, bucket_context, static_question, alt_str)

    # Store session
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "llm": llm,
        "system_prompt": system_prompt,
        "step": 0,
        "messages": [{"role": "assistant", "content": static_question}],
        "bucket_name": bucket_name,
        "property_id": req.property_id,
        "eg_property_id": eg_prop_id,
        "alt_areas": alt_str,
    }
    _save_sessions(sessions)

    return ChatStartResponse(
        session_id=session_id,
        question=static_question,
        step=0,
        bucket_name=bucket_name,
    )


def _get_session_llm(session: dict) -> ChatOpenAI:
    """Return the LLM for a session, rebuilding it if lost after a server reload."""
    if "llm" not in session or session["llm"] is None:
        session["llm"] = ChatOpenAI(model="gpt-4o", temperature=0.4)
    return session["llm"]


@app.post("/api/chat/respond", response_model=ChatRespondResponse)
def chat_respond(req: ChatRespondRequest):
    """Process a user message and return the AI's next response."""

    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # ══════════════════════════════════════════════════════════════════
    # SURVEY STATE MACHINE  — mirrors app.py exactly
    #
    #  Q1 (static, from DB) shown on session start
    #        │
    #  User answers Q1 ──► step = 1
    #        ├─ Vague (≤2 words) or "I don't know"
    #        │       └─► LLM pivot (doubles as freehand Q), step forced to 2
    #        ├─ Detailed ──► LLM decides:
    #        │       ├─ GAPS_RESOLVED ──► LLM freehand Q, step forced to 2
    #        │       └─ Still gaps    ──► LLM follow-up Q, step stays 1
    #        │
    #  User answers follow-up ──► step = 2
    #        └─► LLM freehand open-invitation Q  (always fires here)
    #
    #  User answers freehand ──► step = 3
    #        └─► LLM warm closing ──► step = 10, is_complete = True
    # ══════════════════════════════════════════════════════════════════
    session["step"] += 1
    step = session["step"]
    session["messages"].append({"role": "user", "content": req.user_message})

    user_input = req.user_message
    word_count = len(user_input.split())
    bucket_name = session["bucket_name"]
    history_so_far = session["messages"][:-1]

    injection_keywords = [
        "write code", "print(", "def ", "import ", "python", "script", "ignore instructions"
    ]
    is_injection = any(k in user_input.lower() for k in injection_keywords)

    no_knowledge_phrases = [
        "don't know", "dont know", "didn't use", "didnt use", "not sure",
        "can't remember", "cant remember", "no idea", "haven't been", "havent been",
        "didn't go", "didnt go", "never used", "n/a", "skip",
        "nothing to say", "nothing to add", "nothing to share", "have nothing",
        "nothing about", "no comment", "no opinion", "no feedback",
        "didn't visit", "didnt visit", "didn't try", "didnt try",
        "not applicable", "not relevant", "no experience"
    ]
    is_no_knowledge = any(p in user_input.lower() for p in no_knowledge_phrases)

    _llm = _get_session_llm(session)
    _sp  = session["system_prompt"]

    def ask_freehand():
        """LLM open-invitation question — always the last question before close."""
        return call_llm(
            _llm, _sp, session["messages"],
            f"[SYSTEM — FREEHAND QUESTION]\n\n"
            f"Ask one neutral, open-ended question inviting the guest to share any other "
            f"observations about their stay — any area of the property.\n"
            f"No emotional language. No preamble. Output ONLY the question. Under 20 words."
        ).strip()

    # ── STEP 3 : freehand answered → close → COMPLETE ────────────────────
    if step >= 3:
        response_text = call_llm(
            _llm, _sp, session["messages"],
            "[SYSTEM — CLOSING MESSAGE]\n\n"
            "Write 1 neutral sentence acknowledging the guest's feedback is complete. "
            "No emotional language. No exclamation marks. "
            "Forbidden: data, record, survey, submitted, captured. Under 20 words."
        ).strip()
        session["messages"].append({"role": "assistant", "content": response_text})
        session["step"] = 10
        return ChatRespondResponse(response=response_text, step=10, is_complete=True)

    # ── STEP 2 : always show freehand open-invitation Q ──────────────────
    if step == 2:
        response_text = ask_freehand()
        session["messages"].append({"role": "assistant", "content": response_text})
        return ChatRespondResponse(response=response_text, step=2, is_complete=False)

    # ── STEP 1 : first user reply — dynamic stopping ──────────────────────

    if is_injection:
        response_text = call_llm(
            _llm, _sp, history_so_far,
            f"{user_input}\n\n"
            f"[SYSTEM: Guest went off-topic. Redirect neutrally back to {bucket_name}. "
            f"One sentence + restate original question. No emotional language.]"
        ).strip()
        session["messages"].append({"role": "assistant", "content": response_text})
        return ChatRespondResponse(response=response_text, step=1, is_complete=False)

    if word_count <= 5 or is_no_knowledge:
        # Short/IDK → skip follow-up; pivot response IS the freehand Q
        response_text = call_llm(
            _llm, _sp, session["messages"],
            f"[SYSTEM — PIVOT TO FREEHAND]\n\n"
            f"Guest gave a brief or uncertain response: \"{user_input}\"\n"
            f"Acknowledge neutrally in one short clause, then ask one open-ended question "
            f"inviting any other observations about their stay — any area of the property.\n"
            f"No emotional language. No exclamation marks. Under 25 words total."
        ).strip()
        session["messages"].append({"role": "assistant", "content": response_text})
        session["step"] = 2   # next reply → step 3 → complete
        return ChatRespondResponse(response=response_text, step=2, is_complete=False)

    _save_sessions(sessions)

    # Detailed reply → LLM decides: follow-up OR skip straight to freehand
    llm_decision = call_llm(
        _llm, _sp, history_so_far,
        f"{user_input}\n\n"
        f"[SYSTEM — FOLLOW-UP DECISION]\n"
        f"Topic: {bucket_name}\n\n"
        f"Decide:\n"
        f"• If guest's response is comprehensive (covers quality, timing, availability, cost, etc.) "
        f"→ reply with ONLY the token: GAPS_RESOLVED\n"
        f"• If ONE important dimension is still missing → write one neutral follow-up question:\n"
        f"  - No acknowledgment sentence. Go straight to the question.\n"
        f"  - Under 20 words. No emotional language. No exclamation marks.\n"
        f"  - Forbidden: data, record, gap, validate, extract\n\n"
        f"Output ONLY 'GAPS_RESOLVED' or your question."
    ).strip()

    if llm_decision.upper().startswith("GAPS_RESOLVED"):
        # No follow-up needed → jump straight to freehand Q
        response_text = ask_freehand()
        session["messages"].append({"role": "assistant", "content": response_text})
        session["step"] = 2   # next reply → step 3 → complete
        return ChatRespondResponse(response=response_text, step=2, is_complete=False)

    # Follow-up needed → show it; next reply → step 2 → freehand
    session["messages"].append({"role": "assistant", "content": llm_decision})
    return ChatRespondResponse(response=llm_decision, step=1, is_complete=False)


@app.post("/api/chat/extract", response_model=ChatExtractResponse)
def chat_extract(req: ChatExtractRequest):
    """Extract structured findings from a completed conversation and update databases."""
    print(f"[EXTRACT] called with session_id={req.session_id}", flush=True)
    print(f"[EXTRACT] known sessions: {list(sessions.keys())}", flush=True)

    session = sessions.get(req.session_id)
    if not session:
        print(f"[EXTRACT] ERROR — session not found", flush=True)
        raise HTTPException(404, "Session not found")

    bucket_name = session["bucket_name"]
    alt_areas   = session["alt_areas"]
    messages    = session["messages"]
    eg_prop_id  = session["eg_property_id"]

    # ── LLM extraction (best-effort, fully wrapped) ───────────────────────
    findings: dict = {
        "landmark_name": bucket_name,
        "verdicts": [],
        "cross_landmark_discoveries": [],
        "freehand_insights": "",
        "user_engagement": "high",
        "data_quality": "reliable",
    }
    try:
        _llm = _get_session_llm(session)
        _sp  = session["system_prompt"]
        full_history = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        extraction_prompt = f"""You are a precision property data extractor.
FOCAL LANDMARK: {bucket_name}
ALL VALID PROPERTY AREAS: {alt_areas}
FULL CONVERSATION TRANSCRIPT:
{full_history}
Return RAW JSON only. No markdown fences.
{{
  "landmark_name": "{bucket_name}",
  "verdicts": [{{"sub_feature":"<str>","resolved_conflict":true,"discovery":"<str>","sentiment":"positive|negative|neutral"}}],
  "cross_landmark_discoveries": [{{"area_name":"<str>","fact_captured":"<str>","sentiment":"positive|negative|neutral"}}],
  "freehand_insights": "<str>",
  "user_engagement": "high|low",
  "data_quality": "reliable|unclear"
}}"""
        raw = call_llm(_llm, _sp, messages, extraction_prompt)
        parsed = json.loads(raw.replace("```json","").replace("```","").strip())
        findings.update(parsed)
    except Exception as e:
        print(f"[extract] LLM extraction skipped: {e}", flush=True)

    # ── Single append write — no read/modify/rewrite of existing content ──
    export_data = {
        "eg_property_id": eg_prop_id,
        "landmark": bucket_name,
        "conversation_status": "complete",
        "findings": findings,
    }
    with open(RESPONSES_FILE, "a", encoding="utf-8") as f:
        json.dump(export_data, f)
        f.write("\n")
    print(f"[extract] wrote entry for {eg_prop_id} / {bucket_name}", flush=True)

    # ── STEP 3: Update gap scores (optional, best-effort) ────────────────
    n_updates = 0
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("update_databases", base("update_databases.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        n_updates = mod.run_update()
    except Exception:
        pass

    # Clean up session
    del sessions[req.session_id]
    _save_sessions(sessions)

    return ChatExtractResponse(findings=findings, db_updates=n_updates)


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "sessions": len(sessions)}


# ── Debug endpoint — call this to verify the pipeline instantly ───────────
@app.get("/api/debug")
def debug():
    responses_path = RESPONSES_FILE
    file_exists = os.path.exists(responses_path)
    file_size   = os.path.getsize(responses_path) if file_exists else 0

    entries = []
    if file_exists and file_size > 0:
        try:
            with open(responses_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            decoder = json.JSONDecoder()
            pos = 0
            while pos < len(raw):
                while pos < len(raw) and raw[pos] in ' \t\n\r':
                    pos += 1
                if pos >= len(raw):
                    break
                obj, pos = decoder.raw_decode(raw, pos)
                entries.append({"eg_property_id": obj.get("eg_property_id"), "landmark": obj.get("landmark")})
        except Exception as e:
            entries = [{"error": str(e)}]

    # Write a test entry to prove the path works
    test_write_ok = False
    try:
        with open(responses_path, "a", encoding="utf-8") as f:
            pass  # just open/close to verify write permission
        test_write_ok = True
    except Exception:
        pass

    return {
        "base_dir": BASE_DIR,
        "responses_path": responses_path,
        "file_exists": file_exists,
        "file_size_bytes": file_size,
        "entries_count": len(entries),
        "entries_summary": entries[-5:],
        "write_permission_ok": test_write_ok,
        "active_sessions": list(sessions.keys()),
    }


# ── Dashboard endpoint ────────────────────────────────────────────────────
@app.get("/api/dashboard")
def dashboard(property_id: str = "resort"):
    """Return aggregated review stats and current gap scores for a property."""

    eg_prop_id = PROP_ID_MAP.get(property_id)
    if not eg_prop_id:
        raise HTTPException(400, f"Unknown property_id: {property_id}")

    # --- Read gamified_responses.json (newline-delimited JSON, mixed formats) ---
    submissions = []
    try:
        with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()

        # Support both NDJSON and single JSON array
        if raw.startswith("["):
            all_entries = json.loads(raw)
        else:
            # NDJSON: parse objects one by one using absolute index positions
            decoder = json.JSONDecoder()
            pos = 0
            all_entries = []
            while pos < len(raw):
                # Skip any whitespace / newlines between objects
                while pos < len(raw) and raw[pos] in ' \t\n\r':
                    pos += 1
                if pos >= len(raw):
                    break
                # raw_decode(s, idx) returns (obj, end) where end is the
                # absolute index in s right after the parsed object
                obj, pos = decoder.raw_decode(raw, pos)
                all_entries.append(obj)

        for entry in all_entries:
            if entry.get("eg_property_id") == eg_prop_id:
                submissions.append(entry)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # --- Aggregate sentiment counts from new-format entries (findings.verdicts) ---
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    gaps_covered = set()
    recent_submissions = []

    for entry in submissions:
        findings = entry.get("findings", {})
        landmark = entry.get("landmark") or entry.get("target_amenity", "Unknown")
        gaps_covered.add(landmark)

        for verdict in findings.get("verdicts", []):
            s = verdict.get("sentiment", "neutral")
            if s in sentiment_counts:
                sentiment_counts[s] += 1

        recent_submissions.append({
            "landmark": landmark,
            "freehand_insights": findings.get("freehand_insights", ""),
            "user_engagement": findings.get("user_engagement", ""),
            "data_quality": findings.get("data_quality", ""),
            "verdicts": findings.get("verdicts", []),
        })

    # --- Current gap scores from new_bounties_db.json ---
    gap_scores = []
    gap_entry = gap_map.get(eg_prop_id)
    if gap_entry:
        for bucket in gap_entry.get("buckets", []):
            bucket_name = bucket.get("bucket_name", "")
            sub_scores = []
            for sf in bucket.get("sub_features", []):
                sub_scores.append({
                    "name": sf.get("sub_feature_name", ""),
                    "gap_score": round(sf.get("gap_score", 0), 3),
                    "ambiguity_score": round(sf.get("ambiguity_score", 0), 3),
                    "staleness_score": round(sf.get("staleness_score", 0), 3),
                })
            gap_scores.append({
                "bucket": bucket_name,
                "sub_features": sub_scores,
                "avg_gap": round(
                    sum(s["gap_score"] for s in sub_scores) / len(sub_scores), 3
                ) if sub_scores else 0,
            })

    return {
        "property_id": property_id,
        "eg_property_id": eg_prop_id,
        "total_submissions": len(submissions),
        "gaps_covered": sorted(gaps_covered),
        "sentiment_breakdown": sentiment_counts,
        "recent_submissions": recent_submissions[-10:],  # last 10
        "gap_scores": gap_scores,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8507)
