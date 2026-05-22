import streamlit as st

# =========================
# CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(
    page_title="Gestión de Inventario",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Sistema de Gestión de Inventario")

# =========================
# ESTADO GLOBAL
# =========================
if "productos" not in st.session_state:
    st.session_state.productos = []

productos = st.session_state.productos

# =========================
# AGREGAR PRODUCTO
# =========================
st.header("➕ Agregar producto")

with st.form("form_producto"):
    pid = st.number_input("ID del producto", min_value=1, step=1)
    nombre = st.text_input("Nombre del producto")
    stock = st.number_input("Stock disponible", min_value=0, step=1)

    submitted = st.form_submit_button("Guardar producto")

    if submitted:
        productos.append({
            "id": pid,
            "nombre": nombre,
            "stock": stock
        })
        st.success("✅ Producto agregado correctamente")
        st.rerun()

# =========================
# BUSCAR PRODUCTO
# =========================
st.header("🔍 Buscar producto")

buscar = st.text_input("Buscar por ID o nombre")

if buscar:
    resultados = [
        p for p in productos
        if buscar.lower() in str(p["id"]).lower()
        or buscar.lower() in p["nombre"].lower()
    ]

    if resultados:
        for p in resultados:
            st.info(f"ID: {p['id']} | {p['nombre']} | Stock: {p['stock']}")
    else:
        st.warning("❌ Producto no encontrado")

# =========================
# LISTAR Y ELIMINAR PRODUCTOS
# =========================
st.header("🗑️ Productos registrados")

if not productos:
    st.info("No hay productos registrados")
else:
    for i, p in enumerate(productos):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(f"📦 ID: {p['id']} | {p['nombre']} | Stock: {p['stock']}")

        with col2:
            if st.button("Eliminar", key=f"eliminar_{p['id']}"):
                productos.pop(i)
                st.success("🗑️ Producto eliminado")
                st.rerun()

# =========================
# MÉTRICAS
# =========================
st.header("📊 Resumen")

st.metric("Total de productos", len(productos))