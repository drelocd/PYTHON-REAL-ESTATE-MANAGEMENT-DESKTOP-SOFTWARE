import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
from tkcalendar import DateEntry  # For date pickers
from datetime import datetime, timedelta

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class ActivityLogViewerForm(tk.Toplevel):
    """
    A Toplevel window for viewing system activity logs.
    Allows filtering by user, action type, and date range, and supports pagination.
    """

    def __init__(self, parent, db_manager, parent_icon_loader=None):
        """
        Initializes the ActivityLogViewerForm window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager for database interactions.
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader

        self.title("Activity Logs")
        self.geometry("1000x700")
        self.transient(parent)
        self.grab_set()

        self._set_window_icon()
        self.icons = {}  # To store PhotoImage references for buttons

        self.current_page = 1
        self.page_size = 20  # Number of logs per page
        self.total_logs = 0
        self.total_pages = 1

        self._create_widgets()
        self.load_logs()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_icon(self):
        """Sets the window icon, preferring .ico, then .png."""
        ico_path = os.path.join(ICONS_DIR, "activity_log.ico")
        png_path = os.path.join(ICONS_DIR, "activity_logs.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception as e:
                print(f"Error loading .ico icon for ActivityLogViewerForm: {e}")

        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
                self.icon_photo_ref = photo
                return
            except Exception as e:
                print(f"Error loading .png icon for ActivityLogViewerForm: {e}")
        else:
            print("No valid icon file found for ActivityLogViewerForm (activity_log.ico or activity_log.png).")

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
                print(f"ActivityLogViewerForm: Fallback Error loading icon {icon_name}: {e}")
                img = Image.new('RGB', size, color='red')
                tk_img = ImageTk.PhotoImage(img)
                if path not in self.icons:
                    self.icons[path] = tk_img
                return tk_img
        return img

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Filter Frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filter_frame.pack(fill="x", pady=10)

        # User Filter
        ttk.Label(filter_frame, text="User:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.user_filter_combobox = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.user_filter_combobox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self._populate_user_filter()

        # Action Type Filter
        ttk.Label(filter_frame, text="Action Type:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.action_type_filter_combobox = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.action_type_filter_combobox.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        self._populate_action_type_filter()

        # Date Range Filter
        ttk.Label(filter_frame, text="Start Date:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.start_date_entry = DateEntry(filter_frame, width=22, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(filter_frame, text="End Date:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.end_date_entry = DateEntry(filter_frame, width=22, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        self.apply_filter_icon = self._load_icon_for_button("filter.png")
        self.clear_filter_icon = self._load_icon_for_button("clear_filter.png")

        apply_filter_button = ttk.Button(filter_frame, text="Apply Filters", command=self._apply_filters,
                                         image=self.apply_filter_icon, compound=tk.LEFT)
        apply_filter_button.grid(row=0, column=4, padx=10, pady=5)

        clear_filter_button = ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters,
                                         image=self.clear_filter_icon, compound=tk.LEFT)
        clear_filter_button.grid(row=1, column=4, padx=10, pady=5)

        # Log List (Treeview)
        log_list_frame = ttk.LabelFrame(main_frame, text="Activity Log Entries", padding="10")
        log_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_tree = ttk.Treeview(log_list_frame, columns=("ID", "Timestamp", "User", "Action Type", "Details"),
                                     show="headings")
        self.log_tree.heading("ID", text="ID", anchor=tk.W)
        self.log_tree.heading("Timestamp", text="Timestamp", anchor=tk.W)
        self.log_tree.heading("User", text="User", anchor=tk.W)
        self.log_tree.heading("Action Type", text="Action Type", anchor=tk.W)
        self.log_tree.heading("Details", text="Details", anchor=tk.W)

        self.log_tree.column("ID", width=50, stretch=tk.NO)
        self.log_tree.column("Timestamp", width=150, stretch=tk.NO)
        self.log_tree.column("User", width=100)
        self.log_tree.column("Action Type", width=150)
        self.log_tree.column("Details", width=350)

        self.log_tree.pack(fill=tk.BOTH, expand=True)

        log_tree_scrollbar = ttk.Scrollbar(log_list_frame, orient="vertical", command=self.log_tree.yview)
        log_tree_scrollbar.pack(side="right", fill="y")
        self.log_tree.configure(yscrollcommand=log_tree_scrollbar.set)

        # Pagination Controls
        pagination_frame = ttk.Frame(main_frame)
        pagination_frame.pack(pady=10)

        self.prev_button = ttk.Button(pagination_frame, text="Previous", command=self._prev_page)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.page_info_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_info_label.pack(side=tk.LEFT, padx=10)

        self.next_button = ttk.Button(pagination_frame, text="Next", command=self._next_page)
        self.next_button.pack(side=tk.LEFT, padx=5)

    def _populate_user_filter(self):
        users = self.db_manager.get_all_users()
        user_names = ["All Users"] + [user['username'] for user in users]
        self.user_filter_combobox['values'] = user_names
        self.user_filter_combobox.set("All Users")

    def _populate_action_type_filter(self):
        # This list should ideally come from a distinct query on activity_logs table
        # For now, hardcode common action types, or make it dynamic if needed.
        action_types = [
            "All Actions",
            "USER_ADDED", "USER_UPDATED", "USER_DELETED", "USER_PASSWORD_UPDATED", "USER_ROLE_UPDATED",
            "PROPERTY_ADDED", "PROPERTY_UPDATED", "PROPERTY_DELETED", "PROPERTY_SOLD",
            "CLIENT_ADDED", "CLIENT_UPDATED", "CLIENT_DELETED",
            "TRANSACTION_UPDATED",
            "SURVEY_JOB_ADDED", "SURVEY_JOB_UPDATED", "SURVEY_JOB_DELETED", "SURVEY_RECEIPT_UPDATED",
            "SURVEY_ATTACHMENTS_UPDATED",
            "SETTING_ADDED", "SETTING_UPDATED"
        ]
        self.action_type_filter_combobox['values'] = action_types
        self.action_type_filter_combobox.set("All Actions")

    def load_logs(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        selected_user = self.user_filter_combobox.get()
        selected_action_type = self.action_type_filter_combobox.get()
        start_date = self.start_date_entry.get_date().strftime('%Y-%m-%d') if self.start_date_entry.get_date() else None
        end_date = self.end_date_entry.get_date().strftime('%Y-%m-%d') if self.end_date_entry.get_date() else None

        user_id_filter = None
        if selected_user != "All Users":
            user_data = self.db_manager.get_user_by_username(selected_user)
            if user_data:
                user_id_filter = user_data['user_id']

        action_type_filter = None
        if selected_action_type != "All Actions":
            action_type_filter = selected_action_type

        # Get total count for pagination
        self.total_logs = self.db_manager.get_total_activity_logs_count(
            user_id=user_id_filter,
            action_type=action_type_filter,
            start_date=start_date,
            end_date=end_date
        )
        self.total_pages = (self.total_logs + self.page_size - 1) // self.page_size
        if self.total_pages == 0:  # Handle case with no logs
            self.total_pages = 1

        # Ensure current_page is within valid bounds
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1

        offset = (self.current_page - 1) * self.page_size

        logs = self.db_manager.get_activity_logs(
            limit=self.page_size,
            offset=offset,
            user_id=user_id_filter,
            action_type=action_type_filter,
            start_date=start_date,
            end_date=end_date
        )

        if logs:
            for log in logs:
                self.log_tree.insert("", tk.END, values=(
                    log['log_id'],
                    log['timestamp'],
                    log['username'],
                    log['action_type'],
                    log['details']
                ))

        self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages} ({self.total_logs} logs)")
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")

    def _apply_filters(self):
        self.current_page = 1  # Reset to first page when applying filters
        self.load_logs()

    def _clear_filters(self):
        self.user_filter_combobox.set("All Users")
        self.action_type_filter_combobox.set("All Actions")
        self.start_date_entry.set_date(None)  # Clear date
        self.end_date_entry.set_date(None)  # Clear date
        self.current_page = 1
        self.load_logs()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_logs()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_logs()

    def _on_closing(self):
        """Handle the window close button (X)."""
        self.grab_release()
        self.destroy()


