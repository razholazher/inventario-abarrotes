import streamlit as st
import pandas as pd
import io
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection

# Librerías para generar el PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuración de página
st.set_page_config(page_title="Sistema Integral de Abarrotes", page_icon="🏪", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(worksheet_name, columns_default):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columns_default)
        return df
    except Exception:
        return pd.DataFrame(columns=columns_default)

def guardar_tabla(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)

# --- FUNCIONALIDAD DE HORA LOCAL (COLOMBIA) ---
def obtener_fecha_hora_local():
    return datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S")

def obtener_fecha_corta_local():
    return datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d")

# --- CARGA Y PROCESAMIENTO DE DATOS ---

def cargar_inventario():
    cols = ["ID", "Nombre", "Categoría", "Precio Compra", "Precio Venta", "Cantidad", "Proveedor", "Fecha Ingreso", "Observaciones"]
    df = cargar_tabla("inventario", cols)
    if not df.empty:
        df["ID"] = df["ID"].astype(str)
        df["Nombre"] = df["Nombre"].astype(str).str.upper()
        df["Categoría"] = df["Categoría"].astype(str).str.upper()
        df["Proveedor"] = df.get("Proveedor", pd.Series(["GENERAL"] * len(df))).astype(str).str.upper()
        df["Observaciones"] = df["Observaciones"].fillna("").astype(str).str.upper()
        df["Fecha Ingreso"] = df["Fecha Ingreso"].fillna("").astype(str)
    return df

def guardar_inventario(df):
    guardar_tabla(df, "inventario")

def registrar_kardex(id_prod, nombre, tipo_movimiento, cantidad, motivo=""):
    cols = ["Fecha", "ID", "Producto", "Tipo", "Cantidad", "Motivo"]
    df_kardex = cargar_tabla("kardex", cols)
    nuevo_mov = {
        "Fecha": obtener_fecha_hora_local(),
        "ID": str(id_prod),
        "Producto": str(nombre).upper(),
        "Tipo": tipo_movimiento.upper(),
        "Cantidad": cantidad,
        "Motivo": motivo.upper()
    }
    df_kardex = pd.concat([df_kardex, pd.DataFrame([nuevo_mov])], ignore_index=True)
    guardar_tabla(df_kardex, "kardex")

def registrar_venta_desglosada(items_venta, m_efectivo, m_transf, m_fiado, cliente=""):
    cols = ["Fecha_Hora", "Fecha", "ID", "Producto", "Cantidad", "Precio_Venta", "Total", "Monto_Efectivo", "Monto_Transferencia", "Monto_Fiado", "Metodo_Pago", "Cliente"]
    df_ventas = cargar_tabla("ventas", cols)
    
    fecha_hora = obtener_fecha_hora_local()
    fecha_corta = obtener_fecha_corta_local()
    registros = []
    
    total_venta = sum(item["Cantidad"] * item["Precio Venta"] for item in items_venta)
    
    if m_fiado == total_venta:
        metodo_general = "FIADO"
    elif m_efectivo == total_venta:
        metodo_general = "EFECTIVO"
    elif m_transf == total_venta:
        metodo_general = "TRANSFERENCIA"
    else:
        metodo_general = "PAGO MIXTO"

    for item in items_venta:
        subtotal = item["Cantidad"] * item["Precio Venta"]
        prop = subtotal / total_venta if total_venta > 0 else 0
        
        registros.append({
            "Fecha_Hora": fecha_hora,
            "Fecha": str(fecha_corta),
            "ID": str(item["ID"]),
            "Producto": item["Nombre"].upper(),
            "Cantidad": item["Cantidad"],
            "Precio_Venta": item["Precio Venta"],
            "Total": subtotal,
            "Monto_Efectivo": round(m_efectivo * prop, 2),
            "Monto_Transferencia": round(m_transf * prop, 2),
            "Monto_Fiado": round(m_fiado * prop, 2),
            "Metodo_Pago": metodo_general,
            "Cliente": cliente.upper() if cliente else "GENERAL"
        })
    
    df_ventas = pd.concat([df_ventas, pd.DataFrame(registros)], ignore_index=True)
    guardar_tabla(df_ventas, "ventas")

def cargar_fiados():
    cols = ["Cliente", "Total_Deuda", "Ultimo_Abono", "Fecha_Ultimo_Movimiento"]
    return cargar_tabla("fiados", cols)

def guardar_fiados(df_fiados):
    guardar_tabla(df_fiados, "fiados")

def registrar_abono_historial(cliente, monto, metodo_pago):
    cols = ["Fecha_Hora", "Fecha", "Cliente", "Monto", "Metodo_Pago"]
    df_ab = cargar_tabla("abonos", cols)
    nuevo_abono = {
        "Fecha_Hora": obtener_fecha_hora_local(),
        "Fecha": str(obtener_fecha_corta_local()),
        "Cliente": str(cliente).upper(),
        "Monto": float(monto),
        "Metodo_Pago": str(metodo_pago).upper()
    }
    df_ab = pd.concat([df_ab, pd.DataFrame([nuevo_abono])], ignore_index=True)
    guardar_tabla(df_ab, "abonos")

# --- GENERACIÓN DE REPORTES PDF ---

def generar_pdf_inventario(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('TituloStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1F2937"), spaceAfter=12)
    
    story.append(Paragraph("📦 REPORTE OFICIAL DE INVENTARIO", titulo_style))
    story.append(Spacer(1, 10))
    
    headers = ["ID", "Nombre", "Categoría", "P. Compra", "P. Venta", "Cant.", "Fecha Ingreso"]
    data = [headers]
    for _, row in df.iterrows():
        data.append([
            str(row["ID"]), str(row["Nombre"]).upper(), str(row["Categoría"]).upper(),
            f"${row['Precio Compra']:,.2f}", f"${row['Precio Venta']:,.2f}", str(row["Cantidad"]), str(row.get("Fecha Ingreso", ""))
        ])
    
    tabla = Table(data, colWidths=[50, 130, 80, 65, 65, 40, 90])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
    ]))
    story.append(tabla)
    doc.build(story)
    buffer.seek(0)
    return buffer

def generar_pdf_cierre_caja(fecha_str, total_efectivo, total_transf, total_fiado, total_recaudo, df_ventas, df_abonos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('TituloStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1E3A8A"), spaceAfter=8)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor("#1F2937"), spaceBefore=10, spaceAfter=6)
    
    story.append(Paragraph(f"📊 REPORTE DE CIERRE DE CAJA - {fecha_str}", titulo_style))
    story.append(Paragraph(f"Fecha de Generación: {obtener_fecha_hora_local()}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    data_resumen = [
        ["CONCEPTO", "MONTO"],
        ["💵 Total Efectivo en Caja", f"${total_efectivo:,.2f}"],
        ["💳 Total Transferencias", f"${total_transf:,.2f}"],
        ["🤝 Valor Mercancía Fiada Hoy", f"${total_fiado:,.2f}"],
        ["💰 RECAUDO REAL DEL DÍA", f"${total_recaudo:,.2f}"]
    ]
    t_resumen = Table(data_resumen, colWidths=[250, 250])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#D1E7DD")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("📑 Detalle de Ventas del Día", sub_style))
    if not df_ventas.empty:
        data_v = [["Hora", "Producto", "Cant.", "Total", "Pago", "Cliente"]]
        for _, r in df_ventas.iterrows():
            data_v.append([
                str(r["Fecha_Hora"]).split()[-1] if len(str(r["Fecha_Hora"]).split()) > 1 else str(r["Fecha_Hora"]),
                str(r["Producto"]), str(r["Cantidad"]), f"${r['Total']:,.2f}", str(r["Metodo_Pago"]), str(r["Cliente"]) if pd.notna(r["Cliente"]) else ""
            ])
        t_ventas = Table(data_v, colWidths=[60, 160, 40, 70, 90, 80])
        t_ventas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ]))
        story.append(t_ventas)
    else:
        story.append(Paragraph("No hubo ventas en la fecha seleccionada.", styles['Normal']))
        
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("💵 Abonos Recibidos Hoy", sub_style))
    if not df_abonos.empty:
        data_a = [["Hora", "Cliente", "Monto", "Método Pago"]]
        for _, r in df_abonos.iterrows():
            data_a.append([
                str(r["Fecha_Hora"]).split()[-1] if len(str(r["Fecha_Hora"]).split()) > 1 else str(r["Fecha_Hora"]),
                str(r["Cliente"]), f"${r['Monto']:,.2f}", str(r["Metodo_Pago"])
            ])
        t_abonos = Table(data_a, colWidths=[80, 200, 100, 120])
        t_abonos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ]))
        story.append(t_abonos)
    else:
        story.append(Paragraph("No se registraron abonos en esta fecha.", styles['Normal']))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# Carga inicial de datos desde Google Sheets
df_inv = cargar_inventario()

if not df_inv.empty:
    df_inv["Precio Compra"] = pd.to_numeric(df_inv["Precio Compra"], errors="coerce").fillna(0)
    df_inv["Precio Venta"] = pd.to_numeric(df_inv["Precio Venta"], errors="coerce").fillna(0)
    df_inv["Cantidad"] = pd.to_numeric(df_inv["Cantidad"], errors="coerce").fillna(0).astype(int)
    df_inv["Fecha Ingreso"] = df_inv["Fecha Ingreso"].astype(str)

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# Encabezado Principal
st.title("🏪 SISTEMA INTEGRAL DE ABARROTES")

tab_pos, tab_inv, tab_kardex, tab_prov, tab_fiados, tab_rep = st.tabs([
    "🛒 PUNTO DE VENTA (POS)",
    "📦 INVENTARIO & PRODUCTOS",
    "📜 KARDEX / MOVIMIENTOS",
    "🚚 PROVEEDORES",
    "🤝 FIADOS / CRÉDITOS",
    "📊 REPORTES & CIERRE"
])

# ==========================================
# 1. PUNTO DE VENTA (POS) Y CARRITO
# ==========================================
with tab_pos:
    st.subheader("🛒 Carrito / Punto de Venta")
    col_pos1, col_pos2 = st.columns([2, 1])
    
    with col_pos1:
        st.markdown("### 🔍 Buscar y Agregar Producto")
        if not df_inv.empty:
            opciones_buscar = [f"{r['ID']} - {r['Nombre']} (Stock: {r['Cantidad']}) - ${r['Precio Venta']:,.0f}" for _, r in df_inv.iterrows()]
            prod_seleccionado = st.selectbox("Buscar por ID o Nombre:", ["-- SELECCIONAR --"] + opciones_buscar)
            
            if prod_seleccionado != "-- SELECCIONAR --":
                id_sel = prod_seleccionado.split(" - ")[0]
                item_inv = df_inv[df_inv["ID"] == id_sel].iloc[0]
                
                col_cant, col_btn = st.columns([1, 1])
                with col_cant:
                    cant_vender = st.number_input("Cantidad a vender:", min_value=1, max_value=int(item_inv["Cantidad"]) if item_inv["Cantidad"] > 0 else 1, value=1, step=1)
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("➕ Agregar al Carrito", use_container_width=True):
                        if item_inv["Cantidad"] < cant_vender:
                            st.error("❌ Stock insuficiente.")
                        else:
                            encontrado = False
                            for c in st.session_state.carrito:
                                if c["ID"] == id_sel:
                                    c["Cantidad"] += cant_vender
                                    encontrado = True
                                    break
                            if not encontrado:
                                st.session_state.carrito.append({
                                    "ID": id_sel,
                                    "Nombre": item_inv["Nombre"],
                                    "Precio Venta": item_inv["Precio Venta"],
                                    "Cantidad": cant_vender
                                })
                            st.success(f"Agregado: {item_inv['Nombre']} x{cant_vender}")
                            st.rerun()
        else:
            st.info("No hay productos en inventario.")

    with col_pos2:
        st.markdown("### 🛍️ Resumen del Carrito")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            df_car["Subtotal"] = df_car["Cantidad"] * df_car["Precio Venta"]
            st.dataframe(df_car[["Nombre", "Cantidad", "Precio Venta", "Subtotal"]], use_container_width=True, hide_index=True)
            
            total_pagar = df_car["Subtotal"].sum()
            st.markdown(f"## **TOTAL: ${total_pagar:,.2f}**")
            
            metodo_pago = st.selectbox("Método de Pago:", ["EFECTIVO", "TRANSFERENCIA", "FIADO", "PAGO MIXTO / COMBINADO"])
            
            m_efectivo = 0.0
            m_transf = 0.0
            m_fiado = 0.0
            cliente_fiado = ""
            
            if metodo_pago == "EFECTIVO":
                m_efectivo = float(total_pagar)
            elif metodo_pago == "TRANSFERENCIA":
                m_transf = float(total_pagar)
            elif metodo_pago == "FIADO":
                m_fiado = float(total_pagar)
                cliente_fiado = st.text_input("Nombre del Cliente (Fiado):").strip().upper()
            elif metodo_pago == "PAGO MIXTO / COMBINADO":
                st.markdown("#### 💵 Desglose del Pago Mixto")
                m_efectivo = st.number_input("💵 Pago en Efectivo ($):", min_value=0.0, value=0.0, step=500.0)
                m_transf = st.number_input("💳 Pago en Transferencia ($):", min_value=0.0, value=0.0, step=500.0)
                m_fiado = st.number_input("🤝 Queda debiendo / Fiado ($):", min_value=0.0, value=0.0, step=500.0)
                
                if m_fiado > 0:
                    cliente_fiado = st.text_input("Nombre del Cliente (Fiado):").strip().upper()
                    
                suma_pagos = m_efectivo + m_transf + m_fiado
                diferencia = total_pagar - suma_pagos
                
                if abs(diferencia) > 0.01:
                    st.warning(f"⚠️ La suma de los pagos (${suma_pagos:,.2f}) no coincide con el total (${total_pagar:,.2f}). Faltan / Sobran: ${diferencia:,.2f}")
                else:
                    st.success("✅ El desglose coincide perfectamente con el total.")

            if st.button("✅ REGISTRAR VENTA", type="primary", use_container_width=True):
                suma_pagos = m_efectivo + m_transf + m_fiado
                if abs(total_pagar - suma_pagos) > 0.01:
                    st.error("❌ El total pagado no coincide con el total de la venta.")
                elif m_fiado > 0 and not cliente_fiado:
                    st.error("❌ Debes ingresar el nombre del cliente para registrar el fiado.")
                else:
                    for item in st.session_state.carrito:
                        id_item = item["ID"]
                        cant = item["Cantidad"]
                        df_inv.loc[df_inv["ID"] == id_item, "Cantidad"] -= cant
                        registrar_kardex(id_item, item["Nombre"], "VENTA", cant, f"Venta {metodo_pago}")
                    
                    guardar_inventario(df_inv)
                    registrar_venta_desglosada(st.session_state.carrito, m_efectivo, m_transf, m_fiado, cliente_fiado)
                    
                    if m_fiado > 0:
                        df_f = cargar_fiados()
                        if not df_f.empty and cliente_fiado in df_f["Cliente"].astype(str).values:
                            df_f.loc[df_f["Cliente"].astype(str) == cliente_fiado, "Total_Deuda"] = pd.to_numeric(df_f.loc[df_f["Cliente"].astype(str) == cliente_fiado, "Total_Deuda"], errors="coerce").fillna(0) + m_fiado
                            df_f.loc[df_f["Cliente"].astype(str) == cliente_fiado, "Fecha_Ultimo_Movimiento"] = obtener_fecha_corta_local()
                        else:
                            nuevo_fiado = {
                                "Cliente": cliente_fiado,
                                "Total_Deuda": m_fiado,
                                "Ultimo_Abono": 0,
                                "Fecha_Ultimo_Movimiento": obtener_fecha_corta_local()
                            }
                            df_f = pd.concat([df_f, pd.DataFrame([nuevo_fiado])], ignore_index=True)
                        guardar_fiados(df_f)
                    
                    st.session_state.carrito = []
                    st.success("🎉 ¡Venta registrada exitosamente!")
                    st.rerun()
                    
            if st.button("🗑️ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("El carrito está vacío.")

# ==========================================
# 2. INVENTARIO & PRODUCTOS
# ==========================================
with tab_inv:
    col_inv1, col_inv2 = st.columns([3, 1])
    with col_inv1:
        st.subheader("📋 Inventario Actual")
    with col_inv2:
        if not df_inv.empty:
            pdf_data = generar_pdf_inventario(df_inv)
            st.download_button("📄 Descargar PDF Inventario", data=pdf_data, file_name="Inventario.pdf", mime="application/pdf", use_container_width=True)

    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("El inventario está vacío.")

    st.divider()
    st.subheader("📝 FORMULARIO DE PRODUCTO (CREAR / EDITAR / ELIMINAR)")

    opciones = ["-- CREAR PRODUCTO NUEVO --"] + [f"{row['ID']} - {str(row['Nombre']).upper()}" for _, row in df_inv.iterrows()]
    seleccion = st.selectbox("SELECCIONA UN PRODUCTO PARA EDITAR / ELIMINAR:", opciones, key="select_producto")

    is_nuevo = (seleccion == "-- CREAR PRODUCTO NUEVO --")
    
    if not is_nuevo:
        id_sel = seleccion.split(" - ")[0]
        prod = df_inv[df_inv["ID"].astype(str) == str(id_sel)].iloc[0]
        val_id = str(prod["ID"])
        val_nombre = str(prod["Nombre"]).upper()
        val_cat = str(prod["Categoría"]).upper()
        val_compra = str(prod["Precio Compra"])
        val_venta = str(prod["Precio Venta"])
        val_cant = str(prod["Cantidad"])
        val_prov = str(prod.get("Proveedor", "GENERAL")).upper()
        val_ingreso = str(prod.get("Fecha Ingreso", obtener_fecha_hora_local()))
        val_obs = str(prod["Observaciones"]).upper() if pd.notna(prod["Observaciones"]) else ""
    else:
        val_id, val_nombre, val_cat, val_compra, val_venta, val_cant, val_prov, val_obs = "", "", "", "", "", "", "GENERAL", ""
        val_ingreso = obtener_fecha_hora_local()

    with st.form("form_producto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            id_prod = st.text_input("ID DEL PRODUCTO *", value=val_id, placeholder="Ej: 1001")
            nombre = st.text_input("NOMBRE DEL PRODUCTO *", value=val_nombre, placeholder="Ej: ARROZ 1KG")
            categoria = st.text_input("CATEGORÍA *", value=val_cat, placeholder="Ej: ABARROTES")

        with col2:
            precio_compra = st.text_input("PRECIO DE COMPRA ($) *", value=val_compra, placeholder="Ej: 2000")
            precio_venta = st.text_input("PRECIO DE VENTA ($) *", value=val_venta, placeholder="Ej: 2800")
            cantidad = st.text_input("CANTIDAD *", value=val_cant, placeholder="Ej: 20")

        with col3:
            proveedor = st.text_input("PROVEEDOR", value=val_prov, placeholder="Ej: DIANA / COLANTA")
            st.text_input("FECHA Y HORA DE INGRESO (AUTOMÁTICA)", value=val_ingreso, disabled=True)
            observaciones = st.text_input("OBSERVACIONES", value=val_obs, placeholder="Notas...")

        modo_ingreso = "Sobrescribir / Modificar"
        if is_nuevo:
            modo_ingreso = st.radio(
                "SI EL ID YA EXISTE:",
                ["Sumar al stock y Promediar Costo de Compra", "Sobrescribir completamente"]
            )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            boton_guardar = st.form_submit_button("💾 GUARDAR PRODUCTO", use_container_width=True)
        with col_b2:
            confirmar_borrado = False
            if not is_nuevo:
                confirmar_borrado = st.checkbox("Confirmar eliminación de este producto")
                boton_eliminar = st.form_submit_button("🗑️ ELIMINAR PRODUCTO", use_container_width=True)
            else:
                boton_eliminar = False

        if boton_guardar:
            id_ingresado = id_prod.strip().upper()
            if not id_ingresado or not nombre.strip() or not categoria.strip() or not precio_compra.strip() or not precio_venta.strip() or not cantidad.strip():
                st.error("❌ Completa los campos obligatorios (*).")
            else:
                try:
                    p_compra_nuevo = float(precio_compra.replace(",", "."))
                    p_venta_nuevo = float(precio_venta.replace(",", "."))
                    cant_nueva = int(cantidad)
                    fecha_ahora = obtener_fecha_hora_local()

                    existe = id_ingresado in df_inv["ID"].astype(str).values

                    if existe and is_nuevo and modo_ingreso.startswith("Sumar"):
                        idx = df_inv[df_inv["ID"].astype(str) == id_ingresado].index[0]
                        cant_actual = int(df_inv.at[idx, "Cantidad"])
                        p_compra_actual = float(df_inv.at[idx, "Precio Compra"])

                        costo_total_acumulado = (cant_actual * p_compra_actual) + (cant_nueva * p_compra_nuevo)
                        cant_total = cant_actual + cant_nueva
                        nuevo_p_compra_promedio = costo_total_acumulado / cant_total if cant_total > 0 else p_compra_nuevo

                        df_inv.at[idx, "Cantidad"] = cant_total
                        df_inv.at[idx, "Precio Compra"] = round(nuevo_p_compra_promedio, 2)
                        df_inv.at[idx, "Precio Venta"] = p_venta_nuevo
                        df_inv.at[idx, "Nombre"] = nombre.strip().upper()
                        df_inv.at[idx, "Categoría"] = categoria.strip().upper()
                        df_inv.at[idx, "Proveedor"] = proveedor.strip().upper()
                        df_inv.at[idx, "Fecha Ingreso"] = str(fecha_ahora)
                        df_inv.at[idx, "Observaciones"] = observaciones.strip().upper()

                        guardar_inventario(df_inv)
                        registrar_kardex(id_ingresado, nombre, "ENTRADA", cant_nueva, "Reingreso Mercancía (Promediado)")
                        st.success(f"✅ Stock de '{nombre.upper()}' actualizado ({cant_total} unid).")
                        st.rerun()
                    else:
                        nuevo_registro = {
                            "ID": str(id_ingresado),
                            "Nombre": str(nombre.strip().upper()),
                            "Categoría": str(categoria.strip().upper()),
                            "Precio Compra": p_compra_nuevo,
                            "Precio Venta": p_venta_nuevo,
                            "Cantidad": cant_nueva,
                            "Proveedor": str(proveedor.strip().upper()),
                            "Fecha Ingreso": str(fecha_ahora if is_nuevo else val_ingreso),
                            "Observaciones": str(observaciones.strip().upper())
                        }
                        if existe:
                            df_inv = df_inv[df_inv["ID"].astype(str) != id_ingresado]
                        df_inv = pd.concat([df_inv, pd.DataFrame([nuevo_registro])], ignore_index=True)
                        guardar_inventario(df_inv)
                        registrar_kardex(id_ingresado, nombre, "ENTRADA" if is_nuevo else "AJUSTE", cant_nueva, "Registro de producto")
                        st.success(f"✅ Producto '{nombre.upper()}' guardado exitosamente.")
                        st.rerun()

                except ValueError:
                    st.error("❌ Los Precios y la Cantidad deben ser valores numéricos válidos.")

        if boton_eliminar:
            if not confirmar_borrado:
                st.error("⚠️ Marca la casilla de confirmación para eliminar este producto.")
            else:
                id_elim = val_id
                nombre_elim = val_nombre
                cant_elim = int(val_cant) if val_cant.isdigit() else 0
                
                df_inv = df_inv[df_inv["ID"].astype(str) != str(id_elim)]
                guardar_inventario(df_inv)
                registrar_kardex(id_elim, nombre_elim, "MERMA / BORRADO", cant_elim, "Eliminado del inventario")
                st.success(f"🗑️ Producto '{nombre_elim}' eliminado correctamente.")
                st.rerun()

# ==========================================
# 3. KARDEX Y MOVIMIENTOS
# ==========================================
with tab_kardex:
    st.subheader("📜 Historial de Movimientos de Inventario (Kardex)")
    st.info("💡 Nota: El Kardex registra el movimiento físico de mercancías (entradas, ventas y ajustes). Los abonos en efectivo/transferencia se consultan en las pestañas de Fiados y Reportes de Caja.")
    df_k = cargar_tabla("kardex", ["Fecha", "ID", "Producto", "Tipo", "Cantidad", "Motivo"])
    if not df_k.empty:
        st.dataframe(df_k.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay movimientos registrados.")

# ==========================================
# 4. GESTIÓN DE PROVEEDORES
# ==========================================
with tab_prov:
    st.subheader("🚚 Gestión y Reporte por Proveedor")
    if not df_inv.empty:
        proveedores = list(df_inv["Proveedor"].unique())
        prov_sel = st.selectbox("Filtrar por Proveedor:", ["TODOS"] + proveedores)
        
        if prov_sel != "TODOS":
            df_p = df_inv[df_inv["Proveedor"] == prov_sel]
        else:
            df_p = df_inv
            
        st.dataframe(df_p[["ID", "Nombre", "Categoría", "Cantidad", "Precio Compra", "Proveedor"]], use_container_width=True, hide_index=True)
        inversion_prov = (df_p["Precio Compra"] * df_p["Cantidad"]).sum()
        st.metric("Inversión Total retenida con este Proveedor", f"${inversion_prov:,.2f}")
    else:
        st.info("No hay productos en inventario.")

# ==========================================
# 5. FIADOS / CRÉDITOS
# ==========================================
with tab_fiados:
    st.subheader("🤝 Control de Cuentas por Cobrar (Fiados)")
    df_f = cargar_fiados()
    if not df_f.empty:
        df_f["Total_Deuda"] = pd.to_numeric(df_f["Total_Deuda"], errors="coerce").fillna(0)
    
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        st.markdown("### 📋 Deudores Actuales")
        if not df_f.empty and (df_f["Total_Deuda"] > 0).any():
            st.dataframe(df_f[df_f["Total_Deuda"] > 0], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡No hay cuentas pendientes por cobrar!")
            
    with col_f2:
        st.markdown("### 💵 Registrar Abono")
        if not df_f.empty and (df_f["Total_Deuda"] > 0).any():
            clientes_deudores = df_f[df_f["Total_Deuda"] > 0]["Cliente"].tolist()
            cli_sel = st.selectbox("Selecciona Cliente:", clientes_deudores)
            monto_abono = st.number_input("Monto del Abono ($):", min_value=1.0, step=500.0)
            metodo_abono = st.selectbox("Método de Pago del Abono:", ["EFECTIVO", "TRANSFERENCIA"])
            
            if st.button("💾 Registrar Abono", use_container_width=True):
                deuda_actual = float(df_f.loc[df_f["Cliente"] == cli_sel, "Total_Deuda"].values[0])
                nueva_deuda = max(0.0, deuda_actual - monto_abono)
                
                df_f.loc[df_f["Cliente"] == cli_sel, "Total_Deuda"] = nueva_deuda
                df_f.loc[df_f["Cliente"] == cli_sel, "Ultimo_Abono"] = monto_abono
                df_f.loc[df_f["Cliente"] == cli_sel, "Fecha_Ultimo_Movimiento"] = obtener_fecha_corta_local()
                
                guardar_fiados(df_f)
                registrar_abono_historial(cli_sel, monto_abono, metodo_abono)
                st.success(f"Abono de ${monto_abono:,.2f} ({metodo_abono}) registrado para {cli_sel}. Nueva deuda: ${nueva_deuda:,.2f}")
                st.rerun()

    st.divider()
    st.markdown("### 📜 Historial General de Abonos Recibidos")
    df_ab_hist = cargar_tabla("abonos", ["Fecha_Hora", "Fecha", "Cliente", "Monto", "Metodo_Pago"])
    if not df_ab_hist.empty:
        st.dataframe(df_ab_hist.sort_values(by="Fecha_Hora", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Aún no se han registrado abonos a deudas.")

# ==========================================
# 6. REPORTES Y CIERRE DE CAJA
# ==========================================
with tab_rep:
    st.subheader("📊 Cierre de Caja Diario y Reportes Financieros")
    
    fecha_filtro = st.date_input("Seleccionar Fecha de Cierre de Caja:", value=date.today())
    fecha_str = fecha_filtro.strftime("%Y-%m-%d")
    
    df_v = cargar_tabla("ventas", ["Fecha_Hora", "Fecha", "ID", "Producto", "Cantidad", "Precio_Venta", "Total", "Monto_Efectivo", "Monto_Transferencia", "Monto_Fiado", "Metodo_Pago", "Cliente"])
    ventas_dia = df_v[df_v["Fecha"].astype(str) == str(fecha_str)] if not df_v.empty and "Fecha" in df_v.columns else pd.DataFrame()

    df_ab = cargar_tabla("abonos", ["Fecha_Hora", "Fecha", "Cliente", "Monto", "Metodo_Pago"])
    abonos_dia = df_ab[df_ab["Fecha"].astype(str) == str(fecha_str)] if not df_ab.empty and "Fecha" in df_ab.columns else pd.DataFrame()

    if not ventas_dia.empty:
        ventas_efectivo = pd.to_numeric(ventas_dia.get("Monto_Efectivo", ventas_dia[ventas_dia["Metodo_Pago"] == "EFECTIVO"]["Total"]), errors="coerce").fillna(0).sum()
        ventas_transf = pd.to_numeric(ventas_dia.get("Monto_Transferencia", ventas_dia[ventas_dia["Metodo_Pago"] == "TRANSFERENCIA"]["Total"]), errors="coerce").fillna(0).sum()
        ventas_fiado = pd.to_numeric(ventas_dia.get("Monto_Fiado", ventas_dia[ventas_dia["Metodo_Pago"] == "FIADO"]["Total"]), errors="coerce").fillna(0).sum()
    else:
        ventas_efectivo, ventas_transf, ventas_fiado = 0.0, 0.0, 0.0

    abonos_efectivo = pd.to_numeric(abonos_dia[abonos_dia["Metodo_Pago"] == "EFECTIVO"]["Monto"], errors="coerce").sum() if not abonos_dia.empty else 0
    abonos_transf = pd.to_numeric(abonos_dia[abonos_dia["Metodo_Pago"] == "TRANSFERENCIA"]["Monto"], errors="coerce").sum() if not abonos_dia.empty else 0

    total_efectivo_caja = ventas_efectivo + abonos_efectivo
    total_transferencias = ventas_transf + abonos_transf
    recaudo_real_dia = total_efectivo_caja + total_transferencias

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Efectivo en Caja", f"${total_efectivo_caja:,.2f}")
    c2.metric("💳 Transferencias", f"${total_transferencias:,.2f}")
    c3.metric("🤝 Fiado Hoy", f"${ventas_fiado:,.2f}")
    c4.metric("💰 Recaudo Real", f"${recaudo_real_dia:,.2f}")

    st.divider()

    pdf_cierre = generar_pdf_cierre_caja(
        fecha_str, total_efectivo_caja, total_transferencias, ventas_fiado, recaudo_real_dia, ventas_dia, abonos_dia
    )
    st.download_button(
        label="📄 Descargar PDF Cierre de Caja",
        data=pdf_cierre,
        file_name=f"Cierre_Caja_{fecha_str}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.markdown("### 📑 Ventas Registradas en el Día")
    if not ventas_dia.empty:
        st.dataframe(ventas_dia, use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas para esta fecha.")

    st.markdown("### 💵 Abonos Registrados en el Día")
    if not abonos_dia.empty:
        st.dataframe(abonos_dia, use_container_width=True, hide_index=True)
    else:
        st.info("No hay abonos registrados para esta fecha.")
