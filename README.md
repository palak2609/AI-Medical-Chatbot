# 🏥 AI Medical Assistant

An AI-powered multimodal healthcare assistant capable of analyzing user symptoms through text, voice, and medical images. The system uses Retrieval-Augmented Generation (RAG), emergency detection, conversational memory, and contextual medical reasoning to provide intelligent healthcare guidance.

---

# 🚀 Project Overview

AI Medical Assistant is a smart healthcare platform designed to provide preliminary medical guidance using Artificial Intelligence.

The system supports:
- 🎤 Voice Input
- 📝 Text Input
- 🖼 Medical Image Analysis
- 🚨 Emergency Detection
- 🧠 Conversational Memory
- 📚 RAG-based Medical Responses
- 🏥 Hospital Recommendation System
- 🌦 Context-aware Medical Suggestions

This project aims to simulate a modern AI healthcare assistant platform capable of assisting users with symptom analysis and basic healthcare guidance.

---

# ✨ Features

## ✅ Implemented Features

### 🎤 Voice Input
- Upload or record voice symptoms
- Speech-to-text conversion using AI

### 📝 Text Input
- Direct symptom-based interaction

### 🖼 Medical Image Analysis
- Upload medical/skin-related images
- AI-based image understanding and analysis

### 🧠 RAG-Based Medical Assistant
- Uses Retrieval-Augmented Generation
- Retrieves relevant medical context before generating responses

### 🚨 Emergency Detection System
Detects dangerous symptoms such as:
- Chest pain
- Breathing difficulty
- Stroke symptoms
- Severe bleeding

Provides:
- Emergency alerts
- Urgent guidance
- Nearby hospital recommendations

### ⚠ Severity Detection
Classifies conditions into:
- Mild
- Moderate
- Severe
- Emergency

### 🏥 Nearby Hospital Recommendation
Suggests:
- Nearby hospitals
- Google Maps links
- Emergency healthcare centers

### 🔊 Voice Response
Converts AI-generated response into speech.

### 💬 Conversational Memory
Maintains previous conversation context for follow-up interactions.

---

# 🚧 Upcoming Features

- 📄 PDF Medical Report Generation
- 🌦 Weather-aware Disease Prediction
- 🦠 Current Disease Awareness (COVID, Viral outbreaks)
- 📊 Health Dashboard
- 💊 Medicine Reminder System
- 👨‍⚕ Specialist Recommendation System
- 📈 Medical History Tracking
- 🌐 Multilingual Support



# 🌦 Context-Aware Medical Intelligence

One of the key innovations of this project is its ability to perform context-aware healthcare reasoning.

Instead of generating generic responses, the AI assistant can take into account:

- Current weather conditions
- Seasonal disease patterns
- Ongoing public health situations
- Environmental context
- Symptom trends common during specific periods

This enables the system to generate more realistic and medically relevant responses.

---

## 🧠 Example Scenarios

### ☔ Rainy Season
During monsoon/rainy seasons, the system may consider:
- Viral fever
- Cold and cough
- Dengue risk
- Flu infections

Example:
If a user reports fever, body pain, and weakness during rainy season, the AI may mention the possibility of seasonal viral infections.

---

### ☀ Summer Season
During high-temperature conditions, the system may consider:
- Dehydration
- Heatstroke
- Fatigue
- Electrolyte imbalance

---

### 🦠 Pandemic / Outbreak Awareness
The system is designed to support current disease awareness.

For example:
- During COVID-like outbreaks, respiratory symptoms may trigger contextual analysis related to viral spread patterns.
- During flu outbreaks, symptom matching may prioritize seasonal flu possibilities.

---

## ⚙ Planned Technical Implementation

The contextual reasoning layer will use:
- Weather APIs
- Seasonal logic
- Prompt engineering
- Context injection into the RAG pipeline
- Disease trend mapping

This allows the assistant to behave more like an intelligent healthcare support system instead of a static chatbot.

---
---

# 🏗 System Architecture

## Input Layer
- Voice Input
- Text Input
- Image Upload

↓

## AI Processing Layer
- Speech-to-Text
- Image Analysis
- RAG Pipeline
- Severity Detection
- Emergency Detection
- Conversational Memory
- Context-aware Reasoning

↓

## Response Layer
- AI Medical Guidance
- Voice Response
- Emergency Alerts
- Hospital Recommendations
- Medical Reports

---

# 🛠 Tech Stack

## Frontend
- Streamlit
- Gradio (Initial Prototype)

## Backend
- Python

## AI / ML
- LangChain
- Groq LLM
- Gemini Vision API
- HuggingFace Embeddings

## Vector Database
- Pinecone

## APIs
- Groq API
- Gemini API
- OpenStreetMap API
- Weather API

## Other Libraries
- gTTS
- PIL
- dotenv
- requests

---

# 📂 Project Structure

```bash
AI-Medical-Assistant/
│
├── app.py
├── streamlit_app.py
├── requirements.txt
├── README.md
├── CLAUDE.md
│
├── src/
│   ├── multimodal.py
│   ├── rag_pipeline.py
│   ├── vision.py
│   ├── emergency.py
│   ├── severity.py
│   ├── hospital_finder.py
│   ├── voice_input.py
│   ├── voice_output.py
│   └── prompt.py
│
├── data/
│
└── research/
```

---

# ⚙ Installation

## 1. Clone Repository

```bash
git clone <repository-url>
cd AI-Medical-Assistant
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

### Windows
```bash
venv\Scripts\activate
```

### Mac/Linux
```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_key
PINECONE_API_KEY=your_key
GEMINI_API_KEY=your_key
```

---

# ▶ Running the Project

## Streamlit Frontend

```bash
streamlit run streamlit_app.py
```

## Gradio Version

```bash
python app.py
```

---

# 📸 Screenshots

## Dashboard
(Add Screenshot)

## Emergency Detection
(Add Screenshot)

## Image Analysis
(Add Screenshot)

---

# 🎯 Future Scope

- Integration with wearable devices
- Real-time health monitoring
- Doctor consultation integration
- AI-powered health prediction
- Multi-language healthcare assistant
- Cloud deployment
- User authentication system

---

# ⚠ Disclaimer

This project is for educational and research purposes only.

The AI-generated responses are not a substitute for professional medical diagnosis, treatment, or emergency healthcare services.

Always consult qualified healthcare professionals for medical advice.

---

# 👩‍💻 Developed By

Palak Srivastava  
B.Tech IT  
Manipal University Jaipur

---