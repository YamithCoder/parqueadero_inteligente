"""
metricas.py

Módulo de métricas, logs y exportación de datos del simulador.

Registra cada evento del parqueadero en:
  - Log en memoria (para la GUI)
  - Archivo .log en disco
  - Archivo .csv para análisis posterior

Universidad EAN · Arquitectura de Computadores y Sistemas Operativos
"""

import csv
import os
import time
import threading
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


#  CONFIGURACIÓN
DIRECTORIO_LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
MAX_LOG_MEMORIA = 500   # Máximo de entradas en memoria para la GUI



#  MODELO DE ENTRADA DE LOG
@dataclass
class EntradaLog:
    """Representa un evento registrado en el sistema."""
    timestamp:  float
    tipo:       str          # vehiculo_nuevo | ingreso | salida | espera | timeout | sistema
    nivel:      str          # info | warning | error | success
    mensaje:    str
    vehiculo_id:    Optional[int]   = None
    vehiculo_tipo:  Optional[str]   = None
    espacios_libres: Optional[int]  = None
    tiempo_espera:  Optional[float] = None
    tiempo_estacion: Optional[float] = None

    @property
    def hora_formateada(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def fila_csv(self) -> list:
        return [
            self.hora_formateada,
            self.tipo,
            self.nivel,
            self.vehiculo_id or "",
            self.vehiculo_tipo or "",
            self.espacios_libres if self.espacios_libres is not None else "",
            self.tiempo_espera or "",
            self.tiempo_estacion or "",
            self.mensaje,
        ]


#  GESTOR DE MÉTRICAS
class GestorMetricas:
    """
    Registra, almacena y exporta métricas del simulador.

    Thread-safe: usa Lock interno para proteger escrituras concurrentes.
    La GUI puede leer el log en cualquier momento sin condiciones de carrera.
    """

    CABECERA_CSV = [
        "hora", "tipo", "nivel", "vehiculo_id", "vehiculo_tipo",
        "espacios_libres", "tiempo_espera_s", "tiempo_estacion_s", "mensaje"
    ]

    def __init__(self, nombre_sesion: Optional[str] = None):
        self._lock = threading.Lock()  # Protege acceso concurrente al log

        # Nombre de sesión para archivos
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.nombre_sesion = nombre_sesion or f"sesion_{ts}"

        # Asegurar que el directorio de logs existe
        os.makedirs(DIRECTORIO_LOGS, exist_ok=True)

        self._ruta_log = os.path.join(DIRECTORIO_LOGS, f"{self.nombre_sesion}.log")
        self._ruta_csv = os.path.join(DIRECTORIO_LOGS, f"{self.nombre_sesion}.csv")

        # Log en memoria (máximo MAX_LOG_MEMORIA entradas)
        self._entradas: list[EntradaLog] = []

        # Contadores para estadísticas rápidas
        self._contadores = {
            "ingresos":  0,
            "salidas":   0,
            "timeouts":  0,
            "esperas":   0,
        }

        # Inicializar CSV con cabecera
        self._inicializar_csv()
        self.registrar("sistema", "info", "📋 Gestor de métricas iniciado")

    def _inicializar_csv(self):
        """Crea el archivo CSV con cabecera."""
        try:
            with open(self._ruta_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CABECERA_CSV)
        except OSError:
            pass  # Si no se puede crear, continuar sin CSV

    def registrar(self, tipo: str, nivel: str, mensaje: str,
                  vehiculo_id: Optional[int] = None,
                  vehiculo_tipo: Optional[str] = None,
                  espacios_libres: Optional[int] = None,
                  tiempo_espera: Optional[float] = None,
                  tiempo_estacion: Optional[float] = None):
        """
        Registra un evento en memoria, en el archivo .log y en el CSV.
        Thread-safe gracias al Lock interno.
        """
        entrada = EntradaLog(
            timestamp=time.time(),
            tipo=tipo,
            nivel=nivel,
            mensaje=mensaje,
            vehiculo_id=vehiculo_id,
            vehiculo_tipo=vehiculo_tipo,
            espacios_libres=espacios_libres,
            tiempo_espera=tiempo_espera,
            tiempo_estacion=tiempo_estacion,
        )

        with self._lock:
            # Mantener tamaño máximo en memoria
            if len(self._entradas) >= MAX_LOG_MEMORIA:
                self._entradas.pop(0)
            self._entradas.append(entrada)

            # Actualizar contadores
            if tipo == "ingreso":
                self._contadores["ingresos"] += 1
            elif tipo == "salida":
                self._contadores["salidas"] += 1
            elif tipo == "timeout":
                self._contadores["timeouts"] += 1
            elif tipo == "espera":
                self._contadores["esperas"] += 1

        # Escribir en archivos (fuera del lock para no bloquear)
        self._escribir_log(entrada)
        self._escribir_csv(entrada)

    def registrar_desde_evento(self, evento: dict):
        """
        Convierte un evento de la cola del simulador en entrada de log.
        Facilita la integración con SimuladorParqueadero.
        """
        v = evento.get("vehiculo")
        self.registrar(
            tipo=evento.get("tipo", "sistema"),
            nivel=evento.get("nivel", "info"),
            mensaje=evento.get("mensaje", ""),
            vehiculo_id=v.id if v else None,
            vehiculo_tipo=v.tipo.etiqueta if v else None,
            espacios_libres=evento.get("libres"),
            tiempo_espera=v.tiempo_espera if v else None,
            tiempo_estacion=v.tiempo_estacionado if v else None,
        )

    def _escribir_log(self, entrada: EntradaLog):
        """Escribe una línea en el archivo .log."""
        try:
            linea = f"[{entrada.hora_formateada}] [{entrada.nivel.upper():7s}] {entrada.mensaje}\n"
            with open(self._ruta_log, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError:
            pass

    def _escribir_csv(self, entrada: EntradaLog):
        """Escribe una fila en el archivo CSV."""
        try:
            with open(self._ruta_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(entrada.fila_csv)
        except OSError:
            pass

    
    #  CONSULTAS THREAD-SAFE
    def obtener_log_reciente(self, n: int = 50) -> list[EntradaLog]:
        """Retorna las últimas N entradas del log."""
        with self._lock:
            return list(self._entradas[-n:])

    def obtener_resumen(self) -> dict:
        """Retorna un resumen estadístico de la sesión."""
        with self._lock:
            total = self._contadores["ingresos"]
            return {
                "sesion":           self.nombre_sesion,
                "total_ingresos":   self._contadores["ingresos"],
                "total_salidas":    self._contadores["salidas"],
                "total_timeouts":   self._contadores["timeouts"],
                "total_esperas":    self._contadores["esperas"],
                "tasa_exito_pct":   round((total / max(total + self._contadores["timeouts"], 1)) * 100, 1),
                "ruta_log":         self._ruta_log,
                "ruta_csv":         self._ruta_csv,
            }

    def exportar_csv_manual(self, ruta_destino: str) -> bool:
        """Exporta el CSV actual a una ruta personalizada."""
        try:
            import shutil
            shutil.copy2(self._ruta_csv, ruta_destino)
            return True
        except OSError:
            return False

    def limpiar(self):
        """Limpia el log en memoria (sin borrar archivos)."""
        with self._lock:
            self._entradas.clear()
            for k in self._contadores:
                self._contadores[k] = 0
