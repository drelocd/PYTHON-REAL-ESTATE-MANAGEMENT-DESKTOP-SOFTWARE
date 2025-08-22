import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from PIL import Image, ImageTk
from forms.agents_signup_form import AgentSignupForm
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


class AdminManageAgentsPanel(tk.Toplevel):
    """
    A Toplevel window for managing real estate agents.
    """
    def __init__(self, parent, db_manager, user_id, parent_icon_loader=None,window_icon_name="add_survey.png"):
        """
        Initializes the AgentManagementPanel window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager.
            user_id: The ID of the currently logged-in user.
            username: The username of the currently logged-in user.
            parent_icon_loader: A callable from the parent to load icons consistently.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id  # Store the user_id
        self.parent_icon_loader = parent_icon_loader

        # Variables for custom title bar dragging
        # Set initial window properties
        self.title("Admin Panel- Manage Users")
        self.geometry("1200x700")  # Set window size
        self.transient(parent)
        self.grab_set()

        self._start_x = 0
        self._start_y = 0

        # Store references to PhotoImage objects to prevent garbage collection
        self.icons = {}
        self._set_window_icon(window_icon_name)

        # Set initial window properties
        
        self._customize_title_bar()

        # Create widgets and populate the list
        self._create_widgets()
        self.populate_agent_list()

        # Handle window focus and closing protocol
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_icon(self, icon_name):
        """Sets the window icon, preferring .ico, then .png."""
        ico_path = os.path.join(ICONS_DIR, "admin_panel.ico")
        png_path = os.path.join(ICONS_DIR, "manage_agents.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception as e:
                print(f"Error loading .ico icon for AdminPanel: {e}")

        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
                self.icon_photo_ref = photo
                return
            except Exception as e:
                print(f"Error loading .png icon for AdminPanel: {e}")
        else:
            print("No valid icon file found for AdminPanel (admin_panel.ico or admin_panel.png).")


    def _customize_title_bar(self):
        """
        Customizes the title bar appearance. Falls back to a custom Tkinter title bar
        if native customization fails.
        """
        try:
            # Windows-specific title bar customization using win32/ctypes (if available)
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00804000) # Blue background: #004080 in BBGGRR format
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
                text_color = c_int(0x00FFFFFF) # White text color
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
                self.title("Agent Management")
            else:
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize native title bar: {e}. Falling back to custom Tkinter title bar.")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar when native customization isn't available."""
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=40)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(
            title_bar,
            text="Agent Management",
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
        """Handles the window close button."""
        self.grab_release()
        self.destroy()

    def _load_icon_for_button(self, icon_name, size=(24, 24)):
        """
        Loads an icon using the parent's loader, or a fallback if not provided.
        Caches the PhotoImage to prevent garbage collection.
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
                print(f"AgentManagementPanel: Fallback Error loading icon {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        return img

    def _create_widgets(self):
        """Creates the main content widgets with a paned window layout."""
        # Main container using PanedWindow
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Frame for Agent List
        left_frame = ttk.LabelFrame(self.paned_window, text="Agents", padding="10")
        self.paned_window.add(left_frame, weight=2)

        # Right Frame for Agent Details/Actions
        right_frame = ttk.LabelFrame(self.paned_window, text="Agent Details", padding="10")
        self.paned_window.add(right_frame, weight=1)

        # --- Agent List (Left Frame) ---
        # Search bar
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_agents)
        
        # Treeview for displaying agents
        self.agent_tree = ttk.Treeview(left_frame, columns=("ID", "Name", "Status", "Added By", "Date Added"), show="headings")
        self.agent_tree.heading("ID", text="ID", anchor=tk.W)
        self.agent_tree.heading("Name", text="Name", anchor=tk.W)
        self.agent_tree.heading("Status", text="Status", anchor=tk.W)
        self.agent_tree.heading("Added By", text="Added By", anchor=tk.W)
        self.agent_tree.heading("Date Added", text="Date Added", anchor=tk.W)

        self.agent_tree.column("ID", width=50, stretch=tk.NO)
        self.agent_tree.column("Name", width=150)
        self.agent_tree.column("Status", width=100)
        self.agent_tree.column("Added By", width=100)
        self.agent_tree.column("Date Added", width=150)

        self.agent_tree.pack(fill=tk.BOTH, expand=True)

        agent_tree_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.agent_tree.yview)
        agent_tree_scrollbar.pack(side="right", fill="y")
        self.agent_tree.configure(yscrollcommand=agent_tree_scrollbar.set)

        self.agent_tree.bind("<<TreeviewSelect>>", self._on_agent_select)

        # --- Agent Details (Right Frame) ---
        details_frame = ttk.Frame(right_frame)
        details_frame.pack(pady=10, padx=10, fill="x")

        # Details Labels and Entries
        ttk.Label(details_frame, text="Agent ID:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=5)
        self.agent_id_entry = ttk.Entry(details_frame, state='readonly', width=30)
        self.agent_id_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(details_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.name_entry = ttk.Entry(details_frame, width=30)
        self.name_entry.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(details_frame, text="Status:").grid(row=2, column=0, sticky=tk.W, pady=2, padx=5)
        self.status_combobox = ttk.Combobox(details_frame, values=["active", "inactive"], state="readonly", width=27)
        self.status_combobox.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(details_frame, text="Added By:").grid(row=3, column=0, sticky=tk.W, pady=2, padx=5)
        self.added_by_entry = ttk.Entry(details_frame, state='readonly', width=30)
        self.added_by_entry.grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(details_frame, text="Date Added:").grid(row=4, column=0, sticky=tk.W, pady=2, padx=5)
        self.timestamp_entry = ttk.Entry(details_frame, state='readonly', width=30)
        self.timestamp_entry.grid(row=4, column=1, sticky=tk.W, pady=2, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=20)

        # Store button icons as attributes of the instance to prevent garbage collection
        self.add_icon = self._load_icon_for_button("add_user.png")
        self.update_icon = self._load_icon_for_button("update_agent.png")
        self.delete_icon = self._load_icon_for_button("delete_agent.png")

        self.add_button = ttk.Button(button_frame, text="Add New Agent", command=self._open_agent_signup_form,
                                     image=self.add_icon, compound=tk.LEFT)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.update_button = ttk.Button(button_frame, text="Update Agent", command=self._update_agent,
                                         image=self.update_icon, compound=tk.LEFT)
        self.update_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(button_frame, text="Delete Agent", command=self._delete_agent,
                                         image=self.delete_icon, compound=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def populate_agent_list(self):
        """Fetches all agents from the database and populates the Treeview."""
        # Clear existing items
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)

        # Get agents from the database
        agents = self.db_manager.get_all_agents()
        if agents:
            for agent in agents:
                self.agent_tree.insert("", tk.END, values=(
                    agent['agent_id'],
                    agent['name'],
                    agent['status'],
                    agent['added_by'],
                    agent['timestamp']
                ))
            # Select the first item by default
            first_item = self.agent_tree.get_children()[0]
            self.agent_tree.selection_set(first_item)
            self._on_agent_select(None)
        else:
            self._clear_fields()

    def _filter_agents(self, event):
        """Filters the Treeview based on the search entry's content."""
        search_term = self.search_entry.get().strip().lower()
        
        # Clear the treeview and re-populate with filtered data
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)
            
        agents = self.db_manager.get_all_agents()
        if agents:
            for agent in agents:
                # Check if the search term is in any of the values
                if any(search_term in str(value).lower() for value in agent.values()):
                    self.agent_tree.insert("", tk.END, values=(
                        agent['agent_id'],
                        agent['name'],
                        agent['status'],
                        agent['added_by'],
                        agent['timestamp']
                    ))
        # Clear details if selection is lost
        if not self.agent_tree.get_children():
            self._clear_fields()

    def _on_agent_select(self, event):
        """Handles agent selection in the Treeview and populates the details fields."""
        selected_item = self.agent_tree.selection()
        if selected_item:
            values = self.agent_tree.item(selected_item, 'values')
            
            # Enable and populate readonly fields
            self.agent_id_entry.config(state='normal')
            self.added_by_entry.config(state='normal')
            self.timestamp_entry.config(state='normal')

            self.agent_id_entry.delete(0, tk.END)
            self.agent_id_entry.insert(0, values[0])
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, values[1])
            self.status_combobox.set(values[2])
            self.added_by_entry.delete(0, tk.END)
            self.added_by_entry.insert(0, values[3])
            self.timestamp_entry.delete(0, tk.END)
            self.timestamp_entry.insert(0, values[4])

            # Set readonly fields back to readonly
            self.agent_id_entry.config(state='readonly')
            self.added_by_entry.config(state='readonly')
            self.timestamp_entry.config(state='readonly')
        else:
            self._clear_fields()

    def _open_agent_signup_form(self):
        """Opens the SignupForm to add a new user."""
        try:
            signup_form = AgentSignupForm(
                parent=self,
                db_manager=self.db_manager,
                user_id=self.user_id, # FIX: Pass the user_id to the AgentSignupForm
                refresh_callback=self.populate_agent_list
            )
            signup_form.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open signup form: {e}")

    def _update_agent(self):
        """Updates an existing agent's details."""
        agent_id_str = self.agent_id_entry.get()
        if not agent_id_str:
            messagebox.showwarning("Selection Error", "Please select an agent to update.")
            return

        agent_id = int(agent_id_str)
        new_name = self.name_entry.get().strip()
        new_status = self.status_combobox.get()

        if not new_name and not new_status:
            messagebox.showwarning("Input Error", "Please enter new details to update.")
            return
        
        # Check if the agent is the current user and warn if changing status to inactive
        is_current_user_an_agent = self.db_manager.check_if_user_is_agent(self.user_id)
        current_agent_data = self.db_manager.get_agent_by_user_id(self.user_id)
        if is_current_user_an_agent and current_agent_data and current_agent_data['agent_id'] == agent_id and new_status != 'active':
            if not messagebox.askyesno("Warning", "You are attempting to change your own agent status to inactive. This might prevent you from accessing agent-specific features. Are you sure?"):
                return

        if self.db_manager.update_agent(agent_id, new_name, new_status):
            messagebox.showinfo("Success", f"Agent ID {agent_id} updated successfully.")
            self.populate_agent_list()
            self._clear_fields()
            # If the current user's agent status was changed, we should reflect that in the parent window.
            # A reload or status check on the parent might be needed here, depending on its implementation.
        else:
            messagebox.showerror("Error", "Failed to update agent.")

    def _delete_agent(self):
        """Deletes a selected agent."""
        agent_id_str = self.agent_id_entry.get()
        if not agent_id_str:
            messagebox.showwarning("Selection Error", "Please select an agent to delete.")
            return

        agent_id = int(agent_id_str)
        name_to_delete = self.name_entry.get()

        # Added a check to prevent an admin from deleting their own agent account
        if self.db_manager.check_if_user_is_agent(self.user_id):
            current_agent_data = self.db_manager.get_agent_by_user_id(self.user_id)
            if current_agent_data and current_agent_data['agent_id'] == agent_id:
                messagebox.showwarning("Deletion Error", "You cannot delete your own agent account while logged in.")
                return

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete agent '{name_to_delete}' (ID: {agent_id})? This action cannot be undone."):
            if self.db_manager.delete_agent(agent_id):
                messagebox.showinfo("Success", f"Agent '{name_to_delete}' deleted successfully.")
                self.populate_agent_list()
                self._clear_fields()
            else:
                messagebox.showerror("Error", "Failed to delete agent.")

    def _clear_fields(self):
        """Clears all input and display fields on the right side."""
        self.agent_tree.selection_remove(self.agent_tree.selection())
        
        self.agent_id_entry.config(state='normal')
        self.agent_id_entry.delete(0, tk.END)
        self.agent_id_entry.config(state='readonly')
        
        self.name_entry.delete(0, tk.END)
        self.status_combobox.set('')
        
        self.added_by_entry.config(state='normal')
        self.added_by_entry.delete(0, tk.END)
        self.added_by_entry.config(state='readonly')
        
        self.timestamp_entry.config(state='normal')
        self.timestamp_entry.delete(0, tk.END)
        self.timestamp_entry.config(state='readonly')
