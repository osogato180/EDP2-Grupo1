import os
import psycopg2
import redis
import streamlit as st
import json

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Inventario Cloud", page_icon="📦")

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
# UTILIDADES
# =========================
def generar_id():
    cursor.execute("SELECT COUNT(*) FROM productos")
    return f"CODINV{cursor.fetchone()[0] + 1:02d}"

def limpiar_cache():
    redis_client.delete("productos")

def obtener_productos():
    cache = redis_client.get("productos")
    if cache:
        return json.loads(cache)

    cursor.execute("SELECT * FROM productos ORDER BY id")
    productos = cursor.fetchall()

    redis_client.set("productos", json.dumps(productos), ex=30)
    return productos

# =========================
# UI
# =========================
st.title("📦 Sistema de Inventario Cloud")

# =========================
# AGREGAR
# =========================
st.header("➕ Agregar producto")

with st.form("agregar", clear_on_submit=True):
    nombre = st.text_input("Nombre")
    stock = st.number_input("Stock", min_value=0, step=1)
    enviar = st.form_submit_button("Guardar")

    if enviar and nombre:
        cursor.execute(
            "INSERT INTO productos VALUES (%s, %s, %s)",
            (generar_id(), nombre, stock)
        )
        conn.commit()
        limpiar_cache()
        st.success("Producto agregado")
        st.rerun()

# =========================
# BUSCAR
# =========================
st.header("🔍 Buscar producto")

buscar = st.text_input("Buscar por nombre o ID")
productos = obtener_productos()

if buscar:
    encontrados = [
        p for p in productos
        if buscar.lower() in p[0].lower()
        or buscar.lower() in p[1].lower()
    ]
else:
    encontrados = productos

# =========================
# LISTAR / EDITAR / ELIMINAR
# =========================
for p in encontrados:
    col1, col2, col3 = st.columns([4, 2, 1])

    with col1:
        st.write(f"📦 {p[0]} | {p[1]} | Stock: {p[2]}")

    with col2:
        nuevo_stock = st.number_input(
            "Stock",
            min_value=0,
            value=p[2],
            key=f"stock_{p[0]}"
        )

        if st.button("Actualizar", key=f"edit_{p[0]}"):
            cursor.execute(
                "UPDATE productos SET stock=%s WHERE id=%s",
                (nuevo_stock, p[0])
            )
            conn.commit()
            limpiar_cache()
            st.success("Actualizado")
            st.rerun()

    with col3:
        if st.button("Eliminar", key=f"del_{p[0]}"):
            cursor.execute("DELETE FROM productos WHERE id=%s", (p[0],))
            conn.commit()
            limpiar_cache()
            st.warning("Eliminado")
            st.rerun()

# =========================
# MÉTRICAS
# =========================
st.header("📊 Métricas")
st.metric("Productos totales", len(productos))