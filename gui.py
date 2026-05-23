"""
gui.py - Simulador de Parqueadero Inteligente
Universidad EAN - Arquitectura de Computadores y Sistemas Operativos
"""
import tkinter as tk
from tkinter import ttk
import time, queue
from simulador import SimuladorParqueadero, EstadoVehiculo
from metricas import GestorMetricas

# ── Colores ────────────────────────────────────────────────────────────────────
BG      = "#0f1117"
PANEL   = "#1a1d2e"
CARD    = "#1e2235"
BORDE   = "#2e3355"
VERDE   = "#1db954"
ROJO    = "#e74c3c"
NARANJA = "#f39c12"
AZUL    = "#3f51b5"
GRIS    = "#455a64"
TXT     = "#e8eaf6"
TXT2    = "#9fa8da"
DIM     = "#5c6494"
INFO    = "#7ecfff"

# ── Fuentes ────────────────────────────────────────────────────────────────────
FM = ("Courier New", 9)
FU = ("Segoe UI", 9)
FB = ("Segoe UI", 9, "bold")
FT = ("Segoe UI", 10, "bold")
FG = ("Segoe UI", 13, "bold")


def mk_card(parent, titulo):
    """Crea un panel con borde y titulo."""
    outer = tk.Frame(parent, bg=BORDE)
    outer.pack(fill="x", pady=(0, 5))
    inner = tk.Frame(outer, bg=CARD)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Label(inner, text=titulo, font=FT, bg=CARD, fg=TXT2,
             anchor="w").pack(fill="x", padx=10, pady=(6, 2))
    tk.Frame(inner, bg=BORDE, height=1).pack(fill="x", padx=6)
    return inner


def mk_btn(parent, text, color, cmd, state="normal"):
    """Crea un boton estilizado."""
    def lighter(hx):
        try:
            r = min(255, int(hx[1:3], 16) + 25)
            g = min(255, int(hx[3:5], 16) + 25)
            b = min(255, int(hx[5:7], 16) + 25)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hx
    b = tk.Button(parent, text=text, font=FB, bg=color, fg="white",
                  activebackground=lighter(color), activeforeground="white",
                  relief="flat", bd=0, padx=6, pady=7,
                  cursor="hand2", command=cmd, state=state)
    b.bind("<Enter>", lambda e: b.config(bg=lighter(color)))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


class AppParqueadero(tk.Tk):
    def __init__(self):
        super().__init__()
        self.simulador = SimuladorParqueadero(capacidad=6)
        self.metricas  = GestorMetricas()
        self._activo   = True
        self._ws       = []           # widgets de espacios

        self.title("Simulador de Parqueadero Inteligente - Universidad EAN")
        self.configure(bg=BG)
        self.geometry("1150x760")
        self.minsize(1000, 660)

        # ── Construir UI en orden: header → body → footer ─────────────────
        self._header()
        self._body()
        self._footer()

        # ── Iniciar loop de actualizacion (solo hilo principal) ───────────
        self.after(120, self._loop)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        # Centrar ventana
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"1150x760+{(sw-1150)//2}+{(sh-760)//2}")

    # ── HEADER ────────────────────────────────────────────────────────────
    def _header(self):
        h = tk.Frame(self, bg=PANEL, height=52)
        h.pack(fill="x", side="top")
        h.pack_propagate(False)

        tk.Label(h, text="PARQUEADERO INTELIGENTE - EAN",
                 font=FG, bg=PANEL, fg=TXT
                 ).pack(side="left", padx=16, pady=10)

        self._lbl_hora = tk.Label(h, text="", font=FM, bg=PANEL, fg=DIM)
        self._lbl_hora.pack(side="right", padx=16)

        self._lbl_sys = tk.Label(h, text="DETENIDO", font=FT, bg=PANEL, fg=ROJO)
        self._lbl_sys.pack(side="right", padx=16)

        self._tick_hora()

    def _tick_hora(self):
        self._lbl_hora.config(text=time.strftime("%H:%M:%S"))
        self.after(1000, self._tick_hora)

    # ── FOOTER ────────────────────────────────────────────────────────────
    def _footer(self):
        f = tk.Frame(self, bg=PANEL, height=26)
        f.pack(fill="x", side="bottom")
        f.pack_propagate(False)

        tk.Label(f,
                 text="Universidad EAN  |  Arquitectura de Computadores y SO  |  2025",
                 font=("Segoe UI", 8), bg=PANEL, fg=DIM
                 ).pack(side="left", padx=10)

        self._lbl_ses = tk.Label(f, text="", font=("Segoe UI", 8), bg=PANEL, fg=DIM)
        self._lbl_ses.pack(side="right", padx=10)

    # ── BODY (usa grid para columnas fijas) ───────────────────────────────
    def _body(self):
        """
        Usa grid en lugar de pack para las columnas.
        grid es mas predecible que pack en Windows para layouts complejos.
        """
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        # Columna 0: fija 340px  |  Columna 1: expansible
        body.columnconfigure(0, minsize=340, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ── Columna izquierda ──────────────────────────────────────────────
        izq = tk.Frame(body, bg=BG)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._panel_espacios(izq)
        self._panel_metricas(izq)
        self._panel_control(izq)

        # ── Columna derecha ────────────────────────────────────────────────
        der = tk.Frame(body, bg=BG)
        der.grid(row=0, column=1, sticky="nsew")
        der.rowconfigure(0, weight=1)
        der.rowconfigure(1, weight=1)
        der.columnconfigure(0, weight=1)

        self._panel_vehiculos(der)
        self._panel_log(der)

    # ── PANEL ESPACIOS ────────────────────────────────────────────────────
    def _panel_espacios(self, parent):
        fr = mk_card(parent, "ESPACIOS DEL PARQUEADERO")

        self._lbl_alerta = tk.Label(fr, text="", font=FB, bg=CARD, fg=ROJO)
        self._lbl_alerta.pack()

        self._fr_grid = tk.Frame(fr, bg=CARD)
        self._fr_grid.pack(padx=8, pady=8)

        self._build_grid_espacios()

    def _build_grid_espacios(self):
        """Construye o reconstruye el grid de espacios."""
        for w in self._fr_grid.winfo_children():
            w.destroy()
        self._ws.clear()

        cap  = self.simulador.capacidad
        cols = min(cap, 3)

        for i in range(cap):
            r = i // cols
            c = i %  cols

            box = tk.Frame(self._fr_grid, bg=VERDE, width=90, height=68)
            box.grid(row=r, column=c, padx=3, pady=3)
            box.grid_propagate(False)

            # Numero del espacio
            lnum = tk.Label(box, text=f"#{i+1}", font=("Segoe UI", 7),
                            bg=VERDE, fg="white")
            lnum.place(x=4, y=3)

            # Estado (texto grande)
            lest = tk.Label(box, text="OK", font=("Segoe UI", 16, "bold"),
                            bg=VERDE, fg="white")
            lest.place(relx=0.5, rely=0.45, anchor="center")

            # ID vehiculo
            lvid = tk.Label(box, text="LIBRE", font=("Segoe UI", 7, "bold"),
                            bg=VERDE, fg="white")
            lvid.place(relx=0.5, rely=0.88, anchor="center")

            self._ws.append({"box": box, "est": lest, "vid": lvid, "num": lnum})

    # ── PANEL METRICAS ────────────────────────────────────────────────────
    def _panel_metricas(self, parent):
        fr = mk_card(parent, "METRICAS EN VIVO")

        self._mvars = {}
        items = [
            ("ocupados",           "Ocupados"),
            ("libres",             "Libres"),
            ("utilizacion_pct",    "Utilizacion"),
            ("total_creados",      "Creados"),
            ("total_procesados",   "Procesados"),
            ("total_timeout",      "Timeout"),
            ("espera_promedio_s",  "Espera prom."),
            ("estacion_promedio_s","Estacion prom."),
        ]

        g = tk.Frame(fr, bg=CARD)
        g.pack(fill="x", padx=8, pady=6)

        for i, (key, lbl) in enumerate(items):
            row = i // 2
            c0  = (i % 2) * 2

            tk.Label(g, text=lbl, font=("Segoe UI", 8),
                     bg=CARD, fg=TXT2, anchor="w"
                     ).grid(row=row, column=c0, sticky="w", padx=(6, 2), pady=2)

            v = tk.StringVar(value="--")
            self._mvars[key] = v

            tk.Label(g, textvariable=v, font=("Courier New", 9, "bold"),
                     bg=CARD, fg=TXT, anchor="e", width=8
                     ).grid(row=row, column=c0+1, sticky="e", padx=(0, 8), pady=2)

    # ── PANEL CONTROL ─────────────────────────────────────────────────────
    def _panel_control(self, parent):
        fr = mk_card(parent, "CONTROL")

        def fila():
            f = tk.Frame(fr, bg=CARD)
            f.pack(fill="x", padx=8, pady=3)
            return f

        # Fila 1: Iniciar / Detener
        f1 = fila()
        self._btn_ini = mk_btn(f1, "INICIAR",   VERDE,   self._do_ini)
        self._btn_ini.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._btn_det = mk_btn(f1, "DETENER",   ROJO,    self._do_det, "disabled")
        self._btn_det.pack(side="left", expand=True, fill="x")

        # Fila 2: Pausar / Reiniciar
        f2 = fila()
        self._btn_pau = mk_btn(f2, "PAUSAR",    NARANJA, self._do_pau, "disabled")
        self._btn_pau.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._btn_rei = mk_btn(f2, "REINICIAR", GRIS,    self._do_rei)
        self._btn_rei.pack(side="left", expand=True, fill="x")

        # Fila 3: Agregar vehiculos
        f3 = fila()
        self._btn_add = mk_btn(f3, "+1 Vehiculo", AZUL,
                               lambda: self.simulador.agregar_vehiculo(), "disabled")
        self._btn_add.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._btn_lot = mk_btn(f3, "+5 Vehiculos", AZUL,
                               lambda: self.simulador.agregar_lote(5), "disabled")
        self._btn_lot.pack(side="left", expand=True, fill="x")

        # Fila 4: Flujo continuo automatico
        f4b = fila()
        self._var_auto = tk.BooleanVar(value=False)
        self._chk_auto = tk.Checkbutton(
            f4b, text="Flujo automatico",
            variable=self._var_auto,
            font=FU, bg=CARD, fg=TXT2,
            activebackground=CARD, activeforeground=TXT,
            selectcolor=BORDE,
            command=self._toggle_auto,
            state="disabled"
        )
        self._chk_auto.pack(side="left", padx=6)

        # Fila 4: Capacidad
        f4 = fila()
        tk.Label(f4, text="Capacidad:", font=FU, bg=CARD, fg=TXT2).pack(side="left")
        self._var_cap = tk.IntVar(value=6)
        tk.Spinbox(f4, from_=2, to=12, textvariable=self._var_cap,
                   width=4, font=FU, bg=CARD, fg=TXT,
                   buttonbackground=BORDE, relief="flat"
                   ).pack(side="left", padx=6)
        tk.Label(f4, text="espacios", font=FU, bg=CARD, fg=DIM).pack(side="left")

        tk.Frame(fr, bg=CARD, height=6).pack()

    # ── PANEL VEHICULOS ───────────────────────────────────────────────────
    def _panel_vehiculos(self, parent):
        outer = tk.Frame(parent, bg=BORDE)
        outer.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        fr = tk.Frame(outer, bg=CARD)
        fr.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(fr, text="VEHICULOS ACTIVOS", font=FT,
                 bg=CARD, fg=TXT2, anchor="w"
                 ).pack(fill="x", padx=10, pady=(6, 2))
        tk.Frame(fr, bg=BORDE, height=1).pack(fill="x", padx=6)

        # Estilo del treeview
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("P.Treeview", background=CARD, foreground=TXT,
                    fieldbackground=CARD, borderwidth=0, font=FM, rowheight=24)
        s.configure("P.Treeview.Heading", background=PANEL,
                    foreground=TXT2, borderwidth=0, font=FB)
        s.map("P.Treeview", background=[("selected", BORDE)])

        cols = ("ID", "Tipo", "Estado", "Espacio", "Espera(s)")
        self._tree = ttk.Treeview(fr, columns=cols, show="headings",
                                  height=8, style="P.Treeview")
        for col in cols:
            self._tree.heading(col, text=col)
        self._tree.column("ID",        width=55,  anchor="center")
        self._tree.column("Tipo",      width=130, anchor="center")
        self._tree.column("Estado",    width=150, anchor="center")
        self._tree.column("Espacio",   width=80,  anchor="center")
        self._tree.column("Espera(s)", width=80,  anchor="center")

        sb = ttk.Scrollbar(fr, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 4))

    # ── PANEL LOG ─────────────────────────────────────────────────────────
    def _panel_log(self, parent):
        outer = tk.Frame(parent, bg=BORDE)
        outer.grid(row=1, column=0, sticky="nsew")
        fr = tk.Frame(outer, bg=CARD)
        fr.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(fr, text="LOG DE EVENTOS", font=FT,
                 bg=CARD, fg=TXT2, anchor="w"
                 ).pack(fill="x", padx=10, pady=(6, 2))
        tk.Frame(fr, bg=BORDE, height=1).pack(fill="x", padx=6)

        self._log = tk.Text(fr, font=FM, bg="#0a0c14", fg=TXT,
                            relief="flat", state="disabled",
                            wrap="word", height=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        self._log.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 4))

        self._log.tag_config("info",    foreground=INFO)
        self._log.tag_config("warning", foreground=NARANJA)
        self._log.tag_config("error",   foreground=ROJO)
        self._log.tag_config("success", foreground=VERDE)
        self._log.tag_config("dim",     foreground=DIM)

    def _toggle_auto(self):
        """Activa/desactiva el flujo continuo de vehículos."""
        if self._var_auto.get():
            self._flujo_auto()

    def _flujo_auto(self):
        """
        Agrega un vehiculo cada 5-10 segundos.
        Intervalo largo = GUI fluida, simulacion realista.
        """
        if not self._var_auto.get() or not self.simulador.esta_activo:
            return
        self.simulador.agregar_vehiculo()
        # Cada 8-12 segundos — 1 vehiculo nuevo mientras otros estan estacionados
        import random as _r
        intervalo = _r.randint(8000, 12000)
        self.after(intervalo, self._flujo_auto)

    # ── ACCIONES DE BOTONES ───────────────────────────────────────────────
    def _do_ini(self):
        cap = self._var_cap.get()
        self.simulador = SimuladorParqueadero(capacidad=cap)
        self.metricas  = GestorMetricas()
        self.simulador.iniciar()
        self._build_grid_espacios()
        self._btn_ini.config(state="disabled")
        self._btn_det.config(state="normal")
        self._btn_pau.config(state="normal")
        self._btn_add.config(state="normal")
        self._btn_lot.config(state="normal")
        self._chk_auto.config(state="normal")
        self._lbl_sys.config(text="EN EJECUCION", fg=VERDE)
        self._lbl_ses.config(text=f"Sesion: {self.metricas.nombre_sesion}")

    def _do_det(self):
        self._var_auto.set(False)
        self.simulador.detener()
        self._btn_ini.config(state="normal")
        self._btn_det.config(state="disabled")
        self._btn_pau.config(state="disabled")
        self._btn_add.config(state="disabled")
        self._btn_lot.config(state="disabled")
        self._chk_auto.config(state="disabled")
        self._lbl_sys.config(text="DETENIDO", fg=ROJO)

    def _do_pau(self):
        if self.simulador.esta_pausado:
            self.simulador.reanudar()
            self._btn_pau.config(text="PAUSAR")
            self._lbl_sys.config(text="EN EJECUCION", fg=VERDE)
        else:
            self.simulador.pausar()
            self._btn_pau.config(text="REANUDAR")
            self._lbl_sys.config(text="PAUSADO", fg=NARANJA)

    def _do_rei(self):
        self._var_auto.set(False)
        cap = self._var_cap.get()
        self.simulador = SimuladorParqueadero(capacidad=cap)
        self.metricas  = GestorMetricas()
        self._build_grid_espacios()
        self._clear_tree()
        self._clear_log()
        self._lbl_alerta.config(text="")
        self._lbl_ses.config(text="")
        self._btn_ini.config(state="normal")
        self._btn_det.config(state="disabled")
        self._btn_pau.config(state="disabled", text="PAUSAR")
        self._btn_add.config(state="disabled")
        self._btn_lot.config(state="disabled")
        self._chk_auto.config(state="disabled")
        self._lbl_sys.config(text="DETENIDO", fg=ROJO)

    # ── LOOP PRINCIPAL (solo hilo principal via after) ────────────────────
    def _loop(self):
        """
        Consume la cola del simulador y actualiza la GUI.
        CRITICO: este metodo SOLO corre en el hilo principal.
        Un solo snapshot_gui() por ciclo = un solo Lock.
        """
        if not self._activo:
            return

        # 1. Consumir eventos de la cola (log + alerta)
        try:
            for _ in range(20):
                ev = self.simulador.cola_eventos.get_nowait()
                self._on_evento(ev)
                self.metricas.registrar_desde_evento(ev)
        except queue.Empty:
            pass

        # 2. Un solo snapshot para todos los paneles — evita multiples Locks
        snap = self.simulador.snapshot_gui()
        self._upd_espacios(snap)
        self._upd_metricas(snap)
        self._upd_tree(snap)

        # Reprogramar en 150ms (suficiente para UI fluida, menos carga)
        self.after(120, self._loop)

    def _on_evento(self, ev):
        self._log_add(ev["mensaje"], ev["nivel"])
        if ev.get("libres", 1) == 0:
            self._lbl_alerta.config(text="PARQUEADERO LLENO - Vehiculos en espera")
        else:
            self._lbl_alerta.config(text="")

    # ── ACTUALIZACIONES DE UI (usan snapshot — sin Lock extra) ───────────
    def _upd_espacios(self, snap: dict):
        """Actualiza espacios solo si el estado cambio."""
        if not self._ws:
            return
        estado = snap["espacios"]
        vhs    = snap["vehiculos"]

        for i, w in enumerate(self._ws):
            if i >= len(estado):
                break
            oid = estado[i]
            if oid is None:
                col, est, vid = VERDE,   "OK",  "LIBRE"
            else:
                v = vhs.get(oid)
                if v and v.tipo.name == "DISCAPACIDAD":
                    col, est, vid = NARANJA, "D",  f"V{oid:03d}"
                else:
                    col, est, vid = ROJO,    "XX", f"V{oid:03d}"
            # Solo actualizar si cambio — evita redraws innecesarios
            if w["box"].cget("bg") != col:
                w["box"].config(bg=col)
                w["est"].config(bg=col, text=est)
                w["vid"].config(bg=col, text=vid)
                w["num"].config(bg=col)

    def _upd_metricas(self, snap: dict):
        """Actualiza metricas desde el snapshot."""
        vals = {
            "ocupados":           str(snap["ocupados"]),
            "libres":             str(snap["libres"]),
            "utilizacion_pct":    f"{snap['utilizacion']}%",
            "total_creados":      str(snap["creados"]),
            "total_procesados":   str(snap["procesados"]),
            "total_timeout":      str(snap["timeout"]),
            "espera_promedio_s":  f"{snap['espera_prom']}s",
            "estacion_promedio_s":f"{snap['estacion_prom']}s",
        }
        for k, v in self._mvars.items():
            v.set(vals.get(k, "--"))

    def _upd_tree(self, snap: dict):
        """Actualiza tabla de vehiculos activos desde el snapshot."""
        vhs       = snap["vehiculos"]
        ids_tabla = set(self._tree.get_children())
        ids_activos = set()

        for vid, v in vhs.items():
            ids_activos.add(str(vid))
            esp  = f"#{v.espacio_asignado}" if v.espacio_asignado else "--"
            wait = str(v.tiempo_espera)     if v.tiempo_espera    else "--"
            vals = (f"V{v.id:03d}", v.tipo.etiqueta, v.estado.value, esp, wait)
            iid  = str(vid)
            if iid in ids_tabla:
                self._tree.item(iid, values=vals)
            else:
                self._tree.insert("", "end", iid=iid, values=vals)

        # Eliminar filas de vehiculos que ya salieron
        for iid in ids_tabla - ids_activos:
            self._tree.delete(iid)

    def _log_add(self, msg, nivel="info"):
        self._log.config(state="normal")
        self._log.insert("end", f"[{time.strftime('%H:%M:%S')}] ", "dim")
        self._log.insert("end", f"{msg}\n", nivel)
        self._log.see("end")
        self._log.config(state="disabled")

    def _clear_tree(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _cerrar(self):
        self._activo = False
        self.simulador.detener()
        self.after(300, self.destroy)
