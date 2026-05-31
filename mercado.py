from nicegui import ui
import sqlite3
import random
import main

DB_NAME = "munonbol_elche_95.db"

def obtener_conexion_db():
    from main import obtener_ruta_db
    return sqlite3.connect(obtener_ruta_db())

FRASES_REGATEO = [
    "¿Me estás diciendo que {nombre} no vale {precio} Pts? Míralo bien, ¡no es de cabra!",
    "¿Qué? ¿Pretendes insultarme a mí con {precio} Pts? ¡¿Con mi pobre abuela muriéndose?!",
    "¿Qué? ¡A mí me costó {precio_alto} Pts! ¡Es que pretendes arruinarme!",
    "¿Qué? ¿Por esta calabaza? Vale por lo menos {precio_alto} Pts.",
    "¿Lo has mirado bien? este no es de los que se hunden",
    "Yo soy cola, tú pegamento",
    "¡Noooo! Quiero {precio} Pts, es mi última oferta, ¡así me muera!"
]

def formatear_precio_corto(valor):
    if valor is None or valor == 0:
        return "0 Pts"
    if valor >= 1000000:
        millones = valor / 1000000
        if millones.is_integer():
            return f"{int(millones)}M Pts"
        else:
            return f"{millones:.1f}M Pts".replace(".", ",")
    return f"{int(valor / 1000)}K Pts"

def obtener_fondos_y_plantilla(equipo_id):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT presupuesto_pts FROM equipos WHERE id = ?", (equipo_id,))
    presupuesto = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jugadores WHERE equipo_id = ?", (equipo_id,))
    num_jugadores = cursor.fetchone()[0]
    conn.close()
    return presupuesto, num_jugadores

def obtener_mercado_compras(equipo_id):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.id, j.nombre, j.posicion, j.ataque, j.defensa, j.precio_pts, e.nombre
        FROM jugadores j
        LEFT JOIN equipos e ON j.equipo_id = e.id
        WHERE j.equipo_id = ? AND j.a_la_venta = 1
    """, (equipo_id,))
    propios = cursor.fetchall()
    cursor.execute("""
        SELECT j.id, j.nombre, j.posicion, j.ataque, j.defensa, j.precio_pts, e.nombre
        FROM jugadores j
        LEFT JOIN equipos e ON j.equipo_id = e.id
        WHERE j.equipo_id IS NULL OR (j.equipo_id != ? AND j.a_la_venta = 1)
        LIMIT 20
    """, (equipo_id,))
    otros = cursor.fetchall()
    conn.close()
    def fila(f, propio):
        return {'id': f[0], 'nombre': f[1], 'pos': f[2],
                'ataque': f[3], 'defensa': f[4], 'media': int((f[3]+f[4])/2),
                'precio': f[5], 'propietario': f[6] if f[6] else "Libre (El Aljub)",
                'es_propio': propio}
    return [fila(f, True) for f in propios] + [fila(f, False) for f in otros]

def obtener_mis_ventas(equipo_id):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, posicion, ataque, defensa, precio_pts, a_la_venta FROM jugadores WHERE equipo_id = ?", (equipo_id,))
    filas = cursor.fetchall()
    conn.close()
    return [{
        'id': f[0], 'nombre': f[1], 'pos': f[2],
        'ataque': f[3], 'defensa': f[4], 'media': int((f[3]+f[4])/2),
        'precio': f[5], 'en_venta': f[6]
    } for f in filas]

def generar_ofertas_jugadores_venta(equipo_id, jornada):
    import main  # 🌟 Aseguramos enrutar a la partida viva
    db_path = main.obtener_ruta_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Extraemos a los jugadores en venta, ¡ahora incluyendo su Ataque y Defensa!
    cursor.execute("SELECT id, precio_pts, ataque, defensa FROM jugadores WHERE equipo_id = ? AND a_la_venta = 1", (equipo_id,))
    jugadores_venta = cursor.fetchall()
    
    if not jugadores_venta:
        conn.close()
        return

    # 2. Obtenemos la clasificación de TODOS los equipos para ver quién manda en la liga
    cursor.execute("""
        SELECT e.id, e.nombre,
            SUM(CASE WHEN p.local_id = e.id AND p.goles_local > p.goles_visita THEN 3
                     WHEN p.visita_id = e.id AND p.goles_visita > p.goles_local THEN 3
                     WHEN p.goles_local IS NOT NULL AND p.goles_local = p.goles_visita THEN 1
                     ELSE 0 END) as puntos
        FROM equipos e
        LEFT JOIN partidos p ON (p.local_id = e.id OR p.visita_id = e.id) AND p.goles_local IS NOT NULL
        GROUP BY e.id
        ORDER BY puntos DESC
    """)
    clasificacion = cursor.fetchall()
    if not clasificacion:
        conn.close()
        return

    # 3. 📈 PRESTIGIO DE TU EQUIPO: ¿En qué posición de poder estás para negociar?
    max_puntos = max((c[2] or 0) for c in clasificacion) or 1
    mis_puntos = next((c[2] or 0 for c in clasificacion if c[0] == equipo_id), 0)
    
    # Si vas líder, sacas hasta un +40% extra de dinero en las ventas por ser un equipo top.
    factor_prestigio = 1.0 + (0.4 * (mis_puntos / max_puntos))

    # Filtramos a los compradores (todos los demás equipos menos tú)
    compradores = [c for c in clasificacion if c[0] != equipo_id]

    for j_id, j_precio, j_atk, j_def in jugadores_venta:
        # 4. ⚽ CALIDAD REAL: Calculamos la media del jugador
        media = ((j_atk or 0) + (j_def or 0)) / 2
        
        # Fórmula: Compara la media con un jugador estándar de 50.
        # Si tiene 80 de media, vale un 160% (1.6). Si tiene 20 de media, cae al 0.4.
        factor_calidad = max(0.3, media / 50.0) 
        
        # El mercado ya no se traga que pidas 10 millones por un cojo.
        # Ajustamos el precio base que pusiste multiplicándolo por su factor de calidad.
        precio_justo_mercado = (j_precio * factor_calidad)

        # Generamos entre 1 y 3 ofertas entrantes
        num_ofertas = random.randint(1, min(3, len(compradores)))
        ofertantes = random.sample(compradores, num_ofertas)
        
        for eq_comp_id, eq_comp_nombre, pts_comp in ofertantes:
            # 5. 🗣️ FACTOR REGATEO: Cada equipo hace una valoración ligeramente distinta (+/- 15%)
            factor_regateo = random.uniform(0.85, 1.15)
            
            # 💰 CÁLCULO FINAL: Precio Justo * Prestigio de tu equipo * Regateo
            importe_final = int(precio_justo_mercado * factor_prestigio * factor_regateo)

            # 🌟 EL TOPE DE REALISMO: ¡Nadie te ofrece más de lo que pides!
            if importe_final > j_precio:
                importe_final = j_precio

            cursor.execute("""
                INSERT INTO ofertas_pendientes (jugador_id, equipo_comprador_id, nombre_comprador, importe, jornada)
                VALUES (?, ?, ?, ?, ?)
            """, (j_id, eq_comp_id, eq_comp_nombre, importe_final, jornada))
            
    conn.commit()
    conn.close()

def obtener_ofertas_pendientes(equipo_id):
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.id, o.jugador_id, j.nombre, o.equipo_comprador_id, o.nombre_comprador, o.importe
        FROM ofertas_pendientes o
        JOIN jugadores j ON o.jugador_id = j.id
        WHERE j.equipo_id = ?
        ORDER BY o.jugador_id, o.importe DESC
    """, (equipo_id,))
    rows = cursor.fetchall()
    conn.close()
    conteo = {}
    result = []
    for r in rows:
        conteo[r[1]] = conteo.get(r[1], 0) + 1
        if conteo[r[1]] <= 3:
            result.append({'oferta_id': r[0], 'jugador_id': r[1], 'jugador': r[2],
                           'comprador_id': r[3], 'comprador': r[4], 'importe': r[5]})
    return result

def mostrar_ventana_ofertas(equipo_id, callback_refrescar=None):
    ofertas = obtener_ofertas_pendientes(equipo_id)
    if not ofertas:
        return
    pendientes = {'vivas': len(ofertas), 'rechazadas': 0, 'aceptadas': 0}
    filas_por_jugador = {}
    with ui.dialog() as dlg, ui.card().classes('w-[560px] bg-slate-50 p-6 rounded-2xl shadow-xl font-sans'):
        ui.label("📬 Tienes ofertas que parecen interesar lo mínimo").classes('text-base font-bold text-slate-800 mb-1')
        ui.label("Decide el destino de tus jugadores antes de continuar").classes('text-xs text-slate-400 mb-4')
        with ui.scroll_area().classes('w-full max-h-[400px]'):
            for o in ofertas:
                with ui.row().classes('w-full bg-white border border-slate-100 rounded-lg px-4 py-3 items-center gap-3 mb-2') as fila:
                    filas_por_jugador.setdefault(o['jugador_id'], []).append(fila)
                    with ui.column().classes('flex-1 gap-0'):
                        ui.label(o['jugador'].upper()).classes('font-bold text-slate-800 text-sm')
                        ui.label(o['comprador']).classes('text-[11px] text-slate-500')
                    ui.label(formatear_precio_corto(o['importe'])).classes('font-bold text-emerald-700 text-sm shrink-0')

                    def hacer_aceptar(oferta=o):
                        conn2 = obtener_conexion_db()
                        cur2 = conn2.cursor()
                        cur2.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + ? WHERE id = ?", (oferta['importe'], equipo_id))
                        cur2.execute("UPDATE jugadores SET equipo_id = ?, titular = 0, a_la_venta = 0 WHERE id = ?", (oferta['comprador_id'], oferta['jugador_id']))
                        cur2.execute("DELETE FROM ofertas_pendientes WHERE jugador_id = ?", (oferta['jugador_id'],))
                        conn2.commit()
                        conn2.close()
                        hermanas = filas_por_jugador.get(oferta['jugador_id'], [])
                        pendientes['vivas'] -= len(hermanas)
                        for r in hermanas:
                            r.set_visibility(False)
                        ui.notify(f"✅ {oferta['jugador']} vendido a {oferta['comprador']} por {formatear_precio_corto(oferta['importe'])}", type='positive')
                        if callback_refrescar:
                            callback_refrescar()
                        pendientes['aceptadas'] += 1
                        if pendientes['vivas'] <= 0:
                            dlg.close()

                    def hacer_rechazar(oferta=o, row=fila):
                        conn2 = obtener_conexion_db()
                        cur2 = conn2.cursor()
                        cur2.execute("DELETE FROM ofertas_pendientes WHERE id = ?", (oferta['oferta_id'],))
                        conn2.commit()
                        conn2.close()
                        row.set_visibility(False)
                        pendientes['rechazadas'] += 1
                        pendientes['vivas'] -= 1
                        if pendientes['vivas'] <= 0:
                            if pendientes['aceptadas'] == 0:
                                ui.notify("🤷 Yo por lo menos ofrezco...", type='warning', timeout=4000)
                            dlg.close()

                    ui.button('ACEPTAR', on_click=hacer_aceptar).props('unelevated size=sm').classes('bg-emerald-600 text-white text-xs shrink-0')
                    ui.button('RECHAZAR', on_click=hacer_rechazar).props('unelevated size=sm').classes('bg-rose-600 text-white text-xs shrink-0')
    dlg.open()

def abrir_mercado_aljub(jornada_actual, callback_refresco_main):
    from main import obtener_mi_equipo_id
    ui.dark_mode().disable()
    equipo_id = obtener_mi_equipo_id()

    with ui.dialog() as dialogo, ui.card().classes('w-[800px] max-w-5xl bg-slate-50 p-6 rounded-2xl shadow-xl font-sans text-slate-900'):
        
        with ui.row().classes('w-full border-b border-slate-200 pb-4 justify-between items-center'):
            with ui.column().classes('gap-0'):
                ui.label("Lonja de Traspasos — El Aljub").classes('text-xl font-bold tracking-tight text-slate-900')
                ui.label("Regatea contratos y gestiona el escaparate de tu plantilla").classes('text-xs text-slate-400')
            ui.button(icon='close', on_click=dialogo.close).props('flat round dense').classes('text-slate-400')

        # Indicadores de estado de la plantilla
        stats_box = ui.row().classes('w-full justify-end gap-4 text-xs font-semibold px-2')

        def refrescar_stats_mercado():
            stats_box.clear()
            with stats_box:
                pres, total_j = obtener_fondos_y_plantilla(equipo_id)
                ui.label(f"Presupuesto: {pres:,} Pts").classes('text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md')
                ui.label(f"Efectivos: {total_j}/12 (Mín: 6)").classes('text-blue-700 bg-blue-50 px-2 py-1 rounded-md')

        refrescar_stats_mercado()

        # Selector de sección estilo Diario
        with ui.row().classes('w-full justify-between items-center my-2 border-b border-slate-100 pb-4'):
            with ui.row().classes('gap-4'):
                btn_compra_tab = ui.button('Adquirir Cracks', icon='shopping_bag').props('unelevated rounded').classes('bg-slate-900 text-white text-xs')
                btn_venta_tab = ui.button('Escaparate de Ventas', icon='sell').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs')
                btn_ent_tab = ui.button('Banquillo Técnico', icon='sports').props('unelevated rounded').classes('bg-slate-200 text-slate-700 text-xs')
            ui.button('VER OFERTAS', icon='mail', on_click=lambda: mostrar_ventana_ofertas(equipo_id, callback_refresco_main)).props('unelevated rounded').classes('bg-indigo-600 text-white text-xs')

        panel_compras = ui.column().classes('w-full')
        panel_ventas = ui.column().classes('w-full hidden')
        panel_entrenadores = ui.column().classes('w-full hidden')

        # --- SECCIÓN COMPRAR (CON REGATEO DE LA VIDA DE BRIAN) ---
        def redibujar_compras():
            panel_compras.clear()
            with panel_compras:
                for j in obtener_mercado_compras(equipo_id):
                    med_bg = 'bg-emerald-500' if j['media'] >= 70 else ('bg-amber-400' if j['media'] >= 50 else 'bg-rose-400')
                    fila_cls = 'w-full border rounded-lg px-4 py-3 items-center text-xs mb-1 gap-3'
                    if j['es_propio']:
                        fila_cls += ' bg-slate-100 border-slate-200 opacity-70'
                    else:
                        fila_cls += ' bg-white border-slate-100 hover:bg-slate-50'
                    with ui.row().classes(fila_cls):
                        with ui.column().classes('flex-1 gap-0 min-w-0'):
                            ui.label(j['nombre'].upper()).classes('font-bold text-slate-800 text-[12px] truncate')
                            lbl_prop = ("🏷️ TU JUGADOR · EN VENTA" if j['es_propio'] else f"{j['pos']}  ·  {j['propietario']}")
                            ui.label(lbl_prop).classes('text-[10px] text-slate-400')
                        with ui.row().classes('items-center gap-3 shrink-0'):
                            ui.label(f"ATK {j['ataque']}").classes('text-[11px] text-emerald-600 font-bold')
                            ui.label(f"DEF {j['defensa']}").classes('text-[11px] text-blue-600 font-bold')
                            ui.label(str(j['media'])).classes(f'text-sm font-extrabold text-white px-2 py-0.5 rounded-full {med_bg}')
                        ui.label(formatear_precio_corto(j['precio'])).classes('w-16 text-right text-slate-500 shrink-0')
                        if j['es_propio']:
                            ui.button('OFERTAR', on_click=lambda: ui.notify('Chiquito, no vas a comprar lo que es tuyo', type='warning')).props('unelevated rounded size=sm').classes('bg-slate-400 text-white shrink-0 text-[10px]')
                        else:
                            oferta_input = ui.number(value=round(j['precio']*0.8/1000000, 1), step=0.5, min=0).props('outlined dense suffix="M"').classes('w-28 text-xs shrink-0')
                            ui.button('OFERTAR', on_click=lambda jj=j, oi=oferta_input: procesar_regateo(jj, oi)).props('unelevated rounded size=sm').classes('bg-slate-900 text-white shrink-0 text-[10px]')
        # --- SECCIÓN VENDER (CON AZAR BASADO EN LA CLASIFICACIÓN) ---
        def redibujar_ventas():
            panel_ventas.clear()
            with panel_ventas:
                for j in obtener_mis_ventas(equipo_id):
                    med_bg = 'bg-emerald-500' if j['media'] >= 70 else ('bg-amber-400' if j['media'] >= 50 else 'bg-rose-400')
                    with ui.row().classes('w-full bg-white border border-slate-100 rounded-lg px-4 py-3 items-center text-xs mb-1 gap-3 hover:bg-slate-50'):
                        with ui.column().classes('flex-1 gap-0 min-w-0'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(j['nombre'].upper()).classes('font-bold text-slate-800 text-[12px] truncate')
                                if j['en_venta']:
                                    ui.label('🏷️ EN VENTA').classes('text-[9px] font-bold text-amber-600 bg-amber-50 border border-amber-200 rounded px-1 py-0.5 shrink-0')
                            ui.label(j['pos']).classes('text-[10px] text-slate-400')
                        with ui.row().classes('items-center gap-3 shrink-0'):
                            ui.label(f"ATK {j['ataque']}").classes('text-[11px] text-emerald-600 font-bold')
                            ui.label(f"DEF {j['defensa']}").classes('text-[11px] text-blue-600 font-bold')
                            ui.label(str(j['media'])).classes(f'text-sm font-extrabold text-white px-2 py-0.5 rounded-full {med_bg}')
                        with ui.row().classes('items-center gap-2 shrink-0'):
                            ui.label(formatear_precio_corto(j['precio'])).classes('text-[11px] text-slate-500 w-14 text-right')
                            input_precio = ui.number(value=round(j['precio']/1000000, 1), step=0.5, min=0).props('outlined dense suffix="M"').classes('w-24 text-xs')
                            ui.button('DAR LA PATADA', on_click=lambda jj=j, ip=input_precio: liquidar_jugador(jj, ip)).props('unelevated rounded size=sm').classes('bg-rose-600 text-white text-[10px]')

                            def toggle_escaparate(jj=j, ip=input_precio):
                                conn2 = obtener_conexion_db()
                                cur2 = conn2.cursor()
                                nuevo_estado = 0 if jj['en_venta'] else 1
                                if nuevo_estado == 1:
                                    precio_fijado = int((ip.value or 0) * 1_000_000)
                                    if precio_fijado <= 0:
                                        ui.notify("❌ Fija un precio válido antes de poner a la venta.", type='negative')
                                        conn2.close()
                                        return
                                    cur2.execute("UPDATE jugadores SET a_la_venta = 1, precio_pts = ? WHERE id = ?", (precio_fijado, jj['id']))
                                else:
                                    cur2.execute("UPDATE jugadores SET a_la_venta = 0 WHERE id = ?", (jj['id'],))
                                    cur2.execute("DELETE FROM ofertas_pendientes WHERE jugador_id = ?", (jj['id'],))
                                conn2.commit()
                                conn2.close()
                                redibujar_ventas()
                                redibujar_compras()

                            if j['en_venta']:
                                ui.button('RETIRAR', on_click=toggle_escaparate).props('unelevated rounded size=sm').classes('bg-amber-500 text-white text-[10px]')
                            else:
                                ui.button('PONER A LA VENTA', on_click=toggle_escaparate).props('unelevated rounded size=sm').classes('bg-slate-600 text-white text-[10px]')
        def ejecutar_fichaje_directo(j_id, coste):
            conn = obtener_conexion_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - ? WHERE id = ?", (coste, equipo_id))
            cursor.execute("UPDATE jugadores SET equipo_id = ?, titular = 0, a_la_venta = 0 WHERE id = ?", (equipo_id, j_id))
            conn.commit()
            conn.close()

        def procesar_regateo(j, oferta_ref):
            oferta = int((oferta_ref.value or 0) * 1_000_000)
            pres, total_j = obtener_fondos_y_plantilla(equipo_id)
            if total_j >= 12:
                ui.notify("❌ Plantilla al completo (máximo 12 jugadores).", type='negative')
                return
            if oferta <= 0 or oferta > pres:
                ui.notify("❌ Fondos insuficientes o importe inválido.", type='negative')
                return
            if oferta < j['precio'] * 0.6:
                frase = random.choice(FRASES_REGATEO).format(
                    nombre=j['nombre'],
                    precio=formatear_precio_corto(int(j['precio'] * 0.9)),
                    precio_alto=formatear_precio_corto(int(j['precio'] * 1.2))
                )
                ui.notify(frase, type='warning', timeout=6000)
                return
            ejecutar_fichaje_directo(j['id'], oferta)
            ui.notify(f"✅ ¡{j['nombre']} fichado por {formatear_precio_corto(oferta)}!", type='positive')
            dialogo.close()
            callback_refresco_main()

        def liquidar_jugador(j, precio_ref):
            precio = int((precio_ref.value or 0) * 1_000_000)
            if precio <= 0:
                ui.notify("❌ Introduce un precio válido.", type='negative')
                return
            conn = obtener_conexion_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + ? WHERE id = ?", (precio, equipo_id))
            cursor.execute("UPDATE jugadores SET equipo_id = NULL, titular = 0, a_la_venta = 0 WHERE id = ?", (j['id'],))
            conn.commit()
            conn.close()
            ui.notify(f"💰 {j['nombre']} vendido por {formatear_precio_corto(precio)}.", type='positive')
            refrescar_stats_mercado()
            redibujar_ventas()
            callback_refresco_main()

        # Control de Pestañas modernas
        def redibujar_entrenadores():
            panel_entrenadores.clear()
            with panel_entrenadores:
                conn_e = obtener_conexion_db()
                cur_e = conn_e.cursor()
                cur_e.execute("""
                    SELECT ent.id, ent.nombre, ent.mote, ent.bono_ataque, ent.bono_defensa, ent.frase_mitica, ent.precio_pts
                    FROM equipos eq LEFT JOIN entrenadores ent ON ent.id = eq.entrenador_id
                    WHERE eq.id = ?
                """, (equipo_id,))
                mi_ent = cur_e.fetchone()
                cur_e.execute("""
                    SELECT ent.id, ent.nombre, ent.mote, ent.bono_ataque, ent.bono_defensa, ent.frase_mitica, ent.precio_pts
                    FROM entrenadores ent
                    WHERE ent.id NOT IN (
                        SELECT entrenador_id FROM equipos WHERE entrenador_id IS NOT NULL
                    )
                """)
                libres = cur_e.fetchall()
                conn_e.close()

                ui.label('TU CUERPO TÉCNICO ACTUAL').classes('text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2')
                if mi_ent and mi_ent[0]:
                    ent_id, nombre, mote, atk, dfs, frase, precio_ptas = mi_ent
                    indemnizacion = int((precio_ptas or 0) * 0.5)
                    with ui.row().classes('w-full bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 items-center gap-4 mb-4'):
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(nombre.upper()).classes('font-bold text-amber-900 text-sm')
                            if mote:
                                ui.label(f'"{mote}"').classes('text-[10px] italic text-amber-700')
                            if frase:
                                ui.label(f'"{frase}"').classes('text-[10px] text-slate-500 mt-1 italic')
                        with ui.row().classes('gap-3 shrink-0 text-[11px] font-bold'):
                            ui.label(f'ATK +{atk or 0}').classes('text-amber-800 bg-amber-100 px-2 py-1 rounded')
                            ui.label(f'DEF +{dfs or 0}').classes('text-amber-800 bg-amber-100 px-2 py-1 rounded')
                            ui.label(f'Indemniz. -{formatear_precio_corto(indemnizacion)}').classes('text-rose-700 bg-rose-50 px-2 py-1 rounded')
                        def dar_la_patada(eid=ent_id, indem=indemnizacion):
                            conn2 = obtener_conexion_db()
                            cur2 = conn2.cursor()
                            cur2.execute('SELECT presupuesto_pts FROM equipos WHERE id = ?', (equipo_id,))
                            fondos = cur2.fetchone()[0] or 0
                            if fondos < indem:
                                conn2.close()
                                ui.notify(f'❌ No tienes fondos para la indemnización ({formatear_precio_corto(indem)}).', type='negative')
                                return
                            cur2.execute('UPDATE equipos SET entrenador_id = NULL, presupuesto_pts = presupuesto_pts - ? WHERE id = ?', (indem, equipo_id))
                            conn2.commit()
                            conn2.close()
                            ui.notify(f'👟 Le has dado la patada. Indemnización pagada: {formatear_precio_corto(indem)}.', type='warning')
                            redibujar_entrenadores()
                            refrescar_stats_mercado()
                            callback_refresco_main()
                        ui.button('DALE LA PATADA', on_click=dar_la_patada).props('unelevated rounded size=sm').classes('bg-rose-600 text-white text-[10px] shrink-0')
                else:
                    with ui.row().classes('w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-3 items-center gap-2 mb-4'):
                        ui.icon('sports', color='grey').classes('text-lg')
                        ui.label('Sin entrenador. Aquí se juega al libre albedrío.').classes('text-[11px] italic text-slate-400')

                ui.label('ENTRENADORES DISPONIBLES EN EL MERCADO').classes('text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2')
                if not libres:
                    ui.label('No hay entrenadores libres en este momento.').classes('text-slate-400 italic text-xs py-2')
                else:
                    for ent_id, nombre, mote, atk, dfs, frase, precio_ptas in libres:
                        with ui.row().classes('w-full bg-white border border-slate-100 rounded-xl px-4 py-3 items-center gap-4 mb-1 hover:bg-slate-50'):
                            with ui.column().classes('flex-1 gap-0'):
                                ui.label(nombre.upper()).classes('font-bold text-slate-800 text-sm')
                                if mote:
                                    ui.label(f'"{mote}"').classes('text-[10px] italic text-slate-500')
                                if frase:
                                    ui.label(f'"{frase}"').classes('text-[10px] text-slate-400 italic mt-0.5')
                            with ui.row().classes('gap-3 shrink-0 text-[11px] font-bold'):
                                ui.label(f'ATK +{atk or 0}').classes('text-emerald-700 bg-emerald-50 px-2 py-1 rounded')
                                ui.label(f'DEF +{dfs or 0}').classes('text-blue-700 bg-blue-50 px-2 py-1 rounded')
                                ui.label(formatear_precio_corto(precio_ptas or 0)).classes('text-slate-600 bg-slate-100 px-2 py-1 rounded')
                            def contratar(eid=ent_id, nom=nombre, precio=precio_ptas):
                                conn2 = obtener_conexion_db()
                                cur2 = conn2.cursor()
                                cur2.execute('SELECT entrenador_id, presupuesto_pts FROM equipos WHERE id = ?', (equipo_id,))
                                row = cur2.fetchone()
                                if row and row[0] is not None:
                                    conn2.close()
                                    ui.notify('🐓 Vende a tu entrenador o dale la patada, no puede haber dos gallos en el mismo corral.', type='negative', timeout=5000)
                                    return
                                coste = precio or 0
                                fondos = row[1] if row else 0
                                if fondos < coste:
                                    conn2.close()
                                    ui.notify(f'❌ Fondos insuficientes. Se necesitan {formatear_precio_corto(coste)}.', type='negative')
                                    return
                                cur2.execute('UPDATE equipos SET entrenador_id = ?, presupuesto_pts = presupuesto_pts - ? WHERE id = ?', (eid, coste, equipo_id))
                                conn2.commit()
                                conn2.close()
                                ui.notify(f'✅ {nom} contratado por {formatear_precio_corto(coste)}. A ver qué hace con estos muñones.', type='positive')
                                redibujar_entrenadores()
                                refrescar_stats_mercado()
                                callback_refresco_main()
                            ui.button('CONTRATAR', on_click=contratar).props('unelevated rounded size=sm').classes('bg-slate-900 text-white text-[10px] shrink-0')

        def alternar_pestana(destino):
            btn_compra_tab.classes(replace='bg-slate-200 text-slate-700 text-xs')
            btn_venta_tab.classes(replace='bg-slate-200 text-slate-700 text-xs')
            btn_ent_tab.classes(replace='bg-slate-200 text-slate-700 text-xs')
            panel_compras.classes(add='hidden')
            panel_ventas.classes(add='hidden')
            panel_entrenadores.classes(add='hidden')

            if destino == 'compra':
                btn_compra_tab.classes(replace='bg-slate-900 text-white text-xs')
                panel_compras.classes(remove='hidden')
                redibujar_compras()
            elif destino == 'venta':
                btn_venta_tab.classes(replace='bg-slate-900 text-white text-xs')
                panel_ventas.classes(remove='hidden')
                redibujar_ventas()
            else:
                btn_ent_tab.classes(replace='bg-slate-900 text-white text-xs')
                panel_entrenadores.classes(remove='hidden')
                redibujar_entrenadores()

        btn_compra_tab.on('click', lambda: alternar_pestana('compra'))
        btn_venta_tab.on('click', lambda: alternar_pestana('venta'))
        btn_ent_tab.on('click', lambda: alternar_pestana('entrenador'))

        # Inicialización
        redibujar_compras()
        dialogo.open()
    mostrar_ventana_ofertas(equipo_id, callback_refresco_main)

def simular_movimientos_cpu(mi_equipo_id, jornada):
    """Hace que la CPU compre y venda jugadores automáticamente a partir de la jornada 1."""
    if jornada < 1:
        return  # En pretemporada no se mueve el mercado de la CPU

    conn = obtener_conexion_db()
    cursor = conn.cursor()

    # --- 🛒 FASE 1: LA CPU COMPRA JUGADORES ---
    # La CPU mira los jugadores que otros equipos de la CPU han puesto a la venta
    cursor.execute("""
        SELECT j.id, j.precio_pts, j.equipo_id
        FROM jugadores j
        WHERE j.a_la_venta = 1 AND j.equipo_id != ? AND j.equipo_id IS NOT NULL
    """, (mi_equipo_id,))
    en_venta_cpu = cursor.fetchall()

    for j_id, precio, eq_vendedor_id in en_venta_cpu:
        # Hay un 25% de probabilidad de que un jugador en venta sea comprado por otro club en cada jornada
        if random.random() < 0.25:
            # Buscamos clubes que tengan dinero suficiente (excluyendo al usuario y al vendedor)
            cursor.execute("""
                SELECT id, presupuesto_pts FROM equipos 
                WHERE id != ? AND id != ? AND presupuesto_pts >= ?
            """, (mi_equipo_id, eq_vendedor_id, precio))
            posibles_compradores = cursor.fetchall()
            
            if posibles_compradores:
                comprador = random.choice(posibles_compradores)
                eq_comprador_id = comprador[0]
                
                # Ejecutamos el traspaso
                cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts - ? WHERE id = ?", (precio, eq_comprador_id))
                cursor.execute("UPDATE equipos SET presupuesto_pts = presupuesto_pts + ? WHERE id = ?", (precio, eq_vendedor_id))
                # El jugador cambia de equipo y se retira del mercado
                cursor.execute("UPDATE jugadores SET equipo_id = ?, a_la_venta = 0, titular = 0 WHERE id = ?", (eq_comprador_id, j_id))

    # --- 🏷️ FASE 2: LA CPU PONE JUGADORES A LA VENTA ---
    # Contamos cuántos jugadores de la CPU hay en el mercado actualmente
    cursor.execute("SELECT COUNT(id) FROM jugadores WHERE a_la_venta = 1 AND equipo_id != ?", (mi_equipo_id,))
    total_en_venta = cursor.fetchone()[0]

    huecos_libres = 10 - total_en_venta

    if huecos_libres > 0:
        # Buscamos suplentes sanos de la CPU para ponerlos en el escaparate
        cursor.execute("""
            SELECT id, ataque, defensa, equipo_id
            FROM jugadores
            WHERE equipo_id != ? AND a_la_venta = 0 AND semanas_lesion = 0 AND titular = 0
            ORDER BY RANDOM()
            LIMIT ?
        """, (mi_equipo_id, huecos_libres))
        candidatos = cursor.fetchall()

        for c_id, atk, df, eq_id in candidatos:
            media = ((atk or 0) + (df or 0)) / 2
            
            # Recuperamos su valor original o generamos uno acorde a su calidad
            cursor.execute("SELECT precio_pts FROM jugadores WHERE id = ?", (c_id,))
            res_precio = cursor.fetchone()
            precio_base = res_precio[0] if res_precio and res_precio[0] > 0 else max(500000, int(media * 85000))

            # Los clubes le aplican un factor de inflación al ponerlo a la venta (entre un 90% y un 130% de su valor)
            precio_venta = int(precio_base * random.uniform(0.9, 1.3))

            cursor.execute("UPDATE jugadores SET a_la_venta = 1, precio_pts = ? WHERE id = ?", (precio_venta, c_id))

    conn.commit()
    conn.close()


def simular_movimientos_cpu_entrenadores(mi_equipo_id, jornada):
    """Mueve entrenadores entre equipos CPU (~15 cambios por temporada de 22 jornadas)."""
    if jornada < 1:
        return

    # P_DESPIDO por equipo ~0.10 → en 22 jornadas × 11 equipos ≈ 24 eventos de despido máx
    # P_FICHAJE por equipo sin entrenador ~0.50 → los huecos se cubren rápido
    P_DESPIDO = 0.10
    P_FICHAJE = 0.50

    conn = obtener_conexion_db()
    cursor = conn.cursor()

    # --- FASE 1: DESPIDOS —equipos CPU con entrenador pueden echarlo ---
    cursor.execute(
        "SELECT id FROM equipos WHERE id != ? AND entrenador_id IS NOT NULL",
        (mi_equipo_id,)
    )
    equipos_con_ent = [r[0] for r in cursor.fetchall()]

    for eq_id in equipos_con_ent:
        if random.random() < P_DESPIDO:
            cursor.execute("UPDATE equipos SET entrenador_id = NULL WHERE id = ?", (eq_id,))

    # --- FASE 2: FICHAJES — equipos CPU sin entrenador contratan uno libre ---
    cursor.execute(
        "SELECT id FROM equipos WHERE id != ? AND entrenador_id IS NULL",
        (mi_equipo_id,)
    )
    equipos_sin_ent = [r[0] for r in cursor.fetchall()]

    for eq_id in equipos_sin_ent:
        if random.random() < P_FICHAJE:
            cursor.execute("""
                SELECT id FROM entrenadores
                WHERE id NOT IN (
                    SELECT entrenador_id FROM equipos WHERE entrenador_id IS NOT NULL
                )
                ORDER BY RANDOM() LIMIT 1
            """)
            libre = cursor.fetchone()
            if libre:
                cursor.execute(
                    "UPDATE equipos SET entrenador_id = ? WHERE id = ?",
                    (libre[0], eq_id)
                )

    conn.commit()
    conn.close()