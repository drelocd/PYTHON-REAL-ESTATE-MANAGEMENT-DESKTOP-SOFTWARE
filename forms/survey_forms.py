import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import os
import shutil
from PIL import Image, ImageTk
from tkcalendar import DateEntry # Import DateEntry for the date picker

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons') # Assuming icons are here

# Add these lines:
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')

# Ensure the RECEIPTS_DIR exists
if not os.path.exists(RECEIPTS_DIR):
    os.makedirs(RECEIPTS_DIR)
    print(f"Created receipts directory: {RECEIPTS_DIR}")

class AddSurveyJobForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None, window_icon_name="add_survey.png"):
        super().__init__(master)
        self.title("Register New Survey Job")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback # Callback to update survey overview
        self.parent_icon_loader = parent_icon_loader # Store the icon loader callback
        self._window_icon_ref = None # <--- Added for window icon persistence

        # References for internal button icons
        self.add_icon_ref = None
        self.cancel_icon_ref = None

        # Set window properties (size, position, icon)
        self._set_window_properties(600, 500, window_icon_name, parent_icon_loader)

        self._create_widgets(parent_icon_loader) # Pass loader to _create_widgets

        # Ensure that the window is closed properly when clicking the 'x' button
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks() # Ensures window dimensions are calculated before positioning
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate x to center horizontally, and y to be 100 pixels from top
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        # Set window icon and keep a strong reference
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image # <--- Store strong reference
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader): # Added parent_icon_loader argument
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Client Name:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_client_name = ttk.Entry(main_frame)
        self.entry_client_name.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Client Contact:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_client_contact = ttk.Entry(main_frame)
        self.entry_client_contact.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Location:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_location = ttk.Entry(main_frame)
        self.entry_location.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=5, padx=5)
        self.text_description = tk.Text(main_frame, height=4, wrap=tk.WORD)
        self.text_description.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Agreed Price (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_price = ttk.Entry(main_frame)
        self.entry_price.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Deadline Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_deadline = ttk.Entry(main_frame)
        self.entry_deadline.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.entry_deadline.insert(0, (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")) # Default to a year from now for deadline
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        # Load icons for buttons if parent_icon_loader is available and store references
        if parent_icon_loader:
            self.add_icon_ref = parent_icon_loader("add_job.png", size=(20, 20))
            self.cancel_icon_ref = parent_icon_loader("cancel.png", size=(20, 20))

        # Changed command for "Cancel" button to _on_closing
        ttk.Button(button_frame, text="Add Survey Job", image=self.add_icon_ref, compound=tk.LEFT, command=self._add_survey_job).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", image=self.cancel_icon_ref, compound=tk.LEFT, command=self._on_closing).pack(side="left", padx=10)


    def _add_survey_job(self):
        client_name = self.entry_client_name.get().strip()
        client_contact = self.entry_client_contact.get().strip()
        location = self.entry_location.get().strip()
        description = self.text_description.get("1.0", tk.END).strip()
        price_str = self.entry_price.get().strip()
        deadline_date_str = self.entry_deadline.get().strip()

        if not all([client_name, client_contact, location, price_str, deadline_date_str]):
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            agreed_price = float(price_str)
            if agreed_price <= 0:
                messagebox.showerror("Input Error", "Agreed Price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Agreed Price. Please enter a number.")
            return

        try:
            datetime.strptime(deadline_date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format for Deadline Date. Use YYYY-MM-DD.")
            return

        try:
            client = self.db_manager.get_client_by_contact_info(client_contact)
            if client:
                client_id = client['client_id'] # Access by key as row_factory is dict
                if client['name'] != client_name: # Check if name needs update
                    self.db_manager.update_client(client_id, name=client_name)
            else:
                client_id = self.db_manager.add_client(client_name, client_contact)
                if not client_id:
                    messagebox.showerror("Database Error", "Failed to add new client.")
                    return

            job_id = self.db_manager.add_survey_job(
                client_id, location, description, agreed_price, deadline_date_str
            )
            if job_id:
                messagebox.showinfo("Success", f"Survey Job added with ID: {job_id}")
                self.refresh_callback() # Refresh parent view on successful add
                self.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add survey job.")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            print(f"Error adding survey job: {e}")

    def _on_closing(self):
        """Handles window closing by releasing grab and destroying the window."""
        self.grab_release()
        self.destroy()


class ManagePaymentForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None, window_icon_name="payment.png"):
        super().__init__(master)
        self.title("Manage Payment")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self._window_icon_ref = None # For icon persistence

        self.selected_receipt_path = None

        # Store references to button icons (assuming they are loaded via parent_icon_loader)
        self._btn_receipt_icon = None
        self._record_payment_icon = None
        self._cancel_payment_icon = None

        # Set window properties and customize title bar (placeholders for actual implementation)
        self._set_window_properties(650, 450, window_icon_name, parent_icon_loader)
        # self._customize_title_bar() # Uncomment and implement fully if needed

        self._create_widgets(parent_icon_loader)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon.
           (Similar to AddPropertyForm)
        """
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")

        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader):
        """Creates and arranges the widgets for the payment management form."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        # Client/Property/Job Identification
        ttk.Label(main_frame, text="Client Name/ID:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_client_info = ttk.Entry(main_frame, width=40)
        self.entry_client_info.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Property/Job ID:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_property_job_id = ttk.Entry(main_frame, width=40)
        self.entry_property_job_id.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        # Payment Details
        ttk.Label(main_frame, text="Payment Date:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.date_entry = DateEntry(main_frame, width=37, background='darkblue', foreground='white',
                                    borderwidth=2, year=datetime.now().year, month=datetime.now().month,
                                    day=datetime.now().day, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Amount Paid (KES):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_amount_paid = ttk.Entry(main_frame, width=40)
        self.entry_amount_paid.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Payment Method:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.method_combobox = ttk.Combobox(main_frame, values=["Cash", "Bank Transfer", "M-Pesa", "Cheque", "Other"],
                                            state="readonly", width=37)
        self.method_combobox.set("Cash") # Default value
        self.method_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Transaction ID/Receipt No.:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_transaction_id = ttk.Entry(main_frame, width=40)
        self.entry_transaction_id.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Notes/Description:").grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        self.text_notes = tk.Text(main_frame, width=40, height=4, wrap=tk.WORD)
        self.text_notes.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        # Attach Receipt
        if parent_icon_loader:
            self._btn_receipt_icon = parent_icon_loader("folder_open.png", size=(20,20))
            self._record_payment_icon = parent_icon_loader("save.png", size=(20,20))
            self._cancel_payment_icon = parent_icon_loader("cancel.png", size=(20,20))

        ttk.Label(main_frame, text="Attach Receipt:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_attach_receipt = ttk.Button(main_frame, text="Browse...", image=self._btn_receipt_icon,
                                        compound=tk.LEFT, command=self._select_receipt_image)
        btn_attach_receipt.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_attach_receipt.image = self._btn_receipt_icon # Keep reference
        self.lbl_receipt_path = ttk.Label(main_frame, text="No file selected")
        self.lbl_receipt_path.grid(row=row+1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        record_btn = ttk.Button(button_frame, text="Record Payment", image=self._record_payment_icon,
                                compound=tk.LEFT, command=self._record_payment)
        record_btn.pack(side="left", padx=5)
        record_btn.image = self._record_payment_icon # Keep reference

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_payment_icon,
                                compound=tk.LEFT, command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_payment_icon # Keep reference

    def _select_receipt_image(self):
        """Handles selection of a receipt image file."""
        file_path = filedialog.askopenfilename(
            title="Select Receipt Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_receipt_path = file_path
            self.lbl_receipt_path.config(text=os.path.basename(file_path))

    def _save_receipt(self, source_path, destination_dir):
        """
        Saves the receipt file to the specified directory and returns its relative path.
        (Similar to _save_images in AddPropertyForm)
        """
        if not source_path:
            return None

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename, file_extension = os.path.splitext(os.path.basename(source_path))
        new_filename = f"receipt_{timestamp}{file_extension}"
        destination_path = os.path.join(destination_dir, new_filename)

        try:
            shutil.copy2(source_path, destination_path)
            # Make path relative to DATA_DIR, consistent with your other forms
            relative_path = os.path.relpath(destination_path, DATA_DIR).replace("\\", "/")
            return relative_path
        except Exception as e:
            messagebox.showerror("File Save Error", f"Failed to save receipt {source_path}: {e}")
            return None

    def _record_payment(self):
        """Handles the recording of a payment."""
        client_info = self.entry_client_info.get().strip()
        property_job_id = self.entry_property_job_id.get().strip()
        payment_date_str = self.date_entry.get()
        amount_paid_str = self.entry_amount_paid.get().strip()
        payment_method = self.method_combobox.get().strip()
        transaction_id = self.entry_transaction_id.get().strip()
        notes = self.text_notes.get("1.0", tk.END).strip()

        if not client_info or not amount_paid_str or not payment_date_str:
            messagebox.showerror("Input Error", "Client Info, Amount Paid, and Payment Date are required.")
            return

        try:
            amount_paid = float(amount_paid_str)
            if amount_paid <= 0:
                messagebox.showerror("Input Error", "Amount Paid must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Amount Paid. Please enter a number.")
            return

        # Save the receipt file if selected
        saved_receipt_path = self._save_receipt(self.selected_receipt_path, RECEIPTS_DIR)

        try:
            # --- Database Interaction Placeholder ---
            # Here you would call your database manager to record the payment.
            # Example:
            # payment_id = self.db_manager.add_payment(
            #     client_info,
            #     property_job_id if property_job_id else None, # Allow null for optional fields
            #     payment_date_str,
            #     amount_paid,
            #     payment_method,
            #     transaction_id if transaction_id else None,
            #     notes if notes else None,
            #     saved_receipt_path
            # )
            #
            # if payment_id:
            #     messagebox.showinfo("Success", f"Payment recorded successfully! Payment ID: {payment_id}")
            #     self.refresh_callback() # Refresh parent view on successful add
            #     self.destroy()
            # else:
            #     messagebox.showerror("Database Error", "Failed to record payment.")

            # --- Mock Success Message for Demonstration ---
            messagebox.showinfo("Success", f"Payment recorded for {client_info} (Mock success).")
            self.refresh_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while recording payment: {e}")
            print(f"Error recording payment: {e}")

class TrackSurveyJobsForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback=None, parent_icon_loader=None, window_icon_name="track_jobs.png"):
        super().__init__(master)
        self.title("Track Survey Jobs")
        self.geometry("1100x600")
        self.grab_set()
        self.transient(master)

        self._window_icon_ref = None
        if parent_icon_loader and window_icon_name:
            try:
                icon_image = parent_icon_loader(window_icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to load icon for TrackSurveyJobsForm: {e}")

        self.view = TrackSurveyJobsView(self, db_manager, refresh_callback, parent_icon_loader)
        self.view.pack(fill="both", expand=True)

class TrackSurveyJobsView(ttk.Frame):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None):
        super().__init__(master)
        self.db_manager = db_manager
        self.refresh_callback = refresh_callback # Callback to refresh the main UI if needed
        self.parent_icon_loader = parent_icon_loader # For loading icons

        self._create_widgets()
        self.load_jobs() # Load jobs when the view is initialized

        # References for internal button icons
        self._search_icon = None
        self._reset_icon = None
        self._details_icon = None
        self._edit_icon = None
        self._payment_icon = None
        self._complete_icon = None
        self._delete_icon = None


    def _create_widgets(self):
        """Creates the widgets for tracking survey jobs."""
        # Load icons if parent_icon_loader is provided
        if self.parent_icon_loader:
            self._search_icon = self.parent_icon_loader("search.png", size=(20, 20))
            self._reset_icon = self.parent_icon_loader("reset.png", size=(20, 20))
            self._details_icon = self.parent_icon_loader("details.png", size=(20, 20))
            self._edit_icon = self.parent_icon_loader("edit.png", size=(20, 20))
            self._payment_icon = self.parent_icon_loader("payment.png", size=(20, 20))
            self._complete_icon = self.parent_icon_loader("complete.png", size=(20, 20))
            self._delete_icon = self.parent_icon_loader("delete.png", size=(20, 20))


        # --- Search and Filter Frame ---
        filter_frame = ttk.LabelFrame(self, text="Filter Jobs", padding="10")
        filter_frame.pack(side="top", fill="x", padx=10, pady=5)

        filter_frame.columnconfigure(1, weight=1) # Allow entry to expand

        ttk.Label(filter_frame, text="Search by Client Name/Location:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.search_entry = ttk.Entry(filter_frame, width=50)
        self.search_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        search_btn = ttk.Button(filter_frame, text="Search", image=self._search_icon, compound=tk.LEFT, command=self.load_jobs)
        search_btn.grid(row=0, column=2, padx=5, pady=2)
        search_btn.image = self._search_icon # Keep reference

        reset_btn = ttk.Button(filter_frame, text="Reset", image=self._reset_icon, compound=tk.LEFT, command=self._reset_filters)
        reset_btn.grid(row=0, column=3, padx=5, pady=2)
        reset_btn.image = self._reset_icon # Keep reference

        ttk.Label(filter_frame, text="Status:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.status_combobox = ttk.Combobox(filter_frame, values=["All", "Pending", "Completed", "Cancelled"], state="readonly")
        self.status_combobox.set("All")
        self.status_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.status_combobox.bind("<<ComboboxSelected>>", lambda event: self.load_jobs())

        # --- Treeview for displaying jobs ---
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(self.tree_frame, columns=(
            "Job ID", "Client Name", "Contact", "Location", "Agreed Price",
            "Deadline", "Status"
        ), show="headings", selectmode="browse")

        # Define column headings and widths
        self.tree.heading("Job ID", text="Job ID")
        self.tree.heading("Client Name", text="Client Name")
        self.tree.heading("Contact", text="Contact")
        self.tree.heading("Location", text="Location")
        self.tree.heading("Agreed Price", text="Agreed Price")
        self.tree.heading("Deadline", text="Deadline")
        self.tree.heading("Status", text="Status")

        self.tree.column("Job ID", width=60, anchor="center")
        self.tree.column("Client Name", width=150, anchor="w")
        self.tree.column("Contact", width=120, anchor="w")
        self.tree.column("Location", width=150, anchor="w")
        self.tree.column("Agreed Price", width=100, anchor="e")
        self.tree.column("Deadline", width=100, anchor="center")
        self.tree.column("Status", width=90, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Action Buttons Frame ---
        action_frame = ttk.Frame(self)
        action_frame.pack(side="bottom", fill="x", padx=10, pady=5)

        ttk.Button(action_frame, text="View Details", image=self._details_icon, compound=tk.LEFT, command=self._view_job_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Edit Job", image=self._edit_icon, compound=tk.LEFT, command=self._edit_job).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Add Payment", image=self._payment_icon, compound=tk.LEFT, command=self._add_payment).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Mark as Completed", image=self._complete_icon, compound=tk.LEFT, command=lambda: self._update_job_status("Completed")).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Delete Job", image=self._delete_icon, compound=tk.LEFT, command=self._delete_job).pack(side="right", padx=5)


    def load_jobs(self):
        """Loads survey jobs from the database into the Treeview, applying filters."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_term = self.search_entry.get().strip()
        status_filter = self.status_combobox.get()
        if status_filter == "All":
            status_filter = None # Pass None to get all statuses

        jobs = self.db_manager.get_all_survey_jobs(
            search_term=search_term if search_term else None,
            status=status_filter
        )

        if not jobs:
            self.tree.insert("", "end", values=("", "No jobs found.", "", "", "", "", ""), tags=('no_data',))
            self.tree.tag_configure('no_data', foreground='gray', font=('TkDefaultFont', 10, 'italic'))
            return

        for job in jobs:
            # Assuming job is a dictionary or an object with attributes matching column names
            # You might need to adjust column names based on your DB schema and db_manager output
            self.tree.insert("", "end", values=(
                job.get('job_id', ''),
                job.get('client_name', ''),
                job.get('client_contact', ''),
                job.get('location', ''),
                f"KES {job.get('agreed_price', 0):,.2f}",
                job.get('deadline_date', ''),
                job.get('status', '')
            ))
        if self.refresh_callback:
            self.refresh_callback() # Trigger a refresh in the main app if necessary

    def _reset_filters(self):
        """Resets search filters and reloads all jobs."""
        self.search_entry.delete(0, tk.END)
        self.status_combobox.set("All")
        self.load_jobs()

    def _get_selected_job_id(self):
        """Helper to get the job_id of the currently selected item in the Treeview."""
        selected_item = self.tree.focus()
        if not selected_item or self.tree.item(selected_item, "tags") == ('no_data',):
            messagebox.showwarning("No Selection", "Please select a survey job from the list.")
            return None
        return self.tree.item(selected_item, "values")[0] # Job ID is in the first column


    def _view_job_details(self):
        """Opens a dialog to view details of the selected job."""
        job_id = self._get_selected_job_id()
        if job_id:
            messagebox.showinfo("Job Details", f"Viewing details for Job ID: {job_id}\n(Implement actual detail view here)")
            # You would typically open a new Toplevel window here
            # e.g., JobDetailsForm(self.master, self.db_manager, job_id, self.parent_icon_loader)

    def _edit_job(self):
        """Opens a form to edit the selected job."""
        job_id = self._get_selected_job_id()
        if job_id:
            messagebox.showinfo("Edit Job", f"Editing Job ID: {job_id}\n(Implement actual edit form here)")
            # You would typically open an EditSurveyJobForm here, pre-filled with job data
            # e.g., EditSurveyJobForm(self.master, self.db_manager, job_id, self.load_jobs, self.parent_icon_loader)

    def _add_payment(self):
        """Opens the ManagePaymentForm for the selected job."""
        job_id = self._get_selected_job_id()
        if job_id:
            # Import ManagePaymentForm at the top of survey_forms.py
            # from your_forms_module import ManagePaymentForm # if ManagePaymentForm is in a separate file
            from forms.survey_forms import ManagePaymentForm # Adjust this import if ManagePaymentForm is separate

            # Pass the job_id to the ManagePaymentForm for pre-filling or linking
            # Ensure ManagePaymentForm's __init__ accepts a job_id parameter
            # For simplicity, this example just opens the form
            manage_payment_form = ManagePaymentForm(
                self.master,
                self.db_manager,
                self.load_jobs, # Refresh this view after payment is added
                self.parent_icon_loader
            )
            # You might want to pre-fill the Property/Job ID field
            manage_payment_form.entry_property_job_id.insert(0, job_id)
            # You might also want to pre-fill client name if available
            # find_client = self.db_manager.get_job_client_info(job_id)
            # if find_client:
            #     manage_payment_form.entry_client_info.insert(0, find_client['client_name'])


    def _update_job_status(self, new_status):
        """Updates the status of the selected job."""
        job_id = self._get_selected_job_id()
        if job_id:
            if messagebox.askyesno("Confirm Status Change", f"Are you sure you want to mark Job ID {job_id} as '{new_status}'?"):
                if self.db_manager.update_survey_job_status(job_id, new_status):
                    messagebox.showinfo("Success", f"Job ID {job_id} marked as '{new_status}'.")
                    self.load_jobs() # Reload to reflect changes
                else:
                    messagebox.showerror("Error", f"Failed to update status for Job ID {job_id}.")

    def _delete_job(self):
        """Deletes the selected job."""
        job_id = self._get_selected_job_id()
        if job_id:
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Job ID {job_id}? This action cannot be undone."):
                if self.db_manager.delete_survey_job(job_id):
                    messagebox.showinfo("Success", f"Job ID {job_id} deleted.")
                    self.load_jobs() # Reload to reflect changes
                else:
                    messagebox.showerror("Error", f"Failed to delete Job ID {job_id}.")

