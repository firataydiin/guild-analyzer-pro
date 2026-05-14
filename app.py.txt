# ---------------------------------------------------------------------------
# Guild Analyzer Pro v2 – Weekly Visual Dashboard Edition
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
from datetime import datetime

DB_PATH = "data.db"

# ---------------------------------------------------------------------------
# INITIALIZATION
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
        is_admin INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS guild_members (
        name TEXT PRIMARY KEY,
        rank TEXT,
        is_active INTEGER DEFAULT 1,
        joined_date TEXT
    );
    """)
    conn.commit(); conn.close()

def create_default_admin():
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        hashed=bcrypt.hashpw("19051905".encode(),bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users VALUES ('RebelW0lf', ?, 1)",(hashed,))
        conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# SAFE EXCEL CLEAN
# ---------------------------------------------------------------------------
def clean_excel(df):
    df = df.fillna("")
    df.columns = [str(c).strip().title().replace("_"," ").replace("-"," ") for c in df.columns]
    rename_map = {
        "Igg Id":"igg_id","Iggid":"igg_id",
        "Name":"name","Rank":"rank",
        "Might":"might","Old Might":"old_might",
        "Might Difference":"might_diff",
        "Kills":"kills","Old Kills":"old_kills",
        "Kills Difference":"kills_diff","Old Name":"old_name"
    }
    df = df.rename(columns=rename_map)
    required=list(rename_map.values())
    for col in required:
        if col not in df.columns:
            df[col]=0
    df=df[required]
    numeric=["might","old_might","might_diff","kills","old_kills","kills_diff"]
    for col in numeric:
        df[col]=pd.to_numeric(df[col],errors="coerce").fillna(0)
    return df

def insert_data(df,user):
    df["uploaded_by"]=user
    df["upload_date"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn=sqlite3.connect(DB_PATH)
    try:
        df.to_sql("guild_data",conn,if_exists="append",index=False)
    except Exception as e:
        st.error(f"Yükleme Hatası: {e}")
    finally:
        cur=conn.cursor()
        for n,r in zip(df["name"],df["rank"]):
            cur.execute("INSERT OR IGNORE INTO guild_members VALUES (?,?,1,?)",
                        (n,r,datetime.now().strftime("%Y-%m-%d")))
        conn.commit(); conn.close()

def load_data():
    conn=sqlite3.connect(DB_PATH)
    df=pd.read_sql("SELECT * FROM guild_data",conn)
    conn.close(); return df

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
def verify_user(u,p):
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT password_hash,is_admin FROM users WHERE username=?",(u,))
    r=c.fetchone(); conn.close()
    if not r: return False,False
    return bcrypt.checkpw(p.encode(),r[0].encode()), bool(r[1])

def register_user(u,p):
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?",(u,))
    if c.fetchone(): conn.close(); return False
    hashed=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users VALUES (?,?,0)",(u,hashed))
    conn.commit(); conn.close(); return True

# ---------------------------------------------------------------------------
# STYLES
# ---------------------------------------------------------------------------
DARK_CSS = """
<style>
body, .stApp {background-color:#111; color:#e6e6e6;}
.block-container {padding-top:1rem;}
.sidebar .sidebar-content {background: #222;}
.dataframe th, .dataframe td {color:#e6e6e6 !important;}
</style>
"""

LIGHT_CSS = """
<style>
body, .stApp {background-color:#fafafa; color:#111;}
</style>
"""

# ---------------------------------------------------------------------------
# UI LOGIC
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Guild Analyzer Pro v2", layout="wide")
init_db(); create_default_admin()

if "theme" not in st.session_state: st.session_state.theme="Dark"
if "lang" not in st.session_state: st.session_state.lang="TR"
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
    st.session_state.user=None
    st.session_state.is_admin=False

# --- Dil / Tema seçici ---
st.sidebar.markdown("### 🌐 Language / Dil")
st.session_state.lang = st.sidebar.radio("",["TR","EN"],horizontal=True)
st.sidebar.markdown("### 🎨 Tema")
st.session_state.theme = st.sidebar.radio("",["Dark","Light"],horizontal=True)
st.markdown(DARK_CSS if st.session_state.theme=="Dark" else LIGHT_CSS, unsafe_allow_html=True)

TXT={
    "TR":{"login":"Giriş Yap","register":"Kayıt Ol","username":"Kullanıcı Adı","password":"Parola","logout":"Çıkış"},
    "EN":{"login":"Login","register":"Register","username":"Username","password":"Password","logout":"Logout"}
}
t=TXT[st.session_state.lang]

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.logged_in:
    st.title("⚔️ Guild Analyzer Pro v2")
    act=st.radio("İşlem",[t["login"],t["register"]],horizontal=True)
    u=st.text_input(t["username"])
    p=st.text_input(t["password"],type="password")
    if act==t["register"]:
        if st.button("Oluştur"):
            st.success("Created ✅") if register_user(u,p) else st.error("User exists!")
    else:
        if st.button(t["login"]):
            ok,adm=verify_user(u,p)
            if ok: st.session_state.update(logged_in=True,user=u,is_admin=adm); st.rerun()
            else: st.error("Wrong credentials")
else:
    left,right=st.columns([10,1])
    with right:
        if st.button(t["logout"]): st.session_state.logged_in=False; st.rerun()

    menu=st.sidebar.radio("Menü",["Dashboard","Guild Analyzer","GF Point","Üyeler"])
    st.title(f"⚔️ {menu}")

    # ---------------- DASHBOARD ----------------
    if menu=="Dashboard":
        data=load_data()
        if data.empty:
            st.info("Henüz veri yok.")
        else:
            # Haftalık veriye dönüştürme
            data["Tarih"]=pd.to_datetime(data["upload_date"]).dt.date
            data["Hafta"]=pd.to_datetime(data["upload_date"]).dt.isocalendar().week
            st.subheader("📅 Haftalık Performans Paneli")

            haftalar=data["Hafta"].unique().tolist()
            haftalar.sort()
            secilen=st.selectbox("Hafta Seç:",haftalar)
            dfhafta=data[data["Hafta"]==secilen]

            haftalik=dfhafta.groupby("name",as_index=False)[["kills_diff","might_diff"]].sum()
            haftalik=haftalik.sort_values("kills_diff",ascending=False)

            total_k=int(haftalik["kills_diff"].sum())
            total_m=int(haftalik["might_diff"].sum())
            aktif=len(dfhafta["name"].unique())

            c1,c2,c3=st.columns(3)
            c1.metric("🩸 Toplam Kill",f"{total_k:,}")
            c2.metric("💪 Toplam Might",f"{total_m:,}")
            c3.metric("👥 Aktif Oyuncu",f"{aktif}")

            st.markdown("### 🏆 En Çok Kill Yapan 10 Oyuncu")
            top10=haftalik.head(10)
            fig,ax=plt.subplots(figsize=(8,4))
            bars=ax.barh(top10["name"],top10["kills_diff"],color=plt.cm.viridis_r(top10["kills_diff"]/max(top10["kills_diff"])))
            ax.invert_yaxis(); ax.set_xlabel("Kills Δ"); ax.set_ylabel("Oyuncu"); ax.set_title("Top 10 Killers")
            st.pyplot(fig)

            st.markdown("### 📋 Tüm Oyuncular (Haftalık Toplamlar)")
            renk=[f"background-color: rgba(0,255,0,{min(1,v/max(haftalik['kills_diff']))})" for v in haftalik["kills_diff"]]
            st.dataframe(haftalik.style.apply(lambda _: renk, axis=0, subset=["kills_diff"]))

    # ---------------- GUILD ANALYZER ----------------
    elif menu=="Guild Analyzer":
        up=st.file_uploader("Excel (.xlsx)",type=["xlsx"])
        if up:
            df=pd.read_excel(up)
            df=clean_excel(df)
            insert_data(df,st.session_state.user)
            st.success(f"{len(df)} kayıt yüklendi ✅")

    # ---------------- GF POINT ----------------
    elif menu=="GF Point":
        st.write("🧮 GF Point alanı yakında güncellenecek. (Veri yükleme aktif)")
        up=st.file_uploader("GF Point Excel (.xlsx)",type=["xlsx"])
        if up:
            df=pd.read_excel(up).fillna("")
            if "GF Points" in df.columns:
                df=df.rename(columns={"Name":"name","GF Points":"gf_points"})
                df["upload_date"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df["uploaded_by"]=st.session_state.user
                conn=sqlite3.connect(DB_PATH)
                df.to_sql("gf_data",conn,if_exists="append",index=False); conn.close()
                st.success("GF verisi eklendi ✅")

    # ---------------- MEMBERS ----------------
    elif menu=="Üyeler":
        conn=sqlite3.connect(DB_PATH)
        mem=pd.read_sql("SELECT * FROM guild_members",conn); conn.close()
        st.metric("Toplam Üye",f"{len(mem)}/100")
        st.dataframe(mem)
