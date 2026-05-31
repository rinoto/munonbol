import sqlite3
import os

DB_NAME = "munonbol_elche_95.db"

def forjar_base_de_datos():
    # Si ya existía una versión vieja, la liquidamos para arrancar limpios
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("🧹 Base de datos antigua eliminada para reescribir los anales de la liga...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("🏗️ Forjando las tablas del Muñonbol...")

    # ==========================================
    # 1. TABLA: ENTRENADORES (Mitos del banquillo)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrenadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            mote TEXT,
            bono_ataque INTEGER NOT NULL,
            bono_defensa INTEGER NOT NULL,
            frase_mitica TEXT
        )
    ''')

    # ==========================================
    # 2. TABLA: EQUIPOS (Con estadios oficiales y patrocinadores)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            estadio TEXT NOT NULL,
            presupuesto_pts INTEGER NOT NULL,  -- ¡En gloriosas pesetas!
            sponsor_nombre TEXT DEFAULT 'Ninguno',
            sponsor_ingreso_jornada INTEGER DEFAULT 0,
            entrenador_id INTEGER,
            puntos INTEGER DEFAULT 0,
            goles_favor INTEGER DEFAULT 0,
            goles_contra INTEGER DEFAULT 0,
            FOREIGN KEY(entrenador_id) REFERENCES entrenadores(id)
        )
    ''')

    # ==========================================
    # 3. TABLA: JUGADORES (Amigos y muñones de relleno)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER NOT NULL,
            posicion TEXT NOT NULL,           -- 'POR' (Portero) o 'JUG' (Jugador de campo)
            ataque INTEGER NOT NULL,
            defensa INTEGER NOT NULL,
            flotabilidad INTEGER DEFAULT 20,  -- Índice calórico de prestigio (estético)
            precio_pts INTEGER DEFAULT 0,     -- Tasación oficial en El Aljub
            a_la_venta INTEGER DEFAULT 0,     -- 0 = No, 1 = Expuesto en el escaparate (Máx 3)
            equipo_id INTEGER,                -- Si es NULL, está libre en El Aljub
            semanas_lesion INTEGER DEFAULT 0,
            FOREIGN KEY(equipo_id) REFERENCES equipos(id)
        )
    ''')

    # ------------------------------------------
    # INYECCIÓN DE LA DOCTRINA: ENTRENADORES
    # ------------------------------------------
    entrenadores = [
        ("Amílcar Barça", "Defensa Histórica", 0, 8, "Si los cartagineses aguantaron el asedio, mis muchachos no se hunden."),
        ("Insisto Marcos", "Ataque Persistente", 8, 0, "¡Insisto, Marcos! ¡Hay que chutar más a puerta!"),
        ("Paquita la guarra", "Motivación de Barrio", 6, 6, "Al que meta gol, bocadillo de lomo gratis."),
        ("Luis 'Achavo' Aragonés", "Furia de Carrús", 15, 0, "¡Achavo el tío bacora! ¡Míreme a los ojos y salga a morder!"),
        ("Javi 'Encarnellas' Clemente", "El Rubio de Algoda", 0, 12, "Estilo es que el rival salga del agua lleno de encarnellas.")
    ]
    cursor.executemany('''
        INSERT INTO entrenadores (nombre, mote, bono_ataque, bono_defensa, frase_mitica)
        VALUES (?, ?, ?, ?, ?)
    ''', entrenadores)

    # ------------------------------------------
    # INYECCIÓN DE LA DOCTRINA: LOS 12 EQUIPOS Y SUS ESTADIOS
    # ------------------------------------------
    # Presupuesto inicial estándar: 50 millones de pesetas (50.000.000 Pts)
    # Sponsors iniciales repartidos entre Hamburguerix y Restaurante Nugolat
    equipos_data = [
        ("San Antón Spurs", "Pintor Benedicto", 50000000, "Hamburguerix", 250000),
        ("Rayo Carrusano", "Guembley", 45000000, "Restaurante Nugolat", 300000),
        ("El Espanyol de Plaza Barcelona", "El Camp de la Plaza", 48000000, "Hamburguerix", 250000),
        ("El Toscar de Belgrado", "La botonera", 52000000, "Restaurante Nugolat", 300000),
        ("Pedro Ibarra Muñonpié", "Palmeral arena", 35000000, "Hamburguerix", 250000),
        ("Garden City", "José Serrano Ambit", 60000000, "Restaurante Nugolat", 350000),
        ("Prada y Marcos", "La lija", 55000000, "Hamburguerix", 250000),
        ("Internit del Albà", "Can Siro", 50000000, "Restaurante Nugolat", 300000),
        ("Matola City", "el Hondo traford", 40000000, "Hamburguerix", 250000),
        ("Inter de Algoda", "Macaranà", 38000000, "Restaurante Nugolat", 300000),
        ("Asprillas United", "Bacora center", 39000000, "Hamburguerix", 250000),
        ("Los Arenals Lakers", "Playas Metropolitano", 65000000, "Restaurante Nugolat", 350000)
    ]
    
    for idx, (nombre, estadio, presupuesto, spon, pago) in enumerate(equipos_data, start=1):
        # Asignamos un entrenador de la lista (ID del 1 al 5 en bucle)
        entrenador_id = (idx % 5) + 1
        cursor.execute('''
            INSERT INTO equipos (nombre, estadio, presupuesto_pts, sponsor_nombre, sponsor_ingreso_jornada, entrenador_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, estadio, presupuesto, spon, pago, entrenador_id))

    # ------------------------------------------
    # INYECCIÓN DE LA DOCTRINA: LAS 23 LEYENDAS LIBRES EN EL ALJUB
    # ------------------------------------------
    leyendas = [
        ("danieleggem", 17, "JUG", 82, 60, 25, 12000000),
        ("chimoeneas", 18, "POR", 40, 85, 30, 11500000),
        ("M. Castello", 17, "JUG", 78, 75, 20, 10500000),
        ("El hombre alga", 16, "JUG", 65, 88, 45, 14000000),
        ("Rafiki", 18, "JUG", 80, 70, 15, 9500000),
        ("PGEUG", 17, "JUG", 74, 74, 22, 9000000),
        ("El pocho", 16, "JUG", 85, 50, 18, 13000000),
        ("Chiminín", 15, "JUG", 88, 40, 12, 15000000),
        ("El Verdu", 18, "POR", 35, 89, 35, 12500000),
        ("Juanje", 17, "JUG", 72, 80, 28, 9800000),
        ("Fransuà", 19, "JUG", 84, 65, 20, 11000000),
        ("Dechopān", 17, "JUG", 77, 73, 40, 10500000),
        ("El Mendi", 18, "JUG", 60, 82, 33, 8500000),
        ("Gonzalo", 16, "JUG", 79, 71, 24, 11200000),
        ("Iván Primo", 17, "JUG", 83, 68, 19, 12800000),
        ("Periquín", 15, "JUG", 86, 45, 15, 14500000),
        ("Don Quirant", 19, "POR", 30, 92, 50, 16000000),
        ("Bonus", 17, "JUG", 75, 75, 30, 9000000),
        ("Zulema", 18, "JUG", 81, 79, 26, 13500000),
        ("Carmen LM", 17, "JUG", 87, 72, 22, 15500000),
        ("Negro de la Noche", 19, "JUG", 90, 55, 10, 17000000),
        ("El palas", 18, "JUG", 68, 85, 38, 10000000),
        ("Sancho", 17, "JUG", 76, 76, 31, 9500000)
    ]

    for nombre, edad, pos, atk, df, flot, precio in leyendas:
        # Se insertan con equipo_id = NULL (Libres) y a_la_venta = 1 (Disponibles en El Aljub)
        cursor.execute('''
            INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, flotabilidad, precio_pts, equipo_id, a_la_venta)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1)
        ''', (nombre, edad, pos, atk, df, flot, precio))

    # ------------------------------------------
    # GENERAR RELLENO: JUGADORES BASE PARA LOS EQUIPOS
    # ------------------------------------------
    # Rellenamos cada uno de los 12 equipos con 1 portero malo y 5 muñones base
    # para que tengan con quién jugar antes de que fichen a las verdaderas leyendas.
    for eq_id in range(1, 13):
        cursor.execute('''
            INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, flotabilidad, precio_pts, equipo_id, a_la_venta)
            VALUES (?, 18, 'POR', 45, 45, 20, 2000000, ?, 0)
        ''', (f"Portero Relleno B{eq_id}", eq_id))
        
        for j in range(1, 6):
            cursor.execute('''
                INSERT INTO jugadores (nombre, edad, posicion, ataque, defensa, flotabilidad, precio_pts, equipo_id, a_la_venta)
                VALUES (?, 18, 'JUG', 50, 50, 20, 2500000, ?, 0)
            ''', (f"Muñón {j} del Eq {eq_id}", eq_id))
    # ==========================================
    # 4. TABLA: CONFIGURACION (Estado del torneo)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor INTEGER
        )
    ''')
    # Empezamos en la Jornada 1
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada_actual', 1)")
    conn.commit()
    conn.close()
    print("🎯 ¡Base de datos maestro 'munonbol_elche_95.db' forjada e inicializada con éxito total!")

if __name__ == "__main__":
    forjar_base_de_datos()