import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta,date

import os
import sys
from PIL import Image, ImageTk
import shutil
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Image as RLImage, Paragraph, Spacer, Table, TableStyle
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
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

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




class AddNewTaskForm(FormBase):
    """
    A form for adding a new task (job) to a specific client file.
    """
    def __init__(self, master, db_manager, client_data, user_id, refresh_callback, parent_icon_loader=None):
        # The icon_name 'add_task.png' is passed to the FormBase constructor
        super().__init__(master, 450, 340, "Add New Task", "add_task.png", parent_icon_loader)
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
        ttk.Label(main_frame, text=self.client_data['name'], font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Label(main_frame, text="File:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(main_frame, text=self.client_data['file_name'], font=('Helvetica', 10, 'bold')).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(main_frame, text="Brought By:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Label(main_frame, text=self.client_data['brought_by'], font=('Helvetica', 10, 'bold')).grid(row=2, column=1, sticky="w", pady=5)
        
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
        
        ttk.Button(main_frame, text="Submit Task", image=self.button_icon, compound=tk.LEFT, command=self._submit_task).grid(row=9, column=0, columnspan=2, pady=15)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def _submit_task(self):
        """Validates and submits the new task to the database."""
        job_description = self.job_description_entry.get().strip()
        title_name = self.title_name_entry.get().strip()
        title_number = self.title_number_entry.get().strip()
        price_str = self.price_entry.get().strip()
        amountpaid_str = '0.0'

        if not all([job_description, title_name, title_number, price_str]):
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            amountpaid_val = float(amountpaid_str)
            if amountpaid_val < 0:
                messagebox.showerror("Input Error", "Price must be a positive number.") 
                return
        except ValueError:
            messagebox.showerror("Input Error", "Price must be a valid number.")
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

        balance_val = price_val - amountpaid_val
            
        success = self.db_manager.add_job(
            file_id=self.client_data['file_id'],
            job_description=job_description,
            title_name=title_name,
            title_number=title_number,
            fee=price_val,
            added_by=added_by,
            brought_by=self.client_data['brought_by']
        )
        
        if success:
            print(f"Job added successfully with ID: {success}", file=sys.stderr)
            payment_success = self.db_manager.add_payment(
                job_id=success,
                fee=price_val,
                amount=amountpaid_val,
                balance=balance_val
            )

            if payment_success:
                messagebox.showinfo("Success", "New task and payments added successfully")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Task added, but failed to record the initial payment.")
                self.refresh_callback()
                self.destroy()
        else:
            print(f"Failed to add job. Result was: {success}", file=sys.stderr)
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
        ttk.Label(client_info_frame, text=f"Client Name: {self.client_data['name']}", font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)
        ttk.Label(client_info_frame, text=f"File Name: {self.client_data['file_name']}", font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)
        ttk.Label(client_info_frame, text=f"Brought By: {self.client_data['brought_by']}", font=('Helvetica', 12, 'bold')).pack(anchor="w", padx=10, pady=2)

        # Style and Icon for the Add Task button
        # Use the parent_icon_loader to load the icon
        if self.parent_icon_loader:
            self.button_icon = self.parent_icon_loader("add_task.png", size=(20, 20))
        else:
            self.button_icon = None

        style = ttk.Style()

        # Add New Task button
        btn = ttk.Button(top_frame, text="Add New Task", command=self._open_add_task_form, image=self.button_icon, compound=tk.LEFT)
        btn.pack(side="right", padx=10)

        # --- Separator ---
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10, padx=10)

        # --- Middle section with tasks table ---
        table_frame = ttk.Frame(self, padding="10")
        
        # New label above the table
        ttk.Label(table_frame, text=f"Job History for client: {self.client_data['name']}, file name: {self.client_data['file_name']}", font=('Helvetica', 10, 'bold')).pack(pady=5, padx=10, anchor="center")
        
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
        super().__init__(master, 950, 500, "Add Client or File", "add_client.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        
        self.selected_client_id = None # Tracks the selected client from the table
        self.all_clients = self._fetch_clients()

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
        self.client_name_var = tk.StringVar()
        self.client_combobox = ttk.Combobox(self.new_client_frame, textvariable=self.client_name_var)
        self.client_combobox.pack(fill="x", pady=(0, 10))
        self.client_combobox['values'] = self.all_clients  # Populate with initial list
        self.client_combobox.bind('<KeyRelease>', self._update_client_list)
        self.client_combobox.bind('<<ComboboxSelected>>', self._on_client_select1)

        # Telephone number
        new_telephone_label_frame = ttk.Frame(self.new_client_frame)
        new_telephone_label_frame.pack(fill="x")
        ttk.Label(new_telephone_label_frame, text="Telephone Number:").pack(side="left", fill="x", expand=True)
        self.telephone_entry = ttk.Entry(self.new_client_frame)
        self.telephone_entry.pack(fill="x", pady=(0, 10))
        
        # Email address
        new_email_label_frame = ttk.Frame(self.new_client_frame)
        new_email_label_frame.pack(fill="x")
        ttk.Label(new_email_label_frame, text="Email Address:").pack(side="left", fill="x", expand=True)
        self.email_entry = ttk.Entry(self.new_client_frame)
        self.email_entry.pack(fill="x", pady=(0, 10))

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

        columns = ("client_name", "telephone", "email")
        self.client_tree = ttk.Treeview(self.existing_client_frame, columns=columns, show="headings", height=10)
        self.client_tree.heading("client_name", text="Client Name")
        self.client_tree.heading("telephone", text="Telephone")
        self.client_tree.heading("email", text="Email")
        self.client_tree.column("client_name", width=150, anchor=tk.W)
        self.client_tree.column("telephone", width=120, anchor=tk.W)
        self.client_tree.column("email", width=180, anchor=tk.W)

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
        self.submit_btn = ttk.Button(self.main_frame, text="Submit", command=self._submit_form)
        self.submit_btn.pack(pady=20)
        
        # Initial population of the table
        self._populate_clients_table()
        

    def _fetch_clients(self):
        """Fetches all existing client names from the database."""
        try:
            # Assumes db_manager.get_all_clients() returns a list of dictionaries
            # like [{'name': 'Client A', ...}, {'name': 'Client B', ...}]
            self.all_daily_clients_survey_data = self.db_manager.get_all_daily_clients_survey()
            self.all_daily_clients_survey_data.sort(key=lambda x: x.get('name', ''))
            
            # Extract only the 'name' from each dictionary
            client_names = [client.get('name', '') for client in self.all_daily_clients_survey_data]
            
            return client_names
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch client list: {e}")
            return []
        

    def _on_client_select1(self, event):
        print("DEBUG: <<ComboboxSelected>> event triggered!")
        selected_name = self.client_name_var.get()
        print(f"DEBUG: Selected client name: {selected_name}")
        selected_client = next(
            (client for client in self.all_daily_clients_survey_data if client.get('name') == selected_name),
            None
        )
        if selected_client:
            # Clear existing data and set to readonly before filling
            self.telephone_entry.config(state='normal')
            self.email_entry.config(state='normal')
            self.brought_by_entry.config(state='normal')

            # Fill telephone
            telephone = selected_client.get('telephone_number', '')
            self.telephone_entry.delete(0, tk.END)
            self.telephone_entry.insert(0, telephone)
            print(f"Filled telephone with: {telephone}")

            # Fill email
            email = selected_client.get('email', '')
            self.email_entry.delete(0, tk.END)
            self.email_entry.insert(0, email)
            print(f"Filled email with: {email}")

            # Fill brought_by
            brought_by = selected_client.get('brought_by', '')
            self.brought_by_entry.delete(0, tk.END)
            self.brought_by_entry.insert(0, brought_by)

            # Make the fields read-only to prevent editing
            self.telephone_entry.config(state='readonly')
            self.email_entry.config(state='readonly')
            self.brought_by_entry.config(state='readonly')

    def _update_client_list(self, event=None):
        """
        Updates the Combobox dropdown based on the user's input and manages
        the state of the data entry fields.
        """
        current_text = self.client_name_var.get()
        if current_text == '':
            # If the text is empty, reset all fields to be editable for new client entry
            self.telephone_entry.config(state='normal')
            self.email_entry.config(state='normal')
            self.brought_by_entry.config(state='normal')
            self.telephone_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.brought_by_entry.delete(0, tk.END)
            self.client_combobox['values'] = self.all_clients
        else:
            # Filter the combobox values
            filtered_clients = [
                client for client in self.all_clients
                if current_text.lower() in client.lower()
            ]
            self.client_combobox['values'] = filtered_clients

    def _populate_clients_table(self):
        """Populates the client table with all clients."""
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        self.all_clients = self.db_manager.get_all_service_clients()
        for client in self.all_clients:
            self.client_tree.insert("", tk.END,
                                    values=(client['name'], client['telephone_number'], client['email']),
                                    iid=client['client_id'])

    def _filter_clients_table(self, event=None):
        """Filters the client table based on the search entry."""
        search_query = self.search_entry.get().lower()
        
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        
        filtered_clients = [c for c in self.all_clients if search_query in c['name'].lower() or search_query in c['telephone_number'].lower()]
        
        for client in filtered_clients:
            self.client_tree.insert("", tk.END, values=(client['name'], client['telephone_number']), iid=client['client_id'])

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
            name = self.client_name_var.get().strip().title()
            telephone_number = self.telephone_entry.get().strip()
            email = self.email_entry.get().strip().lower()
            brought_by = self.brought_by_entry.get().strip().title()
            file_name = self.new_client_file_name_entry.get().strip().upper()

            if not all([name, telephone_number, email, brought_by, file_name]):
                messagebox.showerror("Validation Error", "All fields are required for a new client.")
                return

            if not telephone_number.isdigit():
                messagebox.showerror("Validation Error", "Telephone number must be numeric.")
                return

            if "@" not in email or "." not in email:
                messagebox.showerror("Validation Error", "Please enter a valid email address.")
                return

            client_id = self.db_manager.add_service_client(name, telephone_number, email, brought_by, self.user_id)
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
        
        elif current_tab_id == 1: # "Add New File to Existing Client" tab
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

class UpdateStatusForm(FormBase):
    def __init__(self, master, db_manager, job_id, refresh_callback, parent_icon_loader):
        super().__init__(master, 300, 250, "Update Job Status", "update_status.png", parent_icon_loader)
        self.db_manager = db_manager
        self.job_id = job_id
        self.refresh_callback = refresh_callback
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text=f"Updating Job ID: {self.job_id}", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        ttk.Label(main_frame, text="Select New Status:").pack(pady=5)
        self.status_combobox = ttk.Combobox(main_frame, values=["Completed","Cancelled"], state="readonly")
        self.status_combobox.set("Ongoing")
        self.status_combobox.pack(pady=5)
        
        ttk.Button(main_frame, text="Confirm", command=self._update_job_status).pack(pady=20)
        
    def _update_job_status(self):
        new_status = self.status_combobox.get()
        if not new_status:
            messagebox.showerror("Error", "Please select a status.")
            return
        
        confirmation = messagebox.askyesno(
            "Irreversible Action",
            "This action is irreversible and will permanently update the job status.\n\n"
            "Do you want to proceed?"
        )
        if not confirmation:
            return
            
        success = self.db_manager.update_job_status(self.job_id, new_status)
        if success:
            messagebox.showinfo("Success", f"Job {self.job_id} status updated to '{new_status}'.")
            self.refresh_callback()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to update job status.")
            
class TrackJobsView(FormBase):
    """
    A system-wide view to track all jobs, now with real-time search.
    """
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master, 1200, 600, "Track All Jobs", "track_jobs.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self.update_icon = None # To hold reference to the button icon
        self.all_jobs_data = [] # To store the unfiltered job list
        self._create_widgets()
        self._populate_jobs_table()
        self._update_status_button_state()

    def _create_widgets(self):
        # Frame for the search bar
        search_frame = ttk.Frame(self, padding="10")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_jobs)
        
        # Frame for the table
        table_frame = ttk.Frame(self, padding="10")
        table_frame.pack(fill="both", expand=True)

        # Updated columns
        columns = ("date", "description", "title_name", "title_number", "file_name", "client_name", "status")
        self.jobs_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.jobs_tree.heading("date", text="Date")
        self.jobs_tree.heading("description", text="Description")
        self.jobs_tree.heading("title_name", text="Title Name")
        self.jobs_tree.heading("title_number", text="Title Number")
        self.jobs_tree.heading("file_name", text="File Name")
        self.jobs_tree.heading("client_name", text="Client Name")
        self.jobs_tree.heading("status", text="Status")
        
        self.jobs_tree.column("date", width=120, anchor=tk.W)
        self.jobs_tree.column("description", width=250, anchor=tk.W)
        self.jobs_tree.column("title_name", width=120, anchor=tk.W)
        self.jobs_tree.column("title_number", width=120, anchor=tk.W)
        self.jobs_tree.column("file_name", width=100, anchor=tk.W)
        self.jobs_tree.column("client_name", width=150, anchor=tk.W)
        self.jobs_tree.column("status", width=100, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.jobs_tree.bind("<<TreeviewSelect>>", self._update_status_button_state)
        
        # Frame for buttons
        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill="x", side="bottom")

        # Update Status Button
        if self.parent_icon_loader:
            self.update_icon = self.parent_icon_loader("update_status.png", size=(20, 20))

        self.update_status_btn = ttk.Button(
            button_frame, 
            text="Update Status", 
            image=self.update_icon, 
            compound=tk.LEFT,
            state="disabled",
            command=self._open_update_status_window
        )
        self.update_status_btn.pack(side="right")
    
    def _populate_jobs_table(self):
        """Populates the table with all jobs, fetched with client info."""
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        self.all_jobs_data = self.db_manager.get_all_jobs()
        
        for job in self.all_jobs_data:
            # Display all relevant data, converted to uppercase for consistency
            values = (
                job['timestamp'],
                job['job_description'].upper(),
                job['title_name'].upper(),
                job['title_number'].upper(),
                job['file_name'].upper(),
                job['client_name'].upper(),
                job['status'].upper()
            )
            # We store the job_id in the item's `iid` so we can easily retrieve it later.
            self.jobs_tree.insert("", tk.END, iid=job['job_id'], values=values)
            
    def _filter_jobs(self, event=None):
        """Filters the jobs table based on the search entry text."""
        search_text = self.search_entry.get().strip().lower()
        
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
            
        if not search_text:
            self._populate_jobs_table()
            return
            
        for job in self.all_jobs_data:
            # Search across multiple fields
            if (search_text in str(job.get('title_number', '')).lower() or
                search_text in str(job.get('client_name', '')).lower() or
                search_text in str(job.get('file_name', '')).lower() or
                search_text in str(job.get('title_name', '')).lower()):
                
                # Re-insert the filtered job
                values = (
                    job['timestamp'].upper(),
                    job['job_description'].upper(),
                    job['title_name'].upper(),
                    job['title_number'].upper(),
                    job['file_name'].upper(),
                    job['client_name'].upper(),
                    job['status'].upper()
                )
                self.jobs_tree.insert("", tk.END, iid=job['job_id'], values=values)
    
    def _update_status_button_state(self, event=None):
        """Enables/disables the update button based on row selection and status."""
        selected_item = self.jobs_tree.selection()
        if selected_item:
            # Get the status from the values of the selected row
            item_values = self.jobs_tree.item(selected_item[0], 'values')
            status = item_values[-1] # Status is the last element
            if status.lower() == 'ongoing':
                self.update_status_btn['state'] = 'normal'
            else:
                self.update_status_btn['state'] = 'disabled'
        else:
            self.update_status_btn['state'] = 'disabled'

    def _open_update_status_window(self):
        """Opens the form to update the status of the selected job."""
        selected_item = self.jobs_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection Error", "Please select a job to update its status.")
            return
            
        # Retrieve the job_id stored in the item's iid
        job_id = selected_item[0] # Corrected line
        
        # Open the new form to update the status
        UpdateStatusForm(self.master, self.db_manager, job_id, self._populate_jobs_table, self.parent_icon_loader)

class UpdatePaymentForm(FormBase):
    """
    A form for updating a specific payment's details and status.
    """

    def __init__(self, master, db_manager, payment_data, populate_callback, parent_icon_loader=None):
        """
        Initializes the form with a specific payment's data.

        Args:
            master: The parent window.
            db_manager: An instance of the DatabaseManager.
            payment_data (tuple): A tuple containing the payment record details.
            populate_callback (callable): A function to refresh the main view.
            parent_icon_loader: A function to load icons.
        """
        # FormBase already handles transient and grab_set, so we remove them here.
        super().__init__(master, 450, 370, "Update Payment", "update.png", parent_icon_loader)
        self.db_manager = db_manager
        self.payment_data = payment_data
        self.populate_callback = populate_callback
        self._create_widgets()

    def _create_widgets(self):
        """
        Creates the UI widgets for the update form.
        """
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Update Payment", font=('Helvetica', 14, 'bold')).pack(pady=(0, 15))

        # --- Client Details Section ---
        details_frame = ttk.Frame(main_frame)
        details_frame.pack(fill="x", pady=10)

        details_frame.columnconfigure(0, weight=1)
        details_frame.columnconfigure(1, weight=1)
        details_frame.columnconfigure(2, weight=1)

        ttk.Label(details_frame, text="Client Name:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w",
                                                                                            padx=(0, 5))
        ttk.Label(details_frame, text=self.payment_data[1].upper(), font=('Helvetica', 12, 'bold')).grid(row=1,
                                                                                                        column=0,
                                                                                                        sticky="w",
                                                                                                        pady=(0, 5))

        ttk.Label(details_frame, text="Description:", font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky="w",
                                                                                            padx=(15, 5))
        ttk.Label(details_frame, text=self.payment_data[3].upper(), font=('Helvetica', 12, 'bold')).grid(row=1,
                                                                                                        column=1,
                                                                                                        sticky="w",
                                                                                                        pady=(0, 5))

        ttk.Label(details_frame, text="Title Number:", font=('Helvetica', 10, 'bold')).grid(row=0, column=2, sticky="w",
                                                                                             padx=(15, 5))
        ttk.Label(details_frame, text=self.payment_data[4], font=('Helvetica', 12, 'bold')).grid(row=1, column=2,
                                                                                                sticky="w",
                                                                                                pady=(0, 5))
        # --- End Client Details Section ---

        # --- Balance & Fee Section ---
        financial_frame = ttk.Frame(main_frame)
        financial_frame.pack(fill="x", pady=10)
        financial_frame.columnconfigure(0, weight=1)
        financial_frame.columnconfigure(1, weight=1)

        # Balance (Left Side)
        ttk.Label(financial_frame, text="Balance:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w")
        balance_value = self.payment_data[7]
        self.balance_label = ttk.Label(financial_frame,
                                       text=f"KES {balance_value:,.2f}" if isinstance(balance_value, (int, float)) else balance_value,
                                       font=('Helvetica', 16, 'bold'))
        self.balance_label.grid(row=1, column=0, sticky="w", pady=(0, 5))

        # Fee (Right Side)
        ttk.Label(financial_frame, text="Fee:", font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky="e")
        fee_value = self.payment_data[5]
        self.fee_label = ttk.Label(financial_frame,
                                   text=f"KES {fee_value:,.2f}" if isinstance(fee_value, (int, float)) else fee_value,
                                   font=('Helvetica', 16, 'bold'))
        self.fee_label.grid(row=1, column=1, sticky="e", pady=(0, 5))
        
        # --- End Balance & Fee Section ---

        # --- Payment Input Section ---
        payment_input_frame = ttk.Frame(main_frame)
        payment_input_frame.pack(fill="x", pady=10)
        payment_input_frame.columnconfigure(0, weight=1)
        payment_input_frame.columnconfigure(1, weight=1)

        # Payment Amount (Left)
        ttk.Label(payment_input_frame, text="Payment Amount (KES):", font=('Helvetica', 10, 'bold')).grid(row=0,
                                                                                                         column=0,
                                                                                                         sticky="w",
                                                                                                         padx=(0, 5))
        self.entry_payment_amount = ttk.Entry(payment_input_frame)
        self.entry_payment_amount.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        # Payment Type (Right)
        ttk.Label(payment_input_frame, text="Payment Type:", font=('Helvetica', 10, 'bold')).grid(row=0, column=1,
                                                                                                  sticky="w",
                                                                                                  padx=(15, 5))
        self.payment_type_combobox = ttk.Combobox(payment_input_frame, values=["cash", "mpesa", "bank"], state="readonly")
        self.payment_type_combobox.set("cash")  # Set a default value
        self.payment_type_combobox.grid(row=1, column=1, sticky="ew", padx=(15, 0))

        # --- End Payment Input Section ---

        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        # Load and store button icons to prevent garbage collection
        if self.parent_icon_loader:
            self._submit_icon = self.parent_icon_loader("confirm.png", size=(16, 16))
            self._cancel_icon = self.parent_icon_loader("cancel.png", size=(16, 16))
        else:
            self._submit_icon = None
            self._cancel_icon = None

        submit_btn = ttk.Button(button_frame, text="Submit", image=self._submit_icon, compound=tk.LEFT,
                                command=self._submit_update_action)
        submit_btn.pack(side="left", padx=5)

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_icon, compound=tk.LEFT,
                                command=self.destroy)
        cancel_btn.pack(side="left", padx=5)

    def _submit_update_action(self):
        """
        Handles the submission of the payment update, checking for full or partial payment.
        """
        selected_type = self.payment_type_combobox.get()
        payment_amount_str = self.entry_payment_amount.get()

        if not selected_type:
            messagebox.showwarning("Invalid Selection", "Please select a payment type.")
            return

        try:
            payment_amount = float(payment_amount_str)
            if payment_amount <= 0:
                messagebox.showwarning("Invalid Amount", "Please enter a valid positive payment amount.")
                return
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid positive payment amount.")
            return
        
        try:
            current_balance = float(self.payment_data[7]) # Corrected index
            total_fee = float(self.payment_data[5])
            job_description = self.payment_data[3]
            job_title = self.payment_data[4] # Get the job description
        except (ValueError, IndexError) as e:
            messagebox.showerror("Data Error", f"Could not retrieve valid fee or balance amount: {e}")
            return
        
        # Correct calculation: total_amount_paid + current_payment
        total_paid_after_update = (total_fee - current_balance) + payment_amount

        if total_paid_after_update > total_fee:
            remaining_due = total_fee - (total_fee - current_balance)
            messagebox.showwarning(
                "Invalid Amount",
                f"Payment of KES {payment_amount:,.2f} exceeds the remaining balance of KES {remaining_due:,.2f}."
            )
            return
        new_balance = total_fee - total_paid_after_update
        
        # Determine the new status
        if abs(total_paid_after_update - total_fee) < 0.01:
            new_status = 'paid'
            final_balance = 0.0
        else:
            new_status = 'partially Paid'
            final_balance = new_balance
            
        final_payment_amount = payment_amount

        confirmation = messagebox.askyesno(
            "Confirm Action",
            f"Are you sure you want to update this payment with amount KES {final_payment_amount:,.2f} and type '{selected_type}'? This will set the status to '{new_status}'."
        )

        if confirmation:
            payment_id = self.payment_data[0]
            
            # The update_payment_record function should handle adding to the total amount paid
            if self.db_manager.update_payment_record(payment_id, new_status, final_payment_amount, selected_type):
                messagebox.showinfo("Success", "Payment updated successfully.")
                self.generate_and_save_receipt(job_description, job_title, total_fee, payment_amount, final_balance)
                self.populate_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to update payment.")

    def generate_and_save_receipt(self, service_description, service_title, fee, amount_paid, balance):
        receipt_content = f"""
    Ndiritu Mathenge Associates
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    --------------------------------------
    SERVICE:
    {service_description} for {service_title}

    FEE:
    KES {fee:,.2f}

    AMOUNT PAID:
    KES {amount_paid:,.2f}

    BALANCE:
    KES {balance:,.2f}
    --------------------------------------
    """
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Receipt As"
        )

        if file_path:
            try:
                with open(file_path, "w") as file:
                    file.write(receipt_content)
                    messagebox.showinfo("Receipt Saved", f"Receipt successfully saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save receipt: {e}")


# --- Original ManagePaymentsView with modifications ---

class ManagePaymentsView(FormBase):
    """
    Form to manage payment records, inheriting from FormBase.
    This includes viewing, adding, editing, and deleting payments.
    """
    def __init__(self, master, db_manager, populate_survey_overview, parent_icon_loader=None):
        """
        Initializes the ManagePaymentsView form.
        """
        super().__init__(master, 1200, 620, "Manage Payments", "payment.png", parent_icon_loader)
        self.db_manager = db_manager
        self.populate_survey_overview = populate_survey_overview
        self.parent_icon_loader = parent_icon_loader
        self.selected_item = None
        self.page_size = 20
        self.current_page = 1
        self.total_payments = 0
        self.total_pages = 0

        # Load icons for the buttons
        self._apply_filters_icon = None
        self._clear_filters_icon = None
        self._update_icon = None
        self._prev_icon = None
        self._next_icon = None
        self._close_icon = None
        
        self._create_widgets()
        self._fetch_and_display_payments()

    def _create_widgets(self):
        """Creates the UI widgets for the payments management form."""
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="MANAGE PAYMENTS", font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=10)

        filter_frame = ttk.LabelFrame(main_frame, text="Filter Payments", padding="10")
        filter_frame.pack(fill="x", pady=5)
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        filter_frame.columnconfigure(5, weight=1)

        # Row 0
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.status_filter_combobox = ttk.Combobox(filter_frame, values=["All", "paid", "unpaid", "partially paid"], state="readonly", width=10)
        self.status_filter_combobox.set("All")
        self.status_filter_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="From Date:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.from_date_entry = DateEntry(filter_frame, width=12, date_pattern='yyyy-mm-dd')
        self.from_date_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.from_date_entry.set_date(date.today())

        ttk.Label(filter_frame, text="To Date:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.to_date_entry = DateEntry(filter_frame, width=12, date_pattern='yyyy-mm-dd')
        self.to_date_entry.grid(row=0, column=5, padx=5, pady=2, sticky="ew")
        self.to_date_entry.set_date(date.today())

        # Row 1
        ttk.Label(filter_frame, text="Payment Mode:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.payment_mode_filter_combobox = ttk.Combobox(filter_frame, values=["", "cash", "bank", "mpesa"], state="readonly", width=10)
        self.payment_mode_filter_combobox.set("")
        self.payment_mode_filter_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="Client Name:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.client_name_search_entry = ttk.Entry(filter_frame, width=20)
        self.client_name_search_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="File Name:").grid(row=1, column=4, padx=5, pady=2, sticky="w")
        self.file_name_search_entry = ttk.Entry(filter_frame, width=20)
        self.file_name_search_entry.grid(row=1, column=5, padx=5, pady=2, sticky="ew")
        
        # New: Title Number Filter (Row 2)
        ttk.Label(filter_frame, text="Title Number:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.title_number_search_entry = ttk.Entry(filter_frame, width=20)
        self.title_number_search_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Buttons for filters (Row 3)
        if self.parent_icon_loader:
            self._apply_filters_icon = self.parent_icon_loader("filter.png", size=(20, 20))
            self._clear_filters_icon = self.parent_icon_loader("clear_filter.png", size=(20, 20))

        apply_button = ttk.Button(filter_frame, text="Apply Filters", command=self._apply_filters,
                                 image=self._apply_filters_icon, compound=tk.LEFT)
        apply_button.grid(row=3, column=0, columnspan=3, pady=10)

        clear_button = ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters,
                                 image=self._clear_filters_icon, compound=tk.LEFT)
        clear_button.grid(row=3, column=3, columnspan=3, pady=10)

        # Treeview to display payments
        columns = ("payment_id", "client_name", "file_name", "description", "title_number", "fee", "amount", "balance", "payment_date")
        self.payments_tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        # Define headings and columns
        for col in columns:
            self.payments_tree.heading(col, text=col.replace('_', ' ').title())
        
        # Hide the payment_id column as it's for internal use
        self.payments_tree.column("payment_id", width=0, stretch=tk.NO)
        self.payments_tree.column("client_name", width=120, anchor=tk.W)
        self.payments_tree.column("file_name", width=120, anchor=tk.W)
        self.payments_tree.column("description", width=250, anchor=tk.W)
        self.payments_tree.column("title_number", width=120, anchor=tk.CENTER)
        self.payments_tree.column("fee", width=80, anchor=tk.CENTER)
        self.payments_tree.column("amount", width=100, anchor=tk.CENTER)
        self.payments_tree.column("balance", width=100, anchor=tk.CENTER)
        self.payments_tree.column("payment_date", width=120, anchor=tk.CENTER)
        
        # Bind the selection event
        self.payments_tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.payments_tree.bind("<Escape>", self._deselect_all)
        self.bind("<Escape>", self._deselect_all)  # Also bind to the frame itself
        self.bind("<Button-1>", self._handle_click_to_deselect)
        
        self.payments_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollbar for the treeview
        tree_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Pagination and close buttons
        pagination_frame = ttk.Frame(main_frame, padding="5")
        pagination_frame.pack(fill="x", pady=5)

        # Action button frame
        action_frame = ttk.Frame(pagination_frame)
        action_frame.pack(side="left")

        # Update Payment button - initially disabled
        if self.parent_icon_loader:
            self._update_icon = self.parent_icon_loader("edit.png", size=(20, 20))
        self.update_button = ttk.Button(action_frame, text="Update Payment", command=self._update_payment,
                                       image=self._update_icon, compound=tk.LEFT, state=tk.DISABLED)
        self.update_button.pack(padx=5, side=tk.LEFT)
        
        # Pagination controls
        pagination_controls_frame = ttk.Frame(pagination_frame)
        pagination_controls_frame.pack(side=tk.LEFT, expand=True, padx=20)
        
        if self.parent_icon_loader:
            self._prev_icon = self.parent_icon_loader("arrow_left.png", size=(20, 20))
            self._next_icon = self.parent_icon_loader("arrow_right.png", size=(20, 20))

        self.payments_tree.bind('<Double-1>', self._on_double_click_payment)
        
        self.prev_button = ttk.Button(pagination_controls_frame, text="Previous", command=self._go_previous_page,
                                     image=self._prev_icon, compound=tk.LEFT, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.page_info_label = ttk.Label(pagination_controls_frame, text="Page 1 of 1")
        self.page_info_label.pack(side=tk.LEFT, padx=10)

        self.next_button = ttk.Button(pagination_controls_frame, text="Next", command=self._go_next_page,
                                     image=self._next_icon, compound=tk.RIGHT, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        if self.parent_icon_loader:
            self._close_icon = self.parent_icon_loader("cancel.png", size=(20, 20))
        close_btn = ttk.Button(pagination_frame, text="Close", command=self.destroy,
                               image=self._close_icon, compound=tk.LEFT)
        close_btn.pack(side="right", padx=5)

        # Generate Report button
        report_btn = ttk.Button(pagination_frame, text="Generate Report",
                                command=self._open_payment_reports)
        report_btn.pack(side="right", padx=5)
    
    def _on_double_click_payment(self, event):
        selected_items = self.payments_tree.selection()
        if selected_items:
            item = selected_items[0]
            payment_data = self.payments_tree.item(item)['values']
            payment_id = payment_data[0]

            PaymentHistoryView(
                master=self,
                db_manager=self.db_manager,
                payment_id=payment_id,
                parent_icon_loader=self.parent_icon_loader
            )

    def _open_payment_reports(self):
        """Opens the Payment Reports view."""
        PaymentReportsView(
            master=self,
            db_manager=self.db_manager,
            parent_icon_loader=self.parent_icon_loader
        )

    def _deselect_all(self, event=None):
        """Deselects all items in the client Treeview when the Escape key is pressed."""
        self.payments_tree.selection_remove(self.payments_tree.selection())

    def _handle_click_to_deselect(self, event):
        """Deselects all items in the treeview if the click was not on the treeview itself."""
        if event.widget != self.payments_tree and event.widget != self.update_button:
            self.payments_tree.selection_remove(self.payments_tree.selection())

    def _fetch_and_display_payments(self):
        """
        Fetches payments from the database based on current filters and page,
        then updates the Treeview and pagination controls.
        """
        filters = {
            'status': self.status_filter_combobox.get(),
            'payment_mode': self.payment_mode_filter_combobox.get(),
            'client_name': self.client_name_search_entry.get(),
            'file_name': self.file_name_search_entry.get(),
            'title_number': self.title_number_search_entry.get(),
            'from_date': self.from_date_entry.get_date(),
            'to_date': self.to_date_entry.get_date()
        }
        
        try:
            payments, total_count = self.db_manager.get_filtered_payments(filters, self.current_page, self.page_size)
            
            # Clear existing items
            for item in self.payments_tree.get_children():
                self.payments_tree.delete(item)

            # Fix: Access values by key from the dictionary instead of unpacking
            for payment in payments:
                # Create the display tuple
                display_values = (
                    payment.get('payment_id', ''),
                    payment.get('client_name', '').upper(),
                    payment.get('file_name', '').upper(),
                    payment.get('job_description', '').upper(),
                    payment.get('title_number', '').upper(),
                    payment.get('fee', 0.0),
                    payment.get('amount', 0.0),
                    payment.get('balance', 0.0),
                    payment.get('payment_date', '')
                )
                
                self.payments_tree.insert("", tk.END, values=display_values)

            self.total_payments = total_count
            self.total_pages = (self.total_payments + self.page_size - 1) // self.page_size
            
            # Update page info label and button states
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")
            
            self.prev_button.config(state=tk.DISABLED if self.current_page <= 1 else tk.NORMAL)
            self.next_button.config(state=tk.DISABLED if self.current_page >= self.total_pages else tk.NORMAL)
            self.update_button.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load payments: {e}")

    def _load_payments(self):
        """Initial load of payments. Calls the unified fetch method."""
        self.current_page = 1
        self._fetch_and_display_payments()

    def _apply_filters(self):
        """Applies filters. Resets to page 1 and calls the unified fetch method."""
        self.current_page = 1
        self._fetch_and_display_payments()
        
    def _clear_filters(self):
        """Clears all filter fields and reloads all payments."""
        self.status_filter_combobox.set("All")
        self.payment_mode_filter_combobox.set("")
        self.client_name_search_entry.delete(0, tk.END)
        self.file_name_search_entry.delete(0, tk.END)
        self.title_number_search_entry.delete(0, tk.END)
        self.from_date_entry.set_date(date.today())
        self.to_date_entry.set_date(date.today())
        
        self.current_page = 1
        self._fetch_and_display_payments()

    def _go_next_page(self):
        """Moves to the next page of payments."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._fetch_and_display_payments()
            
    def _go_previous_page(self):
        """Moves to the previous page of payments."""
        if self.current_page > 1:
            self.current_page -= 1
            self._fetch_and_display_payments()

    def _on_tree_select(self, event):
        """
        Handles selection of a row in the Treeview and enables/disables the update button
        based on the payment's status.
        """
        selected_items = self.payments_tree.selection()
        if selected_items:
            # Get the dictionary of values for the selected item
            item_data = self.payments_tree.item(selected_items[0])
            self.selected_item = item_data['values']

            try:
                current_balance = float(self.selected_item[7])
            except (ValueError, IndexError):
                current_balance = 0.0
            if current_balance > 0:
                self.update_button.config(state=tk.NORMAL)
                print(f"Selected payment with Title Number: {self.selected_item[4]} has a balance of KES {current_balance:,.2f}. Update button enabled.")
            else:
                self.update_button.config(state=tk.DISABLED)
                print(f"Payment with ID {self.selected_item[0]} has a zero balance. Update button disabled.")
        else:
            self.selected_item = None
            self.update_button.config(state=tk.DISABLED)
    

    def _update_payment(self):
        """Opens a new window to handle the payment update."""
        if not self.selected_item:
            messagebox.showwarning("No Selection", "Please select a payment to update.")
            return

        # Open the new UpdatePaymentForm window
        UpdatePaymentForm(
            master=self,
            db_manager=self.db_manager,
            payment_data=self.selected_item,
            populate_callback=self._fetch_and_display_payments,
            parent_icon_loader=self.parent_icon_loader
        )

class PaymentHistoryView(FormBase):
    """
    A form to display the history of micro-payments for a specific service job.
    """
    def __init__(self, master, db_manager, payment_id, parent_icon_loader=None):
        super().__init__(master, 600, 400, "Payment History", "history.png", parent_icon_loader)
        self.db_manager = db_manager
        self.payment_id = payment_id
        self.parent_icon_loader = parent_icon_loader
        self._create_widgets()
        self._fetch_and_display_history()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="PAYMENT HISTORY", font=('Helvetica', 14, 'bold')).pack(pady=10)

        # Treeview to display history
        columns = ("history_id", "Payment Amount", "Payment Type", "Payment Date")
        self.history_tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        for col in columns:
            self.history_tree.heading(col, text=col.replace('_', ' ').title())

        # Hide the history_id column
        self.history_tree.column("history_id", width=0, stretch=tk.NO)
        self.history_tree.column("Payment Amount", width=150, anchor=tk.CENTER)
        self.history_tree.column("Payment Type", width=100, anchor=tk.CENTER)
        self.history_tree.column("Payment Date", width=180, anchor=tk.CENTER)
        
        self.history_tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Close Button
        if self.parent_icon_loader:
            self._close_icon = self.parent_icon_loader("cancel.png", size=(20, 20))
        close_btn = ttk.Button(self, text="Close", command=self.destroy,
                               image=self._close_icon, compound=tk.LEFT)
        close_btn.pack(pady=5)

    def _fetch_and_display_history(self):
        """Fetches and displays payment history from the database."""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            history_records = self.db_manager.get_payment_history(self.payment_id)

            # Fix: Check if history_records is a list of dictionaries before proceeding
            if history_records and isinstance(history_records[0], dict):
                for record in history_records:
                    # Access values using dictionary keys instead of a for-loop
                    display_values = (
                        record.get('history_id', ''),
                        f"{record.get('payment_amount', 0.0):,.2f}", # Format as currency
                        record.get('payment_type', '').upper(),
                        str(record.get('payment_date', '')).upper()
                    )
                    self.history_tree.insert("", tk.END, values=display_values)
            else:
                # Fallback for old tuple-based return type
                for record in history_records:
                    processed_values = []
                    for i, value in enumerate(record):
                        if i == 0:
                            processed_values.append(str(value))
                        elif i == 1:
                            processed_values.append(f"{float(value):,.2f}")
                        elif isinstance(value, str):
                            processed_values.append(value.upper())
                        elif value is not None:
                            processed_values.append(str(value).upper())
                        else:
                            processed_values.append("")
                    self.history_tree.insert("", tk.END, values=processed_values)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load payment history: {e}")



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
            """Generates PDF report using ReportLab (with logo, word wrap, footer) 
            and prompts user to choose where to save it."""
            if not _REPORTLAB_AVAILABLE:
                return None

            from datetime import datetime  # ensure correct import

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

            # --- Default starting folder: Documents (fallback to Desktop if missing) ---
            default_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.exists(default_dir):
                default_dir = os.path.join(os.path.expanduser("~"), "Desktop")

            file_path = filedialog.asksaveasfilename(
                title="Save Report As",
                defaultextension=".pdf",
                initialfile=file_name,
                initialdir=default_dir,
                filetypes=[("PDF files", "*.pdf")]
            )

            if not file_path:  # user cancelled
                return None

            try:
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                styles = getSampleStyleSheet()
                story = []

                # --- Business Header with Logo ---
                logo_path = os.path.join(ICONS_DIR, "survey.png")

                if os.path.exists(logo_path):
                    logo = RLImage(logo_path)
                    logo._restrictSize(1.2 * inch, 1.2 * inch)
                else:
                    logo = Paragraph("", styles['Normal'])

                header_table = Table([
                    [logo, "NDIRITU MATHENGE & ASSOCIATES", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                ], colWidths=[1.2 * inch, 3.5 * inch, 2 * inch])

                header_table.setStyle(TableStyle([
                    ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (1, 0), (1, 0), 14),
                    ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ]))
                story.append(header_table)
                story.append(Spacer(1, 12))

                # --- Report Title & Period ---
                story.append(Paragraph(f"<b>{report_name.upper()}</b>", styles['Heading2']))
                story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
                story.append(Spacer(1, 12))

                # --- Table Content ---
                if content.get('data'):
                    headers = [
                        "Job ID", "Payment ID", "Title Name", "Title Number", "Description",
                        "Created", "Payment Date", "Job Status", "Payment Status", "Job Fee",
                        "Amount Paid", "Balance",
                    ]

                    # wrapping styles
                    wrap_style_header = ParagraphStyle('wrap_header', fontSize=8, leading=10, alignment=1)  # centered
                    wrap_style_body = ParagraphStyle('wrap_body', fontSize=7, leading=9, alignment=0)      # left

                    # wrap headers
                    table_data = [[Paragraph(h, wrap_style_header) for h in headers]]

                    # helper for safe date conversion
                    def fmt_date(val):
                        if not val:
                            return ""
                        if isinstance(val, datetime):
                            return val.strftime("%Y-%m-%d")
                        return str(val).split(" ")[0]

                    for job in content['data']:
                        created_val = fmt_date(job.get('job_created'))
                        payment_date_val = fmt_date(job.get('payment_date'))

                        row = [
                            Paragraph(str(job.get('job_id', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('payment_id', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('title_name', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('title_number', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('job_description', '') or ""), wrap_style_body),
                            Paragraph(created_val, wrap_style_body),
                            Paragraph(payment_date_val, wrap_style_body),
                            Paragraph(str(job.get('job_status', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('payment_status', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('job_fee', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('amount_paid', '') or ""), wrap_style_body),
                            Paragraph(str(job.get('balance', '') or ""), wrap_style_body),
                        ]
                        table_data.append(row)

                    t = Table(table_data, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),

                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 7),
                        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),

                        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
                        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),

                        ('LEFTPADDING', (0, 0), (-1, -1), 3),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ]))

                    story.append(t)
                else:
                    story.append(Paragraph("No jobs found for this period and status.", styles['Normal']))

                # --- Footer with Page Number ---
                def add_page_number(canvas, doc):
                    page_num = canvas.getPageNumber()
                    canvas.setFont("Helvetica", 8)
                    canvas.drawRightString(7.5 * inch, 0.5 * inch, f"Page {page_num}")

                doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
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
            
                        
class PaymentReportsView(FormBase):
    """
    A system-wide view for generating service payment reports, including gross and net sales.
    """

    def __init__(self, master, db_manager, parent_icon_loader=None):
        super().__init__(master, 750, 500, "Payment Reports", "survey_reports.png", parent_icon_loader)
        self.db_manager = db_manager
        self.parent_icon_loader_ref = parent_icon_loader

        self.report_type_var = tk.StringVar(self, value="daily")
        self.from_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))
        self.to_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))

        self._create_widgets()
        self._toggle_date_entries()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Generate Payment Reports", font=('Helvetica', 14, 'bold')).pack(pady=10)

        # Report options
        options_frame = ttk.LabelFrame(main_frame, text="Report Options", padding="10")
        options_frame.pack(fill="x", pady=10)

        ttk.Label(options_frame, text="Report Period:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        for idx, (label, value) in enumerate([("Daily", "daily"), ("Monthly", "monthly"),
                                               ("Custom", "custom")]):
            ttk.Radiobutton(options_frame, text=label, variable=self.report_type_var,
                            value=value, command=self._toggle_date_entries).grid(row=0, column=idx+1, padx=2, pady=5)

        # Date range inputs
        date_frame = ttk.Frame(options_frame)
        date_frame.grid(row=1, column=0, columnspan=5, pady=5, sticky="ew")

        ttk.Label(date_frame, text="From Date:").pack(side="left", padx=5)
        self.from_entry = ttk.Entry(date_frame, textvariable=self.from_date_var, width=12)
        self.from_entry.pack(side="left", padx=2)

        ttk.Label(date_frame, text="To Date:").pack(side="left", padx=5)
        self.to_entry = ttk.Entry(date_frame, textvariable=self.to_date_var, width=12)
        self.to_entry.pack(side="left", padx=2)

        generate_btn = ttk.Button(main_frame, text="Generate Report", command=self._generate_report)
        generate_btn.pack(pady=10)

                # Export Button
        export_btn = ttk.Button(main_frame, text="Export to PDF", command=self._export_to_pdf)
        export_btn.pack(pady=5)


        # Table
        self.tree = ttk.Treeview(main_frame, columns=("date", "gross", "net"), show="headings")
        self.tree.heading("date", text="Date")
        self.tree.heading("gross", text="Gross Sales")
        self.tree.heading("net", text="Net Sales")

        self.tree.column("date", width=120, anchor=tk.W)
        self.tree.column("gross", width=150, anchor=tk.CENTER)
        self.tree.column("net", width=150, anchor=tk.CENTER)

        self.tree.pack(fill="both", expand=True, pady=10)

    def _export_to_pdf(self):
        """Exports the payment report to a PDF file."""
        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "ReportLab is not installed. Cannot export PDF.")
            return

        # Ask user where to save
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Payment Report As"
        )
        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Title
            elements.append(Paragraph("Payment Sales Report", styles['Title']))
            elements.append(Spacer(1, 12))

            # Period info
            period_text = f"Report Type: {self.report_type_var.get().capitalize()}"
            if self.report_type_var.get() == "custom":
                period_text += f" (From {self.from_date_var.get()} To {self.to_date_var.get()})"
            elements.append(Paragraph(period_text, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Table data
            data = [["Date", "Gross Sales", "Net Sales"]]
            for item in self.tree.get_children():
                row = self.tree.item(item)['values']
                data.append([
                    str(row[0]),
                    str(row[1]),
                    str(row[2])
                ])

            table = Table(data, colWidths=[120, 150, 150])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)

            # Build PDF
            doc.build(elements)
            messagebox.showinfo("Success", f"Report exported successfully:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export report: {e}")


    def _toggle_date_entries(self):
        state = "normal" if self.report_type_var.get() == "custom" else "disabled"
        self.from_entry.config(state=state)
        self.to_entry.config(state=state)

    def _generate_report(self):
        period = self.report_type_var.get()
        start_date = self.from_date_var.get()
        end_date = self.to_date_var.get()

        try:
            results = self.db_manager.get_service_sales_summary(period, start_date, end_date)

            for item in self.tree.get_children():
                self.tree.delete(item)

            for row in results:
                self.tree.insert("", tk.END, values=(
                    row.get("date", ""),
                    f"KES {row.get('total_gross', 0):,.2f}",
                    f"KES {row.get('total_net', 0):,.2f}"
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

