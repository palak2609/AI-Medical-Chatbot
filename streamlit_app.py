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
from src.context_engine  import get_user_location, get_weather, get_season
from src.first_aid       import get_card as get_first_aid_card, all_cards, render_html as fa_html
from src.history         import save_session, load_history, clear_history
from src.pdf_report      import generate_report
from src.translator      import LANGUAGES, to_english, from_english
from src.report_analyzer import analyze_pdf, analyze_image_report
from src.voice_output    import text_to_speech

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
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:4px 0 12px'>"
        "<div style='font-size:19px;font-weight:800;color:#E6EDF3;letter-spacing:-.3px'>🏥 MediAssist AI</div>"
        "<div style='display:flex;align-items:center;gap:6px;margin-top:5px'>"
        "<span style='width:7px;height:7px;border-radius:50%;background:#3FB950;"
        "box-shadow:0 0 6px #3FB950;display:inline-block'></span>"
        "<span style='font-size:12px;color:#6E7681;font-weight:500'>System Online</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Environmental context ─────────────────────────────────────────────────
    st.markdown("### 🌍 Your Context")

    @st.cache_data(ttl=600, show_spinner=False)
    def _fetch_env():
        loc = get_user_location()
        if not loc:
            return None
        return {
            "location": loc,
            "weather":  get_weather(loc["lat"], loc["lon"]),
            "season":   get_season(loc["lat"], loc["lon"]),
        }

    _env = _fetch_env()
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
    else:
        st.info("Location unavailable — context features limited.")

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

    # ── Medical History ───────────────────────────────────────────────────────
    with st.expander("📋 Consultation History"):
        _hist = load_history()
        if not _hist:
            st.info("No past consultations saved yet.")
        else:
            for _entry in _hist[:10]:
                _sev = _entry.get("severity", "MILD")
                _pill = (
                    f"<span class='hist-pill hist-{_sev}'>{_sev}</span>"
                )
                st.markdown(
                    f"**{_entry['date_display']}** {_pill}<br>"
                    f"<span style='color:#C9D1D9;font-size:14px'>{_entry['main_complaint'][:80]}</span>",
                    unsafe_allow_html=True,
                )
                with st.expander("View AI summary", expanded=False):
                    st.write(_entry.get("ai_summary", "—"))
                st.markdown("---")
            if st.button("🗑️ Clear All History", use_container_width=True):
                clear_history()
                st.rerun()

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
# TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_chat, _tab_report, _tab_eval = st.tabs(["💬 Consultation", "🔬 Analyze Medical Report", "📊 Evaluation"])

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

# ══════════════════════════ EVALUATION TAB ════════════════════════════════════
with _tab_eval:
    st.markdown(
        "<h3 style='color:#E6EDF3;font-size:22px;font-weight:700;margin-bottom:4px'>"
        "RAG vs Plain LLM — Ablation Study</h3>"
        "<p style='color:#8B949E;font-size:15px;margin-bottom:20px'>"
        "Compares responses from the full RAG pipeline (Pinecone + 3 knowledge sources) "
        "against a plain LLM with no medical knowledge base. "
        "Scored 1–5 by an independent LLM judge on accuracy, specificity, and grounding.</p>",
        unsafe_allow_html=True,
    )

    _eval_file = os.path.join("data", "eval_results.json")

    if not os.path.exists(_eval_file):
        st.info(
            "Evaluation results not generated yet.\n\n"
            "Run this command once from your project folder:\n\n"
            "```\npython eval.py\n```\n\n"
            "It tests 20 medical questions, compares RAG vs plain LLM, "
            "and saves results here automatically."
        )
    else:
        import json as _json
        with open(_eval_file, encoding="utf-8") as _ef:
            _edata = _json.load(_ef)

        _summary = _edata.get("summary", {})
        _results = _edata.get("results", [])

        # ── Summary banner ────────────────────────────────────────────────────
        _c1, _c2, _c3 = st.columns(3)
        _avg_rag = _summary.get("avg_rag_score", 0)
        _avg_llm = _summary.get("avg_llm_score", 0)
        _improvement = _summary.get("improvement_pct", 0)

        with _c1:
            st.markdown(
                f"<div style='background:#0D1B2A;border:1px solid #1F3A5F;border-radius:12px;padding:18px;text-align:center'>"
                f"<div style='color:#8B949E;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px'>RAG Pipeline</div>"
                f"<div style='color:#58A6FF;font-size:36px;font-weight:800;margin:6px 0'>{_avg_rag:.1f}<span style='font-size:18px'>/5</span></div>"
                f"<div style='color:#8B949E;font-size:13px'>Average Score</div>"
                f"</div>", unsafe_allow_html=True)
        with _c2:
            st.markdown(
                f"<div style='background:#0D1B2A;border:1px solid #2D1B5F;border-radius:12px;padding:18px;text-align:center'>"
                f"<div style='color:#8B949E;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Plain LLM</div>"
                f"<div style='color:#A371F7;font-size:36px;font-weight:800;margin:6px 0'>{_avg_llm:.1f}<span style='font-size:18px'>/5</span></div>"
                f"<div style='color:#8B949E;font-size:13px'>Average Score</div>"
                f"</div>", unsafe_allow_html=True)
        with _c3:
            _imp_val   = abs(_improvement)
            _imp_sign  = "+" if _improvement >= 0 else "-"
            _imp_color = "#3FB950" if _improvement >= 0 else "#FFA040"
            _imp_label = "RAG over Plain LLM" if _improvement >= 0 else "LLM slightly ahead"
            st.markdown(
                f"<div style='background:#0D1B2A;border:1px solid #1B3A1F;border-radius:12px;padding:18px;text-align:center'>"
                f"<div style='color:#8B949E;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Score Difference</div>"
                f"<div style='color:{_imp_color};font-size:36px;font-weight:800;margin:6px 0'>{_imp_sign}{_imp_val:.0f}<span style='font-size:18px'>%</span></div>"
                f"<div style='color:#8B949E;font-size:13px'>{_imp_label}</div>"
                f"</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Knowledge sources used ────────────────────────────────────────────
        _sources_used = _summary.get("knowledge_sources", [])
        if _sources_used:
            st.markdown(
                "<p style='color:#8B949E;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Knowledge Sources</p>",
                unsafe_allow_html=True,
            )
            _src_html = " &nbsp;·&nbsp; ".join(
                f"<span style='color:#C9D1D9;background:#161B22;border:1px solid #30363D;"
                f"border-radius:6px;padding:3px 10px;font-size:13px'>{s}</span>"
                for s in _sources_used
            )
            st.markdown(_src_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # ── Per-question breakdown ────────────────────────────────────────────
        st.markdown(
            "<p style='color:#E6EDF3;font-size:16px;font-weight:600;margin-bottom:12px'>Question-by-Question Breakdown</p>",
            unsafe_allow_html=True,
        )

        _categories = {}
        for _r in _results:
            _cat = _r.get("category", "General")
            _categories.setdefault(_cat, []).append(_r)

        for _cat, _items in _categories.items():
            st.markdown(
                f"<p style='color:#58A6FF;font-size:13px;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px'>{_cat}</p>",
                unsafe_allow_html=True,
            )
            for _r in _items:
                _rs  = _r.get("rag_score", 0)
                _ls  = _r.get("llm_score", 0)
                _srcs = ", ".join(_r.get("sources", [])) or "—"
                _winner = "RAG" if _rs >= _ls else "LLM"
                _win_col = "#58A6FF" if _winner == "RAG" else "#A371F7"
                st.markdown(
                    f"<div class='eval-card'>"
                    f"<div class='eval-q'>Q: {_r['question']}</div>"
                    f"<div style='display:flex;gap:32px;align-items:flex-start'>"
                    f"<div style='flex:1'>"
                    f"  <div class='eval-label'>RAG Pipeline</div>"
                    f"  <div class='eval-score eval-rag-score'>{_rs}/5</div>"
                    f"  <div class='score-bar-wrap'><div class='score-bar score-rag' style='width:{_rs/5*100:.0f}%'></div></div>"
                    f"  <div style='color:#8B949E;font-size:12px'>Sources: {_srcs}</div>"
                    f"</div>"
                    f"<div style='flex:1'>"
                    f"  <div class='eval-label'>Plain LLM</div>"
                    f"  <div class='eval-score eval-llm-score'>{_ls}/5</div>"
                    f"  <div class='score-bar-wrap'><div class='score-bar score-llm' style='width:{_ls/5*100:.0f}%'></div></div>"
                    f"  <div style='color:#8B949E;font-size:12px'>{_r.get('llm_note','No knowledge base')}</div>"
                    f"</div>"
                    f"<div style='text-align:center;min-width:80px'>"
                    f"  <div class='eval-label'>Winner</div>"
                    f"  <div style='color:{_win_col};font-size:18px;font-weight:800;margin-top:4px'>{_winner}</div>"
                    f"</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # ── Methodology note ──────────────────────────────────────────────────
        with st.expander("Methodology", expanded=False):
            st.markdown("""
**Evaluation approach:** LLM-as-judge (Groq LLaMA 3.1-8B-Instant)

Each response is scored 1–5 on three dimensions:
- **Accuracy** — Is the medical information correct?
- **Specificity** — Does it give concrete, actionable details (dosages, drug names, timelines)?
- **Grounding** — Is the answer supported by a cited source, or is it generic?

Final score = average of the three dimensions.

**RAG pipeline knowledge base:**
- Gale Encyclopedia of Medicine (11,718 chunks)
- WHO Essential Medicines List 2023 (205 chunks)
- WHO Model Formulary (1,848 chunks)

**Plain LLM baseline:** Same Groq LLaMA 3.1-8B-Instant model with no retrieval context.
            """)

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
        # Upsert — same session_id updates the same history entry
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
