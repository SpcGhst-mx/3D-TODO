import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
from datetime import datetime
import csv
from PIL import Image, ImageTk

DB_NAME = "inventario_filamentos.db"

class InventarioFilamentosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Inventario, Cotizador y Historial 3D")
        self.root.geometry("1180x720")
        self.root.minsize(1020, 620)
        self.root.configure(bg="#f4f6f9")

        self.id_seleccionado = None
        self.mapa_bobinas_calc = {}
        self.ultimo_resumen_texto = ""
        self.ruta_imagen_pieza = None
        self.img_tk_preview = None

        self.inicializar_bd()
        self.configurar_estilos()
        self.crear_interfaz()
        self.cargar_datos()
        self.cargar_historial()

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
        conn.commit()
        conn.close()

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", fieldbackground="white", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#1e293b")
        style.map("Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])

        style.configure("TNotebook", background="#f4f6f9", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[14, 8], background="#cbd5e1", foreground="#1e293b")
        style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])

    def crear_interfaz(self):
        # --- BARRA SUPERIOR DE RESUMEN (KPIs) ---
        frame_top = tk.Frame(self.root, bg="#1e293b", pady=12, padx=20)
        frame_top.pack(fill="x")

        tk.Label(
            frame_top, text="Gestor de Filamentos y Cotizador 3D",
            bg="#1e293b", fg="white", font=("Segoe UI", 15, "bold")
        ).pack(side="left")

        self.lbl_resumen = tk.Label(
            frame_top, text="Bobinas: 0  |  Material Restante: 0 g  |  Inversión Total: $0.00",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 11, "bold")
        )
        self.lbl_resumen.pack(side="right")

        # --- SISTEMA DE PESTAÑAS (NOTEBOOK) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        self.tab_inventario = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_calculadora = tk.Frame(self.notebook, bg="#f4f6f9")
        self.tab_historial = tk.Frame(self.notebook, bg="#f4f6f9")

        self.notebook.add(self.tab_inventario, text=" 📦 Inventario de Filamentos ")
        self.notebook.add(self.tab_calculadora, text=" 🧮 Calculadora de Impresión 3D ")
        self.notebook.add(self.tab_historial, text=" 📜 Historial de Impresiones ")

        self.construir_tab_inventario()
        self.construir_tab_calculadora()
        self.construir_tab_historial()

    # =========================================================================
    # PESTAÑA 1: INVENTARIO
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
    # PESTAÑA 2: CALCULADORA DE COSTO DE IMPRESIÓN 3D
    # =========================================================================
    def construir_tab_calculadora(self):
        frame_calc_main = tk.Frame(self.tab_calculadora, bg="#f4f6f9", padx=15, pady=12)
        frame_calc_main.pack(fill="both", expand=True)

        # Columna Izquierda: Parámetros
        frame_inputs = tk.LabelFrame(
            frame_calc_main, text=" Parámetros de la Pieza y Energía ",
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

        tk.Label(frame_inputs, text="Nombre de la pieza o proyecto:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(frame_inputs, textvariable=self.var_calc_nombre, font=("Segoe UI", 10)).pack(fill="x", pady=(2, 8))

        tk.Label(frame_inputs, text="Seleccionar Bobina del Inventario:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.combo_bobinas_calc = ttk.Combobox(frame_inputs, textvariable=self.var_calc_bobina, state="readonly", font=("Segoe UI", 10))
        self.combo_bobinas_calc.pack(fill="x", pady=(2, 2))
        self.combo_bobinas_calc.bind("<<ComboboxSelected>>", lambda e: self.calcular_costo_impresion())

        self.lbl_info_bobina = tk.Label(frame_inputs, text="Costo por gramo: $0.00/g  |  Disponible: 0 g", bg="white", fg="#0284c7", font=("Segoe UI", 9, "bold"))
        self.lbl_info_bobina.pack(anchor="w", pady=(0, 8))

        frame_fila1 = tk.Frame(frame_inputs, bg="white")
        frame_fila1.pack(fill="x", pady=(0, 8))

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
        frame_fila2.pack(fill="x", pady=(0, 8))

        col_w = tk.Frame(frame_fila2, bg="white")
        col_w.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col_w, text="Watts Impresora:", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_w, textvariable=self.var_calc_watts, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_kwh = tk.Frame(frame_fila2, bg="white")
        col_kwh.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(col_kwh, text="Costo kWh ($):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_kwh, textvariable=self.var_calc_kwh_costo, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        frame_fila3 = tk.Frame(frame_inputs, bg="white")
        frame_fila3.pack(fill="x", pady=(0, 10))

        col_ext = tk.Frame(frame_fila3, bg="white")
        col_ext.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col_ext, text="Extras / Desgaste ($):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_ext, textvariable=self.var_calc_extra, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        col_mar = tk.Frame(frame_fila3, bg="white")
        col_mar.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(col_mar, text="Margen Ganancia (%):", bg="white", fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(col_mar, textvariable=self.var_calc_margen, font=("Segoe UI", 10)).pack(fill="x", pady=2)

        tk.Button(
            frame_inputs, text="🧮 Calcular Costo", command=self.calcular_costo_impresion,
            bg="#3b82f6", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=6, cursor="hand2"
        ).pack(fill="x", pady=3)

        # Columna Central: Imagen de la pieza (Min 500x500px)
        frame_img_panel = tk.LabelFrame(
            frame_calc_main, text=" Imagen de la Pieza (Mín. 500x500 px) ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=12, pady=10, width=240
        )
        frame_img_panel.pack(side="left", fill="y", padx=(0, 10))
        frame_img_panel.pack_propagate(False)

        self.lbl_preview_img = tk.Label(frame_img_panel, text="Sin imagen\n(>= 500x500px)", bg="#e2e8f0", fg="#64748b", font=("Segoe UI", 9), width=26, height=12)
        self.lbl_preview_img.pack(pady=(5, 8))

        tk.Button(
            frame_img_panel, text="📁 Adjuntar Imagen...", command=self.seleccionar_imagen_pieza,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=4, cursor="hand2"
        ).pack(fill="x", pady=2)

        tk.Button(
            frame_img_panel, text="❌ Quitar Imagen", command=self.quitar_imagen_pieza,
            bg="#94a3b8", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", pady=3, cursor="hand2"
        ).pack(fill="x")

        # Columna Derecha: Desglose y Acciones
        frame_res = tk.LabelFrame(
            frame_calc_main, text=" Desglose y Cotización ",
            bg="white", fg="#1e293b", font=("Segoe UI", 11, "bold"), padx=15, pady=10, width=370
        )
        frame_res.pack(side="right", fill="y")
        frame_res.pack_propagate(False)

        self.lbl_res_filamento = self.crear_fila_resultado(frame_res, "Costo Filamento:", "$0.00")
        self.lbl_res_luz = self.crear_fila_resultado(frame_res, "Costo Energía:", "$0.00")
        self.lbl_res_extra = self.crear_fila_resultado(frame_res, "Extras / Desgaste:", "$0.00")

        ttk.Separator(frame_res, orient="horizontal").pack(fill="x", pady=6)

        self.lbl_res_produccion = self.crear_fila_resultado(frame_res, "COSTO PRODUCCIÓN:", "$0.00", bold=True, color="#1e293b")
        self.lbl_res_ganancia = self.crear_fila_resultado(frame_res, "Ganancia neta:", "$0.00", color="#10b981")

        frame_total_box = tk.Frame(frame_res, bg="#eff6ff", highlightbackground="#93c5fd", highlightthickness=1, padx=10, pady=8)
        frame_total_box.pack(fill="x", pady=8)

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
    # PESTAÑA 3: HISTORIAL DE IMPRESIONES
    # =========================================================================
    def construir_tab_historial(self):
        frame_hist_main = tk.Frame(self.tab_historial, bg="#f4f6f9", padx=15, pady=12)
        frame_hist_main.pack(fill="both", expand=True)

        frame_tools_h = tk.Frame(frame_hist_main, bg="white", padx=12, pady=10)
        frame_tools_h.pack(fill="x", pady=(0, 10))

        tk.Label(frame_tools_h, text="📜 Registro de piezas impresas y cotizadas", bg="white", font=("Segoe UI", 11, "bold"), fg="#1e293b").pack(side="left")

        tk.Button(
            frame_tools_h, text="📊 Exportar Historial CSV", command=self.exportar_historial_csv,
            bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2"
        ).pack(side="right")

        tk.Button(
            frame_tools_h, text="🗑️ Borrar Historial", command=self.borrar_historial,
            bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2"
        ).pack(side="right", padx=6)

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

    def crear_fila_resultado(self, parent, texto_izq, texto_der, bold=False, color="#475569"):
        fila = tk.Frame(parent, bg="white", pady=3)
        fila.pack(fill="x")
        fuente = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 9)
        tk.Label(fila, text=texto_izq, bg="white", fg=color, font=fuente).pack(side="left")
        lbl_valor = tk.Label(fila, text=texto_der, bg="white", fg=color, font=("Segoe UI", 10, "bold"))
        lbl_valor.pack(side="right")
        return lbl_valor

    # =========================================================================
    # LÓGICA DE IMAGEN (>= 500x500px)
    # =========================================================================
    def seleccionar_imagen_pieza(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de la pieza",
            filetypes=[("Archivos de Imagen", "*.jpg *.jpeg *.png *.webp")]
        )
        if not ruta:
            return

        try:
            img = Image.open(ruta)
            ancho, alto = img.size
            if ancho < 500 or alto < 500:
                messagebox.showerror(
                    "Imagen muy pequeña",
                    f"La imagen seleccionada tiene una resolución de {ancho}x{alto} px.\n\n"
                    f"El sistema requiere que la imagen sea de al menos **500px x 500px**."
                )
                return

            self.ruta_imagen_pieza = ruta
            img.thumbnail((160, 140))
            self.img_tk_preview = ImageTk.PhotoImage(img)
            self.lbl_preview_img.config(image=self.img_tk_preview, text="", width=160, height=140)
            messagebox.showinfo("Imagen válida", f"Imagen cargada correctamente ({ancho}x{alto} px).")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")

    def quitar_imagen_pieza(self):
        self.ruta_imagen_pieza = None
        self.img_tk_preview = None
        self.lbl_preview_img.config(image="", text="Sin imagen\n(>= 500x500px)", width=26, height=12)

    # =========================================================================
    # LÓGICA DE CÁLCULO E HISTORIAL
    # =========================================================================
    def calcular_costo_impresion(self):
        clave_bobina = self.var_calc_bobina.get()
        if not clave_bobina or clave_bobina not in self.mapa_bobinas_calc:
            return None, None, None, None

        datos_b = self.mapa_bobinas_calc[clave_bobina]
        peso_ini = datos_b["peso_ini"] if datos_b["peso_ini"] > 0 else 1000.0
        costo_bobina = datos_b["costo"]
        costo_por_gramo = costo_bobina / peso_ini

        self.lbl_info_bobina.config(
            text=f"Costo/g: ${costo_por_gramo:.4f}  |  Disponible: {datos_b['peso_act']:.0f} g"
        )

        try:
            gramos = float(self.var_calc_gramos.get() or 0)
            horas = float(self.var_calc_horas.get() or 0)
            minutos = float(self.var_calc_minutos.get() or 0)
            watts = float(self.var_calc_watts.get() or 0)
            costo_kwh = float(self.var_calc_kwh_costo.get() or 0)
            extra = float(self.var_calc_extra.get() or 0)
            margen = float(self.var_calc_margen.get() or 0)

            if min(gramos, horas, minutos, watts, costo_kwh, extra, margen) < 0:
                raise ValueError
        except ValueError:
            return None, None, None, None

        tiempo_total_horas = horas + (minutos / 60.0)
        consumo_kwh = (watts / 1000.0) * tiempo_total_horas

        costo_filamento = gramos * costo_por_gramo
        costo_luz = consumo_kwh * costo_kwh
        costo_produccion = costo_filamento + costo_luz + extra
        ganancia = costo_produccion * (margen / 100.0)
        precio_final = costo_produccion + ganancia

        self.lbl_res_filamento.config(text=f"${costo_filamento:,.2f}")
        self.lbl_res_luz.config(text=f"${costo_luz:,.2f} ({consumo_kwh:.2f} kWh)")
        self.lbl_res_extra.config(text=f"${extra:,.2f}")
        self.lbl_res_produccion.config(text=f"${costo_produccion:,.2f}")
        self.lbl_res_ganancia.config(text=f"+${ganancia:,.2f} ({margen:.0f}%)")
        self.lbl_precio_final.config(text=f"${precio_final:,.2f}")

        self.ultimo_resumen_texto = (
            f"--- COTIZACIÓN IMPRESIÓN 3D ---\n"
            f"Pieza: {self.var_calc_nombre.get()}\n"
            f"Material: {datos_b['marca']} {datos_b['material']} ({datos_b['color']})\n"
            f"Peso estimado: {gramos:.1f} g\n"
            f"Tiempo de impresión: {int(horas)}h {int(minutos)}m\n"
            f"-------------------------------\n"
            f"Costo Producción: ${costo_produccion:,.2f}\n"
            f"Precio Venta Sugerido: ${precio_final:,.2f}"
        )
        return costo_produccion, precio_final, gramos, datos_b

    def guardar_impresion_y_descontar(self):
        res = self.calcular_costo_impresion()
        if not res or res[0] is None:
            messagebox.showwarning("Datos incompletos", "Verifica que la bobina seleccionada y los valores numéricos sean correctos.")
            return

        costo_prod, precio_v, gramos, datos_b = res
        horas = int(self.var_calc_horas.get() or 0)
        minutos = int(self.var_calc_minutos.get() or 0)
        tiempo_str = f"{horas}h {minutos}m"
        nombre_pieza = self.var_calc_nombre.get().strip() or "Pieza sin nombre"
        nombre_bobina = f"{datos_b['marca']} {datos_b['material']} ({datos_b['color']})"

        confirmar = messagebox.askyesno(
            "Confirmar Registro",
            f"¿Descontar {gramos} g de la bobina y guardar la impresión en el Historial?\n\n"
            f"Pieza: {nombre_pieza}\n"
            f"Costo Producción: ${costo_prod:,.2f}  |  Precio Venta: ${precio_v:,.2f}"
        )
        if not confirmar:
            return

        # 1. Descontar del inventario
        nuevo_peso = max(0.0, round(datos_b["peso_act"] - gramos, 2))
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE filamentos SET peso_actual=? WHERE id=?", (nuevo_peso, datos_b["id"]))

        # 2. Guardar en historial
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
        ruta_img_guardar = self.ruta_imagen_pieza if self.ruta_imagen_pieza else "Ninguna"
        cursor.execute("""
            INSERT INTO historial_impresiones (fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (fecha_actual, nombre_pieza, nombre_bobina, gramos, tiempo_str, costo_prod, precio_v, ruta_img_guardar))

        conn.commit()
        conn.close()

        self.cargar_datos()
        self.cargar_historial()
        messagebox.showinfo("Éxito", "Pieza registrada en el Historial y stock descontado correctamente.")

    def copiar_cotizacion(self):
        self.calcular_costo_impresion()
        if self.ultimo_resumen_texto:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.ultimo_resumen_texto)
            messagebox.showinfo("Copiado", "Resumen copiado al portapapeles.")

    def cargar_historial(self):
        for fila in self.tabla_historial.get_children():
            self.tabla_historial.delete(fila)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen FROM historial_impresiones ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()

        for f in filas:
            has_img = "Sí (>=500px)" if f[8] and f[8] != "Ninguna" else "Sin imagen"
            self.tabla_historial.insert("", "end", values=(
                f[0], f[1], f[2], f[3], f"{f[4]:.1f} g", f[5], f"${f[6]:.2f}", f"${f[7]:.2f}", has_img
            ))

    def borrar_historial(self):
        confirmar = messagebox.askyesno("Confirmar", "¿Deseas vaciar todo el historial de impresiones?")
        if confirmar:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM historial_impresiones")
            conn.commit()
            conn.close()
            self.cargar_historial()

    def exportar_historial_csv(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv")],
            initialfile="historial_impresiones.csv"
        )
        if not ruta:
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, pieza, bobina, gramos, tiempo, costo_produccion, precio_venta, ruta_imagen FROM historial_impresiones ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()

        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as archivo:
            writer = csv.writer(archivo)
            writer.writerow(["Fecha y Hora", "Pieza", "Bobina", "Gramos (g)", "Tiempo", "Costo Produccion ($)", "Precio Venta ($)", "Ruta Imagen"])
            writer.writerows(filas)

        messagebox.showinfo("Exportado", f"Historial guardado en:\n{ruta}")

    # =========================================================================
    # LÓGICA DEL INVENTARIO
    # =========================================================================
    def validar_numeros(self):
        try:
            p_ini = float(self.var_peso_ini.get())
            p_act = float(self.var_peso_act.get())
            costo = float(self.var_costo.get())
            if p_ini <= 0 or p_act < 0 or costo < 0:
                raise ValueError
            return p_ini, p_act, costo
        except ValueError:
            messagebox.showerror("Datos inválidos", "Verifica que el Peso Inicial sea mayor a 0 y los demás valores sean válidos.")
            return None

    def agregar_filamento(self):
        if not self.var_marca.get().strip() or not self.var_color.get().strip():
            messagebox.showwarning("Incompleto", "Ingresa al menos la Marca y el Color/Modelo.")
            return
        vals = self.validar_numeros()
        if not vals: return
        p_ini, p_act, costo = vals

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO filamentos (marca, material, color_modelo, diametro, peso_inicial, peso_actual, costo, fecha_compra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.var_marca.get().strip(), self.var_material.get().strip(), self.var_color.get().strip(), self.var_diametro.get().strip(), p_ini, p_act, costo, self.var_fecha.get().strip()))
        conn.commit()
        conn.close()

        self.limpiar_formulario()
        self.cargar_datos()
        messagebox.showinfo("Éxito", "Bobina agregada.")

    def actualizar_filamento(self):
        if not self.id_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una bobina de la tabla.")
            return
        vals = self.validar_numeros()
        if not vals: return
        p_ini, p_act, costo = vals

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE filamentos SET marca=?, material=?, color_modelo=?, diametro=?, peso_inicial=?, peso_actual=?, costo=?, fecha_compra=?
            WHERE id=?
        """, (self.var_marca.get().strip(), self.var_material.get().strip(), self.var_color.get().strip(), self.var_diametro.get().strip(), p_ini, p_act, costo, self.var_fecha.get().strip(), self.id_seleccionado))
        conn.commit()
        conn.close()

        self.limpiar_formulario()
        self.cargar_datos()
        messagebox.showinfo("Actualizado", "Bobina actualizada.")

    def eliminar_filamento(self):
        if not self.id_seleccionado:
            messagebox.showwarning("Selección", "Selecciona una bobina.")
            return
        if messagebox.askyesno("Baja", f"¿Eliminar bobina #{self.id_seleccionado}?"):
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
        g = simpledialog.askfloat("Descontar", f"Gramos a descontar de '{self.var_marca.get()}':", minvalue=0.1)
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
        for item in self.tabla.selection():
            self.tabla.selection_remove(item)

    def cargar_datos(self):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        filtro = f"%{self.var_buscar.get().strip()}%"
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, marca, material, color_modelo, diametro, peso_inicial, peso_actual, costo, fecha_compra
            FROM filamentos WHERE marca LIKE ? OR material LIKE ? OR color_modelo LIKE ? ORDER BY id DESC
        """, (filtro, filtro, filtro))
        filas = cursor.fetchall()

        cursor.execute("SELECT id, marca, material, color_modelo, peso_inicial, peso_actual, costo FROM filamentos ORDER BY marca ASC")
        todas_bobinas = cursor.fetchall()
        conn.close()

        total_bobinas = len(filas)
        total_gramos = 0.0
        total_inversion = 0.0

        for f in filas:
            total_gramos += f[6]
            total_inversion += f[7]
            p_act = f[6]
            etiqueta = "alerta_roja" if p_act < 50 else ("alerta_amarilla" if p_act < 150 else "normal")
            self.tabla.insert("", "end", values=(
                f[0], f[1], f[2], f[3], f[4], f"{f[5]:.0f} g", f"{f[6]:.0f} g", f"${f[7]:.2f}", f[8]
            ), tags=(etiqueta,))

        self.lbl_resumen.config(
            text=f"Bobinas: {total_bobinas}  |  Restante: {total_gramos:,.0f} g ({total_gramos/1000:.2f} kg)  |  Inversión: ${total_inversion:,.2f}"
        )

        self.mapa_bobinas_calc.clear()
        opciones = []
        for b in todas_bobinas:
            eti = f"#{b[0]} - {b[1]} | {b[2]} {b[3]} (Quedan: {b[5]:.0f}g - ${b[6]:.2f})"
            opciones.append(eti)
            self.mapa_bobinas_calc[eti] = {"id": b[0], "marca": b[1], "material": b[2], "color": b[3], "peso_ini": b[4], "peso_act": b[5], "costo": b[6]}

        self.combo_bobinas_calc["values"] = opciones
        if opciones and self.var_calc_bobina.get() not in self.mapa_bobinas_calc:
            self.combo_bobinas_calc.current(0)
        self.calcular_costo_impresion()

    def exportar_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="inventario_filamentos.csv")
        if not ruta: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM filamentos ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()
        with open(ruta, mode="w", newline="", encoding="utf-8-sig") as archivo:
            writer = csv.writer(archivo)
            writer.writerow(["ID", "Marca", "Material", "Color", "Diametro", "Peso Inicial", "Peso Restante", "Costo", "Fecha"])
            writer.writerows(filas)
        messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InventarioFilamentosApp(root)
    root.mainloop()
