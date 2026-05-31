from nicegui import ui
import sqlite3
import main

def obtener_conexion_db():
    return sqlite3.connect(main.obtener_ruta_db())
# Diccionario con las coordenadas reales de cada sistema táctico en la piscina
ESTRATEGIAS = {
    '1-2-2': {
        1: 'bottom: 8%; left: 45%;',   # Portero
        2: 'bottom: 35%; left: 18%;',  # Defensa Izquierdo
        3: 'bottom: 35%; left: 72%;',  # Defensa Derecho
        4: 'top: 25%; left: 22%;',     # Atacante Izquierdo
        5: 'top: 25%; left: 68%;',     # Atacante Derecho
    },
    '1-3-1': {
        1: 'bottom: 8%; left: 45%;',   # Portero
        2: 'bottom: 35%; left: 15%;',  # Defensa Izquierdo
        3: 'bottom: 40%; left: 45%;',  # Cierre / Medio
        4: 'bottom: 35%; left: 75%;',  # Defensa Derecho
        5: 'top: 22%; left: 45%;',     # Boya / Atacante
    },
    '1-1-3': {
        1: 'bottom: 8%; left: 45%;',   # Portero
        2: 'bottom: 38%; left: 45%;',  # Único Defensa
        3: 'top: 25%; left: 15%;',     # Atacante Izquierdo
        4: 'top: 22%; left: 45%;',     # Atacante Centro
        5: 'top: 25%; left: 75%;',     # Atacante Derecho
    },
    '1-4-0': {
        1: 'bottom: 8%; left: 45%;',   # Portero
        2: 'bottom: 38%; left: 12%;',  # Línea defensiva ultra-poblada
        3: 'bottom: 38%; left: 34%;',
        4: 'bottom: 38%; left: 56%;',
        5: 'bottom: 38%; left: 78%;',
    },
    '0-0-5': {
        1: 'top: 22%; left: 10%;',     # ¡Todos arriba al abordaje, sin portero!
        2: 'top: 22%; left: 30%;',
        3: 'top: 20%; left: 50%;',
        4: 'top: 22%; left: 70%;',
        5: 'top: 22%; left: 90%;',
    }
}

tactica_actual = '1-2-2'

def abrir_popup_rival():
    from main import obtener_proximo_rival_info
    _, rival_id, _ = obtener_proximo_rival_info()
    if not rival_id:
        ui.notify('No hay próximo rival registrado', type='warning')
        return

    conn = obtener_conexion_db()
    cur = conn.cursor()

    cur.execute("SELECT e.nombre, ent.nombre, ent.mote, ent.bono_ataque, ent.bono_defensa FROM equipos e LEFT JOIN entrenadores ent ON e.entrenador_id = ent.id WHERE e.id = ?", (rival_id,))
    eq_row = cur.fetchone()
    nom_rival = eq_row[0] if eq_row else 'Rival'
    ent_nombre, ent_apodo, ent_atk, ent_def = (eq_row[1], eq_row[2], eq_row[3], eq_row[4]) if eq_row and eq_row[1] else (None, None, 0, 0)

    cur.execute("""
        SELECT nombre, defensa, ataque, bacora, flotabilidad, titular, semanas_lesion
        FROM jugadores WHERE equipo_id = ?
        ORDER BY titular DESC, nombre
    """, (rival_id,))
    todos = cur.fetchall()
    conn.close()

    cols_r = [
        {'name': 'nombre', 'label': 'JUGADOR', 'field': 'nombre', 'align': 'left'},
        {'name': 'def',    'label': 'DEF',     'field': 'def',    'align': 'center', 'style': 'width:40px'},
        {'name': 'atk',    'label': 'ATK',     'field': 'atk',    'align': 'center', 'style': 'width:40px'},
        {'name': 'bac',    'label': 'BAC',     'field': 'bac',    'align': 'center', 'style': 'width:40px'},
        {'name': 'flot',   'label': 'FLOT',    'field': 'flot',   'align': 'center', 'style': 'width:40px'},
        {'name': 'med',    'label': 'MED',     'field': 'med',    'align': 'center', 'style': 'width:45px'},
    ]

    rows_r = []
    for n, d, a, b, f, t, sl in todos:
        nombre_display = f'🚑 {n}' if sl and sl > 0 else n
        rows_r.append({
            'nombre': nombre_display,
            'def': d or 0, 'atk': a or 0, 'bac': b or 0, 'flot': f or 0,
            'med': int(((d or 0) + (a or 0)) / 2),
        })

    with ui.dialog() as dlg, ui.card().classes('w-[580px] bg-white p-5 rounded-2xl shadow-xl font-sans text-slate-900 gap-3'):
        with ui.row().classes('w-full justify-between items-center border-b border-slate-100 pb-3'):
            with ui.column().classes('gap-0'):
                ui.label(nom_rival.upper()).classes('text-lg font-extrabold text-slate-800 tracking-tight')
                ui.label('Plantilla completa del próximo rival').classes('text-[10px] text-slate-400')
            ui.button(icon='close', on_click=dlg.close).props('flat round dense').classes('text-slate-400')

        if ent_nombre:
            with ui.row().classes('w-full items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg p-2'):
                ui.icon('sports', color='amber').classes('text-base')
                ui.label(ent_nombre).classes('text-xs font-bold text-amber-900 flex-1')
                if ent_apodo:
                    ui.label(f'"{ent_apodo}"').classes('text-[10px] italic text-amber-700')
                ui.label(f'ATK +{ent_atk or 0}').classes('text-[10px] font-semibold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded')
                ui.label(f'DEF +{ent_def or 0}').classes('text-[10px] font-semibold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded')
        else:
            with ui.row().classes('w-full items-center gap-2 bg-slate-100 border border-slate-200 rounded-lg p-2'):
                ui.icon('sports', color='grey').classes('text-base')
                ui.label('Sin entrenador asignado').classes('text-[10px] italic text-slate-400')

        # --- PLANTILLA COMPLETA ---
        ui.label(f'PLANTILLA — {len(rows_r)} jugadores').classes('text-[9px] font-bold text-slate-400 tracking-widest mt-1')
        with ui.table(columns=cols_r, rows=rows_r, row_key='nombre').classes('w-full bg-slate-50 border border-slate-200 flat font-sans text-slate-800 shadow-sm dense') as t_r:
            t_r.props('hide-bottom')
            t_r.add_slot('body-cell-med', '''
                <q-td :props="props" class="q-pa-xs">
                    <q-badge color="slate-7" class="text-bold px-1.5 py-0.5 rounded">{{ props.value }}</q-badge>
                </q-td>
            ''')

        dlg.open()

def menu_alineacion():
    global tactica_actual
    from main import obtener_mi_equipo_id

    ui.dark_mode().disable()
    equipo_id = obtener_mi_equipo_id()

    # LAYOUT DE PANTALLA COMPLETA — contenedores creados en su posición correcta
    with ui.column().classes('w-full p-6 bg-slate-50 min-h-screen font-sans text-slate-900'):
        with ui.row().classes('w-full border-b border-slate-200 pb-4 justify-between items-center mb-4'):
            with ui.column().classes('gap-0'):
                ui.label("Estrategia del Equipo").classes('text-2xl font-bold tracking-tight text-slate-900')
                ui.label("Define el quinteto de agua y su distribución").classes('text-xs text-slate-400')
            with ui.row().classes('gap-2'):
                ui.button("VER RIVAL", icon='visibility', on_click=abrir_popup_rival) \
                    .classes('bg-rose-700 text-white text-xs font-semibold rounded-lg h-9 px-4 hover:bg-rose-800 transition')
                ui.button("CONFIRMAR Y SALIR", on_click=lambda: ui.navigate.to('/despacho')) \
                    .classes('bg-slate-900 text-white text-xs font-semibold rounded-lg h-9 px-4 hover:bg-slate-800 transition')


        with ui.row().style('display: flex; flex-direction: row; flex-wrap: nowrap; width: 100%; gap: 24px; align-items: start;'):
            with ui.column().style('width: 55%; flex-shrink: 0;'):
                box_titulares = ui.column().classes('w-full')
                box_suplentes = ui.column().classes('w-full')
                box_ambulatorio = ui.column().classes('w-full')

            with ui.column().style('width: 42%; flex-shrink: 0;').classes('bg-white p-4 border border-slate-200 rounded-xl shadow-sm items-center'):
                ui.label("DISPOSICIÓN TÁCTICA EN PISCINA").classes('text-slate-400 font-bold text-[10px] tracking-widest mb-4 font-sans text-center w-full')
                terreno_juego = ui.element('div').classes('relative w-full h-[480px] bg-sky-600/90 border-2 border-white rounded-xl shadow-lg overflow-hidden')

 
                ui.label("SISTEMA TÁCTICO:").classes('text-[10px] font-bold tracking-widest text-slate-400 font-sans')
                ui.select(
                    options=['1-2-2', '1-3-1', '1-1-3', '1-4-0', '0-0-5'],
                    value=tactica_actual,
                    on_change=lambda e: cambiar_tactica(e)
                ).props('outlined dense options-dense invisible-borders').classes('w-32 font-sans font-medium text-xs text-slate-700')



    def ejecutar_cambio_estado(j_id, nuevo_estado):
        if j_id is None: return
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        if nuevo_estado == 1:
            cursor.execute("SELECT titular FROM jugadores WHERE equipo_id = ? AND titular > 0", (equipo_id,))
            slots_ocupados = {r[0] for r in cursor.fetchall()}
            if len(slots_ocupados) >= 5:
                ui.notify("⚠️ ¡Estrategia ilegal! Saca a un muñón al banco antes de meter a otro.", type='warning')
                conn.close()
                return
            slot_libre = next(s for s in range(1, 6) if s not in slots_ocupados)
            cursor.execute("UPDATE jugadores SET titular = ? WHERE id = ?", (slot_libre, j_id))
        else:
            cursor.execute("UPDATE jugadores SET titular = 0 WHERE id = ?", (j_id,))
        conn.commit()
        conn.close()
        actualizar_pantalla()

    def cambiar_tactica(e):
        global tactica_actual
        tactica_actual = e.value
        ui.notify(f"📋 Sistema de juego modificado a: {tactica_actual}", type='info')
        actualizar_pantalla()

    def actualizar_pantalla():
        # --- Entrenador ---
        conn_e = obtener_conexion_db()
        cur_e = conn_e.cursor()
        try:
            cur_e.execute("""
                SELECT ent.nombre, ent.mote, ent.bono_ataque, ent.bono_defensa
                FROM equipos eq LEFT JOIN entrenadores ent ON ent.id = eq.entrenador_id
                WHERE eq.id = ?
            """, (equipo_id,))
            ent_row = cur_e.fetchone()
        except Exception:
            ent_row = None
        conn_e.close()

        datos = obtener_datos_tacticos(equipo_id)

        # Migrar datos legacy: si hay varios jugadores con titular=1 (valor booleano antiguo),
        # reasignarles slots únicos 1..N antes de continuar
        legacy = [d for d in datos if d['titular'] == 1]
        if len(legacy) > 1:
            conn_mig = obtener_conexion_db()
            cur_mig = conn_mig.cursor()
            for i, j in enumerate(legacy, start=1):
                cur_mig.execute("UPDATE jugadores SET titular = ? WHERE id = ?", (i, j['id']))
            conn_mig.commit()
            conn_mig.close()
            datos = obtener_datos_tacticos(equipo_id)

        titulares_actuales = [d for d in datos if d['titular'] > 0]
        suplentes_actuales  = [d for d in datos if d['titular'] == 0]

        # Slot fijo: cada jugador ocupa el slot == su valor titular (1-5)
        estructura_fija_titulares = []
        for puesto in range(1, 6):
            jugador = next((d for d in datos if d['titular'] == puesto), None)
            if jugador:
                jugador['puesto_num'] = puesto
                estructura_fija_titulares.append(jugador)
            else:
                estructura_fija_titulares.append({
                    'id': None, 'nombre': '[ VACANTE - SIN JUGADOR ]', 'defensa': 0, 'ataque': 0,
                    'bacora': 0, 'flotabilidad': 0, 'media': 0, 'titular': 0, 'puesto_num': puesto, 'pos': '-', 'lesion': 0
                })

        columnas = [
            {'name': 'puesto',       'label': 'POS',    'field': 'puesto_num',  'align': 'center', 'style': 'width: 25px;'},
            {'name': 'nombre',       'label': 'JUGADOR','field': 'nombre',      'align': 'left'},
            {'name': 'defensa',      'label': 'DEF',    'field': 'defensa',     'align': 'center', 'style': 'width: 35px;'},
            {'name': 'ataque',       'label': 'ATK',    'field': 'ataque',      'align': 'center', 'style': 'width: 35px;'},
            {'name': 'bacora',       'label': 'BAC',    'field': 'bacora',      'align': 'center', 'style': 'width: 35px;'},
            {'name': 'flotabilidad', 'label': 'FLOT',   'field': 'flotabilidad','align': 'center', 'style': 'width: 45px;'},
            {'name': 'media',        'label': 'MED',    'field': 'media',       'align': 'center', 'style': 'width: 40px;'},
            {'name': 'accion',       'label': 'ESTADO', 'field': 'id',          'align': 'center', 'style': 'width: 90px;'},
        ]

        # Promedios titulares reales
        real_t = [j for j in estructura_fija_titulares if j['id'] is not None]
        n = max(1, len(real_t))
        avg_def  = round(sum(j['defensa']      for j in real_t) / n)
        avg_atk  = round(sum(j['ataque']       for j in real_t) / n)
        avg_bac  = round(sum(j['bacora']       for j in real_t) / n)
        avg_flot = round(sum(j['flotabilidad'] for j in real_t) / n)
        avg_med  = round(sum(j['media']        for j in real_t) / n)

        # --- TABLA 1: TITULARES ---
        box_titulares.clear()
        with box_titulares:
            # Banner entrenador
            if ent_row and ent_row[0]:
                with ui.row().classes('w-full items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg p-2 mb-2'):
                    ui.icon('sports', color='amber').classes('text-lg')
                    with ui.column().classes('gap-0'):
                        ui.label(ent_row[0].upper()).classes('text-xs font-bold text-amber-900')
                        if ent_row[1]:
                            ui.label(f'"{ent_row[1]}"').classes('text-[10px] text-amber-700 italic')
                    with ui.row().classes('gap-2 ml-auto text-[10px] font-semibold'):
                        ui.label(f"ATK +{ent_row[2]}").classes('text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded').tooltip('Fuerza de ataque del entrenador')
                        ui.label(f"DEF +{ent_row[3]}").classes('text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded').tooltip('Fuerza de defensa del entrenador')
            else:
                with ui.row().classes('w-full items-center gap-2 bg-slate-100 border border-slate-200 rounded-lg p-2 mb-2'):
                    ui.icon('sports', color='grey').classes('text-base')
                    ui.label("Aquí se juega al libre albedrío, no tienes entrenador que te ladre").classes('text-[10px] italic text-slate-400')

            ui.label("🏊 CONVOCATORIA TITULAR (5 PUESTOS REGLAMENTARIOS)").classes('text-emerald-800 font-bold text-xs font-sans uppercase tracking-wider mb-1')
            with ui.table(columns=columnas, rows=estructura_fija_titulares, row_key='puesto_num').classes('w-full bg-emerald-50/60 border border-emerald-200 flat font-sans text-emerald-950 shadow-sm dense') as t1:
                t1.style('font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.82rem; --q-table-horizontal-padding: 5px;')
                t1.props('hide-bottom')
                t1.add_slot('body-cell-nombre', '''
                    <q-td :props="props" class="q-pa-xs">
                        <span class="flex items-center gap-1.5">
                            <span>{{ props.row.nombre }}</span>
                            <q-badge v-if="props.row.lesion > 0" color="red" text-color="white" class="text-[9px] font-bold px-1 py-0.5">
                                🏥 {{ props.row.lesion }}j
                            </q-badge>
                        </span>
                    </q-td>
                ''')
                t1.add_slot('body-cell-media', '''
                    <q-td :props="props" class="q-pa-xs">
                        <q-badge v-if="props.row.id" color="green-8" class="text-bold px-1.5 py-0.5 rounded">{{ props.value }}</q-badge>
                        <span v-else>-</span>
                    </q-td>
                ''')
                t1.add_slot('body-cell-accion', '''
                    <q-td :props="props" class="q-pa-xs">
                        <q-btn v-if="props.row.id" unelevated rounded size="xs" color="deep-orange-7" label="SACAR" @click="$parent.$emit('sacar_muñon', props.row)" class="px-2" />
                        <q-btn v-else unelevated rounded size="xs" color="grey-7" label="ELEGIR" @click="$parent.$emit('elegir_suplente', props.row.puesto_num)" class="px-2" />
                    </q-td>
                ''')
                t1.add_slot('bottom-row', f'''
                    <q-tr class="bg-gray-200">
                        <q-td class="text-center text-[10px] font-bold text-emerald-900">~</q-td>
                        <q-td class="text-[12px] font-bold text-emerald-900">MEDIA DEL EQUIPO</q-td>
                        <q-td class="text-center text-[12px] font-bold text-emerald-900">{avg_def}</q-td>
                        <q-td class="text-center text-[12px] font-bold text-emerald-900">{avg_atk}</q-td>
                        <q-td class="text-center text-[12px] font-bold text-emerald-900">{avg_bac}</q-td>
                        <q-td class="text-center text-[12px] font-bold text-emerald-900">{avg_flot}</q-td>
                        <q-td class="text-center text-[12px] font-bold text-emerald-900"><q-badge color="green-8" class="text-bold px-1.5 py-0.5 rounded">{avg_med}</q-badge></q-td>
                        <q-td></q-td>
                    </q-tr>
                ''')
                t1.on('sacar_muñon', lambda msg: ejecutar_cambio_estado(msg.args['id'], 0))
                def elegir_suplente(msg):
                    suplentes_now = [d for d in obtener_datos_tacticos(equipo_id) if d['titular'] == 0]
                    if not suplentes_now:
                        ui.notify("No hay suplentes disponibles.", type='warning')
                        return
                    with ui.dialog() as dlg_el, ui.card().classes('w-[300px] p-4 font-sans gap-3'):
                        ui.label("ELEGIR JUGADOR PARA EL AGUA").classes('text-xs font-bold text-slate-400 tracking-wider')
                        sel_sup = ui.select(
                            options={s['id']: s['nombre'].upper() for s in suplentes_now},
                            label='Suplente'
                        ).props('outlined dense').classes('w-full')
                        def confirmar_eleccion(d=dlg_el, s=sel_sup):
                            if s.value:
                                ejecutar_cambio_estado(s.value, 1)
                            d.close()
                        ui.button('AL AGUA', on_click=confirmar_eleccion).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-xs w-full')
                    dlg_el.open()
                t1.on('elegir_suplente', elegir_suplente)

        # --- TABLA 2: RESERVAS ---
        box_suplentes.clear()
        with box_suplentes:
            ui.label("🪑 SECCIÓN CHUPANDO BANQUILLO (RESERVAS)").classes('text-slate-500 font-bold text-xs font-sans uppercase tracking-wider mt-4 mb-1')
            with ui.table(columns=columnas[1:], rows=suplentes_actuales, row_key='id').classes('w-full bg-white border border-slate-200 flat font-sans text-slate-600 shadow-sm dense') as t2:
                t2.style('font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.82rem; --q-table-horizontal-padding: 5px;')
                t2.props('hide-bottom')
                t2.add_slot('body-cell-nombre', '''
                    <q-td :props="props" class="q-pa-xs">
                        <span class="flex items-center gap-1.5">
                            <span>{{ props.row.nombre }}</span>
                            <q-badge v-if="props.row.lesion > 0" color="red" text-color="white" class="text-[9px] font-bold px-1 py-0.5">
                                🏥 {{ props.row.lesion }}j
                            </q-badge>
                        </span>
                    </q-td>
                ''')
                t2.add_slot('body-cell-media', '''
                    <q-td :props="props" class="q-pa-xs">
                        <q-badge color="indigo-7" class="text-bold px-1.5 py-0.5 rounded">{{ props.value }}</q-badge>
                    </q-td>
                ''')
                t2.add_slot('body-cell-accion', '''
                    <q-td :props="props" class="q-pa-xs">
                        <q-btn unelevated rounded size="xs" color="blue-grey-8" label="AL AGUA" @click="$parent.$emit('meter_muñon', props.row)" class="px-2" />
                    </q-td>
                ''')
                t2.on('meter_muñon', lambda msg: ejecutar_cambio_estado(msg.args['id'], 1))

        # --- TABLA 3: AMBULATORIO ---
        box_ambulatorio.clear()
        with box_ambulatorio:
            ui.label("🏥 AMBULATORIO DE SAN FERMÍN").classes('text-red-700 font-bold text-xs font-sans uppercase tracking-wider mt-4 mb-1')
            conn_amb = obtener_conexion_db()
            cur_amb = conn_amb.cursor()
            cur_amb.execute("""
                SELECT j.nombre, COALESCE(l.nombre, 'Lesión desconocida'), j.semanas_lesion
                FROM jugadores j
                LEFT JOIN lesiones l ON j.lesion_id = l.id
                WHERE j.equipo_id = ? AND j.semanas_lesion > 0
                ORDER BY j.semanas_lesion DESC
            """, (equipo_id,))
            bajas = cur_amb.fetchall()
            conn_amb.close()
            if not bajas:
                ui.label('Che quina ensalà, no hay nadie enfermo').classes('text-slate-400 italic text-xs py-2 px-3 bg-white border border-slate-100 rounded-lg w-full')
            else:
                cols_amb = [
                    {'name': 'nombre',  'label': 'JUGADOR',  'field': 'nombre',   'align': 'left'},
                    {'name': 'lesion',  'label': 'DIAGNÓSTICO', 'field': 'lesion', 'align': 'left'},
                    {'name': 'semanas', 'label': 'BAJA', 'field': 'semanas',      'align': 'center', 'style': 'width: 60px;'},
                ]
                rows_amb = [{'nombre': r[0], 'lesion': r[1], 'semanas': f"{r[2]}j"} for r in bajas]
                with ui.table(columns=cols_amb, rows=rows_amb, row_key='nombre').classes('w-full bg-red-50/60 border border-red-200 flat font-sans text-red-950 shadow-sm dense'):
                    pass

        # --- PISCINA ---
        terreno_juego.clear()
        with terreno_juego:
            ui.element('div').classes('absolute top-1/2 w-full h-[1px] bg-white/30')
            ui.element('div').classes('absolute top-0 left-1/2 -translate-x-1/2 w-40 h-12 border border-t-0 border-white/40 bg-white/5')
            ui.element('div').classes('absolute bottom-0 left-1/2 -translate-x-1/2 w-40 h-12 border border-b-0 border-white/40 bg-white/5')
            ui.label(tactica_actual).classes('absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-5xl font-extrabold font-sans text-white/10 tracking-widest pointer-events-none')
            coordenadas_sistema = ESTRATEGIAS.get(tactica_actual, ESTRATEGIAS['1-2-2'])
            for idx, jugador in enumerate(titulares_actuales[:5], start=1):
                estilo_pos = coordenadas_sistema.get(idx, '')
                with ui.column().style(f'position: absolute; {estilo_pos}').classes('items-center gap-1'):
                    ui.label(str(idx)).classes('w-7 h-7 bg-slate-900 text-white border border-white/80 rounded-full flex items-center justify-center font-bold font-sans shadow-lg text-xs')
                    ui.label(jugador['nombre'].upper()).classes('text-[9px] font-sans font-semibold text-slate-900 bg-white/95 px-1.5 py-0.5 rounded shadow-sm whitespace-nowrap')

    actualizar_pantalla()


def obtener_datos_tacticos(equipo_id):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, defensa, ataque, bacora, flotabilidad, titular, posicion, semanas_lesion
        FROM jugadores WHERE equipo_id = ?
    """, (equipo_id,))
    filas = cursor.fetchall()
    conn.close()

    datos = []
    for f in filas:
        def_ = f[2] or 0
        atk  = f[3] or 0
        bac  = f[4] or 0
        flot = f[5] or 0
        datos.append({
            'id': f[0],
            'nombre': f[1] or '???',
            'defensa': def_,
            'ataque': atk,
            'bacora': bac,
            'flotabilidad': flot,
            'titular': f[6] or 0,
            'media': int((def_ + atk) / 2),
            'pos': f[7] or 'JUG',
            'lesion': f[8] or 0
        })
    return datos