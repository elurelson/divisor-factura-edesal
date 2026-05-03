import json
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
HISTORY_FILE = APP_DIR / "historial_luz.json"
MONEY_PATTERN = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)")


def parse_number(value, allow_empty=False):
    cleaned = value.strip()
    if not cleaned:
        if allow_empty:
            return 0.0
        raise ValueError("empty")

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    elif "." in cleaned:
        whole, fraction = cleaned.split(".")
        if len(fraction) == 3 and whole.isdigit() and fraction.isdigit():
            cleaned = whole + fraction

    return float(cleaned)


def format_currency(value):
    formatted = f"{value:,.2f}"
    return "$" + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_number(value):
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def calculate_split(total_kwh, total_amount, my_kwh, fixed_amount=0):
    if total_kwh <= 0:
        raise ValueError("El consumo total debe ser mayor a cero.")
    if total_amount <= 0:
        raise ValueError("El importe total debe ser mayor a cero.")
    if my_kwh < 0:
        raise ValueError("Tu consumo no puede ser negativo.")
    if my_kwh > total_kwh:
        raise ValueError("Tu consumo no puede ser mayor al consumo total.")
    if fixed_amount < 0:
        raise ValueError("El cargo fijo no puede ser negativo.")
    if fixed_amount > total_amount:
        raise ValueError("El cargo fijo no puede ser mayor al importe total.")

    variable_amount = total_amount - fixed_amount
    price_per_kwh = variable_amount / total_kwh
    my_variable_amount = my_kwh * price_per_kwh
    my_fixed_amount = fixed_amount / 2
    grandmother_fixed_amount = fixed_amount / 2
    my_amount = my_variable_amount + my_fixed_amount
    grandmother_amount = total_amount - my_amount

    return {
        "price_per_kwh": price_per_kwh,
        "variable_amount": variable_amount,
        "my_variable_amount": my_variable_amount,
        "my_fixed_amount": my_fixed_amount,
        "grandmother_fixed_amount": grandmother_fixed_amount,
        "my_amount": my_amount,
        "grandmother_amount": grandmother_amount,
    }


def make_receipt(record):
    return (
        "Comprobante de division de factura de luz\n"
        "========================================\n"
        f"Fecha: {record['date']}\n\n"
        f"Consumo total: {format_number(record['total_kwh'])} kWh\n"
        f"Importe total: {format_currency(record['total_amount'])}\n"
        f"Cargo fijo total: {format_currency(record['fixed_amount'])}\n"
        f"Importe por consumo: {format_currency(record['result']['variable_amount'])}\n"
        f"Mi consumo: {format_number(record['my_kwh'])} kWh\n"
        f"Precio por kWh: {format_currency(record['result']['price_per_kwh'])}\n\n"
        f"Me corresponde pagar: {format_currency(record['result']['my_amount'])}\n"
        f"Le corresponde pagar a mi abuela: {format_currency(record['result']['grandmother_amount'])}\n\n"
        "Detalle\n"
        f"- Mi parte por consumo: {format_currency(record['result']['my_variable_amount'])}\n"
        f"- Mi parte del cargo fijo: {format_currency(record['result']['my_fixed_amount'])}\n"
        f"- Parte del cargo fijo de mi abuela: {format_currency(record['result']['grandmother_fixed_amount'])}\n"
    )


def read_pdf_text(path):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "Para leer PDFs instala pypdf con: python -m pip install pypdf"
        ) from error

    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def amount_from_line(line):
    matches = MONEY_PATTERN.findall(line)
    if not matches:
        return 0.0
    return parse_number(matches[-1])


def extract_invoice_data(text):
    active_match = re.search(r"Activa\s+\d+\s+\d+\s+[\d,.]+\s+(\d+)", text)
    total_kwh = float(active_match.group(1)) if active_match else 0.0

    all_amounts = MONEY_PATTERN.findall(text)
    total_amount = parse_number(all_amounts[-1]) if all_amounts else 0.0

    fixed_amount = 0.0
    variable_amount = 0.0
    penalties = 0.0
    taxes = 0.0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        amount = amount_from_line(line)
        if amount == 0:
            continue

        if line.startswith("Cargo Fijo") or line.startswith("Cargo Uso de Red"):
            fixed_amount += amount
        elif line.startswith("Cargo Variable"):
            variable_amount += amount
        elif line.startswith("Penalidad"):
            penalties += amount
        elif line.startswith("IVA ") or line.startswith("Contr. Municipal"):
            taxes += amount

    if total_kwh <= 0 or total_amount <= 0:
        raise ValueError("No pude detectar consumo total o importe total en el PDF.")

    return {
        "total_kwh": total_kwh,
        "total_amount": total_amount,
        "fixed_amount": fixed_amount,
        "variable_amount": variable_amount,
        "penalties": penalties,
        "taxes": taxes,
    }


class ElectricityBillCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculadora de factura de luz")
        self.geometry("860x520")
        self.minsize(820, 500)
        self.configure(bg="#eef1ee")

        self.total_kwh_var = tk.StringVar()
        self.total_amount_var = tk.StringVar()
        self.fixed_amount_var = tk.StringVar()
        self.my_kwh_var = tk.StringVar()
        self.result_var = tk.StringVar(value="Carga los datos y presiona Calcular.")
        self.pdf_summary_var = tk.StringVar(value="Ningun PDF cargado.")

        self.history = self.load_history()
        self.current_record = None

        self._configure_style()
        self._build_ui()
        self.refresh_history()

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#eef1ee")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#eef1ee", foreground="#1e2421", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1e2421")
        style.configure("Hint.TLabel", foreground="#5a655f")
        style.configure("Result.TLabel", background="#f8faf8", foreground="#1e2421", font=("Segoe UI", 11))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main = ttk.Frame(self, padding=18)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        title = ttk.Label(main, text="Dividir factura de luz", style="Title.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        left = ttk.Frame(main, style="Panel.TFrame", padding=16)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        left.columnconfigure(1, weight=1)

        right = ttk.Frame(main, style="Panel.TFrame", padding=16)
        right.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self._build_form(left)
        self._build_history(right)

    def _build_form(self, parent):
        form_title = ttk.Label(parent, text="Datos de la factura", font=("Segoe UI", 12, "bold"))
        form_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._add_input(parent, 1, "Consumo total (kWh)", self.total_kwh_var)
        self._add_input(parent, 2, "Importe total", self.total_amount_var)
        self._add_input(parent, 3, "Cargo fijo total (opcional)", self.fixed_amount_var)
        self._add_input(parent, 4, "Mi consumo (kWh)", self.my_kwh_var)

        hint = ttk.Label(
            parent,
            text="El cargo fijo se divide mitad y mitad. El resto se reparte por consumo.",
            style="Hint.TLabel",
            wraplength=350,
        )
        hint.grid(row=5, column=0, columnspan=2, sticky="w", pady=(3, 10))

        pdf_button = ttk.Button(parent, text="Cargar factura PDF", command=self.load_pdf_invoice)
        pdf_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        pdf_summary = ttk.Label(
            parent,
            textvariable=self.pdf_summary_var,
            style="Hint.TLabel",
            wraplength=350,
            justify="left",
        )
        pdf_summary.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 10))

        buttons = ttk.Frame(parent, style="Panel.TFrame")
        buttons.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)

        ttk.Button(buttons, text="Calcular", command=self.calculate, style="Accent.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(buttons, text="Limpiar", command=self.clear_form).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(buttons, text="Comprobante", command=self.save_receipt).grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )

        result = ttk.Label(
            parent,
            textvariable=self.result_var,
            style="Result.TLabel",
            justify="left",
            anchor="nw",
            padding=14,
            wraplength=360,
        )
        result.grid(row=9, column=0, columnspan=2, sticky="nsew")
        parent.rowconfigure(9, weight=1)

    def _build_history(self, parent):
        header = ttk.Label(parent, text="Historial", font=("Segoe UI", 12, "bold"))
        header.grid(row=0, column=0, sticky="w", pady=(0, 10))

        columns = ("date", "my_amount", "grandmother_amount")
        self.history_tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        self.history_tree.heading("date", text="Fecha")
        self.history_tree.heading("my_amount", text="Yo")
        self.history_tree.heading("grandmother_amount", text="Abuela")
        self.history_tree.column("date", width=150, anchor="w")
        self.history_tree.column("my_amount", width=90, anchor="e")
        self.history_tree.column("grandmother_amount", width=90, anchor="e")
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        self.history_tree.bind("<<TreeviewSelect>>", self.select_history_item)

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.history_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(parent, style="Panel.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        ttk.Button(actions, text="Ver comprobante", command=self.show_selected_receipt).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions, text="Borrar historial", command=self.clear_history).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

    def _add_input(self, parent, row, label, variable):
        label_widget = ttk.Label(parent, text=label)
        label_widget.grid(row=row, column=0, sticky="w", pady=7)

        entry = ttk.Entry(parent, textvariable=variable, justify="right", font=("Segoe UI", 11))
        entry.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=7)

    def calculate(self):
        try:
            total_kwh = parse_number(self.total_kwh_var.get())
            total_amount = parse_number(self.total_amount_var.get())
            fixed_amount = parse_number(self.fixed_amount_var.get(), allow_empty=True)
            my_kwh = parse_number(self.my_kwh_var.get())
            result = calculate_split(total_kwh, total_amount, my_kwh, fixed_amount)
        except ValueError as error:
            self.show_value_error(error)
            return

        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_kwh": total_kwh,
            "total_amount": total_amount,
            "fixed_amount": fixed_amount,
            "my_kwh": my_kwh,
            "result": result,
        }
        self.current_record = record
        self.history.insert(0, record)
        self.save_history()
        self.refresh_history()
        self.show_result(record)

    def show_result(self, record):
        result = record["result"]
        self.result_var.set(
            "Resultado\n"
            f"Precio por kWh: {format_currency(result['price_per_kwh'])}\n"
            f"Importe por consumo: {format_currency(result['variable_amount'])}\n"
            f"Cargo fijo dividido: {format_currency(result['my_fixed_amount'])} cada uno\n\n"
            f"Te corresponde pagar: {format_currency(result['my_amount'])}\n"
            f"Le corresponde pagar a tu abuela: {format_currency(result['grandmother_amount'])}"
        )

    def show_value_error(self, error):
        if str(error) == "empty":
            message = "Completa todos los campos obligatorios antes de calcular."
        elif "could not convert" in str(error):
            message = "Ingresa solo numeros validos. Podes usar coma o punto decimal."
        else:
            message = str(error)

        messagebox.showerror("Datos invalidos", message)

    def clear_form(self):
        self.total_kwh_var.set("")
        self.total_amount_var.set("")
        self.fixed_amount_var.set("")
        self.my_kwh_var.set("")
        self.current_record = None
        self.result_var.set("Carga los datos y presiona Calcular.")
        self.pdf_summary_var.set("Ningun PDF cargado.")
        self.history_tree.selection_remove(self.history_tree.selection())

    def load_pdf_invoice(self):
        path = filedialog.askopenfilename(
            title="Cargar factura PDF",
            filetypes=(("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return

        try:
            text = read_pdf_text(path)
            data = extract_invoice_data(text)
        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror("No se pudo leer el PDF", str(error))
            return

        self.total_kwh_var.set(format_number(data["total_kwh"]))
        self.total_amount_var.set(format_number(data["total_amount"]))
        self.fixed_amount_var.set(format_number(data["fixed_amount"]) if data["fixed_amount"] else "")
        self.current_record = None
        self.result_var.set("PDF cargado. Ingresa tu consumo y presiona Calcular.")
        self.pdf_summary_var.set(
            "Detectado del PDF:\n"
            f"Consumo total: {format_number(data['total_kwh'])} kWh\n"
            f"Total factura: {format_currency(data['total_amount'])}\n"
            f"Cargos fijos y uso de red: {format_currency(data['fixed_amount'])}\n"
            f"Cargos variables: {format_currency(data['variable_amount'])}\n"
            f"Mora: {format_currency(data['penalties'])}\n"
            f"Impuestos: {format_currency(data['taxes'])}"
        )

    def load_history(self):
        if not HISTORY_FILE.exists():
            return []

        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []

        return data if isinstance(data, list) else []

    def save_history(self):
        with HISTORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.history, file, ensure_ascii=False, indent=2)

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for index, record in enumerate(self.history):
            self.history_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    record["date"],
                    format_currency(record["result"]["my_amount"]),
                    format_currency(record["result"]["grandmother_amount"]),
                ),
            )

    def get_selected_record(self):
        selection = self.history_tree.selection()
        if not selection:
            return None

        index = int(selection[0])
        if index < 0 or index >= len(self.history):
            return None
        return self.history[index]

    def select_history_item(self, _event=None):
        record = self.get_selected_record()
        if record is None:
            return

        self.current_record = record
        self.total_kwh_var.set(format_number(record["total_kwh"]))
        self.total_amount_var.set(format_number(record["total_amount"]))
        self.fixed_amount_var.set(format_number(record["fixed_amount"]) if record["fixed_amount"] else "")
        self.my_kwh_var.set(format_number(record["my_kwh"]))
        self.show_result(record)

    def show_selected_receipt(self):
        record = self.get_selected_record() or self.current_record
        if record is None:
            messagebox.showinfo("Sin comprobante", "Primero calcula o selecciona un item del historial.")
            return

        receipt_window = tk.Toplevel(self)
        receipt_window.title("Comprobante")
        receipt_window.geometry("560x440")

        text = tk.Text(receipt_window, wrap="word", font=("Consolas", 10), padx=12, pady=12)
        text.pack(fill="both", expand=True)
        text.insert("1.0", make_receipt(record))
        text.configure(state="disabled")

    def save_receipt(self):
        record = self.current_record
        if record is None:
            messagebox.showinfo("Sin comprobante", "Primero realiza un calculo.")
            return

        default_name = "comprobante_luz_" + datetime.now().strftime("%Y%m%d_%H%M") + ".txt"
        path = filedialog.asksaveasfilename(
            title="Guardar comprobante",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=(("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return

        try:
            Path(path).write_text(make_receipt(record), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("No se pudo guardar", str(error))
            return

        messagebox.showinfo("Comprobante guardado", "El comprobante se guardo correctamente.")

    def clear_history(self):
        if not self.history:
            return

        confirmed = messagebox.askyesno("Borrar historial", "Seguro que queres borrar todo el historial?")
        if not confirmed:
            return

        self.history = []
        self.current_record = None
        self.save_history()
        self.refresh_history()


if __name__ == "__main__":
    app = ElectricityBillCalculator()
    app.mainloop()
