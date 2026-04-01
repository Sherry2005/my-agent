from groq import Groq
from dotenv import load_dotenv
import json
import os
import requests
import streamlit as st

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Agent",
    page_icon="⚡",
    layout="centered"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark background */
.stApp {
    background-color: #0d0d0d;
    color: #e8e8e8;
}

/* Hide default streamlit header */
header[data-testid="stHeader"] { background: transparent; }

/* Title area */
.agent-title {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #00ff99;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}
.agent-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    color: #555;
    margin-top: 2px;
    margin-bottom: 1.5rem;
}

/* Chat messages */
.msg-user {
    background: #1a1a1a;
    border-left: 3px solid #00ff99;
    padding: 12px 16px;
    border-radius: 4px;
    margin: 10px 0;
    font-size: 0.95rem;
    color: #e8e8e8;
}
.msg-agent {
    background: #111;
    border-left: 3px solid #444;
    padding: 12px 16px;
    border-radius: 4px;
    margin: 10px 0;
    font-size: 0.95rem;
    color: #ccc;
}
.msg-tool {
    background: #0a1a0a;
    border-left: 3px solid #1a7a3a;
    padding: 8px 14px;
    border-radius: 4px;
    margin: 4px 0 4px 16px;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #4caf7d;
}
.msg-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
    color: #555;
}
.msg-label.user { color: #00ff99; }
.msg-label.agent { color: #888; }
.msg-label.tool { color: #2e7d52; }

/* Input box */
.stTextInput > div > div > input {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 4px !important;
    color: #e8e8e8 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #00ff99 !important;
    box-shadow: 0 0 0 1px #00ff9933 !important;
}

/* Button */
.stButton > button {
    background: #00ff99 !important;
    color: #0d0d0d !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 10px 24px !important;
    letter-spacing: 0.5px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Divider */
hr { border-color: #1f1f1f !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid #1a1a1a !important;
}
</style>
""", unsafe_allow_html=True)

# ── Tools definition ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression and return the exact result. Use this for any arithmetic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A math expression like '1234 * 5678'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city. Use when the user asks about weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. 'Cairo'"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

def execute_tool(name, args):
    if name == "calculate":
        try:
            return str(eval(args["expression"]))
        except Exception as e:
            return f"Error evaluating expression: {e}"

    if name == "get_weather":
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return "Weather API key not configured."
        city = args["city"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        try:
            data = requests.get(url, timeout=5).json()
        except Exception as e:
            return f"Network error: {e}"
        cod = data.get("cod")
        if cod == 401:
            return "Weather API key is not active yet. Try again later."
        if cod != 200:
            return f"Could not find weather for '{city}'."
        temp     = data["main"]["temp"]
        feels    = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc     = data["weather"][0]["description"]
        return f"{city}: {temp}°C (feels like {feels}°C), {desc}, humidity {humidity}%"

    return f"Unknown tool: {name}"


def run_agent(user_message, groq_api_key):
    """Run the agent and return (final_answer, tool_logs)."""
    client = Groq(api_key=groq_api_key)
    messages = [{"role": "user", "content": user_message}]
    tool_logs = []

    for _ in range(10):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages
        )
        choice = response.choices[0]

        if choice.finish_reason == "stop":
            return choice.message.content, tool_logs

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = execute_tool(name, args)
                tool_logs.append((name, args, result))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

    return "Sorry, I could not complete that request.", tool_logs


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Config")
    groq_key = st.text_input("Groq API Key", type="password",
                              value=os.getenv("GROQ_API_KEY", ""))
    openweather_key = st.text_input("OpenWeather API Key", type="password",
                                     value=os.getenv("OPENWEATHER_API_KEY", ""))
    if openweather_key:
        os.environ["OPENWEATHER_API_KEY"] = openweather_key

    st.markdown("---")
    st.markdown("**Tools available:**")
    st.markdown("🧮 `calculate` — math expressions")
    st.markdown("🌤️ `get_weather` — live weather by city")
    st.markdown("---")
    if st.button("Clear chat"):
        st.session_state.history = []
        st.rerun()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="agent-title">⚡ AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="agent-sub">Powered by Groq · LLaMA 3.3 70B · Tool Use</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Session state ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ── Render chat history ────────────────────────────────────────────────────────
for entry in st.session_state.history:
    st.markdown(f'<div class="msg-label user">You</div><div class="msg-user">{entry["user"]}</div>', unsafe_allow_html=True)
    for (tool_name, tool_args, tool_result) in entry.get("tools", []):
        st.markdown(
            f'<div class="msg-tool">🔧 {tool_name}({tool_args})<br>↳ {tool_result}</div>',
            unsafe_allow_html=True
        )
    st.markdown(f'<div class="msg-label agent">Agent</div><div class="msg-agent">{entry["agent"]}</div>', unsafe_allow_html=True)

# ── Input ──────────────────────────────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input("", placeholder="Ask me anything — weather, math, or general questions...", label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Send")

if submitted and user_input.strip():
    if not groq_key:
        st.error("Please enter your Groq API key in the sidebar.")
    else:
        with st.spinner("Thinking..."):
            answer, tool_logs = run_agent(user_input.strip(), groq_key)
        st.session_state.history.append({
            "user": user_input.strip(),
            "tools": tool_logs,
            "agent": answer
        })
        st.rerun()
