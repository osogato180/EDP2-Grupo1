import streamlit as st

# =========================
# CONFIGURACIÓN
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

if "contador_id" not in st.session_state:
    st.session_state.contador_id = 1

productos = st.session_state.productos

# =========================
# FUNCIÓN ID AUTOMÁTICO
# =========================
def generar_id():
    cod = f"CODINV{st.session_state.contador_id:02d}"
    st.session_state.contador_id += 1
    return cod

# =========================
# AGREGAR PRODUCTO
# =========================
st.header("➕ Agregar producto")

with st.form("form_agregar", clear_on_submit=True):
    nombre = st.text_input("Nombre del producto")
    stock = st.number_input("Stock disponible", min_value=0, step=1)

    submitted = st.form_submit_button("Guardar producto")

    if submitted:
        if nombre.strip() == "":
            st.warning("⚠️ El nombre no puede estar vacío")
        else:
            productos.append({
                "id": generar_id(),
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
        if buscar.lower() in p["id"].lower()
        or buscar.lower() in p["nombre"].lower()
    ]

    if resultados:
        for p in resultados:
            st.info(f"ID: {p['id']} | {p['nombre']} | Stock: {p['stock']}")
    else:
        st.warning("❌ Producto no encontrado")

# =========================
# EDITAR PRODUCTO
# =========================
st.header("✏️ Editar producto")

ids = [p["id"] for p in productos]

if not ids:
    st.info("No hay productos para editar")
else:
    id_seleccionado = st.selectbox("Selecciona el ID del producto", ids)

    producto = next(p for p in productos if p["id"] == id_seleccionado)

    with st.form("form_editar"):
        nuevo_nombre = st.text_input("Nuevo nombre", value=producto["nombre"])
        nuevo_stock = st.number_input(
            "Nuevo stock",
            min_value=0,
            step=1,
            value=producto["stock"]
        )

        editar = st.form_submit_button("Actualizar producto")

        if editar:
            producto["nombre"] = nuevo_nombre
            producto["stock"] = nuevo_stock
            st.success("✏️ Producto actualizado correctamente")
            st.rerun()

# =========================
# LISTAR Y ELIMINAR
# =========================
st.header("🗑️ Productos registrados")

if not productos:
    st.info("No hay productos registrados")
else:
    for i, p in enumerate(productos):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(f"📦 **{p['id']}** | {p['nombre']} | Stock: {p['stock']}")

        with col2:
            if st.button("Eliminar", key=f"del_{p['id']}"):
                productos.pop(i)
                st.success("🗑️ Producto eliminado")
                st.rerun()

# =========================
# MÉTRICAS
# =========================
st.header("📊 Resumen")

st.metric("Total de productos", len(productos))