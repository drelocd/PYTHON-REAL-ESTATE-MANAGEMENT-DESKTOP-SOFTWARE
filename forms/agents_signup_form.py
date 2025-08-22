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


class AgentSignupForm(tk.Toplevel):
    """
    A Toplevel window for new agent registration.
    Allows new agents to be registered in the 'agents' table.
    """

    def __init__(self, parent, db_manager, user_id=None, parent_icon_loader=None, refresh_callback=None):
        """
        Initializes the AgentSignupForm window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager for database interactions.
            user_id (str): The ID of the user who is creating this agent.
            parent_icon_loader: A callable to load icons.
            refresh_callback: A function to call after a successful signup.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        # The added_by_user_id is now the original user ID, which we'll use to look up the name.
        self.added_by_user_id = user_id 
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
        window_height = 200  # Adjusted height for the simpler form
        self.geometry(self._center_window(window_width, window_height))

        # Set the custom icon for the window
        # Note: You may want to use a different icon specific to agents.
        self._set_window_icon("add_survey.png")
        
        # Create and place widgets
        self._create_widgets()

        # Grab focus and set the protocol after everything is configured
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar, bypassing the native one."""
        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Updated title text
        title_label = tk.Label(
            title_bar,
            text="Sign Up New Agent",
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
        """Creates and places the widgets in the agent signup form."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Register New Agent", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # Agent Name Label and Entry (replaces username, password, and role)
        ttk.Label(main_frame, text="Agent Name:").grid(row=1, column=0, sticky="w", pady=5)
        self.agent_name_entry = ttk.Entry(main_frame, width=30)
        self.agent_name_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.agent_name_entry.focus_set()

        # Signup Button
        signup_button = ttk.Button(main_frame, text="Add Agent", command=self._signup_agent)
        signup_button.grid(row=2, column=0, columnspan=2, pady=20)

        # Configure grid columns to expand
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=3)

    def _signup_agent(self):
        """
        Handles the agent signup process when the add agent button is clicked.
        Validates input and calls the database manager to add the agent.
        """
        agent_name = self.agent_name_entry.get().strip()

        if not agent_name:
            messagebox.showwarning("Input Error", "Agent Name cannot be empty.", parent=self)
            return

        if not self.db_manager:
            messagebox.showerror("Database Error", "Database manager is not initialized.", parent=self)
            return

        # Check if the agent already exists
        existing_agent = self.db_manager.get_agent_by_name(agent_name)
        if existing_agent:
            messagebox.showwarning("Signup Failed", f"Agent '{agent_name}' already exists. Please choose a different name.", parent=self)
            return

        # Now, get the username from the user ID before adding the agent
        added_by_username = self.db_manager.get_username_by_id(self.added_by_user_id)

        if not added_by_username:
            messagebox.showerror("Error", "Could not find the username for the current user.", parent=self)
            return

        # Call the correct database function for adding an agent, passing the username
        try:
            success = self.db_manager.add_agent(agent_name, added_by_username)

            if success:
                messagebox.showinfo("Success",
                                     f"Agent '{agent_name}' registered successfully!",
                                     parent=self)
                if self.refresh_callback:
                    self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Signup Failed", f"Could not register agent '{agent_name}'. An unexpected error occurred.", parent=self)
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during agent signup: {e}", parent=self)
