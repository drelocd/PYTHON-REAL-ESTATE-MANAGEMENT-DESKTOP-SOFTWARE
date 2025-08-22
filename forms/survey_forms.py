import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
from PIL import Image, ImageTk
import shutil
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from tkcalendar import DateEntry

# Assuming database.py is in the same directory or accessible via PYTHONPATH
from database import DatabaseManager

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')

# Data and Receipts
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
os.makedirs(RECEIPTS_DIR, exist_ok=True)  # Ensure receipts directory exists

try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Import Error", "The 'tkcalendar' library is not found. "
                                         "Please install it using: pip install tkcalendar")
    DateEntry = None

# Import ReportLab components for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    print("ReportLab not found. PDF receipt generation will be disabled.")

# Import functions and directories directly from file_manager
try:
    from utils.file_manager import save_files, SURVEY_ATTACHMENTS_DIR, get_full_path
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import file_manager: {e}. Ensure utils/file_manager.py exists.")
    save_files = None
    SURVEY_ATTACHMENTS_DIR = None
    get_full_path = None


class SuccessMessage(tk.Toplevel):
    def __init__(self, master, success, message, pdf_path="", parent_icon_loader=None):
        super().__init__(master)
        self.title("Notification")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        self._icon_photo_ref = None  # Keep strong reference to PhotoImage

        if parent_icon_loader:
            icon_name = "success.png" if success else "error.png"
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._icon_photo_ref = icon_image  # Store strong reference
            except Exception as e:
                print(f"Failed to set icon for SuccessMessage: {e}")

        lbl = ttk.Label(self, text=message, font=('Helvetica', 10), wraplength=300, justify=tk.CENTER)
        lbl.pack(padx=20, pady=10)

        if success and pdf_path and _REPORTLAB_AVAILABLE:  # Only show Open button if PDF was actually generated
            open_btn = ttk.Button(self, text="Open Report Folder", command=lambda: os.startfile(
                os.path.dirname(pdf_path)))  # Open parent directory of PDF
            open_btn.pack(pady=5)

        ok_btn = ttk.Button(self, text="OK", command=self.destroy)
        ok_btn.pack(pady=10)

        self.update_idletasks()
        x = master.winfo_x() + master.winfo_width() // 2 - self.winfo_width() // 2
        y = master.winfo_y() + master.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")


class AddSurveyJobForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None,
                 window_icon_name="add_survey.png", current_user_id=None):
        super().__init__(master)

        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None

        self.add_icon_ref = None
        self.cancel_icon_ref = None
        self.attach_icon_ref = None
        self.current_user_id = current_user_id

        self.selected_files = []
        self.all_clients = []  # Store all clients for filtering
        self.client_name_to_id = {}  # Map client name to ID
        self.client_id_to_details = {}  # Map client ID to full details

        self.balance_var = tk.StringVar(self, value="0.00")
        self.selected_client_id = None  # To store the ID of the selected client

        self._set_window_properties(600, 520, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader)
        self._load_clients_for_combobox()  # Load clients when the form initializes

        if os.name != 'nt' or not hasattr(self, '_original_wm_protocol'):
            self.protocol("WM_DELETE_WINDOW", self._on_closing)
        else:
            self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._update_balance_display()

    def _customize_title_bar(self):
        """Customizes the title bar appearance. Attempts Windows-specific
        customization, falls back to a custom Tkinter title bar."""
        try:
            if os.name == 'nt':  # Windows-specific title bar customization
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
                self.title("Register New Survey Job")
            else:
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize native title bar: {e}. Falling back to custom Tkinter title bar.")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar when native customization isn't available."""
        self.overrideredirect(True)

        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=40)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text="Register New Survey Job",
            bg='#004080',
            fg='white',
            font=('Helvetica', 10, 'bold')
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=5)

        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#004080',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5, pady=5)

        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)
        close_button.bind('<Button-1>', self._save_drag_start_pos)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Client Name:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.client_combobox = ttk.Combobox(main_frame, state="normal")  # Can be 'readonly' or 'normal'
        self.client_combobox.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.client_combobox.bind("<<ComboboxSelected>>", self._on_client_selected)
        self.client_combobox.bind("<KeyRelease>", self._filter_clients)  # For auto-suggestion
        row += 1

        ttk.Label(main_frame, text="Client Contact:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_client_contact = ttk.Entry(main_frame)  # Changed from Label to Entry
        self.entry_client_contact.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Location:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_location = ttk.Entry(main_frame)
        self.entry_location.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=5, padx=5)
        self.text_description = tk.Text(main_frame, height=4, wrap=tk.WORD)
        self.text_description.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Agreed Price (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_price = ttk.Entry(main_frame)
        self.entry_price.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.entry_price.bind("<KeyRelease>", self._update_balance_display)
        row += 1

        ttk.Label(main_frame, text="Deposit (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_amount_paid = ttk.Entry(main_frame)
        self.entry_amount_paid.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.entry_amount_paid.insert(0, "0.00")
        self.entry_amount_paid.bind("<KeyRelease>", self._update_balance_display)
        row += 1

        ttk.Label(main_frame, text="Balance (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.label_balance = ttk.Label(main_frame, textvariable=self.balance_var, font=('Helvetica', 10, 'bold'),
                                       foreground='green')
        self.label_balance.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Deadline Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        if DateEntry:
            self.datepicker_deadline = DateEntry(main_frame, selectmode='day',
                                                 year=datetime.now().year, month=datetime.now().month,
                                                 day=datetime.now().day, date_pattern='yyyy-mm-dd')
            self.datepicker_deadline.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            default_deadline = datetime.now() + timedelta(days=365)
            self.datepicker_deadline.set_date(default_deadline)
        else:
            self.entry_deadline_fallback = ttk.Entry(main_frame)
            self.entry_deadline_fallback.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            self.entry_deadline_fallback.insert(0, (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"))
        row += 1

        ttk.Label(main_frame, text="Attachments (Max 5):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        file_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=0)

        self.listbox_files = tk.Listbox(file_frame, height=3, selectmode=tk.SINGLE)
        self.listbox_files.grid(row=0, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.listbox_files.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox_files.config(yscrollcommand=scrollbar.set)

        if parent_icon_loader:
            self.attach_icon_ref = parent_icon_loader("attach.png", size=(20, 20))

        ttk.Button(file_frame, text="Add Files", image=self.attach_icon_ref, compound=tk.LEFT,
                   command=self._add_files).grid(row=1, column=0, columnspan=2, pady=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        if parent_icon_loader:
            self.add_icon_ref = parent_icon_loader("add_job.png", size=(20, 20))
            self.cancel_icon_ref = parent_icon_loader("cancel.png", size=(20, 20))

        ttk.Button(button_frame, text="Add Survey Job", image=self.add_icon_ref, compound=tk.LEFT,
                   command=self._add_survey_job).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", image=self.cancel_icon_ref, compound=tk.LEFT,
                   command=self._on_closing).pack(side="right", padx=10)

    def _load_clients_for_combobox(self):
        """Loads all clients from the database and populates the combobox."""
        self.all_clients = self.db_manager.get_all_clients()
        client_names = []
        self.client_name_to_id = {}
        self.client_id_to_details = {}

        for client in self.all_clients:
            client_name = client['name']
            client_id = client['client_id']
            client_names.append(client_name)
            self.client_name_to_id[client_name] = client_id
            self.client_id_to_details[client_id] = client

        self.client_combobox['values'] = sorted(client_names)
        self.client_combobox.set("")  # Clear any initial selection

    def _filter_clients(self, event):
        """Filters the client combobox based on user input for auto-suggestion."""
        search_text = self.client_combobox.get().strip().lower()
        if not search_text:
            self.client_combobox['values'] = sorted([c['name'] for c in self.all_clients])
            self.entry_client_contact.delete(0, tk.END)  # Clear contact if text is cleared
            self.selected_client_id = None
            return

        filtered_names = []
        for client in self.all_clients:
            if search_text in client['name'].lower() or search_text in client['contact_info'].lower():
                filtered_names.append(client['name'])

        self.client_combobox['values'] = sorted(filtered_names)
        # If there's only one exact match, select it
        if len(filtered_names) == 1 and filtered_names[0].lower() == search_text:
            self.client_combobox.set(filtered_names[0])
            self._on_client_selected(event)  # Manually trigger selection logic
        else:
            # If the current text doesn't match a selected client, clear contact and ID
            current_name_in_box = self.client_combobox.get()
            if current_name_in_box not in self.client_name_to_id:
                self.entry_client_contact.delete(0, tk.END)
                self.selected_client_id = None

    def _on_client_selected(self, event):
        """Handles selection of a client from the combobox."""
        selected_name = self.client_combobox.get()
        client_id = self.client_name_to_id.get(selected_name)

        if client_id:
            self.selected_client_id = client_id
            client_details = self.client_id_to_details.get(client_id)
            if client_details:
                self.entry_client_contact.delete(0, tk.END)  # Clear existing text
                self.entry_client_contact.insert(0, client_details['contact_info'])  # Insert new contact
            else:
                self.entry_client_contact.delete(0, tk.END)
                self.entry_client_contact.insert(0, "Contact not found")
        else:
            self.selected_client_id = None
            self.entry_client_contact.delete(0, tk.END)  # Clear contact if no client is selected or new text typed

    def _add_files(self):
        filetypes = [
            ("PDF Documents", "*.pdf"),
            ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("Text Documents", "*.txt"),
            ("All Files", "*.*")
        ]

        file_paths = filedialog.askopenfilenames(
            title="Select Attachment Files",
            initialdir=os.path.expanduser("~"),
            filetypes=filetypes
        )

        if file_paths:
            self.selected_files = []
            self.listbox_files.delete(0, tk.END)

            for path in file_paths:
                if len(self.selected_files) < 5:
                    self.selected_files.append(path)
                    self.listbox_files.insert(tk.END, os.path.basename(path))
                else:
                    messagebox.showwarning("File Limit Exceeded", "You can select a maximum of 5 files.")
                    break

    def _update_balance_display(self, event=None):
        """Calculates and updates the balance display in real-time."""
        try:
            agreed_price = float(self.entry_price.get() or "0.0")
        except ValueError:
            agreed_price = 0.0

        try:
            paid_amount = float(self.entry_amount_paid.get() or "0.0")
        except ValueError:
            paid_amount = 0.0

        calculated_balance = agreed_price - paid_amount
        self.balance_var.set(f"{calculated_balance:,.2f}")  # Format with commas for thousands

        if calculated_balance > 0:
            self.label_balance.config(foreground='black')
        elif calculated_balance < 0:
            self.label_balance.config(foreground='red')
        else:
            self.label_balance.config(foreground='green')

    def _generate_job_creation_receipt(self, job_info, client_info):
        """
        Generates a PDF receipt for a newly created survey job, including initial payment.
        Returns the path to the generated PDF, or None if generation fails.
        """
        if not _REPORTLAB_AVAILABLE:
            messagebox.showwarning("Feature Unavailable",
                                   "ReportLab library is not installed. Cannot generate PDF receipts. "
                                   "Please install it using: pip install reportlab")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            receipt_filename = f"Job_Creation_Receipt_Job_{job_info['job_id']}_{timestamp}.pdf"
            pdf_path = os.path.join(RECEIPTS_DIR, receipt_filename)

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Custom styles
            styles.add(
                ParagraphStyle(name='TitleStyle', alignment=1, fontName='Helvetica-Bold', fontSize=16, spaceAfter=10))
            styles.add(
                ParagraphStyle(name='HeadingStyle', alignment=0, fontName='Helvetica-Bold', fontSize=12, spaceAfter=6))
            styles.add(ParagraphStyle(name='NormalStyle', alignment=0, fontName='Helvetica', fontSize=10, spaceAfter=3))
            styles.add(
                ParagraphStyle(name='BoldValue', alignment=0, fontName='Helvetica-Bold', fontSize=10, spaceAfter=3))
            styles.add(
                ParagraphStyle(name='SignatureLine', alignment=0, fontName='Helvetica', fontSize=10, spaceBefore=40))

            story = []

            # Company Header
            story.append(Paragraph("<b>Mathenge's Real Estate Management System</b>", styles['TitleStyle']))
            story.append(Paragraph("Receipt for New Survey Job Registration", styles['h3']))
            story.append(Spacer(1, 0.2 * inch))

            # Receipt Details
            story.append(Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                   styles['NormalStyle']))
            story.append(Paragraph(f"<b>Job ID:</b> {job_info['job_id']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.1 * inch))

            # Client Details
            story.append(Paragraph("<b>Client Details:</b>", styles['HeadingStyle']))
            story.append(Paragraph(f"Name: {client_info['name']}", styles['NormalStyle']))
            story.append(Paragraph(f"Contact: {client_info['contact_info']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.2 * inch))

            # Job Details
            story.append(Paragraph("<b>Survey Job Summary:</b>", styles['HeadingStyle']))
            story.append(Paragraph(f"Location: {job_info['property_location']}", styles['NormalStyle']))
            story.append(Paragraph(f"Description: {job_info['job_description']}", styles['NormalStyle']))
            story.append(Paragraph(f"Deadline: {job_info['deadline']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.1 * inch))

            # Financial Summary Table
            financial_data = [
                ['Description', 'Amount (KES)'],
                ['Agreed Total Fee', f"{job_info['fee']:,.2f}"],
                ['Deposit at Registration', f"{job_info['amount_paid']:,.2f}"],
                ['Current Balance Due', f"{job_info['balance']:,.2f}"]
            ]

            financial_table = Table(financial_data, colWidths=[3.5 * inch, 2.0 * inch])
            financial_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Align amounts to the right
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Make balance bold
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.green if job_info['balance'] <= 0 else colors.orange)
                # Color balance
            ]))
            story.append(financial_table)
            story.append(Spacer(1, 0.3 * inch))

            # Footer
            story.append(Paragraph("This receipt confirms the registration of a new survey job "
                                   "and any initial payment received.", styles['NormalStyle']))
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Thank you for your business!", styles['HeadingStyle']))
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph("_________________________", styles['SignatureLine']))
            story.append(Paragraph("Authorized Signature", styles['NormalStyle']))

            doc.build(story)
            return pdf_path

        except Exception as e:
            messagebox.showerror("Receipt Generation Error", f"An error occurred while generating the receipt: {e}")
            print(f"Error generating job creation receipt: {e}")
            return None

    def _add_survey_job(self):
        client_name = self.client_combobox.get().strip()
        client_contact = self.entry_client_contact.get().strip()  # Get contact from Entry
        location = self.entry_location.get().strip()
        description = self.text_description.get("1.0", tk.END).strip()
        price_str = self.entry_price.get().strip()
        amount_paid_str = self.entry_amount_paid.get().strip()

        deadline_date_str = ""
        if DateEntry and hasattr(self, 'datepicker_deadline'):
            try:
                deadline_date_str = self.datepicker_deadline.get_date().strftime("%Y-%m-%d")
            except Exception:
                messagebox.showerror("Input Error", "Please select a valid Deadline Date.")
                return
        elif hasattr(self, 'entry_deadline_fallback'):
            deadline_date_str = self.entry_deadline_fallback.get().strip()
            try:
                datetime.strptime(deadline_date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Input Error", "Invalid date format for Deadline Date. Use YYYY-MM-DD.")
                return
        else:
            messagebox.showerror("Input Error", "Deadline Date input widget not found.")
            return

        created_at_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not all([client_name, client_contact, location, price_str, amount_paid_str, deadline_date_str]):
            messagebox.showerror("Input Error", "All required fields are necessary.")
            return

        try:
            agreed_price = float(price_str)
            if agreed_price <= 0:
                messagebox.showerror("Input Error", "Agreed Price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Agreed Price. Please enter a number.")
            return

        try:
            paid_amount = float(amount_paid_str)
            if paid_amount < 0:
                messagebox.showerror("Input Error", "DEPOSIT cannot be negative.")
                return
            # NEW VALIDATION: Amount Paid cannot be more than the Fee
            if paid_amount > agreed_price:
                messagebox.showerror("Input Error", "DEPOSIT cannot be more than the Agreed Fee.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for DEPOSIT. Please enter a number.")
            return

        calculated_balance = agreed_price - paid_amount

        # NEW VALIDATION: Balance should not be a negative number
        if calculated_balance < 0:
            # This should ideally not happen if paid_amount > agreed_price is caught above,
            # but as a safeguard.
            messagebox.showerror("Input Error",
                                 "Calculated Balance cannot be negative. Please check fee and amount paid.")
            return

        try:
            client_id = self.selected_client_id  # Use the ID from combobox selection
            full_client_info = None

            if client_id:  # An existing client was selected
                full_client_info = self.client_id_to_details.get(client_id)
                # Ensure client_name and client_contact match the selected client
                if full_client_info and (
                        full_client_info['name'] != client_name or full_client_info['contact_info'] != client_contact):
                    # This scenario means user typed something different after selecting, or manually edited.
                    # For simplicity, if an ID is selected, we prioritize its details.
                    # If you want to allow editing, you'd need more complex logic here.
                    client_name = full_client_info['name']
                    client_contact = full_client_info['contact_info']
            else:  # No existing client selected, attempt to find or add
                client = self.db_manager.get_client_by_contact_info(client_contact)
                if client:
                    client_id = client['client_id']
                    full_client_info = client
                    if client['name'] != client_name:
                        if not self.db_manager.update_client(client_id, name=client_name):
                            messagebox.showwarning("Database Warning", "Could not update existing client name.")
                else:
                    client_id = self.db_manager.add_client(client_name, client_contact,
                                                           added_by_user_id=self.current_user_id)
                    if not client_id:
                        messagebox.showerror("Database Error",
                                             "Failed to add new client. Contact info might already exist.")
                        return
                    full_client_info = self.db_manager.get_client_by_id(client_id)  # Fetch newly added client details

            job_id = self.db_manager.add_survey_job(
                client_id=client_id,
                property_location=location,
                job_description=description,
                fee=agreed_price,
                deadline=deadline_date_str,
                amount_paid=paid_amount,
                balance=calculated_balance,
                status='Pending',
                attachments_path=None,  # This is for other attachments, not the auto-generated receipt
                added_by_user_id=self.current_user_id,
                created_at=created_at_timestamp
            )

            if job_id:
                receipt_pdf_path = None
                if full_client_info:  # Ensure client info is available for receipt
                    job_info_for_receipt = {
                        'job_id': job_id,
                        'property_location': location,
                        'job_description': description,
                        'fee': agreed_price,
                        'amount_paid': paid_amount,
                        'balance': calculated_balance,
                        'deadline': deadline_date_str,
                        'status': 'Pending',
                        'created_at': created_at_timestamp
                    }
                    try:
                        receipt_pdf_path = self._generate_job_creation_receipt(job_info_for_receipt, full_client_info)
                    except Exception as e:
                        messagebox.showwarning("Receipt Generation Error", f"Failed to generate receipt PDF: {e}")
                        print(f"Error generating receipt: {e}")

                if receipt_pdf_path:
                    # Update the newly added survey job with the receipt path
                    if self.db_manager.update_survey_job_receipt_path(job_id, receipt_pdf_path):
                        # Ask user to print the receipt
                        response = messagebox.askyesno(
                            "Success & Print",
                            f"Survey Job added with ID: {job_id} and receipt generated at:\n{receipt_pdf_path}\n\nDo you want to print this receipt?",
                            detail="Click 'Yes' to print, 'No' to close."
                        )
                        if response:
                            try:
                                # Use default system PDF viewer/printer (cross-platform approach)
                                import subprocess
                                if os.name == 'nt':  # For Windows
                                    os.startfile(receipt_pdf_path, "print")
                                elif os.sys.platform == 'darwin':  # For macOS
                                    subprocess.run(['open', '-a', 'Preview', '-p', receipt_pdf_path])
                                else:  # For Linux/Unix
                                    subprocess.run(['lp', receipt_pdf_path])  # or 'lpr'
                                messagebox.showinfo("Print Status", "Print command sent successfully.")
                            except Exception as print_e:
                                messagebox.showwarning("Print Error",
                                                       f"Could not send print command:\n{print_e}\nYou may need to print manually from {receipt_pdf_path}")
                                print(f"Error printing PDF: {print_e}")
                        else:
                            messagebox.showinfo("Success", f"Survey Job added with ID: {job_id} and receipt generated.")
                    else:
                        messagebox.showwarning("Database Update Warning",
                                               f"Survey Job added with ID: {job_id}, receipt generated but failed to save path in DB.")
                else:
                    messagebox.showwarning("Receipt Warning",
                                           f"Survey Job added with ID: {job_id}, but receipt generation failed or path was not returned.")

                # Handle other attachments
                survey_attachments_paths_str = None
                if self.selected_files:
                    if save_files and SURVEY_ATTACHMENTS_DIR:
                        try:
                            survey_attachments_paths_str = save_files(self.selected_files, SURVEY_ATTACHMENTS_DIR)
                            if survey_attachments_paths_str is None:
                                messagebox.showwarning("File Save Error", "Survey job attachments could not be saved.")
                            else:
                                self.db_manager.update_survey_job_attachments(job_id, survey_attachments_paths_str)
                                messagebox.showinfo("Attachments", "Additional attachments saved.")
                        except Exception as e:
                            messagebox.showwarning("File Save Error", f"Failed to save attachments: {e}")
                            print(f"Error saving attachments: {e}")
                    else:
                        messagebox.showwarning("File Manager Missing",
                                               "File saving functionality for attachments not available.")

                # Final success message, if no specific messages were already shown by receipt/attachments
                if not receipt_pdf_path and (not self.selected_files or survey_attachments_paths_str is None):
                    messagebox.showinfo("Success", f"Survey Job added with ID: {job_id}")

                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add survey job to the database.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            print(f"Error adding survey job: {e}")

    def _on_closing(self):
        """Handles window closing by releasing grab and destroying the window."""
        if self.master.winfo_exists():  # Check if master still exists before releasing grab
            self.grab_release()
        self.destroy()


# Mock the original ManagePaymentForm (now specifically for adding a single payment to a job)
class RecordSinglePaymentForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None,
                 window_icon_name="payment.png", job_id_to_pay=None):
        super().__init__(master)
        self.title("Record Payment for Survey Job" + (f" ID {job_id_to_pay}" if job_id_to_pay else ""))
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        # Set blue title bar (Windows only)
        try:
            from ctypes import windll, byref, sizeof, c_int
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            hwnd = windll.user32.GetParent(self.winfo_id())
            # Blue color (RGB: 0, 119, 215) -> 0x00D77700 in BGR
            color = c_int(0x00D77700)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
            # White text
            text_color = c_int(0x00FFFFFF)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
        except Exception as e:
            print(f"Could not customize title bar: {e}")

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self.job_id_to_pay = job_id_to_pay

        self._window_icon_ref = None
        self._record_payment_icon = None
        self._cancel_payment_icon = None

        self._set_window_properties(500, 300, window_icon_name, parent_icon_loader)
        self._create_widgets(parent_icon_loader)
        self._load_job_details()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Job ID:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_job_id = ttk.Label(main_frame, text=self.job_id_to_pay, font=('Helvetica', 10, 'bold'))
        self.lbl_job_id.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Client:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_client_name = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_client_name.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Fee (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_fee = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_fee.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Amount Paid (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_amount_paid = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_amount_paid.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Current Balance:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_current_balance = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10, 'bold'),
                                             foreground='red')
        self.lbl_current_balance.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Payment Amount (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_payment_amount = ttk.Entry(main_frame)
        self.entry_payment_amount.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        if parent_icon_loader:
            self._record_payment_icon = parent_icon_loader("save.png", size=(20, 20))
            self._cancel_payment_icon = parent_icon_loader("cancel.png", size=(20, 20))

        record_btn = ttk.Button(button_frame, text="Record Payment", image=self._record_payment_icon,
                                compound=tk.LEFT, command=self.record_payment_action)
        record_btn.pack(side="left", padx=5)
        record_btn.image = self._record_payment_icon  # Fixed this line - was using wrong variable name

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_payment_icon,
                                compound=tk.LEFT, command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_payment_icon

    def _load_job_details(self):
        if self.job_id_to_pay:
            job_info = self.db_manager.get_survey_job_by_id(self.job_id_to_pay)
            if job_info:
                client_info = self.db_manager.get_client_by_id(job_info['client_id'])
                self.lbl_client_name.config(text=client_info['name'] if client_info else "N/A")
                self.lbl_fee.config(text=f"KES {job_info['fee']:,.2f}")
                self.lbl_amount_paid.config(text=f"KES {job_info['amount_paid']:,.2f}")

                # Calculate and display current balance
                balance = job_info['fee'] - job_info['amount_paid']
                self.lbl_current_balance.config(text=f"KES {balance:,.2f}")

                if balance <= 0:
                    self.lbl_current_balance.config(foreground='green')
                    self.entry_payment_amount.config(state='disabled')
                else:
                    self.lbl_current_balance.config(foreground='red')
            else:
                messagebox.showerror("Error", "Job not found.")
                self.destroy()

    def record_payment_action(self):  # Fixed method name (removed underscore)
        payment_amount_str = self.entry_payment_amount.get().strip()

        if not payment_amount_str:
            messagebox.showerror("Input Error", "Payment amount is required.")
            return

        try:
            payment_amount = float(payment_amount_str)
            if payment_amount <= 0:
                messagebox.showerror("Invalid Amount", "Payment amount must be positive.")
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the payment amount.")
            return

        job_info = self.db_manager.get_survey_job_by_id(self.job_id_to_pay)
        if not job_info:
            messagebox.showerror("Error", "Job information could not be retrieved.")
            return

        current_balance = job_info['fee'] - job_info['amount_paid']

        if payment_amount > current_balance:
            messagebox.showerror(
                "Payment Error",
                f"Cannot process payment. Amount (KES {payment_amount:,.2f}) exceeds balance (KES {current_balance:,.2f}).\n"
                "Please enter a lower amount that doesn't exceed the outstanding balance."
            )
            return

        # Calculate new amount_paid (add to existing amount)
        new_amount_paid = job_info['amount_paid'] + payment_amount

        # Update the database
        success = self.db_manager.update_survey_job(
            self.job_id_to_pay,
            amount_paid=new_amount_paid,
            balance=job_info['fee'] - new_amount_paid
        )

        if success:
            messagebox.showinfo("Success", f"Payment of KES {payment_amount:,.2f} recorded successfully!")
            self.refresh_callback()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to record payment in database.")

    def _on_closing(self):
        self.grab_release()
        self.destroy()


# --- ManageSurveyJobsFrame (The main table view for jobs) ---
class PaymentSurveyJobsFrame(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_main_view_callback=None, parent_icon_loader=None,
                 window_icon_name="payment.png"):
        super().__init__(master)
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self.title("Manage Survey Payments")

        self.db_manager = db_manager
        self.refresh_main_view_callback = refresh_main_view_callback
        self.parent_icon_loader = parent_icon_loader

        self.current_page = 1
        self.items_per_page = 15
        self.total_jobs = 0
        self.total_pages = 0
        self.all_jobs_data = []
        self.selected_job_data = None

        # Filter variables
        self.filter_client_name = tk.StringVar(self, value="")
        self.filter_location = tk.StringVar(self, value="")
        self.filter_start_date = tk.StringVar(self, value="")
        self.filter_end_date = tk.StringVar(self, value="")

        # Icon references
        self._icons = {}
        self._window_icon_ref = None

        self._set_window_properties(1000, 600, window_icon_name, parent_icon_loader)
        self._customize_title_bar()
        self._create_widgets()
        self._apply_filters()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to blue (RGB: 0, 119, 215) -> 0x00D77700 in BGR
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
        except Exception as e:
            print(f"Could not customize title bar: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Filter Frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filter_frame.pack(padx=10, pady=5, fill="x")

        # Filter Grid
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill="x", padx=5, pady=5)

        # Client Name Filter
        ttk.Label(filter_grid, text="Client Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(filter_grid, textvariable=self.filter_client_name).grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Location Filter
        ttk.Label(filter_grid, text="Location:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(filter_grid, textvariable=self.filter_location).grid(row=0, column=3, sticky="ew", padx=5, pady=2)

        # Date Range Filters
        ttk.Label(filter_grid, text="From Date:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.start_date_entry = DateEntry(filter_grid, selectmode='day', date_pattern='yyyy-mm-dd',
                                          textvariable=self.filter_start_date)
        self.start_date_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.start_date_entry.set_date(None)

        ttk.Label(filter_grid, text="To Date:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.end_date_entry = DateEntry(filter_grid, selectmode='day', date_pattern='yyyy-mm-dd',
                                        textvariable=self.filter_end_date)
        self.end_date_entry.grid(row=1, column=3, sticky="ew", padx=5, pady=2)
        self.end_date_entry.set_date(None)

        # Filter Buttons
        button_frame = ttk.Frame(filter_frame)
        button_frame.pack(fill="x", pady=5)

        # Load icons
        if self.parent_icon_loader:
            self._search_icon = self.parent_icon_loader("search.png", size=(20, 20))
            self._clear_icon = self.parent_icon_loader("clear_filter.png", size=(20, 20))

        ttk.Button(button_frame, text="Apply Filters", image=self._search_icon, compound=tk.LEFT,
                   command=self._apply_filters).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear Filters", image=self._clear_icon, compound=tk.LEFT,
                   command=self._clear_filters).pack(side="left", padx=5)

        # Treeview
        columns = ("Date", "Time", "Client Name", "Location", "Fee", "Paid", "Balance")
        self.job_tree = ttk.Treeview(main_frame, columns=columns, show="headings", style='Treeview')

        # Configure columns
        self.job_tree.heading("Date", text="Date", anchor=tk.CENTER)
        self.job_tree.heading("Time", text="Time", anchor=tk.CENTER)
        self.job_tree.heading("Client Name", text="Client Name", anchor=tk.W)
        self.job_tree.heading("Location", text="Location", anchor=tk.W)
        self.job_tree.heading("Fee", text="Fee (KES)", anchor=tk.E)
        self.job_tree.heading("Paid", text="Paid (KES)", anchor=tk.E)
        self.job_tree.heading("Balance", text="Balance (KES)", anchor=tk.E)

        self.job_tree.column("Date", width=100, anchor=tk.CENTER, stretch=tk.NO)
        self.job_tree.column("Time", width=80, anchor=tk.CENTER, stretch=tk.NO)
        self.job_tree.column("Client Name", width=150, anchor=tk.W)
        self.job_tree.column("Location", width=150, anchor=tk.W)
        self.job_tree.column("Fee", width=100, anchor=tk.E)
        self.job_tree.column("Paid", width=100, anchor=tk.E)
        self.job_tree.column("Balance", width=100, anchor=tk.E)

        self.job_tree.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Bind selection event
        self.job_tree.bind("<<TreeviewSelect>>", self._on_job_select)

        # Action Buttons
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill="x", pady=5)

        # Load payment icon
        if self.parent_icon_loader:
            self._payment_icon = self.parent_icon_loader("pay.png", size=(20, 20))
            self._close_icon = self.parent_icon_loader("cancel.png", size=(20, 20))
            self._prev_icon = self.parent_icon_loader("arrow_left.png", size=(16, 16))
            self._next_icon = self.parent_icon_loader("arrow_right.png", size=(16, 16))

        self.make_payment_btn = ttk.Button(
            action_frame,
            text="Make Payment",
            image=self._payment_icon,
            compound=tk.LEFT,
            command=self._open_record_payment_form,
            state="disabled"
        )
        self.make_payment_btn.pack(side="left", padx=5)
        self.make_payment_btn.image = self._payment_icon

        # Pagination
        pagination_frame = ttk.Frame(main_frame, padding="5")
        pagination_frame.pack(pady=5, fill="x")

        self.prev_button = ttk.Button(
            pagination_frame,
            text="Previous",
            image=self._prev_icon,
            compound=tk.LEFT,
            command=self._go_previous_page,
            state="disabled"
        )
        self.prev_button.pack(side="left", padx=5)
        self.prev_button.image = self._prev_icon

        self.page_info_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_info_label.pack(side="left", padx=5)

        self.next_button = ttk.Button(
            pagination_frame,
            text="Next",
            image=self._next_icon,
            compound=tk.RIGHT,
            command=self._go_next_page,
            state="disabled"
        )
        self.next_button.pack(side="left", padx=5)
        self.next_button.image = self._next_icon

        ttk.Button(
            pagination_frame,
            text="Close",
            image=self._close_icon,
            compound=tk.LEFT,
            command=self._on_closing
        ).pack(side="right", padx=5)

    def _apply_filters(self):
        """Applies filters and reloads the first page of survey jobs."""
        filters = {
            'client_name': self.filter_client_name.get().strip() or None,
            'location': self.filter_location.get().strip() or None,
            'start_date': self.filter_start_date.get() if self.filter_start_date.get() != 'None' else None,
            'end_date': self.filter_end_date.get() if self.filter_end_date.get() != 'None' else None
        }

        # Validate date range if both dates are provided
        if filters['start_date'] and filters['end_date']:
            try:
                start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                if start_date > end_date:
                    messagebox.showwarning("Input Error", "Start date cannot be after end date.")
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid date format. Use YYYY-MM-DD.")
                return

        # Fetch data with pagination
        self.all_jobs_data, self.total_jobs = self.db_manager.get_survey_jobs_paginated(
            page=1,
            page_size=self.items_per_page,
            filters=filters,
            sort_by='created_at',
            sort_order='DESC'
        )

        self.total_pages = max(1, (self.total_jobs + self.items_per_page - 1) // self.items_per_page)
        self._load_page(1)

    def _clear_filters(self):
        """Clears all filters and reloads data."""
        self.filter_client_name.set("")
        self.filter_location.set("")
        self.start_date_entry.set_date(None)
        self.end_date_entry.set_date(None)
        self._apply_filters()

    def _load_page(self, page_number):
        """Loads data for the specified page number into the Treeview."""
        if page_number < 1 or page_number > self.total_pages:
            return

        self.current_page = page_number

        # Re-fetch data for the current page with filters
        filters = {
            'client_name': self.filter_client_name.get().strip() or None,
            'location': self.filter_location.get().strip() or None,
            'start_date': self.filter_start_date.get() if self.filter_start_date.get() != 'None' else None,
            'end_date': self.filter_end_date.get() if self.filter_end_date.get() != 'None' else None
        }

        self.all_jobs_data, self.total_jobs = self.db_manager.get_survey_jobs_paginated(
            page=self.current_page,
            page_size=self.items_per_page,
            filters=filters,
            sort_by='created_at',
            sort_order='DESC'
        )

        self._populate_job_treeview()
        self._update_pagination_buttons()
        self.selected_job_data = None
        self._update_payment_button_state()

    def _populate_job_treeview(self):
        """Populates the Treeview with the current page of data."""
        self.job_tree.delete(*self.job_tree.get_children())

        if not self.all_jobs_data:
            self.job_tree.insert("", "end", values=("No jobs found", "", "", "", "", "", ""))
            return

        for job in self.all_jobs_data:
            # Split created_at into date and time components
            created_at = job.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M')
                except ValueError:
                    date_str = created_at.split(' ')[0] if ' ' in created_at else created_at
                    time_str = created_at.split(' ')[1] if ' ' in created_at else ''
            else:
                date_str = time_str = ''

            self.job_tree.insert("", "end", values=(
                date_str,
                time_str,
                job.get('client_name', ''),
                job.get('property_location', ''),
                f"{job.get('fee', 0):,.2f}",
                f"{job.get('amount_paid', 0):,.2f}",
                f"{job.get('balance', 0):,.2f}"
            ), iid=job.get('job_id'))

    def _on_job_select(self, event):
        """Handles job selection in the Treeview."""
        selected_item = self.job_tree.focus()
        if selected_item:
            job_id = int(selected_item)
            self.selected_job_data = next((j for j in self.all_jobs_data if j['job_id'] == job_id), None)
        else:
            self.selected_job_data = None

        self._update_payment_button_state()

    def _update_payment_button_state(self):
        """Updates the state of the payment button based on selection and balance."""
        if self.selected_job_data and self.selected_job_data.get('balance', 0) > 0:
            self.make_payment_btn.config(state="normal")
        else:
            self.make_payment_btn.config(state="disabled")

    def _open_record_payment_form(self):
        """Opens the payment form for the selected job."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to record payment for.")
            return

        job_id = self.selected_job_data['job_id']
        if self.selected_job_data['balance'] <= 0:
            messagebox.showinfo("No Balance", "This job has no outstanding balance.")
            return

        payment_form = RecordSinglePaymentForm(
            self.master,
            self.db_manager,
            self._refresh_after_payment,
            parent_icon_loader=self.parent_icon_loader,
            window_icon_name="payment.png",
            job_id_to_pay=job_id
        )
        payment_form.wait_window()

    def _refresh_after_payment(self):
        """Refreshes the view after a payment is recorded."""
        self._apply_filters()
        if self.refresh_main_view_callback:
            self.refresh_main_view_callback()

    def _go_previous_page(self):
        if self.current_page > 1:
            self._load_page(self.current_page - 1)

    def _go_next_page(self):
        if self.current_page < self.total_pages:
            self._load_page(self.current_page + 1)

    def _update_pagination_buttons(self):
        """Updates the state of pagination buttons and page info."""
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")

        if self.total_jobs == 0:
            self.page_info_label.config(text="No Jobs")
        else:
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")

    def _on_closing(self):
        """Handles window closing, releases grab, and calls callback."""
        self.grab_release()
        self.destroy()
        if self.refresh_main_view_callback:
            self.refresh_main_view_callback()


class TrackSurveyJobsFrame(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_main_view_callback=None, parent_icon_loader=None, window_icon_name="track_jobs.png"):
        super().__init__(master)
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self.title("Track Survey Jobs")

        self.db_manager = db_manager
        self.refresh_main_view_callback = refresh_main_view_callback
        self.parent_icon_loader = parent_icon_loader

        self.current_page = 1
        self.items_per_page = 15
        self.total_jobs = 0
        self.total_pages = 0
        self.all_jobs_data = []
        self.selected_job_data = None

        # Filter variables
        self.filter_client_name = tk.StringVar(self, value="")
        self.filter_location = tk.StringVar(self, value="")
        self.filter_status = tk.StringVar(self, value="All")
        self.filter_start_date = tk.StringVar(self, value="")
        self.filter_end_date = tk.StringVar(self, value="")

        # Icon references
        self._icons = {}
        self._window_icon_ref = None

        self._set_window_properties(1000, 600, window_icon_name, parent_icon_loader)
        self._customize_title_bar()
        self._create_widgets()
        self._apply_filters()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300)  # Dark blue color
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
                text_color = c_int(0x00FFFFFF)  # White text
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
        except Exception as e:
            print(f"Could not customize title bar: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Filter Frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filter_frame.pack(padx=10, pady=5, fill="x")

        # Filter Grid
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill="x", padx=5, pady=5)
        
        # Client Name Filter
        ttk.Label(filter_grid, text="Client Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(filter_grid, textvariable=self.filter_client_name).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # Location Filter
        ttk.Label(filter_grid, text="Location:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(filter_grid, textvariable=self.filter_location).grid(row=0, column=3, sticky="ew", padx=5, pady=2)
        
        # Status Filter
        ttk.Label(filter_grid, text="Status:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        status_options = ["All", "Pending", "Ongoing", "Completed", "Cancelled"]
        ttk.Combobox(filter_grid, textvariable=self.filter_status, values=status_options, state="readonly").grid(row=0, column=5, sticky="ew", padx=5, pady=2)
        
        # Date Range Filters
        ttk.Label(filter_grid, text="From Date:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.start_date_entry = DateEntry(filter_grid, selectmode='day', date_pattern='yyyy-mm-dd', 
                                         textvariable=self.filter_start_date)
        self.start_date_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.start_date_entry.set_date(None)
        
        ttk.Label(filter_grid, text="To Date:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.end_date_entry = DateEntry(filter_grid, selectmode='day', date_pattern='yyyy-mm-dd', 
                                       textvariable=self.filter_end_date)
        self.end_date_entry.grid(row=1, column=3, sticky="ew", padx=5, pady=2)
        self.end_date_entry.set_date(None)
        
        # Filter Buttons
        button_frame = ttk.Frame(filter_frame)
        button_frame.pack(fill="x", pady=5)
        
        # Load icons
        if self.parent_icon_loader:
            self._search_icon = self.parent_icon_loader("search.png", size=(20,20))
            self._clear_icon = self.parent_icon_loader("clear_filter.png", size=(20,20))
            self._status_icon = self.parent_icon_loader("status.png", size=(20,20))
            self._delete_icon = self.parent_icon_loader("delete.png", size=(20,20))
            self._close_icon = self.parent_icon_loader("cancel.png", size=(20,20))
            self._prev_icon = self.parent_icon_loader("arrow_left.png", size=(16,16))
            self._next_icon = self.parent_icon_loader("arrow_right.png", size=(16,16))
            self._edit_icon = self.parent_icon_loader("edit.png", size=(20,20))

        ttk.Button(button_frame, text="Apply Filters", image=self._search_icon, compound=tk.LEFT, 
                  command=self._apply_filters).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear Filters", image=self._clear_icon, compound=tk.LEFT, 
                  command=self._clear_filters).pack(side="right", padx=5)

        # Treeview
        columns = ("Date", "Time", "Client Name", "Contact", "Location",  "Deadline", "Added By", "Status")
        self.job_tree = ttk.Treeview(main_frame, columns=columns, show="headings", style='Treeview')
        
        # Configure columns
        self.job_tree.heading("Date", text="Date", anchor=tk.CENTER)
        self.job_tree.heading("Time", text="Time", anchor=tk.CENTER)
        self.job_tree.heading("Client Name", text="Client Name", anchor=tk.W)
        self.job_tree.heading("Contact", text="Contact", anchor=tk.W)
        self.job_tree.heading("Location", text="Location", anchor=tk.W)
        self.job_tree.heading("Deadline", text="Deadline", anchor=tk.CENTER)
        self.job_tree.heading("Added By", text="Added By", anchor=tk.W)
        self.job_tree.heading("Status", text="Status", anchor=tk.CENTER)
        
        self.job_tree.column("Date", width=100, anchor=tk.CENTER, stretch=tk.NO)
        self.job_tree.column("Time", width=80, anchor=tk.CENTER, stretch=tk.NO)
        self.job_tree.column("Client Name", width=150, anchor=tk.W)
        self.job_tree.column("Contact", width=120, anchor=tk.W)
        self.job_tree.column("Location", width=150, anchor=tk.W)
        self.job_tree.column("Deadline", width=100, anchor=tk.CENTER, stretch=tk.NO)
        self.job_tree.column("Added By", width=120, anchor=tk.W)
        self.job_tree.column("Status", width=100, anchor=tk.CENTER)
        
        self.job_tree.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Bind selection event
        self.job_tree.bind("<<TreeviewSelect>>", self._on_job_select)

        # Action Buttons
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill="x", pady=5)
        
        self.update_status_btn = ttk.Button(
            action_frame, 
            text="Update Status", 
            image=self._status_icon,
            compound=tk.LEFT,
            command=self._update_job_status,
            state="disabled"
        )
        self.update_status_btn.pack(side="left", padx=5)
        self.update_status_btn.image = self._status_icon

        self.delete_job_btn = ttk.Button(
            action_frame,
            text="Delete Job",
            image=self._delete_icon,
            compound=tk.LEFT,
            command=self._delete_job,
            state="disabled"
        )
        self.delete_job_btn.pack(side="left", padx=5)
        self.delete_job_btn.image = self._delete_icon

        self.edit_deadline_btn = ttk.Button(
            action_frame,
            text="Edit Deadline",
            image=self._edit_icon,  # You'll need to load this icon
            compound=tk.LEFT,
            command=self._edit_deadline,
            state="disabled"
        )
        self.edit_deadline_btn.pack(side="right", padx=5)
        self.edit_deadline_btn.image = self._edit_icon

        self.edit_details_btn = ttk.Button(
            action_frame,
            text="Edit Details",
            image=self._edit_icon,  # You can use the same icon or load a different one
            compound=tk.LEFT,
            command=self._edit_details,
            state="disabled"
        )
        self.edit_details_btn.pack(side="right", padx=5)
        self.edit_details_btn.image = self._edit_icon


        # Pagination
        pagination_frame = ttk.Frame(main_frame, padding="5")
        pagination_frame.pack(pady=5, fill="x")
        
        self.prev_button = ttk.Button(
            pagination_frame, 
            text="Previous",
            image=self._prev_icon,
            compound=tk.LEFT,
            command=self._go_previous_page,
            state="disabled"
        )
        self.prev_button.pack(side="left", padx=5)
        self.prev_button.image = self._prev_icon
        
        self.page_info_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_info_label.pack(side="left", padx=5)
        
        self.next_button = ttk.Button(
            pagination_frame, 
            text="Next",
            image=self._next_icon,
            compound=tk.RIGHT,
            command=self._go_next_page,
            state="disabled"
        )
        self.next_button.pack(side="left", padx=5)
        self.next_button.image = self._next_icon

        ttk.Button(
            pagination_frame,
            text="Close",
            image=self._close_icon,
            compound=tk.LEFT,
            command=self._on_closing
        ).pack(side="right", padx=5)

    def _apply_filters(self):
        """Applies filters and reloads the first page of survey jobs."""
        filters = {
            'client_name': self.filter_client_name.get().strip() or None,
            'location': self.filter_location.get().strip() or None,
            'status': self.filter_status.get() if self.filter_status.get() != "All" else None,
            'start_date': self.filter_start_date.get() if self.filter_start_date.get() != 'None' else None,
            'end_date': self.filter_end_date.get() if self.filter_end_date.get() != 'None' else None
        }

        # Validate date range if both dates are provided
        if filters['start_date'] and filters['end_date']:
            try:
                start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                if start_date > end_date:
                    messagebox.showwarning("Input Error", "Start date cannot be after end date.")
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid date format. Use YYYY-MM-DD.")
                return

        # Fetch data with pagination
        self.all_jobs_data, self.total_jobs = self.db_manager.get_survey_jobs_paginated(
            page=1,
            page_size=self.items_per_page,
            filters=filters,
            sort_by='created_at',
            sort_order='DESC'
        )

        self.total_pages = max(1, (self.total_jobs + self.items_per_page - 1) // self.items_per_page)
        self._load_page(1)

    def _clear_filters(self):
        """Clears all filters and reloads data."""
        self.filter_client_name.set("")
        self.filter_location.set("")
        self.filter_status.set("All")
        self.start_date_entry.set_date(None)
        self.end_date_entry.set_date(None)
        self._apply_filters()

    def _load_page(self, page_number):
        """Loads data for the specified page number into the Treeview."""
        if page_number < 1 or page_number > self.total_pages:
            return

        self.current_page = page_number
        
        # Re-fetch data for the current page with filters
        filters = {
            'client_name': self.filter_client_name.get().strip() or None,
            'location': self.filter_location.get().strip() or None,
            'status': self.filter_status.get() if self.filter_status.get() != "All" else None,
            'start_date': self.filter_start_date.get() if self.filter_start_date.get() != 'None' else None,
            'end_date': self.filter_end_date.get() if self.filter_end_date.get() != 'None' else None
        }
        
        self.all_jobs_data, self.total_jobs = self.db_manager.get_survey_jobs_paginated(
            page=self.current_page,
            page_size=self.items_per_page,
            filters=filters,
            sort_by='created_at',
            sort_order='DESC'
        )

        self._populate_job_treeview()
        self._update_pagination_buttons()
        self.selected_job_data = None
        self._update_action_buttons_state()

    def _populate_job_treeview(self):
        """Populates the Treeview with the current page of data."""
        self.job_tree.delete(*self.job_tree.get_children())
        
        if not self.all_jobs_data:
            self.job_tree.insert("", "end", values=("No jobs found", "", "", "", "", "", ""))
            return

        for job in self.all_jobs_data:
            # Split created_at into date and time components
            created_at = job.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M')
                except ValueError:
                    date_str = created_at.split(' ')[0] if ' ' in created_at else created_at
                    time_str = created_at.split(' ')[1] if ' ' in created_at else ''
            else:
                date_str = time_str = ''

            added_by = job.get('added_by_username', job.get('added_by_user_id', 'Unknown'))    

            self.job_tree.insert("", "end", values=(
                date_str,
                time_str,
                job.get('client_name', ''),
                job.get('client_contact', ''),
                job.get('property_location', ''),
                job.get('deadline', ''),
                added_by,
                job.get('status', '').upper()
            ), iid=job.get('job_id'))

    def _on_job_select(self, event):
        """Handles job selection in the Treeview."""
        selected_item = self.job_tree.focus()
        if selected_item:
            job_id = int(selected_item)
            self.selected_job_data = next((j for j in self.all_jobs_data if j['job_id'] == job_id), None)
        else:
            self.selected_job_data = None
            
        self._update_action_buttons_state()

    def _update_action_buttons_state(self):
        """Updates the state of action buttons based on selection."""
        is_selected = self.selected_job_data is not None
        is_completed = is_selected and self.selected_job_data.get('status') == 'Completed'

        self.update_status_btn.config(state="normal" if is_selected else "disabled")
        self.delete_job_btn.config(state="normal" if is_selected else "disabled")

        self.edit_deadline_btn.config(state="normal" if (is_selected and not is_completed) else "disabled")
        self.edit_details_btn.config(state="normal" if (is_selected and not is_completed) else "disabled")


    def _update_job_status(self):
        """Opens a dialog to update the status of the selected job."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to update its status.")
            return

        job_id = self.selected_job_data['job_id']
        current_status = self.selected_job_data['status']

        status_dialog = tk.Toplevel(self)
        status_dialog.title("Update Job Status")
        status_dialog.transient(self)
        status_dialog.grab_set()
        status_dialog.resizable(False, False)

        dialog_frame = ttk.Frame(status_dialog, padding="15")
        dialog_frame.pack(fill="both", expand=True)

        ttk.Label(dialog_frame, text=f"Update status for Job ID: {job_id}").pack(pady=10)
        ttk.Label(dialog_frame, text=f"Current Status: {current_status}").pack(pady=5)

        new_status_var = tk.StringVar(value=current_status)
        status_options = ["Pending", "Ongoing", "Completed", "Cancelled"]
        status_combobox = ttk.Combobox(dialog_frame, textvariable=new_status_var,
                                     values=status_options, state="readonly")
        status_combobox.pack(pady=10)

        def save_status():
            new_status = new_status_var.get()
            if new_status and new_status != current_status:
                if self.db_manager.update_survey_job(job_id, status=new_status):
                    messagebox.showinfo("Success", f"Job {job_id} status updated to '{new_status}'.")
                    self._refresh_after_action()
                    status_dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to update job status in database.")
            else:
                messagebox.showinfo("No Change", "No new status selected or status is the same.")
                status_dialog.destroy()

        button_frame = ttk.Frame(dialog_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save", command=save_status).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=status_dialog.destroy).pack(side="left", padx=5)

        status_dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (status_dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (status_dialog.winfo_height() // 2)
        status_dialog.geometry(f"+{x}+{y}")

    def _delete_job(self):
        """Deletes the selected job after confirmation."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to delete.")
            return

        job_id = self.selected_job_data['job_id']
        client_name = self.selected_job_data['client_name']

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete Survey Job ID: {job_id} for Client: {client_name}?\n\nThis action cannot be undone.",
            icon='warning'
        )

        if confirm:
            if self.db_manager.delete_survey_job(job_id):
                messagebox.showinfo("Success", f"Job ID {job_id} deleted successfully.")
                self._refresh_after_action()
            else:
                messagebox.showerror("Error", "Failed to delete job from the database.")

    def _refresh_after_action(self):
        """Refreshes the view after status update or deletion."""
        self._apply_filters()
        if self.refresh_main_view_callback:
            self.refresh_main_view_callback()

    def _go_previous_page(self):
        if self.current_page > 1:
            self._load_page(self.current_page - 1)

    def _go_next_page(self):
        if self.current_page < self.total_pages:
            self._load_page(self.current_page + 1)

    def _update_pagination_buttons(self):
        """Updates the state of pagination buttons and page info."""
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")
        
        if self.total_jobs == 0:
            self.page_info_label.config(text="No Jobs")
        else:
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")

    def _on_closing(self):
        """Handles window closing, releases grab, and calls callback."""
        self.grab_release()
        self.destroy()
        if self.refresh_main_view_callback:
            self.refresh_main_view_callback()
    
    def _edit_deadline(self):
        """Opens a dialog to edit the deadline of the selected job."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to edit its deadline.")
            return

        job_id = self.selected_job_data['job_id']
        current_deadline = self.selected_job_data.get('deadline', '')

        deadline_dialog = tk.Toplevel(self)
        deadline_dialog.title("Edit Job Deadline")
        deadline_dialog.transient(self)
        deadline_dialog.grab_set()
        deadline_dialog.resizable(False, False)

        dialog_frame = ttk.Frame(deadline_dialog, padding="15")
        dialog_frame.pack(fill="both", expand=True)

        ttk.Label(dialog_frame, text=f"Edit Deadline for Job ID: {job_id}").pack(pady=10)
        ttk.Label(dialog_frame, text=f"Current Deadline: {current_deadline}").pack(pady=5)

        new_deadline_var = tk.StringVar(value=current_deadline)
        deadline_entry = DateEntry(dialog_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                                   textvariable=new_deadline_var)
        deadline_entry.pack(pady=10)

        def save_deadline():
            new_deadline = new_deadline_var.get()
            if not new_deadline:
                messagebox.showwarning("Input Error", "Please select a valid deadline date.")
                return
                
            try:
                deadline_date = datetime.strptime(new_deadline, '%Y-%m-%d').date()
                today = datetime.now().date()
                
                if deadline_date < today:
                    messagebox.showwarning("Invalid Date", "Deadline cannot be earlier than today's date.")
                    return
                    
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid date format. Please use YYYY-MM-DD.")
                return

            if new_deadline == current_deadline:
                messagebox.showinfo("No Change", "Deadline is the same as current value.")
                deadline_dialog.destroy()
                return

            if self.db_manager.update_survey_job(job_id, deadline=new_deadline):
                messagebox.showinfo("Success", f"Job {job_id} deadline updated to '{new_deadline}'.")
                self._refresh_after_action()
                deadline_dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update job deadline in database.")

        button_frame = ttk.Frame(dialog_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save", command=save_deadline).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=deadline_dialog.destroy).pack(side="left", padx=5)

        deadline_dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (deadline_dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (deadline_dialog.winfo_height() // 2)
        deadline_dialog.geometry(f"+{x}+{y}")

    def _edit_details(self):
        """Opens a dialog to edit the details of the selected job."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to edit its details.")
            return

        job_id = self.selected_job_data['job_id']
        current_location = self.selected_job_data.get('property_location', '')
        current_description = self.selected_job_data.get('job_description', '')

        details_dialog = tk.Toplevel(self)
        details_dialog.title("Edit Job Details")
        details_dialog.transient(self)
        details_dialog.grab_set()
        details_dialog.resizable(False, False)

        main_frame = ttk.Frame(details_dialog, padding="15")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Location:").grid(row=0, column=0, sticky="w", pady=5)
        location_entry = ttk.Entry(main_frame, width=50)
        location_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        location_entry.insert(0, current_location)

        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky="nw", pady=5)
        description_text = tk.Text(main_frame, height=6, width=50, wrap=tk.WORD)
        description_text.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        description_text.insert("1.0", current_description)

        def save_details():
            new_location = location_entry.get().strip()
            new_description = description_text.get("1.0", tk.END).strip()

            if not new_location:
                messagebox.showwarning("Input Error", "Location cannot be empty.")
                return
            
            updates = {
                'property_location': new_location,
                'job_description': new_description
            }

            if self.db_manager.update_survey_job(job_id, **updates):
                messagebox.showinfo("Success", f"Job {job_id} details updated successfully.")
                self._refresh_after_action()
                details_dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update job details in database.")

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Save", command=save_details).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=details_dialog.destroy).pack(side="left", padx=5)

        details_dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (details_dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (details_dialog.winfo_height() // 2)
        details_dialog.geometry(f"+{x}+{y}")
    

class SurveyReportsForm(tk.Toplevel):
    def __init__(self, master, db_manager, parent_icon_loader=None, window_icon_name="survey_reports.png"):
        super().__init__(master)
        self.resizable(False, False)  # Keep fixed size for reports window
        self.grab_set()  # Keep the window modal
        self.transient(master)  # Keep it on top of the master window
        self.title("Survey Reports")

        self.db_manager = db_manager
        self.parent_icon_loader_ref = parent_icon_loader
        self._window_icon_ref = None  # For window icon persistence

        self._calendar_icon = None
        self._generate_report_icon = None
        self._close_icon = None  # For the close button *within* the form content

        self.from_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))
        self.to_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))

        self.completed_surveys_report_text = None
        self.upcoming_deadlines_report_text = None

        # These are only used for the custom title bar fallback (non-Windows)
        self._start_x = 0
        self._start_y = 0

        # Set initial window properties (geometry, icon)
        self._set_window_properties(850, 550, window_icon_name, parent_icon_loader)

        # Apply custom title bar styling
        self._customize_title_bar()

        # Create and lay out widgets below the (now natively styled or custom) title bar
        self._create_widgets(parent_icon_loader)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()  # Ensure window dimensions are calculated
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        # Set icon for the window itself (this will appear in the native title bar)
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(52, 52))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image  # Store strong reference for icon
            except Exception as e:
                print(f"Failed to set icon for {self.winfo_name()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102) -> 0x00663300 in BGR
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems (Linux/macOS)
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()  # Fallback even if ctypes fails

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)

        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Title label
        title_label = tk.Label(
            title_bar,
            text=self.title(),  # Use the actual window title
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging (used in fallback)."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar (used in fallback)."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self, parent_icon_loader):
        """Creates all UI widgets and the Notebook for tabs."""
        content_frame = ttk.Frame(self, padding="15")
        content_frame.pack(fill="both", expand=True)

        # Load icons
        if parent_icon_loader:
            self._calendar_icon = parent_icon_loader("calendar_icon.png", size=(20, 20))
            self._generate_report_icon = parent_icon_loader("report.png", size=(20, 20))
            self._close_icon = parent_icon_loader("cancel.png", size=(20, 20))

        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill="both", expand=True)

        self._create_completed_surveys_tab(notebook)
        self._create_upcoming_deadlines_tab(notebook)

        # Close button at the bottom of the form (within content_frame)
        close_btn = ttk.Button(content_frame, text="Close", image=self._close_icon, compound=tk.LEFT,
                               command=self.destroy)
        close_btn.image = self._close_icon  # Keep a reference to prevent garbage collection
        close_btn.pack(pady=10)

    def _create_completed_surveys_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Completed Surveys")
        self._create_report_tab(
            frame, "completed_surveys", "Completed Surveys",
            self._generate_completed_surveys_report,
            "completed_surveys_report_text"
        )

    def _create_upcoming_deadlines_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Upcoming Deadlines")
        self._create_report_tab(
            frame, "upcoming_deadlines", "Upcoming Deadlines",
            self._generate_upcoming_deadlines_report,
            "upcoming_deadlines_report_text"
        )

    def _create_report_tab(self, parent_frame, report_prefix, report_title, generate_function, text_widget_attr_name):
        control_frame = ttk.LabelFrame(parent_frame, text=f"{report_title} Report Options", padding="10")
        control_frame.pack(fill="x", pady=10)

        report_type_var = tk.StringVar(control_frame, value="daily")
        ttk.Label(control_frame, text="Select Report Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Daily", variable=report_type_var, value="daily",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, False, v)).grid(
            row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Monthly", variable=report_type_var, value="monthly",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, False, v)).grid(
            row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Custom Range", variable=report_type_var, value="custom",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, True, v)).grid(row=0,
                                                                                                                  column=3,
                                                                                                                  padx=5,
                                                                                                                  pady=5,
                                                                                                                  sticky="w")

        date_range_frame = ttk.Frame(control_frame)
        date_range_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="ew")

        ttk.Label(date_range_frame, text="From:").pack(side="left", padx=5)
        from_entry = ttk.Entry(date_range_frame, textvariable=self.from_date_var, state="readonly", width=15)
        from_entry.pack(side="left", padx=2)
        from_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon,
                                  command=lambda: self._open_datepicker(self.from_date_var))
        from_cal_btn.image = self._calendar_icon
        from_cal_btn.pack(side="left", padx=2)

        ttk.Label(date_range_frame, text="To:").pack(side="left", padx=5)
        to_entry = ttk.Entry(date_range_frame, textvariable=self.to_date_var, state="readonly", width=15)
        to_entry.pack(side="left", padx=2)
        to_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon,
                                command=lambda: self._open_datepicker(self.to_date_var))
        to_cal_btn.image = self._calendar_icon
        to_cal_btn.pack(side="left", padx=2)

        control_frame._from_entry = from_entry
        control_frame._to_entry = to_entry
        control_frame._from_cal_btn = from_cal_btn
        control_frame._to_cal_btn = to_cal_btn

        self._toggle_date_entries(control_frame, False, report_type_var)

        generate_btn = ttk.Button(control_frame, text=f"Generate {report_title} Report",
                                  image=self._generate_report_icon, compound=tk.LEFT,
                                  command=lambda: generate_function(report_type_var.get()))
        generate_btn.image = self._generate_report_icon
        generate_btn.grid(row=2, column=0, columnspan=4, pady=10)

        report_preview_frame = ttk.LabelFrame(parent_frame, text="Report Preview", padding="10")
        report_preview_frame.pack(fill="both", expand=True, pady=10)
        report_preview_frame.grid_columnconfigure(0, weight=1)
        report_preview_frame.grid_rowconfigure(0, weight=1)

        report_text = tk.Text(report_preview_frame, wrap=tk.WORD, height=15, font=('Helvetica', 9))
        report_text.grid(row=0, column=0, sticky="nsew")

        report_scroll_y = ttk.Scrollbar(report_preview_frame, orient="vertical", command=report_text.yview)
        report_scroll_y.grid(row=0, column=1, sticky="ns")
        report_text.config(yscrollcommand=report_scroll_y.set)

        report_scroll_x = ttk.Scrollbar(report_preview_frame, orient="horizontal", command=report_text.xview)
        report_scroll_x.grid(row=1, column=0, sticky="ew")
        report_text.config(xscrollcommand=report_scroll_x.set)

        setattr(self, text_widget_attr_name, report_text)

    def _toggle_date_entries(self, control_frame, enable, report_type_var):
        """Enables/disables custom date entry fields."""
        state = "normal" if enable else "readonly"
        button_state = "normal" if enable else "disabled"

        control_frame._from_entry.config(state=state)
        control_frame._to_entry.config(state=state)
        control_frame._from_cal_btn.config(state=button_state)
        control_frame._to_cal_btn.config(state=button_state)

        if not enable:
            today = datetime.now()
            current_report_type = report_type_var.get()
            if current_report_type == "daily":
                self.from_date_var.set(today.strftime("%Y-%m-%d"))
                self.to_date_var.set(today.strftime("%Y-%m-%d"))
            elif current_report_type == "monthly":
                first_day_of_month = today.replace(day=1)
                # Calculate last day of the current month
                if today.month == 12:
                    last_day_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                self.from_date_var.set(first_day_of_month.strftime("%Y-%m-%d"))
                self.to_date_var.set(last_day_of_month.strftime("%Y-%m-%d"))

    def _open_datepicker(self, target_var):
        """Opens date picker for a specific StringVar."""
        current_date_str = target_var.get()
        try:
            current_date_obj = datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            current_date_obj = datetime.now()

        # Assuming DatePicker is a class you have defined elsewhere
        # DatePicker(self, current_date_obj, lambda d: target_var.set(d),
        #            parent_icon_loader=self.parent_icon_loader_ref,
        #            window_icon_name="calendar_icon.png")
        messagebox.showinfo("Date Picker",
                            f"Date picker would open for {target_var.get()}")  # Placeholder if DatePicker isn't available

    def _get_report_dates(self, report_type):
        """Determines start and end dates based on report type."""
        today = datetime.now()
        start_date = None
        end_date = None

        if report_type == "daily":
            start_date = today.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif report_type == "monthly":
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")
        elif report_type == "custom":
            start_date = self.from_date_var.get()
            end_date = self.to_date_var.get()
            if not self._is_valid_date(start_date) or not self._is_valid_date(end_date):
                messagebox.showerror("Date Error", "Invalid custom date range. Please use YYYY-MM-DD format.")
                return None, None
            # Convert to datetime objects for comparison
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                messagebox.showerror("Date Error", "Start date cannot be after end date.")
                return None, None
        return start_date, end_date

    def _is_valid_date(self, date_string):
        """Validates date format."""
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _generate_completed_surveys_report(self, report_type):
        """Generates completed surveys report (text preview and PDF)."""
        report_text_widget = self.completed_surveys_report_text
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Completed surveys report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            completed_surveys = self.db_manager.get_completed_surveys_for_date_range(start_date, end_date)

            # Format the report text for preview
            report_text = f"Completed Surveys Report\n"
            report_text += f"Period: {start_date} to {end_date}\n\n"
            report_text += f"Total Surveys Completed: {len(completed_surveys)}\n\n"

            if completed_surveys:
                report_text += "Survey Details:\n"
                report_text += "=" * 80 + "\n"
                for i, survey in enumerate(completed_surveys):
                    report_text += f"Survey #{i + 1}\n"
                    report_text += f"  Job ID: {survey.get('job_id', 'N/A')}\n"
                    report_text += f"  Client: {survey.get('client_name', 'N/A')}\n"
                    report_text += f"  Location: {survey.get('property_location', 'N/A')}\n"
                    report_text += f"  Description: {survey.get('job_description', 'N/A')}\n"
                    report_text += f"  Fee: {survey.get('fee', 0.0):,.2f}\n"
                    report_text += f"  Status: {survey.get('status', 'N/A')}\n"
                    report_text += f"  Completion Date: {survey.get('completion_date', 'N/A')}\n"
                    report_text += f"  Added By: {survey.get('surveyor_name', 'N/A')}\n"
                    report_text += "-" * 80 + "\n"
            else:
                report_text += "No surveys were completed in this period.\n"

            # Generate PDF
            pdf_path = self._generate_pdf_report(
                "Completed Surveys Report",
                {'data': completed_surveys},  # Pass data for PDF generation
                report_type,
                start_date,
                end_date
            )

            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", report_text)  # Show text preview regardless of PDF success

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Completed Surveys Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Completed Surveys Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)

        except Exception as e:
            messagebox.showerror("Report Generation Error",
                                 f"An error occurred while generating Completed Surveys Report: {type(e).__name__}: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {type(e).__name__}: {e}")

    def _generate_upcoming_deadlines_report(self, report_type):
        """Generates upcoming deadlines report (text preview and PDF)."""
        report_text_widget = self.upcoming_deadlines_report_text
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Upcoming deadlines report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            upcoming_deadlines = self.db_manager.get_upcoming_survey_deadlines_for_date_range(start_date, end_date)

            # Format the report text for preview
            report_text = f"Upcoming Survey Deadlines Report\n"
            report_text += f"Period: {start_date} to {end_date}\n\n"
            report_text += f"Total Upcoming Deadlines: {len(upcoming_deadlines)}\n\n"

            if upcoming_deadlines:
                report_text += "Deadline Details:\n"
                report_text += "=" * 80 + "\n"
                for i, deadline in enumerate(upcoming_deadlines):
                    report_text += f"Deadline #{i + 1}\n"
                    report_text += f"  Job ID: {deadline.get('job_id', 'N/A')}\n"
                    report_text += f"  Client: {deadline.get('client_name', 'N/A')}\n"
                    report_text += f"  Location: {deadline.get('property_location', 'N/A')}\n"
                    report_text += f"  Deadline Date: {deadline.get('deadline_date', 'N/A')}\n"
                    report_text += f"  Status: {deadline.get('status', 'N/A')}\n"
                    report_text += f"  Added By: {deadline.get('assigned_to', 'N/A')}\n"
                    report_text += f"  Priority: {deadline.get('priority', 'N/A')}\n"
                    report_text += "-" * 80 + "\n"
            else:
                report_text += "No upcoming deadlines in this period.\n"

            # Generate PDF
            pdf_path = self._generate_pdf_report(
                "Upcoming Deadlines Report",
                {'data': upcoming_deadlines},  # Pass data for PDF generation
                report_type,
                start_date,
                end_date
            )

            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", report_text)  # Show text preview regardless of PDF success

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Upcoming Deadlines Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Upcoming Deadlines Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)

        except Exception as e:
            messagebox.showerror("Report Generation Error",
                                 f"An error occurred while generating Upcoming Deadlines Report: {type(e).__name__}: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {type(e).__name__}: {e}")

    # Your existing _generate_sales_report method (copied for reference, will assume it's already there)
    def _generate_sales_report(self, report_type):
        """Generates sales report (detailed accounting style) as PDF and shows preview."""
        report_text_widget = self.sales_report_text  # Make sure self.sales_report_text is initialized
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Sales report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)  # Clear previous content
        report_text_widget.insert("1.0", "Generating report, please wait...")  # Show status

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)  # Clear "generating" message
            return  # Date validation failed

        try:
            # Fetch detailed sales transactions for the accounting report
            detailed_sales_data = self.db_manager.get_detailed_sales_transactions_for_date_range(start_date, end_date)

            pdf_path = self._generate_pdf_report(
                "Sales Report",
                {'data': detailed_sales_data},  # Pass detailed data
                report_type,
                start_date,
                end_date
            )

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Sales Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Sales Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating Sales Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")

    # Your existing _generate_sold_properties_report method (copied for reference, will assume it's already there)
    def _generate_sold_properties_report(self, report_type):
        """Generates sold properties report as PDF and shows preview."""
        report_text_widget = self.sold_properties_report_text  # Make sure self.sold_properties_report_text is initialized
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Sold properties report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            sold_properties = self.db_manager.get_sold_properties_for_date_range_detailed(start_date, end_date)

            pdf_path = self._generate_pdf_report(
                "Sold Properties Report",
                {'data': sold_properties},  # Pass detailed data
                report_type,
                start_date,
                end_date
            )

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Sold Properties Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Sold Properties Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error",
                                 f"An error occurred while generating Sold Properties Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")

    # Your existing _generate_pending_instalments_report method (copied for reference, will assume it's already there)
    def _generate_pending_instalments_report(self, report_type):
        """Generates pending instalments report as PDF and shows preview."""
        report_text_widget = self.pending_instalments_report_text  # Make sure self.pending_instalments_report_text is initialized
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Pending instalments report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            pending_instalments = self.db_manager.get_pending_instalments_for_date_range(start_date, end_date)

            pdf_path = self._generate_pdf_report(
                "Pending Instalments Report",
                {'data': pending_instalments},  # Pass detailed data
                report_type,
                start_date,
                end_date
            )

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Pending Instalments Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Pending Instalments Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error",
                                 f"An error occurred while generating Pending Instalments Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")

    # New or updated _generate_pdf_report method (placeholder, you should have your full implementation)
    def _generate_pdf_report(self, report_title, data_dict, report_type, start_date, end_date):
        """
        Generates a generic PDF report based on the provided data.
        This is a placeholder. You need to implement the actual PDF content generation
        based on the `report_title` and `data_dict`.
        """
        if not _REPORTLAB_AVAILABLE:
            print("ReportLab is not available. Cannot generate PDF.")
            return None

        # Define directory for reports
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        filename = f"{report_title.replace(' ', '_')}_{start_date}_to_{end_date}.pdf"
        filepath = os.path.join(reports_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph(report_title, styles['h1']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['h3']))
        story.append(Spacer(1, 0.4 * inch))

        # Determine how to format the data for the PDF
        if report_title == "Upcoming Deadlines Report":
            # Assuming 'data' key holds the list of dictionaries
            deadlines_data = data_dict.get('data', [])
            story.append(Paragraph(f"Total Upcoming Deadlines: {len(deadlines_data)}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            if deadlines_data:
                # Table headers
                table_headers = ["Job ID", "Client", "Location", "Deadline Date", "Status", "Assigned To", "Priority"]

                # Table data
                table_rows = [table_headers]
                for item in deadlines_data:
                    table_rows.append([
                        item.get('job_id', 'N/A'),
                        item.get('client_name', 'N/A'),
                        item.get('property_location', 'N/A'),
                        item.get('deadline_date', 'N/A'),
                        item.get('status', 'N/A'),
                        item.get('assigned_to', 'N/A'),
                        item.get('priority', 'N/A')
                    ])

                # Create the table
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ])
                # Calculate column widths dynamically based on content or fixed proportions
                col_widths = [1.0 * inch, 1.5 * inch, 1.5 * inch, 1.2 * inch, 0.8 * inch, 1.2 * inch, 0.8 * inch]

                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(table_style)
                story.append(table)
            else:
                story.append(Paragraph("No upcoming deadlines found for this period.", styles['Normal']))

        elif report_title == "Completed Surveys Report":
            # Assuming 'data' holds the list of dictionaries
            surveys_data = data_dict.get('data', [])
            story.append(Paragraph(f"Total Surveys Completed: {len(surveys_data)}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            if surveys_data:
                table_headers = ["Job ID", "Client", "Location", "Description", "Fee", "Status", "Completion Date",
                                 "Added By"]
                table_rows = [table_headers]
                for item in surveys_data:
                    table_rows.append([
                        item.get('job_id', 'N/A'),
                        item.get('client_name', 'N/A'),
                        item.get('property_location', 'N/A'),
                        item.get('job_description', 'N/A'),
                        f"{item.get('fee', 0.0):,.2f}",  # Format currency
                        item.get('status', 'N/A'),
                        item.get('completion_date', 'N/A'),
                        item.get('surveyor_name', 'N/A')
                    ])

                col_widths = [0.8 * inch, 1.2 * inch, 1.2 * inch, 1.5 * inch, 0.8 * inch, 0.8 * inch, 1.2 * inch,
                              1.0 * inch]
                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No completed surveys found for this period.", styles['Normal']))

        # Add handling for "Sales Report" (your existing logic)
        elif report_title == "Sales Report":
            sales_data = data_dict.get('data', [])
            # Calculate totals for the report summary
            total_revenue = sum(item.get('amount_paid', 0) + item.get('balance', 0) for item in sales_data)
            total_properties_sold = len(
                set(item.get('title_deed') for item in sales_data if item.get('title_deed')))  # Count unique properties

            story.append(Paragraph(f"Total Revenue: KES {total_revenue:,.2f}", styles['Normal']))
            story.append(Paragraph(f"Total Properties Sold: {total_properties_sold}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            if sales_data:
                table_headers = ["Title Deed", "Property Type", "Actual Price", "Amount Paid", "Balance"]
                table_rows = [table_headers]
                for item in sales_data:
                    table_rows.append([
                        item.get('title_deed', 'N/A'),
                        item.get('property_type', 'N/A'),
                        f"{item.get('actual_price', 0.0):,.2f}",
                        f"{item.get('amount_paid', 0.0):,.2f}",
                        f"{item.get('balance', 0.0):,.2f}"
                    ])

                col_widths = [1.5 * inch, 1.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]
                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No sales transactions found for this period.", styles['Normal']))

        # Add handling for "Sold Properties Report"
        elif report_title == "Sold Properties Report":
            sold_data = data_dict.get('data', [])
            story.append(Paragraph(f"Total Sold Properties: {len(sold_data)}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            if sold_data:
                table_headers = ["Title Deed", "Location", "Size", "Date Sold", "Amount Paid", "Balance", "Client Name"]
                table_rows = [table_headers]
                for item in sold_data:
                    table_rows.append([
                        item.get('title_deed_number', 'N/A'),
                        item.get('location', 'N/A'),
                        f"{item.get('size', 0.0):.2f}",
                        item.get('date_sold', 'N/A'),
                        f"{item.get('total_amount_paid', 0.0):,.2f}",
                        f"{item.get('balance', 0.0):,.2f}",
                        item.get('client_name', 'N/A')
                    ])
                col_widths = [1.2 * inch, 1.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch, 0.8 * inch, 1.5 * inch]
                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No sold properties found for this period.", styles['Normal']))

        # Add handling for "Pending Instalments Report"
        elif report_title == "Pending Instalments Report":
            instalments_data = data_dict.get('data', [])
            total_pending_balance = sum(item.get('balance', 0) for item in instalments_data)
            story.append(Paragraph(f"Total Pending Balance: KES {total_pending_balance:,.2f}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            if instalments_data:
                table_headers = ["Trans ID", "Date", "Title Deed", "Original Price", "Paid", "Balance", "Client"]
                table_rows = [table_headers]
                for item in instalments_data:
                    table_rows.append([
                        item.get('transaction_id', 'N/A'),
                        item.get('transaction_date', 'N/A').split(' ')[0],  # Just date
                        item.get('title_deed_number', 'N/A'),
                        f"{item.get('original_price', 0.0):,.2f}",
                        f"{item.get('total_amount_paid', 0.0):,.2f}",
                        f"{item.get('balance', 0.0):,.2f}",
                        item.get('client_name', 'N/A')
                    ])
                col_widths = [0.8 * inch, 1.0 * inch, 1.5 * inch, 1.2 * inch, 1.0 * inch, 0.8 * inch, 1.5 * inch]
                table = Table(table_rows, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No pending instalments found for this period.", styles['Normal']))

        try:
            doc.build(story)
            print(f"PDF report generated at: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error building PDF: {e}")
            return None

    def _show_pdf_preview(self, pdf_path, text_widget):
        """
        Displays a message in the text widget indicating PDF preview (since Tkinter can't embed PDF).
        In a real app, you might use a PDF viewer library or open the PDF in the default application.
        """
        if pdf_path:
            text_widget.insert(tk.END, f"\n\nPDF report saved to: {os.path.basename(pdf_path)}\n")
            text_widget.insert(tk.END, f"Full path: {pdf_path}\n")
            text_widget.insert(tk.END, "Please open the PDF file in an external viewer to see the full report.\n")
            # Optional: Open the PDF automatically (might not work in all environments/OSes)
            # import webbrowser
            # webbrowser.open_new_tab(pdf_path)
        else:
            text_widget.insert(tk.END, "\n\nPDF report could not be generated. Check console for errors.\n")

    def _on_closing(self):
        """Handles window closing."""
        self.destroy()
