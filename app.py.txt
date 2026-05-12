# ---------------------------------------------------------------------------
# Guild Analyzer Pro - Daily Change Report Edition
# Step 2 in advanced UI series
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
from datetime import datetime, timedelta

DB_PATH = "data.db"
TODAY = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    CREATE TABLE IF NOT EXISTS gf_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploaded_by TEXT,
        upload_date TEXT,
        name TEXT,
        gf_points REAL
    );
    """)
    conn.commit(); conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        pw = bcrypt.hashpw("19051905".encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users VALUES ('RebelW0lf', ?, 1)", (pw,))
        conn.commit()
    conn.close()

# ---------------- HELPERS ----------------
def clean_excel(df):
    df = df.fillna("")
    expected = ["IGG ID","Name","Rank","Might","Old Might",
                "Might Difference","Kills","Old Kills","Kills Difference","Old Name"]
    df.columns = [c.strip().title() for c in df.columns]
    for col in expected:
        if col not in df.columns:
            df[col] = 0
    df = df[expected]
    for c in ["Might","Old Might","Might Difference",
              "Kills","Old Kills","Kills Difference"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def insert_data(df,user):
    df["uploaded_by"]=user
    df["upload_date"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn=sqlite3.connect(DB_PATH)
    df.to_sql("guild_data",conn,if_exists="append",index=False)
    cur=conn.cursor()
    for n,r in zip(df["Name"],df["Rank"]):
        cur.execute("INSERT OR IGNORE INTO guild_members VALUES (?,?,1,?)",(n,r,datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()

def load_data():
    conn=sqlite3.connect(DB_PATH)
    df=pd.read_sql("SELECT * FROM guild_data",conn)
    conn.close(); return df

# ---------------- AUTH ----------------
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

# ---------------- UI ----------------
st.set_page_config("Guild Analyzer Pro", layout="wide")
init_db(); create_default_admin()

# Theme
if "theme" not in st.session_state: st.session_state.theme="Dark"
theme_choice = st.sidebar.radio("🎨 Tema",["Dark","Light"],index=0)
DARK = "<style>body,.stApp{background:#1b1d23;color:#e0e0e0}</style>"
LIGHT = "<style>body,.stApp{background:#f2f2f2;color:#111}</style>"
st.markdown(DARK if theme_choice=="Dark" else LIGHT, unsafe_allow_html=True)

# Session vars
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
    st.session_state.user=None
    st.session_state.is_admin=False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.title("⚔️ Guild Analyzer Pro")
    act=st.radio("İşlem",["Giriş Yap","Kayıt Ol"],horizontal=True)
    u=st.text_input("Kullanıcı Adı"); p=st.text_input("Parola",type="password")
    if act=="Kayıt Ol":
        if st.button("Kaydol"): 
            st.success("Kayıt eklendi") if register_user(u,p) else st.error("Kullanıcı mevcut")
    else:
        if st.button("Giriş"):
            ok,adm=verify_user(u,p)
            if ok: st.session_state.update(logged_in=True,user=u,is_admin=adm); st.rerun()
            else: st.error("Hatalı kullanıcı veya şifre")
else:
    left,right=st.columns([10,1])
    with right:
        if st.button("Çıkış"): st.session_state.logged_in=False; st.rerun()

    menu=st.sidebar.radio("Menü",
        ["Dashboard","Guild Analyzer","GF Point","Üyeler"])
    st.title(f"⚔️ {menu}")

    # --------------- DASHBOARD ----------------
    if menu=="Dashboard":
        conn=sqlite3.connect(DB_PATH)
        data=pd.read_sql("SELECT * FROM guild_data",conn)
        mem=pd.read_sql("SELECT * FROM guild_members",conn)
        conn.close()
        if not data.empty:
            total_kills=int(data["Kills Difference"].sum())
            total_might=int(data["Might Difference"].sum())
            active=len(mem)
            last=data["upload_date"].max()
            c1,c2,c3,c4=st.columns(4)
            c1.metric("🩸 Toplam Kill",f"{total_kills:,}")
            c2.metric("💪 Toplam Might",f"{total_might:,}")
            c3.metric("👥 Aktif Üye",f"{active}/100")
            c4.metric("📅 Son Güncelleme",last)

            # Günlük toplam grafiği
            data["Gün"]=data["upload_date"].str[:10]
            daily=data.groupby("Gün")[["Kills Difference","Might Difference"]].sum()
            st.markdown("### 📊 Günlük Varyasyon Grafiği")
            st.bar_chart(daily)

            # ----- Günlük Değişim RAPORU -----
            if st.session_state.is_admin:
                st.markdown("## 📅 Günlük Değişim Raporu")
                selected = st.date_input("Tarih Seç", value=datetime.now().date())
                prev_day = (selected - timedelta(days=1)).strftime("%Y-%m-%d")

                today_data = data[data["upload_date"].str.startswith(str(selected))]
                yesterday = data[data["upload_date"].str.startswith(prev_day)]

                if not today_data.empty and not yesterday.empty:
                    merged = pd.merge(today_data,yesterday,on="Name",suffixes=("_new","_old"))
                    merged["KillChange"] = merged["Kills Difference_new"] - merged["Kills Difference_old"]
                    merged["MightChange"] = merged["Might Difference_new"] - merged["Might Difference_old"]

                    top_kill = merged.sort_values("KillChange",ascending=False).head(5)[["Name","KillChange"]]
                    down_might = merged.sort_values("MightChange").head(5)[["Name","MightChange"]]

                    col1,col2 = st.columns(2)
                    col1.markdown("### 🏆 En Çok Kill Artışı")
                    col1.dataframe(top_kill,use_container_width=True)
                    col2.markdown("### 💀 Might Kaybı Yaşayanlar")
                    col2.dataframe(down_might,use_container_width=True)

                    tot_change = merged["KillChange"].sum()
                    st.metric("🔺 Günlük Toplam Kill Artışı", f"{int(tot_change):,}")
                else:
                    st.info("Seçilen gün veya önceki gün için veri bulunamadı.")
        else: st.info("Henüz veri yok.")

    # --------------- GUILD ANALYZER -------------
    elif menu=="Guild Analyzer":
        up=st.file_uploader("Excel Yükle (.xlsx)",type=["xlsx"])
        if up:
            df=pd.read_excel(up)
            df=clean_excel(df)
            insert_data(df,st.session_state.user)
            st.success(f"{len(df)} kayıt eklendi ✅")
        data=load_data()
        if not data.empty:
            date_select = st.date_input("📅 Tarih Seç")
            d=str(date_select)
            filt=data[data["upload_date"].str.startswith(d)]
            if filt.empty:
                st.warning("Bu tarih için veri yok.")
            else:
                if st.session_state.is_admin:
                    c1,c2=st.columns(2)
                    top=filt.sort_values("Kills Difference",ascending=False).head(10)
                    low=filt.sort_values("Kills Difference").head(10)
                    c1.markdown("### 🏆 En Çok Kill Yapanlar")
                    c1.dataframe(top[["Name","Kills Difference"]])
                    c2.markdown("### 💀 En Az Kill Yapanlar")
                    c2.dataframe(low[["Name","Kills Difference"]])
                    st.metric("Toplam Kill", int(filt["Kills Difference"].sum()))
                def color(v):
                    c='lightgreen' if v>100000 else 'salmon' if v<0 else 'white'
                    return f'background-color:{c}'
                st.dataframe(filt.style.applymap(color,subset=["Kills Difference"]))
        else: st.info("Henüz veri yüklenmedi.")

    # --------------- GF POINT -----------------
    elif menu=="GF Point":
        up=st.file_uploader("GF Point Excel (.xlsx)",type=["xlsx"])
        if up:
            df=pd.read_excel(up).fillna("")
            if "GF Points" in df.columns:
                df=df.rename(columns={"Name":"name","GF Points":"gf_points"})
                df["upload_date"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df["uploaded_by"]=st.session_state.user
                conn=sqlite3.connect(DB_PATH)
                df.to_sql("gf_data",conn,if_exists="append",index=False)
                conn.close()
                st.success("GF verisi eklendi ✅")
        conn=sqlite3.connect(DB_PATH)
        g=pd.read_sql("SELECT * FROM gf_data",conn)
        conn.close()
        if not g.empty:
            st.metric("Toplam GF", int(g["gf_points"].sum()))
            if st.session_state.is_admin:
                c1,c2=st.columns(2)
                c1.dataframe(g.sort_values("gf_points",ascending=False).head(10))
                c2.dataframe(g.sort_values("gf_points").head(10))
        else: st.info("GF verisi yok.")

    # --------------- ÜYELER -----------------
    elif menu=="Üyeler":
        conn=sqlite3.connect(DB_PATH)
        mem=pd.read_sql("SELECT * FROM guild_members",conn)
        conn.close()
        st.metric("Toplam Üye", f"{len(mem)}/100")
        st.dataframe(mem)
