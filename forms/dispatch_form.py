import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta, date
import os
import shutil
import io
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from tkcalendar import DateEntry
from utils.tooltips import ToolTip

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
                    print(f"Icon '{icon_name}' loaded successfully.") # Add this line
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

class DispatchDetailsForm(FormBase):
    """
    A form for entering dispatch details for a specific completed job.
    """
    def __init__(self, master, db_manager, job_id, refresh_callback, parent_icon_loader):
        super().__init__(master, 500, 450, "Dispatch Job", "dispatch.png", parent_icon_loader)
        self.db_manager = db_manager
        self.job_id = job_id
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self.selected_files = []
        
        # Fetch job details when the form is initialized
        self.job_details = self.db_manager.get_job_details(self.job_id)
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Job details display
        job_details_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 20))
        job_details_frame.pack(fill="x")

        # Labels for the information headers
        ttk.Label(job_details_frame, text="Client Name:", font=('Helvetica', 10, 'bold')).pack(side="left", padx=10)
        ttk.Label(job_details_frame, text="Job Description:", font=('Helvetica', 10, 'bold')).pack(side="left", padx=10, expand=True)
        ttk.Label(job_details_frame, text="Title Number:", font=('Helvetica', 10, 'bold')).pack(side="right", padx=10)
        
        # Frame for the actual data
        data_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 20))
        data_frame.pack(fill="x")

        # Use fetched details to populate the labels
        ttk.Label(data_frame, text=self.job_details.get('client_name', 'N/A').upper()).pack(side="left", padx=10)
        ttk.Label(data_frame, text=self.job_details.get('job_description', 'N/A').upper()).pack(side="left", padx=10, expand=True)
        ttk.Label(data_frame, text=self.job_details.get('title_number', 'N/A').upper()).pack(side="right", padx=10)
        
        # --- Form input fields ---
        
        # Reason for Dispatch
        ttk.Label(main_frame, text="Reason for Dispatch:", font=('Helvetica', 8, 'bold')).pack(anchor="w")
        self.reason_entry = ttk.Entry(main_frame, width=50)
        self.reason_entry.pack(fill="x", pady=(0, 10))

        # Collected By
        ttk.Label(main_frame, text="Collected By:", font=('Helvetica', 8, 'bold')).pack(anchor="w")
        self.collected_by_entry = ttk.Entry(main_frame, width=50)
        self.collected_by_entry.pack(fill="x", pady=(0, 10))

        # Collector Phone Number
        ttk.Label(main_frame, text="Collector Phone Number:", font=('Helvetica', 8, 'bold')).pack(anchor="w")
        self.phone_entry = ttk.Entry(main_frame, width=50)
        self.phone_entry.pack(fill="x", pady=(0, 10))
        
        # Signature File Upload Section
        file_frame = ttk.LabelFrame(main_frame, text="Digital Signature (PDF)", padding=10)
        file_frame.pack(fill="x", pady=10)
        
        self.file_list_label = ttk.Label(file_frame, text="No files selected.")
        self.file_list_label.pack(side="left", padx=5)
        
        upload_icon = self.parent_icon_loader("folder.png", size=(16, 16))
        self.upload_btn = ttk.Button(file_frame, text="Select Files", image=upload_icon, compound="left", command=self._select_files)
        self.upload_btn.pack(side="right", padx=5)
        
        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        submit_icon = self.parent_icon_loader("confirm.png", size=(16, 16))
        submit_btn = ttk.Button(button_frame, text="Submit", image=submit_icon, compound="left", command=self._submit_dispatch)
        submit_btn.pack(side="left", padx=5)
        
        cancel_icon = self.parent_icon_loader("cancel.png", size=(16, 16))
        cancel_btn = ttk.Button(button_frame, text="Cancel", image=cancel_icon, compound="left", command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        
    def _select_files(self):
        """Allows the user to select up to 3 PDF files for signature."""
        file_types = [("PDF files", "*.pdf")]
        # filedialog.askopenfilenames returns a tuple of file paths
        filenames = filedialog.askopenfilenames(
            title="Select Signature Files (max 3)",
            filetypes=file_types
        )
        
        if len(filenames) > 3:
            messagebox.showwarning("File Limit Exceeded", "You can only select a maximum of 3 files.")
            self.selected_files = list(filenames[:3]) # Truncate to 3 files
        else:
            self.selected_files = list(filenames)
        
        if self.selected_files:
            file_names_text = ", ".join([os.path.basename(f) for f in self.selected_files])
            self.file_list_label.config(text=f"Selected: {file_names_text.upper()}")
        else:
            self.file_list_label.config(text="NO FILES SELECTED.")
        
    def _submit_dispatch(self):
        """Handles the submission of the dispatch details to the database."""
        reason = self.reason_entry.get().strip()
        collected_by = self.collected_by_entry.get().strip()
        phone = self.phone_entry.get().strip()

        if not all([reason, collected_by, phone]):
            messagebox.showwarning("Missing Information", "Please fill in all fields.")
            return

        # Read the file contents into a BLOB
        # In a real app, you would handle this more robustly
        signs_data_blob = None
        if self.selected_files:
            try:
                # For simplicity, we'll just read the first file as the BLOB.
                # In a real app, you'd handle multiple files or a composite BLOB.
                with open(self.selected_files[0], 'rb') as f:
                    signs_data_blob = f.read()
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to read file: {e}")
                return

        if self.db_manager.save_dispatch_details(
            self.job_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            reason,
            collected_by,
            phone,
            signs_data_blob
        ):
            messagebox.showinfo("Success", "Job dispatched successfully.")
            self.refresh_callback() # Refresh the main table
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to dispatch job.")

class DispatchJobsView(FormBase):
    """
    A form with a notebook to manage dispatching and viewing dispatch records.
    """
    def __init__(self, master, db_manager, refresh_callback, user_id, parent_icon_loader):
        super().__init__(master, 1200, 600, "Job Dispatch & Records", "dispatch.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader
        self.update_icon = None
        self.apply_icon = None
        self.clear_icon = None

        

        self._create_widgets()
        self.populate_completed_jobs_table()
        self.populate_dispatch_records_table()
        self._update_dispatch_button_state()
        
    def refresh_all_tables(self):
        """Refreshes both the completed jobs and dispatch records tables."""
        self.populate_completed_jobs_table()
        self.populate_dispatch_records_table()

    def _create_widgets(self):
        # Create a notebook to hold the two tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame for the Dispatch Jobs tab
        self.dispatch_jobs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dispatch_jobs_tab, text="Dispatch Jobs")
        self._create_dispatch_jobs_tab()

        # Frame for the Dispatch Records tab
        self.dispatch_records_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dispatch_records_tab, text="Dispatch Records")
        self._create_dispatch_records_tab()

    def _create_dispatch_jobs_tab(self):
        """Creates the widgets for the 'Dispatch Jobs' tab."""
        search_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10 5")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        ToolTip(self.search_entry, "Search Jobs Using Title Name, File Name, Client Name, Title Number or Task Type .")

        table_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10")
        table_frame.pack(fill="both", expand=True)

        columns = ("job_id", "date", "task_type", "title_name", "title_number", "file_name", "client_name", "status")
        self.completed_jobs_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.completed_jobs_tree.heading("job_id", text="Job ID")
        self.completed_jobs_tree.heading("date", text="Date")
        self.completed_jobs_tree.heading("task_type", text="Task Type")
        self.completed_jobs_tree.heading("title_name", text="Title Name")
        self.completed_jobs_tree.heading("title_number", text="Title Number")
        self.completed_jobs_tree.heading("file_name", text="File Name")
        self.completed_jobs_tree.heading("client_name", text="Client Name")
        self.completed_jobs_tree.heading("status", text="Status")
        
        self.completed_jobs_tree.column("job_id", width=60, anchor=tk.CENTER)
        self.completed_jobs_tree.column("date", width=120, anchor=tk.W)
        self.completed_jobs_tree.column("task_type", width=250, anchor=tk.W)
        self.completed_jobs_tree.column("title_name", width=120, anchor=tk.W)
        self.completed_jobs_tree.column("title_number", width=120, anchor=tk.W)
        self.completed_jobs_tree.column("file_name", width=100, anchor=tk.W)
        self.completed_jobs_tree.column("client_name", width=150, anchor=tk.W)
        self.completed_jobs_tree.column("status", width=100, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.completed_jobs_tree.yview)
        self.completed_jobs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.completed_jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.completed_jobs_tree.bind("<<TreeviewSelect>>", self._update_dispatch_button_state)
        ToolTip(self.completed_jobs_tree, "Click to Select a Job to dispatch.")
        
        button_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10")
        button_frame.pack(fill="x", side="bottom")

        if self.parent_icon_loader:
            self.dispatch_icon = self.parent_icon_loader("dispatch.png", size=(20, 20))
        else:
            self.dispatch_icon = None

        self.dispatch_job_btn = ttk.Button(
            button_frame, 
            text="Dispatch Job", 
            image=self.dispatch_icon, 
            compound=tk.LEFT,
            state="disabled",
            command=self._open_dispatch_details_window
        )
        self.dispatch_job_btn.pack(side="right")
        ToolTip(self.dispatch_job_btn, "Click to Open Dispatch Form For Selected Job.")

        
    def _create_dispatch_records_tab(self):
        """Creates the widgets for the 'Dispatch Records' tab."""
        main_frame = ttk.Frame(self.dispatch_records_tab, padding="10")
        main_frame.pack(fill="both", expand=True)

        filter_frame = ttk.LabelFrame(main_frame, text="Filter Dispatch records", padding="10")
        filter_frame.pack(fill="x", pady=(0, 10))
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)

        ttk.Label(filter_frame, text="From Date:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.from_date_entry = DateEntry(filter_frame, width=12, date_pattern='yyyy-mm-dd')
        self.from_date_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.from_date_entry.set_date(date.today() - timedelta(days=30))

        ttk.Label(filter_frame, text="To Date:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.to_date_entry = DateEntry(filter_frame, width=12, date_pattern='yyyy-mm-dd')
        self.to_date_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.to_date_entry.set_date(date.today())
        
        ttk.Label(filter_frame, text="Title Number:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.title_number_search_entry = ttk.Entry(filter_frame, width=20)
        self.title_number_search_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(filter_frame, text="Collected By:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.collected_by_search_entry = ttk.Entry(filter_frame, width=20)
        self.collected_by_search_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        
        if self.parent_icon_loader:
            self.apply_icon = self.parent_icon_loader("confirm.png", size=(16, 16))
            self.clear_icon = self.parent_icon_loader("cancel.png", size=(16, 16))
        
        apply_button = ttk.Button(
            filter_frame, 
            text="Apply Filters", 
            image=self.apply_icon, 
            compound="left",
            command=self._apply_filters
        )
        apply_button.grid(row=2, column=0, columnspan=2, pady=10, sticky="e")
        ToolTip(apply_button, "Click to Search Using Set Filters .")

        clear_button = ttk.Button(
            filter_frame, 
            text="Clear Filters", 
            image=self.clear_icon, 
            compound="left",
            command=self._clear_filters
        )
        clear_button.grid(row=2, column=2, columnspan=2, pady=10, sticky="w")
        ToolTip(clear_button, "Click to Remove Set Filters .")

        table_frame = ttk.Frame(main_frame, padding="10")
        table_frame.pack(fill="both", expand=True)
        
        columns = (
            "job_id", "dispatch_date", "title_name", "title_number", "task_type", 
            "collected_by", "collector_phone", "reason_for_dispatch"
        )
        self.dispatch_records_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.dispatch_records_tree.column("job_id", width=0, stretch=tk.NO)

        self.dispatch_records_tree.heading("dispatch_date", text="Date")
        self.dispatch_records_tree.heading("title_name", text="Title Name")
        self.dispatch_records_tree.heading("title_number", text="Title Number")
        self.dispatch_records_tree.heading("task_type", text="Task Type")
        self.dispatch_records_tree.heading("collected_by", text="Collected By")
        self.dispatch_records_tree.heading("collector_phone", text="Phone Number")
        self.dispatch_records_tree.heading("reason_for_dispatch", text="Reason for Dispatch")
        
        self.dispatch_records_tree.column("dispatch_date", width=100, anchor=tk.W)
        self.dispatch_records_tree.column("title_name", width=150, anchor=tk.W)
        self.dispatch_records_tree.column("title_number", width=120, anchor=tk.W)
        self.dispatch_records_tree.column("task_type", width=250, anchor=tk.W)
        self.dispatch_records_tree.column("collected_by", width=150, anchor=tk.W)
        self.dispatch_records_tree.column("collector_phone", width=120, anchor=tk.W)
        self.dispatch_records_tree.column("reason_for_dispatch", width=300, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.dispatch_records_tree.yview)
        self.dispatch_records_tree.configure(yscrollcommand=scrollbar.set)
        
        self.dispatch_records_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dispatch_records_tree.bind("<Double-1>", self._save_signature_file)
        ToolTip(self.dispatch_records_tree, "Double Click a Record to Download Signed Dispatch Form .")
        

        style = ttk.Style()
        style.configure("Completed.Treeview", background="green")
        style.configure("Cancelled.Treeview", background="red")
        style.configure("Default.Treeview", background="white")

    def _on_search_change(self, event):
        """Calls the filter function whenever the search entry changes."""
        search_text = self.search_entry.get().strip()
        self._filter_and_populate_table(search_text)

    def populate_completed_jobs_table(self):
        """Populates the 'Dispatch Jobs' table with completed jobs."""
        self.all_completed_jobs = self.db_manager.get_completed_jobs()
        self._filter_and_populate_table()

    def _filter_and_populate_table(self, search_text=""):
        """Filters the completed jobs and populates the table based on search criteria."""
        for item in self.completed_jobs_tree.get_children():
            self.completed_jobs_tree.delete(item)
        
        lower_search_text = search_text.lower()
        
        for job in self.all_completed_jobs:
            search_data = [
                str(job.get('job_id', '')).lower(),
                str(job.get('title_name', '')).lower(),
                str(job.get('title_number', '')).lower(),
                str(job.get('file_name', '')).lower(),
                str(job.get('client_name', '')).lower(),
                str(job.get('task_type', '')).lower()
            ]
            
            if any(lower_search_text in s for s in search_data):
                job_status = str(job.get('status', '')).upper()
                if job_status == 'COMPLETED':
                    tag = "Completed"
                elif job_status == 'CANCELLED':
                    tag = "Cancelled"
                else:
                    tag = "Default"



                values = (
                    job.get('job_id', ''),
                    job.get('timestamp', ''),
                    str(job.get('task_type', '')).upper(),
                    str(job.get('title_name', '')).upper(),
                    str(job.get('title_number', '')).upper(),
                    str(job.get('file_name', '')).upper(),
                    str(job.get('client_name', '')).upper(),
                    job_status
                )
                self.completed_jobs_tree.insert("", tk.END, values=values, tags=(tag,))
            
    def populate_dispatch_records_table(self):
        """Populates the 'Dispatch Records' table with dispatched jobs."""
        self._load_dispatch_records()
        
    def _load_dispatch_records(self, filters=None):
        """
        Loads dispatch records by calling a dedicated function in the DatabaseManager.
        """
        for item in self.dispatch_records_tree.get_children():
            self.dispatch_records_tree.delete(item)
        
        records = self.db_manager.get_dispatch_records(filters)

        if records:
            for record in records:
                values = (
                    record.get('job_id', ''),
                    record.get('dispatch_date', ''),
                    str(record.get('title_name', '')).upper(),
                    str(record.get('title_number', '')).upper(),
                    str(record.get('job_description', '')).upper(),
                    str(record.get('collected_by', '')).upper(),
                    str(record.get('collector_phone', '')).upper(),
                    str(record.get('reason_for_dispatch', '')).upper()
                )
                self.dispatch_records_tree.insert("", "end", values=values)

    def _apply_filters(self):
        """Applies filters to the dispatch records table."""
        try:
            filters = {
                'from_date': self.from_date_entry.get_date().strftime('%Y-%m-%d'),
                'to_date': self.to_date_entry.get_date().strftime('%Y-%m-%d'),
                'title_number': self.title_number_search_entry.get().strip(),
                'collected_by': self.collected_by_search_entry.get().strip()
            }
            self._load_dispatch_records(filters)
        except Exception as e:
            messagebox.showerror("Filter Error", f"An error occurred while applying filters: {e}")

    def _clear_filters(self):
        """Clears all filter entries and reloads the full table."""
        if self.from_date_entry:
            self.from_date_entry.set_date(date.today() - timedelta(days=30))
        if self.to_date_entry:
            self.to_date_entry.set_date(date.today())
        if self.title_number_search_entry:
            self.title_number_search_entry.delete(0, tk.END)
        if self.collected_by_search_entry:
            self.collected_by_search_entry.delete(0, tk.END)
        
        self._load_dispatch_records()
        
    def _save_signature_file(self, event):
        """Handles the double-click event to save the digital signature file."""
        selected_item = self.dispatch_records_tree.focus()
        if not selected_item:
            return
        
        values = self.dispatch_records_tree.item(selected_item)['values']
        job_id = values[0]
        
        try:
            result = self.db_manager.get_signature_by_job_id(job_id)
            
            if result and result.get('sign'):
                signature_data = result['sign']
                
                title_name = values[2]
                job_description = values[4]
                title_number = values[3]
                
                default_filename = f"{title_name}_{job_description}_{title_number}_signature.pdf"
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    initialfile=default_filename,
                    filetypes=[("PDF files", "*.pdf")]
                )
                
                if file_path:
                    with open(file_path, "wb") as f:
                        f.write(signature_data)
                    messagebox.showinfo("Success", "Digital signature saved successfully!")
            else:
                messagebox.showinfo("Not Found", "No digital signature file found for this record.")
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving the file: {e}")

    def _update_dispatch_button_state(self, event=None):
        """Enables/disables the dispatch button based on row selection."""
        if self.completed_jobs_tree.selection():
            self.dispatch_job_btn['state'] = 'normal'
        else:
            self.dispatch_job_btn['state'] = 'disabled'

    def _open_dispatch_details_window(self):
        """Opens the form to enter dispatch details for the selected job."""
        selected_item = self.completed_jobs_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection Error", "Please select a completed job to dispatch.")
            return
            
        job_id = self.completed_jobs_tree.item(selected_item[0])['values'][0]
        
        DispatchDetailsForm(
            self,
            self.db_manager,
            job_id,
            self.refresh_all_tables,
            self.parent_icon_loader
        )
