import tkinter as tk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.label = None
        self.tip_window = None
        
        # We don't set the text here because it's set just before show_tip is called.
        # This is because the initial text is passed to __init__.
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def set_text(self, text):
        self.text = text
        if self.label:
            self.label.config(text=self.text)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        
        # Get coordinates for the tooltip window
        x, y, cx, cy = 10, 10, 0, 0
        try:
            x, y, cx, cy = self.widget.bbox("insert")
        except Exception:
            # Fallback for widgets without 'bbox' method
            pass

        x = x + self.widget.winfo_rootx() + 40
        y = y + cy + self.widget.winfo_rooty() + 20

        # Create the top-level window for the tooltip
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        # Create the label inside the top-level window
        self.label = tk.Label(
            tw, text=self.text, background="#ffffe0",
            relief="solid", borderwidth=1,
            font=("tahoma", 9, "normal"), wraplength=200, justify="left"
        )
        self.label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None