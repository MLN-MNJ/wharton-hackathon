import streamlit as st
import os
import json
import csv
import io
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from openai import OpenAI

# ── Security: Load API key from .env ──────────────────────────────────────
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    st.error("⚠️ OPENAI_API_KEY not found. Add it to your .env file.")
    st.stop()
os.environ["OPENAI_API_KEY"] = api_key
openai_client = OpenAI(api_key=api_key)

# ── Page Config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Expedia | PropertyIQ",
    page_icon="🏝️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Premium CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global Reset */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #0d0d1a 0%, #0f1929 50%, #0d1a2e 100%);
    color: #e8eaf0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1929 100%);
    border-right: 1px solid rgba(255,183,77,0.15);
}
[data-testid="stSidebar"] * {
    color: #c8d0e0 !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }

/* Selectbox & widgets */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,183,77,0.25) !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
}

/* Sidebar area card buttons */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    color: #c8d0e0 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-align: left !important;
    padding: 14px 16px !important;
    margin-bottom: 6px !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,183,77,0.08) !important;
    border-color: rgba(255,183,77,0.3) !important;
    color: #ffb74d !important;
    transform: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .selected-card > .stButton > button {
    background: rgba(255,183,77,0.1) !important;
    border-color: rgba(255,183,77,0.45) !important;
    color: #ffb74d !important;
}
/* Points badge pill */
.pts-badge {
    background: #c8860a;
    color: #fff8e1;
    border-radius: 20px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
    display: inline-block;
    margin-top: 2px;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,183,77,0.25) !important;
    border-radius: 12px !important;
}
[data-testid="stChatInput"] textarea {
    color: #e8eaf0 !important;
    background: transparent !important;
}

/* Bot chat message */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: rgba(255,183,77,0.07) !important;
    border: 1px solid rgba(255,183,77,0.12) !important;
    border-radius: 14px !important;
    padding: 14px !important;
    margin-bottom: 8px !important;
}

/* User chat message */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(100,140,255,0.07) !important;
    border: 1px solid rgba(100,140,255,0.15) !important;
    border-radius: 14px !important;
    padding: 14px !important;
    margin-bottom: 8px !important;
}

/* Spinner */
[data-testid="stSpinner"] { color: #ffb74d !important; }

/* Info/success boxes */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
}
.stSuccess { background: rgba(76,175,80,0.15) !important; }
.stInfo { background: rgba(33,150,243,0.15) !important; }
.stWarning { background: rgba(255,183,77,0.15) !important; }

/* Progress bar */
.stProgress > div > div > div { background: linear-gradient(90deg, #ffb74d, #f57c00) !important; }

/* Markdown text */
.stMarkdown p, .stMarkdown li { color: #c8d0e0 !important; }

/* Audio recorder */
audio { border-radius: 8px; width: 100%; }

/* Main content buttons (Begin Review, Reset) — gold gradient */
[data-testid="stMain"] .stButton > button,
[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] .stButton > button {
    background: linear-gradient(135deg, #ffb74d, #f57c00) !important;
    color: #0d0d1a !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 28px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(255,183,77,0.3) !important;
}
[data-testid="stMain"] .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255,183,77,0.45) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Data Loading ──────────────────────────────────────────────────────────
@st.cache_resource
def load_data():
    with open("physical_landmarks_db.json", "r", encoding="utf-8") as f:
        landmarks = json.load(f)
    with open("new_bounties_db.json", "r", encoding="utf-8") as f:
        gaps = json.load(f)
    return landmarks, gaps

landmarks, gaps_db = load_data()
landmark_map = {p["eg_property_id"]: p for p in landmarks}
gap_map = {p["eg_property_id"]: p for p in gaps_db}
prop_ids = list(landmark_map.keys())

def retrieve_bucket_context(gap_data):
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

# ── Sidebar: Property Selection ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 20px 0 10px 0;'>
        <div style='font-size:42px;'>🏝️</div>
        <div style='font-size:22px; font-weight:700; color:#ffb74d; letter-spacing:1px;'>PropertyIQ</div>
        <div style='font-size:11px; color:#7a8aaa; margin-top:4px; letter-spacing:2px; text-transform:uppercase;'>by Expedia Group</div>
    </div>
    <hr style='border-color:rgba(255,183,77,0.15); margin: 10px 0 20px 0;'>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:12px; color:#7a8aaa; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>Property</div>", unsafe_allow_html=True)
    selected_prop = st.selectbox("", prop_ids, label_visibility="collapsed")

    if selected_prop:
        prop_landmarks = landmark_map[selected_prop]
        city = prop_landmarks.get("location", {}).get("city", "Unknown City")
        stars = prop_landmarks.get("location", {}).get("star_rating", "")
        star_display = "⭐" * int(float(stars)) if stars and stars != "" else ""
        st.markdown(f"""
        <div style='background:rgba(255,183,77,0.08); border:1px solid rgba(255,183,77,0.2); border-radius:10px; padding:12px; margin:10px 0;'>
            <div style='font-size:13px; color:#ffb74d; font-weight:600;'>📍 {city}</div>
            <div style='font-size:11px; color:#7a8aaa; margin-top:4px;'>{star_display} {selected_prop[:16]}...</div>
        </div>
        """, unsafe_allow_html=True)

        all_buckets_data = prop_landmarks.get("buckets", [])
        buckets = [b["frontend_name"] for b in all_buckets_data]
        if not buckets:
            st.warning("No landmarks found for this property.")
            st.stop()

        # Sort buckets by priority score (highest gap = most valuable to review)
        sorted_buckets = sorted(
            all_buckets_data,
            key=lambda x: x.get("bounty_priority_score", 0),
            reverse=True
        )

        if "selected_bucket_name" not in st.session_state:
            st.session_state.selected_bucket_name = sorted_buckets[0]["frontend_name"] if sorted_buckets else buckets[0]

        st.markdown("""
        <div style='margin: 16px 0 10px 0;'>
            <div style='font-size:15px; font-weight:700; color:#e8eaf0;'>Top gaps to fix</div>
            <div style='font-size:11px; color:#5a6a8a; margin-top:3px; line-height:1.5;'>Guide the user to the highest-value questions first, but always leave room for unprompted feedback.</div>
        </div>
        """, unsafe_allow_html=True)

        AREA_ICONS = {
            "Bedrooms": "🛏️", "Dining": "🍽️", "Reception": "🛎️",
            "Facilities": "🏊", "Recreation": "🏖️", "Location": "📍",
            "Pool": "🏊", "Spa": "💆", "Gym": "💪",
            "Services": "🛎️", "Bar": "🍸", "Garden": "🌿",
            "Other": "✨", "Miscellaneous": "📋", "Additional Feedback": "💬"
        }

        for bkt in sorted_buckets:
            b = bkt["frontend_name"]
            pts = int(bkt.get("allocated_points", 0))
            icon = next((v for k, v in AREA_ICONS.items() if k.lower() in b.lower()), "📍")
            is_selected = st.session_state.selected_bucket_name == b

            # Two-column card: [icon + name] [pts badge]
            col_name, col_pts = st.columns([3.5, 1])
            with col_name:
                clicked = st.button(
                    f"{icon}  {b}",
                    key=f"area_{b}",
                    use_container_width=True
                )
            with col_pts:
                badge_bg = "#c8860a" if is_selected else "rgba(200,134,10,0.55)"
                st.markdown(
                    f"<div style='padding-top:8px; text-align:right;'>"
                    f"<span style='background:{badge_bg}; color:#fff8e1; border-radius:20px; "
                    f"padding:5px 11px; font-size:12px; font-weight:700; white-space:nowrap;'>"
                    f"+{pts} pts</span></div>",
                    unsafe_allow_html=True
                )
            if clicked and st.session_state.selected_bucket_name != b:
                st.session_state.selected_bucket_name = b
                st.session_state.chat_steps = 0
                st.session_state.conversation = None
                st.session_state.messages = []
                st.rerun()
            # Add small divider gap between cards
            st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <hr style='border-color:rgba(255,183,77,0.1); margin: 20px 0 12px 0;'>
    <div style='font-size:10px; color:#3a4a6a; text-align:center;'>
        PropertyIQ © 2026 · Wharton Hack-AI-thon
    </div>
    """, unsafe_allow_html=True)

# ── Main Header ───────────────────────────────────────────────────────────
selected_bucket_name = st.session_state.get("selected_bucket_name", buckets[0] if buckets else "")
selected_bucket_data = next(
    (b for b in prop_landmarks["buckets"] if b["frontend_name"] == selected_bucket_name), None
)
selected_gap_data = None
if selected_prop in gap_map:
    selected_gap_data = next(
        (b for b in gap_map[selected_prop]["buckets"]
         if b["bucket_name"] == selected_bucket_data.get("bucket_name", "")), None
    ) if selected_bucket_data else None

# Compute priority for this bucket
priority = selected_bucket_data.get("bounty_priority_score", 0) if selected_bucket_data else 0
allocated = selected_bucket_data.get("allocated_points", 0) if selected_bucket_data else 0

area_icons_main = {
    "Bedrooms": "🛏️", "Dining": "🍽️", "Reception": "🛎️",
    "Facilities": "🏊", "Recreation": "🎯", "Location": "📍",
    "Pool": "🏊", "Spa": "💆", "Gym": "💪",
    "Services": "🤝", "Bar": "🍸", "Garden": "🌿",
    "Other": "✨", "Miscellaneous": "📋", "Additional Feedback": "💬"
}
main_icon = next((v for k, v in area_icons_main.items() if k.lower() in selected_bucket_name.lower()), "📍")

col_title, col_meta = st.columns([3, 1])
with col_title:
    st.markdown(f"""
    <div style='padding: 8px 0 4px 0;'>
        <div style='font-size:28px; font-weight:700; color:#ffffff; letter-spacing:-0.5px;'>
            {main_icon} {selected_bucket_name} <span style='color:#ffb74d;'>Review</span>
        </div>
        <div style='font-size:13px; color:#5a6a8a; margin-top:4px;'>
            Share your experience to help future travelers · Your insights are anonymous and valuable
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_meta:
    st.markdown(f"""
    <div style='background:rgba(255,183,77,0.08); border:1px solid rgba(255,183,77,0.2); border-radius:10px; padding:12px; text-align:center; margin-top:8px;'>
        <div style='font-size:22px; font-weight:700; color:#ffb74d;'>{int(allocated)}</div>
        <div style='font-size:10px; color:#7a8aaa; text-transform:uppercase; letter-spacing:1px;'>Points Available</div>
    </div>
    """, unsafe_allow_html=True)

# Progress indicator
steps_done = min(st.session_state.get("chat_steps", 0), 3)
step_labels = ["Start", "Your Experience", "Follow-up", "Final Thoughts"]
progress_html = "<div style='display:flex; gap:8px; align-items:center; margin: 16px 0 20px 0;'>"
for i, label in enumerate(step_labels):
    if i < steps_done:
        color, bg = "#ffb74d", "rgba(255,183,77,0.2)"
        dot = "✓"
    elif i == steps_done:
        color, bg = "#ffffff", "rgba(255,183,77,0.4)"
        dot = str(i + 1)
    else:
        color, bg = "#3a4a6a", "rgba(255,255,255,0.05)"
        dot = str(i + 1)
    progress_html += f"""
    <div style='display:flex; align-items:center; gap:6px;'>
        <div style='width:26px; height:26px; border-radius:50%; background:{bg}; border:1.5px solid {color};
                    display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:600; color:{color};'>{dot}</div>
        <span style='font-size:11px; color:{color}; font-weight:{"600" if i <= steps_done else "400"};'>{label}</span>
    </div>
    """
    if i < len(step_labels) - 1:
        line_color = "rgba(255,183,77,0.4)" if i < steps_done else "rgba(255,255,255,0.08)"
        progress_html += f"<div style='flex:1; height:1.5px; background:{line_color};'></div>"

progress_html += "</div>"
st.markdown(progress_html, unsafe_allow_html=True)
st.markdown("<hr style='border-color:rgba(255,255,255,0.06); margin-bottom:20px;'>", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────
for key, val in [("chat_steps", 0), ("conversation", None), ("messages", []), ("alt_str", "")]:
    if key not in st.session_state:
        st.session_state[key] = val

def reset_chat():
    st.session_state.chat_steps = 0
    st.session_state.conversation = None
    st.session_state.messages = []

# ── Start Button ──────────────────────────────────────────────────────────
if not st.session_state.conversation:
    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        start_clicked = st.button("✨ Begin Review", key="start_btn", use_container_width=True)
    with col_hint:
        st.markdown(f"<div style='color:#5a6a8a; font-size:13px; padding:10px 0;'>Takes less than 2 minutes · 3 simple questions</div>", unsafe_allow_html=True)

    if start_clicked:
        reset_chat()
        bucket_context = retrieve_bucket_context(selected_gap_data)
        st.session_state.context = bucket_context

        all_areas = [b["frontend_name"] for b in prop_landmarks.get("buckets", [])]
        alternative_areas = [a for a in all_areas if a != selected_bucket_name]
        alt_str = ", ".join(alternative_areas) if alternative_areas else "None available"
        st.session_state.alt_str = alt_str

        llm = ChatOpenAI(model="gpt-4o", temperature=0.4)

        template = """You are a sophisticated property concierge at a luxury hotel, having a warm and natural conversation with a returning guest about their recent stay.

Your mission: make the guest feel genuinely heard while naturally drawing out vivid, specific details about their experience that will help future guests.

AREA OF FOCUS: {bucket_name}
OTHER PROPERTY AREAS (for natural pivots if guest goes off-topic): {alternative_areas}

INTERNAL CONTEXT — Use to guide what details are worth exploring. Never mention these terms to the guest:
{historical_context}

YOUR VOICE & STYLE:
- Warm, curious, and genuinely interested — like a trusted 5-star hotel concierge
- One brief, natural acknowledgment before your question (max 1 sentence)
- Conversational and flowing — never robotic or survey-like
- If the guest mentions another area, acknowledge it warmly ("The spa, of course! I'd love to hear about that too.") then gently return to focus

ABSOLUTELY FORBIDDEN WORDS — Never use: "data", "record", "log", "capture", "extract", "gap", "conflict",
"validate", "bounty", "survey", "questionnaire", "form", "submission", "investigation"

SCOPE GUARD: If the guest asks something off-topic (coding, jokes, etc.), respond warmly:
"I'd love to keep our focus on your stay experience — you mentioned {bucket_name}?"

CONVERSATION HISTORY:
{history}

LATEST GUEST MESSAGE:
{input}

Respond as the concierge: one warm acknowledgment (max 10 words) + one clear question. Total under 35 words."""

        prompt = PromptTemplate(
            input_variables=["history", "input", "bucket_name", "historical_context", "alternative_areas"],
            template=template
        )
        partial_prompt = prompt.partial(
            bucket_name=selected_bucket_name,
            alternative_areas=alt_str,
            historical_context=st.session_state.context,
        )
        memory = ConversationBufferMemory(memory_key="history", input_key="input")
        initial_response = selected_bucket_data.get("static_question", "How was your experience?")
        memory.save_context({"input": "Begin"}, {"output": initial_response})

        conversation = ConversationChain(llm=llm, prompt=partial_prompt, memory=memory, verbose=False)
        st.session_state.conversation = conversation
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.rerun()

# ── Chat Display ──────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🏝️" if msg["role"] == "assistant" else "🧑"):
        st.markdown(msg["content"])

# ── Completion: Extraction + Verdict Cards ────────────────────────────────
if st.session_state.conversation and st.session_state.chat_steps >= 3:

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:linear-gradient(135deg,rgba(76,175,80,0.15),rgba(76,175,80,0.05));
                border:1px solid rgba(76,175,80,0.3); border-radius:14px; padding:16px 20px; margin-bottom:20px;'>
        <div style='font-size:18px; font-weight:700; color:#66bb6a;'>✓ Thank you for sharing your experience!</div>
        <div style='font-size:13px; color:#a5d6a7; margin-top:4px;'>Your unique insights are now helping future travelers make better decisions.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Part 1: Full-Conversation Extraction ─────────────────────
    with st.spinner("Analysing your insights..."):
        alt_areas_context = st.session_state.get("alt_str", "None")
        full_history = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]
        )
        extraction_prompt = f"""You are a precision property data extractor.

FOCAL LANDMARK: {selected_bucket_name}
ALL VALID PROPERTY AREAS: {alt_areas_context}

FULL CONVERSATION TRANSCRIPT:
{full_history}

TASK: Analyse the FULL conversation — ALL user messages.

CRITICAL REQUIREMENTS:
1. `verdicts`: Facts about the FOCAL LANDMARK ({selected_bucket_name}).
2. `cross_landmark_discoveries`: ANY mention of other areas (negative or positive, even briefly). Do NOT leave empty if user mentioned anything outside the focal landmark.
3. `freehand_insights`: General qualitative impressions that don't map to a specific area.
4. Return RAW JSON only. No markdown fences.

JSON SCHEMA:
{{
  "landmark_name": "{selected_bucket_name}",
  "verdicts": [
    {{
      "sub_feature": "<string>",
      "resolved_conflict": <true/false>,
      "discovery": "<string summary>",
      "sentiment": "positive|negative|neutral"
    }}
  ],
  "cross_landmark_discoveries": [
    {{
      "area_name": "<must match one of: {alt_areas_context}>",
      "fact_captured": "<exact nature of finding>",
      "sentiment": "positive|negative|neutral"
    }}
  ],
  "freehand_insights": "<general vibe or qualitative observation>",
  "user_engagement": "high|low",
  "data_quality": "reliable|unclear"
}}"""
        raw_analysis = st.session_state.conversation.predict(input=extraction_prompt)
        final_analysis_str = raw_analysis.replace("```json", "").replace("```", "").strip()

    # ── Part 2: Freehand Classifier ──────────────────────────────
    user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    freehand_text = user_msgs[-1] if user_msgs else ""
    freehand_classifications = []

    if freehand_text and len(freehand_text.split()) > 3:
        with st.spinner("Mapping additional comments to property areas..."):
            classifier_prompt = f"""You are a property review classifier.

A hotel guest left this comment:
"{freehand_text}"

The property has these known areas: {alt_areas_context}, {selected_bucket_name}

TASK: Split the comment into individual facts. For each fact map it to the most relevant property area, assign sentiment, and write a clean structured fact.

Return ONLY a raw JSON array (no markdown):
[
  {{
    "original_text": "<verbatim portion>",
    "mapped_bucket": "<area from the list>",
    "fact": "<clean structured finding>",
    "sentiment": "positive|negative|neutral"
  }}
]
If no useful facts, return: []"""
            raw_freehand = st.session_state.conversation.predict(input=classifier_prompt)
            clean_freehand = raw_freehand.replace("```json", "").replace("```", "").strip()
            try:
                freehand_classifications = json.loads(clean_freehand)
            except json.JSONDecodeError:
                freehand_classifications = []

    # ── Merge ────────────────────────────────────────────────────
    try:
        findings_obj = json.loads(final_analysis_str)
    except json.JSONDecodeError:
        findings_obj = {
            "landmark_name": selected_bucket_name,
            "verdicts": [],
            "cross_landmark_discoveries": [],
            "freehand_insights": ""
        }

    if freehand_classifications:
        findings_obj["freehand_classifications"] = freehand_classifications
        existing_areas = {c.get("area_name", "") for c in findings_obj.get("cross_landmark_discoveries", [])}
        for fc in freehand_classifications:
            mapped = fc.get("mapped_bucket", "")
            if mapped and mapped != selected_bucket_name and mapped not in existing_areas:
                findings_obj.setdefault("cross_landmark_discoveries", []).append({
                    "area_name": mapped,
                    "fact_captured": fc.get("fact", ""),
                    "sentiment": fc.get("sentiment", "neutral")
                })
                existing_areas.add(mapped)

    # ── Premium Verdict Cards (NO raw JSON) ──────────────────────
    st.markdown("### 📋 Your Insights Summary")

    # Primary verdicts
    verdicts = findings_obj.get("verdicts", [])
    if verdicts:
        st.markdown(f"**{main_icon} {selected_bucket_name}**")
        for v in verdicts:
            snt = v.get("sentiment", "neutral")
            snt_color = {"positive": "#66bb6a", "negative": "#ef5350", "neutral": "#42a5f5"}.get(snt, "#42a5f5")
            snt_icon = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(snt, "→")
            resolved = "✓ Resolved" if v.get("resolved_conflict") else "· Noted"
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);
     border-left:3px solid {snt_color}; border-radius:10px; padding:12px 16px; margin-bottom:8px;'>
    <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
        <div>
            <div style='font-size:13px; font-weight:600; color:#c8d0e0;'>{v.get("sub_feature", "General")}</div>
            <div style='font-size:13px; color:#8a9ab5; margin-top:4px;'>{v.get("discovery", "")}</div>
        </div>
        <div style='text-align:right; flex-shrink:0; margin-left:12px;'>
            <div style='font-size:12px; color:{snt_color}; font-weight:600;'>{snt_icon} {snt.capitalize()}</div>
            <div style='font-size:10px; color:#4a5a7a; margin-top:2px;'>{resolved}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    # Cross-landmark discoveries
    cross = findings_obj.get("cross_landmark_discoveries", [])
    if cross:
        st.markdown("**🔀 Additional Property Insights**")
        for c in cross:
            snt = c.get("sentiment", "neutral")
            snt_color = {"positive": "#66bb6a", "negative": "#ef5350", "neutral": "#42a5f5"}.get(snt, "#42a5f5")
            snt_icon = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(snt, "→")
            area_icon = next((v for k, v in area_icons_main.items() if k.lower() in c.get("area_name", "").lower()), "📍")
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06);
     border-left:3px solid {snt_color}; border-radius:10px; padding:12px 16px; margin-bottom:8px;'>
    <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
        <div>
            <div style='font-size:11px; font-weight:600; color:{snt_color}; text-transform:uppercase; letter-spacing:1px;'>{area_icon} {c.get("area_name", "")}</div>
            <div style='font-size:13px; color:#8a9ab5; margin-top:4px;'>{c.get("fact_captured", "")}</div>
        </div>
        <div style='font-size:12px; color:{snt_color}; font-weight:600; flex-shrink:0; margin-left:12px;'>{snt_icon} {snt.capitalize()}</div>
    </div>
</div>
""", unsafe_allow_html=True)

    # Freehand insight
    freehand_insight = findings_obj.get("freehand_insights", "")
    if freehand_insight and len(freehand_insight) > 10:
        st.markdown(f"""
<div style='background:rgba(255,183,77,0.06); border:1px solid rgba(255,183,77,0.2);
     border-radius:10px; padding:14px 16px; margin-top:8px;'>
    <div style='font-size:11px; font-weight:600; color:#ffb74d; text-transform:uppercase; letter-spacing:1px;'>💬 Overall Impression</div>
    <div style='font-size:13px; color:#c8d0e0; margin-top:6px; font-style:italic;'>"{freehand_insight}"</div>
</div>
""", unsafe_allow_html=True)

    # Engagement badge
    engagement = findings_obj.get("user_engagement", "low")
    quality = findings_obj.get("data_quality", "unclear")
    pts_earned = allocated if engagement == "high" else allocated // 2
    st.markdown(f"""
<div style='display:flex; gap:12px; margin-top:16px; flex-wrap:wrap;'>
    <div style='background:rgba(255,183,77,0.1); border:1px solid rgba(255,183,77,0.25); border-radius:8px; padding:10px 16px;'>
        <div style='font-size:18px; font-weight:700; color:#ffb74d;'>🪙 +{pts_earned}</div>
        <div style='font-size:10px; color:#7a8aaa; text-transform:uppercase; letter-spacing:1px;'>Points Earned</div>
    </div>
    <div style='background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:10px 16px;'>
        <div style='font-size:13px; font-weight:600; color:#c8d0e0;'>{"⭐ High" if engagement == "high" else "📊 Standard"} Engagement</div>
        <div style='font-size:10px; color:#7a8aaa; margin-top:2px;'>{"Reliable" if quality == "reliable" else "Logged"} data quality</div>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Part 3: Save & Auto-Update Databases ─────────────────────
    export_data = {
        "eg_property_id": selected_prop,
        "landmark": selected_bucket_name,
        "conversation_status": "complete",
        "findings": findings_obj
    }
    with open("gamified_responses.json", "a") as f:
        json.dump(export_data, f)
        f.write("\n")

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("update_databases", "update_databases.py")
        update_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(update_mod)
        n_updates = update_mod.run_update()
        st.markdown(f"""
<div style='background:rgba(33,150,243,0.1); border:1px solid rgba(33,150,243,0.25); border-radius:10px; padding:12px 16px; margin-top:16px;'>
    <div style='font-size:13px; color:#64b5f6;'>✅ Property database updated · {n_updates} data points improved for future guests.</div>
</div>
""", unsafe_allow_html=True)
    except Exception as db_err:
        st.markdown("""
<div style='background:rgba(33,150,243,0.1); border:1px solid rgba(33,150,243,0.25); border-radius:10px; padding:12px 16px; margin-top:16px;'>
    <div style='font-size:13px; color:#64b5f6;'>✅ Your insights have been captured and saved.</div>
</div>
""", unsafe_allow_html=True)

    # Reset button
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    if st.button("↩ Review Another Area", key="reset_btn"):
        reset_chat()
        st.rerun()

# ── Active Chat + Voice Input ─────────────────────────────────────────────
elif st.session_state.conversation:

    col_chat, col_voice = st.columns([5, 1])

    with col_voice:
        st.markdown("<div style='padding-top:8px;'>", unsafe_allow_html=True)
        try:
            from audio_recorder_streamlit import audio_recorder
            audio_bytes = audio_recorder(
                text="",
                recording_color="#ffb74d",
                neutral_color="#3a4a6a",
                icon_name="microphone",
                icon_size="2x",
                pause_threshold=2.5,
                key="voice_recorder"
            )
            if audio_bytes:
                with st.spinner("Transcribing..."):
                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = "voice_input.wav"
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en"
                    )
                    transcribed_text = transcript.text.strip()
                    if transcribed_text:
                        st.session_state["voice_input"] = transcribed_text
                        st.rerun()
        except ImportError:
            pass
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chat:
        # Pre-fill from voice if available
        voice_prefill = st.session_state.pop("voice_input", "")

        if voice_prefill:
            # Display it as a user message and process
            user_input = voice_prefill
            st.session_state.messages.append({"role": "user", "content": f"🎤 {user_input}"})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(f"🎤 *{user_input}*")
        else:
            user_input_raw = st.chat_input("Share your thoughts... or tap 🎙️ to speak", key="chat_text")
            if user_input_raw:
                user_input = user_input_raw
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user", avatar="🧑"):
                    st.markdown(user_input)
            else:
                user_input = None

    if user_input:
        # ══════════════════════════════════════════════════════════════════
        # SURVEY STATE MACHINE  (chat_steps is incremented FIRST each turn)
        #
        #  Q1 (static, from DB) ── shown on "Begin Review" click
        #        │
        #  User answers Q1 ──► chat_steps = 1
        #        │
        #        ├─ Vague (≤2 words) or "I don't know"
        #        │       └─► LLM generates warm pivot that doubles as freehand Q
        #        │           chat_steps forced to 2
        #        │
        #        ├─ Detailed ──► LLM decides:
        #        │       ├─ GAPS_RESOLVED ──► LLM freehand Q, chat_steps forced to 2
        #        │       └─ Still gaps    ──► LLM follow-up Q, chat_steps stays 1
        #        │
        #  User answers follow-up / pivot ──► chat_steps = 2
        #        │
        #        └─► LLM generates freehand open-invitation Q  (always fires here)
        #
        #  User answers freehand ──► chat_steps = 3
        #        │
        #        └─► LLM warm closing message ──► chat_steps = 10 → COMPLETE
        # ══════════════════════════════════════════════════════════════════
        st.session_state.chat_steps += 1

        with st.chat_message("assistant", avatar="🏝️"):
            with st.spinner(""):

                word_count = len(user_input.split())

                injection_keywords = [
                    "write code", "print(", "def ", "import ", "python", "script", "ignore instructions"
                ]
                is_injection = any(k in user_input.lower() for k in injection_keywords)

                no_knowledge_phrases = [
                    "don't know", "dont know", "didn't use", "didnt use", "not sure",
                    "can't remember", "cant remember", "no idea", "haven't been",
                    "havent been", "didn't go", "didnt go", "never used", "n/a", "skip",
                    "nothing to say", "nothing to add", "nothing to share", "have nothing",
                    "nothing about", "no comment", "no opinion", "no feedback",
                    "didn't visit", "didnt visit", "didn't try", "didnt try",
                    "not applicable", "not relevant", "no experience"
                ]
                is_no_knowledge = any(p in user_input.lower() for p in no_knowledge_phrases)

                # ── STEP 3 : freehand answered → warm close → COMPLETE ────
                if st.session_state.chat_steps >= 3:
                    closing_nudge = (
                        "[CONCIERGE GUIDANCE — GRACEFUL CLOSE]\n\n"
                        "The guest has finished sharing. Write 1-2 warm sentences that:\n"
                        "- Thank them naturally (not gushing)\n"
                        "- Convey their perspective will genuinely help future guests\n"
                        "Forbidden words: data, record, survey, submitted, logged, captured\n"
                        "Output ONLY your closing. Under 30 words. No questions."
                    )
                    response_text = st.session_state.conversation.predict(input=closing_nudge)
                    st.session_state.chat_steps = 10   # triggers extraction UI

                # ── STEP 2 : always show freehand open-invitation Q ───────
                elif st.session_state.chat_steps == 2:
                    freehand_nudge = (
                        f"[CONCIERGE GUIDANCE — OPEN INVITATION]\n\n"
                        f"The guest has finished on {selected_bucket_name}. Ask a single warm, broad question "
                        f"inviting them to share any other impression from their stay — any area, any topic. "
                        f"Feel like a concierge wrapping up a pleasant chat, not a form.\n"
                        f"Output ONLY your question. Under 25 words."
                    )
                    response_text = st.session_state.conversation.predict(input=freehand_nudge)

                # ── STEP 1 : first user reply — dynamic stopping ──────────
                else:
                    if is_injection:
                        response_text = st.session_state.conversation.predict(
                            input=(
                                f"{user_input}\n\n"
                                f"[CONCIERGE GUIDANCE: Guest went off-topic. Warmly redirect back to "
                                f"their experience at {selected_bucket_name}. One sentence + original question. Stay friendly.]"
                            )
                        )

                    elif word_count <= 2 or is_no_knowledge:
                        # Short/IDK → skip follow-up; this pivot response IS the freehand Q
                        response_text = st.session_state.conversation.predict(
                            input=(
                                f"[CONCIERGE GUIDANCE — GENTLE PIVOT]\n\n"
                                f"Guest gave a brief/uncertain response: \"{user_input}\"\n"
                                f"Write a warm 1-sentence acknowledgment (no judgment) then ask an open "
                                f"invitation question for any other impression from their stay.\n"
                                f"Output ONLY your acknowledgment + question. Under 30 words."
                            )
                        )
                        st.session_state.chat_steps = 2   # next reply → step 3 → complete

                    else:
                        # Detailed reply → LLM decides: follow-up OR skip straight to freehand
                        llm_decision = st.session_state.conversation.predict(
                            input=(
                                f"{user_input}\n\n"
                                f"[CONCIERGE GUIDANCE — FOLLOW-UP DECISION]\n"
                                f"Topic: {selected_bucket_name}\n\n"
                                f"Decide:\n"
                                f"• If the guest's response is comprehensive (covers quality, timing, availability, "
                                f"cost, comparison — whatever applies) → reply with ONLY the token: GAPS_RESOLVED\n"
                                f"• If ONE important dimension is still missing → write a warm concierge follow-up:\n"
                                f"  - One genuine acknowledgment (≤8 words) + one specific question\n"
                                f"  - Total ≤30 words. Sound like a curious concierge, not a survey.\n"
                                f"  - Forbidden: data, record, gap, validate, extract\n\n"
                                f"Output ONLY 'GAPS_RESOLVED' or your acknowledgment + question."
                            )
                        )

                        if llm_decision.strip().upper().startswith("GAPS_RESOLVED"):
                            # No follow-up needed → jump straight to freehand Q
                            response_text = st.session_state.conversation.predict(
                                input=(
                                    f"[CONCIERGE GUIDANCE — OPEN INVITATION]\n\n"
                                    f"Guest covered {selected_bucket_name} well. Ask a warm, broad open-invitation "
                                    f"question for any other impression from their stay — any area.\n"
                                    f"Output ONLY your question. Under 25 words."
                                )
                            )
                            st.session_state.chat_steps = 2   # next reply → step 3 → complete
                        else:
                            # Follow-up needed → show it; next reply → step 2 → freehand
                            response_text = llm_decision

                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.rerun()
