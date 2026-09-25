import streamlit as st
import pandas as pd
from datetime import datetime
import zoneinfo
import io
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ZONA HORARIA
# ---------------------------------------------------------
st.set_page_config(
    page_title="POS & Inventario Abarrotes",
    page_icon="🛒",
    layout="wide"
)

# Hora local de Colombia
BOGOTA_TZ = zoneinfo.ZoneInfo("America/Bogota")

def obtener_fecha_hora():
    now = datetime.now(BOGOTA_TZ)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

# URL oficial del Google Sheet del sistema
URL_SHEET = "https://docs.google.com/spreadsheets/d/1fqMOserbjbk72F74-mlA-3Qb6DhN0-gnQIbzZQL0eqQ/edit"

# Conexión persistente a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(worksheet_name):
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet=worksheet_name, ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def guardar_tabla(df, worksheet_name):
    try:
        conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar en {worksheet_name}: {e}")
        return False

# ---------------------------------------------------------
# INICIALIZACIÓN DE DATOS Y CARGA
# ---------------------------------------------------------
df_inventario = cargar_tabla("inventario")
df_ventas = cargar_tabla("ventas")
df_kardex = cargar_tabla("kardex")
df_fiados = cargar_tabla("fiados")
df_abonos = cargar_tabla("abonos")

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# ---------------------------------------------------------
# NAVEGACIÓN Y MENÚ PRINCIPAL
# ---------------------------------------------------------
st.title("🏪 Sistema de Control POS & Inventario - Abarrotes")

opcion = st.sidebar.radio(
    "Menú de Operaciones",
    ["🛒 Punto de Venta (POS)", "📦 Inventario & Productos", "👥 Fiados y Abonos", "📊 Kardex & Merma", "🔒 Cierre de Caja"]
)

# ---------------------------------------------------------
# 1. PUNTO DE VENTA (POS)
# ---------------------------------------------------------
if opcion == "🛒 Punto de Venta (POS)":
    st.header("🛒 Punto de Venta")
    
    if not df_inventario.empty:
        col_prod, col_carr = st.columns([1.5, 1])
        
        with col_prod:
            st.subheader("Seleccionar Productos")
            busqueda = st.text_input("🔍 Buscar por Código o Nombre").upper()
            
            df_fil = df_inventario.copy()
            if busqueda:
                df_fil = df_fil[
                    df_fil["ID"].astype(str).str.contains(busqueda) | 
                    df_fil["Producto"].astype(str).str.contains(busqueda)
                ]
            
            for idx, row in df_fil.iterrows():
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['Producto']}** (ID: {row['ID']})")
                c2.write(f"${row['Precio']:,.0f}")
                c3.write(f"Stock: {row['Stock']}")
                if c4.button("➕ Añadir", key=f"add_{row['ID']}"):
                    if row['Stock'] > 0:
                        st.session_state.carrito.append({
                            "ID": row['ID'],
                            "Producto": row['Producto'],
                            "Precio": float(row['Precio']),
                            "Cantidad": 1
                        })
                        st.success(f"Añadido {row['Producto']}")
                        st.rerun()
                    else:
                        st.error("Sin stock disponible.")
        
        with col_carr:
            st.subheader("🛒 Carrito de Compras")
            if st.session_state.carrito:
                df_c = pd.DataFrame(st.session_state.carrito)
                st.dataframe(df_c[["Producto", "Precio", "Cantidad"]], use_container_width=True)
                
                total = sum(item["Precio"] * item["Cantidad"] for item in st.session_state.carrito)
                st.markdown(f"### Total: **${total:,.0f}**")
                
                metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi/Daviplata", "Mixto", "A Crédito (Fiado)"])
                
                cliente_fiado = ""
                pago_efectivo, pago_digital = 0.0, 0.0
                
                if metodo_pago == "A Crédito (Fiado)":
                    cliente_fiado = st.text_input("Nombre del Cliente").upper()
                elif metodo_pago == "Mixto":
                    pago_efectivo = st.number_input("Monto en Efectivo ($)", min_value=0.0, max_value=float(total))
                    pago_digital = total - pago_efectivo
                    st.info(f"Monto Digital Restante: ${pago_digital:,.0f}")
                
                if st.button("✅ Registrar Venta", type="primary"):
                    fecha, hora = obtener_fecha_hora()
                    
                    # Desglose según método
                    efec = total if metodo_pago == "Efectivo" else (pago_efectivo if metodo_pago == "Mixto" else 0.0)
                    digi = total if metodo_pago == "Nequi/Daviplata" else (pago_digital if metodo_pago == "Mixto" else 0.0)
                    cred = total if metodo_pago == "A Crédito (Fiado)" else 0.0
                    
                    # Registrar venta
                    nueva_venta = pd.DataFrame([{
                        "Fecha": fecha,
                        "Hora": hora,
                        "Total": total,
                        "Efectivo": efec,
                        "Digital": digi,
                        "Credito": cred,
                        "Cliente": cliente_fiado,
                        "Metodo": metodo_pago
                    }])
                    
                    df_v_act = pd.concat([df_ventas, nueva_venta], ignore_index=True)
                    guardar_tabla(df_v_act, "ventas")
                    
                    # Actualizar Stock
                    for item in st.session_state.carrito:
                        p_idx = df_inventario[df_inventario["ID"].astype(str) == str(item["ID"])].index
                        if not p_idx.empty:
                            df_inventario.loc[p_idx[0], "Stock"] -= item["Cantidad"]
                    
                    guardar_tabla(df_inventario, "inventario")
                    
                    # Registrar Fiado si aplica
                    if metodo_pago == "A Crédito (Fiado)" and cliente_fiado:
                        nuevo_fiado = pd.DataFrame([{
                            "Fecha": fecha,
                            "Cliente": cliente_fiado,
                            "Monto_Inicial": total,
                            "Saldo_Pendiente": total,
                            "Estado": "PENDIENTE"
                        }])
                        df_f_act = pd.concat([df_fiados, nuevo_fiado], ignore_index=True)
                        guardar_tabla(df_f_act, "fiados")
                    
                    st.session_state.carrito = []
                    st.success("¡Venta completada con éxito!")
                    st.rerun()
                
                if st.button("🗑️ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
            else:
                st.info("El carrito está vacío.")
    else:
        st.warning("No se pudo cargar el inventario.")

# ---------------------------------------------------------
# 2. INVENTARIO Y PRODUCTOS
# ---------------------------------------------------------
elif opcion == "📦 Inventario & Productos":
    st.header("📦 Gestión de Inventario")
    
    t1, t2, t3 = st.tabs(["📋 Lista de Productos", "➕ Nuevo Producto", "⚙️ Editar / Eliminar"])
    
    with t1:
        st.dataframe(df_inventario, use_container_width=True)
        
    with t2:
        with st.form("f_nuevo"):
            c_id = st.text_input("Código / ID").upper()
            c_nom = st.text_input("Nombre del Producto").upper()
            c_cat = st.text_input("Categoría", value="GENERAL").upper()
            c_pre = st.number_input("Precio ($)", min_value=0.0, step=50.0)
            c_stk = st.number_input("Stock Inicial", min_value=0, step=1)
            
            if st.form_submit_button("Guardar"):
                if c_id and c_nom:
                    n_p = pd.DataFrame([{"ID": c_id, "Producto": c_nom, "Precio": c_pre, "Stock": c_stk, "Categoria": c_cat}])
                    df_i_act = pd.concat([df_inventario, n_p], ignore_index=True)
                    if guardar_tabla(df_i_act, "inventario"):
                        st.success("Producto creado.")
                        st.rerun()
    
    with t3:
        if not df_inventario.empty:
            l_ids = df_inventario["ID"].astype(str).tolist()
            sel_id = st.selectbox("Seleccionar Producto", l_ids)
            idx = df_inventario[df_inventario["ID"].astype(str) == sel_id].index[0]
            prod = df_inventario.loc[idx]
            
            e_nom = st.text_input("Nombre", value=str(prod["Producto"])).upper()
            e_pre = st.number_input("Precio", value=float(prod["Precio"]))
            e_stk = st.number_input("Stock", value=int(prod["Stock"]))
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Actualizar"):
                    df_inventario.loc[idx, "Producto"] = e_nom
                    df_inventario.loc[idx, "Precio"] = e_pre
                    df_inventario.loc[idx, "Stock"] = e_stk
                    guardar_tabla(df_inventario, "inventario")
                    st.success("Actualizado.")
                    st.rerun()
            with col_b2:
                confirmar_merma = st.checkbox("Confirmar baja/merma en Kardex")
                if st.button("Eliminar Producto", type="primary"):
                    if confirmar_merma:
                        fecha, hora = obtener_fecha_hora()
                        reg_kardex = pd.DataFrame([{
                            "Fecha": fecha,
                            "Hora": hora,
                            "Producto": prod["Producto"],
                            "Tipo": "MERMA/ELIMINACION",
                            "Cantidad": prod["Stock"],
                            "Observacion": "Baja de producto desde inventario"
                        }])
                        df_k_act = pd.concat([df_kardex, reg_kardex], ignore_index=True)
                        guardar_tabla(df_k_act, "kardex")
                    
                    df_act = df_inventario.drop(idx).reset_index(drop=True)
                    guardar_tabla(df_act, "inventario")
                    st.success("Producto eliminado.")
                    st.rerun()

# ---------------------------------------------------------
# 3. FIADOS Y ABONOS
# ---------------------------------------------------------
elif opcion == "👥 Fiados y Abonos":
    st.header("👥 Gestión de Créditos y Abonos")
    st.dataframe(df_fiados, use_container_width=True)
    
    st.subheader("Registrar Abono")
    if not df_fiados.empty:
        pendientes = df_fiados[df_fiados["Estado"] == "PENDIENTE"]
        if not pendientes.empty:
            cli_sel = st.selectbox("Seleccionar Cliente", pendientes["Cliente"].unique())
            monto_abono = st.number_input("Monto del Abono ($)", min_value=0.0, step=1000.0)
            
            if st.button("Registrar Abono"):
                fecha, hora = obtener_fecha_hora()
                f_idx = df_fiados[df_fiados["Cliente"] == cli_sel].index[0]
                
                saldo_act = float(df_fiados.loc[f_idx, "Saldo_Pendiente"]) - monto_abono
                df_fiados.loc[f_idx, "Saldo_Pendiente"] = max(0.0, saldo_act)
                if saldo_act <= 0:
                    df_fiados.loc[f_idx, "Estado"] = "PAGADO"
                
                guardar_tabla(df_fiados, "fiados")
                
                reg_abono = pd.DataFrame([{
                    "Fecha": fecha,
                    "Hora": hora,
                    "Cliente": cli_sel,
                    "Monto": monto_abono
                }])
                df_a_act = pd.concat([df_abonos, reg_abono], ignore_index=True)
                guardar_tabla(df_a_act, "abonos")
                st.success("Abono registrado correctamente.")
                st.rerun()

# ---------------------------------------------------------
# 4. KARDEX Y MERMA
# ---------------------------------------------------------
elif opcion == "📊 Kardex & Merma":
    st.header("📊 Registro de Movimientos y Mermas (Kardex)")
    st.dataframe(df_kardex, use_container_width=True)

# ---------------------------------------------------------
# 5. CIERRE DE CAJA Y REPORTES PDF
# ---------------------------------------------------------
elif opcion == "🔒 Cierre de Caja":
    st.header("🔒 Arqueo y Cierre Diario de Caja")
    fecha_hoy, _ = obtener_fecha_hora()
    
    v_hoy = df_ventas[df_ventas["Fecha"] == fecha_hoy] if not df_ventas.empty else pd.DataFrame()
    a_hoy = df_abonos[df_abonos["Fecha"] == fecha_hoy] if not df_abonos.empty else pd.DataFrame()
    
    tot_efectivo = v_hoy["Efectivo"].sum() if not v_hoy.empty else 0.0
    tot_digital = v_hoy["Digital"].sum() if not v_hoy.empty else 0.0
    tot_credito = v_hoy["Credito"].sum() if not v_hoy.empty else 0.0
    tot_abonos = a_hoy["Monto"].sum() if not a_hoy.empty else 0.0
    
    tot_caja = tot_efectivo + tot_digital + tot_abonos
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Efectivo Ventas", f"${tot_efectivo:,.0f}")
    m2.metric("Digital (Nequi/Daviplata)", f"${tot_digital:,.0f}")
    m3.metric("Abonos Cobrados", f"${tot_abonos:,.0f}")
    m4.metric("Créditos Otorgados", f"${tot_credito:,.0f}")
    
    st.markdown(f"### Total Recaudado en Caja: **${tot_caja:,.0f}**")
    
    # Generación de Reporte PDF en Memoria
    def generar_pdf_cierre():
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"<b>REPORTE DE CIERRE DE CAJA</b>", styles['Title']))
        elements.append(Paragraph(f"Fecha: {fecha_hoy} | Hora: {obtener_fecha_hora()[1]}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        datos = [
            ["Concepto", "Monto ($)"],
            ["Ventas Efectivo", f"${tot_efectivo:,.0f}"],
            ["Ventas Digitales", f"${tot_digital:,.0f}"],
            ["Abonos Recibidos", f"${tot_abonos:,.0f}"],
            ["Créditos (Fiados)", f"${tot_credito:,.0f}"],
            ["TOTAL RECAUDADO", f"${tot_caja:,.0f}"]
        ]
        
        t = Table(datos, colWidths=[200, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf_file = generar_pdf_cierre()
    st.download_button(
        label="📄 Descargar Cierre en PDF",
        data=pdf_file,
        file_name=f"cierre_caja_{fecha_hoy}.pdf",
        mime="application/pdf"
    )
