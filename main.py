from nicegui import ui, app
import sqlite3
import os
import random
import cantina
import simulador_liga
import escudos
import mercado
import shutil
import alineacion
import diario
import configuracion
import finanzas

DB_RAIZ = "munonbol_elche_95.db"
DB_PARTIDA = "munonbol_partida.db"

ui.add_head_html('<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">', shared=True)
app.add_static_files('/img', 'img')
# =========================================================================
# SISTEMA DE AUTO-REPARACIÓN DE LA BASE DE DATOS
# =========================================================================
def asegurar_infraestructura_db():
    # 1. 🌟 USAMOS LA RUTA DINÁMICA (Para que actúe sobre la partida, no sobre el molde sagrado)
    db_path = obtener_ruta_db() 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor INTEGER
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada_actual', 1)")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('temporada_actual', 0)")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jornada INTEGER NOT NULL,
            local_id INTEGER NOT NULL,
            visita_id INTEGER NOT NULL,
            goles_local INTEGER,
            goles_visita INTEGER,
            jugado INTEGER DEFAULT 0
        )
    ''')
    
    # Comprobamos las columnas reales de tu tabla de jugadores
    cursor.execute("PRAGMA table_info(jugadores)")
    columnas_j = [col[1] for col in cursor.fetchall()]
    
    if "goles" not in columnas_j:
        cursor.execute("ALTER TABLE jugadores ADD COLUMN goles INTEGER DEFAULT 0")
    if "est_actif" not in columnas_j:
        cursor.execute("ALTER TABLE jugadores ADD COLUMN est_actif INTEGER DEFAULT 1")
    if "titular" not in columnas_j:
        cursor.execute("ALTER TABLE jugadores ADD COLUMN titular INTEGER DEFAULT 0")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ofertas_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador_id INTEGER NOT NULL,
            equipo_comprador_id INTEGER,
            nombre_comprador TEXT,
            importe INTEGER,
            jornada INTEGER
        )
    ''')

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
    
    # 2. 🌟 ASEGURAMOS LAS COLUMNAS DE LIGAS EN EQUIPOS
    cursor.execute("PRAGMA table_info(equipos)")
    columnas_e = [col[1] for col in cursor.fetchall()]
    if "division" not in columnas_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN division TEXT DEFAULT 'Liga SuperEmpanadill'")
    if "estadio" not in columnas_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN estadio TEXT DEFAULT 'Piscina Municipal'")
    conn.commit()

    # 3. 🌟 SEPARACIÓN QUIRÚRGICA DE LIGAS (12 en Primera, 5 en Segunda)
    cursor.execute("SELECT id FROM equipos")
    todos_los_equipos = [r[0] for r in cursor.fetchall()]
    
    for pos, eq_id in enumerate(todos_los_equipos):
        if pos < 12:
            cursor.execute("UPDATE equipos SET division = 'Liga SuperEmpanadill' WHERE id = ?", (eq_id,))
        else:
            cursor.execute("UPDATE equipos SET division = 'Liga Mandinga' WHERE id = ?", (eq_id,))
    
 
    


    conn.commit()

    # NOTA: Quitamos el UPDATE masivo de est_actif para que no rompa tu configuración
    
    conn.commit()
    conn.close()


# =========================================================================
# GESTIÓN DE BASE DE DATOS Y PARTIDAS DINÁMICAS
# =========================================================================

def obtener_ruta_db():
    """
    Función crucial: El resto del juego (mercado, partidos, clasificaciones) 
    debe usar SIEMPRE 'obtener_ruta_db()' en sus conexiones en lugar de un texto fijo.
    Si existe una partida en curso, lee la de batalla; si no, apunta a la raíz.
    """
    if os.path.exists(DB_PARTIDA):
        return DB_PARTIDA
    return DB_RAIZ

def inicializar_nueva_partida():
    """
    Copia la base de datos raíz y fuerza la reestructuración de divisiones
    para que la Liga SuperEmpanadill tenga exactamente 12 equipos antes de simular.
    """
    if not os.path.exists(DB_RAIZ):
        ui.notify(f"❌ Error crítico: ¡No se encuentra la base de datos raíz ({DB_RAIZ})!", type='negative')
        return False
        
    try:
        # 1. Hacemos la copia física limpia del molde original
        shutil.copyfile(DB_RAIZ, DB_PARTIDA)
        
        # 2. Abrimos conexión sobre la PARTIDA NUEVA para aplicar el filtro de la federación
        conn = sqlite3.connect(DB_PARTIDA)
        cursor = conn.cursor()
        
        # Seteamos la jornada inicial
        cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave = 'jornada_actual'")
        
        # Conseguimos todos los equipos existentes (los 17)
        cursor.execute("SELECT id FROM equipos")
        todos_los_clubes = [row[0] for row in cursor.fetchall()]
        
        # REPARACIÓN RIGUROSA: Mandamos los 12 primeros a Primera y los 5 restantes a Segunda
        for posicion, eq_id in enumerate(todos_los_clubes):
            if posicion < 12:
                cursor.execute("UPDATE equipos SET division = 'Liga SuperEmpanadill' WHERE id = ?", (eq_id,))
            else:
                cursor.execute("UPDATE equipos SET division = 'Liga Mandinga' WHERE id = ?", (eq_id,))
                
        # 1. Limpiamos a fondo los jugadores de fábrica para la nueva pretemporada
        cursor.execute("UPDATE jugadores SET goles = 0, semanas_lesion = 0, lesion_id = NULL, a_la_venta = 0")
        
        # 2. Reseteamos los marcadores de la tabla de equipos
        cursor.execute("UPDATE equipos SET puntos = 0, goles_favor = 0, goles_contra = 0")
        
        # 3. Limpiamos ofertas residuales heredadas de la root DB
        cursor.execute("DELETE FROM ofertas_pendientes")
        
        conn.commit()
        conn.close()
        
        # 3. Lanzamos el simulador para que genere el fixture Round Robin con los 12 filtrados
        mensaje_calendario = simulador_liga.generar_calendario_liga()
        print(mensaje_calendario) # Verificación en la consola de comandos
        
        ui.notify("⚽ ¡Temporada inicializada con 12 equipos en Primera!", type='positive')
        asegurar_infraestructura_db()
        return True
        
    except Exception as e:
        ui.notify(f"❌ Error al clonar el universo: {e}", type='negative')
        return False

# 🌟 SE HAN ELIMINADO LAS DEFINICIONES REPETIDAS QUE MACHACABAN EL CÓDIGO 🌟

def obtener_mi_equipo_id(): 
    return app.storage.user.get('id_equipo_seleccionado', 2)

def obtener_datos_partida_guardada():
    """Devuelve (equipo_id, equipo_nombre) del save activo, o (None, None) si no existe."""
    if not os.path.exists(DB_PARTIDA):
        return None, None
    try:
        conn = sqlite3.connect(DB_PARTIDA)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'equipo_jugador'")
        res = cursor.fetchone()
        if not res:
            conn.close()
            return None, None
        eq_id = res[0]
        cursor.execute("SELECT nombre FROM equipos WHERE id = ?", (eq_id,))
        nombre = cursor.fetchone()
        conn.close()
        return eq_id, (nombre[0] if nombre else 'Equipo desconocido')
    except Exception:
        return None, None

def obtener_jornada_actual():
    # Ahora usa la función inteligente de arriba de forma garantizada
    conn = sqlite3.connect(obtener_ruta_db())
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada_actual'")
    res = cursor.fetchone()
    jornada = res[0] if res else 1
    conn.close()
    return jornada

def avanzar_jornada_db():
    j_actual = obtener_jornada_actual()
    db_path = obtener_ruta_db()
    my_eq_id = obtener_mi_equipo_id()
    if j_actual < 22:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Avanzamos la jornada liguera
        cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'jornada_actual'")
        
        # 2. 💰 INGRESO COMERCIAL SEMANAL: Sumamos patrocinadores y TV al presupuesto_pts del usuario
        cursor.execute("CREATE TABLE IF NOT EXISTS contratos_sponsors (sitio TEXT PRIMARY KEY, marca TEXT NOT NULL, ingreso_millones INTEGER NOT NULL, duracion TEXT NOT NULL, semanas_restantes INTEGER NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS contrato_television (id INTEGER PRIMARY KEY AUTOINCREMENT, cadena TEXT UNIQUE, ingreso_millones INTEGER NOT NULL, duracion TEXT NOT NULL, semanas_restantes INTEGER NOT NULL)")
        cursor.execute("SELECT SUM(ingreso_millones) FROM contratos_sponsors")
        total_sponsors = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(ingreso_millones) FROM contrato_television")
        total_tv = cursor.fetchone()[0] or 0
        
        ingreso_total_pesetas = total_sponsors + total_tv
        if ingreso_total_pesetas > 0:
            cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + ? WHERE id = ?", (ingreso_total_pesetas, my_eq_id))
        
        # 3. 💸 COBRO AUTOMÁTICO DE NÓMINAS: Cada club paga a la federación el 5% del valor de sus fichas
        cursor.execute("SELECT CAST(COALESCE(SUM(precio_pts) * 0.05, 0) AS INTEGER) FROM jugadores WHERE equipo_id = ?", (my_eq_id,))
        nominas_usuario = cursor.fetchone()[0] or 0
        cursor.execute("""
            UPDATE equipos 
            SET presupuesto_pts = presupuesto_pts - (
                SELECT CAST(COALESCE(SUM(precio_pts) * 0.05, 0) AS INTEGER)
                FROM jugadores 
                WHERE jugadores.equipo_id = equipos.id
            )
        """)
        
        # 4. ⏳ CONTROL DE CONTRATOS TEMPORALES
        cursor.execute("UPDATE contratos_sponsors SET semanas_restantes = semanas_restantes - 1")
        cursor.execute("DELETE FROM contratos_sponsors WHERE semanas_restantes <= 0")
        
        cursor.execute("UPDATE contrato_television SET semanas_restantes = semanas_restantes - 1")
        cursor.execute("DELETE FROM contrato_television WHERE semanas_restantes <= 0")
        
        # 5. 🧼 LIMPIEZA DE OPERACIONES ESPECIALES RECIENTES
        cursor.execute("UPDATE configuracion SET valor = 0 WHERE clave = 'balones_pinchados'")
        
        # 6. Actualización médica estándar
        cursor.execute("UPDATE jugadores SET semanas_lesion = semanas_lesion - 1 WHERE semanas_lesion > 0")
        cursor.execute("UPDATE jugadores SET lesion_id = NULL WHERE semanas_lesion = 0 AND lesion_id IS NOT NULL")

        # 7. 📒 HISTORIAL DE CAJA
        cursor.execute("""CREATE TABLE IF NOT EXISTS historial_caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jornada INTEGER NOT NULL,
            concepto TEXT NOT NULL,
            tipo TEXT NOT NULL,
            importe INTEGER NOT NULL DEFAULT 0
        )""")
        ing_sponsors = total_sponsors
        ing_tv = total_tv
        if ing_sponsors > 0:
            cursor.execute("INSERT INTO historial_caja (jornada, concepto, tipo, importe) VALUES (?, 'Sponsors', 'ingreso', ?)", (j_actual, ing_sponsors))
        if ing_tv > 0:
            cursor.execute("INSERT INTO historial_caja (jornada, concepto, tipo, importe) VALUES (?, 'Derechos TV', 'ingreso', ?)", (j_actual, ing_tv))
        if nominas_usuario > 0:
            cursor.execute("INSERT INTO historial_caja (jornada, concepto, tipo, importe) VALUES (?, 'Nóminas (5%)', 'gasto', ?)", (j_actual, nominas_usuario))

        conn.commit()
        conn.close()

        import mercado
        mercado.simular_movimientos_cpu(my_eq_id, j_actual)
        mercado.simular_movimientos_cpu_entrenadores(my_eq_id, j_actual)
    elif j_actual == 22:
        # EL VERANO YA LLEGO
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada_actual'")
        r_temp = cursor.fetchone()
        temporada_copa = int(r_temp[0]) if r_temp else 1
        cursor.execute("UPDATE configuracion SET valor = 23 WHERE clave = 'jornada_actual'")
        conn.commit()
        conn.close()
        import copa as copa_mod
        copa_mod.inicializar_copa(temporada_copa)
        campeon_id = copa_mod.simular_copa_completa(temporada_copa)
        if campeon_id:
            conn_n = sqlite3.connect(db_path)
            cur_n = conn_n.cursor()
            cur_n.execute("SELECT nombre FROM equipos WHERE id = ?", (campeon_id,))
            nom_camp = cur_n.fetchone()
            conn_n.close()
            nombre_camp = nom_camp[0].upper() if nom_camp else "Desconocido"
            ui.notify(f"🏆 Copa Intermuñonal: ¡{nombre_camp} es el campeón! Consulta el Diario.", type='positive', timeout=8000)
    elif j_actual >= 23:
        # EL FINAL... DEEEEL VERAAANOOO
        procesar_cambio_de_temporada()

def procesar_cambio_de_temporada():
    """Ejecuta el cierre de año, aplica descensos/ascensos, reparte premios y prepara la nueva liga."""
    db_path = obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # =========================================================================
    # 📉 FASE 1: DESCENSOS Y ASCENSOS (¡Se ejecuta antes de borrar los puntos!)
    # =========================================================================
    
    # 1. Localizamos los 2 peores equipos de Primera (Liga SuperEmpanadill)
    cursor.execute("""
        SELECT id FROM equipos 
        WHERE division = 'Liga SuperEmpanadill' 
        ORDER BY puntos ASC, (goles_favor - goles_contra) ASC 
        LIMIT 2
    """)
    descendidos = [row[0] for row in cursor.fetchall()]

    # 2. Localizamos los 2 mejores equipos de Segunda (Liga Mandinga)
    cursor.execute("""
        SELECT id FROM equipos 
        WHERE division = 'Liga Mandinga' 
        ORDER BY puntos DESC, (goles_favor - goles_contra) DESC 
        LIMIT 2
    """)
    ascendidos = [row[0] for row in cursor.fetchall()]

    # 3. Intercambiamos las categorías en la base de datos
    for eq_id in descendidos:
        cursor.execute("UPDATE equipos SET division = 'Liga Mandinga' WHERE id = ?", (eq_id,))
        
    for eq_id in ascendidos:
        cursor.execute("UPDATE equipos SET division = 'Liga SuperEmpanadill' WHERE id = ?", (eq_id,))
        
    # =========================================================================
    # 🔄 FASE 2: RESETEO ANUAL Y PREPARACIÓN DE LA NUEVA TEMPORADA
    # =========================================================================
    
    # 4. Sumamos un año al calendario de la federación
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'temporada_actual'")
    
    # 5. Devolvemos el marcador de semanas a la Jornada 1
    cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave = 'jornada_actual'")
    
    # 6. 💰 REPARTO DE PREMIOS: Inyectamos presupuesto extra según los puntos conseguidos en Primera
    cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + (puntos * 200000) WHERE division = 'Liga SuperEmpanadill'")
    
    # 7. 🧼 LIMPIEZA DE TABLAS: Puntos y goles de los clubes vuelven a cero
    cursor.execute("UPDATE equipos SET puntos = 0, goles_favor = 0, goles_contra = 0")
    
    # 8. 🏥 ALTA SANITARIA Y PICHICHI: Goles individuales a cero y lesionados curados (Las plantillas se mantienen)
    cursor.execute("UPDATE jugadores SET goles = 0, semanas_lesion = 0, lesion_id = NULL")
    
    conn.commit()
    conn.close()
    
    # 9. 📅 NUEVO SORTEO: Regeneramos el fixture Round Robin con los nuevos 12 integrantes de Primera
    import simulador_liga
    simulador_liga.generar_calendario_liga()
    
    ui.notify("🔄 ¡CAMBIO DE TEMPORADA! Se han tramitado los ascensos y descensos oficiales.", type='info')

def volver_al_menu_principal():
    # 🧹 Limpiamos el rastro del equipo seleccionado en la sesión activa
    app.storage.user.pop('id_equipo_seleccionado', None)
    app.storage.user.pop('equipo_id', None)
    
    # 🚀 Navegamos de vuelta a la raíz (el selector de clubes / portada)
    ui.navigate.to('/')

def simular_fichajes_ia():
    """Con 30% de probabilidad, un equipo IA ficha un jugador de otro equipo IA. Máx 8 por temporada."""
    db_path = obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'fichajes_ia_temporada'")
    row = cursor.fetchone()
    total = row[0] if row else 0
    if total >= 8 or random.random() > 0.30:
        conn.close()
        return

    mi_eq_id = obtener_mi_equipo_id()
    cursor.execute("SELECT id FROM equipos WHERE id != ?", (mi_eq_id,))
    equipos_ia = [r[0] for r in cursor.fetchall()]
    random.shuffle(equipos_ia)

    for comprador_id in equipos_ia:
        cursor.execute("SELECT presupuesto_pts FROM equipos WHERE id = ?", (comprador_id,))
        presupuesto = cursor.fetchone()[0] or 0
        cursor.execute("""
            SELECT id, nombre, equipo_id, precio_pts FROM jugadores
            WHERE equipo_id != ? AND equipo_id != ? AND equipo_id IS NOT NULL
              AND precio_pts > 0 AND precio_pts <= ? AND semanas_lesion = 0
            ORDER BY RANDOM() LIMIT 1
        """, (comprador_id, mi_eq_id, presupuesto))
        jugador = cursor.fetchone()
        if jugador:
            j_id, j_nombre, vendedor_id, precio = jugador
            cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - ? WHERE id = ?", (precio, comprador_id))
            cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + ? WHERE id = ?", (precio, vendedor_id))
            cursor.execute("UPDATE jugadores SET equipo_id = ?, titular = 0 WHERE id = ?", (comprador_id, j_id))
            cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('fichajes_ia_temporada', ?)", (total + 1,))
            conn.commit()
            print(f"[MERCADO IA] {j_nombre} fichado por equipo {comprador_id} por {precio} pts (fichaje {total+1}/8)")
            break

    conn.close()

def auto_completar_plantillas():
    """Para cada equipo: mueve titulares lesionados al banco y rellena slots vacantes con suplentes sanos."""
    db_path = obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM equipos")
    equipos = [r[0] for r in cursor.fetchall()]
    for eq_id in equipos:
        cursor.execute("UPDATE jugadores SET titular = 0 WHERE equipo_id = ? AND titular > 0 AND semanas_lesion > 0", (eq_id,))
        cursor.execute("UPDATE jugadores SET titular = 0 WHERE equipo_id = ? AND (titular < 1 OR titular > 5) AND titular != 0", (eq_id,))
        cursor.execute("SELECT titular FROM jugadores WHERE equipo_id = ? AND titular BETWEEN 1 AND 5 AND semanas_lesion = 0", (eq_id,))
        slots_ocupados = {r[0] for r in cursor.fetchall()}
        cursor.execute("SELECT id FROM jugadores WHERE equipo_id = ? AND titular = 0 AND semanas_lesion = 0 ORDER BY id", (eq_id,))
        suplentes = [r[0] for r in cursor.fetchall()]
        idx = 0
        for slot in range(1, 6):
            if slot not in slots_ocupados and idx < len(suplentes):
                cursor.execute("UPDATE jugadores SET titular = ? WHERE id = ?", (slot, suplentes[idx]))
                idx += 1
    conn.commit()
    conn.close()

def obtener_proximo_rival_info():
    db_path = obtener_ruta_db()
    eq_id = obtener_mi_equipo_id()
    j_actual = obtener_jornada_actual()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.local_id, p.visita_id, el.nombre, ev.nombre
        FROM partidos p
        JOIN equipos el ON p.local_id = el.id
        JOIN equipos ev ON p.visita_id = ev.id
        WHERE p.jornada = ? AND (p.local_id = ? OR p.visita_id = ?)
    ''', (j_actual, eq_id, eq_id))
    partido = cursor.fetchone()
    conn.close()
    
    if not partido: return "🏁 Fin de la Liga", 0, ""
    loc_id, vis_id, nom_l, nom_v = partido
    if loc_id == eq_id:
        return f"Rival: {nom_v.upper()} (En Casa)", vis_id, "local"
    else:
        return f"Rival: {nom_l.upper()} (Fuera)", loc_id, "visita"
# =========================================================================
# ESTILOS RETRO CORPORATIVOS (Gris Industrial y Marcos Biselados)
# =========================================================================
ESTILO_BOTON_MENU = (
    'w-full h-16 bg-gradient-to-b from-zinc-300 to-zinc-400 '
    'text-zinc-900 font-bold font-mono text-sm border-2 border-t-white '
    'border-l-white border-b-zinc-600 border-r-zinc-600 active:border-t-zinc-600 '
    'active:border-l-zinc-600 rounded shadow-md uppercase tracking-wider'
)
ESTILO_VENTANA_MODAL = 'w-[650px] bg-zinc-300 p-4 border-4 border-zinc-500 rounded-none shadow-2xl text-zinc-900'
ESTILO_CABECERA_MODAL = 'w-full bg-blue-900 text-white font-mono font-bold px-3 py-1.5 shadow-inner flex justify-between text-sm'

# =========================================================================
# MODALES FLOTANTES INDEPENDIENTES (Diario, Fichajes, Finanzas)
# =========================================================================
def abrir_ventana_diario():
    db_path = obtener_ruta_db()
    j_actual = obtener_jornada_actual()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, puntos FROM equipos ORDER BY puntos DESC, (goles_favor - goles_contra) DESC")
    tabla = cursor.fetchall()
    cursor.execute('''
        SELECT p.goles_local, p.goles_visita, el.nombre, ev.nombre, p.jugado 
        FROM partidos p JOIN equipos el ON p.local_id = el.id JOIN equipos ev ON p.visita_id = ev.id WHERE p.jornada = ?
    ''', (j_actual,))
    partidos = cursor.fetchall()
    conn.close()

    with ui.dialog() as dialogo, ui.card().classes(ESTILO_VENTANA_MODAL):
        with ui.row().classes(ESTILO_CABECERA_MODAL):
            ui.label("⚙️ DIARIO INFORMACIÓN - JORNADA " + str(j_actual))
        
        with ui.row().classes('w-full gap-4 mt-2 font-mono text-xs'):
            with ui.column().classes('w-[48%] bg-zinc-200 p-2 border border-zinc-400'):
                ui.label("⚽ RESULTADOS:").classes('font-bold text-blue-900 mb-1')
                for g_l, g_v, n_l, n_v, jugado in partidos:
                    marcador = f"{g_l} - {g_v}" if jugado else "VS"
                    ui.label(f"{n_l[:9]} {marcador} {n_v[:9]}").classes('text-[11px] text-zinc-800')
            
            with ui.column().classes('w-[48%] bg-zinc-200 p-2 border border-zinc-400'):
                ui.label("🏆 CLASIFICACIÓN GENERAL:").classes('font-bold text-blue-900 mb-1')
                for pos, (id_c, nom_c, pts_c) in enumerate(tabla, start=1):
                    with ui.row().classes('w-full justify-between text-[11px] py-0.5 border-b border-zinc-300'):
                        ui.label(f"{pos}. {nom_c[:12]}").classes('text-zinc-900')
                        ui.label(f"{pts_c} PTS").classes('font-bold text-blue-800')
                        
        ui.button('VOLVER', on_click=dialogo.close).classes(ESTILO_BOTON_MENU + ' h-10 mt-2')
    dialogo.open()



###QUE HAGO CON ESTO?###
def abrir_ventana_fichajes(callback_refresco):
    def recargar_mercado_aljub(cc, cv):
        db_path = obtener_ruta_db()
        eq_id = obtener_mi_equipo_id()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, posicion, ataque, defensa, precio_pts FROM jugadores WHERE equipo_id IS NULL AND a_la_venta = 1 LIMIT 3")
        libres = cursor.fetchall()
        cursor.execute("SELECT id, nombre, posicion, precio_pts, a_la_venta FROM jugadores WHERE equipo_id = ?", (eq_id,))
        propios = cursor.fetchall()
        cursor.execute("SELECT id FROM equipos ORDER BY puntos DESC, (goles_favor - goles_contra) DESC")
        puestos = [r[0] for r in cursor.fetchall()]
        mi_puesto = puestos.index(eq_id) + 1
        conn.close()
        
        cc.clear()
        with cc:
            ui.label("🛒 COMPRAR CRACKS LIBRES:").classes('text-xs font-mono font-bold text-green-900 mb-1')
            for j_id, name, pos, atk, defs, precio in libres:
                with ui.row().classes('w-full justify-between items-center text-[11px] font-mono py-1 border-b border-zinc-400 bg-zinc-100 rounded px-1 mb-1'):
                    ui.label(f"{name} ({pos}) Med:{int((atk+defs)/2)}").classes('text-zinc-800')
                    ui.button(f"FICHAR ({precio:,} Pts)", on_click=lambda j=j_id: comprar_crack(j)).classes('bg-green-800 text-[9px] h-5 text-white font-mono')
                    
        cv.clear()
        with cv:
            ui.label("💰 PONER A LA VENTA EN EL ESCAPARATE:").classes('text-xs font-mono font-bold text-zinc-700 mt-2 mb-1')
            for j_id, name, pos, precio_base, en_venta in propios:
                modificador = max(0.5, 1.4 - (mi_puesto * 0.06))
                precio_tasado = int(precio_base * modificador)
                bg_item = "bg-orange-100/60 border border-orange-400" if en_venta else "bg-zinc-100"
                with ui.row().classes(f'w-full justify-between items-center text-[11px] font-mono py-1 border-b border-zinc-400 {bg_item} rounded px-1 mb-1'):
                    with ui.column().classes('gap-0'):
                        ui.label(f"{name} ({pos})").classes('text-zinc-800 font-bold')
                        ui.label(f"Base: {precio_base:,} -> Tasado: {precio_tasado:,} Pts").classes('text-[9px] text-zinc-500')
                    if en_venta:
                        ui.button('RETIRAR', on_click=lambda j=j_id: cambiar_cartel_venta(j, 0, cc, cv)).classes('bg-zinc-600 text-[9px] h-5 text-white font-mono')
                    else:
                        ui.button('TASAR', on_click=lambda j=j_id: cambiar_cartel_venta(j, 1, cc, cv)).classes('bg-orange-800 text-[9px] h-5 text-white font-mono')

    def comprar_crack(j_id):
        res = mercado_aljub.ejecutar_fichaje_aljub(j_id, obtener_mi_equipo_id())
        ui.notify(res, type='negative' if "❌" in res else 'positive')
        dialogo.close()
        callback_refresco()

    def cambiar_cartel_venta(j_id, estado, cc, cv):
        conn = sqlite3.connect(obtener_ruta_db())
        cursor = conn.cursor()
        cursor.execute("UPDATE jugadores SET a_la_venta = ? WHERE id = ?", (estado, j_id))
        conn.commit()
        conn.close()
        ui.notify("📋 Escaparate actualizado." if estado == 1 else "🛡️ Retirado de las vitrinas.", type='info')
        recargar_mercado_aljub(cc, cv)

    with ui.dialog() as dialogo, ui.card().classes(ESTILO_VENTANA_MODAL):
        with ui.row().classes(ESTILO_CABECERA_MODAL):
            ui.label("🛍️ TRASPASOS Y CONTRATOS - EL ALJUB")
        box_compra = ui.column().classes('w-full')
        box_venta = ui.column().classes('w-full')
        recargar_mercado_aljub(box_compra, box_venta)
        ui.button('CERRAR OFICINA', on_click=dialogo.close).classes(ESTILO_BOTON_MENU + ' h-10 mt-2')
    dialogo.open()

def abrir_ventana_finanzas():
    db_path = obtener_ruta_db()
    eq_id = obtener_mi_equipo_id()
    
    # Conseguimos el presupuesto actual para comprobar si tenemos fondos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT presupuesto_pts FROM equipos WHERE id = ?", (eq_id,))
    presupuesto_actual = cursor.fetchone()[0]
    conn.close()

    def comprar_arbitro_real():
        if presupuesto_actual < 5000000:
            ui.notify("❌ No tienes fondos suficientes. ¡A los árbitros no se les paga a plazos!", type='negative')
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 1. Restamos los 5 millones de la caja del club
        cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - 5000000 WHERE id = ?", (eq_id,))
        # 2. Activamos el favor arbitral en la configuración para esta jornada (1 = activado)
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('favor_arbitral', 1)")
        conn.commit()
        conn.close()
        
        ui.notify("💼 ¡Maletín entregado! El comité arbitral ha recibido el ingreso. +2 goles garantizados.", type='warning')
        dialogo.close()

    with ui.dialog() as dialogo, ui.card().classes('w-[450px] bg-zinc-300 p-4 border-4 border-zinc-500 rounded-none font-mono text-zinc-900 shadow-2xl'):
        with ui.row().classes(ESTILO_CABECERA_MODAL):
            ui.label("💼 CAJA GENERAL Y DECISIONES")
        with ui.card().classes('bg-zinc-200 border border-zinc-400 p-3 w-full text-center shadow-none mt-2'):
            ui.label("⚖️ Adquirir Favoritismo Arbitral de la Jornada").classes('text-xs text-zinc-800 font-bold')
            ui.label("Coste: 5.000.000 Pts (+2 goles fantasma garantizados)").classes('text-[10px] text-red-700 my-1 font-bold')
            
            # Conectamos el botón a la función real de pago
            ui.button('ENTREGAR MALETÍN', on_click=comprar_arbitro_real) \
                .classes('bg-purple-900 text-xs text-white mt-1 w-full font-mono h-8')
        ui.button('VOLVER A LA JUNTA', on_click=dialogo.close).classes(ESTILO_BOTON_MENU + ' h-10 mt-2')
    dialogo.open()

# =========================================================================
# REFRESCADOR GENERAL DEL DESPACHO
# =========================================================================
def refrescar_despacho_limpio(header_box, partido_box):
    db_path = obtener_ruta_db()
    eq_id = obtener_mi_equipo_id()
    j_actual = obtener_jornada_actual()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, presupuesto_pts FROM equipos WHERE id = ?", (eq_id,))
    eq_nombre, eq_presupuesto = cursor.fetchone()
    conn.close()
    
    header_box.clear()
    with header_box:
        with ui.row().classes('w-full justify-between items-center bg-zinc-400 p-3 border-2 border-t-white border-l-white border-b-zinc-600 border-r-zinc-600 rounded font-mono shadow-md'):
            with ui.row().classes('items-center gap-2'):
                escudos.pintar_escudo(eq_id, "w-7 h-9")
                ui.label(f"CLUB: {eq_nombre.upper()}").classes('text-lg font-bold text-blue-950')
            ui.label(f"CAJA: {eq_presupuesto:,} PTS").classes('text-lg font-bold text-green-900')

    partido_box.clear()
    with partido_box:
        texto_rival, rival_id, localia = obtener_proximo_rival_info()
        bg_rival = "bg-blue-100 border-blue-400" if localia == "local" else "bg-amber-100 border-amber-400"
        with ui.row().classes(f'w-full justify-between items-center p-2.5 border-2 rounded font-mono {bg_rival} shadow-sm'):
            with ui.row().classes('items-center gap-2 text-xs'):
                ui.label(f"📋 PRÓXIMA JORNADA {j_actual}:").classes('font-bold text-zinc-600')
                ui.label(texto_rival).classes('text-sm font-bold text-blue-900')
            if rival_id: escudos.pintar_escudo(rival_id, "w-5 h-6")




# =========================================================================
# PORTADA DE LANZAMIENTO RETRO
# =========================================================================
@ui.page('/')
def portada():
    # 1. Aseguramos que la base de datos raíz tenga las tablas bien estructuradas
    asegurar_infraestructura_db()
    ui.dark_mode().disable()
    
    def saltar_al_juego():
        ui.navigate.to('/menu')

    # Contenedor a pantalla completa que reacciona al clic
    with ui.column().classes('w-full min-h-screen bg-black items-center justify-center cursor-pointer').on('click', saltar_al_juego):
        ui.image('/img/portada.jpeg').classes('max-w-full max-h-screen object-contain')
        ui.label('PULSAR PARA CONTINUAR').classes('text-white font-mono text-xs tracking-widest animate-pulse mt-4')


# =========================================================================
# MENÚ PRINCIPAL
# =========================================================================
@ui.page('/menu')
def pantalla_inicio():
    ui.dark_mode().disable()
    with ui.column().classes('w-full min-h-screen bg-zinc-700 items-center justify-center'):
        with ui.column().classes('w-[460px] border-4 border-t-zinc-200 border-l-zinc-200 border-b-zinc-900 border-r-zinc-900 shadow-2xl gap-0'):
            with ui.row().classes('w-full bg-blue-900 px-3 py-1.5 justify-between items-center'):
                ui.label("MUÑONBOL MANAGER '95").classes('text-white font-mono font-bold text-sm tracking-wider')
                ui.label("─ □ ✕").classes('text-white font-mono text-xs cursor-default select-none')
            with ui.column().classes('w-full bg-zinc-300 p-6 items-center gap-4'):
                with ui.column().classes('w-full bg-blue-950 border-2 border-t-zinc-600 border-l-zinc-600 border-b-zinc-200 border-r-zinc-200 p-5 items-center gap-1'):
                    ui.label("⚽ MUÑONBOL MANAGER").classes('text-yellow-300 font-mono font-bold text-2xl tracking-widest')
                    ui.label("E L C H E  ' 9 5").classes('text-zinc-400 font-mono text-xs tracking-[0.4em] mt-1')
                ui.separator().classes('w-full border-t border-zinc-400')
                
                eq_id_save, eq_nombre_save = obtener_datos_partida_guardada()

                def nueva_partida():
                    if os.path.exists(DB_PARTIDA):
                        os.remove(DB_PARTIDA)
                    app.storage.user.pop('id_equipo_seleccionado', None)
                    app.storage.user.pop('equipo_id', None)
                    if inicializar_nueva_partida():
                        ui.navigate.to('/elegir_equipo')

                def continuar_partida(eid=eq_id_save):
                    app.storage.user['id_equipo_seleccionado'] = eid
                    ui.navigate.to('/despacho')

                ui.button('► INICIAR NUEVA TEMPORADA', on_click=nueva_partida) \
                    .classes(ESTILO_BOTON_MENU + ' h-12 text-sm w-full')

                if eq_id_save is not None:
                    ui.button(f'► CONTINUAR — {eq_nombre_save.upper()}', on_click=continuar_partida) \
                        .classes(ESTILO_BOTON_MENU + ' h-12 text-sm w-full')
                else:
                    ui.button('► CONTINUAR PARTIDA GUARDADA', on_click=None) \
                        .classes(ESTILO_BOTON_MENU + ' h-12 text-sm w-full opacity-40') \
                        .props('disabled')

                ui.button('⚙ CONFIGURACIÓN DEL SISTEMA', on_click=lambda: ui.navigate.to('/configuracion')) \
                    .classes(ESTILO_BOTON_MENU + ' h-10 text-xs w-full')
            with ui.row().classes('w-full bg-zinc-400 border-t-2 border-t-zinc-500 px-3 py-0.5'):
                ui.label("F1=Ayuda   ESC=Salir").classes('text-zinc-600 font-mono text-[10px]')
# =========================================================================
# PANEL DE CONFIGURACIÓN Y EDICIÓN DE BASE DE DATOS (PÁGINA APARTE)
# =========================================================================
@ui.page('/configuracion')
def pagina_configuracion_sistema():
    configuracion.render_pagina_configuracion()

# =========================================================================
# SELECCIÓN DE EQUIPO
# =========================================================================
@ui.page('/elegir_equipo')
def selector_de_clubes():
    ui.dark_mode().disable()
    with ui.column().classes('w-full min-h-screen bg-zinc-700 items-center justify-start py-8'):
        with ui.column().classes('w-[780px] border-4 border-t-zinc-200 border-l-zinc-200 border-b-zinc-900 border-r-zinc-900 shadow-2xl gap-0'):
            with ui.row().classes('w-full bg-blue-900 px-3 py-1.5 justify-between items-center'):
                ui.label("SELECCIÓN DE CLUB — TEMPORADA '95").classes('text-white font-mono font-bold text-sm')
                ui.label("─ □ ✕").classes('text-white font-mono text-xs cursor-default select-none')
            with ui.column().classes('w-full bg-zinc-300 p-4 gap-3'):
                with ui.row().classes('w-full bg-zinc-400 border-2 border-t-zinc-600 border-l-zinc-600 border-b-zinc-200 border-r-zinc-200 px-3 py-1'):
                    ui.label("Elige el club que dirigirás durante la temporada:").classes('font-mono text-xs text-zinc-800 font-bold')
                
                # 🌟 CONEXIÓN Y FILTRADO EXCLUSIVO DE PRIMERA DIVISIÓN 🌟
                conn = sqlite3.connect(obtener_ruta_db())
                cursor = conn.cursor()
                cursor.execute("SELECT e.id, e.nombre, e.presupuesto_pts FROM equipos e WHERE e.division = 'Liga SuperEmpanadill'")
                clubes = cursor.fetchall()
                conn.close()
                
                # La rejilla ahora pintará automáticamente solo 12 tarjetas en lugar de 17
                with ui.grid(columns=3).classes('w-full gap-3'):
                    for num_id, nombre, presupuesto in clubes:
                        with ui.column().classes('bg-zinc-300 border-2 border-t-white border-l-white border-b-zinc-600 border-r-zinc-600 p-3 items-center text-center gap-1 shadow'):
                            escudos.pintar_escudo(num_id, "w-12 h-14")
                            ui.label(nombre.upper()).classes('text-xs font-bold text-blue-950 font-mono leading-tight mt-1')
                            ui.label(f"{presupuesto:,} Pts").classes('text-[10px] font-mono text-zinc-600')
                            ui.button('TOMAR MANDOS', on_click=lambda e_id=num_id: asignary_saltar(e_id)).classes(ESTILO_BOTON_MENU + ' h-9 text-xs w-full')
            with ui.row().classes('w-full bg-zinc-400 border-t-2 border-t-zinc-500 px-3 py-0.5'):
                ui.label("F1=Ayuda   ESC=Volver").classes('text-zinc-600 font-mono text-[10px]')

def asignary_saltar(equipo_id):
    app.storage.user['id_equipo_seleccionado'] = equipo_id
    try:
        conn = sqlite3.connect(DB_PARTIDA)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('equipo_jugador', ?)", (equipo_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass
    ui.navigate.to('/despacho')

# --- REGISTRO DE LA NUEVA PÁGINA DEL ARCHIVO INDEPENDIENTE ---
@ui.page('/alineacion')
def pagina_alineacion_tactica_piscina():
    # Llama a la función del archivo alineacion.py que creamos antes
    alineacion.menu_alineacion()

@ui.page('/despacho')
def despacho_club():
    ui.dark_mode().disable()
    
    box_finanzas = ui.column().classes('w-full')
    box_proximo_rival = ui.column().classes('w-full')
    fn_refrescar = lambda: refrescar_despacho_limpio(box_finanzas, box_proximo_rival)

    with ui.column().classes('w-full p-6 max-w-4xl mx-auto gap-4 bg-slate-100 border border-slate-300 rounded-2xl min-h-screen shadow-xl font-sans text-slate-900'):
        box_finanzas.classes('w-full')
        box_proximo_rival.classes('w-full')
        
        ui.label("🗄️ CUADRO DE MANDOS E INGENIERÍA").classes('text-[10px] font-bold text-slate-500 tracking-widest mt-2 uppercase')
        
        with ui.grid(columns=2).classes('w-full gap-4'):
            
            # Botón 1: Diario Información
            with ui.column().classes('bg-white border border-slate-300 rounded-xl shadow-sm p-3 items-center gap-2'):
                ui.image('/img/informacion.png').classes('w-full h-28 object-contain')
                ui.button('Diario Información', on_click=lambda: diario.abrir_centro_informacion(obtener_jornada_actual())) \
                    .props('unelevated').classes('w-full bg-slate-800 text-white text-xs font-bold rounded-lg h-9')

            # Botón 2: Alineación Táctica
            with ui.column().classes('bg-white border border-slate-300 rounded-xl shadow-sm p-3 items-center gap-2'):
                ui.image('/img/alineacion.png').classes('w-full h-28 object-contain')
                ui.button('Alineación Táctica', on_click=lambda: ui.navigate.to('/alineacion')) \
                    .props('unelevated').classes('w-full bg-slate-800 text-white text-xs font-bold rounded-lg h-9')

            # Botón 3: Mercado El Aljub
            with ui.column().classes('bg-white border border-slate-300 rounded-xl shadow-sm p-3 items-center gap-2'):
                ui.image('/img/aljub.png').classes('w-full h-28 object-contain')
                ui.button('Mercado El Aljub', on_click=lambda: mercado.abrir_mercado_aljub(obtener_jornada_actual(), fn_refrescar)) \
                    .props('unelevated').classes('w-full bg-slate-800 text-white text-xs font-bold rounded-lg h-9')

            # Botón 4: Decisiones Financieras
            with ui.column().classes('bg-white border border-slate-300 rounded-xl shadow-sm p-3 items-center gap-2'):
                ui.image('/img/finanzas.png').classes('w-full h-28 object-contain')
                ui.button("CAJA GENERAL Y DECISIONES", icon='payments', on_click=finanzas.abrir_caja_y_decisiones) \
                    .props('unelevated').classes('w-full bg-slate-800 text-white text-xs font-bold rounded-lg h-9')

        with ui.row().classes('w-full justify-between items-center mt-8 border-t border-slate-300 pt-4'):
            ui.button('Grabar Liga', icon='save', on_click=lambda: ui.notify("💾 Partida guardada con éxito.", type='positive')) \
                .props('flat').classes('text-slate-500 text-xs font-semibold rounded-lg')
            ui.button('MENÚ PRINCIPAL', icon='home', on_click=volver_al_menu_principal) \
                .props('unelevated rounded') \
                .classes('bg-slate-700 text-white text-xs px-4') \
                .tooltip('Regresar a la pantalla de selección de club')    
            ui.button('JUGAR JORNADA OBLIGATORIA', icon='play_arrow', on_click=lambda: simular_jornada_pcfutbol(box_finanzas, box_proximo_rival)) \
                .props('unelevated').classes('bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs px-6 h-12 rounded-xl shadow-md transition')
        
        fn_refrescar()

def simular_jornada_pcfutbol(b_fin, b_partido):
    db_path = obtener_ruta_db()
    
    # 🌟 BLINDAJE EXTRA: Forzamos a capturar cualquier variante de sesión para que no use el ID 2 a ciegas
    eq_id = app.storage.user.get('id_equipo_seleccionado') or app.storage.user.get('equipo_id') or 2

    # Consulta previa: titulares sanos
    conn_chk = sqlite3.connect(db_path)
    cur_chk = conn_chk.cursor()
    cur_chk.execute(
        "SELECT COUNT(*) FROM jugadores WHERE equipo_id = ? AND titular > 0 AND semanas_lesion = 0",
        (eq_id,)
    )
    total_titulares = cur_chk.fetchone()[0]
    conn_chk.close()

    def _ejecutar_jornada():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        j_actual = obtener_jornada_actual()

        # 2. Comprobamos si compramos al árbitro para esta jornada
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'favor_arbitral'")
        res_favor = cursor.fetchone()
        tiene_favor = res_favor[0] if res_favor else 0

        # Consumimos el maletín (vuelve a 0 para la próxima jornada)
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('favor_arbitral', 0)")
        conn.commit()
        conn.close()

        # Auto-rotar plantillas: titulares lesionados → banco, suplentes sanos → slots vacantes
        auto_completar_plantillas()

        # Snapshot lesiones previas (todos los equipos) para detectar nuevas tras simular
        conn_pre = sqlite3.connect(db_path)
        cur_pre = conn_pre.cursor()
        cur_pre.execute("SELECT id FROM jugadores WHERE semanas_lesion > 0")
        ids_lesionados_pre = {r[0] for r in cur_pre.fetchall()}
        conn_pre.close()

        # 3. Simulación matemática de la liga en segundo plano
        simulador_liga.jugar_jornada_completa(j_actual)

        # Nuevas lesiones producidas en esta jornada (todos los equipos, con equipo_id)
        conn_post = sqlite3.connect(db_path)
        cur_post = conn_post.cursor()
        cur_post.execute("SELECT id, nombre, semanas_lesion, equipo_id FROM jugadores WHERE semanas_lesion > 0")
        todas_nuevas_lesiones = [(jid, jnom, sem, eqid) for jid, jnom, sem, eqid in cur_post.fetchall() if jid not in ids_lesionados_pre]
        conn_post.close()
        nuevas_lesiones = [(jid, jnom, sem) for jid, jnom, sem, eqid in todas_nuevas_lesiones if eqid == eq_id]

        # 4. Procesamos los resultados e incidencias en un ÚNICO bucle limpio
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.local_id, p.visita_id, p.goles_local, p.goles_visita, el.nombre, ev.nombre
            FROM partidos p 
            JOIN equipos el ON p.local_id = el.id 
            JOIN equipos ev ON p.visita_id = ev.id
            WHERE p.jornada = ?
        ''', (j_actual,))
        partidos_jugados = cursor.fetchall()

        partido_usuario = None
        resto_partidos = []
        resumen_incidencias = {}

        for p_id, loc_id, vis_id, g_l, g_v, nom_l, nom_v in partidos_jugados:
            resumen_incidencias[p_id] = {'goles_l': [], 'goles_v': [], 'extras_l': [], 'extras_v': []}

            # APLICACIÓN DEL MALETÍN
            if tiene_favor == 1:
                def _pts(gl, gv): return (3, 0) if gl > gv else ((0, 3) if gv > gl else (1, 1))
                if loc_id == eq_id:
                    orig_l, orig_v = _pts(g_l, g_v)
                    g_l += 2
                    cursor.execute("UPDATE partidos SET goles_local = ? WHERE id = ?", (g_l, p_id))
                    new_l, new_v = _pts(g_l, g_v)
                    if new_l != orig_l:
                        cursor.execute("UPDATE equipos SET puntos = puntos + ? WHERE id = ?", (new_l - orig_l, loc_id))
                        cursor.execute("UPDATE equipos SET puntos = puntos + ? WHERE id = ?", (new_v - orig_v, vis_id))
                    resumen_incidencias[p_id]['extras_l'].append((0, "💼 Gol fantasma de penalti inexistente"))
                    resumen_incidencias[p_id]['extras_l'].append((0, "💼 Fuera de juego de 4 metros ignorado"))
                elif vis_id == eq_id:
                    orig_l, orig_v = _pts(g_l, g_v)
                    g_v += 2
                    cursor.execute("UPDATE partidos SET goles_visita = ? WHERE id = ?", (g_v, p_id))
                    new_l, new_v = _pts(g_l, g_v)
                    if new_v != orig_v:
                        cursor.execute("UPDATE equipos SET puntos = puntos + ? WHERE id = ?", (new_l - orig_l, loc_id))
                        cursor.execute("UPDATE equipos SET puntos = puntos + ? WHERE id = ?", (new_v - orig_v, vis_id))
                    resumen_incidencias[p_id]['extras_v'].append((0, "💼 Gol fantasma de penalti inexistente"))
                    resumen_incidencias[p_id]['extras_v'].append((0, "💼 Fuera de juego de 4 metros ignorado"))

            cursor.execute("SELECT id, nombre, COALESCE(bacora,1) FROM jugadores WHERE equipo_id = ? AND titular BETWEEN 1 AND 5 AND semanas_lesion = 0", (loc_id,))
            jugadores_l = cursor.fetchall() or [(None, "Muñón L", 1)]
            cursor.execute("SELECT id, nombre, COALESCE(bacora,1) FROM jugadores WHERE equipo_id = ? AND titular BETWEEN 1 AND 5 AND semanas_lesion = 0", (vis_id,))
            jugadores_v = cursor.fetchall() or [(None, "Muñón V", 1)]
            pesos_l = [max(1, j[2]) for j in jugadores_l]
            pesos_v = [max(1, j[2]) for j in jugadores_v]

            for _ in range(g_l or 0):
                j_id, j_nom, _ = random.choices(jugadores_l, weights=pesos_l, k=1)[0]
                resumen_incidencias[p_id]['goles_l'].append((random.randint(1, 44), j_nom))
                if j_id:
                    cursor.execute("UPDATE jugadores SET goles = goles + 1 WHERE id = ?", (j_id,))

            for _ in range(g_v or 0):
                j_id, j_nom, _ = random.choices(jugadores_v, weights=pesos_v, k=1)[0]
                resumen_incidencias[p_id]['goles_v'].append((random.randint(1, 44), j_nom))
                if j_id:
                    cursor.execute("UPDATE jugadores SET goles = goles + 1 WHERE id = ?", (j_id,))

            if random.random() < 0.15:
                _, j_nom, _ = random.choice(jugadores_l)
                resumen_incidencias[p_id]['extras_l'].append((random.randint(5, 40), f"💳 Tarjeta Carrefour ({j_nom} expulsado)"))
            if random.random() < 0.15:
                _, j_nom, _ = random.choice(jugadores_v)
                resumen_incidencias[p_id]['extras_v'].append((random.randint(5, 40), f"💳 Tarjeta Carrefour ({j_nom} expulsado)"))

            resumen_incidencias[p_id]['goles_l'].sort(key=lambda x: x[0])
            resumen_incidencias[p_id]['goles_v'].sort(key=lambda x: x[0])
            resumen_incidencias[p_id]['extras_l'].sort(key=lambda x: x[0])
            resumen_incidencias[p_id]['extras_v'].sort(key=lambda x: x[0])

            if loc_id == eq_id or vis_id == eq_id:
                partido_usuario = (p_id, loc_id, vis_id, g_l, g_v, nom_l, nom_v)
            else:
                resto_partidos.append((p_id, loc_id, vis_id, g_l, g_v, nom_l, nom_v))

        def procesar_mercado_ia_extranjera():
            db_path = obtener_ruta_db()
            my_eq_id = obtener_mi_equipo_id()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            conn.close()
            cursor.execute("SELECT COUNT(*) FROM jugadores")
            total_censo = cursor.fetchone()[0]
            if total_censo < 100:
                nombres_falsos = ["Muñón Centenario", "Gorrotatu", "Clorofílico", "Zampabacoras", "El brian de Elche"]
                cursor.execute(
                    "INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, precio_pts) VALUES (?, ?, 'JUG', ?, ?, ?)",
                    (random.choice(nombres_falsos), random.randint(18,34), random.randint(30,70), random.randint(30,70), random.randint(500000, 3000000))
                )
            cursor.execute("SELECT id FROM equipos")
            todos_id = [r[0] for r in cursor.fetchall()]
            for eq_rival in todos_id:
                cursor.execute("SELECT COUNT(*) FROM jugadores WHERE equipo_id = ?", (eq_rival,))
                plantilla_size = cursor.fetchone()[0]
                if plantilla_size < 6:
                    cursor.execute("SELECT id FROM jugadores WHERE equipo_id IS NULL LIMIT 1")
                    libre = cursor.fetchone()
                    if libre: cursor.execute("UPDATE jugadores SET equipo_id = ? WHERE id = ?", (eq_rival, libre[0]))
                elif plantilla_size > 12:
                    cursor.execute("SELECT id FROM jugadores WHERE equipo_id = ? LIMIT 1", (eq_rival,))
                    descarte = cursor.fetchone()
                    if descarte: cursor.execute("UPDATE jugadores SET equipo_id = NULL, titular = 0 WHERE id = ?", (descarte[0]))

        conn.commit()
        conn.close()

        # --- 5. RENDERIZADO DEL ACTA DE ENCUENTROS ---
        def renderizar_fila_partido(datos_p, es_destacado=False):
            p_id, loc_id, vis_id, g_l, g_v, nom_l, nom_v = datos_p
            inc = resumen_incidencias[p_id]
            border_cls = "border-2 border-indigo-500 bg-indigo-50/40" if es_destacado else "border border-slate-100 bg-slate-50/40"
            with ui.column().classes(f'w-full rounded-xl p-4 mb-3 gap-1 shadow-sm {border_cls}'):
                if es_destacado:
                    ui.label("⭐️ TU PARTIDO").classes('text-[9px] font-extrabold text-indigo-700 tracking-widest uppercase mb-1')
                with ui.row().classes('w-full items-center justify-center gap-4 font-sans'):
                    with ui.row().classes('items-center gap-2 w-[35%] justify-end text-right'):
                        ui.label(nom_l.upper()).classes('text-sm font-bold text-slate-800 truncate')
                        escudos.pintar_escudo(loc_id, "w-6 h-8")
                    with ui.row().classes('bg-slate-900 text-white font-bold text-base px-4 py-1 rounded-lg min-w-[75px] justify-center tracking-widest'):
                        ui.label(f"{g_l} - {g_v}")
                    with ui.row().classes('items-center gap-2 w-[35%] justify-start text-left'):
                        escudos.pintar_escudo(vis_id, "w-6 h-8")
                        ui.label(nom_v.upper()).classes('text-sm font-bold text-slate-800 truncate')
                with ui.row().classes('w-full pt-1.5 text-[10px] items-start justify-between px-4 font-sans text-slate-600 border-t border-dashed border-slate-200/60 mt-1'):
                    with ui.column().classes('w-[46%] items-end text-right gap-0.5'):
                        for m, j in inc['goles_l']: ui.label(f"{j} ({m}') ⚽")
                        for m, t in inc['extras_l']: ui.label(f"{t} ({m}')").classes('text-rose-700 font-semibold')
                    with ui.column().classes('w-[46%] items-start text-left gap-0.5'):
                        for m, j in inc['goles_v']: ui.label(f"⚽ ({m}') {j}")
                        for m, t in inc['extras_v']: ui.label(f"({m}') {t}").classes('text-rose-700 font-semibold')
                lesiones_partido = [(jnom, sem) for _, jnom, sem, eqid in todas_nuevas_lesiones if eqid in (loc_id, vis_id)]
                if lesiones_partido:
                    with ui.row().classes('w-full items-center gap-2 flex-wrap mt-1 pt-1 border-t border-dashed border-red-100 px-4'):
                        ui.icon('local_hospital', color='red').classes('text-sm')
                        for jnom, sem in lesiones_partido:
                            ui.label(f"🚑 {jnom} — {sem}j baja").classes('text-[9px] text-red-700 font-semibold bg-red-50 border border-red-100 rounded px-1.5 py-0.5')

        def cerrar_acta():
            panel_acta.close()
            conn_of = sqlite3.connect(db_path)
            cur_of = conn_of.cursor()
            cur_of.execute("""
                SELECT COUNT(*) FROM ofertas_pendientes o
                JOIN jugadores j ON o.jugador_id = j.id
                WHERE j.equipo_id = ?
            """, (eq_id,))
            hay_ofertas = cur_of.fetchone()[0] > 0
            conn_of.close()

            def mostrar_popup_ofertas():
                if hay_ofertas:
                    with ui.dialog() as dlg_of, ui.card().classes('w-[380px] p-5 font-sans gap-3 items-center'):
                        ui.icon('monetization_on', color='green').classes('text-5xl mb-1')
                        ui.label('TIENES OFERTAS').classes('text-xl font-extrabold text-slate-800 tracking-wide')
                        ui.label('Tienes ofertas que no parecen interesar lo más mínimo').classes('text-sm text-slate-500 text-center')
                        ui.button('VER OFERTAS', on_click=lambda: (dlg_of.close(), mercado.abrir_mercado_aljub(obtener_jornada_actual(), lambda: None))).props('unelevated rounded').classes('bg-emerald-700 text-white text-xs mt-1')
                        ui.button('YA VEREMOS', on_click=dlg_of.close).props('flat rounded').classes('text-slate-400 text-xs')
                    dlg_of.open()

            if nuevas_lesiones:
                with ui.dialog() as dlg_les, ui.card().classes('w-[380px] p-5 font-sans gap-2 items-center'):
                    ui.icon('local_hospital', color='red').classes('text-5xl mb-1')
                    ui.label('¡FOTRE!').classes('text-2xl font-extrabold text-red-700 tracking-wide')
                    ui.label('Se te han escacharrao algunos jugadores').classes('text-sm text-slate-500 text-center')
                    with ui.column().classes('w-full gap-1 mt-1'):
                        for _, jnom, sem in nuevas_lesiones:
                            ui.label(f"🚑 {jnom.upper()} — baja {sem} jornada{'s' if sem != 1 else ''}").classes('text-xs text-red-800 font-semibold bg-red-50 border border-red-200 rounded px-2 py-1 w-full text-center')
                    ui.button('MALA SUERTE', on_click=lambda: (dlg_les.close(), mostrar_popup_ofertas())).props('unelevated rounded').classes('bg-slate-900 text-white text-xs mt-2')
                dlg_les.open()
            else:
                mostrar_popup_ofertas()

        with ui.dialog() as panel_acta, ui.card().classes('w-[680px] max-w-4xl bg-white p-5 rounded-2xl shadow-xl font-sans text-slate-900'):
            with ui.row().classes('w-full border-b border-slate-100 pb-2 justify-between items-center'):
                ui.label(f"Acta de Encuentros — Jornada {j_actual}").classes('text-lg font-bold text-slate-800')
                ui.button("ARCHIVAR JORNADA", on_click=cerrar_acta).classes('bg-slate-900 text-white text-xs font-semibold rounded-lg h-8 px-4')
            with ui.scroll_area().classes('w-full h-[460px] pr-2 mt-3'):
                if partido_usuario: renderizar_fila_partido(partido_usuario, es_destacado=True)
                if resto_partidos:
                    ui.label("OTROS RESULTADOS").classes('text-[9px] font-bold text-slate-400 tracking-widest mt-4 mb-2 text-center w-full')
                    for p_data in resto_partidos: renderizar_fila_partido(p_data, es_destacado=False)
            panel_acta.open()

        # 6. Generamos ofertas de IA para jugadores en venta
        mercado.generar_ofertas_jugadores_venta(eq_id, j_actual)

        # 7. Avanzamos jornada de liga de forma segura y refrescamos el despacho
        avanzar_jornada_db()
        refrescar_despacho_limpio(b_fin, b_partido)

    # --- Diálogo pulpo: aviso si faltan titulares ---
    if total_titulares < 5:
        with ui.dialog() as dlg_pulpo, ui.card().classes('w-[400px] p-6 font-sans rounded-2xl shadow-xl gap-3 items-center'):
            ui.icon('sports_handball', color='orange').classes('text-5xl mb-1')
            ui.label('¡AVISO DEL MÍSTER!').classes('text-xl font-extrabold text-orange-600 tracking-wide')
            ui.label(f'Solo tienes {total_titulares} titular(es) sano(s).').classes('text-sm font-semibold text-slate-700 text-center')
            ui.label('Te van a meter la del pulpo. ¿Juegas de todas formas?').classes('text-xs text-slate-400 text-center')
            with ui.row().classes('gap-3 mt-2'):
                ui.button('🎽 JUGAR DE TODAS FORMAS', on_click=lambda: (dlg_pulpo.close(), _ejecutar_jornada())).props('unelevated rounded').classes('bg-orange-500 text-white text-xs px-4')
                ui.button('VOLVER', on_click=dlg_pulpo.close).props('flat rounded').classes('text-slate-500 text-xs')
        dlg_pulpo.open()
    else:
        _ejecutar_jornada()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Muñonbol Manager '95", port=8080, reload=True, storage_secret="ELCHE_1995_SECRET_KEY")