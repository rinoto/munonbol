import sqlite3
import main  # 🌟 IMPORTANTE: Importamos tu módulo principal

# El menú oficial de la cantina con sus costes y beneficios de flotabilidad
MENU_CANTINA = {
    "choleck": {"nombre": "Choleck de Litro", "coste": 150000, "flotabilidad": 2},
    "lomo": {"nombre": "Bocata de Lomo de Paquita", "coste": 350000, "flotabilidad": 5},
    "arroz": {"nombre": "Arroz con Costra Premium", "coste": 750000, "flotabilidad": 12}
}

def alimentar_jugador(jugador_id, equipo_id, tipo_comida):
    """Gasta pesetas del equipo para aumentar la flotabilidad de un jugador."""
    if tipo_comida not in MENU_CANTINA:
        return "❌ Ese plato no está en el menú de hoy."
        
    comida = MENU_CANTINA[tipo_comida]
    coste = comida["coste"]
    plus_flotabilidad = comida["flotabilidad"]
    
    # 🌟 CORREGIDO: Conectamos a la ruta dinámica de la partida en juego
    conn = sqlite3.connect(main.obtener_ruta_db())
    cursor = conn.cursor()
    
    # 1. Verificar presupuesto del equipo (usando la columna oficial presupuesto_pts)
    cursor.execute("SELECT presupuesto_pts, nombre FROM equipos WHERE id = ?", (equipo_id,))
    equipo = cursor.fetchone()
    if not equipo:
        conn.close()
        return "❌ El equipo no existe."
    
    presupuesto, nombre_equipo = equipo
    if presupuesto < coste:
        conn.close()
        return f"❌ No hay bastantes pesetas en la caja de {nombre_equipo}. Cuesta {coste:,} Pts."
        
    # 2. Verificar que el jugador es del equipo
    cursor.execute("SELECT nombre, flotabilidad FROM jugadores WHERE id = ? AND equipo_id = ?", (jugador_id, equipo_id))
    jugador = cursor.fetchone()
    if not jugador:
        conn.close()
        return "❌ Este jugador no pertenece a tu disciplina de por vida."
        
    nombre_jugador, flotabilidad_actual = jugador
    nueva_flotabilidad = min(flotabilidad_actual + plus_flotabilidad, 100) # El tope es 100% de grasa flotante
    
    # 3. Cobrar y cebar (usando presupuesto_pts)
    cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - ? WHERE id = ?", (coste, equipo_id))
    cursor.execute("UPDATE jugadores SET flotabilidad = ? WHERE id = ?", (nueva_flotabilidad, jugador_id))
    
    conn.commit()
    conn.close()
    
    return f"🍔 ¡{nombre_jugador} se ha metido un {comida['nombre']}! Flotabilidad: {nueva_flotabilidad}%"