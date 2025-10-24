🤖 StockBot AI — Real-Time Financial Chatbot

StockBot AI is an interactive, real-time financial assistant built with Streamlit and powered by the Google Gemini API. It allows users to look up current stock information using Yahoo Finance data, get deep market analysis, and maintain a persistent chat history powered by Firestore.

✨ Features

Real-Time Context: Fetches current stock data (price, 52W range, sector) using yfinance and injects it as context directly into the LLM prompt.

Intelligent Analysis: Uses the Google Gemini API with Google Search Grounding to provide up-to-date and reliable market analysis.

Persistent Chat History: Utilizes Google Firestore to save and load conversation history, ensuring seamless continuation across sessions and devices.

Intuitive UI: Features a dark-themed, collapsible sidebar for efficient navigation and a clean chat interface.

Top Picks: Displays a real-time list of top-performing stocks and market commentary in the sidebar.

⚙️ Setup and Installation

1. Clone the Repository

git clone [https://github.com/YOUR_USERNAME/AI_Stockbot.git](https://github.com/YOUR_USERNAME/AI_Stockbot.git)
cd AI_Stockbot


2. Create a Virtual Environment (Recommended)

python -m venv venv
# Activate the environment (Windows)
.\venv\Scripts\activate
# Activate the environment (macOS/Linux)
source venv/bin/activate


3. Install Dependencies

Install all required Python packages using the requirements.txt file:

pip install -r requirements.txt


4. Configure API Keys

Create a file named .env in your project root directory and add your Google Gemini API key:

# .env file content
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"


5. Run the Application Locally

streamlit run app.py


Your application should open automatically in your browser (usually http://localhost:8501).

🚀 Deployment to Streamlit Community Cloud

Streamlit Community Cloud is the fastest and easiest way to deploy this application.

Prerequisites

Your code must be pushed to a public GitHub repository.

You must have your API keys and Firebase configuration ready.

Step-by-Step Deployment

Log in to Streamlit Community Cloud.

Create a New App: Click the New App button.

Link Repository: Select your AI_Stockbot repository and set the Main file path to app.py.

Configure Secrets (CRITICAL): Click Advanced settings and add the following secrets in TOML format:

# 1. Gemini API Key
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# 2. Firestore Configuration (for persistence)
# NOTE: You must obtain the service account JSON from your Firebase project, 
# and format it as a single JSON string for the environment variable.
__firebase_config = '{"type": "service_account", "project_id": "...", "private_key_id": "...", "private_key": "-----BEGIN PRIVATE KEY---\\n...", "client_email": "...", "client_id": "...", "auth_uri": "...", "token_uri": "...", "auth_provider_x509_cert_url": "...", "client_x509_cert_url": "..."}'

# 3. Streamlit Cloud requires dummy values for the Canvas environment variables
__app_id = "ai-stockbot-deployment"
__initial_auth_token = "dummy_token_12345"


Deploy: Click Deploy! and share your live StockBot AI application!
