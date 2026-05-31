from nicegui import ui
import sqlite3
import main
import copa

# 🌟 CORRECCIÓN CRUCIAL: Eliminamos la constante fija para usar la ruta dinámica de partida
def obtener_conexion_db():
    return sqlite3.connect(main.obtener_ruta_db())

def obtener_clasificacion_completa(mi_equipo_id=None):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, puntos, goles_favor, goles_contra 
        FROM equipos 
        WHERE division = 'Liga SuperEmpanadill'
        ORDER BY puntos DESC, (goles_favor - goles_contra) DESC
    """)
    filas = cursor.fetchall()

    datos = []
    for pos, f in enumerate(filas, start=1):
        eq_id = f[0]
        cursor.execute("""
            SELECT
                SUM(CASE
                    WHEN (local_id = ? AND goles_local > goles_visita) OR
                         (visita_id = ? AND goles_visita > goles_local) THEN 1 ELSE 0 END),
                SUM(CASE WHEN goles_local = goles_visita THEN 1 ELSE 0 END),
                SUM(CASE
                    WHEN (local_id = ? AND goles_local < goles_visita) OR
                         (visita_id = ? AND goles_visita < goles_local) THEN 1 ELSE 0 END)
            FROM partidos
            WHERE jugado = 1 AND (local_id = ? OR visita_id = ?)
        """, (eq_id, eq_id, eq_id, eq_id, eq_id, eq_id))
        row = cursor.fetchone()
        pg, pe, pp = (row[0] or 0), (row[1] or 0), (row[2] or 0)

        datos.append({
            'pos': pos,
            'nombre': f[1].upper(),
            'pts': f[2],
            'gf': f[3],
            'gc': f[4],
            'pg': pg,
            'pe': pe,
            'pp': pp,
            'flot': min(100, max(10, 50 + (f[3] - f[4]) * 3)),
            'es_propio': 1 if eq_id == mi_equipo_id else 0
        })

    conn.close()
    return datos

def obtener_pichichis():
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, goles, posicion FROM jugadores ORDER BY goles DESC")
    filas = cursor.fetchall()
    conn.close()
    
    datos_goleadores = []
    for f in filas:
        datos_goleadores.append({
            'nombre': f[0],
            'goles': f[1],
            'posicion': f[2]
        })
    return datos_goleadores

def obtener_partidos_jornada(jornada):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.goles_local, p.goles_visita, el.nombre, ev.nombre, p.jugado 
        FROM partidos p 
        JOIN equipos el ON p.local_id = el.id 
        JOIN equipos ev ON p.visita_id = ev.id 
        WHERE p.jornada = ?
    """, (jornada,))
    partidos = cursor.fetchall()
    conn.close()
    return partidos

# Obtener predicción de la Maga Maja
def obtener_prediccion_maga_maja(jornada):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    
    # 1. Sacamos el nombre de TU equipo
    mi_id = main.obtener_mi_equipo_id()
    cursor.execute("SELECT nombre FROM equipos WHERE id = ?", (mi_id,))
    res = cursor.fetchone()
    nombre_equipo = res[0].upper() if res else "TU EQUIPO"
    conn.close()

    # 2. Las visiones de la Maga Maja
    visiones = [
        f"Los posos del cantueso me dicen que el {nombre_equipo} sufrirá una pájara monumental en el agua. ¡Avisados quedáis!",
        f"La Dama de Elche me ha hablado en sueños... dice que el {nombre_equipo} hoy flotará como un corcho en las Salinas.",
        f"Veo una sombra muy oscura sobre el vestuario del {nombre_equipo}... Alguien se ha dejado una empanadilla fuera de la nevera.",
        f"Cuidado, míster del {nombre_equipo}. Las palmeras se agitan y el árbitro hoy viene con ganas de sacar tarjeta por respirar.",
        f"La alineación de los astros sobre el Aljub augura un penalti injusto a favor del {nombre_equipo}. ¡No lo falléis!",
        f"Siento turbulencias acuáticas... Hoy el {nombre_equipo} marcará un gol de rebote con el gorro de waterpolo."
    ]
    
    # Elegimos la visión según la jornada para que cambie cada semana
    return visiones[jornada % len(visiones)]

# 🌟 NUEVA FUNCIÓN: Recuperar los partes médicos reales con tu nuevo lesion_id
def obtener_enfermeria_activa():
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.nombre, l.nombre, j.semanas_lesion, e.nombre
        FROM jugadores j
        JOIN lesiones l ON j.lesion_id = l.id
        JOIN equipos e ON j.equipo_id = e.id
        WHERE j.semanas_lesion > 0
        ORDER BY j.semanas_lesion DESC
    """)
    lesionados = cursor.fetchall()
    conn.close()
    return lesionados


def abrir_centro_informacion(jornada_actual):
    with ui.dialog() as dialogo, ui.card().classes('w-[950px] max-w-5xl bg-slate-50 p-6 rounded-2xl shadow-xl font-sans text-slate-900'):
        
        # Cabecera del Centro de Datos
        with ui.row().classes('w-full border-b border-slate-200 pb-4 justify-between items-center'):
            with ui.column().classes('gap-0'):
                ui.label("Centro de Datos — Diario Información").classes('text-xl font-bold tracking-tight text-slate-900')
                ui.label("Analítica deportiva y scouting en tiempo real").classes('text-xs text-slate-400')
            ui.button(icon='close', on_click=dialogo.close).props('flat round dense').classes('text-slate-400')

        # BARRA DE NAVEGACIÓN POR ICONOS (¡Añadida la cuarta pestaña médica!)
        with ui.row().classes('w-full justify-center gap-2 my-4 border-b border-slate-100 pb-4'):
            btn_clasif = ui.button('Clasificación', icon='leaderboard').props('unelevated rounded').classes('bg-slate-900 text-white text-xs px-4')
            btn_gold = ui.button('Muñón de Oro', icon='emoji_events').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs px-4')
            btn_res = ui.button('Resultados', icon='calendar_month').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs px-4')
            # 🚑 Botón de la nueva sección médica
            btn_med = ui.button('Parte Médico', icon='medical_services').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs px-4')
            btn_maga = ui.button('Maga Maja', icon='visibility').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs px-4')
            btn_copa = ui.button('Copa Intermuñonal', icon='emoji_events').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs px-4')

        # Contenedores de las secciones
        panel_clasificacion = ui.column().classes('w-full')
        panel_munon_oro = ui.column().classes('w-full hidden')
        panel_resultados = ui.column().classes('w-full hidden')
        panel_medico = ui.column().classes('w-full hidden') # 🚑 Panel oculto por defecto
        panel_prediccion = ui.column().classes('w-full hidden') # 🌟 Panel de predicción de la Maga Maja
        panel_copa = ui.column().classes('w-full hidden')

        # --- SECCIÓN 1: CLASIFICACIÓN MODERNA ---
        mi_id = main.obtener_mi_equipo_id()
        with panel_clasificacion:
            ui.label("TABLA DE CLASIFICACIÓN LIGA").classes('text-[10px] font-bold tracking-widest text-slate-400 mb-2')
            columnas_clubes = [
                {'name': 'pos', 'label': 'POS', 'field': 'pos', 'align': 'center'},
                {'name': 'nombre', 'label': 'CLUB', 'field': 'nombre', 'align': 'left'},
                {'name': 'pts', 'label': 'PTS', 'field': 'pts', 'align': 'center'},
                {'name': 'pg', 'label': 'PG', 'field': 'pg', 'align': 'center'},
                {'name': 'pe', 'label': 'PE', 'field': 'pe', 'align': 'center'},
                {'name': 'pp', 'label': 'PP', 'field': 'pp', 'align': 'center'},
                {'name': 'gf', 'label': 'GF', 'field': 'gf', 'align': 'center'},
                {'name': 'gc', 'label': 'GC', 'field': 'gc', 'align': 'center'},
                {'name': 'flot', 'label': 'ÍNDICE FLOTABILIDAD', 'field': 'flot', 'align': 'center'},
            ]
            tabla_clas = ui.table(columns=columnas_clubes, rows=obtener_clasificacion_completa(mi_id), row_key='pos') \
                .classes('w-full bg-white border border-slate-200 flat font-sans text-xs dense shadow-sm') \
                .style('--q-table-horizontal-padding: 8px;')
            tabla_clas.add_slot('body', '''
                <q-tr :props="props"
                    :class="props.row.es_propio ? 'bg-amber-100 font-bold' :
                            props.row.pos <= 3 ? 'bg-emerald-50' :
                            props.row.pos >= 11 && props.row.pos <= 12 ? 'bg-red-50' : ''"
                >
                    <q-td v-for="col in props.cols" :key="col.name" :props="props">
                        <span :class="props.row.es_propio && col.name === 'nombre' ? 'text-amber-700 font-extrabold' :
                                      props.row.pos <= 3 && col.name === 'nombre' ? 'text-emerald-700 font-bold' :
                                      props.row.pos >= 11 && props.row.pos <= 12 && col.name === 'nombre' ? 'text-red-600 font-bold' :
                                      col.name === 'pts' ? 'font-extrabold text-slate-900' : ''">{{ col.value }}</span>
                        <q-icon v-if="props.row.es_propio && col.name === 'nombre'" name="star" color="amber" size="xs" class="ml-1" />
                        <q-icon v-if="props.row.pos <= 3 && !props.row.es_propio && col.name === 'pos'" name="emoji_events" color="green" size="xs" />
                        <q-icon v-if="props.row.pos >= 11 && props.row.pos <= 12 && col.name === 'pos'" name="arrow_downward" color="red" size="xs" />
                    </q-td>
                </q-tr>
            ''')

        # --- SECCIÓN 2: MUÑÓN DE ORO ---
        with panel_munon_oro:
            ui.label("GALARDÓN INTERNACIONAL MUÑÓN DE ORO").classes('text-[10px] font-bold tracking-widest text-slate-400 mb-2')
            goleadores = obtener_pichichis()
            
            segundo_goleador_txt = "Nadie todavía"
            goles_segundo = 0
            
            if len(goleadores) >= 2:
                goles_unicos = sorted(list(set([g['goles'] for g in goleadores])), reverse=True)
                if len(goles_unicos) >= 2:
                    teoricos_segundos = [g for g in goleadores if g['goles'] == goles_unicos[1]]
                    if teoricos_segundos:
                        segundo_goleador_txt = f"{teoricos_segundos[0]['nombre']} ({teoricos_segundos[0]['posicion']})"
                        goles_segundo = teoricos_segundos[0]['goles']
                else:
                    segundo_goleador_txt = f"{goleadores[1]['nombre']} ({goleadores[1]['posicion']})"
                    goles_segundo = goleadores[1]['goles']

            with ui.row().classes('w-full bg-amber-50 border border-amber-200 p-4 rounded-xl items-center gap-4 mb-4'):
                ui.icon('emoji_events').classes('text-4xl text-amber-500')
                with ui.column().classes('gap-0'):
                    ui.label("LÍDER VIRTUAL DEL MUÑÓN DE ORO (2º PUESTO)").classes('text-[9px] font-bold text-amber-800 tracking-wider')
                    ui.label(segundo_goleador_txt.upper()).classes('text-lg font-bold text-slate-900')
                    ui.label(f"Registra un total de {goles_segundo} bacoras anotadas").classes('text-xs text-slate-500')

            columnas_pichichi = [
                {'name': 'nombre', 'label': 'MUÑÓN', 'field': 'nombre', 'align': 'left'},
                {'name': 'pos', 'label': 'POSICIÓN', 'field': 'posicion', 'align': 'center'},
                {'name': 'goles', 'label': 'BACORAS TOTALES', 'field': 'goles', 'align': 'center'},
            ]
            ui.table(columns=columnas_pichichi, rows=goleadores[:8], row_key='nombre') \
                .classes('w-full bg-white border border-slate-200 flat font-sans text-xs dense')

        # --- SECCIÓN 3: RESULTADOS E HISTÓRICO ---
        with panel_resultados:
            estado_jornada = {'num': jornada_actual}
            
            with ui.row().classes('w-full justify-between items-center bg-white border border-slate-200 p-2 rounded-xl mb-3 shadow-sm'):
                def cambiar_jornada_visor(delta):
                    nuevo = estado_jornada['num'] + delta
                    if 1 <= nuevo <= 22:
                        estado_jornada['num'] = nuevo
                        lbl_jornada.set_text(f"JORNADA OBLIGATORIA {estado_jornada['num']}")
                        renderizar_lista_partidos(estado_jornada['num'])

                ui.button(icon='arrow_back', on_click=lambda: cambiar_jornada_visor(-1)).props('flat dense')
                lbl_jornada = ui.label(f"JORNADA OBLIGATORIA {estado_jornada['num']}").classes('font-bold text-xs text-slate-700 tracking-wide')
                ui.button(icon='arrow_forward', on_click=lambda: cambiar_jornada_visor(1)).props('flat dense')

            box_partidos_historico = ui.column().classes('w-full gap-2')

            def renderizar_lista_partidos(j_ver):
                box_partidos_historico.clear()
                partidos = obtener_partidos_jornada(j_ver)
                with box_partidos_historico:
                    for g_l, g_v, n_l, n_v, jugado in partidos:
                        marcador = f"{g_l} – {g_v}" if jugado else "VS"
                        bg_partido = "bg-slate-100/50" if jugado else "bg-blue-50/40 border border-blue-100"
                        with ui.row().classes(f'w-full justify-between items-center p-2.5 rounded-xl text-xs font-sans {bg_partido}'):
                            ui.label(n_l.upper()).classes('w-[40%] text-right font-semibold text-slate-700')
                            ui.label(marcador).classes('bg-slate-900 text-white font-bold px-3 py-0.5 rounded-lg text-center tracking-widest text-[11px]')
                            ui.label(n_v.upper()).classes('w-[40%] text-left font-semibold text-slate-700')

            renderizar_lista_partidos(jornada_actual)

        # --- 🚑 SECCIÓN 4: PARTE MÉDICO (NUEVA SECCIÓN MAQUETADA) ---
        with panel_medico:
            ui.label("PARTE MÉDICO OFICIAL — HOSPITAL ILICITANO").classes('text-[10px] font-bold tracking-widest text-slate-400 mb-2')
            
            lesionados = obtener_enfermeria_activa()
            
            if not lesionados:
                with ui.row().classes('w-full bg-emerald-50 border border-emerald-200 p-4 rounded-xl items-center gap-3'):
                    ui.icon('check_circle', color='emerald').classes('text-2xl')
                    with ui.column().classes('gap-0'):
                        ui.label("ENFERMERÍA VACÍA").classes('text-xs font-bold text-emerald-800')
                        ui.label("Todos los muñonistas se encuentran listos y en óptimas condiciones de flotabilidad.").classes('text-xs text-slate-500')
            else:
                with ui.column().classes('w-full gap-2'):
                    for nom_jugador, nom_lesion, semanas, nom_equipo in lesionados:
                        with ui.row().classes('w-full bg-rose-50/60 border border-rose-100 p-3 rounded-xl justify-between items-center font-sans text-xs shadow-sm'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('medical_services', color='rose').classes('text-lg')
                                with ui.column().classes('gap-0'):
                                    ui.label(nom_jugador.upper()).classes('font-bold text-slate-800 text-sm')
                                    ui.label(nom_equipo.upper()).classes('text-[10px] text-slate-400 font-medium')
                            
                            # Diagnóstico del catálogo maestro
                            ui.label(nom_lesion).classes('bg-rose-100 text-rose-800 font-semibold px-2 py-0.5 rounded-md text-[11px]')
                            
                            # Semanas restantes
                            txt_semanas = "ÚLTIMA SEMANA" if semanas == 1 else f"{semanas} JORNADAS DE BAJA"
                            ui.label(txt_semanas).classes('text-slate-600 font-mono font-bold')

        # ---  SECCIÓN 6: COPA INTERMUÑONAL ---
        with panel_copa:
            copa.render_copa_intermuñonal()

        # --- 🌟 SECCIÓN 5: PREDICCIÓN DE LA MAGA MAJA ---
        with panel_prediccion:
            ui.label("PREDECIR PRÓXIMA JORNADA").classes('text-[10px] font-bold tracking-widest text-slate-400 mb-2')
            # Aquí irá la predicción de la Maga Maja
# 🔮 SECCIÓN: LA MAGA MAJA
            with ui.column().classes('w-full bg-fuchsia-50/60 border border-fuchsia-200 p-4 rounded-xl gap-2 font-sans text-xs shadow-sm'):
                with ui.row().classes('items-center gap-2 text-fuchsia-800 font-bold'):
                    ui.icon('visibility').classes('text-lg')
                    ui.label("👁️ LA PREDICCIÓN DE LA MAGA MAJA").classes('tracking-wide text-[10px]')
                
                ui.separator().classes('border-fuchsia-100 my-1')
                
                texto_maga = obtener_prediccion_maga_maja(jornada_actual)
                
                with ui.row().classes('w-full gap-3 items-center mt-1'):
                    ui.icon('auto_awesome', color='fuchsia-700').classes('text-2xl mt-0.5')
                    ui.label(f'"{texto_maga}"').classes('text-slate-700 italic font-semibold text-xs leading-relaxed flex-1')                
        # --- 🌟 SISTEMA ACTUALIZADO DE CONMUTACIÓN DE PESTAÑAS 🌟 ---
        def activar_seccion(pestana):
            for btn in [btn_clasif, btn_gold, btn_res, btn_med, btn_maga, btn_copa]:
                btn.classes(replace='bg-slate-200 text-slate-700 text-xs px-4')
            for panel in [panel_clasificacion, panel_munon_oro, panel_resultados,
                          panel_medico, panel_prediccion, panel_copa]:
                panel.classes(add='hidden')

            if pestana == 'clasif':
                btn_clasif.classes(replace='bg-slate-900 text-white text-xs px-4')
                panel_clasificacion.classes(remove='hidden')
            elif pestana == 'gold':
                btn_gold.classes(replace='bg-slate-900 text-white text-xs px-4')
                panel_munon_oro.classes(remove='hidden')
            elif pestana == 'res':
                btn_res.classes(replace='bg-slate-900 text-white text-xs px-4')
                panel_resultados.classes(remove='hidden')
            elif pestana == 'med':
                btn_med.classes(replace='bg-slate-900 text-white text-xs px-4')
                panel_medico.classes(remove='hidden')
            elif pestana == 'maga':
                btn_maga.classes(replace='bg-slate-900 text-white text-xs px-4')
                panel_prediccion.classes(remove='hidden')
            elif pestana == 'copa':
                btn_copa.classes(replace='bg-amber-500 text-white text-xs px-4')
                panel_copa.classes(remove='hidden')

        btn_clasif.on('click', lambda: activar_seccion('clasif'))
        btn_gold.on('click', lambda: activar_seccion('gold'))
        btn_res.on('click', lambda: activar_seccion('res'))
        btn_med.on('click', lambda: activar_seccion('med'))
        btn_maga.on('click', lambda: activar_seccion('maga'))
        btn_copa.on('click', lambda: activar_seccion('copa'))

        dialogo.open()