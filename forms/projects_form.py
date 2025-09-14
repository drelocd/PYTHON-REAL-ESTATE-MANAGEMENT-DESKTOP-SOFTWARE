import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta,date
from utils.tooltips import ToolTip
import os
import sys


class FormBase(tk.Toplevel):
    """
    Base class for all forms to handle common functionalities like
    window centering, title bar customization, and icon loading.
    """
    def __init__(self, master, width, height, title, icon_name, parent_icon_loader):
        # Correctly set the parent to the top-level window.
        # This fixes the "bad window path name" error.
        super().__init__(master.winfo_toplevel())
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        
        self.parent_icon_loader = parent_icon_loader
        self._window_icon_ref = None
        self._set_window_properties(width, height, icon_name, parent_icon_loader)
        self._customize_title_bar()
        # Removed the _on_closing() call as it was causing the window to close immediately
        # after being created.

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
                    print(f"Icon '{icon_name}' loaded successfully.") # Add this line
                else:
                    print(f"Icon '{icon_name}' could not be loaded.")
                
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")

    def _customize_title_bar(self):
        """Customizes the title bar appearance. Attempts Windows-specific
        customization, falls back to a custom Tkinter title bar."""
        try:
            if os.name == 'nt':  # Windows-specific title bar customization
                from ctypes import windll, byref, sizeof, c_int

                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36

                hwnd = windll.user32.GetParent(self.winfo_id())
                color = c_int(0x00804000)  # Dark blue color
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
            else:
                self._create_custom_title_bar()
        except Exception as e:
            print(f"Could not customize native title bar: {e}. Falling back to custom Tkinter title bar.")
            self._create_custom_title_bar()

    def _create_custom_title_bar(self):
        """Creates a custom Tkinter title bar when native customization isn't available."""
        self.overrideredirect(True)

        title_bar = tk.Frame(self, bg='#004080', relief='raised', bd=0, height=30)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            title_bar,
            text=self.title(),
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

    def _on_closing(self):
        """Callback for window closing event."""
        self.destroy()

class AddProjectForm(FormBase):
    """
    Form for adding a new project.
    """
    def __init__(self, master, db_manager, parent_icon_loader, user_id, refresh_callback):
        super().__init__(master, 400, 200, "Add New Project", "add.png", parent_icon_loader)
        self.db_manager = db_manager
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        self._load_button_icons()
        self._create_widgets()

    def _load_button_icons(self):
        """Loads icons for the buttons."""
        try:
            self.add_icon = self.parent_icon_loader("add.png", size=(16, 16))
            self.cancel_icon = self.parent_icon_loader("cancel.png", size=(16, 16))
        except Exception as e:
            print(f"Failed to load icons: {e}")
            self.add_icon = None
            self.cancel_icon = None

    def _create_widgets(self):
        """Creates the form widgets."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Project Name:").pack(pady=(0, 5))
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.pack(pady=(0, 20))
        ToolTip(self.name_entry, "Enter the name of the new project.")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", expand=True)
        
        self.add_btn = ttk.Button(button_frame, text="Add Project", image=self.add_icon, compound=tk.LEFT, command=self._add_project)
        self.add_btn.pack(side="left", padx=(0, 10))
        ToolTip(self.add_btn, "Click to save the new project.")

        self.cancel_btn = ttk.Button(button_frame, text="Cancel", image=self.cancel_icon, compound=tk.LEFT, command=self.destroy)
        self.cancel_btn.pack(side="right")
        ToolTip(self.cancel_btn, "Click to close without saving.")
        
    def _add_project(self):
        """Adds the project to the database and closes the form."""
        project_name = self.name_entry.get().strip()
        if not project_name:
            messagebox.showwarning("Input Error", "Project name cannot be empty.")
            return

        try:
            if self.db_manager.add_project(project_name, self.user_id):
                messagebox.showinfo("Success", "Project added successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to add project.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

class UpdateProjectForm(FormBase):
    """
    Form for updating an existing project.
    """
    def __init__(self, master, db_manager, parent_icon_loader, project_id, project_name, refresh_callback):
        super().__init__(master, 400, 200, f"Edit Project: {project_name}", "edit.png", parent_icon_loader)
        self.db_manager = db_manager
        self.project_id = project_id
        self.refresh_callback = refresh_callback
        self._load_button_icons()
        self._create_widgets(project_name)

    def _load_button_icons(self):
        """Loads icons for the buttons."""
        try:
            self.update_icon = self.parent_icon_loader("update.png", size=(16, 16))
            self.cancel_icon = self.parent_icon_loader("cancel.png", size=(16, 16))
        except Exception as e:
            print(f"Failed to load icons: {e}")
            self.update_icon = None
            self.cancel_icon = None

    def _create_widgets(self, project_name):
        """Creates the form widgets."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Project Name:").pack(pady=(0, 5))
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.insert(0, project_name)
        self.name_entry.pack(pady=(0, 20))
        ToolTip(self.name_entry, "Update the name of the project.")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", expand=True)
        
        self.update_btn = ttk.Button(button_frame, text="Update Project", image=self.update_icon, compound=tk.LEFT, command=self._update_project)
        self.update_btn.pack(side="left", padx=(0, 10))
        ToolTip(self.update_btn, "Click to save the changes.")

        self.cancel_btn = ttk.Button(button_frame, text="Cancel", image=self.cancel_icon, compound=tk.LEFT, command=self.destroy)
        self.cancel_btn.pack(side="right")
        ToolTip(self.cancel_btn, "Click to close without saving.")
        
    def _update_project(self):
        """Updates the project in the database and closes the form."""
        new_name = self.name_entry.get().strip()
        if not new_name:
            messagebox.showwarning("Input Error", "Project name cannot be empty.")
            return

        try:
            if self.db_manager.update_project(self.project_id, new_name):
                messagebox.showinfo("Success", "Project updated successfully.")
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to update project.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

class ProjectsPanel(FormBase):
    def __init__(self, master, db_manager, parent_icon_loader, user_id):
        # Pass the user_id to the base class if needed, or store it here.
        super().__init__(master, width=800, height=600, title="Projects Panel", icon_name="project.png", parent_icon_loader=parent_icon_loader)
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader
        self.user_id = user_id  # Store the user ID
        self.all_projects = []

        self._load_button_icons()
        self._setup_ui()
        self._populate_projects_table()

    def _load_button_icons(self):
        """Load icons for buttons."""
        try:
            self.add_icon_img = self.parent_icon_loader("add.png", size=(16, 16))
            self.edit_icon_img = self.parent_icon_loader("edit.png", size=(16, 16))
            self.delete_icon_img = self.parent_icon_loader("delete.png", size=(16, 16))
        except Exception as e:
            print(f"Failed to load button icons: {e}")
            self.add_icon_img = None
            self.edit_icon_img = None
            self.delete_icon_img = None

    def _setup_ui(self):
        """Sets up the user interface components."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Top frame for Add Project button
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))

        add_btn = ttk.Button(top_frame, text="Add Project", compound=tk.LEFT, image=self.add_icon_img, command=self._add_project)
        add_btn.pack(side="right")
        ToolTip(add_btn, "Click to add a new project.")

        # Table frame
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill="both", expand=True)

        columns = ("project_name", "num_properties", "added_by", "sale_status")
        self.projects_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.projects_tree.heading("project_name", text="Project Name")
        self.projects_tree.heading("num_properties", text="No. of Properties")
        self.projects_tree.heading("added_by", text="Added By")
        self.projects_tree.heading("sale_status", text="Sale Status")
        
        # Set column widths
        self.projects_tree.column("project_name", width=200)
        self.projects_tree.column("num_properties", width=120)
        self.projects_tree.column("added_by", width=120)
        self.projects_tree.column("sale_status", width=100)

        self.projects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.projects_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.projects_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bottom frame for Edit and Delete buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", pady=(10, 0))

        delete_btn = ttk.Button(bottom_frame, text="Delete Project", compound=tk.LEFT, image=self.delete_icon_img, command=self._delete_project)
        delete_btn.pack(side="left")
        ToolTip(delete_btn, "Click to delete the selected project.")

        edit_btn = ttk.Button(bottom_frame, text="Edit Project", compound=tk.LEFT, image=self.edit_icon_img, command=self._edit_project)
        edit_btn.pack(side="right")
        ToolTip(edit_btn, "Click to edit the selected project.")

    def _populate_projects_table(self):
        """Fetches and displays projects data."""
        for item in self.projects_tree.get_children():
            self.projects_tree.delete(item)
        
        try:
            self.all_projects = self.db_manager.get_projects_data()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve projects data: {e}")
            self.all_projects = []
            
        if self.all_projects is None:
            self.all_projects = []

        for project in self.all_projects:
            self.projects_tree.insert("", tk.END, values=(
                project['project_name'].upper(),
                project['num_properties'],
                project['added_by_username'].upper(),
                project['sale_status'].upper()
            ))

    def _add_project(self):
        """Opens the form to add a new project."""
        AddProjectForm(self.master, self.db_manager, self.parent_icon_loader, self.user_id, self._populate_projects_table)

    def _edit_project(self):
        """Opens the form to edit a selected project."""
        selected_item = self.projects_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a project to edit.")
            return

        project_data = self.projects_tree.item(selected_item, 'values')
        project_name = project_data[0]
        
        # You need the project_id to update the project. Let's assume you store it
        # as a hidden column or a data attribute. For now, we'll get it from a lookup.
        # In a real app, you'd insert the project_id into the treeview.
        # Let's find the project ID from the all_projects list.
        project_id = None
        for project in self.all_projects:
            if project['project_name'] == project_name:
                project_id = project['project_id']
                break
        
        if project_id:
            UpdateProjectForm(self.master, self.db_manager, self.parent_icon_loader, project_id, project_name, self._populate_projects_table)
        else:
            messagebox.showerror("Error", "Could not find project details.")

    def _delete_project(self):
        """Placeholder for deleting a selected project."""
        selected_item = self.projects_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a project to delete.")
            return

        project_data = self.projects_tree.item(selected_item, 'values')
        project_name = project_data[0]
        
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the project '{project_name}'?"):
            project_id = None
            for project in self.all_projects:
                if project['project_name'] == project_name:
                    project_id = project['project_id']
                    break
            
            if project_id:
                try:
                    if self.db_manager.delete_project(project_id):
                        messagebox.showinfo("Success", f"Project '{project_name}' has been marked as inactive.")
                        self._populate_projects_table() # Refresh table
                    else:
                        messagebox.showerror("Error", "Failed to delete project.")
                except Exception as e:
                    messagebox.showerror("Database Error", f"An error occurred: {e}")
            else:
                messagebox.showerror("Error", "Could not find project details for deletion.")
