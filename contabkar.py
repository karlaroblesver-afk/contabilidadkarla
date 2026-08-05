import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Gestor Financiero Personal & Emprendimiento",
    page_icon="💰",
    layout="wide"
)

# --- CONFIGURACIÓN Y CREACIÓN DE LA BASE DE DATOS ---
def inicializar_bd():
    conexion = sqlite3.connect("finanzas_personales.db", check_same_thread=False)
    cursor = conexion.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            tipo TEXT,
            saldo REAL DEFAULT 0.0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            fuente TEXT,
            monto REAL,
            cuenta_id INTEGER,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            tipo TEXT,
            categoria TEXT,
            monto REAL,
            metodo_pago TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deudas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            monto_total REAL,
            monto_restante REAL,
            meses_totales INTEGER,
            meses_restantes INTEGER
        )
    """)
    
    conexion.commit()
    
    cuentas_iniciales = [
        ("Débito Personal", "debito", 0.0),
        ("Débito Ahorro", "ahorro", 0.0),
        ("Tarjeta de Crédito", "credito", 0.0)
    ]
    for nombre, tipo, saldo in cuentas_iniciales:
        cursor.execute("INSERT OR IGNORE INTO cuentas (nombre, tipo, saldo) VALUES (?, ?, ?)", (nombre, tipo, saldo))
    
    conexion.commit()
    conexion.close()

inicializar_bd()

def obtener_conexion():
    return sqlite3.connect("finanzas_personales.db", check_same_thread=False)

# --- ESTILOS VISUALES EN TONOS VERDES ---
st.markdown("""
    <style>
    .main {
        background-color: #f4f9f4;
    }
    h1, h2, h3 {
        color: #1b4332;
    }
    .stMetric {
        background-color: #e9f5ed;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2d6a4f;
    }
    </style>
""", unsafe_allow_html=True)

# --- MENÚ LATERAL ---
st.sidebar.title("🌿 Menú de Navegación")
menu = st.sidebar.radio("Selecciona una opción:", [
    "📊 Resumen Financiero", 
    "💵 Registrar Ingreso", 
    "🛒 Registrar Gasto", 
    "💳 Control de Deudas y MSI",
    "📈 Gráficas y Análisis",
    "⚙️ Ajustes / Borrar Datos"
])

# ==========================================
# 1. RESUMEN FINANCIERO
# ==========================================
if menu == "📊 Resumen Financiero":
    st.title("📊 Resumen Financiero Actual")
    st.write("Consulta el estado actual de tus cuentas, tus ingresos acumulados y tus deudas.")
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT saldo FROM cuentas WHERE nombre = 'Débito Personal'")
    deb_personal = cursor.fetchone()[0]
    
    cursor.execute("SELECT saldo FROM cuentas WHERE nombre = 'Débito Ahorro'")
    deb_ahorro = cursor.fetchone()[0]
    
    cursor.execute("SELECT saldo FROM cuentas WHERE tipo = 'credito'")
    t_credito = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(monto_restante) FROM deudas")
    res_deudas = cursor.fetchone()[0]
    deuda_total_msi = res_deudas if res_deudas else 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Débito Personal", value=f"${deb_personal:,.2f}")
    with col2:
        st.metric(label="Débito Ahorro", value=f"${deb_ahorro:,.2f}")
    with col3:
        st.metric(label="Tarjeta de Crédito", value=f"${t_credito:,.2f}")
    with col4:
        st.metric(label="Total Deudas / MSI", value=f"${deuda_total_msi:,.2f}")
        
    st.markdown("---")
    
    col_i, col_g = st.columns(2)
    with col_i:
        st.subheader("📥 Total Ingresos por Fuente")
        df_ingresos = pd.read_sql_query("SELECT fuente AS 'Fuente', SUM(monto) AS 'Total ($)' FROM ingresos GROUP BY fuente", conexion)
        if not df_ingresos.empty:
            st.dataframe(df_ingresos, use_container_width=True, hide_index=True)
        else:
            st.info("No hay ingresos registrados todavía.")
            
    with col_g:
        st.subheader("📤 Total Gastos por Tipo")
        df_gastos = pd.read_sql_query("SELECT tipo AS 'Tipo de Gasto', SUM(monto) AS 'Total ($)' FROM gastos GROUP BY tipo", conexion)
        if not df_gastos.empty:
            st.dataframe(df_gastos, use_container_width=True, hide_index=True)
        else:
            st.info("No hay gastos registrados todavía.")
            
    conexion.close()

# ==========================================
# 2. REGISTRAR INGRESO
# ==========================================
elif menu == "💵 Registrar Ingreso":
    st.title("💵 Registro de Ingresos")
    st.write("Registra tus entradas de dinero y decide si una parte va directo a abonar y reducir alguna de tus deudas.")
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, saldo FROM cuentas WHERE tipo != 'credito'")
    cuentas_disp = cursor.fetchall()
    
    cursor.execute("SELECT id, nombre, monto_restante FROM deudas WHERE monto_restante > 0")
    deudas_disp = cursor.fetchall()
    conexion.close()
    
    opciones_cuentas = {c[1]: c[0] for c in cuentas_disp}
    
    with st.form("form_ingreso"):
        fuente = st.selectbox("Fuente del Ingreso", ["Trabajo", "Pensión papá", "Emprendimiento"])
        monto = st.number_input("Monto total del ingreso ($)", min_value=0.0, format="%.2f")
        cuenta_elegida = st.selectbox("¿A qué cuenta de débito/ahorro cae este dinero?", list(opciones_cuentas.keys()))
        
        usar_para_deuda = st.checkbox("¿Quieres destinar parte de este ingreso a pagar alguna deuda?")
        
        deuda_elegida_id = None
        monto_para_deuda = 0.0
        if usar_para_deuda and deudas_disp:
            opciones_deudas = {f"{d[1]} (Restante: ${d[2]:,.2f})": d[0] for d in deudas_disp}
            deuda_texto = st.selectbox("Selecciona la deuda a abonar", list(opciones_deudas.keys()))
            deuda_elegida_id = opciones_deudas[deuda_texto]
            monto_para_deuda = st.number_input("¿Cuánto de este ingreso se irá a abonar a esta deuda?", min_value=0.0, max_value=monto, format="%.2f")
        elif usar_para_deuda and not deudas_disp:
            st.info("No tienes deudas activas registradas actualmente.")

        submit_ingreso = st.form_submit_button("Guardar Ingreso")
        
        if submit_ingreso:
            if monto > 0:
                if usar_para_deuda and monto_para_deuda > monto:
                    st.error("El monto para abonar a la deuda no puede ser mayor que el ingreso total.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    cuenta_id = opciones_cuentas[cuenta_elegida]
                    monto_a_cuenta = monto - monto_para_deuda
                    
                    conexion = obtener_conexion()
                    cursor = conexion.cursor()
                    cursor.execute("INSERT INTO ingresos (fecha, fuente, monto, cuenta_id) VALUES (?, ?, ?, ?)", 
                                   (fecha, fuente, monto, cuenta_id))
                    
                    if monto_a_cuenta > 0:
                        cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE id = ?", (monto_a_cuenta, cuenta_id))
                    
                    if usar_para_deuda and deuda_elegida_id and monto_para_deuda > 0:
                        cursor.execute("SELECT monto_restante, meses_restantes FROM deudas WHERE id = ?", (deuda_elegida_id,))
                        res_deuda = cursor.fetchone()
                        m_restante, m_meses = res_deuda
                        
                        nuevo_restante = max(0.0, m_restante - monto_para_deuda)
                        nuevos_meses = max(0, m_meses - 1) if nuevo_restante > 0 else 0
                        
                        cursor.execute("UPDATE deudas SET monto_restante = ?, meses_restantes = ? WHERE id = ?", 
                                       (nuevo_restante, nuevos_meses, deuda_elegida_id))
                    
                    conexion.commit()
                    conexion.close()
                    
                    st.success(f"¡Ingreso registrado! Se abonaron ${monto_para_deuda:,.2f} a tu deuda y ${monto_a_cuenta:,.2f} a tu cuenta.")
            else:
                st.error("Por favor, ingresa un monto mayor al 0.")

# ==========================================
# 3. REGISTRAR GASTO
# ==========================================
elif menu == "🛒 Registrar Gasto":
    st.title("🛒 Registro de Gastos")
    st.write("Controla tus salidas de dinero diarias.")
    
    with st.form("form_gasto"):
        tipo_gasto = st.selectbox("Tipo de Gasto", ["Personal", "Emprendimiento"])
        categoria = st.text_input("Categoría (ej. Comida, Insumos, Transporte)")
        monto = st.number_input("Monto del gasto ($)", min_value=0.0, format="%.2f")
        metodo_pago = st.selectbox("Método de Pago / Cuenta", ["Débito Personal", "Tarjeta de Crédito", "Efectivo/Otro"])
        
        submit_gasto = st.form_submit_button("Guardar Gasto")
        
        if submit_gasto:
            if monto > 0 and categoria.strip() != "":
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                conexion = obtener_conexion()
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO gastos (fecha, tipo, categoria, monto, metodo_pago) VALUES (?, ?, ?, ?, ?)", 
                               (fecha, tipo_gasto, categoria, monto, metodo_pago))
                
                if metodo_pago == "Tarjeta de Crédito":
                    cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE tipo = 'credito'", (monto,))
                elif metodo_pago == "Débito Personal":
                    cursor.execute("UPDATE cuentas SET saldo = saldo - ? WHERE nombre = 'Débito Personal'", (monto,))
                    
                conexion.commit()
                conexion.close()
                
                st.success(f"¡Gasto de ${monto:,.2f} guardado correctamente!")
            else:
                st.error("Asegúrate de llenar la categoría y un monto mayor a 0.")

# ==========================================
# 4. CONTROL DE DEUDAS Y MSI
# ==========================================
elif menu == "💳 Control de Deudas y MSI":
    st.title("💳 Control de Deudas y Meses Sin Intereses")
    st.write("Gestiona tus deudas y registra pagos descontándolos automáticamente de tus cuentas.")
    
    tab1, tab2 = st.tabs(["📋 Ver y Pagar Deudas", "➕ Registrar Nueva Deuda"])
    
    with tab1:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, monto_total, monto_restante, meses_totales, meses_restantes FROM deudas")
        deudas = cursor.fetchall()
        
        cursor.execute("SELECT id, nombre, saldo FROM cuentas WHERE tipo != 'credito'")
        cuentas_pago = cursor.fetchall()
        opciones_cuentas_pago = {c[1]: (c[0], c[2]) for c in cuentas_pago}
        
        if deudas:
            st.subheader("Tus deudas actuales:")
            for d in deudas:
                deuda_id, nombre, total, restante, m_tot, m_res = d
                
                with st.container():
                    col_d1, col_d2, col_d3 = st.columns([2, 2, 3])
                    with col_d1:
                        st.markdown(f"**{nombre}**")
                        st.text(f"Total: ${total:,.2f}")
                    with col_d2:
                        st.markdown(f"**Restante: ${restante:,.2f}**")
                        st.text(f"Meses faltantes: {m_res} de {m_tot}")
                    with col_d3:
                        with st.form(f"form_pago_{deuda_id}"):
                            pago_parcial = st.number_input(f"Abonar ($)", min_value=0.0, max_value=float(restante) if restante > 0 else 0.0, format="%.2f")
                            cuenta_origen = st.selectbox("Descontar de:", list(opciones_cuentas_pago.keys()))
                            
                            btn_pagar = st.form_submit_button(f"Registrar Pago")
                            
                            if btn_pagar:
                                if pago_parcial > 0:
                                    c_id, c_saldo = opciones_cuentas_pago[cuenta_origen]
                                    nuevo_restante = restante - pago_parcial
                                    nuevos_meses_res = max(0, m_res - 1) if nuevo_restante > 0 else 0
                                    
                                    cursor.execute("UPDATE deudas SET monto_restante = ?, meses_restantes = ? WHERE id = ?", (nuevo_restante, nuevos_meses_res, deuda_id))
                                    cursor.execute("UPDATE cuentas SET saldo = saldo - ? WHERE id = ?", (pago_parcial, c_id))
                                    
                                    conexion.commit()
                                    st.success(f"¡Pago de ${pago_parcial:,.2f} registrado!")
                                    st.rerun()
                                else:
                                    st.warning("Ingresa un monto válido.")
                    st.markdown("---")
        else:
            st.info("No tienes deudas registradas por ahora.")
            
        conexion.close()
        
    with tab2:
        with st.form("form_nueva_deuda"):
            nombre_deuda = st.text_input("¿Qué es? (Ej. iPhone a MSI, Préstamo, etc.)")
            monto_deuda = st.number_input("Monto total de la deuda ($)", min_value=0.0, format="%.2f")
            meses_deuda = st.number_input("Plazo total en meses", min_value=1, step=1)
            
            submit_deuda = st.form_submit_button("Guardar Deuda")
            
            if submit_deuda:
                if nombre_deuda.strip() != "" and monto_deuda > 0:
                    conexion = obtener_conexion()
                    cursor = conexion.cursor()
                    cursor.execute("INSERT INTO deudas (nombre, monto_total, monto_restante, meses_totales, meses_restantes) VALUES (?, ?, ?, ?, ?)", 
                                   (nombre_deuda, monto_deuda, monto_deuda, meses_deuda, meses_deuda))
                    conexion.commit()
                    conexion.close()
                    st.success(f"¡Deuda '{nombre_deuda}' registrada con éxito!")
                    st.rerun()
                else:
                    st.error("Llena el nombre y un monto válido.")

# ==========================================
# 5. GRÁFICAS Y ANÁLISIS
# ==========================================
elif menu == "📈 Gráficas y Análisis":
    st.title("📈 Gráficas Financieras")
    st.write("Análisis visual de tus finanzas en tonos verdes.")
    
    conexion = obtener_conexion()
    df_gastos = pd.read_sql_query("SELECT tipo, monto FROM gastos", conexion)
    df_ingresos = pd.read_sql_query("SELECT fuente, monto FROM ingresos", conexion)
    conexion.close()
    
    col_g1, col_g2 = st.columns(2)
    colores_verdes = ['#2d6a4f', '#52b788', '#74c69d', '#b7e4c7', '#95d5b2']
    
    with col_g1:
        st.subheader("Gastos: Personal vs Emprendimiento")
        if not df_gastos.empty:
            gasto_agrupado = df_gastos.groupby("tipo")["monto"].sum()
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#f4f9f4')
            ax.set_facecolor('#e9f5ed')
            gasto_agrupado.plot(kind='bar', color=['#2d6a4f', '#52b788'], ax=ax)
            ax.set_ylabel("Monto ($)", color='#1b4332')
            ax.set_xlabel("Tipo de Gasto", color='#1b4332')
            plt.xticks(rotation=0)
            ax.grid(axis='y', linestyle='--', alpha=0.5, color='#a3b18a')
            st.pyplot(fig)
        else:
            st.info("Aún no hay suficientes gastos para graficar.")
            
    with col_g2:
        st.subheader("Distribución de Ingresos")
        if not df_ingresos.empty:
            ingreso_agrupado = df_ingresos.groupby("fuente")["monto"].sum()
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#f4f9f4')
            ax.set_facecolor('#e9f5ed')
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#f4f9f4')
            ax.set_facecolor('#e9f5ed')
            ax.pie(ingreso_agrupado, labels=ingreso_agrupado.index, autopct='%1.1f%%', 
                   startangle=140, colors=colores_verdes[:len(ingreso_agrupado)],
                   textprops={'color': '#1b4332', 'weight': 'bold'})
            st.pyplot(fig)
        else:
            st.info("Aún no hay suficientes ingresos para graficar.")

# ==========================================
# 6. AJUSTES / BORRAR DATOS (NUEVO)
# ==========================================
elif menu == "⚙️ Ajustes / Borrar Datos":
    st.title("⚙️ Ajustes y Corrección de Datos")
    st.write("Si metiste información por error o quieres borrar deudas de prueba, hazlo desde aquí.")
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # 1. Borrar Deudas Individuales
    st.subheader("🗑️ Eliminar una Deuda Específica")
    cursor.execute("SELECT id, nombre, monto_restante FROM deudas")
    deudas_borrar = cursor.fetchall()
    
    if deudas_borrar:
        opciones_borrar_deuda = {f"{d[1]} (Restante: ${d[2]:,.2f})": d[0] for d in deudas_borrar}
        deuda_a_eliminar = st.selectbox("Selecciona la deuda que deseas borrar por completo", list(opciones_borrar_deuda.keys()))
        
        if st.button("Eliminar esta deuda seleccionada"):
            id_del = opciones_borrar_deuda[deuda_a_eliminar]
            cursor.execute("DELETE FROM deudas WHERE id = ?", (id_del,))
            conexion.commit()
            st.success(f"¡La deuda '{deuda_a_eliminar}' ha sido borrada con éxito!")
            st.rerun()
    else:
        st.info("No hay deudas registradas para borrar.")
        
    st.markdown("---")
    
    # 2. Reiniciar Cuentas a 0
    st.subheader("🔄 Reiniciar Saldos de Cuentas")
    st.write("Si tus saldos o deudas de tarjeta de crédito se descuadraron por pruebas, puedes ponerlos a $0.00 de nuevo.")
    if st.button("Restablecer todas las cuentas y tarjetas a $0.00"):
        cursor.execute("UPDATE cuentas SET saldo = 0.0")
        conexion.commit()
        st.success("¡Todas las cuentas se han restablecido a cero!")
        st.rerun()
        
    conexion.close()
