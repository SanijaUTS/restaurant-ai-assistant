import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("API key not found. Check your .env file")

client = OpenAI(api_key=api_key)

# Restaurant info
restaurant_info = """
You are an AI assistant for a restaurant called "Sunset Bites" in Sydney.

Opening hours:
Mon–Fri: 8am–10pm
Sat–Sun: 9am–11pm

Menu highlights:
- Burgers
- Pasta
- Vegan options available

Booking policy:
If someone asks to book, collect date, time, number of people, and name.
"""

# Memory (conversation history)
conversation = [{"role": "system", "content": restaurant_info}]

def ask_ai(user_message):
    conversation.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=conversation
    )

    reply = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": reply})

    return reply


print("AI Agent Running (type 'exit' to stop)\n")

while True:
    user_input = input("Customer: ").strip()

    if user_input.lower() == "exit":
        break

    if not user_input:
        continue

    reply = ask_ai(user_input)
    print("AI:", reply, "\n")