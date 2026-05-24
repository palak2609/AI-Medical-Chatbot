import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.multimodal import process
from src.context_engine import get_user_location, get_weather, get_season

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
# CSS — white text everywhere, bigger/brighter sidebar text
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>

/* ── Base background ── */
.stApp { background-color: #0D1117; }

/* ── Chat message body — was rendering dim grey on dark bg ── */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] a,
[data-testid="stChatMessage"] code {
    color: #E6EDF3 !important;
    font-size: 15px;
    line-height: 1.75;
}

/* ── Sidebar list items and feature text — were dim ── */
[data-testid="stSidebar"] .stMarkdown li,
[data-testid="stSidebar"] .stMarkdown p {
    color: #C9D1D9 !important;
    font-size: 14px !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #E6EDF3 !important;
    font-size: 16px !important;
}
[data-testid="stSidebar"] .stCaption p {
    color: #8B949E !important;
    font-size: 13px !important;
}

/* ── Context card — on dark #161B22 background ── */
.ctx-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.8;
    color: #C9D1D9;
    margin-bottom: 10px;
}
.ctx-card b { color: #79C0FF; }

/* ── Severity badges ── */
.badge {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
}
.badge-EMERGENCY { background: #FF4B4B; color: #fff; }
.badge-SEVERE    { background: #FF8C00; color: #fff; }
.badge-MODERATE  { background: #B8860B; color: #fff; }
.badge-MILD      { background: #238636; color: #fff; }

/* ── Buttons ── */
div.stButton > button {
    background: linear-gradient(90deg, #1f6feb, #388bfd);
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
}
div.stButton > button:hover {
    background: linear-gradient(90deg, #388bfd, #58a6ff);
}

/* ── Footer ── */
section.main > div { padding-bottom: 90px; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
defaults = {
    "messages": [],
    "pending_audio_bytes": None,
    "pending_audio_ext": "wav",
    "pending_image_bytes": None,
    "pending_image_ext": "jpg",
    "file_key": 0,          # incrementing key resets file uploaders
    "trigger_analyze": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 AI Medical Assistant")
    st.caption("Voice · Vision · RAG · Context-Aware")
    st.divider()

    # ── Environmental context ─────────────────────────────────────────────────
    st.markdown("### 🌍 Your Context")

    @st.cache_data(ttl=600, show_spinner=False)
    def fetch_env():
        loc = get_user_location()
        if not loc:
            return None
        w = get_weather(loc["lat"], loc["lon"])
        s = get_season(loc["lat"], loc["lon"])
        return {"location": loc, "weather": w, "season": s}

    env = fetch_env()
    if env:
        loc = env["location"]
        w   = env["weather"]
        s   = env["season"]
        html = (
            "<div class='ctx-card'>"
            f"📍 <b>{loc['city']}, {loc['country']}</b><br>"
            f"🍂 Season: <b>{s}</b>"
        )
        if w:
            html += (
                f"<br>🌡️ Temp: <b>{w['temp_c']}°C</b>"
                f"<br>💧 Humidity: <b>{w['humidity']}%</b>"
                f"<br>☁️ {w['condition']}"
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Location unavailable — context features limited.")

    st.divider()

    # ── Attachments ───────────────────────────────────────────────────────────
    st.markdown("### 📎 Attach Files")

    # Browser mic recording (Streamlit ≥ 1.34)
    recorded_audio = None
    try:
        recorded_audio = st.audio_input("🎙️ Record Voice")
    except AttributeError:
        pass

    fkey = st.session_state.file_key
    uploaded_audio = st.file_uploader(
        "🎤 Or upload audio",
        type=["wav", "mp3", "ogg", "m4a"],
        key=f"audio_upload_{fkey}",
    )
    uploaded_image = st.file_uploader(
        "🖼️ Upload Medical Image",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"image_upload_{fkey}",
    )

    # Persist uploads in session state
    if recorded_audio is not None:
        st.session_state.pending_audio_bytes = recorded_audio.read()
        st.session_state.pending_audio_ext = "wav"
    elif uploaded_audio is not None:
        st.session_state.pending_audio_bytes = uploaded_audio.read()
        st.session_state.pending_audio_ext = uploaded_audio.name.rsplit(".", 1)[-1]

    if uploaded_image is not None:
        st.session_state.pending_image_bytes = uploaded_image.read()
        st.session_state.pending_image_ext = uploaded_image.name.rsplit(".", 1)[-1]

    has_audio = st.session_state.pending_audio_bytes is not None
    has_image = st.session_state.pending_image_bytes is not None

    if has_audio or has_image:
        attached = []
        if has_audio: attached.append("🎤 audio")
        if has_image: attached.append("🖼️ image")
        st.success(f"Ready: {', '.join(attached)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Analyze", use_container_width=True):
                st.session_state.trigger_analyze = True
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.pending_audio_bytes = None
                st.session_state.pending_image_bytes = None
                st.session_state.file_key += 1   # resets the file uploader widgets
                st.rerun()

    st.divider()

    # ── Controls ──────────────────────────────────────────────────────────────
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_audio_bytes = None
        st.session_state.pending_image_bytes = None
        st.session_state.file_key += 1
        st.rerun()

    st.divider()

    # ── Features list ─────────────────────────────────────────────────────────
    st.markdown("### ✅ Active Features")
    for feat in [
        "🧠 RAG Medical Knowledge",
        "🎤 Voice Input (Whisper)",
        "🖼️ Real Image Analysis",
        "🚨 Emergency Detection",
        "⚠️ Severity Classification",
        "🏥 Nearby Hospital Finder",
        "🌍 Context-Aware Responses",
        "💬 Conversational Memory",
        "🔊 Voice Response",
    ]:
        st.markdown(f"- {feat}")

    st.divider()
    st.warning(
        "⚠️ **Disclaimer:** Preliminary AI guidance only. "
        "Always consult a qualified doctor. "
        "Emergencies: call **112** (India) immediately."
    )

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;color:#4DA6FF;margin-bottom:2px;font-size:42px'>"
    "🏥 AI Medical Assistant</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#8B949E;margin-bottom:24px;font-size:16px'>"
    "Multimodal · Context-Aware · Emergency-Ready</p>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────────────────────────────────────
_SEV = {
    "EMERGENCY": ("🚨", "badge-EMERGENCY"),
    "SEVERE":    ("⚠️", "badge-SEVERE"),
    "MODERATE":  ("⚠️", "badge-MODERATE"),
    "MILD":      ("✅", "badge-MILD"),
}

for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant" and msg.get("severity"):
            sev = msg["severity"]
            icon, cls = _SEV.get(sev, ("✅", "badge-MILD"))
            st.markdown(
                f'<span class="badge {cls}">{icon} {sev}</span>',
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])
        if msg.get("audio_bytes"):
            st.audio(msg["audio_bytes"], format="audio/mp3")

# ─────────────────────────────────────────────────────────────────────────────
# PROCESS HELPER — called from both chat_input and "Analyze" button
# ─────────────────────────────────────────────────────────────────────────────
def run_analysis(prompt_text: str):
    has_audio = st.session_state.pending_audio_bytes is not None
    has_image = st.session_state.pending_image_bytes is not None

    # Build display text for user bubble
    display = prompt_text or ("🎤 Voice message" if has_audio else "")
    if has_image:
        display += (" 🖼️" if display else "🖼️ Image uploaded")

    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(display or "_No text provided_")
    st.session_state.messages.append({"role": "user", "content": display or "_No text provided_"})

    tmp_audio = None
    tmp_image = None

    try:
        # Write audio to temp file
        if has_audio:
            ext = st.session_state.pending_audio_ext
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tmp.write(st.session_state.pending_audio_bytes)
            tmp.close()
            tmp_audio = tmp.name

        # Write image to temp file
        if has_image:
            ext = st.session_state.pending_image_ext
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tmp.write(st.session_state.pending_image_bytes)
            tmp.close()
            tmp_image = tmp.name

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing your symptoms..."):
                result = process(
                    audio_path=tmp_audio,
                    text_input=prompt_text,
                    image_path=tmp_image,
                    conversation_history=history,
                )

            sev = result["severity"]
            icon, cls = _SEV.get(sev, ("✅", "badge-MILD"))
            st.markdown(
                f'<span class="badge {cls}">{icon} {sev}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(result["response"])
            if result.get("audio_bytes"):
                st.audio(result["audio_bytes"], format="audio/mp3")

        # If voice was used, update the user bubble with transcription
        if result["query"] and tmp_audio:
            st.session_state.messages[-1]["content"] = f'🎤 *"{result["query"]}"*'

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"],
            "severity": result["severity"],
            "audio_bytes": result.get("audio_bytes"),
        })

    finally:
        for path in [tmp_audio, tmp_image]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        st.session_state.pending_audio_bytes = None
        st.session_state.pending_image_bytes = None
        st.session_state.file_key += 1

# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER: "Analyze" button (attachment with no text)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.trigger_analyze:
    st.session_state.trigger_analyze = False
    run_analysis("")
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER: chat_input (text with optional attachment)
# ─────────────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Describe your symptoms or ask a medical question..."):
    run_analysis(prompt)
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
