import sqlite3
import random
import main
from nicegui import ui

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def obtener_conexion_db():
    return sqlite3.connect(main.obtener_ruta_db())


def _crear_tablas(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS copa_participantes (
            temporada   INTEGER NOT NULL,
            equipo_id   INTEGER NOT NULL,
            origen      TEXT    NOT NULL,
            PRIMARY KEY (temporada, equipo_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS copa_partidos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            temporada       INTEGER NOT NULL,
            ronda           INTEGER NOT NULL,
            enfrentamiento  INTEGER NOT NULL,
            leg             INTEGER NOT NULL,
            local_id        INTEGER NOT NULL,
            visita_id       INTEGER NOT NULL,
            goles_local     INTEGER DEFAULT NULL,
            goles_visita    INTEGER DEFAULT NULL,
            jugado          INTEGER DEFAULT 0
        )
    ''')


def _simular_goles():
    """Distribución ~5.7 goles/equipo de media, con 0 posible."""
    _DIST  = [0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]
    _PESOS = [2,  3,  6,  9, 12, 14, 16, 14, 10,  7,  4,  2,  1]
    return random.choices(_DIST, weights=_PESOS, k=1)[0]


def _ganador_eliminatoria(gl_ida, gv_ida, gl_vta, gv_vta, eq_a, eq_b):
    """
    eq_a = local de ida / visita de vuelta
    eq_b = visita de ida / local de vuelta
    Gana quien más goles tiene en total; empate → sorteo.
    """
    total_a = gl_ida + gv_vta
    total_b = gv_ida + gl_vta
    if total_a > total_b:
        return eq_a
    elif total_b > total_a:
        return eq_b
    else:
        return random.choice([eq_a, eq_b])


# ---------------------------------------------------------------------------
# Inicialización del torneo (al final de la temporada)
# ---------------------------------------------------------------------------

def inicializar_copa(temporada):
    """
    Selecciona los 8 participantes, sortea cuartos e inserta los 8 partidos
    (4 enfrentamientos × 2 legs).  Si ya existe la copa de esta temporada no hace nada.
    """
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    _crear_tablas(cursor)
    conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM copa_participantes WHERE temporada = ?", (temporada,)
    )
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False

    # Siempre los 3 primeros de Liga SuperEmpanadill según clasificación final
    cursor.execute("""
        SELECT id FROM equipos
        WHERE division = 'Liga SuperEmpanadill'
        ORDER BY puntos DESC, (goles_favor - goles_contra) DESC
        LIMIT 3
    """)
    super_top3 = [r[0] for r in cursor.fetchall()]

    # Equipos de Liga Intermuñonal (si los hay)
    cursor.execute("""
        SELECT id FROM equipos
        WHERE division = 'Liga Intermuñonal'
        ORDER BY puntos DESC, (goles_favor - goles_contra) DESC
    """)
    inter_ids = [r[0] for r in cursor.fetchall()]

    # Base: top 3 SuperEmpanadill + Intermuñonal, sin duplicados, máx 8
    equipos = super_top3 + [i for i in inter_ids if i not in super_top3]
    equipos = equipos[:8]

    # Si el total es impar, añadir el 4º de SuperEmpanadill para cuadrar el bracket
    if len(equipos) % 2 != 0:
        cursor.execute("""
            SELECT id FROM equipos
            WHERE division = 'Liga SuperEmpanadill'
            ORDER BY puntos DESC, (goles_favor - goles_contra) DESC
            LIMIT 4
        """)
        cuarto = [r[0] for r in cursor.fetchall() if r[0] not in equipos]
        if cuarto:
            equipos.append(cuarto[0])

    if len(equipos) < 4:
        conn.close()
        print(f"[COPA] Equipos insuficientes para el torneo: {len(equipos)}")
        return False

    # Si son impares, quitar el último para tener número par
    if len(equipos) % 2 != 0:
        equipos = equipos[:-1]

    for eq_id in equipos:
        origen = 'intermuñonal' if eq_id in inter_ids else 'superempanadill'
        cursor.execute(
            "INSERT OR IGNORE INTO copa_participantes VALUES (?, ?, ?)",
            (temporada, eq_id, origen)
        )

    # Sorteo primera ronda (cuartos si hay 8, semis si hay 4)
    ronda_inicio = 1 if len(equipos) == 8 else 2
    random.shuffle(equipos)
    n_enfrentamientos = len(equipos) // 2
    for i in range(n_enfrentamientos):
        a, b = equipos[i * 2], equipos[i * 2 + 1]
        cursor.execute(
            "INSERT INTO copa_partidos (temporada,ronda,enfrentamiento,leg,local_id,visita_id) VALUES (?,?,?,1,?,?)",
            (temporada, ronda_inicio, i + 1, a, b)
        )
        cursor.execute(
            "INSERT INTO copa_partidos (temporada,ronda,enfrentamiento,leg,local_id,visita_id) VALUES (?,?,?,2,?,?)",
            (temporada, ronda_inicio, i + 1, b, a)
        )

    conn.commit()
    conn.close()
    print(f"[COPA] Temporada {temporada}: cuadro generado con {len(equipos)} equipos.")
    return True


# ---------------------------------------------------------------------------
# Simulación por rondas
# ---------------------------------------------------------------------------

def _simular_ronda(temporada, ronda):
    """Simula todos los partidos de una ronda y devuelve lista de (enfrentamiento, ganador_id)."""
    conn = obtener_conexion_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT enfrentamiento FROM copa_partidos WHERE temporada=? AND ronda=? ORDER BY enfrentamiento",
        (temporada, ronda)
    )
    enfrentamientos = [r[0] for r in cursor.fetchall()]
    ganadores = []

    for enf in enfrentamientos:
        cursor.execute(
            "SELECT id, local_id, visita_id FROM copa_partidos WHERE temporada=? AND ronda=? AND enfrentamiento=? AND leg=1",
            (temporada, ronda, enf)
        )
        ida = cursor.fetchone()
        cursor.execute(
            "SELECT id, local_id, visita_id FROM copa_partidos WHERE temporada=? AND ronda=? AND enfrentamiento=? AND leg=2",
            (temporada, ronda, enf)
        )
        vta = cursor.fetchone()
        if not ida or not vta:
            continue

        ida_id, eq_a, eq_b = ida
        vta_id, _,    _    = vta

        gl_ida = _simular_goles()
        gv_ida = _simular_goles()
        gl_vta = _simular_goles()
        gv_vta = _simular_goles()

        cursor.execute(
            "UPDATE copa_partidos SET goles_local=?,goles_visita=?,jugado=1 WHERE id=?",
            (gl_ida, gv_ida, ida_id)
        )
        cursor.execute(
            "UPDATE copa_partidos SET goles_local=?,goles_visita=?,jugado=1 WHERE id=?",
            (gl_vta, gv_vta, vta_id)
        )
        ganador = _ganador_eliminatoria(gl_ida, gv_ida, gl_vta, gv_vta, eq_a, eq_b)
        ganadores.append((enf, ganador))

    conn.commit()
    conn.close()
    return ganadores


def _insertar_ronda(temporada, ronda, parejas):
    """Inserta los partidos ida/vuelta de una ronda nueva."""
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    for i, (a, b) in enumerate(parejas, start=1):
        cursor.execute(
            "INSERT INTO copa_partidos (temporada,ronda,enfrentamiento,leg,local_id,visita_id) VALUES (?,?,?,1,?,?)",
            (temporada, ronda, i, a, b)
        )
        cursor.execute(
            "INSERT INTO copa_partidos (temporada,ronda,enfrentamiento,leg,local_id,visita_id) VALUES (?,?,?,2,?,?)",
            (temporada, ronda, i, b, a)
        )
    conn.commit()
    conn.close()


def simular_copa_completa(temporada):
    """Simula cuartos (si los hay) → semis → final y devuelve el campeón (equipo_id)."""
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MIN(ronda) FROM copa_partidos WHERE temporada = ?", (temporada,)
    )
    row = cursor.fetchone()
    conn.close()
    ronda_inicio = row[0] if row and row[0] else 1

    ganadores = []

    if ronda_inicio == 1:
        # Cuartos
        g_cuartos = _simular_ronda(temporada, 1)
        if len(g_cuartos) < 4:
            return None
        ganadores = g_cuartos

        # Semis
        semis_eq = [g[1] for g in ganadores]
        random.shuffle(semis_eq)
        _insertar_ronda(temporada, 2, [(semis_eq[0], semis_eq[1]), (semis_eq[2], semis_eq[3])])

    # Simular semis (ronda 2)
    g_semis = _simular_ronda(temporada, 2)
    if len(g_semis) < 2:
        return None

    # Final
    finalistas = [g[1] for g in g_semis]
    _insertar_ronda(temporada, 3, [(finalistas[0], finalistas[1])])
    g_final = _simular_ronda(temporada, 3)
    campeon_id = g_final[0][1] if g_final else None

    # Guardar campeón en configuracion
    if campeon_id:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (f'copa_campeon_{temporada}', campeon_id)
        )
        conn.commit()
        conn.close()
        conn2 = obtener_conexion_db()
        c2 = conn2.cursor()
        c2.execute("SELECT nombre FROM equipos WHERE id = ?", (campeon_id,))
        nom = c2.fetchone()
        conn2.close()
        print(f"[COPA] 🏆 Campeón temporada {temporada}: {nom[0] if nom else campeon_id}")

    return campeon_id


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

RONDA_LABELS = {1: 'CUARTOS DE FINAL', 2: 'SEMIFINALES', 3: 'GRAN FINAL'}


def render_copa_intermuñonal():
    """Renderiza el panel de la Copa Intermuñonal con bracket y resultados."""
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    _crear_tablas(cursor)
    conn.commit()

    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada_actual'")
    row = cursor.fetchone()
    temporada = int(row[0]) if row else 1

    cursor.execute(
        "SELECT COUNT(*) FROM copa_participantes WHERE temporada = ?", (temporada,)
    )
    hay_copa = cursor.fetchone()[0] > 0

    if not hay_copa:
        # Buscar temporada anterior
        temporada -= 1
        cursor.execute(
            "SELECT COUNT(*) FROM copa_participantes WHERE temporada = ?", (temporada,)
        )
        hay_copa = cursor.fetchone()[0] > 0

    # --- Clasificación Liga Intermuñonal (siempre visible) ---
    cursor.execute("""
        SELECT nombre, puntos, goles_favor, goles_contra
        FROM equipos
        WHERE division = 'Liga Intermuñonal'
        ORDER BY puntos DESC, (goles_favor - goles_contra) DESC
    """)
    inter_rows = cursor.fetchall()

    if inter_rows:
        ui.label('CLASIFICACIÓN LIGA INTERMUÑONAL').classes(
            'text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2'
        )
        cols_inter = [
            {'name': 'pos',    'label': 'POS', 'field': 'pos',    'align': 'center'},
            {'name': 'nombre', 'label': 'CLUB', 'field': 'nombre', 'align': 'left'},
            {'name': 'pts',    'label': 'PTS',  'field': 'pts',    'align': 'center'},
            {'name': 'gf',     'label': 'GF',   'field': 'gf',     'align': 'center'},
            {'name': 'gc',     'label': 'GC',   'field': 'gc',     'align': 'center'},
        ]
        rows_inter = [
            {'pos': i + 1, 'nombre': r[0].upper(), 'pts': r[1], 'gf': r[2], 'gc': r[3]}
            for i, r in enumerate(inter_rows)
        ]
        ui.table(columns=cols_inter, rows=rows_inter, row_key='pos').classes(
            'w-full text-xs flat bg-blue-50 border border-blue-100 rounded-xl mb-4'
        )

    if not hay_copa:
        conn.close()
        with ui.row().classes('w-full items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl p-4 mt-2'):
            ui.icon('hourglass_empty', color='grey').classes('text-2xl')
            ui.label('La Copa Intermuñonal se disputará al finalizar la jornada 22.').classes('text-sm text-slate-400 italic')
        return

    # Campeón
    cursor.execute(
        "SELECT valor FROM configuracion WHERE clave = ?", (f'copa_campeon_{temporada}',)
    )
    r_camp = cursor.fetchone()
    if r_camp:
        cursor.execute("SELECT nombre FROM equipos WHERE id = ?", (r_camp[0],))
        nom_camp = cursor.fetchone()
        if nom_camp:
            with ui.row().classes('w-full justify-center items-center gap-2 mb-4 bg-amber-50 border border-amber-200 rounded-xl py-3 px-5'):
                ui.icon('emoji_events', color='amber').classes('text-2xl')
                ui.label(f'🏆 CAMPEÓN: {nom_camp[0].upper()}').classes('text-sm font-extrabold text-amber-800 tracking-widest')

    # Partidos por ronda
    cursor.execute("""
        SELECT cp.ronda, cp.enfrentamiento, cp.leg,
               el.nombre, cp.goles_local, cp.goles_visita, ev.nombre
        FROM copa_partidos cp
        JOIN equipos el ON el.id = cp.local_id
        JOIN equipos ev ON ev.id = cp.visita_id
        WHERE cp.temporada = ? AND cp.jugado = 1
        ORDER BY cp.ronda, cp.enfrentamiento, cp.leg
    """, (temporada,))
    partidos = cursor.fetchall()
    conn.close()

    if not partidos:
        ui.label('No hay resultados disponibles aún.').classes('text-slate-400 italic text-xs py-4')
        return

    from itertools import groupby
    for ronda, grupo_r in groupby(partidos, key=lambda x: x[0]):
        ui.label(RONDA_LABELS.get(ronda, f'RONDA {ronda}')).classes(
            'text-[10px] font-bold tracking-widest text-slate-400 uppercase mt-4 mb-2'
        )
        grupo_r = list(grupo_r)
        for enf, grupo_e in groupby(grupo_r, key=lambda x: x[1]):
            legs = list(grupo_e)
            with ui.column().classes('w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 mb-2 gap-1'):
                for leg in legs:
                    _, _, n_leg, loc, gl, gv, vis = leg
                    leg_lbl = 'IDA' if n_leg == 1 else 'VUELTA'
                    resultado_cls = 'text-emerald-700 font-bold' if gl > gv else ('text-rose-600 font-bold' if gv > gl else 'text-slate-500 font-bold')
                    with ui.row().classes('w-full items-center gap-2 text-xs'):
                        ui.label(leg_lbl).classes('text-[9px] font-bold text-slate-400 w-10 shrink-0')
                        ui.label(loc.upper()).classes('flex-1 text-right font-semibold text-slate-700 truncate')
                        ui.label(f'{gl} - {gv}').classes(f'text-sm px-2 shrink-0 {resultado_cls}')
                        ui.label(vis.upper()).classes('flex-1 text-left font-semibold text-slate-700 truncate')

                # Agregado del enfrentamiento
                if len(legs) == 2:
                    _, _, _, eq_a, gl1, gv1, eq_b = legs[0]
                    _, _, _, _,    gl2, gv2, _    = legs[1]
                    tot_a = gl1 + gv2
                    tot_b = gv1 + gl2
                    empate_str = '= SORTEO' if tot_a == tot_b else ''
                    ganador_str = eq_a if tot_a > tot_b else (eq_b if tot_b > tot_a else '—')
                    with ui.row().classes('w-full justify-center items-center gap-2 mt-1 pt-1 border-t border-slate-100'):
                        ui.label(f'Global: {tot_a} – {tot_b}  {empate_str}').classes('text-[10px] text-slate-500')
                        ui.label(f'✅ Pasa: {ganador_str.upper()}').classes('text-[10px] font-bold text-slate-700')
