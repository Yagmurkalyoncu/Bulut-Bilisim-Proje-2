"""
dashboard.py
-------------
Streamlit ile gerçek zamanlı IoT dashboard.

DynamoDB'deki son 100 kaydı çeker ve görselleştirir.
5 saniyede bir otomatik yenilenir.

Kullanım:
  streamlit run dashboard/dashboard.py

Erişim:
  http://localhost:8501
"""

import streamlit as st
import boto3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv

load_dotenv()

# ─── Sayfa konfigürasyonu ──────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Sensör Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── AWS bağlantısı ────────────────────────────────────────────────────────
@st.cache_resource
def get_dynamodb():
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "eu-west-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

@st.cache_resource
def get_table():
    db = get_dynamodb()
    return db.Table(os.getenv("DYNAMODB_TABLE_NAME", "IoTSensorData"))


def fetch_data(device_id: str, limit: int = 100) -> pd.DataFrame:
    """DynamoDB'den son N kaydı çeker."""
    table = get_table()
    try:
        response = table.query(
            KeyConditionExpression=Key("device_id").eq(device_id),
            ScanIndexForward=False,  # En yeni önce
            Limit=limit
        )
        items = response.get("Items", [])
        if not items:
            return pd.DataFrame()

        df = pd.DataFrame(items)
        # Decimal → float dönüşümü
        for col in ["temperature", "humidity", "pressure", "co2_ppm", "light"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: float(x) if isinstance(x, Decimal) else x
                )
        df["datetime"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
        df = df.sort_values("datetime")
        return df

    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return pd.DataFrame()


def fetch_all_devices() -> pd.DataFrame:
    """Tüm sensörlerden son veriyi çek."""
    devices = ["sensor-ankara-01", "sensor-ankara-02", "sensor-ankara-03"]
    frames  = []
    for dev in devices:
        df = fetch_data(dev, limit=1)
        if not df.empty:
            frames.append(df.iloc[0])
    if frames:
        return pd.DataFrame(frames)
    return pd.DataFrame()


# ─── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Ayarlar")
    selected_device = st.selectbox(
        "Sensör Seçin",
        ["sensor-ankara-01", "sensor-ankara-02", "sensor-ankara-03"],
    )
    record_count = st.slider("Gösterilecek kayıt sayısı", 10, 200, 100)
    refresh_interval = st.slider("Yenileme süresi (sn)", 3, 30, 5)
    auto_refresh = st.checkbox("Otomatik yenile", value=True)

    st.divider()
    st.markdown("**Kaynak bilgileri**")
    st.caption(f"Bölge: {os.getenv('AWS_REGION', 'eu-west-1')}")
    st.caption(f"Tablo: {os.getenv('DYNAMODB_TABLE_NAME', 'IoTSensorData')}")


# ─── Ana başlık ────────────────────────────────────────────────────────────
st.title("🌡️ IoT Sensör Veri Dashboard")
st.caption(f"Son güncelleme: {time.strftime('%H:%M:%S')}")

# ─── Tüm sensörler özet ────────────────────────────────────────────────────
st.subheader("Tüm Sensörler — Anlık Değerler")
latest_all = fetch_all_devices()

if not latest_all.empty:
    cols = st.columns(len(latest_all))
    for i, (_, row) in enumerate(latest_all.iterrows()):
        with cols[i]:
            temp = float(row.get("temperature", 0))
            color = "🔴" if temp > 30 else "🟢"
            st.metric(
                label=f"{color} {row['device_id'].split('-', 1)[1]}",
                value=f"{temp:.1f} °C",
                delta=f"Nem: {float(row.get('humidity', 0)):.1f}%"
            )
else:
    st.info("DynamoDB'de henüz veri yok. Sensör simülatörünü başlatın.")

st.divider()

# ─── Seçili sensör detay ───────────────────────────────────────────────────
st.subheader(f"Detay: {selected_device}")
df = fetch_data(selected_device, record_count)

if df.empty:
    st.warning("Bu sensör için veri bulunamadı.")
else:
    # Metrik kartları
    m1, m2, m3, m4, m5 = st.columns(5)
    last = df.iloc[-1]
    m1.metric("Sıcaklık",     f"{float(last.get('temperature', 0)):.1f} °C")
    m2.metric("Nem",          f"{float(last.get('humidity', 0)):.1f} %")
    m3.metric("Basınç",       f"{float(last.get('pressure', 0)):.1f} hPa")
    m4.metric("CO₂",          f"{float(last.get('co2_ppm', 0)):.0f} ppm")
    m5.metric("Işık",         f"{float(last.get('light', 0)):.0f} lux")

    st.divider()

    # ─── Grafikler ─────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["Sıcaklık & Nem", "Basınç & CO₂", "İstatistikler"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["temperature"],
            name="Sıcaklık (°C)", line=dict(color="#EF553B", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["humidity"],
            name="Nem (%)", line=dict(color="#636EFA", width=2),
            yaxis="y2"
        ))
        fig.update_layout(
            yaxis=dict(title="Sıcaklık (°C)"),
            yaxis2=dict(title="Nem (%)", overlaying="y", side="right"),
            hovermode="x unified",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["datetime"], y=df["pressure"],
            name="Basınç (hPa)", line=dict(color="#00CC96", width=2)
        ))
        fig2.add_trace(go.Scatter(
            x=df["datetime"], y=df["co2_ppm"],
            name="CO₂ (ppm)", line=dict(color="#AB63FA", width=2),
            yaxis="y2"
        ))
        fig2.update_layout(
            yaxis=dict(title="Basınç (hPa)"),
            yaxis2=dict(title="CO₂ (ppm)", overlaying="y", side="right"),
            hovermode="x unified",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Sıcaklık Dağılımı**")
            fig3 = px.histogram(df, x="temperature", nbins=20,
                                color_discrete_sequence=["#EF553B"])
            fig3.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig3, use_container_width=True)
        with col_b:
            st.markdown("**Özet İstatistikler**")
            summary = df[["temperature","humidity","pressure","co2_ppm"]].describe().round(2)
            st.dataframe(summary, use_container_width=True)

    # ─── Ham veri tablosu ──────────────────────────────────────────────────
    with st.expander("Ham Veri (son 20 kayıt)"):
        display_cols = ["datetime","device_id","temperature","humidity","pressure","co2_ppm"]
        available    = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available].tail(20), use_container_width=True)

# ─── Otomatik yenileme ─────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
