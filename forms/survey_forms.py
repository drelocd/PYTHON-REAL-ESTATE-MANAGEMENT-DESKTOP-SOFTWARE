import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import os
from PIL import Image, ImageTk

# Define paths relative to the project root for icon loading
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons') # Assuming icons are here

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