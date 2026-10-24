import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
from datetime import datetime
import csv
import os
from PIL import Image, ImageTk

DB_NAME = "inventario_filamentos.db"

class InventarioFilamentosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Inventario, Cotizador e Historial 3D")
        self.root.geometry("1280x780")
        self.root.minsize(1050, 640)
        self.root.configure(bg="#f4f6f9")

        self.id_seleccionado = None
        self.id_historial_seleccionado = None
        self.id_extra_seleccionado = None
        self.mapa_bobinas_calc = {}
        self.mapa_extras_calc = {}
        self.ultimo_resumen_texto = ""
        self.ruta_imagen_pieza = None
        self.img_tk_preview = None

        self.inicializar_bd()
        self.configurar_estilos()
        self.crear_interfaz()
        self.cargar_datos()
        self.cargar_historial()
        self.cargar_extras()
        self.cargar_estadisticas()

    def inicializar_bd(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marca TEXT NOT NULL,
                material TEXT NOT NULL,
                color_modelo TEXT NOT NULL,
                diametro TEXT NOT NULL,
                peso_inicial REAL NOT NULL,
                peso_actual REAL NOT NULL,
                costo REAL NOT NULL,
                fecha_compra TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_impresiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                pieza TEXT NOT NULL,
                bobina TEXT NOT NULL,
                gramos REAL NOT NULL,
                tiempo TEXT NOT NULL,
                costo_produccion REAL NOT NULL,
                precio_venta REAL NOT NULL,
                ruta_imagen TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materiales_extra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,
                nombre TEXT NOT NULL,
                cantidad REAL NOT NULL,
                unidad TEXT NOT NULL,
                costo_unitario REAL NOT NULL,
                proveedor TEXT NOT NULL,
                fecha_compra TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", fieldbackground="white", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#1e293b")
        style.map("Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])

        style.configure("TNotebook", background="#f4f6f9", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[10, 8], background="#cbd5e1", foreground="#1e293b")
        style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])

    def crear_interfaz(self):
        # --- BARRA SUPERIOR DE RESUMEN (KPIs) ---
        frame_top = tk.Frame(self.root, bg="#1e293b", pady=12, padx=20)
        frame_top.pack(fill="x")

        tk.Label(
            frame_top, text="Gestor de Filamentos y Accesorios 3D",
            bg="#1e293b", fg="white", font=("Segoe UI", 15, "bold")
        ).pack(side="left")

        self.lbl_resumen = tk.Label(
            frame_top, text="Bobinas: 0  |  Filamento Restante: 0 g  |  Inversión Total: $0.00",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 11, "bold")
        )
        self.lbl_resumen.pack(side="right")

        # --- SISTEMA DE PESTAÑAS (NOTEBOOK) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        self.tab_inventario = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_calculadora = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_extras = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_historial = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_estadisticas = tk.Frame(self.notebook, bg="#f4f6f9")

        self.notebook.add(self.tab_inventario, text=" 📦 Inventario Filamentos ")
        self.notebook.add(self.tab_calculadora, text=" 🧮 Cotizador 3D ")
        self.notebook.add(self.tab_extras, text=" 🛠️ Materiales Extra ")
        self.notebook.add(self.tab_historial, text=" 📜 Historial Impresiones ")
        self.notebook.add(self.tab_estadisticas, text=" 📊 Estadísticas ")

        self.construir_tab_inventario()
        self.construir_tab_calculadora()
        self.construir_tab_extras()
        self.construir_tab_historial()
        self.construir_tab_estadisticas()

    # =========================================================================
    # PESTAÑA 1: INVENTARIO DE FILAMENTOS
    # =========================================================================
    def construir_tab_inventario(self):
        frame_main = tk.Frame(self.tab_inventario, bg="#f4f6f9", padx=10, pady=10)
        frame_main.pack(fill="both", expand=True)

        frame_form = tk.LabelFrame(
            frame_main, text=" Registro / Edición de Bobina ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=15, pady=10
        )
        frame_form.pack(side="left", fill="y", padx=(0, 15))

        self.var_marca = tk.StringVar()
        self.var_material = tk.StringVar(value="PLA")
        self.var_color = tk.StringVar()
        self.var_diametro = tk.StringVar(value="1.75 mm")
        self.var_peso_ini = tk.StringVar(value="1000")
        self.var_peso_act = tk.StringVar(value="1000")
        self.var_costo = tk.StringVar(value="0.00")
        self.var_fecha = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        campos = [
            ("Marca (ej. eSUN, Hatchbox, Creality):", self.var_marca, "entry", None),
            ("Tipo de Material:", self.var_material, "combo", ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "Nylon", "PC", "Resina", "Otro"]),
            ("Color / Modelo (ej. Negro Mate, Silk Oro):", self.var_color, "entry", None),
            ("Diámetro / Tamaño:", self.var_diametro, "combo", ["1.75 mm", "2.85 mm"]),
            ("Peso Inicial Neto (gramos):", self.var_peso_ini, "entry", None),
            ("Peso Actual Restante (gramos):", self.var_peso_act, "entry", None),
            ("Costo de Compra ($):", self.var_costo, "entry", None),
            ("Fecha de Compra (AAAA-MM-DD):", self.var_fecha, "entry", None),
        ]

        for idx, (texto, variable, tipo, opciones) in enumerate(campos):
            tk.Label(frame_form, text=texto, bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).grid(
                row=idx * 2, column=0, sticky="w", pady=(4, 1)
            )
            if tipo == "entry":
                widget = ttk.Entry(frame_form, textvariable=variable, width=32, font=("Segoe UI", 10))
            else:
                widget = ttk.Combobox(frame_form, textvariable=variable, values=opciones, width=30, font=("Segoe UI", 10))
            widget.grid(row=idx * 2 + 1, column=0, sticky="we", pady=(0, 4))

        frame_btns = tk.Frame(frame_form, bg="white", pady=6)
        frame_btns.grid(row=16, column=0, sticky="we")

        tk.Button(
            frame_btns, text="➕ Agregar (Alta)", command=self.agregar_filamento,
            bg="#10b981", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=3)

        tk.Button(
            frame_btns, text="💾 Guardar Cambios", command=self.actualizar_filamento,
            bg="#3b82f6", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=3)

        tk.Button(
            frame_btns, text="🧹 Limpiar Formulario", command=self.limpiar_formulario,
            bg="#94a3b8", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=4, cursor="hand2"
        ).pack(fill="x", pady=3)

        frame_right = tk.Frame(frame_main, bg="#f4f6f9")
        frame_right.pack(side="right", fill="both", expand=True)

        frame_tools = tk.Frame(frame_right, bg="white", padx=12, pady=10)
        frame_tools.pack(fill="x", pady=(0, 10))

        tk.Label(frame_tools, text="🔍 Buscar:", bg="white", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_buscar = tk.StringVar()
        self.var_buscar.trace_add("write", lambda *args: self.cargar_datos())
        ttk.Entry(frame_tools, textvariable=self.var_buscar, width=22, font=("Segoe UI", 10)).pack(side="left", padx=8)

        frame_leyenda = tk.Frame(frame_tools, bg="white")
        frame_leyenda.pack(side="left", padx=10)
        tk.Label(frame_leyenda, text=" ■ < 50g ", bg="white", fg="#ef4444", font=("Segoe UI", 9, "bold")).pack(side="left", padx=2)
        tk.Label(frame_leyenda, text=" ■ < 150g ", bg="white", fg="#d97706", font=("Segoe UI", 9, "bold")).pack(side="left", padx=2)

        tk.Button(
            frame_tools, text="🗑️ Dar de Baja", command=self.eliminar_filamento,
            bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools, text="📉 Descontar Gramos", command=self.descontar_gramos,
            bg="#f59e0b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools, text="📊 Exportar CSV", command=self.exportar_csv,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        frame_tabla = tk.Frame(frame_right, bg="white")
        frame_tabla.pack(fill="both", expand=True)

        columnas = ("id", "marca", "material", "color", "diametro", "peso_ini", "peso_act", "costo", "fecha")
        self.tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", selectmode="browse")

        self.tabla.tag_configure("alerta_roja", background="#fee2e2", foreground="#991b1b")
        self.tabla.tag_configure("alerta_amarilla", background="#fef3c7", foreground="#92400e")
        self.tabla.tag_configure("normal", background="white", foreground="#1e293b")

        encabezados = {
            "id": ("ID", 40),
            "marca": ("Marca", 100),
            "material": ("Material", 70),
            "color": ("Color / Modelo", 125),
            "diametro": ("Tamaño", 70),
            "peso_ini": ("Inicial (g)", 75),
            "peso_act": ("Restante (g)", 85),
            "costo": ("Costo ($)", 75),
            "fecha": ("Compra", 90),
        }

        for col, (texto, ancho) in encabezados.items():
            self.tabla.heading(col, text=texto)
            alineacion = "center" if col in ("id", "material", "diametro", "fecha") else ("e" if col in ("peso_ini", "peso_act", "costo") else "w")
            self.tabla.column(col, width=ancho, anchor=alineacion)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scrollbar.set)

        self.tabla.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar_fila)

    # =========================================================================
    # PESTAÑA 2: CALCULADORA / COTIZADOR 3D
    # =========================================================================
    def construir_tab_calculadora(self):
        frame_calc_main = tk.Frame(self.tab_calculadora, bg="#f4f6f9", padx=15, pady=12)
        frame_calc_main.pack(fill="both", expand=True)

        frame_inputs = tk.LabelFrame(
            frame_calc_main, text=" Parámetros de la Pieza, Energía y Accesorios ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=15, pady=10
        )
        frame_inputs.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.var_calc_nombre = tk.StringVar(value="Pieza 3D")
        self.var_calc_bobina = tk.StringVar()
        self.var_calc_gramos = tk.StringVar(value="50")
        self.var_calc_horas = tk.StringVar(value="2")
        self.var_calc_minutos = tk.StringVar(value="30")
        self.var_calc_watts = tk.StringVar(value="150")
        self.var_calc_kwh_costo = tk.StringVar(value="2.50")
        self.var_calc_extra = tk.StringVar(value="0.00")
        self.var_calc_margen = tk.StringVar(value="30")
        
        self.var_calc_mat_extra = tk.StringVar(value="Ninguno")
        self.var_calc_cant_extra = tk.StringVar(value="1")

        tk.Label(frame_inputs, text="Nombre de la pieza o proyecto:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(frame_inputs, textvariable=self.var_calc_nombre, font=("Segoe UI", 10)).pack(fill="x", pady=(2, 6))

        tk.Label(frame_inputs, text="Seleccionar Bobina de Filamento:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.combo_bobinas_calc = ttk.Combobox(frame_inputs, textvariable=self.var_calc_bobina, state="readonly", font=("Segoe UI", 10))
        self.combo_bobinas_calc.pack(fill="x", pady=(2, 2))
        self.combo_bobinas_calc.bind("<<ComboboxSelected>>", lambda e: self.calcular_costo_impresion())

        self.lbl_info_bobina = tk.Label(frame_inputs, text="Costo por gramo: $0.00/g  |  Disponible: 0 g", bg="white", fg="#0284c7", font=("Segoe UI", 9, "bold"))
        self.lbl_info_bobina.pack(anchor="w", pady=(0, 6))

        frame_ext_box = tk.Frame(frame_inputs, bg="#f8fafc", highlightbackground="#cbd5e1", highlightthickness=1, padx=8, pady=6)
        frame_ext_box.pack(fill="x", pady=(0, 6))

        tk.Label(frame_ext_box, text="🛠️ Material Extra Opcional (Insertos, Pegamento, etc.):", bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        frame_ext_sub = tk.Frame(frame_ext_box, bg="#f8fafc")
        frame_ext_sub.pack(fill="x", pady=(3, 0))

        self.combo_extras_calc = ttk.Combobox(frame_ext_sub, textvariable=self.var_calc_mat_extra, state="readonly", font=("Segoe UI", 9))
        self.combo_extras_calc.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.combo_extras_calc.bind("<<ComboboxSelected>>", lambda e: self.calcular_costo_impresion())

        tk.Label(frame_ext_sub, text="Cant:", bg="#f8fafc", fg="#475569", font=("Segoe UI", 9)).pack(side="left")
        ttk.Entry(frame_ext_sub, textvariable=self.var_calc_cant_extra, width=6, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        self.var_calc_cant_extra.trace_add("write", lambda *args: self.calcular_costo_impresion())

        frame_fila1 = tk.Frame(frame_inputs, bg="white")
        frame_fila1.pack(fill="x", pady=(0, 6))

        col_g = tk.Frame(frame_fila1, bg="white")
        col_g.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col_g, text="Gramos (g):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_g, textvariable=self.var_calc_gramos, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_h = tk.Frame(frame_fila1, bg="white")
        col_h.pack(side="left", fill="x", expand=True, padx=3)
        tk.Label(col_h, text="Horas:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_h, textvariable=self.var_calc_horas, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_m = tk.Frame(frame_fila1, bg="white")
        col_m.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(col_m, text="Minutos:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_m, textvariable=self.var_calc_minutos, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        frame_fila2 = tk.Frame(frame_inputs, bg="white")
        frame_fila2.pack(fill="x", pady=(0, 6))

        col_w = tk.Frame(frame_fila2, bg="white")
        col_w.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col_w, text="Watts Impresora:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_w, textvariable=self.var_calc_watts, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_kwh = tk.Frame(frame_fila2, bg="white")
        col_kwh.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(col_kwh, text="Costo kWh ($):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_kwh, textvariable=self.var_calc_kwh_costo, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        frame_fila3 = tk.Frame(frame_inputs, bg="white")
        frame_fila3.pack(fill="x", pady=(0, 8))

        col_ext = tk.Frame(frame_fila3, bg="white")
        col_ext.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col_ext, text="Otros Desgastes ($):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_ext, textvariable=self.var_calc_extra, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_mar = tk.Frame(frame_fila3, bg="white")
        col_mar.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(col_mar, text="Margen Ganancia (%):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_mar, textvariable=self.var_calc_margen, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        tk.Button(
            frame_inputs, text="🧮 Calcular Costo", command=self.calcular_costo_impresion,
            bg="#3b82f6", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=2)

        frame_img_panel = tk.LabelFrame(
            frame_calc_main, text=" Imagen de la Pieza (Mín. 500x500 px) ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=12, pady=10, width=230
        )
        frame_img_panel.pack(side="left", fill="y", padx=(0, 10))
        frame_img_panel.pack_propagate(False)

        self.lbl_preview_img = tk.Label(frame_img_panel, text="Sin imagen\n(>= 500x500px)", bg="#e2e8f0", fg="#64748b", font=("Segoe UI", 9), width=24, height=12)
        self.lbl_preview_img.pack(pady=(5, 8))

        tk.Button(
            frame_img_panel, text="📁 Adjuntar Imagen...", command=self.seleccionar_imagen_pieza,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=4, cursor="hand2"
        ).pack(fill="x", pady=2)

        tk.Button(
            frame_img_panel, text="❌ Quitar Imagen", command=self.quitar_imagen_pieza,
            bg="#94a3b8", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", pady=3, cursor="hand2"
        ).pack(fill="x")

        frame_res = tk.LabelFrame(
            frame_calc_main, text=" Desglose y Cotización ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=15, pady=10, width=380
        )
        frame_res.pack(side="right", fill="y")
        frame_res.pack_propagate(False)

        self.lbl_res_filamento = self.crear_fila_resultado(frame_res, "Costo Filamento:", "$0.00")
        self.lbl_res_mat_extra = self.crear_fila_resultado(frame_res, "Costo Material Extra:", "$0.00")
        self.lbl_res_luz = self.crear_fila_resultado(frame_res, "Costo Energía:", "$0.00")
        self.lbl_res_extra = self.crear_fila_resultado(frame_res, "Otros Desgastes:", "$0.00")

        ttk.Separator(frame_res, orient="horizontal").pack(fill="x", pady=5)

        self.lbl_res_produccion = self.crear_fila_resultado(frame_res, "COSTO PRODUCCIÓN:", "$0.00", bold=True, color="#1e293b")
        self.lbl_res_ganancia = self.crear_fila_resultado(frame_res, "Ganancia neta:", "$0.00", color="#10b981")

        frame_total_box = tk.Frame(frame_res, bg="#eff6ff", highlightbackground="#93c5fd", highlightthickness=1, padx=10, pady=8)
        frame_total_box.pack(fill="x", pady=10)

        tk.Label(frame_total_box, text="PRECIO DE VENTA SUGERIDO", bg="#eff6ff", fg="#1d4ed8", font=("Segoe UI", 9, "bold")).pack()
        self.lbl_precio_final = tk.Label(frame_total_box, text="$0.00", bg="#eff6ff", fg="#1e3a8a", font=("Segoe UI", 18, "bold"))
        self.lbl_precio_final.pack(pady=2)

        tk.Button(
            frame_res, text="💾 Descontar Stock y Guardar en Historial", command=self.guardar_impresion_y_descontar,
            bg="#f59e0b", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=6, cursor="hand2"
        ).pack(fill="x", pady=3)

        tk.Button(
            frame_res, text="📋 Copiar Resumen Cotización", command=self.copiar_cotizacion,
            bg="#10b981", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=3)

    # =========================================================================
    # PESTAÑA 3: MATERIALES EXTRA
    # =========================================================================
    def construir_tab_extras(self):
        frame_main_e = tk.Frame(self.tab_extras, bg="#f4f6f9", padx=10, pady=10)
        frame_main_e.pack(fill="both", expand=True)

        frame_form_e = tk.LabelFrame(
            frame_main_e, text=" Registro / Edición de Accesorio ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=15, pady=10
        )
        frame_form_e.pack(side="left", fill="y", padx=(0, 15))

        self.var_ext_cat = tk.StringVar(value="Herrajes")
        self.var_ext_nombre = tk.StringVar()
        self.var_ext_cant = tk.StringVar(value="10")
        self.var_ext_unidad = tk.StringVar(value="Piezas")
        self.var_ext_costo = tk.StringVar(value="0.00")
        self.var_ext_proveedor = tk.StringVar()
        self.var_ext_fecha = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        campos_e = [
            ("Categoría:", self.var_ext_cat, "combo", ["Herrajes", "Pegamentos", "Herramientas", "Tintas / Pinturas", "Pinceles", "Lijas / Abrasivos", "Otros"]),
            ("Nombre / Descripción (ej. Inserts M3, Pega Loca):", self.var_ext_nombre, "entry", None),
            ("Cantidad en Stock:", self.var_ext_cant, "entry", None),
            ("Unidad de Medida:", self.var_ext_unidad, "combo", ["Piezas", "Botes", "Tubos", "Metros", "ml", "g", "Juegos"]),
            ("Costo Unitario ($):", self.var_ext_costo, "entry", None),
            ("Proveedor / Tienda:", self.var_ext_proveedor, "entry", None),
            ("Fecha de Adquisición:", self.var_ext_fecha, "entry", None),
        ]

        for idx, (texto, variable, tipo, opciones) in enumerate(campos_e):
            tk.Label(frame_form_e, text=texto, bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).grid(
                row=idx * 2, column=0, sticky="w", pady=(4, 1)
            )
            if tipo == "entry":
                widget = ttk.Entry(frame_form_e, textvariable=variable, width=30, font=("Segoe UI", 10))
            else:
                widget = ttk.Combobox(frame_form_e, textvariable=variable, values=opciones, width=28, font=("Segoe UI", 10))
            widget.grid(row=idx * 2 + 1, column=0, sticky="we", pady=(0, 4))

        frame_btns_e = tk.Frame(frame_form_e, bg="white", pady=10)
        frame_btns_e.grid(row=16, column=0, sticky="we")

        tk.Button(
            frame_btns_e, text="➕ Agregar Accesorio", command=self.agregar_extra,
            bg="#10b981", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=3)

        tk.Button(
            frame_btns_e, text="💾 Guardar Cambios", command=self.actualizar_extra,
            bg="#3b82f6", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=5, cursor="hand2"
        ).pack(fill="x", pady=3)

        tk.Button(
            frame_btns_e, text="🧹 Limpiar Formulario", command=self.limpiar_formulario_extra,
            bg="#94a3b8", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=4, cursor="hand2"
        ).pack(fill="x", pady=3)

        frame_right_e = tk.Frame(frame_main_e, bg="#f4f6f9")
        frame_right_e.pack(side="right", fill="both", expand=True)

        frame_tools_e = tk.Frame(frame_right_e, bg="white", padx=12, pady=10)
        frame_tools_e.pack(fill="x", pady=(0, 10))

        tk.Label(frame_tools_e, text="🔍 Buscar:", bg="white", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_buscar_extra = tk.StringVar()
        self.var_buscar_extra.trace_add("write", lambda *args: self.cargar_extras())
        ttk.Entry(frame_tools_e, textvariable=self.var_buscar_extra, width=22, font=("Segoe UI", 10)).pack(side="left", padx=8)

        tk.Label(frame_tools_e, text=" ■ Stock bajo (<3) ", bg="white", fg="#ef4444", font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

        tk.Button(
            frame_tools_e, text="🗑️ Eliminar", command=self.eliminar_extra,
            bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools_e, text="📊 Exportar CSV", command=self.exportar_extras_csv,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        frame_tabla_e = tk.Frame(frame_right_e, bg="white")
        frame_tabla_e.pack(fill="both", expand=True)

        columnas_e = ("id", "categoria", "nombre", "cantidad", "unidad", "costo", "proveedor", "fecha")
        self.tabla_extras = ttk.Treeview(frame_tabla_e, columns=columnas_e, show="headings", selectmode="browse")

        self.tabla_extras.tag_configure("alerta_roja", background="#fee2e2", foreground="#991b1b")
        self.tabla_extras.tag_configure("normal", background="white", foreground="#1e293b")

        encabezados_e = {
            "id": ("ID", 40),
            "categoria": ("Categoría", 110),
            "nombre": ("Nombre / Descripción", 170),
            "cantidad": ("Cantidad", 80),
            "unidad": ("Unidad", 75),
            "costo": ("Costo U. ($)", 85),
            "proveedor": ("Proveedor", 110),
            "fecha": ("Adquisición", 90),
        }

        for col, (texto, ancho) in encabezados_e.items():
            self.tabla_extras.heading(col, text=texto)
            alineacion = "center" if col in ("id", "unidad", "fecha") else ("e" if col in ("cantidad", "costo") else "w")
            self.tabla_extras.column(col, width=ancho, anchor=alineacion)

        scrollbar_e = ttk.Scrollbar(frame_tabla_e, orient="vertical", command=self.tabla_extras.yview)
        self.tabla_extras.configure(yscrollcommand=scrollbar_e.set)

        self.tabla_extras.pack(side="left", fill="both", expand=True)
        scrollbar_e.pack(side="right", fill="y")
        self.tabla_extras.bind("<<TreeviewSelect>>", self.seleccionar_fila_extra)

    # =========================================================================
    # PESTAÑA 4: HISTORIAL DE IMPRESIONES (CON VISOR EMERGENTE DE IMAGEN)
    # =========================================================================
    def construir_tab_historial(self):
        frame_hist_main = tk.Frame(self.tab_historial, bg="#f4f6f9", padx=15, pady=12)
        frame_hist_main.pack(fill="both", expand=True)

        frame_tools_h = tk.Frame(frame_hist_main, bg="white", padx=12, pady=10)
        frame_tools_h.pack(fill="x", pady=(0, 10))

        tk.Label(frame_tools_h, text="🔍 Buscar:", bg="white", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_buscar_historial = tk.StringVar()
        self.var_buscar_historial.trace_add("write", lambda *args: self.cargar_historial())
        ttk.Entry(frame_tools_h, textvariable=self.var_buscar_historial, width=22, font=("Segoe UI", 10)).pack(side="left", padx=8)

        tk.Label(
            frame_tools_h, text="💡 Tip: Haz doble clic en una fila para ver su foto",
            bg="white", fg="#64748b", font=("Segoe UI", 9, "italic")
        ).pack(side="left", padx=10)

        tk.Button(
            frame_tools_h, text="📊 Exportar CSV", command=self.exportar_historial_csv,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools_h, text="🗑️ Eliminar Seleccionado", command=self.eliminar_historial_seleccionado,
            bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools_h, text="🧹 Vaciar Todo", command=self.borrar_historial,
            bg="#991b1b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            frame_tools_h, text="🖼️ Ver Foto de la Pieza", command=self.ver_imagen_historial,
            bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2"
        ).pack(side="right", padx=4)

        frame_tabla_h = tk.Frame(frame_hist_main, bg="white")
        frame_tabla_h.pack(fill="both", expand=True)

        columnas_h = ("id", "fecha", "pieza", "bobina", "gramos", "tiempo", "costo", "precio", "imagen")
        self.tabla_historial = ttk.Treeview(frame_tabla_h, columns=columnas_h, show="headings", selectmode="browse")

        encabezados_h = {
            "id": ("ID", 40),
            "fecha": ("Fecha y Hora", 130),
            "pieza": ("Pieza", 150),
            "bobina": ("Bobina Utilizada", 180),
            "gramos": ("Gramos", 75),
            "tiempo": ("Tiempo", 85),
            "costo": ("Costo Prod. ($)", 95),
            "precio": ("Precio Venta ($)", 105),
            "imagen": ("Imagen Registrada", 120),
        }

        for col, (texto, ancho) in encabezados_h.items():
            self.tabla_historial.heading(col, text=texto)
            alineacion = "center" if col in ("id", "fecha", "gramos", "tiempo", "imagen") else ("e" if col in ("costo", "precio") else "w")
            self.tabla_historial.column(col, width=ancho, anchor=alineacion)

        scrollbar_h = ttk.Scrollbar(frame_tabla_h, orient="vertical", command=self.tabla_historial.yview)
        self.tabla_historial.configure(yscrollcommand=scrollbar_h.set)

        self.tabla_historial.pack(side="left", fill="both", expand=True)
        scrollbar_h.pack(side="right", fill="y")
        self.tabla_historial.bind("<<TreeviewSelect>>", self.seleccionar_fila_historial)
        self.tabla_historial.bind("<Double-1>", self.ver_imagen_historial)

    def ver_imagen_historial(self, event=None):
        # Si fue activado por doble clic, identificar la fila directamente bajo el cursor
        if event is not None:
            item_id = self.tabla_historial.identify_row(event.y)
            if item_id:
                self.tabla_historial.selection_set(item_id)
                self.id_historial_seleccionado = self.tabla_historial.item(item_id)["values"][0]

        if not self.id_historial_seleccionado:
            sel = self.tabla_historial.selection()
            if sel:
                self.id_historial_seleccionado = self.tabla_historial.item(sel[0])["values"][0]
            else:
                messagebox.showwarning("Sin selección", "Selecciona primero una impresión de la tabla o haz doble clic sobre ella para ver su foto.")
                return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pieza, fecha, bobina, gramos, precio_venta, ruta_imagen
            FROM historial_impresiones
            WHERE id=?
        """, (self.id_historial_seleccionado,))
        registro = cursor.fetchone()
        conn.close()

        if not registro:
            return

        pieza, fecha, bobina, gramos, precio, ruta_img = registro

        if not ruta_img or ruta_img == "Ninguna":
            messagebox.showinfo("Sin foto", f"La pieza '{pieza}' (ID #{self.id_historial_seleccionado}) no tiene ninguna fotografía registrada.")
            return

        if not os.path.exists(ruta_img):
            messagebox.showerror(
                "Archivo no encontrado",
                f"No se encontró el archivo de imagen en la ruta:\n\n{ruta_img}\n\n"
                "Verifica que la foto no haya sido movida o eliminada de esa carpeta."
            )
            return

        try:
            img = Image.open(ruta_img)
            ancho_orig, alto_orig = img.size
            img.thumbnail((600, 560))
            img_tk = ImageTk.PhotoImage(img)

            ventana_visor = tk.Toplevel(self.root)
            ventana_visor.title(f"Visor de Pieza #{self.id_historial_seleccionado} - {pieza}")
            ventana_visor.configure(bg="#f4f6f9")
            ventana_visor.resizable(False, False)
            ventana_visor.transient(self.root)
            ventana_visor.grab_set()

            # Encabezado con detalles de la pieza
            frame_info = tk.Frame(ventana_visor, bg="#1e293b", padx=20, pady=12)
            frame_info.pack(fill="x")

            tk.Label(
                frame_info, text=f"📦 {pieza}",
                bg="#1e293b", fg="white", font=("Segoe UI", 13, "bold")
            ).pack(anchor="w")

            tk.Label(
                frame_info,
                text=f"Fecha: {fecha}  |  Material: {bobina}  |  Peso: {gramos:.1f} g  |  Precio Venta: ${precio:,.2f}",
                bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(3, 0))

            # Contenedor central de la imagen
            frame_contenedor_img = tk.Frame(
                ventana_visor, bg="white", padx=15, pady=15,
                highlightbackground="#cbd5e1", highlightthickness=1
            )
            frame_contenedor_img.pack(padx=15, pady=15)

            lbl_img = tk.Label(frame_contenedor_img, image=img_tk, bg="white")
            lbl_img.image = img_tk  # Mantener referencia en memoria
            lbl_img.pack()

            # Pie de ventana con resolución y botón de cierre
            frame_footer = tk.Frame(ventana_visor, bg="#f4f6f9", padx=15, pady=8)
            frame_footer.pack(fill="x", pady=(0, 8))

            tk.Label(
                frame_footer, text=f"Resolución original: {ancho_orig} x {alto_orig} px",
                bg="#f4f6f9", fg="#64748b", font=("Segoe UI", 9)
            ).pack(side="left")

            tk.Button(
                frame_footer, text="Cerrar Visor", command=ventana_visor.destroy,
                bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=5, cursor="hand2"
            ).pack(side="right")

            # Centrar la ventana emergente respecto a la ventana principal
            ventana_visor.update_idletasks()
            ancho_v = ventana_visor.winfo_width()
            alto_v = ventana_visor.winfo_height()
            pos_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ancho_v // 2)
            pos_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (alto_v // 2)
            ventana_visor.geometry(f"+{max(0, pos_x)}+{max(0, pos_y)}")

        except Exception as e:
            messagebox.showerror("Error al abrir imagen", f"Ocurrió un problema al cargar la imagen:\n{e}")

    # =========================================================================
    # PESTAÑA 5: ESTADÍSTICAS Y REPORTE MENSUAL
    # =========================================================================
    def construir_tab_estadisticas(self):
        frame_est_main = tk.Frame(self.tab_estadisticas, bg="#f4f6f9", padx=15, pady=12)
        frame_est_main.pack(fill="both", expand=True)

        frame_filtros = tk.Frame(frame_est_main, bg="white", padx=15, pady=12)
        frame_filtros.pack(fill="x", pady=(0, 12))

        tk.Label(frame_filtros, text="📅 Seleccionar Periodo de Reporte:", bg="white", font=("Segoe UI", 11, "bold"), fg="#1e293b").pack(side="left", padx=(0, 10))

        meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.var_est_mes = tk.StringVar(value=meses_nombres[datetime.now().month - 1])
        self.combo_est_mes = ttk.Combobox(frame_filtros, textvariable=self.var_est_mes, values=meses_nombres, state="readonly", width=12, font=("Segoe UI", 10))
        self.combo_est_mes.pack(side="left", padx=5)
        self.combo_est_mes.bind("<<ComboboxSelected>>", lambda e: self.cargar_estadisticas())

        anos_disponibles = [str(y) for y in range(2024, 2031)]
        self.var_est_ano = tk.StringVar(value=str(datetime.now().year))
        self.combo_est_ano = ttk.Combobox(frame_filtros, textvariable=self.var_est_ano, values=anos_disponibles, state="readonly", width=8, font=("Segoe UI", 10))
        self.combo_est_ano.pack(side="left", padx=5)
        self.combo_est_ano.bind("<<ComboboxSelected>>", lambda e: self.cargar_estadisticas())

        tk.Button(
            frame_filtros, text="🔄 Actualizar Reporte", command=self.cargar_estadisticas,
            bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2"
        ).pack(side="left", padx=15)

        tk.Button(
            frame_filtros, text="📊 Exportar Reporte Mensual CSV", command=self.exportar_estadisticas_csv,
            bg="#10b981", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2"
        ).pack(side="right", padx=5)

        frame_tarjetas = tk.Frame(frame_est_main, bg="#f4f6f9")
        frame_tarjetas.pack(fill="x", pady=(0, 12))

        self.lbl_kpi_piezas = self.crear_tarjeta_kpi(frame_tarjetas, "PIEZAS IMPRESAS", "0", "#1e293b")
        self.lbl_kpi_ingresos = self.crear_tarjeta_kpi(frame_tarjetas, "INGRESOS (VENTAS)", "$0.00", "#0284c7")
        self.lbl_kpi_costos = self.crear_tarjeta_kpi(frame_tarjetas, "COSTO PRODUCCIÓN", "$0.00", "#d97706")
        self.lbl_kpi_ganancia = self.crear_tarjeta_kpi(frame_tarjetas, "GANANCIA NETA", "$0.00", "#10b981")

        frame_detalles = tk.Frame(frame_est_main, bg="#f4f6f9")
        frame_detalles.pack(fill="both", expand=True)

        frame_table_box = tk.LabelFrame(frame_detalles, text=" Detalle de Impresiones del Periodo ", bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=10, pady=10)
        frame_table_box.pack(fill="both", expand=True)

        cols_est = ("fecha", "pieza", "bobina", "gramos", "tiempo", "costo", "precio", "ganancia")
        self.tabla_est = ttk.Treeview(frame_table_box, columns=cols_est, show="headings", selectmode="browse")

        headers_est = {
            "fecha": ("Fecha y Hora", 130),
            "pieza": ("Pieza", 180),
            "bobina": ("Bobina Utilizada", 200),
            "gramos": ("Gramos", 80),
            "tiempo": ("Tiempo", 90),
            "costo": ("Costo Prod. ($)", 100),
            "precio": ("Precio Venta ($)", 110),
            "ganancia": ("Ganancia Neta ($)", 110),
        }

        for col, (txt, w) in headers_est.items():
            self.tabla_est.heading(col, text=txt)
            al = "center" if col in ("fecha", "gramos", "tiempo") else ("e" if col in ("costo", "precio", "ganancia") else "w")
            self.tabla_est.column(col, width=w, anchor=al)

        scrollbar_est = ttk.Scrollbar(frame_table_box, orient="vertical", command=self.tabla_est.yview)
        self.tabla_est.configure(yscrollcommand=scrollbar_est.set)

        self.tabla_est.pack(side="left", fill="both", expand=True)
        scrollbar_est.pack(side="right", fill="y")

    def crear_tarjeta_kpi(self, parent, titulo, valor_inicial, color_txt):
        card = tk.Frame(parent, bg="white", highlightbackground="#cbd5e1", highlightthickness=1, padx=15, pady=12)
        card.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(card, text=titulo, bg="white", fg="#64748b", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        lbl_val = tk.Label(card, text=valor_inicial, bg="white", fg=color_txt, font=("Segoe UI", 20, "bold"))
        lbl_val.pack(anchor="w", pady=(4, 0))
        return lbl_val

    def obtener_datos_periodo_est(self):
        meses_map = {
            "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
            "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
            "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
        }
        mes_nombre = self.var_est_mes.get()
        mes_num = meses_map.get(mes_nombre, "01")
        ano_str = self.var_est_ano.get()
        prefijo_fecha = f"{ano_str}-{mes_num}"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta 
            FROM historial_impresiones 
            WHERE fecha LIKE ? 
            ORDER BY id DESC
        """, (f"{prefijo_fecha}%",))
        filas = cursor.fetchall()
        conn.close()
        return filas, mes_nombre, ano_str

    def cargar_estadisticas(self):
        for row in self.tabla_est.get_children():
            self.tabla_est.delete(row)

        filas, _, _ = self.obtener_datos_periodo_est()

        total_piezas = len(filas)
        total_ingresos = 0.0
        total_costos = 0.0

        for f in filas:
            costo = f[5]
            precio = f[6]
            ganancia_neta = precio - costo
            total_ingresos += precio
            total_costos += costo

            self.tabla_est.insert("", "end", values=(
                f[0], f[1], f[2], f"{f[3]:.1f} g", f[4], f"${costo:,.2f}", f"${precio:,.2f}", f"${ganancia_neta:,.2f}"
            ))

        ganancia_total = total_ingresos - total_costos

        self.lbl_kpi_piezas.config(text=str(total_piezas))
        self.lbl_kpi_ingresos.config(text=f"${total_ingresos:,.2f}")
        self.lbl_kpi_costos.config(text=f"${total_costos:,.2f}")
        self.lbl_kpi_ganancia.config(text=f"${ganancia_total:,.2f}")

    def exportar_estadisticas_csv(self):
        filas, mes_nombre, ano_str = self.obtener_datos_periodo_est()
        if not filas:
            messagebox.showwarning("Sin datos", f"No hay impresiones registradas en {mes_nombre} de {ano_str} para exportar.")
            return

        nombre_sugerido = f"Reporte_3D_{mes_nombre}_{ano_str}.csv"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo CSV (Excel)", "*.csv")],
            title="Guardar Reporte Mensual como...",
            initialfile=nombre_sugerido
        )
        if not ruta:
            return

        total_piezas = len(filas)
        total_gramos = sum(f[3] for f in filas)
        total_costos = sum(f[5] for f in filas)
        total_ingresos = sum(f[6] for f in filas)
        ganancia_total = total_ingresos - total_costos

        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as f_csv:
            w = csv.writer(f_csv)
            w.writerow(["REPORTE FINANCIERO MENSUAL DE IMPRESIÓN 3D"])
            w.writerow(["Periodo", f"{mes_nombre} {ano_str}"])
            w.writerow(["Fecha de Generación", datetime.now().strftime("%Y-%m-%d %H:%M")])
            w.writerow([])
            w.writerow(["RESUMEN EJECUTIVO", "VALOR"])
            w.writerow(["Total Piezas Impresas", total_piezas])
            w.writerow(["Total Filamento Consumido (g)", f"{total_gramos:.2f}"])
            w.writerow(["Ingresos Brutos / Ventas ($)", f"{total_ingresos:.2f}"])
            w.writerow(["Costo de Producción Total ($)", f"{total_costos:.2f}"])
            w.writerow(["Ganancia Neta del Mes ($)", f"{ganancia_total:.2f}"])
            w.writerow([])
            w.writerow(["DETALLE DE IMPRESIONES DEL MES"])
            w.writerow(["Fecha y Hora", "Pieza", "Bobina Utilizada", "Gramos (g)", "Tiempo", "Costo Producción ($)", "Precio Venta ($)", "Ganancia Neta ($)"])
            for fila in filas:
                costo = fila[5]
                precio = fila[6]
                ganancia = precio - costo
                w.writerow([
                    fila[0], fila[1], fila[2],
                    f"{fila[3]:.1f}", fila[4],
                    f"{costo:.2f}", f"{precio:.2f}", f"{ganancia:.2f}"
                ])
            w.writerow([])
            w.writerow(["TOTALES", f"{total_piezas} piezas", "", f"{total_gramos:.1f}", "", f"{total_costos:.2f}", f"{total_ingresos:.2f}", f"{ganancia_total:.2f}"])

        messagebox.showinfo("Reporte Exportado", f"El reporte mensual de {mes_nombre} {ano_str} se guardó exitosamente en:\n{ruta}")

    def crear_fila_resultado(self, parent, texto_izq, texto_der, bold=False, color="#475569"):
        fila = tk.Frame(parent, bg="white", pady=3)
        fila.pack(fill="x")
        fuente = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 9)
        tk.Label(fila, text=texto_izq, bg="white", fg=color, font=fuente).pack(side="left")
        lbl_valor = tk.Label(fila, text=texto_der, bg="white", fg=color, font=("Segoe UI", 10, "bold"))
        lbl_valor.pack(side="right")
        return lbl_valor

    # =========================================================================
    # LÓGICA DE CÁLCULO E IMPRESIÓN (COTIZADOR)
    # =========================================================================
    def seleccionar_imagen_pieza(self):
        ruta = filedialog.askopenfilename(title="Seleccionar imagen", filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp")])
        if not ruta: return
        try:
            img = Image.open(ruta)
            ancho, alto = img.size
            if ancho < 500 or alto < 500:
                messagebox.showerror("Muy pequeña", f"La resolución es {ancho}x{alto} px. Se requiere mínimo 500x500px.")
                return
            self.ruta_imagen_pieza = ruta
            img.thumbnail((160, 140))
            self.img_tk_preview = ImageTk.PhotoImage(img)
            self.lbl_preview_img.config(image=self.img_tk_preview, text="", width=160, height=140)
            messagebox.showinfo("Válida", f"Imagen cargada ({ancho}x{alto} px).")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar: {e}")

    def quitar_imagen_pieza(self):
        self.ruta_imagen_pieza = None
        self.img_tk_preview = None
        self.lbl_preview_img.config(image="", text="Sin imagen\n(>= 500x500px)", width=24, height=12)

    def calcular_costo_impresion(self):
        clave_bobina = self.var_calc_bobina.get()
        if not clave_bobina or clave_bobina not in self.mapa_bobinas_calc:
            return None, None, None, None, None, 0.0

        datos_b = self.mapa_bobinas_calc[clave_bobina]
        peso_ini = datos_b["peso_ini"] if datos_b["peso_ini"] > 0 else 1000.0
        costo_bobina = datos_b["costo"]
        costo_por_gramo = costo_bobina / peso_ini

        self.lbl_info_bobina.config(text=f"Costo/g: ${costo_por_gramo:.4f}  |  Disponible: {datos_b['peso_act']:.0f} g")

        costo_mat_extra = 0.0
        cant_extra_usada = 0.0
        nombre_mat_extra_usado = "Ninguno"
        datos_e = None
        clave_extra = self.var_calc_mat_extra.get()
        if clave_extra and clave_extra != "Ninguno" and clave_extra in self.mapa_extras_calc:
            datos_e = self.mapa_extras_calc[clave_extra]
            try:
                cant_extra_usada = float(self.var_calc_cant_extra.get() or 0)
                if cant_extra_usada < 0: cant_extra_usada = 0.0
            except ValueError:
                cant_extra_usada = 0.0
            costo_mat_extra = cant_extra_usada * datos_e["costo_u"]
            nombre_mat_extra_usado = f"{cant_extra_usada} x {datos_e['nombre']}"

        try:
            gramos = float(self.var_calc_gramos.get() or 0)
            horas = float(self.var_calc_horas.get() or 0)
            minutos = float(self.var_calc_minutos.get() or 0)
            watts = float(self.var_calc_watts.get() or 0)
            costo_kwh = float(self.var_calc_kwh_costo.get() or 0)
            extra = float(self.var_calc_extra.get() or 0)
            margen = float(self.var_calc_margen.get() or 0)
            if min(gramos, horas, minutos, watts, costo_kwh, extra, margen) < 0: raise ValueError
        except ValueError:
            return None, None, None, None, None, 0.0

        tiempo_total_horas = horas + (minutos / 60.0)
        consumo_kwh = (watts / 1000.0) * tiempo_total_horas

        costo_filamento = gramos * costo_por_gramo
        costo_luz = consumo_kwh * costo_kwh
        costo_produccion = costo_filamento + costo_mat_extra + costo_luz + extra
        ganancia = costo_produccion * (margen / 100.0)
        precio_final = costo_produccion + ganancia

        self.lbl_res_filamento.config(text=f"${costo_filamento:,.2f}")
        self.lbl_res_mat_extra.config(text=f"${costo_mat_extra:,.2f}")
        self.lbl_res_luz.config(text=f"${costo_luz:,.2f} ({consumo_kwh:.2f} kWh)")
        self.lbl_res_extra.config(text=f"${extra:,.2f}")
        self.lbl_res_produccion.config(text=f"${costo_produccion:,.2f}")
        self.lbl_res_ganancia.config(text=f"+${ganancia:,.2f} ({margen:.0f}%)")
        self.lbl_precio_final.config(text=f"${precio_final:,.2f}")

        self.ultimo_resumen_texto = (
            f"--- COTIZACIÓN IMPRESIÓN 3D ---\n"
            f"Pieza: {self.var_calc_nombre.get()}\n"
            f"Material: {datos_b['marca']} {datos_b['material']} ({datos_b['color']}) [{gramos:.1f}g]\n"
            f"Extra: {nombre_mat_extra_usado} [${costo_mat_extra:,.2f}]\n"
            f"Tiempo de impresión: {int(horas)}h {int(minutos)}m\n"
            f"-------------------------------\n"
            f"Costo Producción: ${costo_produccion:,.2f}\n"
            f"Precio Venta Sugerido: ${precio_final:,.2f}"
        )

        return costo_produccion, precio_final, gramos, datos_b, datos_e, cant_extra_usada

    def guardar_impresion_y_descontar(self):
        res = self.calcular_costo_impresion()
        if not res or res[0] is None:
            messagebox.showwarning("Incompleto", "Verifica los datos de la calculadora.")
            return
        
        costo_prod, precio_v, gramos, datos_b, datos_e, cant_extra_usada = res
        horas = int(self.var_calc_horas.get() or 0)
        minutos = int(self.var_calc_minutos.get() or 0)
        tiempo_str = f"{horas}h {minutos}m"
        nombre_pieza = self.var_calc_nombre.get().strip() or "Pieza sin nombre"
        nombre_bobina = f"{datos_b['marca']} {datos_b['material']} ({datos_b['color']})"

        msg_extra = f"\n- {cant_extra_usada} x {datos_e['nombre']}" if datos_e and cant_extra_usada > 0 else ""
        if not messagebox.askyesno("Confirmar", f"¿Descontar stock y registrar '{nombre_pieza}'?\n\n- {gramos}g de filamento{msg_extra}"): return

        # 1. Descontar filamento
        nuevo_peso_fil = max(0.0, round(datos_b["peso_act"] - gramos, 2))
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE filamentos SET peso_actual=? WHERE id=?", (nuevo_peso_fil, datos_b["id"]))

        # 2. Descontar material extra
        if datos_e and cant_extra_usada > 0:
            cursor.execute("SELECT cantidad FROM materiales_extra WHERE id=?", (datos_e["id"],))
            stock_actual = cursor.fetchone()
            if stock_actual:
                nuevo_stock_ext = max(0.0, round(stock_actual[0] - cant_extra_usada, 2))
                cursor.execute("UPDATE materiales_extra SET cantidad=? WHERE id=?", (nuevo_stock_ext, datos_e["id"]))

        # 3. Guardar en historial
        cursor.execute("""
            INSERT INTO historial_impresiones (fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_pieza, nombre_bobina, gramos, tiempo_str, costo_prod, precio_v, self.ruta_imagen_pieza or "Ninguna"))
        
        conn.commit()
        conn.close()

        self.cargar_datos()
        self.cargar_extras()
        self.cargar_historial()
        self.cargar_estadisticas()
        messagebox.showinfo("Éxito", "Pieza registrada en historial y stock descontado.")

    def copiar_cotizacion(self):
        res = self.calcular_costo_impresion()
        if res and res[0] is not None and self.ultimo_resumen_texto:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.ultimo_resumen_texto)
            messagebox.showinfo("Copiado", "Resumen de cotización copiado al portapapeles.")

    def seleccionar_fila_historial(self, event):
        sel = self.tabla_historial.selection()
        if not sel: return
        self.id_historial_seleccionado = self.tabla_historial.item(sel[0])["values"][0]

    def eliminar_historial_seleccionado(self):
        if not self.id_historial_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una fila del historial.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar registro #{self.id_historial_seleccionado}?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM historial_impresiones WHERE id=?", (self.id_historial_seleccionado,))
            conn.commit()
            conn.close()
            self.id_historial_seleccionado = None
            self.cargar_historial()
            self.cargar_estadisticas()

    def cargar_historial(self):
        for fila in self.tabla_historial.get_children(): self.tabla_historial.delete(fila)
        self.id_historial_seleccionado = None
        filtro = f"%{self.var_buscar_historial.get().strip()}%"
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen FROM historial_impresiones WHERE pieza LIKE ? OR bobina LIKE ? OR fecha LIKE ? ORDER BY id DESC", (filtro, filtro, filtro))
        filas = cursor.fetchall()
        conn.close()
        for f in filas:
            has_img = "🖼️ Ver Foto" if f[8] and f[8] != "Ninguna" else "Sin imagen"
            self.tabla_historial.insert("", "end", values=(f[0], f[1], f[2], f[3], f"{f[4]:.1f} g", f[5], f"${f[6]:.2f}", f"${f[7]:.2f}", has_img))

    def borrar_historial(self):
        if messagebox.askyesno("Confirmar", "¿Vaciar todo el historial?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM historial_impresiones")
            conn.commit()
            conn.close()
            self.cargar_historial()
            self.cargar_estadisticas()

    def exportar_historial_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="historial_impresiones.csv")
        if not ruta: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen FROM historial_impresiones ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()
        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Pieza", "Bobina", "Gramos", "Tiempo", "Costo", "Precio", "Ruta Imagen"])
            w.writerows(filas)
        messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")

    # =========================================================================
    # LÓGICA DE MATERIALES EXTRA
    # =========================================================================
    def agregar_extra(self):
        if not self.var_ext_nombre.get().strip():
            messagebox.showwarning("Incompleto", "Ingresa el nombre o descripción.")
            return
        try:
            cant = float(self.var_ext_cant.get())
            costo = float(self.var_ext_costo.get())
            if cant < 0 or costo < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Cantidad y costo inválidos.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO materiales_extra (categoria, nombre, cantidad, unidad, costo_unitario, proveedor, fecha_compra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.var_ext_cat.get(),
            self.var_ext_nombre.get().strip(),
            cant,
            self.var_ext_unidad.get(),
            costo,
            self.var_ext_proveedor.get().strip() or "N/D",
            self.var_ext_fecha.get().strip()
        ))
        conn.commit()
        conn.close()

        self.limpiar_formulario_extra()
        self.cargar_extras()
        messagebox.showinfo("Éxito", "Accesorio agregado.")

    def actualizar_extra(self):
        if not self.id_extra_seleccionado:
            messagebox.showwarning("Selección", "Selecciona un elemento de Materiales Extra.")
            return
        try:
            cant = float(self.var_ext_cant.get())
            costo = float(self.var_ext_costo.get())
            if cant < 0 or costo < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Valores numéricos inválidos.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE materiales_extra SET categoria=?, nombre=?, cantidad=?, unidad=?, costo_unitario=?, proveedor=?, fecha_compra=?
            WHERE id=?
        """, (
            self.var_ext_cat.get(),
            self.var_ext_nombre.get().strip(),
            cant,
            self.var_ext_unidad.get(),
            costo,
            self.var_ext_proveedor.get().strip() or "N/D",
            self.var_ext_fecha.get().strip(),
            self.id_extra_seleccionado
        ))
        conn.commit()
        conn.close()

        self.limpiar_formulario_extra()
        self.cargar_extras()
        messagebox.showinfo("Actualizado", "Accesorio actualizado.")

    def eliminar_extra(self):
        if not self.id_extra_seleccionado:
            messagebox.showwarning("Selección", "Selecciona un elemento.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar ID #{self.id_extra_seleccionado}?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materiales_extra WHERE id=?", (self.id_extra_seleccionado,))
            conn.commit()
            conn.close()
            self.limpiar_formulario_extra()
            self.cargar_extras()

    def seleccionar_fila_extra(self, event):
        sel = self.tabla_extras.selection()
        if not sel: return
        vals = self.tabla_extras.item(sel[0])["values"]
        self.id_extra_seleccionado = vals[0]
        self.var_ext_cat.set(vals[1])
        self.var_ext_nombre.set(vals[2])
        self.var_ext_cant.set(str(vals[3]))
        self.var_ext_unidad.set(vals[4])
        self.var_ext_costo.set(str(vals[5]).replace("$", ""))
        self.var_ext_proveedor.set(vals[6])
        self.var_ext_fecha.set(vals[7])

    def limpiar_formulario_extra(self):
        self.id_extra_seleccionado = None
        self.var_ext_cat.set("Herrajes")
        self.var_ext_nombre.set("")
        self.var_ext_cant.set("10")
        self.var_ext_unidad.set("Piezas")
        self.var_ext_costo.set("0.00")
        self.var_ext_proveedor.set("")
        self.var_ext_fecha.set(datetime.now().strftime("%Y-%m-%d"))
        for item in self.tabla_extras.selection(): self.tabla_extras.selection_remove(item)

    def cargar_extras(self):
        for fila in self.tabla_extras.get_children(): self.tabla_extras.delete(fila)
        filtro = f"%{self.var_buscar_extra.get().strip()}%"
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, categoria, nombre, cantidad, unidad, costo_unitario, proveedor, fecha_compra FROM materiales_extra WHERE categoria LIKE ? OR nombre LIKE ? ORDER BY id DESC", (filtro, filtro))
        filas = cursor.fetchall()

        cursor.execute("SELECT id, nombre, costo_unitario, unidad FROM materiales_extra ORDER BY nombre ASC")
        todos_extras = cursor.fetchall()
        conn.close()

        total_inv_extras = sum(f[3] * f[5] for f in filas)

        for f in filas:
            tag = "alerta_roja" if f[3] < 3 else "normal"
            self.tabla_extras.insert("", "end", values=(f[0], f[1], f[2], f[3], f[4], f"${f[5]:.2f}", f[6], f[7]), tags=(tag,))

        self.mapa_extras_calc.clear()
        opciones_e = ["Ninguno"]
        for e in todos_extras:
            eti = f"#{e[0]} - {e[1]} (${e[2]:.2f} c/{e[3]})"
            opciones_e.append(eti)
            self.mapa_extras_calc[eti] = {"id": e[0], "nombre": e[1], "costo_u": e[2], "unidad": e[3]}

        self.combo_extras_calc["values"] = opciones_e
        if self.var_calc_mat_extra.get() not in opciones_e:
            self.combo_extras_calc.current(0)

        self.actualizar_resumen_general(inv_extras=total_inv_extras)

    def exportar_extras_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="materiales_extra.csv")
        if not ruta: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT categoria, nombre, cantidad, unidad, costo_unitario, proveedor, fecha_compra FROM materiales_extra ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()
        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Categoría", "Nombre", "Cantidad", "Unidad", "Costo Unitario", "Proveedor", "Fecha"])
            w.writerows(filas)
        messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")

    # =========================================================================
    # INVENTARIO DE FILAMENTOS (LÓGICA)
    # =========================================================================
    def validar_numeros(self):
        try:
            p_ini = float(self.var_peso_ini.get())
            p_act = float(self.var_peso_act.get())
            costo = float(self.var_costo.get())
            if p_ini <= 0 or p_act < 0 or costo < 0: raise ValueError
            return p_ini, p_act, costo
        except ValueError:
            messagebox.showerror("Error", "Valores numéricos inválidos.")
            return None

    def agregar_filamento(self):
        if not self.var_marca.get().strip() or not self.var_color.get().strip():
            messagebox.showwarning("Incompleto", "Ingresa Marca y Color.")
            return
        vals = self.validar_numeros()
        if not vals: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO filamentos (marca, material, color_modelo, diametro, peso_inicial, peso_actual, costo, fecha_compra) VALUES (?,?,?,?,?,?,?,?)",
                       (self.var_marca.get().strip(), self.var_material.get(), self.var_color.get().strip(), self.var_diametro.get(), vals[0], vals[1], vals[2], self.var_fecha.get().strip()))
        conn.commit()
        conn.close()
        self.limpiar_formulario()
        self.cargar_datos()
        messagebox.showinfo("Éxito", "Bobina agregada.")

    def actualizar_filamento(self):
        if not self.id_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una bobina.")
            return
        vals = self.validar_numeros()
        if not vals: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE filamentos SET marca=?, material=?, color_modelo=?, diametro=?, peso_inicial=?, peso_actual=?, costo=?, fecha_compra=? WHERE id=?",
                       (self.var_marca.get().strip(), self.var_material.get(), self.var_color.get().strip(), self.var_diametro.get(), vals[0], vals[1], vals[2], self.var_fecha.get().strip(), self.id_seleccionado))
        conn.commit()
        conn.close()
        self.limpiar_formulario()
        self.cargar_datos()
        messagebox.showinfo("Actualizado", "Bobina actualizada.")

    def eliminar_filamento(self):
        if not self.id_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una bobina.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar bobina #{self.id_seleccionado}?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM filamentos WHERE id=?", (self.id_seleccionado,))
            conn.commit()
            conn.close()
            self.limpiar_formulario()
            self.cargar_datos()

    def descontar_gramos(self):
        if not self.id_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una bobina.")
            return
        g = simpledialog.askfloat("Descontar", "Gramos a descontar:", minvalue=0.1)
        if g is not None:
            p_act = float(self.var_peso_act.get())
            nuevo = max(0.0, round(p_act - g, 2))
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE filamentos SET peso_actual=? WHERE id=?", (nuevo, self.id_seleccionado))
            conn.commit()
            conn.close()
            self.var_peso_act.set(str(nuevo))
            self.cargar_datos()

    def seleccionar_fila(self, event):
        sel = self.tabla.selection()
        if not sel: return
        vals = self.tabla.item(sel[0])["values"]
        self.id_seleccionado = vals[0]
        self.var_marca.set(vals[1])
        self.var_material.set(vals[2])
        self.var_color.set(vals[3])
        self.var_diametro.set(vals[4])
        self.var_peso_ini.set(str(vals[5]).replace(" g", ""))
        self.var_peso_act.set(str(vals[6]).replace(" g", ""))
        self.var_costo.set(str(vals[7]).replace("$", ""))
        self.var_fecha.set(vals[8])

    def limpiar_formulario(self):
        self.id_seleccionado = None
        self.var_marca.set("")
        self.var_material.set("PLA")
        self.var_color.set("")
        self.var_diametro.set("1.75 mm")
        self.var_peso_ini.set("1000")
        self.var_peso_act.set("1000")
        self.var_costo.set("0.00")
        self.var_fecha.set(datetime.now().strftime("%Y-%m-%d"))
        for item in self.tabla.selection(): self.tabla.selection_remove(item)

    def cargar_datos(self):
        for fila in self.tabla.get_children(): self.tabla.delete(fila)
        filtro = f"%{self.var_buscar.get().strip()}%"
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, marca, material, color_modelo, diametro, peso_inicial, peso_actual, costo, fecha_compra FROM filamentos WHERE marca LIKE ? OR material LIKE ? OR color_modelo LIKE ? ORDER BY id DESC", (filtro, filtro, filtro))
        filas = cursor.fetchall()
        cursor.execute("SELECT id, marca, material, color_modelo, peso_inicial, peso_actual, costo FROM filamentos ORDER BY marca ASC")
        todas_bobinas = cursor.fetchall()
        conn.close()

        for f in filas:
            p_act = f[6]
            tag = "alerta_roja" if p_act < 50 else ("alerta_amarilla" if p_act < 150 else "normal")
            self.tabla.insert("", "end", values=(f[0], f[1], f[2], f[3], f[4], f"{f[5]:.0f} g", f"{f[6]:.0f} g", f"${f[7]:.2f}", f[8]), tags=(tag,))

        self.mapa_bobinas_calc.clear()
        opciones = []
        for b in todas_bobinas:
            eti = f"#{b[0]} - {b[1]} | {b[2]} {b[3]} (Quedan: {b[5]:.0f}g - ${b[6]:.2f})"
            opciones.append(eti)
            self.mapa_bobinas_calc[eti] = {"id": b[0], "marca": b[1], "material": b[2], "color": b[3], "peso_ini": b[4], "peso_act": b[5], "costo": b[6]}
        self.combo_bobinas_calc["values"] = opciones
        if opciones and self.var_calc_bobina.get() not in self.mapa_bobinas_calc: self.combo_bobinas_calc.current(0)
        self.calcular_costo_impresion()
        self.actualizar_resumen_general()

    def actualizar_resumen_general(self, inv_extras=None):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(costo) FROM filamentos")
        inv_fil = cursor.fetchone()[0] or 0.0
        if inv_extras is None:
            cursor.execute("SELECT SUM(cantidad * costo_unitario) FROM materiales_extra")
            inv_extras = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT COUNT(*), SUM(peso_actual) FROM filamentos")
        res_b = cursor.fetchone()
        conn.close()

        tot_bob = res_b[0] or 0
        tot_gramos = res_b[1] or 0.0
        inversion_total = inv_fil + inv_extras

        self.lbl_resumen.config(
            text=f"Bobinas: {tot_bob}  |  Filamento Restante: {tot_gramos:,.0f} g  |  Inversión Total: ${inversion_total:,.2f}"
        )

    def exportar_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="inventario_filamentos.csv")
        if not ruta: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM filamentos ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()
        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Marca", "Material", "Color", "Diametro", "Peso Ini", "Peso Act", "Costo", "Fecha"])
            w.writerows(filas)
        messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InventarioFilamentosApp(root)
    root.mainloop()
