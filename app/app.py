import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

# ---------------------------------
# CONFIG
# ---------------------------------

UPLOAD_DIR = Path("uploads/productos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------
# DB CONNECTION
# ---------------------------------

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cur = conn.cursor()

# ---------------------------------
# TABLE
# ---------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS inventario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    precio NUMERIC(10,2),
    estado VARCHAR(20),
    imagen TEXT
)
""")

conn.commit()

# ---------------------------------
# SAFE IMAGE HANDLER
# ---------------------------------

def mostrar_imagen_segura(ruta):
    if not ruta:
        return False
    if str(ruta).lower() == "none":
        return False
    path = Path(ruta)
    if not path.exists():
        return False
    st.image(str(path), width=250)
    return True

# ---------------------------------
# UI
# ---------------------------------

st.set_page_config(page_title="Inventario Cloud", layout="wide")
st.title("☁️ Plataforma Cloud de Inventario Inteligente")
st.caption("Caso real de transformación digital con arquitectura escalable")

tab1, tab2, tab3 = st.tabs([
    "📦 Registro",
    "📊 Inventario",
    "🖼️ Evidencias"
])

# =================================
# REGISTRO
# =================================

with tab1:
    with st.form("form_registro"):
        nombre = st.text_input("Producto")
        precio = st.number_input("Precio", min_value=0.0)
        estado = st.selectbox("Estado", ["Disponible", "Agotado"])
        imagen = st.file_uploader("Imagen (opcional)", type=["png", "jpg", "jpeg"])
        guardar = st.form_submit_button("Guardar")

        if guardar:
            ruta = None
            if imagen:
                ruta = UPLOAD_DIR / imagen.name
                with open(ruta, "wb") as f:
                    f.write(imagen.getbuffer())

            cur.execute(
                """
                INSERT INTO inventario (nombre, precio, estado, imagen)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre, precio, estado, str(ruta) if ruta else None)
            )
            conn.commit()
            st.success("Producto registrado correctamente")

# =================================
# INVENTARIO
# =================================

with tab2:
    df = pd.read_sql(
        "SELECT id, nombre, precio, estado FROM inventario ORDER BY id",
        conn
    )
    st.dataframe(df, use_container_width=True)

# =================================
# EVIDENCIAS
# =================================

with tab3:
    cur.execute("SELECT nombre, imagen FROM inventario")
    rows = cur.fetchall()

    for nombre, imagen in rows:
        st.markdown(f"**{nombre}**")
        if not mostrar_imagen_segura(imagen):
            st.info("Sin evidencia visual")
