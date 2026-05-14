# ---------------------------------------------------------------------------
# Guild Analyzer Pro - Stable Full Edition (May 2026)
# Veritabanı korumalı kullanıcı panosu • Güvenli Excel yükleme
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime, timedelta

DB_PATH = "data.db"

# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------------
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
    CREATE TABLE IF NOT EXISTS gf_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploaded_by TEXT,
        upload_date TEXT,
        name TEXT,
        gf_points REAL
    );
    CREATE TABLE IF NOT EXISTS admin_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        admin_name TEXT,
        note TEXT,
        created_at TEXT
    );
    """)
    conn.commit()
    conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE is_admin=1")
    if not cur.fetchone():
        hashed = bcrypt.hashpw("19051905".encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users VALUES ('RebelW0lf', ?, 1)", (hashed,))
        conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# SECURE DATA CLEANING FOR EXCEL FILES
# ---------------------------------------------------------------------------
def clean_excel(df):
    """Normalize, validate and sanitize Excel columns before importing"""
    df = df.copy().fillna("")
    df.columns = [str(c).strip().title().replace("_"," ").replace("-", " ") for c in df.columns]

    expected = [
        "Igg Id","Name","Rank","Might","Old Might",
        "Might Difference","Kills","Old Kills",
        "Kills Difference","Old Name"
    ]

    # Eksik sütunları ekle
    for col in expected:
        if col not in df.columns:
            df[col] = 0

    # Fazla sütunları at
    df = df[[c for c in expected]]

    # Sayısal sütunları dönüştür
    numeric = ["Might","Old Might","Might Difference","Kills","Old Kills","Kills Difference"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# ---------------------------------------------------------------------------
# CORE DATA OPS
# ---------------------------------------------------------------------------
def insert_data(df, user):
    def clean_excel(df):
    """Excel dosyasını veritabanı yapısına tam olarak uydurur."""
    df = df.copy().fillna("")

    # Tüm başlıkları normalize et
    df.columns = (
        df.columns.str.strip()
        .str.title()
        .str.replace("_", " ")
        .str.replace("-", " ")
    )

    # Olası tüm varyasyonlar (mapping)
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

    # Sütunları istenen isimlere dönüştür
    df = df.rename(columns=rename_map)

    # Eksik sütunları 0 ile tamamlama
    required = list(rename_map.values())
    for col in required:
        if col not in df.columns:
            df[col] = 0

    # Sadece doğru sıralı sütunlar
    df = df[required]

    # Sayısal değerleri dönüştür
    numeric = ["might", "old_might", "might_diff",
               "kills", "old_kills", "kills_diff"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ---------------------------------------------------------------------------
# AUTH SYSTEM
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# ADMIN NOTES
# ---------------------------------------------------------------------------
def add_note(player, admin, note):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO admin_notes (player_name, admin_name, note, created_at)"
        " VALUES (?, ?, ?, ?)",
        (player, admin, note, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()

def get_notes(player):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT admin_name AS Admin, note AS Not, created_at AS Tarih "
        "FROM admin_notes WHERE player_name=? ORDER BY id DESC",
        conn,
        params=(player,),
    )
    conn.close()
    return df

# ---------------------------------------------------------------------------
# WEEKLY REPORT
# ---------------------------------------------------------------------------
def generate_weekly_report(admin_user="Admin"):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM guild_data", conn)
    conn.close()
    if df.empty:
        st.warning("Veri bulunamadı.")
        return None

    df["date"] = pd.to_datetime(df["upload_date"]).dt.date
    week_ago = datetime.now().date() - timedelta(days=7)
    week_df = df[df["date"] >= week_ago]
    if week_df.empty:
        st.warning("Son 7 güne ait veri yok.")
        return None

    total_kills = int(week_df["Kills Difference"].sum())
    total_might = int(week_df["Might Difference"].sum())

    plt.figure(figsize=(7, 4))
    week_df["Gun"] = week_df["upload_date"].str[:10]
    trend = week_df.groupby("Gun")[["Kills Difference", "Might Difference"]].sum()
    plt.plot(trend.index, trend["Kills Difference"], label="Kills Δ", color="orange")
    plt.plot(trend.index, trend["Might Difference"], label="Might Δ", color="cyan")
    plt.title("7 Günlük Lonca Grafiği")
    plt.legend()
    plt.tight_layout()
    plt.savefig("weekly_chart.png")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Guild Weekly Report", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Prepared by: {admin_user}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(200, 10, txt=f"Total Might: {total_might:,}", ln=True)
    pdf.cell(200, 10, txt=f"Total Kills: {total_kills:,}", ln=True)
    pdf.image("weekly_chart.png", x=20, y=None, w=170)
    pdf.output("guild_weekly_report.pdf")
    return "guild_weekly_report.pdf"

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config("Guild Analyzer Pro", layout="wide")
init_db()
create_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_admin = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.title("⚔️ Guild Analyzer Pro")
    act = st.radio("İşlem", ["Giriş Yap", "Kayıt Ol"], horizontal=True)
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Parola", type="password")

    if act == "Kayıt Ol":
        if st.button("Kaydol"):
            st.success("Kayıt oluşturuldu ✅") if register_user(u, p) else st.error("Kullanıcı mevcut.")
    else:
        if st.button("Giriş"):
            ok, adm = verify_user(u, p)
            if ok:
                st.session_state.update(logged_in=True, user=u, is_admin=adm)
                st.rerun()
            else:
                st.error("Hatalı giriş bilgisi.")
else:
    left, right = st.columns([10, 1])
    with right:
        if st.button("Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    menu = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Guild Analyzer", "GF Point", "Üyeler"],
    )
    st.title(menu)

    # ---------------- DASHBOARD ----------------
    if menu == "Dashboard":
        conn = sqlite3.connect(DB_PATH)
        data = pd.read_sql("SELECT * FROM guild_data", conn)
        mem = pd.read_sql("SELECT * FROM guild_members", conn)
        conn.close()

        if not data.empty:
            c1, c2, c3, c4 = st.columns(4)
            total_kills = int(data["Kills Difference"].sum())
            total_might = int(data["Might Difference"].sum())
            active = len(mem)
            last = data["upload_date"].max()
            c1.metric("🩸 Toplam Kill", f"{total_kills:,}")
            c2.metric("💪 Toplam Might", f"{total_might:,}")
            c3.metric("👥 Aktif Üye", f"{active}/100")
            c4.metric("📅 Son Yükleme", last)
            st.bar_chart(data.groupby(data["upload_date"].str[:10])["Kills Difference"].sum())

            if st.session_state.is_admin:
                st.markdown("---")
                if st.button("📄 Haftalık Rapor Oluştur"):
                    file = generate_weekly_report(st.session_state.user)
                    if file:
                        with open(file, "rb") as f:
                            st.download_button("📥 Raporu İndir", f, file_name=file)
        else:
            st.info("Veri bulunamadı.")

    # ---------------- GUILD ANALYZER ----------------
    elif menu == "Guild Analyzer":
        up = st.file_uploader("Excel (.xlsx)", type=["xlsx"])
        if up:
            df = pd.read_excel(up)
            df = clean_excel(df)
            insert_data(df, st.session_state.user)
            st.success(f"{len(df)} satır eklendi ✅")

        data = load_data()
        if not data.empty:
            d = str(st.date_input("📅 Tarih Seç"))
            filt = data[data["upload_date"].str.startswith(d)]
            if not filt.empty:
                col1, col2 = st.columns(2)
                top = filt.sort_values("Kills Difference", ascending=False).head(10)
                low = filt.sort_values("Kills Difference").head(10)
                col1.dataframe(top[["Name", "Kills Difference"]], use_container_width=True)
                col2.dataframe(low[["Name", "Kills Difference"]], use_container_width=True)
                st.metric("Toplam Kill", int(filt["Kills Difference"].sum()))
            else:
                st.warning("Bu tarih için veri bulunamadı.")

    # ---------------- GF POINT ----------------
    elif menu == "GF Point":
        up = st.file_uploader("GF Point Excel (.xlsx)", type=["xlsx"])
        if up:
            df = pd.read_excel(up).fillna("")
            if "GF Points" in df.columns:
                df = df.rename(columns={"Name": "name", "GF Points": "gf_points"})
                df["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df["uploaded_by"] = st.session_state.user
                conn = sqlite3.connect(DB_PATH)
                df.to_sql("gf_data", conn, if_exists="append", index=False)
                conn.close()
                st.success("GF verisi eklendi ✅")
        conn = sqlite3.connect(DB_PATH)
        g = pd.read_sql("SELECT * FROM gf_data", conn)
        conn.close()
        if not g.empty:
            st.metric("Toplam GF", int(g["gf_points"].sum()))
        else:
            st.info("GF verisi yok.")

    # ---------------- MEMBERS ----------------
    elif menu == "Üyeler":
        conn = sqlite3.connect(DB_PATH)
        mem = pd.read_sql("SELECT * FROM guild_members", conn)
        data = pd.read_sql("SELECT * FROM guild_data", conn)
        conn.close()
        st.metric("Toplam Üye", f"{len(mem)}/100")
        st.dataframe(mem)
