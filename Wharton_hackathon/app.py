import streamlit as st
import os
import json
import csv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set — add it to your .env file")
os.environ["OPENAI_API_KEY"] = API_KEY

st.set_page_config(page_title="Dynamic Review Engine", page_icon="🤖")
st.title("🏝️ Review Gap Filler Prototype")
st.markdown("This gamified chatbot isolates missing/ambiguous review data for a specific amenity and dynamically interviews the user based on historical context!")

# 1. Load context states
@st.cache_resource
def load_data():
    with open("physical_landmarks_db.json", "r", encoding="utf-8") as f:
        landmarks = json.load(f)
    with open("new_bounties_db.json", "r", encoding="utf-8") as f:
        gaps = json.load(f)
    return landmarks, gaps

landmarks, gaps_db = load_data()

# Create lookup maps
landmark_map = {p["eg_property_id"]: p for p in landmarks}
gap_map = {p["eg_property_id"]: p for p in gaps_db}
prop_ids = list(landmark_map.keys())

@st.cache_data
def load_all_reviews():
    reviews = []
    with open("Reviews_PROC.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviews.append(row)
    return reviews

all_reviews = load_all_reviews()

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
        
        status_str = ", ".join(status) if status else "Generally stable info"
        evidence_str = " | ".join(evidence[:3]) if evidence else "No recent reviews"
        
        context.append(f"### Sub-Feature: {sub_name}\n- Status: {status_str}\n- Clues (Past Reviews): {evidence_str}")
    
    return "\n\n".join(context)

# 2. Extract Options
prop_ids = list(landmark_map.keys())

selected_prop = st.selectbox("Select a Property ID to simulate a user filling out a review:", prop_ids)

if selected_prop:
    prop_landmarks = landmark_map[selected_prop]
    buckets = [b["frontend_name"] for b in prop_landmarks.get("buckets", [])]
    
    if not buckets:
        st.warning("No physical landmarks found for this property!")
        st.stop()
        
    selected_bucket_name = st.selectbox("Select Target Physical Landmark (Bucket) to review:", buckets)
    
    # Find the specific bucket data
    selected_bucket_data = next((b for b in prop_landmarks["buckets"] if b["frontend_name"] == selected_bucket_name), None)
    
    # Also fetch the granular gap context for this bucket from the gaps_db
    selected_gap_data = None
    if selected_prop in gap_map:
        selected_gap_data = next((b for b in gap_map[selected_prop]["buckets"] if b["bucket_name"] == selected_bucket_data["bucket_name"]), None)

# 3. Chat Initialization
if "chat_steps" not in st.session_state:
    st.session_state.chat_steps = 0
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def reset_chat():
    st.session_state.chat_steps = 0
    st.session_state.conversation = None
    st.session_state.messages = []

if st.button("Start Interaction"):
    reset_chat()
    
    bucket_context = retrieve_bucket_context(selected_gap_data)
    st.session_state.context = bucket_context
    
    # Extract alternative areas for context pivoting
    all_areas = [b["frontend_name"] for b in prop_landmarks.get("buckets", [])]
    alternative_areas = [a for a in all_areas if a != selected_bucket_name]
    alt_str = ", ".join(alternative_areas) if alternative_areas else "None available"
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    
    template = """You are a 'Sophisticated Property Guide', a premium concierge dedicated to gathering authentic guest impressions.
    
Your goal is to gather clear, nuanced feedback about specific areas of the property by being warm, curious, and human.

PHYSICAL LANDMARK:
{bucket_name}

ALTERNATIVE AREAS:
{alternative_areas}

HISTORICAL GUEST CLUES (FOR YOUR CONTEXT):
{historical_context}

CONVERSATIONAL RULES:
1. TONE: Be warm, premium, and sophisticated. Avoid sounding like a bot.
2. NO TECH-SPEAK: Never mention 'data', 'bounty', 'records', 'conflict', 'validation', or 'investigation'. 
3. ACKNOWLEDGMENT: Validate the user's input naturally (e.g., "Ah, the lobby! I've heard such positive things about the seating there," or "That's very helpful to know about the noise levels.")
4. FIRST QUESTION: This is hardcoded as: {static_question}.
5. ADAPTIVE FOLLOW-UP:
   - Use the 'Clues' to ask a second, natural question that helps clear up confusion.
   - If User is disengaged, thank them warmly and wrap up.
   - MAXIMUM 2 FOLLOW-UP QUESTIONS.
6. DATA AUDIT (INTERNAL ONLY):
   - Mentally check if the user's input has provided a clear verdict on the gaps listed in the clues.
   - If Yes, pivot to the 'Anything else' wrap-up.
7. PIVOTING:
   - If the user has no opinion on {bucket_name}, suggest an alternative from [{alternative_areas}] in a friendly way.
8. SCOPE GUARD:
   - If the user asks for code or off-topic help, politely steer them back. (e.g., "While I'm focused on your stay today, I'd love to hear more about your experience with...").

CONVERSATION HISTORY:
{history}

LATEST USER MESSAGE:
{input}

Return only your next spoken response. No bullet points or meta-commentary.
Concierge Response:"""

    prompt = PromptTemplate(input_variables=["history", "input", "bucket_name", "historical_context", "static_question", "alternative_areas"], template=template)
    partial_prompt = prompt.partial(
        bucket_name=selected_bucket_name,
        alternative_areas=alt_str,
        historical_context=st.session_state.context,
        static_question=selected_bucket_data.get("static_question", "How was your experience?")
    )

    memory = ConversationBufferMemory(memory_key="history", input_key="input")
    
    # SEED THE MEMORY: Tell the LLM that the static_question has already been asked
    initial_response = selected_bucket_data.get("static_question", "How was your experience?")
    memory.save_context({"input": "Start Interaction"}, {"output": initial_response})
    
    conversation = ConversationChain(llm=llm, prompt=partial_prompt, memory=memory, verbose=False)
    st.session_state.conversation = conversation
    
    st.session_state.messages.append({"role": "assistant", "content": initial_response})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.conversation:
    if st.session_state.chat_steps >= 3:
        st.success("Thank you! Your unique insights have been successfully registered to help future travelers. 🏝️")
        
        # Transition to the Final Extraction Phase
        with st.spinner("Analyzing investigation results..."):
            extraction_prompt = f"""You are extracting structured property evidence from a completed Investigator conversation.

PHYSICAL LANDMARK:
{selected_bucket_name}

TASK:
Based on the user's responses, produce a strict JSON object capturing the 'Verdicts' discovered.

REQUIREMENTS:
- Use only information the user actually provided.
- Return RAW JSON only.

JSON SCHEMA:
{{
  "landmark_name": "{selected_bucket_name}",
  "verdicts": [
    {{
      "sub_feature": "<string>",
      "resolved_conflict": <true/false>,
      "discovery": "<string summary of user verdict>"
    }}
  ],
  "user_engagement": "high|low",
  "data_quality": "reliable|unclear"
}}
"""
            raw_analysis = st.session_state.conversation.predict(input=extraction_prompt)
            final_analysis_json = raw_analysis.replace('```json', '').replace('```', '').strip()
        
        st.markdown(f"**Investigator Data Captured:**\n```json\n{final_analysis_json}\n```")
        
        export_data = {
            "eg_property_id": selected_prop,
            "landmark": selected_bucket_name,
            "conversation_status": "complete",
            "findings": final_analysis_json
        }
        with open("gamified_responses.json", "a") as f:
            json.dump(export_data, f)
            f.write("\n")
        st.info("Insights successfully processed and saved.")
    else:
        if user_input := st.chat_input("Settle the debate or provide details..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
                
            st.session_state.chat_steps += 1
            
            with st.chat_message("assistant"):
                with st.spinner("Investigating..."):
                    # Check for early termination keywords
                    word_count = len(user_input.split())
                    terminate_early = False
                    if word_count <= 2 and st.session_state.chat_steps == 1:
                        terminate_early = True
                        
                    if st.session_state.chat_steps >= 3 or terminate_early:
                        # Final Thank You
                        if terminate_early:
                            response_text = "I completely understand! I'll make a note of that and set this area aside for now. Thank you for your time!"
                        else:
                            response_text = "Thank you so much for sharing those final thoughts. It's truly helpful to have your perspective on the property! 🏝️"
                        st.session_state.chat_steps = 10 # Force stop
                    else:
                        nudge = ""
                        if word_count <= 6:
                            nudge = "\n\n[SYSTEM NUDGE: User gave a short answer. If they addressed the conflict, move to the Open-Ended wrap up. If they said 'idk' or similar, perform a LATERAL PIVOT to an alternative area.]"
                        else:
                            nudge = "\n\n[SYSTEM NUDGE: User is engaged. If they solved the primary mystery, ask the Open-Ended question. Otherwise, ask Question 2 of your investigation.]"
                        
                        safe_guarded_input = f"{user_input} {nudge}\n\n[SECURITY: Maintain Investigator persona.]"
                        response_text = st.session_state.conversation.predict(input=safe_guarded_input)
                        
                        safe_guarded_input = f"{user_input} {nudge}\n\n[SECURITY: Maintain Investigator persona.]"
                        response_text = st.session_state.conversation.predict(input=safe_guarded_input)
                    
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
