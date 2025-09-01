import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')

# Assuming DatabaseManager is in 'database.py'
try:
    from database import DatabaseManager
except ImportError:
    messagebox.showerror("Import Error", "Could not import DatabaseManager. "
                                         "Please ensure 'database.py' is in the correct directory.")
    DatabaseManager = None


class SignupForm(tk.Toplevel):
    """
    A Toplevel window for user signup (admin or regular user).
    Allows new users to be registered in the database.
    """

    def __init__(self, parent, db_manager, parent_icon_loader=None, refresh_callback=None):
        """
        Initializes the SignupForm window.

        Args:
            parent: The parent Tkinter window (e.g., the main application window).
            db_manager: An instance of DatabaseManager for database interactions.
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader
        self.refresh_callback = refresh_callback

        # Variables for custom title bar dragging
        self._start_x = 0
        self._start_y = 0
        self.icons = {}

        # Set the window to have no native title bar and create a custom one
        self.overrideredirect(True)
        self._create_custom_title_bar()

        # Set the window size and center it on the screen
        window_width = 400
        window_height = 300
        self.geometry(self._center_window(window_width, window_height))

        # Set the custom icon for the window
        self._set_window_icon("add_user.png")
        
        # Create and place widgets
        self._create_widgets()

        # Grab focus and set the protocol after everything is configured
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar, bypassing the native one."""
        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text="Sign Up New User",
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

    def _center_window(self, width, height):
        """Calculates the coordinates to center the window on the screen."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        return f"{width}x{height}+{x}+{y}"

    def _set_window_icon(self, icon_name):
        """Sets the window icon from the assets directory."""
        png_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
                self.icon_photo_ref = photo
            except Exception as e:
                print(f"Error loading .png icon for SignupForm: {e}")
        else:
            print(f"Icon file not found: {png_path}")

    def _create_widgets(self):
        """Creates and places the widgets in the signup form."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Register New User", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # Username Label and Entry
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.username_entry.focus_set()

        # Password Label and Entry
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, sticky="ew", pady=5)

        # Role Label and Combobox
        ttk.Label(main_frame, text="Role:").grid(row=3, column=0, sticky="w", pady=5)
        self.role_combobox = ttk.Combobox(main_frame, values=["user", "admin", "accountant", "property_manager", "sales_agent"], state="readonly", width=27)
        self.role_combobox.grid(row=3, column=1, sticky="ew", pady=5)
        self.role_combobox.set("user")

        ttk.Label(main_frame, text="Agent status:").grid(row=4, column=0, sticky="w", pady=5)
        self.agent_combobox = ttk.Combobox(main_frame, values=["yes", "no"], state="readonly", width=27)
        self.agent_combobox.grid(row=4, column=1, sticky="ew", pady=5)
        self.agent_combobox.set("no")

        # Signup Button
        signup_button = ttk.Button(main_frame, text="Sign Up", command=self._signup_user)
        signup_button.grid(row=5, column=0, columnspan=2, pady=20)

        # Configure grid columns to expand
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=3)

    def _signup_user(self):
        """
        Handles the user signup process when the signup button is clicked.
        Validates input and calls the database manager to add the user.
        """
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_combobox.get().strip()
        is_agent = self.agent_combobox.get().strip()

        if not username or not password:
            messagebox.showwarning("Input Error", "Username and Password cannot be empty.", parent=self)
            return

        if not self.db_manager:
            messagebox.showerror("Database Error", "Database manager is not initialized.", parent=self)
            return

        try:
            # Check if the user already exists to provide a more specific error
            existing_user = self.db_manager.get_user_by_username(username)
            if existing_user:
                messagebox.showwarning("Signup Failed", f"User '{username}' already exists. Please choose a different username.", parent=self)
                return

            user_id = self.db_manager.add_user(username, password,is_agent,role)

            if user_id:
                messagebox.showinfo("Signup Successful",
                                     f"User '{username}' with role '{role}' registered successfully! User ID: {user_id}",
                                     parent=self)
                if self.refresh_callback:
                    self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Signup Failed", f"Could not register user '{username}'. An unexpected error occurred.", parent=self)
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during signup: {e}", parent=self)

