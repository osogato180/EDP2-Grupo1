import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

# ---------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------

UPLOAD_DIR = Path("uploads/productos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------
# CONEXIÓN A POSTGRESQL
# ---------------------------------

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cur = conn.cursor()

# ---------------------------------
# TABLA INVENTARIO
# ---------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS inventario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    precio NUMERIC(10,2),
    estado VARCHAR(20),
    imagen VARCHAR(255)
)
""")

conn.commit()

# ---------------------------------
# INTERFAZ STREAMLIT
# ---------------------------------

st.set_page_config(
    page_title="Inventario Cloud",
    layout="wide"
)

st.title("☁️ Sistema Cloud de Inventario Digital")
st.caption("Plataforma de transformación digital para negocios pequeños")

tab1, tab2, tab3 = st.tabs(
    ["📦 Registrar producto", "📊 Inventario", "🖼️ Evidencias"]
)

# =================================
# REGISTRAR PRODUCTO
# =================================

with tab1:
    st.subheader("Registro de nuevo producto")

    with st.form("form_producto"):
        nombre = st.text_input("Nombre del producto")
        precio = st.number_input("Precio", min_value=0.0)
        estado = st.selectbox(
            "Estado",
            ["Disponible", "Agotado"]
        )
        imagen = st.file_uploader(
            "Imagen del producto (opcional)",
            type=["jpg", "png", "jpeg"]
        )

        guardar = st.form_submit_button("Registrar producto")

        if guardar:
            ruta_imagen = None

            if imagen:
                ruta_imagen = UPLOAD_DIR / imagen.name
                with open(ruta_imagen, "wb") as f:
                    f.write(imagen.getbuffer())

            cur.execute(
                """
                INSERT INTO inventario
                (nombre, precio, estado, imagen)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre, precio, estado, str(ruta_imagen))
            )
            conn.commit()

            st.success("Producto registrado en la nube")

# =================================
# INVENTARIO
# =================================

with tab2:
    st.subheader("Inventario digital")

    filtro = st.selectbox(
        "Filtrar por estado",
        ["Todos", "Disponible", "Agotado"]
    )

    if filtro == "Todos":
        df = pd.read_sql(
            "SELECT id, nombre, precio, estado FROM inventario",
            conn
        )
    else:
        df = pd.read_sql(
            "SELECT id, nombre, precio, estado FROM inventario WHERE estado = %s",
            conn,
            params=(filtro,)
        )

    st.dataframe(df, use_container_width=True)

# =================================
# EVIDENCIAS VISUALES
# =================================

with tab3:
    st.subheader("Evidencias visuales de productos")

    cur.execute(
        "SELECT nombre, imagen FROM inventario WHERE imagen IS NOT NULL"
    )

    registros = cur.fetchall()

    if registros:
        for nombre, imagen in registros:
            st.markdown(f"**{nombre}**")
            st.image(imagen, width=250)
    else:
        st.info("No hay imágenes registradas")
