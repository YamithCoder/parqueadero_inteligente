"""
main.py
=======
Punto de entrada del Simulador de Parqueadero Inteligente.

Uso:
    python main.py

Universidad EAN - Arquitectura de Computadores y Sistemas Operativos
Docente: Diana Carolina Beltrán Peña
"""

import sys
import os

# Agregar la carpeta actual al path para que Python encuentre los modulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import AppParqueadero


def main():
    """Lanza la aplicacion grafica."""
    app = AppParqueadero()
    app.mainloop()


if __name__ == "__main__":
    main()
