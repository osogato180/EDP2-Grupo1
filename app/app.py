import streamlit as st
import json
import os
import redis
import pika
import smtplib
from email.mime.text import MIMEText

# ===============================
# CONFIGURACIÓN
# ===============================
DATA_FILE = "data/productos.json"
STOCK_MINIMO = 5

REDIS_HOST = "redis"
REDIS_PORT = 6379

RABBIT_HOST = "rabbitmq"
QUEUE_NAME = "stock_alerts"

MAILHOG_HOST = "mailhog"
MAILHOG_PORT = 1025

# ===============================
# REDIS
# ===============================
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ===============================
# UTILIDADES
# ===============================
def cargar_productos():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def guardar_productos(productos):
    with open(DATA_FILE, "w") as f:
        json.dump(productos, f, indent=4)

def generar_id(productos):
    if not productos:
        return "CODINV01"
    ultimo = max(int(p["id"].replace("CODINV", "")) for p in productos)
    return f"CODINV{str(ultimo + 1).zfill(2)}"

def cachear_productos(productos):
    redis_client.set("productos", json.dumps(productos))

def obtener_productos_cache():
    data = redis_client.get("productos")
    return json.loads(data) if data else None

# ===============================
# RABBIT + MAIL
# ===============================
def enviar_alerta_stock(producto):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)

    mensaje = f"⚠️ Stock bajo\nProducto: {producto['nombre']}\nStock: {producto['stock']}"
    channel.basic_publish(exchange="", routing_key=QUEUE_NAME, body=mensaje)
    connection.close()

    enviar_correo(mensaje)

def enviar_correo(mensaje):
    msg = MIMEText(mensaje)
    msg["Subject"] = "Alerta de Stock Bajo"
    msg["From"] = "inventario@sistema.com"
    msg["To"] = "admin@sistema.com"

    with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT) as server:
        server.send_message(msg)

# ===============================
# STREAMLIT
# ===============================
st.set_page_config(page_title="Inventario", layout="wide")
st.title("📦 Sistema de Inventario")

# ===============================
# CARGA DE DATOS
# ===============================
productos = obtener_productos_cache()
if productos is None:
    productos = cargar_productos()
    cachear_productos(productos)

# ===============================
# AGREGAR PRODUCTO
# ===============================
st.header("➕ Agregar producto")

with st.form("form_agregar"):
    nombre = st.text_input("Nombre")
    stock = st.number_input("Stock", min_value=0)
    precio = st.number_input("Precio", min_value=0.0)
    submit = st.form_submit_button("Agregar")

    if submit:
        nuevo = {
            "id": generar_id(productos),
            "nombre": nombre,
            "stock": stock,
            "precio": precio
        }
        productos.append(nuevo)
        guardar_productos(productos)
        cachear_productos(productos)

        if stock <= STOCK_MINIMO:
            enviar_alerta_stock(nuevo)

        st.success("Producto agregado correctamente")
        st.rerun()

# ===============================
# BUSCAR PRODUCTO
# ===============================
st.header("🔍 Buscar producto")
busqueda = st.text_input("Buscar por nombre o ID")

productos_filtrados = [
    p for p in productos
    if busqueda.lower() in p["nombre"].lower()
    or busqueda.lower() in p["id"].lower()
]

# ===============================
# EDITAR / ELIMINAR
# ===============================
st.header("✏️ Editar / 🗑 Eliminar producto")

ids = [p["id"] for p in productos]
producto_id = st.selectbox("Selecciona un producto (CODINV)", ids)

producto = next(p for p in productos if p["id"] == producto_id)

nuevo_nombre = st.text_input("Nombre", producto["nombre"])
nuevo_stock = st.number_input("Stock", min_value=0, value=producto["stock"])
nuevo_precio = st.number_input("Precio", min_value=0.0, value=producto["precio"])

col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Guardar cambios", key="editar"):
        producto["nombre"] = nuevo_nombre
        producto["stock"] = nuevo_stock
        producto["precio"] = nuevo_precio

        guardar_productos(productos)
        cachear_productos(productos)

        if nuevo_stock <= STOCK_MINIMO:
            enviar_alerta_stock(producto)

        st.success("Producto actualizado")
        st.rerun()

with col2:
    if st.button("🗑 Eliminar producto", key="eliminar"):
        productos.remove(producto)
        guardar_productos(productos)
        cachear_productos(productos)
        st.warning("Producto eliminado")
        st.rerun()

# ===============================
# TABLA DE PRODUCTOS
# ===============================
st.header("📋 Lista de productos")
st.dataframe(productos_filtrados)