"""
simulador.py
============
Núcleo del Simulador de Parqueadero Inteligente.

Analogía con Sistemas Operativos:
  - Vehículo     → Proceso
  - Espacio      → Recurso (CPU / memoria)
  - Semáforo     → Planificador de acceso a recursos
  - Lock         → Exclusión mutua (sección crítica)
  - Event        → Señal de control del SO (interrupciones / shutdown)

Universidad EAN · Arquitectura de Computadores y Sistemas Operativos
Docente: Diana Carolina Beltrán Peña
"""

import threading
import time
import random
import queue
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────
random.seed(42)          # Reproducibilidad de resultados

CAPACIDAD_DEFAULT     = 6   # Espacios totales del parqueadero
TIEMPO_MIN_ESPERA     = 1   # Segundos minimos antes de intentar entrar
TIEMPO_MAX_ESPERA     = 2   # Segundos maximos antes de intentar entrar
TIEMPO_MIN_ESTACION   = 10  # Segundos minimos estacionado
TIEMPO_MAX_ESTACION   = 20  # Segundos maximos estacionado
TIMEOUT_INGRESO       = 25  # Segundos maximos esperando un cupo
MAX_VEHICULOS_ACTIVOS = 12  # Maximo hilos activos simultaneos


# ─────────────────────────────────────────────
#  ENUMERACIONES
# ─────────────────────────────────────────────
class EstadoVehiculo(Enum):
    """
    Ciclo de vida del vehículo (análogo al ciclo de vida de un proceso en SO).
    ESPERANDO_LLEGADA → ESPERANDO_CUPO → ESTACIONADO → SALIENDO → FINALIZADO / TIMEOUT
    """
    ESPERANDO_LLEGADA = "En camino"
    ESPERANDO_CUPO    = "Esperando cupo"
    ESTACIONADO       = "Estacionado"
    SALIENDO          = "Saliendo"
    FINALIZADO        = "Finalizado"
    TIMEOUT           = "Sin cupo (timeout)"


class TipoVehiculo(Enum):
    """
    Tipos de vehículos del parqueadero.
    DISCAPACIDAD tiene prioridad sobre NORMAL
    (análogo a prioridad de procesos en SO).
    """
    DISCAPACIDAD = ("Discapacidad", 1)
    NORMAL       = ("Normal",       2)

    def __init__(self, etiqueta: str, prioridad: int):
        self.etiqueta  = etiqueta
        self.prioridad = prioridad


# ─────────────────────────────────────────────
#  MODELO DE VEHÍCULO
# ─────────────────────────────────────────────
@dataclass
class Vehiculo:
    """
    Representa un vehículo (proceso) en el simulador.
    Cada instancia corre en su propio hilo de threading.
    """
    id:         int
    tipo:       TipoVehiculo
    tiempo_llegada:    float = field(default_factory=time.time)
    tiempo_ingreso:    Optional[float] = None
    tiempo_salida:     Optional[float] = None
    estado:            EstadoVehiculo = EstadoVehiculo.ESPERANDO_LLEGADA
    espacio_asignado:  Optional[int]  = None

    # ── Métricas individuales ──────────────────
    @property
    def tiempo_espera(self) -> float:
        """Tiempo que el vehículo esperó un cupo disponible (en segundos)."""
        if self.tiempo_ingreso:
            return round(self.tiempo_ingreso - self.tiempo_llegada, 2)
        return 0.0

    @property
    def tiempo_estacionado(self) -> float:
        """Tiempo total que el vehículo ocupó el espacio."""
        if self.tiempo_ingreso and self.tiempo_salida:
            return round(self.tiempo_salida - self.tiempo_ingreso, 2)
        return 0.0

    def __str__(self) -> str:
        return f"V{self.id:03d} [{self.tipo.etiqueta}] → {self.estado.value}"


# ─────────────────────────────────────────────
#  NÚCLEO DEL SIMULADOR
# ─────────────────────────────────────────────
class SimuladorParqueadero:
    """
    Gestiona la simulación concurrente del parqueadero.

    Mecanismos de sincronización utilizados:
      - threading.Semaphore : controla los cupos disponibles (planificador de recursos)
      - threading.Lock      : protege variables compartidas (exclusión mutua)
      - threading.Event     : señal de parada / control del ciclo de vida (interrupción SO)
      - queue.Queue         : comunicación segura hilo → GUI (sin actualizar widgets desde hilos)
    """

    def __init__(self, capacidad: int = CAPACIDAD_DEFAULT):
        self.capacidad = capacidad

        # ── Primitivas de sincronización ──────────────────────────────────
        # SEMÁFORO: controla acceso al parqueadero (análogo al planificador del SO)
        # Inicializado con `capacidad` → permite N vehículos simultáneos
        self._semaforo = threading.Semaphore(capacidad)

        # LOCK: protege variables compartidas (espacios_ocupados, lista de vehículos)
        # Solo un hilo puede modificar el estado a la vez → exclusión mutua
        self._lock = threading.Lock()

        # EVENT: señal de apagado del sistema
        # Cuando se activa, todos los hilos deben terminar ordenadamente
        self._evento_parada = threading.Event()

        # EVENT: señal de pausa (simula suspensión de procesos)
        self._evento_pausa = threading.Event()
        self._evento_pausa.set()  # Inicia sin pausa

        # ── Estado compartido (protegido por _lock) ───────────────────────
        self._espacios_ocupados: int = 0
        self._espacios_estado: list[Optional[int]] = [None] * capacidad  # None=libre, int=id vehículo
        self._vehiculos: dict[int, Vehiculo] = {}
        self._contador_id: int = 0
        self._hilos_activos: list[threading.Thread] = []

        # ── Cola de eventos para la GUI ────────────────────────────────────
        # Los hilos secundarios NUNCA deben tocar widgets Tkinter directamente
        # En su lugar, ponen eventos en esta cola que la GUI consume con .after()
        self.cola_eventos: queue.Queue = queue.Queue()

        # ── Métricas globales ──────────────────────────────────────────────
        self._total_vehiculos_procesados: int = 0
        self._total_vehiculos_timeout:    int = 0
        self._suma_tiempos_espera:        float = 0.0
        self._suma_tiempos_estacion:      float = 0.0

    # ─────────────────────────────────────────
    #  PROPIEDADES DE SOLO LECTURA
    # ─────────────────────────────────────────
    @property
    def espacios_libres(self) -> int:
        return self.capacidad - self._espacios_ocupados

    @property
    def espacios_ocupados(self) -> int:
        return self._espacios_ocupados

    @property
    def esta_activo(self) -> bool:
        return not self._evento_parada.is_set()

    @property
    def esta_pausado(self) -> bool:
        return not self._evento_pausa.is_set()

    @property
    def vehiculos_activos(self) -> dict:
        """Solo vehiculos en estados activos — la GUI no necesita los finalizados."""
        estados_activos = {
            EstadoVehiculo.ESPERANDO_LLEGADA, EstadoVehiculo.ESPERANDO_CUPO,
            EstadoVehiculo.ESTACIONADO,       EstadoVehiculo.SALIENDO,
        }
        with self._lock:
            return {k: v for k, v in self._vehiculos.items()
                    if v.estado in estados_activos}

    @property
    def estado_espacios(self) -> list:
        with self._lock:
            return list(self._espacios_estado)

    def snapshot_gui(self) -> dict:
        """
        UN SOLO Lock para todo lo que necesita la GUI por ciclo.
        Evitar multiples adquisiciones de Lock cada 100ms.
        """
        estados_activos = {
            EstadoVehiculo.ESPERANDO_LLEGADA, EstadoVehiculo.ESPERANDO_CUPO,
            EstadoVehiculo.ESTACIONADO,       EstadoVehiculo.SALIENDO,
        }
        with self._lock:
            p = self._total_vehiculos_procesados
            return {
                "espacios":      list(self._espacios_estado),
                "vehiculos":     {k: v for k, v in self._vehiculos.items()
                                  if v.estado in estados_activos},
                "ocupados":      self._espacios_ocupados,
                "libres":        self.capacidad - self._espacios_ocupados,
                "utilizacion":   round((self._espacios_ocupados / self.capacidad) * 100, 1),
                "creados":       self._contador_id,
                "procesados":    p,
                "timeout":       self._total_vehiculos_timeout,
                "espera_prom":   round(self._suma_tiempos_espera   / p, 2) if p else 0.0,
                "estacion_prom": round(self._suma_tiempos_estacion / p, 2) if p else 0.0,
            }

    # ─────────────────────────────────────────
    #  MÉTODOS DE CONTROL
    # ─────────────────────────────────────────
    def iniciar(self):
        """Inicia el simulador limpiando el evento de parada."""
        self._evento_parada.clear()
        self._evento_pausa.set()
        self._emitir_evento("sistema", "Simulador iniciado", "info")

    def detener(self):
        """
        Detiene el simulador de forma ordenada.
        Activa el evento de parada → todos los hilos verifican este flag
        y terminan en su próxima iteración. (Análogo a SIGTERM en SO)
        """
        self._evento_parada.set()
        self._evento_pausa.set()  # Desbloquear si estaba pausado
        self._emitir_evento("sistema", "Simulador detenido", "warning")

    def pausar(self):
        """Pausa todos los hilos (análogo a suspensión de procesos)."""
        self._evento_pausa.clear()
        self._emitir_evento("sistema", "Simulador pausado", "warning")

    def reanudar(self):
        """Reanuda los hilos pausados."""
        self._evento_pausa.set()
        self._emitir_evento("sistema", "Simulador reanudado", "info")

    def reiniciar(self, nueva_capacidad: Optional[int] = None):
        """Reinicia el simulador completamente."""
        self.detener()
        time.sleep(0.5)  # Dar tiempo a los hilos para terminar

        # Esperar que todos los hilos terminen
        for hilo in self._hilos_activos:
            hilo.join(timeout=2)

        cap = nueva_capacidad or self.capacidad
        self.__init__(cap)
        self._emitir_evento("sistema", "Simulador reiniciado", "info")

    # ─────────────────────────────────────────
    #  AGREGAR VEHÍCULOS
    # ─────────────────────────────────────────
    def agregar_vehiculo(self, tipo: TipoVehiculo = None) -> Optional[Vehiculo]:
        """
        Crea un nuevo vehículo y lanza su hilo de ejecución.

        Analogía SO:
          Crear un vehículo = fork() / crear nuevo proceso
          Lanzar el hilo    = scheduler admite el proceso a la cola de listos
        """
        if not self.esta_activo:
            return None

        # Limite de hilos activos para no saturar el sistema
        with self._lock:
            activos = sum(1 for v in self._vehiculos.values()
                         if v.estado.value not in ("Finalizado", "Sin cupo (timeout)"))
            if activos >= MAX_VEHICULOS_ACTIVOS:
                return None

        if tipo is None:
            # 85% Normal, 15% Discapacidad
            tipo = random.choices(
                [TipoVehiculo.NORMAL, TipoVehiculo.DISCAPACIDAD],
                weights=[85, 15]
            )[0]

        with self._lock:
            self._contador_id += 1
            vid = self._contador_id
            vehiculo = Vehiculo(id=vid, tipo=tipo)
            self._vehiculos[vid] = vehiculo

        # Lanzar hilo del vehículo (análogo a admitir proceso al sistema)
        hilo = threading.Thread(
            target=self._ciclo_vehiculo,
            args=(vehiculo,),
            name=f"Vehiculo-{vid}",
            daemon=True  # Se cierra automáticamente si el programa termina
        )
        self._hilos_activos.append(hilo)
        hilo.start()

        self._emitir_evento("vehiculo_nuevo", f"{vehiculo} creado", "info", vehiculo)
        return vehiculo

    def agregar_lote(self, cantidad: int):
        """Agrega múltiples vehículos con pequeño delay entre ellos."""
        def _lanzar():
            for _ in range(cantidad):
                if not self.esta_activo:
                    break
                self.agregar_vehiculo()
                time.sleep(random.uniform(0.3, 1.2))

        hilo = threading.Thread(target=_lanzar, daemon=True)
        hilo.start()

    # ─────────────────────────────────────────
    #  CICLO DE VIDA DEL VEHÍCULO (HILO)
    # ─────────────────────────────────────────
    def _ciclo_vehiculo(self, v: Vehiculo):
        """
        Ciclo de vida completo de un vehículo en su propio hilo.

        Fases (análogo al ciclo de vida de un proceso):
          1. ESPERANDO_LLEGADA → simula tiempo en tránsito
          2. ESPERANDO_CUPO    → bloqueado esperando recurso (semáforo)
          3. ESTACIONADO       → usando el recurso (en ejecución)
          4. SALIENDO          → liberando el recurso
          5. FINALIZADO        → proceso terminado

        ⚠️ SECCIÓN CRÍTICA: modificación de _espacios_ocupados protegida con Lock
        """

        # ── FASE 1: En camino ──────────────────────────────────────────────
        self._actualizar_estado(v, EstadoVehiculo.ESPERANDO_LLEGADA)

        # Discapacidad tiene prioridad → llega antes (factor menor)
        factor_llegada = {
            TipoVehiculo.DISCAPACIDAD: 0.5,
            TipoVehiculo.NORMAL:       1.0
        }[v.tipo]
        tiempo_llegada = random.uniform(TIEMPO_MIN_ESPERA, TIEMPO_MAX_ESPERA) * factor_llegada
        self._esperar_interruptible(tiempo_llegada)

        if not self.esta_activo:
            return

        # ── FASE 2: Esperando cupo ─────────────────────────────────────────
        self._actualizar_estado(v, EstadoVehiculo.ESPERANDO_CUPO)
        v.tiempo_llegada = time.time()  # Registrar tiempo real de espera
        self._emitir_evento("espera", f"V{v.id:03d} esperando cupo...", "warning", v)

        # SEMÁFORO: acquire() bloquea si no hay cupos (planificador del SO)
        # timeout evita espera infinita → previene deadlock
        adquirido = self._semaforo.acquire(timeout=TIMEOUT_INGRESO)

        if not self.esta_activo:
            if adquirido:
                self._semaforo.release()
            return

        if not adquirido:
            # Timeout: el vehículo se va sin estacionarse
            self._actualizar_estado(v, EstadoVehiculo.TIMEOUT)
            with self._lock:
                self._total_vehiculos_timeout += 1
            self._emitir_evento("timeout", f"V{v.id:03d} sin cupo - timeout", "error", v)
            return

        # ── FASE 3: Ingresar al parqueadero ───────────────────────────────
        v.tiempo_ingreso = time.time()

        # LOCK: sección crítica — solo un hilo modifica _espacios_ocupados
        with self._lock:
            self._espacios_ocupados += 1
            # Asignar espacio físico
            for i, ocupante in enumerate(self._espacios_estado):
                if ocupante is None:
                    self._espacios_estado[i] = v.id
                    v.espacio_asignado = i + 1
                    break

        self._actualizar_estado(v, EstadoVehiculo.ESTACIONADO)
        self._emitir_evento(
            "ingreso",
            f"V{v.id:03d} ingreso -> Espacio #{v.espacio_asignado} "
            f"| Espera: {v.tiempo_espera}s",
            "success", v
        )

        # ── FASE 4: Estacionado (usando el recurso) ────────────────────────
        tiempo_estacion = random.uniform(TIEMPO_MIN_ESTACION, TIEMPO_MAX_ESTACION)
        self._esperar_interruptible(tiempo_estacion)

        # ── FASE 5: Salir y liberar recurso ───────────────────────────────
        self._actualizar_estado(v, EstadoVehiculo.SALIENDO)
        v.tiempo_salida = time.time()

        # LOCK: sección crítica — liberar espacio físico
        with self._lock:
            self._espacios_ocupados -= 1
            if v.espacio_asignado:
                self._espacios_estado[v.espacio_asignado - 1] = None
            self._total_vehiculos_procesados += 1
            self._suma_tiempos_espera   += v.tiempo_espera
            self._suma_tiempos_estacion += v.tiempo_estacionado

        # SEMÁFORO: release() — libera el cupo para el siguiente vehículo
        # (análogo a process exit → scheduler desbloquea proceso siguiente)
        self._semaforo.release()

        self._actualizar_estado(v, EstadoVehiculo.FINALIZADO)
        self._emitir_evento(
            "salida",
            f"V{v.id:03d} salio | Estacionado: {v.tiempo_estacionado}s",
            "info", v
        )
        # Limpiar vehiculo del dict tras 3s para no acumular memoria
        def _limpiar():
            import time as _t
            _t.sleep(3)
            with self._lock:
                self._vehiculos.pop(v.id, None)
        threading.Thread(target=_limpiar, daemon=True).start()

    # ─────────────────────────────────────────
    #  UTILIDADES INTERNAS
    # ─────────────────────────────────────────
    def _esperar_interruptible(self, segundos: float):
        """
        Espera interruptible que respeta el evento de parada y pausa.
        Reemplaza time.sleep() simple para permitir detención limpia.
        Análogo a un proceso que verifica señales del SO entre instrucciones.
        """
        fin = time.time() + segundos
        while time.time() < fin:
            if self._evento_parada.is_set():
                break
            # Verificar pausa (proceso suspendido)
            self._evento_pausa.wait(timeout=0.1)

    def _actualizar_estado(self, v: Vehiculo, nuevo_estado: EstadoVehiculo):
        """Actualiza el estado del vehículo de forma thread-safe."""
        with self._lock:
            v.estado = nuevo_estado

    def _emitir_evento(self, tipo: str, mensaje: str, nivel: str,
                       vehiculo: Optional[Vehiculo] = None):
        """
        Pone un evento en la cola para que la GUI lo consuma.
        NUNCA actualizar widgets Tkinter desde hilos secundarios.
        La GUI lee esta cola con root.after() en el hilo principal.
        """
        evento = {
            "tipo":     tipo,
            "mensaje":  mensaje,
            "nivel":    nivel,          # info | warning | error | success
            "vehiculo": vehiculo,
            "timestamp": time.time(),
            "libres":   self.espacios_libres,
            "ocupados": self._espacios_ocupados,
        }
        self.cola_eventos.put(evento)

    # ─────────────────────────────────────────
    #  MÉTRICAS
    # ─────────────────────────────────────────
    def obtener_metricas(self) -> dict:
        """
        Retorna métricas actuales del simulador.
        Thread-safe gracias al Lock.
        """
        with self._lock:
            procesados = self._total_vehiculos_procesados
            espera_prom = (
                round(self._suma_tiempos_espera / procesados, 2)
                if procesados > 0 else 0.0
            )
            estacion_prom = (
                round(self._suma_tiempos_estacion / procesados, 2)
                if procesados > 0 else 0.0
            )
            utilizacion = (
                round((self._espacios_ocupados / self.capacidad) * 100, 1)
                if self.capacidad > 0 else 0.0
            )
            total_creados = self._contador_id

            return {
                "capacidad":            self.capacidad,
                "ocupados":             self._espacios_ocupados,
                "libres":               self.espacios_libres,
                "utilizacion_pct":      utilizacion,
                "total_creados":        total_creados,
                "total_procesados":     procesados,
                "total_timeout":        self._total_vehiculos_timeout,
                "espera_promedio_s":    espera_prom,
                "estacion_promedio_s":  estacion_prom,
                "estado_espacios":      list(self._espacios_estado),
            }
