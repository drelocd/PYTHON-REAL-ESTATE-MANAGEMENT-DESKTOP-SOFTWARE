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
        
        ttk.Button(main_frame, text="Submit Task", image=self.button_icon, compound=tk.LEFT, command=self._submit_task).grid(row=8, column=0, columnspan=2, pady=15)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def _submit_task(self):
        """Validates and submits the new task to the database."""
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
            
        success = self.db_manager.add_job(
            file_id=self.client_data['file_id'],
            job_description=job_description,
            title_name=title_name,
            title_number=title_number,
            fee=price_val,
            amount_paid=price_val,
            added_by=added_by,
            brought_by=self.client_data['brought_by']
        )
        
        if success:
            messagebox.showinfo("Success", "New task added successfully.")
            self.refresh_callback()
            self.destroy()
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
        style.configure("Red.TButton", background="red", foreground="black")

        # Add New Task button
        btn = ttk.Button(top_frame, text="Add New Task", command=self._open_add_task_form, image=self.button_icon, compound=tk.LEFT, style="Red.TButton")
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
        super().__init__(master, 750, 500, "Add Client or File", "add_client.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        
        self.selected_client_id = None # Tracks the selected client from the table

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
        
        filtered_clients = [c for c in self.all_clients if search_query in c['name'].lower() or search_query in c['contact'].lower()]
        
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
        
        if current_tab_id == 0: # "Add New Client" tab
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
