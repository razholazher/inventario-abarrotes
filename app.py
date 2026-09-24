import streamlit as st
import pandas as pd
import os
import io

# Librerías para generar el PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuración de página
st.set_page_config(page_title="Sistema de Gestión de Inventario", page_icon="📦", layout="wide")

ARCHIVO_EXCEL = "inventario.xlsx"

# Función para cargar datos
def cargar_datos():
    if os.path.exists(ARCHIVO_EXCEL):
        try:
            df = pd.read_excel(ARCHIVO_EXCEL)
            df["ID"] = df["ID"].astype(str)
            df["Observaciones"] = df["Observaciones"].fillna("")
            return df
        except Exception:
            return pd.DataFrame(columns=["ID", "Nombre", "Categoría", "Precio Compra", "Precio Venta", "Cantidad", "Observaciones"])
    else:
        return pd.DataFrame(columns=["ID", "Nombre", "Categoría", "Precio Compra", "Precio Venta", "Cantidad", "Observaciones"])

# Función para guardar datos
def guardar_datos(df):
    df.to_excel(ARCHIVO_EXCEL, index=False)

# Función para generar el PDF en memoria
def generar_pdf_inventario(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=12
    )
    
    story.append(Paragraph("📦 REPORTE OFICIAL DE INVENTARIO", titulo_style))
    story.append(Spacer(1, 10))
    
    headers = ["ID", "Nombre", "Categoría", "P. Compra", "P. Venta", "Cant."]
    data = [headers]
    
    for _, row in df.iterrows():
        data.append([
            str(row["ID"]),
            str(row["Nombre"]).upper(),
            str(row["Categoría"]).upper(),
            f"${row['Precio Compra']:,.2f}",
            f"${row['Precio Venta']:,.2f}",
            str(row["Cantidad"])
        ])
    
    tabla = Table(data, colWidths=[60, 150, 110, 80, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    story.append(tabla)
    doc.build(story)
    buffer.seek(0)
    return buffer

df = cargar_datos()

# Asegurar tipos numéricos en el dataframe
if not df.empty:
    df["Precio Compra"] = pd.to_numeric(df["Precio Compra"], errors="coerce").fillna(0)
    df["Precio Venta"] = pd.to_numeric(df["Precio Venta"], errors="coerce").fillna(0)
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)

# Encabezado Principal
st.title("📦 SISTEMA DE GESTIÓN DE INVENTARIO")

# Pestañas
tab1, tab2, tab3 = st.tabs(["📋 INVENTARIO", "➕ REGISTRAR / EDITAR", "📊 REPORTES"])

with tab1:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("📋 Inventario Actual")
    with col_t2:
        if not df.empty:
            pdf_data = generar_pdf_inventario(df)
            st.download_button(
                label="📄 Descargar Inventario PDF",
                data=pdf_data,
                file_name="Reporte_Inventario.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("El inventario está vacío actualmente.")

with tab2:
    st.subheader("📝 FORMULARIO DE PRODUCTO")

    opciones = ["-- CREAR PRODUCTO NUEVO --"] + [f"{row['ID']} - {str(row['Nombre']).upper()}" for _, row in df.iterrows()]
    seleccion = st.selectbox("SELECCIONA UN PRODUCTO PARA EDITAR:", opciones, key="select_producto")

    is_nuevo = (seleccion == "-- CREAR PRODUCTO NUEVO --")
    
    if not is_nuevo:
        id_sel = seleccion.split(" - ")[0]
        prod = df[df["ID"].astype(str) == str(id_sel)].iloc[0]
        val_id = str(prod["ID"])
        val_nombre = str(prod["Nombre"]).upper()
        val_cat = str(prod["Categoría"]).upper()
        val_compra = str(prod["Precio Compra"])
        val_venta = str(prod["Precio Venta"])
        val_cant = str(prod["Cantidad"])
        val_obs = str(prod["Observaciones"]).upper() if pd.notna(prod["Observaciones"]) else ""
    else:
        val_id = ""
        val_nombre = ""
        val_cat = ""
        val_compra = ""
        val_venta = ""
        val_cant = ""
        val_obs = ""

    with st.form("form_producto", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            id_prod = st.text_input("ID DEL PRODUCTO *", value=val_id, placeholder="Ej: 1001")
            nombre = st.text_input("NOMBRE DEL PRODUCTO *", value=val_nombre, placeholder="Ej: ARROZ")
            categoria = st.text_input("CATEGORÍA *", value=val_cat, placeholder="Ej: ABARROTES")

        with col2:
            precio_compra = st.text_input("PRECIO DE COMPRA ($) *", value=val_compra, placeholder="Ej: 1500")
            precio_venta = st.text_input("PRECIO DE VENTA ($) *", value=val_venta, placeholder="Ej: 3500")
            cantidad = st.text_input("CANTIDAD *", value=val_cant, placeholder="Ej: 30")

        observaciones = st.text_area("OBSERVACIONES", value=val_obs, placeholder="Notas adicionales...")

        # Modo de actualización si el ID ya existe al crear
        modo_ingreso = "Sobrescribir / Modificar"
        if is_nuevo:
            modo_ingreso = st.radio(
                "SI EL ID YA EXISTE, ¿QUÉ DESEAS HACER?:",
                ["Sumar al stock y Promediar Costo de Compra", "Sobrescribir / Reemplazar completamente"],
                help="El promedio ponderado ajustará el costo de compra combinando las unidades viejas con las nuevas."
            )

        boton_guardar = st.form_submit_button("💾 GUARDAR PRODUCTO", use_container_width=True)

        if boton_guardar:
            id_ingresado = id_prod.strip().upper()
            
            if not id_ingresado or not nombre.strip() or not categoria.strip() or not precio_compra.strip() or not precio_venta.strip() or not cantidad.strip():
                st.error("❌ Por favor completa todos los campos obligatorios (*).")
            else:
                try:
                    p_compra_nuevo = float(precio_compra.replace(",", "."))
                    p_venta_nuevo = float(precio_venta.replace(",", "."))
                    cant_nueva = int(cantidad)

                    # Verificar si existe el ID
                    existe = id_ingresado in df["ID"].astype(str).values

                    if existe and is_nuevo and modo_ingreso.startswith("Sumar"):
                        # CALCULO DE PROMEDIO PONDERADO
                        prod_existente = df[df["ID"].astype(str) == id_ingresado].iloc[0]
                        cant_actual = int(prod_existente["Cantidad"])
                        p_compra_actual = float(prod_existente["Precio Compra"])

                        costo_total_acumulado = (cant_actual * p_compra_actual) + (cant_nueva * p_compra_nuevo)
                        cant_total = cant_actual + cant_nueva
                        nuevo_p_compra_promedio = costo_total_acumulado / cant_total if cant_total > 0 else p_compra_nuevo

                        # Actualizar la fila existente
                        df.loc[df["ID"].astype(str) == id_ingresado, "Cantidad"] = cant_total
                        df.loc[df["ID"].astype(str) == id_ingresado, "Precio Compra"] = round(nuevo_p_compra_promedio, 2)
                        df.loc[df["ID"].astype(str) == id_ingresado, "Precio Venta"] = p_venta_nuevo
                        df.loc[df["ID"].astype(str) == id_ingresado, "Nombre"] = nombre.strip().upper()
                        df.loc[df["ID"].astype(str) == id_ingresado, "Categoría"] = categoria.strip().upper()
                        df.loc[df["ID"].astype(str) == id_ingresado, "Observaciones"] = observaciones.strip().upper()

                        guardar_datos(df)
                        st.success(f"✅ Stock de '{nombre.upper()}' actualizado. Nuevo stock: {cant_total} unid. Nuevo costo promedio: ${nuevo_p_compra_promedio:,.2f}")
                        st.rerun()

                    else:
                        # Registro normal o edición directa
                        nuevo_registro = {
                            "ID": id_ingresado,
                            "Nombre": nombre.strip().upper(),
                            "Categoría": categoria.strip().upper(),
                            "Precio Compra": p_compra_nuevo,
                            "Precio Venta": p_venta_nuevo,
                            "Cantidad": cant_nueva,
                            "Observaciones": observaciones.strip().upper()
                        }

                        if existe:
                            df = df[df["ID"].astype(str) != id_ingresado]

                        df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
                        guardar_datos(df)

                        st.success(f"✅ Producto '{nombre.upper()}' guardado exitosamente.")
                        st.rerun()

                except ValueError:
                    st.error("❌ Los campos de Precios y Cantidad deben ser valores numéricos válidos.")

with tab3:
    st.subheader("📊 Resumen Financiero y Métricas del Inventario")
    
    if not df.empty:
        costo_total = (df["Precio Compra"] * df["Cantidad"]).sum()
        venta_total = (df["Precio Venta"] * df["Cantidad"]).sum()
        ganancia_estimada = venta_total - costo_total
        margen_promedio = (ganancia_estimada / venta_total * 100) if venta_total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Productos", len(df))
        c2.metric("Total Unidades", int(df["Cantidad"].sum()))
        c3.metric("Inversión (Costo)", f"${costo_total:,.2f}")
        c4.metric("Venta Estimada", f"${venta_total:,.2f}")

        st.divider()

        c_ganancia, c_alerta = st.columns([1, 1])

        with c_ganancia:
            st.markdown("### 💰 Proyección de Utilidad")
            st.metric("Ganancia Bruta Estimada", f"${ganancia_estimada:,.2f}", delta=f"{margen_promedio:.1f}% Margen")
            st.caption("Muestra la utilidad neta estimada si se vende todo el stock actual.")

        with c_alerta:
            st.markdown("### ⚠️ Alerta de Stock Bajo (Menos de 10 unidades)")
            stock_bajo = df[df["Cantidad"] < 10][["ID", "Nombre", "Cantidad"]]
            if not stock_bajo.empty:
                st.dataframe(stock_bajo, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 Todos los productos tienen suficiente stock (10 o más unidades).")

        st.divider()

        st.markdown("### 📈 Análisis por Categoría")
        col_g1, col_g2 = st.columns(2)

        df_cat = df.groupby("Categoría").agg(
            Unidades=("Cantidad", "sum"),
            Inversion=("Precio Compra", lambda x: (x * df.loc[x.index, "Cantidad"]).sum())
        ).reset_index()

        with col_g1:
            st.caption("Unidades Disponibles por Categoría")
            st.bar_chart(data=df_cat, x="Categoría", y="Unidades", use_container_width=True)

        with col_g2:
            st.caption("Inversión Retenida ($) por Categoría")
            st.bar_chart(data=df_cat, x="Categoría", y="Inversion", use_container_width=True)

        st.divider()

        st.markdown("### 📑 Rentabilidad Detallada por Producto")
        
        df_reporte = df.copy()
        df_reporte["Inversión ($)"] = df_reporte["Precio Compra"] * df_reporte["Cantidad"]
        df_reporte["Venta Total ($)"] = df_reporte["Precio Venta"] * df_reporte["Cantidad"]
        df_reporte["Ganancia Total ($)"] = df_reporte["Venta Total ($)"] - df_reporte["Inversión ($)"]
        df_reporte["Ganancia por Unid ($)"] = df_reporte["Precio Venta"] - df_reporte["Precio Compra"]

        columnas_mostrar = ["ID", "Nombre", "Categoría", "Cantidad", "Precio Compra", "Precio Venta", "Ganancia por Unid ($)", "Inversión ($)", "Ganancia Total ($)"]
        st.dataframe(df_reporte[columnas_mostrar], use_container_width=True, hide_index=True)

    else:
        st.info("No hay datos para generar reportes. Agrega productos desde la pestaña 'REGISTRAR / EDITAR'.")