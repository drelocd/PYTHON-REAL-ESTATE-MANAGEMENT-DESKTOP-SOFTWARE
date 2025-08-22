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



class subdividelandForm(tk.Toplevel):
    def __init__(self, master, db_manager, user_id, refresh_callback, parent_icon_loader=None, window_icon_name="subdivide.png"):
        """
        Initializes the subdivideLandForm window for managing land subdivision.
        
        Args:
            master (tk.Tk): The parent window.
            db_manager: An instance of the database manager.
            user_id (str): The ID of the current user.
            refresh_callback (callable): A function to call to refresh the main view.
            parent_icon_loader (object, optional): An icon loader from the parent window. Defaults to None.
            window_icon_name (str, optional): The filename for the window icon. Defaults to "subdivide.png".
        """
        super().__init__(master)
        self.title("Subdivide Land and Manage Records")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.db_manager = db_manager
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        
        # UI state variables
        self.selected_block = None
        self.selected_lot_id = None
        self.all_blocks = []
        self.all_proposed_lots = []

        # Assuming you have these widgets in your UI
        self.lot_size_entry = tk.Entry(self)
        self.surveyor_name_entry = tk.Entry(self)

        # Treeviews
        self.blocks_tree = ttk.Treeview(self)
        self.update_lots_tree = None

        # Confirmation and rejection buttons
        self.confirm_lot_btn = None
        self.reject_lot_btn = None
        self._confirm_icon = None
        self._reject_icon = None
        
        # Other widgets
        self.update_form_frame = None
        self.search_entry = None
        self.notebook = ttk.Notebook(self)
        self.proposed_lots_frame = ttk.Frame(self.notebook)

        self.bold_font = tkfont.Font(family="Helvetica", size=10, weight="bold")

        self.style = ttk.Style()
        self.style.configure('Green.TButton', background='green', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Green.TButton', background=[('active', 'darkgreen')], foreground=[('disabled', 'gray')])
        self.style.configure('Yellow.TButton', background='gold', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Yellow.TButton', background=[('active', 'goldenrod')], foreground=[('disabled', 'gray')])
        self.style.configure('Red.TButton', background='red', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('Red.TButton', background=[('active', 'darkred')])
        
        self.master_icon_loader_ref = parent_icon_loader
        self._subdivide_icon = None
        
        self._set_window_properties(1300, 680, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._populate_blocks_tree()
        self._populate_proposed_lots_tree()
        self._populate_update_lots_tree()

    def _customize_title_bar(self):
        """Customizes the title bar appearance."""
        try:
            if os.name == 'nt':
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
            print(f"Could not customize title bar: {e}")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom title bar when native customization isn't available."""
        self.overrideredirect(True)
        title_bar = tk.Frame(self, bg='#003366', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(title_bar, text=self.title(), bg='#003366', fg='white', font=('Helvetica', 10))
        title_label.pack(side=tk.LEFT, padx=10)
        close_button = tk.Button(title_bar, text='×', bg='#003366', fg='white', bd=0, activebackground='red', command=self._on_closing, font=('Helvetica', 12, 'bold'))
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

    def _on_closing(self):
        """Handle window closing, release grab, and call callback."""
        self.grab_release()
        self.destroy()

    def _create_widgets(self, parent_icon_loader):
        """Creates the main widgets using a notebook (tabbed interface)."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create frames for each tab
        self.subdivision_frame = ttk.Frame(self.notebook, padding="10")
        self.proposed_lots_frame = ttk.Frame(self.notebook, padding="10")
        self.update_lots_frame = ttk.Frame(self.notebook, padding="10")

        # Add the frames as tabs to the notebook
        self.notebook.add(self.subdivision_frame, text="Subdivide Block")
        self.notebook.add(self.proposed_lots_frame, text="Proposed Lots")
        self.notebook.add(self.update_lots_frame, text="Update Lots")

        # Call methods to populate each tab's widgets
        self._create_subdivision_widgets(self.subdivision_frame)
        self._create_proposed_lots_widgets(self.proposed_lots_frame)
        self._create_update_lots_widgets(self.update_lots_frame)

    def _create_subdivision_widgets(self, parent_frame):
        """Creates the GUI for subdividing a block."""
        sub_frame = ttk.LabelFrame(parent_frame, text="Subdivide a Block", padding="10")
        sub_frame.pack(fill="both", expand=True)

        search_and_table_frame = ttk.Frame(sub_frame)
        search_and_table_frame.pack(fill="both", expand=True, pady=5)

        search_bar_label = ttk.Label(search_and_table_frame, text="Search for a block:")
        search_bar_label.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_and_table_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_blocks)

        self.blocks_tree = ttk.Treeview(sub_frame, columns=("ID", "Title Deed Number", "Size", "Status", "Location"), show="headings")
        self.blocks_tree.heading("ID", text="ID")
        self.blocks_tree.heading("Title Deed Number", text="Title Deed Number")
        self.blocks_tree.heading("Size", text="Size (Acres)")
        self.blocks_tree.heading("Status", text="Status")
        self.blocks_tree.heading("Location", text="Location")
        self.blocks_tree.pack(fill="both", expand=True, pady=10)
        self.blocks_tree.bind("<<TreeviewSelect>>", self._on_block_select)

        if self.master_icon_loader_ref:
            self._subdivide_icon = self.master_icon_loader_ref("subdivide.png", size=(20, 20))
        
        self.subdivide_btn = ttk.Button(
            sub_frame,
            text="Subdivide",
            image=self._subdivide_icon,
            compound=tk.LEFT,
            command=self._show_new_lot_form,
            state=tk.DISABLED
        )
        self.subdivide_btn.pack(pady=10)

        # Frame for the new lot form (initially hidden)
        self.new_lot_frame = ttk.LabelFrame(sub_frame, text="New Lot Details", padding="10")
        
    def _create_proposed_lots_widgets(self, parent_frame):
        """Creates the GUI for managing proposed lots."""
        proposed_frame = ttk.LabelFrame(parent_frame, text="Proposed Lots", padding="10")
        proposed_frame.pack(fill="both", expand=True)
        
        search_and_table_frame = ttk.Frame(proposed_frame)
        search_and_table_frame.pack(fill="x", pady=10)

        search_bar_label = ttk.Label(search_and_table_frame, text="Search Proposed Lots:")
        search_bar_label.pack(side=tk.LEFT, padx=(0, 5))
        self.proposed_search_entry = ttk.Entry(search_and_table_frame)
        self.proposed_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.proposed_search_entry.bind("<KeyRelease>", self._filter_proposed_lots)

        self.proposed_lots_tree = ttk.Treeview(proposed_frame, columns=("Title Deed Number", "Size", "Location", "Surveyor Name", "Created By", "Status"), show="headings")
        self.proposed_lots_tree.heading("Title Deed Number", text="Parent Block Title Deed")
        self.proposed_lots_tree.heading("Size", text="Size (Acres)")
        self.proposed_lots_tree.heading("Location", text="Location")
        self.proposed_lots_tree.heading("Surveyor Name", text="Surveyor Name")
        self.proposed_lots_tree.heading("Created By", text="Created By")
        self.proposed_lots_tree.heading("Status", text="Status")
        self.proposed_lots_tree.pack(fill="both", expand=True, pady=10)
        self.proposed_lots_tree.bind("<<TreeviewSelect>>", self._on_proposed_lot_select)

        
    def _create_update_lots_widgets(self, parent_frame):
        """Creates the GUI for updating existing lots."""
        update_frame = ttk.LabelFrame(parent_frame, text="Update Lot Details", padding="10")
        update_frame.pack(fill="both", expand=True)

        # Search bar
        search_frame = ttk.Frame(update_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_lots_for_updates)

        self.update_lots_tree = ttk.Treeview(update_frame, columns=("ID", "Title Deed Number", "Size", "Status", "Location"), show="headings")
        self.update_lots_tree.heading("ID", text="ID")
        self.update_lots_tree.heading("Title Deed Number", text="Title Deed Number")
        self.update_lots_tree.heading("Size", text="Size (Acres)")
        self.update_lots_tree.heading("Status", text="Status")
        self.update_lots_tree.heading("Location", text="Location")
        self.update_lots_tree.pack(fill="both", expand=True, pady=10)
        self.update_lots_tree.bind("<<TreeviewSelect>>", self._on_update_lot_select)

        button_frame = ttk.Frame(update_frame)
        button_frame.pack(fill="x", pady=10)

        # Confirm and Reject buttons
        if hasattr(self, 'master_icon_loader_ref'):
            self._confirm_icon = self.master_icon_loader_ref("confirm.png", size=(20, 20))
            self._reject_icon = self.master_icon_loader_ref("reject.png", size=(20, 20))
        
        # Placing Reject button on the left
        self.reject_lot_btn = ttk.Button(
            button_frame,
            text="Reject Lot",
            image=self._reject_icon,
            compound=tk.LEFT,
            command=self._reject_proposed_lot,
            state=tk.DISABLED,
            style='Red.TButton'
        )
        self.reject_lot_btn.pack(side=tk.LEFT, padx=5)

        # Placing Confirm button on the right
        self.confirm_lot_btn = ttk.Button(
            button_frame,
            text="Confirm Lot",
            image=self._confirm_icon,
            compound=tk.LEFT,
            command=self._confirm_proposed_lot,
            state=tk.DISABLED,
            style='Green.TButton'
        )
        self.confirm_lot_btn.pack(side=tk.RIGHT, padx=5)

        # The form for confirming lot details
        self.update_form_frame = ttk.LabelFrame(update_frame, text="Lot Details", padding="10")

    def _populate_blocks_tree(self):
        """Populates the Treeview with available blocks."""
        for item in self.blocks_tree.get_children():
            self.blocks_tree.delete(item)
        
        self.all_blocks = self.db_manager.get_all_properties_blocks(status='Available', property_type='Block')
        
        for block in self.all_blocks:
            self.blocks_tree.insert("", tk.END, iid=block['property_id'], values=(block['property_id'], block['title_deed_number'], block['size'], block['status'], block['location']))

    def _populate_proposed_lots_tree(self):
        """Populates the Treeview with proposed lots."""
        # Placeholder call to get proposed lots with all data fields
        self.all_proposed_lots = self.db_manager.get_proposed_lots_with_details()
        
        for item in self.proposed_lots_tree.get_children():
            self.proposed_lots_tree.delete(item)
        
        for lot in self.all_proposed_lots:
            self.proposed_lots_tree.insert("", tk.END, iid=lot['lot_id'], values=(
                lot['title_deed_number'], 
                lot['size'], 
                lot['location'],
                lot['surveyor_name'],
                lot['created_by'],
                lot['status']
            ))

    def _populate_update_lots_tree(self):
        """Populates the Treeview with lots that can be updated."""
        # This is a placeholder. You would fetch data from your db_manager here.
        self.update_lots = self.db_manager.get_lots_for_update() # Placeholder call
        
        for item in self.update_lots_tree.get_children():
            self.update_lots_tree.delete(item)
        
        for lot in self.update_lots:
            self.update_lots_tree.insert("", tk.END, iid=lot['lot_id'], values=(lot['lot_id'], lot['title_deed'], lot['size'], lot['status'], lot['location']))

    def _filter_blocks(self, event=None):
        """Filters the blocks Treeview based on the search entry."""
        search_term = self.search_entry.get().lower()
        self.blocks_tree.delete(*self.blocks_tree.get_children())
        
        for block in self.all_blocks:
            if search_term in str(block['property_id']).lower() or \
               search_term in str(block['title_deed_number']).lower() or \
               search_term in str(block['size']).lower() or \
               search_term in str(block['location']).lower():
                self.blocks_tree.insert("", tk.END, iid=block['property_id'], values=(block['property_id'], block['title_deed_number'], block['size'], block['status'], block['location']))

    def _filter_proposed_lots(self, event=None):
        """Filters the proposed lots Treeview based on the search entry."""
        search_term = self.proposed_search_entry.get().lower()
        self.proposed_lots_tree.delete(*self.proposed_lots_tree.get_children())

        for lot in self.all_proposed_lots:
            if search_term in str(lot['lot_id']).lower() or \
               search_term in str(lot['location']).lower() or \
               search_term in str(lot['surveyor_name']).lower() or \
               search_term in str(lot['created_by']).lower():
                self.proposed_lots_tree.insert("", tk.END, iid=lot['lot_id'], values=(
                    lot['title_deed_number'],
                    lot['size'],
                    lot['location'],
                    lot['surveyor_name'],
                    lot['created_by'],
                    lot['status']
                ))

    def _on_block_select(self, event=None):
        """Handles a row selection in the blocks table and enables the button."""
        selected_item = self.blocks_tree.focus()
        if selected_item:
            self.selected_block = selected_item
            self.subdivide_btn.config(state=tk.NORMAL)
        else:
            self.selected_block = None
            self.subdivide_btn.config(state=tk.DISABLED)

    def _on_proposed_lot_select(self, event=None):
        """Handles a row selection in the proposed lots table and enables the confirm button."""
        selected_item = self.proposed_lots_tree.focus()
        if selected_item:
            self.selected_proposed_lot = selected_item
            self.confirm_lot_btn.config(state=tk.NORMAL)
        else:
            self.selected_proposed_lot = None
            self.confirm_lot_btn.config(state=tk.DISABLED)
        
    def _filter_lots(self, event=None):
        """Filters the lots in the treeview based on the search entry."""
        query = self.search_entry.get().strip().lower()

        # Clear existing items
        for item in self.update_lots_tree.get_children():
            self.update_lots_tree.delete(item)
        
        # Insert filtered items
        for lot in self.all_proposed_lots:
            lot_values = [str(v).lower() for v in lot.values()]
            if any(query in val for val in lot_values):
                self.update_lots_tree.insert(
                    "",
                    "end",
                    values=(
                        lot['lot_id'],
                        lot['title_deed_number'],
                        lot['size'],
                        lot['status'],
                        lot['location']
                    )
                )
        
    def _filter_lots_for_updates(self, event=None):
        """Filters the lots in the treeview based on the search entry and 'Proposed' status."""
        query = self.search_entry.get().strip().lower()

        # Clear existing items
        for item in self.update_lots_tree.get_children():
            self.update_lots_tree.delete(item)
        
        # Insert filtered items
        for lot in self.update_lots:
            # Check if the lot status is 'Proposed' AND if the query matches any of its values
            if lot['status'].lower() == 'proposed':
                lot_values = [str(v).lower() for v in lot.values()]
                if any(query in val for val in lot_values):
                    self.update_lots_tree.insert(
                        "",
                        "end",
                        values=(
                            lot['lot_id'],
                            lot['title_deed'],
                            lot['size'],
                            lot['status'],
                            lot['location']
                        )
                    )


    def _on_update_lot_select(self, event):
        """Handles the selection of a lot in the update treeview."""
        selected_item = self.update_lots_tree.selection()
        if selected_item:
            self.confirm_lot_btn.config(state=tk.NORMAL)
            self.reject_lot_btn.config(state=tk.NORMAL)
            self.selected_lot_id = self.update_lots_tree.item(selected_item, "values")[0]
            # No need to hide the form frame here since it's now in a separate window
        else:
            self.confirm_lot_btn.config(state=tk.DISABLED)
            self.reject_lot_btn.config(state=tk.DISABLED)
            self.selected_lot_id = None

            
    def _show_new_lot_form(self):
        """Shows the form for entering new lot details."""
        if not self.selected_block:
            messagebox.showerror("Error", "Please select a block to subdivide.")
            return

        self.subdivide_btn.pack_forget()

        self.new_lot_frame.pack(fill="x", pady=10)
        input_and_summary_frame = ttk.Frame(self.new_lot_frame)
        input_and_summary_frame.pack(fill="x", expand=True)

        input_frame = ttk.Frame(input_and_summary_frame)
        input_frame.pack(fill="x", padx=5)

        ttk.Label(input_frame, text="New Lot Size (Acres):").pack(side=tk.LEFT, padx=5, pady=5)
        self.lot_size_entry = ttk.Entry(input_frame)
        self.lot_size_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)

        ttk.Label(input_frame, text="Surveyor Name:").pack(side=tk.LEFT, padx=5, pady=5)
        self.surveyor_name_entry = ttk.Entry(input_frame)
        self.surveyor_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)

        confirm_btn = ttk.Button(
            self.new_lot_frame,
            text="Confirm Subdivision",
            command=self._on_subdivide,
            style='Green.TButton'
        )
        confirm_btn.pack(pady=10)

    def _on_subdivide(self):
        """Handles the subdivision and record update logic."""
        if not self.selected_block:
            messagebox.showerror("Error", "Please select a block to subdivide.")
            return

        new_lot_size_str = self.lot_size_entry.get()
        surveyor_name = self.surveyor_name_entry.get()
        title_deed_number = 'N/A' # The new lot has no title deed yet

        if not new_lot_size_str or not surveyor_name:
            messagebox.showerror("Error", "Please fill in all new lot details.")
            return

        try:
            new_lot_size = float(new_lot_size_str)
            
            # Get data from the selected parent block
            block_data = self.blocks_tree.item(self.selected_block, "values")
            parent_block_id = block_data[0]
            parent_block_size = float(block_data[2])
            parent_location = block_data[4]

            # Validation: The new lot's size cannot exceed the parent block's size
            if new_lot_size > parent_block_size:
                messagebox.showerror("Invalid Size", "New lot size cannot be larger than the parent block's size.")
                return

            # Ask the user to confirm the action
            confirmation = messagebox.askyesno(
                "Confirm Subdivision",
                f"Are you sure you want to subdivide the block and create a new lot of size {new_lot_size}?"
            )
            
            if not confirmation:
                return

            # This is where you would call your db_manager to create the new proposed lot record
            proposed_lot_data = {
                'parent_block_id': parent_block_id,
                'size': new_lot_size,
                'location': parent_location,
                'surveyor_name': surveyor_name,
                'created_by': self.user_id,
                'title_deed_number': title_deed_number, 
                'price': 0, 
                'status': 'Proposed'
            }
            self.db_manager.propose_new_lot(proposed_lot_data)

            # Calculate and update the parent block's remaining size
            remaining_size = parent_block_size - new_lot_size
            self.db_manager.update_block_size(parent_block_id, remaining_size)
            
            # Check if the block is fully subdivided and update its status
            if remaining_size <= 0.001:  # Using a small tolerance for floating-point comparison
                self.db_manager.update_block_status(parent_block_id, 'Unavailable')
                messagebox.showinfo("Block Unavailable", f"The parent block is now fully subdivided and its status has been updated to 'Unavailable'.")
            
            messagebox.showinfo("Success", "Block successfully subdivided and a new proposed lot record created. Please check the 'Proposed Lots' tab to confirm.")
            
            # After successful subdivision, clear the entry fields
            self.lot_size_entry.delete(0, tk.END)
            self.surveyor_name_entry.delete(0, tk.END)

            # Refresh the list and potentially the main view
            self._populate_blocks_tree()
            self._populate_proposed_lots_tree()
            self.refresh_callback()

            # Switch to the 'Proposed Lots' tab and show the new entry
            self.notebook.select(self.proposed_lots_frame)

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the new lot size.")
        except Exception as e:
            messagebox.showerror("An Error Occurred", f"An unexpected error occurred: {e}")


    def _confirm_proposed_lot(self):
        """Opens a new window to enter details for a confirmed lot."""
        if not self.selected_lot_id:
            messagebox.showerror("Error", "Please select a lot to confirm.")
            return

        # Create the new window and pass the necessary info
        ConfirmationForm(self, self.db_manager, self.selected_lot_id, self.user_id, self.refresh_callback, self.master_icon_loader_ref)

    def _reject_proposed_lot(self):
        """Rejects a proposed lot and returns its size to the parent block."""
        if not self.selected_lot_id:
            messagebox.showerror("Error", "Please select a lot to reject.")
            return

        confirmation = messagebox.askyesno(
            "Confirm Rejection",
            "Are you sure you want to reject this lot? This action cannot be undone."
        )

        if confirmation:
            try:
                # Retrieve the lot's size and its parent block's ID before rejection
                lot_data = self.db_manager.get_proposed_lot_details(self.selected_lot_id)
                if lot_data:
                    parent_block_id = lot_data['parent_block_id']
                    rejected_size = lot_data['size']

                    # First, return the size of the rejected lot to the parent block
                    self.db_manager.return_size_to_block(parent_block_id, rejected_size)

                # Then, update the lot's status to 'Rejected'
                self.db_manager.reject_lot(self.selected_lot_id)

                messagebox.showinfo("Success", "Lot has been successfully rejected and the parent block has been updated.")
                self._populate_update_lots_tree()
                self._populate_proposed_lots_tree()
                self.selected_lot_id = None
                self._filter_lots()
                self._populate_blocks_tree() # Refresh the blocks list to show the new size/status
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reject lot: {e}")

    
class ConfirmationForm(tk.Toplevel):
    def __init__(self, master, db_manager, lot_id, user_id, refresh_callback, icon_loader=None):
        """
        Initializes the confirmation form window.
        
        Args:
            master (tk.Toplevel): The parent window.
            db_manager: An instance of the database manager.
            lot_id (int): The ID of the lot to confirm.
            user_id (str): The ID of the current user.
            refresh_callback (callable): A function to refresh the main view.
        """
        super().__init__(master)
        self.master = master
        self.db_manager = db_manager
        self.lot_id = lot_id
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        self.icon_loader = icon_loader

        self.title("Finalize Lot Details")
        self.geometry("400x500") # Set a default size for the window
        self.grab_set()
        self.transient(master)

        self.image_paths = []
        self.title_image_paths = []
        
        self.title_deed_entry = None
        self.description_entry = None
        self.owner_entry = None
        self.contact_entry = None
        self.price_entry = None

        self._create_widgets()

    def _create_widgets(self):
        """Creates the GUI for the confirmation form."""
        form_frame = ttk.LabelFrame(self, text="Lot Details", padding="10")
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Form fields
        ttk.Label(form_frame, text="Issued Title Deed Number:").pack(anchor='w', pady=(5,0))
        self.title_deed_entry = ttk.Entry(form_frame)
        self.title_deed_entry.pack(fill='x', pady=2)
        
        ttk.Label(form_frame, text="Price:").pack(anchor='w', pady=(5,0))
        self.price_entry = ttk.Entry(form_frame)
        self.price_entry.pack(fill='x', pady=2)
        
        ttk.Label(form_frame, text="Owner Name:").pack(anchor='w', pady=(5,0))
        self.owner_entry = ttk.Entry(form_frame)
        self.owner_entry.pack(fill='x', pady=2)
        
        ttk.Label(form_frame, text="Contact Info:").pack(anchor='w', pady=(5,0))
        self.contact_entry = ttk.Entry(form_frame)
        self.contact_entry.pack(fill='x', pady=2)

        ttk.Label(form_frame, text="Description:").pack(anchor='w', pady=(5,0))
        self.description_entry = tk.Text(form_frame, height=4)
        self.description_entry.pack(fill='x', pady=2)
        
        # File selection buttons
        ttk.Button(form_frame, text="Select Image Files", command=self._select_image_files).pack(fill='x', pady=5)
        ttk.Button(form_frame, text="Select Title Deed Files", command=self._select_title_deed_files).pack(fill='x', pady=5)
        
        # Submit button
        submit_btn = ttk.Button(form_frame, text="Finalize Lot", command=self._finalize_confirmation)
        submit_btn.pack(pady=10)

    def _select_image_files(self):
        self.image_paths = filedialog.askopenfilenames(
            title="Select Image Files",
            filetypes=(("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        if self.image_paths:
            messagebox.showinfo("Files Selected", f"{len(self.image_paths)} image file(s) selected.")

    def _select_title_deed_files(self):
        self.title_image_paths = filedialog.askopenfilenames(
            title="Select Title Deed Files",
            filetypes=(("PDF and Image files", "*.pdf *.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        if self.title_image_paths:
            messagebox.showinfo("Files Selected", f"{len(self.title_image_paths)} title deed file(s) selected.")

    def _finalize_confirmation(self):
        """Saves the lot details and moves it from proposed_lots to properties table."""
        if not self.lot_id:
            return

        # Get data from the form
        title_deed = self.title_deed_entry.get().strip()
        description = self.description_entry.get("1.0", tk.END).strip()
        owner = self.owner_entry.get().strip()
        contact = self.contact_entry.get().strip()
        price_str = self.price_entry.get().strip()
        
        if not all([title_deed, owner, contact, price_str]):
            messagebox.showerror("Error", "Please fill in all required fields.")
            return

        try:
            price = float(price_str)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the price.")
            return

        # Get lot size and location from the original proposed lot record
        lot_data = self.db_manager.get_lots_for_update()
        current_lot = next((lot for lot in lot_data if lot['lot_id'] == int(self.lot_id)), None)

        if not current_lot:
            messagebox.showerror("Error", "Could not find lot details.")
            return

        try:
            # 1. Add the new property to the properties table
            self.db_manager.add_property(
                property_type='Lot',
                title_deed_number=title_deed,
                location=current_lot['location'],
                size=current_lot['size'],
                description=description,
                owner=owner,
                contact=contact,
                price=price,
                image_paths=','.join(self.image_paths),
                title_image_paths=','.join(self.title_image_paths),
                added_by_user_id=self.user_id
            )

            # 2. Update the status of the lot in the proposed_lots table
            self.db_manager.finalize_lot(self.lot_id)

            messagebox.showinfo("Success", "Lot has been finalized and added to properties.")
            
            # Refresh UI and clear state
            self.master._populate_proposed_lots_tree()
            self.master._populate_update_lots_tree()
            self.master._on_update_lot_select(None)
            if self.refresh_callback:
                self.refresh_callback()
            self.master._filter_lots() # Re-filter the list after the action
            self.destroy() # Close the confirmation window

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while finalizing the lot: {e}")
