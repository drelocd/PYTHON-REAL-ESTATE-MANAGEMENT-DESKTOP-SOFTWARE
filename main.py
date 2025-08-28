import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime
from datetime import datetime, timedelta
import menubar
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests  # Used for making HTTP requests to download files
import json  # Used for parsing JSON responses from GitHub API
import threading  # Used to run update checks and downloads in the background
import webbrowser  # Used for opening download links (as a fallback)
import sys  # Used to get the executable path
import logging  # For structured logging
# from packaging.version import parse as parse_version # REMOVED: Causing import issues

# Import your DatabaseManager
from database import DatabaseManager
from forms.transfer_form import PropertyTransferForm  # Import the transfer form
from forms.main_menu_form import MainMenuForm
from forms.admin_manage_users_form import AdminManageUsersPanel  # Import the admin panel for user management
# NEW IMPORTS from your file
from forms.property_forms import AddPropertyForm, SellPropertyLandingForm, TrackPaymentsForm, SoldPropertiesView, \
    ViewAllPropertiesForm, EditPropertyForm, SalesReportsForm
from forms.survey_forms import ClientFileDashboard, AddClientAndFileForm, TrackJobsView, ManagePaymentsView,JobReportsView
from forms.signup_form import SignupForm
from forms.dashboard_form import DashboardForm
from forms.client_form import ClientForm
from forms.system_settings_form import SystemSettingsForm  # NEW
from forms.activity_log_viewer_form import ActivityLogViewerForm
from forms.subdivide_lands_form import subdividelandForm  # NEW: Import the subdivide land form
# Assuming this is the correct import for ViewPropertiesToTransferForm
#from forms.view_properties_to_transfer_form import ViewPropertiesToTransferForm


db_manager = DatabaseManager()
print("\n--- Checking/Adding Default Users ---")

# Add 'admin' user if they don't exist
# We use db_manager.authenticate_user to check for existence and valid password (for a robust check)
# If authenticate_user returns None, the user doesn't exist or password is wrong, so we can try adding them.
admin_username = "admin"
admin_password = "admin"  # This will be hashed by add_user
admin_is_agent = "no"  # This is a flag to indicate the user is an admin

if not db_manager.authenticate_user(admin_username, admin_password):
    print(f"'{admin_username}' user not found or password incorrect. Attempting to add...")
    admin_id = db_manager.add_user(admin_username, admin_password, admin_is_agent, "admin")
    if admin_id:
        print(f"Admin user '{admin_username}' added successfully with ID: {admin_id}")
    else:
        print(f"Failed to add admin user '{admin_username}'. It might already exist with a different password.")
else:
    print(f"Admin user '{admin_username}' already exists.")

# Add 'property_manager' user if they don't exist
pm_username = "pm"
pm_password = "pm"
pm_is_agent = "no"  # This is a flag to indicate the user is a property manager
if not db_manager.authenticate_user(pm_username, pm_password):
    print(f"'{pm_username}' user not found or password incorrect. Attempting to add...")
    pm_id = db_manager.add_user(pm_username, pm_password, pm_is_agent, "property_manager")
    if pm_id:
        print(f"Property Manager user '{pm_username}' added successfully with ID: {pm_id}")
    else:
        print(f"Failed to add property manager user '{pm_username}'. It might already exist with a different password.")
else:
    print(f"Property Manager user '{pm_username}' already exists.")

# Add 'sales_agent' user if they don't exist
sa_username = "sa"
sa_password = "sa"
sa_is_agent = "no"  # This is a flag to indicate the user is a sales agent
if not db_manager.authenticate_user(sa_username, sa_password):
    print(f"'{sa_username}' user not found or password incorrect. Attempting to add...")
    sa_id = db_manager.add_user(sa_username, sa_password, sa_is_agent, "sales_agent")
    if sa_id:
        print(f"Sales Agent user '{sa_username}' added successfully with ID: {sa_id}")
    else:
        print(f"Failed to add sales agent user '{sa_username}'. It might already exist with a different password.")
else:
    print(f"Sales Agent user '{sa_username}' already exists.")

# Add 'accountant' user if they don't exist
acc_username = "acc"
acc_password = "acc"
acc_is_agent = "no"  # This is a flag to indicate the user is an accountant
if not db_manager.authenticate_user(acc_username, acc_password):
    print(f"'{acc_username}' user not found or password incorrect. Attempting to add...")
    acc_id = db_manager.add_user(acc_username, acc_password, acc_is_agent, "accountant")
    if acc_id:
        print(f"Accountant user '{acc_username}' added successfully with ID: {acc_id}")
    else:
        print(f"Failed to add accountant user '{acc_username}'. It might already exist with a different password.")
else:
    print(f"Accountant user '{acc_username}' already exists.")

print("--- Default User Setup Complete ---")

# --- Global Constants ---
# Define the current application version
APP_VERSION = "1.0.1"  # IMPORTANT: Increment this version number for new releases!

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROPERTY_IMAGES_DIR = os.path.join(DATA_DIR, 'images')
TITLE_DEEDS_DIR = os.path.join(DATA_DIR, 'deeds')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
SURVEY_ATTACHMENTS_DIR = os.path.join(DATA_DIR, 'survey_attachments')

# Ensure necessary directories exist
for d in [PROPERTY_IMAGES_DIR, TITLE_DEEDS_DIR, RECEIPTS_DIR, SURVEY_ATTACHMENTS_DIR]:
    os.makedirs(d, exist_ok=True)


# --- End Global Constants ---

# --- Section View Classes ---

class SalesSectionView(ttk.Frame):
    def __init__(self, master, db_manager, load_icon_callback, user_id, user_type):
        super().__init__(master, padding="10 10 10 10")
        self.db_manager = db_manager
        self.load_icon_callback = load_icon_callback  # Callback to main app's _load_icon
        self.user_id = user_id
        self.user_type = user_type  # Store user type here

        # Initialize a list to hold references to PhotoImage objects for SalesSection buttons
        self.sales_button_icons = []

        self._create_widgets()
        self.populate_system_overview()

    def _create_widgets(self):
        button_grid_container = ttk.Frame(self, padding="20")
        button_grid_container.pack(pady=20, padx=20, fill="x", anchor="n")

        # Configure grid columns to expand equally
        for i in range(3):
            button_grid_container.grid_columnconfigure(i, weight=1, uniform="sales_button_cols")
        # Configure grid rows to expand equally
        for i in range(3):
            button_grid_container.grid_rowconfigure(i, weight=1, uniform="sales_button_rows")

        buttons_data = [
            {"text": "Add New Property", "icon": "add_property.png", "command": self._open_add_property_form,
             "roles": ['admin', 'property_manager']},
            {"text": "Sell Property", "icon": "manage_sales.png", "command": self._open_sell_property_form,
             "roles": ['admin', 'property_manager', 'sales_agent']},
            {"text": "Track Payments", "icon": "track_payments.png", "command": self._open_track_payments_view,
             "roles": ['admin', 'sales_agent', 'accountant']},
            {"text": "Sold Properties", "icon": "sold_properties.png", "command": self._open_sold_properties_view,
             "roles": ['admin', 'property_manager', 'sales_agent', 'accountant']},
            {"text": "View All Properties", "icon": "view_all_properties.png",
             "command": self._open_view_all_properties, "roles": ['admin', 'property_manager', 'sales_agent']},
            {"text": "Reports & Receipts", "icon": "reports_receipts.png",
             "command": self._open_sales_reports_receipts_view,
             "roles": ['admin', 'property_manager', 'sales_agent', 'accountant']},
            {"text": "Transfer Property", "icon": "transfer.png", "command": self._open_property_transfer_form,
             "roles": ['admin', 'property_manager']},
            {"text": "View Properties To Transfer", "icon": "view_transfer_properties.png",
             "command": self._open_view_property_to_transfer_form,
             "roles": ['admin', 'property_manager']},
            {"text": "Land Division & Records", "icon": "subdivide.png", "command": self._open_land_division_form,
             "roles": ['admin', 'property_manager']}
        ]

        row, col = 0, 0
        for data in buttons_data:
            state = 'normal' if self.user_type in data["roles"] else 'disabled'
            # Check if button should be created at all to avoid empty slots for strict roles
            # For simplicity and to maintain grid, we will create and disable.

            icon_img = self.load_icon_callback(data["icon"])
            self.sales_button_icons.append(icon_img)  # Store reference to prevent garbage collection

            btn_wrapper_frame = ttk.Frame(button_grid_container, relief="raised", borderwidth=1,
                                          cursor="hand2" if state == 'normal' else "")
            btn_wrapper_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            btn = ttk.Button(
                btn_wrapper_frame,
                text=data["text"],
                image=icon_img,
                compound=tk.TOP,
                command=data["command"],
                state=state  # Apply the state here
            )
            btn.pack(expand=True, fill="both", ipadx=20, ipady=20)
            btn.image = icon_img  # Store reference on the button itself

            col += 1
            if col > 2:
                col = 0
                row += 1

        

    def populate_system_overview(self):
        """
        Fetches data from the database and updates the System Overview dashboard
        with key metrics and charts for sales.
        """
        print("Refreshing UI...")
        

    # --- Methods called by buttons within SalesSection ---
    def _open_add_property_form(self):
        AddPropertyForm(self.master, self.db_manager, self.populate_system_overview,
                        user_id=self.user_id,
                        parent_icon_loader=self.load_icon_callback, window_icon_name="add_property.png")

    def _open_sell_property_form(self):
        SellPropertyLandingForm(self.master, self.db_manager, self.populate_system_overview,
                                parent_icon_loader=self.load_icon_callback, window_icon_name="manage_sales.png")

    def _open_track_payments_view(self):
        TrackPaymentsForm(self.master, self.db_manager, self.populate_system_overview,
                          parent_icon_loader=self.load_icon_callback, window_icon_name="track_payments.png")

    def _open_sold_properties_view(self):
        SoldPropertiesView(self.master, self.db_manager, self.populate_system_overview,
                           parent_icon_loader=self.load_icon_callback, window_icon_name="sold_properties.png")

    def _open_view_all_properties(self):
        # NEW: Open the ViewAllPropertiesForm
        ViewAllPropertiesForm(self.master, self.db_manager, self.populate_system_overview,
                              parent_icon_loader=self.load_icon_callback, window_icon_name="view_all_properties.png")

    def _open_sales_reports_receipts_view(self):
        SalesReportsForm(self.master, self.db_manager, parent_icon_loader=self.load_icon_callback,
                         window_icon_name="reports.png")

    # NEW METHOD to open the PropertyTransferForm
    def _open_property_transfer_form(self):
        PropertyTransferForm(
            self.master,
            self.db_manager,
            self.populate_system_overview,
            user_id=self.user_id,
            # No dummy_property_data is passed now
            parent_icon_loader=self.load_icon_callback,
            window_icon_name="transfer.png"
        )

    def _open_view_property_to_transfer_form(self):
        ViewPropertiesToTransferForm(
            self.master,
            self.db_manager,
            self.populate_system_overview,
            user_id=self.user_id,
            # No dummy_property_data is passed now
            parent_icon_loader=self.load_icon_callback,
            window_icon_name="transfer.png"
        )

    def _open_land_division_form(self):
        subdividelandForm(
            master=self.master,
            db_manager=self.db_manager,
            user_id=self.user_id,
            refresh_callback=self.populate_system_overview,
            parent_icon_loader=self.load_icon_callback,
            window_icon_name="subdivide.png"
        )

    def generate_report_type(self, action):
        # self.notebook.select(self.sales_section)
        if action == "Daily/Monthly Sales":
            self._open_sales_reports_receipts_view()  # Corrected from self.sales_section
        elif action == "Sold Properties":
            self._open_sales_reports_receipts_view()  # Corrected from self.sales_section
        elif action == "Pending Instalments":
            self._open_sales_reports_receipts_view()


class SurveySectionView(ttk.Frame):
    """
    The main view for the 'Survey Section' tab, providing a central hub
    for client search/creation and access to all related functionalities.
    """
    def __init__(self, master, db_manager, load_icon_callback, user_id, user_type):
        super().__init__(master, padding="10 10 10 10")
        self.db_manager = db_manager
        self.load_icon_callback = load_icon_callback
        self.user_id = user_id
        self.user_type = user_type
        self.button_icons = []
        self._create_widgets()
        self.populate_survey_overview()

    def _create_widgets(self):
        """Creates the grid of buttons for the main dashboard."""
        
        # --- Top Section: Client Search and Creation ---
        client_frame = ttk.Frame(self)
        client_frame.pack(pady=20, padx=20, fill="x")

        ttk.Label(client_frame, text="Search for a Client:").pack(side="left", padx=(0, 10))
        self.client_search_entry = ttk.Entry(client_frame)
        self.client_search_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.client_search_entry.bind("<KeyRelease>", self._filter_clients)
        
        # This button will now open the unified form
        style = ttk.Style()
        # Configure a new style named "Red.TButton"
        style.configure("Red.TButton", background="green", foreground="black")
        ttk.Button(client_frame, text="Add Client/File", command=self._open_add_client_and_file_form, style="Red.TButton").pack(side="left", padx=(10, 0))

        # Client Table
        client_table_frame = ttk.Frame(self)
        client_table_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        columns = ("client_name", "file_name", "contact")
        self.client_tree = ttk.Treeview(client_table_frame, columns=columns, show="headings")
        self.client_tree.heading("client_name", text="Client Name")
        self.client_tree.heading("file_name", text="File Name")
        self.client_tree.heading("contact", text="Contact Info")

        self.client_tree.column("client_name", width=150, anchor=tk.W)
        self.client_tree.column("file_name", width=100, anchor=tk.W)
        self.client_tree.column("contact", width=100, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(client_table_frame, orient=tk.VERTICAL, command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=scrollbar.set)
        
        self.client_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.client_tree.bind("<Double-1>", self._open_client_file_dashboard)
        self.client_tree.bind("<Return>", self._open_client_file_dashboard)

        # Bind the Escape key to deselect all items in the treeview
        self.client_tree.bind("<Escape>", self._deselect_all)
        self.bind("<Escape>", self._deselect_all)  # Also bind to the frame itself
        self.bind("<Button-1>", self._handle_click_to_deselect)



        # --- Middle Section: Main Action Buttons ---
        button_grid_container = ttk.Frame(self, padding="20")
        button_grid_container.pack(pady=20, padx=20, fill="x", anchor="n")

        for i in range(2):
            button_grid_container.grid_columnconfigure(i, weight=1, uniform="button_cols")
        for i in range(2):
            button_grid_container.grid_rowconfigure(i, weight=1, uniform="button_rows")

        buttons_data = [
            {"text": "Track Jobs", "icon": "track_jobs.png", "command": self._open_track_jobs_view,
             "roles": ['admin', 'field_worker']},
            {"text": "Manage Payments", "icon": "manage_payments.png",
             "command": self._open_manage_payments_view, "roles": ['admin', 'accountant']},
            {"text": "Job Reports", "icon": "survey_reports.png", "command": self._open_job_reports_view,
             "roles": ['admin', 'accountant']},
        ]

        row, col = 0, 0
        for data in buttons_data:
            state = 'normal' if self.user_type in data["roles"] else 'disabled'

            icon_img = self.load_icon_callback(data["icon"], size=(64, 64))
            self.button_icons.append(icon_img)

            btn_wrapper_frame = ttk.Frame(button_grid_container, relief="raised", borderwidth=1,
                                          cursor="hand2" if state == 'normal' else "")
            btn_wrapper_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            btn = ttk.Button(
                btn_wrapper_frame,
                text=data["text"],
                image=icon_img,
                compound=tk.TOP,
                command=data["command"],
                state=state
            )
            btn.pack(expand=True, fill="both", ipadx=20, ipady=20)
            btn.image = icon_img

            col += 1
            if col > 1:
                col = 0
                row += 1

    # --- Button Command Methods ---
    def _deselect_all(self, event=None):
        """Deselects all items in the client Treeview when the Escape key is pressed."""
        self.client_tree.selection_remove(self.client_tree.selection())

    def _handle_click_to_deselect(self, event):
        """Deselects all items in the treeview if the click was not on the treeview itself."""
        if event.widget != self.client_tree:
            self.client_tree.selection_remove(self.client_tree.selection())



    def populate_survey_overview(self):
        """Refreshes the data displayed in the view, including the client table."""
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        
        # Assuming a new db_manager method that gets all files with client info joined
        files_data = self.db_manager.get_all_client_files()
        for file in files_data:
            client_name = file['client_name'].upper()
            file_name = file['file_name'].upper()
            contact = file['contact'].upper()
            
            self.client_tree.insert("", tk.END, values=(client_name,file_name,contact), 
                                        tags=('client_row',), iid=file['file_id'])
        
        print("UI refreshed with all client files.")

    def _filter_clients(self, event=None):
        """Filters the client treeview based on the text in the search entry."""
        search_query = self.client_search_entry.get().lower()
        
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        all_files = self.db_manager.get_all_client_files()
        for file in all_files:
            if search_query in file['client_name'].lower() or search_query in file['file_name'].lower():
                self.client_tree.insert("", tk.END, values=(file['client_name'], file['file_name'], file['contact']),
                                         tags=('client_row',), iid=file['file_id'])


    def _open_client_file_dashboard(self, event=None):
        """
        Opens a new window for the selected client's file.
        Correctly retrieves the file ID from the Treeview item.
        """
        selected_items = self.client_tree.selection()
        
        if not selected_items:
            messagebox.showinfo("Selection Error", "Please double-click on a client file row.")
            return

        # The selection method returns a tuple of iids. We get the first one, which is the file_id.
        file_id = selected_items[0]

        # Get the specific file data based on the file_id
        file_data = self.db_manager.get_file_by_id(file_id)
        if not file_data:
            messagebox.showerror("Data Error", "Could not retrieve data for the selected file.")
            return
        
        client_id = file_data.get('client_id')
        if not client_id:
            messagebox.showerror("Data Error", "The selected file does not have a valid client associated.")
            return
        
        client_data = self.db_manager.get_service_client_by_id(client_id)
        if not client_data:
            messagebox.showerror("Data Error", "Could not retrieve data for the associated client.")
            return
        
        combined_data = {**file_data, **client_data}
        ClientFileDashboard(
            self.master,
            self.db_manager,
            combined_data,
            self.populate_survey_overview,
            self.user_id,
            parent_icon_loader=self.load_icon_callback
        )
    def _open_add_client_and_file_form(self):
        """
        Opens the unified form for registering a new client or adding a new file.
        """
        AddClientAndFileForm(
            self.master,
            self.db_manager,
            self.populate_survey_overview,
            self.user_id,
            parent_icon_loader=self.load_icon_callback
        )

    def _open_track_jobs_view(self):
        """Opens the view for tracking the status of all jobs."""
        TrackJobsView(
            self.master,
            self.db_manager,
            self.populate_survey_overview,
            parent_icon_loader=self.load_icon_callback
        )

    def _open_manage_payments_view(self):
        """Opens the view for managing payments for all jobs."""
        ManagePaymentsView(
            self.master,
            self.db_manager,
            self.populate_survey_overview,
            parent_icon_loader=self.load_icon_callback
        )

    def _open_job_reports_view(self):
        """Opens the view for generating reports on all jobs."""
        JobReportsView(
            self.master,
            self.db_manager,
            parent_icon_loader=self.load_icon_callback
        )


class LoginPage(tk.Toplevel):
    def __init__(self, master, db_manager, login_callback, signup_callback):
        super().__init__(master)
        self.master = master
        self.db_manager = db_manager
        self.login_callback = login_callback
        self.signup_callback = signup_callback

        self.title("Login")
        self.geometry("400x250")
        self.resizable(False, False)
        self.grab_set()  # Make the login window modal
        self.transient(master)  # Make it appear on top of the master window
        self.focus_set()

        # Center the login window
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 3) - (self.winfo_width() // 3)
        y = master.winfo_y() + (master.winfo_height() // 3) - (self.winfo_height() // 3)
        self.geometry(f"+{x}+{y}")

        self._create_widgets()

        # Bind Enter key to login
        self.bind('<Return>', lambda event=None: self._login())
        # Protocol handler for closing the window (X button)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")

        lbl_title = ttk.Label(main_frame, text="Login to the REMS System", font=("Arial", 16, "bold"))
        lbl_title.pack(pady=10)

        # Username/Email
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(pady=5, fill="x")
        ttk.Label(username_frame, text="Username/Email:").pack(side="left", padx=(0, 5))
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.pack(side="right", expand=True, fill="x")
        self.username_entry.focus_set()
        # Bind Enter key on username entry to move focus to password
        self.username_entry.bind('<Return>', lambda event=None: self._focus_password_entry())

        # Password
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(pady=5, fill="x")
        ttk.Label(password_frame, text="Password:").pack(side="left", padx=(0, 5))
        self.password_entry = ttk.Entry(password_frame, show="*", width=30)
        self.password_entry.pack(side="right", expand=True, fill="x")

        login_button = ttk.Button(main_frame, text="Login", command=self._login)
        login_button.pack(pady=15)

        # Signup Button - Now packed directly into main_frame

    # signup_button = ttk.Button(main_frame, text="Sign Up for New Account", command=self.signup_callback)
    # signup_button.pack(pady=(10, 0))  # Changed parent and used pack

    def _focus_password_entry(self):
        """Moves focus to the password entry field."""
        self.password_entry.focus_set()

    def _login(self):
        username_email = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username_email or not password:
            messagebox.showwarning("Login Error", "Please enter both username/email and password.")
            return

        user_data = self.db_manager.authenticate_user(username_email, password)

        if user_data:
            role = user_data.get('role')
            user_id = user_data.get('user_id')  # Get the user_id (employee ID)

            messagebox.showinfo("Login Success",
                                f"Welcome, {username_email}! You are logged in as {role.upper()} (ID: {user_id}).")
            self.login_callback(True, role, user_id)  # Pass True, role, and user_id
            self.destroy()  # Close login window
        else:
            messagebox.showerror("Login Failed", "Invalid username/email or password.")
            self.password_entry.delete(0, tk.END)  # Clear password field

    def _on_closing(self):
        """Handle the window close button (X) to exit the app if login is not successful."""
        if messagebox.askokcancel("Exit Login", "Are you sure you want to exit the application?"):
            # When closing without successful login, pass False, None for role, and None for user_id
            self.login_callback(False, None, None)
            # self.destroy()


class RealEstateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # Hide the main window initially
        self.title("Real Estate Management System")
        self.geometry("1200x800")
        self.state('zoomed')

        self.db_manager = DatabaseManager()
        self.icon_images = {}  # Cache for PhotoImage objects

        # Initialize GitHub repository details as class attributes
        self.github_owner = "drelocd"
        self.github_repo = "PYTHON-REAL-ESTATE-MANAGEMENT-DESKTOP-SOFTWARE"

        # Initialize logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Track last update check time to implement rate limiting
        self.last_update_check_time = None
        self.update_check_interval = timedelta(hours=24)  # Check once every 24 hours

        # --- Apply Dark Theme ---
        self.style = ttk.Style(self)
        self.style.theme_use('clam')  # 'clam' is a good base for customization

        # Notebook (tabs) styling
        self.style.configure('TNotebook', background="#FFFFFF", borderwidth=0)
        self.style.configure('TNotebook.Tab', foreground='black', padding=[5, 2])
        self.style.map('TNotebook.Tab',
                       background=[('selected', '#007ACC'), ('active', "#2F8043")],
                       foreground=[('selected', 'white')])

        # Treeview (for tables) styling
        self.style.configure("Treeview",
                             background="#8F8F8F",
                             foreground="black",
                             fieldbackground="#818181",
                             rowheight=25)
        self.style.configure("Treeview.Heading",
                             background="#6BBCF1",
                             foreground="black",
                             font=('Arial', 10, 'bold'))
        self.style.map("Treeview",
                       background=[('selected', "#F5F5F5")],
                       foreground=[('selected', 'black')],
                       font=[('selected', ('Arial', 10, 'bold'))])  # Added font style

        self.login_successful = False
        self.user_type = None
        self.show_login_page()  # Start with the login page

        # Removed the status label at the bottom for update messages
        # self.update_status_label = ttk.Label(self, text="")
        # self.update_status_label.pack(side=tk.BOTTOM, pady=5) # Example packing

        # Removed the initial update check here. It will now run after login.
        # self.after(5000, self.check_for_updates)

    def check_for_updates(self):
        """
        Initiates a version update check in a separate thread to avoid freezing the UI.
        Implements rate limiting to avoid excessive API calls.
        """
        now = datetime.now()
        if self.last_update_check_time and (now - self.last_update_check_time) < self.update_check_interval:
            self.logger.info("Skipping update check: last check was too recent.")
            # No pop-up for skipping, as it's a silent background check interval.
            return

        self.logger.info("Starting update check thread.")
        threading.Thread(target=self._run_update_check, daemon=True).start()

    def _run_update_check(self):
        """
        Performs the actual update check by fetching release information from GitHub.
        This method runs in a separate thread.
        """
        # Using class attributes for GitHub details
        github_release_api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases/latest"

        latest_version_clean = None
        download_url = None
        asset_filename = None

        try:
            response = requests.get(github_release_api_url, timeout=10)
            response.raise_for_status()

            release_info = response.json()
            latest_version_tag = release_info.get("tag_name")

            assets = release_info.get("assets", [])
            for asset in assets:
                if "REMS" in asset["name"].lower() and asset["name"].lower().endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    asset_filename = asset["name"]
                    break

            if not download_url:
                download_url = release_info.get("html_url")
                asset_filename = f"MathengeRealEstateApp-Update-{latest_version_tag}.html"

            if latest_version_tag and download_url and asset_filename:
                if latest_version_tag.startswith('v'):
                    latest_version_clean = latest_version_tag[1:]
                else:
                    latest_version_clean = latest_version_tag

                if self._is_newer_version(latest_version_clean):
                    self.logger.info(f"Newer version available: {latest_version_clean}. Current: {APP_VERSION}")
                    self.after(0, lambda lv=latest_version_clean, dl=download_url,
                                         af=asset_filename: self._prompt_and_download_update(lv, dl, af))
                else:
                    self.logger.info(f"Currently using the latest version: {APP_VERSION}")
                    self.after(0, lambda: messagebox.showinfo("Update Check", "You are using the latest version."))
            else:
                self.logger.warning(
                    "GitHub API response is missing 'tag_name' or 'download_url'. No update information available.")
                self.after(0, lambda: messagebox.showinfo("Update Check",
                                                          "Could not retrieve complete update information from GitHub. No updates available."))

        except requests.exceptions.RequestException as request_exception:
            self.logger.error(f"Failed to check for updates from GitHub: {request_exception}")
            self.after(0, lambda: messagebox.showerror("Update Check Failed",
                                                       f"Failed to check for updates: {request_exception}. Please check your internet connection or repository details."))
        except json.JSONDecodeError:
            self.logger.error("Failed to decode update information from GitHub API. Response was not valid JSON.")
            self.after(0, lambda: messagebox.showerror("Update Check Failed",
                                                       "Failed to decode update information from GitHub. The response was not valid."))
        except Exception as general_exception:
            self.logger.critical(f"An unexpected error occurred during GitHub update check: {general_exception}",
                                 exc_info=True)
            self.after(0, lambda: messagebox.showerror("Update Check Failed",
                                                       f"An unexpected error occurred during update check: {general_exception}"))
        finally:
            self.last_update_check_time = datetime.now()
            self.logger.info(f"Last update check time updated to {self.last_update_check_time}")

    def _is_newer_version(self, latest_version):
        """
        Compares the current application version with the latest version available online.
        Versions are expected in 'X.Y.Z' (semantic versioning) format.
        """
        try:
            current_app_version = [int(x) for x in APP_VERSION.split('.')]
            latest_online_version = [int(x) for x in latest_version.split('.')]

            max_len = max(len(current_app_version), len(latest_online_version))
            current_app_version.extend([0] * (max_len - len(current_app_version)))
            latest_online_version.extend([0] * (max_len - len(latest_online_version)))

            return latest_online_version > current_app_version
        except ValueError as e:
            self.logger.error(f"Error parsing version numbers for comparison: {e}")
            return False

    def _prompt_and_download_update(self, latest_version, download_url, asset_filename):
        """
        Prompts the user if they want to download the update and then initiates the download.
        """
        if messagebox.askyesno(
                "Update Available",
                f"A new version ({latest_version}) of Mathenge's Real Estate Management System is available! "
                f"You are currently using version {APP_VERSION}.\n\n"
                "Would you like to download the update now?"
        ):
            self.logger.info(f"User accepted update to version {latest_version}. Initiating download.")
            threading.Thread(target=self._download_update, args=(download_url, asset_filename, latest_version),
                             daemon=True).start()
        else:
            self.logger.info("User declined the update.")
            messagebox.showinfo("Update Declined",
                                "You declined to download the update. You can check for updates later via the Help menu.")

    def _download_update(self, url, filename, latest_version):
        """
        Downloads the update file to a temporary directory.
        """
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Mathenge_App_Updates")
        os.makedirs(download_dir, exist_ok=True)
        temp_filepath = os.path.join(download_dir, filename)

        try:
            # Use a messagebox to indicate download started
            self.after(0, lambda: messagebox.showinfo("Downloading Update",
                                                      f"Downloading {filename} in the background. You will be notified when it's complete."))
            self.logger.info(f"Starting download of {filename} from {url} to {temp_filepath}")

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                # Progress is not shown in a pop-up, but the download occurs.
                with open(temp_filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            self.logger.info(f"Download of {filename} completed successfully.")
            # Inform the user about the downloaded file and how to install it
            self.after(0, lambda: messagebox.showinfo(
                "Update Downloaded",
                f"A new version ({latest_version}) has been downloaded to:\n\n{temp_filepath}\n\n"
                "Please close the application and run this downloaded file to complete the update process."
            ))

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download update {filename}: {e}")
            self.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download update: {e}"))
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during download of {filename}: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred during download: {e}"))

    def show_login_page(self):
        """Displays the login window."""
        LoginPage(self, self.db_manager, self.on_login_complete, self._open_signup_form)
        # The mainloop will pause here until the Toplevel (LoginPage) is destroyed.

    def on_login_complete(self, success, user_type=None, user_id=None):
        """Callback from LoginPage, executed after a login attempt."""
        self.login_successful = success
        self.user_type = user_type
        self.user_id = user_id  # Store the user ID (employee ID)
        if self.login_successful:
            self.deiconify()  # Show the main window
            self._set_window_icon()
            self._set_taskbar_icon()
            self._customize_title_bar()
            self._create_menu_bar()  # Menu bar now depends on user_type
            self._create_main_frames()
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
            self._on_tab_change(None)  # Populate initial tab data
            # NEW: Check for updates right after successful login
            self.after(1000, self.check_for_updates)  # Check for updates 1 second after login
        else:
            self.destroy()  # Exit application if login fails or is cancelled

    def _open_signup_form(self):
        """
        Opens the SignupForm window to allow new user registration.
        """
        if not self.db_manager:
            messagebox.showerror("Error", "Database manager is not initialized.")
            return

        signup_window = SignupForm(self, self.db_manager, parent_icon_loader=self._load_icon)
        signup_window.wait_window()  # Makes the signup form modal (waits for it to close)

    def _on_tab_change(self, event):
        selected_tab_id = self.notebook.select()
        selected_tab_widget = self.notebook.nametowidget(selected_tab_id)
        if isinstance(selected_tab_widget, DashboardForm):
            selected_tab_widget.populate_dashboard()
        elif isinstance(selected_tab_widget, SalesSectionView):
            selected_tab_widget.populate_system_overview()
        elif isinstance(selected_tab_widget, SurveySectionView):
            selected_tab_widget.populate_survey_overview()

    def _set_window_icon(self):
        ico_path = os.path.join(ICONS_DIR, "home.ico")
        png_path = os.path.join(ICONS_DIR, "home.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception as e:
                print(f"Error loading .ico icon: {e}")

        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
            except Exception as e:
                print(f"Error loading .png icon: {e}")
        else:
            print("No valid icon file found")

    def _set_taskbar_icon(self):
        if os.name == 'nt':
            try:
                from ctypes import windll
                windll.shell32.SetCurrentProcessExplicitAppUserModelID('Mathenge.RealEstate.1')
            except Exception as e:
                print(f"Could not set taskbar ID: {e}")

    def _customize_title_bar(self):
        if os.name == 'nt':
            self._customize_windows_title_bar()
        else:
            self._create_custom_title_bar()

    def _customize_windows_title_bar(self):
        try:
            from ctypes import windll, byref, sizeof, c_int
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36

            hwnd = windll.user32.GetParent(self.winfo_id())

            value = c_int(1)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(value), sizeof(value))

            color = c_int(0x00663300)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))

            text_color = c_int(0x00FFFFFF)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
        except Exception as e:
            print(f"Could not customize Windows title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        self.overrideredirect(True)

        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text="Mathenge's Real Estate Management System",
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        minimize_button = tk.Button(
            title_bar,
            text='−',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='#004080',
            command=lambda: self.state('iconic'),
            font=('Helvetica', 12, 'bold')
        )
        minimize_button.pack(side=tk.RIGHT, padx=5)

        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _load_icon(self, icon_name, size=(40, 40)):
        path = os.path.join(ICONS_DIR, icon_name)
        if not os.path.exists(path):
            print(f"Warning: Icon not found at {path}")
            img = Image.new('RGB', size, color='red')
            tk_img = ImageTk.PhotoImage(img)
            self.icon_images[path] = tk_img
            return tk_img
        try:
            img = Image.open(path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.icon_images[path] = tk_img
            return tk_img
        except Exception as e:
            print(f"Error loading icon {icon_name}: {e}")
            img = Image.new('RGB', size, color='gray')
            tk_img = ImageTk.PhotoImage(img)
            self.icon_images[path] = tk_img
            return tk_img

    def _handle_report_generation(self, section_name, report_type):
        """
        Selects the relevant tab and triggers the report generation method
        on the corresponding section view.
        """
        if section_name == "sales":
            self.notebook.select(self.sales_section)  # Select the Sales tab
            self.sales_section.generate_report_type(report_type)
        elif section_name == "survey":
            self.notebook.select(self.survey_section)  # Select the Survey tab
            self.survey_section.generate_report_type(report_type)

    def _create_menu_bar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_exit)

        # Clients Menu - Now with role-based access
        self.client_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Clients", menu=self.client_menu)
        self.client_menu.add_command(label="Client Management", command=self._open_client_management_form,
                                     state='normal' if self.user_type in ['admin', 'sales_agent'] else 'disabled')

        sales_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sales", menu=sales_menu)
        sales_menu.add_command(label="Add New Property",
                               command=lambda: self._go_to_sales_tab_and_action("add_property"),
                               state='normal' if self.user_type in ['admin', 'property_manager'] else 'disabled')
        sales_menu.add_command(label="Sell Property",
                               command=lambda: self._go_to_sales_tab_and_action("sell_property"),
                               state='normal' if self.user_type in ['admin', 'property_manager',
                                                                    'sales_agent'] else 'disabled')
        sales_menu.add_command(label="Transfer Property",  # NEW MENU ITEM
                               command=lambda: self._go_to_sales_tab_and_action("transfer_property"),
                               state='normal' if self.user_type in ['admin', 'property_manager'] else 'disabled')
        sales_menu.add_separator()
        sales_menu.add_command(label="View All Properties",
                               command=lambda: self._go_to_sales_tab_and_action("view_all"),
                               state='normal' if self.user_type in ['admin', 'property_manager',
                                                                    'sales_agent'] else 'disabled')  # Sales Agent might view properties, but filtered
        sales_menu.add_command(label="Track Payments",
                               command=lambda: self.sales_section._open_track_payments_view(),
                               state='normal' if self.user_type in ['admin', 'sales_agent',
                                                                    'accountant'] else 'disabled')
        sales_menu.add_command(label="Sold Properties Records",
                               command=lambda: self.sales_section._open_sold_properties_view(),
                               state='normal' if self.user_type in ['admin', 'property_manager', 'sales_agent',
                                                                    'accountant'] else 'disabled')

        surveys_menu = tk.Menu(menubar, tearoff=0)
        # Only show Surveys menu if admin or accountant
        if self.user_type in ['admin', 'accountant']:
            menubar.add_cascade(label="Surveys", menu=surveys_menu)
            surveys_menu.add_command(label="Register New Job",
                                     command=lambda: self._go_to_survey_tab_and_action("add_job"),
                                     state='normal' if self.user_type == 'admin' else 'disabled')  # Only admin can register new survey jobs
            surveys_menu.add_command(label="Track Jobs",
                                     command=lambda: self._go_to_survey_tab_and_action("track_jobs"),
                                     state='normal' if self.user_type == 'admin' else 'disabled')  # Only admin can track all jobs
            surveys_menu.add_command(label="Manage Payments",  # Added this menu item
                                     command=lambda: self.survey_section._open_manage_survey_payments_view(),
                                     state='normal' if self.user_type in ['admin', 'accountant'] else 'disabled')
            surveys_menu.add_command(label="Survey Reports",  # Added this menu item
                                     command=lambda: self.survey_section._open_survey_reports_view(),
                                     state='normal' if self.user_type in ['admin', 'accountant'] else 'disabled')

        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Daily/Monthly Sales Report",
                                 command=lambda: self.sales_section.generate_report_type("Daily/Monthly Sales"),
                                 state='normal' if self.user_type in ['admin', 'property_manager', 'sales_agent',
                                                                      'accountant'] else 'disabled')
        reports_menu.add_command(label="Sold Properties Report",
                                 command=lambda: self.sales_section.generate_report_type("Sold Properties"),
                                 state='normal' if self.user_type in ['admin', 'property_manager', 'sales_agent',
                                                                      'accountant'] else 'disabled')
        reports_menu.add_command(label="Pending Instalments Report",
                                 command=lambda: self.sales_section.generate_report_type("Pending Instalments"),
                                 state='normal' if self.user_type in ['admin', 'accountant'] else 'disabled')
        reports_menu.add_command(label="Completed Survey Jobs Report",
                                 command=lambda: self.survey_section.generate_report_type("Completed Survey Jobs"),
                                 state='normal' if self.user_type in ['admin', 'accountant'] else 'disabled')
        reports_menu.add_command(label="Upcoming Deadlines for Surveys",
                                 command=lambda: self.survey_section.generate_report_type("Upcoming Survey Deadlines"),
                                 state='normal' if self.user_type in ['admin', 'accountant'] else 'disabled')

        # --- ADMIN MENU: Only visible if user_type is 'admin' ---
        if self.user_type == 'admin':
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Admin", menu=admin_menu)
            admin_menu.add_command(label="Main Admin Panel", command=self._open_admin_menu)
            admin_menu.add_command(label="Manage Users", command=self._open_admin_Users_panel)
            admin_menu.add_command(label="Add New User (Signup)",
                                   command=self._open_signup_form)  # Added signup option for admin
            admin_menu.add_separator()  # NEW
            admin_menu.add_command(label="System Settings", command=self._open_system_settings)  # NEW
            admin_menu.add_command(label="View Activity Logs", command=self._open_activity_logs)  # NEW
        # --- END ADMIN MENU ---

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        # Add the 'Check for Updates' option
        help_menu.add_command(label="Check for Updates...", command=self.check_for_updates)
        help_menu.add_command(label="About", command=self.show_about_dialog)

    def _open_admin_Users_panel(self):
        # Open the AdminManageusersPanel window
        AdminManageUsersPanel(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_admin_menu(self):

        MainMenuForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_client_management_form(self):
        """
        Opens the ClientForm window for client management.
        """
        ClientForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_system_settings(self):  # NEW METHOD
        """Opens the SystemSettingsForm window."""
        SystemSettingsForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_activity_logs(self):  # NEW METHOD
        """Opens the ActivityLogViewerForm window."""
        ActivityLogViewerForm(self, self.db_manager, parent_icon_loader=self._load_icon)

    def _go_to_sales_tab_and_action(self, action):
        self.notebook.select(self.sales_section)
        if action == "add_property":
            self.sales_section._open_add_property_form()
        elif action == "sell_property":
            self.sales_section._open_sell_property_form()
        elif action == "transfer_property":  # NEW ACTION
            self.sales_section._open_property_transfer_form()
        elif action == "view_all":
            self.sales_section._open_view_all_properties()
        elif action == "track_payments":
            self.sales_section._open_track_payments_view()
        elif action == "sold_properties":
            self.sales_section._open_sold_properties_view()

    def _go_to_survey_tab_and_action(self, action):
        self.notebook.select(self.survey_section)
        if action == "add_job":
            self.survey_section._open_add_survey_job_form()
        elif action == "track_jobs":
            self.survey_section._open_track_survey_jobs_view()

    def _create_main_frames(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Pass user_type to section views
        self.dashboard_section = DashboardForm(self.notebook, self.db_manager, self._load_icon,
                                               user_type=self.user_type)
        self.notebook.add(self.dashboard_section, text="   Dashboard   ")

        self.sales_section = SalesSectionView(self.notebook, self.db_manager, self._load_icon, user_id=self.user_id,
                                              user_type=self.user_type)
        self.notebook.add(self.sales_section, text="   Land Sales & Purchases   ")

        self.survey_section = SurveySectionView(self.notebook, self.db_manager, self._load_icon, user_id=self.user_id,
                                                user_type=self.user_type)
        self.notebook.add(self.survey_section, text="   Survey Services   ")

    def show_about_dialog(self):
        messagebox.showinfo(
            "About",
            "Real Estate Management System\n"
            f"Version {APP_VERSION}\n"  # Display the current app version
            "Developed by Nexora Solutions\n"
            "© 2025 All Rights Reserved."
        )

    def on_exit(self):
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit?"):
            # self.db_manager.close() # Close database connection
            self.destroy()


if __name__ == "__main__":
    app = RealEstateApp()
    app.mainloop()
