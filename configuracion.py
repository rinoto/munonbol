from nicegui import ui
import sqlite3
import random

DB_NAME = "munonbol_elche_95.db"

def obtener_conexion_db():
    return sqlite3.connect(DB_NAME)

def resetear_campeonato_desde_cero():
    from main import obtener_ruta_db
    conn = sqlite3.connect(obtener_ruta_db())
    cursor = conn.cursor()
    
    # 1. Devolvemos la liga a la Jornada 1
    cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave = 'jornada_actual'")
    
    # 2. Reseteamos el casillero de favoritismo arbitral por si acaso
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('favor_arbitral', 0)")
    
    # 3. Limpiamos el historial de todos los partidos (jugado=0, goles en blanco)
    cursor.execute("UPDATE partidos SET goles_local = NULL, goles_visita = NULL, jugado = 0")
    
    # 4. Quitamos los goles acumulados de los jugadores (Pichichi a cero)
    cursor.execute("UPDATE jugadores SET goles = 0, semanas_lesion = 0")
    
    # 5. Reseteamos los puntos y goles de la tabla de equipos para limpiar la clasificación
    # (Asegúrate de que tus columnas se llamen exactamente así en la tabla de equipos)
    cursor.execute("UPDATE equipos SET puntos = 0, goles_favor = 0, goles_contra = 0")
    
    conn.commit()
    conn.close()
    
    ui.notify("🗑️ ¡LIGA REINICIADA! Marcadores a cero y plantillas listas para la Jornada 1.", type='positive')
    ui.navigate.to('/configuracion') # Recarga para ver todo limpio

def formatear_precio_corto(valor):
    if valor is None or valor == 0:
        return "0 Pts"
    
    # Si prefieres formato estricto en K (ej: 12.000K):
    # return f"{int(valor / 1000):,}K Pts".replace(",", ".")
    
    # Si prefieres formato en Millones (ej: 12M o 10,5M) que es más limpio:
    if valor >= 1000000:
        millones = valor / 1000000
        if millones.is_integer():
            return f"{int(millones)}M Pts"
        else:
            return f"{millones:.1f}M Pts".replace(".", ",")
            
    return f"{int(valor / 1000)}K Pts"

def ejecutar_consulta(sql, params=()):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    res = cursor.fetchall()
    conn.commit()
    conn.close()
    return res

def asegurar_y_limpiar_infraestructura():
    # Asegura las columnas y despierta SOLO una vez a los que estaban a 0 de antes
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(jugadores)")
    cols_j = [c[1] for c in cursor.fetchall()]
    if "est_actif" not in cols_j:
        cursor.execute("ALTER TABLE jugadores ADD COLUMN est_actif INTEGER DEFAULT 1")
        conn.commit()
    
    # Comprobamos si hay una bandera de limpieza para no machacar el archivado siempre
    cursor.execute("PRAGMA table_info(equipos)")
    cols_e = [c[1] for c in cursor.fetchall()]
    if "estadio" not in cols_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN estadio TEXT DEFAULT 'Estadio Comarcal'")
    if "division" not in cols_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN division TEXT DEFAULT 'Liga SuperEmpanadill'")
    if "entrenador_id" not in cols_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN entrenador_id INTEGER DEFAULT NULL")
    if "aforo" not in cols_e:
        cursor.execute("ALTER TABLE equipos ADD COLUMN aforo INTEGER DEFAULT 5000")
    cursor.execute("""CREATE TABLE IF NOT EXISTS entrenadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        mote TEXT,
        bono_ataque INTEGER NOT NULL DEFAULT 0,
        bono_defensa INTEGER NOT NULL DEFAULT 0,
        frase_mitica TEXT,
        precio_pts INTEGER
    )""")
    conn.commit()
    conn.close()

def render_pagina_configuracion():
    asegurar_y_limpiar_infraestructura()
    
    # --- COMPROBACIÓN DE CONTROL DE 12 EQUIPOS EN PRIMERA ---
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM equipos WHERE division = 'Liga SuperEmpanadill'")
    cuenta_primera = cursor.fetchone()[0]
    conn.close()
    
    if cuenta_primera < 12:
        with ui.dialog() as alerta_div, ui.card().classes('w-[450px] p-4 text-center font-sans'):
            ui.icon('warning', color='warning').classes('text-4xl mb-2')
            ui.label("⚠️ CONFIGURACIÓN ILEGAL").classes('text-xs font-extrabold text-amber-600 tracking-widest')
            ui.label(f"Actualmente hay {cuenta_primera} equipos en Primera división. ¡La federación exige exactamente 12! O te ocupas tú o me ocupo yo y hago lo que me de la gana.").classes('text-sm text-slate-700 my-2')
            with ui.row().classes('w-full gap-2 justify-center mt-2'):
                ui.button("Ok, voy al tema", on_click=alerta_div.close).props('unelevated rounded size=sm').classes('bg-slate-900 text-white')
                def balanceo_arenque():
                    conn = obtener_conexion_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM equipos WHERE division != 'Liga SuperEmpanadill' LIMIT ?", (12 - cuenta_primera,))
                    for (eq_id,) in cursor.fetchall():
                        cursor.execute("UPDATE equipos SET division = 'Liga SuperEmpanadill' WHERE id = ?", (eq_id,))
                    conn.commit()
                    conn.close()
                    ui.notify("🐟 ¡Ordenado con un arenque! Se han ascendido clubes automáticos.", type='info')
                    alerta_div.close()
                    redibujar_tabla_equipos()
                ui.button("Hazlo tú, con un arenque", on_click=balanceo_arenque).props('unelevated rounded size=sm').classes('bg-blue-600 text-white')
        alerta_div.open()

    # --- DISEÑO GENERAL A PANTALLA COMPLETA ---
    with ui.row().classes('gap-2'):
            ui.button("REINICIAR LIGA (CERO)", icon='refresh', on_click=resetear_campeonato_desde_cero) \
                .props('unelevated rounded').classes('bg-rose-700 hover:bg-rose-800 text-white text-xs h-9 px-4 font-bold')
                
            ui.button("VOLVER AL MENÚ", icon='arrow_back', on_click=lambda: ui.navigate.to('/')) \
                .props('unelevated rounded').classes('bg-slate-900 text-white text-xs h-9 px-4')


    with ui.column().classes('w-full p-6 max-w-6xl mx-auto font-sans bg-slate-50 min-h-screen text-slate-900'):
        with ui.row().classes('w-full border-b border-slate-200 pb-4 justify-between items-center mb-4'):
            with ui.column().classes('gap-0'):
                ui.label("Consola de Ingeniería de la Federación").classes('text-2xl font-bold tracking-tight')
                ui.label("Gestión total de plantillas, estadios, ligas mandinga y actas sanitarias").classes('text-xs text-slate-400')
            ui.button("VOLVER AL MENÚ", icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('unelevated rounded').classes('bg-slate-900 text-white text-xs h-9 px-4')

        with ui.tabs().classes('w-full border-b border-slate-200 mb-4') as tabs:
            tab_jug = ui.tab('JUGADORES', icon='people')
            tab_eq  = ui.tab('EQUIPOS / LIGAS', icon='shield')
            tab_est = ui.tab('ESTADIOS', icon='stadium')
            tab_les = ui.tab('PARTE MÉDICO', icon='medical_services')
            tab_ent = ui.tab('ENTRENADORES', icon='sports')

        with ui.tab_panels(tabs, value=tab_jug).classes('w-full bg-transparent shadow-none p-0'):
            
            # =========================================================================
            # TAB 1: JUGADORES (AÑADIR, RETOCAR, ORDENAR Y ACCIONES VISIBLES)
            # =========================================================================
            with ui.tab_panel(tab_jug):
                with ui.column().classes('w-full bg-white border border-slate-200 p-4 rounded-xl shadow-sm'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        ui.label("REGISTRO OFICIAL DE ATLETAS").classes('text-[10px] font-bold text-slate-400 tracking-wider')
                        def abrir_popup_nuevo_jugador_tab():
                            clubes_tab = ejecutar_consulta("SELECT id, nombre FROM equipos")
                            with ui.dialog() as dlg_nj, ui.card().classes('w-[400px] p-5 font-sans gap-3'):
                                ui.label("INSCRIBIR MUÑONISTA").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                                nj_nom = ui.input(label='Nombre').props('outlined dense').classes('w-full')
                                with ui.row().classes('w-full gap-2'):
                                    nj_atk = ui.number(label='ATK', value=50).props('outlined dense').classes('flex-1')
                                    nj_def = ui.number(label='DEF', value=50).props('outlined dense').classes('flex-1')
                                with ui.row().classes('w-full gap-2'):
                                    nj_bac = ui.number(label='BAC', value=50).props('outlined dense').classes('flex-1')
                                    nj_flo = ui.number(label='FLOT', value=50).props('outlined dense').classes('flex-1')
                                nj_prc = ui.number(label='Precio (M Pts)', value=1.2, step=0.5, min=0).props('outlined dense suffix="M"').classes('w-full')
                                nj_pos = ui.select(options=['JUG', 'POR'], value='JUG', label='Posición').props('outlined dense').classes('w-full')
                                nj_eq = ui.select(options={r[0]: r[1].upper() for r in clubes_tab}, label='Club (vacío=libre)').props('outlined dense clearable').classes('w-full')
                                with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                    ui.button('CANCELAR', on_click=dlg_nj.close).props('flat rounded size=sm').classes('text-slate-600')
                                    def guardar_nj(d=dlg_nj, n=nj_nom, a=nj_atk, dv=nj_def, b=nj_bac, f=nj_flo, p=nj_prc, pos=nj_pos, eq=nj_eq):
                                        if not n.value:
                                            ui.notify("❌ Nombre obligatorio.", type='negative')
                                            return
                                        ejecutar_consulta(
                                            "INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, bacora, flotabilidad, precio_pts, equipo_id, goles, est_actif) VALUES (?, 24, ?, ?, ?, ?, ?, ?, ?, 0, 1)",
                                            (n.value, pos.value, int(a.value), int(dv.value), int(b.value), int(f.value), int((p.value or 0) * 1_000_000), eq.value)
                                        )
                                        ui.notify(f"🏊 {n.value.upper()} inscrito.", type='positive')
                                        d.close()
                                        redibujar_jugadores()
                                    ui.button('INSCRIBIR', on_click=guardar_nj).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                            dlg_nj.open()
                        ui.button('+ JUGADOR', icon='person_add', on_click=abrir_popup_nuevo_jugador_tab).props('unelevated rounded size=sm').classes('bg-emerald-700 text-white text-xs')

                    box_jugadores = ui.column().classes('w-full')

                    def redibujar_jugadores():
                        box_jugadores.clear()
                        with box_jugadores:
                            filas_j = ejecutar_consulta("SELECT id, nombre, defensa, ataque, precio_pts, est_actif, posicion, bacora, flotabilidad FROM jugadores")
                            ddatos_j = [{
                                'id': f[0],
                                'nombre': f[1].upper(),
                                'defensa': f[2],
                                'ataque': f[3],
                                'precio_raw': f[4],
                                'precio': formatear_precio_corto(f[4]),
                                'activo': "SÍ" if f[5]==1 else "NO",
                                'pos': f[6],
                                'bac': f[7] or 0,
                                'flot': f[8] or 0,
                            } for f in filas_j]

                            cols_j = [
                                {'name': 'nombre',  'label': 'MUÑÓN',     'field': 'nombre',  'align': 'left',   'sortable': True},
                                {'name': 'defensa', 'label': 'DEF',       'field': 'defensa', 'align': 'center', 'sortable': True},
                                {'name': 'ataque',  'label': 'ATK',       'field': 'ataque',  'align': 'center', 'sortable': True},
                                {'name': 'bac',     'label': 'BAC',       'field': 'bac',     'align': 'center', 'sortable': True},
                                {'name': 'flot',    'label': 'FLOT',      'field': 'flot',    'align': 'center', 'sortable': True},
                                {'name': 'precio',  'label': 'PRECIO',    'field': 'precio',  'align': 'right',  'sortable': True},
                                {'name': 'activo',  'label': 'ACTIVO',    'field': 'activo',  'align': 'center', 'sortable': True},
                                {'name': 'id',      'label': 'ACCIONES',  'field': 'id',      'align': 'center'}
                            ]

                            with ui.table(columns=cols_j, rows=ddatos_j, row_key='id').classes('w-full text-xs flat') as t_j:
                                t_j.add_slot('body-cell-id', '''
                                    <q-td :props="props">
                                        <q-btn dense flat color="primary" icon="edit" @click="$parent.$emit('modificar', props.row)" />
                                        <q-btn dense flat color="negative" icon="archive" @click="$parent.$emit('archivar', props.row.id)" />
                                    </q-td>
                                ''')

                                def abrir_pop_edicion(row):
                                    with ui.dialog() as pop, ui.card().classes('w-[400px] p-4 font-sans gap-3'):
                                        ui.label("MODIFICAR DATOS").classes('font-bold text-xs mb-1')
                                        edit_nom = ui.input(label='Nombre', value=row['nombre']).props('outlined dense').classes('w-full')
                                        with ui.row().classes('w-full gap-2'):
                                            edit_atk = ui.number(label='ATK', value=row['ataque']).props('outlined dense').classes('flex-1')
                                            edit_def = ui.number(label='DEF', value=row['defensa']).props('outlined dense').classes('flex-1')
                                        with ui.row().classes('w-full gap-2'):
                                            edit_bac = ui.number(label='BAC', value=row['bac']).props('outlined dense').classes('flex-1')
                                            edit_flo = ui.number(label='FLOT', value=row['flot']).props('outlined dense').classes('flex-1')
                                        edit_prc = ui.number(label='Precio (M Pts)', value=round((row['precio_raw'] or 0)/1_000_000, 1), step=0.5, min=0).props('outlined dense suffix="M"').classes('w-full')
                                        def aplicar():
                                            ejecutar_consulta("UPDATE jugadores SET nombre=?, ataque=?, defensa=?, bacora=?, flotabilidad=?, precio_pts=? WHERE id=?",
                                                (edit_nom.value, int(edit_atk.value), int(edit_def.value), int(edit_bac.value), int(edit_flo.value), int((edit_prc.value or 0) * 1_000_000), row['id']))
                                            ui.notify("Ficha modificada.", type='positive')
                                            pop.close()
                                            redibujar_jugadores()
                                        ui.button('GUARDAR', on_click=aplicar).props('unelevated rounded').classes('w-full bg-slate-900 text-white mt-1')
                                    pop.open()

                                def archivar(idx):
                                    ejecutar_consulta("UPDATE jugadores SET est_actif = 0 WHERE id = ?", (idx,))
                                    ui.notify("🗄️ El jugador ya no está activo en la liga.", type='info')
                                    redibujar_jugadores()

                                t_j.on('modificar', lambda msg: abrir_pop_edicion(msg.args))
                                t_j.on('archivar', lambda msg: archivar(msg.args))

                    redibujar_jugadores()

            # =========================================================================
            # TAB 2: EQUIPOS / LIGAS
            # =========================================================================
            with ui.tab_panel(tab_eq):
                # --- HEADER ---
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label("CLUBES AFILIADOS A LA FEDERACIÓN").classes('text-[10px] font-bold text-slate-400 tracking-wider')
                    def abrir_form_nuevo_equipo():
                        with ui.dialog() as dlg_n, ui.card().classes('w-[420px] p-5 font-sans gap-3'):
                            ui.label("FUNDAR NUEVO CLUB").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                            f_nom = ui.input(label='Nombre del Club').props('outlined dense').classes('w-full')
                            f_est = ui.input(label='Estadio / Piscina', value='Piscina Municipal').props('outlined dense').classes('w-full')
                            f_div = ui.select(
                                options=['Liga SuperEmpanadill', 'Liga Mandinga', 'Liga Intermuñonal'],
                                value='Liga SuperEmpanadill', label='Liga'
                            ).props('outlined dense').classes('w-full')
                            with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                ui.button('CANCELAR', on_click=dlg_n.close).props('flat rounded size=sm').classes('text-slate-600')
                                def confirmar(d=dlg_n, n=f_nom, e=f_est, dv=f_div):
                                    if not n.value:
                                        ui.notify("❌ Nombre obligatorio.", type='negative')
                                        return
                                    ejecutar_consulta(
                                        "INSERT INTO equipos (nombre, presupuesto_pts, estadio, division) VALUES (?, 15000000, ?, ?)",
                                        (n.value, e.value, dv.value)
                                    )
                                    ui.notify(f"🛡️ {n.value.upper()} afiliado.", type='positive')
                                    d.close()
                                    redibujar_tabla_equipos()
                                ui.button('REGISTRAR', on_click=confirmar).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                        dlg_n.open()
                    ui.button('+ FUNDAR NUEVO CLUB', icon='shield', on_click=abrir_form_nuevo_equipo).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')

                # --- DOS COLUMNAS ---
                with ui.row().style('display: flex; flex-direction: row; flex-wrap: nowrap; width: 100%; gap: 16px; align-items: start;'):
                    with ui.column().style('width: 48%; flex-shrink: 0;').classes('bg-white border border-slate-200 p-4 rounded-xl shadow-sm'):
                        ui.label("LISTADO DE CLUBES").classes('text-[10px] font-bold text-slate-400 tracking-wider mb-2')
                        with ui.row().classes('w-full gap-2 mb-2'):
                            filtro_nombre = ui.input(
                                placeholder='🔍 Buscar equipo...',
                                on_change=lambda e: redibujar_tabla_equipos()
                            ).props('outlined dense clearable').classes('flex-1 text-xs')
                            filtro_liga = ui.select(
                                options=['Todas', 'Liga SuperEmpanadill', 'Liga Mandinga', 'Liga Intermuñonal'],
                                value='Todas',
                                on_change=lambda e: redibujar_tabla_equipos()
                            ).props('outlined dense').classes('w-44 text-xs')
                        box_tabla_equipos = ui.column().classes('w-full')

                    box_desglose = ui.column().style('width: 48%; flex-shrink: 0;').classes('bg-white border border-slate-200 p-4 rounded-xl shadow-sm min-h-[300px]')

                LIGA_COLORS = {
                    'Liga SuperEmpanadill': 'bg-emerald-100 text-emerald-800',
                    'Liga Mandinga':        'bg-purple-100 text-purple-800',
                    'Liga Intermuñonal':    'bg-blue-100 text-blue-800',
                }

                def redibujar_tabla_equipos():
                    box_tabla_equipos.clear()
                    filtro_n = (filtro_nombre.value or '').lower()
                    filtro_l = filtro_liga.value
                    filas_e = ejecutar_consulta("SELECT id, nombre, estadio, division FROM equipos ORDER BY nombre")
                    with box_tabla_equipos:
                        for e_id, name, est, div in filas_e:
                            if filtro_n and filtro_n not in name.lower():
                                continue
                            if filtro_l != 'Todas' and div != filtro_l:
                                continue
                            badge_c = LIGA_COLORS.get(div, 'bg-slate-100 text-slate-600')
                            div_short = div.split(" ")[-1] if " " in div else div
                            with ui.row().classes('w-full justify-between items-center p-2 border-b border-slate-100 hover:bg-slate-50 cursor-pointer rounded') \
                                    .on('click', lambda _, idx=e_id: cargar_desglose_equipo(idx)):
                                with ui.column().classes('gap-0'):
                                    ui.label(name.upper()).classes('font-bold text-xs text-slate-800')
                                    ui.label(f"🏟️ {est}").classes('text-[10px] text-slate-400')
                                ui.label(div_short).classes(f'text-[9px] font-bold px-1.5 py-0.5 rounded {badge_c}')

                def cargar_desglose_equipo(eq_id):
                    box_desglose.clear()
                    conn = obtener_conexion_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT nombre, division, entrenador_id, presupuesto_pts FROM equipos WHERE id=?", (eq_id,))
                    n_club, d_club, ent_id, presupuesto_pts = cursor.fetchone()
                    cursor.execute("SELECT id, nombre, posicion, ataque, defensa, precio_pts FROM jugadores WHERE equipo_id=? ORDER BY nombre", (eq_id,))
                    militantes = cursor.fetchall()
                    cursor.execute("SELECT id, nombre FROM jugadores WHERE equipo_id IS NULL AND est_actif=1 ORDER BY nombre")
                    libres = cursor.fetchall()
                    conn.close()

                    with box_desglose:
                        with ui.row().classes('w-full justify-between items-center border-b pb-2 mb-3'):
                            ui.label(f"PLANTILLA: {n_club.upper()}").classes('font-bold text-sm text-slate-900')
                            def abrir_form_jugador(cid=eq_id):
                                with ui.dialog() as dlg_j, ui.card().classes('w-[400px] p-5 font-sans gap-3'):
                                    ui.label("INSCRIBIR JUGADOR").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                                    jf_nom = ui.input(label='Nombre').props('outlined dense').classes('w-full')
                                    with ui.row().classes('w-full gap-2'):
                                        jf_atk = ui.number(label='ATK', value=50).props('outlined dense').classes('flex-1')
                                        jf_def = ui.number(label='DEF', value=50).props('outlined dense').classes('flex-1')
                                    with ui.row().classes('w-full gap-2'):
                                        jf_bac = ui.number(label='BAC', value=50).props('outlined dense').classes('flex-1')
                                        jf_flo = ui.number(label='FLOT', value=50).props('outlined dense').classes('flex-1')
                                    jf_prc = ui.number(label='Precio (M Pts)', value=1.2, step=0.5, min=0).props('outlined dense suffix="M"').classes('w-full')
                                    jf_pos = ui.select(options=['JUG', 'POR'], value='JUG', label='Posición').props('outlined dense').classes('w-full')
                                    with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                        ui.button('CANCELAR', on_click=dlg_j.close).props('flat rounded size=sm').classes('text-slate-600')
                                        def guardar_jugador(d=dlg_j, n=jf_nom, a=jf_atk, dv=jf_def, b=jf_bac, f=jf_flo, p=jf_prc, pos=jf_pos, c=cid):
                                            if not n.value:
                                                ui.notify("❌ Nombre obligatorio.", type='negative')
                                                return
                                            ejecutar_consulta(
                                                "INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, bacora, flotabilidad, precio_pts, equipo_id, goles, est_actif) VALUES (?, 24, ?, ?, ?, ?, ?, ?, ?, 0, 1)",
                                                (n.value, pos.value, int(a.value), int(dv.value), int(b.value), int(f.value), int((p.value or 0) * 1_000_000), c)
                                            )
                                            ui.notify(f"🏊 {n.value.upper()} inscrito.", type='positive')
                                            d.close()
                                            cargar_desglose_equipo(c)
                                        ui.button('INSCRIBIR', on_click=guardar_jugador).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                                dlg_j.open()
                            ui.button('+ JUGADOR', icon='person_add', on_click=abrir_form_jugador).props('unelevated rounded size=sm').classes('bg-emerald-700 text-white text-xs')

                        with ui.row().classes('w-full items-center gap-2 bg-slate-50 p-2 rounded-lg mb-2 text-xs'):
                            ui.icon('badge').classes('text-base text-slate-400')
                            nombre_input = ui.input(label='Nombre del club', value=n_club).props('outlined dense').classes('flex-1 bg-white text-xs')
                            def guardar_nombre_equipo(ni=nombre_input, eid=eq_id):
                                nuevo = ni.value.strip()
                                if not nuevo:
                                    ui.notify("❌ El nombre no puede estar vacío.", type='negative')
                                    return
                                ejecutar_consulta("UPDATE equipos SET nombre = ? WHERE id = ?", (nuevo, eid))
                                ui.notify(f"✅ Club renombrado a «{nuevo.upper()}».", type='positive')
                                redibujar_tabla_equipos()
                                cargar_desglose_equipo(eid)
                            ui.button('RENOMBRAR', on_click=guardar_nombre_equipo).props('unelevated rounded size=sm').classes('bg-slate-700 text-white text-xs')

                        with ui.row().classes('w-full items-center gap-2 bg-slate-50 p-2 rounded-lg mb-2 text-xs'):
                            ui.icon('account_balance_wallet').classes('text-base text-slate-400')
                            presupuesto_input = ui.number(
                                label='Presupuesto (M Pts)',
                                value=round((presupuesto_pts or 0) / 1_000_000, 1),
                                step=1, min=0
                            ).props('outlined dense suffix="M"').classes('flex-1 bg-white text-xs')
                            def guardar_presupuesto(pi=presupuesto_input, eid=eq_id):
                                ejecutar_consulta(
                                    "UPDATE equipos SET presupuesto_pts = ? WHERE id = ?",
                                    (int((pi.value or 0) * 1_000_000), eid)
                                )
                                ui.notify(f"💰 Presupuesto actualizado a {pi.value:.1f}M Pts.", type='positive')
                            ui.button('GUARDAR', on_click=guardar_presupuesto).props('unelevated rounded size=sm').classes('bg-green-700 text-white text-xs')

                        with ui.row().classes('w-full items-center gap-2 bg-slate-50 p-2 rounded-lg mb-3 text-xs'):
                            ui.label("Liga:").classes('font-semibold text-slate-500 shrink-0')
                            div_select = ui.select(
                                options=['Liga SuperEmpanadill', 'Liga Mandinga', 'Liga Intermuñonal'],
                                value=d_club
                            ).props('outlined dense').classes('flex-1 bg-white text-xs')
                            def alterar_liga(ds=div_select, eid=eq_id):
                                ejecutar_consulta("UPDATE equipos SET division=? WHERE id=?", (ds.value, eid))
                                ui.notify(f"🚀 Transferido a {ds.value}.", type='info')
                                redibujar_tabla_equipos()
                            ui.button('GUARDAR', on_click=alterar_liga).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')

                        entrenadores_opts = ejecutar_consulta("""
                            SELECT id, nombre FROM entrenadores
                            WHERE id NOT IN (
                                SELECT entrenador_id FROM equipos
                                WHERE entrenador_id IS NOT NULL AND id != ?
                            )
                            ORDER BY nombre
                        """, (eq_id,))
                        with ui.row().classes('w-full items-center gap-2 bg-amber-50 p-2 rounded-lg mb-3 text-xs'):
                            ui.label("Entrenador:").classes('font-semibold text-slate-500 shrink-0')
                            ent_select = ui.select(
                                options={r[0]: r[1].upper() for r in entrenadores_opts},
                                value=ent_id
                            ).props('outlined dense clearable').classes('flex-1 bg-white text-xs')
                            def guardar_entrenador(es=ent_select, eid=eq_id):
                                nuevo_ent_id = es.value
                                if nuevo_ent_id:
                                    ejecutar_consulta("UPDATE equipos SET entrenador_id = NULL WHERE entrenador_id = ?", (nuevo_ent_id,))
                                ejecutar_consulta("UPDATE equipos SET entrenador_id = ? WHERE id = ?", (nuevo_ent_id, eid))
                                ui.notify("Entrenador asignado." if nuevo_ent_id else "Entrenador desvinculado.", type='positive')
                                cargar_desglose_equipo(eid)
                            ui.button('ASIGNAR', on_click=guardar_entrenador).props('unelevated rounded size=sm').classes('bg-amber-600 text-white text-xs')

                        if militantes:
                            cols_m = [
                                {'name': 'nombre', 'label': 'JUGADOR', 'field': 'nombre', 'align': 'left'},
                                {'name': 'pos',    'label': 'POS',     'field': 'pos',    'align': 'center'},
                                {'name': 'atk',    'label': 'ATK',     'field': 'atk',    'align': 'center'},
                                {'name': 'def_',   'label': 'DEF',     'field': 'def_',   'align': 'center'},
                                {'name': 'id',     'label': '',        'field': 'id',     'align': 'center', 'style': 'width:40px'},
                            ]
                            rows_m = [{'id': r[0], 'nombre': r[1].upper(), 'pos': r[2], 'atk': r[3], 'def_': r[4], 'precio': r[5]} for r in militantes]
                            with ui.table(columns=cols_m, rows=rows_m, row_key='id').classes('w-full text-xs flat dense') as t_m:
                                t_m.props('hide-bottom')
                                t_m.add_slot('body-cell-id', '''
                                    <q-td :props="props" class="q-pa-xs">
                                        <q-btn flat dense size="xs" color="primary" icon="edit" @click="$parent.$emit('modificar', props.row)" />
                                        <q-btn flat dense size="xs" color="negative" icon="remove_circle" @click="$parent.$emit('quitar', props.row.id)" />
                                    </q-td>
                                ''')
                                def hacer_quitar(msg, cid=eq_id):
                                    ejecutar_consulta("UPDATE jugadores SET equipo_id=NULL, titular=0 WHERE id=?", (msg.args,))
                                    cargar_desglose_equipo(cid)
                                t_m.on('quitar', hacer_quitar)
                                def hacer_modificar(msg, cid=eq_id):
                                    row = msg.args
                                    with ui.dialog() as dlg_e, ui.card().classes('w-[380px] p-5 font-sans gap-3'):
                                        ui.label("MODIFICAR JUGADOR").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                                        em_nom = ui.input(label='Nombre', value=row['nombre']).props('outlined dense').classes('w-full')
                                        with ui.row().classes('w-full gap-2'):
                                            em_atk = ui.number(label='ATK', value=row['atk']).props('outlined dense').classes('flex-1')
                                            em_def = ui.number(label='DEF', value=row['def_']).props('outlined dense').classes('flex-1')
                                        em_prc = ui.number(label='Precio (M Pts)', value=round(row['precio']/1_000_000, 1), step=0.5, min=0).props('outlined dense suffix="M"').classes('w-full')
                                        em_pos = ui.select(options=['JUG', 'POR'], value=row['pos'], label='Posición').props('outlined dense').classes('w-full')
                                        with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                            ui.button('CANCELAR', on_click=dlg_e.close).props('flat rounded size=sm').classes('text-slate-600')
                                            def aplicar_edicion(d=dlg_e, n=em_nom, a=em_atk, dv=em_def, p=em_prc, pos=em_pos, rid=row['id'], c=cid):
                                                ejecutar_consulta("UPDATE jugadores SET nombre=?, ataque=?, defensa=?, precio_pts=?, posicion=? WHERE id=?", (n.value, int(a.value), int(dv.value), int((p.value or 0) * 1_000_000), pos.value, rid))
                                                ui.notify("Ficha actualizada.", type='positive')
                                                d.close()
                                                cargar_desglose_equipo(c)
                                            ui.button('GUARDAR', on_click=aplicar_edicion).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                                    dlg_e.open()
                                t_m.on('modificar', hacer_modificar)
                        else:
                            ui.label("Sin jugadores en plantilla.").classes('text-xs text-slate-400 italic py-2')

                        if libres:
                            ui.element('div').classes('w-full border-t border-dashed border-slate-200 my-3')
                            with ui.row().classes('w-full gap-2 items-center'):
                                sel_l = ui.select(options={r[0]: r[1].upper() for r in libres}, label='Inyectar Muñón Libre').props('outlined dense clearable').classes('flex-1 text-xs')
                                def meter(cid=eq_id, sl=sel_l):
                                    if not sl.value: return
                                    ejecutar_consulta("UPDATE jugadores SET equipo_id=? WHERE id=?", (cid, sl.value))
                                    ui.notify("Jugador incorporado.", type='positive')
                                    cargar_desglose_equipo(cid)
                                ui.button(icon='add', on_click=meter).props('unelevated square').classes('bg-slate-900 text-white h-10 w-10 rounded-lg')

                redibujar_tabla_equipos()
                filas_init = ejecutar_consulta("SELECT id FROM equipos ORDER BY nombre LIMIT 1")
                if filas_init:
                    cargar_desglose_equipo(filas_init[0][0])

            # =========================================================================
            # TAB 3: ESTADIOS (CON FORMULARIO COMPLETO)
            # =========================================================================
            with ui.tab_panel(tab_est):
                def guardar_nuevo_estadio():
                    if not est_nom.value or not est_eq.value: return
                    ejecutar_consulta("UPDATE equipos SET estadio = ?, aforo = ? WHERE id = ?",
                        (est_nom.value, int(est_aforo.value or 5000), est_eq.value))
                    ui.notify(f"🏟️ Feudo municipal reasignado correctamente.", type='positive')
                    est_nom.value = ''
                    est_aforo.value = 5000
                    redibujar_estadios()

                with ui.row().classes('w-full gap-6 items-start flex-row flex-nowrap'):
                    with ui.column().style('width: 35%; flex-shrink: 0;').classes('bg-white p-4 border border-slate-200 rounded-xl shadow-sm gap-3'):
                        ui.label("REGISTRAR COMPLEJO").classes('text-[10px] font-bold text-slate-400 tracking-wider')
                        est_nom = ui.input(label='Nombre de la Piscina / Estadio').props('outlined dense').classes('w-full')
                        est_aforo = ui.number(label='Aforo', value=5000, min=0, step=500).props('outlined dense').classes('w-full')
                        clubes_db = ejecutar_consulta("SELECT id, nombre FROM equipos")
                        est_eq = ui.select(options={r[0]: r[1].upper() for r in clubes_db}, label='Club Residente').props('outlined dense').classes('w-full')
                        ui.button('ASIGNAR ESTADIO', on_click=guardar_nuevo_estadio).props('unelevated rounded').classes('w-full bg-slate-900 text-white text-xs h-9')

                    box_estadios = ui.column().classes('flex-1')

                    def redibujar_estadios():
                        box_estadios.clear()
                        with box_estadios:
                            cols_est = [
                                {'name': 'estadio', 'label': 'ESTADIO / PISCINA', 'field': 'estadio', 'align': 'left', 'sortable': True},
                                {'name': 'club',    'label': 'CLUB',              'field': 'club',    'align': 'left', 'sortable': True},
                                {'name': 'aforo',   'label': 'AFORO',             'field': 'aforo',   'align': 'center', 'sortable': True},
                                {'name': 'id',      'label': '',                  'field': 'id',      'align': 'center', 'style': 'width:50px'},
                            ]
                            filas_est = ejecutar_consulta("SELECT id, nombre, estadio, aforo FROM equipos ORDER BY nombre")
                            rows_est = [{
                                'id': r[0], 'club': r[1].upper(),
                                'estadio': (r[2] or '').upper(),
                                'aforo': r[3] or 0
                            } for r in filas_est]
                            with ui.table(columns=cols_est, rows=rows_est, row_key='id').classes('w-full text-xs flat bg-white border border-slate-200 rounded-xl shadow-sm') as t_est:
                                t_est.add_slot('body-cell-id', '''
                                    <q-td :props="props">
                                        <q-btn flat dense size="xs" color="primary" icon="edit" @click="$parent.$emit('editar', props.row)" />
                                    </q-td>
                                ''')
                                def abrir_edit_estadio(row):
                                    with ui.dialog() as pop_e, ui.card().classes('w-[360px] p-4 font-sans gap-3'):
                                        ui.label("MODIFICAR ESTADIO").classes('font-bold text-xs text-slate-400 tracking-wider mb-1')
                                        e_name = ui.input(label='Nombre', value=row['estadio']).props('outlined dense').classes('w-full')
                                        e_aforo = ui.number(label='Aforo', value=row['aforo'], min=0, step=500).props('outlined dense').classes('w-full')
                                        def guardar_edit():
                                            ejecutar_consulta("UPDATE equipos SET estadio = ?, aforo = ? WHERE id = ?",
                                                (e_name.value, int(e_aforo.value or 0), row['id']))
                                            ui.notify("🏟️ Estadio actualizado.", type='positive')
                                            pop_e.close()
                                            redibujar_estadios()
                                        with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                            ui.button('CANCELAR', on_click=pop_e.close).props('flat rounded size=sm').classes('text-slate-600')
                                            ui.button('GUARDAR', on_click=guardar_edit).props('unelevated rounded size=sm').classes('bg-slate-900 text-white')
                                    pop_e.open()
                                t_est.on('editar', lambda msg: abrir_edit_estadio(msg.args))

                    redibujar_estadios()

            # =========================================================================
            # TAB 4: PARTE MÉDICO — catálogo de lesiones
            # =========================================================================
            with ui.tab_panel(tab_les):
                ejecutar_consulta("""CREATE TABLE IF NOT EXISTS lesiones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    semanas INTEGER
                )""")

                box_lesiones = ui.column().classes('w-full')

                def redibujar_lesiones():
                    box_lesiones.clear()
                    filas_les = ejecutar_consulta("SELECT id, nombre, semanas FROM lesiones ORDER BY nombre")
                    with box_lesiones:
                        if not filas_les:
                            ui.label("Catálogo vacío.").classes('text-xs text-slate-400 italic py-4')
                            return
                        cols_les = [
                            {'name': 'nombre',  'label': 'LESIÓN',   'field': 'nombre',  'align': 'left',   'sortable': True},
                            {'name': 'semanas', 'label': 'SEMANAS',  'field': 'semanas', 'align': 'center', 'sortable': True},
                            {'name': 'id',      'label': '',         'field': 'id',      'align': 'center', 'style': 'width:60px'},
                        ]
                        rows_les = [{'id': r[0], 'nombre': r[1], 'semanas': r[2]} for r in filas_les]
                        with ui.table(columns=cols_les, rows=rows_les, row_key='id').classes('w-full text-xs flat') as t_les:
                            t_les.add_slot('body-cell-id', '''
                                <q-td :props="props" class="q-pa-xs">
                                    <q-btn flat dense size="xs" color="primary" icon="edit"   @click="$parent.$emit('editar_les', props.row)" />
                                    <q-btn flat dense size="xs" color="negative" icon="delete" @click="$parent.$emit('borrar_les', props.row.id)" />
                                </q-td>
                            ''')
                            def abrir_edicion_lesion(row):
                                with ui.dialog() as dlg_el, ui.card().classes('w-[360px] p-5 font-sans gap-3'):
                                    ui.label("MODIFICAR LESIÓN").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                                    el_nom = ui.input(label='Nombre de la lesión', value=row['nombre']).props('outlined dense').classes('w-full')
                                    el_sem = ui.number(label='Semanas de baja', value=row['semanas']).props('outlined dense').classes('w-full')
                                    with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                        ui.button('CANCELAR', on_click=dlg_el.close).props('flat rounded size=sm').classes('text-slate-600')
                                        def guardar_edicion(d=dlg_el, n=el_nom, s=el_sem, rid=row['id']):
                                            if not n.value:
                                                ui.notify("❌ Nombre obligatorio.", type='negative')
                                                return
                                            ejecutar_consulta("UPDATE lesiones SET nombre=?, semanas=? WHERE id=?", (n.value, int(s.value or 0), rid))
                                            ui.notify("Lesión actualizada.", type='positive')
                                            d.close()
                                            redibujar_lesiones()
                                        ui.button('GUARDAR', on_click=guardar_edicion).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                                dlg_el.open()
                            def borrar_lesion(les_id):
                                ejecutar_consulta("DELETE FROM lesiones WHERE id=?", (les_id,))
                                ui.notify("Lesión eliminada.", type='warning')
                                redibujar_lesiones()
                            t_les.on('editar_les', lambda msg: abrir_edicion_lesion(msg.args))
                            t_les.on('borrar_les', lambda msg: borrar_lesion(msg.args))

                with ui.row().classes('w-full gap-6 items-start flex-row flex-nowrap mb-4'):
                    with ui.column().style('width: 40%; flex-shrink: 0;').classes('bg-white p-4 border border-slate-200 rounded-xl shadow-sm gap-3'):
                        ui.label("REGISTRAR NUEVA LESIÓN").classes('text-[10px] font-bold text-slate-400 tracking-wider')
                        nl_nom = ui.input(label='Nombre de la lesión').props('outlined dense').classes('w-full')
                        nl_sem = ui.number(label='Semanas de baja', value=2, min=1).props('outlined dense').classes('w-full')
                        def añadir_lesion():
                            if not nl_nom.value:
                                ui.notify("❌ Nombre obligatorio.", type='negative')
                                return
                            ejecutar_consulta("INSERT INTO lesiones (nombre, semanas) VALUES (?, ?)", (nl_nom.value, int(nl_sem.value or 1)))
                            ui.notify(f"🩺 '{nl_nom.value}' añadida al catálogo.", type='positive')
                            nl_nom.set_value('')
                            nl_sem.set_value(2)
                            redibujar_lesiones()
                        ui.button('AÑADIR AL CATÁLOGO', icon='add', on_click=añadir_lesion).props('unelevated rounded').classes('w-full bg-rose-700 text-white text-xs h-9')

                    with ui.column().classes('flex-1 bg-white p-4 border border-slate-200 rounded-xl shadow-sm'):
                        ui.label("CATÁLOGO DE LESIONES").classes('text-[10px] font-bold text-slate-400 tracking-wider mb-2')
                        redibujar_lesiones()

            # =========================================================================
            # TAB 5: ENTRENADORES
            # =========================================================================
            with ui.tab_panel(tab_ent):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label("CUERPO TÉCNICO FEDERATIVO").classes('text-[10px] font-bold text-slate-400 tracking-wider')
                    def abrir_form_entrenador(ent_row=None):
                        es_edicion = ent_row is not None
                        with ui.dialog() as dlg_ent, ui.card().classes('w-[440px] p-5 font-sans gap-3'):
                            ui.label("MODIFICAR ENTRENADOR" if es_edicion else "FICHAR ENTRENADOR").classes('text-xs font-bold text-slate-400 tracking-wider mb-1')
                            e_nom = ui.input(label='Nombre', value=ent_row['nombre'] if es_edicion else '').props('outlined dense').classes('w-full')
                            e_mot = ui.input(label='Mote', value=ent_row['mote'] if es_edicion else '').props('outlined dense').classes('w-full')
                            with ui.row().classes('w-full gap-2'):
                                e_atk = ui.number(label='Bono ATK', value=ent_row['batk'] if es_edicion else 0).props('outlined dense').classes('flex-1')
                                e_def = ui.number(label='Bono DEF', value=ent_row['bdef'] if es_edicion else 0).props('outlined dense').classes('flex-1')
                            e_fra = ui.input(label='Frase mítica', value=ent_row['frase'] if es_edicion else '').props('outlined dense').classes('w-full')
                            e_prc = ui.number(label='Precio (M Pts)', value=round(ent_row['precio']/1_000_000, 1) if es_edicion else 0.5, step=0.5, min=0).props('outlined dense suffix="M"').classes('w-full')
                            with ui.row().classes('w-full gap-2 justify-end mt-2'):
                                ui.button('CANCELAR', on_click=dlg_ent.close).props('flat rounded size=sm').classes('text-slate-600')
                                def guardar_ent(d=dlg_ent, n=e_nom, m=e_mot, a=e_atk, dv=e_def, f=e_fra, p=e_prc, row=ent_row):
                                    if not n.value:
                                        ui.notify("❌ Nombre obligatorio.", type='negative')
                                        return
                                    precio = int((p.value or 0) * 1_000_000)
                                    if row:
                                        ejecutar_consulta(
                                            "UPDATE entrenadores SET nombre=?, mote=?, bono_ataque=?, bono_defensa=?, frase_mitica=?, precio_pts=? WHERE id=?",
                                            (n.value, m.value, int(a.value), int(dv.value), f.value, precio, row['id'])
                                        )
                                        ui.notify("Ficha actualizada.", type='positive')
                                    else:
                                        ejecutar_consulta(
                                            "INSERT INTO entrenadores (nombre, mote, bono_ataque, bono_defensa, frase_mitica, precio_pts) VALUES (?, ?, ?, ?, ?, ?)",
                                            (n.value, m.value, int(a.value), int(dv.value), f.value, precio)
                                        )
                                        ui.notify(f"🎽 {n.value.upper()} fichado.", type='positive')
                                    d.close()
                                    redibujar_entrenadores()
                                ui.button('GUARDAR', on_click=guardar_ent).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')
                        dlg_ent.open()
                    ui.button('+ FICHAR ENTRENADOR', icon='sports', on_click=lambda: abrir_form_entrenador()).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs')

                box_entrenadores = ui.column().classes('w-full')

                def redibujar_entrenadores():
                    box_entrenadores.clear()
                    with box_entrenadores:
                        entrenadores_db = ejecutar_consulta("""
                            SELECT ent.id, ent.nombre, ent.mote, ent.bono_ataque, ent.bono_defensa,
                                   ent.frase_mitica, ent.precio_pts, eq.nombre
                            FROM entrenadores ent
                            LEFT JOIN equipos eq ON eq.entrenador_id = ent.id
                            ORDER BY ent.nombre
                        """)
                        if not entrenadores_db:
                            ui.label("No hay entrenadores registrados.").classes('text-xs text-slate-400 italic py-4')
                        else:
                            cols_ent = [
                                {'name': 'nombre', 'label': 'NOMBRE',  'field': 'nombre',     'align': 'left',   'sortable': True},
                                {'name': 'mote',   'label': 'MOTE',    'field': 'mote',       'align': 'left',   'style': 'max-width:180px; width:180px'},
                                {'name': 'batk',   'label': 'B.ATK',   'field': 'batk',       'align': 'center', 'sortable': True},
                                {'name': 'bdef',   'label': 'B.DEF',   'field': 'bdef',       'align': 'center', 'sortable': True},
                                {'name': 'frase',  'label': 'FRASE',   'field': 'frase',      'align': 'left',   'style': 'max-width:220px; width:220px'},
                                {'name': 'precio', 'label': 'PRECIO',  'field': 'precio_fmt', 'align': 'right'},
                                {'name': 'equipo', 'label': 'EQUIPO',  'field': 'equipo',     'align': 'left'},
                                {'name': 'id',     'label': '',        'field': 'id',         'align': 'center', 'style': 'width:60px'},
                            ]
                            rows_ent = [{
                                'id': r[0], 'nombre': r[1].upper(), 'mote': r[2] or '', 'batk': r[3],
                                'bdef': r[4], 'frase': r[5] or '', 'precio': r[6] or 0,
                                'precio_fmt': formatear_precio_corto(r[6] or 0),
                                'equipo': r[7] or '—'
                            } for r in entrenadores_db]
                            with ui.table(columns=cols_ent, rows=rows_ent, row_key='id').classes('w-full text-xs flat') as t_ent:
                                t_ent.add_slot('body-cell-mote', '''
                                    <q-td :props="props" style="max-width:180px; width:180px;">
                                        <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;"
                                             :title="props.value">{{ props.value }}</div>
                                    </q-td>
                                ''')
                                t_ent.add_slot('body-cell-frase', '''
                                    <q-td :props="props" style="max-width:220px; width:220px;">
                                        <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:220px;"
                                             :title="props.value">{{ props.value }}</div>
                                    </q-td>
                                ''')
                                t_ent.add_slot('body-cell-id', '''
                                    <q-td :props="props" class="q-pa-xs">
                                        <q-btn flat dense size="xs" color="primary" icon="edit" @click="$parent.$emit('editar', props.row)" />
                                        <q-btn flat dense size="xs" color="negative" icon="delete" @click="$parent.$emit('borrar', props.row.id)" />
                                    </q-td>
                                ''')
                                def hacer_editar_ent(msg):
                                    abrir_form_entrenador(msg.args)
                                t_ent.on('editar', hacer_editar_ent)
                                def hacer_borrar_ent(msg):
                                    ejecutar_consulta("DELETE FROM entrenadores WHERE id=?", (msg.args,))
                                    ui.notify("Entrenador eliminado.", type='warning')
                                    redibujar_entrenadores()
                                t_ent.on('borrar', hacer_borrar_ent)

                redibujar_entrenadores()