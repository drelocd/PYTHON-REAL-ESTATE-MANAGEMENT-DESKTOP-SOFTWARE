import tkinter as tk
from tkinter import ttk, messagebox
import os
from database import DatabaseManager  # Assuming database.py is in the same directory
from PIL import Image, ImageTk  # Required for loading images, even if for dummy icons

# Define paths relative to the project root for icon loading (if needed, simplified for this example)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')


class ClientForm(tk.Toplevel):
    """
    A Toplevel window for managing client information (Add, Update, View)
    and displaying their associated land purchases and survey jobs.
    """

    def __init__(self, parent, db_manager, user_id=None, parent_icon_loader=None):
        """
        Initializes the ClientForm window.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of DatabaseManager for database interactions.
            user_id: The ID of the currently logged-in user (optional, for 'added_by_user_id').
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader  # For consistent icon loading

        self.title("Client Management & Activity Overview")
        self.geometry("1000x800")  # Increased size to accommodate new sections
        self.resizable(True, True)

        self._create_widgets()
        self._load_clients()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill="both", expand=True, pady=10)

        # --- Top Pane: Client Details & List ---
        top_pane = ttk.Frame(paned_window)
        paned_window.add(top_pane, weight=1)

        # Input Frame for Adding/Updating Clients
        input_frame = ttk.LabelFrame(top_pane, text="Client Details", padding="15")
        input_frame.pack(fill="x", pady=10)

        ttk.Label(input_frame, text="Client Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.client_name_entry = ttk.Entry(input_frame, width=40)
        self.client_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Contact Info (Email/Phone):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.contact_info_entry = ttk.Entry(input_frame, width=40)
        self.contact_info_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Buttons for actions
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.add_button = ttk.Button(button_frame, text="Add New Client", command=self._add_client)
        self.add_button.pack(side="left", padx=5)

        self.update_button = ttk.Button(button_frame, text="Update Selected Client", command=self._update_client)
        self.update_button.pack(side="left", padx=5)
        self.update_button.config(state="disabled")

        self.clear_button = ttk.Button(button_frame, text="Clear Form", command=self._clear_form)
        self.clear_button.pack(side="left", padx=5)

        # Keep this single definition of the delete button
        self.delete_button = ttk.Button(button_frame, text="Delete Selected Client", command=self._delete_client)
        self.delete_button.pack(side="right", padx=5)
        self.delete_button.config(state="disabled")

        # Client List View
        list_frame = ttk.LabelFrame(top_pane, text="Existing Clients", padding="10")
        list_frame.pack(fill="both", expand=True, pady=10)

        self.tree = ttk.Treeview(list_frame, columns=("ID", "Name", "Contact Info", "Added By User"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Client Name")
        self.tree.heading("Contact Info", text="Contact Info")
        self.tree.heading("Added By User", text="Added By User ID")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.column("Contact Info", width=250)
        self.tree.column("Added By User", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_client_select)

        # Scrollbar for the Treeview
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Bottom Pane: Associated Activities ---
        bottom_pane = ttk.Frame(paned_window)
        paned_window.add(bottom_pane, weight=1)

        notebook_activities = ttk.Notebook(bottom_pane)
        notebook_activities.pack(fill="both", expand=True, padx=5, pady=5)

        # Land Purchases Tab
        land_frame = ttk.Frame(notebook_activities, padding="10")
        notebook_activities.add(land_frame, text="   Associated Land Purchases   ")

        self.land_tree = ttk.Treeview(land_frame, columns=(
        "Prop ID", "Title Deed", "Location", "Size", "Price", "Status", "Purchase Date"), show="headings")
        self.land_tree.heading("Prop ID", text="Property ID")
        self.land_tree.heading("Title Deed", text="Title Deed No.")
        self.land_tree.heading("Location", text="Location")
        self.land_tree.heading("Size", text="Size")
        self.land_tree.heading("Price", text="Price")
        self.land_tree.heading("Status", text="Status")
        self.land_tree.heading("Purchase Date", text="Purchase Date")

        self.land_tree.column("Prop ID", width=70, anchor="center")
        self.land_tree.column("Title Deed", width=120)
        self.land_tree.column("Location", width=120)
        self.land_tree.column("Size", width=80)
        self.land_tree.column("Price", width=100)
        self.land_tree.column("Status", width=80)
        self.land_tree.column("Purchase Date", width=100)

        self.land_tree.pack(fill="both", expand=True)
        land_scrollbar = ttk.Scrollbar(land_frame, orient="vertical", command=self.land_tree.yview)
        self.land_tree.configure(yscrollcommand=land_scrollbar.set)
        land_scrollbar.pack(side="right", fill="y")

        # Survey Jobs Tab
        survey_frame = ttk.Frame(notebook_activities, padding="10")
        notebook_activities.add(survey_frame, text="   Associated Survey Jobs   ")

        self.survey_tree = ttk.Treeview(survey_frame, columns=(
        "Job ID", "Location", "Job Type", "Fee", "Status", "Deadline", "Created At"), show="headings")
        self.survey_tree.heading("Job ID", text="Job ID")
        self.survey_tree.heading("Location", text="Location")
        self.survey_tree.heading("Job Type", text="Job Type")
        self.survey_tree.heading("Fee", text="Fee")
        self.survey_tree.heading("Status", text="Status")
        self.survey_tree.heading("Deadline", text="Deadline")
        self.survey_tree.heading("Created At", text="Created At")

        self.survey_tree.column("Job ID", width=70, anchor="center")
        self.survey_tree.column("Location", width=120)
        self.survey_tree.column("Job Type", width=100)
        self.survey_tree.column("Fee", width=80)
        self.survey_tree.column("Status", width=80)
        self.survey_tree.column("Deadline", width=100)
        self.survey_tree.column("Created At", width=100)

        self.survey_tree.pack(fill="both", expand=True)
        survey_scrollbar = ttk.Scrollbar(survey_frame, orient="vertical", command=self.survey_tree.yview)
        self.survey_tree.configure(yscrollcommand=survey_scrollbar.set)
        survey_scrollbar.pack(side="right", fill="y")

    def _load_clients(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        clients = self.db_manager.get_all_clients()
        if clients:
            for client in clients:
                self.tree.insert("", "end", values=(
                client['client_id'], client['name'], client['contact_info'], client['added_by_username']))
        self._clear_associated_data()  # Clear associated data when loading all clients

    def _add_client(self):
        name = self.client_name_entry.get().strip()
        contact_info = self.contact_info_entry.get().strip()

        if not name or not contact_info:
            messagebox.showerror("Input Error", "Client Name and Contact Info cannot be empty.")
            return

        try:
            client_id = self.db_manager.add_client(name, contact_info, self.user_id)
            if client_id:
                messagebox.showinfo("Success", f"Client '{name}' added successfully with ID: {client_id}")
                self._clear_form()
                self._load_clients()
            else:
                messagebox.showerror("Error", "Failed to add client. Contact info might already exist.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def _update_client(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a client from the list to update.")
            return

        client_id = self.tree.item(selected_item, "values")[0]
        new_name = self.client_name_entry.get().strip()
        new_contact_info = self.contact_info_entry.get().strip()

        if not new_name or not new_contact_info:
            messagebox.showerror("Input Error", "Client Name and Contact Info cannot be empty for update.")
            return

        try:
            # Check if contact info is unique if it's being changed
            current_client = self.db_manager.get_client(client_id)
            if current_client and current_client['contact_info'] != new_contact_info:
                existing_client_by_contact = self.db_manager.get_client_by_contact_info(new_contact_info)
                if existing_client_by_contact and existing_client_by_contact['client_id'] != client_id:
                    messagebox.showerror("Update Error", "Another client already uses this contact information.")
                    return

            updated = self.db_manager.update_client(client_id, name=new_name, contact_info=new_contact_info)
            if updated:
                messagebox.showinfo("Success", f"Client ID {client_id} updated successfully.")
                self._clear_form()
                self._load_clients()
            else:
                messagebox.showerror("Error", "Failed to update client. No changes or client not found.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during update: {e}")

    def _delete_client(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a client from the list to delete.")
            return

        client_id = self.tree.item(selected_item, "values")[0]
        client_name = self.tree.item(selected_item, "values")[1]

        # Check for associated records before deleting
        associated_properties = self.db_manager.get_client_properties(client_id)
        associated_surveys = self.db_manager.get_client_survey_jobs(client_id)

        if associated_properties or associated_surveys:
            confirm_msg = f"Client '{client_name}' (ID: {client_id}) has associated records:\n"
            if associated_properties:
                confirm_msg += f"- {len(associated_properties)} Land Purchase(s)\n"
            if associated_surveys:
                confirm_msg += f"- {len(associated_surveys)} Survey Job(s)\n"
            confirm_msg += "Deleting this client might affect these records or violate database constraints. Do you wish to proceed anyway?"

            if not messagebox.askyesno("Confirm Delete with Associations", confirm_msg):
                return  # User cancelled

        if messagebox.askyesno("Confirm Delete",
                               f"Are you sure you want to delete client '{client_name}' (ID: {client_id})? This action cannot be undone."):
            try:
                deleted = self.db_manager.delete_client(client_id)
                if deleted:
                    messagebox.showinfo("Success", f"Client '{client_name}' deleted successfully.")
                    self._clear_form()
                    self._load_clients()
                else:
                    messagebox.showerror("Error", "Failed to delete client. Client not found.")
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred during deletion: {e}")

    def _on_client_select(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, "values")
            client_id = values[0]  # Get client ID

            self.client_name_entry.delete(0, tk.END)
            self.client_name_entry.insert(0, values[1])  # Name
            self.contact_info_entry.delete(0, tk.END)
            self.contact_info_entry.insert(0, values[2])  # Contact Info

            self.update_button.config(state="normal")
            self.delete_button.config(state="normal")
            self.add_button.config(state="disabled")  # Disable add when updating

            self._load_associated_data(client_id)  # Load associated data for selected client
        else:
            self._clear_form()
            self.update_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.add_button.config(state="normal")
            self._clear_associated_data()  # Clear associated data if nothing selected

    def _clear_form(self):
        self.client_name_entry.delete(0, tk.END)
        self.contact_info_entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.focus())  # Deselect any item in treeview
        self.update_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.add_button.config(state="normal")
        self._clear_associated_data()  # Clear associated data as well

    def _clear_associated_data(self):
        for item in self.land_tree.get_children():
            self.land_tree.delete(item)
        for item in self.survey_tree.get_children():
            self.survey_tree.delete(item)

    def _load_associated_data(self, client_id):
        self._clear_associated_data()

        # Load associated Land Purchases
        properties = self.db_manager.get_client_properties(client_id)
        if properties:
            for prop in properties:
                self.land_tree.insert("", "end", values=(
                    prop['property_id'],
                    prop['title_deed_number'],
                    prop['location'],
                    prop['size'],
                    prop['price'],
                    prop['status'],
                    prop['transaction_date']
                ))

        # Load associated Survey Jobs
        survey_jobs = self.db_manager.get_client_survey_jobs(client_id)
        if survey_jobs:
            for job in survey_jobs:
                self.survey_tree.insert("", "end", values=(
                    job['job_id'],
                    job['property_location'],
                    job['job_description'],
                    job['fee'],
                    job['status'],
                    job['deadline'],
                    job['created_at']
                ))

