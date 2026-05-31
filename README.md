# munonbol

## Ejecutar en local

1. Crea y activa un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows:

```bat
py -m venv .venv
.venv\Scripts\activate
```

2. Instala la dependencia principal:

```bash
pip install nicegui
```

3. Si necesitas recrear la base de datos desde cero, ejecuta:

```bash
python inicializar_banco_datos.py
```

4. Arranca la aplicación:

```bash
python main.py
```

5. Abre el navegador en:

```text
http://localhost:8080
```

### Notas

- Ejecuta los comandos desde la raíz del proyecto.
- La partida activa usa `munonbol_partida.db` si existe; si quieres empezar de cero, elimínala antes de lanzar la app.
- La base de datos principal es `munonbol_elche_95.db`.
