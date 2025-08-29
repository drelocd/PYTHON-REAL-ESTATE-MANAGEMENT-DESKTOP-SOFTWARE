import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import shutil
import io
from PIL import Image, ImageTk

# Assuming database.py is in the same directory or accessible via PYTHONPATH
# The DatabaseManager class is now fully functional
from database import DatabaseManager

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')



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
        ttk.Label(data_frame, text=self.job_details.get('client_name', 'N/A',font=('Helvetica', 10, 'bold'))).pack(side="left", padx=10)
        ttk.Label(data_frame, text=self.job_details.get('job_description', 'N/A',font=('Helvetica', 10, 'bold'))).pack(side="left", padx=10, expand=True)
        ttk.Label(data_frame, text=self.job_details.get('title_number', 'N/A',font=('Helvetica', 10, 'bold'))).pack(side="right", padx=10)
        
        # --- Form input fields ---
        
        # Reason for Dispatch
        ttk.Label(main_frame, text="Reason for Dispatch:").pack(anchor="w")
        self.reason_entry = ttk.Entry(main_frame, width=50)
        self.reason_entry.pack(fill="x", pady=(0, 10))

        # Collected By
        ttk.Label(main_frame, text="Collected By:").pack(anchor="w")
        self.collected_by_entry = ttk.Entry(main_frame, width=50)
        self.collected_by_entry.pack(fill="x", pady=(0, 10))

        # Collector Phone Number
        ttk.Label(main_frame, text="Collector Phone Number:").pack(anchor="w")
        self.phone_entry = ttk.Entry(main_frame, width=50)
        self.phone_entry.pack(fill="x", pady=(0, 10))
        
        # Signature File Upload Section
        file_frame = ttk.LabelFrame(main_frame, text="Digital Signature (PDF)", padding=10)
        file_frame.pack(fill="x", pady=10)
        
        self.file_list_label = ttk.Label(file_frame, text="No files selected.")
        self.file_list_label.pack(side="left", padx=5)
        
        upload_icon = self.parent_icon_loader("upload.png", size=(16, 16))
        self.upload_btn = ttk.Button(file_frame, text="Select Files", image=upload_icon, compound="left", command=self._select_files)
        self.upload_btn.pack(side="right", padx=5)
        
        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        submit_icon = self.parent_icon_loader("check.png", size=(16, 16))
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
            self.file_list_label.config(text=f"Selected: {file_names_text}")
        else:
            self.file_list_label.config(text="No files selected.")
        
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
        # The user_id parameter has been added here to match the calling function.
        super().__init__(master, 1200, 600, "Job Dispatch & Records", "dispatch.png", parent_icon_loader)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id  # Store the user ID
        self.parent_icon_loader = parent_icon_loader
        self.update_icon = None
        
        self._create_widgets()
        self.populate_completed_jobs_table()
        self.populate_dispatch_records_table()
        self._update_dispatch_button_state()
        
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
        """Creates the widgets for the 'Dispatch Jobs' tab."""
        # Frame for the search bar
        search_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10 5")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        # Frame for the table
        table_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10")
        table_frame.pack(fill="both", expand=True)

        # Columns for the table
        columns = ("job_id", "date", "description", "title_name", "title_number", "file_name", "client_name", "status")
        self.completed_jobs_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.completed_jobs_tree.heading("job_id", text="Job ID")
        self.completed_jobs_tree.heading("date", text="Date")
        self.completed_jobs_tree.heading("description", text="Description")
        self.completed_jobs_tree.heading("title_name", text="Title Name")
        self.completed_jobs_tree.heading("title_number", text="Title Number")
        self.completed_jobs_tree.heading("file_name", text="File Name")
        self.completed_jobs_tree.heading("client_name", text="Client Name")
        self.completed_jobs_tree.heading("status", text="Status")
        
        self.completed_jobs_tree.column("job_id", width=60, anchor=tk.CENTER)
        self.completed_jobs_tree.column("date", width=120, anchor=tk.W)
        self.completed_jobs_tree.column("description", width=250, anchor=tk.W)
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
        
        # Frame for buttons
        button_frame = ttk.Frame(self.dispatch_jobs_tab, padding="10")
        button_frame.pack(fill="x", side="bottom")

        # Dispatch Job Button
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
        
    def _create_dispatch_records_tab(self):
        """Creates the widgets for the 'Dispatch Records' tab."""
        # Frame for the table
        table_frame = ttk.Frame(self.dispatch_records_tab, padding="10")
        table_frame.pack(fill="both", expand=True)

        # Columns for the table
        columns = ("dispatch_id", "job_id", "date", "collected_by", "phone", "reason")
        self.dispatch_records_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.dispatch_records_tree.heading("dispatch_id", text="Dispatch ID")
        self.dispatch_records_tree.heading("job_id", text="Job ID")
        self.dispatch_records_tree.heading("date", text="Date")
        self.dispatch_records_tree.heading("collected_by", text="Collected By")
        self.dispatch_records_tree.heading("phone", text="Phone Number")
        self.dispatch_records_tree.heading("reason", text="Reason for Dispatch")
        
        self.dispatch_records_tree.column("dispatch_id", width=80, anchor=tk.CENTER)
        self.dispatch_records_tree.column("job_id", width=60, anchor=tk.CENTER)
        self.dispatch_records_tree.column("date", width=120, anchor=tk.W)
        self.dispatch_records_tree.column("collected_by", width=150, anchor=tk.W)
        self.dispatch_records_tree.column("phone", width=120, anchor=tk.W)
        self.dispatch_records_tree.column("reason", width=300, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.dispatch_records_tree.yview)
        self.dispatch_records_tree.configure(yscrollcommand=scrollbar.set)
        
        self.dispatch_records_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_search_change(self, event):
        """Calls the filter function whenever the search entry changes."""
        search_text = self.search_entry.get().strip()
        self._filter_and_populate_table(search_text)

    def populate_completed_jobs_table(self):
        """Populates the 'Dispatch Jobs' table with completed jobs."""
        # Fetch the full list of completed jobs once
        self.all_completed_jobs = self.db_manager.get_completed_jobs()
        self._filter_and_populate_table()

    def _filter_and_populate_table(self, search_text=""):
        """Filters the completed jobs and populates the table based on search criteria."""
        # Clear existing items
        for item in self.completed_jobs_tree.get_children():
            self.completed_jobs_tree.delete(item)
        
        lower_search_text = search_text.lower()
        
        for job in self.all_completed_jobs:
            # Check if any of the relevant fields contain the search text
            search_data = [
                str(job['job_id']).lower(),
                str(job['title_name']).lower(),
                str(job['title_number']).lower(),
                str(job['file_name']).lower(),
                str(job['client_name']).lower(),
                str(job['job_description']).lower()
            ]
            
            if any(lower_search_text in s for s in search_data):
                values = (
                    job['job_id'],
                    job['timestamp'],
                    job['job_description'],
                    job['title_name'],
                    job['title_number'],
                    job['file_name'],
                    job['client_name'],
                    job['status']
                )
                self.completed_jobs_tree.insert("", tk.END, values=values)
            
    def populate_dispatch_records_table(self):
        """Populates the 'Dispatch Records' table with dispatched jobs."""
        for item in self.dispatch_records_tree.get_children():
            self.dispatch_records_tree.delete(item)
            
        dispatched_jobs = self.db_manager.get_dispatched_jobs()
        
        for record in dispatched_jobs:
            values = (
                record['dispatch_id'],
                record['job_id'],
                record['dispatch_date'],
                record['collected_by'],
                record['collector_phone'],
                record['reason_for_dispatch']
            )
            self.dispatch_records_tree.insert("", tk.END, values=values)

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
            
        # Get the job_id from the first column of the selected row
        job_id = self.completed_jobs_tree.item(selected_item[0])['values'][0]
        
        # Open the new form
        DispatchDetailsForm(
            self,
            self.db_manager,
            job_id,
            self.populate_completed_jobs_table, # This callback will refresh the main list
            self.parent_icon_loader
        )