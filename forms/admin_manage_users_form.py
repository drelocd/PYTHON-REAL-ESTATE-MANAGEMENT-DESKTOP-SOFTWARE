import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from PIL import Image, ImageTk
# Assuming signup_form.py exists and is in the 'forms' directory
from forms.signup_form import SignupForm 

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class AdminManageUsersPanel(tk.Toplevel):
    """
    A Toplevel window for administrative controls, including user management
    and system settings.
    """

    def __init__(self, parent, db_manager, user_id, parent_icon_loader=None, window_icon_name="add_survey.png"):
        """
        Initializes the AdminPanel window.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader

        # Set initial window properties
        self.title("Admin Panel- Manage Users")
        self.geometry("1200x700")  # Set window size
        self.transient(parent)
        self.grab_set()

        # Variables for custom title bar dragging
        self._start_x = 0
        self._start_y = 0

        # Store references to PhotoImage objects to prevent garbage collection
        self.icons = {}

        # Set the window icon first, as the custom title bar might hide it
        self._set_window_icon(window_icon_name)
        
        # Use the robust title bar customization logic
        self._customize_title_bar()

        self._create_widgets()
        self.populate_user_list()
        self._show_initial_details()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _customize_title_bar(self):
        """
        Customizes the title bar appearance. Attempts Windows-specific
        customization, falls back to a custom Tkinter title bar.
        """
        try:
            # Windows-specific title bar customization using win32/ctypes
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                # These are Windows-specific constants for DWM
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Blue background color: 0x00RRGGBB -> 0x00BBGGRR
                # For blue: #004080 (R=00, G=40, B=80). In BBGGRR this is #804000
                color = c_int(0x00804000)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # White text color
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
                self.title("Admin Panel-Manage Users")
            else:
                # Fallback to custom Tkinter title bar for other OS
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
            text="Admin Panel-Manage Users",
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

    def _set_window_icon(self, icon_name):
        """Sets the window icon, preferring .ico, then .png."""
        ico_path = os.path.join(ICONS_DIR, "admin_panel.ico")
        png_path = os.path.join(ICONS_DIR, "admin_panel.png")

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

    def _open_signup_form(self):
        """Opens the SignupForm to add a new user."""
        try:
            signup_form = SignupForm(
                parent=self,
                db_manager=self.db_manager,
                refresh_callback=self.populate_user_list
            )
            signup_form.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open signup form: {e}")

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
                print(f"AdminPanel: Fallback Error loading icon {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        return img

    def _create_widgets(self):
        """Creates the main content widgets, now packed below the custom title bar."""
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Frame for User List
        left_frame = ttk.LabelFrame(self.paned_window, text="User Accounts", padding="10")
        self.paned_window.add(left_frame, weight=2)

        # Right Frame for User Details/Actions
        right_frame = ttk.LabelFrame(self.paned_window, text="User Details", padding="10")
        self.paned_window.add(right_frame, weight=1)

        # --- User List (Left Frame) ---
        self.user_tree = ttk.Treeview(left_frame, columns=("ID", "Username", "Role"), show="headings")
        self.user_tree.heading("ID", text="ID", anchor=tk.W)
        self.user_tree.heading("Username", text="Username", anchor=tk.W)
        self.user_tree.heading("Role", text="Role", anchor=tk.W)

        self.user_tree.column("ID", width=50, stretch=tk.NO)
        self.user_tree.column("Username", width=150)
        self.user_tree.column("Role", width=100)

        self.user_tree.pack(fill=tk.BOTH, expand=True)

        user_tree_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.user_tree.yview)
        user_tree_scrollbar.pack(side="right", fill="y")
        self.user_tree.configure(yscrollcommand=user_tree_scrollbar.set)

        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        # --- User Details (Right Frame) ---
        details_frame = ttk.Frame(right_frame)
        details_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(details_frame, text="User ID:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=5)
        self.user_id_entry = ttk.Entry(details_frame, state='readonly', width=30)
        self.user_id_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(details_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.username_entry = ttk.Entry(details_frame, width=30)
        self.username_entry.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(details_frame, text="Password (leave blank if no change):").grid(row=2, column=0, sticky=tk.W, pady=2,
                                                                               padx=5)
        self.password_entry = ttk.Entry(details_frame, show="*", width=30)
        self.password_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(details_frame, text="Role:").grid(row=3, column=0, sticky=tk.W, pady=2, padx=5)
        self.role_combobox = ttk.Combobox(details_frame, values=["user", "admin"], state="readonly", width=27)
        self.role_combobox.grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=20)

        # Store button icons as attributes of the instance to prevent garbage collection
        self.add_icon = self._load_icon_for_button("add_user.png")
        self.update_icon = self._load_icon_for_button("update_user.png")
        self.delete_icon = self._load_icon_for_button("delete_user.png")

        self.add_button = ttk.Button(button_frame, text="Add New User", command=self._open_signup_form,
                                     image=self.add_icon, compound=tk.LEFT)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.update_button = ttk.Button(button_frame, text="Update User", command=self._update_user,
                                        image=self.update_icon, compound=tk.LEFT)
        self.update_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(button_frame, text="Delete User", command=self._delete_user,
                                        image=self.delete_icon, compound=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def populate_user_list(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)

        users = self.db_manager.get_all_users()
        if users:
            for user in users:
                self.user_tree.insert("", tk.END, values=(user['user_id'], user['username'], user['role']))

        self._show_initial_details()

    def _show_initial_details(self):
        self.user_id_entry.config(state='normal')
        self.user_id_entry.delete(0, tk.END)
        self.user_id_entry.config(state='readonly')
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_combobox.set('')

        first_item = self.user_tree.get_children()[0] if self.user_tree.get_children() else None
        if first_item:
            self.user_tree.selection_set(first_item)
            self._on_user_select(None)

    def _on_user_select(self, event):
        selected_item = self.user_tree.selection()
        if selected_item:
            values = self.user_tree.item(selected_item, 'values')
            self.user_id_entry.config(state='normal')
            self.user_id_entry.delete(0, tk.END)
            self.user_id_entry.insert(0, values[0])
            self.user_id_entry.config(state='readonly')

            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, values[1])

            self.password_entry.delete(0, tk.END)

            self.role_combobox.set(values[2])
        else:
            self.user_id_entry.config(state='normal')
            self.user_id_entry.delete(0, tk.END)
            self.user_id_entry.config(state='readonly')
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            self.role_combobox.set('')

    def _add_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_combobox.get()

        if not username or not password or not role:
            messagebox.showwarning("Input Error", "Username, Password, and Role are required to add a new user.")
            return

        if self.db_manager.add_user(username, password, role):
            messagebox.showinfo("Success", f"User '{username}' added successfully.")
            self.populate_user_list()
            self._clear_fields()
        else:
            messagebox.showerror("Error", "Failed to add user. Username might already exist.")

    def _update_user(self):
        user_id_str = self.user_id_entry.get()
        if not user_id_str:
            messagebox.showwarning("Selection Error", "Please select a user to update.")
            return

        user_id = int(user_id_str)
        new_username = self.username_entry.get().strip()
        new_password = self.password_entry.get().strip()
        new_role = self.role_combobox.get()

        if not new_username and not new_password and not new_role:
            messagebox.showwarning("Input Error", "Please enter new details to update.")
            return

        if user_id == self.user_id and new_role and new_role != 'admin':
            if messagebox.askyesno("Warning",
                                   "You are attempting to change your own role from admin. This might lock you out. Are you sure?"):
                pass
            else:
                return

        if self.db_manager.update_user(user_id, new_username, new_password if new_password else None, new_role):
            messagebox.showinfo("Success", f"User ID {user_id} updated successfully.")
            self.populate_user_list()
            self._clear_fields()
        else:
            messagebox.showerror("Error",
                                 "Failed to update user. Username might already exist or no changes were made.")

    def _delete_user(self):
        user_id_str = self.user_id_entry.get()
        if not user_id_str:
            messagebox.showwarning("Selection Error", "Please select a user to delete.")
            return

        user_id = int(user_id_str)
        username_to_delete = self.username_entry.get()

        if user_id == self.user_id:
            messagebox.showwarning("Deletion Error", "You cannot delete your own account while logged in.")
            return

        if messagebox.askyesno("Confirm Deletion",
                               f"Are you sure you want to delete user '{username_to_delete}' (ID: {user_id})? This action cannot be undone."):
            if self.db_manager.delete_user(user_id):
                messagebox.showinfo("Success", f"User '{username_to_delete}' deleted successfully.")
                self.populate_user_list()
                self._clear_fields()
            else:
                messagebox.showerror("Error", "Failed to delete user.")

    def _clear_fields(self):
        self.user_tree.selection_remove(self.user_tree.selection())
        self.user_id_entry.config(state='normal')
        self.user_id_entry.delete(0, tk.END)
        self.user_id_entry.config(state='readonly')
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_combobox.set('')