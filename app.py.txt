# ---------------------------------------------------------------------------
# Guild Analyzer Pro – Stable Data-Load Fix Edition (May 2026)
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime, timedelta

DB_PATH = "data.db"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
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
        is_admin INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS guild_members (
        name TEXT PRIMARY KEY,
        rank TEXT,
        is_active INTEGER DEFAULT 1,
        joined_date TEXT
    );
    """)
    conn.commit()
    conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        pw = bcrypt.hashpw("19051905".encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users VALUES ('RebelW0lf', ?, 1)", (pw,))
        conn.commit()
    conn.close()

# ---------------- CLEAN EXCEL ----------------
def clean_excel(df):
    """Normalize and validate Excel columns before inserting to DB"""
    df = df.fillna("")

    # Normalize all column names
    df.columns = [str(col).strip().title().replace("_", " ").replace("-", " ") for col in df.columns]

    expected = [
        "Igg Id", "Name", "Rank", "Might", "Old Might",
        "Might Difference", "Kills", "Old Kills",
        "Kills Difference", "Old Name"
    ]

    # Add missing expected columns
    for col in expected:
        if col not in df.columns:
            df[col] = 0

    # Keep only expected columns in proper order
    df = df[[col for col in expected]]

    # Convert numeric columns safely
    num_cols = ["Might", "Old Might", "Might Difference",
                "Kills", "Old Kills", "Kills Difference"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# ---------------- INSERT DATA ----------------
def insert_data(df, user):
    df["uploaded_by"] = user
    df["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql("guild_data", conn, if_exists="append", index=False)
    except Exception as e:
        st.error(f"Veri yükleme sırasında hata: {e}")
    finally:
        # Update members table safely
        cur = conn.cursor()
        for n, r in zip(df["Name"], df["Rank"]):
            cur.execute(
                "INSERT OR IGNORE INTO guild_members VALUES (?,?,1,?)",
                (n, r, datetime.now().strftime("%Y-%m-%d"))
            )
        conn.commit()
        conn.close()

# ---------------- AUTH ----------------
def verify_user(u, p):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash, is_admin FROM users WHERE username=?", (u,))
    r = c.fetchone()
    conn.close()
    if not r:
        return False, False
    return bcrypt.checkpw(p.encode(), r[0].encode()), bool(r[1])

def register_user(u, p):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (u,))
    if c.fetchone():
        conn.close()
        return False
    hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users VALUES (?,?,0)", (u, hashed))
    conn.commit()
    conn.close()
    return True

# ---------------- UI ----------------
st.set_page_config("Guild Analyzer Pro", layout="wide")
init_db()
create_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_admin = False

# ------------- LOGIN / REGISTER -------------
if not st.session_state.logged_in:
    st.title("⚔️ Guild Analyzer Pro")
    act = st.radio("İşlem", ["Giriş Yap", "Kayıt Ol"], horizontal=True)
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Parola", type="password")

    if act == "Kayıt Ol":
        if st.button("Kaydet"):
            st.success("Kayıt oluşturuldu ✅") if register_user(u, p) else st.error("Kullanıcı mevcut.")
    else:
        if st.button("Giriş"):
            ok, adm = verify_user(u, p)
            if ok:
                st.session_state.update(logged_in=True, user=u, is_admin=adm)
                st.rerun()
            else:
                st.error("Hatalı bilgi")

else:
    left, right = st.columns([10, 1])
    with right:
        if st.button("Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    menu = st.sidebar.radio("Menü", ["Veri Yükle", "Veritabanı Görüntüle"])
    st.title(f"⚔️ {menu}")

    # ----------- DATA UPLOAD -------------
    if menu == "Veri Yükle":
        up = st.file_uploader("Excel (.xlsx)", type=["xlsx"])
        if up:
            df = pd.read_excel(up)
            df = clean_excel(df)  # güvenli veri temizleme
            insert_data(df, st.session_state.user)
            st.success(f"{len(df)} kayıt yüklendi ✅")

    # ----------- VIEW DATABASE -----------
    elif menu == "Veritabanı Görüntüle":
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM guild_data ORDER BY upload_date DESC", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("Henüz veri yüklenmedi.")
