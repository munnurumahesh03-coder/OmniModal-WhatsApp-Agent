# 🤖 HextGen Omni-Modal Onboarding Agent

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg )](https://www.python.org/ )
[![Playwright](https://img.shields.io/badge/Playwright-Web_Automation-2EAD33.svg )](https://playwright.dev/ )
[![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-Cloud_Database-47A248.svg )](https://www.mongodb.com/ )
[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B.svg )](https://streamlit.io/ )
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg )](https://www.docker.com/ )
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF.svg )](https://github.com/features/actions )

## 🌟 Live Deployment Links
* **Live Web Dashboard:** [View Streamlit Application](https://omnimodal-whatsapp-agent-3pjibcpz748vhpndaceeqv.streamlit.app/ )
* **Docker Image:** `docker pull ghcr.io/munnurumahesh03-coder/omnimodal-whatsapp-agent:latest`

## 📖 Overview
This project is an advanced **Omni-Modal Robotic Process Automation (RPA) Pipeline**. It utilizes a Playwright browser to continuously monitor multiple WhatsApp groups, dynamically extracting unstructured hospital onboarding data from any file format (Text, PDFs, CSVs, and Images). 

It leverages Google Gemini Vision and Groq LLMs to intelligently parse, clean, and structure the data into JSON. The structured data is securely merged into a cloud-hosted MongoDB Atlas database. The entire system is decoupled, allowing operations teams to control the bot's patrol route dynamically via a live **Streamlit Web Dashboard**.

## ⚙️ System Architecture (ETL Pipeline)

1. **Extract (Playwright & Omni-Modal Router):** A Playwright agent continuously patrols target WhatsApp groups. When a file is detected, it routes it to the correct engine: `PyMuPDF` for PDFs, `Pandas` for CSVs, or `Gemini 3.6 Flash Vision` for Images/Handwritten forms.
2. **Transform (LLM Parsing & Sanitization):** The raw text is passed to Groq (gpt-oss-120b). The AI identifies target entities and formats them into a strict JSON schema. A custom Python sanitization layer cleans phone numbers and validates mandatory fields.
3. **Load (MongoDB Atlas):** The script connects to MongoDB and uses `upsert=True` logic. It securely merges new data with historical records, preventing data loss and duplicate entries.
4. **Interact (Streamlit UI):** A live web dashboard fetches data directly from MongoDB, displaying onboarded hospitals, live audit logs, and allowing users to add/remove WhatsApp groups from the bot's patrol route in real-time.

## 🧠 Key Engineering Decisions
| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Web Automation** | Playwright | Handles asynchronous Single-Page Applications (like WhatsApp Web) better than Selenium, with built-in auto-waiting to prevent timeout errors. |
| **Data Structuring** | Groq LLM & Gemini Vision | Replaces brittle RegEx rules. The Omni-Modal AI understands context, allowing it to extract data from messy handwritten images or unstructured PDFs flawlessly. |
| **Database** | MongoDB Atlas | NoSQL document structure is perfectly suited for ingesting dynamic JSON outputs and handling complex `upsert` merge logic. |
| **Dynamic Config** | Streamlit + MongoDB | Hardcoding is eliminated. The bot fetches its target groups from the database every cycle, allowing non-technical users to control the bot via the UI. |
| **Deployment** | Docker & GitHub Actions | Containerizing the Playwright agent ensures it runs flawlessly on any cloud server, with GitHub Actions providing automated CI/CD image builds. |

## 🐳 Run Locally via Docker (Recommended)
The automation pipeline is fully containerized. You can pull and run the image directly from the GitHub Container Registry. You must pass your API keys as environment variables (`-e`) for the script to authenticate.

```bash
# Pull the latest image
docker pull ghcr.io/munnurumahesh03-coder/omnimodal-whatsapp-agent:latest

# Run the container (Injecting your secret keys)
docker run -e GROQ_API_KEY="your_groq_key" -e GEMINI_API_KEY="your_gemini_key" -e MONGO_URI="your_mongodb_uri" ghcr.io/munnurumahesh03-coder/omnimodal-whatsapp-agent:latest
```

## 💻 Manual Local Execution
If you wish to run the Python scripts directly on your machine:

```bash
# 1. Clone the repository
git clone https://github.com/munnurumahesh03-coder/OmniModal-WhatsApp-Agent.git
cd OmniModal-WhatsApp-Agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set Environment Variables
# Create a .env file in the root directory and add:
# GROQ_API_KEY="your_groq_key"
# GEMINI_API_KEY="your_gemini_key"
# MONGO_URI="your_mongodb_uri"

# 4. Run the AI Agent (Backend )
python main.py

# 5. Run the Dashboard (Frontend)
streamlit run dashboard.py
```
