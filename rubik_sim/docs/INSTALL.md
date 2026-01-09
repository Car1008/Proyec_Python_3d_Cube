# Instalación y ejecución (Windows / VSCode)

## Requisitos
- Python 3.10+ (recomendado 3.11)
- Git (opcional, para control de versiones)
- VSCode (opcional)

## 1) Clonar / abrir el proyecto
# Si usas Git:
# ```bash
git clone <https://github.com/Car1008/Proyec_Python_3d_Cube.git>
cd Proyec_Python_3d_Cube


## 1) Crear entorno virtual
En PowerShell dentro de la carpeta del proyecto:
-->   python -m venv .venv

## 3) Activar entorno virtual
PowerShell:
--> .\.venv\Scripts\Activate.ps1

## 4) Instalar dependencias
Con el entorno virtual activado:
# (.venv)
python -m pip install --upgrade pip
pip install -r requirements.txt

## 5) Ejecutar el simulador
python main.py

## 6) (Opcional) Ejecutar tests
python -m unittest discover -s rubik_sim/tests -p "test_*.py" -v