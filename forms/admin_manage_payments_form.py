import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import platform
import string

try:
    from ctypes import windll, byref, sizeof, c_int
    HAS_CTYPES = True
except (ImportError, OSError):
    HAS_CTYPES = False

# --- New Form for Creating a New Payment Plan ---
class CreatePaymentPlanForm(tk.Toplevel):
    """
    A separate modal form for creating a new payment plan.
    """
    def __init__(self, master, db_manager, user_id, refresh_callback, icon_loader):
        """
        Initializes the form to create a new payment plan.

        Args:
            master (tk.Toplevel): The parent window.
            db_manager: An instance of the database manager.
            user_id (str): The ID of the current user.
            refresh_callback (callable): A function in the parent to refresh the treeview.
            icon_loader (callable): A function to load a custom icon.
        """
        super().__init__(master)
        
        self.db_manager = db_manager
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        self.icon_loader = icon_loader

        self.title("Create New Plan")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._set_window_properties(400, 250, "payment.png")
        self._customize_title_bar()
        self._create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_window_properties(self, width, height, icon_name):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 70
        self.geometry(f"+{x}+{y}")
        
        if self.icon_loader and icon_name:
            try:
                icon_image = self.icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Applies a custom color to the title bar on Windows systems."""
        if platform.system() == 'Windows' and HAS_CTYPES:
            try:
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300) # Dark blue in BGR format
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color)
                )
                text_color = c_int(0x00FFFFFF) # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")

    def _create_widgets(self):
        """Creates the GUI for the new plan creation form."""
        form_frame = ttk.Frame(self, padding="15")
        form_frame.pack(expand=True, fill="both")

        ttk.Label(form_frame, text="Plan Name:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.plan_name_entry = ttk.Entry(form_frame, width=30)
        self.plan_name_entry.grid(row=0, column=1, sticky='we', padx=5, pady=5)

        ttk.Label(form_frame, text="Deposit Percentage (%):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.deposit_percentage_entry = ttk.Entry(form_frame, width=10)
        self.deposit_percentage_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(form_frame, text="Duration (months):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.duration_spinbox = ttk.Spinbox(form_frame, from_=1, to=120, width=5)
        self.duration_spinbox.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(form_frame, text="Interest Rate (%):").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.interest_rate_entry = ttk.Entry(form_frame, width=10)
        self.interest_rate_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        # Create a style for the green button
        style = ttk.Style()
        style.configure('TButton', font=('Segoe UI', 10, 'bold')) # Apply to all buttons
        style.configure('Custom.Green.TButton', background='#4CAF50', foreground='white')

        create_btn = ttk.Button(form_frame, text="Create", style='Custom.Green.TButton', command=self._create_plan)
        create_btn.grid(row=4, column=0, columnspan=2, pady=20)

    def _validate_input(self):
        """Validates form input before saving."""
        plan_name = self.plan_name_entry.get().strip()
        deposit_percentage_str = self.deposit_percentage_entry.get().strip()
        duration_str = self.duration_spinbox.get().strip()
        interest_rate_str = self.interest_rate_entry.get().strip()

        if not all([plan_name, deposit_percentage_str, duration_str, interest_rate_str]):
            messagebox.showerror("Input Error", "All fields are required.", parent=self)
            return False, None, None, None, None

        try:
            duration = int(duration_str)
            interest_rate = float(interest_rate_str)
            deposit_percentage = float(deposit_percentage_str)
            if duration <= 0 or interest_rate < 0 or deposit_percentage < 0:
                messagebox.showerror("Input Error", "Duration must be a positive integer and interest rate a non-negative number.", parent=self)
                return False, None, None, None, None
            return True, plan_name, deposit_percentage, duration, interest_rate
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers for duration and interest rate.", parent=self)
            return False, None, None, None, None

    def _create_plan(self):
        """
        Creates a new payment plan and then closes the form, refreshing the parent.
        """
        is_valid, plan_name,deposit_percentage, duration, interest_rate = self._validate_input()
        if not is_valid:
            return

        username = self.db_manager.get_username_by_id(self.user_id)
        if not username:
            messagebox.showerror("Error", "Could not find a username for the current user.", parent=self)
            return

        plan_data_dict = {
            "name": plan_name,
            "deposit_percentage": deposit_percentage,
            "duration_months": duration,
            "interest_rate": interest_rate,
            "created_by": username
        }

        try:
            self.db_manager.create_payment_plan(plan_data_dict)
            messagebox.showinfo("Success", "Payment plan created successfully.", parent=self)
            # Call the refresh function on the parent form
            self.refresh_callback()
            self._on_closing()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}", parent=self)

    def _on_closing(self):
        self.grab_release()
        self.destroy()

# --- Revamped ManagePaymentPlansForm Class ---
class ManagePaymentPlansForm(tk.Toplevel):
    """
    Initializes the form to manage payment plans.

    Args:
        master (tk.Toplevel): The parent window.
        db_manager: An instance of the database manager.
        user_id (str): The ID of the current user.
        parent_icon_loader (callable): A function to load a custom icon.
        window_icon_name (str): The name of the icon file for this window.
    """
    def __init__(self, master, db_manager, user_id, parent_icon_loader=None, window_icon_name="payment.png"):
        super().__init__(master)
        
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.master = master
        self.db_manager = db_manager
        self.user_id = user_id
        self.icon_loader = parent_icon_loader 
        self.selected_plan_id = None
        self._all_plans_data = [] # Cache to hold all plans for searching

        self.title("Manage Payment Plans")
        
        self._set_window_properties(1300, 550, window_icon_name)
        self._customize_title_bar()
        
        self._create_styles()
        self._create_widgets()
        self._populate_plans_treeview()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_styles(self):
        """Creates custom ttk styles for buttons."""
        style = ttk.Style()
        style.configure('Custom.Yellow.TButton', background='#FFC107', foreground='black', font=('Segoe UI', 10, 'bold'))
        style.configure('Custom.Red.TButton', background='#F44336', foreground='black',font=('Segoe UI', 10, 'bold'))
        style.configure('Custom.Green.TButton', background='#4CAF50', foreground='black', font=('Segoe UI', 10, 'bold'))
        # Configure Treeview to remove the white background on selection
        style.map('Treeview', background=[('selected', 'white')])
        style.map('Treeview.Heading', background=[('active', 'darkgrey')])

    def _set_window_properties(self, width, height, icon_name):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 50
        self.geometry(f"+{x}+{y}")
        
        if self.icon_loader and icon_name:
            try:
                icon_image = self.icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Applies a custom color to the title bar on Windows systems."""
        if platform.system() == 'Windows' and HAS_CTYPES:
            try:
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300) # Dark blue in BGR format
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color)
                )
                text_color = c_int(0x00FFFFFF) # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color)
                )
            except Exception as e:
                print(f"Could not customize title bar: {e}")

    def _create_widgets(self):
        """Creates the GUI for the payment plans form with the new layout."""
        # Top frame for search and create button
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill="x")
        
        ttk.Label(top_frame, text="Search Plans:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.search_entry = ttk.Entry(top_frame, width=50)
        self.search_entry.grid(row=0, column=1, sticky='we', padx=5, pady=2)
        self.search_entry.bind("<KeyRelease>", self._filter_treeview)
        
        # Create button on the right
        create_btn = ttk.Button(top_frame, text="Create New Plan", style='Custom.Green.TButton', command=self._open_create_plan_form)
        create_btn.grid(row=0, column=2, sticky='e', padx=5, pady=2)
        top_frame.grid_columnconfigure(1, weight=1) # Makes the entry fill available space

        # Treeview to display existing plans
        tree_frame = ttk.Frame(self, padding="10")
        tree_frame.pack(fill="both", expand=True)
        
        columns = ("plan_id", "name", "deposit_percentage", "duration", "interest_rate", "Created By")
        self.plans_treeview = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings",
            selectmode="browse"
        )
        self.plans_treeview.heading("plan_id", text="ID")
        self.plans_treeview.heading("name", text="Plan Name")
        self.plans_treeview.heading("deposit_percentage", text="Deposit (%)")
        self.plans_treeview.heading("duration", text="Duration")
        self.plans_treeview.heading("interest_rate", text="Interest Rate (%)")
        self.plans_treeview.heading("Created By", text="Created By")
        
        self.plans_treeview.column("plan_id", width=50, anchor=tk.CENTER)
        self.plans_treeview.column("name", width=200)
        self.plans_treeview.column("deposit_percentage", width=100, anchor=tk.CENTER)
        self.plans_treeview.column("duration", width=100, anchor=tk.CENTER)
        self.plans_treeview.column("interest_rate", width=100, anchor=tk.CENTER)
        self.plans_treeview.column("Created By", width=150, anchor=tk.CENTER)
        
        self.plans_treeview.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.plans_treeview.yview)
        scrollbar.pack(side="right", fill="y")
        self.plans_treeview.configure(yscrollcommand=scrollbar.set)
        
        self.plans_treeview.bind("<<TreeviewSelect>>", self._on_treeview_select)

        # Bottom frame for update and delete buttons
        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill="x", side="bottom")

        update_btn = ttk.Button(button_frame, text="Update Selected Plan", style='Custom.Yellow.TButton', command=self._update_plan)
        update_btn.pack(side="left", padx=5, expand=True)
        
        delete_btn = ttk.Button(button_frame, text="Delete Selected Plan", style='Custom.Red.TButton', command=self._delete_plan)
        delete_btn.pack(side="right", padx=5, expand=True)
        
    def _open_create_plan_form(self):
        """Opens the new modal window for creating a plan."""
        # The new form handles its own creation logic and calls back to refresh the parent.
        CreatePaymentPlanForm(
            self,
            self.db_manager,
            self.user_id,
            self._populate_plans_treeview,
            self.icon_loader
        )

    def _on_closing(self):
        self.grab_release()
        self.destroy()

    def _on_treeview_select(self, event):
        """Loads data from the selected row into the entry fields for easy update."""
        selected_item = self.plans_treeview.selection()
        if not selected_item:
            return
        
        item_values = self.plans_treeview.item(selected_item, 'values')
        
        self.selected_plan_id = item_values[0]

        # The input fields have been moved to a separate form, so this is just for demonstration
        # if you were to re-implement them here for a different purpose.
        # For now, we only store the selected plan ID.
        print(f"Selected plan ID: {self.selected_plan_id}")

    def _populate_plans_treeview(self):
        """Fetches all payment plans and populates the treeview."""
        # Clear existing items
        for item in self.plans_treeview.get_children():
            self.plans_treeview.delete(item)
        
        try:
            # Cache the full list of plans for local filtering
            self._all_plans_data = self.db_manager.get_payment_plans()
            for plan in self._all_plans_data:
                self.plans_treeview.insert("", "end", values=(
                    plan['plan_id'],
                    plan['name'],
                    plan['deposit_percentage'],  # Assuming this is now included
                    plan['duration_months'],
                    plan['interest_rate'],
                    plan['created_by']
                ))
            # After populating, run a quick filter to ensure the search bar state is reflected
            self._filter_treeview()
            self.plans_treeview.selection_clear()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load payment plans: {e}")

    def _filter_treeview(self, event=None):
        """
        Filters the Treeview items based on the search entry's content.
        This is a live filter that re-populates the treeview for simplicity.
        """
        search_term = self.search_entry.get().strip().lower()
        
        # Clear existing items
        for item in self.plans_treeview.get_children():
            self.plans_treeview.delete(item)

        # Repopulate with filtered data
        if not search_term:
            filtered_plans = self._all_plans_data
        else:
            filtered_plans = [
                plan for plan in self._all_plans_data
                if any(
                    search_term in str(value).lower()
                    for value in plan.values()
                )
            ]
        
        for plan in filtered_plans:
            self.plans_treeview.insert("", "end", values=(
                plan['plan_id'],
                plan['name'],
                plan['deposit_percentage'],
                plan['duration_months'],
                plan['interest_rate'],
                plan['created_by']
            ))

    def _update_plan(self):
        """
        Opens a new form to update the selected plan. 
        This is a placeholder and would require a new Toplevel form similar to create.
        """
        if not self.selected_plan_id:
            messagebox.showerror("Error", "Please select a plan to update.")
            return
        selected_plan_data = self.db_manager.get_plan_by_id(self.selected_plan_id)
            

        if selected_plan_data:
            PlanUpdateForm(
                self,
                self.db_manager,
                selected_plan_data,
                self._populate_plans_treeview,
                self.icon_loader
            )
        else:
            messagebox.showerror("Error", "Selected plan data not found.")
            

        

    def _delete_plan(self):
        """Deletes the selected payment plan."""
        if not self.selected_plan_id:
            messagebox.showerror("Error", "Please select a plan to delete.")
            return
            
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this payment plan?"):
            try:
                self.db_manager.delete_payment_plan(self.selected_plan_id)
                messagebox.showinfo("Success", "Payment plan deleted successfully.")
                self.selected_plan_id = None
                self._populate_plans_treeview()
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
class PlanUpdateForm(tk.Toplevel):
    """
    A Toplevel form for updating an existing plan based on the
    payment_plans table schema, with custom styling.
    """
    def __init__(self, parent, db_manager, plan_details, on_update_callback, icon_loader):
        """
        Initializes the update form.

        Args:
            parent: The parent Tkinter window.
            db_manager: An instance of your database manager.
            plan_details (dict): A dictionary containing the details of the plan to be updated.
            on_update_callback (callable): A function to call after the plan is updated.
            icon_loader (callable): A function to load a custom icon.
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.plan_details = plan_details
        self.on_update_callback = on_update_callback
        self.icon_loader = icon_loader

        self.title("Update Plan")
        self.resizable(False, False)
        self.transient(parent)  # Make form modal
        self.grab_set()         # Grab all events from the application

        # Call the new methods to set window properties and customize the title bar
        self._set_window_properties(400, 250, "payment.png")
        self._customize_title_bar()

        self.create_widgets()
        self.populate_fields()

    def _set_window_properties(self, width, height, icon_name):
        """Sets the window size, position, and icon."""
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"+{x}+{y}")
        
        if self.icon_loader and icon_name:
            try:
                icon_image = self.icon_loader(icon_name, size=(32, 32))
                self.iconphoto(False, icon_image)
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Applies a custom color to the title bar on Windows systems."""
        if platform.system() == 'Windows':
            try:
                # DWMWA values are for Windows 10/11
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00663300) # Dark blue in BGR format
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR, byref(color), sizeof(color)
                )
                text_color = c_int(0x00FFFFFF) # White in BGR
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color)
                )
            except (ImportError, OSError):
                # This is okay, it just means the dwmapi module is not available
                pass
            except Exception as e:
                print(f"Could not customize title bar: {e}")

    def create_widgets(self):
        """
        Creates the form's widgets (labels, entry fields, and buttons).
        """
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Plan Name
        ttk.Label(main_frame, text="Plan Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=30)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5)

        #deposit Percentage
        ttk.Label(main_frame, text="Deposit Percentage (%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.deposit_percentage_entry = ttk.Entry(main_frame, width=10)
        self.deposit_percentage_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)


        # Duration (months)
        ttk.Label(main_frame, text="Duration (months):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.duration_spinbox = ttk.Spinbox(main_frame, from_=1, to=120, width=5)
        self.duration_spinbox.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        # Interest Rate (%)
        ttk.Label(main_frame, text="Interest Rate (%):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.interest_rate_entry = ttk.Entry(main_frame, width=10)
        self.interest_rate_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Load and set images for buttons using the icon_loader function
        save_icon = self.icon_loader("save.png", size=(20, 20))
        cancel_icon = self.icon_loader("cancel.png", size=(20, 20))

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_plan, image=save_icon, compound=tk.LEFT)
        self.save_button.image = save_icon # Keep a reference
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy, image=cancel_icon, compound=tk.LEFT)
        self.cancel_button.image = cancel_icon # Keep a reference
        self.cancel_button.pack(side=tk.LEFT, padx=5)

    def populate_fields(self):
        """
        Pre-populates the form fields with the selected plan's data.
        """
        self.name_entry.insert(0, self.plan_details.get("name", ""))
        self.deposit_percentage_entry.insert(0, self.plan_details.get("deposit_percentage", 0))
        self.duration_spinbox.set(self.plan_details.get("duration_months", 1))
        self.interest_rate_entry.insert(0, self.plan_details.get("interest_rate", 0))

    def save_plan(self):
        """
        Handles saving the updated plan details to the database.
        """
        updated_name = self.name_entry.get()
        
        try:
            # Get and validate numerical inputs
            updated_deposit_percentage = float(self.deposit_percentage_entry.get())
            if not (0 <= updated_deposit_percentage <= 100):
                messagebox.showerror("Validation Error", "Deposit Percentage must be between 0 and 100.", parent=self)
                return  
            updated_duration = int(self.duration_spinbox.get())
            updated_interest_rate = float(self.interest_rate_entry.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Duration and Interest Rate must be numbers.", parent=self)
            return

        if not updated_name:
            messagebox.showerror("Validation Error", "Plan name is required.", parent=self)
            return

        # Use the correct plan_id from the initial details
        plan_id = self.plan_details.get("plan_id")

        updated_plan_data = {
        'name': updated_name,
        'deposit_percentage': updated_deposit_percentage,
        'duration_months': updated_duration,
        'interest_rate': updated_interest_rate
        }
        
        try:
            # Assuming your db_manager has a method to update a plan
            self.db_manager.update_payment_plan(
                plan_id=plan_id,
                plan_data=updated_plan_data
            )
            messagebox.showinfo("Success", "Plan updated successfully!", parent=self)
            
            # Call the callback to refresh the main view
            if self.on_update_callback:
                self.on_update_callback()
                
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update plan: {e}", parent=self)
