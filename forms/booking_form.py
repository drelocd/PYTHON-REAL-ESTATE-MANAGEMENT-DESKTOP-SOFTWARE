import tkinter as tk
from tkinter import ttk, messagebox
import os
from forms.property_forms import CashPaymentWindow, InstallmentPaymentWindow
try:
    from ctypes import windll, byref, sizeof, c_int
    has_ctypes = True
except ImportError:
    has_ctypes = False

from datetime import datetime
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from tkinter import filedialog
from PIL import Image, ImageTk

# Assuming a DATA_DIR exists
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Assuming a DBManager class exists somewhere in the project, e.g., db_manager.py
# from your_project.db_manager import DBManager

class FormBase(tk.Toplevel):
    """
    Base class for all forms to handle common functionalities like
    window centering, title bar customization, and icon loading.
    """
    def __init__(self, master, width=700, height=500, title="Form", icon_name=None, parent_icon_loader=None):
        super().__init__(master.winfo_toplevel())
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None
        self._set_window_properties(width, height, icon_name, parent_icon_loader)
        self._customize_title_bar()

    def _set_window_properties(self, width, height, icon_name, parent_icon_loader):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"+{x}+{y}")
        if parent_icon_loader and icon_name:
            try:
                icon_image = parent_icon_loader(icon_name, size=(32, 32))
                if icon_image:
                    self.iconphoto(False, icon_image)
                    self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        try:
            if os.name == 'nt':  # Windows-specific title bar customization
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00804000)  # Dark blue
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
            else:
                self._create_custom_title_bar()
        except Exception:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(
            title_bar, text=self.title(),
            bg='#004080', fg='white',
            font=('Helvetica', 10, 'bold')
        )
        title_label.pack(side=tk.LEFT, padx=10)
        close_button = tk.Button(
            title_bar, text='×', bg='#004080', fg='white',
            bd=0, activebackground='red',
            command=self.destroy,
            font=('Helvetica', 12, 'bold')
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        title_bar.bind('<Button-1>', self._save_drag_start_pos)
        title_bar.bind('<B1-Motion>', self._move_window)
        title_label.bind('<Button-1>', self._save_drag_start_pos)
        title_label.bind('<B1-Motion>', self._move_window)

    def _save_drag_start_pos(self, event):
        self._start_x, self._start_y = event.x, event.y

    def _move_window(self, event):
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

class BookingManagementApp(FormBase):
    def __init__(self, master, db_manager, user_id, on_close_callback, parent_icon_loader=None, window_icon_name="book_land.png"):
        super().__init__(master, width=1000, height=600, title="Booking Management", icon_name=window_icon_name, parent_icon_loader=parent_icon_loader)
        self.db_manager = db_manager
        self.user_id = user_id
        self.on_close_callback = on_close_callback
        self.master_icon_loader_ref = parent_icon_loader

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Corrected instantiation of bookLandForm, removing the extra argument
        self.book_land_frame = bookLandForm(self.notebook, self.db_manager, self.user_id, self.master_icon_loader_ref)
        self.view_booked_lands_frame = ViewBookedLandsFrame(self.notebook, self.db_manager, self.master_icon_loader_ref)

        self.notebook.add(self.book_land_frame, text="Book Land")
        self.notebook.add(self.view_booked_lands_frame, text="View Booked Lands")
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
        # Link the refresh callback from the booking form to the view booked lands frame
        self.book_land_frame.set_refresh_callback(self.view_booked_lands_frame._populate_booked_lands_treeview)
        
        # Initial population of the view booked lands tab
        self.view_booked_lands_frame._populate_booked_lands_treeview()

    def _on_tab_change(self, event):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        if current_tab == "View Booked Lands":
            self.view_booked_lands_frame._populate_booked_lands_treeview()
            
    def _on_closing(self):
        self.grab_release()
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()

class bookLandForm(ttk.Frame):
    def __init__(self, master, db_manager, user_id, parent_icon_loader=None):
        super().__init__(master, padding="10")
        self.db_manager = db_manager
        self.user_id = user_id
        self.refresh_callback = None
        self.selected_property = None
        self.title_deed_images = []
        self._window_icon_ref = None
        self.master_icon_loader_ref = parent_icon_loader
        self.available_properties_data = []

        self.daily_clients_list = []
        self.daily_clients_map = {}
        self.selected_client_data = None
        
        self.style = ttk.Style()
        self.style.configure('Green.TButton', background='green', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Green.TButton', background=[('active', 'darkgreen')], foreground=[('disabled', 'gray')])
        self.style.configure('Yellow.TButton', background='gold', foreground='black', font=('Arial', 10, 'bold'))
        self.style.map('Yellow.TButton', background=[('active', 'goldenrod')], foreground=[('disabled', 'gray')])
        self.style.configure('Red.TButton', background='red', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Red.TButton', background=[('active', 'darkred')])
        
        self.style.configure('TEntry', bordercolor='lightgrey', relief='solid', borderwidth=1)
        self.style.map('TEntry', bordercolor=[('focus', '#0099C2')])

        self._create_widgets(parent_icon_loader)
        self._populate_property_list()
        self._load_daily_clients()
        
    def set_refresh_callback(self, callback):
        self.refresh_callback = callback
    
    def _create_widgets(self, parent_icon_loader):
        main_frame = self
        
        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Information", padding="5")
        buyer_info_frame.pack(fill="x", pady=5)
        buyer_info_frame.columnconfigure(1, weight=1)

        ttk.Label(buyer_info_frame, text="Buyer Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.buyer_name_var = tk.StringVar()
        self.combo_buyer_name = ttk.Combobox(
            buyer_info_frame, 
            textvariable=self.buyer_name_var, 
            state='normal',
        )
        self.combo_buyer_name.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.combo_buyer_name.configure(takefocus=False)
        self.combo_buyer_name.bind('<KeyRelease>', self._update_client_list)
        self.combo_buyer_name.bind("<<ComboboxSelected>>", self._on_buyer_select)

        ttk.Label(buyer_info_frame, text="Telephone Number:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.buyer_contact_var = tk.StringVar()
        self.entry_buyer_contact = ttk.Entry(buyer_info_frame, textvariable=self.buyer_contact_var, state='readonly')
        self.entry_buyer_contact.grid(row=1, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(buyer_info_frame, text="Buyer Email:").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.buyer_email_var = tk.StringVar()
        self.entry_buyer_email = ttk.Entry(buyer_info_frame, textvariable=self.buyer_email_var, state='readonly')
        self.entry_buyer_email.grid(row=2, column=1, sticky="ew", pady=2, padx=5)

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

        payment_options_frame = ttk.LabelFrame(main_frame, text="Payment Options", padding="5")
        payment_options_frame.pack(fill="x", pady=5)

        self.btn_installments = ttk.Button(payment_options_frame, text="Book Now", command=self._open_installment_booking_window, style='Yellow.TButton')
        self.btn_installments.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)
        
    def _load_daily_clients(self):
        """Fetches daily land sales clients and populates the combobox."""
        try:
            clients = self.db_manager.get_all_daily_clients_lands()
            self.daily_clients_list = [client['name'] for client in clients]
            self.daily_clients_map = {client['name']: client for client in clients}
            self.combo_buyer_name['values'] = self.daily_clients_list
        except Exception as e:
            messagebox.showerror("Client Data Error", f"Failed to load daily clients: {e}", parent=self)
            
    def _on_buyer_select(self, event):
        current_selection = self.property_listbox.curselection()
        selected_name = self.combo_buyer_name.get()
        client_data = self.daily_clients_map.get(selected_name)
        if client_data:
            self.buyer_contact_var.set(client_data.get('telephone_number', ''))
            self.buyer_email_var.set(client_data.get('email', ''))
            self.selected_client_data = client_data
        else:
            self.buyer_contact_var.set('')
            self.buyer_email_var.set('')
            self.selected_client_data = None

        if not self.property_listbox.curselection() and current_selection:
            self.property_listbox.selection_set(current_selection[0])
            if current_selection[0] < len(self.available_properties_data):
                self.selected_property = self.available_properties_data[current_selection[0]]

    def _update_client_list(self, event=None):
        """
        Updates the Combobox dropdown based on the user's input.
        """
        current_text = self.buyer_name_var.get()
        if current_text == '':
            self.combo_buyer_name['values'] = self.daily_clients_list
        else:
            filtered_clients = [
                client for client in self.daily_clients_list
                if current_text.lower() in client.lower()
            ]
            self.combo_buyer_name['values'] = filtered_clients

    def _validate_buyer_info(self):
        buyer_name = self.combo_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()

        if not buyer_name or not buyer_contact:
            messagebox.showwarning("Buyer Information Required", "Please select a buyer from the list and ensure their contact information is correct.", parent=self)
            return False

        if buyer_name not in self.daily_clients_map:
            messagebox.showerror("Invalid Buyer", "The entered buyer is not a valid daily client. Please select a client from the dropdown list.", parent=self)
            return False
        
        client_data = self.daily_clients_map.get(buyer_name)
        if client_data and client_data.get('telephone_number') != buyer_contact:
            messagebox.showerror("Invalid Contact", "The contact number does not match the selected client. Please use the correct number.", parent=self)
            return False

        return True

    def _open_installment_booking_window(self):
        if not self.selected_property:
            messagebox.showwarning("No Property Selected", "Please select a property first.", parent=self)
            return

        if not self._validate_buyer_info():
            return
            
        brought_by = self.selected_client_data.get('brought_by', 'N/A')
        visit_id = self.selected_client_data.get('visit_id')
        
        buyer_name = self.combo_buyer_name.get().strip()
        buyer_contact = self.entry_buyer_contact.get().strip()
        
        # We need the top-level window to pass to InstallmentPaymentWindow
        top_level_master = self.winfo_toplevel()

        InstallmentPaymentWindow(top_level_master, self.db_manager, self.user_id, self.selected_property, buyer_name, buyer_contact, brought_by, "installment", self.refresh_callback, self.master_icon_loader_ref, visit_id=visit_id)

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
        self.buyer_name_var.set('')
        self.buyer_contact_var.set('')
        self.buyer_email_var.set('')
        self.selected_client_data = None
        self.property_listbox.selection_clear(0, tk.END)
        self.selected_property = None

    def _populate_property_list(self, search_query="", min_size=None, max_size=None):
        self.property_listbox.delete(0, tk.END)
        self.available_properties_data = self.db_manager.get_all_properties(status='Available')
        if not self.available_properties_data:
            self.property_listbox.insert(tk.END, "NO AVAILABLE PROPERTIES FOUND.")
            return
        filtered_properties = []
        for prop in self.available_properties_data:
            title_deed = prop.get('title_deed_number', '')
            location = prop.get('location', '')
            size = prop.get('size', 0.0)
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
            formatted_entry = f"Property: {prop.get('property_id')} - {prop.get('location', '').upper()} ({prop.get('size', 0.0):.2f} ACRES) - KES {prop.get('price', 0.0):,.2f}"
            self.property_listbox.insert(tk.END, formatted_entry)
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
                    messagebox.showwarning("Input Error", "Minimum size cannot be negative.", parent=self)
                    self.entry_min_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Min Size. Please enter a number.", parent=self)
                self.entry_min_size.delete(0, tk.END)
                return
        if max_size_str:
            try:
                max_size = float(max_size_str)
                if max_size < 0:
                    messagebox.showwarning("Input Error", "Maximum size cannot be negative.", parent=self)
                    self.entry_max_size.delete(0, tk.END)
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid value for Max Size. Please enter a number.", parent=self)
                self.entry_max_size.delete(0, tk.END)
                return
        if min_size is not None and max_size is not None and min_size > max_size:
            messagebox.showwarning("Input Error", "Minimum size cannot be greater than maximum size.", parent=self)
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
            self.current_title_image_label.image = photo
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
            messagebox.showinfo("No Images", "No title deed images available for this property.", parent=self)
            return
        gallery = tk.Toplevel(self)
        gallery.title("Title Deed Image Gallery")
        gallery.transient(self)
        gallery.grab_set()
        
        gallery.gallery_image_paths = self._get_full_title_deed_paths()
        gallery.current_gallery_index = 0
        gallery.image_container_frame = ttk.Frame(gallery, relief="solid", borderwidth=1)
        gallery.image_container_frame.pack(fill="both", expand=True)
        gallery.gallery_image_label = ttk.Label(gallery.image_container_frame)
        gallery.gallery_image_label.pack(fill="both", expand=True)
        prev_arrow = ttk.Label(gallery.image_container_frame, text='◀', font=('Arial', 24, 'bold'), foreground='black', cursor='hand2')
        prev_arrow.place(relx=0, rely=0.5, anchor='w', relwidth=0.15, relheight=1)
        prev_arrow.bind("<Button-1>", lambda e: self._show_previous_image_in_gallery(gallery))
        prev_arrow.config(wraplength=1)
        next_arrow = ttk.Label(gallery.image_container_frame, text='▶', font=('Arial', 24, 'bold'), foreground='black', cursor='hand2')
        next_arrow.place(relx=1, rely=0.5, anchor='e', relwidth=0.15, relheight=1)
        next_arrow.bind("<Button-1>", lambda e: self._show_next_image_in_gallery(gallery))
        next_arrow.config(wraplength=1)
        self._update_gallery_image(gallery)

    def _show_previous_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index - 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _show_next_image_in_gallery(self, gallery_window):
        if gallery_window.gallery_image_paths:
            gallery_window.current_gallery_index = (gallery_window.current_gallery_index + 1) % len(gallery_window.gallery_image_paths)
            self._update_gallery_image(gallery_window)

    def _update_gallery_image(self, gallery_window):
        if gallery_window.gallery_image_paths:
            try:
                img_path = gallery_window.gallery_image_paths[gallery_window.current_gallery_index]
                img = Image.open(img_path)
                gallery_window.image_container_frame.update_idletasks()
                container_width = gallery_window.image_container_frame.winfo_width()
                container_height = gallery_window.image_container_frame.winfo_height()
                if container_width <= 1: 
                    container_width = gallery_window.winfo_width() - 2
                    if container_width < 100: container_width = 100
                if container_height <= 1: 
                    container_height = gallery_window.winfo_height() - 2
                    if container_height < 100: container_height = 100
                original_width, original_height = img.size
                ratio = min(container_width / original_width, container_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                if new_width == 0: new_width = 1
                if new_height == 0: new_height = 1
                img = img.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                gallery_window.gallery_image_label.config(image=photo)
                gallery_window.gallery_image_label.image = photo
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not load image: {e}", parent=self)
                gallery_window.gallery_image_label.config(image='', text="Error loading image.")
                gallery_window.gallery_image_label.image = None
        else:
            gallery_window.gallery_image_label.config(image='', text="No image to display.")
            gallery_window.gallery_image_label.image = None
            
class ViewBookedLandsFrame(ttk.Frame):
    def __init__(self, master, db_manager, parent_icon_loader=None):
        super().__init__(master, padding="10")
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader
        self.booked_lands_data = [] # Store raw data for filtering

        self._create_widgets()
        self._populate_booked_lands_treeview() # Initial population
        
    def _create_widgets(self):
        main_frame = self

        # Search Frame
        search_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 5))
        search_frame.pack(fill=tk.X)
        
        self.search_var = tk.StringVar()
        # Note: self._filter_booked_lands now filters based on self.booked_lands_data
        self.search_var.trace_add("write", self._filter_booked_lands)

        ttk.Label(search_frame, text="Search Booked Lands:").pack(side=tk.LEFT, padx=(0, 5))
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var)
        self.entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Treeview
        self.tree = ttk.Treeview(main_frame, columns=("client_name", "title_deed", "location", "price", "status", "payment_mode"), show="headings")
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("client_name", text="Client Name", anchor=tk.W)
        self.tree.heading("title_deed", text="Title Deed", anchor=tk.W)
        self.tree.heading("location", text="Location", anchor=tk.W)
        self.tree.heading("price", text="Price", anchor=tk.E)
        self.tree.heading("status", text="Status", anchor=tk.W)
        self.tree.heading("payment_mode", text="Payment Mode", anchor=tk.W)

        self.tree.column("client_name", width=150, minwidth=100)
        self.tree.column("title_deed", width=100, minwidth=80)
        self.tree.column("location", width=150, minwidth=100)
        self.tree.column("price", width=100, minwidth=80, anchor=tk.E)
        self.tree.column("status", width=80, minwidth=60)
        self.tree.column("payment_mode", width=100, minwidth=80)

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bindings
        self.tree.bind("<Double-1>", self._on_double_click)
        # NEW: Bind selection event to toggle button state
        self.tree.bind("<<TreeviewSelect>>", self._toggle_refund_button) 
        
        # Button Frame (NEW)
        button_frame = ttk.Frame(main_frame, padding=(0, 5, 0, 0))
        button_frame.pack(fill=tk.X)
        
        # Refund Button (NEW)
        self.btn_refund = ttk.Button(
            button_frame, 
            text="Refund & Mark Available", 
            command=self._process_refund,
            state=tk.DISABLED # Start disabled
        )
        self.btn_refund.pack(side=tk.RIGHT, padx=5) # Added padx for spacing

    def _on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # We need the title deed from the treeview item to fetch full details
            item = self.tree.item(item_id, 'values')
            # Title deed is at index 1 in the values tuple
            title_deed = item[1] 
            
            # Assuming you have a method in your DBManager to get full transaction details
            booked_property = self.db_manager.get_booked_property_details(title_deed)
            
            if booked_property:
                # Use a cleaner way to format the currency
                def format_currency(value):
                    return f"KES {value:,.2f}" if isinstance(value, (int, float)) else str(value)

                messagebox.showinfo(
                    "Booked Property Details", 
                    f"Title Deed: {booked_property['title_deed_number']}\n"
                    f"Location: {booked_property['location']}\n"
                    f"Price: {format_currency(booked_property['price'])}\n"
                    f"Status: {booked_property['status']}\n"
                    f"Client Name: {booked_property['name']}\n"
                    f"Client Contact: {booked_property['client_contact']}\n"
                    f"Payment Mode: {booked_property['payment_mode']}\n"
                    f"Initial Payment: {format_currency(booked_property['initial_payment'])}\n"
                    f"Balance: {format_currency(booked_property['balance'])}", 
                    parent=self
                )
            else:
                messagebox.showerror("Error", "Could not retrieve property details.", parent=self)

    def _toggle_refund_button(self, event=None):
        """Enables/disables the Refund button based on Treeview selection."""
        selected_items = self.tree.selection()
        if selected_items:
            self.btn_refund.config(state=tk.NORMAL)
        else:
            self.btn_refund.config(state=tk.DISABLED)

    def _process_refund(self):
        """Processes the refund, updates DB status, and clears client info."""
        selected_items = self.tree.selection()
        if not selected_items:
            # This should technically not happen if the button is disabled correctly
            messagebox.showwarning("Selection Required", "Please select a booked property to process a refund.", parent=self)
            return

        # Get the values of the first selected item
        selected_item = selected_items[0]
        item_values = self.tree.item(selected_item, 'values')
        
        # Title deed is at index 1, Client Name is at index 0
        title_deed = item_values[1]
        client_name = item_values[0]

        confirm = messagebox.askyesno(
            "Confirm Refund",
            f"Are you sure you want to process a refund for property with Title Deed: {title_deed} (Client: {client_name})?\n\n"
            "This action will clear all client/payment details and set the property status back to 'available'.",
            parent=self
        )

        if confirm:
            try:
                # Call the DB manager method to handle the reset logic
                success = self.db_manager.process_refund_and_reset(title_deed)
                
                if success:
                    messagebox.showinfo("Success", f"Refund processed successfully. Property {title_deed} is now marked as 'available'.", parent=self)
                    # Clear selection and refresh treeview
                    self.tree.selection_remove(selected_items)
                    self._populate_booked_lands_treeview()
                    self._toggle_refund_button() # Ensure button is disabled
                else:
                    messagebox.showerror("Error", f"Failed to find or update property {title_deed}.", parent=self)
            except Exception as e:
                # Catch actual database exceptions if the MockDBManager were replaced
                messagebox.showerror("Database Error", f"An error occurred during refund processing: {e}", parent=self)

    def _populate_booked_lands_treeview(self, *args):
        # Clear existing treeview items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Fetch the current list of booked lands ('unvailable' status)
        self.booked_lands_data = self.db_manager.get_all_booked_properties(status='unvailable')
        
        # Insert data into the treeview
        for land in self.booked_lands_data:
            # Prepare formatted price string
            price_str = f"KES {land.get('price', 0):,.2f}"
            
            self.tree.insert("", tk.END, values=(
                land.get('name', 'N/A'),
                land.get('title_deed_number', 'N/A'),
                land.get('location', 'N/A'),
                price_str, # Use formatted price string
                land.get('status', 'N/A'),
                land.get('payment_mode', 'N/A')
            ))
            
        # Ensure the refund button state is correct after populating
        self._toggle_refund_button()
            
    def _filter_booked_lands(self, *args):
        search_query = self.search_var.get().strip().lower()
        
        # Optimization: Detach and reattach based on the full data list (self.booked_lands_data)
        # However, for simplicity and working with the current Treeview item values:
        
        for item in self.tree.get_children():
            # Get the current displayed values for filtering
            values = [str(v).lower() for v in self.tree.item(item, 'values')]
            
            if not search_query or any(search_query in v for v in values):
                # Reattach if it matches or if search is empty
                self.tree.reattach(item, '', 'end')
            else:
                # Detach if it doesn't match
                self.tree.detach(item)
                

class InstallmentPaymentWindow(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, selected_property, buyer_name, buyer_contact, brought_by, payment_mode, refresh_callback, icon_loader, visit_id=None):
        super().__init__(master)
        self.db_manager = db_manager
        self.user_id = user_id
        self.visit_id = visit_id
        self.selected_property = selected_property
        self.buyer_name = buyer_name
        self.buyer_contact = buyer_contact
        self.brought_by = brought_by
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
        if has_ctypes and os.name == 'nt':
            try:
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color))
                text_color = c_int(0x00FFFFFF)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
            except Exception as e:
                print(f"Could not customize title bar: {e}")
                self._create_custom_title_bar()
        else:
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
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
        self._start_x = event.x
        self._start_y = event.y

    def _move_window(self, event):
        x = self.winfo_pointerx() - self._start_x
        y = self.winfo_pointery() - self._start_y
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        # Buyer Information
        buyer_info_frame = ttk.LabelFrame(main_frame, text="Buyer Details", padding=5)
        buyer_info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(buyer_info_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_name, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text="Contact:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.buyer_contact, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=2, padx=5)
        # Add the 'Referred By' label and data
        ttk.Label(buyer_info_frame, text="Referred By:").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(buyer_info_frame, text=self.brought_by if self.brought_by else "N/A", font=("Arial", 10, "bold")).grid(row=2, column=1, sticky="w", pady=2, padx=5)
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
        total_payable = float(self._total_amount_paid_var.get().strip().replace(',', ''))
        balance = total_payable - amount_paid
        # 7. Record the sale in the database
        transaction_id = self.db_manager.add_transaction(
            self.selected_property['property_id'],
            client_id,
            payment_mode,
            amount_paid,
            self.brought_by,
            0.0,
            balance
        )
        if transaction_id:
            # Add a new payment history record for the initial transaction
            payment_reason = "Initial Property Purchase Payment"
            self.db_manager.add_transaction_history(
                transaction_id,
                installment_id=None,
                payment_amount=amount_paid,
                payment_mode=payment_mode,
                payment_reason=payment_reason,
                payment_date=datetime.now()
            )
            # Retrieve the selected payment plan details
            selected_plan_str = self.payment_plan_combobox.get()
            plan_name = selected_plan_str.split(' (')[0]
            selected_plan = self._all_payment_plans.get(plan_name)
            # 8. Calculate and record the installment plan details
            total_balance = total_payable - amount_paid
            duration_months = selected_plan.get('duration_months', 0)
            if duration_months > 0:
                monthly_installment_amount = total_balance / duration_months
            else:
                monthly_installment_amount = 0.0
            # Add the installment plan instance to the database
            plan_instance_id = self.db_manager.add_installment_plan(
                transaction_id,
                selected_plan['plan_id'],
                total_balance,
                monthly_installment_amount,
                datetime.now().date()
            )
            if plan_instance_id:
                # 9. Schedule the future monthly payments
                current_date = datetime.now().date()
                for i in range(duration_months):
                    due_date = current_date + relativedelta(months=i + 1)
                    self.db_manager.schedule_installment_payment(
                        plan_instance_id,
                        due_date,
                        monthly_installment_amount
                    )

        if transaction_id:
            # 8. Update property status
            self.db_manager.update_property(self.selected_property['property_id'], status='unvailable')
            if self.visit_id:
                self.db_manager.delete_daily_client(self.visit_id)
            # 9. Ask user if they want to generate a receipt and call the receipt function
            if messagebox.askyesno("Generate Receipt?", "Installment plan recorded. Do you want to generate a receipt for the initial payment?"):
                self._save_receipt(
                    transaction_id=transaction_id,
                    transaction_date=datetime.now().strftime("%Y-%m-%d"),
                    prop_title_deed=self.selected_property.get('title_deed_number', 'N/A'),
                    prop_location=self.selected_property.get('location', 'N/A'),
                    prop_size=self.selected_property.get('size', 'N/A'),
                    prop_price=self.selected_property.get('price', 0.0),
                    buyer_name=buyer_name,
                    buyer_contact=buyer_contact,
                    payment_mode=payment_mode,
                    amount_paid=amount_paid,
                    discount=0.0,
                    balance=balance,
                    brought_by=self.brought_by
                )

            messagebox.showinfo("Success", "Installment sale recorded successfully!", parent=self)
            self.refresh_callback()
            self.master.book_land_frame._clear_property_details_ui()
            self.master.book_land_frame._load_daily_clients()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to record installment transaction.", parent=self)

    def _save_receipt(self, **kwargs):
        """
        Generates a PDF receipt and prompts the user to save it using a file dialog.
        """
        receipt_data = {
            'transaction_id': kwargs.get('transaction_id', 'N/A'),
            'transaction_date': kwargs.get('transaction_date', datetime.now().strftime("%Y-%m-%d")),
            'prop_title_deed': kwargs.get('prop_title_deed', 'N/A'),
            'prop_location': kwargs.get('prop_location', 'N/A'),
            'prop_size': kwargs.get('prop_size', 'N/A'),
            'prop_price': kwargs.get('prop_price', 0.0),
            'buyer_name': kwargs.get('buyer_name', 'N/A'),
            'buyer_contact': kwargs.get('buyer_contact', 'N/A'),
            'brought_by': kwargs.get('brought_by', 'N/A'),
            'payment_mode': kwargs.get('payment_mode', 'N/A'),
            'amount_paid': kwargs.get('amount_paid', 0.0),
            'discount': kwargs.get('discount', 0.0),
            'balance': kwargs.get('balance', 0.0)
        }
        receipt_data['net_price'] = receipt_data['prop_price'] - receipt_data['discount']
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_prop_title_deed = "".join(c for c in receipt_data['prop_title_deed'] if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        default_filename = f"receipt_{timestamp}_{safe_prop_title_deed}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_filename,
            title="Save Receipt As"
        )
        if not filepath:
            messagebox.showinfo("Receipt Not Saved", "Receipt generation was cancelled.")
            return
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                    leftMargin=50, rightMargin=50,
                                    topMargin=50, bottomMargin=40)
            story = []
            styles = getSampleStyleSheet()
            normal = styles['Normal']
            normal.fontSize = 10
            normal.leading = 14
            header_style = ParagraphStyle("Header",
                                          parent=styles['Heading1'],
                                          alignment=TA_CENTER,
                                          fontSize=14,
                                          spaceAfter=6
                                          )
            section_header = ParagraphStyle("SectionHeader",
                                            parent=styles['Heading2'],
                                            fontSize=11,
                                            textColor=colors.darkblue,
                                            spaceAfter=6,
                                            spaceBefore=12
                                            )
            # --- Logo + Company Name ---
            ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icons')
            logo_path = os.path.join(ICONS_DIR, "NEWCITY.png")
            if os.path.exists(logo_path):
                logo = RLImage(logo_path, width=1.0 * inch, height=1.0 * inch)
            else:
                logo = Paragraph("", normal)
            header_table = Table([
                ["", [logo, Paragraph("<b>NEWCITY REAL ESTATE</b>", header_style)], ""]
            ], colWidths=[2 * inch, 3 * inch, 2 * inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (1, 0), (1, 0), 'MIDDLE')
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2 * inch))
            # --- Receipt Title ---
            story.append(Paragraph("<b>PROPERTY SALE RECEIPT</b>", header_style))
            story.append(Spacer(1, 0.2 * inch))
            # --- Transaction Info ---
            tx_table = Table([[
                "Date:", receipt_data['transaction_date'],
                "Transaction ID:", receipt_data['transaction_id']
            ]], colWidths=[1 * inch, 2 * inch, 1.2 * inch, 2 * inch])
            tx_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(tx_table)
            # --- Buyer Details ---
            story.append(Paragraph("BUYER DETAILS", section_header))
            buyer_table = Table([
                ["Name:", receipt_data['buyer_name']],
                ["Contact:", receipt_data['buyer_contact']],
                ["Referred By:", receipt_data['brought_by']]
            ], colWidths=[1.2 * inch, 4 * inch])
            buyer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(buyer_table)
            # --- Property Details ---
            story.append(Paragraph("PROPERTY DETAILS", section_header))
            prop_table = Table([
                ["Title Deed:", receipt_data['prop_title_deed']],
                ["Location:", receipt_data['prop_location']],
                ["Size:", f"{receipt_data['prop_size']} Acres"]
            ], colWidths=[1.2 * inch, 4 * inch])
            prop_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(prop_table)
            # --- Financial Summary ---
            story.append(Paragraph("FINANCIAL SUMMARY", section_header))
            finance_table = Table([
                ["Original Price:", f"KES {receipt_data['prop_price']:,.2f}"],
                ["Discount:", f"KES {receipt_data['discount']:,.2f}"],
                ["Net Price:", f"KES {receipt_data['net_price']:,.2f}"],
                ["Amount Paid:", f"KES {receipt_data['amount_paid']:,.2f}"],
                ["Balance Due:", f"KES {receipt_data['balance']:,.2f}"],
                ["Payment Mode:", receipt_data['payment_mode']]
            ], colWidths=[1.5 * inch, 3.7 * inch])
            finance_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 2), (-1, 2), colors.whitesmoke),
                ('BACKGROUND', (0, 4), (-1, 4), colors.lightgrey),
                ('FONTNAME', (0, 2), (-1, 4), 'Helvetica-Bold'),
            ]))
            story.append(finance_table)
            # --- Footer ---
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("<b><i>Thank you for your business!</i></b>", normal))
            story.append(Paragraph(
                f"<font size='8' color='#888888'>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</font>",
                normal
            ))
            doc.build(story)
            messagebox.showinfo("Receipt Generated", f"Receipt saved successfully to:\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("PDF Generation Error", f"An error occurred while generating or saving the receipt PDF: {e}", parent=self)

    def cancel(self):
        self.destroy()