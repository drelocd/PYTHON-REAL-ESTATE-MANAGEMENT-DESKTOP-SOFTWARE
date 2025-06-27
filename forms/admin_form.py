import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from PIL import Image, ImageTk  # Make sure PIL (Pillow) is installed: pip install Pillow
from datetime import datetime

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class AdminPanel(tk.Toplevel):
    """
    A Toplevel window for administrative controls, including user management
    and system settings.
    """

    def __init__(self, parent, db_manager, user_id, parent_icon_loader=None):
        """
        Initializes the AdminPanel window.

        Args:
            parent: The parent Tkinter window (e.g., the main application window).
            db_manager: An instance of DatabaseManager for database interactions.
            user_id: The ID of the currently logged-in user.
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader  # This is the _load_icon method from main.py

        self.title("Admin Panel")
        self.geometry("900x600")  # Set a default size for the admin panel
        self.transient(parent)  # Make it appear on top of the parent window
        self.grab_set()  # Make the admin panel modal

        # Set the window icon using the parent's icon loader
        # Use a more robust icon setting like in main.py
        self._set_window_icon()  # Call a new helper method

        # Store references to PhotoImage objects to prevent garbage collection
        self.icons = {}

        self._create_widgets()
        self.populate_user_list()
        self._show_initial_details()

        # Bind closing protocol
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_icon(self):
        """Sets the window icon, preferring .ico, then .png."""
        ico_path = os.path.join(ICONS_DIR, "admin_panel.ico")  # Prefer .ico
        png_path = os.path.join(ICONS_DIR, "admin_panel.png")  # Fallback to .png

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
                # Store the photo reference to prevent garbage collection
                self.icon_photo_ref = photo
                return
            except Exception as e:
                print(f"Error loading .png icon for AdminPanel: {e}")
        else:
            print("No valid icon file found for AdminPanel (admin_panel.ico or admin_panel.png).")

    def _load_icon_for_button(self, icon_name, size=(24, 24)):
        """
        Loads an icon using the parent's loader, or a fallback if not provided.
        Caches the PhotoImage to prevent garbage collection.
        """
        if self.parent_icon_loader:
            img = self.parent_icon_loader(icon_name, size=size)
        else:
            # Fallback if parent_icon_loader is not provided (e.g., during standalone testing)
            path = os.path.join(ICONS_DIR, icon_name)
            try:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Icon not found at {path}")
                original_img = Image.open(path)
                img = original_img.resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                # Store it in a local cache for this class
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
            except Exception as e:
                print(f"AdminPanel: Fallback Error loading icon {icon_name}: {e}")
                # Create a blank image for error
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        # If parent_icon_loader was used, it should have already cached it.
        return img

    def _create_widgets(self):
        # Create a PanedWindow to divide the layout
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Frame for User List
        left_frame = ttk.LabelFrame(self.paned_window, text="User Accounts", padding="10")
        self.paned_window.add(left_frame, weight=1)

        # Right Frame for User Details/Actions
        right_frame = ttk.LabelFrame(self.paned_window, text="User Details", padding="10")
        self.paned_window.add(right_frame, weight=2)

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

        self.add_button = ttk.Button(button_frame, text="Add New User", command=self._add_user,
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

        self._show_initial_details()  # Clear or show first item details after repopulating

    def _show_initial_details(self):
        # Clear fields or populate with the first user if available
        self.user_id_entry.config(state='normal')
        self.user_id_entry.delete(0, tk.END)
        self.user_id_entry.config(state='readonly')
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_combobox.set('')

        first_item = self.user_tree.get_children()[0] if self.user_tree.get_children() else None
        if first_item:
            self.user_tree.selection_set(first_item)
            self._on_user_select(None)  # Manually call to populate details

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

            self.password_entry.delete(0, tk.END)  # Clear password field on select

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

        # Prevent current logged-in admin from changing their own role to non-admin
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

        # Prevent admin from deleting themselves
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

    def _on_closing(self):
        """Handle the window close button (X)."""
        self.grab_release()  # Release the grab
        self.destroy()  # Close the admin panel window


""" if __name__ == '__main__':
    # This block is for testing the AdminPanel independently
    # You would typically run main.py and open it from there.
    from database import DatabaseManager


    class MockApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Mock Main App")
            self.geometry("400x300")
            self.db_manager = DatabaseManager()
            self.user_id = 1  # Mock user ID (assuming admin for testing)
            self.label = ttk.Label(self, text="This is a mock main application window.")
            self.label.pack(pady=20)
            self.admin_button = ttk.Button(self, text="Open Admin Panel", command=self.open_admin)
            self.admin_button.pack(pady=10)

            # Ensure a mock admin user exists for testing
            if not self.db_manager.authenticate_user("test_admin", "password123"):
                self.db_manager.add_user("test_admin", "password123", "admin")
            if not self.db_manager.authenticate_user("test_user", "password123"):
                self.db_manager.add_user("test_user", "password123", "user")

        def open_admin(self):
            # Pass self._load_icon from the MockApp if it were properly defined
            # For this simple test, we'll pass a dummy or directly the function
            admin_panel = AdminPanel(self, self.db_manager, self.user_id, parent_icon_loader=self._mock_load_icon)
            admin_panel.wait_window()

        def _mock_load_icon(self, icon_name, size=(40, 40)):
            # Dummy icon loader for testing purposes
            # In a real app, this would load actual icons
            path = os.path.join(ICONS_DIR, icon_name)
            try:
                if not os.path.exists(path):
                    # Create a dummy image if the actual icon is not found for testing
                    img = Image.new('RGB', size, color='blue')
                    tk_img = ImageTk.PhotoImage(img)
                    print(f"Mock loading dummy icon for {icon_name}")
                    return tk_img

                original_img = Image.open(path)
                resized_img = original_img.resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(resized_img)
                return tk_img
            except Exception as e:
                print(f"Mock icon loading error for {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                return ImageTk.PhotoImage(img)


    app = MockApp()
    app.mainloop() """