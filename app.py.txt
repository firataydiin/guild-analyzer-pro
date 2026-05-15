# ---------------------------------------------------------------------------
# Guild Analyzer Pro v4 – Weekly Dashboard + Roles + GF Point + Cleaner
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
from datetime import datetime

DB_PATH = "data.db"

# ---------------------------------------------------------------------------
# DATABASE INIT
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS guild_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploaded_by TEXT,
        upload_date TEXT,
        igg_id TEXT,
        name TEXT,
        rank TEXT,
        might REAL,
        old_might REAL,
        might_diff REAL,
        kills REAL,
        old_kills REAL,
        kills_diff REAL,
        old_name TEXT
    );

    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        role TEXT DEFAULT "User"
    );

    CREATE TABLE IF NOT EXISTS guild_members (
        name TEXT PRIMARY KEY,
        rank TEXT,
        is_active INTEGER DEFAULT 1,
        joined_date TEXT
    );

    CREATE TABLE IF NOT EXISTS gf_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploaded_by TEXT,
        upload_date TEXT,
        name TEXT,
        gf_points REAL
    );
    """)
    conn.commit()
    conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username='RebelW0lf'")
    if not cur.fetchone():
        hashed = bcrypt.hashpw("19051905".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
            ("RebelW0lf", hashed, "Admin")
        )
        conn.commit()

    conn.close()

# ---------------------------------------------------------------------------
# SAFE EXCEL CLEAN
# ---------------------------------------------------------------------------
def clean_excel(df):
    df = df.copy().fillna("")

    # Normalize column names
    df.columns = [str(c).strip().title().replace("_", " ").replace("-", " ") for c in df.columns]

    rename_map = {
        "Igg Id": "igg_id",
        "Iggid": "igg_id",
        "Name": "name",
        "Rank": "rank",
        "Might": "might",
        "Old Might": "old_might",
        "Might Difference": "might_diff",
        "Kills": "kills",
        "Old Kills": "old_kills",
        "Kills Difference": "kills_diff",
        "Old Name": "old_name",
    }

    df = df.rename(columns=rename_map)

    required = list(rename_map.values())
    for col in required:
        if col not in df.columns:
            df[col] = 0

    df = df[required]

    numeric_cols = ["might", "old_might", "might_diff", "kills", "old_kills", "kills_diff"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    return df

# ---------------------------------------------------------------------------
# INSERT DATA (ADMIN + OFFICER)
# ---------------------------------------------------------------------------
def insert_data(df, user):
    df["uploaded_by"] = user
    df["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql("guild_data", conn, if_exists="append", index=False)
    except Exception as e:
        st.error(f"❌ Veri yüklenemedi: {e}")
    finally:
        cur = conn.cursor()
        for n, r in zip(df["name"], df["rank"]):
            cur.execute(
                "INSERT OR IGNORE INTO guild_members VALUES (?,?,1,?)",
                (n, r, datetime.now().strftime("%Y-%m-%d"))
            )
        conn.commit()
        conn.close()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM guild_data", conn)
    conn.close()
    return df

# ---------------------------------------------------------------------------
# AUTHENTICATION (Login / Register)
# ---------------------------------------------------------------------------
def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash,role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, None

    stored_hash, role = row
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return True, role
    return False, None

def register_user(username, password, role="User"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE username=?", (username,))
    if cur.fetchone():
        conn.close()
        return False

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                (username,hashed,role))
    conn.commit()
    conn.close()
    return True

# ---------------------------------------------------------------------------
# STYLES (Dark-Light Themes)
# ---------------------------------------------------------------------------
DARK_CSS = """
<style>
body, .stApp {background-color:#111; color:#eee;}
.sidebar .sidebar-content {background:#222;}
.dataframe th, .dataframe td {color:#eee !important;}
.metric-box {background:#222;padding:12px;border-radius:8px;margin-bottom:10px;text-align:center;}
</style>
"""

LIGHT_CSS = """
<style>
body, .stApp {background-color:#f6f6f6; color:#111;}
.metric-box {background:#eaeaea;padding:12px;border-radius:8px;margin-bottom:10px;text-align:center;}
</style>
"""

# ---------------------------------------------------------------------------
# UI SETUP
# ---------------------------------------------------------------------------
st.set_page_config("Guild Analyzer Pro v4", layout="wide")
init_db()
create_default_admin()

if "role" not in st.session_state: st.session_state.role="User"
if "lang" not in st.session_state: st.session_state.lang="TR"
if "theme" not in st.session_state: st.session_state.theme="Dark"
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
    st.session_state.username=None
    st.session_state.role=None

# Sidebar: Language & Theme
st.sidebar.markdown("### 🌐 Language / Dil")
st.session_state.lang = st.sidebar.radio("",["TR","EN"],horizontal=True)

st.sidebar.markdown("### 🎨 Tema")
st.session_state.theme = st.sidebar.radio("",["Dark","Light"],horizontal=True)

# Apply theme
st.markdown(DARK_CSS if st.session_state.theme=="Dark" else LIGHT_CSS, unsafe_allow_html=True)

TXT = {
    "TR":{"login":"Giriş Yap","register":"Kayıt Ol","username":"Kullanıcı Adı","password":"Parola","logout":"Çıkış"},
    "EN":{"login":"Login","register":"Register","username":"Username","password":"Password","logout":"Logout"}
}
t = TXT[st.session_state.lang]
