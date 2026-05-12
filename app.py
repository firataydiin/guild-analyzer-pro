import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
from datetime import datetime

DB_PATH = "data.db"

# ---------- Veritabanı Hazırlığı ----------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0
        )
    """)
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
        print("Varsayılan admin oluşturuldu: RebelW0lf / 19051905")
    conn.close()

# ---------- Yardımcı Fonksiyonlar ----------

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

def insert_data(df, user):
    df["uploaded_by"] = user
    df["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("guild_data", conn, if_exists="append", index=False)
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM guild_data", conn)
    conn.close()
    return df

# ---------- Uygulama Ayarları ----------

st.set_page_config(page_title="Guild Analyzer Pro", layout="wide")
init_db()
create_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_admin = False
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# ---------- Dil Metinleri ----------

TXT = {
    "EN": {
        "language": "Language",
        "login": "Login",
        "register": "Register",
        "username": "Username",
        "password": "Password",
        "logout": "Logout",
        "welcome": "Welcome",
        "upload": "Upload Excel (.xlsx)",
        "records": "Uploaded Records",
        "showhide": "Show / Hide Data",
        "delete": "Delete Record (Admin only)",
        "analyzer": "Guild Analyzer",
        "gfpoint": "GF POINT",
        "first": "First Upload",
        "last": "Last Upload",
        "by": "Uploaded by",
        "player_summary": "Player Upload Summary (Admin)",
    },
    "TR": {
        "language": "Dil",
        "login": "Giriş Yap",
        "register": "Kayıt Ol",
        "username": "Kullanıcı Adı",
        "password": "Parola",
        "logout": "Çıkış",
        "welcome": "Hoş Geldin",
        "upload": "Excel Dosyası Yükle (.xlsx)",
        "records": "Yüklenmiş Veriler",
        "showhide": "Verileri Göster / Gizle",
        "delete": "Kayıt Sil (Sadece Admin)",
        "analyzer": "Guild Analiz",
        "gfpoint": "GF PUAN",
        "first": "İlk Yükleme",
        "last": "Son Yükleme",
        "by": "Yükleyen",
        "player_summary": "Yükleme Özeti (Sadece Admin)",
    }
}

# ---------- Giriş Ekranı ----------

if not st.session_state.logged_in:
    st.title("⚔️ Guild Analyzer Pro")

    # Dil seçimi (sayfanın başında)
    lang_col1, lang_col2 = st.columns([1, 2])
    with lang_col1:
        st.session_state.lang = st.selectbox("🌐 Language / Dil", ["EN", "TR"], index=1)
    t = TXT[st.session_state.lang]

    choice = st.radio(f"{t['language']}:", [t["login"], t["register"]], horizontal=True)
    username = st.text_input(t["username"])
    password = st.text_input(t["password"], type="password")

    if choice == t["register"]:
        if st.button(t["register"]):
            if register_user(username, password):
                st.success("Kayıt oluşturuldu.")
            else:
                st.error("Bu kullanıcı adı zaten var!")
    else:
        if st.button(t["login"]):
            ok, is_admin = verify_user(username, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.is_admin = is_admin
                st.rerun()
            else:
                st.error("Kullanıcı veya parola hatalı.")
else:
    # ---------- Ana Sayfa ----------
    t = TXT[st.session_state.lang]

    header_col1, header_col2, header_col3 = st.columns([8, 1, 1])
    with header_col2:
        st.write(f"👤 {st.session_state.user}")
    with header_col3:
        if st.button(t["logout"]):
            st.session_state.logged_in = False
            st.rerun()

    menu_choice = st.sidebar.radio("Menü", [t["analyzer"], t["gfpoint"]])
    st.title(f"⚔️ {menu_choice}")

    if menu_choice == t["analyzer"]:
        uploaded = st.file_uploader(t["upload"], type=["xlsx"])
        if uploaded:
            df = pd.read_excel(uploaded).fillna("")
            df = df.rename(columns={
                "IGG ID": "igg_id",
                "Name": "name",
                "Rank": "rank",
                "Might": "might",
                "Old Might": "old_might",
                "Might Difference": "might_diff",
                "Kills": "kills",
                "Old Kills": "old_kills",
                "Kills Difference": "kills_diff",
                "Old Name": "old_name"
            })
            insert_data(df, st.session_state.user)
            st.success(f"{len(df)} satır yüklendi ✅")

        data = load_data()
        if not data.empty:
            if st.button(t["showhide"]):
                st.dataframe(
                    data[["id", "upload_date", "uploaded_by", "name", "rank",
                          "might_diff", "kills_diff"]],
                    use_container_width=True
                )

            if st.session_state.is_admin:
                st.subheader(f"🔒 {t['player_summary']}")
                grouped = data.groupby("name").agg(
                    first_upload=("upload_date", "min"),
                    last_upload=("upload_date", "max"),
                    total_might=("might_diff", "sum"),
                    total_kills=("kills_diff", "sum"),
                    uploader=("uploaded_by", "last")
                ).reset_index()

                for i, row in grouped.iterrows():
                    st.markdown(
                        f"<div style='border:1px solid #ccc;padding:8px;border-radius:6px;margin-bottom:6px;'>"
                        f"<b>{row['name']}</b> - {t['by']}: {row['uploader']}<br>"
                        f"💪 {t['first']}: {row['first_upload']} | ☠️ {t['last']}: {row['last_upload']}<br>"
                        f"Might Δ: {int(row['total_might'])} | Kills Δ: {int(row['total_kills'])}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                st.subheader(f"🗑️ {t['delete']}")
                del_id = st.number_input("ID", min_value=0, step=1)
                if st.button("Sil"):
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("DELETE FROM guild_data WHERE id=?", (del_id,))
                    conn.commit()
                    conn.close()
                    st.warning(f"{del_id} ID silindi.")
                    st.rerun()
        else:
            st.info("Henüz veri yok.")
    else:
        st.markdown("🏹 **GF PUAN bölümü** – Yakında eklenecek.")
