import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime
from datetime import datetime, timedelta

import menubar
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import your DatabaseManager
from database import DatabaseManager
db_manager = DatabaseManager()
print("\n--- Checking/Adding Default Users ---")

# Add 'admin' user if they don't exist
# We use db_manager.authenticate_user to check for existence and valid password (for a robust check)
# If authenticate_user returns None, the user doesn't exist or password is wrong, so we can try adding them.
admin_username = "admin"
admin_password = "admin" # This will be hashed by add_user

if not db_manager.authenticate_user(admin_username, admin_password):
    print(f"'{admin_username}' user not found or password incorrect. Attempting to add...")
    admin_id = db_manager.add_user(admin_username, admin_password, "admin")
    if admin_id:
        print(f"Admin user '{admin_username}' added successfully with ID: {admin_id}")
    else:
        print(f"Failed to add admin user '{admin_username}'. It might already exist with a different password.")
else:
    print(f"Admin user '{admin_username}' already exists.")

# Add 'user' user if they don't exist
user_username = "user"
user_password = "user" # This will be hashed by add_user (if you want 'user' as password for 'user')
# OR user_password = "admin" if you want 'admin' password for both 'user' and 'admin' accounts
# Based on your request, I'll use "admin" as the password for the 'user' account too.
user_password_for_creation = "admin"


if not db_manager.authenticate_user(user_username, user_password_for_creation):
    print(f"'{user_username}' user not found or password incorrect. Attempting to add...")
    user_id = db_manager.add_user(user_username, user_password_for_creation, "user")
    if user_id:
        print(f"Regular user '{user_username}' added successfully with ID: {user_id}")
    else:
        print(f"Failed to add regular user '{user_username}'. It might already exist with a different password.")
else:
    print(f"Regular user '{user_username}' already exists.")

print("--- Default User Setup Complete ---")

# Import form classes from your forms directory
# Assuming property_forms.py now contains AddPropertyForm, SellPropertyForm,
# TrackPaymentsForm, SoldPropertiesView, ViewAllPropertiesForm, and EditPropertyForm
from forms.property_forms import AddPropertyForm, SellPropertyForm, TrackPaymentsForm, SoldPropertiesView, ViewAllPropertiesForm, EditPropertyForm, SalesReportsForm
from forms.survey_forms import AddSurveyJobForm,  PaymentSurveyJobsFrame, TrackSurveyJobsFrame, SurveyReportsForm
from forms.admin_form import AdminPanel # Import the AdminPanel class
from forms.signup_form import SignupForm
from forms.client_form import ClientForm


# --- Global Constants ---
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
    def __init__(self, master, db_manager, load_icon_callback, user_id):
        super().__init__(master, padding="10 10 10 10")
        self.db_manager = db_manager
        self.load_icon_callback = load_icon_callback # Callback to main app's _load_icon
        self.user_id = user_id
        

        # Initialize a list to hold references to PhotoImage objects for SalesSection buttons
        self.sales_button_icons = [] 

        self._create_widgets()
        self.populate_system_overview()
        

    def _create_widgets(self):
        button_grid_container = ttk.Frame(self, padding="20")
        button_grid_container.pack(pady=20, padx=20, fill="x", anchor="n")

        for i in range(3):
            button_grid_container.grid_columnconfigure(i, weight=1, uniform="sales_button_cols")
        for i in range(2):
            button_grid_container.grid_rowconfigure(i, weight=1, uniform="sales_button_rows")

        buttons_data = [
            {"text": "Add New Property", "icon": "add_property.png", "command": self._open_add_property_form},
            {"text": "Sell Property", "icon": "manage_sales.png", "command": self._open_sell_property_form},
            {"text": "Track Payments", "icon": "track_payments.png", "command": self._open_track_payments_view},
            {"text": "Sold Properties", "icon": "sold_properties.png", "command": self._open_sold_properties_view},
            {"text": "View All Properties", "icon": "view_all_properties.png", "command": self._open_view_all_properties}, 
            {"text": "Reports & Receipts", "icon": "reports_receipts.png", "command": self._open_sales_reports_receipts_view},
        ]

        row, col = 0, 0
        for data in buttons_data:
            icon_img = self.load_icon_callback(data["icon"])
            self.sales_button_icons.append(icon_img) # <--- IMPORTANT: Store reference here!
            
            btn_wrapper_frame = ttk.Frame(button_grid_container, relief="raised", borderwidth=1, cursor="hand2")
            btn_wrapper_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            btn = ttk.Button(
                btn_wrapper_frame,
                text=data["text"],
                image=icon_img,
                compound=tk.TOP,
                command=data["command"]
            )
            btn.pack(expand=True, fill="both", ipadx=20, ipady=20)
            
            btn.image = icon_img # <--- IMPORTANT: Also store reference on the button widget itself!
            
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        self.system_overview_frame = ttk.LabelFrame(self, text="System Overview", padding="10")
        self.system_overview_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.stats_frame = ttk.Frame(self.system_overview_frame)
        self.stats_frame.pack(side="top", fill="x", pady=(5, 10))
        
        self.lbl_properties_sold = ttk.Label(self.stats_frame, text="Properties Sold: N/A", font=("Arial", 12, "bold"))
        self.lbl_properties_sold.pack(side="left", padx=10)
        
        self.lbl_total_properties = ttk.Label(self.stats_frame, text="Total Properties: N/A", font=("Arial", 12, "bold"))
        self.lbl_total_properties.pack(side="left", padx=10)

        self.lbl_pending_payments = ttk.Label(self.stats_frame, text="Pending Sales Payments: N/A", font=("Arial", 12, "bold"))
        self.lbl_pending_payments.pack(side="left", padx=10)

        self.lbl_total_clients = ttk.Label(self.stats_frame, text="Total Clients: N/A", font=("Arial", 12, "bold"))
        self.lbl_total_clients.pack(side="left", padx=10)

        self.lbl_current_date = ttk.Label(self.stats_frame, text=f"Date: {datetime.now().strftime('%Y-%m-%d')}", font=("Arial", 10))
        self.lbl_current_date.pack(side="right", padx=10)

        self.charts_frame = ttk.Frame(self.system_overview_frame)
        self.charts_frame.pack(side="bottom", fill="both", expand=True)

    def populate_system_overview(self):
        """
        Fetches data from the database and updates the System Overview dashboard
        with key metrics and charts for sales.
        """
        for widget in self.charts_frame.winfo_children():
            widget.destroy()

        num_properties_sold = 0
        num_properties_available = 0
        num_total_properties = 0
        total_pending_sales_payments = 0.0
        total_clients = 0

        display_properties_sold = "N/A"
        display_total_properties = "N/A"
        display_pending_sales_payments_str = "N/A"
        display_total_clients = "N/A"

        try:
            properties_sold_data = self.db_manager.get_all_properties(status='Sold') 
            properties_available_data = self.db_manager.get_all_properties(status='Available') 
            
            num_properties_sold = len(properties_sold_data) if properties_sold_data else 0
            num_properties_available = len(properties_available_data) if properties_available_data else 0
            num_total_properties = num_properties_sold + num_properties_available

            total_pending_sales_payments = self.db_manager.get_total_pending_sales_payments()
            
            total_clients = self.db_manager.get_total_clients()

            display_properties_sold = str(num_properties_sold)
            display_total_properties = str(num_total_properties)
            display_pending_sales_payments_str = f"KES {total_pending_sales_payments:,.2f}"
            display_total_clients = str(total_clients)

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve sales overview data: {e}")
            
        self.lbl_properties_sold.config(text=f"Properties Sold: {display_properties_sold}")
        self.lbl_total_properties.config(text=f"Total Properties: {display_total_properties}")
        self.lbl_pending_payments.config(text=f"Pending Sales Payments: {display_pending_sales_payments_str}")
        self.lbl_total_clients.config(text=f"Total Clients: {display_total_clients}")
        self.lbl_current_date.config(text=f"Date: {datetime.now().strftime('%Y-%m-%d')}")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        fig.patch.set_facecolor('lightgray')

        labels = ['Sold', 'Available']
        sizes = [num_properties_sold, num_properties_available]
        colors = ['#4CAF50', '#FFC107']
        
        if sum(sizes) > 0:
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90,
                            wedgeprops={'edgecolor': 'black'})
        else:
            ax1.text(0.5, 0.5, 'No Property Data', horizontalalignment='center',
                                 verticalalignment='center', transform=ax1.transAxes, fontsize=12)
        ax1.set_title('Property Status Overview')
        ax1.axis('equal')

        if isinstance(total_pending_sales_payments, (int, float)):
            payment_status_data = [num_properties_sold, total_pending_sales_payments]
            payment_labels = ['Sold Count', 'Pending Payments (KES)']
            
            display_pending_payments = total_pending_sales_payments 
            if total_pending_sales_payments > 100000:
                display_pending_payments = total_pending_sales_payments / 100000
            
            ax2.bar(payment_labels, [num_properties_sold, display_pending_payments], color=['skyblue', 'salmon'])
            ax2.set_title('Sales vs. Pending Payments')
            ax2.set_ylabel('Count / Value')
            for i, v in enumerate([num_properties_sold, display_pending_payments]):
                ax2.text(i, v + 0.1, f'{v:,.0f}', color='black', ha='center', va='bottom')
        else:
            ax2.text(0.5, 0.5, 'No Detailed Payment Data', horizontalalignment='center',
                                 verticalalignment='center', transform=ax2.transAxes, fontsize=12)
        
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # <--- FIX: Close the Matplotlib figure after embedding it in Tkinter
        plt.close(fig)

    # --- Methods called by buttons within SalesSection ---
    def _open_add_property_form(self):
        AddPropertyForm(self.master, self.db_manager, self.populate_system_overview,
                        user_id=self.user_id,
                        parent_icon_loader=self.load_icon_callback, window_icon_name="add_property.png")

    def _open_sell_property_form(self):
        SellPropertyForm(self.master, self.db_manager, self.populate_system_overview,
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
        SalesReportsForm(self.master, self.db_manager, parent_icon_loader=self.load_icon_callback, window_icon_name="reports.png")

    def generate_report_type(self, action):
        #self.notebook.select(self.sales_section)
        if action == "Daily/Monthly Sales":
            self._open_sales_reports_receipts_view()  # Corrected from self.sales_section
        elif action == "Sold Properties":
            self._open_sales_reports_receipts_view()  # Corrected from self.sales_section
        elif action == "Pending Instalments":
            self._open_sales_reports_receipts_view()




class SurveySectionView(ttk.Frame):
    def __init__(self, master, db_manager, load_icon_callback, user_id):
        super().__init__(master, padding="10 10 10 10")
        self.db_manager = db_manager
        self.load_icon_callback = load_icon_callback
        self.user_id = user_id
        self.survey_button_icons = [] # To hold PhotoImage references
        self._create_widgets()
        self.populate_survey_overview()

    def _create_widgets(self):
        button_grid_container = ttk.Frame(self, padding="20")
        button_grid_container.pack(pady=20, padx=20, fill="x", anchor="n")

        for i in range(2):
            button_grid_container.grid_columnconfigure(i, weight=1, uniform="survey_button_cols")
        for i in range(2):
            button_grid_container.grid_rowconfigure(i, weight=1, uniform="survey_button_rows")

        buttons_data = [
            {"text": "Register New Job", "icon": "add_survey.png", "command": self._open_add_survey_job_form},
            {"text": "Track Jobs", "icon": "track_jobs.png", "command": self._open_track_survey_jobs_view},
            {"text": "Manage Payments", "icon": "manage_payments.png", "command": self._open_manage_survey_payments_view},
            {"text": "Survey Reports", "icon": "survey_reports.png", "command": self._open_survey_reports_view},
        ]

        row, col = 0, 0
        for data in buttons_data:
            # Ensure load_icon_callback can handle 'size' if needed by your IconLoader
            icon_img = self.load_icon_callback(data["icon"], size=(64, 64)) # Example size for a button icon
            self.survey_button_icons.append(icon_img) # IMPORTANT: Store reference here!

            btn_wrapper_frame = ttk.Frame(button_grid_container, relief="raised", borderwidth=1, cursor="hand2")
            btn_wrapper_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            btn = ttk.Button(
                btn_wrapper_frame,
                text=data["text"],
                image=icon_img,
                compound=tk.TOP,
                command=data["command"]
            )
            btn.pack(expand=True, fill="both", ipadx=20, ipady=20)

            btn.image = icon_img # Also store reference on the button widget itself!

            col += 1
            if col > 1:
                col = 0
                row += 1

        self.survey_overview_frame = ttk.LabelFrame(self, text="Survey Overview", padding="10")
        self.survey_overview_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.lbl_total_jobs = ttk.Label(self.survey_overview_frame, text="Total Jobs: N/A", font=("Arial", 12, "bold"))
        self.lbl_total_jobs.pack(side="left", padx=10)

        self.lbl_completed_jobs = ttk.Label(self.survey_overview_frame, text="Completed Jobs: N/A", font=("Arial", 12, "bold"))
        self.lbl_completed_jobs.pack(side="left", padx=10)

        self.lbl_upcoming_deadlines = ttk.Label(self.survey_overview_frame, text="Upcoming Deadlines (30 days): N/A", font=("Arial", 12, "bold"))
        self.lbl_upcoming_deadlines.pack(side="left", padx=10)

        self.lbl_pending_survey_payments = ttk.Label(self.survey_overview_frame, text="Pending Survey Payments: N/A", font=("Arial", 12, "bold"))
        self.lbl_pending_survey_payments.pack(side="left", padx=10)

    def populate_survey_overview(self):
        
        
        # ... (Your existing populate_survey_overview method) ...
        try:
            total_jobs = self.db_manager.get_total_survey_jobs()
            completed_jobs = self.db_manager.get_completed_survey_jobs_count()
            upcoming_deadlines_count = self.db_manager.get_upcoming_survey_deadlines_count()
            total_pending_survey_payments = self.db_manager.get_total_pending_survey_payments()

            self.lbl_total_jobs.config(text=f"Total Jobs: {total_jobs}")
            self.lbl_completed_jobs.config(text=f"Completed Jobs: {completed_jobs}")
            self.lbl_upcoming_deadlines.config(text=f"Upcoming Deadlines (30 days): {upcoming_deadlines_count}")
            self.lbl_pending_survey_payments.config(text=f"Pending Survey Payments: KES {total_pending_survey_payments:,.2f}")

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve survey overview data: {e}")
            self.lbl_total_jobs.config(text="Total Jobs: N/A")
            self.lbl_completed_jobs.config(text="Completed Jobs: N/A")
            self.lbl_upcoming_deadlines.config(text="Upcoming Deadlines: N/A")
            self.lbl_pending_survey_payments.config(text="Pending Survey Payments: N/A")


    def _open_add_survey_job_form(self):
        AddSurveyJobForm(self.master, self.db_manager, self.populate_survey_overview,
                         parent_icon_loader=self.load_icon_callback, window_icon_name="add_survey.png",current_user_id=self.user_id)

    def _open_track_survey_jobs_view(self):
        TrackSurveyJobsFrame(self.master, self.db_manager,self.populate_survey_overview,
                             parent_icon_loader=self.load_icon_callback,window_icon_name="track_jobs.png")


    def _open_manage_survey_payments_view(self):
        PaymentSurveyJobsFrame(self.master, self.db_manager, self.populate_survey_overview,
                              parent_icon_loader=self.load_icon_callback, 
                              window_icon_name="manage_payments.png")



    def _open_survey_reports_view(self):
        SurveyReportsForm(self.master, self.db_manager,
                               parent_icon_loader=self.load_icon_callback,window_icon_name="survey_reports.png")

    def generate_report_type(self, action):
        # self.notebook.select(self.sales_section)
        if action == "Completed Survey Jobs":
            self._open_survey_reports_view()  # Corrected from self.sales_section
        elif action == "Upcoming Survey Deadlines":
            self._open_survey_reports_view()


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
        self.transient(master) # Make it appear on top of the master window
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

        lbl_title = ttk.Label(main_frame, text="Login to Mathenge's System", font=("Arial", 16, "bold"))
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
            user_id = user_data.get('user_id') # Get the user_id (employee ID)
            
            messagebox.showinfo("Login Success", f"Welcome, {username_email}! You are logged in as {role.upper()} (ID: {user_id}).")
            self.login_callback(True, role, user_id) # Pass True, role, and user_id
            self.destroy() # Close login window
        else:
            messagebox.showerror("Login Failed", "Invalid username/email or password.")
            self.password_entry.delete(0, tk.END) # Clear password field

    def _on_closing(self):
        """Handle the window close button (X) to exit the app if login is not successful."""
        if messagebox.askokcancel("Exit Login", "Are you sure you want to exit the application?"):
            # When closing without successful login, pass False, None for role, and None for user_id
            self.login_callback(False, None, None) 
            #self.destroy()



class RealEstateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide the main window initially
        self.title("Mathenge's Real Estate Management System")
        self.geometry("1200x800")
        self.state('zoomed')

        self.db_manager = DatabaseManager()
        self.icon_images = {}  # Cache for PhotoImage objects

        # --- Apply Dark Theme ---
        self.style = ttk.Style(self)
        self.style.theme_use('clam') # 'clam' is a good base for customization
        
        
        
        
        
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
               font=[('selected', ('Arial', 10, 'bold'))]) # Added font style
                       
        self.login_successful = False
        self.user_type = None
        self.show_login_page() # Start with the login page

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
            self.deiconify() # Show the main window
            self._set_window_icon()
            self._set_taskbar_icon()
            self._customize_title_bar()
            self._create_menu_bar() # Menu bar now depends on user_type
            self._create_main_frames()
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
            self._on_tab_change(None) # Populate initial tab data
        else:
            self.destroy() # Exit application if login fails or is cancelled

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
        
        if isinstance(selected_tab_widget, SalesSectionView):
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

    def _load_icon(self, icon_name, size=(40,40)):
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

        # Clients Menu - NEWLY ADDED
        self.client_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Clients", menu=self.client_menu)
        self.client_menu.add_command(label="Client Management", command=self._open_client_management_form)

        sales_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sales", menu=sales_menu)
        sales_menu.add_command(label="Add New Property", command=lambda: self._go_to_sales_tab_and_action("add_property"))
        sales_menu.add_command(label="Sell Property", command=lambda: self._go_to_sales_tab_and_action("sell_property"))
        sales_menu.add_separator()
        sales_menu.add_command(label="View All Properties", command=lambda: self._go_to_sales_tab_and_action("view_all"))
        sales_menu.add_command(label="Track Payments", command=lambda: self._go_to_sales_tab_and_action("track_payments"))
        sales_menu.add_command(label="Sold Properties Records", command=lambda: self._go_to_sales_tab_and_action("sold_properties"))

        surveys_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Surveys", menu=surveys_menu)
        surveys_menu.add_command(label="Register New Job", command=lambda: self._go_to_survey_tab_and_action("add_job"))
        surveys_menu.add_command(label="Track Jobs", command=lambda: self._go_to_survey_tab_and_action("track_jobs"))

        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Daily/Monthly Sales Report", command=lambda: self.sales_section.generate_report_type("Daily/Monthly Sales"))
        reports_menu.add_command(label="Sold Properties Report", command=lambda: self.sales_section.generate_report_type("Sold Properties"))
        reports_menu.add_command(label="Pending Instalments Report", command=lambda: self.sales_section.generate_report_type("Pending Instalments"))
        reports_menu.add_command(label="Completed Survey Jobs Report", command=lambda: self.survey_section.generate_report_type("Completed Survey Jobs"))
        reports_menu.add_command(label="Upcoming Deadlines for Surveys", command=lambda: self.survey_section.generate_report_type("Upcoming Survey Deadlines"))

        # --- ADMIN MENU: Only visible if user_type is 'admin' ---
        if self.user_type == 'admin':
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Admin", menu=admin_menu)
            admin_menu.add_command(label="Manage Users", command=self._open_admin_panel)
            admin_menu.add_command(label="Add New User (Signup)", command=self._open_signup_form)  # Added signup option for admin
            # You can add more admin-specific functionalities here later
        # --- END ADMIN MENU ---

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)

    def _open_admin_panel(self):
        # Open the AdminPanel window
        AdminPanel(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_client_management_form(self):
        """
        Opens the ClientForm window for client management.
        """
        ClientForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _go_to_sales_tab_and_action(self, action):
        self.notebook.select(self.sales_section)
        if action == "add_property":
            self.sales_section._open_add_property_form()
        elif action == "sell_property":
            self.sales_section._open_sell_property_form()
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

        self.sales_section = SalesSectionView(self.notebook, self.db_manager, self._load_icon,user_id=self.user_id)
        self.notebook.add(self.sales_section, text="   Land Sales & Purchases   ")

        self.survey_section = SurveySectionView(self.notebook, self.db_manager, self._load_icon, user_id=self.user_id)
        self.notebook.add(self.survey_section, text="   Survey Services   ")

    def show_about_dialog(self):
        messagebox.showinfo(
            "About",
            "Mathenge's Real Estate Management System\n"
            "Version 1.0\n"
            "Developed by Nexora Solutions\n"
            "© 2025 All Rights Reserved."
        )

    def on_exit(self):
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit?"):
            #self.db_manager.close() # Close database connection
            self.destroy()

if __name__ == "__main__":
    app = RealEstateApp()
    app.mainloop()