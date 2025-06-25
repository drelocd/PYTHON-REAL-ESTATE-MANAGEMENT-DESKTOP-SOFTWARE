class TrackPaymentsForm(tk.Toplevel):
    def __init__(self, master, db_manager, callback_on_close=None, parent_icon_loader=None, window_icon_name="track_payments.png"):
        super().__init__(master)
        self.title("Track Payments")
        self.resizable(False, False)

        self.db_manager = db_manager
        self.callback_on_close = callback_on_close
        self._window_icon_ref = None  # For icon persistence

        # Set window properties and customize title bar
        self._set_window_properties(1300, 550, window_icon_name, parent_icon_loader)
        self._customize_title_bar()

        self._create_widgets(parent_icon_loader)

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
                self._window_icon_ref = icon_image
            except Exception as e:
                print(f"Failed to set icon for {self.title()}: {e}")
    def _on_closing(self):
        """Handle window closing, release grab, and call callback."""
        self.grab_release()
        self.destroy()
        if self.callback_on_close:
            self.callback_on_close()                