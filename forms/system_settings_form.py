import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
from datetime import datetime

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class SystemSettingsForm(tk.Toplevel):
    """
    A Toplevel window for managing application settings.
    Allows administrators to view, add, and update key-value settings.
    """

    def __init__(self, parent, db_manager, user_id, parent_icon_loader=None):
        """
        Initializes the SystemSettingsForm window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager for database interactions.
            user_id: The ID of the currently logged-in user.
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader

        self.title("System Settings")
        self.geometry("800x550")
        self.transient(parent)
        self.grab_set()

        self._set_window_icon()
        self.icons = {}  # To store PhotoImage references for buttons

        self._create_widgets()
        self.populate_settings_list()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_icon(self):
        """Sets the window icon, preferring .ico, then .png."""
        ico_path = os.path.join(ICONS_DIR, "settings.ico")
        png_path = os.path.join(ICONS_DIR, "settings.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception as e:
                print(f"Error loading .ico icon for SystemSettingsForm: {e}")

        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
                self.icon_photo_ref = photo
                return
            except Exception as e:
                print(f"Error loading .png icon for SystemSettingsForm: {e}")
        else:
            print("No valid icon file found for SystemSettingsForm (settings.ico or settings.png).")

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
                print(f"SystemSettingsForm: Fallback Error loading icon {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        return img

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Settings List (Treeview)
        settings_list_frame = ttk.LabelFrame(main_frame, text="Current Settings", padding="10")
        settings_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.settings_tree = ttk.Treeview(settings_list_frame, columns=("Name", "Value", "Description"),
                                          show="headings")
        self.settings_tree.heading("Name", text="Setting Name")
        self.settings_tree.heading("Value", text="Setting Value")
        self.settings_tree.heading("Description", text="Description")

        self.settings_tree.column("Name", width=150, stretch=tk.NO)
        self.settings_tree.column("Value", width=200)
        self.settings_tree.column("Description", width=300)

        self.settings_tree.pack(fill=tk.BOTH, expand=True)

        settings_tree_scrollbar = ttk.Scrollbar(settings_list_frame, orient="vertical",
                                                command=self.settings_tree.yview)
        settings_tree_scrollbar.pack(side="right", fill="y")
        self.settings_tree.configure(yscrollcommand=settings_tree_scrollbar.set)

        self.settings_tree.bind("<<TreeviewSelect>>", self._on_setting_select)

        # Setting Details and Actions
        details_frame = ttk.LabelFrame(main_frame, text="Edit Setting", padding="10")
        details_frame.pack(fill="x", pady=10)

        ttk.Label(details_frame, text="Setting Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.name_entry = ttk.Entry(details_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        ttk.Label(details_frame, text="Setting Value:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.value_entry = ttk.Entry(details_frame, width=40)
        self.value_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        ttk.Label(details_frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.description_entry = ttk.Entry(details_frame, width=40)
        self.description_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.save_icon = self._load_icon_for_button("save.png")
        self.clear_icon = self._load_icon_for_button("clear.png")

        self.save_button = ttk.Button(button_frame, text="Save Setting", command=self._save_setting,
                                      image=self.save_icon, compound=tk.LEFT)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(button_frame, text="Clear Fields", command=self._clear_fields,
                                       image=self.clear_icon, compound=tk.LEFT)
        self.clear_button.pack(side=tk.LEFT, padx=5)

    def populate_settings_list(self):
        for item in self.settings_tree.get_children():
            self.settings_tree.delete(item)

        settings = self.db_manager.get_all_settings()
        if settings:
            for setting in settings:
                self.settings_tree.insert("", tk.END, values=(setting['setting_name'], setting['setting_value'],
                                                              setting['description']))
        self._clear_fields()  # Clear fields after populating

    def _on_setting_select(self, event):
        selected_item = self.settings_tree.selection()
        if selected_item:
            values = self.settings_tree.item(selected_item, 'values')
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, values[0])
            self.name_entry.config(state='readonly')  # Prevent changing name of existing setting

            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, values[1])

            self.description_entry.delete(0, tk.END)
            self.description_entry.insert(0, values[2])
        else:
            self._clear_fields()

    def _save_setting(self):
        setting_name = self.name_entry.get().strip()
        setting_value = self.value_entry.get().strip()
        description = self.description_entry.get().strip()

        if not setting_name or not setting_value:
            messagebox.showwarning("Input Error", "Setting Name and Value are required.")
            return

        # Get current user's username for logging
        current_user = self.db_manager.get_user_by_id(self.user_id)
        username = current_user['username'] if current_user else "Unknown"

        if self.db_manager.set_setting(setting_name, setting_value, description, self.user_id, username):
            messagebox.showinfo("Success", f"Setting '{setting_name}' saved successfully.")
            self.populate_settings_list()
            self._clear_fields()
        else:
            messagebox.showerror("Error", f"Failed to save setting '{setting_name}'.")

    def _clear_fields(self):
        self.settings_tree.selection_remove(self.settings_tree.selection())
        self.name_entry.config(state='normal')  # Allow editing name for new entries
        self.name_entry.delete(0, tk.END)
        self.value_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)

    def _on_closing(self):
        """Handle the window close button (X)."""
        self.grab_release()
        self.destroy()

