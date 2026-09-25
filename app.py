import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Inventario - Abarrotes",
    page_icon="📦",
    layout="wide"
)

# ---------------------------------------------------------
# CONEXIÓN CON GOOGLE SHEETS
# ---------------------------------------------------------
# Inicializa la conexión usando el bloque [gsheets] de Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_inventario():
    """Lee la hoja de inventario desde Google Sheets sin cachear para datos frescos."""
    try:
        df = conn.read(worksheet="inventario", ttl=0)
        return df
    except Exception as e:
        st.error(f"Error al cargar el inventario: {e}")
        return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Categoria"])

def guardar_inventario(df_inv):
    """Guarda el DataFrame actualizado en la pestaña 'inventario'."""
    try:
        conn.update(worksheet="inventario", data=df_inv)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar los datos: {e}")
        return False

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL DE LA APLICACIÓN
# ---------------------------------------------------------
st.title("📦 Gestión de Inventario y Productos")

# Cargar los datos actuales
df_inventario = cargar_inventario()

# Pestañas para las operaciones del sistema
tab_ver, tab_agregar, tab_editar = st.tabs(["📋 Ver Inventario", "➕ Agregar Producto", "⚙️ Modificar / Eliminar"])

# 1. VISUALIZAR INVENTARIO
with tab_ver:
    st.subheader("Productos Registrados")
    if not df_inventario.empty:
        st.dataframe(df_inventario, use_container_width=True)
    else:
        st.info("No hay productos registrados o no se pudo cargar la tabla.")

# 2. AGREGAR PRODUCTO
with tab_agregar:
    st.subheader("Registrar Nuevo Producto")
    with st.form("form_nuevo_producto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_id = st.text_input("Código / ID del Producto")
            nuevo_nombre = st.text_input("Nombre del Producto")
            nueva_categoria = st.text_input("Categoría", value="General")
        with col2:
            nuevo_precio = st.number_input("Precio ($)", min_value=0.0, step=50.0)
            nuevo_stock = st.number_input("Cantidad en Stock", min_value=0, step=1)

        guardar_btn = st.form_submit_button("Guardar Producto")

        if guardar_btn:
            if nuevo_id and nuevo_nombre:
                nuevo_registro = pd.DataFrame([{
                    "ID": nuevo_id,
                    "Producto": nuevo_nombre,
                    "Precio": nuevo_precio,
                    "Stock": nuevo_stock,
                    "Categoria": nueva_categoria
                }])
                
                # Concatenar el nuevo registro al DataFrame existente
                df_actualizado = pd.concat([df_inventario, nuevo_registro], ignore_index=True)
                
                if guardar_inventario(df_actualizado):
                    st.success(f"¡Producto '{nuevo_nombre}' agregado correctamente!")
                    st.rerun()
            else:
                st.warning("Por favor completa al menos el ID y el Nombre del producto.")

# 3. MODIFICAR / ELIMINAR PRODUCTO
with tab_editar:
    st.subheader("Editar o Eliminar Producto Existente")
    if not df_inventario.empty and "ID" in df_inventario.columns:
        lista_ids = df_inventario["ID"].astype(str).tolist()
        id_seleccionado = st.selectbox("Selecciona el ID del Producto", options=lista_ids)
        
        # Filtrar producto seleccionado
        producto_idx = df_inventario[df_inventario["ID"].astype(str) == id_seleccionado].index
        
        if not producto_idx.empty:
            idx = producto_idx[0]
            prod_actual = df_inventario.loc[idx]

            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                edit_nombre = st.text_input("Nombre", value=str(prod_actual.get("Producto", "")))
                edit_cat = st.text_input("Categoría", value=str(prod_actual.get("Categoria", "")))
            with col_edit2:
                edit_precio = st.number_input("Precio ($)", value=float(prod_actual.get("Precio", 0.0)), step=50.0)
                edit_stock = st.number_input("Stock", value=int(prod_actual.get("Stock", 0)), step=1)

            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Actualizar Producto"):
                    df_inventario.loc[idx, "Producto"] = edit_nombre
                    df_inventario.loc[idx, "Categoria"] = edit_cat
                    df_inventario.loc[idx, "Precio"] = edit_precio
                    df_inventario.loc[idx, "Stock"] = edit_stock
                    
                    if guardar_inventario(df_inventario):
                        st.success("Producto actualizado con éxito.")
                        st.rerun()

            with col_btn2:
                if st.button("Eliminar Producto", type="primary"):
                    df_actualizado = df_inventario.drop(idx).reset_index(drop=True)
                    if guardar_inventario(df_actualizado):
                        st.success("Producto eliminado con éxito.")
                        st.rerun()
    else:
        st.info("No hay datos disponibles para editar.")
