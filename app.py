import streamlit as st
import yfinance as yf
from dotenv import load_dotenv
import os
import json
import time
import uuid 
import requests

# --- Firebase Imports ---
# We use the firebase-admin SDK for Python/Streamlit backend
import firebase_admin
from firebase_admin import credentials, firestore

# --- Configuration ---
# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
MODEL = "gemini-2.5-flash-preview-09-2025"

# Define the system prompt
SYSTEM_PROMPT = """
You are StockBot AI, a helpful, concise, and expert financial assistant.
Your goal is to provide analysis and answer user questions about the stock market and specific companies.
You have access to a Google Search tool for current, real-time grounding. Use it for current price, news, and recent performance whenever needed.
If specific stock data is provided in the CONTEXT section of the user's prompt (from yfinance), you MUST also use that data for your analysis and comparisons.
Keep your answers professional, informative, and focused on the user's financial inquiry.
"""

# --- Firebase and Firestore Setup ---
# Use mandatory global variables provided by the environment
app_id = os.environ.get("__app_id", "default-app-id")
firebase_config_json = os.environ.get("__firebase_config")
initial_auth_token = os.environ.get("__initial_auth_token")

# Initialize Firebase App only once per session
if "db" not in st.session_state:
    try:
        # Attempt to initialize Firebase with environment credentials
        if not firebase_admin._apps:
            if firebase_config_json:
                # Assuming the config is for a service account in this Python environment
                config = json.loads(firebase_config_json)
                cred = credentials.Certificate(config)
                firebase_admin.initialize_app(cred, name=app_id)
            else:
                # Fallback to default initialization if config is missing
                firebase_admin.initialize_app(name=app_id)
        
        st.session_state.db = firestore.client(app=firebase_admin.get_app(name=app_id))
        st.session_state.is_auth_ready = True
        
    except Exception as e:
        # st.warning(f"Could not initialize Firebase for persistence. Using session state only. Error: {e}")
        st.session_state.is_auth_ready = False
        st.session_state.db = None

# Determine User ID and History Path
if st.session_state.get("is_auth_ready"):
    # Mocking user ID based on token presence or anonymous UUID
    if initial_auth_token:
        # Use a portion of the token as a pseudo-user ID for pathing
        user_id = initial_auth_token[:16] 
    elif "user_id" in st.session_state:
        # Use existing anonymous ID if present
        user_id = st.session_state.user_id
    else:
        # Generate new anonymous ID and store it
        user_id = str(uuid.uuid4())
        st.session_state.user_id = user_id
        
    # Mandatory private data path structure
    HISTORY_DOC_PATH = f"artifacts/{app_id}/users/{user_id}/stockbot_history/chat_doc"
    st.session_state.user_id_display = user_id # Store for display
else:
    HISTORY_DOC_PATH = None
    st.session_state.user_id_display = "Anonymous (No Persistence)"


# --- Streamlit UI Setup ---
st.set_page_config(page_title="📈 StockBot AI", page_icon="🤖", layout="wide")

# Initialize analysis state
if "top_stocks_analysis" not in st.session_state:
    st.session_state["top_stocks_analysis"] = "Click 'Refresh Top Picks' to get today's analysis."

# Apply custom styling for a clean, contrasting dark-on-light look
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5em;
        font-weight: 700;
        /* Header color white for dark background */
        color: #FFFFFF; 
        text-align: center;
        padding-bottom: 20px;
    }
    .stSpinner {
        color: #10b981; /* Tailwind Emerald */
    }
    /* Styling for the main chat input area */
    .stChatInput > div > div > div > textarea {
        border-radius: 0.75rem; 
        border-color: #374151; 
        background-color: #1f2937; 
        color: #FFFFFF;
    }
    /* FIX: Sidebar styling (Dark Grey theme) */
    [data-testid="stSidebar"] {
        background-color: #1F2937; /* Dark Grey background */
        color: #FFFFFF; /* White text for contrast */
        border-right: 1px solid #374151; /* Dark border */
        padding: 1.5rem;
    }
    /* Sidebar headers (White) */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #FFFFFF; 
        font-weight: 600;
    }
    /* Sidebar text/subheader color (Slightly lighter grey) */
    [data-testid="stSidebar"] p {
        color: #D1D5DB; /* Light gray text */
    }

    .sidebar-button button {
        background-color: #10B981 !important; /* Emerald 500 */
        color: white !important;
        font-weight: 600;
        border-radius: 0.5rem;
    }
    .sidebar-button button:hover {
        background-color: #059669 !important; /* Emerald 600 */
    }
    /* Styling for the previous queries buttons (Light grey on dark sidebar) */
    .stButton>button {
        background-color: #374151; /* Darker grey for buttons */
        color: #F3F4F6; /* Very light text */
        border: none;
        padding: 4px 8px;
        font-size: 0.9em;
        margin-bottom: 4px;
        text-align: left;
        
        /* THE NEW FIX: Ensures word wrap is prioritized */
        word-break: normal; 
        white-space: normal;
        overflow-wrap: break-word; /* Additional assurance for long words */
        height: auto; /* Allow height to adjust for word wrap */
    }
    .stButton>button:hover {
        background-color: #4B5563; /* Medium grey on hover */
        color: #F3F4F6;
    }
    /* Style for the Top Stocks analysis box - Ensures text is not wrapped in a clickable element */
    .analysis-box {
        background-color: #374151; /* Darker grey box */
        border: 1px solid #4B5563;
        padding: 10px;
        border-radius: 0.5rem;
        font-size: 0.9em;
        color: #F3F4F6; /* Light text inside box */
        /* Ensure non-interactivity */
        pointer-events: none;
        user-select: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="main-header">🤖 StockBot AI — Chat About Stocks in Real Time (Powered by Gemini)</div>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align: center; color: #9ca3af; font-size: 0.9em;">User ID: <code>{st.session_state.user_id_display}</code></p>', unsafe_allow_html=True)


# --- History Loading Function ---

def load_chat_history():
    """Loads chat history from Firestore if auth is ready and history hasn't been loaded."""
    if st.session_state.get("is_auth_ready") and "history_loaded" not in st.session_state:
        try:
            doc_ref = st.session_state.db.document(HISTORY_DOC_PATH)
            doc = doc_ref.get()
            
            if doc.exists and doc.get("messages"):
                loaded_messages = doc.get("messages")
                # Ensure the system prompt is present and at the start
                if not loaded_messages or loaded_messages[0].get("role") != "system":
                    loaded_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                st.session_state["messages"] = loaded_messages
            else:
                # Initialize with system prompt if no doc
                st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
                
            st.session_state.history_loaded = True
            st.session_state.history_doc_ref = doc_ref # Store reference for saving

        except Exception as e:
            # st.warning(f"Error loading chat history from Firestore: {e}. Starting new session.")
            st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.session_state.history_loaded = True

# --- Stock Data Fetching Function (Remains the same) ---

def fetch_stock_data(symbol):
    """Fetches key stock information using yfinance."""
    try:
        stock = yf.Ticker(symbol.upper())
        info = stock.info
        
        if info.get('regularMarketPrice') is None and info.get('currentPrice') is None:
             raise ValueError("Symbol not found or data unavailable.")

        data = {
            "symbol": symbol.upper(),
            "shortName": info.get("shortName", symbol.upper()),
            "sector": info.get("sector", "N/A"),
            "currentPrice": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", "N/A"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", "N/A"),
            # Ensure the summary is safe to embed in the prompt
            "longBusinessSummary": info.get("longBusinessSummary", "No business summary available."),
            "marketCap": info.get("marketCap", "N/A")
        }
        return data
    except Exception as e:
        st.sidebar.error(f"Failed to fetch data for {symbol.upper()}: {e}")
        return None

# --- Gemini API Call Function (Remains the same) ---

def get_gemini_response(api_messages):
    if not GEMINI_API_KEY:
        return "⚠️ **Configuration Error:** The `GEMINI_API_KEY` is not set in your `.env` file."

    # Convert the messages into the format expected by the Gemini API (role: user/model)
    gemini_contents = []
    system_instruction_part = None
    
    for msg in api_messages:
        role = "user" if msg["role"] == "user" else "model"
        
        # Handle the system prompt separately
        if msg["role"] == "system":
            system_instruction_part = msg["content"]
            continue

        gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Build the payload (Corrected for systemInstruction structure and adding Google Search tool)
    payload = {
        "contents": gemini_contents,
        "systemInstruction": {
            "parts": [
                { "text": system_instruction_part }
            ]
        },
        "tools": [
            { "google_search": {} }
        ]
    }
    
    # We will implement a basic retry mechanism (exponential backoff)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json=payload
            )
            
            response.raise_for_status()
            
            # Successful response
            result = response.json()
            
            # Extract the text
            if result and result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "⚠️ **API Response Error:** The Gemini API returned an empty or unexpected response structure."

        except requests.exceptions.HTTPError as errh:
            status_code = errh.response.status_code
            if status_code == 429 and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                # st.warning(f"Rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return f"⚠️ **HTTP Error (Gemini):** Status {status_code}. Error: {errh.response.text}"
        except requests.exceptions.RequestException as err:
            return f"⚠️ **Connection Error (Gemini):** {err}"
            
    return "⚠️ **Error:** Failed to get a response after multiple retries due to rate limiting."

# --- New Function: Fetch Top Stock Picks ---

def fetch_top_stocks_analysis():
    """Fetches general top stock analysis using Gemini with Google Search grounding."""
    # This prompt asks for a concise, list-based output for easy sidebar display
    prompt = "What are 5 notable top-performing stocks today? Provide the ticker, the current price or change, and a very short, one-sentence reason based on market news. Format the output as a clean markdown list."
    
    # We only send the system prompt and the specific request.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Use the core API function
    return get_gemini_response(messages)

# --- State Initialization & History Load ---

if "history_loaded" not in st.session_state and st.session_state.get("is_auth_ready"):
    load_chat_history()
    st.rerun() # Rerun once after loading history

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]

if "stock_data" not in st.session_state:
    st.session_state["stock_data"] = None

# Initialize the text value that can be set by sidebar clicks
if "chat_input_text" not in st.session_state:
    st.session_state["chat_input_text"] = ""


# --- Callback for Previous Query Click ---
def set_chat_input(query):
    # Set the text to be placed in the input box
    st.session_state["chat_input_text"] = query
    # Immediately process the query by appending it to the messages and triggering a rerun
    st.session_state["messages"].append({"role": "user", "content": query})
    st.rerun()

# --- Sidebar UI (Reordered & Collapsible) ---

# 1. Previous Queries Section (Collapsible)
with st.sidebar.expander("📝 Previous Queries", expanded=True):
    # Filter and display user queries in the sidebar
    user_queries = [msg["content"] for msg in st.session_state["messages"] if msg["role"] == "user"]
    user_queries.reverse() # Show most recent first

    # Use a container to make the list scrollable if it gets long
    with st.container(height=250):
        if user_queries:
            for i, query in enumerate(user_queries):
                # Using st.button inside st.container with a custom class for styling
                st.button(
                    query,
                    key=f"query_btn_{i}",
                    on_click=set_chat_input,
                    args=(query,),
                    use_container_width=True
                )
        else:
            st.info("Start a conversation to see your history here!")

st.sidebar.markdown("---")

# 2. Top Stock Picks Today Section (Collapsible)
with st.sidebar.expander("⭐ Top Stock Picks Today", expanded=False):
    # Button to refresh the analysis
    if st.button("Refresh Top Picks", key="refresh_picks_button", use_container_width=True):
        with st.spinner("Fetching today's market analysis..."):
            st.session_state["top_stocks_analysis"] = fetch_top_stocks_analysis()
            st.rerun()
    
    # FIX: Use st.write/st.markdown and wrap in the non-interactive analysis-box div 
    st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
    st.markdown(st.session_state["top_stocks_analysis"])
    st.markdown('</div>', unsafe_allow_html=True)


st.sidebar.markdown("---")

# 3. Stock Lookup Section (Collapsible)
with st.sidebar.expander("🔍 Stock Lookup", expanded=True):
    symbol_input = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA, INFY):")

    if st.button("Fetch and Set Context", key="fetch_button"):
        if symbol_input:
            with st.spinner(f"Fetching data for {symbol_input.upper()}..."):
                data = fetch_stock_data(symbol_input)
                st.session_state["stock_data"] = data
                if data:
                    st.success(f"Context set for {data['symbol']}!")
                    st.subheader(data['shortName'])
                    st.write(f"💰 **Current Price:** ${data['currentPrice']}")
                    st.write(f"🏢 **Sector:** {data['sector']}")
                    st.write(f"📅 **52W Range:** ${data['fiftyTwoWeekLow']} - ${data['fiftyTwoWeekHigh']}")
                    
                    # Clear chat history to reset context for the new stock
                    st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    st.rerun() 
        else:
            st.warning("Please enter a stock symbol.")

    # Display currently active context
    if st.session_state["stock_data"]:
        data = st.session_state["stock_data"]
        st.markdown("---")
        st.subheader("Active Context")
        st.markdown(f"**Symbol:** `{data['symbol']}`")
        st.markdown(f"**Company:** {data['shortName']}")
        st.markdown(f"**Price:** **${data['currentPrice']}**")
        st.markdown(f"**Sector:** {data['sector']}")

st.sidebar.markdown("---")

# --- Chat Logic ---

# Display previous messages (skip the initial system prompt)
for msg in st.session_state["messages"][1:]:
    if msg["role"] == "user":
        st.chat_message("user").markdown(f"🧑‍💻 **You:** {msg['content']}")
    else:
        st.chat_message("assistant").markdown(f"🤖 **StockBot:** {msg['content']}")

# The input value from the sidebar click is handled by appending the message in set_chat_input and calling rerun.
# Now, st.chat_input is used normally without the 'value' argument.
user_input = st.chat_input(
    "Ask StockBot about the active stock or anything else...", 
    key="chat_submission_key"
)

# Handle the case where a new value was submitted via the chat box
if user_input:
    # 1. Append user input to session history (only if it's new input, not from sidebar button)
    # The submission from the sidebar is already handled in the set_chat_input callback.
    # We only append here if it's a fresh text box submission.
    
    # We compare the input to the last message to avoid duplicating if the user hits enter quickly after a button click
    if not st.session_state["messages"][-1]["content"] == user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})

    # 2. Build the message list for the API call (including context if available)
    api_messages = list(st.session_state["messages"]) # Copy the list

    # Inject stock context if available right before the user's latest query
    if st.session_state["stock_data"]:
        data = st.session_state["stock_data"]
        context_message = f"""
        CONTEXT: The user's query relates to the currently active stock: {data['symbol']} ({data['shortName']}).
        Use the following real-time data for your analysis:
        - Current Price: ${data['currentPrice']}
        - 52-Week Range: ${data['fiftyTwoWeekLow']} - ${data['fiftyTwoWeekHigh']}
        - Sector: {data['sector']}
        - Business Summary (Partial): {data['longBusinessSummary'][:500].replace('\n', ' ')}...
        """
        # Insert context as an extra user message right before the latest query
        # Find the index of the current user message (the last one)
        last_user_index = len(api_messages) - 1
        
        # Insert the context right before the last user message
        api_messages.insert(last_user_index, {"role": "user", "content": context_message})

    # Show loading spinner while waiting for response
    with st.spinner("StockBot is thinking... 💭"):
        # Use the new Gemini API function
        bot_reply = get_gemini_response(api_messages)

    # 3. Append bot reply to session history
    st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
    
    # 4. Save history to Firestore
    if st.session_state.get("history_doc_ref"):
        try:
            # We use set() with a map/dictionary to save the entire messages list
            st.session_state.history_doc_ref.set({
                "messages": st.session_state["messages"],
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            st.warning(f"Failed to save history to Firestore: {e}")

    # Rerun to clear the input field and display the new message
    st.rerun()
