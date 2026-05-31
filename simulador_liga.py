import sqlite3
import random
import main  # IMPORTANTE: Importamos main para usar la ruta dinamica de la partida

def generar_calendario_liga():
    """
    Algoritmo Round Robin para cruzar UNICAMENTE a los 12 equipos de la 
    Liga SuperEmpanadill en 22 jornadas.
    """
    db_path = main.obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jornada INTEGER NOT NULL,
            local_id INTEGER NOT NULL,
            visita_id INTEGER NOT NULL,
            goles_local INTEGER,
            goles_visita INTEGER,
            jugado INTEGER DEFAULT 0,
            FOREIGN KEY(local_id) REFERENCES equipos(id),
            FOREIGN KEY(visita_id) REFERENCES equipos(id)
        )
    ''')
    
    cursor.execute("DELETE FROM partidos")
    cursor.execute("UPDATE equipos SET puntos = 0, goles_favor = 0, goles_contra = 0")
    
    # 🌟 FILTRO CLAVE: Solo entran en el sorteo los de Primera Division
    cursor.execute("SELECT id FROM equipos WHERE division = 'Liga SuperEmpanadill'")
    equipos = [row[0] for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    
    num_equipos = len(equipos)
    if num_equipos % 2 != 0:
        return "❌ Se necesita un número par de equipos (exactamente 12) en Primera."

    jornadas_ida = num_equipos - 1
    partidos_por_jornada = num_equipos // 2
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Generacion de la Ida (Jornadas 1 a 11)
    for jornada in range(1, jornadas_ida + 1):
        for i in range(partidos_por_jornada):
            local = equipos[i]
            visita = equipos[num_equipos - 1 - i]
            
            if jornada % 2 == 0:
                local, visita = visita, local
                
            cursor.execute("INSERT INTO partidos (jornada, local_id, visita_id) VALUES (?, ?, ?)", 
                           (jornada, local, visita))
        
        equipos = [equipos[0]] + [equipos[-1]] + equipos[1:-1]
        
    conn.commit()
    conn.close()
    
    # Generacion de la Vuelta (Jornadas 12 a 22)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT jornada, local_id, visita_id FROM partidos WHERE jornada <= ?", (jornadas_ida,))
    partidos_ida = cursor.fetchall()
    
    for j_ida, loc_id, vis_id in partidos_ida:
        j_vuelta = j_ida + jornadas_ida
        cursor.execute("INSERT INTO partidos (jornada, local_id, visita_id) VALUES (?, ?, ?)", 
                       (j_vuelta, vis_id, loc_id))
        
    conn.commit()
    conn.close()
    return "🗓️ ¡Calendario oficial de la Liga SuperEmpanadill (12 equipos) generado!"


def _poder_equipo(cursor, equipo_id):
    """
    Devuelve (med_atk, med_def, med_bac, penalty) para un equipo.
    - Si hay 5+ titulares sanos: penalty = 1.0
    - Si hay menos: rellena con suplentes sanos y reduce el poder
      un 12% por cada titular que falta (mín. 0.40).
    """
    cursor.execute(
        "SELECT COUNT(*) FROM jugadores WHERE equipo_id = ? AND titular BETWEEN 1 AND 5 AND semanas_lesion = 0",
        (equipo_id,)
    )
    n_sanos = cursor.fetchone()[0]

    if n_sanos >= 5:
        cursor.execute(
            "SELECT AVG(ataque), AVG(defensa), AVG(COALESCE(bacora,0)) "
            "FROM jugadores WHERE equipo_id = ? AND titular BETWEEN 1 AND 5 AND semanas_lesion = 0",
            (equipo_id,)
        )
        penalty = 1.0
    else:
        # Usar todos los jugadores sanos del equipo (titulares + suplentes)
        cursor.execute(
            "SELECT AVG(ataque), AVG(defensa), AVG(COALESCE(bacora,0)) "
            "FROM jugadores WHERE equipo_id = ? AND semanas_lesion = 0",
            (equipo_id,)
        )
        faltantes = max(0, 5 - n_sanos)
        penalty = max(0.40, 1.0 - faltantes * 0.12)

    res = cursor.fetchone()
    med_atk = (res[0] or 50) * penalty
    med_def = (res[1] or 50) * penalty
    med_bac = (res[2] or 0)  * penalty
    return med_atk, med_def, med_bac, penalty


def simular_partido(partido_id):
    db_path = main.obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tratamiento de seguridad si los entrenadores no estan mapeados en equipos basicos
    cursor.execute('''
        SELECT p.local_id, p.visita_id, el.nombre, ev.nombre
        FROM partidos p
        JOIN equipos el ON p.local_id = el.id
        JOIN equipos ev ON p.visita_id = ev.id
        WHERE p.id = ? AND p.jugado = 0
    ''', (partido_id,)) 
    # Nota: Simplificamos la query para evitar bloqueos si no hay tablas relacionales de entrenadores activas
    cursor.execute('''
        SELECT p.local_id, p.visita_id, el.nombre, ev.nombre
        FROM partidos p
        JOIN equipos el ON p.local_id = el.id
        JOIN equipos ev ON p.visita_id = ev.id
        WHERE p.id = ? AND p.jugado = 0
    ''', (partido_id,))
    
    partido = cursor.fetchone()
    if not partido:
        conn.close()
        return None
        
    loc_id, vis_id, name_l, name_v = partido
    
    # Potencia de cada equipo (con penalización si faltan titulares sanos)
    med_atk_l, med_def_l, med_bac_l, pen_l = _poder_equipo(cursor, loc_id)
    med_atk_v, med_def_v, med_bac_v, pen_v = _poder_equipo(cursor, vis_id)

    poder_ofensivo_local   = med_atk_l + med_bac_l * 0.5 + random.randint(1, 15)
    poder_defensivo_visita = med_def_v + random.randint(1, 15)
    poder_ofensivo_visita  = med_atk_v + med_bac_v * 0.5 + random.randint(1, 15)
    poder_defensivo_local  = med_def_l + random.randint(1, 15)

    # --- 🌟 CÁLCULO DE GOLES (distribución ~12 totales, permite 0-0) ---
    _DIST  = [0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]
    _PESOS = [2,  3,  6,  9, 12, 14, 16, 14, 10,  7,  4,  2,  1]

    goles_l = random.choices(_DIST, weights=_PESOS, k=1)[0]
    goles_v = random.choices(_DIST, weights=_PESOS, k=1)[0]

    # Bonificación por ventaja ATK/DEF real (+0-2 al equipo dominante)
    total_poder = poder_ofensivo_local + poder_ofensivo_visita
    ratio_l = poder_ofensivo_local / total_poder if total_poder > 0 else 0.5
    if ratio_l > 0.55:
        goles_l += random.randint(0, 2)
    elif ratio_l < 0.45:
        goles_v += random.randint(0, 2)

    # � BALONES PINCHADOS: reduce goles del visitante ~30%
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'balones_pinchados'")
    res_balones = cursor.fetchone()
    balones_pinchados_activo = res_balones[0] if res_balones else 0
    mi_equipo_id = main.obtener_mi_equipo_id()
    if balones_pinchados_activo == 1 and loc_id == mi_equipo_id:
        goles_v = max(0, int(goles_v * 0.7))
    # --- 🌟 FIN DEL BLOQUE ---

    cursor.execute("UPDATE partidos SET goles_local = ?, goles_visita = ?, jugado = 1 WHERE id = ?",
                   (goles_l, goles_v, partido_id))
    
    puntos_l, puntos_v = (3, 0) if goles_l > goles_v else ((0, 3) if goles_v > goles_l else (1, 1))
    
    cursor.execute('''UPDATE equipos SET puntos = puntos + ?, goles_favor = goles_favor + ?, 
                      goles_contra = goles_contra + ? WHERE id = ?''', (puntos_l, goles_l, goles_v, loc_id))
    cursor.execute('''UPDATE equipos SET puntos = puntos + ?, goles_favor = goles_favor + ?, 
                      goles_contra = goles_contra + ? WHERE id = ?''', (puntos_v, goles_v, goles_l, vis_id))
    
    # --- DENTRO DE simular_partido(partido_id) EN simulador_liga.py ---
    
    # 💥 PROBABILIDAD DE LESIÓN (15% de opciones por partido simulado)
    if random.random() < 0.80:
        # Buscamos un jugador aleatorio de cualquiera de los dos equipos que están jugando
        cursor.execute("SELECT id, nombre FROM jugadores WHERE equipo_id IN (?, ?) AND (est_actif IS NULL OR est_actif = 1) AND semanas_lesion = 0", (loc_id, vis_id))
        todos_los_activos = cursor.fetchall()
        
        if todos_los_activos:
            jugador_afectado_id, nom_jugador = random.choice(todos_los_activos)
            
            # Seleccionamos una lesión al azar del catálogo maestro
            cursor.execute("SELECT id, nombre, semanas FROM lesiones ORDER BY RANDOM() LIMIT 1")
            lesion = cursor.fetchone()
            
            if lesion:
                les_id, nom_lesion, num_semanas = lesion
                # Guardamos tanto el ID de la lesión como el contador de semanas en la ficha del jugador
                cursor.execute('''
                    UPDATE jugadores 
                    SET semanas_lesion = ?, lesion_id = ? 
                    WHERE id = ?
                ''', (num_semanas, les_id, jugador_afectado_id))
                
                print(f"🚑 ¡PARTE MÉDICO!: {nom_jugador} se ha lesionado. Diagnóstico: '{nom_lesion}'. ¡Baja por {num_semanas} jornadas!")

    conn.commit()
    conn.close()
    return f"🏟️ {name_l} {goles_l} - {goles_v} {name_v}"


def jugar_jornada_completa(num_jornada):
    db_path = main.obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM partidos WHERE jornada = ? AND jugado = 0", (num_jornada,))
    partidos_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not partidos_ids:
        return []
        
    resultados = []
    for p_id in partidos_ids:
        res = simular_partido(p_id)
        if res: resultados.append(res)
        
    return resultados