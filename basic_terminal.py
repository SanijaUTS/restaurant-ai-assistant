import os
from dotenv import load_dotenv
from openai import OpenAI

# 1) Load environment variables from .env
load_dotenv()

# 2) Read the API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in .env")

# 3) Create OpenAI client
client = OpenAI(api_key=api_key)

print("Basic AI Chat (type 'exit' to quit)\n")

# 4) Chat loop
while True:
    user_text = input("You: ").strip()
    if user_text.lower() == "exit":
        break

    # 5) Send 2 messages: system + user
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_text}
        ]
    )

    # 6) Extract reply text
    reply = response.choices[0].message.content
    print("AI:", reply, "\n")