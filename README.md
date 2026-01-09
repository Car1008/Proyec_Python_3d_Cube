# Proyec_Python_3d_Cube

Simulador 3D de Cubo Rubik desarrollado en Python para el ramo **Python Científico**.  
Incluye render 3D, animaciones, interacción, historial (Undo/Redo), mezcla (Scramble) y resolución básica por búsqueda (IDDFS) con feedback al usuario.

---

## Características
- ✅ Visualización 3D del cubo con stickers 3x3 por cara
- ✅ Movimientos animados (capas del cubo)
- ✅ Interacción desde GUI (botones + secuencias de texto)
- ✅ Historial de movimientos + Undo / Redo
- ✅ Scramble configurable
- ✅ Solver básico IDDFS:
  - **Buscar solución**: muestra pasos encontrados
  - **Solve (auto)**: busca y aplica automáticamente
  - **Cancelar búsqueda**: detiene búsquedas en curso
- ✅ Pruebas unitarias (tests) y documentación del proyecto

> Nota: El solver IDDFS está pensado para **mezclas cortas** (ej. 3–8 movimientos).  
> Para mezclas largas (20+), puede no encontrar solución dentro del límite de profundidad.

---

rubik_sim/
  app/         # GUI (MainWindow), workers/hilos
  core/        # Modelo lógico (CubeModel)
  logic/       # Utilidades (parse movimientos, scramble, inversos)
  render/      # Render 3D y animación (OpenGL widget)
  solve/       # Algoritmos de resolución (IDDFS)
  tests/       # Pruebas unitarias
doc/           # Documentación (instalación, testing, arquitectura)
main.py        # Punto de entrada
requirements.txt

---

## Requisitos
- Python 3.10+ (recomendado 3.11)
- PySide6
- PyOpenGL
- numpy

---

## Instalación (Windows / PowerShell)

# 1) Crear entorno virtual:
# ```powershell
python -m venv .venv

# 2) Activar entorno virtual:
# ```powershellG
.\.venv\Scripts\Activate.ps1

# 2.5)Si aparece un error de políticas de ejecución, ejecutar una vez:
 Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

--- luego, repetir paso #2)

# 3) Instalar dependencias:
# (.venv)
python -m pip install --upgrade pip
pip install -r requirements.txt


# 4) Tests:
# (.venv) 
python -m unittest discover -s rubik_sim/tests -p "test_*.py" -v

# 5) Ejecutar programa:
# (.venv) 
python main.py

