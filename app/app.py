import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# PostgreSQL connection
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    precio NUMERIC(10,2)
)
""")

conn.commit()

st.set_page_config(page_title="CRUD Demo", layout="wide")

st.title("🐳 Streamlit + PostgreSQL CRUD")

tab1, tab2 = st.tabs(["CRUD Productos", "Subir Archivos"])

with tab1:
    st.header("➕ Crear producto")

    with st.form("crear_producto"):
        nombre = st.text_input("Nombre")
        precio = st.number_input("Precio", min_value=0.0)
        submitted = st.form_submit_button("Guardar")

        if submitted:
            cur.execute(
                "INSERT INTO productos (nombre, precio) VALUES (%s, %s)",
                (nombre, precio)
            )
            conn.commit()
            st.success("Producto creado")

    st.divider()

    st.header("📋 Lista de productos")

    df = pd.read_sql("SELECT * FROM productos ORDER BY id", conn)
    st.dataframe(df, use_container_width=True)

    st.divider()

    st.header("✏️ Actualizar producto")

    product_id = st.number_input("ID producto", min_value=1, step=1)
    nuevo_nombre = st.text_input("Nuevo nombre")
    nuevo_precio = st.number_input("Nuevo precio", min_value=0.0)

    if st.button("Actualizar"):
        cur.execute(
            """
            UPDATE productos
            SET nombre=%s, precio=%s
            WHERE id=%s
            """,
            (nuevo_nombre, nuevo_precio, product_id)
        )
        conn.commit()
        st.success("Producto actualizado")

    st.divider()

    st.header("🗑️ Eliminar producto")

    delete_id = st.number_input("ID a eliminar", min_value=1, step=1)

    if st.button("Eliminar"):
        cur.execute(
            "DELETE FROM productos WHERE id=%s",
            (delete_id,)
        )
        conn.commit()
        st.warning("Producto eliminado")

with tab2:
    st.header("📂 Subida de archivos")

    uploaded_file = st.file_uploader("Selecciona un archivo")

    if uploaded_file is not None:
        file_path = UPLOAD_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Archivo guardado en {file_path}")
        st.write(os.listdir(UPLOAD_DIR))
