import os
import json
import psycopg2
import redis
import streamlit as st

# =========================
# CONFIG STREAMLIT
# =========================
st.set_page_config(
    page_title="Inventario Cloud",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Sistema de Inventario en la Nube")

# =========================
# CONEXIONES
# =========================
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

# =========================
# TABLA
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id VARCHAR(20) PRIMARY KEY,
    nombre VARCHAR(100),
    stock INTEGER
)
""")
conn.commit()

# =========================
# FUNCIONES
# =========================
def generar_id():
    cursor.execute("SELECT COUNT(*) FROM productos")
    total = cursor.fetchone()[0] + 1
    return f"CODINV{total:02d}"

def limpiar_cache():
    redis_client.delete("productos")

def obtener_productos():
    cache = redis_client.get("productos")
    if cache:
        return json.loads(cache)

    cursor.execute("SELECT * FROM productos ORDER BY id")
    data = cursor.fetchall()
    redis_client.set("productos", json.dumps(data), ex=60)
    return data

# =========================
# AGREGAR PRODUCTO
# =========================
st.header("➕ Agregar producto")

with st.form("form_agregar", clear_on_submit=True):
    nombre = st.text_input("Nombre del producto")
    stock = st.number_input("Stock", min_value=0, step=1)
    guardar = st.form_submit_button("Guardar")

    if guardar:
        if nombre.strip() == "":
            st.warning("⚠️ El nombre es obligatorio")
        else:
            cursor.execute(
                "INSERT INTO productos VALUES (%s, %s, %s)",
                (generar_id(), nombre, stock)
            )
            conn.commit()
            limpiar_cache()
            st.success("✅ Producto agregado")
            st.rerun()

# =========================
# BUSCAR
# =========================
st.header("🔍 Buscar producto")

buscar = st.text_input("Buscar por ID o nombre")
productos = obtener_productos()

if buscar:
    productos = [
        p for p in productos
        if buscar.lower() in p[0].lower()
        or buscar.lower() in p[1].lower()
    ]

# =========================
# EDITAR / ELIMINAR
# =========================
st.header("✏️ Editar / 🗑️ Eliminar producto")

if productos:
    ids = [p[0] for p in productos]
    id_sel = st.selectbox("Selecciona el producto (CODINV)", ids)

    producto = next(p for p in productos if p[0] == id_sel)

    nuevo_nombre = st.text_input("Nombre", value=producto[1])
    nuevo_stock = st.number_input("Stock", min_value=0, value=producto[2])

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Actualizar"):
            cursor.execute("""
                UPDATE productos
                SET nombre=%s, stock=%s
                WHERE id=%s
            """, (nuevo_nombre, nuevo_stock, id_sel))
            conn.commit()
            limpiar_cache()
            st.success("✏️ Producto actualizado")
            st.rerun()

    with col2:
        if st.button("Eliminar"):
            cursor.execute("DELETE FROM productos WHERE id=%s", (id_sel,))
            conn.commit()
            limpiar_cache()
            st.warning("🗑️ Producto eliminado")
            st.rerun()
else:
    st.info("No hay productos registrados")

# =========================
# LISTADO
# =========================
st.header("📋 Productos registrados")

for p in productos:
    st.write(f"📦 **{p[0]}** | {p[1]} | Stock: {p[2]}")

# =========================
# MÉTRICAS
# =========================
st.header("📊 Resumen")
st.metric("Total de productos", len(productos))