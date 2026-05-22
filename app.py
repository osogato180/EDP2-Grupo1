import os
import psycopg2
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
# CONEXIÓN BD
# =========================
conn = psycopg2.connect(
    host=os.environ.get("DB_HOST"),
    database=os.environ.get("DB_NAME"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD")
)
cursor = conn.cursor()

# =========================
# CREAR TABLA SI NO EXISTE
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
# GENERAR ID AUTOMÁTICO
# =========================
def generar_id():
    cursor.execute("SELECT COUNT(*) FROM productos")
    count = cursor.fetchone()[0] + 1
    return f"CODINV{count:02d}"

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
            st.success("✅ Producto guardado")
            st.rerun()

# =========================
# BUSCAR PRODUCTO
# =========================
st.header("🔍 Buscar producto")

buscar = st.text_input("Buscar por ID o nombre")

cursor.execute("SELECT * FROM productos")
productos = cursor.fetchall()

if buscar:
    encontrados = [
        p for p in productos
        if buscar.lower() in p[0].lower()
        or buscar.lower() in p[1].lower()
    ]

    if encontrados:
        for p in encontrados:
            st.info(f"{p[0]} | {p[1]} | Stock: {p[2]}")
    else:
        st.warning("❌ No encontrado")

# =========================
# EDITAR PRODUCTO
# =========================
st.header("✏️ Editar producto")

ids = [p[0] for p in productos]

if ids:
    id_sel = st.selectbox("Selecciona ID", ids)

    cursor.execute("SELECT * FROM productos WHERE id=%s", (id_sel,))
    prod = cursor.fetchone()

    with st.form("form_editar"):
        nuevo_nombre = st.text_input("Nombre", value=prod[1])
        nuevo_stock = st.number_input("Stock", min_value=0, value=prod[2])

        actualizar = st.form_submit_button("Actualizar")

        if actualizar:
            cursor.execute("""
                UPDATE productos
                SET nombre=%s, stock=%s
                WHERE id=%s
            """, (nuevo_nombre, nuevo_stock, id_sel))
            conn.commit()
            st.success("✏️ Producto actualizado")
            st.rerun()
else:
    st.info("No hay productos")

# =========================
# LISTAR Y ELIMINAR
# =========================
st.header("🗑️ Productos registrados")

for p in productos:
    col1, col2 = st.columns([4, 1])

    with col1:
        st.write(f"📦 **{p[0]}** | {p[1]} | Stock: {p[2]}")

    with col2:
        if st.button("Eliminar", key=p[0]):
            cursor.execute("DELETE FROM productos WHERE id=%s", (p[0],))
            conn.commit()
            st.success("🗑️ Eliminado")
            st.rerun()

# =========================
# MÉTRICAS
# =========================
st.header("📊 Resumen")
st.metric("Total productos", len(productos))