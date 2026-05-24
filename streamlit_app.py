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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp {
    background-color: #0D1117;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #010409 !important;
    border-right: 1px solid #21262D;
}
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #E6EDF3 !important; font-size: 19px !important; font-weight: 700 !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #58A6FF !important; font-size: 12px !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 1px;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    color: #C9D1D9 !important; font-size: 15px !important; line-height: 1.75 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption p {
    color: #8B949E !important; font-size: 13px !important;
}

/* Context card */
.ctx-card {
    background: #0D1B2A; border: 1px solid #1F3A5F;
    border-radius: 12px; padding: 16px 18px;
    font-size: 15px; line-height: 1.9; color: #D0D7DE; margin-bottom: 12px;
}
.ctx-card b { color: #58A6FF; font-weight: 600; }

/* Chat messages */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] em,
[data-testid="stChatMessage"] a {
    color: #E6EDF3 !important; font-size: 16px !important; line-height: 1.85 !important;
}
[data-testid="stChatMessage"] h2 { font-size: 20px !important; font-weight: 700 !important; }
[data-testid="stChatMessage"] h3 { font-size: 17px !important; font-weight: 600 !important; }
[data-testid="stChatMessage"] code {
    background: #161B22 !important; color: #79C0FF !important;
    padding: 2px 7px !important; border-radius: 5px !important; font-size: 14px !important;
}
[data-testid="stChatMessage"] a { color: #58A6FF !important; text-decoration: underline; }

/* Severity badges */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 18px; border-radius: 50px;
    font-size: 12px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 14px;
}
.badge-EMERGENCY { background:rgba(255,75,75,.12);  color:#FF6B6B; border:1.5px solid #FF6B6B; }
.badge-SEVERE    { background:rgba(255,140,0,.12);  color:#FFA040; border:1.5px solid #FFA040; }
.badge-MODERATE  { background:rgba(210,160,0,.12);  color:#E5B000; border:1.5px solid #E5B000; }
.badge-MILD      { background:rgba(63,185,80,.12);  color:#3FB950; border:1.5px solid #3FB950; }

/* Buttons */
div.stButton > button {
    background: linear-gradient(135deg,#1f6feb,#388bfd);
    color:#fff !important; border:none !important; border-radius:10px;
    font-size:14px; font-weight:600; padding:8px 16px;
    transition:all .2s ease; box-shadow:0 2px 8px rgba(31,111,235,.3);
}
div.stButton > button:hover {
    background: linear-gradient(135deg,#388bfd,#58a6ff) !important;
    box-shadow:0 4px 16px rgba(88,166,255,.35) !important; transform:translateY(-1px);
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    font-size:15px !important; color:#E6EDF3 !important;
    background:#161B22 !important; border:1px solid #30363D !important; border-radius:12px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color:#6E7681 !important; }

/* History severity pills */
.hist-pill {
    display:inline-block; padding:2px 10px; border-radius:50px;
    font-size:11px; font-weight:700; letter-spacing:.5px;
}
.hist-EMERGENCY { background:#FF4B4B22; color:#FF6B6B; border:1px solid #FF6B6B; }
.hist-SEVERE    { background:#FF8C0022; color:#FFA040; border:1px solid #FFA040; }
.hist-MODERATE  { background:#D4A01722; color:#E5B000; border:1px solid #E5B000; }
.hist-MILD      { background:#3FB95022; color:#3FB950; border:1px solid #3FB950; }

[data-testid="stAlert"] p { font-size:14px !important; }
hr { border-color:#21262D !important; opacity:1 !important; }
section.main > div { padding-bottom:100px; }
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
    st.markdown("## 🏥 AI Medical Assistant")
    st.caption("Voice · Vision · RAG · Context-Aware")
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
    "<h1 style='text-align:center;color:#4DA6FF;margin-bottom:2px;font-size:44px;font-weight:800'>"
    "🏥 AI Medical Assistant</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#8B949E;margin-bottom:24px;font-size:16px'>"
    "Multimodal · Context-Aware · Emergency-Ready · Multilingual</p>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_chat, _tab_report = st.tabs(["💬 Consultation", "🔬 Analyze Medical Report"])

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
            st.markdown(f'<span class="badge {_cls}">{_icon} {_sev}</span>', unsafe_allow_html=True)
            st.markdown(_response_display)

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
