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
# The DatabaseManager class is now fully functional
from database import DatabaseManager

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')

# Data and Receipts
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
os.makedirs(RECEIPTS_DIR, exist_ok=True)  # Ensure receipts directory exists

# Directory for reports
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)  # Ensure reports directory exists

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


class FormBase(tk.Toplevel):
    """
    Base class for all forms to handle common functionalities like
    window centering, title bar customization, and icon loading.
    """

    def __init__(self, master, width, height, title, icon_name, parent_icon_loader):
        # Correctly set the parent to the top-level window.
        # This fixes the "bad window path name" error.
        super().__init__(master.winfo_toplevel())
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None
        self._set_window_properties(width, height, icon_name, parent_icon_loader)
        self._customize_title_bar()
        # Removed the _on_closing() call as it was causing the window to close immediately
        # after being created.

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                if icon_image:
                    self.iconphoto(False, icon_image)
                    self._window_icon_ref = icon_image
                    print(f"Icon '{icon_name}' loaded successfully.")  # Add this line
                else:
                    print(f"Icon '{icon_name}' could not be loaded.")

            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance. Attempts Windows-specific
        customization, falls back to a custom Tkinter title bar."""
        try:
            if os.name == 'nt':  # Windows-specific title bar customization
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00804000)  # Dark blue color
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
            else:
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize native title bar: {e}. Falling back to custom Tkinter title bar.")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar when native customization isn't available."""
        self.overrideredirect(True)

        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text=self.title(),
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

    def _on_closing(self):
        """Callback for window closing event."""
        self.destroy()


# Helper function for generating PDF receipts (extracted from AddNewTaskForm)
def _generate_pdf_payment_receipt(job_id, client_name, file_name, job_description, amount_paid, payment_date):
    """
    Generates a PDF payment receipt using ReportLab.
    Returns the path to the generated PDF or None on failure.
    This is a standalone function to be reused by multiple forms.
    """
    if not _REPORTLAB_AVAILABLE:
        return None

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        receipt_filename = f"Receipt_Job_{job_id}_{timestamp}.pdf"
        receipt_path = os.path.join(RECEIPTS_DIR, receipt_filename)

        doc = SimpleDocTemplate(receipt_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Business Header
        header_data = [
            [Paragraph("<b>NDIRITU MATHENGE & ASSOCIATES</b>", styles['Normal']),
             Paragraph(f"Date: {payment_date}", styles['Normal'])]
        ]
        header_table = Table(header_data, colWidths=[4 * inch, 2 * inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
        ]))
        story.append(header_table)

        story.append(Spacer(1, 24))
        story.append(Paragraph("<b>PAYMENT RECEIPT</b>", styles['Heading1']))
        story.append(Spacer(1, 12))

        # Receipt Details Table
        data = [
            ["Receipt Number:", job_id],
            ["Client Name:", client_name],
            ["File Name:", file_name],
            ["Job Description:", job_description],
            ["Amount Paid:", f"KSh {amount_paid:,.2f}"],
        ]

        t = Table(data, colWidths=[2 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 24))
        story.append(Paragraph("Thank you for your business.", styles['Normal']))

        # Build the PDF
        doc.build(story)
        return receipt_path
    except Exception as e:
        messagebox.showerror("Receipt Error", f"Failed to generate PDF receipt: {e}")
        return None


class AddNewTaskForm(FormBase):
    """
    A form for adding a new task (job) to a specific client file.
    """

    def __init__(self, master, db_manager, client_data, user_id, refresh_callback, parent_icon_loader=None):
        # The icon_name 'add_task.png' is passed to the FormBase constructor
        super().__init__(master, 450, 310, "Add New Task", "add_task.png", parent_icon_loader)
        self.db_manager = db_manager
        self.client_data = client_data
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        # Keep a reference to the button icon to prevent garbage collection
        self.button_icon = None
        self._create_widgets()

    def _create_widgets(self):
        """Creates the widgets for the new task form."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Client:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(main_frame, text=self.client_data['name'], font=('Helvetica', 10, 'bold')).grid(row=0, column=1,
                                                                                                  sticky="w", pady=5)

        ttk.Label(main_frame, text="File:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(main_frame, text=self.client_data['file_name'], font=('Helvetica', 10, 'bold')).grid(row=1, column=1,
                                                                                                       sticky="w",
                                                                                                       pady=5)

        ttk.Label(main_frame, text="Brought By:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Label(main_frame, text=self.client_data['brought_by'], font=('Helvetica', 10, 'bold')).grid(row=2, column=1,
                                                                                                        sticky="w",
                                                                                                        pady=5)

        ttk.Separator(main_frame, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(main_frame, text="Job Description:").grid(row=4, column=0, sticky="w", pady=5)
        self.job_description_entry = ttk.Entry(main_frame)
        self.job_description_entry.grid(row=4, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Title Name:").grid(row=5, column=0, sticky="w", pady=5)
        self.title_name_entry = ttk.Entry(main_frame)
        self.title_name_entry.grid(row=5, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Title Number:").grid(row=6, column=0, sticky="w", pady=5)
        self.title_number_entry = ttk.Entry(main_frame)
        self.title_number_entry.grid(row=6, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Price:").grid(row=7, column=0, sticky="w", pady=5)
        self.price_entry = ttk.Entry(main_frame)
        self.price_entry.grid(row=7, column=1, sticky="ew", pady=5)

        if self.parent_icon_loader:
            self.button_icon = self.parent_icon_loader("add_task.png", size=(20, 20))

        # We need to make sure the reference is explicitly held
        self.button_icon_ref = self.button_icon

        ttk.Button(main_frame, text="Submit Task", image=self.button_icon, compound=tk.LEFT,
                   command=self._submit_task).grid(row=8, column=0, columnspan=2, pady=15)

        main_frame.grid_columnconfigure(1, weight=1)

    def _submit_task(self):
        """
        Validates and submits the new task to the database.
        Also records an initial payment for the task.
        """
        job_description = self.job_description_entry.get().strip()
        title_name = self.title_name_entry.get().strip()
        title_number = self.title_number_entry.get().strip()
        price_str = self.price_entry.get().strip()

        if not all([job_description, title_name, title_number, price_str]):
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            price_val = float(price_str)
            if price_val < 0:
                messagebox.showerror("Input Error", "Price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Price must be a valid number.")
            return

        added_by = self.db_manager.get_username_by_id(self.user_id)
        if not added_by:
            added_by = "Unknown User"

        # Step 1: Add the job to the database
        # ASSUMPTION: db_manager.add_job now returns the job_id if successful, else None.
        job_id = self.db_manager.add_job(
            file_id=self.client_data['file_id'],
            job_description=job_description,
            title_name=title_name,
            title_number=title_number,
            fee=price_val,
            amount_paid=price_val,  # Initial payment is the full fee
            added_by=added_by,
            brought_by=self.client_data['brought_by']
        )

        if job_id:  # Check if job was added successfully
            # Step 2: Record an initial payment for this job
            # ASSUMPTION: db_manager has an 'add_payment' method that takes:
            # (job_id, amount, payment_date, payment_type, recorded_by)
            payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payment_type = "Initial Payment"  # Default type for task submission payment

            payment_success = self.db_manager.add_payment(
                job_id=job_id,
                amount=price_val,
                payment_date=payment_date,
                payment_type=payment_type,
                recorded_by=added_by  # Records who added the payment
            )

            if payment_success:
                # Step 3: Print a payment receipt using the new helper function
                receipt_path = _generate_pdf_payment_receipt(
                    job_id=job_id,
                    client_name=self.client_data['name'],
                    file_name=self.client_data['file_name'],
                    job_description=job_description,
                    amount_paid=price_val,
                    payment_date=payment_date
                )

                if receipt_path:
                    SuccessMessage(
                        self.master,
                        success=True,
                        message="New task and initial payment added successfully.\nPayment receipt generated.",
                        pdf_path=receipt_path,
                        parent_icon_loader=self.parent_icon_loader
                    )
                else:
                    messagebox.showinfo("Success",
                                        "New task and initial payment added successfully, but receipt generation failed.")
                self.refresh_callback()  # Refresh the parent dashboard
                self.destroy()
            else:
                messagebox.showerror("Error",
                                     "New task added, but failed to record initial payment. Please check payment records manually.")
                # Depending on business logic, you might want to roll back the job creation here
                # self.db_manager.delete_job(job_id) # Example rollback
        else:
            messagebox.showerror("Error", "Failed to add new task.")


class ClientFileDashboard(FormBase):
    """
    A dashboard view for a specific client's file. It shows their recent tasks
    and allows for the creation of new tasks.
    """

    def __init__(self, master, db_manager, client_data, refresh_callback, user_id, parent_icon_loader=None):
        # We need the client_data to include the file_id for the new task form
        super().__init__(master, 900, 500, f"Client File: {client_data['name']}", "client_file.png", parent_icon_loader)
        self.db_manager = db_manager
        self.client_data = client_data
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        # We need to save the icon loader for later use with buttons
        self.parent_icon_loader = parent_icon_loader
        self._create_widgets()
        self._populate_tasks_table()

    def _create_widgets(self):
        """Creates the UI for the client file dashboard."""

        # --- Top section with client details and Add Task button ---
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill="x", pady=10)

        # Client and File Info
        client_info_frame = ttk.Frame(top_frame)
        client_info_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(client_info_frame, text=f"Client Name: {self.client_data['name']}",
                  font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)
        ttk.Label(client_info_frame, text=f"File Name: {self.client_data['file_name']}",
                  font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)
        ttk.Label(client_info_frame, text=f"Brought By: {self.client_data['brought_by']}",
                  font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)

        # Style and Icon for the Add Task button
        # Use the parent_icon_loader to load the icon
        if self.parent_icon_loader:
            self.button_icon = self.parent_icon_loader("add_task.png", size=(20, 20))
        else:
            self.button_icon = None

        style = ttk.Style()
        style.configure("Red.TButton", background="red", foreground="black")

        # Add New Task button
        btn = ttk.Button(top_frame, text="Add New Task", command=self._open_add_task_form, image=self.button_icon,
                         compound=tk.LEFT, style="Red.TButton")
        btn.pack(side="right", padx=10)

        # --- Separator ---
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10, padx=10)

        # --- Middle section with tasks table ---
        table_frame = ttk.Frame(self, padding="10")

        # New label above the table
        ttk.Label(table_frame,
                  text=f"Job History for client: {self.client_data['name']}, file name: {self.client_data['file_name']}",
                  font=('Helvetica', 10, 'bold')).pack(pady=5, padx=10, anchor="center")

        table_frame.pack(fill="both", expand=True)

        columns = ("job_id", "date", "description", "title_name", "title_number", "status")
        self.tasks_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tasks_tree.heading("job_id", text="ID")
        self.tasks_tree.heading("date", text="Date")
        self.tasks_tree.heading("description", text="Task Description")
        self.tasks_tree.heading("title_name", text="Title Name")
        self.tasks_tree.heading("title_number", text="Title Number")
        self.tasks_tree.heading("status", text="Status")

        self.tasks_tree.column("job_id", width=50, anchor=tk.W)
        self.tasks_tree.column("date", width=120, anchor=tk.W)
        self.tasks_tree.column("description", width=200, anchor=tk.W)
        self.tasks_tree.column("title_name", width=150, anchor=tk.W)
        self.tasks_tree.column("title_number", width=150, anchor=tk.W)
        self.tasks_tree.column("status", width=120, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)

        self.tasks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _populate_tasks_table(self):
        """Populates the tasks table with data for the selected client."""
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)

        # We now use file_id from self.client_data to get the jobs
        tasks = self.db_manager.get_jobs_by_file_id(self.client_data['file_id'])
        for task in tasks:
            self.tasks_tree.insert("", tk.END, values=(
                task['job_id'],
                task['timestamp'],
                task['job_description'].upper(),
                task['title_name'].upper(),
                task['title_number'].upper(),
                task['status'].upper()
            ))

    def _open_add_task_form(self):
        """Opens a new window to add a new task."""
        AddNewTaskForm(
            master=self.master,
            db_manager=self.db_manager,
            client_data=self.client_data,
            user_id=self.user_id,
            refresh_callback=self._populate_tasks_table,
            parent_icon_loader=self.parent_icon_loader
        )


class AddClientAndFileForm(FormBase):
    """
    A unified form to either create a new client and their first file,
    or to add a new file to an existing client, using a tabbed interface.
    """

    def __init__(self, master, db_manager, refresh_callback, user_id, parent_icon_loader=None):
        # Increased window height to accommodate the tabbed layout
        super().__init__(master, 750, 500, "Add Client or File", "add_client.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id

        self.selected_client_id = None  # Tracks the selected client from the table

        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(expand=True, fill="both")

        # Use a Notebook widget for the tabbed interface
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill="both")

        # Create the frames for the tabs
        self.new_client_frame = ttk.Frame(self.notebook, padding="10")
        self.existing_client_frame = ttk.Frame(self.notebook, padding="10")

        # Add the frames as tabs to the notebook
        self.notebook.add(self.new_client_frame, text="Add New Client")
        self.notebook.add(self.existing_client_frame, text="Add New File to Existing Client")

        # --- New Client fields with uniform size ---
        # The content for the 'new client' tab
        new_client_label_frame = ttk.Frame(self.new_client_frame)
        new_client_label_frame.pack(fill="x")
        ttk.Label(new_client_label_frame, text="Client Name:").pack(side="left", fill="x", expand=True)
        self.name_entry = ttk.Entry(self.new_client_frame)
        self.name_entry.pack(fill="x", pady=(0, 10))

        new_contact_label_frame = ttk.Frame(self.new_client_frame)
        new_contact_label_frame.pack(fill="x")
        ttk.Label(new_contact_label_frame, text="Contact:").pack(side="left", fill="x", expand=True)
        self.contact_entry = ttk.Entry(self.new_client_frame)
        self.contact_entry.pack(fill="x", pady=(0, 10))

        new_brought_by_label_frame = ttk.Frame(self.new_client_frame)
        new_brought_by_label_frame.pack(fill="x")
        ttk.Label(new_brought_by_label_frame, text="Brought By:").pack(side="left", fill="x", expand=True)
        self.brought_by_entry = ttk.Entry(self.new_client_frame)
        self.brought_by_entry.pack(fill="x", pady=(0, 10))

        new_file_label_frame = ttk.Frame(self.new_client_frame)
        new_file_label_frame.pack(fill="x")
        ttk.Label(new_file_label_frame, text="File Name:").pack(side="left", fill="x", expand=True)
        self.new_client_file_name_entry = ttk.Entry(self.new_client_frame)
        self.new_client_file_name_entry.pack(fill="x", pady=(0, 10))

        # --- Existing Client fields with real-time search and short table ---
        # The content for the 'existing client' tab
        ttk.Label(self.existing_client_frame, text="Search for a Client:").pack(pady=(0, 5), anchor="w")
        self.search_entry = ttk.Entry(self.existing_client_frame)
        self.search_entry.pack(fill="x", pady=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._filter_clients_table)

        columns = ("client_name", "contact")
        self.client_tree = ttk.Treeview(self.existing_client_frame, columns=columns, show="headings", height=10)
        self.client_tree.heading("client_name", text="Client Name")
        self.client_tree.heading("contact", text="Contact")
        self.client_tree.column("client_name", width=150, anchor=tk.W)
        self.client_tree.column("contact", width=150, anchor=tk.W)

        scrollbar = ttk.Scrollbar(self.existing_client_frame, orient=tk.VERTICAL, command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=scrollbar.set)

        self.client_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.client_tree.bind("<<TreeviewSelect>>", self._on_client_select)

        # Common file name field for existing client
        ttk.Label(self.existing_client_frame, text="File Name:").pack(pady=(15, 5), anchor="w")
        self.existing_client_file_name_entry = ttk.Entry(self.existing_client_frame)
        self.existing_client_file_name_entry.pack(fill="x")

        # Submit button with green color
        style = ttk.Style()
        style.configure("Green.TButton", background="green", foreground="black")
        self.submit_btn = ttk.Button(self.main_frame, text="Submit", command=self._submit_form, style="Green.TButton")
        self.submit_btn.pack(pady=20)

        # Initial population of the table
        self._populate_clients_table()

    def _populate_clients_table(self):
        """Populates the client table with all clients."""
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        self.all_clients = self.db_manager.get_all_service_clients()
        for client in self.all_clients:
            self.client_tree.insert("", tk.END, values=(client['name'], client['contact']), iid=client['client_id'])

    def _filter_clients_table(self, event=None):
        """Filters the client table based on the search entry."""
        search_query = self.search_entry.get().lower()

        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        filtered_clients = [c for c in self.all_clients if
                            search_query in c['name'].lower() or search_query in c['contact'].lower()]

        for client in filtered_clients:
            self.client_tree.insert("", tk.END, values=(client['name'], client['contact']), iid=client['client_id'])

    def _on_client_select(self, event):
        """Saves the selected client's ID."""
        selected_item = self.client_tree.selection()
        if selected_item:
            self.selected_client_id = selected_item[0]
            print(f"Selected client ID: {self.selected_client_id}")

    def _submit_form(self):
        """Handles the submission logic based on the currently selected tab."""
        current_tab_id = self.notebook.index(self.notebook.select())

        if current_tab_id == 0:  # "Add New Client" tab
            name = self.name_entry.get().strip().upper()
            contact = self.contact_entry.get().strip().upper()
            brought_by = self.brought_by_entry.get().strip().upper()
            file_name = self.new_client_file_name_entry.get().strip().upper()

            if not all([name, contact, brought_by, file_name]):
                messagebox.showerror("Validation Error", "All fields are required for a new client.")
                return

            client_id = self.db_manager.add_service_client(name, contact, brought_by, self.user_id)
            if client_id:
                file_id = self.db_manager.add_client_file(client_id, file_name, self.user_id)
                if file_id:
                    messagebox.showinfo("Success", f"Client '{name}' and file '{file_name}' added successfully!")
                    self.destroy()
                    self.refresh_callback()
                else:
                    messagebox.showerror("Error", "Failed to add file. File name might be a duplicate.")
            else:
                messagebox.showerror("Error", "Failed to add client. Contact might already exist.")

        elif current_tab_id == 1:  # "Add New File to Existing Client" tab
            if not self.selected_client_id:
                messagebox.showerror("Validation Error", "Please select a client from the table.")
                return

            file_name = self.existing_client_file_name_entry.get().strip().upper()
            if not file_name:
                messagebox.showerror("Validation Error", "File Name cannot be empty.")
                return

            file_id = self.db_manager.add_client_file(self.selected_client_id, file_name, self.user_id)
            if file_id:
                messagebox.showinfo("Success", f"File '{file_name}' added successfully!")
                self.destroy()
                self.refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to add file. File name might be a duplicate for this client.")


class TrackJobsView(FormBase):
    """
    A system-wide view to track all jobs.
    Allows editing the status of a selected job.
    """

    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 950, 600, "Track All Jobs", "track_jobs.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader  # Store for button icons
        self._create_widgets()
        self._populate_jobs_table()

    def _create_widgets(self):
        ttk.Label(self, text="All System Jobs", font=('Helvetica', 14, 'bold')).pack(pady=10)

        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)

        columns = ("job_id", "client_name", "file_name", "description", "status")
        self.jobs_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.jobs_tree.heading("job_id", text="Job ID")
        self.jobs_tree.heading("client_name", text="Client Name")
        self.jobs_tree.heading("file_name", text="File Name")
        self.jobs_tree.heading("description", text="Description")
        self.jobs_tree.heading("status", text="Status")

        self.jobs_tree.column("job_id", width=80, anchor=tk.W)
        self.jobs_tree.column("client_name", width=150, anchor=tk.W)
        self.jobs_tree.column("file_name", width=150, anchor=tk.W)
        self.jobs_tree.column("description", width=300, anchor=tk.W)
        self.jobs_tree.column("status", width=120, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)

        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons for Edit Status and Cancel
        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill="x", pady=10)

        # Load icons for buttons
        self.edit_icon_ref = None
        self.cancel_icon_ref = None
        if self.parent_icon_loader:
            self.edit_icon_ref = self.parent_icon_loader("edit.png", size=(20, 20))
            self.cancel_icon_ref = self.parent_icon_loader("cancel.png", size=(20, 20))

        ttk.Button(button_frame, text="Edit Status", image=self.edit_icon_ref, compound=tk.LEFT,
                   command=self._open_edit_status_form).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", image=self.cancel_icon_ref, compound=tk.LEFT,
                   command=self.destroy).pack(side=tk.RIGHT, padx=10)

    def _populate_jobs_table(self):
        """Populates the table with all jobs, including client names and file names."""
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)

        try:
            all_jobs = self.db_manager.get_all_jobs()
            all_clients_data = self.db_manager.get_all_service_clients()
            client_name_map = {client['client_id']: client['name'] for client in all_clients_data}

            # Assuming db_manager also has a way to get file name by file_id
            # For this example, we'll create a mock file_name_map
            file_name_map = {}
            for job in all_jobs:
                file_id = job.get('file_id')
                if file_id and file_id not in file_name_map:
                    file_data = self.db_manager.get_file_by_id(file_id)
                    file_name_map[file_id] = file_data.get('file_name', 'N/A') if file_data else 'N/A'

            if not all_jobs:
                self.jobs_tree.insert("", tk.END, values=("", "", "", "No jobs found.", ""))
                return

            for job in all_jobs:
                job_id = job.get('job_id', 'N/A')
                client_id = job.get('client_id')
                file_id = job.get('file_id')  # Get file_id from job data
                description = job.get('job_description', 'N/A')
                status = job.get('status', 'N/A')

                client_name = client_name_map.get(client_id, 'Unknown Client')
                file_name = file_name_map.get(file_id, 'Unknown File')  # Get file_name from map

                self.jobs_tree.insert("", tk.END, values=(
                    job_id,
                    job['timestamp'], # Keep full timestamp for consistency
                    client_name,
                    file_name,
                    description.upper(),
                    status.upper()
                ), iid=job_id)  # Use job_id as iid for easy lookup

        except AttributeError as ae:
            messagebox.showerror("Database Error",
                                 f"Missing database method: {ae}. Ensure DatabaseManager has 'get_all_jobs', 'get_all_service_clients', and 'get_file_by_id' methods.")
            self.jobs_tree.insert("", tk.END, values=("", "", "", f"Error: {ae}", ""))
        except KeyError as ke:
            messagebox.showerror("Data Structure Error",
                                 f"Missing key in job/client data: {ke}. Check database return format.")
            self.jobs_tree.insert("", tk.END, values=("", "", "", f"Error: {ke}", ""))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.jobs_tree.insert("", tk.END, values=("", "", "", f"Error: {e}", ""))

    def _open_edit_status_form(self):
        """Opens a form to edit the status of the selected job."""
        selected_item = self.jobs_tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a job from the table to edit its status.")
            return

        # FIX: The iid is directly the selected_item[0]
        job_id = selected_item[0]

        # Fetch the full job data from the database
        job_data = self.db_manager.get_job_by_id(job_id)

        if job_data:
            EditJobStatusForm(
                master=self.master,
                db_manager=self.db_manager,
                job_data=job_data,
                refresh_callback=self._populate_jobs_table,  # Refresh this view after update
                parent_icon_loader=self.parent_icon_loader
            )
        else:
            messagebox.showerror("Error", f"Could not find details for Job ID: {job_id}")


class EditJobStatusForm(FormBase):
    """
    A form to edit the status of a selected job.
    """

    def __init__(self, master, db_manager, job_data, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 400, 250, f"Edit Job Status: {job_data['job_id']}", "edit.png", parent_icon_loader)
        self.db_manager = db_manager
        self.job_data = job_data
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text=f"Job ID: {self.job_data['job_id']}", font=('Helvetica', 10, 'bold')).pack(
            anchor="w", pady=5)
        ttk.Label(main_frame, text=f"Description: {self.job_data['job_description']}", font=('Helvetica', 10)).pack(
            anchor="w", pady=2)
        ttk.Label(main_frame, text=f"Current Status: {self.job_data['status']}", font=('Helvetica', 10)).pack(
            anchor="w", pady=2)

        ttk.Label(main_frame, text="Select New Status:").pack(anchor="w", pady=(10, 5))

        # Define available statuses (MUST match database CHECK constraint)
        self.new_status_var = tk.StringVar(self)
        # 🌟 FIX: Updated job_statuses to match the database schema 🌟
        job_statuses = ["Ongoing", "Completed", "Cancelled"]
        self.new_status_var.set(self.job_data['status'])  # Set initial value to current status

        self.status_option_menu = ttk.OptionMenu(
            main_frame,
            self.new_status_var,
            self.new_status_var.get(),
            *job_statuses
        )
        self.status_option_menu.pack(fill="x", pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)

        ttk.Button(button_frame, text="Update Status", command=self._update_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _update_status(self):
        new_status = self.new_status_var.get()
        if new_status == self.job_data['status']:
            messagebox.showinfo("No Change", "Job status is already set to this value.")
            return

        success = self.db_manager.update_job_status(self.job_data['job_id'], new_status)

        if success:
            messagebox.showinfo("Success", f"Job {self.job_data['job_id']} status updated to {new_status}.")
            self.refresh_callback()  # Refresh the jobs table in TrackJobsView
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to update job status.")


class ManagePaymentsView(FormBase):
    """
    A system-wide view for managing payments, displaying more detailed job and client info.
    Includes a button to print receipts for selected payments.
    """

    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 900, 550, "Manage Payments", "manage_payments.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader # Store for button icons
        self._create_widgets()
        self._populate_payments_table()

    def _create_widgets(self):
        ttk.Label(self, text="Payment Management System", font=('Helvetica', 14, 'bold')).pack(pady=10)

        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)

        # Updated columns based on the image: Payment ID, Job ID, Client Name, Task, Amount, Date
        columns = ("payment_id", "job_id", "client_name", "task_description", "amount", "payment_date", "payment_type")
        self.payments_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        self.payments_tree.heading("payment_id", text="Payment ID")
        self.payments_tree.heading("job_id", text="Job ID")
        self.payments_tree.heading("client_name", text="Client Name")
        self.payments_tree.heading("task_description", text="Task")
        self.payments_tree.heading("amount", text="Amount")
        self.payments_tree.heading("payment_date", text="Date")
        self.payments_tree.heading("payment_type", text="Type")

        self.payments_tree.column("payment_id", width=80, anchor=tk.W)
        self.payments_tree.column("job_id", width=60, anchor=tk.W)
        self.payments_tree.column("client_name", width=150, anchor=tk.W)
        self.payments_tree.column("task_description", width=250, anchor=tk.W)
        self.payments_tree.column("amount", width=100, anchor=tk.E)  # Right-align amount
        self.payments_tree.column("payment_date", width=120, anchor=tk.W)
        self.payments_tree.column("payment_type", width=100, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=scrollbar.set)

        self.payments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill="x", pady=10)

        self.refresh_icon_ref = None
        self.print_icon_ref = None # New icon reference for Print button
        if self.parent_icon_loader:
            self.refresh_icon_ref = self.parent_icon_loader("refresh.png",
                                                            size=(20, 20))  # Assuming a refresh icon exists
            self.print_icon_ref = self.parent_icon_loader("print_icon.png", # Assuming a print icon exists
                                                           size=(20, 20))

        ttk.Button(button_frame, text="Refresh", image=self.refresh_icon_ref, compound=tk.LEFT,
                   command=self._populate_payments_table).pack(side=tk.LEFT, padx=5)

        # New Print Receipt Button
        ttk.Button(button_frame, text="Print Receipt", image=self.print_icon_ref, compound=tk.LEFT,
                   command=self._print_receipt_for_selected_payment).pack(side=tk.RIGHT, padx=5)


    def _populate_payments_table(self):
        """Populates the table with payment records, including related job and client data."""
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)

        try:
            payments = self.db_manager.get_all_payments()

            if not payments:
                self.payments_tree.insert("", tk.END, values=("", "", "", "No payments found.", "", "", ""))
                return

            for payment in payments:
                payment_id = payment.get('payment_id', 'N/A')
                job_id = payment.get('job_id', 'N/A')
                amount = f"KSh {payment.get('amount', 0.00):,.2f}"  # Format as currency
                payment_date = payment.get('payment_date', 'N/A')
                payment_type = payment.get('payment_type', 'N/A')

                client_name = 'Unknown Client'
                task_description = 'Unknown Task'
                file_name = 'N/A' # Initialize file_name here

                if job_id != 'N/A':
                    job_data = self.db_manager.get_job_by_id(job_id)
                    if job_data:
                        task_description = job_data.get('job_description', 'N/A').upper()
                        client_id = job_data.get('client_id')
                        file_id = job_data.get('file_id') # Get file_id from job_data

                        if client_id:
                            client_data = self.db_manager.get_client_by_id(client_id)
                            if client_data:
                                client_name = client_data.get('name', 'N/A').upper()
                        if file_id:
                            file_data = self.db_manager.get_file_by_id(file_id)
                            if file_data:
                                file_name = file_data.get('file_name', 'N/A').upper()


                self.payments_tree.insert("", tk.END, values=(
                    payment_id,
                    job_id,
                    client_name,
                    task_description,
                    amount,
                    payment_date,
                    payment_type
                ), iid=payment_id)  # Use payment_id as iid

        except AttributeError as ae:
            messagebox.showerror("Database Error",
                                 f"Missing database method: {ae}. Ensure DatabaseManager has 'get_all_payments', 'get_job_by_id', 'get_client_by_id', and 'get_file_by_id' methods.")
            self.payments_tree.insert("", tk.END, values=("", "", "", f"Error: {ae}", "", "", ""))
        except KeyError as ke:
            messagebox.showerror("Data Structure Error",
                                 f"Missing key in data: {ke}. Check database return format for payments, jobs, or clients.")
            self.payments_tree.insert("", tk.END, values=("", "", "", f"Error: {ke}", "", "", ""))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.payments_tree.insert("", tk.END, values=("", "", "", f"Error: {e}", "", "", ""))

    def _print_receipt_for_selected_payment(self):
        """
        Retrieves details for the selected payment and generates a PDF receipt.
        """
        selected_item = self.payments_tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a payment from the table to print a receipt.")
            return

        payment_id = selected_item[0]
        payment_data = self.db_manager.get_payment_by_id(payment_id)

        if not payment_data:
            messagebox.showerror("Error", f"Could not retrieve details for Payment ID: {payment_id}")
            return

        # Extract details for the receipt
        job_id = payment_data.get('job_id', 'N/A')
        amount_paid = payment_data.get('amount', 0.0)
        payment_date = payment_data.get('payment_date', 'N/A')

        # Fetch associated job and client data
        client_name = 'Unknown Client'
        file_name = 'N/A'
        job_description = 'N/A'

        if job_id != 'N/A':
            job_data = self.db_manager.get_job_by_id(job_id)
            if job_data:
                job_description = job_data.get('job_description', 'N/A')
                client_id = job_data.get('client_id')
                file_id = job_data.get('file_id')

                if client_id:
                    client_data = self.db_manager.get_client_by_id(client_id)
                    if client_data:
                        client_name = client_data.get('name', 'N/A')
                if file_id:
                    file_data = self.db_manager.get_file_by_id(file_id)
                    if file_data:
                        file_name = file_data.get('file_name', 'N/A')

        # Generate the PDF receipt using the helper function
        receipt_path = _generate_pdf_payment_receipt(
            job_id=job_id,
            client_name=client_name,
            file_name=file_name,
            job_description=job_description,
            amount_paid=amount_paid,
            payment_date=payment_date
        )

        if receipt_path:
            SuccessMessage(
                self.master,
                success=True,
                message=f"Receipt for Payment ID {payment_id} generated successfully!",
                pdf_path=receipt_path,
                parent_icon_loader=self.parent_icon_loader
            )
        else:
            messagebox.showerror("Receipt Error", f"Failed to generate receipt for Payment ID {payment_id}.")



class JobReportsView(FormBase):
    """
    A system-wide view for generating job reports, including daily, monthly, yearly,
    and custom range reports based on job status.
    """

    def __init__(self, master, db_manager, parent_icon_loader=None):
        super().__init__(master, 750, 600, "Job Reports", "survey_reports.png", parent_icon_loader)
        self.db_manager = db_manager
        self.parent_icon_loader_ref = parent_icon_loader  # Store for icon loading

        self.report_type_var = tk.StringVar(self, value="daily")
        self.job_status_var = tk.StringVar(self, value="All")
        self.from_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))
        self.to_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))

        # Icon references for internal buttons
        self._calendar_icon = None
        self._generate_report_icon = None

        self._create_widgets()
        self._toggle_date_entries()  # Initialize date entry states
        # self._generate_report() # Optional: generate a default report on open

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Generate Job Reports", font=('Helvetica', 14, 'bold')).pack(pady=10)

        # --- Report Options Frame ---
        options_frame = ttk.LabelFrame(main_frame, text="Report Options", padding="10")
        options_frame.pack(fill="x", pady=10)

        # Report Type Radio Buttons
        ttk.Label(options_frame, text="Report Period:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(options_frame, text="Daily", variable=self.report_type_var, value="daily",
                        command=self._toggle_date_entries).grid(row=0, column=1, padx=2, pady=5, sticky="w")
        ttk.Radiobutton(options_frame, text="Monthly", variable=self.report_type_var, value="monthly",
                        command=self._toggle_date_entries).grid(row=0, column=2, padx=2, pady=5, sticky="w")
        ttk.Radiobutton(options_frame, text="Yearly", variable=self.report_type_var, value="yearly",
                        command=self._toggle_date_entries).grid(row=0, column=3, padx=2, pady=5, sticky="w")
        ttk.Radiobutton(options_frame, text="Custom Range", variable=self.report_type_var, value="custom",
                        command=self._toggle_date_entries).grid(row=0, column=4, padx=2, pady=5, sticky="w")

        # Job Status Dropdown
        ttk.Label(options_frame, text="Job Status:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.status_combobox = ttk.Combobox(options_frame, textvariable=self.job_status_var,
                                            values=["All", "Ongoing", "Completed", "Cancelled"], state="readonly")
        self.status_combobox.grid(row=1, column=1, columnspan=4, padx=5, pady=5, sticky="ew")

        # Custom Date Range Inputs
        date_range_frame = ttk.Frame(options_frame)
        date_range_frame.grid(row=2, column=0, columnspan=5, pady=5, sticky="ew")

        ttk.Label(date_range_frame, text="From Date:").pack(side="left", padx=5)
        self.from_date_entry = ttk.Entry(date_range_frame, textvariable=self.from_date_var, state="readonly", width=12)
        self.from_date_entry.pack(side="left", padx=2)

        if self.parent_icon_loader:
            self._calendar_icon = self.parent_icon_loader("calendar_icon.png", size=(20, 20))

        self.from_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon,
                                       command=lambda: self._open_datepicker(self.from_date_var))
        self.from_cal_btn.image = self._calendar_icon  # Keep reference
        self.from_cal_btn.pack(side="left", padx=2)

        ttk.Label(date_range_frame, text="To Date:").pack(side="left", padx=(15, 5))
        self.to_date_entry = ttk.Entry(date_range_frame, textvariable=self.to_date_var, state="readonly", width=12)
        self.to_date_entry.pack(side="left", padx=2)
        self.to_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon,
                                     command=lambda: self._open_datepicker(self.to_date_var))
        self.to_cal_btn.image = self._calendar_icon  # Keep reference
        self.to_cal_btn.pack(side="left", padx=2)

        # Configure columns to expand
        options_frame.grid_columnconfigure(1, weight=1)
        options_frame.grid_columnconfigure(2, weight=1)
        options_frame.grid_columnconfigure(3, weight=1)
        options_frame.grid_columnconfigure(4, weight=1)

        # Generate Report Button
        if self.parent_icon_loader:
            self._generate_report_icon = self.parent_icon_loader("report.png", size=(20, 20))

        ttk.Button(main_frame, text="Generate PDF Report", image=self._generate_report_icon, compound=tk.LEFT,
                   command=self._generate_report).pack(pady=15)

        # --- Report Preview Area ---
        report_preview_frame = ttk.LabelFrame(main_frame, text="Report Preview", padding="10")
        report_preview_frame.pack(fill="both", expand=True, pady=10)
        report_preview_frame.grid_columnconfigure(0, weight=1)
        report_preview_frame.grid_rowconfigure(0, weight=1)

        self.report_text_widget = tk.Text(report_preview_frame, wrap=tk.WORD, height=10, font=('Helvetica', 9))
        self.report_text_widget.grid(row=0, column=0, sticky="nsew")

        report_scroll_y = ttk.Scrollbar(report_preview_frame, orient="vertical", command=self.report_text_widget.yview)
        report_scroll_y.grid(row=0, column=1, sticky="ns")
        self.report_text_widget.config(yscrollcommand=report_scroll_y.set)

        report_scroll_x = ttk.Scrollbar(report_preview_frame, orient="horizontal",
                                        command=self.report_text_widget.xview)
        report_scroll_x.grid(row=1, column=0, sticky="ew")
        self.report_text_widget.config(xscrollcommand=report_scroll_x.set)

    def _toggle_date_entries(self):
        """Enables/disables custom date entry fields based on report type selection."""
        report_type = self.report_type_var.get()
        is_custom = (report_type == "custom")
        state = "normal" if is_custom else "readonly"
        button_state = "normal" if is_custom else "disabled"

        self.from_date_entry.config(state=state)
        self.to_date_entry.config(state=state)
        self.from_cal_btn.config(state=button_state)
        self.to_cal_btn.config(state=button_state)

        # Set default dates based on report type if not custom
        today = datetime.now()
        if report_type == "daily":
            self.from_date_var.set(today.strftime("%Y-%m-%d"))
            self.to_date_var.set(today.strftime("%Y-%m-%d"))
        elif report_type == "monthly":
            first_day_of_month = today.replace(day=1)
            # Calculate last day of the current month
            if today.month == 12:
                last_day_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            self.from_date_var.set(first_day_of_month.strftime("%Y-%m-%d"))
            self.to_date_var.set(last_day_of_month.strftime("%Y-%m-%d"))
        elif report_type == "yearly":
            first_day_of_year = today.replace(month=1, day=1)
            last_day_of_year = today.replace(month=12, day=31)
            self.from_date_var.set(first_day_of_year.strftime("%Y-%m-%d"))
            self.to_date_var.set(last_day_of_year.strftime("%Y-%m-%d"))

    def _open_datepicker(self, target_var):
        """Opens date picker for a specific StringVar."""
        current_date_str = target_var.get()
        try:
            current_date_obj = datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            current_date_obj = datetime.now()

        DatePicker(self, current_date_obj, lambda d: target_var.set(d),
                   parent_icon_loader=self.parent_icon_loader_ref,
                   window_icon_name="calendar_icon.png")

    def _get_report_dates(self):
        """Determines start and end dates based on selected report type."""
        report_type = self.report_type_var.get()
        start_date_str = self.from_date_var.get()
        end_date_str = self.to_date_var.get()

        if report_type == "custom":
            if not self._is_valid_date(start_date_str) or not self._is_valid_date(end_date_str):
                messagebox.showerror("Date Error", "Invalid custom date range. Please use YYYY-MM-DD format.")
                return None, None
            if start_date_str > end_date_str:
                messagebox.showerror("Date Error", "Start date cannot be after end date.")
                return None, None

        return start_date_str, end_date_str

    def _is_valid_date(self, date_string):
        """Validates date format."""
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _generate_report(self):
        """
        Fetches job data based on filters and generates a PDF report.
        """
        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error",
                                 "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            self.report_text_widget.delete("1.0", tk.END)
            self.report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        self.report_text_widget.delete("1.0", tk.END)  # Clear previous content
        self.report_text_widget.insert("1.0", "Generating report, please wait...")  # Show status

        start_date, end_date = self._get_report_dates()
        if start_date is None:
            self.report_text_widget.delete("1.0", tk.END)  # Clear "generating" message
            return  # Date validation failed

        selected_status = self.job_status_var.get()
        db_status = selected_status if selected_status != "All" else None

        try:
            # Call the database manager method to get job data
            jobs_for_report = self.db_manager.get_service_jobs_for_report(
                start_date=start_date,
                end_date=end_date,
                status=db_status
            )

            report_name = f"Service Jobs Report ({selected_status})"
            pdf_path = self._generate_pdf_report(
                report_name,
                {'data': jobs_for_report},
                self.report_type_var.get(),
                start_date,
                end_date
            )

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Service Jobs Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, self.report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Service Jobs Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, self.report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating Job Report: {e}")
            self.report_text_widget.delete("1.0", tk.END)
            self.report_text_widget.insert("1.0", f"Error: {e}")

    def _generate_pdf_report(self, report_name, content, report_type, start_date, end_date):
        """Generates PDF report using ReportLab and returns the file path."""
        if not _REPORTLAB_AVAILABLE:
            return None  # Error message already shown by calling function

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        period_suffix = ""

        if report_type == "daily":
            period_suffix = f"_{start_date}"
        elif report_type == "monthly":
            period_suffix = f"_{datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m')}"
        elif report_type == "yearly":
            period_suffix = f"_{datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y')}"
        elif report_type == "custom":
            period_suffix = f"_{start_date}_to_{end_date}"

        file_name = f"{report_name.replace(' ', '_')}{period_suffix}_{timestamp}.pdf"
        file_path = os.path.join(REPORTS_DIR, file_name)

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Business Header with Timestamp
            header_table = Table([
                ["MATHENGE REAL ESTATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ], colWidths=[4 * inch, 2 * inch])

            header_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, -1), 14),
                ('FONTSIZE', (1, 0), (1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(header_table)

            # Report Title
            story.append(Paragraph(f"<b>{report_name.upper()}</b>", styles['Heading2']))
            story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
            story.append(Spacer(1, 12))

            if content.get('data'):
                headers = ["Job ID", "Date", "Client Name", "File Name", "Description", "Status"]
                table_data = [headers]

                for job in content['data']:
                    date_part = job['timestamp'].split(' ')[0] if ' ' in job['timestamp'] else job['timestamp']
                    table_data.append([
                        job['job_id'],
                        date_part,
                        job['client_name'],
                        job['file_name'],
                        job['job_description'],
                        job['status']
                    ])

                # Adjust column widths dynamically or provide fixed widths
                col_widths = [0.8 * inch, 1.2 * inch, 1.5 * inch, 1.5 * inch, 1.8 * inch, 1 * inch]
                t = Table(table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ]))
                story.append(t)
            else:
                story.append(Paragraph("No jobs found for this period and status.", styles['Normal']))

            # Build the PDF
            doc.build(story)
            return file_path

        except Exception as e:
            print(f"PDF generation failed: {e}")
            return None

    def _show_pdf_preview(self, pdf_path, report_text_widget):
        """Displays PDF generation status in the preview area."""
        if pdf_path and os.path.exists(pdf_path):
            preview_text = f"PDF successfully generated and saved to:\n{pdf_path}\n\n"
            preview_text += "Note: A full PDF preview is not available directly within Tkinter. You can open the file from the saved location.\n\n"

            # Add a basic file info
            preview_text += f"File size: {os.path.getsize(pdf_path) / 1024:.1f} KB"

            report_text_widget.delete(1.0, tk.END)
            report_text_widget.insert(tk.END, preview_text)
        else:
            report_text_widget.delete(1.0, tk.END)
            report_text_widget.insert(tk.END,
                                      "PDF generation failed. Please check the error logs or ensure ReportLab is installed and data is available.")


# Dummy DatePicker and REPORTS_DIR if not defined in your context
# You should ensure these are properly imported/defined in your actual project
if 'DatePicker' not in locals():
    class DatePicker(tk.Toplevel):
        def __init__(self, master, current_date, callback, parent_icon_loader=None, window_icon_name=None):
            super().__init__(master)
            self.title("Select Date")
            self.transient(master)
            self.grab_set()
            self.callback = callback
            self.current_date = current_date

            # Simple placeholder for DateEntry
            if DateEntry:
                self.cal = DateEntry(self, selectmode='day', year=current_date.year, month=current_date.month,
                                     day=current_date.day)
                self.cal.pack(padx=10, pady=10)
                self.cal.bind("<<DateSelected>>", self._on_date_selected)
            else:
                ttk.Label(self, text="DateEntry not available. Cannot select date.").pack(padx=10, pady=10)
                ttk.Button(self, text="OK", command=self.destroy).pack(pady=5)

        def _on_date_selected(self, event):
            self.callback(self.cal.get_date().strftime("%Y-%m-%d"))
            self.destroy()

# Ensure REPORTS_DIR is defined if not already in global scope or imported
if 'REPORTS_DIR' not in locals():
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    os.makedirs(REPORTS_DIR, exist_ok=True)
