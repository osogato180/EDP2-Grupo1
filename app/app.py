import streamlit as st
import json
import os
import redis
import pika
import smtplib
from email.mime.text import MIMEText
from prometheus_client import Counter, Gauge, start_http_server

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
# PROMETHEUS (SEGURO PARA STREAMLIT)
# ===============================
from prometheus_client import Counter, Gauge, start_http_server, REGISTRY

def get_or_create_counter(name, description):
    try:
        return Counter(name, description)
    except ValueError:
        return REGISTRY._names_to_collectors[name]

def get_or_create_gauge(name, description):
    try:
        return Gauge(name, description)
    except ValueError:
        return REGISTRY._names_to_collectors[name]

# Iniciar servidor una sola vez
try:
    start_http_server(8001)
except OSError:
    pass

productos_creados = get_or_create_counter(
    "productos_creados_total",
    "Cantidad total de productos creados"
)

productos_editados = get_or_create_counter(
    "productos_editados_total",
    "Cantidad total de productos editados"
)

productos_eliminados = get_or_create_counter(
    "productos_eliminados_total",
    "Cantidad total de productos eliminados"
)

stock_bajo = get_or_create_gauge(
    "productos_stock_bajo",
    "Cantidad de productos con stock bajo"
)

# ===============================
# REDIS
# ===============================
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

# ===============================
# UTILIDADES
# ===============================
def cargar_productos():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                return []
            return json.loads(contenido)
    except json.JSONDecodeError:
        return []

def guardar_productos(productos):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=4, ensure_ascii=False)

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

def actualizar_metrica_stock(productos):
    stock_bajo.set(len([p for p in productos if p["stock"] <= STOCK_MINIMO]))

# ===============================
# RABBITMQ + MAILHOG
# ===============================
def enviar_alerta_stock(producto):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBIT_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME)

        mensaje = (
            f"⚠️ STOCK BAJO\n"
            f"ID: {producto['id']}\n"
            f"Producto: {producto['nombre']}\n"
            f"Stock: {producto['stock']}"
        )

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=mensaje
        )
        connection.close()
        enviar_correo(mensaje)
    except Exception:
        pass

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
st.set_page_config(
    page_title="Sistema de Inventario",
    layout="wide"
)

st.title("📦 Sistema de Inventario en la Nube")

# ===============================
# CARGA DE DATOS
# ===============================
productos = obtener_productos_cache()
if productos is None:
    productos = cargar_productos()
    cachear_productos(productos)

actualizar_metrica_stock(productos)

# ===============================
# AGREGAR PRODUCTO
# ===============================
st.header("➕ Agregar producto")

with st.form("form_agregar", clear_on_submit=True):
    nombre = st.text_input("Nombre", key="nombre_nuevo")
    stock = st.number_input("Stock", min_value=0, key="stock_nuevo")
    precio = st.number_input("Precio", min_value=0.0, key="precio_nuevo")
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

        productos_creados.inc()

        if stock <= STOCK_MINIMO:
            enviar_alerta_stock(nuevo)

        st.success("Producto agregado correctamente")
        st.rerun()

# ===============================
# BUSCAR PRODUCTO
# ===============================
st.header("🔍 Buscar producto")

busqueda = st.text_input("Buscar por ID o nombre")

productos_filtrados = [
    p for p in productos
    if busqueda.lower() in p["id"].lower()
    or busqueda.lower() in p["nombre"].lower()
]

# ===============================
# EDITAR / ELIMINAR
# ===============================
st.header("✏️ Editar / 🗑 Eliminar producto")

if productos:
    ids = [p["id"] for p in productos]
    producto_id = st.selectbox("Selecciona un producto (CODINV)", ids)

    producto = next(p for p in productos if p["id"] == producto_id)

    nuevo_nombre = st.text_input("Nombre", producto["nombre"])
    nuevo_stock = st.number_input(
        "Stock", min_value=0, value=producto["stock"], step=1
    )
    nuevo_precio = st.number_input(
        "Precio", min_value=0.0, value=producto["precio"], step=0.1
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Guardar cambios", key="editar"):
            producto["nombre"] = nuevo_nombre
            producto["stock"] = nuevo_stock
            producto["precio"] = nuevo_precio

            guardar_productos(productos)
            cachear_productos(productos)

            productos_editados.inc()
            actualizar_metrica_stock(productos)

            if nuevo_stock <= STOCK_MINIMO:
                enviar_alerta_stock(producto)

            st.success("✏️ Producto actualizado")
            st.rerun()

    with col2:
        if st.button("🗑 Eliminar producto", key="eliminar"):
            productos.remove(producto)
            guardar_productos(productos)
            cachear_productos(productos)

            productos_eliminados.inc()
            actualizar_metrica_stock(productos)

            st.warning("🗑 Producto eliminado")
            st.rerun()
else:
    st.info("No hay productos registrados")

# ===============================
# TABLA
# ===============================
st.header("📋 Lista de productos")
st.dataframe(productos_filtrados)