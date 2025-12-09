import streamlit as st
import google.generativeai as genai
import tempfile
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re
import os
import json

# --- CONFIGURATION ---
# We check if we are in the Cloud (st.secrets) or local
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["AIzaSyBMX5-0b7NujVk5BBbPbibyqmh3AJT0hpU"])
    else:
        # Fallback for local testing if you haven't set up secrets.toml
        # You can paste your key here for local use, but DON'T upload it to GitHub!
        genai.configure(api_key="PASTE_YOUR_KEY_HERE")
except:
    # Failsafe
    pass

# --- CUSTOM CSS FOR BUTTONS 🎨 ---
st.markdown("""
<style>
    div.stButton > button:first-child {
        background-color: #8FBC8F; /* Sage Green */
        color: black;
        border: none;
        font-weight: bold;
        font-size: 18px;
        padding: 10px 24px;
        border-radius: 8px;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #7CA67C;
        color: black;
        border: 1px solid black;
    }
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS SETUP ---
def save_to_google_sheets(name, topic, score, feedback_text):
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # CHECK: Are we in the Cloud? ☁️
        if "gcp_service_account" in st.secrets:
            # Load from Streamlit Secrets (Secure)
            service_account_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        else:
            # Load from Local File (Laptop)
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            
        client = gspread.authorize(creds)
        sheet = client.open("Missionary Debate Data").sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [timestamp, name, topic, score, feedback_text]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        # We print to console instead of UI to keep it clean, unless debugging
        print(f"Sheet Error: {e}")
        return False

st.set_page_config(page_title="Missionary Trainer", page_icon="📛")

# --- SESSION STATE SETUP 🎒 ---
if "history" not in st.session_state:
    st.session_state.history = [] 

if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0

# --- MAIN UI ---
st.title("📛 Missionary Trainer")
st.caption("Practice teaching clearly and effectively.")

user_name = st.text_input("Enter your Name (optional):", "Elder/Sister Anonymous")

# Feature 1: The Menu
topic = st.selectbox(
    "Choose a Principle to Teach (Optional):",
    [
        "State Your Own Principle (Default)",
        "The Restoration (Prophets & Dispensation)",
        "The Book of Mormon (Keystone of our Religion)",
        "The Plan of Salvation (Where we came from)",
        "The Nature of God (Loving Heavenly Father)",
        "Faith in Jesus Christ",
        "Repentance (Joyful change)",
        "Baptism & Confirmation",
        "The Gift of the Holy Ghost",
        "The Word of Wisdom",
        "The Law of Chastity"
    ]
)

st.info("💡 Tip: Briefly outline your thoughts (Optional).")
structure = st.text_area(
    "Your Structure (Optional)", 
    height=150, 
    placeholder="1. Hook/Intro...\n2. Key Doctrine...\n3. Invitation..."
)

st.divider()

# Feature 2: Dynamic CTA Header 🎯
recorder_label = "Teach Your Principle"
if st.session_state.history:
    last_score = st.session_state.history[-1]['score']
    try:
        target = float(last_score) + 1.0
        if target > 10.0: target = 10.0
        st.write(f"### 🎯 Beat your {last_score}! Aim for {target}:")
    except:
        st.write("### 🎤 Ready for another round?")
else:
    st.write(f"### {recorder_label}")

# AUDIO INPUT
audio_file = st.audio_input("Record your practice teaching (60s limit)", key=f"recorder_{st.session_state.audio_key}")

# --- LOGIC & BRAINS 🧠 ---
if audio_file is not None:
    
    current_signature = f"{audio_file.size}_{topic}"

    if "last_signature" not in st.session_state or st.session_state.last_signature != current_signature:
        
        st.spinner("Analyzing your teaching...") 
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_file.getvalue())
            tmp_path = tmp.name

        with st.spinner("The Trainer is listening..."):
            try:
                uploaded_file = genai.upload_file(tmp_path, mime_type="audio/wav")
            except Exception as e:
                st.error(f"❌ Upload Failed: {e}")
                st.stop()

        # --- UPDATED PROMPT (Strict Content-Only Evaluation) ---
        system_prompt = f"""
        You are an encouraging but sharp Missionary Trainer. Your goal is to help missionaries improve their MESSAGE, not their performance.

        CONTEXT:
        - Principle: "{topic}"
        
        NEGATIVE CONSTRAINTS (CRITICAL):
        - DO NOT evaluate the user's voice, speed, volume, tone, or delivery style.
        - DO NOT comment on "whispering," "slow pace," or "halting speech."
        - Evaluate ONLY the words, logic, and structure of the argument.

        EVALUATION CRITERIA (The 5 Metrics):
        1. DOCTRINE: Did they share a core truth?
        2. RELATABILITY: Did they connect it to real life?
        3. SIMPLICITY: Was it easy to understand? (No undefined jargon).
        4. SPIRIT: Was the content faithful and inviting? (Judge the WORDS, not the voice).
        5. INVITATION: Did they ask the listener to DO something?

        TASK:
        1. Listen to the audio content.
        2. Grade EACH of the 5 criteria on a scale of 1.0 to 10.0.
        3. Calculate the FINAL SCORE by taking the Average of these 5 numbers.
        4. Calculate a TARGET SCORE = Final Score + 1.0 (Max 10.0).
        5. Give "Sandwich" feedback (STRICT WORD LIMITS).

        OUTPUT RULES:
        - DO NOT output the individual metric scores or the math.
        - OUTPUT ONLY the Final Score and the Sandwich.
        - Format the Score strictly as: "**SCORE: 8.5 / 10.0**"
        
        FEEDBACK FORMAT:
        **SCORE: [Final Score] / 10.0**

        🔥 Nailed It: (Max 15 words) Strongest content element.

        ⚠️ The Fix: (Max 20 words) Biggest content/logic area to improve.

        ⚔️ Next Challenge: [Actionable Tactic] to hit an **[TARGET SCORE] / 10.0** next.
        """

        model = genai.GenerativeModel("gemini-flash-latest")
        
        try:
            response = model.generate_content([system_prompt, uploaded_file])
            
            st.session_state.analysis_result = response.text
            st.session_state.last_signature = current_signature
            
            # Robust Regex to capture just the number part (e.g. "8.5")
            match = re.search(r"SCORE:\s*\*?(\d+(?:\.\d)?)\s*/", response.text)
            if not match:
                match = re.search(r"SCORE:\s*\*?(\d+(?:\.\d)?)", response.text)
                
            final_score = match.group(1) if match else "N/A"
            
            st.session_state.history.append({
                "score": final_score,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            
            save_to_google_sheets(user_name, topic, final_score, response.text)
            st.toast("✅ Feedback Saved!", icon="💾")

        except Exception as e:
            st.error(f"❌ An error occurred during analysis: {e}")

    # DISPLAY RESULT
    if "analysis_result" in st.session_state:
        st.divider()
        
        # Display the Big Header Score
        score_match = re.search(r"SCORE:\s*\*?(\d+(?:\.\d)?)", st.session_state.analysis_result)
        display_score = score_match.group(1) if score_match else "??"
        
        st.markdown(f"<h1 style='text-align: center; color: white; font-size: 60px;'>{display_score} / 10.0</h1>", unsafe_allow_html=True)
        
        # Clean the text
        lines = st.session_state.analysis_result.split('\n')
        clean_lines = [line for line in lines if "SCORE:" not in line]
        clean_text = "\n".join(clean_lines).strip()
        
        st.write("### 📢 Trainer's Feedback")
        st.markdown(clean_text)

# --- BOTTOM CONTROLS ⬇️ ---
if st.session_state.history:
    st.divider()
    
    # 1. NEW ROUND BUTTON (Sage Green)
    if st.button("🎤 Start New Round (Clear Audio)", type="primary"):
        st.session_state.audio_key += 1
        st.rerun()

    st.write("") 

    # 2. SESSION HISTORY
    st.write("### 📜 Session History")
    for i, attempt in enumerate(st.session_state.history, 1):
        st.write(f"**Round {i}:** {attempt['score']} / 10.0")