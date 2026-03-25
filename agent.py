from groq import Groq
from dotenv import load_dotenv
import json
import os
import requests

load_dotenv()
client = Groq()

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

        # Check if key exists at all
        if not api_key:
            return "Weather API key not configured."

        city = args["city"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

        try:
            data = requests.get(url, timeout=5).json()
        except Exception as e:
            return f"Network error: {e}"

        cod = data.get("cod")

        # Key not activated yet
        if cod == 401:
            return "Weather API key is not active yet. It can take up to 2 hours after signing up. Try again later."

        if cod != 200:
            return f"Could not find weather for '{city}'. Try a different city name."

        temp     = data["main"]["temp"]
        feels    = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc     = data["weather"][0]["description"]
        return f"{city}: {temp}°C (feels like {feels}°C), {desc}, humidity {humidity}%"

    return f"Unknown tool: {name}"


def run_agent(user_message):
    messages = [{"role": "user", "content": user_message}]

    for _ in range(10):  # max 10 iterations, prevents infinite loops
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages
        )

        choice = response.choices[0]

        if choice.finish_reason == "stop":
            print(f"Agent: {choice.message.content}\n")
            return

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"  [tool] {name}({args})")

                result = execute_tool(name, args)
                print(f"  [result] {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

    print("Agent: Sorry, I could not complete that request.\n")

# --- Live CLI ---
if __name__ == "__main__":
    print("Agent ready. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input:
            run_agent(user_input)