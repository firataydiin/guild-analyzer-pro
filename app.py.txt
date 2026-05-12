# ------------------------------------------------------------------------------
# Guild Analyzer Pro - Advanced Guild Management Panel
# Türkçe & İngilizce - Renkli görseller, üyeler, tarih filtresi ve sohbet
# ------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
from datetime import datetime

DB_PATH = "data.db"
DATE_TODAY = datetime.now().strftime("%Y-%m-%d")

# ----------------- DATABASE SETUP --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Main data
    cur.execute("""
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
    )""")

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        is_admin INTEGER DEFAULT 0
    )""")

    # Members
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_members (
        name TEXT PRIMARY KEY,
        rank TEXT,
        is_active INTEGER DEFAULT 1,
        joined_date TEXT
    )""")

    # GF Points
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gf_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploaded_by TEXT,
        upload_date TEXT,
        name TEXT,
        gf_points REAL
    )""")

    # Chat
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message TEXT,
        timestamp TEXT
    )""")

    conn.commit()
    conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE is_admin=1")
    if not cur.fetchone():
        username = "RebelW0lf"
        password = "19051905"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                    (username, hashed))
        conn.commit()
        print("Default admin -> RebelW0lf / 19051905")
    conn.close()

# ------------------ CORE DATA OPS ---------------------

def insert_data(df, user):
    df["uploaded_by"] = user
    df["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("guild_data", conn, if_exists="append", index=False)
    # also auto update members
    cur = conn.cursor()
    for name, rank in zip(df["name"], df["rank"]):
        cur.execute("INSERT OR IGNORE INTO guild_members (name, rank, joined_date) VALUES (?,?,?)",
                    (name, rank, DATE_TODAY))
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM guild_data", conn)
    conn.close()
    return df

def save_message(user, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO guild_chat (username, message, timestamp) VALUES (?,?,?)",
                 (user, message, ts))
    conn.commit()
    conn.close()

def get_messages(limit=25):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM guild_chat ORDER BY id DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df[::-1]  # reverse for chronological order


# ---------------- AUTH SYSTEM -------------------

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash,is_admin FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False, False
    stored_hash, is_admin = row
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return True, bool(is_admin)
    return False, False

def register_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE username=?", (username,))
    if cur.fetchone():
        conn.close()
        return False
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)",
                (username, hashed))
    conn.commit()
    conn.close()
    return True

# ---------------- UI CONFIG ---------------------

st.set_page_config(page_title="Guild Analyzer Pro", layout="wide")
init_db()
create_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_admin = False
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

TXT = {
    "EN": {"login":"Login","register":"Register","username":"Username","password":"Password",
           "logout":"Logout","upload":"Upload Excel (.xlsx)","records":"Uploaded Records",
           "showhide":"Show / Hide Data","guild":"Guild Analyzer","gf":"GF Point","chat":"Chat","members":"Members"},
    "TR": {"login":"Giriş Yap","register":"Kayıt Ol","username":"Kullanıcı Adı","password":"Parola",
           "logout":"Çıkış","upload":"Excel Yükle (.xlsx)","records":"Yüklenmiş Veriler",
           "showhide":"Verileri Göster / Gizle","guild":"Guild Analiz","gf":"GF Puan","chat":"Sohbet","members":"Üyeler"}
}

# ---------------- LOGIN SCREEN ---------------------
if not st.session_state.logged_in:
    st.sidebar.markdown("### 🌐 Language / Dil")
    st.session_state.lang = st.sidebar.radio("", ["EN", "TR"])
    t = TXT[st.session_state.lang]

    st.title("⚔️ Guild Analyzer Pro")
    act = st.radio("", [t["login"], t["register"]], horizontal=True)
    u = st.text_input(t["username"])
    p = st.text_input(t["password"], type="password")

    if act == t["register"]:
        if st.button(t["register"]):
            st.success("Account created" if register_user(u,p) else "User exists!")
    else:
        if st.button(t["login"]):
            ok, adm = verify_user(u,p)
            if ok:
                st.session_state.logged_in=True
                st.session_state.user=u
                st.session_state.is_admin=adm
                st.rerun()
            else:
                st.error("Invalid credentials")
else:
    t = TXT[st.session_state.lang]
    # ------------- TOP BAR ----------------
    left,right = st.columns([10,1])
    with right:
        if st.button(t["logout"]):
            st.session_state.logged_in=False
            st.rerun()

    # Sidebar menu
    section = st.sidebar.radio("📂 Menü", [t["guild"], t["gf"], t["members"], t["chat"]])
    st.title(f"⚔️ {section}")

    # ------------- GUILD ANALYZER -------------
    if section == t["guild"]:
        uploaded = st.file_uploader(t["upload"], type=["xlsx"])
        if uploaded:
            df = pd.read_excel(uploaded).fillna("")
            if "Kills Difference" in df.columns:
                df = df.rename(columns={"Kills Difference": "kills_diff",
                                        "Might Difference": "might_diff",
                                        "Name": "name","Rank":"rank"})
                insert_data(df, st.session_state.user)
                st.success(f"{len(df)} kayıt yüklendi ✅")

        data = load_data()
        if not data.empty:
            # Date filter
            selected_date = st.date_input("📅 Tarih seç:")
            st.write("Seçilen tarih:", selected_date)
            filtered = data[data["upload_date"].str.startswith(str(selected_date))]

            # Top & Low kills
            if st.session_state.is_admin:
                st.subheader("🏆 Top 10 Killers / Lowest 10")
                col1,col2 = st.columns(2)
                top10 = filtered.sort_values("kills_diff", ascending=False).head(10)
                low10 = filtered.sort_values("kills_diff").head(10)
                col1.markdown("#### Top 10")
                col1.dataframe(top10[["name","kills_diff"]], use_container_width=True)
                col2.markdown("#### Lowest 10")
                col2.dataframe(low10[["name","kills_diff"]], use_container_width=True)

                total_kills = int(filtered["kills_diff"].sum())
                st.metric("Total Kills (Selected Date)", f"{total_kills:,}")

            # Colored full data
            def color_kills(v): 
                c='lightgreen' if v>100000 else 'salmon' if v<0 else 'white'
                return f'background-color:{c}'
            st.dataframe(filtered.style.applymap(color_kills, subset=["kills_diff"]), use_container_width=True)
        else:
            st.info("Henüz veri yok.")

    # ------------- GF POINT -------------
    elif section == t["gf"]:
        gf = st.file_uploader("GF Point Yükle (Excel)", type=["xlsx"])
        if gf:
            gdf = pd.read_excel(gf).fillna("")
            if "GF Points" in gdf.columns:
                gdf = gdf.rename(columns={"Name":"name","GF Points":"gf_points"})
                gdf["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                gdf["uploaded_by"] = st.session_state.user
                conn = sqlite3.connect(DB_PATH)
                gdf.to_sql("gf_data", conn, if_exists="append", index=False)
                conn.close()
                st.success("GF verileri yüklendi ✅")

        conn = sqlite3.connect(DB_PATH)
        gdf = pd.read_sql("SELECT * FROM gf_data",conn)
        conn.close()
        if not gdf.empty:
            st.metric("Total GF Points", int(gdf["gf_points"].sum()))
            if st.session_state.is_admin:
                top = gdf.sort_values("gf_points", ascending=False).head(10)
                low = gdf.sort_values("gf_points").head(10)
                col1,col2=st.columns(2)
                col1.markdown("### Top 10 Points")
                col1.dataframe(top[["name","gf_points"]])
                col2.markdown("### Lowest 10 Points")
                col2.dataframe(low[["name","gf_points"]])

    # ------------- MEMBERS -------------
    elif section == t["members"]:
        conn = sqlite3.connect(DB_PATH)
        mem = pd.read_sql("SELECT * FROM guild_members", conn)
        conn.close()
        st.metric("Total Members (Max 100)", f"{len(mem)}/100")
        st.dataframe(mem, use_container_width=True)

    # ------------- CHAT -------------
    elif section == t["chat"]:
        st.subheader("💬 Lonca Sohbeti")
        msg = st.text_input("Mesaj yaz...")
        if st.button("Gönder"):
            if msg.strip():
                save_message(st.session_state.user,msg)
                st.success("Mesaj gönderildi")
                st.rerun()
        messages = get_messages()
        for _,m in messages.iterrows():
            st.markdown(f"**{m['username']}**: {m['message']}  \n*{m['timestamp']}*")

