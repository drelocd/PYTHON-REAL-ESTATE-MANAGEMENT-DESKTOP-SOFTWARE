import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')

# Assuming AdminPanel and SignupForm are in the 'forms' directory
try:
    from forms.admin_manage_users_form import AdminManageUsersPanel
    from forms.signup_form import SignupForm
    from forms.admin_manage_agents_form import AdminManageAgentsPanel
    from forms.agents_signup_form import AgentSignupForm
    from forms.admin_manage_payments_form import ManagePaymentPlansForm
    from forms.activity_log_viewer_form import ActivityLogViewerForm
    from forms.projects_form import ProjectsPanel
    from forms.system_settings_form import SystemSettingsForm
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import required modules. "
                                         f"Please ensure admin_panel.py and signup_form.py are in the 'forms' directory. Error: {e}")
    AdminManageUsersPanel = None
    SignupForm = None
    AdminManageAgentsPanel = None
    AgentSignupForm = None



class MainMenuForm(tk.Toplevel):
    """
    A Toplevel window that serves as the main admin menu.
    It provides buttons to open various administrative functions.
    """

    def __init__(self, parent, db_manager, user_id, parent_icon_loader=None):
        """
        Initializes the MainMenuForm window with a custom title bar and a centered layout.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager.
            user_id: The ID of the currently logged-in user.
            parent_icon_loader: A callable from the parent to load icons consistently.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader

        # Variables for custom title bar dragging
        self._start_x = 0
        self._start_y = 0
        self.icons = {}  # To store PhotoImage references
        self.icon_images = {}

        # Set the window properties and create the custom title bar
        self._set_window_properties(600, 350, "admin_panel.png")
        self._customize_title_bar()

        # Create and place widgets based on the new layout
        self._create_widgets()

        # Grab focus and set the protocol
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _customize_title_bar(self):
        """Creates a custom Tkinter title bar, bypassing the native one."""
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text="Admin Main Menu",
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

    def _save_drag_start_pos(self, event):
        """Saves the initial position of the mouse pointer for dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Moves the window based on the mouse drag."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _on_closing(self):
        """Handle the window close button (X) for custom title bar."""
        self.grab_release()
        self.destroy()

    def _set_window_properties(self, width, height, icon_name):
        """Calculates the coordinates to center the window and sets its properties."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set the custom icon for the window
        png_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
                self.icon_photo_ref = photo # Keep a reference to prevent garbage collection
            except Exception as e:
                print(f"Error loading .png icon for MainMenuForm: {e}")
        else:
            print(f"Icon file not found: {png_path}")

    def _load_icon_for_button(self, icon_name, size=(24, 24)):
        """
        Loads an icon for a button. Caches the PhotoImage to prevent garbage collection.
        Uses parent's loader if available, otherwise falls back to local loading.
        """
        if self.parent_icon_loader:
            img = self.parent_icon_loader(icon_name, size=size)
        else:
            path = os.path.join(ICONS_DIR, icon_name)
            try:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Icon not found at {path}")
                original_img = Image.open(path)
                img = original_img.resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
            except Exception as e:
                print(f"MainMenuForm: Fallback Error loading icon {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        return img
    
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

    def _create_widgets(self):
        """Creates and places the buttons in the main menu with a new layout."""
        # Main content frame with a slight border and padding
        main_frame = ttk.Frame(self, padding="20", relief="groove")
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(main_frame, text="Admin Functions", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # A frame for the buttons to keep them together in a grid
        button_container = ttk.Frame(main_frame)
        button_container.pack(fill="both", expand=True)
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, weight=1)

        # Create a style for the buttons and apply the font here
        style = ttk.Style()
        button_font = ('Helvetica', 12, 'bold')
        style.configure('Custom.TButton', font=button_font)
        button_style = 'Custom.TButton'
        button_padding = 10
        button_sticky = "nsew"

        # Load icons for the buttons
        self.manage_users_icon = self._load_icon_for_button("manage_users.png")
        self.add_new_project_icon = self._load_icon_for_button("project.png")
        self.settings_icon = self._load_icon_for_button("system_settings.png")
        self.logs_icon = self._load_icon_for_button("activity_logs.png")
        self.admin_menu_icon = self._load_icon_for_button("manage_agents.png") # Assuming a new icon for the main menu
        self.payment_icon = self._load_icon_for_button("payment.png") # Assuming a new icon for payment plans

        # Button 1: Main Admin Panel
        btn_main_admin = ttk.Button(
            button_container,
            text="Manage Agents",
            image=self.admin_menu_icon,
            compound=tk.LEFT,
            command=self._open_admin_manage_agents_panel,
            style=button_style,
        )
        btn_main_admin.grid(row=0, column=0, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)

        # Button 2: Manage Users
        btn_manage_users = ttk.Button(
            button_container,
            text="Manage Users",
            image=self.manage_users_icon,
            compound=tk.LEFT,
            command=self._open_admin_manage_users_panel,
            style=button_style,
        )
        btn_manage_users.grid(row=0, column=1, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)

        # Button 3: Add New User (Signup)
        btn_add_user = ttk.Button(
            button_container,
            text="Manage Projects",
            image=self.add_new_project_icon,
            compound=tk.LEFT,
            command=self._open_projects_panel,
            style=button_style,
        )
        btn_add_user.grid(row=1, column=0, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)

        # Button 4: System Settings
        btn_settings = ttk.Button(
            button_container,
            text="System Settings",
            image=self.settings_icon,
            compound=tk.LEFT,
            command=self._open_system_settings,
            style=button_style,
        )
        btn_settings.grid(row=1, column=1, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)
        
        # Button 5: View Activity Logs
        btn_logs = ttk.Button(
            button_container,
            text="View Activity Logs",
            image=self.logs_icon,
            compound=tk.LEFT,
            command=self._open_activity_logs,
            style=button_style,
        )
        btn_logs.grid(row=2, column=0, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)

        # Button 6: (payment)
        
        btn_payment_plans = ttk.Button(
            button_container,
            text="Manage Payment Plans",
            image=self.payment_icon,
            compound=tk.LEFT,
            command=self._open_manage_payment_plans,
            style=button_style,
        )
        btn_payment_plans.grid(row=2, column=1, padx=5, pady=5, ipadx=button_padding, ipady=button_padding, sticky=button_sticky)
    
    def _open_admin_manage_users_panel(self):
        """Opens the AdminPanel window."""
        if AdminManageUsersPanel:
            AdminManageUsersPanel(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon_for_button)
        else:
            messagebox.showerror("Error", "AdminPanel module is not available.")
    def _open_admin_manage_agents_panel(self):
        """Opens the AdminManageAgentsPanel window."""
        if AdminManageAgentsPanel:
            AdminManageAgentsPanel(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon_for_button)
        else:
            messagebox.showerror("Error", "AdminManageAgentsPanel module is not available.")

    def _open_projects_panel(self):
        """Opens the ProjectsPanel window."""
        # Pass the user_id to the new panel
        ProjectsPanel(self, self.db_manager, parent_icon_loader=self._load_icon_for_button, user_id=self.user_id)

    
    def _open_manage_payment_plans(self):
        if ManagePaymentPlansForm:
            ManagePaymentPlansForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon_for_button)
        else:
            messagebox.showerror("Error", "ManagePaymentPlansForm module is not available.")

    def _open_system_settings(self):  # NEW METHOD
        """Opens the SystemSettingsForm window."""
        SystemSettingsForm(self, self.db_manager, self.user_id, parent_icon_loader=self._load_icon)

    def _open_activity_logs(self):  # NEW METHOD
        """Opens the ActivityLogViewerForm window."""
        ActivityLogViewerForm(self, self.db_manager, parent_icon_loader=self._load_icon)

