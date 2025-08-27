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
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
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

class ClientFileDashboard(FormBase):
    """
    A dashboard view for a specific client's file. It shows their recent tasks
    and allows for the creation of new tasks.
    """
    def __init__(self, master, db_manager, client_data, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 700, 600, f"Client File: {client_data['name']}", "client_file.png", parent_icon_loader)
        self.db_manager = db_manager
        self.client_data = client_data
        self.refresh_callback = refresh_callback
        self._create_widgets()
        self._populate_tasks_table()

    def _create_widgets(self):
        # Top section with client details and new task form
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill="x", pady=10)
        
        ttk.Label(top_frame, text=f"Client Name: {self.client_data['name']}", font=('Helvetica', 12, 'bold')).pack(side="left", padx=10)
        ttk.Label(top_frame, text=f"File Name: {self.client_data['file_name']}", font=('Helvetica', 10)).pack(side="left", padx=10)
        
        # New task form fields - simplified for this dashboard
        task_frame = ttk.Frame(self, padding="10")
        task_frame.pack(fill="x", pady=10)
        
        ttk.Label(task_frame, text="Description:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.task_description_entry = ttk.Entry(task_frame)
        self.task_description_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(task_frame, text="Price:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.task_price_entry = ttk.Entry(task_frame)
        self.task_price_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Button(task_frame, text="Add New Task", command=self._add_new_task).grid(row=2, column=0, columnspan=2, pady=10)

        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10, padx=10)

        # Middle section with tasks table
        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)

        columns = ("job_id", "description", "status")
        self.tasks_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tasks_tree.heading("job_id", text="Job ID")
        self.tasks_tree.heading("description", text="Task Description")
        self.tasks_tree.heading("status", text="Status")
        
        self.tasks_tree.column("job_id", width=80, anchor=tk.W)
        self.tasks_tree.column("description", width=400, anchor=tk.W)
        self.tasks_tree.column("status", width=120, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tasks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _populate_tasks_table(self):
        """Populates the tasks table with data for the selected client."""
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        # Using the new get_jobs_by_client_id method
        tasks = self.db_manager.get_jobs_by_client_id(self.client_data['client_id'])
        for task in tasks:
            self.tasks_tree.insert("", tk.END, values=(task['job_id'], task['job_description'], task['status']))

    def _add_new_task(self):
        """Handles adding a new task for the selected client."""
        description = self.task_description_entry.get().strip()
        price = self.task_price_entry.get().strip()
        
        if not description or not price:
            messagebox.showerror("Input Error", "Please provide a description and price for the new task.")
            return

        try:
            price_val = float(price)
        except ValueError:
            messagebox.showerror("Input Error", "Price must be a valid number.")
            return

        # Call the new add_job method from DatabaseManager
        # We'll use a placeholder for added_by for now.
        job_id = self.db_manager.add_job(
            client_id=self.client_data['client_id'],
            job_description=description,
            fee=price_val,
            added_by="current_user" # This should be replaced with actual user data
        )
        
        if job_id:
            messagebox.showinfo("Success", "New task added successfully.")
            self._populate_tasks_table()
            self.refresh_callback() # Refresh the main dashboard if needed
            self.task_description_entry.delete(0, tk.END)
            self.task_price_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Failed to add new task.")


class AddNewClientForm(FormBase):
    """
    A form to register a new client.
    """
    def __init__(self, master, db_manager,refresh_callback,user_id, parent_icon_loader=None):
        super().__init__(master, 450, 300, "Register New Client", "add_client.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        self._create_widgets()
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        # Client Name
        ttk.Label(main_frame, text="Client Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.client_name_entry = ttk.Entry(main_frame)
        self.client_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # File Name
        ttk.Label(main_frame, text="File Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.file_name_entry = ttk.Entry(main_frame)
        self.file_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Contact
        ttk.Label(main_frame, text="Contact Info:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.contact_entry = ttk.Entry(main_frame)
        self.contact_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        #BROUGHT BY - Future feature, not implemented yet
        ttk.Label(main_frame, text="Brought By:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.brought_by_entry = ttk.Entry(main_frame)
        self.brought_by_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save Client", command=self._save_client).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", command=self._on_closing).pack(side="right", padx=10)
    
    def _save_client(self):
        client_name = self.client_name_entry.get().strip()
        file_name = self.file_name_entry.get().strip()
        contact = self.contact_entry.get().strip()
        brought_by = self.brought_by_entry.get().strip()
        
        if not all([client_name, file_name, contact, brought_by]):
            messagebox.showerror("Input Error", "All fields are required.")
            return
        
        # Call the new add_client method
        client_id = self.db_manager.add_service_client(
            name=client_name,
            contact=contact,
            file_name=file_name,
            brought_by="", # Placeholder for a future feature
            added_by=self.user_id # This should be replaced with actual user data
        )

        if client_id:
            messagebox.showinfo("Success", "New client registered successfully!")
            self.refresh_callback() # Refresh main dashboard
            self._on_closing()
        else:
            messagebox.showerror("Error", "A client with this File Name already exists.")


class TrackJobsView(FormBase):
    """
    A system-wide view to track all jobs.
    """
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 800, 600, "Track All Jobs", "track_jobs.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self._create_widgets()
        self._populate_jobs_table()

    def _create_widgets(self):
        # A simple table to display all jobs
        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)

        columns = ("job_id", "client_name", "description", "status")
        self.jobs_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.jobs_tree.heading("job_id", text="Job ID")
        self.jobs_tree.heading("client_name", text="Client Name")
        self.jobs_tree.heading("description", text="Description")
        self.jobs_tree.heading("status", text="Status")
        
        self.jobs_tree.column("job_id", width=80, anchor=tk.W)
        self.jobs_tree.column("client_name", width=150, anchor=tk.W)
        self.jobs_tree.column("description", width=400, anchor=tk.W)
        self.jobs_tree.column("status", width=120, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _populate_jobs_table(self):
        """Populates the table with all jobs."""
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Using the new get_all_jobs method and mapping client IDs to names
        all_jobs = self.db_manager.get_all_jobs()
        all_clients = {c['client_id']: c['name'] for c in self.db_manager.get_all_service_clients()}
        
        for job in all_jobs:
            client_name = all_clients.get(job['client_id'], 'Unknown Client')
            self.jobs_tree.insert("", tk.END, values=(job['job_id'], client_name, job['job_description'], job['status']))


class ManagePaymentsView(FormBase):
    """
    A system-wide view for managing payments.
    """
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 700, 500, "Manage Payments", "manage_payments.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self._create_widgets()
        self._populate_payments_table()

    def _create_widgets(self):
        # Placeholder for payment management UI
        ttk.Label(self, text="Payment Management System", font=('Helvetica', 14, 'bold')).pack(pady=20)
        
        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)
        
        columns = ("payment_id", "job_id", "amount", "payment_date", "payment_type")
        self.payments_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.payments_tree.heading("payment_id", text="Payment ID")
        self.payments_tree.heading("job_id", text="Job ID")
        self.payments_tree.heading("amount", text="Amount")
        self.payments_tree.heading("payment_date", text="Date")
        self.payments_tree.heading("payment_type", text="Type")
        
        self.payments_tree.column("payment_id", width=80)
        self.payments_tree.column("job_id", width=80)
        self.payments_tree.column("amount", width=120)
        self.payments_tree.column("payment_date", width=150)
        self.payments_tree.column("payment_type", width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=scrollbar.set)
        
        self.payments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _populate_payments_table(self):
        """Populates the table with payment records."""
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)
        
        # This function isn't yet in DatabaseManager, but assuming a get_all_payments()
        # for a future implementation.
        payments = self.db_manager.get_all_payments()
        for payment in payments:
            self.payments_tree.insert("", tk.END, values=(payment['payment_id'], payment['job_id'], payment['amount'], payment['payment_date'], payment['payment_type']))


class JobReportsView(FormBase):
    """
    A system-wide view for generating job reports.
    """
    def __init__(self, master, db_manager, parent_icon_loader=None):
        super().__init__(master, 500, 400, "Job Reports", "survey_reports.png", parent_icon_loader)
        self.db_manager = db_manager
        self._create_widgets()

    def _create_widgets(self):
        # UI for generating reports
        ttk.Label(self, text="Generate Job Reports", font=('Helvetica', 14, 'bold')).pack(pady=20)
        
        # Placeholder for report generation options
        ttk.Label(self, text="Select a report type and time range:").pack(pady=5)
        
        ttk.Button(self, text="Generate PDF Report", command=self._generate_report).pack(pady=20)

    def _generate_report(self):
        """Calls the database manager to generate a PDF report."""
        pdf_path = self.db_manager.generate_report()
        if pdf_path:
            messagebox.showinfo("Report Generated", f"Report saved successfully at: {pdf_path}")
            # Optional: Open the folder containing the report
            # import subprocess
            # if sys.platform == "win32":
            #     os.startfile(os.path.dirname(pdf_path))
            # elif sys.platform == "darwin":
            #     subprocess.Popen(["open", os.path.dirname(pdf_path)])
            # else:
            #     subprocess.Popen(["xdg-open", os.path.dirname(pdf_path)])
        else:
            messagebox.showerror("Error", "Failed to generate report.")
