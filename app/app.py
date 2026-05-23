import streamlit as st
import json
import os
import redis
from prometheus_client import Counter, Gauge, start_http_server, REGISTRY

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
DATA_FILE = "data/productos.json"
STOCK_MINIMO = 5

REDIS_HOST = "redis"
REDIS_PORT = 6379

PROMETHEUS_PORT = 8000

# ===============================
# PROMETHEUS (ANTI DUPLICADOS)
# ===============================
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

# Iniciar servidor Prometheus solo una vez
try:
    start_http_server(PROMETHEUS_PORT)
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

productos_stock_bajo = get_or_create_gauge(
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
            return json.loads(contenido) if contenido else []
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
    redis_client.set("productos", json.dumps(productos), ex=3600)

def obtener_productos_cache():
    data = redis_client.get("productos")
    return json.loads(data) if data else None

def actualizar_metrica_stock(productos):
    productos_stock_bajo.set(
        len([p for p in productos if p["stock"] <= STOCK_MINIMO])
    )

# ===============================
# STREAMLIT
# ===============================
st.set_page_config(
    page_title="Sistema de Inventario",
    layout="wide"
)

st.title("📦 Sistema de Inventario – Tiendita de Don Pepe")

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
    nombre = st.text_input("Nombre")
    stock = st.number_input("Stock", min_value=0, step=1)
    precio = st.number_input("Precio", min_value=0.0, step=0.1)
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
        actualizar_metrica_stock(productos)

        st.success("✅ Producto agregado correctamente")
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
    producto_id = st.selectbox("Selecciona un producto", ids)

    producto = next(p for p in productos if p["id"] == producto_id)

    nuevo_nombre = st.text_input("Nombre", producto["nombre"])
    nuevo_stock = st.number_input("Stock", min_value=0, value=producto["stock"], step=1)
    nuevo_precio = st.number_input("Precio", min_value=0.0, value=producto["precio"], step=0.1)

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

# ===============================
# ANÁLISIS DE INVENTARIO
# ===============================
st.header("📊 Análisis de Inventario")

# -------- KPIs --------
col1, col2, col3, col4 = st.columns(4)

total_productos = len(productos)
stock_total = sum(p["stock"] for p in productos)
precio_promedio = (
    sum(p["precio"] for p in productos) / total_productos
    if total_productos > 0 else 0
)
productos_stock_bajo = len([p for p in productos if p["stock"] <= STOCK_MINIMO])

col1.metric("📦 Total productos", total_productos)
col2.metric("📉 Stock total", stock_total)
col3.metric("⚠️ Stock bajo", productos_stock_bajo)
col4.metric("💰 Precio promedio", f"S/. {precio_promedio:.2f}")

# -------- Tablas y gráficos --------
st.subheader("⚠️ Productos con stock bajo")
bajo_stock = [p for p in productos if p["stock"] <= STOCK_MINIMO]

if bajo_stock:
    st.table(bajo_stock)
else:
    st.success("No hay productos con stock bajo")

st.subheader("📈 Productos con mayor stock")
top_stock = sorted(productos, key=lambda x: x["stock"], reverse=True)[:5]
if top_stock:
    st.bar_chart({p["nombre"]: p["stock"] for p in top_stock})

st.subheader("💎 Productos más caros")
top_precio = sorted(productos, key=lambda x: x["precio"], reverse=True)[:5]
if top_precio:
    st.bar_chart({p["nombre"]: p["precio"] for p in top_precio})

# -------- Grafana embebido --------
st.subheader("📡 Monitoreo avanzado (Grafana)")

st.components.v1.iframe(
    "http://localhost:3000/goto/cfmw88m76begwf?orgId=1",
    height=400
)

st.components.v1.iframe(
    "http://localhost:3000/goto/cfmw88m76begwf?orgId=2",
    height=400
)