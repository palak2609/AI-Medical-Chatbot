import os
import tempfile
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── API key guard — fail fast with a clear message ────────────────────────────
_missing = [k for k in ("GROQ_API_KEY", "PINECONE_API_KEY") if not os.getenv(k)]
if _missing:
    st.set_page_config(page_title="AI Medical Assistant", page_icon="🏥")
    st.error(
        f"**Missing API keys:** {', '.join(_missing)}\n\n"
        "Add them to your `.env` file and restart the app:\n"
        "```\nGROQ_API_KEY=your_key_here\nPINECONE_API_KEY=your_key_here\n```"
    )
    st.stop()

from src.multimodal      import process
from src.context_engine  import get_user_location, get_weather, get_season, geocode_city
from src.first_aid       import get_card as get_first_aid_card, all_cards, render_html as fa_html
from src.history         import save_session, load_history, clear_history
from src.pdf_report      import generate_report
from src.translator      import LANGUAGES, to_english, from_english
from src.report_analyzer      import analyze_pdf, analyze_image_report
from src.prescription_analyzer import analyze_prescription
from src.voice_output          import text_to_speech
from src.vitals                import METRICS, status, status_color
from src.drug_interaction      import check_interaction
from src.database              import (is_cloud, save_consultation, get_consultations,
                                       save_vital, get_vitals, save_prescription,
                                       save_mood, get_today_mood, get_mood_history,
                                       save_food_log, get_food_logs, get_today_calories)
from src.auth                  import login as auth_login, register as auth_register
from src.food_analyzer         import analyze_food_text, analyze_food_photo

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Medical Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══════════════════════════════════════════════════════════════════════════
   ANIMATIONS
══════════════════════════════════════════════════════════════════════════ */
@keyframes pulse-emergency {
    0%,100% { box-shadow: 0 0 0 0 rgba(255,75,75,.0),  0 0 12px rgba(255,75,75,.3); }
    50%      { box-shadow: 0 0 0 6px rgba(255,75,75,.0), 0 0 28px rgba(255,75,75,.7); }
}
@keyframes pulse-severe {
    0%,100% { box-shadow: 0 0 8px rgba(255,140,0,.2); }
    50%      { box-shadow: 0 0 20px rgba(255,140,0,.55); }
}
@keyframes fadeInUp {
    from { opacity:0; transform:translateY(10px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position:  400px 0; }
}
@keyframes spin-ring {
    to { transform: rotate(360deg); }
}

/* ══════════════════════════════════════════════════════════════════════════
   BASE
══════════════════════════════════════════════════════════════════════════ */
.stApp {
    background: radial-gradient(ellipse 80% 60% at 10% 0%, #0D1B2A 0%, #0D1117 55%, #060B10 100%);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
}
section.main > div { padding-bottom: 120px; }
hr { border-color: #1C2128 !important; opacity: 1 !important; }

/* ══════════════════════════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #010409 0%, #040B12 100%) !important;
    border-right: 1px solid #1C2128 !important;
}
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #E6EDF3 !important; font-size: 17px !important; font-weight: 700 !important;
    letter-spacing: -.2px;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #39D0FF !important; font-size: 10px !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    color: #B0BAC8 !important; font-size: 13.5px !important; line-height: 1.7 !important;
}

/* ══════════════════════════════════════════════════════════════════════════
   TABS  — pill style
══════════════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] > div:first-child {
    gap: 6px !important; border-bottom: 1px solid #1C2128 !important; padding-bottom: 4px;
}
button[data-baseweb="tab"] {
    color: #6E7681 !important; font-size: 14px !important; font-weight: 600 !important;
    background: transparent !important; padding: 8px 20px !important;
    border-radius: 8px !important; transition: all .18s ease !important;
    border: 1px solid transparent !important;
}
button[data-baseweb="tab"]:hover {
    color: #C9D1D9 !important; background: #161B22 !important;
    border-color: #30363D !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #39D0FF !important; background: rgba(57,208,255,.08) !important;
    border-color: rgba(57,208,255,.3) !important;
}

/* ── All form inputs (global fix for dark theme) ──────────────────────────── */
input, textarea {
    background-color: #161B22 !important; color: #E6EDF3 !important;
    border: 1px solid #30363D !important; border-radius: 8px !important;
    font-size: 14px !important;
}
input::placeholder, textarea::placeholder { color: #6E7681 !important; }
select {
    background-color: #161B22 !important; color: #E6EDF3 !important;
    border: 1px solid #30363D !important;
}

/* ── Labels ───────────────────────────────────────────────────────────────── */
label { color: #8B949E !important; font-size: 13px !important; }
[data-testid="stSidebar"] label { color: #8B949E !important; font-size: 13px !important; }

/* ── Selectbox dropdown ───────────────────────────────────────────────────── */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child {
    background: #161B22 !important; border-color: #30363D !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    color: #E6EDF3 !important; font-size: 14px !important;
}
li[role="option"] {
    background: #161B22 !important; color: #C9D1D9 !important; font-size: 14px !important;
}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {
    background: #21262D !important; color: #E6EDF3 !important;
}

/* ── Expanders ────────────────────────────────────────────────────────────── */
details summary {
    color: #C9D1D9 !important; font-size: 14px !important; font-weight: 500 !important;
}
details summary:hover { color: #E6EDF3 !important; }
details[open] summary { color: #58A6FF !important; }
details > div { background: #0D1117 !important; }
details > div p, details > div li { color: #C9D1D9 !important; font-size: 14px !important; }

/* ── Number input ─────────────────────────────────────────────────────────── */
[data-testid="stNumberInput"] button {
    background: #21262D !important; color: #E6EDF3 !important;
    border-color: #30363D !important;
}

/* ── Toggle ───────────────────────────────────────────────────────────────── */
[data-testid="stToggle"] p, [data-testid="stToggle"] label,
[data-testid="stToggle"] span { color: #C9D1D9 !important; font-size: 14px !important; }

/* ── File uploader ────────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] label {
    color: #C9D1D9 !important; font-size: 14px !important; font-weight: 500 !important;
}
[data-testid="stFileUploader"] section {
    background: #161B22 !important; border: 1.5px dashed #30363D !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"] section p,
[data-testid="stFileUploader"] section span { color: #8B949E !important; font-size: 13px !important; }
[data-testid="stFileUploader"] section button {
    background: #21262D !important; color: #C9D1D9 !important;
    border: 1px solid #30363D !important; font-size: 13px !important;
}

/* ── Alert / Info / Warning / Success / Error boxes ──────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important; padding: 12px 16px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] li,
[data-testid="stAlert"] strong {
    color: #C9D1D9 !important; font-size: 14px !important; line-height: 1.6 !important;
}

/* ── Caption ──────────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p,
.stCaption p { color: #6E7681 !important; font-size: 13px !important; }

/* ── Main content text (outside chat) ────────────────────────────────────── */
.stMarkdown p  { color: #C9D1D9; font-size: 15px; line-height: 1.75; }
.stMarkdown li { color: #C9D1D9; font-size: 15px; line-height: 1.75; }
.stMarkdown strong, .stMarkdown b { color: #E6EDF3; font-weight: 600; }
.stMarkdown h1 { color: #E6EDF3; font-size: 26px; font-weight: 700; margin-bottom: 8px; }
.stMarkdown h2 { color: #E6EDF3; font-size: 20px; font-weight: 600; margin-bottom: 6px; }
.stMarkdown h3 { color: #58A6FF; font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.stMarkdown h4 { color: #C9D1D9; font-size: 15px; font-weight: 600; }
.stMarkdown code {
    background: #161B22; color: #79C0FF;
    padding: 2px 6px; border-radius: 4px; font-size: 13px;
}
.stMarkdown a { color: #58A6FF; text-decoration: underline; }

/* ══════════════════════════════════════════════════════════════════════════
   CHAT MESSAGES  — glassmorphism cards
══════════════════════════════════════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    background: rgba(22,27,34,.75) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid #21262D !important;
    border-radius: 16px !important;
    padding: 18px 22px !important;
    margin: 6px 0 !important;
    animation: fadeInUp .25s ease forwards;
    transition: border-color .2s ease, box-shadow .2s ease;
}
[data-testid="stChatMessage"]:hover {
    border-color: #30363D !important;
    box-shadow: 0 4px 24px rgba(0,0,0,.4) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] em,
[data-testid="stChatMessage"] a {
    color: #E6EDF3 !important; font-size: 15.5px !important; line-height: 1.85 !important;
}
[data-testid="stChatMessage"] h2 { font-size: 19px !important; font-weight: 700 !important; color: #E6EDF3 !important; }
[data-testid="stChatMessage"] h3 { font-size: 16px !important; font-weight: 600 !important; color: #39D0FF !important; }
[data-testid="stChatMessage"] code {
    background: #0D1117 !important; color: #79C0FF !important;
    padding: 2px 7px !important; border-radius: 5px !important; font-size: 13.5px !important;
    border: 1px solid #21262D !important;
}
[data-testid="stChatMessage"] a { color: #39D0FF !important; }
[data-testid="stChatMessage"] table { width: 100%; border-collapse: collapse; margin: 10px 0; border-radius: 10px; overflow: hidden; }
[data-testid="stChatMessage"] th {
    background: #0D1B2A !important; color: #39D0FF !important;
    padding: 10px 14px; font-size: 13px; text-align: left; font-weight: 700;
    border-bottom: 1px solid #1F3A5F;
}
[data-testid="stChatMessage"] td {
    color: #C9D1D9 !important; padding: 9px 14px; font-size: 14px;
    border-bottom: 1px solid #1C2128;
}
[data-testid="stChatMessage"] tr:last-child td { border-bottom: none !important; }

/* ══════════════════════════════════════════════════════════════════════════
   CHAT INPUT  — neon focus ring
══════════════════════════════════════════════════════════════════════════ */
[data-testid="stChatInput"] {
    background: rgba(22,27,34,.9) !important;
    border: 1.5px solid #30363D !important;
    border-radius: 16px !important;
    backdrop-filter: blur(8px) !important;
    padding: 4px 8px !important;
    transition: border-color .2s ease, box-shadow .2s ease !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(57,208,255,.5) !important;
    box-shadow: 0 0 0 3px rgba(57,208,255,.1), 0 0 20px rgba(57,208,255,.08) !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 15px !important; color: #E6EDF3 !important;
    background: transparent !important; border: none !important;
    border-radius: 0 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #484F58 !important; font-size: 14.5px !important; }

/* ══════════════════════════════════════════════════════════════════════════
   SEVERITY BADGES  — neon glow
══════════════════════════════════════════════════════════════════════════ */
.badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 20px; border-radius: 50px;
    font-size: 11.5px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; margin-bottom: 14px;
    transition: box-shadow .3s ease;
}
.badge-EMERGENCY {
    background: rgba(255,75,75,.15); color: #FF6B6B; border: 1.5px solid #FF6B6B;
    animation: pulse-emergency 2s ease-in-out infinite;
}
.badge-SEVERE {
    background: rgba(255,140,0,.12); color: #FFA040; border: 1.5px solid #FFA040;
    animation: pulse-severe 2.5s ease-in-out infinite;
}
.badge-MODERATE { background: rgba(210,160,0,.10); color: #E5B000; border: 1.5px solid #E5B000; box-shadow: 0 0 8px rgba(229,176,0,.2); }
.badge-MILD     { background: rgba(63,185,80,.10);  color: #3FB950; border: 1.5px solid #3FB950; box-shadow: 0 0 8px rgba(63,185,80,.15); }

/* ── History pills ────────────────────────────────────────────────────────── */
.hist-pill { display: inline-block; padding: 2px 10px; border-radius: 50px; font-size: 11px; font-weight: 700; letter-spacing: .5px; }
.hist-EMERGENCY { background: #FF4B4B22; color: #FF6B6B; border: 1px solid #FF6B6B; }
.hist-SEVERE    { background: #FF8C0022; color: #FFA040; border: 1px solid #FFA040; }
.hist-MODERATE  { background: #D4A01722; color: #E5B000; border: 1px solid #E5B000; }
.hist-MILD      { background: #3FB95022; color: #3FB950; border: 1px solid #3FB950; }

/* ══════════════════════════════════════════════════════════════════════════
   CONTEXT CARD  — glassmorphism
══════════════════════════════════════════════════════════════════════════ */
.ctx-card {
    background: linear-gradient(135deg, rgba(13,27,42,.9), rgba(9,18,30,.9));
    border: 1px solid #1F3A5F; border-radius: 14px;
    padding: 14px 16px; font-size: 13.5px; line-height: 1.9;
    color: #B0BAC8; margin-bottom: 10px;
    box-shadow: 0 2px 16px rgba(0,0,0,.3), inset 0 1px 0 rgba(57,208,255,.06);
}
.ctx-card b { color: #39D0FF; font-weight: 600; }

/* ══════════════════════════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════════════════════════ */
div.stButton > button {
    background: linear-gradient(135deg, #1461c7, #2d80fc);
    color: #fff !important; border: none !important; border-radius: 10px;
    font-size: 13.5px; font-weight: 600; padding: 8px 16px;
    transition: all .2s ease;
    box-shadow: 0 2px 12px rgba(45,128,252,.3), inset 0 1px 0 rgba(255,255,255,.1);
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #2d80fc, #39D0FF) !important;
    box-shadow: 0 4px 20px rgba(57,208,255,.35) !important;
    transform: translateY(-1px);
}
div.stButton > button:active { transform: translateY(0) !important; }

[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #14532d, #16a34a) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(22,163,74,.25) !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(135deg, #16a34a, #22c55e) !important;
    box-shadow: 0 4px 20px rgba(34,197,94,.35) !important;
}

/* ══════════════════════════════════════════════════════════════════════════
   AUDIO PLAYER
══════════════════════════════════════════════════════════════════════════ */
audio {
    width: 100%; border-radius: 10px; margin-top: 8px;
    background: #161B22; border: 1px solid #21262D;
}

/* ══════════════════════════════════════════════════════════════════════════
   SPINNER / LOADING
══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSpinner"] p { color: #6E7681 !important; font-size: 13.5px !important; }

/* ── Eval score bars ──────────────────────────────────────────────────────── */
.score-bar-wrap { background:#21262D; border-radius:6px; height:10px; margin:4px 0 10px; }
.score-bar { height:10px; border-radius:6px; }
.score-rag  { background: linear-gradient(90deg, #1f6feb, #58a6ff); }
.score-llm  { background: linear-gradient(90deg, #6e40c9, #a371f7); }
.eval-card {
    background: #161B22; border: 1px solid #21262D; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 14px;
}
.eval-q { color: #E6EDF3; font-size: 15px; font-weight: 600; margin-bottom: 10px; }
.eval-label { color: #8B949E; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 4px; }
.eval-score { font-size: 22px; font-weight: 800; }
.eval-rag-score  { color: #58A6FF; }
.eval-llm-score  { color: #A371F7; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "messages":            [],
    "pending_audio_bytes": None,
    "pending_audio_ext":   "wav",
    "pending_image_bytes": None,
    "pending_image_ext":   "jpg",
    "file_key":            0,
    "trigger_analyze":     False,
    "lang_code":           "en",
    "worst_severity":      "MILD",
    "session_id":          datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
    "voice_output":        True,
    "patient_profile":     {"name": "", "age": "", "conditions": ""},
    "manual_city":         "",
    # Auth
    "logged_in":           False,
    "user_id":             "",
    "username":            "",
    "user":                {},
    "auth_tab":            "Login",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE  (shown when not authenticated)
# ─────────────────────────────────────────────────────────────────────────────
BLOOD_GROUPS = ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

def _show_login():
    st.markdown(
        "<div style='max-width:420px;margin:60px auto 0'>"
        "<div style='text-align:center;margin-bottom:32px'>"
        "<div style='font-size:40px;margin-bottom:8px'>🏥</div>"
        "<div style='background:linear-gradient(135deg,#E6EDF3,#39D0FF);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "font-size:28px;font-weight:800;letter-spacing:-0.5px'>MediAssist AI</div>"
        "<div style='color:#484F58;font-size:14px;margin-top:4px'>AI-Powered Healthcare Platform</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    _l_col, _form_col, _r_col = st.columns([1, 2, 1])
    with _form_col:
        _tab_l, _tab_r = st.tabs(["🔑 Login", "📝 Register"])

        # ── Login tab ────────────────────────────────────────────────────────
        with _tab_l:
            _lu = st.text_input("Username", key="login_u", placeholder="your username")
            _lp = st.text_input("Password", type="password", key="login_p", placeholder="••••••••")
            if st.button("Login", use_container_width=True, type="primary", key="login_btn"):
                ok, user, err = auth_login(_lu, _lp)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_id   = user["id"]
                    st.session_state.username  = user["username"]
                    st.session_state.user      = user
                    st.session_state.patient_profile = {
                        "name":       user.get("name", ""),
                        "age":        user.get("age", ""),
                        "conditions": user.get("conditions", ""),
                    }
                    st.rerun()
                else:
                    st.error(err)

        # ── Register tab ─────────────────────────────────────────────────────
        with _tab_r:
            _ru   = st.text_input("Username*",   key="reg_u",   placeholder="choose a username")
            _re   = st.text_input("Email",        key="reg_e",   placeholder="optional")
            _rp   = st.text_input("Password*",    type="password", key="reg_p",  placeholder="min 6 chars")
            _rp2  = st.text_input("Confirm Password*", type="password", key="reg_p2", placeholder="repeat password")
            st.markdown("<p style='color:#484F58;font-size:12px;margin:8px 0 2px'>Optional health profile</p>", unsafe_allow_html=True)
            _rname = st.text_input("Full Name",   key="reg_name", placeholder="e.g. Rahul Sharma")
            _rage  = st.text_input("Age",          key="reg_age",  placeholder="e.g. 28")
            _rbg   = st.selectbox("Blood Group",   BLOOD_GROUPS,   key="reg_bg")
            _rcond = st.text_area("Existing Conditions / Medications", key="reg_cond",
                                  placeholder="e.g. Diabetic, on Metformin 500mg", height=70)
            if st.button("Create Account", use_container_width=True, type="primary", key="reg_btn"):
                ok, user, err = auth_register(_ru, _re, _rp, _rp2, _rname, _rage, _rbg, _rcond)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_id   = user["id"]
                    st.session_state.username  = user["username"]
                    st.session_state.user      = user
                    st.session_state.patient_profile = {
                        "name": _rname, "age": _rage, "conditions": _rcond,
                    }
                    st.success("Account created! Welcome to MediAssist AI.")
                    st.rerun()
                else:
                    st.error(err)

        st.markdown(
            "<p style='text-align:center;color:#484F58;font-size:12px;margin-top:20px'>"
            "Your medical data is stored securely.<br>Never share your password.</p>",
            unsafe_allow_html=True,
        )

if not st.session_state.logged_in:
    _show_login()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Branding + user info ──────────────────────────────────────────────────
    _db_dot   = ("#3FB950", "Cloud DB ✓") if is_cloud() else ("#E5B000", "Local DB")
    _u        = st.session_state.user
    _disp     = _u.get("name") or st.session_state.username
    _subtitle = []
    if _u.get("age"):        _subtitle.append(f"{_u['age']}y")
    if _u.get("blood_group"): _subtitle.append(_u["blood_group"])
    if _u.get("conditions"):  _subtitle.append(_u["conditions"][:30])
    st.markdown(
        "<div style='padding:4px 0 10px'>"
        "<div style='font-size:18px;font-weight:800;color:#E6EDF3;letter-spacing:-.3px'>🏥 MediAssist AI</div>"
        f"<div style='color:#C9D1D9;font-size:14px;font-weight:600;margin-top:8px'>👤 {_disp}</div>"
        f"<div style='color:#6E7681;font-size:12px'>@{st.session_state.username}"
        + (f" · {' · '.join(_subtitle)}" if _subtitle else "") + "</div>"
        "<div style='display:flex;align-items:center;gap:6px;margin-top:6px'>"
        f"<span style='width:7px;height:7px;border-radius:50%;background:{_db_dot[0]};"
        f"box-shadow:0 0 6px {_db_dot[0]};display:inline-block'></span>"
        f"<span style='font-size:11px;color:#6E7681;font-weight:500'>{_db_dot[1]}</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()
    st.divider()

    # ── Environmental context ─────────────────────────────────────────────────
    st.markdown("### 🌍 Your Context")

    @st.cache_data(ttl=600, show_spinner=False)
    def _fetch_env_auto():
        loc = get_user_location()
        if not loc:
            return None
        return {
            "location": loc,
            "weather":  get_weather(loc["lat"], loc["lon"]),
            "season":   get_season(loc["lat"], loc["lon"]),
        }

    @st.cache_data(ttl=600, show_spinner=False)
    def _fetch_env_manual(city: str):
        loc = geocode_city(city)
        if not loc:
            return None
        return {
            "location": loc,
            "weather":  get_weather(loc["lat"], loc["lon"]),
            "season":   get_season(loc["lat"], loc["lon"]),
        }

    _env = _fetch_env_auto()

    # Manual city fallback when auto-detection fails
    if not _env:
        _manual_input = st.text_input(
            "Enter your city",
            value=st.session_state.manual_city,
            placeholder="e.g. New Delhi, Mumbai, Bengaluru",
            key="manual_city_input",
        )
        if _manual_input != st.session_state.manual_city:
            st.session_state.manual_city = _manual_input
            st.rerun()
        if st.session_state.manual_city:
            _env = _fetch_env_manual(st.session_state.manual_city)
            if not _env:
                st.caption("City not found — try a different spelling.")

    _city = ""
    if _env:
        loc = _env["location"]
        w   = _env["weather"]
        s   = _env["season"]
        _city = loc["city"]
        _html = (
            "<div class='ctx-card'>"
            f"📍 <b>{loc['city']}, {loc['country']}</b><br>"
            f"🍂 Season: <b>{s}</b>"
        )
        if w:
            _html += (
                f"<br>🌡️ Temp: <b>{w['temp_c']}°C</b>"
                f"<br>💧 Humidity: <b>{w['humidity']}%</b>"
                f"<br>☁️ {w['condition']}"
            )
        _html += "</div>"
        st.markdown(_html, unsafe_allow_html=True)
    elif not st.session_state.manual_city:
        st.caption("Auto-detection unavailable. Enter your city above.")

    st.divider()

    # ── Language selector ─────────────────────────────────────────────────────
    st.markdown("### 🌐 Language")
    _lang_name = st.selectbox(
        "Respond in:",
        list(LANGUAGES.keys()),
        index=0,
        label_visibility="collapsed",
    )
    st.session_state.lang_code = LANGUAGES[_lang_name]

    st.divider()

    # ── Voice output toggle ───────────────────────────────────────────────────
    st.markdown("### 🔊 Voice Output")
    st.session_state.voice_output = st.toggle(
        "Read responses aloud", value=st.session_state.voice_output
    )

    st.divider()

    # ── Patient profile ───────────────────────────────────────────────────────
    with st.expander("👤 Patient Profile", expanded=False):
        st.caption("Helps the AI give more personalised answers.")
        _p = st.session_state.patient_profile
        _p["name"] = st.text_input("Name", value=_p["name"], placeholder="e.g. Rahul")
        _p["age"]  = st.text_input("Age", value=_p["age"], placeholder="e.g. 32")
        _p["conditions"] = st.text_area(
            "Existing conditions / medications",
            value=_p["conditions"],
            placeholder="e.g. Diabetic, on Metformin",
            height=80,
        )

    st.divider()

    # ── Attachments ───────────────────────────────────────────────────────────
    st.markdown("### 📎 Attach Files")

    _recorded = None
    try:
        _recorded = st.audio_input("🎙️ Record Voice")
    except AttributeError:
        pass

    _fkey = st.session_state.file_key
    _up_audio = st.file_uploader("🎤 Or upload audio", type=["wav","mp3","ogg","m4a"], key=f"aud_{_fkey}")
    _up_image = st.file_uploader("🖼️ Upload Medical Image", type=["png","jpg","jpeg","webp"], key=f"img_{_fkey}")

    if _recorded is not None:
        st.session_state.pending_audio_bytes = _recorded.read()
        st.session_state.pending_audio_ext   = "wav"
    elif _up_audio is not None:
        st.session_state.pending_audio_bytes = _up_audio.read()
        st.session_state.pending_audio_ext   = _up_audio.name.rsplit(".",1)[-1]

    if _up_image is not None:
        st.session_state.pending_image_bytes = _up_image.read()
        st.session_state.pending_image_ext   = _up_image.name.rsplit(".",1)[-1]

    _has_audio = st.session_state.pending_audio_bytes is not None
    _has_image = st.session_state.pending_image_bytes is not None

    if _has_audio or _has_image:
        _att = []
        if _has_audio: _att.append("🎤 audio")
        if _has_image: _att.append("🖼️ image")
        st.success(f"Ready: {', '.join(_att)}")
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("🚀 Analyze", use_container_width=True):
                st.session_state.trigger_analyze = True
                st.rerun()
        with _c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.pending_audio_bytes = None
                st.session_state.pending_image_bytes = None
                st.session_state.file_key += 1
                st.rerun()

    st.divider()

    # ── BMI Calculator ────────────────────────────────────────────────────────
    with st.expander("⚖️ BMI Calculator"):
        _w = st.number_input("Weight (kg)", 1.0, 300.0, 70.0, key="bmi_w")
        _h = st.number_input("Height (cm)", 50.0, 250.0, 170.0, key="bmi_h")
        if st.button("Calculate BMI", use_container_width=True):
            _bmi = _w / ((_h / 100) ** 2)
            if _bmi < 18.5:
                _cat, _col = "Underweight", "#58A6FF"
                _tip = "Consider increasing caloric intake with nutritious foods."
            elif _bmi < 25:
                _cat, _col = "Normal Weight", "#3FB950"
                _tip = "Maintain your current healthy lifestyle."
            elif _bmi < 30:
                _cat, _col = "Overweight", "#E5B000"
                _tip = "Regular exercise and balanced diet recommended."
            else:
                _cat, _col = "Obese", "#FF6B6B"
                _tip = "Consult a doctor for a supervised weight management plan."
            st.markdown(
                f"<div style='background:#161B22;border-radius:10px;padding:14px;margin-top:8px'>"
                f"<b style='font-size:24px;color:{_col}'>{_bmi:.1f}</b> "
                f"<span style='color:{_col};font-size:13px;font-weight:700'>{_cat}</span>"
                f"<p style='color:#C9D1D9;font-size:13px;margin:6px 0 0'>{_tip}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── First Aid Guide ───────────────────────────────────────────────────────
    with st.expander("🆘 First Aid Guide"):
        _cards = all_cards()
        _titles = [f"{c['icon']} {c['title']}" for c in _cards]
        _sel = st.selectbox("Choose emergency type:", _titles, key="fa_select",
                            label_visibility="collapsed")
        _idx = _titles.index(_sel)
        st.markdown(fa_html(_cards[_idx]), unsafe_allow_html=True)

    # ── Vitals Tracker ────────────────────────────────────────────────────────
    with st.expander("📈 Health Vitals Tracker"):
        import plotly.graph_objects as go

        _vdata = get_vitals(st.session_state.user_id)

        # Log new reading
        st.markdown("<p style='color:#C9D1D9;font-size:13px;font-weight:600;margin-bottom:6px'>Log Today's Reading</p>", unsafe_allow_html=True)
        _vc1, _vc2 = st.columns(2)
        with _vc1:
            _v_sys  = st.number_input("Systolic BP",  60,  220, step=1, value=None, placeholder="mmHg", key="v_sys")
            _v_glu  = st.number_input("Blood Glucose", 50, 500, step=1, value=None, placeholder="mg/dL", key="v_glu")
            _v_spo2 = st.number_input("SpO₂ %",       50,  100, step=1, value=None, placeholder="%",    key="v_spo2")
        with _vc2:
            _v_dia  = st.number_input("Diastolic BP",  40, 140, step=1, value=None, placeholder="mmHg", key="v_dia")
            _v_hr   = st.number_input("Heart Rate",    30, 220, step=1, value=None, placeholder="bpm",  key="v_hr")
            _v_wt   = st.number_input("Weight",        20, 300, step=1, value=None, placeholder="kg",   key="v_wt")

        if st.button("💾 Save Reading", use_container_width=True, key="save_vitals"):
            _new = {k: v for k, v in {
                "systolic_bp": _v_sys, "diastolic_bp": _v_dia,
                "glucose": _v_glu, "heart_rate": _v_hr,
                "weight": _v_wt, "spo2": _v_spo2,
            }.items() if v is not None}
            if _new:
                save_vital(st.session_state.user_id, _new)
                st.success("Reading saved.")
                st.rerun()
            else:
                st.warning("Enter at least one value.")

        # Current status summary
        if _vdata:
            st.markdown("<p style='color:#C9D1D9;font-size:13px;font-weight:600;margin:10px 0 6px'>Latest Values</p>", unsafe_allow_html=True)
            _summary_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px'>"
            for _key, _cfg in METRICS.items():
                # latest value from DB records
                _lv = next((e[_key] for e in reversed(_vdata) if e.get(_key) is not None), None)
                if _lv is None:
                    continue
                _sc = status_color(status(_key, _lv))
                _summary_html += (
                    f"<div style='background:#161B22;border:1px solid #21262D;border-radius:8px;"
                    f"padding:6px 10px;min-width:80px'>"
                    f"<div style='color:#8B949E;font-size:10px;font-weight:600'>{_cfg['label']}</div>"
                    f"<div style='color:{_sc};font-size:16px;font-weight:700'>{_lv}</div>"
                    f"<div style='color:#484F58;font-size:10px'>{_cfg['unit']}</div>"
                    f"</div>"
                )
            _summary_html += "</div>"
            st.markdown(_summary_html, unsafe_allow_html=True)

            # Chart for each metric that has data
            _dates = [e.get("timestamp", "")[:10] for e in _vdata]
            for _key, _cfg in METRICS.items():
                _vals = [e.get(_key) for e in _vdata]
                _pairs = [(d, v) for d, v in zip(_dates, _vals) if v is not None]
                if len(_pairs) < 2:
                    continue
                _xd, _yd = zip(*_pairs)
                _fig = go.Figure()
                _fig.add_trace(go.Scatter(
                    x=list(_xd), y=list(_yd), mode="lines+markers",
                    line=dict(color=_cfg["color"], width=2),
                    marker=dict(size=6, color=_cfg["color"]),
                    name=_cfg["label"],
                ))
                # Add normal range band
                if _cfg.get("normal"):
                    _fig.add_hrect(
                        y0=_cfg["normal"][0], y1=_cfg["normal"][1],
                        fillcolor="rgba(63,185,80,0.08)", line_width=0,
                        annotation_text="Normal", annotation_position="right",
                        annotation=dict(font_size=10, font_color="#3FB950"),
                    )
                _fig.update_layout(
                    title=dict(text=f"{_cfg['label']} ({_cfg['unit']})", font=dict(color="#C9D1D9", size=13)),
                    paper_bgcolor="#0D1117", plot_bgcolor="#161B22",
                    height=200, margin=dict(l=10, r=10, t=30, b=10),
                    xaxis=dict(tickfont=dict(color="#8B949E", size=10), gridcolor="#21262D", showgrid=True),
                    yaxis=dict(tickfont=dict(color="#8B949E", size=10), gridcolor="#21262D", showgrid=True),
                    showlegend=False,
                )
                st.plotly_chart(_fig, use_container_width=True)

            if st.button("🗑️ Clear Vitals History", use_container_width=True, key="clear_vitals"):
                clear_vitals()
                st.rerun()
        else:
            st.caption("No readings yet. Log your first reading above.")

    # ── Drug Interaction Checker ──────────────────────────────────────────────
    with st.expander("💊 Drug Interaction Checker"):
        st.caption("Check if two medicines are safe to take together.")
        _d1 = st.text_input("Medicine 1", placeholder="e.g. Metformin", key="di_d1")
        _d2 = st.text_input("Medicine 2", placeholder="e.g. Ibuprofen", key="di_d2")
        if st.button("Check Interaction", use_container_width=True, key="di_check"):
            if _d1.strip() and _d2.strip():
                with st.spinner("Checking interaction…"):
                    _di = check_interaction(_d1, _d2)
                st.markdown(
                    f"<div style='background:#161B22;border:1px solid {_di['color']}33;"
                    f"border-left:3px solid {_di['color']};border-radius:10px;padding:12px 14px;margin-top:8px'>"
                    f"<div style='color:{_di['color']};font-size:13px;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:.8px;margin-bottom:8px'>{_di['label']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(_di["explanation"])
            else:
                st.warning("Enter both medicine names.")

    # ── Medical History ───────────────────────────────────────────────────────
    with st.expander("📋 Consultation History"):
        _db_hist = get_consultations(st.session_state.user_id, limit=10)
        if not _db_hist:
            st.info("No past consultations yet.")
        else:
            for _entry in _db_hist:
                _sev  = _entry.get("severity", "MILD")
                _ts   = (_entry.get("timestamp") or "")[:16].replace("T", " ")
                _city_h = _entry.get("city", "")
                _pill = f"<span class='hist-pill hist-{_sev}'>{_sev}</span>"
                # Parse first user message as the complaint
                try:
                    import json as _j
                    _msgs_raw = _entry.get("messages") or "[]"
                    _msgs = _j.loads(_msgs_raw) if isinstance(_msgs_raw, str) else _msgs_raw
                    _complaint = next((m["content"] for m in _msgs if m.get("role") == "user"), "—")
                except Exception:
                    _complaint = "—"
                st.markdown(
                    f"**{_ts}** {_pill}"
                    + (f" · {_city_h}" if _city_h else "") + "<br>"
                    f"<span style='color:#C9D1D9;font-size:13px'>{str(_complaint)[:80]}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")

    st.divider()

    # ── New Conversation ──────────────────────────────────────────────────────
    if st.button("✨ New Conversation", use_container_width=True):
        # Final save of the outgoing session, then reset for the new one
        if st.session_state.messages:
            save_session(
                st.session_state.messages,
                st.session_state.worst_severity,
                session_id=st.session_state.session_id,
            )
        st.session_state.messages            = []
        st.session_state.pending_audio_bytes = None
        st.session_state.pending_image_bytes = None
        st.session_state.worst_severity      = "MILD"
        st.session_state.file_key           += 1
        st.session_state.session_id          = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        st.rerun()

    st.divider()

    # ── Feature list ──────────────────────────────────────────────────────────
    st.markdown("### ✅ Active Features")
    for _f in [
        "🧠 RAG Medical Knowledge",
        "🎤 Voice Input (Whisper)",
        "🖼️ Real Image Analysis",
        "🚨 Emergency Detection",
        "⚠️ Severity Classification",
        "🏥 Nearby Hospital Finder",
        "🌍 Context-Aware Responses",
        "💬 Conversational Memory",
        "🔊 Voice Response",
        "📄 PDF Report Download",
        "📋 Consultation History",
        "🆘 First Aid Quick Cards",
        "⚖️ BMI Calculator",
        "🌐 Multilingual Support",
        "💊 Prescription Decoder",
        "📈 Vitals Tracker",
        "🔗 Drug Interaction Checker",
    ]:
        st.markdown(f"- {_f}")

    st.divider()
    st.warning(
        "⚠️ **Disclaimer:** Preliminary AI guidance only. "
        "Always consult a qualified doctor. "
        "Emergencies: call **112** immediately."
    )

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;padding:28px 0 18px'>"
    "<div style='display:inline-block;background:linear-gradient(135deg,rgba(57,208,255,.12),rgba(31,111,235,.08));"
    "border:1px solid rgba(57,208,255,.2);border-radius:20px;padding:6px 20px;margin-bottom:16px;"
    "font-size:12px;font-weight:700;color:#39D0FF;letter-spacing:2px;text-transform:uppercase'>"
    "AI-Powered Healthcare Platform</div>"
    "<h1 style='background:linear-gradient(135deg,#E6EDF3 0%,#39D0FF 50%,#58A6FF 100%);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
    "font-size:46px;font-weight:800;margin:0 0 10px;letter-spacing:-1px;line-height:1.1'>"
    "🏥 AI Medical Assistant</h1>"
    "<p style='color:#6E7681;font-size:15px;margin:0;font-weight:400;letter-spacing:.3px'>"
    "Multimodal &nbsp;·&nbsp; Context-Aware &nbsp;·&nbsp; Emergency-Ready &nbsp;·&nbsp; Multilingual</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SEASONAL DISEASE ALERT BANNER
# ─────────────────────────────────────────────────────────────────────────────
if _env:
    _season_val = _env.get("season", "")
    _weather_val = _env.get("weather") or {}
    _temp_val = _weather_val.get("temp_c")

    _alert = None
    if _season_val == "Monsoon":
        _alert = ("🦟", "#E5B000", "Monsoon Alert",
                  "High season for Dengue, Malaria & Typhoid. Use mosquito repellent, drink only boiled or filtered water, and avoid street food.")
    elif _season_val == "Summer" and _temp_val and _temp_val >= 38:
        _alert = ("🌡️", "#FFA040", "Extreme Heat Alert",
                  f"Current temperature {_temp_val}°C — high risk of Heatstroke & Dehydration. Stay indoors during peak hours, drink 3–4 litres of water daily.")
    elif _season_val == "Summer" and _temp_val and _temp_val >= 33:
        _alert = ("☀️", "#E5B000", "Heat Advisory",
                  f"Temperature {_temp_val}°C — elevated risk of Dehydration & Heat Exhaustion. Keep hydrated and avoid prolonged sun exposure.")
    elif _season_val == "Winter":
        _alert = ("🌬️", "#58A6FF", "Winter Health Notice",
                  "Cold season — higher risk of Influenza, Pneumonia & Respiratory infections. Wash hands frequently and consider a flu vaccine.")
    elif _season_val == "Post-Monsoon":
        _alert = ("🌧️", "#8B949E", "Post-Monsoon Advisory",
                  "Residual mosquito breeding season — Dengue and Chikungunya remain a risk. Eliminate stagnant water around your home.")

    if _alert:
        _ic, _ac, _at, _am = _alert
        st.markdown(
            f"<div style='background:rgba({','.join(str(int(int(_ac.lstrip('#')[i:i+2],16)) ) for i in (0,2,4))},.08);"
            f"border:1px solid {_ac}44;border-left:4px solid {_ac};border-radius:12px;"
            f"padding:12px 18px;margin-bottom:16px;display:flex;align-items:flex-start;gap:12px'>"
            f"<span style='font-size:22px;line-height:1'>{_ic}</span>"
            f"<div><div style='color:{_ac};font-size:13px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.8px;margin-bottom:3px'>{_at}</div>"
            f"<div style='color:#C9D1D9;font-size:14px;line-height:1.6'>{_am}</div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_chat, _tab_report, _tab_dash = st.tabs(["💬 Consultation", "🔬 Analyze Medical Report", "📊 My Dashboard"])

# ══════════════════════════ REPORT ANALYSIS TAB ═══════════════════════════════
with _tab_report:
    st.markdown(
        "<p style='color:#8B949E;font-size:15px;margin-bottom:20px'>"
        "Upload a <b style='color:#C9D1D9'>lab report (PDF)</b> or a "
        "<b style='color:#C9D1D9'>scanned/photo report (image)</b>. "
        "The AI will read every value, flag abnormal results, and explain what they mean in plain language.</p>",
        unsafe_allow_html=True,
    )

    _r_col1, _r_col2 = st.columns([1, 1])

    with _r_col1:
        st.markdown("#### 📄 Upload PDF Report")
        _pdf_upload = st.file_uploader(
            "Lab report, discharge summary, doctor's note…",
            type=["pdf"],
            key="report_pdf",
        )

    with _r_col2:
        st.markdown("#### 🖼️ Upload Image Report")
        _img_upload = st.file_uploader(
            "Scanned report, photo of prescription, X-ray report…",
            type=["png", "jpg", "jpeg", "webp"],
            key="report_img",
        )

    st.markdown("")

    _what_we_analyze = st.expander("ℹ️ What gets analyzed?", expanded=False)
    with _what_we_analyze:
        st.markdown("""
- **Blood tests** — CBC, hemoglobin, WBC, platelets, RBC
- **Metabolic panel** — glucose, HbA1c, creatinine, urea, electrolytes
- **Lipid panel** — cholesterol, LDL, HDL, triglycerides
- **Liver function** — SGPT, SGOT, bilirubin, albumin
- **Thyroid** — TSH, T3, T4
- **Urine analysis** — protein, glucose, ketones, pH
- **Doctor's notes / prescriptions** — medicines, dosage, instructions
- **Discharge summaries** — diagnosis, follow-up plan
- **X-ray / scan text reports** — findings, impressions
        """)

    _analyze_btn = st.button("🔬 Analyze Report", type="primary", use_container_width=False)

    if _analyze_btn:
        if not _pdf_upload and not _img_upload:
            st.warning("Please upload a PDF or image report first.")
        else:
            _tmp_report = None
            try:
                if _pdf_upload:
                    _ext = "pdf"
                    _raw = _pdf_upload.read()
                else:
                    _ext = _img_upload.name.rsplit(".", 1)[-1]
                    _raw = _img_upload.read()

                _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{_ext}")
                _tmp.write(_raw); _tmp.close()
                _tmp_report = _tmp.name

                with st.spinner("Reading and analyzing your report… this may take 15–30 seconds."):
                    if _ext == "pdf":
                        _analysis = analyze_pdf(_tmp_report)
                    else:
                        _analysis = analyze_image_report(_tmp_report)

                st.markdown("---")
                st.markdown(
                    "<div style='background:#0D1B2A;border:1px solid #1F3A5F;"
                    "border-radius:12px;padding:24px 28px;margin-top:8px'>"
                    f"{_analysis}"
                    "</div>",
                    unsafe_allow_html=True,
                )

                # Download analysis as PDF
                st.markdown("")
                _rpt_msgs = [
                    {"role": "user",      "content": f"Analyzed medical report ({_ext.upper()})"},
                    {"role": "assistant", "content": _analysis},
                ]
                _rpt_pdf = generate_report(_rpt_msgs, severity="", city=_city)
                st.download_button(
                    label="📄 Download Analysis as PDF",
                    data=_rpt_pdf,
                    file_name=f"report_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                )

            except Exception as _e:
                st.error(f"Analysis failed: {_e}")
            finally:
                if _tmp_report and os.path.exists(_tmp_report):
                    try: os.unlink(_tmp_report)
                    except OSError: pass

    # ══════════════════ PRESCRIPTION DECODER ══════════════════════════════════
    st.markdown("---")
    st.markdown(
        "<div style='margin:8px 0 18px'>"
        "<h3 style='color:#E6EDF3;font-size:20px;font-weight:700;margin:0 0 6px'>💊 Prescription Decoder</h3>"
        "<p style='color:#8B949E;font-size:14px;margin:0'>"
        "Upload a photo of your prescription — the AI will identify every medicine, "
        "explain what it does, its dosage, side effects, and what to watch out for.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _rx_col1, _rx_col2 = st.columns([1, 1])
    with _rx_col1:
        _rx_upload = st.file_uploader(
            "Prescription photo (handwritten or printed)",
            type=["png", "jpg", "jpeg", "webp"],
            key="rx_img",
        )
    with _rx_col2:
        if _rx_upload:
            st.image(_rx_upload, caption="Uploaded prescription", use_container_width=True)

    if _rx_upload:
        if st.button("💊 Decode Prescription", type="primary", use_container_width=False):
            _tmp_rx = None
            try:
                _ext_rx = _rx_upload.name.rsplit(".", 1)[-1]
                _t = tempfile.NamedTemporaryFile(delete=False, suffix=f".{_ext_rx}")
                _t.write(_rx_upload.read()); _t.close()
                _tmp_rx = _t.name

                with st.spinner("Reading prescription and looking up each medicine… (20–40 seconds)"):
                    _rx_result = analyze_prescription(_tmp_rx)

                if _rx_result.get("error"):
                    st.warning(_rx_result["error"])
                else:
                    _meds = _rx_result["medicines"]
                    st.markdown(
                        f"<p style='color:#3FB950;font-size:14px;font-weight:600;margin:12px 0'>"
                        f"Found {_rx_result['count']} medicine(s) in your prescription</p>",
                        unsafe_allow_html=True,
                    )

                    for _i, _med in enumerate(_meds, 1):
                        _srcs = _med.get("sources", [])
                        _src_pills = "".join(
                            f"<span style='background:#0D1B2A;border:1px solid #1F3A5F;"
                            f"border-radius:20px;padding:2px 10px;font-size:11px;color:#39D0FF'>{s}</span> "
                            for s in _srcs
                        )
                        st.markdown(
                            f"<div style='background:rgba(22,27,34,.8);border:1px solid #21262D;"
                            f"border-left:3px solid #39D0FF;border-radius:14px;padding:20px 24px;margin:10px 0'>"
                            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px'>"
                            f"<div>"
                            f"  <span style='color:#E6EDF3;font-size:17px;font-weight:700'>{_i}. {_med['name']}</span><br>"
                            f"  <span style='color:#8B949E;font-size:13px'>Dose: {_med['dose']} &nbsp;·&nbsp; Duration: {_med['duration']}</span>"
                            f"</div>"
                            f"<div style='text-align:right'>{_src_pills}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(_med["explanation"])
                        st.markdown("</div>", unsafe_allow_html=True)

                    # Save to DB
                    save_prescription(st.session_state.user_id, _meds)

                    # Download as PDF
                    _rx_msgs = [
                        {"role": "user", "content": "Decode my prescription"},
                        {"role": "assistant", "content": "\n\n".join(
                            f"**{m['name']}** ({m['dose']}, {m['duration']})\n{m['explanation']}"
                            for m in _meds
                        )},
                    ]
                    _rx_pdf = generate_report(_rx_msgs, severity="", city=_city)
                    st.download_button(
                        label="📄 Download Prescription Summary as PDF",
                        data=_rx_pdf,
                        file_name=f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                    )

            except Exception as _e:
                st.error(f"Prescription analysis failed: {_e}")
            finally:
                if _tmp_rx and os.path.exists(_tmp_rx):
                    try: os.unlink(_tmp_rx)
                    except OSError: pass

# ══════════════════════════ DASHBOARD TAB ═════════════════════════════════════
with _tab_dash:
    import plotly.graph_objects as go

    _u_name  = st.session_state.user.get("name") or st.session_state.username
    _u_cond  = st.session_state.user.get("conditions", "")
    _hour    = datetime.now().hour
    _greeting = "Good morning" if _hour < 12 else ("Good afternoon" if _hour < 17 else "Good evening")

    st.markdown(
        f"<h2 style='color:#E6EDF3;font-size:26px;font-weight:700;margin-bottom:4px'>"
        f"{_greeting}, {_u_name}! 👋</h2>"
        f"<p style='color:#6E7681;font-size:15px;margin-bottom:24px'>"
        f"{datetime.now().strftime('%A, %d %B %Y')}"
        + (f" &nbsp;·&nbsp; {_u_cond}" if _u_cond else "") + "</p>",
        unsafe_allow_html=True,
    )

    # ── Section 1: Daily mood check-in ───────────────────────────────────────
    st.markdown("### 🌡️ How are you feeling today?")
    _today_mood = get_today_mood(st.session_state.user_id)
    _moods = {
        "😊 Great":   "great",
        "🙂 Good":    "good",
        "😐 Okay":    "okay",
        "😔 Low":     "low",
        "😫 Unwell":  "unwell",
    }
    _mood_cols = st.columns(len(_moods))
    _selected_mood = _today_mood["mood"] if _today_mood else None

    for _ci, (_label, _val) in enumerate(_moods.items()):
        with _mood_cols[_ci]:
            _active = _selected_mood == _val
            _border = "#39D0FF" if _active else "#21262D"
            _bg     = "rgba(57,208,255,.1)" if _active else "#161B22"
            if st.button(
                _label, key=f"mood_{_val}", use_container_width=True,
            ):
                save_mood(st.session_state.user_id, _val)
                st.rerun()
            if _active:
                st.markdown(
                    f"<div style='height:3px;background:#39D0FF;border-radius:2px;margin-top:-8px'></div>",
                    unsafe_allow_html=True,
                )

    if _today_mood:
        _note_val = _today_mood.get("note", "")
        _new_note = st.text_input("Add a note (optional)", value=_note_val,
                                  placeholder="e.g. Feeling tired after work…", key="mood_note")
        if _new_note != _note_val and st.button("Save note", key="save_mood_note"):
            save_mood(st.session_state.user_id, _today_mood["mood"], _new_note)
            st.rerun()

    # Mood history (last 7 days)
    _mood_hist = get_mood_history(st.session_state.user_id, 7)
    if len(_mood_hist) > 1:
        _mood_score = {"great": 5, "good": 4, "okay": 3, "low": 2, "unwell": 1}
        _mh_dates  = [e["date"] for e in reversed(_mood_hist)]
        _mh_scores = [_mood_score.get(e["mood"], 3) for e in reversed(_mood_hist)]
        _mh_fig = go.Figure(go.Scatter(
            x=_mh_dates, y=_mh_scores, mode="lines+markers",
            line=dict(color="#39D0FF", width=2),
            marker=dict(size=8, color="#39D0FF"),
            fill="tozeroy", fillcolor="rgba(57,208,255,0.07)",
        ))
        _mh_fig.update_layout(
            paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
            height=120, margin=dict(l=0, r=0, t=10, b=20),
            yaxis=dict(tickvals=[1,2,3,4,5],
                       ticktext=["Unwell","Low","Okay","Good","Great"],
                       tickfont=dict(color="#8B949E", size=10), gridcolor="#1C2128"),
            xaxis=dict(tickfont=dict(color="#8B949E", size=10), gridcolor="#1C2128"),
            showlegend=False,
        )
        st.plotly_chart(_mh_fig, use_container_width=True)

    st.markdown("---")

    # ── Section 2: Health stats ───────────────────────────────────────────────
    st.markdown("### 📈 Your Health Stats")

    _vdata_dash = get_vitals(st.session_state.user_id, limit=30)
    _cons_dash  = get_consultations(st.session_state.user_id, limit=30)
    _today_cal  = get_today_calories(st.session_state.user_id)

    _stat_cols = st.columns(4)
    _stat_items = [
        ("Consultations", str(len(_cons_dash)), "this month", "#58A6FF"),
        ("Today's Calories", f"{_today_cal} kcal", "logged today", "#3FB950"),
        ("Last BP", "", "mmHg", "#FFA040"),
        ("Last Glucose", "", "mg/dL", "#E5B000"),
    ]

    # Fill dynamic vitals
    if _vdata_dash:
        _last_bp_sys = next((e.get("systolic_bp") for e in reversed(_vdata_dash) if e.get("systolic_bp")), None)
        _last_bp_dia = next((e.get("diastolic_bp") for e in reversed(_vdata_dash) if e.get("diastolic_bp")), None)
        _last_glc    = next((e.get("glucose")      for e in reversed(_vdata_dash) if e.get("glucose")), None)
        if _last_bp_sys and _last_bp_dia:
            _stat_items[2] = ("Last BP", f"{int(_last_bp_sys)}/{int(_last_bp_dia)}", "mmHg", "#FFA040")
        if _last_glc:
            _stat_items[3] = ("Last Glucose", f"{int(_last_glc)}", "mg/dL", "#E5B000")

    for _ci, (_label, _val, _sub, _col) in enumerate(_stat_items):
        with _stat_cols[_ci]:
            st.markdown(
                f"<div style='background:#161B22;border:1px solid #21262D;border-top:3px solid {_col};"
                f"border-radius:12px;padding:16px;text-align:center'>"
                f"<div style='color:#8B949E;font-size:11px;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:1px'>{_label}</div>"
                f"<div style='color:{_col};font-size:26px;font-weight:800;margin:6px 0'>"
                f"{'—' if not _val else _val}</div>"
                f"<div style='color:#484F58;font-size:11px'>{_sub}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Mini vitals trend (last 14 days)
    if len(_vdata_dash) >= 2:
        st.markdown("<br>", unsafe_allow_html=True)
        _vt_cols = st.columns(2)
        _metric_pairs = [
            ("systolic_bp",  "Systolic BP",  "#FF6B6B", _vt_cols[0]),
            ("glucose",      "Blood Glucose","#E5B000", _vt_cols[1]),
        ]
        for _key, _title, _color, _col in _metric_pairs:
            _pts = [(e.get("timestamp","")[:10], e[_key])
                    for e in _vdata_dash if e.get(_key)]
            if len(_pts) < 2:
                continue
            _xs, _ys = zip(*_pts)
            with _col:
                _fig = go.Figure(go.Scatter(
                    x=list(_xs), y=list(_ys), mode="lines+markers",
                    line=dict(color=_color, width=2),
                    marker=dict(size=5, color=_color),
                    fill="tozeroy", fillcolor=f"rgba{tuple(int(_color.lstrip('#')[i:i+2],16) for i in (0,2,4))+(0.07,)}",
                ))
                _fig.update_layout(
                    title=dict(text=_title, font=dict(color="#C9D1D9", size=13)),
                    paper_bgcolor="#0D1117", plot_bgcolor="#161B22",
                    height=180, margin=dict(l=0, r=0, t=30, b=10),
                    xaxis=dict(tickfont=dict(color="#6E7681", size=9), gridcolor="#1C2128", showgrid=True),
                    yaxis=dict(tickfont=dict(color="#6E7681", size=9), gridcolor="#1C2128", showgrid=True),
                    showlegend=False,
                )
                st.plotly_chart(_fig, use_container_width=True)

    st.markdown("---")

    # ── Section 3: Food & Calorie Tracker ────────────────────────────────────
    st.markdown("### 🍽️ Food & Calorie Tracker")
    st.caption("Log what you ate — text description or a photo of your meal.")

    _food_tab1, _food_tab2 = st.tabs(["📝 Describe your meal", "📸 Photo of meal"])

    _RATING_STYLE = {
        "HEALTHY":   ("#3FB950", "🟢 Healthy"),
        "MODERATE":  ("#E5B000", "🟡 Moderate"),
        "UNHEALTHY": ("#FF6B6B", "🔴 Unhealthy"),
    }

    def _render_food_result(desc: str, result: dict):
        _rc, _lbl = _RATING_STYLE.get(result["rating"], ("#8B949E", "—"))
        st.markdown(
            f"<div style='background:#161B22;border:1px solid #21262D;border-left:3px solid {_rc};"
            f"border-radius:12px;padding:18px 22px;margin:12px 0'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:14px'>"
            f"<div style='color:#E6EDF3;font-size:15px;font-weight:600'>{desc[:60]}</div>"
            f"<div style='color:{_rc};font-size:13px;font-weight:700'>{_lbl}</div>"
            f"</div>"
            f"<div style='display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px'>"
            + "".join(
                f"<div style='text-align:center;background:#0D1117;border-radius:8px;padding:8px 14px'>"
                f"<div style='color:#8B949E;font-size:10px;font-weight:700;text-transform:uppercase'>{n}</div>"
                f"<div style='color:#E6EDF3;font-size:18px;font-weight:800'>{v}</div>"
                f"</div>"
                for n, v in [
                    ("Calories", f"{result['calories']} kcal"),
                    ("Protein",  f"{result['protein']}g"),
                    ("Carbs",    f"{result['carbs']}g"),
                    ("Fat",      f"{result['fat']}g"),
                    ("Fiber",    f"{result['fiber']}g"),
                ]
            )
            + f"</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(result["text"])
        save_food_log(st.session_state.user_id, desc, result)

    with _food_tab1:
        _food_desc = st.text_area(
            "What did you eat?",
            placeholder="e.g. 2 rotis with dal and sabzi, 1 glass of lassi",
            height=80, key="food_text_input",
        )
        if st.button("🔍 Analyze Meal", type="primary", key="analyze_food_text"):
            if _food_desc.strip():
                with st.spinner("Calculating nutrition…"):
                    _food_result = analyze_food_text(
                        _food_desc,
                        profile=st.session_state.patient_profile,
                    )
                _render_food_result(_food_desc[:60], _food_result)
            else:
                st.warning("Please describe what you ate.")

    with _food_tab2:
        _food_img = st.file_uploader(
            "Upload a photo of your meal",
            type=["png", "jpg", "jpeg", "webp"],
            key="food_img_upload",
        )
        if _food_img:
            st.image(_food_img, width=300)
        if _food_img and st.button("🔍 Analyze Photo", type="primary", key="analyze_food_photo"):
            _tmp_food = None
            try:
                _ext_f = _food_img.name.rsplit(".", 1)[-1]
                _tf = tempfile.NamedTemporaryFile(delete=False, suffix=f".{_ext_f}")
                _tf.write(_food_img.read()); _tf.close()
                _tmp_food = _tf.name
                with st.spinner("Identifying food and calculating nutrition…"):
                    _food_result = analyze_food_photo(
                        _tmp_food,
                        profile=st.session_state.patient_profile,
                    )
                _render_food_result("Meal from photo", _food_result)
            except Exception as _e:
                st.error(f"Analysis failed: {_e}")
            finally:
                if _tmp_food and os.path.exists(_tmp_food):
                    try: os.unlink(_tmp_food)
                    except OSError: pass

    # Today's food log
    _today_logs = [
        e for e in get_food_logs(st.session_state.user_id, 20)
        if e.get("timestamp", "")[:10] == datetime.now().strftime("%Y-%m-%d")
    ]
    if _today_logs:
        st.markdown(f"**Today's log — {sum(e.get('calories',0) for e in _today_logs)} kcal total**")
        for _fl in _today_logs:
            _rc2, _lbl2 = _RATING_STYLE.get(_fl.get("rating",""), ("#8B949E","—"))
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"background:#161B22;border-radius:8px;padding:10px 14px;margin:4px 0'>"
                f"<span style='color:#C9D1D9;font-size:13px'>{_fl.get('description','')[:50]}</span>"
                f"<span style='color:{_rc2};font-size:12px;font-weight:700'>"
                f"{_fl.get('calories',0)} kcal &nbsp; {_lbl2}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS (defined before tabs so both tabs can use them)
# ─────────────────────────────────────────────────────────────────────────────
_SEV_ORDER = ["MILD", "MODERATE", "SEVERE", "EMERGENCY"]
_SEV_STYLE = {
    "EMERGENCY": ("🚨", "badge-EMERGENCY"),
    "SEVERE":    ("⚠️",  "badge-SEVERE"),
    "MODERATE":  ("⚠️",  "badge-MODERATE"),
    "MILD":      ("✅",  "badge-MILD"),
}


def _update_worst_severity(sev: str):
    current = st.session_state.worst_severity
    if _SEV_ORDER.index(sev) > _SEV_ORDER.index(current):
        st.session_state.worst_severity = sev


def run_analysis(prompt_text: str):
    lang      = st.session_state.lang_code
    # Derive display name from code — no implicit global dependency
    lang_name = next((k for k, v in LANGUAGES.items() if v == lang), "English")
    _has_a    = st.session_state.pending_audio_bytes is not None
    _has_i    = st.session_state.pending_image_bytes is not None

    _display = prompt_text or ("🎤 Voice message" if _has_a else "")
    if _has_i:
        _display += (" 🖼️" if _display else "🖼️ Image uploaded")

    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(_display or "_No input provided_")
    st.session_state.messages.append({"role": "user", "content": _display or "_No input provided_"})

    _fa_card     = get_first_aid_card(prompt_text) if prompt_text else None
    _fa_rendered = fa_html(_fa_card) if _fa_card else ""

    tmp_audio = tmp_image = None
    try:
        if _has_a:
            _t = tempfile.NamedTemporaryFile(delete=False, suffix=f".{st.session_state.pending_audio_ext}")
            _t.write(st.session_state.pending_audio_bytes); _t.close()
            tmp_audio = _t.name

        if _has_i:
            _t = tempfile.NamedTemporaryFile(delete=False, suffix=f".{st.session_state.pending_image_ext}")
            _t.write(st.session_state.pending_image_bytes); _t.close()
            tmp_image = _t.name

        _eng_text = to_english(prompt_text, lang) if prompt_text else prompt_text

        # Prepend patient profile to query if filled in
        _profile = st.session_state.patient_profile
        if _profile["name"] or _profile["age"] or _profile["conditions"]:
            _pinfo = (
                f"[Patient: {_profile['name'] or 'Unknown'}, "
                f"Age: {_profile['age'] or 'Unknown'}, "
                f"Conditions: {_profile['conditions'] or 'None'}] "
            )
            _eng_text = (_pinfo + (_eng_text or "")).strip() if _eng_text else _pinfo.strip()

        _history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        # Country for localised emergency numbers
        _country = _env["location"]["country"] if _env else ""

        with st.chat_message("assistant", avatar="🤖"):
            if _fa_rendered:
                st.markdown(_fa_rendered, unsafe_allow_html=True)

            with st.spinner("Analyzing your symptoms…"):
                _result = process(
                    audio_path=tmp_audio,
                    text_input=_eng_text,
                    image_path=tmp_image,
                    conversation_history=_history,
                    country=_country,
                )

            _response_display = _result["response"]
            if lang != "en":
                with st.spinner(f"Translating to {lang_name}…"):
                    _response_display = from_english(_result["response"], lang)

            _sev = _result["severity"]
            _icon, _cls = _SEV_STYLE.get(_sev, ("✅", "badge-MILD"))

            # Emergency glow wrapper
            if _sev == "EMERGENCY":
                st.markdown(
                    "<div style='border:1.5px solid rgba(255,75,75,.5);border-radius:12px;"
                    "padding:12px 14px;background:rgba(255,75,75,.04);"
                    "box-shadow:0 0 24px rgba(255,75,75,.2),inset 0 0 24px rgba(255,75,75,.03);"
                    "margin-bottom:10px;animation:pulse-emergency 2s infinite'>",
                    unsafe_allow_html=True,
                )

            st.markdown(f'<span class="badge {_cls}">{_icon} {_sev}</span>', unsafe_allow_html=True)
            st.markdown(_response_display)

            if _sev == "EMERGENCY":
                st.markdown("</div>", unsafe_allow_html=True)

            # Source citations — pill style
            _sources = _result.get("sources", [])
            if _sources:
                _pills = "".join(
                    f"<span style='background:#0D1B2A;border:1px solid #1F3A5F;"
                    f"border-radius:20px;padding:3px 11px;font-size:12px;color:#39D0FF;"
                    f"font-weight:500'>{s}</span>"
                    for s in _sources
                )
                st.markdown(
                    f"<div style='margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap'>"
                    f"<span style='font-size:12px;color:#484F58;font-weight:600;text-transform:uppercase;"
                    f"letter-spacing:.8px'>Sources</span>{_pills}</div>",
                    unsafe_allow_html=True,
                )

            # Voice output — only if toggle is on
            _audio_bytes = None
            if st.session_state.voice_output:
                with st.spinner("Generating audio…"):
                    try:
                        _audio_bytes = text_to_speech(_result["response"])
                    except Exception:
                        _audio_bytes = None
            if _audio_bytes:
                st.audio(_audio_bytes, format="audio/mp3")

        if _result["query"] and tmp_audio:
            st.session_state.messages[-1]["content"] = f'🎤 *"{_result["query"]}"*'

        _update_worst_severity(_result["severity"])
        st.session_state.messages.append({
            "role":           "assistant",
            "content":        _response_display,
            "severity":       _result["severity"],
            "audio_bytes":    _audio_bytes,
            "first_aid_html": _fa_rendered,
            "sources":        _result.get("sources", []),
        })
        # Save to DB (cloud or local SQLite fallback)
        save_consultation(
            user_id    = st.session_state.user_id,
            session_id = st.session_state.session_id,
            messages   = st.session_state.messages,
            severity   = st.session_state.worst_severity,
            city       = _city,
        )
        # Also keep local JSON as secondary backup
        save_session(
            st.session_state.messages,
            st.session_state.worst_severity,
            session_id=st.session_state.session_id,
        )

    finally:
        for _p in [tmp_audio, tmp_image]:
            if _p and os.path.exists(_p):
                try: os.unlink(_p)
                except OSError: pass
        st.session_state.pending_audio_bytes = None
        st.session_state.pending_image_bytes = None
        st.session_state.file_key += 1


# ══════════════════════════ CONSULTATION TAB ══════════════════════════════════
with _tab_chat:

    # ── Demo Mode — shown only when chat is empty ─────────────────────────────
    if not st.session_state.messages:
        st.markdown(
            "<div style='text-align:center;padding:20px 0 8px'>"
            "<p style='color:#484F58;font-size:13px;font-weight:600;text-transform:uppercase;"
            "letter-spacing:1.2px;margin-bottom:16px'>Try an example</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        _demo_queries = [
            ("🤒", "I have high fever and body ache since 2 days. What should I do?"),
            ("💊", "What is the dosage of paracetamol for adults? Are there any side effects?"),
            ("🩸", "My fasting blood sugar is 130 mg/dL. Is that normal? What should I eat?"),
            ("🫀", "What are the early signs of a heart attack I should never ignore?"),
            ("🦟", "How do I know if I have dengue fever and what is the treatment?"),
            ("😴", "I have been getting very poor sleep for weeks. What are the health risks?"),
        ]
        _demo_cols = st.columns(3)
        for _di, (_icon, _q) in enumerate(_demo_queries):
            with _demo_cols[_di % 3]:
                if st.button(
                    f"{_icon} {_q[:45]}…" if len(_q) > 45 else f"{_icon} {_q}",
                    use_container_width=True,
                    key=f"demo_{_di}",
                ):
                    run_analysis(_q)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # PDF download button
    if st.session_state.messages:
        _pdf_col, _spacer = st.columns([1, 4])
        with _pdf_col:
            if st.button("📄 Download Report", use_container_width=True):
                with st.spinner("Generating PDF…"):
                    _pdf_bytes = generate_report(
                        st.session_state.messages,
                        severity=st.session_state.worst_severity,
                        city=_city,
                    )
                _fname = f"medical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.download_button(
                    label="⬇️ Click to download",
                    data=_pdf_bytes,
                    file_name=_fname,
                    mime="application/pdf",
                    use_container_width=True,
                )

    # Chat history
    for _msg in st.session_state.messages:
        _avatar = "🧑‍💼" if _msg["role"] == "user" else "🤖"
        with st.chat_message(_msg["role"], avatar=_avatar):
            if _msg["role"] == "assistant":
                if _msg.get("first_aid_html"):
                    st.markdown(_msg["first_aid_html"], unsafe_allow_html=True)
                if _msg.get("severity"):
                    _sev = _msg["severity"]
                    _icon, _cls = _SEV_STYLE.get(_sev, ("✅", "badge-MILD"))
                    st.markdown(
                        f'<span class="badge {_cls}">{_icon} {_sev}</span>',
                        unsafe_allow_html=True,
                    )
            st.markdown(_msg["content"])
            if _msg.get("sources"):
                _spills = "".join(
                    f"<span style='background:#0D1B2A;border:1px solid #1F3A5F;"
                    f"border-radius:20px;padding:3px 11px;font-size:12px;color:#39D0FF;"
                    f"font-weight:500'>{s}</span>"
                    for s in _msg["sources"]
                )
                st.markdown(
                    f"<div style='margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap'>"
                    f"<span style='font-size:12px;color:#484F58;font-weight:600;text-transform:uppercase;"
                    f"letter-spacing:.8px'>Sources</span>{_spills}</div>",
                    unsafe_allow_html=True,
                )
            if _msg.get("audio_bytes"):
                st.audio(_msg["audio_bytes"], format="audio/mp3")

    # Triggers
    if st.session_state.trigger_analyze:
        st.session_state.trigger_analyze = False
        run_analysis("")
        st.rerun()

    if _prompt := st.chat_input("Describe your symptoms or ask a medical question…"):
        run_analysis(_prompt)
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#484F58;font-size:13px'>"
    "AI Medical Assistant · Groq LLaMA · Pinecone RAG · Open-Meteo · OpenStreetMap<br>"
    "For educational purposes only · Not a substitute for professional medical advice"
    "</div>",
    unsafe_allow_html=True,
)
