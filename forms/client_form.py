import tkinter as tk
from tkinter import ttk, messagebox
import os
import platform
from database import DatabaseManager
from PIL import Image, ImageTk, ImageDraw

try:
    from ctypes import windll, c_int, byref, sizeof

    HAS_CTYPES = True
except (ImportError, OSError):
    HAS_CTYPES = False

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class BaseForm(tk.Toplevel):
    """
    Base class for all forms with common functionality:
    - Custom title bar color on Windows
    - Custom icon
    - Centered positioning
    - Modal behavior
    """

    def __init__(self, parent, title, width, height, icon_name=None, icon_loader=None):
        """Initialize the base form with common properties."""
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry(f"{width}x{height}")

        # Prevent resizing but keep standard window buttons
        self.resizable(False, False)
        self.transient(parent)

        # Set window attributes for Windows
        if platform.system() == 'Windows' and HAS_CTYPES:
            self._customize_title_bar()

        # Center the window
        self._center_window(width, height)

        # Set custom icon if provided
        if icon_name and icon_loader:
            self._set_icon(icon_name, icon_loader)

        # Make window modal
        self.grab_set()
        self.focus_set()

        # Handle window closing
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _customize_title_bar(self):
        """Applies a custom color to the title bar on Windows systems."""
        try:
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            hwnd = windll.user32.GetParent(self.winfo_id())

            # Use the same blue color as your payment plan forms (0x00663300 - dark blue in BGR format)
            color = c_int(0x00663300)
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color)
            )

            # Set white text
            text_color = c_int(0x00FFFFFF)  # White in BGR
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color)
            )
        except Exception as e:
            print(f"Could not customize title bar: {e}")

    def _center_window(self, width, height):
        """Center the window on the screen."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"+{x}+{y}")

    def _set_icon(self, icon_name, icon_loader):
        """Set the window icon using the provided icon loader."""
        try:
            icon_image = icon_loader(icon_name, size=(32, 32))
            self.iconphoto(False, icon_image)
            self._window_icon_ref = icon_image
        except Exception as e:
            print(f"Failed to set icon for {self.title()}: {e}")

    def _on_closing(self):
        """Handle window closing."""
        self.grab_release()
        self.destroy()


class ClientForm(BaseForm):
    """
    A Toplevel window for managing client information and displaying their
    associated land purchases and survey jobs.
    """

    def __init__(self, parent, db_manager, user_id=None, user_type=None, parent_icon_loader=None):
        """
        Initializes the ClientForm window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager for database interactions.
            user_id: The ID of the currently logged-in user.
            parent_icon_loader: A callable to load icons from the parent app.
        """
        super().__init__(parent, "Land Sales Clients Management", 1300, 780, "client.png", parent_icon_loader)

        self.db_manager = db_manager
        self.user_id = user_id
        self.user_type = user_type
        self.parent_icon_loader = parent_icon_loader

        self._load_button_icons()
        self._create_widgets()
        self._load_clients()

    def _load_button_icons(self):
        """Load icons for buttons."""
        try:
            # Load add icon
            self.add_icon_img = self.parent_icon_loader("add.png", size=(16, 16))
            # Load update icon
            self.update_icon_img = self.parent_icon_loader("update.png", size=(16, 16))
            # Load delete icon
            self.delete_icon_img = self.parent_icon_loader("delete.png", size=(16, 16))
        except Exception as e:
            print(f"Failed to load button icons: {e}")
            self.add_icon_img = None
            self.update_icon_img = None
            self.delete_icon_img = None

    def _create_widgets(self):
        """Creates and packs all the widgets for the UI."""

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        # --- Top Pane: Search Bar & Add Button ---
        top_controls_frame = ttk.Frame(main_frame, padding="5")
        top_controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Search bar
        search_frame = ttk.Frame(top_controls_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_clients)

        # Add New Client Button
        self.add_client_button = ttk.Button(top_controls_frame, text="Add New Client",
                                            image=self.add_icon_img, compound=tk.LEFT,
                                            command=self._open_add_client_form)
        self.add_client_button.pack(side=tk.RIGHT, padx=(10, 0))

        # --- Paned Window for Client List and Associated Data ---
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill="both", expand=True, pady=1)
        paned_window.bind("<B1-Motion>", "break")

        # Top Pane: Client List View
        client_list_pane = ttk.Frame(paned_window)
        paned_window.add(client_list_pane, weight=1)

        # New frame to hold the Treeview and the buttons below it
        tree_and_buttons_frame = ttk.Frame(client_list_pane, padding="10")
        tree_and_buttons_frame.pack(fill="both", expand=True)

        list_frame = ttk.LabelFrame(tree_and_buttons_frame, text="Existing Clients")
        list_frame.pack(fill="both", expand=True, pady=(0, 5))

        self.tree = ttk.Treeview(list_frame, columns=("ID", "Name", "Telephone No", "Email", "Purpose", "Added by"),
                                 show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Client Name")
        self.tree.heading("Telephone No", text="Telephone No")
        self.tree.heading("Email", text="Email")
        self.tree.heading("Purpose", text="Purpose")
        self.tree.heading("Added by", text="Added by")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=150)
        self.tree.column("Telephone No", width=100)
        self.tree.column("Email", width=150)
        self.tree.column("Purpose", width=80)
        self.tree.column("Added by", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar for the Treeview
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_client_select)

        # --- Buttons below the table ---
        button_frame = ttk.Frame(tree_and_buttons_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        # Re-ordered and re-packed the buttons
        self.update_button = ttk.Button(button_frame, text="Update Selected Client",
                                        image=self.update_icon_img, compound=tk.LEFT,
                                        command=self._open_update_client_form, state="disabled")
        self.update_button.pack(side=tk.LEFT, padx=(0, 5))

        self.delete_button = ttk.Button(button_frame, text="Delete Selected Client",
                                        image=self.delete_icon_img, compound=tk.LEFT,
                                        command=self._delete_client, state="disabled")
        self.delete_button.pack(side=tk.RIGHT, padx=(5, 0))

        # --- Bottom Pane: Associated Activities ---
        bottom_pane = ttk.Frame(paned_window)
        paned_window.add(bottom_pane, weight=1)

        notebook_activities = ttk.Notebook(bottom_pane)
        notebook_activities.pack(fill="both", expand=True, padx=5, pady=5)

        # Land Purchases Tab
        land_frame = ttk.Frame(notebook_activities, padding="2")
        notebook_activities.add(land_frame, text="Associated Land Purchases")
        self.land_tree = ttk.Treeview(land_frame,
                                      columns=("Prop ID", "Title Deed", "Location", "Size", "Price", "Status",
                                               "Purchase Date"), show="headings")
        self.land_tree.heading("Prop ID", text="Property ID")
        self.land_tree.heading("Title Deed", text="Title Deed No.")
        self.land_tree.heading("Location", text="Location")
        self.land_tree.heading("Size", text="Size")
        self.land_tree.heading("Price", text="Price")
        self.land_tree.heading("Status", text="Status")
        self.land_tree.heading("Purchase Date", text="Purchase Date")
        self.land_tree.pack(fill="both", expand=True)

        # Survey Jobs Tab
        survey_frame = ttk.Frame(notebook_activities, padding="2")
        notebook_activities.add(survey_frame, text="Associated Survey Jobs")
        self.survey_tree = ttk.Treeview(survey_frame,
                                        columns=("Job ID", "File Name", "Description", "Status"), show="headings")
        self.survey_tree.heading("Job ID", text="Job ID")
        self.survey_tree.heading("File Name", text="File Name")
        self.survey_tree.heading("Description", text="Description")
        self.survey_tree.heading("Status", text="Status")
        self.survey_tree.pack(fill="both", expand=True)

    def _load_clients(self):
        """Clears and re-populates the client Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        clients = self.db_manager.get_all_clients()
        if clients:
            for client in clients:
                self.tree.insert("", "end", values=(client['client_id'], client['name'], client['telephone_number'],
                                                    client['email'], client['purpose'], client['added_by_username']))
        self._clear_associated_data()

    def _filter_clients(self, event):
        """Filters the client list in real-time based on search input."""
        search_term = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        clients = self.db_manager.get_all_clients()

        if clients:
            for client in clients:
                client_id, name, telephone, email, purpose, user_id = client['client_id'], client['name'], client[
                    'telephone_number'], client['email'], client['purpose'], client['added_by_username']
                if search_term in str(
                        client_id).lower() or search_term in name.lower() or search_term in telephone.lower() or search_term in email.lower() or search_term in purpose.lower() or search_term in user_id.lower():
                    self.tree.insert("", "end", values=(client_id, name, telephone, email, purpose, user_id))

    def _open_add_client_form(self):
        """Opens a new modal window for adding a client."""
        AddClientForm(self, self.db_manager, self.user_id, self.refresh_view, self.parent_icon_loader)

    def _open_update_client_form(self):
        """Opens a new modal window for updating a client."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a client to update.")
            return

        values = self.tree.item(selected_item, "values")
        client_data = {
            'client_id': values[0],
            'name': values[1],
            'telephone_number': values[2],
            'email': values[3],
            'purpose': values[4]
        }
        UpdateClientForm(self, self.db_manager, self.user_id, client_data, self.refresh_view, self.parent_icon_loader)

    def refresh_view(self):
        """Refreshes the client list and clears selections."""
        self._load_clients()
        self.tree.selection_remove(self.tree.focus())
        self.update_button.config(state="disabled")
        self.delete_button.config(state="disabled")

    def _delete_client(self):
        """Deletes a selected client after confirmation."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a client from the list to delete.")
            return

        client_id = self.tree.item(selected_item, "values")[0]
        client_name = self.tree.item(selected_item, "values")[1]

        confirm_msg = (
            f"Are you sure you want to delete client '{client_name}' (ID: {client_id})?\n\n"
        )
        if messagebox.askyesno("Confirm Delete", confirm_msg):
            try:
                deleted = self.db_manager.delete_client(client_id)
                if deleted:
                    messagebox.showinfo("Success", f"Client '{client_name}' deleted successfully.")
                    self.refresh_view()
                else:
                    messagebox.showerror("Error", "Failed to delete client. Client not found.")
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred during deletion: {e}")
        self.refresh_view()

    def _on_client_select(self, event):
        """Handles a client selection from the Treeview."""
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, "values")
            client_id = values[0]
            self.update_button.config(state="normal")
            self.delete_button.config(state="normal")
            self._load_associated_data(client_id)
        else:
            self.update_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self._clear_associated_data()

    def _clear_associated_data(self):
        """Clears the associated data Treeviews."""
        for item in self.land_tree.get_children():
            self.land_tree.delete(item)
        for item in self.survey_tree.get_children():
            self.survey_tree.delete(item)

    def _load_associated_data(self, client_id):
        """Loads and populates associated data for a given client ID."""
        self._clear_associated_data()
        properties = self.db_manager.get_client_properties(client_id)
        if properties:
            for prop in properties:
                self.land_tree.insert("", "end",
                                      values=(prop['property_id'], prop['title_deed_number'], prop['location'],
                                              prop['size'], prop['price'], prop['status'], prop['transaction_date']))

        survey_jobs = self.db_manager.get_client_survey_jobs(client_id)
        # Note: This code assumes the get_client_survey_jobs method now returns
        # dictionaries with 'job_id', 'file_name', 'description', and 'status' keys.
        if survey_jobs:
            for job in survey_jobs:
                self.survey_tree.insert("", "end",
                                        values=(job['job_id'], job['file_name'], job['description'],
                                                job['status']))


class AddClientForm(BaseForm):
    """A modal form for adding a new client."""

    def __init__(self, parent, db_manager, user_id, refresh_callback, icon_loader):
        super().__init__(parent, "Add New Client", 400, 300, "client.png", icon_loader)

        self.db_manager = db_manager
        self.user_id = user_id
        self.refresh_callback = refresh_callback

        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.Frame(self, padding="15")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Client Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ttk.Entry(frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Telephone Number:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tel_entry = ttk.Entry(frame, width=30)
        self.tel_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.email_entry = ttk.Entry(frame, width=30)
        self.email_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Purpose:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.purpose_var = tk.StringVar(self)
        self.purpose_var.set("N/A")  # default value
        purpose_options = ["Survey", "Land Sales", "N/A"]
        self.purpose_menu = ttk.Combobox(frame, textvariable=self.purpose_var, values=purpose_options, state="readonly")
        self.purpose_menu.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        # New "Brought By" input field
        ttk.Label(frame, text="Brought By:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.brought_by_var = tk.StringVar(self)
        self.brought_by_combobox = ttk.Combobox(frame, textvariable=self.brought_by_var, values=["Self"])
        self.brought_by_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.save_button = ttk.Button(button_frame, text="Save Client", command=self._save_client)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

    def _save_client(self):
        name = self.name_entry.get().strip()
        telephone = self.tel_entry.get().strip()
        email = self.email_entry.get().strip()
        purpose = self.purpose_var.get()
        brought_by = self.brought_by_combobox.get().strip() # Get the new value
        status = 'active'  # Default status for new clients

        if not name or not telephone or not email:
            messagebox.showerror("Input Error", "All fields are required.")
            return
        
        if not telephone.isdigit():
            messagebox.showerror("Validation Error", "Telephone number must be numeric.")
            return

        if "@" not in email or "." not in email:
            messagebox.showerror("Validation Error", "Please enter a valid email address.")
            return

        try:
            # Pass the new 'brought_by' value to the database manager
            client_id = self.db_manager.add_client(name, telephone, email, purpose, status, brought_by, self.user_id)
            if client_id:
                messagebox.showinfo("Success", f"Client '{name}' added successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to add client. Contact info may already exist.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")




class UpdateClientForm(BaseForm):
    """A modal form for updating an existing client."""

    def __init__(self, parent, db_manager, user_id, client_data, refresh_callback, icon_loader):
        super().__init__(parent, "Update Client", 400, 250, "client.png", icon_loader)

        self.db_manager = db_manager
        self.user_id = user_id
        self.client_data = client_data
        self.refresh_callback = refresh_callback

        self._create_widgets()
        self._load_data()

    def _create_widgets(self):
        frame = ttk.Frame(self, padding="15")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Client Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ttk.Entry(frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Telephone Number:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tel_entry = ttk.Entry(frame, width=30)
        self.tel_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.email_entry = ttk.Entry(frame, width=30)
        self.email_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="Purpose:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.purpose_var = tk.StringVar(self)
        purpose_options = ["Survey", "Land Sales", "N/A"]
        self.purpose_menu = ttk.Combobox(frame, textvariable=self.purpose_var, values=purpose_options, state="readonly")
        self.purpose_menu.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.save_button = ttk.Button(button_frame, text="Save Changes", command=self._save_changes)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

    def _load_data(self):
        self.name_entry.insert(0, self.client_data['name'])
        self.tel_entry.insert(0, self.client_data['telephone_number'])
        self.email_entry.insert(0, self.client_data['email'])
        self.purpose_var.set(self.client_data['purpose'])

    def _save_changes(self):
        new_name = self.name_entry.get().strip()
        new_tel = self.tel_entry.get().strip()
        new_email = self.email_entry.get().strip()
        new_purpose = self.purpose_var.get()
        client_id = self.client_data['client_id']

        if not new_name or not new_tel or not new_email:
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            current_client = self.db_manager.get_client(client_id)
            if current_client and (
                    current_client['telephone_number'] != new_tel or current_client['email'] != new_email):
                existing_client_by_contact = self.db_manager.get_client_by_telephone_number(new_tel, new_email)
                if existing_client_by_contact and existing_client_by_contact['client_id'] != client_id:
                    messagebox.showerror("Update Error", "Another client already uses this contact information.")
                    return

            updated = self.db_manager.update_client(client_id, name=new_name, telephone_number=new_tel, email=new_email,
                                                    purpose=new_purpose)
            if updated:
                messagebox.showinfo("Success", f"Client ID {client_id} updated successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to update client. No changes or client not found.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during update: {e}")
