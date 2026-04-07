import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from PIL import Image
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os

# =================================================
# PAGE CONFIG (MUST BE FIRST)
# =================================================
st.set_page_config(
    page_title="Image Description with Voice Output",
    layout="centered"
)

# =================================================
# DATABASE & AUTH FUNCTIONS
# =================================================
def get_db():
    return sqlite3.connect("users.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # Create default admin
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), "admin")
        )

    conn.commit()
    conn.close()

def register_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), "user")
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = cur.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()
    return users

# =================================================
# INIT DATABASE
# =================================================
init_db()

# =================================================
# SESSION STATE
# =================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =================================================
# 🔐 AUTH SECTION
# =================================================
if not st.session_state.logged_in:

    st.title("🔐 Login / Registration")

    tab1, tab2 = st.tabs(["Login", "Register"])

    # ---------------- LOGIN ----------------
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user[0]
                st.session_state.role = user[1]
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    # ---------------- REGISTER ----------------
    with tab2:
        new_user = st.text_input("New Username", key="reg_user")
        new_pass = st.text_input("New Password", type="password", key="reg_pass")

        if st.button("Register"):
            if register_user(new_user, new_pass):
                st.success("Registration successful! Please login.")
            else:
                st.error("Username already exists")

# =================================================
# 🖼️ MAIN APP (AFTER LOGIN)
# =================================================
else:

    # ---------------- SIDEBAR ----------------
    st.sidebar.success(f"👤 {st.session_state.username}")
    st.sidebar.write(f"Role: **{st.session_state.role}**")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ---------------- ADMIN PANEL ----------------
    if st.session_state.role == "admin":
        st.sidebar.markdown("### 👑 Admin Panel")

        if st.sidebar.button("View Registered Users"):
            users = get_all_users()
            df = pd.DataFrame(users, columns=["ID", "Username", "Role"])
            st.subheader("📋 Registered Users")
            st.dataframe(df)

    # =================================================
    # 🖼️ IMAGE DESCRIPTION WITH VOICE OUTPUT
    # =================================================
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"]) # 🔴 Add your Gemini API key
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    st.title("🖼️ Image Description with Voice Output (Gemini Vision)")
    st.markdown(
        "Upload an image to get a **detailed AI-generated description** "
        "and **listen to it as voice output**."
    )

    uploaded_file = st.file_uploader(
        "Upload an Image (JPG / PNG)",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            image.thumbnail((600, 600))
            st.image(image, caption="Uploaded Image")

            if st.button("🧠 Generate Description with Voice"):
                with st.spinner("Analyzing image and generating description..."):

                    response = model.generate_content([
                        "Describe the scene in detail.",
                        image
                    ])

                    description = response.text.strip()

                    st.subheader("📄 Gemini's Description")
                    st.text_area(
                        "AI Output",
                        value=description,
                        height=300
                    )

                    # Generate voice
                    tts = gTTS(text=description, lang="en")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                        tts.save(audio_file.name)
                        audio_path = audio_file.name

                    st.subheader("🔊 Voice Output")
                    st.audio(audio_path, format="audio/mp3")

                    st.caption("Audio generated using Google Text-to-Speech")

        except Exception as e:
            st.error(f"❌ Failed to process image: {e}")
