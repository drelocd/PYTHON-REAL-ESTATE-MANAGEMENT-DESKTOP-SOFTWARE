import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import shutil
from PIL import Image, ImageTk
from tkcalendar import DateEntry # Import DateEntry for the date picker

from forms.property_forms import REPORTS_DIR

# Conditional import for ReportLab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    print("Warning: ReportLab not installed. PDF generation will not work. Install with: pip install reportlab")


# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons') # Assuming icons are here

# Add these lines:
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
SURVEY_ATTACHMENTS_DIR = os.path.join(DATA_DIR, 'survey_attachments')

# Ensure the RECEIPTS_DIR exists
if not os.path.exists(RECEIPTS_DIR):
    os.makedirs(RECEIPTS_DIR)
    print(f"Created receipts directory: {RECEIPTS_DIR}")

# NEW: Ensure REPORTS_DIR exists
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)
    print(f"Created reports directory: {REPORTS_DIR}")

# Ensure the SURVEY_ATTACHMENTS_DIR exists
if not os.path.exists(SURVEY_ATTACHMENTS_DIR):
    os.makedirs(SURVEY_ATTACHMENTS_DIR)
    print(f"Created survey attachments directory: {SURVEY_ATTACHMENTS_DIR}")


class SuccessMessage(tk.Toplevel):
    def __init__(self, master, success, message, pdf_path="",refresh_callback=None, parent_icon_loader=None, window_icon_name=None):

        super().__init__(master)
        self.title("Notification")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        self.refresh_callback = refresh_callback  # Store the callback here
        self._icon_photo_ref = None  # Keep strong reference to PhotoImage

        if parent_icon_loader:
            icon_name = "success.png" if success else "error.png"
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._icon_photo_ref = icon_image  # Store strong reference
            except Exception as e:
                print(f"Failed to set icon for SuccessMessage: {e}")

        lbl = ttk.Label(self, text=message, font=('Helvetica', 10), wraplength=300, justify=tk.CENTER)
        lbl.pack(padx=20, pady=10)

        if success and pdf_path and _REPORTLAB_AVAILABLE:  # Only show Open button if PDF was actually generated
            open_btn = ttk.Button(self, text="Open Report Folder", command=lambda: os.startfile(
                os.path.dirname(pdf_path)))  # Open parent directory of PDF
            open_btn.pack(pady=5)

        ok_btn = ttk.Button(self, text="OK", command=self.destroy)
        ok_btn.pack(pady=10)

        self.update_idletasks()
        x = master.winfo_x() + master.winfo_width() // 2 - self.winfo_width() // 2
        y = master.winfo_y() + master.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")


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

    def _add_attachment(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Attachment Files",
            filetypes=[("All Files", "*.*"), ("Documents", "*.pdf *.doc *.docx *.txt"),
                       ("Images", "*.jpg *.jpeg *.png")]
        )
        if file_paths:
            for path in file_paths:
                if path not in self.attachment_paths:
                    self.attachment_paths.append(path)
            self._update_attachment_label()

    def _update_attachment_label(self):
        if self.attachment_paths:
            num_files = len(self.attachment_paths)
            self.attachment_label.config(text=f"{num_files} file(s) selected.")
        else:
            self.attachment_label.config(text="No files selected.")

    def _save_attachments(self, job_id):
        job_attachment_dir = os.path.join(SURVEY_ATTACHMENTS_DIR, str(job_id))
        if not os.path.exists(job_attachment_dir):
            os.makedirs(job_attachment_dir)

        saved_attachment_paths = []
        for src_path in self.attachment_paths:
            try:
                dest_path = os.path.join(job_attachment_dir, os.path.basename(src_path))
                shutil.copy2(src_path, dest_path)
                saved_attachment_paths.append(dest_path)
            except Exception as e:
                messagebox.showerror("Attachment Error", f"Failed to save attachment {os.path.basename(src_path)}: {e}")
        return saved_attachment_paths

    def _save_survey_job(self):
        client_name = self.entry_client_name.get()
        client_contact = self.entry_client_contact.get()
        property_location = self.entry_property_location.get()
        survey_type = self.combo_survey_type.get()
        fee_quoted_str = self.entry_fee_quoted.get()
        date_assigned_str = self.date_assigned_entry.get_date().strftime('%Y-%m-%d')
        expected_completion_str = self.date_expected_completion_entry.get_date().strftime('%Y-%m-%d')
        status = self.combo_status.get()
        notes = self.text_notes.get("1.0", tk.END).strip()

        if not all([client_name, client_contact, property_location, survey_type, fee_quoted_str, date_assigned_str,
                    expected_completion_str, status]):
            messagebox.showerror("Input Error", "Please fill in all required fields.")
            return

        try:
            fee_quoted = float(fee_quoted_str)
            if fee_quoted < 0:
                messagebox.showerror("Input Error", "Fee Quoted cannot be negative.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Fee Quoted must be a valid number.")
            return

        job_id = self.db_manager.add_survey_job(
            client_name, client_contact, property_location, survey_type,
            fee_quoted, date_assigned_str, expected_completion_str, status, notes
        )

        if job_id:
            saved_attachments = self._save_attachments(job_id)
            if saved_attachments:
                self.db_manager.add_survey_attachments(job_id, saved_attachments)

            SuccessMessage(
                self,
                success=True,
                message=f"Survey Job ID {job_id} registered successfully!",
                parent_icon_loader=self.parent_icon_loader_ref
            )
            self.refresh_callback()
            self.destroy()
        else:
            SuccessMessage(
                self,
                success=False,
                message="Failed to register survey job.",
                parent_icon_loader=self.parent_icon_loader_ref
            )

    def center_window(self):
        self.update_idletasks()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()

        x = master_x + (master_width // 2) - (self.winfo_width() // 2)
        y = master_y + (master_height // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

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

        ttk.Button(button_frame, text="Add Payment", image=self._save_icon_ref, compound=tk.LEFT,
                   command=self._add_payment).pack(side="left", padx=10)
        self.btn_generate_receipt = ttk.Button(button_frame, text="Generate Receipt",
                                               image=self._generate_receipt_icon_ref, compound=tk.LEFT,
                                               command=self._generate_receipt, state=tk.DISABLED)
        self.btn_generate_receipt.pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", image=self._cancel_icon_ref, compound=tk.LEFT,
                   command=self._on_closing).pack(side="left", padx=10)

    def _populate_job_dropdown(self):
        jobs = self.db_manager.get_all_survey_jobs()
        job_ids = [job['job_id'] for job in jobs]
        self.job_id_combobox['values'] = job_ids
        if job_ids:
            self.job_id_combobox.set(job_ids[0])
            self._on_job_selected(None)  # Manually trigger selection for the first item

    def _on_job_selected(self, event):
        selected_job_id = self.job_id_combobox.get()
        if selected_job_id:
            job_info = self.db_manager.get_survey_job_by_id(selected_job_id)
            if job_info:
                client_info = self.db_manager.get_client_by_id(job_info['client_id'])
                self.entry_client_info.config(state="normal")
                self.entry_client_info.delete(0, tk.END)
                self.entry_client_info.insert(0, client_info['name'] if client_info else "N/A")
                self.entry_client_info.config(state="readonly")

                self.entry_total_price.config(state="normal")
                self.entry_total_price.delete(0, tk.END)
                self.entry_total_price.insert(0, f"{job_info['agreed_price']:.2f}")
                self.entry_total_price.config(state="readonly")

                self._update_receipt_button_state()
            else:
                self._clear_fields()
        else:
            self._clear_fields()

    def _clear_fields(self):
        self.entry_client_info.config(state="normal")
        self.entry_client_info.delete(0, tk.END)
        self.entry_client_info.config(state="readonly")

        self.entry_total_price.config(state="normal")
        self.entry_total_price.delete(0, tk.END)
        self.entry_total_price.config(state="readonly")

        self.entry_amount_paid.delete(0, tk.END)
        self.entry_payment_date.set_date(datetime.now().date())
        self.payment_method_combobox.set("Cash")
        self.btn_generate_receipt.config(state=tk.DISABLED)



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

    def _add_payment(self):
        job_id = self.job_id_combobox.get()
        amount_str = self.entry_amount_paid.get().strip()
        payment_date_str = self.entry_payment_date.get_date().strftime("%Y-%m-%d")
        payment_method = self.payment_method_combobox.get()

        if not all([job_id, amount_str, payment_date_str, payment_method]):
            messagebox.showerror("Input Error", "All payment fields are required.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showerror("Input Error", "Amount paid must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Amount Paid. Please enter a number.")
            return

        try:
            if self.db_manager.add_survey_payment(job_id, amount, payment_date_str, payment_method):
                messagebox.showinfo("Success", "Payment added successfully!")
                self.refresh_callback()  # Refresh the parent view
                self._update_receipt_button_state()  # Update button state after payment
                # Clear amount field for next entry
                self.entry_amount_paid.delete(0, tk.END)
            else:
                messagebox.showerror("Database Error", "Failed to add payment.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            print(f"Error adding survey payment: {e}")

    def _update_receipt_button_state(self):
        """Enables the 'Generate Receipt' button if a job is selected."""
        if self.job_id_combobox.get():
            self.btn_generate_receipt.config(state=tk.NORMAL)
        else:
            self.btn_generate_receipt.config(state=tk.DISABLED)

    def _generate_receipt(self):
        if not _REPORTLAB_AVAILABLE:
            messagebox.showwarning("Feature Unavailable",
                                   "ReportLab library is not installed. Cannot generate PDF receipts. Please install it using: pip install reportlab")
            return

        job_id = self.job_id_combobox.get()
        if not job_id:
            messagebox.showerror("Selection Error", "Please select a Survey Job to generate a receipt.")
            return

        try:
            job_info = self.db_manager.get_survey_job_by_id(job_id)
            if not job_info:
                messagebox.showerror("Error", "Could not retrieve job information.")
                return

            client_info = self.db_manager.get_client_by_id(job_info['client_id'])
            if not client_info:
                messagebox.showerror("Error", "Could not retrieve client information.")
                return

            payments = self.db_manager.get_payments_for_survey_job(job_id)
            if not payments:
                messagebox.showwarning("No Payments",
                                       "No payments recorded for this survey job. Cannot generate a receipt.")
                return

            total_paid = sum(p['amount'] for p in payments)
            balance = job_info['agreed_price'] - total_paid

            # Generate PDF
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            receipt_filename = f"Survey_Receipt_Job_{job_id}_{timestamp}.pdf"
            pdf_path = os.path.join(RECEIPTS_DIR, receipt_filename)

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Custom style for bold text
            styles.add(ParagraphStyle(name='BoldCentered', alignment=1, fontName='Helvetica-Bold', fontSize=12))

            story = []

            # Company Header
            story.append(Paragraph("<b>Mathenge's Real Estate Management System</b>", styles['h2']))
            story.append(Paragraph("Survey Services Payment Receipt", styles['h3']))
            story.append(Spacer(1, 0.2 * inch))

            # Receipt Details
            story.append(
                Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"<b>Job ID:</b> {job_id}", styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))

            # Client Details
            story.append(Paragraph("<b>Client Details:</b>", styles['Normal']))
            story.append(Paragraph(f"Name: {client_info['name']}", styles['Normal']))
            story.append(Paragraph(f"Contact: {client_info['contact_info']}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            # Job Details
            story.append(Paragraph("<b>Survey Job Details:</b>", styles['Normal']))
            story.append(Paragraph(f"Location: {job_info['location']}", styles['Normal']))
            story.append(Paragraph(f"Description: {job_info['description']}", styles['Normal']))
            story.append(Paragraph(f"Agreed Price: KES {job_info['agreed_price']:.2f}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            # Payment History Table
            story.append(Paragraph("<b>Payment History:</b>", styles['Normal']))
            table_data = [['Payment ID', 'Amount', 'Date', 'Method']]
            for p in payments:
                table_data.append(
                    [str(p['payment_id']), f"KES {p['amount']:.2f}", p['payment_date'], p['payment_method']])

            # Table style
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black)
            ])

            # Calculate column widths to fit content, allowing description to take more space
            col_widths = [1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch]

            payment_table = Table(table_data, colWidths=col_widths)
            payment_table.setStyle(table_style)
            story.append(payment_table)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f"<b>Total Paid:</b> KES {total_paid:.2f}", styles['Normal']))
            story.append(Paragraph(f"<b>Balance Due:</b> KES {balance:.2f}", styles['Normal']))
            story.append(Spacer(1, 0.4 * inch))

            story.append(Paragraph("Thank you for your business!", styles['BoldCentered']))

            doc.build(story)

            SuccessMessage(
                self,
                success=True,
                message="Receipt PDF generated successfully!",
                pdf_path=pdf_path,
                parent_icon_loader=self.parent_icon_loader
            )
        except Exception as e:
            messagebox.showerror("Receipt Generation Error", f"An error occurred while generating the receipt: {e}")

    def _on_closing(self):
        self.grab_release()
        self.destroy()

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
        self.tree.heading("Agreed Price", text="Agreed Price(KES)")
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

    def _apply_filters(self, event=None):
        search_term = self.search_entry.get().lower().strip()
        status_filter = self.status_filter_combobox.get()

        # Get dates from DateEntry widgets
        start_date_obj = self.date_from_entry.get_date() if self.date_from_entry.get() else None
        end_date_obj = self.date_to_entry.get_date() if self.date_to_entry.get() else None

        # Convert date objects to string for comparison (assuming YYYY-MM-DD format in DB)
        start_date_str = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else ""
        end_date_str = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else ""

        for item_id in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item_id, 'values')

            job_id, client_name, client_contact, location, description, price, paid, balance, deadline_date, status = values

            match_search = True
            if search_term:
                if search_term not in client_name.lower() and \
                        search_term not in location.lower() and \
                        search_term not in description.lower() and \
                        search_term not in client_contact.lower():
                    match_search = False

            match_status = (status_filter == "All" or status == status_filter)

            match_date_range = True
            if deadline_date:  # Ensure deadline_date is not empty
                # Convert deadline_date string from treeview to datetime object for proper comparison
                try:
                    job_deadline = datetime.strptime(deadline_date, "%Y-%m-%d").date()
                    if start_date_obj and job_deadline < start_date_obj:
                        match_date_range = False
                    if end_date_obj and job_deadline > end_date_obj:
                        match_date_range = False
                except ValueError:
                    # Handle cases where deadline_date might be in an unexpected format or empty
                    match_date_range = False

            if match_search and match_status and match_date_range:
                self.jobs_tree.item(item_id, open=True, tags=(''))  # Show
            else:
                self.jobs_tree.item(item_id, open=False, tags=('hidden'))  # Hide

        self.jobs_tree.tag_configure('hidden', A=0)  # Make hidden items invisible

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
        selected_item = self.tree.focus()  # Change from self.jobs_treeview.focus() to self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a job to edit.")
            return

        # Get the job_id from the values of the selected item
        # Assuming Job ID is the first column in your treeview
        job_id = self.tree.item(selected_item, 'values')[0]

        if job_id:
            try:
                job_id = int(job_id) # Ensure job_id is an integer
            except ValueError:
                messagebox.showerror("Error", "Invalid job ID selected.")
                return

            # Open the EditSurveyJobForm, passing the job_id and refresh callback
            EditSurveyJobForm(
                self.master,
                self.db_manager,
                job_id,
                self.load_jobs,  # Use the method that refreshes your treeview
                parent_icon_loader=self.parent_icon_loader, # Assuming parent_icon_loader is an attribute of TrackSurveyJobsView
                window_icon_name="edit_job.png"
            )
        else:
            messagebox.showwarning("No Selection", "Please select a job to edit.")


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

    def _manage_payment(self):
        job_id = self._get_selected_job_id()
        if job_id:
            manage_payment_form = ManagePaymentForm(self, self.db_manager, self.load_jobs,
                                                    parent_icon_loader=self.parent_icon_loader)
            manage_payment_form.grab_set()

            # Prefill job ID if available
            manage_payment_form.job_id_combobox.set(job_id)
            manage_payment_form._on_job_selected(None)  # Manually trigger selection for the prefilled item
            # Do not prefill client name if available
            # find_client = self.db_manager.get_job_client_info(job_id)
            # if find_client:
            #     manage_payment_form.entry_client_info.insert(0, find_client['client_name'])

    def _view_attachments(self):
        job_id = self._get_selected_job_id()
        if job_id:
            job_attachment_dir = os.path.join(SURVEY_ATTACHMENTS_DIR, str(job_id))
            if os.path.exists(job_attachment_dir) and os.listdir(job_attachment_dir):
                os.startfile(job_attachment_dir)  # Open the folder
            else:
                messagebox.showinfo("No Attachments", f"No attachments found for Job ID {job_id}.")

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

    def _on_closing(self):
        """Handles window closing by releasing grab and destroying the window."""
        self.grab_release()
        self.destroy()


class SurveyReportsForm(tk.Toplevel):
    def __init__(self, master: object, db_manager: object,populate_overview_callback, parent_icon_loader: object = None, window_icon_name: object = "survey_reports.png") -> None:
        super().__init__(master)
        self.title("Survey Reports")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.parent_icon_loader_ref = parent_icon_loader
        self._window_icon_ref = None

        # Icon references for buttons
        self._generate_report_icon = None

        self._set_window_properties(700, 600, window_icon_name, parent_icon_loader)
        self._create_widgets(parent_icon_loader)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
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
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Report Type Selection
        ttk.Label(main_frame, text="Select Report Type:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.report_type_combobox = ttk.Combobox(main_frame, values=[
            "All Survey Jobs",
            "Completed Survey Jobs",
            "Pending Survey Jobs",
            "Cancelled Survey Jobs",
            "Survey Payments Report"
        ], state="readonly")
        self.report_type_combobox.set("All Survey Jobs")
        self.report_type_combobox.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        self.report_type_combobox.bind("<<ComboboxSelected>>", self._on_report_type_selected)

        # Date Range Selection
        ttk.Label(main_frame, text="Start Date:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.start_date_entry = DateEntry(main_frame, width=12, background='darkblue', foreground='white',
                                          borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        self.start_date_entry.set_date(datetime.now().replace(day=1).date())  # Default to start of current month

        ttk.Label(main_frame, text="End Date:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.end_date_entry = DateEntry(main_frame, width=12, background='darkblue', foreground='white', borderwidth=2,
                                        date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=5)
        self.end_date_entry.set_date(datetime.now().date())  # Default to today's date

        # Report Text Widget (for preview/status)
        ttk.Label(main_frame, text="Report Preview/Status:").grid(row=3, column=0, columnspan=2, sticky="w", pady=10,
                                                                  padx=5)
        self.report_text_widget = tk.Text(main_frame, wrap=tk.WORD, height=15, width=70, state="disabled")
        self.report_text_widget.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # Scrollbar for text widget
        text_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.report_text_widget.yview)
        text_scrollbar.grid(row=4, column=2, sticky="ns", pady=5)
        self.report_text_widget.config(yscrollcommand=text_scrollbar.set)

        main_frame.rowconfigure(4, weight=1)  # Make text widget expand vertically

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        if parent_icon_loader:
            self._generate_report_icon = parent_icon_loader("report_generate.png", size=(20, 20))

        ttk.Button(button_frame, text="Generate Report", image=self._generate_report_icon, compound=tk.LEFT,
                   command=self._load_report).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Close", command=self._on_closing).pack(side="left", padx=10)

        self._on_report_type_selected(None)  # Initialize date entry states based on default report type

    def _on_report_type_selected(self, event):
        selected_type = self.report_type_combobox.get()
        if "Payments" in selected_type:
            # Enable date range for payments reports
            self.start_date_entry.config(state="normal")
            self.end_date_entry.config(state="normal")
        else:
            # For job status reports, date range might be less critical, but still useful
            # We'll keep them enabled for flexibility for now, but could disable if logic changes.
            self.start_date_entry.config(state="normal")
            self.end_date_entry.config(state="normal")

        self.report_text_widget.config(state="normal")
        self.report_text_widget.delete("1.0", tk.END)
        self.report_text_widget.insert("1.0", f"Select dates and click 'Generate Report' for {selected_type}.")
        self.report_text_widget.config(state="disabled")

    def _load_report(self):
        report_type = self.report_type_combobox.get()
        start_date_str = self.start_date_entry.get_date().strftime("%Y-%m-%d")
        end_date_str = self.end_date_entry.get_date().strftime("%Y-%m-%d")

        self.report_text_widget.config(state="normal")
        self.report_text_widget.delete("1.0", tk.END)
        self.report_text_widget.insert("1.0", "Generating report...")
        self.report_text_widget.config(state="disabled")

        if not _REPORTLAB_AVAILABLE:
            messagebox.showwarning("Feature Unavailable",
                                   "ReportLab library is not installed. Cannot generate PDF reports. Please install it using: pip install reportlab")
            self.report_text_widget.config(state="normal")
            self.report_text_widget.insert("1.0", "Error: ReportLab not installed. PDF generation impossible.")
            self.report_text_widget.config(state="disabled")
            return

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if start_date > end_date:
                messagebox.showerror("Date Error", "Start Date cannot be after End Date.")
                self.report_text_widget.config(state="normal")
                self.report_text_widget.delete("1.0", tk.END)
                return

            report_data = []
            report_title = ""

            if report_type == "All Survey Jobs":
                report_data = self.db_manager.get_all_survey_jobs_with_client_info_for_date_range(start_date_str,
                                                                                                  end_date_str)
                report_title = "All Survey Jobs Report"
            elif report_type == "Completed Survey Jobs":
                report_data = self.db_manager.get_survey_jobs_by_status_for_date_range("Completed", start_date_str,
                                                                                       end_date_str)
                report_title = "Completed Survey Jobs Report"
            elif report_type == "Pending Survey Jobs":
                report_data = self.db_manager.get_survey_jobs_by_status_for_date_range("Pending", start_date_str,
                                                                                       end_date_str)
                report_title = "Pending Survey Jobs Report"
            elif report_type == "Cancelled Survey Jobs":
                report_data = self.db_manager.get_survey_jobs_by_status_for_date_range("Cancelled", start_date_str,
                                                                                       end_date_str)
                report_title = "Cancelled Survey Jobs Report"
            elif report_type == "Survey Payments Report":
                report_data = self.db_manager.get_survey_payments_for_date_range(start_date_str, end_date_str)
                report_title = "Survey Payments Report"

            if not report_data:
                self.report_text_widget.config(state="normal")
                self.report_text_widget.insert("1.0", "No data found for the selected criteria.")
                self.report_text_widget.config(state="disabled")
                messagebox.showinfo("No Data", "No data found for the selected criteria and date range.")
                return

            pdf_path = self._generate_pdf_report(
                report_title,
                {'data': report_data, 'report_type': report_type},  # Pass report_type for internal logic
                report_type,
                start_date_str,
                end_date_str
            )

            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message=f"{report_type} PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, self.report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message=f"{report_type} PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, self.report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating {report_type}: {e}")
            self.report_text_widget.config(state="normal")
            self.report_text_widget.delete("1.0", tk.END)
            self.report_text_widget.insert("1.0", f"Error: {e}")
            self.report_text_widget.config(state="disabled")

    def _generate_pdf_report(self, report_title, data, report_type_key, start_date, end_date):
        if not _REPORTLAB_AVAILABLE:
            print("ReportLab not available. Cannot generate PDF.")
            return None

        file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"Survey_{report_type_key.replace(' ', '_')}_{file_timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph(f"<b>Mathenge's Real Estate Management System</b>", styles['h1']))
        story.append(Paragraph(f"<u>{report_title}</u>", styles['h2']))
        story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        report_data = data['data']

        if report_type_key in ["All Survey Jobs", "Completed Survey Jobs", "Pending Survey Jobs",
                               "Cancelled Survey Jobs"]:
            headers = ["Job ID", "Client Name", "Location", "Description", "Price", "Deadline", "Status"]
            table_data = [headers]
            for job in report_data:
                table_data.append([
                    str(job.get('job_id', '')),
                    job.get('client_name', 'N/A'),
                    job.get('location', ''),
                    job.get('description', ''),
                    f"KES {job.get('agreed_price', 0.0):.2f}",
                    job.get('deadline_date', ''),
                    job.get('status', '')
                ])

            # Define column widths: ID, Client, Location, Description (wider), Price, Deadline, Status
            col_widths = [0.7 * inch, 1.3 * inch, 1.2 * inch, 2.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),  # Dark blue header
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),  # Align price column to right
            ])

            table = Table(table_data, colWidths=col_widths)
            table.setStyle(table_style)
            story.append(table)

        elif report_type_key == "Survey Payments Report":
            headers = ["Payment ID", "Job ID", "Client Name", "Amount", "Date", "Method"]
            table_data = [headers]
            total_payments = 0.0
            for payment in report_data:
                client_info = self.db_manager.get_client_by_id(payment['client_id']) if 'client_id' in payment else {
                    'name': 'N/A'}
                table_data.append([
                    str(payment.get('payment_id', '')),
                    str(payment.get('job_id', '')),
                    client_info.get('name', 'N/A'),
                    f"KES {payment.get('amount', 0.0):.2f}",
                    payment.get('payment_date', ''),
                    payment.get('payment_method', '')
                ])
                total_payments += payment.get('amount', 0.0)

            # Define column widths
            col_widths = [1.0 * inch, 1.0 * inch, 1.5 * inch, 1.0 * inch, 1.0 * inch, 1.5 * inch]

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),  # Dark blue header
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align amount column to right
            ])

            table = Table(table_data, colWidths=col_widths)
            table.setStyle(table_style)
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(f"<b>Total Payments in Period:</b> KES {total_payments:.2f}", styles['h3']))

        try:
            doc.build(story)
            return pdf_path
        except Exception as e:
            print(f"Error building PDF: {e}")
            return None

    def _show_pdf_preview(self, pdf_path, report_text_widget):
        report_text_widget.config(state="normal")
        report_text_widget.delete("1.0", tk.END)
        if pdf_path:
            report_text_widget.insert("1.0",
                                      f"Report generated successfully at:\n{pdf_path}\n\nYou can open the folder using the 'Open Report Folder' button in the notification.")
        else:
            report_text_widget.insert("1.0", "Report generation failed. Please check for errors.")
        report_text_widget.config(state="disabled")

    def _on_closing(self):
        self.grab_release()
        self.destroy()


class EditSurveyJobForm(tk.Toplevel):
    def __init__(self, master, db_manager, job_id, refresh_callback, parent_icon_loader=None,
                 window_icon_name="edit_job.png"):
        super().__init__(master)
        self.db_manager = db_manager
        self.job_id = job_id
        self.refresh_callback = refresh_callback
        self.parent_icon_loader_ref = parent_icon_loader
        self._window_icon_ref = None  # To keep a reference to the window icon

        self.title("Edit Survey Job")
        self.resizable(False, False)
        self.grab_set()  # Make this window modal
        self.transient(master)  # Set master as parent window

        self._set_window_properties(600, 500, window_icon_name, parent_icon_loader)

        # Fetch existing job data
        self.job_data = self.db_manager.get_survey_job_by_id(self.job_id)
        if not self.job_data:
            messagebox.showerror("Error", "Selected job not found.")
            self.destroy()
            return

        self._create_widgets(parent_icon_loader)
        self._populate_fields()

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

        if parent_icon_loader and icon_name:
            self._window_icon_ref = parent_icon_loader(icon_name)
            if self._window_icon_ref:
                self.iconphoto(True, self._window_icon_ref)

    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Labels and Entry fields
        ttk.Label(main_frame, text="Client Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.client_name_var = tk.StringVar()
        # This will be read-only as client linkage shouldn't change
        ttk.Entry(main_frame, textvariable=self.client_name_var, state='readonly', width=40).grid(row=0, column=1,
                                                                                                  sticky="ew", pady=5)

        ttk.Label(main_frame, text="Property Location:").grid(row=1, column=0, sticky="w", pady=5)
        self.property_location_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.property_location_var, width=40).grid(row=1, column=1, sticky="ew",
                                                                                      pady=5)

        ttk.Label(main_frame, text="Job Description:").grid(row=2, column=0, sticky="w", pady=5)
        self.job_description_text = tk.Text(main_frame, height=4, width=30)
        self.job_description_text.grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Fee:").grid(row=3, column=0, sticky="w", pady=5)
        self.fee_var = tk.DoubleVar()
        ttk.Entry(main_frame, textvariable=self.fee_var, width=40).grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Deadline:").grid(row=4, column=0, sticky="w", pady=5)
        self.deadline_date_entry = DateEntry(main_frame, width=37, background='darkblue',
                                             foreground='white', borderwidth=2,
                                             date_pattern='yyyy-mm-dd')
        self.deadline_date_entry.grid(row=4, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Status:").grid(row=5, column=0, sticky="w", pady=5)
        self.status_var = tk.StringVar()
        self.status_options = ['Pending', 'Ongoing', 'Completed', 'Cancelled']
        ttk.OptionMenu(main_frame, self.status_var, self.status_options[0], *self.status_options).grid(row=5, column=1,
                                                                                                       sticky="ew",
                                                                                                       pady=5)

        ttk.Label(main_frame, text="Attachments Path:").grid(row=6, column=0, sticky="w", pady=5)
        self.attachments_path_var = tk.StringVar()
        self.attachments_entry = ttk.Entry(main_frame, textvariable=self.attachments_path_var, width=30)
        self.attachments_entry.grid(row=6, column=1, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self._browse_attachments,
                   image=parent_icon_loader("browse_folder_icon.png") if parent_icon_loader else None,
                   compound=tk.LEFT).grid(row=6, column=2, sticky="w", padx=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)

        save_icon = parent_icon_loader("save_icon.png") if parent_icon_loader else None
        self._save_icon_ref = save_icon  # Keep a reference
        ttk.Button(button_frame, text="Save Changes", command=self._save_changes,
                   image=save_icon, compound=tk.LEFT,
                   style='Green.TButton').pack(side=tk.LEFT, padx=5)

        cancel_icon = parent_icon_loader("cancel_icon.png") if parent_icon_loader else None
        self._cancel_icon_ref = cancel_icon  # Keep a reference
        ttk.Button(button_frame, text="Cancel", command=self.destroy,
                   image=cancel_icon, compound=tk.LEFT,
                   style='Red.TButton').pack(side=tk.LEFT, padx=5)

        main_frame.grid_columnconfigure(1, weight=1)  # Allow column 1 to expand

    def _populate_fields(self):
        # Populate client name (read-only)
        self.client_name_var.set(self.job_data['client_name'])

        # Populate other fields
        self.property_location_var.set(self.job_data['property_location'])
        self.job_description_text.delete("1.0", tk.END)
        self.job_description_text.insert("1.0", self.job_data['job_description'])
        self.fee_var.set(self.job_data['fee'])

        # Populate deadline DateEntry
        deadline_dt_obj = datetime.strptime(self.job_data['deadline'], '%Y-%m-%d %H:%M:%S')  # Assuming format
        self.deadline_date_entry.set_date(deadline_dt_obj.date())  # Set only the date part

        # Populate status dropdown
        current_status = self.job_data['status']
        if current_status in self.status_options:
            self.status_var.set(current_status)
        else:
            self.status_var.set(self.status_options[0])  # Default to first if not recognized

        self.attachments_path_var.set(self.job_data['attachments_path'] or "")

    def _browse_attachments(self):
        initial_dir = self.attachments_path_var.get()
        if not os.path.isdir(initial_dir):
            initial_dir = SURVEY_ATTACHMENTS_DIR  # Fallback to default attachments dir

        folder_path = filedialog.askdirectory(initialdir=initial_dir)
        if folder_path:
            self.attachments_path_var.set(folder_path)

    def _save_changes(self):
        try:
            # Get values from fields
            property_location = self.property_location_var.get().strip()
            job_description = self.job_description_text.get("1.0", tk.END).strip()
            fee = self.fee_var.get()
            deadline_str = self.deadline_date_entry.get_date().strftime('%Y-%m-%d %H:%M:%S')  # Ensure full timestamp
            status = self.status_var.get()
            attachments_path = self.attachments_path_var.get().strip()

            # Basic validation
            if not property_location or not job_description or fee <= 0 or not deadline_str:
                messagebox.showerror("Validation Error",
                                     "Please fill in all required fields and ensure fee is positive.")
                return

            # Use the existing client_id from the fetched job_data
            client_id = self.job_data['client_id']

            if self.db_manager.update_survey_job(
                    self.job_id, client_id, property_location, job_description, fee, deadline_str, status,
                    attachments_path
            ):
                messagebox.showinfo("Success", "Survey job updated successfully!")
                self.refresh_callback()  # Refresh the parent view's data
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to update survey job. Please check inputs.")

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid number for Fee.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
