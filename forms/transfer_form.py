import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from tkcalendar import DateEntry

# Import other forms using absolute imports relative to the project root
from forms.client_form import ClientForm  # For adding new clients during transfer
from forms.property_forms import AddPropertyForTransferForm

# --- Module-level imports for ctypes, ensuring variables are always defined ---
windll = None
byref = None
sizeof = None
c_int = None

if os.name == 'nt':
    try:
        from ctypes import windll, byref, sizeof, c_int
    except (ImportError, Exception):
        pass

# --- End of ctypes import block ---

class PropertyTransferForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, user_id=None, user_role=None, parent_icon_loader=None,
                 window_icon_name="transfer.png"):
        super().__init__(master)
        self.title("Transfer Property")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        self.user_role = user_role
        self.parent_icon_loader = parent_icon_loader

        self.selected_property = None
        self.selected_from_client = None  # Current owner (seller)
        self.selected_to_client = None    # New owner (buyer)
        self.selected_document_path = None # New attribute to hold the path of the selected document

        self._set_window_properties(1300, 750, window_icon_name, parent_icon_loader) # Adjusting height
        self._customize_title_bar()

        # Load data needed for dropdowns and real-time search
        self.all_clients = self.db_manager.get_all_clients()
        self.all_agents = self.db_manager.get_all_agents()
        
        # New attributes to hold entry and combobox widgets
        self.to_client_name_entry = None
        self.agent_combobox = None
        
        self._create_widgets()
        
        self.search_properties() # Load properties on startup
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        self.grab_release()
        self.destroy()

    def _customize_title_bar(self):
        try:
            if os.name == 'nt' and windll and byref and sizeof and c_int:
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
            else:
                self._create_custom_title_bar()
        except Exception as e:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(title_bar, text="Transfer Property", bg='#003366', fg='white', font=('Helvetica', 10))
        title_label.pack(side=tk.LEFT, padx=10)
        close_button = tk.Button(title_bar, text='×', bg='#003366', fg='white', bd=0, activebackground='red',
                                 command=self.destroy, font=('Helvetica', 12, 'bold'))
        close_button.pack(side=tk.RIGHT, padx=5)
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)
    
    def _save_drag_start_pos(self, event):
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 20
        self.geometry(f"+{x}+{y}")
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Load icons
        if self.parent_icon_loader:
            self._transfer_icon = self.parent_icon_loader("transfer.png", size=(20, 20))
            self._cancel_transfer_icon = self.parent_icon_loader("cancel.png", size=(20, 20))
            self._search_icon = self.parent_icon_loader("search.png", size=(20, 20))
            self._add_client_icon = self.parent_icon_loader("add_user.png", size=(20, 20))
            self._add_property_icon = self.parent_icon_loader("add_property.png", size=(20, 20))
            self._browse_icon = self.parent_icon_loader("folder.png", size=(20, 20)) # New icon for file browse

        # --- Property Selection ---
        prop_selection_frame = ttk.LabelFrame(main_frame, text="1. Select Property to Transfer", padding="10")
        prop_selection_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        prop_selection_frame.columnconfigure(1, weight=1)

        search_row_frame = ttk.Frame(prop_selection_frame)
        search_row_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=2)
        search_row_frame.columnconfigure(1, weight=1)

        ttk.Label(search_row_frame, text="Search Property:").grid(row=0, column=0, sticky="w", padx=5)
        self.property_search_entry = ttk.Entry(search_row_frame, width=30)
        self.property_search_entry.grid(row=0, column=1, sticky="ew", padx=5)
        # Real-time search binding
        self.property_search_entry.bind('<KeyRelease>', lambda e: self.search_properties(e))
        
        # New "Add New Property" button
        self.add_prop_btn = ttk.Button(search_row_frame, text="Add New Property", image=self._add_property_icon,
                                        compound=tk.LEFT, command=self._open_add_new_property_form)
        self.add_prop_btn.grid(row=0, column=2, sticky="e", padx=5)

        prop_tree_frame = ttk.Frame(prop_selection_frame)
        prop_tree_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        prop_tree_frame.columnconfigure(0, weight=1)

        self.property_tree = ttk.Treeview(prop_tree_frame, columns=("id", "Title_deed", "Location", "Size", "Owner"),
                                         show="headings", height=5)
        self.property_tree.pack(side="left", fill="both", expand=True)
        self.property_tree.heading("id", text="ID")
        self.property_tree.heading("Title_deed", text="Title Deed")
        self.property_tree.heading("Location", text="Location")
        self.property_tree.heading("Size", text="Size in Acres")
        self.property_tree.heading("Owner", text="Current Owner")
        self.property_tree.column("id", width=40, anchor="center")
        self.property_tree.column("Title_deed", width=120)
        self.property_tree.column("Location", width=150)
        self.property_tree.column("Size", width=80)
        self.property_tree.column("Owner", width=150)
        prop_tree_scrollbar = ttk.Scrollbar(prop_tree_frame, orient="vertical", command=self.property_tree.yview)
        self.property_tree.configure(yscrollcommand=prop_tree_scrollbar.set)
        prop_tree_scrollbar.pack(side="right", fill="y")
        self.property_tree.bind("<<TreeviewSelect>>", self._on_property_select)

        # Property Details & Owner Display
        ttk.Label(prop_selection_frame, text="Selected Property:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.lbl_selected_property = ttk.Label(prop_selection_frame, text="N/A", font=('Helvetica', 10, 'bold'))
        self.lbl_selected_property.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=5)

        ttk.Label(prop_selection_frame, text="Current Owner:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.lbl_current_owner = ttk.Label(prop_selection_frame, text="N/A", font=('Helvetica', 10, 'bold'))
        self.lbl_current_owner.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # --- New Owner and Agent Selection ---
        details_frame = ttk.LabelFrame(main_frame, text="2. New Owner & Agent", padding="10")
        details_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=10)
        details_frame.columnconfigure(0, weight=1)
        details_frame.columnconfigure(1, weight=1)

        # New search frame for client list
        client_search_frame = ttk.Frame(details_frame)
        client_search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2)
        client_search_frame.columnconfigure(1, weight=1)

        ttk.Label(client_search_frame, text="Existing Clients:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.client_search_entry = ttk.Entry(client_search_frame, width=20)
        self.client_search_entry.grid(row=0, column=1, sticky="ew")
        self.client_search_entry.bind('<KeyRelease>', lambda e: self._filter_clients_by_name())

        columns = ("id", "name", "contact")
        self.client_tree = ttk.Treeview(details_frame, columns=columns, show="headings", height=4)
        self.client_tree.grid(row=1, column=0, sticky="ew", pady=(0, 5), columnspan=2)
        client_tree_scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=client_tree_scrollbar.set)
        client_tree_scrollbar.grid(row=1, column=2, sticky="ns")

        self.client_tree.heading("id", text="ID")
        self.client_tree.heading("name", text="Client Name")
        self.client_tree.heading("contact", text="Contact Info")
        self.client_tree.column("id", width=30, stretch=tk.NO)
        self.client_tree.column("name", width=150)
        self.client_tree.column("contact", width=100)
        self.client_tree.bind("<<TreeviewSelect>>", self._on_client_select_from_tree)
        self._populate_client_tree()

        # New Owner Entry and Add Button
        ttk.Label(details_frame, text="New Owner Name:").grid(row=2, column=0, sticky="w", pady=(5, 2))
        self.to_client_name_entry = ttk.Entry(details_frame)
        self.to_client_name_entry.grid(row=3, column=0, sticky="ew", padx=(0, 5), pady=2)
        self.to_client_name_entry.bind("<KeyRelease>", self._clear_tree_selection)
        
        ttk.Button(details_frame, text="Add New Client", image=self._add_client_icon, compound=tk.LEFT,
                    command=self._open_add_new_client_form).grid(row=3, column=1, sticky="e", pady=2, padx=(5,0))
        details_frame.columnconfigure(0, weight=1)

        # Supervising Agent Combobox (now a text input with a dropdown)
        ttk.Label(details_frame, text="Supervising Agent Name:").grid(row=4, column=0, sticky="w", pady=(10, 2))
        self.agent_name_var = tk.StringVar()
        self.agent_combobox = ttk.Combobox(details_frame, textvariable=self.agent_name_var, state="readonly")
        self.agent_combobox.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        self.agent_combobox['values'] = [agent['name'] for agent in self.all_agents]
        self.agent_combobox.bind("<<ComboboxSelected>>", self._on_agent_select)
        
        # --- Transfer Details and Action ---
        transfer_details_frame = ttk.LabelFrame(main_frame, text="3. Transfer Details", padding="10")
        transfer_details_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=10)
        transfer_details_frame.columnconfigure(1, weight=1)

        ttk.Label(transfer_details_frame, text="Transfer Price:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.entry_transfer_price = ttk.Entry(transfer_details_frame)
        self.entry_transfer_price.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(transfer_details_frame, text="Transfer Date:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.date_picker_frame = ttk.Frame(transfer_details_frame)
        self.date_picker_frame.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        self.entry_transfer_date = ttk.Entry(self.date_picker_frame, width=25, state='readonly')
        self.entry_transfer_date.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.date_entry = DateEntry(self.date_picker_frame, width=12, background='darkblue', foreground='white',
                                     borderwidth=2, year=datetime.now().year, month=datetime.now().month,
                                     day=datetime.now().day, date_pattern='y-mm-dd')
        self.date_entry.pack(side=tk.LEFT, padx=5)
        self.date_entry.bind('<<DateEntrySelected>>', self._update_date_entry)
        self._update_date_entry()

        # New: Supporting Document Upload Section
        ttk.Label(transfer_details_frame, text="Supporting Document:").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        doc_frame = ttk.Frame(transfer_details_frame)
        doc_frame.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        doc_frame.columnconfigure(0, weight=1)
        
        self.entry_document_path = ttk.Entry(doc_frame, state='readonly')
        self.entry_document_path.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        browse_btn = ttk.Button(doc_frame, text="Browse...", image=self._browse_icon, compound=tk.LEFT, command=self._browse_document)
        browse_btn.grid(row=0, column=1, sticky="e")

        # Action Buttons (moved to their own frame for centering)
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        transfer_btn = ttk.Button(button_frame, text="Execute Transfer", image=self._transfer_icon, compound=tk.LEFT,
                                     command=self._transfer_property)
        transfer_btn.pack(side="left", padx=5)
        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_transfer_icon, compound=tk.LEFT,
                                 command=self.destroy)
        cancel_btn.pack(side="left", padx=5)


    def _update_date_entry(self, event=None):
        selected_date = self.date_entry.get_date().strftime("%Y-%m-%d")
        self.entry_transfer_date.configure(state='normal')
        self.entry_transfer_date.delete(0, tk.END)
        self.entry_transfer_date.insert(0, selected_date)
        self.entry_transfer_date.configure(state='readonly')
        
    def _browse_document(self):
        """
        Opens a file dialog for the user to select a supporting document.
        """
        file_path = filedialog.askopenfilename(
            title="Select Supporting Document",
            filetypes=[("PDF files", "*.pdf"), ("Image files", "*.jpg;*.jpeg;*.png"), ("All files", "*.*")]
        )
        if file_path:
            self.selected_document_path = file_path
            self.entry_document_path.configure(state='normal')
            self.entry_document_path.delete(0, tk.END)
            self.entry_document_path.insert(0, os.path.basename(file_path))
            self.entry_document_path.configure(state='readonly')

    def _open_add_new_property_form(self):
        self.grab_release()
        self.withdraw()
        # You will need a reference to the AddPropertyForm class
        add_prop_form = AddPropertyForTransferForm(self.master, self.db_manager, self.refresh_callback, self.user_id, self.parent_icon_loader)
        add_prop_form.protocol("WM_DELETE_WINDOW", lambda: self._on_form_close(add_prop_form))

    def _open_add_new_client_form(self):
        self.grab_release()
        self.withdraw()
        # You will need a reference to the ClientForm class
        client_add_form = ClientForm(self.master, self.db_manager, self.user_id, self.user_role)
        client_add_form.protocol("WM_DELETE_WINDOW", lambda: self._on_form_close(client_add_form))
    
    def _on_form_close(self, form):
        form.destroy()
        self.deiconify()
        self.grab_set()
        # Re-fetch data and update the treeview
        self.all_clients = self.db_manager.get_all_clients()
        self.all_agents = self.db_manager.get_all_agents()
        self._populate_client_tree()
        self.agent_combobox['values'] = [agent['name'] for agent in self.all_agents]

    def search_properties(self, event=None):
        for item in self.property_tree.get_children():
            self.property_tree.delete(item)
        search_query = self.property_search_entry.get().strip()
        available_properties = self.db_manager.get_all_propertiesForTransfer_paginated(search_query=search_query)

        if available_properties:
            for prop in available_properties:
                owner_display = prop.get('owner', 'N/A')
                unique_iid = f"{prop['source_table']}-{prop['property_id']}"
                status_display = prop.get('size', 'N/A')
                self.property_tree.insert("", "end", values=(
                    prop['property_id'],
                    prop['title_deed_number'],
                    prop['location'],
                    status_display,
                    owner_display
                ), iid=unique_iid)
        self.selected_property = None
        self.lbl_selected_property.config(text="N/A")
        self.lbl_current_owner.config(text="N/A")

    def _on_property_select(self, event):
        selected_item = self.property_tree.focus()
        if selected_item:
            unique_iid = selected_item
            self.selected_source_table, prop_id = unique_iid.split('-')
            prop_id = int(prop_id)  # Convert property_id back to an integer

            self.selected_property = self.db_manager.get_property_by_source(prop_id, self.selected_source_table)
            if self.selected_property:
                owner_name = self.selected_property.get('owner', 'N/A')
                self.lbl_selected_property.config(
                text=f"ID: {self.selected_property['property_id']} | "
                        f"Title Deed: {self.selected_property['title_deed_number']} | "
                        f"Location: {self.selected_property['location']}"
                )
                self.lbl_current_owner.config(text=owner_name)
                self.selected_from_client = next((c for c in self.all_clients if c['name'] == owner_name), None)
            else:
                self.selected_property = None
                self.lbl_selected_property.config(text="N/A (Details not found)")
                self.lbl_current_owner.config(text="N/A")
        else:
            self.selected_property = None
            self.lbl_selected_property.config(text="N/A")
            self.lbl_current_owner.config(text="N/A")

    def _on_client_select_from_tree(self, event):
        """
        Handles a selection from the Treeview.
        """
        selected_item = self.client_tree.focus()
        if selected_item:
            item_data = self.client_tree.item(selected_item, "values")
            if item_data:
                # Set the entry box with the selected client's name
                self.to_client_name_entry.delete(0, tk.END)
                self.to_client_name_entry.insert(0, item_data[1])

    def _clear_tree_selection(self, event):
        """
        Clears the Treeview selection when the user starts typing in the entry box.
        """
        self.client_tree.selection_remove(self.client_tree.selection())

    def _on_agent_select(self, event):
        """
        Handles a selection from the Combobox.
        """
        selected_name = self.agent_name_var.get()
        self.selected_agent = next((a for a in self.all_agents if a['name'] == selected_name), None)

    def _transfer_property(self):
        # Initial checks
        if not self.user_id:
            messagebox.showerror("Authentication Error", "User not authenticated. Please log in.")
            return
        if not self.selected_property:
            messagebox.showerror("Input Error", "Please select a property.")
            return
        if not self.selected_from_client:
            messagebox.showerror("Input Error", "Could not determine current owner.")
            return

        # Get new owner and agent names from entry widgets
        new_owner_name = self.to_client_name_entry.get().strip()
        agent_name = self.agent_name_var.get().strip()

        if not new_owner_name:
            messagebox.showerror("Input Error", "Please enter a new owner's name.")
            return

        if not agent_name:
            messagebox.showerror("Input Error", "Please select a supervising agent's name.")
            return

        # Find the new owner and agent in the existing database lists
        self.selected_to_client = next((c for c in self.all_clients if c['name'].lower() == new_owner_name.lower()), None)
        self.selected_agent = next((a for a in self.all_agents if a.get('name', '').lower() == agent_name.lower()), None)

        # --- IMPORTANT: Validation Check for Existing Records ---
        if not self.selected_to_client or 'client_id' not in self.selected_to_client:
            messagebox.showerror("Validation Error", f"Client '{new_owner_name}' not found or invalid record. Please check the client list.")
            return

        if not self.selected_agent or 'agent_id' not in self.selected_agent:
            messagebox.showerror("Validation Error", f"Agent '{agent_name}' not found or invalid record. Please check the agent list.")
            return

        # Now you can safely get the IDs, as their existence is guaranteed
        to_client_id = self.selected_to_client['client_id']
        supervising_agent_id = self.selected_agent['agent_id']
        
        # --- (The rest of your code is correct) ---
        transfer_price_str = self.entry_transfer_price.get().strip()
        transfer_date = self.date_entry.get_date().strftime("%Y-%m-%d")

        if not transfer_price_str:
            messagebox.showerror("Input Error", "Please enter the transfer price.")
            return

        try:
            transfer_price = float(transfer_price_str)
            if transfer_price <= 0:
                messagebox.showerror("Input Error", "Transfer price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid transfer price. Please enter a numerical value.")
            return

        # Double-check if the selected property actually belongs to the selected "from client"
        if self.selected_from_client['name'] != self.selected_property['owner']:
            messagebox.showerror("Verification Error", "The selected property is not currently owned by the auto-populated seller.")
            return

        # --- Document Handling Logic (New) ---
        document_path_to_save = None
        if self.selected_document_path:
            try:
                document_path_to_save = self._store_document(self.selected_document_path)
            except Exception as e:
                messagebox.showerror("Document Error", f"Failed to save document: {e}")
                return

        if messagebox.askyesno(
                "Confirm Transfer",
                f"Are you sure you want to transfer property '{self.selected_property['title_deed_number']}' "
                f"from '{self.selected_from_client['name']}' to '{self.selected_to_client['name']}' "
                f"for KES {transfer_price:,.2f} on {transfer_date} "
                f"supervised by '{self.selected_agent['name']}'?"
        ):
            try:
                success = self.db_manager.execute_property_transfer(
                    property_id=self.selected_property['property_id'],
                    from_client_id=self.selected_from_client['client_id'],
                    to_client_id=to_client_id, # Use the validated ID
                    transfer_price=transfer_price,
                    transfer_date=transfer_date,
                    executed_by_user_id=self.user_id,
                    supervising_agent_id=supervising_agent_id, # Use the validated ID
                    document_path=document_path_to_save,
                    source_table=self.selected_source_table
                )

                if success:
                    messagebox.showinfo("Success", f"Property '{self.selected_property['title_deed_number']}' successfully transferred.")
                    self.refresh_callback()
                    self.destroy()
                else:
                    messagebox.showerror("Transfer Failed", "Failed to complete property transfer. Please check logs for details.")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred during transfer: {e}")

    def _store_document(self, source_path):
        """
        A conceptual method to copy the selected document to a persistent storage location.
        In a real application, this would be handled by your db_manager or a dedicated file handler.
        """
        try:
            # Ensure the documents directory exists
            documents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'documents')
            os.makedirs(documents_dir, exist_ok=True)
            
            # Create a unique filename to avoid overwrites
            file_extension = os.path.splitext(source_path)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"transfer_{timestamp}_{self.selected_property['property_id']}{file_extension}"
            destination_path = os.path.join(documents_dir, new_filename)

            # Copy the file
            shutil.copy2(source_path, destination_path)
            messagebox.showinfo("Document Saved", f"Document saved to: {destination_path}")
            return destination_path
        except Exception as e:
            messagebox.showerror("File System Error", f"Could not save the document: {e}")
            raise # Re-raise the exception to be caught in the main transfer method

    # --- New Helper Methods for New Owner and Agent UI ---
    def _populate_client_tree(self):
        """
        Populates the Treeview with client data from the database.
        """
        # Clear existing data
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        try:
            clients_data = self.db_manager.get_all_clients()
            for client in clients_data:
                self.client_tree.insert("", "end", values=(client['client_id'], client['name'], client['contact_info']))
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch client list: {e}")
    def _filter_clients_by_name(self):
        search_query = self.client_search_entry.get().strip().lower()
        
        # Clear existing entries in the Treeview
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        # Filter and repopulate the Treeview with a defensive check for the 'contact' key
        if search_query:
            filtered_clients = [c for c in self.all_clients if search_query in c.get('name', '').lower()]
        else:
            filtered_clients = self.all_clients

        for client in filtered_clients:
            # Use .get() to safely access 'contact' and provide a default value
            client_id = client.get('client_id')
            client_name = client.get('name', 'N/A')
            client_contact = client.get('contact', 'N/A')
            
            if client_id is not None:
                self.client_tree.insert("", "end", values=(client_id, client_name, client_contact))