import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date, timedelta

# Librerías para generar el PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuración de página
st.set_page_config(page_title="Sistema de Gestión de Inventario & POS", page_icon="🏪", layout="wide")

# Archivos de datos
ARCHIVO_INVENTARIO = "inventario.xlsx"
ARCHIVO_VENTAS = "ventas.csv"
ARCHIVO_KARDEX = "kardex.csv"
ARCHIVO_FIADOS = "fiados.csv"

# --- FUNCIONES DE CARGA Y GUARDADO ---

def cargar_inventario():
    if os.path.exists(ARCHIVO_INVENTARIO):
        try:
            df = pd.read_excel(ARCHIVO_INVENTARIO)
            df["ID"] = df["ID"].astype(str)
            df["Nombre"] = df["Nombre"].astype(str).str.upper()
            df["Categoría"] = df["Categoría"].astype(str).str.upper()
            df["Proveedor"] = df.get("Proveedor", pd.Series(["GENERAL"] * len(df))).astype(str).str.upper()
            df["Observaciones"] = df["Observaciones"].fillna("").astype(str).str.upper()
            
            # Formato de fechas de vencimiento
            if "Fecha Vencimiento" not in df.columns:
                df["Fecha Vencimiento"] = ""
            df["Fecha Vencimiento"] = df["Fecha Vencimiento"].fillna("")
            return df
        except Exception:
            return crear_df_inventario_vacio()
    else:
        return crear_df_inventario_vacio()

def crear_df_inventario_vacio():
    return pd.DataFrame(columns=["ID", "Nombre", "Categoría", "Precio Compra", "Precio Venta", "Cantidad", "Proveedor", "Fecha Vencimiento", "Observaciones"])

def guardar_inventario(df):
    df.to_excel(ARCHIVO_INVENTARIO, index=False)

def registrar_kardex(id_prod, nombre, tipo_movimiento, cantidad, motivo=""):
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_mov = {
        "Fecha": fecha_hora,
        "ID": str(id_prod),
        "Producto": str(nombre).upper(),
        "Tipo": tipo_movimiento.upper(), # ENTRADA, VENTA, MERMA, FIADO, AJUSTE
        "Cantidad": cantidad,
        "Motivo": motivo.upper()
    }
    if os.path.exists(ARCHIVO_KARDEX):
        df_kardex = pd.read_csv(ARCHIVO_KARDEX)
        df_kardex = pd.concat([df_kardex, pd.DataFrame([nuevo_mov])], ignore_index=True)
    else:
        df_kardex = pd.DataFrame([nuevo_mov])
    df_kardex.to_csv(ARCHIVO_KARDEX, index=False)

def registrar_venta(items_venta, metodo_pago="EFECTIVO", cliente=""):
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_corta = datetime.now().strftime("%Y-%m-%d")
    registros = []
    
    for item in items_venta:
        total = item["Cantidad"] * item["Precio Venta"]
        registros.append({
            "Fecha_Hora": fecha_hora,
            "Fecha": fecha_corta,
            "ID": item["ID"],
            "Producto": item["Nombre"].upper(),
            "Cantidad": item["Cantidad"],
            "Precio_Venta": item["Precio Venta"],
            "Total": total,
            "Metodo_Pago": metodo_pago,
            "Cliente": cliente.upper()
        })
    
    df_nuevas = pd.DataFrame(registros)
    if os.path.exists(ARCHIVO_VENTAS):
        df_ventas = pd.read_csv(ARCHIVO_VENTAS)
        df_ventas = pd.concat([df_ventas, df_nuevas], ignore_index=True)
    else:
        df_ventas = df_nuevas
    df_ventas.to_csv(ARCHIVO_VENTAS, index=False)

def cargar_fiados():
    if os.path.exists(ARCHIVO_FIADOS):
        return pd.read_csv(ARCHIVO_FIADOS)
    else:
        return pd.DataFrame(columns=["Cliente", "Total_Deuda", "Ultimo_Abono", "Fecha_Ultimo_Movimiento"])

def guardar_fiados(df_fiados):
    df_fiados.to_csv(ARCHIVO_FIADOS, index=False)

# Función para generar el PDF en memoria
def generar_pdf_inventario(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1F2937"), spaceAfter=12
    )
    
    story.append(Paragraph("📦 REPORTE OFICIAL DE INVENTARIO", titulo_style))
    story.append(Spacer(1, 10))
    
    headers = ["ID", "Nombre", "Categoría", "P. Compra", "P. Venta", "Cant.", "Vencimiento"]
    data = [headers]
    
    for _, row in df.iterrows():
        data.append([
            str(row["ID"]),
            str(row["Nombre"]).upper(),
            str(row["Categoría"]).upper(),
            f"${row['Precio Compra']:,.2f}",
            f"${row['Precio Venta']:,.2f}",
            str(row["Cantidad"]),
            str(row.get("Fecha Vencimiento", ""))
        ])
    
    tabla = Table(data, colWidths=[50, 140, 90, 70, 70, 40, 70])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(tabla)
    doc.build(story)
    buffer.seek(0)
    return buffer

# Carga inicial de datos
df_inv = cargar_inventario()

if not df_inv.empty:
    df_inv["Precio Compra"] = pd.to_numeric(df_inv["Precio Compra"], errors="coerce").fillna(0)
    df_inv["Precio Venta"] = pd.to_numeric(df_inv["Precio Venta"], errors="coerce").fillna(0)
    df_inv["Cantidad"] = pd.to_numeric(df_inv["Cantidad"], errors="coerce").fillna(0).astype(int)

# Inicialización de estado de sesión para el Carrito de Ventas
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# Encabezado Principal
st.title("🏪 SISTEMA INTEGRAL DE ABARROTES")

# PESTAÑAS PRINCIPALES
tab_pos, tab_inv, tab_venc, tab_kardex, tab_prov, tab_fiados, tab_rep = st.tabs([
    "🛒 PUNTO DE VENTA (POS)",
    "📦 INVENTARIO & PRODUCTOS",
    "⏰ VENCIMIENTOS",
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
                            # Verificar si ya existe en el carrito
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
            
            metodo_pago = st.selectbox("Método de Pago:", ["EFECTIVO", "TRANSFERENCIA", "FIADO"])
            cliente_fiado = ""
            if metodo_pago == "FIADO":
                cliente_fiado = st.text_input("Nombre del Cliente (Fiado):").strip().upper()
                
            if st.button("✅ REGISTRAR VENTA", type="primary", use_container_width=True):
                if metodo_pago == "FIADO" and not cliente_fiado:
                    st.error("❌ Escribe el nombre del cliente para registrar el fiado.")
                else:
                    # Descontar de inventario y registrar en Kardex
                    for item in st.session_state.carrito:
                        id_item = item["ID"]
                        cant = item["Cantidad"]
                        df_inv.loc[df_inv["ID"] == id_item, "Cantidad"] -= cant
                        registrar_kardex(id_item, item["Nombre"], "VENTA" if metodo_pago != "FIADO" else "FIADO", cant, f"Venta {metodo_pago}")
                    
                    guardar_inventario(df_inv)
                    registrar_venta(st.session_state.carrito, metodo_pago, cliente_fiado)
                    
                    # Si es fiado, registrar/actualizar deuda
                    if metodo_pago == "FIADO":
                        df_f = cargar_fiados()
                        if cliente_fiado in df_f["Cliente"].values:
                            df_f.loc[df_f["Cliente"] == cliente_fiado, "Total_Deuda"] += total_pagar
                            df_f.loc[df_f["Cliente"] == cliente_fiado, "Fecha_Ultimo_Movimiento"] = datetime.now().strftime("%Y-%m-%d")
                        else:
                            nuevo_fiado = {
                                "Cliente": cliente_fiado,
                                "Total_Deuda": total_pagar,
                                "Ultimo_Abono": 0,
                                "Fecha_Ultimo_Movimiento": datetime.now().strftime("%Y-%m-%d")
                            }
                            df_f = pd.concat([df_f, pd.DataFrame([nuevo_fiado])], ignore_index=True)
                        guardar_fiados(df_f)
                    
                    st.session_state.carrito = []
                    st.success("🎉 ¡Venta realizada con éxito!")
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
            st.download_button("📄 Descargar PDF", data=pdf_data, file_name="Inventario.pdf", mime="application/pdf", use_container_width=True)

    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("El inventario está vacío.")

    st.divider()
    st.subheader("📝 FORMULARIO DE PRODUCTO (CREAR / EDITAR)")

    opciones = ["-- CREAR PRODUCTO NUEVO --"] + [f"{row['ID']} - {str(row['Nombre']).upper()}" for _, row in df_inv.iterrows()]
    seleccion = st.selectbox("SELECCIONA UN PRODUCTO PARA EDITAR:", opciones, key="select_producto")

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
        val_venc = str(prod.get("Fecha Vencimiento", ""))
        val_obs = str(prod["Observaciones"]).upper() if pd.notna(prod["Observaciones"]) else ""
    else:
        val_id, val_nombre, val_cat, val_compra, val_venta, val_cant, val_prov, val_venc, val_obs = "", "", "", "", "", "", "GENERAL", "", ""

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
            fecha_venc_in = st.text_input("FECHA VENCIMIENTO (AAAA-MM-DD)", value=val_venc, placeholder="Ej: 2026-12-31")
            observaciones = st.text_input("OBSERVACIONES", value=val_obs, placeholder="Notas...")

        modo_ingreso = "Sobrescribir / Modificar"
        if is_nuevo:
            modo_ingreso = st.radio(
                "SI EL ID YA EXISTE:",
                ["Sumar al stock y Promediar Costo de Compra", "Sobrescribir completamente"]
            )

        boton_guardar = st.form_submit_button("💾 GUARDAR PRODUCTO", use_container_width=True)

        if boton_guardar:
            id_ingresado = id_prod.strip().upper()
            if not id_ingresado or not nombre.strip() or not categoria.strip() or not precio_compra.strip() or not precio_venta.strip() or not cantidad.strip():
                st.error("❌ Completa los campos obligatorios (*).")
            else:
                try:
                    p_compra_nuevo = float(precio_compra.replace(",", "."))
                    p_venta_nuevo = float(precio_venta.replace(",", "."))
                    cant_nueva = int(cantidad)

                    existe = id_ingresado in df_inv["ID"].astype(str).values

                    if existe and is_nuevo and modo_ingreso.startswith("Sumar"):
                        prod_existente = df_inv[df_inv["ID"].astype(str) == id_ingresado].iloc[0]
                        cant_actual = int(prod_existente["Cantidad"])
                        p_compra_actual = float(prod_existente["Precio Compra"])

                        costo_total_acumulado = (cant_actual * p_compra_actual) + (cant_nueva * p_compra_nuevo)
                        cant_total = cant_actual + cant_nueva
                        nuevo_p_compra_promedio = costo_total_acumulado / cant_total if cant_total > 0 else p_compra_nuevo

                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Cantidad"] = cant_total
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Precio Compra"] = round(nuevo_p_compra_promedio, 2)
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Precio Venta"] = p_venta_nuevo
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Nombre"] = nombre.strip().upper()
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Categoría"] = categoria.strip().upper()
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Proveedor"] = proveedor.strip().upper()
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Fecha Vencimiento"] = fecha_venc_in.strip()
                        df_inv.loc[df_inv["ID"].astype(str) == id_ingresado, "Observaciones"] = observaciones.strip().upper()

                        guardar_inventario(df_inv)
                        registrar_kardex(id_ingresado, nombre, "ENTRADA", cant_nueva, "Compra Proveedor (Promediado)")
                        st.success(f"✅ Stock de '{nombre.upper()}' actualizado ({cant_total} unid).")
                        st.rerun()
                    else:
                        nuevo_registro = {
                            "ID": id_ingresado,
                            "Nombre": nombre.strip().upper(),
                            "Categoría": categoria.strip().upper(),
                            "Precio Compra": p_compra_nuevo,
                            "Precio Venta": p_venta_nuevo,
                            "Cantidad": cant_nueva,
                            "Proveedor": proveedor.strip().upper(),
                            "Fecha Vencimiento": fecha_venc_in.strip(),
                            "Observaciones": observaciones.strip().upper()
                        }
                        if existe:
                            df_inv = df_inv[df_inv["ID"].astype(str) != id_ingresado]
                        df_inv = pd.concat([df_inv, pd.DataFrame([nuevo_registro])], ignore_index=True)
                        guardar_inventario(df_inv)
                        registrar_kardex(id_ingresado, nombre, "ENTRADA" if is_nuevo else "AJUSTE", cant_nueva, "Registro manual")
                        st.success(f"✅ Producto '{nombre.upper()}' guardado.")
                        st.rerun()

                except ValueError:
                    st.error("❌ Los Precios y la Cantidad deben ser valores numéricos válidos.")

# ==========================================
# 3. CONTROL DE VENCIMIENTOS
# ==========================================
with tab_venc:
    st.subheader("⏰ Control y Alerta de Caducidad")
    if not df_inv.empty:
        hoy = date.today()
        proximos_7_dias = hoy + timedelta(days=7)
        
        df_venc = df_inv[df_inv["Fecha Vencimiento"].str.strip() != ""].copy()
        
        if not df_venc.empty:
            df_venc["Fecha_Obj"] = pd.to_datetime(df_venc["Fecha Vencimiento"], errors="coerce").dt.date
            df_venc = df_venc.dropna(subset=["Fecha_Obj"])
            
            vencidos = df_venc[df_venc["Fecha_Obj"] < hoy]
            por_vencer = df_venc[(df_venc["Fecha_Obj"] >= hoy) & (df_venc["Fecha_Obj"] <= proximos_7_dias)]
            
            c_v1, c_v2 = st.columns(2)
            with c_v1:
                st.markdown("### 🚨 Productos Vencidos")
                if not vencidos.empty:
                    st.dataframe(vencidos[["ID", "Nombre", "Cantidad", "Fecha Vencimiento"]], use_container_width=True, hide_index=True)
                else:
                    st.success("No hay productos vencidos.")
                    
            with c_v2:
                st.markdown("### ⚠️ Vencen en los próximos 7 días")
                if not por_vencer.empty:
                    st.warning(f"¡Atención! {len(por_vencer)} producto(s) por vencer. Considera ponerlos en oferta.")
                    st.dataframe(por_vencer[["ID", "Nombre", "Cantidad", "Fecha Vencimiento"]], use_container_width=True, hide_index=True)
                else:
                    st.success("No hay productos próximos a vencer esta semana.")
        else:
            st.info("No hay fechas de vencimiento registradas en los productos.")
    else:
        st.info("Inventario vacío.")

# ==========================================
# 4. KARDEX Y MOVIMIENTOS
# ==========================================
with tab_kardex:
    st.subheader("📜 Historial de Movimientos de Inventario (Kardex)")
    if os.path.exists(ARCHIVO_KARDEX):
        df_k = pd.read_csv(ARCHIVO_KARDEX)
        st.dataframe(df_k.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay movimientos registrados.")

# ==========================================
# 5. GESTIÓN DE PROVEEDORES
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
# 6. FIADOS / CRÉDITOS
# ==========================================
with tab_fiados:
    st.subheader("🤝 Control de Cuentas por Cobrar (Fiados)")
    df_f = cargar_fiados()
    
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
            
            if st.button("💾 Registrar Abono", use_container_width=True):
                deuda_actual = df_f.loc[df_f["Cliente"] == cli_sel, "Total_Deuda"].values[0]
                nueva_deuda = max(0.0, deuda_actual - monto_abono)
                
                df_f.loc[df_f["Cliente"] == cli_sel, "Total_Deuda"] = nueva_deuda
                df_f.loc[df_f["Cliente"] == cli_sel, "Ultimo_Abono"] = monto_abono
                df_f.loc[df_f["Cliente"] == cli_sel, "Fecha_Ultimo_Movimiento"] = datetime.now().strftime("%Y-%m-%d")
                
                guardar_fiados(df_f)
                st.success(f"Abono de ${monto_abono:,.2f} registrado para {cli_sel}. Nueva deuda: ${nueva_deuda:,.2f}")
                st.rerun()

# ==========================================
# 7. REPORTES Y CIERRE DE CAJA
# ==========================================
with tab_rep:
    st.subheader("📊 Cierre de Caja Diario y Reportes Financieros")
    
    if os.path.exists(ARCHIVO_VENTAS):
        df_v = pd.read_csv(ARCHIVO_VENTAS)
        
        fecha_filtro = st.date_input("Seleccionar Fecha de Cierre de Caja:", value=date.today())
        fecha_str = fecha_filtro.strftime("%Y-%m-%d")
        
        ventas_dia = df_v[df_v["Fecha"] == fecha_str]
        
        st.markdown(f"### 💵 Cierre de Caja del Día: **{fecha_str}**")
        
        if not ventas_dia.empty:
            total_efectivo = ventas_dia[ventas_dia["Metodo_Pago"] == "EFECTIVO"]["Total"].sum()
            total_transf = ventas_dia[ventas_dia["Metodo_Pago"] == "TRANSFERENCIA"]["Total"].sum()
            total_fiado = ventas_dia[ventas_dia["Metodo_Pago"] == "FIADO"]["Total"].sum()
            gran_total_dia = ventas_dia["Total"].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 Total Efectivo", f"${total_efectivo:,.2f}")
            c2.metric("💳 Total Transferencias", f"${total_transf:,.2f}")
            c3.metric("🤝 Total Fiados", f"${total_fiado:,.2f}")
            c4.metric("💰 INGRESOS TOTALES", f"${gran_total_dia:,.2f}")
            
            st.divider()
            st.markdown("### 📑 Detalle de Ventas del Día")
            st.dataframe(ventas_dia[["Fecha_Hora", "Producto", "Cantidad", "Total", "Metodo_Pago", "Cliente"]], use_container_width=True, hide_index=True)
        else:
            st.info(f"No hay ventas registradas para la fecha {fecha_str}.")
    else:
        st.info("Aún no se han registrado ventas en el sistema.")
