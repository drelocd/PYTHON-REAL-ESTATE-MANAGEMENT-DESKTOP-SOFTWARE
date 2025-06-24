import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import your DatabaseManager
from database import DatabaseManager

# Import form classes from your forms directory
# Assuming property_forms.py now contains AddPropertyForm, SellPropertyForm,
# TrackPaymentsForm, SoldPropertiesView, ViewAllPropertiesForm, and EditPropertyForm
from forms.property_forms import AddPropertyForm, SellPropertyForm, TrackPaymentsForm, SoldPropertiesView, ViewAllPropertiesForm, EditPropertyForm, SalesReportsForm
from forms.survey_forms import AddSurveyJobForm, ManagePaymentForm, TrackSurveyJobsForm, SurveyReportsForm # Import SurveyReportsForm here


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
    def __init__(self, master, db_manager, load_icon_callback, parent_icon_loader=None, **kwargs):
        super().__init__(master, padding="10 10 10 10", **kwargs)
        self.db_manager = db_manager
        # Store the icon loader reference
        self.parent_icon_loader_ref = parent_icon_loader
        self.load_icon_callback = load_icon_callback # Callback to main app's _load_icon

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
            ax2.set_title('Sales vs. Pending Payments (illustrative scale)')
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

    def generate_report_type(self, report_name):
        messagebox.showinfo("Report", f"Generating {report_name} Report from Sales Section... (Feature coming soon!)")


class SurveySectionView(ttk.Frame):
    def __init__(self, master, db_manager, load_icon_callback):
        super().__init__(master, padding="10 10 10 10")
        self.db_manager = db_manager
        self.load_icon_callback = load_icon_callback # Store the callback
        # Initialize a list to hold references to PhotoImage objects for SurveySection buttons
        self.survey_button_icons = []
        self._create_widgets()
        self.populate_survey_overview()

    def _create_widgets(self):
        button_grid_container = ttk.Frame(self, padding="20")
        button_grid_container.pack(pady=20, padx=20, fill="x", anchor="n")

        # Configure columns for uniform spacing
        for i in range(2): # Assuming 2 columns of buttons as per original layout
            button_grid_container.grid_columnconfigure(i, weight=1, uniform="survey_button_cols")
        for i in range(2): # Assuming 2 rows of buttons
            button_grid_container.grid_rowconfigure(i, weight=1, uniform="survey_button_rows")

        buttons_data = [
            {"text": "Register New Job", "icon": "add_survey.png", "command": self._open_add_survey_job_form},
            {"text": "Track Jobs", "icon": "track_jobs.png", "command": self._open_track_survey_jobs_view},
            {"text": "Manage Payments", "icon": "manage_payments.png", "command": self._open_manage_survey_payments_view},
            {"text": "Survey Reports", "icon": "survey_reports.png", "command": self._open_survey_reports_view},
        ]

        row, col = 0, 0
        for data in buttons_data:
            icon_img = self.load_icon_callback(data["icon"]) # Load icon
            self.survey_button_icons.append(icon_img) # <--- IMPORTANT: Store reference here!
            
            btn_wrapper_frame = ttk.Frame(button_grid_container, relief="raised", borderwidth=1, cursor="hand2")
            btn_wrapper_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            btn = ttk.Button(
                btn_wrapper_frame,
                text=data["text"],
                image=icon_img,    # Set the image
                compound=tk.TOP,    # Place image above text
                command=data["command"]
            )
            btn.pack(expand=True, fill="both", ipadx=20, ipady=20)
            
            btn.image = icon_img # <--- IMPORTANT: Also store reference on the button widget itself!

            col += 1
            if col > 1: # Move to next row after 2 columns
                col = 0
                row += 1


                #ADDED
        # Buttons Frame
        buttons_frame = ttk.LabelFrame(self, text="Actions", padding="10")
        buttons_frame.pack(fill="x", padx=10, pady=10)

        btn_view_receipts = ttk.Button(buttons_frame, text="View All Receipts", command=self._open_receipts_folder)
        btn_view_receipts.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Configure column weights for even distribution
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

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
        """
        Fetches data from the database and updates the Survey Overview dashboard.
        """
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
                         parent_icon_loader=self.load_icon_callback, window_icon_name="add_survey.png")

    def _open_track_survey_jobs_view(self):
        TrackSurveyJobsForm(
            self.master,
            self.db_manager,
            self.populate_survey_overview,
            parent_icon_loader=self.load_icon_callback,
            window_icon_name="track_jobs.png"
        )

    #ADDED
    def refresh_summary(self):
        total_jobs = self.db_manager.get_total_survey_jobs_count()
        pending_jobs = self.db_manager.get_pending_survey_jobs_count()
        completed_jobs = self.db_manager.get_completed_survey_jobs_count()

        self.total_survey_jobs_label.config(text=f"Total Survey Jobs: {total_jobs}")
        self.pending_jobs_label.config(text=f"Pending Jobs: {pending_jobs}")
        self.completed_jobs_label.config(text=f"Completed Jobs: {completed_jobs}")

    def _open_manage_survey_payments_view(self):
        ManagePaymentForm(self.master, self.db_manager, self.populate_survey_overview,
                          parent_icon_loader=self.load_icon_callback, window_icon_name="payment.png")

    def _open_survey_reports_view(self):
        SurveyReportsForm(self.master, self.db_manager,
                          parent_icon_loader=self.load_icon_callback, window_icon_name="survey_reports.png")

    def generate_report_type(self, report_name):
        messagebox.showinfo("Report", f"Generating {report_name} Report from Survey Section... (Feature coming soon!)")

    def _open_receipts_folder(self):
        """Opens the receipts directory in the file explorer."""
        if os.path.exists(RECEIPTS_DIR):
            os.startfile(RECEIPTS_DIR)
        else:
            messagebox.showerror("Error", "Receipts folder not found.")


class RealEstateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mathenge's Real Estate Management System")
        self.geometry("1200x800")
        self.state('zoomed')

        # Set window properties
        self._set_window_icon()
        self._set_taskbar_icon()
        self._customize_title_bar()

        self.db_manager = DatabaseManager()
        self.icon_images = {}  # Cache for PhotoImage objects

        self._create_menu_bar()
        self._create_main_frames()
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        self._on_tab_change(None)

        # For custom title bar dragging
        self._start_x = 0
        self._start_y = 0

    def _on_tab_change(self, event):
        """Callback for when the notebook tab changes, to refresh active tab's data."""
        selected_tab_id = self.notebook.select()
        selected_tab_widget = self.notebook.nametowidget(selected_tab_id)
        
        if isinstance(selected_tab_widget, SalesSectionView):
            selected_tab_widget.populate_system_overview()
        elif isinstance(selected_tab_widget, SurveySectionView):
            selected_tab_widget.populate_survey_overview()

    def _set_window_icon(self):
        """Sets the window icon from the assets directory."""
        # Try .ico first (best for Windows)
        ico_path = os.path.join(ICONS_DIR, "home.ico")
        png_path = os.path.join(ICONS_DIR, "home.png")
        
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception as e:
                print(f"Error loading .ico icon: {e}")
        
        # Fallback to .png (cross-platform)
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
        """Ensures the icon appears in the taskbar/dock."""
        # This is handled by _set_window_icon on most platforms
        # Additional Windows-specific taskbar grouping
        if os.name == 'nt':
            try:
                from ctypes import windll
                windll.shell32.SetCurrentProcessExplicitAppUserModelID('Mathenge.RealEstate.1')
            except Exception as e:
                print(f"Could not set taskbar ID: {e}")

    def _customize_title_bar(self):
        """Attempts to customize the title bar appearance."""
        # Try Windows-specific customization first
        if os.name == 'nt':
            self._customize_windows_title_bar()
        else:
            # Fallback to custom title bar for other platforms
            self._create_custom_title_bar()

    def _customize_windows_title_bar(self):
        """Windows-specific title bar customization."""
        try:
            from ctypes import windll, byref, sizeof, c_int
            
            # Windows constants
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            
            hwnd = windll.user32.GetParent(self.winfo_id())
            
            # Set dark mode
            value = c_int(1)
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                byref(value), 
                sizeof(value)
            )
            
            # Set title bar color to dark blue (RGB: 0, 51, 102)
            color = c_int(0x00663300)  # BGR format for Windows
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
            print(f"Could not customize Windows title bar: {e}")
            self._create_custom_title_bar()

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
            text="Mathenge's Real Estate Management System",
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
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Minimize button
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
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _load_icon(self, icon_name, size=(40,40)):
        """
        Loads and resizes an icon from the 'assets/icons' directory.
        Stores a reference to the PhotoImage object to prevent garbage collection.
        """
        path = os.path.join(ICONS_DIR, icon_name)
        if not os.path.exists(path):
            print(f"Warning: Icon not found at {path}")
            # Create a placeholder red square if icon is missing
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
            # Create a placeholder gray square on error
            img = Image.new('RGB', size, color='gray')
            tk_img = ImageTk.PhotoImage(img)
            self.icon_images[path] = tk_img
            return tk_img

    def _create_menu_bar(self):
        """Creates the application's menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_exit)

        # Sales menu
        sales_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sales", menu=sales_menu)
        sales_menu.add_command(label="Add New Property", command=lambda: self._go_to_sales_tab_and_action("add_property"))
        sales_menu.add_command(label="Sell Property", command=lambda: self._go_to_sales_tab_and_action("sell_property"))
        sales_menu.add_separator()
        sales_menu.add_command(label="View All Properties", command=lambda: self._go_to_sales_tab_and_action("view_all"))
        sales_menu.add_command(label="Track Payments", command=lambda: self._go_to_sales_tab_and_action("track_payments"))
        sales_menu.add_command(label="Sold Properties Records", command=lambda: self._go_to_sales_tab_and_action("sold_properties"))

        # Surveys menu
        surveys_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Surveys", menu=surveys_menu)
        surveys_menu.add_command(label="Register New Job", command=lambda: self._go_to_survey_tab_and_action("add_job"))
        surveys_menu.add_command(label="Track Jobs", command=lambda: self._go_to_survey_tab_and_action("track_jobs"))

        # Reports menu
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Daily/Monthly Sales Report", command=lambda: self.sales_section.generate_report_type("Daily/Monthly Sales"))
        reports_menu.add_command(label="Sold Properties Report", command=lambda: self.sales_section.generate_report_type("Sold Properties"))
        reports_menu.add_command(label="Pending Instalments Report", command=lambda: self.sales_section.generate_report_type("Pending Instalments"))
        reports_menu.add_command(label="Completed Survey Jobs Report", command=lambda: self.survey_section.generate_report_type("Completed Survey Jobs"))
        reports_menu.add_command(label="Upcoming Deadlines for Surveys", command=lambda: self.survey_section.generate_report_type("Upcoming Survey Deadlines"))

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)

    def _go_to_sales_tab_and_action(self, action):
        """Helper to switch to sales tab and trigger an action if needed."""
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
        """Helper to switch to survey tab and trigger an action if needed."""
        self.notebook.select(self.survey_section)
        if action == "add_job":
            self.survey_section._open_add_survey_job_form()
        elif action == "track_jobs":
            self.survey_section._open_track_survey_jobs_view()

    def _create_main_frames(self):
        """Creates the main tabbed interface for different sections."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Pass load_icon_callback to SalesSectionView
        self.sales_section = SalesSectionView(self.notebook, self.db_manager, self._load_icon)
        self.notebook.add(self.sales_section, text="   Land Sales & Purchases   ")

        # Pass load_icon_callback to SurveySectionView
        self.survey_section = SurveySectionView(self.notebook, self.db_manager, self._load_icon)
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
        """Handles application exit, confirming with the user."""
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit?"):
            self.destroy()

if __name__ == "__main__":
    app = RealEstateApp()
    app.mainloop()