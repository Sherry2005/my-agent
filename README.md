# ⚡ AI Agent

A lightweight agentic AI chatbot built with **Streamlit**, **Groq**, and **LLaMA 3.3 70B**. The agent can reason, call tools, and loop until it has a final answer — demonstrating a real function-calling agentic loop in under 200 lines of Python.

🔗 **Live demo → [my-agent.streamlit.app](https://my-agent.streamlit.app)**

---

## ✨ Features

- **Agentic loop** — the agent calls tools, observes results, and continues reasoning until it reaches a final answer (up to 10 iterations)
- **Live weather** — fetches real-time weather data via the OpenWeatherMap API
- **Math calculator** — evaluates arithmetic expressions precisely using Python's `eval`
- **Full chat history** — conversation is persisted in session state with tool call traces visible inline
- **Tool transparency** — every tool call and its result is shown in the chat, so you can see exactly how the agent thinks
- **Dark terminal UI** — monospace + minimal aesthetic with a neon green accent

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| UI Framework | [Streamlit](https://streamlit.io) |
| LLM | LLaMA 3.3 70B via [Groq](https://groq.com) |
| Weather Data | [OpenWeatherMap API](https://openweathermap.org/api) |
| Function Calling | Groq native tool use |
| Hosting | Streamlit Cloud |

---

## 🧰 Available Tools

| Tool | Description |
|---|---|
| `calculate` | Evaluates any math expression — e.g. `1234 * 5678` |
| `get_weather` | Fetches current temperature, conditions, and humidity for any city |

---

## ⚙️ How the Agentic Loop Works

```
User message
     │
     ▼
LLaMA 3.3 reasons → decides to call a tool
     │
     ▼
Tool executes (weather API / calculator)
     │
     ▼
Result fed back into conversation
     │
     ▼
LLaMA 3.3 reasons again → stops when it has a final answer
```

The loop runs for up to **10 iterations**, allowing multi-step reasoning and chained tool use. Each tool call and result is appended to the message history so the model has full context.

---

## 💬 Example Prompts

```
What's the weather in Cairo right now?
What is 17 * 384 + 9201?
What's the weather in Tokyo and what is 100 * 1.08?
```

---

## 🚀 Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/Sherry2005/my-agent.git
cd my-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your API keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

Or enter them directly in the app's sidebar at runtime.

**Get your keys:**
- Groq API key → [console.groq.com](https://console.groq.com) (free)
- OpenWeather API key → [openweathermap.org](https://openweathermap.org/api) (free tier available)

> ⚠️ New OpenWeatherMap API keys can take up to 2 hours to activate after registration.

### 4. Run

```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
my-agent/
├── app.py                  # Main Streamlit application + agentic loop
├── .env                    # API keys (not committed to git)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 📦 Requirements

```
streamlit
groq
python-dotenv
requests
```

---

## 🔒 Security Notes

- Never commit your `.env` file — add it to `.gitignore`
- The `calculate` tool uses Python's `eval()` and is intended for demo purposes; do not expose it in a production environment without input sanitization

---

## 🙋 Author

Built by **Sherry Mohareb** — AI Engineer  
[GitHub](https://github.com/Sherry2005) · [LinkedIn](https://linkedin.com/in/sherry-mohareb) · [Upwork](https://upwork.com)
