from nicegui import ui, app
import sqlite3
import random
import main
import cantina  # 🌟 IMPORTANTE: Conectamos el módulo de alimentación

def obtener_conexion_db():
    return sqlite3.connect(main.obtener_ruta_db())

# =========================================================================
# LÓGICA DE NEGOCIO Y BASE DE DATOS
# =========================================================================

def asegurar_tablas_finanzas():
    """Asegura que existan las tablas de contratos en la base de datos activa"""
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('balones_pinchados', 0)")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contratos_sponsors (
            sitio TEXT PRIMARY KEY, 
            marca TEXT NOT NULL,
            ingreso_millones INTEGER NOT NULL,
            duracion TEXT NOT NULL, 
            semanas_restantes INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contrato_television (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cadena TEXT UNIQUE, 
            ingreso_millones INTEGER NOT NULL,
            duracion TEXT NOT NULL,
            semanas_restantes INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jornada INTEGER NOT NULL,
            concepto TEXT NOT NULL,
            tipo TEXT NOT NULL,
            importe INTEGER NOT NULL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def obtener_contratos_activos():
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sitio, marca, ingreso_millones, semanas_restantes FROM contratos_sponsors")
    sponsors = cursor.fetchall()
    cursor.execute("SELECT cadena, ingreso_millones, semanas_restantes FROM contrato_television")
    tv = cursor.fetchone()
    conn.close()
    return sponsors, tv

def obtener_historial_caja():
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS historial_caja (id INTEGER PRIMARY KEY AUTOINCREMENT, jornada INTEGER NOT NULL, concepto TEXT NOT NULL, tipo TEXT NOT NULL, importe INTEGER NOT NULL DEFAULT 0)")
    cursor.execute("""
        SELECT jornada, concepto, tipo, SUM(importe)
        FROM historial_caja
        GROUP BY jornada, concepto, tipo
        ORDER BY jornada ASC, tipo DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

# =========================================================================
# OPERACIONES COMERCIALES
# =========================================================================

def lanzar_oferta_sponsor(contenedor_listado, funcion_refresco_caja):
    mi_equipo_id = main.obtener_mi_equipo_id()
    j_actual = main.obtener_jornada_actual()
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'oferta_sponsor_jornada'")
    res_guard = cursor.fetchone()
    if res_guard and int(res_guard[0]) == j_actual:
        conn.close()
        ui.notify('⛔ Ya has consultado las propuestas de sponsors esta jornada.', type='warning')
        return
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('oferta_sponsor_jornada', ?)", (j_actual,))
    conn.commit()
    
    # 📈 1. CALCULAR EL PRESTIGIO DEL CLUB (Tu posición en la tabla)
    cursor.execute("SELECT puntos FROM equipos WHERE id = ?", (mi_equipo_id,))
    res_pts = cursor.fetchone()
    mis_puntos = res_pts[0] if res_pts else 0
    
    # Buscamos cuántos puntos tiene el líder de la liga para comparar
    cursor.execute("SELECT MAX(puntos) FROM equipos")
    res_max = cursor.fetchone()
    max_puntos = res_max[0] if res_max and res_max[0] > 0 else 1
    conn.close()
    
    # Factor de éxito: 1.0 (si vas último o hay 0 puntos) hasta 2.0 (si eres el líder indiscutible)
    factor_prestigio = 1.0 + (1.0 * (mis_puntos / max_puntos))
    
    # 💼 2. GENERAR HASTA 3 OFERTAS COMERCIALES
    marcas = ["Cuchillería Rodríguez", "Simago", "Choleck", "Damel", "PapachiGym", "Calzados Kelme", "Villalobos"]
    sitios = ["Tribuna", "Preferencia", "Fondo Norte", "Fondo Sur", "En el Gorro"]
    
    num_ofertas = random.randint(1, 3)
    ofertas_generadas = []
    
    for _ in range(num_ofertas):
        marca = random.choice(marcas)
        sitio = random.choice(sitios)
        
        # El precio base se multiplica por tu caché actual
        precio_base = random.randrange(100000, 2000001, 50000)
        ingreso_final = int(precio_base * factor_prestigio)
        
        duracion = random.choice(["1 JORNADA", "TEMPORADA"])
        semanas = 1 if duracion == "1 JORNADA" else 22
        
        ofertas_generadas.append({
            "marca": marca, "sitio": sitio, "ingreso": ingreso_final, 
            "duracion": duracion, "semanas": semanas
        })

    # 🖥️ 3. CREAR LA INTERFAZ CON MÚLTIPLES OPCIONES
    with ui.dialog() as dlg, ui.card().classes('p-5 text-xs font-sans text-slate-900 w-[450px] bg-slate-50'):
        ui.label("💼 PROPUESTAS COMERCIALES").classes('font-bold text-sm text-indigo-900 tracking-wide')
        ui.separator().classes('my-2')
        
        # Si el equipo está en la zona noble, le sacamos pecho
        if factor_prestigio > 1.3:
            bonus = int((factor_prestigio - 1) * 100)
            ui.label(f"📈 Tu buena posición en la tabla atrae ofertas un {bonus}% más altas.").classes('text-[10px] text-emerald-600 font-bold mb-3')
            
        for oferta in ofertas_generadas:
            # Dibujamos una "tarjeta" para cada oferta recibida
            with ui.row().classes('w-full items-center justify-between bg-white p-3 rounded-lg border border-slate-200 shadow-sm mb-2'):
                
                # Datos del contrato (Izquierda)
                with ui.column().classes('gap-0 w-[65%]'):
                    ui.label(f"{oferta['marca']}").classes('font-bold text-slate-800 text-sm')
                    ui.label(f"Para: {oferta['sitio']} ({oferta['duracion']})").classes('text-[10px] text-slate-500 uppercase')
                    ing_str = f"{oferta['ingreso']:,}".replace(',', '.')
                    ui.label(f"+{ing_str} Pts / jornada").classes('font-mono font-bold text-indigo-600 mt-1')
                
                # Botón de Firmar (Derecha)
                boton_container = ui.row().classes('w-[30%] justify-end')
                with boton_container:
                    
                    # Función interna para atrapar los datos correctos al hacer clic en un bucle
                    def crear_evento_firma(datos, contenedor_boton):
                        def al_firmar():
                            conn = obtener_conexion_db()
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT OR REPLACE INTO contratos_sponsors (sitio, marca, ingreso_millones, duracion, semanas_restantes)
                                VALUES (?, ?, ?, ?, ?)
                            """, (datos['sitio'], datos['marca'], datos['ingreso'], datos['duracion'], datos['semanas']))
                            conn.commit()
                            conn.close()
                            
                            ui.notify(f"✍️ Acuerdo cerrado con {datos['marca']}", type='positive')
                            refrescar_visor_contratos(contenedor_listado)
                            funcion_refresco_caja()
                            
                            # Magia visual: Quitamos el botón y ponemos un sello de "FIRMADO"
                            contenedor_boton.clear()
                            with contenedor_boton:
                                ui.label("FIRMADO").classes('text-[10px] font-bold text-emerald-600 bg-emerald-100 px-2 py-1 rounded border border-emerald-300 shadow-inner')
                        return al_firmar
                    
                    ui.button("FIRMAR", on_click=crear_evento_firma(oferta, boton_container)).props('dense unelevated').classes('bg-indigo-600 text-white w-full text-[11px] font-bold')
        
        with ui.row().classes('w-full justify-center mt-3'):
            ui.button("CERRAR MALETÍN", on_click=dlg.close).props('flat').classes('text-slate-600 w-full bg-slate-200 rounded-lg text-xs font-bold hover:bg-slate-300')
    dlg.open()

def lanzar_oferta_tv(contenedor_listado, funcion_refresco_caja):
    mi_equipo_id = main.obtener_mi_equipo_id()
    j_actual = main.obtener_jornada_actual()
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'oferta_tv_jornada'")
    res_guard = cursor.fetchone()
    if res_guard and int(res_guard[0]) == j_actual:
        conn.close()
        ui.notify('⛔ Ya has consultado las ofertas de televisión esta jornada.', type='warning')
        return
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('oferta_tv_jornada', ?)", (j_actual,))
    conn.commit()
    
    # 📈 1. CALCULAR EL PRESTIGIO DEL CLUB (Tu posición en la clasificación)
    cursor.execute("SELECT puntos FROM equipos WHERE id = ?", (mi_equipo_id,))
    res_pts = cursor.fetchone()
    mis_puntos = res_pts[0] if res_pts else 0
    
    cursor.execute("SELECT MAX(puntos) FROM equipos")
    res_max = cursor.fetchone()
    max_puntos = res_max[0] if res_max and res_max[0] > 0 else 1
    conn.close()
    
    # Factor de éxito: Desde 1.0 (zona baja o inicio) hasta 2.0 (líder de la liga)
    factor_prestigio = 1.0 + (1.0 * (mis_puntos / max_puntos))
    
    # 📺 2. GENERAR HASTA 3 OFERTAS DE TELEVISIÓN
    cadenas = ["Teleelx", "Canal 9", "America TV", "Telecrvillent", "Tele Hit"]
    
    num_ofertas = random.randint(0, 2)
    ofertas_generadas = []
    
    # Evitamos que se repita la misma cadena en el mismo panel de ofertas de la jornada
    cadenas_elegidas = random.sample(cadenas, min(num_ofertas, len(cadenas)))
    
    for cadena in cadenas_elegidas:
        duracion = random.choice(["1 JORNADA", "TEMPORADA"])
        semanas = 1 if duracion == "1 JORNADA" else 22
        
        # Las televisiones manejan presupuestos más altos (Mínimo 300k, Máximo 3M base)
        precio_base = random.randrange(100000, 2000001, 100000)
        ingreso_final = int(precio_base * factor_prestigio)
        
        ofertas_generadas.append({
            "cadena": cadena, "ingreso": ingreso_final, 
            "duracion": duracion, "semanas": semanas
        })

    # 🖥️ 3. CREAR LA INTERFAZ CON EL LISTADO DE CADENAS (Estilo Fuchsia de TV)
    with ui.dialog() as dlg, ui.card().classes('p-5 text-xs font-sans text-slate-900 w-[450px] bg-slate-50'):
        ui.label("📺 DERECHOS DE TELEVISIÓN").classes('font-bold text-sm text-fuchsia-900 tracking-wide')
        ui.separator().classes('my-2')
        
        # Notificación de éxito si el club tiene buen rendimiento
        if factor_prestigio > 1.3:
            bonus = int((factor_prestigio - 1) * 100)
            ui.label(f"📈 El interés de las cadenas ha subido un {bonus}% debido a tus resultados.").classes('text-[10px] text-emerald-600 font-bold mb-3')
            
        for oferta in ofertas_generadas:
            with ui.row().classes('w-full items-center justify-between bg-white p-3 rounded-lg border border-slate-200 shadow-sm mb-2'):
                
                # Información de la oferta (Izquierda)
                with ui.column().classes('gap-0 w-[65%]'):
                    ui.label(f"{oferta['cadena'].upper()}").classes('font-bold text-slate-800 text-sm')
                    ui.label(f"Retransmisión: {oferta['duracion']}").classes('text-[10px] text-slate-500 uppercase')
                    ing_str = f"{oferta['ingreso']:,}".replace(',', '.')
                    ui.label(f"+{ing_str} Pts / jornada").classes('font-mono font-bold text-fuchsia-700 mt-1')
                
                # Botón de firma única (Derecha)
                boton_container = ui.row().classes('w-[30%] justify-end')
                with boton_container:
                    
                    def crear_evento_tv(datos):
                        def al_vender():
                            conn = obtener_conexion_db()
                            cursor = conn.cursor()
                            
                            # Al ser exclusiva, rompemos cualquier contrato de televisión anterior
                            cursor.execute("DELETE FROM contrato_television")
                            cursor.execute("""
                                INSERT INTO contrato_television (cadena, ingreso_millones, duracion, semanas_restantes)
                                VALUES (?, ?, ?, ?)
                            """, (datos['cadena'], datos['ingreso'], datos['duracion'], datos['semanas']))
                            
                            conn.commit()
                            conn.close()
                            
                            ui.notify(f"📺 Derechos vendidos a {datos['cadena']}", type='positive')
                            refrescar_visor_contratos(contenedor_listado)
                            funcion_refresco_caja()
                            
                            # Cerramos el diálogo completo porque ya hemos cubierto el único hueco disponible
                            dlg.close()
                        return al_vender
                    
                    ui.button("VENDER", on_click=crear_evento_tv(oferta)).props('dense unelevated').classes('bg-fuchsia-700 text-white w-full text-[11px] font-bold')
        
        with ui.row().classes('w-full justify-center mt-3'):
            ui.button("CERRAR MALETÍN", on_click=dlg.close).props('flat').classes('text-slate-600 w-full bg-slate-200 rounded-lg text-xs font-bold hover:bg-slate-300')
    dlg.open()
    
def refrescar_visor_contratos(contenedor):
    contenedor.clear()
    sponsors, tv = obtener_contratos_activos()
    
    with contenedor:
        for sit, marc, ing, sem in sponsors:
            with ui.row().classes('w-full justify-between bg-slate-50 p-2 rounded-lg border border-slate-100 items-center mb-1'):
                ui.label(f"• [{sit.upper()}] {marc}").classes('text-indigo-600 font-bold')
                
                # 🌟 TRUCO: Formateamos con comas y las cambiamos por puntos
                ing_str = f"{ing:,}".replace(',', '.')
                ui.label(f"+{ing_str} Pts/j ({sem}j)").classes('text-slate-500 font-mono')
                
        if tv:
            with ui.row().classes('w-full justify-between bg-slate-50 p-2 rounded-lg border border-fuchsia-100 items-center'):
                ui.label(f"📺 TV: {tv[0].upper()}").classes('text-fuchsia-600 font-bold')
                
                # 🌟 TRUCO: Lo mismo para la televisión
                tv_str = f"{tv[1]:,}".replace(',', '.')
                ui.label(f"+{tv_str} Pts/j ({tv[2]}j)").classes('text-slate-500 font-mono')
                
        if not sponsors and not tv:
            ui.label("Sin contratos comerciales activos.").classes('text-slate-400 text-center italic w-full py-2 text-[11px]')
# =========================================================================
# INTERFAZ PRINCIPAL (POPUP ANCHO DE DESPACHO)
# =========================================================================

def abrir_caja_y_decisiones():
    asegurar_tablas_finanzas()
    mi_equipo_id = main.obtener_mi_equipo_id()
    
    # 🌟 FUNCIÓN REACTIVA: Actualiza las etiquetas de fondos de la pantalla sobre la marcha
    def refrescar_datos_caja():
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute("SELECT presupuesto_pts FROM equipos WHERE id = ?", (mi_equipo_id,))
        res_presu = cursor.fetchone()
        presu = res_presu[0] if res_presu else 0
        
        cursor.execute("SELECT CAST(COALESCE(SUM(precio_pts) * 0.05, 0) AS INTEGER) FROM jugadores WHERE equipo_id = ?", (mi_equipo_id,))
        nominas = cursor.fetchone()[0]
        conn.close()
        
        lbl_presupuesto.set_text(f"{presu:,} Pts")
        lbl_gastos.set_text(f"-{nominas:,} Pts / jornada")

    def cambiar_estado_balones(switch_elem):
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'balones_pinchados'", (1 if switch_elem.value else 0,))
        conn.commit()
        conn.close()
        ui.notify("🎈 Configuración de esféricos modificada", type='warning')

    # Ventana extra ancha para alojar las 3 columnas cómodamente
    with ui.dialog() as dialogo, ui.card().classes('w-[1050px] max-w-7xl bg-slate-50 p-6 rounded-2xl shadow-xl font-sans text-slate-900'):
        
        # Cabecera
        with ui.row().classes('w-full border-b border-slate-100 pb-3 justify-between items-center'):
            with ui.column().classes('gap-0'):
                ui.label("💼 CAJA GENERAL, DECISIONES Y CATERING").classes('text-lg font-bold text-slate-800 tracking-tight')
                ui.label("Gestión presupuestaria, operaciones especiales y la cantina del club").classes('text-xs text-slate-400')
            ui.button(icon='close', on_click=dialogo.close).props('flat round dense').classes('text-slate-400')

        # CASILLERO CONTABLE PRINCIPAL
        with ui.row().classes('w-full bg-white p-4 rounded-xl border border-slate-100 justify-between items-center font-mono mt-2 shadow-sm'):
            with ui.column().classes('gap-0'):
                ui.label("PRESUPUESTO ACTUAL DEL CLUB").classes('text-[10px] text-slate-400 font-bold tracking-widest')
                lbl_presupuesto = ui.label("0 Pts").classes('text-2xl font-bold text-slate-800')
            with ui.column().classes('gap-0 items-end text-right'):
                ui.label("GASTO FIJO EN NÓMINAS (5%)").classes('text-[10px] text-slate-400 font-bold tracking-widest')
                lbl_gastos = ui.label("0 Ptas / jornada").classes('text-sm font-bold text-rose-500')

        # RELLENAR VALORES INICIALES DE CAJA
        refrescar_datos_caja()

        # =========================================================================
        # DISTRIBUCIÓN HORIZONTAL EN 3 COLUMNAS MÍTICAS
        # =========================================================================
        with ui.row().classes('w-full gap-4 mt-4 items-start justify-between'):
            
            # --- COLUMNA 1: OPERACIONES Y ENGAÑOS (w-[31%]) ---
            with ui.column().classes('w-[31%] bg-white border border-slate-100 rounded-xl p-4 shadow-sm'):
                ui.label("🕵️‍♂️ JUEGO SUCIO Y OPERACIONES").classes('text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-3')
                
                # Maletín arbitral
                with ui.column().classes('w-full p-3 bg-slate-50 border border-slate-100 rounded-xl mb-2 gap-1'):
                    ui.label("💼 Enviar maletín al árbitro").classes('text-xs font-bold text-slate-800')
                    ui.label("Suma +2 goles fantasma esta jornada").classes('text-[10px] text-slate-400 leading-tight mb-1')
                    
                    def comprar_arbitro():
                        coste_maletin = 5000000  # 5 milones de pesetas. ¡Súbelo si quieres que duela más!
                        
                        conn = obtener_conexion_db()
                        cursor = conn.cursor()
                        
                        # 1. Miramos si hay fondos en la caja del club
                        cursor.execute("SELECT presupuesto_pts FROM equipos WHERE id = ?", (mi_equipo_id,))
                        fondos_actuales = cursor.fetchone()[0]
                        
                        if fondos_actuales < coste_maletin:
                            ui.notify("❌ No hay dinero suficiente para sobornos. ¡Ahorra!", type='negative')
                            conn.close()
                            return
                        
                        # 2. Pagamos el soborno y activamos la trampa
                        cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - ? WHERE id = ?", (coste_maletin, mi_equipo_id))
                        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('favor_arbitral', 1)")
                        
                        conn.commit()
                        conn.close()
                        
                        frases_soborno = [
                            f"💼 Maletín de {coste_maletin:,} Ptas entregado. El linier mirará hacia otro lado.",
                            "⚖️ El árbitro respetará la legalidad vigente... codazo, codazo, guiño guiño.",
                            "🤝 Es un placer hacer negocios contigo.",
                            "🌹 Me ha hecho una oferta que no puedo rechazar.",
                            "💵 En billetes pequeños y sin marcar, por favor.",
                        ]
                        ui.notify(random.choice(frases_soborno), type='positive')
                        refrescar_datos_caja()  # 🌟 Actualizamos el dinero de la pantalla en tiempo real
                    
                    ui.button("COMPRAR (5M Ptas)", icon='monetization_on', on_click=comprar_arbitro).props('dense unelevated').classes('bg-amber-500 text-white text-xs w-full py-1 rounded-lg')
                # Balones Pinchados
                with ui.column().classes('w-full p-3 bg-slate-50 border border-slate-100 rounded-xl gap-1'):
                    ui.label("🎈 Jugar con balones pinchados").classes('text-xs font-bold text-slate-800')
                    ui.label("La calidad técnica influye un 30% menos").classes('text-[10px] text-slate-400 leading-tight mb-2')
                    
                    info_rival = main.obtener_proximo_rival_info()
                    es_local = "local" in str(info_rival[2]).lower()
                    
                    conn = obtener_conexion_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'balones_pinchados'")
                    esta_pinchado = cursor.fetchone()[0]
                    conn.close()

                    sw = ui.switch(value=bool(esta_pinchado), on_change=lambda e: cambiar_estado_balones(e)).props('dense color=emerald')
                    sw.set_visibility(es_local)
                    if not es_local:
                        ui.label("❌ SÓLO DISPONIBLE COMO LOCAL").classes('text-[9px] text-rose-500 font-bold font-mono')

            # --- 🌟 COLUMNA 2: LA CANTINA DE PAQUITA (w-[33%]) 🌟 ---
            with ui.column().classes('w-[33%] bg-white border border-slate-100 rounded-xl p-4 shadow-sm'):
                ui.label("🍔 LA CANTINA DE PAQUITA").classes('text-[10px] font-bold tracking-widest text-emerald-600 uppercase mb-3')
                
                # Extraemos la lista de jugadores sanos de tu plantilla para el desplegable
                conn = obtener_conexion_db()
                cursor = conn.cursor()
                cursor.execute("SELECT id, nombre FROM jugadores WHERE equipo_id = ? AND semanas_lesion = 0 ORDER BY nombre ASC", (mi_equipo_id,))
                lista_jugadores = cursor.fetchall()
                conn.close()
                
                opciones_jugadores = {j[0]: j[1].upper() for j in lista_jugadores}
                
                if opciones_jugadores:
                    ui.label("Selecciona el jugador a cebar:").classes('text-[10px] text-slate-500 font-semibold')
                    select_jugador = ui.select(options=opciones_jugadores, label="Elegir nadador").props('dense outlined').classes('w-full mb-2 text-xs')
                    
                    ui.label("Selecciona el menú calórico:").classes('text-[10px] text-slate-500 font-semibold')
                    opciones_menu = {
                        "choleck": "Choleck de Litro (150.000 Ptas / +2 Flot)",
                        "lomo": "Bocata de Lomo (350.000 Ptas / +5 Flot)",
                        "arroz": "Arroz con Costra Premium (750.000 Ptas / +12 Flot)"
                    }
                    select_comida = ui.select(options=opciones_menu, label="Elegir rancho").props('dense outlined').classes('w-full mb-3 text-xs')
                    
                    def ejecutar_comida():
                        j_id = select_jugador.value
                        comida_tipo = select_comida.value
                        if not j_id or not comida_tipo:
                            ui.notify("⚠️ Selecciona un jugador y un menú primero, míster", type='warning')
                            return
                        
                        # Ejecutamos la lógica oficial de cantina.py
                        resultado_texto = cantina.alimentar_jugador(j_id, mi_equipo_id, comida_tipo)
                        
                        if "❌" in resultado_texto:
                            ui.notify(resultado_texto, type='negative')
                        else:
                            ui.notify(resultado_texto, type='positive', icon='restaurant')
                            refrescar_datos_caja()  # 🌟 Sincronizamos la billetera en la pantalla
                    
                    ui.button("CEBAR JUGADOR", icon='restaurant', on_click=ejecutar_comida).props('unelevated').classes('bg-emerald-600 text-white text-xs w-full py-1.5 rounded-lg')
                else:
                    ui.label("No hay jugadores sanos disponibles en la disciplina.").classes('text-slate-400 italic text-[11px] py-4 text-center w-full')

            # --- COLUMNA 3: MARKETING Y CONTRATOS (w-[32%]) ---
            with ui.column().classes('w-[32%] bg-white border border-slate-100 rounded-xl p-4 shadow-sm'):
                ui.label("MARKETING Y CONTRATOS").classes('text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-3')
                
                with ui.row().classes('w-full gap-1 mb-3'):
                    ui.button("Sponsor", icon='ads_click', on_click=lambda: lanzar_oferta_sponsor(box_contratos, refrescar_datos_caja)).props('unelevated').classes('bg-indigo-600 text-white text-[11px] flex-1 py-1 rounded-lg')
                    ui.button("Derechos TV", icon='live_tv', on_click=lambda: lanzar_oferta_tv(box_contratos, refrescar_datos_caja)).props('unelevated').classes('bg-fuchsia-700 text-white text-[11px] flex-1 py-1 rounded-lg')
                
                ui.label("CONTRATOS VIGENTES").classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2')
                
                box_contratos = ui.column().classes('w-full gap-0.5')
                refrescar_visor_contratos(box_contratos)

        # =========================================================================
        # FLUJO DE CAJA — HISTÓRICO DE LA TEMPORADA
        # =========================================================================
        j_actual = main.obtener_jornada_actual()
        historial = obtener_historial_caja()

        with ui.column().classes('w-full bg-white border border-slate-100 rounded-xl p-4 shadow-sm mt-4 gap-2'):
            with ui.row().classes('w-full justify-between items-center mb-1'):
                ui.label('📊 FLUJO DE CAJA — HISTÓRICO DE LA TEMPORADA').classes('text-[10px] font-bold tracking-widest text-slate-400 uppercase')
                if j_actual > 1:
                    ui.label(f'Última jornada registrada: J{j_actual - 1}').classes('text-[10px] text-slate-400 font-mono')

            if not historial:
                ui.label('Aún no hay movimientos registrados. Se generan al avanzar jornada.').classes('text-slate-400 italic text-[11px] py-2 text-center w-full')
            else:
                total_ingresos = sum(imp for _, _, tipo, imp in historial if tipo == 'ingreso')
                total_gastos   = sum(imp for _, _, tipo, imp in historial if tipo == 'gasto')
                neto_total = total_ingresos - total_gastos

                cols_h = [
                    {'name': 'jornada',  'label': 'J',        'field': 'jornada',  'align': 'center', 'style': 'width:36px; font-weight:bold'},
                    {'name': 'concepto', 'label': 'CONCEPTO', 'field': 'concepto', 'align': 'left'},
                    {'name': 'ingreso',  'label': 'INGRESO',  'field': 'ingreso',  'align': 'right'},
                    {'name': 'gasto',    'label': 'GASTO',    'field': 'gasto',    'align': 'right'},
                ]
                rows_h = []
                for jornada, concepto, tipo, importe in historial:
                    rows_h.append({
                        'jornada':  jornada,
                        'concepto': concepto,
                        'ingreso':  f"+{importe:,} Ptas".replace(',', '.') if tipo == 'ingreso' else '',
                        'gasto':    f"-{importe:,} Ptas".replace(',', '.') if tipo == 'gasto'   else '',
                        'es_ultima': jornada == j_actual - 1,
                    })

                with ui.table(columns=cols_h, rows=rows_h, row_key='id').classes('w-full text-xs flat') as t_h:
                    t_h.add_slot('body-cell-ingreso', '''
                        <q-td :props="props" class="font-mono text-indigo-600 font-bold">
                            {{ props.value }}
                        </q-td>
                    ''')
                    t_h.add_slot('body-cell-gasto', '''
                        <q-td :props="props" class="font-mono text-rose-500 font-bold">
                            {{ props.value }}
                        </q-td>
                    ''')
                    t_h.add_slot('body-cell-jornada', '''
                        <q-td :props="props" :class="props.row.es_ultima ? 'bg-amber-50 text-amber-700 font-bold' : 'text-slate-500'">
                            J{{ props.value }}
                        </q-td>
                    ''')

                neto_color = 'text-emerald-600' if neto_total >= 0 else 'text-rose-700'
                signo = '+' if neto_total >= 0 else ''
                with ui.row().classes('w-full justify-end gap-6 mt-1 font-mono text-xs border-t border-slate-100 pt-2'):
                    ui.label(f"INGRESOS TOTALES: +{total_ingresos:,} Ptas".replace(',', '.')).classes('text-indigo-600 font-bold')
                    ui.label(f"GASTOS TOTALES: -{total_gastos:,} Ptas".replace(',', '.')).classes('text-rose-600 font-bold')
                    ui.label(f"NETO TEMPORADA: {signo}{neto_total:,} Ptas".replace(',', '.')).classes(f'font-bold text-sm {neto_color}')

        dialogo.open()