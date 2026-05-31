from nicegui import ui

# Catálogo oficial de colores y estilos para los 12 equipos de Elche
PALETA_ESCUDOS = {
    1:  {"primario": "bg-white",     "secundario": "bg-black",       "patron": "franjas_v", "borde": "border-zinc-400"},  # San Antón Spurs
    2:  {"primario": "bg-red-600",   "secundario": "bg-white",       "patron": "franja_d",  "borde": "border-red-800"},   # Rayo Carrusano
    3:  {"primario": "bg-blue-600",  "secundario": "bg-white",       "patron": "franjas_v", "borde": "border-blue-900"},  # Espanyol de Plaza Barcelona
    4:  {"primario": "bg-zinc-800",  "secundario": "bg-red-600",     "patron": "mitad_h",   "borde": "border-black"},     # Toscar de Belgrado
    5:  {"primario": "bg-green-600", "secundario": "bg-white",       "patron": "cuadros",   "borde": "border-green-800"},  # Pedro Ibarra Muñonpié
    6:  {"primario": "bg-yellow-500","secundario": "bg-black",       "patron": "mitad_v",   "borde": "border-yellow-600"}, # Garden City
    7:  {"primario": "bg-blue-800",  "secundario": "bg-yellow-500",  "patron": "franja_d",  "borde": "border-blue-950"},  # Prada y Marcos
    8:  {"primario": "bg-purple-700","secundario": "bg-white",       "patron": "mitad_h",   "borde": "border-purple-900"}, # Internit del Albà
    9:  {"primario": "bg-orange-600","secundario": "bg-zinc-900",    "patron": "franjas_v", "borde": "border-orange-700"}, # Matola City
    10: {"primario": "bg-blue-700",  "secundario": "bg-black",       "patron": "cuadros",   "borde": "border-blue-900"},  # Inter de Algoda
    11: {"primario": "bg-red-600",   "secundario": "bg-blue-600",     "patron": "mitad_v",   "borde": "border-red-800"},   # Asprillas United
    12: {"primario": "bg-yellow-400","secundario": "bg-purple-800",  "patron": "franjas_v", "borde": "border-yellow-600"},  # Los Arenals Lakers
    13: {"primario": "bg-emerald-600", "secundario": "bg-yellow-400", "patron": "franja_d",  "borde": "border-emerald-800"},
    14: {"primario": "bg-cyan-500",    "secundario": "bg-slate-900",  "patron": "mitad_h",   "borde": "border-cyan-700"},
    15: {"primario": "bg-rose-600",    "secundario": "bg-white",      "patron": "cuadros",   "borde": "border-rose-900"},
    16: {"primario": "bg-amber-500",   "secundario": "bg-teal-700",   "patron": "franjas_v", "borde": "border-amber-700"},
    17: {"primario": "bg-violet-600",  "secundario": "bg-orange-500", "patron": "mitad_v",   "borde": "border-violet-800"},
    18: {"primario": "bg-indigo-600",  "secundario": "bg-pink-500",   "patron": "franja_d",  "borde": "border-indigo-800"},
    19: {"primario": "bg-fuchsia-600", "secundario": "bg-cyan-400",   "patron": "mitad_h",   "borde": "border-fuchsia-800"},
}

def pintar_escudo(equipo_id: int, tamaño: str = "w-10 h-12"):
    """Dibuja un escudo retro con formas geométricas de Tailwind según el club."""
    estilo = PALETA_ESCUDOS.get(equipo_id, {"primario": "bg-zinc-700", "secundario": "bg-zinc-600", "patron": "liso", "borde": "border-zinc-800"})
    
    p = estilo["primario"]
    s = estilo["secundario"]
    b = estilo["borde"]
    patron = estilo["patron"]
    
    # El contenedor base con forma de blasón/escudo clásico redondeado por abajo
    with ui.element('div').classes(f'{tamaño} {p} border-2 {b} rounded-b-xl relative overflow-hidden shadow-md flex items-center justify-center'):
        
        if patron == "franjas_v":
            # Tres franjas verticales simétricas
            ui.element('div').classes(f'w-1/3 h-full {s} absolute left-1/3')
            
        elif patron == "mitad_h":
            # Dividido por la mitad horizontalmente
            ui.element('div').classes(f'w-full h-1/2 {s} absolute bottom-0')
            
        elif patron == "mitad_v":
            # Dividido por la mitad verticalmente
            ui.element('div').classes(f'w-1/2 h-full {s} absolute right-0')
            
        elif patron == "franja_d":
            # Franja diagonal clásica (estilo River/Rayo) rota a 45 grados
            ui.element('div').classes(f'w-32 h-4 {s} absolute rotate-45 transform')
            
        elif patron == "cuadros":
            # Patrón de cuatro cuadrantes ajedrezados
            ui.element('div').classes(f'w-1/2 h-1/2 {s} absolute top-0 left-0')
            ui.element('div').classes(f'w-1/2 h-1/2 {s} absolute bottom-0 right-0')
            
        # El remache central: un pequeño punto pixelado en el corazón del escudo para darle carácter
        ui.element('div').classes('w-2 h-2 bg-yellow-400 rounded-full border border-black z-10 opacity-80')