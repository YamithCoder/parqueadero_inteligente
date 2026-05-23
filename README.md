# 🚗 Simulador de Parqueadero Inteligente

**Universidad EAN — Arquitectura de Computadores y Sistemas Operativos**  
**Estudiante:** Yamith Andrey Peñuela Rincón  
**Docente:** Diana Carolina Beltrán Peña  
**Grupo:** 1 — Primer Semestre Virtual — 2026

---

## 📋 Descripción

Simulador de parqueadero inteligente que modela la gestión de recursos compartidos en un entorno concurrente, aplicando los principios fundamentales de los Sistemas Operativos.

Cada vehículo es un **hilo independiente** que compite por un número limitado de **espacios de parqueo**, coordinados mediante **semáforos**, **locks** y **eventos** — exactamente como un SO gestiona procesos que compiten por CPU o memoria.

### Analogía con Sistemas Operativos

| Parqueadero | Sistema Operativo |
|-------------|------------------|
| Vehículo | Proceso |
| Espacio de parqueo | CPU / Memoria |
| Semáforo | Planificador del SO |
| Lock | Sección crítica |
| Vehículo esperando | Proceso bloqueado |
| Event parada | SIGTERM |

---

## 🖥️ Captura del simulador

![Simulador en ejecución](docs/captura_simulador.png)

---

## ⚙️ Tecnologías

- **Python 3.10+**
- `threading` — hilos, Semaphore, Lock, Event
- `tkinter` — interfaz gráfica
- `queue.Queue` — comunicación thread-safe hilo → GUI
- `csv` — exportación de métricas

---

## 📁 Estructura del proyecto

```
parqueadero/
├── main.py          # Punto de entrada
├── simulador.py     # Lógica de hilos, semáforos y locks
├── gui.py           # Interfaz gráfica Tkinter
├── metricas.py      # Logs, estadísticas y exportación CSV
├── docs/
│   └── captura_simulador.png
└── logs/            # Archivos .log y .csv generados en ejecución
```

---

## 🚀 Instalación y ejecución

### Requisitos
- Python 3.10 o superior
- Tkinter (incluido en la instalación estándar de Python)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/YamithCoder/parqueadero-inteligente.git

# 2. Entrar a la carpeta
cd parqueadero-inteligente

# 3. Ejecutar
python main.py
```

> No requiere instalar dependencias externas — solo Python estándar.

---

## 🎮 Uso del simulador

1. Presiona **INICIAR** para arrancar el sistema
2. Usa **+1 Vehículo** o **+5 Vehículos** para agregar vehículos manualmente
3. Activa **Flujo automático** para simular llegada continua
4. Observa en tiempo real:
   - Espacios ocupados (rojo) / libres (verde) / discapacidad (naranja)
   - Tabla de vehículos activos con estado, espacio asignado y tiempo de espera
   - Log de eventos con entradas, salidas y timeouts
   - Métricas: utilización, tiempo promedio de espera y estacionamiento
5. Usa **PAUSAR** / **REINICIAR** para controlar la simulación
6. Ajusta la **capacidad** del parqueadero antes de iniciar (2 a 12 espacios)

---

## 🔧 Mecanismos de sincronización

### `threading.Semaphore`
Controla cuántos vehículos pueden estar estacionados simultáneamente. Usa `acquire(timeout=T)` para prevenir deadlock — si un vehículo no obtiene cupo en T segundos, abandona la espera.

### `threading.Lock`
Protege las variables compartidas `espacios_ocupados` y `estado_espacios`. Garantiza exclusión mutua en la sección crítica.

### `threading.Event`
- `evento_parada`: apagado ordenado de todos los hilos (análogo a SIGTERM)
- `evento_pausa`: suspensión temporal de hilos activos

### `queue.Queue`
Los hilos nunca modifican widgets de Tkinter directamente. Depositan eventos en una cola thread-safe que el hilo principal consume cada 120ms con `root.after()`.

---

## 📊 Métricas generadas

Cada sesión genera automáticamente en la carpeta `logs/`:

| Archivo | Contenido |
|---------|-----------|
| `sesion_YYYYMMDD_HHMMSS.log` | Log de eventos en texto |
| `sesion_YYYYMMDD_HHMMSS.csv` | Datos tabulares para análisis |

Las métricas incluyen: utilización del parqueadero, tiempo promedio de espera, tiempo promedio de estacionamiento, total de vehículos procesados y timeouts.

---

## 🧠 Conceptos de SO aplicados

- **Concurrencia:** múltiples hilos ejecutándose simultáneamente
- **Exclusión mutua:** Lock protege la sección crítica
- **Semáforos:** control de acceso a recursos limitados
- **Planificación por prioridad:** vehículos de Discapacidad tienen prioridad de llegada
- **Prevención de deadlock:** timeout en acquire() rompe la espera circular
- **Comunicación entre procesos (IPC):** queue.Queue como canal thread-safe

---

## 📄 Licencia

Proyecto académico — Universidad EAN 2026
