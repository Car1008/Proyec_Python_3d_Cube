# Arquitectura del proyecto

Este proyecto implementa un simulador 3D de Cubo Rubik en Python, separando responsabilidades en módulos para facilitar mantenimiento, pruebas y extensiones.

## Estructura de carpetas

rubik_sim/
    app/ # GUI (ventana principal), workers/hilos, control de interacción
    core/ # Modelo lógico del cubo (estado y reglas base)
    logic/ # Utilidades: parsing de movimientos, scramble, validaciones
    render/ # Render 3D y animación (OpenGL + PySide6)
    solve/ # Algoritmos de resolución (ej: IDDFS)
    tests/ # Pruebas unitarias
doc/ # Documentación del proyecto (instalación, testing, arquitectura)
main.py # Punto de entrada de la aplicación
requirements.txt # Dependencias 


###### Más en detalle:######


## Módulos principales (dentro de rubik_sim/):

### `core/` (modelo lógico)
- `CubeModel`: representa el estado del cubo (stickers por cara) y aplica movimientos.
- Contiene funciones como:
  - `apply_move(move)`
  - `apply_sequence(seq)`
  - `is_solved()`
  - `reset()`

### `render/` (visualización)
- `CubeGLWidget`: dibuja el cubo en 3D (stickers 3x3 por cara) y gestiona animaciones.
- Emite señal `move_applied(move)` al finalizar una animación (para sincronizar GUI e historial).

### `app/` (interfaz y control)
- `MainWindow`: contiene botones (Scramble, Apply, Undo/Redo, Solve, etc.) y coordina módulos.
- `SolveWorker`: ejecuta búsqueda del solver en un hilo (QThread) para no congelar la GUI.
- Incluye cancelación segura de búsqueda.

### `logic/` (utilidades)
- `moves.py`: normaliza tokens (`D2' -> D2`), valida, parsea secuencias, calcula inversos.
- `scramble.py`: genera secuencias de mezclado evitando repetir la misma cara.

### `solve/` (resolución)
- `iddfs_solver.py`: solver básico por búsqueda IDDFS (Iterative Deepening DFS).
  - Diseñado para resolver mezclas cortas (ej: 3–6 movimientos).
  - Incluye feedback por profundidad y cancelación.

###### Comunicación entre módulos (flujo) ######
1. El usuario interactúa en GUI (`MainWindow`) o arrastra una capa en `CubeGLWidget`.
2. `CubeGLWidget` anima el movimiento y al final:
   - aplica el movimiento al `CubeModel`
   - emite `move_applied(move)`
3. `MainWindow` recibe la señal y:
   - actualiza historial
   - actualiza estado (resuelto/mezclado)
   - habilita/deshabilita botones

###### Decisiones de diseño ######
- Separación “modelo / vista / control”:
  - `CubeModel` no depende de OpenGL ni de la GUI.
  - `CubeGLWidget` no implementa “resolver”; solo render/animación.
  - `MainWindow` coordina la interacción y el flujo de la app.
- Uso de QThread para el solver:
  - evita congelamiento de la interfaz durante búsquedas.
