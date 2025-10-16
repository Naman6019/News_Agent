# 📰 AI News Agent — Automated News Digest via AI and WhatsApp 🤖  

An intelligent **FastAPI-based news agent** that automatically fetches RSS feeds, summarizes articles using **Gemma 3 (1B)** via **Ollama**, and sends personalized morning and evening WhatsApp digests using **Twilio**.  

Deployed on **Render Cloud**, with full REST API access, automated scheduling, and health monitoring.  

---

## ✨ Features  

- 📡 **Smart RSS Aggregation** — fetches articles from top sources (Technology, Business, Science, World).  
- 🧠 **AI Summarization via Ollama** — powered by `gemma3:1b`, efficient and cost-free.  
- 💬 **WhatsApp Delivery** — sends formatted daily digests via Twilio API.  
- ⏰ **Automated Scheduling** — sends digests at 8 AM and 6 PM IST.  
- 🩺 **Monitoring** — live health and status endpoints.  
- 🐳 **Docker & Render Ready** — deploy locally or on Render with zero config.  
- 💰 **Free AI** — uses local Ollama instead of paid APIs.  

---

## 🚀 Quick Start  

### 🧩 Prerequisites  

- **Python 3.11+**
- **Ollama** with `gemma3:1b` pulled (`ollama pull gemma3:1b`)
- **Twilio account** with WhatsApp sandbox setup
- **Render account** (for cloud deployment)

---

### ⚙️ 1. Clone & Setup  

```bash
git clone <your-repository-url>
cd News_Agent

### ⚙️ 2. Install Dependencies
pip install -r requirements.txt

### 3. Configure Environment

- **Copy and edit .env:**
- cp .env.example .env
#Example

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
WHATSAPP_RECIPIENT_NUMBER=whatsapp:+91XXXXXXXXXX
API_URL=https://your-render-app-name.onrender.com
CHECK_INTERVAL_MINUTES=360
LOG_LEVEL=INFO

### 🧠 Running the App
# ▶️ Local Development
- python -m app.main

#App runs at http://localhost:8000

#🐳 Docker (Local)
- docker-compose up --build -d

### Render Configuration 
OLLAMA_MODEL=gemma3:1b
OLLAMA_BASE_URL=http://localhost:11434
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
WHATSAPP_RECIPIENT_NUMBER=whatsapp:+91XXXXXXXXXX
API_URL=https://your-render-app-name.onrender.com
CHECK_INTERVAL_MINUTES=360
LOG_LEVEL=INFO
