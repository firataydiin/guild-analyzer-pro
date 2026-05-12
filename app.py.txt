import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import bcrypt
from datetime import datetime

DB_PATH = "data.db"

# ========== VERİTABANI BAŞLATMA ==========

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
        print("Varsayılan admin oluşturuldu -> Kullanıcı: RebelW0lf")
    conn.close()

# ========== KULLANICI FONKSİYONLARI ==========

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

def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash, is_admin FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False, False
    stored_hash, is_admin = row
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return True, bool(is_admin)
    return False, False

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

def delete_row(row_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM guild_data WHERE id=?", (row_id,))
    conn.commit()
    conn.close()

# ========== UYGULAMA ==========

st.set_page_config(page_title="Guild Analyzer Pro (Secure Admin)", layout="wide")

init_db()
create_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_admin = False

# GİRİŞ / KAYIT EKRANI
if not st.session_state.logged_in:
    st.title("🔐 Giriş / Kayıt")

    choice = st.radio("İşlem Seç:", ["Giriş Yap", "Kayıt Ol"])
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Parola", type="password")

    if choice == "Kayıt Ol":
        if st.button("Hesap Oluştur"):
            if register_user(username, password):
                st.success("Kayıt tamamlandı ✅ Artık giriş yapabilirsiniz.")
            else:
                st.error("Bu kullanıcı adı zaten kayıtlı.")
    else:
        if st.button("Giriş"):
            success, is_admin = login_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.is_admin = is_admin
                st.experimental_rerun()
            else:
                st.error("Kullanıcı veya parola hatalı.")
else:
    st.sidebar.title(f"✨ Hoş geldin, {st.session_state.user}")
    if st.sidebar.button("🚪 Çıkış"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    st.title("⚔️ Guild Analyzer Pro — Güvenli Sürüm")

    uploaded = st.file_uploader("Yeni Excel dosyası yükle (.xlsx)", type=["xlsx"])
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
        st.success(f"{len(df)} satır başarıyla eklendi ✅")

    data = load_data()
    if data.empty:
        st.info("Henüz veri yok.")
        st.stop()

    st.subheader("📋 Yüklenmiş Veriler")
    st.dataframe(data[["id", "upload_date", "uploaded_by", "name", "rank", "might_diff", "kills_diff"]])

    if st.session_state.is_admin:
        st.subheader("🗑️ Kayıt Sil (Yalnızca Admin)")
        row_to_delete = st.number_input("Silinecek ID numarası:", min_value=0, step=1)
        if st.button("Sil"):
            delete_row(row_to_delete)
            st.warning(f"ID {row_to_delete} silindi.")
            st.experimental_rerun()
    else:
        st.info("🔒 Sadece admin kullanıcılar veri silebilir.")

    st.subheader("📊 Analizler")

    top_gain = data.sort_values("might_diff", ascending=False).head(5)
    top_loss = data.sort_values("might_diff").head(5)

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Oyuncu", len(data))
    c2.metric("Toplam Might Farkı", int(data["might_diff"].sum()))
    c3.metric("Toplam Kills Farkı", int(data["kills_diff"].sum()))

    st.markdown("### 🏹 En Çok Might Kazananlar")
    st.table(top_gain[["name", "might_diff"]])

    st.markdown("### 💥 En Çok Might Kaybedenler")
    st.table(top_loss[["name", "might_diff"]])

    st.markdown("### 📈 Might Farkı Grafiği")
    fig, ax = plt.subplots()
    ax.hist(data["might_diff"], bins=20, color="mediumseagreen", edgecolor="black")
    ax.set_xlabel("Might Difference")
    ax.set_ylabel("Oyuncu Sayısı")
    st.pyplot(fig)
