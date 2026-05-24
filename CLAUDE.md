# CLAUDE.md

# 🏥 AI Medical Assistant Project Context

This file contains complete project context and development roadmap for Claude Code.

---

# 📌 Project Goal

Develop a modern AI-powered multimodal healthcare assistant capable of:
- Understanding voice, text, and medical images
- Providing preliminary medical guidance
- Detecting emergency situations
- Recommending nearby hospitals
- Maintaining conversational memory
- Generating intelligent contextual responses

The final system should resemble a modern AI healthcare platform rather than a simple chatbot.

---

# ✅ Current Features

## Implemented

- Voice Input
- Text Input
- Medical Image Upload
- RAG-based Medical Responses
- Severity Detection
- Emergency Detection
- Nearby Hospital Recommendation
- Conversational Memory
- Voice Response
- Streamlit Dashboard
- Gradio Prototype

---

# 🚧 Planned Features

- PDF Medical Report Generation
- Weather-aware Disease Suggestions
- Seasonal Disease Awareness
- Chat-style Conversation UI
- Interactive Dashboard
- Follow-up Question Flow
- Medical History Tracking
- Specialist Recommendation System
- Multilingual Support

## 🌦 Context-Aware Healthcare Intelligence

Planned implementation of environmental and seasonal medical reasoning.

The system should:
- understand current weather conditions
- understand seasonal disease trends
- understand ongoing disease outbreaks
- inject contextual healthcare information into AI responses

Example:
- rainy season → higher viral/dengue probability
- winter → flu/cold prevalence
- summer → dehydration/heatstroke
- pandemic periods → respiratory illness consideration

Implementation ideas:
- Weather APIs
- Prompt injection
- Context-aware RAG
- Disease trend datasets

Goal:
Transform responses from generic medical replies into contextually intelligent healthcare guidance.

---

# 🧠 Current Architecture

## Frontend
- Streamlit
- Gradio (legacy prototype)

## Backend
- Python

## AI Stack
- Groq LLM
- Gemini Vision API
- LangChain
- HuggingFace Embeddings

## Vector Database
- Pinecone

## APIs
- OpenStreetMap / Overpass
- Weather APIs
- Gemini API
- Groq API

---

# 📂 Important Files

## Frontend

### streamlit_app.py
Modern dashboard UI.

### app.py
Older Gradio-based UI.

---

## Core Backend

### multimodal.py
Main orchestration layer.

Handles:
- text input
- voice input
- image analysis
- emergency routing
- severity analysis
- memory

---

### rag_pipeline.py
Handles:
- RAG retrieval
- Pinecone integration
- LangChain pipeline
- LLM responses

---

### vision.py
Handles:
- image analysis
- Gemini Vision integration

---

### emergency.py
Handles:
- emergency keyword detection
- emergency classification

---

### severity.py
Handles:
- severity classification
- mild/moderate/severe/emergency logic

---

### hospital_finder.py
Handles:
- nearby hospital recommendations
- maps links
- emergency hospital suggestions

---

### voice_input.py
Speech-to-text pipeline.

---

### voice_output.py
Text-to-speech pipeline.

---

# 🎨 Design Goals

The application should:
- feel modern
- resemble a healthcare SaaS product
- have clean dark UI
- support conversational interactions
- prioritize emergency visibility
- provide interactive healthcare workflows

---

# 🧭 Development Roadmap

## Phase 1 — Core AI
✅ Voice Input  
✅ Text Input  
✅ Image Upload  
✅ RAG Integration  
✅ Emergency Detection  
✅ Severity Detection  

---

## Phase 2 — UI Transformation
✅ Streamlit Dashboard  
🚧 Chat-style UI  
🚧 Animated Severity Cards  
🚧 Better Medical Dashboard  

---

## Phase 3 — Advanced Intelligence
🚧 Context-aware Responses  
🚧 Weather-aware Disease Prediction  
🚧 Current Disease Awareness  
🚧 Follow-up Medical Reasoning  

---

## Phase 4 — Healthcare Workflow
🚧 PDF Report Generation  
🚧 Medical History Tracking  
🚧 Specialist Recommendation  
🚧 Better Hospital Recommendation  

---

# ⚠ Important Development Notes

- Keep backend modular.
- Avoid breaking existing APIs.
- Maintain compatibility with Streamlit frontend.
- Prefer lightweight/free APIs.
- UI polish is extremely important.
- Focus on healthcare workflow feel rather than pure chatbot feel.

---

# 🧪 Testing Focus

Test cases should include:
- normal symptoms
- emergency symptoms
- follow-up questions
- image analysis
- conversational memory
- severity classification

---

# 🎯 Final Goal

Transform the system from:
"medical chatbot"

into:

"AI-powered healthcare assistant platform"

with:
- multimodal intelligence
- contextual reasoning
- healthcare workflow support
- modern UI/UX

---