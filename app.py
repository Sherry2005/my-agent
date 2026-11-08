import ast
import html
import json
import operator
import os
from datetime import date

import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ── Demo limits (only used when YOUR keys are stored on the server) ───────────
DEMO_MESSAGES_PER_SESSION = 6
DEMO_MESSAGES_PER_DAY = 150  # shared across all visitors

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Agent", page_icon="⚡", layout="centered")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background-color: #0d0d0d; color: #f0f0f0; }
header[data-testid="stHeader"] { background: transparent; }

/* Make all default Streamlit text readable on the dark background */
.stApp p, .stApp label, .stApp span, .stApp li, .stApp small,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] span, [data-testid="stSidebar"] li,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stMarkdownContainer"] {
    color: #e6e6e6;
}

.agent-title {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem; font-weight: 700; color: #00ff99;
    letter-spacing: -0.5px; margin-bottom: 0;
}
.agent-sub {
    font-size: 0.9rem; color: #a8adb5;
    margin-top: 2px; margin-bottom: 1.5rem;
}

.msg-user {
    background: #1a1a1a; border-left: 3px solid #00ff99;
    padding: 12px 16px; border-radius: 4px; margin: 10px 0;
    font-size: 0.95rem; color: #f0f0f0;
}
.msg-agent {
    background: #141414; border-left: 3px solid #6b7280;
    padding: 12px 16px; border-radius: 4px; margin: 10px 0;
    font-size: 0.95rem; color: #e0e0e0;
}
.msg-tool {
    background: #0a1a0a; border-left: 3px solid #1f9a4d;
    padding: 8px 14px; border-radius: 4px; margin: 4px 0 4px 16px;
    font-family: 'Space Mono', monospace; font-size: 0.78rem; color: #6fe0a1;
}
.msg-label {
    font-family: 'Space Mono', monospace; font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
    color: #9ca3af;
}
.msg-label.user { color: #00ff99; }
.msg-label.agent { color: #c4c8cf; }

/* Input box */
.stTextInput > div > div > input {
    background: #1a1a1a !important; border: 1px solid #3a3a3a !important;
    border-radius: 4px !important; color: #f0f0f0 !important;
    font-size: 0.95rem !important; padding: 10px 14px !important;
}
.stTextInput > div > div > input::placeholder { color: #9ca3af !important; opacity: 1 !important; }
.stTextInput > div > div > input:focus {
    border-color: #00ff99 !important; box-shadow: 0 0 0 1px #00ff9933 !important;
}

/* Buttons (normal and form-submit buttons) */
.stButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: #00ff99 !important; color: #0d0d0d !important;
    font-family: 'Space Mono', monospace !important; font-weight: 700 !important;
    font-size: 0.8rem !important; border: none !important; border-radius: 4px !important;
    padding: 10px 18px !important; letter-spacing: 0.5px !important;
}
.stButton > button p, [data-testid="stFormSubmitButton"] > button p { color: #0d0d0d !important; }
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { opacity: 0.85 !important; }

hr { border-color: #2a2a2a !important; }

[data-testid="stSidebar"] {
    background: #0a0a0a !important; border-right: 1px solid #222 !important;
}
code { color: #00ff99 !important; background: #1a1a1a !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_secret(name):
    """Server-side key: Streamlit secrets first, then environment / .env."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, "")


def esc(text):
    """Escape user/model text before putting it in HTML."""
    return html.escape(str(text)).replace("\n", "<br>")


@st.cache_resource
def daily_usage():
    return {"date": None, "count": 0}


def demo_available():
    usage = daily_usage()
    today = date.today().isoformat()
    if usage["date"] != today:
        usage["date"], usage["count"] = today, 0
    return usage["count"] < DEMO_MESSAGES_PER_DAY


# <<SAFE_EVAL
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(node):
    """Evaluate arithmetic only. No names, calls, or attributes."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 1000 or abs(left) > 1e12):
            raise ValueError("Exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError("Only basic arithmetic is allowed")
# SAFE_EVAL>>


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
                    "expression": {"type": "string", "description": "A math expression like '1234 * 5678'"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city. Use when the user asks about weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name, e.g. 'Cairo'"}
                },
                "required": ["city"],
            },
        },
    },
]


def execute_tool(name, args, weather_key):
    if name == "calculate":
        try:
            result = safe_eval(ast.parse(str(args.get("expression", "")), mode="eval"))
            return str(result)
        except ZeroDivisionError:
            return "Error: division by zero."
        except Exception as e:
            return f"Error evaluating expression: {e}"

    if name == "get_weather":
        if not weather_key:
            return "Weather API key not configured."
        city = str(args.get("city", "")).strip()
        if not city:
            return "No city provided."
        try:
            data = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": weather_key, "units": "metric"},
                timeout=6,
            ).json()
        except Exception as e:
            return f"Network error: {e}"
        cod = int(data.get("cod", 0))
        if cod == 401:
            return "Weather API key is not active yet. Try again later."
        if cod != 200:
            return f"Could not find weather for '{city}'."
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        return f"{city}: {temp}°C (feels like {feels}°C), {desc}, humidity {humidity}%"

    return f"Unknown tool: {name}"


def run_agent(user_message, groq_api_key, weather_key, history):
    """Run the agent and return (final_answer, tool_logs). Remembers recent turns."""
    client = Groq(api_key=groq_api_key)
    messages = [{
        "role": "system",
        "content": "You are a helpful assistant. Use the calculate tool for any arithmetic "
                   "and the get_weather tool for weather. Be concise.",
    }]
    for turn in history[-4:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["agent"]})
    messages.append({"role": "user", "content": user_message})
    tool_logs = []

    for _ in range(10):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        choice = response.choices[0]

        if choice.finish_reason == "stop":
            return choice.message.content, tool_logs

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(name, args, weather_key)
                tool_logs.append((name, args, result))
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    return "Sorry, I could not complete that request.", tool_logs


# ── Session state ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "demo_used" not in st.session_state:
    st.session_state.demo_used = 0

server_groq = get_secret("GROQ_API_KEY")
server_weather = get_secret("OPENWEATHER_API_KEY")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Config")
    if server_groq:
        left = max(0, DEMO_MESSAGES_PER_SESSION - st.session_state.demo_used)
        st.info(f"Free demo: {left} messages left. Add your own Groq key below for unlimited use.")
    user_groq = st.text_input("Groq API Key (optional)" if server_groq else "Groq API Key",
                              type="password")
    user_weather = st.text_input("OpenWeather API Key (optional)" if server_weather else "OpenWeather API Key",
                                 type="password")

    st.markdown("---")
    st.markdown("**Tools available:**")
    st.markdown("🧮 `calculate` — math expressions")
    st.markdown("🌤️ `get_weather` — live weather by city")
    st.markdown("---")
    if st.button("Clear chat"):
        st.session_state.history = []
        st.rerun()

groq_key = user_groq or server_groq
weather_key = user_weather or server_weather
using_demo = (not user_groq) and bool(server_groq)


def handle(text):
    text = text.strip()
    if not text:
        return
    if not groq_key:
        st.error("Please enter your Groq API key in the sidebar.")
        return
    if using_demo:
        if st.session_state.demo_used >= DEMO_MESSAGES_PER_SESSION:
            st.warning("Free demo limit reached. Add your own Groq key in the sidebar to continue.")
            return
        if not demo_available():
            st.warning("Today's free demo capacity is used up. Add your own Groq key in the sidebar.")
            return
    try:
        with st.spinner("Thinking..."):
            answer, tool_logs = run_agent(text, groq_key, weather_key, st.session_state.history)
    except Exception as e:
        st.error(f"Something went wrong calling the model: {e}")
        return
    if using_demo:
        st.session_state.demo_used += 1
        daily_usage()["count"] += 1
    st.session_state.history.append({"user": text, "tools": tool_logs, "agent": answer})
    st.rerun()


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="agent-title">⚡ AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="agent-sub">Powered by Groq · LLaMA 3.3 70B · Tool Use</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Run a clicked example, if any ──────────────────────────────────────────────
pending = st.session_state.pop("pending", None)
if pending:
    handle(pending)

# ── Render chat history ────────────────────────────────────────────────────────
for entry in st.session_state.history:
    st.markdown(f'<div class="msg-label user">You</div><div class="msg-user">{esc(entry["user"])}</div>',
                unsafe_allow_html=True)
    for (tool_name, tool_args, tool_result) in entry.get("tools", []):
        st.markdown(
            f'<div class="msg-tool">🔧 {esc(tool_name)}({esc(json.dumps(tool_args, ensure_ascii=False))})'
            f'<br>↳ {esc(tool_result)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="msg-label agent">Agent</div><div class="msg-agent">{esc(entry["agent"])}</div>',
                unsafe_allow_html=True)

# ── Example prompts (first screen only) ────────────────────────────────────────
if not st.session_state.history:
    st.markdown("**Try an example:**")
    examples = [
        "What's the weather in Cairo, and what is 18% of 2,450?",
        "Calculate 1234 * 5678",
        "Is it warmer in Luxor or Aswan right now?",
    ]
    for i, ex in enumerate(examples):
        if st.button(ex, key=f"ex{i}", use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

# ── Input ──────────────────────────────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input("Message", placeholder="Ask me anything: weather, math, or general questions...",
                                   label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Send")

if submitted:
    handle(user_input)