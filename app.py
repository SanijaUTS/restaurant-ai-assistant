import streamlit as st
import os
import csv
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ---------------- Setup ----------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not found. Check your .env file.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Restaurant AI Assistant", page_icon="🍽️")

# ---------------- Sidebar: Business Settings ----------------
st.sidebar.header("⚙️ Business Settings")

biz_name = st.sidebar.text_input("Business name", "Sunset Bites")
hours = st.sidebar.text_area(
    "Opening hours",
    "Mon–Fri: 8am–10pm\nSat–Sun: 9am–11pm",
    height=80,
)
menu = st.sidebar.text_area(
    "Menu highlights (one per line)",
    "- Burgers\n- Pasta\n- Vegan options available",
    height=120,
)

customer_name = st.sidebar.text_input("Customer name (optional)", "")
mode = st.sidebar.selectbox("Mode", ["General", "Bookings", "Orders"])
short_replies = st.sidebar.checkbox("Short replies (cheaper)", value=True)

restaurant_info = f"""
You are an AI assistant for a restaurant called "{biz_name}".

Opening hours:
{hours}

Menu highlights:
{menu}

Rules:
- Be friendly and concise.
- If someone asks to book, collect: date, time, number of people, and name.
- When details are complete, confirm the booking clearly in one message.
- If someone orders, confirm the items and ask dine-in or takeaway.
- When details are complete, confirm the order clearly in one message.
{"- Keep replies short unless user asks for details." if short_replies else ""}
"""

# ---------------- CSV helpers ----------------
def append_csv(filename: str, headers: list[str], row: list):
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(headers)
        w.writerow(row)

def looks_like_booking_confirmation(text: str) -> bool:
    t = text.lower()
    return ("booking" in t or "reservation" in t) and ("confirm" in t or "confirmed" in t)

def looks_like_order_confirmation(text: str) -> bool:
    t = text.lower()
    return "order" in t and ("confirm" in t or "confirmed" in t or "got it" in t)

def extract_people(text: str) -> str:
    m = re.search(r"(\d+)\s*(people|persons|pax)", text.lower())
    return m.group(1) if m else ""

def extract_time(text: str) -> str:
    m = re.search(r"\b(\d{1,2}(:\d{2})?\s*(am|pm))\b", text.lower())
    if m:
        return m.group(1).replace(" ", "")
    m2 = re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", text)
    return m2.group(0) if m2 else ""

def extract_date(text: str) -> str:
    months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    t = text.lower()
    if any(m in t for m in months):
        return text.strip()
    m = re.search(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b", t)
    return m.group(0) if m else ""

def detect_dine_mode(text: str) -> str:
    t = text.lower()
    if "takeaway" in t or "take away" in t:
        return "takeaway"
    if "dine-in" in t or "dine in" in t or "dine" in t:
        return "dine-in"
    return "unknown"

# ---------------- App State ----------------
st.title("🍽️ Restaurant AI Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": restaurant_info}]

# If business settings change, update the system message (without wiping history)
# (This makes demos easy: update menu/hours and keep chat still functional.)
if st.session_state.messages and st.session_state.messages[0]["role"] == "system":
    st.session_state.messages[0]["content"] = restaurant_info

if "last_saved_signature" not in st.session_state:
    st.session_state.last_saved_signature = None

colA, colB = st.columns([1, 1])
with colA:
    if st.button("Reset chat"):
        st.session_state.messages = [{"role": "system", "content": restaurant_info}]
        st.session_state.last_saved_signature = None
        st.rerun()

with colB:
    st.caption("Tip: Use the sidebar to change business name/hours/menu for quick demos.")

# ---------------- Display chat ----------------
for msg in st.session_state.messages[1:]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.write(msg["content"])

# ---------------- Chat input (auto clears!) ----------------
user_text = st.chat_input("Type a message and press Enter…")
if user_text:
    # add a small steering tag based on mode
    tagged = user_text
    if mode == "Bookings":
        tagged = f"[BOOKING] {user_text}"
    elif mode == "Orders":
        tagged = f"[ORDER] {user_text}"

    st.session_state.messages.append({"role": "user", "content": tagged})
    with st.chat_message("user"):
        st.write(user_text)

    # Call the model
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=st.session_state.messages,
    )
    reply = response.choices[0].message.content.strip()

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)

    # ---------------- Save logic (v1) ----------------
    now = datetime.now().isoformat(timespec="seconds")
    combined = user_text + "\n" + reply

    # booking save
    if looks_like_booking_confirmation(reply):
        name_ = customer_name.strip()
        date_ = extract_date(combined)
        time_ = extract_time(combined)
        people_ = extract_people(combined)
        notes = user_text.strip()

        signature = ("booking", now, name_, date_, time_, people_, notes)
        if st.session_state.last_saved_signature != signature:
            append_csv(
                "bookings.csv",
                ["timestamp", "name", "date", "time", "people", "notes"],
                [now, name_, date_, time_, people_, notes],
            )
            st.session_state.last_saved_signature = signature
            st.success("✅ Saved to bookings.csv")

    # order save
    if looks_like_order_confirmation(reply):
        name_ = customer_name.strip()
        dine = detect_dine_mode(combined)
        notes = user_text.strip()

        signature = ("order", now, name_, dine, notes)
        if st.session_state.last_saved_signature != signature:
            append_csv(
                "orders.csv",
                ["timestamp", "name", "items", "dine_in_or_takeaway", "notes"],
                [now, name_, "see chat", dine, notes],
            )
            st.session_state.last_saved_signature = signature
            st.success("✅ Saved to orders.csv")

# ---------------- Export buttons ----------------
st.divider()
st.subheader("📥 Export")

col1, col2 = st.columns(2)

with col1:
    if os.path.exists("bookings.csv"):
        with open("bookings.csv", "rb") as f:
            st.download_button("Download bookings.csv", f, file_name="bookings.csv")
    else:
        st.caption("No bookings.csv yet (it appears after a confirmed booking).")

with col2:
    if os.path.exists("orders.csv"):
        with open("orders.csv", "rb") as f:
            st.download_button("Download orders.csv", f, file_name="orders.csv")
    else:
        st.caption("No orders.csv yet (it appears after a confirmed order).")