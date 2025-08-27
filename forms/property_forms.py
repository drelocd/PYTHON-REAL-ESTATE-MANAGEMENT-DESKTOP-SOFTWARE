import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from tkinter import font as tkfont
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
from tkcalendar import DateEntry # Import DateEntry for the date picker



try:
    test_date = datetime.now().date()
    print(f"datetime.now().date() works! Today is: {test_date}")
except AttributeError as e:
    print(f"ERROR: datetime.now().date() failed in main.py: {e}")
    # You might want to exit here to prevent the Tkinter app from launching if this fails
    exit() 

# --- Module-level imports for ctypes, ensuring variables are always defined ---
windll = None 
byref = None
sizeof = None
c_int = None

if os.name == 'nt':
    try:
        from ctypes import windll, byref, sizeof, c_int
        print("ctypes components imported successfully on Windows.")
    except ImportError as e:
        print(f"Warning: Failed to import ctypes components (windll, byref, etc.) for Windows title bar customization: {e}")
        # Variables remain None as initialized above.
    except Exception as e: # Catch any other unexpected errors during import
        print(f"Warning: Unexpected error during ctypes import: {e}")
        # Variables remain None.
# --- End of ctypes import block ---


try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch # NEW: Import inch for column widths
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    print("Warning: ReportLab not installed. PDF generation will not work. Install with: pip install reportlab")


# Define paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROPERTY_IMAGES_DIR = os.path.join(DATA_DIR, 'images')
TITLE_DEEDS_DIR = os.path.join(DATA_DIR, 'deeds')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports') # NEW: Define REPORTS_DIR

# Ensure directories exist (might also be done in main app init)
os.makedirs(PROPERTY_IMAGES_DIR, exist_ok=True)
os.makedirs(TITLE_DEEDS_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True) # NEW: Ensure REPORTS_DIR exists


class SuccessMessage(tk.Toplevel):
    def __init__(self, master, success, message, pdf_path="", parent_icon_loader=None):
        super().__init__(master)
        self.title("Notification")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        
        self._icon_photo_ref = None # Keep strong reference to PhotoImage
        
        if parent_icon_loader:
            icon_name = "success.png" if success else "error.png"
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._icon_photo_ref = icon_image # Store strong reference
            except Exception as e:
                print(f"Failed to set icon for SuccessMessage: {e}")

        lbl = ttk.Label(self, text=message, font=('Helvetica', 10), wraplength=300, justify=tk.CENTER)
        lbl.pack(padx=20, pady=10)

        if success and pdf_path and _REPORTLAB_AVAILABLE: # Only show Open button if PDF was actually generated
            open_btn = ttk.Button(self, text="Open Report Folder", command=lambda: os.startfile(os.path.dirname(pdf_path))) # Open parent directory of PDF
            open_btn.pack(pady=5)

        ok_btn = ttk.Button(self, text="OK", command=self.destroy)
        ok_btn.pack(pady=10)

        self.update_idletasks()
        x = master.winfo_x() + master.winfo_width() // 2 - self.winfo_width() // 2
        y = master.winfo_y() + master.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")

# --- DatePicker Class ---
class DatePicker(tk.Toplevel):
    def __init__(self, master, current_date, callback, parent_icon_loader=None, window_icon_name="calendar_icon.png"):
        super().__init__(master)
        self.title("Select Date")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.callback = callback
        self.selected_date = None
        self._window_icon_ref = None # <--- Added for icon persistence

        if isinstance(current_date, str):
            try:
                self.view_date = datetime.strptime(current_date, "%Y-%m-%d")
            except ValueError:
                self.view_date = datetime.now()
        else:
            self.view_date = current_date or datetime.now()

        # Set window properties (size, position, icon)
        self._set_window_properties(250, 250, window_icon_name, parent_icon_loader)

        self._create_widgets()
        self._update_calendar()

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        # Set size first
        self.geometry(f"{width}x{height}") 

        # Position window in the center of the screen with an offset from the top
        self.update_idletasks() # Ensure window dimensions are calculated
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100 # Fixed offset from the top, adjust as desired
        self.geometry(f"+{x}+{y}")

        # Set window icon and keep a strong reference
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image # <--- Store strong reference
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self):
        # Month/Year navigation
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)

        ttk.Button(nav_frame, text="<", command=self._prev_month).pack(side="left", padx=5)
        self.month_year_label = ttk.Label(nav_frame, text="", font=("Arial", 12, "bold"))
        self.month_year_label.pack(side="left", padx=10)
        ttk.Button(nav_frame, text=">", command=self._next_month).pack(side="left", padx=5)

        # Day labels (Sun, Mon, etc.)
        days_frame = ttk.Frame(self)
        days_frame.pack(pady=5)
        for i, day in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            ttk.Label(days_frame, text=day, width=4, anchor="center").grid(row=0, column=i, padx=1, pady=1)

        # Calendar grid
        self.calendar_frame = ttk.Frame(self)
        self.calendar_frame.pack(padx=5, pady=5)

        ttk.Button(self, text="Today", command=self._select_today).pack(pady=5)

    def _update_calendar(self):
        # Clear previous day buttons
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        self.month_year_label.config(text=self.view_date.strftime("%B %Y"))

        # Get first day of the month and number of days in month
        first_day_of_month = self.view_date.replace(day=1)
        start_day_weekday = first_day_of_month.weekday()
        if start_day_weekday == 6: # If Sunday (Python's 6), make it 0 for our grid
            start_day_weekday = 0
        else: # For Mon-Sat, shift to match 0-indexed Sun
            start_day_weekday += 1

        days_in_month = (self.view_date.replace(month=self.view_date.month % 12 + 1, day=1) - timedelta(days=1)).day

        # Populate days
        row_num = 1
        col_num = start_day_weekday

        for day in range(1, days_in_month + 1):
            date_to_display = self.view_date.replace(day=day)
            
            btn_text = str(day)
            
            # Highlight today's date if it's in the current view
            is_today = (date_to_display.date() == datetime.now().date())
            
            # Highlight selected date
            is_selected = (self.selected_date and date_to_display.date() == self.selected_date.date())

            btn = ttk.Button(self.calendar_frame, text=btn_text,
                             command=lambda d=day: self._select_date(d), width=4)
            btn.grid(row=row_num, column=col_num, padx=1, pady=1)

            if is_today and is_selected:
                btn.config(style='DateSelectedToday.TButton')
            elif is_today:
                btn.config(style='DateToday.TButton')
            elif is_selected:
                btn.config(style='DateSelected.TButton')
            else:
                btn.config(style='TButton') # Default style
            
            col_num += 1
            if col_num > 6:
                col_num = 0
                row_num += 1
        
        # Define styles for the date buttons
        self.style = ttk.Style()
        self.style.configure('DateToday.TButton', background='lightblue', foreground='blue')
        self.style.map('DateToday.TButton',
                       background=[('active', 'darkblue')],
                       foreground=[('active', 'white')])
        
        self.style.configure('DateSelected.TButton', background='lightgreen', foreground='darkgreen', font=('Arial', 9, 'bold'))
        self.style.map('DateSelected.TButton',
                       background=[('active', 'darkgreen')],
                       foreground=[('active', 'white')])

        self.style.configure('DateSelectedToday.TButton', background='mediumseagreen', foreground='white', font=('Arial', 9, 'bold'))
        self.style.map('DateSelectedToday.TButton',
                       background=[('active', 'darkseagreen')],
                       foreground=[('active', 'white')])


    def _prev_month(self):
        if self.view_date.month == 1:
            self.view_date = self.view_date.replace(year=self.view_date.year - 1, month=12)
        else:
            self.view_date = self.view_date.replace(month=self.view_date.month - 1)
        self._update_calendar()

    def _next_month(self):
        if self.view_date.month == 12:
            self.view_date = self.view_date.replace(year=self.view_date.year + 1, month=1)
        else:
            self.view_date = self.view_date.replace(month=self.view_date.month + 1)
        self._update_calendar()

    def _select_date(self, day):
        self.selected_date = self.view_date.replace(day=day)
        self.callback(self.selected_date.strftime("%Y-%m-%d"))
        self.destroy()

    def _select_today(self):
        self.selected_date = datetime.now()
        self.callback(self.selected_date.strftime("%Y-%m-%d"))
        self.destroy()


class AddPropertyForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, user_id, parent_icon_loader=None,window_icon_name="add_property.png"):
        super().__init__(master)
        self.title("Add New Property")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self._window_icon_ref = None  # For icon persistence

        self.selected_title_images = []
        self.selected_property_images = []
        self.user_id = user_id
        
        # Store references to button icons
        self._btn_title_img_icon = None
        self._btn_prop_img_icon = None
        self._add_property_icon = None
        self._cancel_add_prop_icon = None

        # Set window properties and customize title bar
        self._set_window_properties(700, 500, window_icon_name, parent_icon_loader)
        self._customize_title_bar()
        self.all_clients = self._fetch_clients()

        self._create_widgets(parent_icon_loader)

    def _fetch_clients(self):
        """Fetches all existing client names from the database."""
        try:
            # Assumes db_manager.get_all_clients() returns a list of dictionaries
            # like [{'name': 'Client A', ...}, {'name': 'Client B', ...}]
            self.all_clients_data = self.db_manager.get_all_clients()
            self.all_clients_data.sort(key=lambda x: x['name'])
            
            # Extract only the 'name' from each dictionary
            client_names = [client['name'] for client in self.all_clients_data]
            
            return client_names
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch client list: {e}")
            return []

    def _on_client_select(self, event):
        selected_name = self.client_name_var.get()
        selected_client = next(
            (client for client in self.all_clients_data if client['name'] == selected_name),
        )
        if selected_client:
            self.entry_contact.delete(0, tk.END)
            self.entry_contact.insert(0, selected_client['contact_info'])

    def _on_contact_edit(self, event):
        current_name = self.client_name_var.get()
        current_contact = self.entry_contact.get()
        matching_client = next(
            (client for client in self.all_clients_data if client['name'] == current_name),
            None
        )
        if matching_client and matching_client['contact_info'] != current_contact:
            self.client_name_var.set('')  # Clear client name if contact info is edited


    def _update_client_list(self, event=None):
        """Updates the Combobox dropdown based on the user's input."""
        current_text = self.client_name_var.get()
        if current_text == '':
            self.client_combobox['values'] = self.all_clients
        else:
            filtered_clients = [
                client for client in self.all_clients
                if current_text.lower() in client.lower()
            ]
            self.client_combobox['values'] = filtered_clients

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=50)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text="Add New Property",
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

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
        self.all_clients_data = []
        self.all_clients = self._fetch_clients()

        row = 0

        # Property Type Selection
        ttk.Label(main_frame, text="Property Type:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.property_type_var = tk.StringVar(value="Block")
        self.property_type_combobox = ttk.Combobox(main_frame, textvariable=self.property_type_var, values=["Block", "Lot"], state="readonly")
        self.property_type_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Client Name:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.client_name_var = tk.StringVar()
        self.client_combobox = ttk.Combobox(main_frame, textvariable=self.client_name_var)
        self.client_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        self.client_combobox['values'] = self.all_clients  # Populate with initial list
        self.client_combobox.bind('<KeyRelease>', self._update_client_list)  # Bind for real-time filtering
        self.client_combobox.bind('<<ComboboxSelected>>', self._on_client_select)
        row += 1
        
        ttk.Label(main_frame, text="Contact Info:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_contact = ttk.Entry(main_frame, width=40)
        self.entry_contact.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        self.entry_contact.bind('<KeyRelease>', self._on_contact_edit)
        row += 1

        ttk.Label(main_frame, text="Title Deed Number:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_title_deed = ttk.Entry(main_frame, width=40)
        self.entry_title_deed.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Location:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_location = ttk.Entry(main_frame, width=40)
        self.entry_location.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Size (Acres):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_size = ttk.Entry(main_frame, width=40)
        self.entry_size.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        self.text_description = tk.Text(main_frame, width=40, height=5, wrap=tk.WORD)
        self.text_description.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Asking Price (KES):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_price = ttk.Entry(main_frame, width=40)
        self.entry_price.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        # Buttons with icons
        if parent_icon_loader:
            self._btn_title_img_icon = parent_icon_loader("folder_open.png", size=(20, 20))
            self._btn_prop_img_icon = parent_icon_loader("folder_open.png", size=(20, 20))
            self._add_property_icon = parent_icon_loader("add_property.png", size=(20, 20))
            self._cancel_add_prop_icon = parent_icon_loader("cancel.png", size=(20, 20))

        ttk.Label(main_frame, text="Attach Title Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_title_img = ttk.Button(main_frame, text="Browse...", image=self._btn_title_img_icon, compound=tk.LEFT, command=self._select_title_images)
        btn_title_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_title_img.image = self._btn_title_img_icon 
        self.lbl_title_image_path = ttk.Label(main_frame, text="No file(s) selected")
        self.lbl_title_image_path.grid(row=row + 1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        ttk.Label(main_frame, text="Attach Property Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_prop_img = ttk.Button(main_frame, text="Browse...", image=self._btn_prop_img_icon, compound=tk.LEFT, command=self._select_property_images)
        btn_prop_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_prop_img.image = self._btn_prop_img_icon
        self.lbl_property_image_path = ttk.Label(main_frame, text="No file(s) selected")
        self.lbl_property_image_path.grid(row=row + 1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        ttk.Label(main_frame, text="Status:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.status_combobox = ttk.Combobox(main_frame, values=["Available"], state="readonly", width=37)
        self.status_combobox.set("Available")
        self.status_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        add_btn = ttk.Button(button_frame, text="Add Property", image=self._add_property_icon, compound=tk.LEFT, command=self._add_property)
        add_btn.pack(side="left", padx=5)
        add_btn.image = self._add_property_icon

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_add_prop_icon, compound=tk.LEFT, command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_add_prop_icon

    def _select_title_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Title Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            self.selected_title_images = list(file_paths)
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_title_image_path.config(text=display_text)

    def _select_property_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Property Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            self.selected_property_images = list(file_paths)
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_property_image_path.config(text=display_text)

    def _save_images(self, source_paths, destination_dir):
        """
        Saves multiple images to the specified directory and returns a
        comma-separated string of their relative paths.
        """
        saved_paths = []
        if not source_paths:
            return None

        for source_path in source_paths:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            filename, file_extension = os.path.splitext(os.path.basename(source_path))
            new_filename = f"{filename}_{timestamp}{file_extension}"
            destination_path = os.path.join(destination_dir, new_filename)

            try:
                shutil.copy2(source_path, destination_path)
                relative_path = os.path.relpath(destination_path, DATA_DIR).replace("\\", "/")
                saved_paths.append(relative_path)
            except Exception as e:
                messagebox.showerror("Image Save Error", f"Failed to save image {source_path}: {e}")
                return None

        return ",".join(saved_paths)

    def _add_property(self):
        # Retrieve all data from the form fields
        property_type = self.property_type_combobox.get().strip()  # Retrieve the selected property type
        client_name = self.client_name_var.get().strip()  # Get the text from the combobox
        contact = self.entry_contact.get().strip()
        title_deed = self.entry_title_deed.get().strip()
        location = self.entry_location.get().strip()
        size_str = self.entry_size.get().strip()
        description = self.text_description.get("1.0", "end-1c").strip()
        price_str = self.entry_price.get().strip()
        status = self.status_combobox.get().strip()

        # Input validation
        if not client_name or not title_deed or not location or not size_str or not price_str:
            messagebox.showerror("Input Error", "Client Name, Title Deed Number, Location, Size, and Asking Price are required.")
            return

        try:
            size = float(size_str)
            if size <= 0:
                messagebox.showerror("Input Error", "Size must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Size. Please enter a number.")
            return

        try:
            price = float(price_str)
            if price <= 0:
                messagebox.showerror("Input Error", "Asking Price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Asking Price. Please enter a number.")
            return

        # Save images and get their paths
        saved_title_image_paths_str = self._save_images(self.selected_title_images, TITLE_DEEDS_DIR)
        saved_property_image_paths_str = self._save_images(self.selected_property_images, PROPERTY_IMAGES_DIR)

        try:
            # Call the add_property method with the correct parameters, including the property_type
            property_id_or_status = self.db_manager.add_property(
                property_type=property_type, # Pass the new parameter
                title_deed_number=title_deed, 
                location=location, 
                size=size, 
                description=description, 
                owner=client_name,
                contact=contact,
                price=price,
                image_paths=saved_property_image_paths_str, 
                title_image_paths=saved_title_image_paths_str, 
                status=status, 
                added_by_user_id=self.user_id
            )

            if property_id_or_status is not None:
                if isinstance(property_id_or_status, int):
                    messagebox.showinfo("Success", f"Property '{title_deed}' added successfully!")
                else:
                    messagebox.showinfo("Success", f"Property '{title_deed}' processed successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Duplicate Error", "A property with this Title Deed Number is already available in the database. Cannot add duplicate active property.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


class AddPropertyForTransferForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, user_id, parent_icon_loader=None,window_icon_name="add_property.png"):
        super().__init__(master)
        self.title("Add New Property For Transfer")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self._window_icon_ref = None  # For icon persistence

        self.selected_title_images = []
        self.selected_property_images = []
        self.user_id = user_id
        

        # Store references to button icons
        self._btn_title_img_icon = None
        self._btn_prop_img_icon = None
        self._add_property_icon = None
        self._cancel_add_prop_icon = None

        # Set window properties and customize title bar
        self._set_window_properties(700, 450, window_icon_name, parent_icon_loader)
        self._customize_title_bar()
        self.all_clients = self._fetch_clients()

        self._create_widgets(parent_icon_loader)

    def _fetch_clients(self):
        """Fetches all existing client names from the database."""
        try:
            # Assumes db_manager.get_all_clients() returns a list of dictionaries
            # like [{'name': 'Client A', ...}, {'name': 'Client B', ...}]
            clients_data = self.db_manager.get_all_clients()
            
            # Extract only the 'name' from each dictionary
            client_names = [client['name'] for client in clients_data]
            
            return sorted(client_names)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch client list: {e}")
            return []
    def _update_client_list(self, event=None):
        """Updates the Combobox dropdown based on the user's input."""
        current_text = self.client_name_var.get()
        if current_text == '':
            self.client_combobox['values'] = self.all_clients
        else:
            filtered_clients = [
                client for client in self.all_clients
                if current_text.lower() in client.lower()
            ]
            self.client_combobox['values'] = filtered_clients


    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=50)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text="Add New Property For Transfer",
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

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
        ttk.Label(main_frame, text="Client Name:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.client_name_var = tk.StringVar()
        self.client_combobox = ttk.Combobox(main_frame, textvariable=self.client_name_var)
        self.client_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        self.client_combobox['values'] = self.all_clients  # Populate with initial list
        self.client_combobox.bind('<KeyRelease>', self._update_client_list) # Bind for real-time filtering
        row += 1
       
        ttk.Label(main_frame, text="Contact Info:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_contact = ttk.Entry(main_frame, width=40)
        self.entry_contact.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Title Deed Number:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_title_deed = ttk.Entry(main_frame, width=40)
        self.entry_title_deed.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Location:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_location = ttk.Entry(main_frame, width=40)
        self.entry_location.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Size (Acres):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_size = ttk.Entry(main_frame, width=40)
        self.entry_size.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        self.text_description = tk.Text(main_frame, width=40, height=5, wrap=tk.WORD)
        self.text_description.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        # Buttons with icons
        if parent_icon_loader:
            self._btn_title_img_icon = parent_icon_loader("folder_open.png", size=(20,20))
            self._btn_prop_img_icon = parent_icon_loader("folder_open.png", size=(20,20))
            self._add_property_icon = parent_icon_loader("add_property.png", size=(20,20))
            self._cancel_add_prop_icon = parent_icon_loader("cancel.png", size=(20,20))

        ttk.Label(main_frame, text="Attach Title Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_title_img = ttk.Button(main_frame, text="Browse...", image=self._btn_title_img_icon, compound=tk.LEFT, command=self._select_title_images)
        btn_title_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_title_img.image = self._btn_title_img_icon 
        self.lbl_title_image_path = ttk.Label(main_frame, text="No file(s) selected")
        self.lbl_title_image_path.grid(row=row+1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        ttk.Label(main_frame, text="Attach Property Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_prop_img = ttk.Button(main_frame, text="Browse...", image=self._btn_prop_img_icon, compound=tk.LEFT, command=self._select_property_images)
        btn_prop_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_prop_img.image = self._btn_prop_img_icon
        self.lbl_property_image_path = ttk.Label(main_frame, text="No file(s) selected")
        self.lbl_property_image_path.grid(row=row+1, column=1, sticky="w", padx=5, pady=0)
        row += 2


        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        add_btn = ttk.Button(button_frame, text="Add Property", image=self._add_property_icon, compound=tk.LEFT, command=self._add_property)
        add_btn.pack(side="left", padx=5)
        add_btn.image = self._add_property_icon

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_add_prop_icon, compound=tk.LEFT, command=self.cancel)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_add_prop_icon

    def _select_title_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Title Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            self.selected_title_images = list(file_paths)
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_title_image_path.config(text=display_text)

    def _select_property_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Property Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            self.selected_property_images = list(file_paths)
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_property_image_path.config(text=display_text)

    def _save_images(self, source_paths, destination_dir):
        """
        Saves multiple images to the specified directory and returns a
        comma-separated string of their relative paths.
        """
        saved_paths = []
        if not source_paths:
            return None

        for source_path in source_paths:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            filename, file_extension = os.path.splitext(os.path.basename(source_path))
            new_filename = f"{filename}_{timestamp}{file_extension}"
            destination_path = os.path.join(destination_dir, new_filename)

            try:
                shutil.copy2(source_path, destination_path)
                relative_path = os.path.relpath(destination_path, DATA_DIR).replace("\\", "/")
                saved_paths.append(relative_path)
            except Exception as e:
                messagebox.showerror("Image Save Error", f"Failed to save image {source_path}: {e}")
                return None

        return ",".join(saved_paths)

    def cancel(self):
        self.destroy()

    def _add_property(self):
        # Retrieve all data from the form fields
        client_name = self.client_name_var.get().strip()  # Get the text from the combobox
        contact = self.entry_contact.get().strip()
        title_deed = self.entry_title_deed.get().strip()
        location = self.entry_location.get().strip()
        size_str = self.entry_size.get().strip()
        description = self.text_description.get("1.0", "end-1c").strip()

        # Input validation
        if not client_name or not title_deed or not location or not size_str:
            messagebox.showerror("Input Error", "Client Name, Title Deed Number, Location, and Size are required.")
            return

        try:
            size = float(size_str)
            if size <= 0:
                messagebox.showerror("Input Error", "Size must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Size. Please enter a number.")
            return

        # Save images and get their paths
        saved_title_image_paths_str = self._save_images(self.selected_title_images, TITLE_DEEDS_DIR)
        saved_property_image_paths_str = self._save_images(self.selected_property_images, PROPERTY_IMAGES_DIR)

        try:
            # Call the add_property method with the correct parameters, including the client_name
            property_id_or_status = self.db_manager.add_propertyForTransfer(
                title_deed_number=title_deed, 
                location=location, 
                size=size, 
                description=description, 
                owner=client_name,  # Pass the client_name here
                contact=contact,
                image_paths=saved_property_image_paths_str, 
                title_image_paths=saved_title_image_paths_str, 
                added_by_user_id=self.user_id
            )

            if property_id_or_status is not None:
                if isinstance(property_id_or_status, int):
                    messagebox.showinfo("Success", f"Property '{title_deed}' added successfully!")
                else:
                    messagebox.showinfo("Success", f"Property '{title_deed}' processed successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Duplicate Error", "A property with this Title Deed Number is already available in the database. Cannot add duplicate active property.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


class EditPropertyForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, property_data, parent_icon_loader=None, window_icon_name="edit.png"):
        super().__init__(master)
        self.title(f"Edit Property: {property_data['title_deed_number']}")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.property_data = property_data
        self._window_icon_ref = None

        # Initialize image lists
        self.selected_title_images = [path.strip() for path in property_data['title_image_paths'].split(',') if path.strip()] if property_data['title_image_paths'] else []
        self.selected_property_images = [path.strip() for path in property_data['image_paths'].split(',') if path.strip()] if property_data['image_paths'] else []

        # Icon references
        self._btn_title_img_icon = None
        self._btn_prop_img_icon = None
        self._update_property_icon = None
        self._cancel_edit_prop_icon = None

        # Set window properties and customize title bar
        self._set_window_properties(600, 400, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader)
        self._populate_fields()

        # For custom title bar dragging
        self._start_x = 0
        self._start_y = 0

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text=f"Edit Property: {self.property_data['title_deed_number']}",
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

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
        ttk.Label(main_frame, text="Title Deed Number:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_title_deed = ttk.Entry(main_frame, width=40)
        self.entry_title_deed.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Location:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_location = ttk.Entry(main_frame, width=40)
        self.entry_location.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Size (Acres):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_size = ttk.Entry(main_frame, width=40)
        self.entry_size.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        self.text_description = tk.Text(main_frame, width=40, height=5, wrap=tk.WORD)
        self.text_description.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(main_frame, text="Asking Price (KES):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.entry_price = ttk.Entry(main_frame, width=40)
        self.entry_price.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        if parent_icon_loader:
            self._btn_title_img_icon = parent_icon_loader("folder_open.png", size=(20,20))
            self._btn_prop_img_icon = parent_icon_loader("folder_open.png", size=(20,20))
            self._update_property_icon = parent_icon_loader("save.png", size=(20,20))
            self._cancel_edit_prop_icon = parent_icon_loader("cancel.png", size=(20,20))

        ttk.Label(main_frame, text="Attach Title Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_title_img = ttk.Button(main_frame, text="Browse...", image=self._btn_title_img_icon, compound=tk.LEFT, command=self._select_title_images)
        btn_title_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_title_img.image = self._btn_title_img_icon
        self.lbl_title_image_path = ttk.Label(main_frame, text="No file(s) selected" if not self.selected_title_images else f"{len(self.selected_title_images)} existing image(s)")
        self.lbl_title_image_path.grid(row=row+1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        ttk.Label(main_frame, text="Attach Property Image(s):").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        btn_prop_img = ttk.Button(main_frame, text="Browse...", image=self._btn_prop_img_icon, compound=tk.LEFT, command=self._select_property_images)
        btn_prop_img.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        btn_prop_img.image = self._btn_prop_img_icon
        self.lbl_property_image_path = ttk.Label(main_frame, text="No file(s) selected" if not self.selected_property_images else f"{len(self.selected_property_images)} existing image(s)")
        self.lbl_property_image_path.grid(row=row+1, column=1, sticky="w", padx=5, pady=0)
        row += 2

        ttk.Label(main_frame, text="Status:").grid(row=row, column=0, sticky="w", pady=2, padx=5)
        self.status_combobox = ttk.Combobox(main_frame, values=["Available", "Sold"], state="readonly", width=37)
        self.status_combobox.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        update_btn = ttk.Button(button_frame, text="Update Property", image=self._update_property_icon, compound=tk.LEFT, command=self._update_property)
        update_btn.pack(side="left", padx=5)
        update_btn.image = self._update_property_icon

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_edit_prop_icon, compound=tk.LEFT, command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_edit_prop_icon

    def _populate_fields(self):
        """Populates the form fields with existing property data."""
        self.entry_title_deed.insert(0, self.property_data.get('title_deed_number', ''))
        self.entry_location.insert(0, self.property_data.get('location', ''))
        self.entry_size.insert(0, str(self.property_data.get('size', '')))
        self.text_description.insert("1.0", tk.END, self.property_data.get('description', '')) # Changed to tk.END for consistency
        self.entry_price.insert(0, str(self.property_data.get('price', '')))
        self.status_combobox.set(self.property_data.get('status', 'Available'))

        # Display current attached file names for visual feedback
        if self.selected_title_images:
            # Filter out empty strings that might result from split(',') on None or empty path
            valid_title_images = [path for path in self.selected_title_images if path.strip()]
            if valid_title_images:
                self.lbl_title_image_path.config(text=f"{len(valid_title_images)} file(s) selected")
        if self.selected_property_images:
            valid_prop_images = [path for path in self.selected_property_images if path.strip()]
            if valid_prop_images:
                self.lbl_property_image_path.config(text=f"{len(valid_prop_images)} file(s) selected")


    def _select_title_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Title Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            # Store full paths temporarily, _save_images will handle copying and relative paths
            self.selected_title_images = list(file_paths) 
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_title_image_path.config(text=display_text)

    def _select_property_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Property Image(s)",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if file_paths:
            self.selected_property_images = list(file_paths)
            display_text = f"{len(file_paths)} file(s) selected"
            if len(file_paths) > 0:
                display_text += f" ({os.path.basename(file_paths[-1])})"
            self.lbl_property_image_path.config(text=display_text)

    def _save_images(self, source_paths, destination_dir):
        """
        Saves new images to the specified directory and returns a
        comma-separated string of their relative paths.
        This version correctly handles existing paths (which are relative)
        and new paths (which are absolute from filedialog).
        """
        saved_paths = []
        if not source_paths:
            return None

        for source_path in source_paths:
            # If the path is already a relative path within DATA_DIR, it means it's an existing image.
            # We assume relative paths stored in DB are relative to DATA_DIR.
            if source_path.startswith(('images/', 'deeds/')) or os.path.exists(os.path.join(DATA_DIR, source_path)):
                # Validate it exists as a full path
                full_existing_path = os.path.join(DATA_DIR, source_path)
                if os.path.exists(full_existing_path):
                    saved_paths.append(source_path) # It's an existing, already saved image, just keep its path
                    continue
            
            # If it's a new image (from file dialog, likely absolute path) or not a valid existing relative path, save it
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            filename, file_extension = os.path.splitext(os.path.basename(source_path))
            new_filename = f"{filename}_{timestamp}{file_extension}"
            destination_path = os.path.join(destination_dir, new_filename)

            try:
                shutil.copy2(source_path, destination_path)
                relative_path = os.path.relpath(destination_path, DATA_DIR).replace("\\", "/")
                saved_paths.append(relative_path)
            except Exception as e:
                messagebox.showerror("Image Save Error", f"Failed to save image {source_path}: {e}")
                # Don't return None immediately, try to save other images
                # but log the error for this specific file.
                continue 

        return ",".join(saved_paths) if saved_paths else None


    def _update_property(self):
        property_id = self.property_data['property_id']
        title_deed = self.entry_title_deed.get().strip()
        location = self.entry_location.get().strip()
        size_str = self.entry_size.get().strip()
        description = self.text_description.get("1.0", tk.END).strip()
        price_str = self.entry_price.get().strip()
        new_status = self.status_combobox.get().strip() # Get the new status from the combobox

        # --- VALIDATION CHECKS (UNCHANGED) ---
        if not title_deed or not location or not size_str or not price_str:
            messagebox.showerror("Input Error", "Title Deed Number, Location, Size, and Asking Price are required.")
            return

        try:
            size = float(size_str)
            if size <= 0:
                messagebox.showerror("Input Error", "Size must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Size. Please enter a number.")
            return

        try:
            price = float(price_str)
            if price <= 0:
                messagebox.showerror("Input Error", "Asking Price must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for Asking Price. Please enter a number.")
            return

        # --- SYSTEM INTEGRITY CHECK: Prevent updating status to 'Sold' ---
        # Get the current status from the original property data loaded when the form opened
        current_status = self.property_data.get('status', 'Available') # Default to 'Available' if not found

        if new_status.lower() == 'sold' and current_status.lower() != 'sold':
            # If the user is trying to change the status to 'Sold'
            # and the current status is NOT already 'Sold'
            messagebox.showerror(
                "Integrity Violation",
                "Property status can only be marked as 'Sold' through the dedicated Sales form to ensure accurate sales records."
            )
            return
        # --- END INTEGRITY CHECK ---

        # Handle image updates: only save new selections, retain existing if not re-selected
        saved_title_image_paths_str = self._save_images(self.selected_title_images, TITLE_DEEDS_DIR)
        saved_property_image_paths_str = self._save_images(self.selected_property_images, PROPERTY_IMAGES_DIR)

        try:
            success = self.db_manager.update_property(
                property_id,
                title_deed_number=title_deed,
                location=location,
                size=size,
                description=description,
                price=price,
                image_paths=saved_property_image_paths_str,
                title_image_paths=saved_title_image_paths_str,
                status=new_status # Use the new_status, which has been validated
            )
            if success:
                messagebox.showinfo("Success", f"Property '{title_deed}' updated successfully!")
                self.refresh_callback() # Refresh the main view or the properties list
                self.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to update property in the database. Title Deed Number might conflict or another DB error occurred.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

class SellPropertyLandingForm(tk.Toplevel):
    """
    A small modal window that provides an option to sell either a Block or a Lot.
    It remains persistent until closed and customizes its appearance.
    """
    def __init__(self, master, db_manager, refresh_callback, user_id=None, parent_icon_loader=None, window_icon_name="manage_sales.png"):
        """
        Initializes the SellPropertyLandingForm.
        
        Args:
            master (tk.Tk or tk.Toplevel): The parent window.
            db_manager (DBManager): An instance of the database manager.
            refresh_callback (callable): A function to call to refresh the main view.
            user_id (str): The unique ID of the currently logged-in user.
            parent_icon_loader (callable, optional): A function to load window icons.
            window_icon_name (str, optional): The filename for the window icon.
        """
        super().__init__(master)
        self.title("Sell Property")
        self.resizable(False, False)
        self.grab_set()  # Make the window modal
        self.transient(master)

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.user_id = user_id
        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None  # To prevent garbage collection of the icon image

        # Store references to button icons to prevent garbage collection
        self._sell_block_icon = None
        self._sell_lot_icon = None
        self._sell_lot_from_block_icon = None
        self._cancel_icon = None

        self._set_window_properties(400, 150, window_icon_name, parent_icon_loader)
        self._customize_title_bar()
        self._create_widgets()

    def _customize_title_bar(self):
        """Customizes the title bar appearance for Windows, with a fallback."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text="Sell Property",
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10, 'bold')
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

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

    def _create_widgets(self):
        """Creates the main widgets for the form."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        info_label = ttk.Label(
            main_frame,
            text="Select the type of property you want to sell:",
            font=('Helvetica', 12)
        )
        info_label.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        # Load icons for buttons
        if self.parent_icon_loader:
            self._sell_block_icon = self.parent_icon_loader("sell_block.png", size=(20, 20))
            self._sell_lot_icon = self.parent_icon_loader("sell_lot.png", size=(20, 20))
            
        # Sell Block button
        sell_block_btn = ttk.Button(
            button_frame,
            text="Sell Block",
            image=self._sell_block_icon,
            compound=tk.LEFT,
            command=self._open_sell_block_form
        )
        sell_block_btn.pack(side="left", padx=10)

        # Sell Lot button
        sell_lot_btn = ttk.Button(
            button_frame,
            text="Sell Lot",
            image=self._sell_lot_icon,
            compound=tk.LEFT,
            command=self._open_sell_lot_form
        )
        sell_lot_btn.pack(side="left", padx=10)


    def _show_landing_form(self):
        """Shows the landing form after a child form is closed."""
        self.deiconify()

    def _open_sell_block_form(self):
        """Hides this window and opens the Sell Block form."""
        self.withdraw()
        try:
            # Pass a callback to the child form so it can re-show the landing form
            SellPropertyFormBlock(
                self.master,
                self.db_manager,
                self.user_id,
                self.refresh_callback,
                on_close_callback=self._show_landing_form,  # This is the on_close_callback
                parent_icon_loader=self.parent_icon_loader  # This is the parent_icon_loader
        )
        except NameError:
            messagebox.showerror(
                "Error",
                "The SellPropertyFormBlock class is not found. Please ensure it is imported correctly."
            )
            self._show_landing_form() # Show the form on error
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self._show_landing_form() # Show the form on error

    def _open_sell_lot_form(self):
        """Hides this window and opens the Sell Lot form."""
        self.withdraw()
        try:
            # Pass a callback to the child form
            SellPropertyFormLot(
            self.master,
            self.db_manager,
            self.user_id,
            self.refresh_callback,
            on_close_callback=self._show_landing_form,  # This is the on_close_callback
            parent_icon_loader=self.parent_icon_loader  # This is the parent_icon_loader
        )
        except NameError:
            messagebox.showerror(
                "Error",
                "The SellPropertyFormLot class is not found. Please ensure it is imported correctly."
            )
            self._show_landing_form()
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self._show_landing_form()
            
try:
    from ctypes import windll, byref, sizeof, c_int
    has_ctypes = True
except (ImportError, OSError):
    has_ctypes = False

class CashPaymentWindow(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, selected_property, buyer_name, buyer_contact, payment_mode, refresh_callback, icon_loader):
        super().__init__(master)
        self.db_manager = db_manager
        self.user_id = user_id
        self.selected_property = selected_property
        self.buyer_name = buyer_name
        self.buyer_contact = buyer_contact
        self.payment_mode = payment_mode
        self.refresh_callback = refresh_callback
        self.icon_loader = icon_loader
        self.grab_set()
        self.transient(master)
        
        # New attributes for custom title bar
        self._start_x = 0
        self._start_y = 0

        self.price = self.selected_property['price']
        self._amount_paid_var = tk.StringVar(value=f"{self.price:,.2f}")
        self._discount_var = tk.StringVar(value="0.00")
        self._balance_var = tk.StringVar(value="0.00")

        # Call the new customization methods
        self._set_window_properties(400, 450, "cash.png")
        self._customize_title_bar()
        
        # Note: _create_widgets will now be adjusted to not have its own header frame
        # as it will be handled by _customize_title_bar
        self._create_widgets()
        
        # You'll need to add _update_receipt_button_state() here if you have it
        # self._update_receipt_button_state()

    def _set_window_properties(self, width, height, icon_name):
        """Sets the window size, position, and icon based on the master window."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x = master_x + (master_width // 2) - (width // 2)
        y = master_y + (master_height // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        self.title("Cash Payment")
        if self.icon_loader and icon_name:
            try:
                icon_image = self.icon_loader(icon_name, size=(20, 20))
                self.iconphoto(False, icon_image)
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    # Copy these methods directly from your SellPropertyFormLot class
    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        if has_ctypes and os.name == 'nt':
            try:
                # DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102 -> BGR: 102, 51, 0)
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white (RGB: 255, 255, 255 -> BGR: 255, 255, 255)
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")
                self._create_custom_title_bar()
        else:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self):
        # Remove the old header_frame and its contents, as the title bar is now a custom one
        # The new title bar is created and packed in _customize_title_bar()
        
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Your existing widget creation code goes here...
        # ... (Buyer Info, Property Details, Payment Details, and Buttons)
        
        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Details", padding=5)
        buyer_info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(buyer_info_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_name, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text="Contact:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_contact, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=2, padx=5)
        prop_info_frame = ttk.LabelFrame(main_frame, text="Property Details", padding=5)
        prop_info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(prop_info_frame, text="Property Title Deed:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text=self.selected_property['title_deed_number'], font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text="Property Price (KES):").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text=f"{self.price:,.2f}", font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=2, padx=5)
        payment_frame = ttk.LabelFrame(main_frame, text="Payment Details", padding=5)
        payment_frame.pack(fill=tk.X, pady=5)
        ttk.Label(payment_frame, text="Amount Paid (KES):").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.entry_amount_paid = ttk.Entry(payment_frame, textvariable=self._amount_paid_var)
        self.entry_amount_paid.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        self.entry_amount_paid.bind("<Double-Button-1>", lambda event: "break")
        ttk.Label(payment_frame, text="Discount (KES):").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.entry_discount = ttk.Entry(payment_frame, textvariable=self._discount_var)
        self.entry_discount.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        self.entry_discount.bind("<Double-Button-1>", lambda event: "break")
        button_frame = ttk.Frame(main_frame, padding=5)
        button_frame.pack(fill="x", pady=10)
        ttk.Button(button_frame, text="Sell", command=self._sell_property, style='Green.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel, style='Red.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    
    def _sell_property(self):
        if not self.selected_property:
            messagebox.showwarning("Validation Error", "Please select a property to sell.")
            return

        buyer_name = self.buyer_name.strip()
        buyer_contact = self.buyer_contact.strip()
        payment_mode = self.payment_mode
        amount_paid_str = self.entry_amount_paid.get().strip()
        discount_str = self.entry_discount.get().strip()
        client_status = 'active'
        added_by_user_id = self.user_id

        if not buyer_name or not buyer_contact or not amount_paid_str:
            messagebox.showerror("Input Error", "Buyer Name, Contact Info, and Amount Paid are required.")
            return

        try:
            amount_paid_input = float(amount_paid_str) # Amount the user intends to pay
            discount = float(discount_str) if discount_str else 0.0
            if amount_paid_input < 0 or discount < 0:
                messagebox.showerror("Input Error", "Amount Paid and Discount cannot be negative.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid numeric input for Amount Paid or Discount.")
            return

        try:
            original_price = self.selected_property['price']
            
            # Calculate the price after discount
            net_price_after_discount = original_price - discount
            
            # --- MODIFICATION START ---
            # Error if discount makes net price negative
            if net_price_after_discount < 0:
                messagebox.showerror(
                    "Input Error", 
                    f"Discount (KES {discount:,.2f}) cannot make the property's net price negative. "
                    f"Original Price: KES {original_price:,.2f}. Please adjust the discount."
                )
                return # Stop transaction

            # Check for overpayment and refuse to proceed
            if amount_paid_input > net_price_after_discount:
                messagebox.showerror(
                    "Input Error", 
                    f"Amount paid (KES {amount_paid_input:,.2f}) cannot exceed the property's net price "
                    f"after discount (KES {net_price_after_discount:,.2f}). Please adjust the amount paid."
                )
                return # Stop transaction
            
            # If we reach here, input is valid: amount_paid_input is not negative,
            # discount is not negative, net_price_after_discount is not negative,
            # and amount_paid_input does not exceed net_price_after_discount.
            
            amount_paid_to_record = amount_paid_input # Now, it's safe to record the input amount
            balance = net_price_after_discount - amount_paid_to_record
            # --- MODIFICATION END ---

        except Exception as e:
            messagebox.showerror("Calculation Error", f"Error calculating sale details: {e}")
            return

        client_data = self.db_manager.get_client_by_contact_info(buyer_contact)
        if client_data:
            client_id = client_data['client_id']
            if client_data['name'] != buyer_name:
                self.db_manager.update_client(client_id, name=buyer_name)
        else:
            client_id = self.db_manager.add_client(buyer_name, buyer_contact,client_status, added_by_user_id)
            if not client_id:
                messagebox.showerror("Database Error", "Failed to add new client.")
                return


        transaction_id = self.db_manager.add_transaction(
            self.selected_property['property_id'],
            client_id,
            payment_mode,
            amount_paid_to_record, # Use the validated and accepted amount here
            discount,
            balance,                 # This balance is now calculated from valid inputs
            None
        )

        if transaction_id:
            # Set property status to 'Sold' if the transaction is successful
            self.db_manager.update_property(self.selected_property['property_id'], status='Sold')

            if messagebox.askyesno("Generate Receipt?", "Transaction recorded. Do you want to generate a receipt now?"):
                self._generate_receipt_from_id(transaction_id)

            messagebox.showinfo("Success", "Property sold and transaction recorded successfully!")
            self.refresh_callback() # Call the callback to refresh the main view
            self.master._clear_property_details_ui() # Clear the property details in the main UI
            self.destroy() # Close the Sell Property form
        else:
            messagebox.showerror("Error", "Failed to record transaction.")

    def _generate_receipt_from_id(self, transaction_id, save_only=False):
        """
        Generates a PDF receipt and optionally saves it.
        If transaction_id is provided, it's assumed this is called after a successful sale.
        If save_only is True, it will save but not attempt to initiate a print dialog.

        Args:
            transaction_id (str, optional): The ID of the transaction. Defaults to None.
            save_only (bool, optional): If True, only saves the receipt, does not
                                        prompt for printing. Defaults to False.

        Returns:
            str or None: The relative path to the saved PDF file if successful,
                         otherwise None.
        """
        # 1. Input Validation and Data Extraction
        # Check if essential fields are filled
        if not transaction_id:
            messagebox.showerror("Receipt Error", "Transaction ID is required to generate a receipt.")
            return None

        #fetch all data from the database using transaction_id
        transaction_data = self.db_manager.get_transaction(transaction_id)
        if not transaction_data:
            messagebox.showerror("Receipt Error", "Transaction data not found.")
            return None
        
        property_data = self.db_manager.get_property(transaction_data.get('property_id'))
        client_data = self.db_manager.get_client(transaction_data.get('client_id'))

        
        try:
            prop_title_deed = property_data.get('title_deed_number', 'N/A')
            prop_location = property_data.get('location', 'N/A')
            prop_size = property_data.get('size', 'N/A')
            prop_price = float(property_data.get('price', 0.0))
            buyer_name = client_data.get('name', 'N/A')
            buyer_contact = client_data.get('contact_info', 'N/A')
            payment_mode = transaction_data.get('payment_mode', 'N/A')
            amount_paid = float(transaction_data.get('amount_paid', 0.0))
            discount = float(transaction_data.get('discount', 0.0))
            balance = float(transaction_data.get('balance', 0.0))
            transaction_date = transaction_data.get('date', datetime.now().strftime("%Y-%m-%d"))
        except (KeyError, ValueError) as e:
            messagebox.showerror("Receipt Error", f"Invalid data format: {e}")
            return None


        # Calculate net price
        net_price = prop_price - discount

        # 2. PDF Document Generation using ReportLab
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Sanitize title deed for filename
        safe_prop_title_deed = "".join(c for c in prop_title_deed if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        receipt_filename = f"receipt_{timestamp}_{safe_prop_title_deed}.pdf"
        receipt_full_path = os.path.join(RECEIPTS_DIR, receipt_filename)

        try:
            # Create a SimpleDocTemplate which handles page layout
            doc = SimpleDocTemplate(receipt_full_path, pagesize=letter)
            # Create a list to hold the document's flowables (paragraphs, spaces, etc.)
            story = []

            # Get default styles
            styles = getSampleStyleSheet()
            normal_style = styles['Normal']
            h1_style = styles['h1']
            h2_style = styles['h2']

            # Add content to the story
            # Header
            story.append(Paragraph("<font size='16' color='#333333'><b>PROPERTY SALE RECEIPT</b></font>", h1_style))
            story.append(Paragraph("<font size='14' color='#555555'>MATHENGE REAL ESTATE</font>", h2_style))
            # Reduced vertical space to help fit content on one page
            story.append(Spacer(1, 0.2 * letter[1])) # Changed from 0.4 * letter[1]

            # Transaction Details
            story.append(Paragraph(f"<b>Date:</b> {transaction_date}", normal_style))
            story.append(Paragraph(f"<b>Transaction ID:</b> {transaction_id if transaction_id else 'N/A'}", normal_style))
            story.append(Spacer(1, 0.15 * letter[1])) # Slightly reduced

            # Buyer Details
            story.append(Paragraph("<font size='12' color='#444444'><b>BUYER DETAILS:</b></font>", h2_style))
            story.append(Paragraph(f"<b>Name:</b> {buyer_name}", normal_style))
            story.append(Paragraph(f"<b>Contact:</b> {buyer_contact}", normal_style))
            story.append(Spacer(1, 0.15 * letter[1])) # Slightly reduced

            # Property Details
            story.append(Paragraph("<font size='12' color='#444444'><b>PROPERTY DETAILS:</b></font>", h2_style))
            story.append(Paragraph(f"<b>Title Deed:</b> {prop_title_deed}", normal_style))
            story.append(Paragraph(f"<b>Location:</b> {prop_location}", normal_style))
            story.append(Paragraph(f"<b>Size:</b> {prop_size}", normal_style))
            story.append(Spacer(1, 0.15 * letter[1])) # Slightly reduced

            # Financial Summary
            story.append(Paragraph("<font size='12' color='#444444'><b>FINANCIAL SUMMARY:</b></font>", h2_style))
            story.append(Paragraph(f"<b>Original Price:</b> KES {prop_price:,.2f}", normal_style))
            # Using non-breaking space &nbsp; for alignment where precise control is needed
            story.append(Paragraph(f"<b>Discount:</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KES {discount:,.2f}", normal_style))
            story.append(Paragraph(f"<b>Net Price:</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KES {net_price:,.2f}", normal_style))
            story.append(Paragraph(f"<b>Amount Paid:</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KES {amount_paid:,.2f}", normal_style))
            story.append(Paragraph(f"<b>Balance Due:</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KES {balance:,.2f}", normal_style))
            story.append(Paragraph(f"<b>Payment Mode:</b> {payment_mode}", normal_style))
            story.append(Spacer(1, 0.2 * letter[1])) # Changed from 0.4 * letter[1]

            # Footer
            story.append(Paragraph("<center>Thank you for your business!</center>", normal_style))
            story.append(Paragraph("<center><font size='8' color='#888888'>Generated on " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "</font></center>", normal_style))

            # Build the PDF document from the story
            doc.build(story)

            messagebox.showinfo("Receipt Generated", f"Receipt saved successfully to:\n{receipt_full_path}")

            # 3. Optional Printing Prompt
            if not save_only:
                if messagebox.askyesno("Print Receipt", "Do you want to print this receipt now?"):
                    try:
                        # Placeholder for actual printing logic
                        # Printing PDFs directly from Python is OS-dependent and often
                        # involves calling external commands or specialized libraries.
                        # Examples (highly platform-specific, not universally guaranteed to work):
                        # On Windows: os.startfile(receipt_full_path, "print")
                        # On macOS: subprocess.run(["open", "-a", "Preview", "-p", receipt_full_path])
                        # On Linux (requires 'lp' or 'lpr'): subprocess.run(["lp", receipt_full_path])
                        messagebox.showinfo("Print Status",
                                            "Printing functionality is highly OS-dependent and requires specific setup.\n"
                                            "The receipt has been saved. Please open and print it manually from:\n"
                                            f"{receipt_full_path}")
                    except Exception as e:
                        messagebox.showerror("Print Error", f"Failed to initiate print job. Please print manually. Error: {e}")

            # Return the relative path, useful for storing in a database or displaying
            return os.path.relpath(receipt_full_path, DATA_DIR).replace("\\", "/")

        except Exception as e:
            messagebox.showerror("PDF Generation Error", f"An error occurred while generating or saving the receipt PDF: {e}")
            return None
        
    def cancel(self):
        self.destroy()

class InstallmentPaymentWindow(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, selected_property, buyer_name, buyer_contact, payment_mode, refresh_callback, icon_loader):
        super().__init__(master)
        self.db_manager = db_manager
        self.user_id = user_id
        self.selected_property = selected_property
        self.buyer_name = buyer_name
        self.buyer_contact = buyer_contact
        self.payment_mode = payment_mode
        self.refresh_callback = refresh_callback
        self.icon_loader = icon_loader
        self.grab_set()
        self.transient(master)

        self._all_payment_plans = {}
        self._required_deposit_var = tk.StringVar(value="0.00")
        self._amount_paid_var = tk.StringVar(value="")
        self._total_amount_paid_var = tk.StringVar(value="0.00")

        self._set_window_properties(400, 450, "installment.png")
        self._customize_title_bar()
        self._create_widgets()
        self._load_payment_plans()

    def _set_window_properties(self, width, height, icon_name):
        """Sets the window size, position, and icon based on the master window."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x = master_x + (master_width // 2) - (width // 2)
        y = master_y + (master_height // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        self.title("Instalments Payment")
        if self.icon_loader and icon_name:
            try:
                icon_image = self.icon_loader(icon_name, size=(20, 20))
                self.iconphoto(False, icon_image)
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        if has_ctypes and os.name == 'nt':
            try:
                # DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102 -> BGR: 102, 51, 0)
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white (RGB: 255, 255, 255 -> BGR: 255, 255, 255)
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")
                self._create_custom_title_bar()
        else:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)
    
    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self):
        # Header Frame with Custom Title Bar elements
        
        
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Buyer Information
        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Details", padding=5)
        buyer_info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(buyer_info_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_name, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text="Contact:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_contact, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=2, padx=5)

        # Property Details
        prop_info_frame = ttk.LabelFrame(main_frame, text="Property Details", padding=5)
        prop_info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(prop_info_frame, text="Property Title Deed:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text=self.selected_property['title_deed_number'], font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text="Property Price (KES):").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(prop_info_frame, text=f"{self.selected_property['price']:,.2f}", font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=2, padx=5)

        # Payment details
        payment_frame = ttk.LabelFrame(main_frame, text="Payment Details", padding=5)
        payment_frame.pack(fill=tk.X, pady=5)

        ttk.Label(payment_frame, text="Payment Plan:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.payment_plan_combobox = ttk.Combobox(payment_frame, state="readonly")
        self.payment_plan_combobox.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        self.payment_plan_combobox.bind("<<ComboboxSelected>>", self._on_payment_plan_select)
        
        ttk.Label(payment_frame, text="Required Deposit (KES):").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        ttk.Label(payment_frame, textvariable=self._required_deposit_var, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        
        ttk.Label(payment_frame, text="Total Amount to be Paid:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        ttk.Label(payment_frame, textvariable=self._total_amount_paid_var, font=("Arial", 10, "bold")).grid(row=2, column=1, sticky="ew", pady=5, padx=5)

        ttk.Label(payment_frame, text="Initial Payment (KES):").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        self.entry_amount_paid = ttk.Entry(payment_frame, textvariable=self._amount_paid_var)
        self.entry_amount_paid.grid(row=3, column=1, sticky="ew", pady=5, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(main_frame, padding=5)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Sell", command=self._sell_property, style='Green.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel, style='Red.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def _load_payment_plans(self):
        try:
            plans = self.db_manager.get_payment_plans()
            self._all_payment_plans = {plan['name']: plan for plan in plans}
            formatted_plans = [f"{plan['name']} (Interest: {plan['interest_rate']}%, Deposit: {plan['deposit_percentage']}%, Duration: {plan['duration_months']} months)" for plan in plans]
            self.payment_plan_combobox['values'] = formatted_plans
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load payment plans: {e}", parent=self)
            
    def _on_payment_plan_select(self, event=None):
        selected_plan_str = self.payment_plan_combobox.get()
        if not selected_plan_str:
            return
        
        plan_name = selected_plan_str.split(' (')[0]
        selected_plan = self._all_payment_plans.get(plan_name)
        if not selected_plan:
            return

        property_price = self.selected_property.get('price', 0)
        deposit_percent = selected_plan.get('deposit_percentage', 0)
        required_deposit = property_price * (deposit_percent / 100)
        self._required_deposit_var.set(f"{required_deposit:,.2f}")
        
        principal = property_price
        interest_rate = selected_plan.get('interest_rate', 0) / 100
        duration = selected_plan.get('duration_months', 0)
        time_in_years = duration / 12
        total_payable_amount = principal * (1 + (interest_rate * time_in_years))
        self._total_amount_paid_var.set(f"{total_payable_amount:,.2f}")
        self._amount_paid_var.set(f"{required_deposit:.2f}")

    def _sell_property(self):
        """Handles the validation and database transaction for an installment sale."""
        # 1. Basic validation from the UI
        if not self.payment_plan_combobox.get():
            messagebox.showerror("Error", "Please select a payment plan.", parent=self)
            return
        
        amount_paid_str = self._amount_paid_var.get().strip().replace(',', '')
        
        # 2. Get required data
        buyer_name = self.buyer_name.strip()
        buyer_contact = self.buyer_contact.strip()
        payment_mode = "Installments"
        client_status = 'active'
        added_by_user_id = self.user_id
        
        if not buyer_name or not buyer_contact or not amount_paid_str:
            messagebox.showerror("Input Error", "Buyer Name, Contact Info, and Initial Payment are required.", parent=self)
            return
        
        # 3. Numeric input validation
        try:
            amount_paid = float(amount_paid_str)
            required_deposit = float(self._required_deposit_var.get().strip().replace(',', ''))
            
            if amount_paid < 0:
                messagebox.showerror("Input Error", "Initial payment cannot be negative.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid numeric input for initial payment.", parent=self)
            return

        # 4. Business logic validation
        if amount_paid < required_deposit:
            messagebox.showerror("Validation Error", "Initial payment cannot be less than the required deposit.", parent=self)
            return
        
        # 5. Get or add client
        client_data = self.db_manager.get_client_by_contact_info(buyer_contact)
        if client_data:
            client_id = client_data['client_id']
            if client_data['name'] != buyer_name:
                self.db_manager.update_client(client_id, name=buyer_name)
        else:
            client_id = self.db_manager.add_client(buyer_name, buyer_contact, client_status, added_by_user_id)
            if not client_id:
                messagebox.showerror("Database Error", "Failed to add new client.", parent=self)
                return
        
        # 6. Prepare sale details for database transaction
        # The balance is the total payable minus the amount paid initially.
        total_payable = float(self._total_amount_paid_var.get().strip().replace(',', ''))
        balance = total_payable - amount_paid
        discount = 0.0 # Assumes no discount for installments for now
        
        transaction_data = {
            'property_id': self.selected_property['property_id'],
            'client_id': client_id,
            'payment_mode': payment_mode,
            'amount_paid': amount_paid,
            'discount': 0.0, # Assumes no discount for installments for now
            'balance': balance,
            'payment_plan': self.payment_plan_combobox.get()
        }
        
        # 7. Record the sale in the database
        transaction_id = self.db_manager.add_transaction(
            self.selected_property['property_id'],
            client_id,
            payment_mode,
            amount_paid,
            discount,
            balance,
            None

        )

        if transaction_id:
            # 8. Update property status
            self.db_manager.update_property(self.selected_property['property_id'], status='Sold')
            
            # 9. Generate receipt and provide confirmation
            if messagebox.askyesno("Generate Receipt?", "Installment plan recorded. Do you want to generate a receipt for the initial payment?"):
                # You'll need to pass the transaction_id to your receipt generator
                # self._generate_receipt_from_id(transaction_id)
                pass # Placeholder for your receipt generation call

            messagebox.showinfo("Success", "Installment sale recorded successfully!", parent=self)
            self.refresh_callback()
            self.master._clear_property_details_ui()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to record installment transaction.", parent=self)

    def _generate_receipt(self):
        messagebox.showinfo("Receipt", "Receipt generation is not yet implemented.", parent=self)
        
    def cancel(self):
        self.destroy()

try:
    from ctypes import windll, byref, sizeof, c_int
    has_ctypes = True
except (ImportError, OSError):
    has_ctypes = False

class SellPropertyFormLot(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, refresh_callback, on_close_callback, parent_icon_loader=None, window_icon_name="sell_property.png"):
        super().__init__(master)
        self.title("Sell Property- Lots Sale")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.user_id = user_id
        self.on_close_callback = on_close_callback
        self.refresh_callback = refresh_callback
        self.selected_property = None
        self.title_deed_images = []
        self._window_icon_ref = None
        self.master_icon_loader_ref = parent_icon_loader
        
        self.available_properties_data = []

        self.style = ttk.Style()
        self.style.configure('Green.TButton', background='green', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Green.TButton', background=[('active', 'darkgreen')], foreground=[('disabled', 'gray')])
        self.style.configure('Yellow.TButton', background='gold', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Yellow.TButton', background=[('active', 'goldenrod')], foreground=[('disabled', 'gray')])
        self.style.configure('Red.TButton', background='red', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Red.TButton', background=[('active', 'darkred')])
        
        self.style.configure('TEntry', bordercolor='lightgrey', relief='solid', borderwidth=1)
        self.style.map('TEntry', bordercolor=[('focus', '#0099C2')])

        self._set_window_properties(1000, 520, window_icon_name, parent_icon_loader)
        self._customize_title_bar()  # Call the new method
        
        self._create_widgets(parent_icon_loader)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._populate_property_list()
        
    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        property_selection_frame = ttk.LabelFrame(main_frame, text="Select Property", padding="5")
        property_selection_frame.pack(fill="x", pady=5)
        property_selection_frame.columnconfigure(0, weight=1)

        search_frame = ttk.Frame(property_selection_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        search_frame.columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_properties)
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.entry_search.pack(side="left", fill="x", expand=True)
        ttk.Label(search_frame, text="Search (Title/Location):").pack(side="left", padx=(5, 2))

        filter_frame = ttk.Frame(property_selection_frame)
        filter_frame.grid(row=0, column=1, sticky="e", padx=5, pady=2)
        ttk.Label(filter_frame, text="Size (Acres): Min").pack(side="left")
        self.entry_min_size = ttk.Entry(filter_frame, width=8)
        self.entry_min_size.pack(side="left", padx=1)
        ttk.Label(filter_frame, text="Max").pack(side="left")
        self.entry_max_size = ttk.Entry(filter_frame, width=8)
        self.entry_max_size.pack(side="left", padx=1)
        
        if parent_icon_loader:
            self._apply_filter_icon = parent_icon_loader("filter.png", size=(20, 20))
            apply_btn = ttk.Button(filter_frame, text="Apply Filter", image=self._apply_filter_icon, compound=tk.LEFT, command=self._filter_properties, style='TButton')
            apply_btn.pack(side="left", padx=2)
            apply_btn.image = self._apply_filter_icon

        self.property_listbox = tk.Listbox(property_selection_frame, height=6, width=70)
        self.property_listbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        self.property_listbox.bind("<<ListboxSelect>>", self._on_property_select)

        listbox_scrollbar = ttk.Scrollbar(property_selection_frame, orient="vertical", command=self.property_listbox.yview)
        listbox_scrollbar.grid(row=1, column=2, sticky="ns", pady=2)
        self.property_listbox.config(yscrollcommand=listbox_scrollbar.set)

        details_frame = ttk.LabelFrame(main_frame, text="Property Details", padding="5")
        details_frame.pack(fill="x", pady=5)
        details_frame.columnconfigure(1, weight=1)
        details_frame.columnconfigure(2, weight=0)

        self.lbl_prop_title_deed = ttk.Label(details_frame, text="Title Deed Number:")
        self.lbl_prop_title_deed.grid(row=0, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_title_deed = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_title_deed.grid(row=0, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_location = ttk.Label(details_frame, text="Location:")
        self.lbl_prop_location.grid(row=1, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_location = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_location.grid(row=1, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_size = ttk.Label(details_frame, text="Size (Acres):")
        self.lbl_prop_size.grid(row=2, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_size = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_size.grid(row=2, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_price = ttk.Label(details_frame, text="Asking Price (KES):")
        self.lbl_prop_price.grid(row=3, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_price = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_price.grid(row=3, column=1, sticky="ew", pady=1, padx=5)

        self.title_deed_image_frame = ttk.LabelFrame(details_frame, text="Title Deed Image", padding=2)
        self.title_deed_image_frame.grid(row=0, column=2, rowspan=4, sticky="nsew", padx=5, pady=2)
        self.title_deed_image_frame.columnconfigure(0, weight=1)

        self.current_title_image_label = ttk.Label(self.title_deed_image_frame)
        self.current_title_image_label.pack(fill="both", expand=True, padx=5, pady=5)
        self.current_title_image_label.bind("<Button-1>", lambda e: self._open_image_gallery())

        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Information", padding="5")
        buyer_info_frame.pack(fill="x", pady=5)
        buyer_info_frame.columnconfigure(1, weight=1)

        ttk.Label(buyer_info_frame, text="Buyer Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.entry_buyer_name = ttk.Entry(buyer_info_frame)
        self.entry_buyer_name.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.entry_buyer_name.bind("<Double-Button-1>", lambda event: "break")

        ttk.Label(buyer_info_frame, text="Buyer Contact Info:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.entry_buyer_contact = ttk.Entry(buyer_info_frame)
        self.entry_buyer_contact.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        self.entry_buyer_contact.bind("<Double-Button-1>", lambda event: "break")

        payment_options_frame = ttk.LabelFrame(main_frame, text="Payment Options", padding="5")
        payment_options_frame.pack(fill="x", pady=5)

        self.btn_cash = ttk.Button(payment_options_frame, text="Cash", command=self._open_cash_payment_window, style='Green.TButton')
        self.btn_cash.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_installments = ttk.Button(payment_options_frame, text="Instalments", command=self._open_installment_payment_window, style='Yellow.TButton')
        self.btn_installments.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)
        
    def _open_cash_payment_window(self):
        if not self.selected_property:
            messagebox.showwarning("No Property Selected", "Please select a property first.", parent=self)
            return

        buyer_name = self.entry_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()

        if not buyer_name or not buyer_contact:
            messagebox.showwarning("Buyer Information Required", "Please enter the buyer's name and contact information.", parent=self)
            return

        CashPaymentWindow(self, self.db_manager, self.user_id, self.selected_property, buyer_name, buyer_contact, "Cash", self._populate_property_list, self.master_icon_loader_ref)
        
    def _open_installment_payment_window(self):
        if not self.selected_property:
            messagebox.showwarning("No Property Selected", "Please select a property first.", parent=self)
            return

        buyer_name = self.entry_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()

        if not buyer_name or not buyer_contact:
            messagebox.showwarning("Buyer Information Required", "Please enter the buyer's name and contact information.", parent=self)
            return

        InstallmentPaymentWindow(self, self.db_manager, self.user_id, self.selected_property, buyer_name, buyer_contact,"installment",self._populate_property_list, self.master_icon_loader_ref)
    
    def _on_property_select(self, event):
        selected_index = self.property_listbox.curselection()
        if selected_index:
            try:
                index = selected_index[0]
                self.selected_property = self.available_properties_data[index]

                title_deed = self.selected_property['title_deed_number']
                location = self.selected_property['location']
                size = self.selected_property['size']
                price = self.selected_property['price']
                title_images_str = self.selected_property['title_image_paths']
                
                self.val_prop_title_deed.config(text=title_deed.upper())
                self.val_prop_location.config(text=location.upper())
                self.val_prop_size.config(text=f"{size:.2f} ACRES")
                self.val_prop_price.config(text=f"KES {price:,.2f}")

                self._display_single_title_deed_thumbnail(title_images_str)
                
            except IndexError:
                self.selected_property = None
                self._clear_property_details_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to select property: {e}", parent=self)
                self.selected_property = None
                self._clear_property_details_ui()
        else:
            self.selected_property = None
            self._clear_property_details_ui()

    def _clear_property_details_ui(self):
        self.val_prop_title_deed.config(text="")
        self.val_prop_location.config(text="")
        self.val_prop_size.config(text="")
        self.val_prop_price.config(text="")
        self.current_title_image_label.config(image='')
        self.current_title_image_label._image_ref = None
        self.entry_buyer_name.delete(0, tk.END)
        self.entry_buyer_contact.delete(0, tk.END)
        self.property_listbox.selection_clear(0, tk.END)
        self.selected_property = None

    def _on_closing(self):
        self.grab_release()
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()
            
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
    
    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        if has_ctypes and os.name == 'nt':
            try:
                # DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102 -> BGR: 102, 51, 0)
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white (RGB: 255, 255, 255 -> BGR: 255, 255, 255)
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")
                self._create_custom_title_bar()
        else:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)

        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Title label
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _populate_property_list(self, search_query="", min_size=None, max_size=None):
        self.property_listbox.delete(0, tk.END)
        self.available_properties_data = self.db_manager.get_all_properties_lots(status='Available',property_type='Lot')

        if not self.available_properties_data:
            self.property_listbox.insert(tk.END, "NO AVAILABLE PROPERTIES FOUND.")
            return

        filtered_properties = []
        for prop in self.available_properties_data:
            title_deed = prop['title_deed_number']
            location = prop['location']
            size = prop['size']

            match_search = True
            if search_query:
                search_query_lower = search_query.lower()
                if search_query_lower not in title_deed.lower() and \
                   search_query_lower not in location.lower():
                    match_search = False

            match_size = True
            if min_size is not None and size < min_size:
                match_size = False
            if max_size is not None and size > max_size:
                match_size = False

            if match_search and match_size:
                filtered_properties.append(prop)

        if not filtered_properties:
            self.property_listbox.insert(tk.END, "NO MATCHING PROPERTIES FOUND.")
            return

        for prop in filtered_properties:
            self.property_listbox.insert(tk.END, f"{prop['title_deed_number'].upper()} - {prop['location'].upper()} ({prop['size']:.2f} ACRES) - KES {prop['price']:,.2f}")

        self.available_properties_data = filtered_properties

    def _filter_properties(self, *args):
        search_query = self.search_var.get().strip()
        min_size_str = self.entry_min_size.get().strip()
        max_size_str = self.entry_max_size.get().strip()

        min_size = None
        max_size = None

        if min_size_str:
            try:
                min_size = float(min_size_str)
                if min_size < 0:
                    messagebox.showwarning("Input Error", "Minimum size cannot be negative.")
                    self.entry_min_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Min Size. Please enter a number.")
                self.entry_min_size.delete(0, tk.END)
                return

        if max_size_str:
            try:
                max_size = float(max_size_str)
                if max_size < 0:
                    messagebox.showwarning("Input Error", "Maximum size cannot be negative.")
                    self.entry_max_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Max Size. Please enter a number.")
                self.entry_max_size.delete(0, tk.END)
                return

        if min_size is not None and max_size is not None and min_size > max_size:
            messagebox.showwarning("Input Error", "Minimum size cannot be greater than maximum size.")
            return

        self._populate_property_list(search_query, min_size, max_size)

    def _update_receipt_button_state(self):
        """Enables or disables the receipt button based on selected property and buyer info."""
        is_selected = self.selected_property is not None
        has_buyer_name = bool(self.entry_buyer_name.get().strip())
        has_buyer_contact = bool(self.entry_buyer_contact.get().strip())
        
        # Check if amount paid is not empty and is a valid number
        try:
            amount_paid = float(self._amount_paid_var.get())
            is_amount_valid = True
        except (ValueError, tk.TclError):
            is_amount_valid = False
            
        enable_buttons = is_selected and has_buyer_name and has_buyer_contact and is_amount_valid
        
        self.generate_receipt_button['state'] = 'normal' if enable_buttons else 'disabled'
        self.sell_button['state'] = 'normal' if enable_buttons else 'disabled'

    def _display_single_title_deed_thumbnail(self, title_images_str):
        self._clear_single_title_deed_thumbnail()

        self.title_deed_images = []
        if title_images_str:
            self.title_deed_images = [path.strip() for path in title_images_str.split(',') if path.strip()]

        if not self.title_deed_images:
            self.current_title_image_label.config(image='', text="No Title Deed Images", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            return

        first_image_rel_path = self.title_deed_images[0]
        full_path = os.path.join(DATA_DIR, first_image_rel_path)

        if not os.path.exists(full_path):
            print(f"Warning: First title deed image file not found at {full_path}")
            self.current_title_image_label.config(image='', text="Image not found", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            return

        try:
            img = Image.open(full_path)
            width, height = img.size
            max_size = 60
            if width > max_size or height > max_size:
                ratio = min(max_size / width, max_size / height)
                img = img.resize((int(width * ratio), int(height * ratio)), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.current_title_image_label.config(image=photo, text="")
            self.current_title_image_label.image = photo # <--- Store reference for label
        except Exception as e:
            print(f"Error loading first title deed thumbnail for {full_path}: {e}")
            self.current_title_image_label.config(image='', text="Error loading image", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            self.current_title_image_label.config(cursor="")
            self.title_deed_image_frame.config(text="Title Deed Image")

    def _clear_single_title_deed_thumbnail(self):
        self.current_title_image_label.config(image='', text="No Title Deed Images Selected", font=('Arial', 10, 'italic'))
        self.current_title_image_label.image = None
        self.current_title_image_label.config(cursor="")
        self.title_deed_image_frame.config(text="Title Deed Image")
        self.title_deed_images.clear()

    def _get_full_title_deed_paths(self):
        return [os.path.join(DATA_DIR, rel_path) for rel_path in self.title_deed_images if os.path.exists(os.path.join(DATA_DIR, rel_path))]


    def _open_image_gallery(self): 
        if not self.title_deed_images:
            messagebox.showinfo("No Images", "No title deed images available for this property.")
            return

        gallery = tk.Toplevel(self)
        gallery.title("Title Deed Image Gallery")
        gallery.transient(self)
        gallery.grab_set()
        
        # Apply window properties to gallery
        self._set_window_properties_for_gallery(gallery, 452, 452, "gallery.png", self.master_icon_loader_ref) 

        # Store gallery-specific state on the gallery Toplevel itself
        gallery.gallery_image_paths = self._get_full_title_deed_paths()
        gallery.current_gallery_index = 0 
        
        # DEBUG Print
        print(f"DEBUG (SellPropertyForm Gallery): Toplevel created: {gallery}, paths count: {len(gallery.gallery_image_paths)}, current_index: {gallery.current_gallery_index}")

        # Create a container for the image and arrows
        gallery.image_container_frame = ttk.Frame(gallery, relief="solid", borderwidth=1)
        gallery.image_container_frame.pack(fill="both", expand=True)

        gallery.gallery_image_label = ttk.Label(gallery.image_container_frame) # Set background for black bars if image is smaller
        gallery.gallery_image_label.pack(fill="both", expand=True) # Use pack for main image label

        # Create navigation arrow labels directly on the image label's parent or on the image label itself if desired
        # Placing them on the gallery_image_label directly and adjusting relative positioning.
        
        # Left Arrow
        prev_arrow = ttk.Label(gallery.image_container_frame, text='◀', font=('Arial', 24, 'bold'), 
                               foreground='black', cursor='hand2')
        prev_arrow.place(relx=0, rely=0.5, anchor='w', relwidth=0.15, relheight=1) # Position on left edge
        prev_arrow.bind("<Button-1>", lambda e: self._show_previous_image_in_gallery(gallery))
        prev_arrow.config(wraplength=1) # Prevent text wrapping

        # Right Arrow
        next_arrow = ttk.Label(gallery.image_container_frame, text='▶', font=('Arial', 24, 'bold'), 
                               foreground='black', cursor='hand2')
        next_arrow.place(relx=1, rely=0.5, anchor='e', relwidth=0.15, relheight=1) # Position on right edge
        next_arrow.bind("<Button-1>", lambda e: self._show_next_image_in_gallery(gallery))
        next_arrow.config(wraplength=1) # Prevent text wrapping


        self._update_gallery_image(gallery) # Pass gallery window to the update function

    def _set_window_properties_for_gallery(self, window, width, height, icon_name, parent_icon_loader):
        """Helper to set properties for the gallery window."""
        window.geometry(f"{width}x{height}")
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 50
        window.geometry(f"+{x}+{y}")
        window.resizable(False, False) # Set fixed size
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                window.iconphoto(False, icon_image)
                window._window_icon_ref = icon_image # <--- Important: Keep reference for gallery window
            except Exception as e:
                print(f"Failed to set icon for {window.title()}: {e}")

    # Specific navigation methods for the SellPropertyForm gallery
    def _show_previous_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index - 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _show_next_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index + 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _update_gallery_image(self, gallery_window):
        # This function now takes the gallery_window as an argument
        if gallery_window.gallery_image_paths:
            try:
                img_path = gallery_window.gallery_image_paths[gallery_window.current_gallery_index]
                img = Image.open(img_path)

                # Get the current dimensions of the label to fit the image
                gallery_window.image_container_frame.update_idletasks() # Ensure label has up-to-date size
                container_width = gallery_window.image_container_frame.winfo_width()
                container_height = gallery_window.image_container_frame.winfo_height()

                # Fallback for initial state if width/height are 0 or very small
                if container_width <= 1: 
                    # Use gallery window's internal dimensions, minus some padding/chrome for a rough estimate
                    container_width = gallery_window.winfo_width() - 2 
                    if container_width < 100: container_width = 100 # Minimum sensible size
                if container_height <= 1: 
                    # Use gallery window's internal dimensions, minus padding/button frame for a rough estimate
                    container_height = gallery_window.winfo_height() - 2
                    if container_height < 100: container_height = 100 # Minimum sensible size


                original_width, original_height = img.size
                
                
                ratio = min(container_width / original_width, container_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)

                # Ensure dimensions are at least 1x1 to prevent errors
                if new_width == 0: new_width = 1
                if new_height == 0: new_height = 1

                img = img.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                gallery_window.gallery_image_label.config(image=photo)
                gallery_window.gallery_image_label.image = photo # <--- Keep strong reference for image label
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not load image: {e}")
                gallery_window.gallery_image_label.config(image='', text="Error loading image.")
                gallery_window.gallery_image_label.image = None
        else:
            gallery_window.gallery_image_label.config(image='', text="No image to display.")
            gallery_window.gallery_image_label.image = None


    

    

class SellPropertyFormBlock(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, refresh_callback, on_close_callback, parent_icon_loader=None, window_icon_name="sell_property.png"):
        super().__init__(master)
        self.title("Sell Property- Blocks Sale")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.user_id = user_id
        self.on_close_callback = on_close_callback
        self.refresh_callback = refresh_callback
        self.selected_property = None
        self.title_deed_images = []
        self._window_icon_ref = None
        self.master_icon_loader_ref = parent_icon_loader
        
        self.available_properties_data = []

        self.style = ttk.Style()
        self.style.configure('Green.TButton', background='green', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Green.TButton', background=[('active', 'darkgreen')], foreground=[('disabled', 'gray')])
        self.style.configure('Yellow.TButton', background='gold', foreground='black', font=('Arial', 10, 'bold'))
        self.style.map('Yellow.TButton', background=[('active', 'goldenrod')], foreground=[('disabled', 'gray')])
        self.style.configure('Red.TButton', background='red', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Red.TButton', background=[('active', 'darkred')])
        
        self.style.configure('TEntry', bordercolor='lightgrey', relief='solid', borderwidth=1)
        self.style.map('TEntry', bordercolor=[('focus', '#0099C2')])

        self._set_window_properties(1000, 520, window_icon_name, parent_icon_loader)
        self._customize_title_bar()  # Call the new method
        
        self._create_widgets(parent_icon_loader)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._populate_property_list()
        
    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        property_selection_frame = ttk.LabelFrame(main_frame, text="Select Property", padding="5")
        property_selection_frame.pack(fill="x", pady=5)
        property_selection_frame.columnconfigure(0, weight=1)

        search_frame = ttk.Frame(property_selection_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        search_frame.columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_properties)
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.entry_search.pack(side="left", fill="x", expand=True)
        ttk.Label(search_frame, text="Search (Title/Location):").pack(side="left", padx=(5, 2))

        filter_frame = ttk.Frame(property_selection_frame)
        filter_frame.grid(row=0, column=1, sticky="e", padx=5, pady=2)
        ttk.Label(filter_frame, text="Size (Acres): Min").pack(side="left")
        self.entry_min_size = ttk.Entry(filter_frame, width=8)
        self.entry_min_size.pack(side="left", padx=1)
        ttk.Label(filter_frame, text="Max").pack(side="left")
        self.entry_max_size = ttk.Entry(filter_frame, width=8)
        self.entry_max_size.pack(side="left", padx=1)
        
        if parent_icon_loader:
            self._apply_filter_icon = parent_icon_loader("filter.png", size=(20, 20))
            apply_btn = ttk.Button(filter_frame, text="Apply Filter", image=self._apply_filter_icon, compound=tk.LEFT, command=self._filter_properties, style='TButton')
            apply_btn.pack(side="left", padx=2)
            apply_btn.image = self._apply_filter_icon

        self.property_listbox = tk.Listbox(property_selection_frame, height=6, width=70)
        self.property_listbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        self.property_listbox.bind("<<ListboxSelect>>", self._on_property_select)

        listbox_scrollbar = ttk.Scrollbar(property_selection_frame, orient="vertical", command=self.property_listbox.yview)
        listbox_scrollbar.grid(row=1, column=2, sticky="ns", pady=2)
        self.property_listbox.config(yscrollcommand=listbox_scrollbar.set)

        details_frame = ttk.LabelFrame(main_frame, text="Property Details", padding="5")
        details_frame.pack(fill="x", pady=5)
        details_frame.columnconfigure(1, weight=1)
        details_frame.columnconfigure(2, weight=0)

        self.lbl_prop_title_deed = ttk.Label(details_frame, text="Title Deed Number:")
        self.lbl_prop_title_deed.grid(row=0, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_title_deed = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_title_deed.grid(row=0, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_location = ttk.Label(details_frame, text="Location:")
        self.lbl_prop_location.grid(row=1, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_location = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_location.grid(row=1, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_size = ttk.Label(details_frame, text="Size (Acres):")
        self.lbl_prop_size.grid(row=2, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_size = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_size.grid(row=2, column=1, sticky="ew", pady=1, padx=5)

        self.lbl_prop_price = ttk.Label(details_frame, text="Asking Price (KES):")
        self.lbl_prop_price.grid(row=3, column=0, sticky="w", pady=1, padx=5)
        self.val_prop_price = ttk.Label(details_frame, text="", font=('Arial', 10, 'bold'))
        self.val_prop_price.grid(row=3, column=1, sticky="ew", pady=1, padx=5)

        self.title_deed_image_frame = ttk.LabelFrame(details_frame, text="Title Deed Image", padding=2)
        self.title_deed_image_frame.grid(row=0, column=2, rowspan=4, sticky="nsew", padx=5, pady=2)
        self.title_deed_image_frame.columnconfigure(0, weight=1)

        self.current_title_image_label = ttk.Label(self.title_deed_image_frame)
        self.current_title_image_label.pack(fill="both", expand=True, padx=5, pady=5)
        self.current_title_image_label.bind("<Button-1>", lambda e: self._open_image_gallery())

        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Information", padding="5")
        buyer_info_frame.pack(fill="x", pady=5)
        buyer_info_frame.columnconfigure(1, weight=1)

        ttk.Label(buyer_info_frame, text="Buyer Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.entry_buyer_name = ttk.Entry(buyer_info_frame)
        self.entry_buyer_name.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.entry_buyer_name.bind("<Double-Button-1>", lambda event: "break")

        ttk.Label(buyer_info_frame, text="Buyer Contact Info:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.entry_buyer_contact = ttk.Entry(buyer_info_frame)
        self.entry_buyer_contact.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        self.entry_buyer_contact.bind("<Double-Button-1>", lambda event: "break")

        payment_options_frame = ttk.LabelFrame(main_frame, text="Payment Options", padding="5")
        payment_options_frame.pack(fill="x", pady=5)

        self.btn_cash = ttk.Button(payment_options_frame, text="Cash", command=self._open_cash_payment_window, style='Green.TButton')
        self.btn_cash.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_installments = ttk.Button(payment_options_frame, text="Instalments", command=self._open_installment_payment_window, style='Yellow.TButton')
        self.btn_installments.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)
        
    def _open_cash_payment_window(self):
        if not self.selected_property:
            messagebox.showwarning("No Property Selected", "Please select a property first.", parent=self)
            return

        buyer_name = self.entry_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()

        if not buyer_name or not buyer_contact:
            messagebox.showwarning("Buyer Information Required", "Please enter the buyer's name and contact information.", parent=self)
            return

        CashPaymentWindow(self, self.db_manager, self.user_id, self.selected_property, buyer_name, buyer_contact, "Cash", self._populate_property_list, self.master_icon_loader_ref)
        
    def _open_installment_payment_window(self):
        if not self.selected_property:
            messagebox.showwarning("No Property Selected", "Please select a property first.", parent=self)
            return

        buyer_name = self.entry_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()

        if not buyer_name or not buyer_contact:
            messagebox.showwarning("Buyer Information Required", "Please enter the buyer's name and contact information.", parent=self)
            return

        InstallmentPaymentWindow(self, self.db_manager, self.user_id, self.selected_property, buyer_name, buyer_contact,"installment",self._populate_property_list, self.master_icon_loader_ref)
    
    def _on_property_select(self, event):
        selected_index = self.property_listbox.curselection()
        if selected_index:
            try:
                index = selected_index[0]
                self.selected_property = self.available_properties_data[index]

                title_deed = self.selected_property['title_deed_number']
                location = self.selected_property['location']
                size = self.selected_property['size']
                price = self.selected_property['price']
                title_images_str = self.selected_property['title_image_paths']
                
                self.val_prop_title_deed.config(text=title_deed.upper())
                self.val_prop_location.config(text=location.upper())
                self.val_prop_size.config(text=f"{size:.2f} ACRES")
                self.val_prop_price.config(text=f"KES {price:,.2f}")

                self._display_single_title_deed_thumbnail(title_images_str)
                
            except IndexError:
                self.selected_property = None
                self._clear_property_details_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to select property: {e}", parent=self)
                self.selected_property = None
                self._clear_property_details_ui()
        else:
            self.selected_property = None
            self._clear_property_details_ui()

    def _clear_property_details_ui(self):
        self.val_prop_title_deed.config(text="")
        self.val_prop_location.config(text="")
        self.val_prop_size.config(text="")
        self.val_prop_price.config(text="")
        self.current_title_image_label.config(image='')
        self.current_title_image_label._image_ref = None
        self.entry_buyer_name.delete(0, tk.END)
        self.entry_buyer_contact.delete(0, tk.END)
        self.property_listbox.selection_clear(0, tk.END)
        self.selected_property = None

    def _on_closing(self):
        self.grab_release()
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()
            
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
    
    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        if has_ctypes and os.name == 'nt':
            try:
                # DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102 -> BGR: 102, 51, 0)
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white (RGB: 255, 255, 255 -> BGR: 255, 255, 255)
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")
                self._create_custom_title_bar()
        else:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)

        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Title label
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _populate_property_list(self, search_query="", min_size=None, max_size=None):
        self.property_listbox.delete(0, tk.END)
        self.available_properties_data = self.db_manager.get_all_properties_lots(status='Available',property_type='Block')

        if not self.available_properties_data:
            self.property_listbox.insert(tk.END, "NO AVAILABLE PROPERTIES FOUND.")
            return

        filtered_properties = []
        for prop in self.available_properties_data:
            title_deed = prop['title_deed_number']
            location = prop['location']
            size = prop['size']

            match_search = True
            if search_query:
                search_query_lower = search_query.lower()
                if search_query_lower not in title_deed.lower() and \
                   search_query_lower not in location.lower():
                    match_search = False

            match_size = True
            if min_size is not None and size < min_size:
                match_size = False
            if max_size is not None and size > max_size:
                match_size = False

            if match_search and match_size:
                filtered_properties.append(prop)

        if not filtered_properties:
            self.property_listbox.insert(tk.END, "NO MATCHING PROPERTIES FOUND.")
            return

        for prop in filtered_properties:
            self.property_listbox.insert(tk.END, f"{prop['title_deed_number'].upper()} - {prop['location'].upper()} ({prop['size']:.2f} ACRES) - KES {prop['price']:,.2f}")

        self.available_properties_data = filtered_properties

    def _filter_properties(self, *args):
        search_query = self.search_var.get().strip()
        min_size_str = self.entry_min_size.get().strip()
        max_size_str = self.entry_max_size.get().strip()

        min_size = None
        max_size = None

        if min_size_str:
            try:
                min_size = float(min_size_str)
                if min_size < 0:
                    messagebox.showwarning("Input Error", "Minimum size cannot be negative.")
                    self.entry_min_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Min Size. Please enter a number.")
                self.entry_min_size.delete(0, tk.END)
                return

        if max_size_str:
            try:
                max_size = float(max_size_str)
                if max_size < 0:
                    messagebox.showwarning("Input Error", "Maximum size cannot be negative.")
                    self.entry_max_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Max Size. Please enter a number.")
                self.entry_max_size.delete(0, tk.END)
                return

        if min_size is not None and max_size is not None and min_size > max_size:
            messagebox.showwarning("Input Error", "Minimum size cannot be greater than maximum size.")
            return

        self._populate_property_list(search_query, min_size, max_size)

    

    def _display_single_title_deed_thumbnail(self, title_images_str):
        self._clear_single_title_deed_thumbnail()

        self.title_deed_images = []
        if title_images_str:
            self.title_deed_images = [path.strip() for path in title_images_str.split(',') if path.strip()]

        if not self.title_deed_images:
            self.current_title_image_label.config(image='', text="No Title Deed Images", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            return

        first_image_rel_path = self.title_deed_images[0]
        full_path = os.path.join(DATA_DIR, first_image_rel_path)

        if not os.path.exists(full_path):
            print(f"Warning: First title deed image file not found at {full_path}")
            self.current_title_image_label.config(image='', text="Image not found", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            return

        try:
            img = Image.open(full_path)
            width, height = img.size
            max_size = 60
            if width > max_size or height > max_size:
                ratio = min(max_size / width, max_size / height)
                img = img.resize((int(width * ratio), int(height * ratio)), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.current_title_image_label.config(image=photo, text="")
            self.current_title_image_label.image = photo # <--- Store reference for label
        except Exception as e:
            print(f"Error loading first title deed thumbnail for {full_path}: {e}")
            self.current_title_image_label.config(image='', text="Error loading image", font=('Arial', 10, 'italic'))
            self.current_title_image_label.image = None
            self.current_title_image_label.config(cursor="")
            self.title_deed_image_frame.config(text="Title Deed Image")

    def _clear_single_title_deed_thumbnail(self):
        self.current_title_image_label.config(image='', text="No Title Deed Images Selected", font=('Arial', 10, 'italic'))
        self.current_title_image_label.image = None
        self.current_title_image_label.config(cursor="")
        self.title_deed_image_frame.config(text="Title Deed Image")
        self.title_deed_images.clear()

    def _get_full_title_deed_paths(self):
        return [os.path.join(DATA_DIR, rel_path) for rel_path in self.title_deed_images if os.path.exists(os.path.join(DATA_DIR, rel_path))]


    def _open_image_gallery(self): 
        if not self.title_deed_images:
            messagebox.showinfo("No Images", "No title deed images available for this property.")
            return

        gallery = tk.Toplevel(self)
        gallery.title("Title Deed Image Gallery")
        gallery.transient(self)
        gallery.grab_set()
        
        # Apply window properties to gallery
        self._set_window_properties_for_gallery(gallery, 452, 452, "gallery.png", self.master_icon_loader_ref) 

        # Store gallery-specific state on the gallery Toplevel itself
        gallery.gallery_image_paths = self._get_full_title_deed_paths()
        gallery.current_gallery_index = 0 
        
        # DEBUG Print
        print(f"DEBUG (SellPropertyForm Gallery): Toplevel created: {gallery}, paths count: {len(gallery.gallery_image_paths)}, current_index: {gallery.current_gallery_index}")

        # Create a container for the image and arrows
        gallery.image_container_frame = ttk.Frame(gallery, relief="solid", borderwidth=1)
        gallery.image_container_frame.pack(fill="both", expand=True)

        gallery.gallery_image_label = ttk.Label(gallery.image_container_frame) # Set background for black bars if image is smaller
        gallery.gallery_image_label.pack(fill="both", expand=True) # Use pack for main image label

        # Create navigation arrow labels directly on the image label's parent or on the image label itself if desired
        # Placing them on the gallery_image_label directly and adjusting relative positioning.
        
        # Left Arrow
        prev_arrow = ttk.Label(gallery.image_container_frame, text='◀', font=('Arial', 24, 'bold'), 
                               foreground='black', cursor='hand2')
        prev_arrow.place(relx=0, rely=0.5, anchor='w', relwidth=0.15, relheight=1) # Position on left edge
        prev_arrow.bind("<Button-1>", lambda e: self._show_previous_image_in_gallery(gallery))
        prev_arrow.config(wraplength=1) # Prevent text wrapping

        # Right Arrow
        next_arrow = ttk.Label(gallery.image_container_frame, text='▶', font=('Arial', 24, 'bold'), 
                               foreground='black', cursor='hand2')
        next_arrow.place(relx=1, rely=0.5, anchor='e', relwidth=0.15, relheight=1) # Position on right edge
        next_arrow.bind("<Button-1>", lambda e: self._show_next_image_in_gallery(gallery))
        next_arrow.config(wraplength=1) # Prevent text wrapping


        self._update_gallery_image(gallery) # Pass gallery window to the update function

    def _set_window_properties_for_gallery(self, window, width, height, icon_name, parent_icon_loader):
        """Helper to set properties for the gallery window."""
        window.geometry(f"{width}x{height}")
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 50
        window.geometry(f"+{x}+{y}")
        window.resizable(False, False) # Set fixed size
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                window.iconphoto(False, icon_image)
                window._window_icon_ref = icon_image # <--- Important: Keep reference for gallery window
            except Exception as e:
                print(f"Failed to set icon for {window.title()}: {e}")

    # Specific navigation methods for the SellPropertyForm gallery
    def _show_previous_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index - 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _show_next_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index + 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _update_gallery_image(self, gallery_window):
        # This function now takes the gallery_window as an argument
        if gallery_window.gallery_image_paths:
            try:
                img_path = gallery_window.gallery_image_paths[gallery_window.current_gallery_index]
                img = Image.open(img_path)

                # Get the current dimensions of the label to fit the image
                gallery_window.image_container_frame.update_idletasks() # Ensure label has up-to-date size
                container_width = gallery_window.image_container_frame.winfo_width()
                container_height = gallery_window.image_container_frame.winfo_height()

                # Fallback for initial state if width/height are 0 or very small
                if container_width <= 1: 
                    # Use gallery window's internal dimensions, minus some padding/chrome for a rough estimate
                    container_width = gallery_window.winfo_width() - 2 
                    if container_width < 100: container_width = 100 # Minimum sensible size
                if container_height <= 1: 
                    # Use gallery window's internal dimensions, minus padding/button frame for a rough estimate
                    container_height = gallery_window.winfo_height() - 2
                    if container_height < 100: container_height = 100 # Minimum sensible size


                original_width, original_height = img.size
                
                
                ratio = min(container_width / original_width, container_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)

                # Ensure dimensions are at least 1x1 to prevent errors
                if new_width == 0: new_width = 1
                if new_height == 0: new_height = 1

                img = img.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                gallery_window.gallery_image_label.config(image=photo)
                gallery_window.gallery_image_label.image = photo # <--- Keep strong reference for image label
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not load image: {e}")
                gallery_window.gallery_image_label.config(image='', text="Error loading image.")
                gallery_window.gallery_image_label.image = None
        

class RecordSinglePaymentForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None,
                 window_icon_name="payment.png", job_id_to_pay=None):
        super().__init__(master)
        self.title("Record Payment for Property Sale" + (f" ID {job_id_to_pay}" if job_id_to_pay else ""))
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        
        # Set blue title bar (Windows only)
        try:
            from ctypes import windll, byref, sizeof, c_int
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            hwnd = windll.user32.GetParent(self.winfo_id())
            # Blue color (RGB: 0, 119, 215) -> 0x00D77700 in BGR
            color = c_int(0x00D77700)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
            # White text
            text_color = c_int(0x00FFFFFF)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
        except Exception as e:
            print(f"Could not customize title bar: {e}")

        self.db_manager = db_manager
        self.refresh_callback = refresh_callback
        self.parent_icon_loader = parent_icon_loader
        self.job_id_to_pay = job_id_to_pay

        self._window_icon_ref = None
        self._record_payment_icon = None
        self._cancel_payment_icon = None

        self._set_window_properties(500, 300, window_icon_name, parent_icon_loader)
        self._create_widgets(parent_icon_loader)
        self._load_job_details()

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

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Transaction ID:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_job_id = ttk.Label(main_frame, text=self.job_id_to_pay, font=('Helvetica', 10, 'bold'))
        self.lbl_job_id.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Client:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_client_name = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_client_name.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Fee (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_fee = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_fee.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Amount Paid (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_amount_paid = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10))
        self.lbl_amount_paid.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Current Balance:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.lbl_current_balance = ttk.Label(main_frame, text="Loading...", font=('Helvetica', 10, 'bold'), foreground='red')
        self.lbl_current_balance.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(main_frame, text="Payment Amount (KES):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.entry_payment_amount = ttk.Entry(main_frame)
        self.entry_payment_amount.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        if parent_icon_loader:
            self._record_payment_icon = parent_icon_loader("save.png", size=(20,20))
            self._cancel_payment_icon = parent_icon_loader("cancel.png", size=(20,20))

        record_btn = ttk.Button(button_frame, text="Record Payment", image=self._record_payment_icon, 
                               compound=tk.LEFT, command=self.record_payment_action)
        record_btn.pack(side="left", padx=5)
        record_btn.image = self._record_payment_icon  # Fixed this line - was using wrong variable name

        cancel_btn = ttk.Button(button_frame, text="Cancel", image=self._cancel_payment_icon, 
                               compound=tk.LEFT, command=self.destroy)
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.image = self._cancel_payment_icon

    def _load_job_details(self):
        if self.job_id_to_pay:
            job_info = self.db_manager.get_transaction(self.job_id_to_pay)
            if job_info:
                client_info = self.db_manager.get_client_by_id(job_info['client_id'])
                self.lbl_client_name.config(text=client_info['name'] if client_info else "N/A")
            if job_info:
                property_info = self.db_manager.get_property(job_info['property_id'])
                self.lbl_fee.config(text=f"KES {property_info['price']:,.2f}")
                self.lbl_amount_paid.config(text=f"KES {job_info['total_amount_paid']:,.2f}")
                
                # Calculate and display current balance
                current_balance = job_info.get('balance',0.0)
                self.lbl_current_balance.config(text=f"KES {current_balance:,.2f}")
                
                if current_balance <= 0:
                    self.lbl_current_balance.config(foreground='green')
                    self.entry_payment_amount.config(state='disabled')
                else:
                    self.lbl_current_balance.config(foreground='red')
            else:
                messagebox.showerror("Error", "Sale not found.")
                self.destroy()

    def record_payment_action(self):  # Fixed method name (removed underscore)
        payment_amount_str = self.entry_payment_amount.get().strip()

        if not payment_amount_str:
            messagebox.showerror("Input Error", "Payment amount is required.")
            return

        try:
            payment_amount = float(payment_amount_str)
            if payment_amount <= 0:
                messagebox.showerror("Invalid Amount", "Payment amount must be positive.")
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the payment amount.")
            return
        
        latest_job_info = self.db_manager.get_transaction(self.job_id_to_pay)
        if not latest_job_info:
            messagebox.showerror("Error", "Job information could not be retrieved.")
            return
        
        current_balance = latest_job_info.get('balance', 0.0)
        current_total_paid = latest_job_info.get('total_amount_paid', 0.0)
        
        if payment_amount > current_balance:
            messagebox.showerror(
                "Payment Error",
                f"Cannot process payment. Amount (KES {payment_amount:,.2f}) exceeds balance (KES {current_balance:,.2f}).\n"
                "Please enter a lower amount that doesn't exceed the outstanding balance."
            )
            return
        new_amount_paid = current_total_paid + payment_amount
        new_balance = current_balance - payment_amount

        # Update the database
        success = self.db_manager.update_transaction(
            self.job_id_to_pay, 
            total_amount_paid=new_amount_paid,
            balance=new_balance
        )
        
        if success:
            messagebox.showinfo("Success", f"Payment of KES {payment_amount:,.2f} recorded successfully!")
            self.refresh_callback()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to record payment in database.")

    def _on_closing(self):
        self.grab_release()
        self.destroy()

class TrackPaymentsForm(tk.Toplevel):
    def __init__(self, master, db_manager, refresh_callback, parent_icon_loader=None, window_icon_name="track_payments.png"):
        super().__init__(master)
        self.title("Track Payments")
        self.resizable(True, True)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.callback_on_close = refresh_callback
        self._window_icon_ref = None # <--- Added for icon persistence
        self.parent_icon_loader = parent_icon_loader
        self.callback_on_close = refresh_callback
        self.refresh_callback = refresh_callback

        # References for internal button icons
        self._apply_filters_icon = None
        self._clear_filters_icon = None # New icon for clear filters
        self._prev_icon = None
        self._next_icon = None
        self._close_icon = None

        # Pagination variables for TrackPaymentsForm (NEW/MOVED)
        self.current_page = 1
        self.items_per_page = 12 # You can adjust this as needed
        self.total_pages = 1
        self.current_transactions_data = [] # To store filtered data for pagination

        # Set window properties (size, position, icon)
        self._set_window_properties(1300, 650, window_icon_name, parent_icon_loader) # Increased height for new filters
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader) # Pass loader to _create_widgets
        self._apply_filters() # This will now call _load_page(1)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)

        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Title label
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

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
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image # <--- Keep a strong reference
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader): # Added parent_icon_loader argument
        # Custom title bar simulation (Tkinter doesn't allow direct title bar styling)
        # This will create a frame at the top that looks like a title bar
        # For a truly custom title bar, you'd need to hide the native one and draw your own,
        # which is much more complex and platform-dependent.
        # Here we'll just set the background of the main frame and add a label.
        
        #main_frame = ttk.Frame(self, padding="10", style="Blue.TFrame")
        # You'll need to define this style:
        #style = ttk.Style()
        #style.configure("Blue.TFrame", background="#2196F3") # Blue color
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        filter_frame = ttk.LabelFrame(main_frame, text="Filter Payments", padding="10")
        filter_frame.pack(fill="x", pady=5)

        # Row 0
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.status_filter_combobox = ttk.Combobox(filter_frame, values=["All", "Complete", "Pending"], state="readonly", width=10)
        self.status_filter_combobox.set("All")
        self.status_filter_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="From Date:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.from_date_entry = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.from_date_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.from_date_entry.set_date(datetime.now().date())

        ttk.Label(filter_frame, text="To Date:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.to_date_entry = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.to_date_entry.grid(row=0, column=5, padx=5, pady=2, sticky="ew")
        self.to_date_entry.set_date(datetime.now().date())

        # Row 1
        ttk.Label(filter_frame, text="Payment Mode:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.payment_mode_filter_combobox = ttk.Combobox(filter_frame, values=["", "Cash", "Instalments"], state="readonly", width=10)
        self.payment_mode_filter_combobox.set("")
        self.payment_mode_filter_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="Client Name:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.client_name_search_entry = ttk.Entry(filter_frame, width=20)
        self.client_name_search_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="Property Search:").grid(row=1, column=4, padx=5, pady=2, sticky="w")
        self.property_search_entry = ttk.Entry(filter_frame, width=20)
        self.property_search_entry.grid(row=1, column=5, padx=5, pady=2, sticky="ew")
        
        # New: Phone Number Filter (Row 2)
        ttk.Label(filter_frame, text="Phone Number:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.phone_number_search_entry = ttk.Entry(filter_frame, width=20)
        self.phone_number_search_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")


        # Buttons for filters (Row 3)
        if parent_icon_loader:
            self._apply_filters_icon = parent_icon_loader("filter.png", size=(20, 20))
            self._clear_filters_icon = parent_icon_loader("clear_filter.png", size=(20, 20)) # Assuming you have a refresh.png icon

        apply_button = ttk.Button(filter_frame, text="Apply Filters", image=self._apply_filters_icon, compound=tk.LEFT, command=self._apply_filters)
        apply_button.grid(row=3, column=0, columnspan=3, pady=10)
        apply_button.image = self._apply_filters_icon # Store reference for this button

        clear_button = ttk.Button(filter_frame, text="Clear Filters", image=self._clear_filters_icon, compound=tk.LEFT, command=self._clear_filters)
        clear_button.grid(row=3, column=3, columnspan=3, pady=10)
        clear_button.image = self._clear_filters_icon # Store reference for this button

        # Configure columns to expand
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)
        filter_frame.grid_columnconfigure(5, weight=1)


        # Updated columns to include "Client Contact"
        columns = ("Date", "Time", "Client Name", "Client Contact", "Property Title Deed", "Location", "Size", "Payment Mode", "Paid", "Discount", "Balance")
        self.payments_tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        self.payments_tree.heading("Date", text="Date")
        self.payments_tree.heading("Time", text="Time")
        self.payments_tree.heading("Client Name", text="Client Name")
        self.payments_tree.heading("Client Contact", text="Client Contact") # New Heading
        self.payments_tree.heading("Property Title Deed", text="Property Title Deed")
        self.payments_tree.heading("Location", text="Location")
        self.payments_tree.heading("Size", text="Size (Acres)")
        self.payments_tree.heading("Payment Mode", text="Payment Mode")
        self.payments_tree.heading("Paid", text="Amount Paid (KES)")
        self.payments_tree.heading("Discount", text="Discount (KES)")
        self.payments_tree.heading("Balance", text="Balance (KES)")

        self.payments_tree.column("Date", width=100, anchor="center")
        self.payments_tree.column("Time", width=80, anchor="center")
        self.payments_tree.column("Client Name", width=150, anchor="w")
        self.payments_tree.column("Client Contact", width=120, anchor="w") # New Column Width
        self.payments_tree.column("Property Title Deed", width=120, anchor="w")
        self.payments_tree.column("Location", width=150, anchor="w")
        self.payments_tree.column("Size", width=80, anchor="e")
        self.payments_tree.column("Payment Mode", width=100, anchor="center")
        self.payments_tree.column("Paid", width=120, anchor="e")
        self.payments_tree.column("Discount", width=100, anchor="e")
        self.payments_tree.column("Balance", width=120, anchor="e")

        self.payments_tree.pack(fill="both", expand=True, pady=10)

        tree_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.payments_tree.yview)
        tree_scrollbar.pack(side="right", fill="y")
        self.payments_tree.config(yscrollcommand=tree_scrollbar.set)


        self.payments_tree.bind("<<TreeviewSelect>>", self._on_job_select)
        self.payments_tree.bind("<Double-1>", self._on_tree_double_click)

        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill="x", pady=5)

        # Pagination buttons (also need icons and references)
        pagination_frame = ttk.Frame(main_frame, padding="5")
        pagination_frame.pack(fill="x", pady=5)

        if parent_icon_loader:
            self._payment_icon = parent_icon_loader("pay.png", size=(20,20))
            self._prev_icon = parent_icon_loader("arrow_left.png", size=(20, 20))
            self._next_icon = parent_icon_loader("arrow_right.png", size=(20, 20))
            self._close_icon = parent_icon_loader("cancel.png", size=(20, 20))

        self.make_payment_btn = ttk.Button(
            action_frame, 
            text="Make Payment", 
            image=self._payment_icon, 
            compound=tk.LEFT, 
            command=self._open_record_payment_form,
            state="disabled"
        )
        self.make_payment_btn.pack(side="left", padx=5)
        self.make_payment_btn.image = self._payment_icon

        self.prev_button = ttk.Button(pagination_frame, text="Previous", image=self._prev_icon, compound=tk.LEFT, command=self._go_previous_page)
        self.prev_button.pack(side="left", padx=5)
        self.prev_button.image = self._prev_icon # Store reference for this button

        self.page_info_label = ttk.Label(pagination_frame, text="Page X of Y")
        self.page_info_label.pack(side="left", padx=10)

        self.next_button = ttk.Button(pagination_frame, text="Next", image=self._next_icon, compound=tk.RIGHT, command=self._go_next_page)
        self.next_button.pack(side="left", padx=5)
        self.next_button.image = self._next_icon # Store reference for this button

        close_btn = ttk.Button(pagination_frame, text="Close", image=self._close_icon, compound=tk.LEFT, command=self.destroy)
        close_btn.pack(side="right", padx=5)
        close_btn.image = self._close_icon # Store reference for this button

        # Set a style for the Toplevel window to try and get a blue background
        # This will set the background of the *client area*, not the native title bar.
        # For a truly blue title bar, you'd need to hide the default title bar and draw your own,
        # which is highly OS-specific and complex for a simple Tkinter app.
        # ttk.Style().configure("Toplevel", background="#2196F3") # Blue color
        # self.config(background="#2196F3") # This sets the background of the Toplevel itself


    def _apply_filters(self):
        status_filter = self.status_filter_combobox.get()
        start_date = self.from_date_entry.get_date().strftime("%Y-%m-%d") if self.from_date_entry.get_date() else ""
        end_date = self.to_date_entry.get_date().strftime("%Y-%m-%d") if self.to_date_entry.get_date() else ""
        payment_mode = self.payment_mode_filter_combobox.get().strip()
        client_name_search = self.client_name_search_entry.get().strip()
        property_search = self.property_search_entry.get().strip()
        phone_number_search = self.phone_number_search_entry.get().strip() # New filter

        if start_date and end_date and start_date > end_date:
            messagebox.showwarning("Input Error", "From Date cannot be after To Date.")
            return
        
        db_status = None
        if status_filter == "Complete":
            db_status = "complete"
        elif status_filter == "Pending":
            db_status = "pending"

        db_payment_mode = payment_mode if payment_mode else None
        db_client_name_search = client_name_search if client_name_search else None
        db_property_search = property_search if property_search else None
        db_phone_number_search = phone_number_search if phone_number_search else None # New filter parameter

        # Fetch all matching transactions based on filters, then paginate locally
        self.current_transactions_data = self.db_manager.get_transactions_with_details(
            status=db_status,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            payment_mode=db_payment_mode,
            client_name_search=db_client_name_search,
            property_search=db_property_search,
            client_contact_search=db_phone_number_search # Pass the new filter
        )
        
        # Calculate total pages based on fetched data
        total_items = len(self.current_transactions_data)
        self.total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if self.total_pages == 0:
            self.total_pages = 1

        self._load_page(1) # Load the first page of filtered data

    def _clear_filters(self):
        """Resets all filter fields to their default values and reapplies filters."""
        self.status_filter_combobox.set("All")
        # --- CHANGE STARTS HERE ---
        today = datetime.now().date()
        self.from_date_entry.set_date(today) # Set to current date
        self.to_date_entry.set_date(today)   # Set to current date
        # --- CHANGE ENDS HERE ---

        self.payment_mode_filter_combobox.set("")
        self.client_name_search_entry.delete(0, tk.END)
        self.property_search_entry.delete(0, tk.END)
        self.phone_number_search_entry.delete(0, tk.END) # Clear phone number filter
        self._apply_filters() # Reapply filters to show all data

    def _load_page(self, page_number):
        """Loads data for the specified page number into the Treeview."""
        if page_number < 1:
            page_number = 1
        elif page_number > self.total_pages:
            page_number = self.total_pages

        self.current_page = page_number
        
        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        
        # Get the slice of data for the current page
        page_data = self.current_transactions_data[start_index:end_index]
        
        self._populate_transactions_treeview(page_data)
        self._update_pagination_buttons()
        self.selected_job_data = None
        self._update_payment_button_state()


    def _populate_transactions_treeview(self, transactions_data_for_page): # Renamed argument for clarity
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)

        if not transactions_data_for_page:
            self.payments_tree.insert("", "end", values=("No matching payments found.", "", "", "", "", "", "", "", "", "", ""), tags=('no_data',))
            return

        for row_data in transactions_data_for_page:
            full_date_time = row_data['transaction_date']

            date_part = full_date_time.split(' ')[0] if ' ' in full_date_time else full_date_time
            time_part = full_date_time.split(' ')[1] if ' ' in full_date_time else ""
            
            self.payments_tree.insert("", "end", values=(
                date_part,
                time_part,
                row_data['client_name'],
                row_data['client_contact_info'], # Display client contact info
                row_data['title_deed_number'],
                row_data['location'],
                f"{row_data['size']:.2f}",
                row_data['payment_mode'],
                f"{row_data['total_amount_paid']:,.2f}",
                f"{row_data['discount']:,.2f}",
                f"{row_data['balance']:,.2f}"
            ), iid=row_data['transaction_id']) # Set iid to the actual transaction_id


    def _on_tree_double_click(self, event):
        selected_item = self.payments_tree.focus()
        if selected_item:
            try:
                transaction_id = int(selected_item) 
            except ValueError:
                messagebox.showinfo("No Details", "No transaction details available for this row.")
                return

            transaction_details = self.db_manager.get_transaction(transaction_id)
            if transaction_details:
                client_details = self.db_manager.get_client(transaction_details['client_id'])
                property_details = self.db_manager.get_property(transaction_details['property_id'])

                detail_message = (
                    f"--- Transaction Details (ID: {transaction_details['transaction_id']}) ---\n"
                    f"Date: {transaction_details['transaction_date']}\n"
                    f"Payment Mode: {transaction_details['payment_mode']}\n"
                    f"Amount Paid: KES {transaction_details['total_amount_paid']:,.2f}\n"
                    f"Discount: KES {transaction_details['discount']:,.2f}\n"
                    f"Balance: KES {transaction_details['balance']:,.2f}\n\n"
                )

                if client_details:
                    detail_message += (
                        "CLIENT INFO:\n"
                        f"Name: {client_details['name']}\n"
                        f"Contact: {client_details['contact_info']}\n\n"
                    )
                if property_details:
                    detail_message += (
                        "PROPERTY INFO:\n"
                        f"Title Deed: {property_details['title_deed_number']}\n"
                        f"Location: {property_details['location']}\n"
                        f"Size: {property_details['size']:.2f} Acres\n"
                        f"Asking Price: KES {property_details['price']:,.2f}\n"
                    )
                
                if transaction_details['receipt_path']:
                    # Ensure DATA_DIR is defined and accessible for opening receipts
                    # For demonstration, let's assume it's in the same directory as the script.
                    # In a real application, you'd manage this securely.
                    if 'DATA_DIR' in globals() and os.path.exists(os.path.join(DATA_DIR, transaction_details['receipt_path'])):
                        receipt_full_path = os.path.join(DATA_DIR, transaction_details['receipt_path'])
                        if messagebox.askyesno("Transaction Details", f"{detail_message}\n\nDo you want to open the receipt now?"):
                            try:
                                os.startfile(receipt_full_path) # For Windows
                            except AttributeError:
                                # For macOS/Linux, you might use 'open' or 'xdg-open'
                                import subprocess
                                subprocess.call(('open', receipt_full_path))
                            except Exception as e:
                                messagebox.showerror("Open Error", f"Could not open receipt file: {e}")
                    else:
                        messagebox.showinfo("Transaction Details", f"{detail_message}\n\nReceipt file not found or path is invalid.")
                else:
                    messagebox.showinfo("Transaction Details", detail_message)
            else:
                messagebox.showwarning("Details", "Could not retrieve full transaction details.")

    def _on_job_select(self, event):
        """Handles job selection in the Treeview."""
        selected_item = self.payments_tree.focus()
        if selected_item:
            job_id = int(selected_item)
            self.selected_job_data = next((j for j in self.current_transactions_data if j['transaction_id'] == job_id), None)
        else:
            self.selected_job_data = None
            
        self._update_payment_button_state()

    def _update_payment_button_state(self):
        """Updates the state of the payment button based on selection and balance."""
        if self.selected_job_data and self.selected_job_data.get('balance', 0) > 0:
            self.make_payment_btn.config(state="normal")
        else:
            self.make_payment_btn.config(state="disabled")

    def _open_record_payment_form(self):
        """Opens the payment form for the selected job."""
        if not self.selected_job_data:
            messagebox.showwarning("No Selection", "Please select a job to record payment for.")
            return
            
        job_id = self.selected_job_data['transaction_id']
        if self.selected_job_data['balance'] <= 0:
            messagebox.showinfo("No Balance", "This job has no outstanding balance.")
            return

        payment_form = RecordSinglePaymentForm(
            self.master,
            self.db_manager,
            self._refresh_after_payment,
            parent_icon_loader=self.parent_icon_loader,
            window_icon_name="payment.png",
            job_id_to_pay=job_id
        )
        payment_form.wait_window()

    def _refresh_after_payment(self):
        """Refreshes the view after a payment is recorded."""
        self._apply_filters()
        if self.refresh_callback:
            self.refresh_callback()
               

    def _go_previous_page(self): # NEW/MOVED
        if self.current_page > 1:
            self._load_page(self.current_page - 1)

    def _go_next_page(self): # NEW/MOVED
        if self.current_page < self.total_pages:
            self._load_page(self.current_page + 1)

    def _update_pagination_buttons(self): # NEW/MOVED
        """Updates the state of pagination buttons and page info label."""
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")
        
        if self.total_pages == 0:
            self.page_info_label.config(text="Page 0 of 0")
        else:
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")


    def _on_closing(self):
        """Handle window closing, release grab, and call callback."""
        self.grab_release()
        self.destroy()
        if self.callback_on_close:
            self.callback_on_close()


# --- NEW SoldPropertiesView CLASS with DatePicker integration ---
class SoldPropertiesView(tk.Toplevel):
    def __init__(self, master, db_manager, callback_on_close=None, parent_icon_loader=None, window_icon_name="sold_properties.png"):
        super().__init__(master)
        self.db_manager = db_manager
        self.callback_on_close = callback_on_close
        self.title("Sold Properties Records")
        self.resizable(True, True)
        self.grab_set()
        self.transient(master)

        self.current_page = 1
        self.items_per_page = 20
        self.total_pages = 1

        self.current_filter_start_date = None
        self.current_filter_end_date = None
        self.parent_icon_loader_ref = parent_icon_loader # Store reference to the main app's icon loader
        self._window_icon_ref = None # <--- Added for icon persistence

        # References for internal button icons
        self._calendar_icon = None
        self._clear_filter_icon = None
        self._prev_page_icon = None
        self._next_page_icon = None
        self._close_sold_prop_icon = None


        # Set window properties (size, position, icon)
        self._set_window_properties(1300, 650, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader) # Pass loader to _create_widgets
        self._set_default_month_filter()
        self._load_page(self.current_page)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())

                # Set title bar color to dark blue (RGB: 0, 51, 102)
                color = c_int(0x00663300)  # BGR format for Windows
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    byref(color),
                    sizeof(color)
                )

                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    byref(text_color),
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)

        # Create custom title bar frame
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        # Title label
        title_label = tk.Label(
            title_bar,
            text=self.title(),
            bg='#003366',
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_button = tk.Button(
            title_bar,
            text='×',
            bg='#003366',
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)

        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)       

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(42, 42))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image # <--- Keep a strong reference
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _create_widgets(self, parent_icon_loader): # Added parent_icon_loader argument
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Sold Properties Overview", font=("Arial", 16, "bold")).pack(pady=10)

        # --- Date Filter Frame (NEW) ---
        date_filter_frame = ttk.Frame(main_frame, padding="5")
        date_filter_frame.pack(fill="x", pady=5)

        ttk.Label(date_filter_frame, text="Filter by Date:").pack(side="left", padx=5)
        
        self.date_filter_entry = ttk.Entry(date_filter_frame, width=25, state="readonly") # Increased width
        self.date_filter_entry.pack(side="left", padx=5)

        # Load icon for Calendar button
        if parent_icon_loader:
            self._calendar_icon = parent_icon_loader("calendar_icon.png", size=(20, 20)) 
            self._clear_filter_icon = parent_icon_loader("clear_filter.png", size=(20, 20)) 

        try:
            self.calendar_button = ttk.Button(date_filter_frame, image=self._calendar_icon, compound=tk.LEFT, command=self._open_datepicker)
            self.calendar_button.pack(side="left", padx=2)
            self.calendar_button.image = self._calendar_icon # Store reference for this button
        except Exception as e:
            print(f"Error loading calendar icon for button: {e}. Using text button.")
            self.calendar_button = ttk.Button(date_filter_frame, text="📅 Select Date", command=self._open_datepicker)
            self.calendar_button.pack(side="left", padx=2)
            
        clear_filter_btn = ttk.Button(date_filter_frame, text="Clear Filter", image=self._clear_filter_icon, compound=tk.LEFT, command=self._clear_date_filter)
        clear_filter_btn.pack(side="left", padx=10)
        clear_filter_btn.image = self._clear_filter_icon # Store reference for this button

        # --- Treeview for Displaying Sold Properties ---
        columns = (
            "Date Sold", "Time Sold", "Title Deed", "Location", "Size", "Client Name",
            "Contact Info", "Original Price", "Amount Paid", "Balance Due"
        )
        self.sold_properties_tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        self.sold_properties_tree.heading("Date Sold", text="Date Sold")
        self.sold_properties_tree.heading("Time Sold", text="Time Sold")
        self.sold_properties_tree.heading("Title Deed", text="Title Deed")
        self.sold_properties_tree.heading("Location", text="Location")
        self.sold_properties_tree.heading("Size", text="Size (Acres)")
        self.sold_properties_tree.heading("Client Name", text="Client Name")
        self.sold_properties_tree.heading("Contact Info", text="Contact Info")
        self.sold_properties_tree.heading("Original Price", text="Original Price (KES)")
        self.sold_properties_tree.heading("Amount Paid", text="Amount Paid (KES)")
        self.sold_properties_tree.heading("Balance Due", text="Balance Due (KES)")

        self.sold_properties_tree.column("Date Sold", width=100, anchor="center")
        self.sold_properties_tree.column("Time Sold", width=80, anchor="center")
        self.sold_properties_tree.column("Title Deed", width=120, anchor="w")
        self.sold_properties_tree.column("Location", width=150, anchor="w")
        self.sold_properties_tree.column("Size", width=80, anchor="e")
        self.sold_properties_tree.column("Client Name", width=150, anchor="w")
        self.sold_properties_tree.column("Contact Info", width=120, anchor="w")
        self.sold_properties_tree.column("Original Price", width=120, anchor="e")
        self.sold_properties_tree.column("Amount Paid", width=120, anchor="e")
        self.sold_properties_tree.column("Balance Due", width=120, anchor="e")

        self.sold_properties_tree.pack(fill="both", expand=True, pady=10)

        tree_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.sold_properties_tree.yview)
        tree_scrollbar.pack(side="right", fill="y")
        self.sold_properties_tree.config(yscrollcommand=tree_scrollbar.set)
        
        # --- Pagination Controls ---
        pagination_frame = ttk.Frame(main_frame, padding="5")
        pagination_frame.pack(fill="x", pady=5)

        # Load icons for pagination buttons
        if parent_icon_loader:
            self._prev_page_icon = parent_icon_loader("arrow_left.png", size=(20, 20))
            self._next_page_icon = parent_icon_loader("arrow_right.png", size=(20, 20))
            self._close_sold_prop_icon = parent_icon_loader("cancel.png", size=(20, 20))

        self.prev_button = ttk.Button(pagination_frame, text="Previous", image=self._prev_page_icon, compound=tk.LEFT, command=self._go_previous_page)
        self.prev_button.pack(side="left", padx=5)
        self.prev_button.image = self._prev_page_icon # Store reference for this button

        self.page_info_label = ttk.Label(pagination_frame, text="Page X of Y")
        self.page_info_label.pack(side="left", padx=10)

        self.next_button = ttk.Button(pagination_frame, text="Next", image=self._next_page_icon, compound=tk.RIGHT, command=self._go_next_page)
        self.next_button.pack(side="left", padx=5)
        self.next_button.image = self._next_page_icon

        close_sold_prop_btn = ttk.Button(pagination_frame, text="Close", image=self._close_sold_prop_icon, compound=tk.LEFT, command=self._on_closing)
        close_sold_prop_btn.pack(side="right", padx=5)
        close_sold_prop_btn.image = self._close_sold_prop_icon

    def _set_default_month_filter(self):
        """Sets the date filter to the beginning and end of the current month."""
        today = datetime.now()
        first_day_of_month = today.replace(day=1)
        if today.month == 12:
            last_day_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        self.current_filter_start_date = first_day_of_month.strftime("%Y-%m-%d")
        self.current_filter_end_date = last_day_of_month.strftime("%Y-%m-%d")
        
        self.date_filter_entry.config(state="normal")
        self.date_filter_entry.delete(0, tk.END)
        self.date_filter_entry.insert(0, f"Current Month ({first_day_of_month.strftime('%b %Y')})")
        self.date_filter_entry.config(state="readonly")

    def _open_datepicker(self):
        """Opens the DatePicker and sets the selected date to the entry."""
        def set_selected_date(date_str):
            self.current_filter_start_date = date_str
            self.current_filter_end_date = date_str # Filter for a single day
            
            self.date_filter_entry.config(state="normal")
            self.date_filter_entry.delete(0, tk.END)
            self.date_filter_entry.insert(0, date_str)
            self.date_filter_entry.config(state="readonly")
            
            self._load_page(1)

        # Pass the parent_icon_loader_ref to the DatePicker
        DatePicker(self, datetime.strptime(self.current_filter_start_date, "%Y-%m-%d") if self.current_filter_start_date else datetime.now(), set_selected_date, parent_icon_loader=self.parent_icon_loader_ref)

    def _clear_date_filter(self):
        """Clears the date filter and reloads data for all properties."""
        self.current_filter_start_date = None
        self.current_filter_end_date = None
        self.date_filter_entry.config(state="normal")
        self.date_filter_entry.delete(0, tk.END)
        self.date_filter_entry.insert(0, "All Dates")
        self.date_filter_entry.config(state="readonly")
        self._load_page(1)

    def _load_page(self, page_number):
        """Loads data for the specified page number into the Treeview, applying date filters."""
        total_items = self.db_manager.get_total_sold_properties_count(
            start_date=self.current_filter_start_date,
            end_date=self.current_filter_end_date
        )
        self.total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if self.total_pages == 0:
            self.total_pages = 1 

        if page_number < 1:
            page_number = 1
        elif page_number > self.total_pages:
            page_number = self.total_pages

        self.current_page = page_number
        
        offset = (self.current_page - 1) * self.items_per_page
        
        sold_properties_data = self.db_manager.get_sold_properties_paginated(
            limit=self.items_per_page,
            offset=offset,
            start_date=self.current_filter_start_date,
            end_date=self.current_filter_end_date
        )
        self._populate_sold_properties_treeview(sold_properties_data)
        self._update_pagination_buttons()

    def _populate_sold_properties_treeview(self, data):
        """Populates the Treeview with the provided sold properties data."""
        for item in self.sold_properties_tree.get_children():
            self.sold_properties_tree.delete(item)

        if not data:
            self.sold_properties_tree.insert("", "end", values=("No sold properties found for this period.", "", "", "", "", "", "", "", "", ""), tags=('no_data',))
            return

        for row in data:
            full_date_time = row['date_sold']
            date_part = full_date_time.split(' ')[0] if ' ' in full_date_time else full_date_time
            time_part = full_date_time.split(' ')[1] if ' ' in full_date_time else ""

            self.sold_properties_tree.insert("", "end", values=(
                date_part,
                time_part,
                row['title_deed_number'],
                row['location'],
                f"{row['size']:.2f}",
                row['name'],
                row['client_contact_info'],
                f"{row['original_price']:,.2f}",
                f"{row['total_amount_paid']:,.2f}",
                f"{row['balance']:,.2f}"
            ), iid=row['transaction_id'])

    def _go_previous_page(self):
        if self.current_page > 1:
            self._load_page(self.current_page - 1)

    def _go_next_page(self):
        if self.current_page < self.total_pages:
            self._load_page(self.current_page + 1)

    def _update_pagination_buttons(self):
        """Updates the state of pagination buttons and page info label."""
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")
        
        if self.total_pages == 0:
            self.page_info_label.config(text="Page 0 of 0")
        else:
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")

    def _on_closing(self):
        """Handles window closing, releases grab, and calls callback."""
        self.grab_release()
        self.destroy()
        if self.callback_on_close:
            self.callback_on_close()


# --- NEW ViewAllPropertiesForm CLASS ---
class ViewAllPropertiesForm(tk.Toplevel):
    def __init__(self, master, db_manager, callback_on_close=None, parent_icon_loader=None, window_icon_name="view_all_properties.png"):
        super().__init__(master)
        # We set resizable to False here because custom title bars often override native resizing.
        # If you need resizing, it's a much more complex implementation involving custom resize grips.
        self.resizable(False, False) # Set to False for custom title bar to handle all window events
        self.grab_set()
        self.transient(master)
        self.title("View All Properties")

        self.db_manager = db_manager
        self.callback_on_close = callback_on_close
        self.parent_icon_loader_ref = parent_icon_loader
        self._window_icon_ref = None

        self.current_page = 1
        self.items_per_page = 20 # Display first 10 newest properties (determined by id)
        self.total_pages = 1
        self.all_properties_data = [] # To store all filtered properties for pagination

        self.selected_property_data = None # Store data of the currently selected property in Treeview

        # Icon references for buttons in this form
        self._search_icon = None
        self._clear_search_icon = None
        self._edit_icon = None
        self._delete_icon = None
        self._view_images_icon = None
        self._prev_page_icon = None
        self._next_page_icon = None
        self._close_icon = None

        # Set window properties and customize title bar
        # Adjust size for the custom title bar (e.g., make it wider if needed)
        self._set_window_properties(1300, 700, window_icon_name, parent_icon_loader)
        self._customize_title_bar() # <--- ADDED CUSTOMIZE TITLE BAR CALL

        self._create_widgets(parent_icon_loader)
        
        # Configure Treeview tags for highlighting after treeview is created
        self.properties_tree.tag_configure('available_prop', background='lightgreen', foreground='darkgreen', font=('Arial', 9, 'bold'))
        self.properties_tree.tag_configure('sold_prop', background='lightcoral', foreground='darkred', font=('Arial', 9, 'bold'))
        self.properties_tree.tag_configure('no_data', foreground='gray', font=('Arial', 9, 'italic'))

        self._apply_filters() # Initial load of data

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        # Note: self.resizable(False, False) is set in __init__ due to overrideredirect
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 50 # Adjusted Y position to match your AddPropertyForm's Y = 100 relative to master, 50 looks good
        self.geometry(f"+{x}+{y}")
        
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102) -> 0x00663300 in BGR
                color = c_int(0x00663300) 
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems (Linux/macOS)
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar() # Fallback even if ctypes fails

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        # Use the dark blue color from AddPropertyForm
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text=self.title(), # Use the actual window title
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing, # Use _on_closing for proper protocol handling
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self, parent_icon_loader):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Filter and Search Frame ---
        filter_search_frame = ttk.LabelFrame(main_frame, text="Filter & Search Properties", padding="10")
        filter_search_frame.pack(fill="x", pady=5)

        filter_search_frame.columnconfigure(1, weight=1) # Make search entry expandable
        filter_search_frame.columnconfigure(4, weight=1) # Make size entries work nicely

        ttk.Label(filter_search_frame, text="Search (Title/Location):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_search_frame, textvariable=self.search_var, width=50)
        self.search_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_search_frame, text="Size (Acres) Min:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.min_size_entry = ttk.Entry(filter_search_frame, width=10)
        self.min_size_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_search_frame, text="Max:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.max_size_entry = ttk.Entry(filter_search_frame, width=10)
        self.max_size_entry.grid(row=0, column=5, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_search_frame, text="Status:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.status_filter_combobox = ttk.Combobox(filter_search_frame, values=["All", "Available", "Sold"], state="readonly", width=15)
        self.status_filter_combobox.set("All")
        self.status_filter_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")


        # Load icons for filter/search buttons
        if parent_icon_loader:
            self._search_icon = parent_icon_loader("search.png", size=(20, 20)) 
            self._clear_search_icon = parent_icon_loader("clear_filter.png", size=(20, 20))

        search_filter_btn = ttk.Button(filter_search_frame, text="Apply Filters", image=self._search_icon, compound=tk.LEFT, command=self._apply_filters)
        search_filter_btn.grid(row=1, column=6, padx=5, pady=2)
        search_filter_btn.image = self._search_icon

        clear_filter_btn = ttk.Button(filter_search_frame, text="Clear Filters", image=self._clear_search_icon, compound=tk.LEFT, command=self._clear_filters)
        clear_filter_btn.grid(row=1, column=7, padx=5, pady=2)
        clear_filter_btn.image = self._clear_search_icon


        # --- Treeview for Displaying Properties ---
        # UPDATED: Added "Added By" column
        columns = ("Property Type", "Title Deed", "Location", "Price", "Size", "Status", "Contact", "Added By","Owner")
        self.properties_tree = ttk.Treeview(main_frame, columns=columns, show="headings", style='Treeview') # Default style

        self.properties_tree.heading("Property Type", text="Type")
        self.properties_tree.heading("Title Deed", text="Title Deed")
        self.properties_tree.heading("Location", text="Location")
        self.properties_tree.heading("Price", text="Price (KES)")
        self.properties_tree.heading("Size", text="Size (Acres)")
        self.properties_tree.heading("Status", text="Status")
        self.properties_tree.heading("Contact", text="Contact") # This column will indicate images presence
        self.properties_tree.heading("Added By", text="Added By") # NEW HEADING
        self.properties_tree.heading("Owner", text="Owner")

        self.properties_tree.column("Property Type", width=60, anchor="center")
        self.properties_tree.column("Title Deed", width=150, anchor="w")
        self.properties_tree.column("Location", width=180, anchor="w")
        self.properties_tree.column("Price", width=120, anchor="e")
        self.properties_tree.column("Size", width=90, anchor="e")
        self.properties_tree.column("Status", width=90, anchor="center")
        self.properties_tree.column("Contact", width=80, anchor="center") # Small column for image indicator
        self.properties_tree.column("Added By", width=120, anchor="center") # NEW COLUMN WIDTH
        self.properties_tree.column("Owner", width=90, anchor="center")

        self.properties_tree.pack(fill="both", expand=True, pady=10)

        tree_scrollbar_y = ttk.Scrollbar(main_frame, orient="vertical", command=self.properties_tree.yview)
        tree_scrollbar_y.pack(side="right", fill="y")
        self.properties_tree.config(yscrollcommand=tree_scrollbar_y.set)
        
        self.properties_tree.bind("<<TreeviewSelect>>", self._on_property_select)

        # Optional: Double-click on "Images" column to open gallery directly
        # self.properties_tree.bind("<Double-1>", self._on_tree_double_click_for_gallery)


        # --- Pagination and Action Buttons ---
        bottom_controls_frame = ttk.Frame(main_frame, padding="5")
        bottom_controls_frame.pack(fill="x", pady=5)
        
        # Left side: Edit/Delete/View Images buttons
        action_buttons_frame = ttk.Frame(bottom_controls_frame)
        action_buttons_frame.pack(side="left", padx=10)

        if parent_icon_loader:
            self._edit_icon = parent_icon_loader("edit.png", size=(20, 20)) 
            self._delete_icon = parent_icon_loader("delete.png", size=(20, 20)) 
            self._view_images_icon = parent_icon_loader("view_images.png", size=(20, 20)) 

        self.edit_button = ttk.Button(action_buttons_frame, text="Edit Property", image=self._edit_icon, compound=tk.LEFT, command=self._open_edit_property_form, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        self.edit_button.image = self._edit_icon

        self.delete_button = ttk.Button(action_buttons_frame, text="Delete Property", image=self._delete_icon, compound=tk.LEFT, command=self._delete_property, state="disabled")
        self.delete_button.pack(side="left", padx=5)
        self.delete_button.image = self._delete_icon
        
        self.view_images_button = ttk.Button(action_buttons_frame, text="View Images", image=self._view_images_icon, compound=tk.LEFT, command=self._open_image_gallery_from_view, state="disabled")
        self.view_images_button.pack(side="left", padx=5)
        self.view_images_button.image = self._view_images_icon


        # Right side: Pagination buttons and Close
        pagination_frame = ttk.Frame(bottom_controls_frame)
        pagination_frame.pack(side="right", padx=10)

        if parent_icon_loader:
            self._prev_page_icon = parent_icon_loader("arrow_left.png", size=(20, 20))
            self._next_page_icon = parent_icon_loader("arrow_right.png", size=(20, 20))
            self._close_icon = parent_icon_loader("cancel.png", size=(20, 20))

        self.prev_button = ttk.Button(pagination_frame, text="Previous", image=self._prev_page_icon, compound=tk.LEFT, command=self._go_previous_page, state="disabled")
        self.prev_button.pack(side="left", padx=5)
        self.prev_button.image = self._prev_page_icon

        self.page_info_label = ttk.Label(pagination_frame, text="Page X of Y")
        self.page_info_label.pack(side="left", padx=10)

        self.next_button = ttk.Button(pagination_frame, text="Next", image=self._next_page_icon, compound=tk.RIGHT, command=self._go_next_page, state="disabled")
        self.next_button.pack(side="left", padx=5)
        self.next_button.image = self._next_page_icon

        close_btn = ttk.Button(pagination_frame, text="Close", image=self._close_icon, compound=tk.LEFT, command=self._on_closing)
        close_btn.pack(side="right", padx=5)
        close_btn.image = self._close_icon

        self._update_action_buttons_state() # Initial state update

    def _apply_filters(self):
        """Applies filters and reloads the first page of properties."""
        search_query = self.search_entry.get().strip()
        min_size_str = self.min_size_entry.get().strip()
        max_size_str = self.max_size_entry.get().strip()
        status_filter = self.status_filter_combobox.get().strip()

        min_size = None
        max_size = None

        if min_size_str:
            try:
                min_size = float(min_size_str)
                if min_size < 0:
                    messagebox.showwarning("Input Error", "Minimum size cannot be negative.")
                    self.min_size_entry.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Min Size. Please enter a number.")
                self.min_size_entry.delete(0, tk.END)
                return

        if max_size_str:
            try:
                max_size = float(max_size_str)
                if max_size < 0:
                    messagebox.showwarning("Input Error", "Maximum size cannot be negative.")
                    self.max_size_entry.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Max Size. Please enter a number.")
                self.max_size_entry.delete(0, tk.END)
                return

        if min_size is not None and max_size is not None and min_size > max_size:
            messagebox.showwarning("Input Error", "Minimum size cannot be greater than maximum size.")
            return
        
        # Determine DB status filter
        db_status = None
        if status_filter == "Available":
            db_status = "Available"
        elif status_filter == "Sold":
            db_status = "Sold"
        # If "All", db_status remains None, fetching all properties

        # Fetch all matching properties based on filters, then paginate locally
        self.all_properties_data = self.db_manager.get_all_properties_paginated(
            limit=None, # Fetch all for local pagination
            offset=None, # Fetch all for local pagination
            search_query=search_query if search_query else None,
            min_size=min_size,
            max_size=max_size,
            status=db_status
        )
        
        # Sort by property_id to get newest first (assuming higher ID means newer)
        self.all_properties_data.sort(key=lambda x: x.get('property_id', 0), reverse=True)


        # Calculate total pages based on fetched data
        total_items = len(self.all_properties_data)
        self.total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if self.total_pages == 0:
            self.total_pages = 1

        self._load_page(1) # Load the first page of filtered data

    def _clear_filters(self):
        """Clears all search and filter fields and reloads properties."""
        self.search_var.set("")
        self.min_size_entry.delete(0, tk.END)
        self.max_size_entry.delete(0, tk.END)
        self.status_filter_combobox.set("All")
        self._apply_filters() # Re-apply to show all properties

    def _load_page(self, page_number):
        """Loads data for the specified page number into the Treeview."""
        if page_number < 1:
            page_number = 1
        elif page_number > self.total_pages:
            page_number = self.total_pages

        self.current_page = page_number
        
        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        
        # Get the slice of data for the current page
        page_data = self.all_properties_data[start_index:end_index]
        
        self._populate_properties_treeview(page_data)
        self._update_pagination_buttons()
        self.selected_property_data = None # Clear selection on page change
        self._update_action_buttons_state() # Update buttons after clearing selection


    def _populate_properties_treeview(self, properties_data_for_page):
        """Populates the Treeview with the provided properties data."""
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)

        if not properties_data_for_page:
            # Using the 'no_data' tag for styling
            self.properties_tree.insert("", "end", values=("No properties found.", "", "", "", "", "", "", "",""), tags=('no_data',))
            return

        for prop in properties_data_for_page:
            # Determine tags for highlighting
            tags = ()
            if prop['status'].lower() == 'available':
                tags = ('available_prop',)
            elif prop['status'].lower() == 'sold':
                tags = ('sold_prop',)

            # Determine image indicator
            image_indicator = ""
            if prop.get('image_paths'):
                # Check if image_paths is not empty or just whitespace
                if any(path.strip() for path in prop['image_paths'].split(',')):
                    image_indicator = "🖼️ View"
            
            self.properties_tree.insert("", "end", values=(
                prop['property_type'],
                prop['title_deed_number'].upper(),
                prop['location'].upper(),
                f"KES {prop['price']:,.2f}",
                f"{prop['size']:.2f}",
                prop['status'].upper(),
                prop['contact'].upper(),
                prop.get('added_by_username', 'N/A').upper(),
                prop['owner'].upper(),
            ), iid=prop['property_id'], tags=tags)


    def _on_property_select(self, event):
        """Called when a property row is selected in the Treeview."""
        selected_item_id = self.properties_tree.focus()
        if selected_item_id:
            # Find the full property data for the selected item
            # The iid of the treeview item is the property_id
            try:
                property_id = int(selected_item_id) 
                self.selected_property_data = next((p for p in self.all_properties_data if p['property_id'] == property_id), None)
            except ValueError: # Handle if a non-integer iid is selected (e.g., "No properties found.")
                self.selected_property_data = None
        else:
            self.selected_property_data = None
        
        self._update_action_buttons_state()

    def _update_action_buttons_state(self):
        """Updates the state of Edit, Delete, and View Images buttons."""
        is_selected_and_available = (self.selected_property_data and 
                                     self.selected_property_data['status'].lower() == 'available')
        
        # Only enable Edit and Delete if property is selected AND is 'Available'
        self.edit_button.config(state="normal" if is_selected_and_available else "disabled")
        self.delete_button.config(state="normal" if is_selected_and_available else "disabled")

        # View Images button is enabled if any property is selected and has image paths
        has_images = (self.selected_property_data and 
                      self.selected_property_data.get('image_paths') and 
                      any(path.strip() for path in self.selected_property_data['image_paths'].split(',')))
        self.view_images_button.config(state="normal" if has_images else "disabled")

    def _open_image_gallery_from_view(self):
        """Opens the image gallery for the selected property."""
        if not self.selected_property_data:
            messagebox.showwarning("No Selection", "Please select a property to view its images.")
            return

        image_paths_str = self.selected_property_data.get('image_paths')
        if not image_paths_str:
            messagebox.showinfo("No Images", "This property has no images attached.")
            return
        
        # Convert relative paths to full paths for the gallery
        full_image_paths = [os.path.join(DATA_DIR, path.strip()) for path in image_paths_str.split(',') if path.strip()]
        
        if not full_image_paths:
            messagebox.showinfo("No Images", "No valid images found for this property.")
            return

        gallery = tk.Toplevel(self)
        gallery.title(f"Images for: {self.selected_property_data['title_deed_number']}")
        gallery.transient(self)
        gallery.grab_set()
        gallery.resizable(False, False) # Fixed size for gallery

        # Set fixed size for the gallery window, e.g., 800x600 (adjust as needed)
        gallery_width = 422
        gallery_height = 452
        self._set_window_properties_for_gallery(gallery, gallery_width, gallery_height, "view_images.png", self.parent_icon_loader_ref) 

        # Store gallery-specific state on the gallery Toplevel itself
        gallery.current_gallery_index = 0
        gallery.gallery_image_paths = full_image_paths
        
        # DEBUG Print
        print(f"DEBUG (ViewAllPropertiesForm Gallery): Toplevel created: {gallery}, paths count: {len(gallery.gallery_image_paths)}, current_index: {gallery.current_gallery_index}")

        gallery.image_container_frame = ttk.Frame(gallery, relief="solid")
        gallery.image_container_frame.pack(fill="both", expand=True)


        gallery.gallery_image_label = ttk.Label(gallery.image_container_frame, background="black") # Set background for black bars if image is smaller
        gallery.gallery_image_label.pack(fill="both", expand=True)

        # Create navigation arrow labels directly on the image label's parent
        # Left Arrow
        prev_arrow = ttk.Label(gallery.image_container_frame, text='◀', font=('Arial', 24, 'bold'), 
                               foreground='black',  cursor='hand2')
        prev_arrow.place(relx=0, rely=0.5, anchor='w', relwidth=0.15, relheight=1) # Position on left edge
        prev_arrow.bind("<Button-1>", lambda e: self._show_previous_gallery_image(gallery))
        prev_arrow.config(wraplength=1) # Prevent text wrapping

        # Right Arrow
        next_arrow = ttk.Label(gallery.image_container_frame, text='▶', font=('Arial', 24, 'bold'), 
                               foreground='black',cursor='hand2')
        next_arrow.place(relx=1, rely=0.5, anchor='e', relwidth=0.15, relheight=1) # Position on right edge
        next_arrow.bind("<Button-1>", lambda e: self._show_next_gallery_image(gallery))
        next_arrow.config(wraplength=1) # Prevent text wrapping
        
        self._update_gallery_image_display(gallery) # Pass gallery window to the update function

    def _set_window_properties_for_gallery(self, window, width, height, icon_name, parent_icon_loader):
        """Helper to set properties for the gallery window."""
        window.geometry(f"{width}x{height}")
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 50
        window.geometry(f"+{x}+{y}")
        window.resizable(False, False) # Fixed size for gallery
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                window.iconphoto(False, icon_image)
                window._window_icon_ref = icon_image 
            except Exception as e:
                print(f"Failed to set icon for {window.title()}: {e}")

    def _show_previous_gallery_image(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index - 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image_display(gallery_window)

    def _show_next_gallery_image(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index + 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image_display(gallery_window)

    def _update_gallery_image_display(self, gallery_window):
        if gallery_window.gallery_image_paths:
            try:
                img_path = gallery_window.gallery_image_paths[gallery_window.current_gallery_index]
                img = Image.open(img_path)

                gallery_window.image_container_frame.update_idletasks() # Ensure label has up-to-date size
                container_width = gallery_window.image_container_frame.winfo_width()
                container_height = gallery_window.image_container_frame.winfo_height()

                # Fallback for initial state if width/height are 0 or very small
                if container_width <= 1: 
                    container_width = gallery_window.winfo_width() - 60 # Subtract approximate padding/frame
                    if container_width < 100: container_width = 100 # Minimum sensible size
                if container_height <= 1: 
                    container_height = gallery_window.winfo_height() - 60 # Subtract approx padding/button frame
                    if container_height < 100: container_height = 100 # Minimum sensible size

                original_width, original_height = img.size
                
            
                

                ratio = min(container_width / original_width, container_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)

                # Ensure dimensions are at least 1x1 to prevent errors
                if new_width == 0: new_width = 1
                if new_height == 0: new_height = 1

                img = img.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                gallery_window.gallery_image_label.config(image=photo)
                gallery_window.gallery_image_label.image = photo # Keep strong reference for image label
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not load image: {e}")
                gallery_window.gallery_image_label.config(image='', text="Error loading image.")
                gallery_window.gallery_image_label.image = None
        else:
            gallery_window.gallery_image_label.config(image='', text="No image to display.")
            gallery_window.gallery_image_label.image = None

    def _open_edit_property_form(self):
        """Opens the EditPropertyForm for the selected property."""
        if not self.selected_property_data:
            messagebox.showwarning("No Selection", "Please select a property to edit.")
            return
        
        # Pass the full property data to the Edit form
        EditPropertyForm(self, self.db_manager, self._on_edit_or_delete_complete, 
                        self.selected_property_data, self.parent_icon_loader_ref, "edit.png")

    def _delete_property(self):
        """Deletes the selected property after confirmation."""
        if not self.selected_property_data:
            messagebox.showwarning("No Selection", "Please select a property to delete.")
            return

        prop_id = self.selected_property_data['property_id']
        title_deed = self.selected_property_data['title_deed_number']

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete property '{title_deed}' (ID: {prop_id})?\nThis action cannot be undone."):
            try:
                success = self.db_manager.delete_property(prop_id)
                if success:
                    messagebox.showinfo("Success", f"Property '{title_deed}' deleted successfully.")
                    self._on_edit_or_delete_complete() # Refresh the list
                else:
                    messagebox.showerror("Deletion Failed", "Failed to delete property from the database.")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred during deletion: {e}")

    def _on_edit_or_delete_complete(self):
        """Callback to refresh the properties list after an edit or delete operation."""
        self._apply_filters() # Re-apply filters to refresh the view
        if self.callback_on_close:
            self.callback_on_close() # Also inform the main app to refresh its overview


    def _go_previous_page(self):
        if self.current_page > 1:
            self._load_page(self.current_page - 1)

    def _go_next_page(self):
        if self.current_page < self.total_pages:
            self._load_page(self.current_page + 1)

    def _update_pagination_buttons(self):
        """Updates the state of pagination buttons and page info label."""
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")
        
        if self.total_pages == 0:
            self.page_info_label.config(text="Page 0 of 0")
        else:
            self.page_info_label.config(text=f"Page {self.current_page} of {self.total_pages}")


    def _on_closing(self):
        """Handles window closing, releases grab, and calls callback."""
        self.grab_release()
        self.destroy()
        if self.callback_on_close:
            self.callback_on_close()


class SalesReportsForm(tk.Toplevel):
    def __init__(self, master, db_manager, parent_icon_loader=None, window_icon_name="reports.png"):
        super().__init__(master)
        # REMOVED: self.overrideredirect(True) -- Native title bar now handled by _customize_title_bar
        self.resizable(False, False) # Keep fixed size for reports window
        self.grab_set() # Keep the window modal
        self.transient(master) # Keep it on top of the master window
        self.title("Reports")

        self.db_manager = db_manager
        self.parent_icon_loader_ref = parent_icon_loader
        self._window_icon_ref = None # For window icon persistence

        self._calendar_icon = None
        self._generate_report_icon = None
        self._close_icon = None # For the close button *within* the form content

        self.from_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))
        self.to_date_var = tk.StringVar(self, value=datetime.now().strftime("%Y-%m-%d"))

        self.sales_report_text = None
        self.sold_properties_report_text = None
        self.pending_instalments_report_text = None

        # These are only used for the custom title bar fallback (non-Windows)
        self._start_x = 0
        self._start_y = 0

        # Set initial window properties (geometry, icon)
        self._set_window_properties(850, 550, window_icon_name, parent_icon_loader)
        
        # Apply custom title bar styling
        self._customize_title_bar() 

        # Create and lay out widgets below the (now natively styled or custom) title bar
        self._create_widgets(parent_icon_loader)

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks() # Ensure window dimensions are calculated
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 100
        self.geometry(f"+{x}+{y}")
        
        # Set icon for the window itself (this will appear in the native title bar)
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(52, 52))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image # Store strong reference for icon
            except Exception as e:
                print(f"Failed to set icon for {self.winfo_name()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            # Windows-specific title bar customization
            if os.name == 'nt':
                from ctypes import windll, byref, sizeof, c_int
                
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # Set title bar color to dark blue (RGB: 0, 51, 102) -> 0x00663300 in BGR
                color = c_int(0x00663300) 
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    byref(color), 
                    sizeof(color)
                )
                
                # Set title text color to white
                text_color = c_int(0x00FFFFFF)  # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    byref(text_color), 
                    sizeof(text_color)
                )
            else:
                # Fallback for non-Windows systems (Linux/macOS)
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar() # Fallback even if ctypes fails

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        # Remove native title bar
        self.overrideredirect(True)
        
        # Create custom title bar frame
        # Use the dark blue color from AddPropertyForm
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text=self.title(), # Use the actual window title
            bg='#003366', 
            fg='white',
            font=('Helvetica', 10)
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        close_button = tk.Button(
            title_bar, 
            text='×', 
            bg='#003366', 
            fg='white',
            bd=0,
            activebackground='red',
            command=self._on_closing, # Use _on_closing for proper protocol handling
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind mouse events for window dragging
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

        # No minimize button for custom title bar (as requested)

    def _save_drag_start_pos(self, event):
        """Saves the initial position for window dragging (used in fallback)."""
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        """Handles window movement for custom title bar (used in fallback)."""
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self, parent_icon_loader):
        """Creates all UI widgets and the Notebook for tabs."""
        content_frame = ttk.Frame(self, padding="15")
        content_frame.pack(fill="both", expand=True)

        if parent_icon_loader:
            self._calendar_icon = parent_icon_loader("calendar_icon.png", size=(20, 20))
            self._generate_report_icon = parent_icon_loader("report.png", size=(20, 20))
            self._close_icon = parent_icon_loader("cancel.png", size=(20, 20))

        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill="both", expand=True)

        self._create_sales_report_tab(notebook)
        self._create_sold_properties_tab(notebook)
        self._create_pending_instalments_tab(notebook)

        # Close button at the bottom of the form (within content_frame)
        close_btn = ttk.Button(content_frame, text="Close", image=self._close_icon, compound=tk.LEFT, command=self.destroy)
        close_btn.image = self._close_icon 
        close_btn.pack(pady=10)

    def _create_sales_report_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Sales Report")
        self._create_report_tab(
            frame, "sales", "Sales", 
            self._generate_sales_report, 
            "sales_report_text"
        )

    def _create_sold_properties_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Sold Properties")
        self._create_report_tab(
            frame, "sold_properties", "Sold Properties", 
            self._generate_sold_properties_report, 
            "sold_properties_report_text"
        )

    def _create_pending_instalments_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Pending Instalments")
        self._create_report_tab(
            frame, "pending_instalments", "Pending Instalments", 
            self._generate_pending_instalments_report, 
            "pending_instalments_report_text"
        )

    def _create_report_tab(self, parent_frame, report_prefix, report_title, generate_function, text_widget_attr_name):
        control_frame = ttk.LabelFrame(parent_frame, text=f"{report_title} Report Options", padding="10")
        control_frame.pack(fill="x", pady=10)

        report_type_var = tk.StringVar(control_frame, value="daily") 
        ttk.Label(control_frame, text="Select Report Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Daily", variable=report_type_var, value="daily",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, False, v)).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Monthly", variable=report_type_var, value="monthly",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, False, v)).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(control_frame, text="Custom Range", variable=report_type_var, value="custom",
                        command=lambda v=report_type_var: self._toggle_date_entries(control_frame, True, v)).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        date_range_frame = ttk.Frame(control_frame)
        date_range_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="ew")
        
        ttk.Label(date_range_frame, text="From:").pack(side="left", padx=5)
        from_entry = ttk.Entry(date_range_frame, textvariable=self.from_date_var, state="readonly", width=15)
        from_entry.pack(side="left", padx=2)
        from_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon, command=lambda: self._open_datepicker(self.from_date_var))
        from_cal_btn.image = self._calendar_icon
        from_cal_btn.pack(side="left", padx=2)

        ttk.Label(date_range_frame, text="To:").pack(side="left", padx=5)
        to_entry = ttk.Entry(date_range_frame, textvariable=self.to_date_var, state="readonly", width=15)
        to_entry.pack(side="left", padx=2)
        to_cal_btn = ttk.Button(date_range_frame, image=self._calendar_icon, command=lambda: self._open_datepicker(self.to_date_var))
        to_cal_btn.image = self._calendar_icon
        to_cal_btn.pack(side="left", padx=2)

        control_frame._from_entry = from_entry
        control_frame._to_entry = to_entry
        control_frame._from_cal_btn = from_cal_btn
        control_frame._to_cal_btn = to_cal_btn

        self._toggle_date_entries(control_frame, False, report_type_var)

        generate_btn = ttk.Button(control_frame, text=f"Generate {report_title} Report",
                                     image=self._generate_report_icon, compound=tk.LEFT,
                                     command=lambda: generate_function(report_type_var.get()))
        generate_btn.image = self._generate_report_icon
        generate_btn.grid(row=2, column=0, columnspan=4, pady=10)

        report_preview_frame = ttk.LabelFrame(parent_frame, text="Report Preview", padding="10")
        report_preview_frame.pack(fill="both", expand=True, pady=10)
        report_preview_frame.grid_columnconfigure(0, weight=1)
        report_preview_frame.grid_rowconfigure(0, weight=1)
        
        report_text = tk.Text(report_preview_frame, wrap=tk.WORD, height=15, font=('Helvetica', 9))
        report_text.grid(row=0, column=0, sticky="nsew")
        
        report_scroll_y = ttk.Scrollbar(report_preview_frame, orient="vertical", command=report_text.yview)
        report_scroll_y.grid(row=0, column=1, sticky="ns")
        report_text.config(yscrollcommand=report_scroll_y.set)

        report_scroll_x = ttk.Scrollbar(report_preview_frame, orient="horizontal", command=report_text.xview)
        report_scroll_x.grid(row=1, column=0, sticky="ew")
        report_text.config(xscrollcommand=report_scroll_x.set)

        setattr(self, text_widget_attr_name, report_text)


    def _toggle_date_entries(self, control_frame, enable, report_type_var):
        """Enables/disables custom date entry fields."""
        state = "normal" if enable else "readonly"
        button_state = "normal" if enable else "disabled"

        control_frame._from_entry.config(state=state)
        control_frame._to_entry.config(state=state)
        control_frame._from_cal_btn.config(state=button_state)
        control_frame._to_cal_btn.config(state=button_state)

        if not enable:
            today = datetime.now()
            current_report_type = report_type_var.get()
            if current_report_type == "daily":
                self.from_date_var.set(today.strftime("%Y-%m-%d"))
                self.to_date_var.set(today.strftime("%Y-%m-%d"))
            elif current_report_type == "monthly":
                first_day_of_month = today.replace(day=1)
                # Calculate last day of the current month
                if today.month == 12:
                    last_day_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                self.from_date_var.set(first_day_of_month.strftime("%Y-%m-%d"))
                self.to_date_var.set(last_day_of_month.strftime("%Y-%m-%d"))


    def _open_datepicker(self, target_var):
        """Opens date picker for a specific StringVar."""
        current_date_str = target_var.get()
        try:
            current_date_obj = datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            current_date_obj = datetime.now()

        # Assuming you have a DatePicker class implemented in this file or imported
        DatePicker(self, current_date_obj, lambda d: target_var.set(d),
                   parent_icon_loader=self.parent_icon_loader_ref,
                   window_icon_name="calendar_icon.png")

    def _get_report_dates(self, report_type):
        """Determines start and end dates based on report type."""
        today = datetime.now()
        start_date = None
        end_date = None

        if report_type == "daily":
            start_date = today.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif report_type == "monthly":
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")
        elif report_type == "custom":
            start_date = self.from_date_var.get()
            end_date = self.to_date_var.get()
            if not self._is_valid_date(start_date) or not self._is_valid_date(end_date):
                messagebox.showerror("Date Error", "Invalid custom date range. Please use YYYY-MM-DD format.")
                return None, None
            if start_date > end_date:
                messagebox.showerror("Date Error", "Start date cannot be after end date.")
                return None, None
        return start_date, end_date

    def _is_valid_date(self, date_string):
        """Validates date format."""
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _generate_pdf_report(self, report_name, content, report_type, start_date, end_date):
        """Generates PDF report using ReportLab and returns the file path."""
        if not _REPORTLAB_AVAILABLE:
            return None # Error message already shown by calling function

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        period_suffix = ""
        
        if report_type == "daily":
            period_suffix = f"_{start_date}"
        elif report_type == "monthly":
            period_suffix = f"_{datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m')}"
        elif report_type == "custom":
            period_suffix = f"_{start_date}_to_{end_date}"
        
        file_name = f"{report_name.replace(' ', '_')}{period_suffix}_{timestamp}.pdf"
        file_path = os.path.join(REPORTS_DIR, file_name)
        
        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Business Header with Timestamp
            header_table = Table([
                ["MATHENGE REAL ESTATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ], colWidths=[4*inch, 2*inch])
            
            header_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (0,-1), 14),
                ('FONTSIZE', (1,0), (1,-1), 10),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(header_table)
            
            # Report Title
            story.append(Paragraph(f"<b>{report_name.upper()}</b>", styles['Heading2']))
            story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
            story.append(Spacer(1, 12))
            
            if "SALES REPORT" in report_name.upper():
                # Accounting-style transaction table
                table_data = [
                    ["Item", "Title Deed", "Qty", "Actual Price ", "Amount Paid", "Balance"]
                ]
                
                gross_sales = 0.0
                net_sales = 0.0
                
                for item in content.get('data', []):
                    # Ensure numeric values are numbers before adding to sums
                    actual_price = float(item.get('actual_price', 0)) if item.get('actual_price') is not None else 0.0
                    amount_paid = float(item.get('amount_paid', 0)) if item.get('amount_paid') is not None else 0.0
                    balance = float(item.get('balance', 0)) if item.get('balance') is not None else 0.0

                    table_data.append([
                        item.get('property_type', 'N/A'),
                        item.get('title_deed', 'N/A'),
                        "1", # Quantity is always 1 for a property
                        f" {actual_price:,.2f}",
                        f" {amount_paid:,.2f}",
                        f" {balance:,.2f}"
                    ])
                    gross_sales += actual_price
                    net_sales += amount_paid
                    total_deficit = gross_sales - net_sales

                
                # Create table
                t = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 0.5*inch, 1*inch, 1*inch, 1*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'), # Data rows
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('ALIGN', (2,0), (-1,-1), 'RIGHT'), # Align Qty, Prices, Balance to right
                    ('ALIGN', (0,0), (1,-1), 'LEFT'), # Align Item, Title Deed to left
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-3), 0.5, colors.lightgrey), # Grid for data rows only
                    ('LINEBELOW', (0,0), (-1,0), 1, colors.black), # Line below header
                    ('LINEABOVE', (0,-2), (-1,-2), 1, colors.black), # Line above separator
                    ('LINEBELOW', (0,-2), (-1,-2), 1, colors.black), # Line below separator
                    ('LINEBELOW', (0,-1), (-1,-1), 2, colors.black), # Thick line below totals
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), # Header background
                    ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), # Totals row background
                    ('SPAN', (0,-1), (1,-1)), # Span "TOTALS" across Item and Title Deed
                ]))
                story.append(t)
                
                # Accounting summary below the table (can be removed if table totals are sufficient)
                story.append(Spacer(1, 12))
                summary_data = [
                    ["GROSS SALES:", f"KES {gross_sales:,.2f}"],
                    ["NET SALES:", f"KES {net_sales:,.2f}"],
                    ["PENDING:", f"KES {total_deficit:,.2f}"]
                ]
                
                summary_table = Table(summary_data, colWidths=[1.5*inch, 1*inch])
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'), # Bold for summary labels
                    ('FONTNAME', (1,0), (1,-1), 'Helvetica'), # Numbers not bold
                    ('FONTSIZE', (0,0), (-1,-1), 10),
                    ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(summary_table)
                
            elif "SOLD PROPERTIES" in report_name.upper():
                if content.get('data'):
                    headers = ["Date", "Title Deed", "Location", "Size(Acres)", "Client", "Paid", "Balance"]
                    table_data = [headers]
                    
                    for prop in content['data']:
                        date_part = prop['date_sold'].split(' ')[0] if ' ' in prop['date_sold'] else prop['date_sold']
                        table_data.append([
                            date_part,
                            prop['title_deed_number'],
                            prop['location'],
                            f"{prop['size']:.2f}",
                            prop['client_name'],
                            f"KES {prop['total_amount_paid']:,.2f}",
                            f"KES {prop['balance']:,.2f}"
                        ])
                    
                    t = Table(table_data, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 0.7*inch, 1.2*inch, 1*inch, 1*inch])
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,0), (-1,-1), 8),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ]))
                    story.append(t)
                else:
                    story.append(Paragraph("No properties sold in this period", styles['Normal']))
                    
            elif "PENDING INSTALMENTS" in report_name.upper():
                if content.get('data'):
                    headers = ["Date", "Client", "Title Deed", "Original Price", "Paid", "Balance Due"] # Updated header
                    table_data = [headers]
                    
                    for inst in content['data']:
                        date_part = inst['transaction_date'].split(' ')[0] if ' ' in inst['transaction_date'] else inst['transaction_date']
                        table_data.append([
                            date_part,
                            inst['client_name'],
                            inst['title_deed_number'],
                            f"KES {inst['original_price']:,.2f}",
                            f"KES {inst['total_amount_paid']:,.2f}",
                            f"KES {inst['balance']:,.2f}"
                        ])
                    
                    t = Table(table_data, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch, 1*inch]) # Adjusted colWidths
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,0), (-1,-1), 8),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ]))
                    story.append(t)
                else:
                    story.append(Paragraph("No pending instalments found", styles['Normal']))
            
            # Build the PDF
            doc.build(story)
            return file_path
            
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return None

    def _show_pdf_preview(self, pdf_path, report_text_widget):
        """Displays PDF generation status in the preview area."""
        if pdf_path and os.path.exists(pdf_path):
            preview_text = f"PDF successfully generated and saved to:\n{pdf_path}\n\n"
            preview_text += "Note: A full PDF preview is not available directly within Tkinter. You can open the file from the saved location.\n\n"
            
            # Add a basic file info
            preview_text += f"File size: {os.path.getsize(pdf_path)/1024:.1f} KB"
            
            report_text_widget.delete(1.0, tk.END)
            report_text_widget.insert(tk.END, preview_text)
        else:
            report_text_widget.delete(1.0, tk.END)
            report_text_widget.insert(tk.END, "PDF generation failed. Please check the error logs or ensure ReportLab is installed and data is available.")


    # --- Report Generation Functions ---

    def _generate_sales_report(self, report_type):
        """Generates sales report (detailed accounting style) as PDF and shows preview."""
        report_text_widget = self.sales_report_text
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Sales report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error", "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END) # Clear previous content
        report_text_widget.insert("1.0", "Generating report, please wait...") # Show status

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None: 
            report_text_widget.delete("1.0", tk.END) # Clear "generating" message
            return # Date validation failed

        try:
            # Fetch detailed sales transactions for the accounting report
            detailed_sales_data = self.db_manager.get_detailed_sales_transactions_for_date_range(start_date, end_date)
            
            pdf_path = self._generate_pdf_report(
                "Sales Report",
                {'data': detailed_sales_data}, # Pass detailed data
                report_type,
                start_date,
                end_date
            )
            
            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Sales Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Sales Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating Sales Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")

    def _generate_sold_properties_report(self, report_type):
        """Generates sold properties report as PDF and shows preview."""
        report_text_widget = self.sold_properties_report_text
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Sold properties report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error", "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            sold_properties = self.db_manager.get_sold_properties_for_date_range_detailed(start_date, end_date)
            
            pdf_path = self._generate_pdf_report(
                "Sold Properties Report",
                {'data': sold_properties}, # Pass detailed data
                report_type,
                start_date,
                end_date
            )
            
            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Sold Properties Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Sold Properties Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating Sold Properties Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")

    def _generate_pending_instalments_report(self, report_type):
        """Generates pending instalments report as PDF and shows preview."""
        report_text_widget = self.pending_instalments_report_text
        if report_text_widget is None:
            messagebox.showerror("Internal Error", "Pending instalments report text widget not initialized.")
            return

        if not _REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error", "ReportLab library is not installed. PDF generation is not available. Please install it using 'pip install reportlab'.")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", "Error: ReportLab not installed for PDF generation.")
            return

        report_text_widget.delete("1.0", tk.END)
        report_text_widget.insert("1.0", "Generating report, please wait...")

        start_date, end_date = self._get_report_dates(report_type)
        if start_date is None:
            report_text_widget.delete("1.0", tk.END)
            return

        try:
            pending_instalments = self.db_manager.get_pending_instalments_for_date_range(start_date, end_date)
            
            pdf_path = self._generate_pdf_report(
                "Pending Instalments Report",
                {'data': pending_instalments}, # Pass detailed data
                report_type,
                start_date,
                end_date
            )
            
            if pdf_path:
                SuccessMessage(
                    self,
                    success=True,
                    message="Pending Instalments Report PDF generated successfully!",
                    pdf_path=pdf_path,
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(pdf_path, report_text_widget)
            else:
                SuccessMessage(
                    self,
                    success=False,
                    message="Pending Instalments Report PDF generation failed!",
                    parent_icon_loader=self.parent_icon_loader_ref
                )
                self._show_pdf_preview(None, report_text_widget)
        except Exception as e:
            messagebox.showerror("Report Generation Error", f"An error occurred while generating Pending Instalments Report: {e}")
            report_text_widget.delete("1.0", tk.END)
            report_text_widget.insert("1.0", f"Error: {e}")


