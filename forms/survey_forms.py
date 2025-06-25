import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
from PIL import Image, ImageTk
import shutil
# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons') 

# Data and Receipts
DATA_DIR = os.path.join(BASE_DIR, 'data') # Directly use BASE_DIR here
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
os.makedirs(RECEIPTS_DIR, exist_ok=True) # Ensure receipts directory exists

try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Import Error", "The 'tkcalendar' library is not found. "
                                        "Please install it using: pip install tkcalendar")
    # Exit or disable datepicker functionality if tkcalendar is not available
    DateEntry = None # Set to None to handle gracefully if not installed

# Import ReportLab components for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    print("ReportLab not found. PDF receipt generation will be disabled.")


# Import functions and directories directly from file_manager
try:
    from utils.file_manager import save_files, SURVEY_ATTACHMENTS_DIR, get_full_path
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import file_manager: {e}. Ensure utils/file_manager.py exists.")
    save_files = None
    SURVEY_ATTACHMENTS_DIR = None
    get_full_path = None

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

class AddSurveyJobForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None,
                 window_icon_name="add_survey.png", current_user_id=None):
        super().__init__(master)

        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None

        self.add_icon_ref = None
        self.cancel_icon_ref = None
        self.attach_icon_ref = None
        self.current_user_id = current_user_id

        self.selected_files = []

        self.balance_var = tk.StringVar(self, value="0.00")

        self._set_window_properties(600, 520, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader)

        if os.name != 'nt' or not hasattr(self, '_original_wm_protocol'):
            self.protocol("WM_DELETE_WINDOW", self._on_closing)
        else:
            self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._update_balance_display()


    def _customize_title_bar(self):
        """Customizes the title bar appearance. Attempts Windows-specific
        customization, falls back to a custom Tkinter title bar."""
        try:
            if os.name == 'nt': # Windows-specific title bar customization
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
                self.title("Register New Survey Job")
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
            text="Register New Survey Job",
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
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')


    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

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
        self.entry_price.bind("<KeyRelease>", self._update_balance_display)
        row += 1

        ttk.Label(main_frame, text="Deposit (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_amount_paid = ttk.Entry(main_frame)
        self.entry_amount_paid.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.entry_amount_paid.insert(0, "0.00")
        self.entry_amount_paid.bind("<KeyRelease>", self._update_balance_display)
        row += 1

        ttk.Label(main_frame, text="Balance (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.label_balance = ttk.Label(main_frame, textvariable=self.balance_var, font=('Helvetica', 10, 'bold'), foreground='green')
        self.label_balance.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Deadline Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        if DateEntry:
            self.datepicker_deadline = DateEntry(main_frame, selectmode='day',
                                                year=datetime.now().year, month=datetime.now().month,
                                                day=datetime.now().day, date_pattern='yyyy-mm-dd')
            self.datepicker_deadline.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            default_deadline = datetime.now() + timedelta(days=365)
            self.datepicker_deadline.set_date(default_deadline)
        else:
            self.entry_deadline_fallback = ttk.Entry(main_frame)
            self.entry_deadline_fallback.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            self.entry_deadline_fallback.insert(0, (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"))
        row += 1

        ttk.Label(main_frame, text="Attachments (Max 5):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        file_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=0)

        self.listbox_files = tk.Listbox(file_frame, height=3, selectmode=tk.SINGLE)
        self.listbox_files.grid(row=0, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.listbox_files.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox_files.config(yscrollcommand=scrollbar.set)

        if parent_icon_loader:
            self.attach_icon_ref = parent_icon_loader("attach.png", size=(20, 20))

        ttk.Button(file_frame, text="Add Files", image=self.attach_icon_ref, compound=tk.LEFT, command=self._add_files).grid(row=1, column=0, columnspan=2, pady=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        if parent_icon_loader:
            self.add_icon_ref = parent_icon_loader("add_job.png", size=(20, 20))
            self.cancel_icon_ref = parent_icon_loader("cancel.png", size=(20, 20))

        ttk.Button(button_frame, text="Add Survey Job", image=self.add_icon_ref, compound=tk.LEFT, command=self._add_survey_job).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", image=self.cancel_icon_ref, compound=tk.LEFT, command=self._on_closing).pack(side="left", padx=10)

    def _add_files(self):
        filetypes = [
            ("PDF Documents", "*.pdf"),
            ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("Text Documents", "*.txt"),
            ("All Files", "*.*")
        ]

        file_paths = filedialog.askopenfilenames(
            title="Select Attachment Files",
            initialdir=os.path.expanduser("~"),
            filetypes=filetypes
        )

        if file_paths:
            self.selected_files = []
            self.listbox_files.delete(0, tk.END)

            for path in file_paths:
                if len(self.selected_files) < 5:
                    self.selected_files.append(path)
                    self.listbox_files.insert(tk.END, os.path.basename(path))
                else:
                    messagebox.showwarning("File Limit Exceeded", "You can select a maximum of 5 files.")
                    break

    def _update_balance_display(self, event=None):
        """Calculates and updates the balance display in real-time."""
        try:
            agreed_price = float(self.entry_price.get() or "0.0")
        except ValueError:
            agreed_price = 0.0

        try:
            paid_amount = float(self.entry_amount_paid.get() or "0.0")
        except ValueError:
            paid_amount = 0.0

        calculated_balance = agreed_price - paid_amount
        self.balance_var.set(f"{calculated_balance:,.2f}") # Format with commas for thousands

        if calculated_balance > 0:
            self.label_balance.config(foreground='black')
        elif calculated_balance < 0:
            self.label_balance.config(foreground='red')
        else:
            self.label_balance.config(foreground='green')

    def _generate_job_creation_receipt(self, job_info, client_info):
        """
        Generates a PDF receipt for a newly created survey job, including initial payment.
        Returns the path to the generated PDF, or None if generation fails.
        """
        if not _REPORTLAB_AVAILABLE:
            messagebox.showwarning("Feature Unavailable",
                                   "ReportLab library is not installed. Cannot generate PDF receipts. "
                                   "Please install it using: pip install reportlab")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            receipt_filename = f"Job_Creation_Receipt_Job_{job_info['job_id']}_{timestamp}.pdf"
            pdf_path = os.path.join(RECEIPTS_DIR, receipt_filename)

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Custom styles
            styles.add(ParagraphStyle(name='TitleStyle', alignment=1, fontName='Helvetica-Bold', fontSize=16, spaceAfter=10))
            styles.add(ParagraphStyle(name='HeadingStyle', alignment=0, fontName='Helvetica-Bold', fontSize=12, spaceAfter=6))
            styles.add(ParagraphStyle(name='NormalStyle', alignment=0, fontName='Helvetica', fontSize=10, spaceAfter=3))
            styles.add(ParagraphStyle(name='BoldValue', alignment=0, fontName='Helvetica-Bold', fontSize=10, spaceAfter=3))
            styles.add(ParagraphStyle(name='SignatureLine', alignment=0, fontName='Helvetica', fontSize=10, spaceBefore=40))

            story = []

            # Company Header
            story.append(Paragraph("<b>Mathenge's Real Estate Management System</b>", styles['TitleStyle']))
            story.append(Paragraph("Receipt for New Survey Job Registration", styles['h3']))
            story.append(Spacer(1, 0.2 * inch))

            # Receipt Details
            story.append(Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['NormalStyle']))
            story.append(Paragraph(f"<b>Job ID:</b> {job_info['job_id']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.1 * inch))

            # Client Details
            story.append(Paragraph("<b>Client Details:</b>", styles['HeadingStyle']))
            story.append(Paragraph(f"Name: {client_info['name']}", styles['NormalStyle']))
            story.append(Paragraph(f"Contact: {client_info['contact_info']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.2 * inch))

            # Job Details
            story.append(Paragraph("<b>Survey Job Summary:</b>", styles['HeadingStyle']))
            story.append(Paragraph(f"Location: {job_info['property_location']}", styles['NormalStyle']))
            story.append(Paragraph(f"Description: {job_info['job_description']}", styles['NormalStyle']))
            story.append(Paragraph(f"Deadline: {job_info['deadline']}", styles['NormalStyle']))
            story.append(Spacer(1, 0.1 * inch))

            # Financial Summary Table
            financial_data = [
                ['Description', 'Amount (KES)'],
                ['Agreed Total Fee', f"{job_info['fee']:,.2f}"],
                ['Deposit at Registration', f"{job_info['amount_paid']:,.2f}"],
                ['Current Balance Due', f"{job_info['balance']:,.2f}"]
            ]

            financial_table = Table(financial_data, colWidths=[3.5 * inch, 2.0 * inch])
            financial_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), # Align amounts to the right
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Make balance bold
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.green if job_info['balance'] <= 0 else colors.orange) # Color balance
            ]))
            story.append(financial_table)
            story.append(Spacer(1, 0.3 * inch))

            # Footer
            story.append(Paragraph("This receipt confirms the registration of a new survey job "
                                  "and any initial payment received.", styles['NormalStyle']))
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Thank you for your business!", styles['HeadingStyle']))
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph("_________________________", styles['SignatureLine']))
            story.append(Paragraph("Authorized Signature", styles['NormalStyle']))

            doc.build(story)
            return pdf_path

        except Exception as e:
            messagebox.showerror("Receipt Generation Error", f"An error occurred while generating the receipt: {e}")
            print(f"Error generating job creation receipt: {e}")
            return None


    def _add_survey_job(self):
        client_name = self.entry_client_name.get().strip()
        client_contact = self.entry_client_contact.get().strip()
        location = self.entry_location.get().strip()
        description = self.text_description.get("1.0", tk.END).strip()
        price_str = self.entry_price.get().strip()
        amount_paid_str = self.entry_amount_paid.get().strip()

        deadline_date_str = ""
        if DateEntry and hasattr(self, 'datepicker_deadline'):
            try:
                deadline_date_str = self.datepicker_deadline.get_date().strftime("%Y-%m-%d")
            except Exception:
                messagebox.showerror("Input Error", "Please select a valid Deadline Date.")
                return
        elif hasattr(self, 'entry_deadline_fallback'):
            deadline_date_str = self.entry_deadline_fallback.get().strip()
            try:
                datetime.strptime(deadline_date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Input Error", "Invalid date format for Deadline Date. Use YYYY-MM-DD.")
                return
        else:
            messagebox.showerror("Input Error", "Deadline Date input widget not found.")
            return

        created_at_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not all([client_name, client_contact, location, price_str, amount_paid_str, deadline_date_str]):
            messagebox.showerror("Input Error", "All required fields are necessary.")
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
            paid_amount = float(amount_paid_str)
            if paid_amount < 0:
                messagebox.showerror("Input Error", "DEPOSIT cannot be negative.")
                return
            # NEW VALIDATION: Amount Paid cannot be more than the Fee
            if paid_amount > agreed_price:
                messagebox.showerror("Input Error", "DEPOSIT cannot be more than the Agreed Fee.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for DEPOSIT. Please enter a number.")
            return

        calculated_balance = agreed_price - paid_amount

        # NEW VALIDATION: Balance should not be a negative number
        if calculated_balance < 0:
            # This should ideally not happen if paid_amount > agreed_price is caught above,
            # but as a safeguard.
            messagebox.showerror("Input Error", "Calculated Balance cannot be negative. Please check fee and amount paid.")
            return

        try:
            client = self.db_manager.get_client_by_contact_info(client_contact)
            if client:
                client_id = client['client_id']
                if client['name'] != client_name:
                    # It's better to verify the update result if it's critical
                    if not self.db_manager.update_client(client_id, name=client_name):
                         messagebox.showwarning("Database Warning", "Could not update existing client name.")
            else:
                client_id = self.db_manager.add_client(client_name, client_contact, added_by_user_id=self.current_user_id) # Ensure user ID is passed
                if not client_id:
                    messagebox.showerror("Database Error", "Failed to add new client. Contact info might already exist.")
                    return

            job_id = self.db_manager.add_survey_job(
                client_id=client_id,
                property_location=location,
                job_description=description,
                fee=agreed_price,
                deadline=deadline_date_str,
                amount_paid=paid_amount,
                balance=calculated_balance,
                status='Pending',
                attachments_path=None, # This is for other attachments, not the auto-generated receipt
                added_by_user_id=self.current_user_id,
                created_at=created_at_timestamp
            )

            if job_id:
                # Prepare job_info and client_info for receipt generation
                # You'll need to fetch client details based on client_id for the receipt.
                # Assuming your db_manager has get_client_by_id and get_survey_job_by_id
                # (even though you just added it, it's good practice for consistency)
                full_client_info = self.db_manager.get_client_by_id(client_id)
                
                # Construct job_info dictionary for the receipt generation
                # Ensure all necessary fields are included for the receipt template
                job_info_for_receipt = {
                    'job_id': job_id,
                    'client_name': full_client_info['name'], # Pass client name directly for receipt
                    'client_contact': full_client_info['contact_info'], # Pass client contact directly
                    'property_location': location,
                    'job_description': description,
                    'fee': agreed_price,
                    'amount_paid': paid_amount,
                    'balance': calculated_balance,
                    'deadline': deadline_date_str,
                    'status': 'Pending',
                    'created_at': created_at_timestamp
                }

                receipt_pdf_path = None
                try:
                    receipt_pdf_path = self._generate_job_creation_receipt(job_info_for_receipt, full_client_info)
                except Exception as e:
                    messagebox.showwarning("Receipt Generation Error", f"Failed to generate receipt PDF: {e}")
                    print(f"Error generating receipt: {e}")

                if receipt_pdf_path:
                    # Update the newly added survey job with the receipt path
                    if self.db_manager.update_survey_job_receipt_path(job_id, receipt_pdf_path):
                        # Ask user to print the receipt
                        response = messagebox.askyesno(
                            "Success & Print", 
                            f"Survey Job added with ID: {job_id} and receipt generated at:\n{receipt_pdf_path}\n\nDo you want to print this receipt?",
                            detail="Click 'Yes' to print, 'No' to close."
                        )
                        if response:
                            try:
                                # Use default system PDF viewer/printer (cross-platform approach)
                                if os.name == 'nt': # For Windows
                                    os.startfile(receipt_pdf_path, "print")
                                elif os.sys.platform == 'darwin': # For macOS
                                    subprocess.run(['open', '-a', 'Preview', '-p', receipt_pdf_path])
                                else: # For Linux/Unix
                                    subprocess.run(['lp', receipt_pdf_path]) # or 'lpr'
                                messagebox.showinfo("Print Status", "Print command sent successfully.")
                            except Exception as print_e:
                                messagebox.showwarning("Print Error", f"Could not send print command:\n{print_e}\nYou may need to print manually from {receipt_pdf_path}")
                                print(f"Error printing PDF: {print_e}")
                        else:
                            messagebox.showinfo("Success", f"Survey Job added with ID: {job_id} and receipt generated.")
                    else:
                        messagebox.showwarning("Database Update Warning", f"Survey Job added with ID: {job_id}, receipt generated but failed to save path in DB.")
                else:
                    messagebox.showwarning("Receipt Warning", f"Survey Job added with ID: {job_id}, but receipt generation failed or path was not returned.")

                # Handle other attachments
                survey_attachments_paths_str = None
                if self.selected_files:
                    if save_files and SURVEY_ATTACHMENTS_DIR:
                        try:
                            survey_attachments_paths_str = save_files(self.selected_files, SURVEY_ATTACHMENTS_DIR)
                            if survey_attachments_paths_str is None:
                                messagebox.showwarning("File Save Error", "Survey job attachments could not be saved.")
                            else:
                                self.db_manager.update_survey_job_attachments(job_id, survey_attachments_paths_str)
                                messagebox.showinfo("Attachments", "Additional attachments saved.")
                        except Exception as e:
                            messagebox.showwarning("File Save Error", f"Failed to save attachments: {e}")
                            print(f"Error saving attachments: {e}")
                    else:
                        messagebox.showwarning("File Manager Missing", "File saving functionality for attachments not available.")

                # Final success message, if no specific messages were already shown by receipt/attachments
                if not receipt_pdf_path and (not self.selected_files or survey_attachments_paths_str is None):
                     messagebox.showinfo("Success", f"Survey Job added with ID: {job_id}")

                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add survey job to the database.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            print(f"Error adding survey job: {e}")

    def _on_closing(self):
        """Handles window closing by releasing grab and destroying the window."""
        if self.master.winfo_exists(): # Check if master still exists before releasing grab
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
