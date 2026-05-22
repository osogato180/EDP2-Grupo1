import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import psycopg2
import pika
import streamlit as st
from prometheus_client import Counter, Gauge, start_http_server

# ==========================
# CONFIG
# ==========================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Prometheus
from prometheus_client import Counter, Gauge, start_http_server
import streamlit as st

# Iniciar Prometheus solo una vez
if "prometheus_started" not in st.session_state:
    start_http_server(8000)
    st.session_state.prometheus_started = True

# Crear métricas SOLO una vez
if "metricas_iniciadas" not in st.session_state:
    st.session_state.productos_creados = Counter(
        "productos_creados", "Productos creados"
    )
    st.session_state.stock_critico = Gauge(
        "stock_critico", "Productos con stock bajo"
    )
    st.session_state.metricas_iniciadas = True

# Referencias
productos_creados = st.session_state.productos_creados
stock_critico = st.session_state.stock_critico

# DB
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

# RabbitMQ
rabbit_conn = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq")
)
channel = rabbit_conn.channel()
channel.queue_declare(queue="alertas_stock")

# ==========================
# TABLE
# ==========================

cur.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    stock INT,
    stock_min INT,
    imagen VARCHAR(200)
)
""")
conn.commit()

# ==========================
# UI
# ==========================

st.set_page_config(page_title="Sistema Inteligente de Inventario", layout="wide")
st.title("📦 Sistema Inteligente de Inventario Cloud")

# ==========================
# FORM CREAR
# ==========================

st.header("➕ Registrar producto")

with st.form("crear_producto", clear_on_submit=True):
    nombre = st.text_input("Nombre del producto")
    stock = st.number_input("Stock actual", min_value=0)
    stock_min = st.number_input("Stock mínimo", min_value=0)
    imagen_file = st.file_uploader("Imagen (opcional)", type=["png", "jpg", "jpeg"])

    submit = st.form_submit_button("Guardar")

    if submit:
        imagen_path = None

        if imagen_file:
            imagen_path = UPLOAD_DIR / imagen_file.name
            with open(imagen_path, "wb") as f:
                f.write(imagen_file.getbuffer())

        cur.execute(
            "INSERT INTO productos (nombre, stock, stock_min, imagen) VALUES (%s,%s,%s,%s)",
            (nombre, stock, stock_min, str(imagen_path) if imagen_path else None)
        )
        conn.commit()
        productos_creados.inc()

        if stock <= stock_min:
            stock_critico.inc()
            channel.basic_publish(
                exchange="",
                routing_key="alertas_stock",
                body=f"Stock bajo para {nombre}"
            )

        st.success("Producto registrado correctamente")

# ==========================
# LISTA
# ==========================

st.divider()
st.header("📋 Productos registrados")

df = pd.read_sql("SELECT * FROM productos ORDER BY id", conn)

if not df.empty:
    for _, row in df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.write(f"**{row['nombre']}**")
            st.write(f"Stock: {row['stock']} | Mín: {row['stock_min']}")

        with col2:
            if row["imagen"]:
                st.image(row["imagen"], width=150)

        with col3:
            if st.button("Eliminar producto"):
                productos.pop(index)
                st.success("Producto eliminado correctamente")
                st.rerun()
else:
    st.info("No hay productos registrados")