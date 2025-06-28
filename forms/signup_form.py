import tkinter as tk
from tkinter import ttk, messagebox
import os

# Assuming DatabaseManager is in 'database.py'
# You might need to adjust the import path based on your project structure
try:
    from database import DatabaseManager
except ImportError:
    messagebox.showerror("Import Error", "Could not import DatabaseManager. "
                                        "Please ensure 'database.py' is in the correct directory.")
    # Exit or handle the error appropriately if DatabaseManager is critical
    DatabaseManager = None # Set to None to prevent further errors if import fails


class SignupForm(tk.Toplevel):
    """
    A Toplevel window for user signup (admin or regular user).
    Allows new users to be registered in the database.
    """

    def __init__(self, parent, db_manager, parent_icon_loader=None):
        """
        Initializes the SignupForm window.

        Args:
            parent: The parent Tkinter window (e.g., the main application window).
            db_manager: An instance of DatabaseManager for database interactions.
            parent_icon_loader: A callable to load icons, typically from the main app.
        """
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader

        self.title("Sign Up New User")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)  # Make it appear on top of the parent
        self.grab_set()  # Grab all events until this window is destroyed

        self._create_widgets()

    def _create_widgets(self):
        """
        Creates and places the widgets in the signup form.
        """
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Register New User", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # Username Label and Entry
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.username_entry.focus_set() # Set focus to username field

        # Password Label and Entry
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show="*") # Show asterisks for password
        self.password_entry.grid(row=2, column=1, sticky="ew", pady=5)

        # Role Label and Combobox
        ttk.Label(main_frame, text="Role:").grid(row=3, column=0, sticky="w", pady=5)
        self.role_combobox = ttk.Combobox(main_frame, values=["user", "admin"], state="readonly", width=27)
        self.role_combobox.grid(row=3, column=1, sticky="ew", pady=5)
        self.role_combobox.set("user")  # Default role

        # Signup Button
        signup_button = ttk.Button(main_frame, text="Sign Up", command=self._signup_user)
        signup_button.grid(row=4, column=0, columnspan=2, pady=20)

        # Configure grid columns to expand
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=3)

    def _signup_user(self):
        """
        Handles the user signup process when the signup button is clicked.
        Validates input and calls the database manager to add the user.
        """
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_combobox.get().strip()

        if not username or not password:
            messagebox.showwarning("Input Error", "Username and Password cannot be empty.", parent=self)
            return

        if not self.db_manager:
            messagebox.showerror("Database Error", "Database manager is not initialized.", parent=self)
            return

        try:
            # Check if the user already exists to provide a more specific error
            existing_user = self.db_manager.get_user_by_username(username)
            if existing_user:
                messagebox.showwarning("Signup Failed", f"User '{username}' already exists. Please choose a different username.", parent=self)
                return

            user_id = self.db_manager.add_user(username, password, role)

            if user_id:
                messagebox.showinfo("Signup Successful",
                                    f"User '{username}' with role '{role}' registered successfully! User ID: {user_id}",
                                    parent=self)
                self.destroy()  # Close the signup form after successful registration
            else:
                # This case should ideally be caught by existing_user check,
                # but kept as a fallback for unexpected database issues.
                messagebox.showerror("Signup Failed", f"Could not register user '{username}'. An unexpected error occurred.", parent=self)
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during signup: {e}", parent=self)

# Example of how to use the SignupForm (for testing purposes, not part of the class itself)
if __name__ == "__main__":
    # This block will only run when signup_form.py is executed directly
    # It simulates a simple Tkinter app to test the SignupForm
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Initialize DatabaseManager (ensure 'database.py' and 'data/real_estate.db' are set up)
    if DatabaseManager:
        db_manager_instance = DatabaseManager()
        # You might want to call _create_tables() explicitly here if not already done by DatabaseManager's __init__
        # db_manager_instance._create_tables() # Uncomment if needed for testing setup

        # Function to open the signup form
        def open_signup_form():
            signup_window = SignupForm(root, db_manager_instance)
            signup_window.wait_window()  # Wait until the signup window is closed
            print("Signup form closed.")
            # After signup, you might want to refresh a user list or perform other actions
            # For testing, you could try to authenticate the new user here

        # Create a button to open the signup form
        test_button = ttk.Button(root, text="Open Signup Form", command=open_signup_form)
        test_button.pack(pady=50)

        # Simple label to show main window is active
        test_label = ttk.Label(root, text="Main Application (hidden)")
        test_label.pack()

        root.deiconify() # Show the main window for the button
        root.mainloop()
    else:
        messagebox.showerror("Application Error", "Cannot run SignupForm example due to missing DatabaseManager.")