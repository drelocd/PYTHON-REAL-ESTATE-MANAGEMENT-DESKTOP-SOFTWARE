# report_utils.py
import tkinter as tk
from tkinter import messagebox
import os
from datetime import datetime, timedelta

# Import ReportLab components
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors

    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    print("Warning: ReportLab library not found. PDF generation will be disabled.")

# Define BASE_DIR relative to the report_utils.py file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)  # Ensure reports directory exists


def get_report_dates(report_type):
    """Determines start and end dates based on report type."""
    today = datetime.now()
    start_date = None
    end_date = None

    if report_type == "daily":
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif report_type == "monthly":
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        # Calculate last day of the month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = end_date.strftime("%Y-%m-%d")
    elif report_type == "yearly":
        start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        end_date = today.replace(month=12, day=31).strftime("%Y-%m-%d")
    # Add custom date range logic if needed, possibly using DatePicker
    return start_date, end_date


def generate_pdf_report(report_title, report_data_details, report_type, start_date=None, end_date=None):
    """
    Generates a PDF report using ReportLab.
    report_data_details is expected to be a dictionary, e.g., {'data': list_of_dicts}.
    """
    if not _REPORTLAB_AVAILABLE:
        messagebox.showerror("Error",
                             "ReportLab library not available. Please install it (`pip install reportlab`) for PDF generation.")
        return None

    filename_suffix = f"_{start_date}_to_{end_date}" if start_date and end_date else ""
    pdf_filename = os.path.join(REPORTS_DIR, f"{report_type.replace(' ', '_').lower()}_report{filename_suffix}.pdf")

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Add title
    story.append(Paragraph(report_title, styles['Title']))
    story.append(Spacer(1, 0.2 * inch))

    # Add date range if applicable
    if start_date and end_date:
        date_range_text = f"Report Period: {start_date} to {end_date}"
        story.append(Paragraph(date_range_text, styles['Normal']))
        story.append(Spacer(1, 0.1 * inch))

    # Add data to the PDF based on report_type
    if report_type == "Sales":
        sales_data = report_data_details.get('data', [])
        if sales_data:
            headers = ["Property ID", "Title Deed", "Buyer Name", "Price (KES)", "Amount Paid (KES)", "Date Sold"]
            table_data = [headers] + [[
                s['property_id'], s['title_deed_number'], s['buyer_name'],
                f"{s['agreed_price']:,.2f}", f"{s['amount_paid']:,.2f}", s['sale_date']
            ] for s in sales_data]

            t = Table(table_data, colWidths=[0.8 * inch, 1.5 * inch, 1.2 * inch, 1 * inch, 1 * inch, 1 * inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No sales data found for this period.", styles['Normal']))
    elif report_type == "Sold Properties":
        sold_properties_data = report_data_details.get('data', [])
        if sold_properties_data:
            headers = ["Property ID", "Title Deed", "Location", "Price", "Date Sold", "Buyer"]
            table_data = [headers] + [[
                p['property_id'], p['title_deed_number'], p['location'], f"{p['price']:,.2f}", p['sale_date'],
                p['buyer_name']
            ] for p in sold_properties_data]

            t = Table(table_data, colWidths=[0.8 * inch, 1.5 * inch, 1.2 * inch, 1 * inch, 1 * inch, 1 * inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No sold properties data found for this period.", styles['Normal']))
    elif report_type == "Pending Instalments":
        pending_instalments_data = report_data_details.get('data', [])
        if pending_instalments_data:
            headers = ["Sale ID", "Property ID", "Buyer Name", "Due Date", "Amount Due", "Status"]
            table_data = [headers] + [[
                i['sale_id'], i['property_id'], i['buyer_name'], i['due_date'], f"{i['amount_due']:,.2f}", i['status']
            ] for i in pending_instalments_data]

            t = Table(table_data, colWidths=[0.8 * inch, 1 * inch, 1.2 * inch, 1 * inch, 1 * inch, 1 * inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No pending instalments data found for this period.", styles['Normal']))

    try:
        doc.build(story)
        print(f"PDF report generated at: {pdf_filename}")
        return pdf_filename
    except Exception as e:
        print(f"Error building PDF: {e}")
        return None


def show_pdf_preview(pdf_path, text_widget):
    """Displays a message in the text widget indicating PDF preview (since Tkinter can't embed PDF)."""
    if pdf_path:
        text_widget.insert(tk.END, f"\n\nPDF report saved to: {os.path.basename(pdf_path)}\n")
        text_widget.insert(tk.END, f"Full path: {pdf_path}\n")
        text_widget.insert(tk.END, "Please open the PDF file in an external viewer to see the full report.\n")
    else:
        text_widget.insert(tk.END, "\n\nPDF report could not be generated.")


# Placeholder for SuccessMessage if it's not in a universally accessible place
# In your actual app, ensure SuccessMessage is imported or defined correctly.
class SuccessMessage(tk.Toplevel):
    def __init__(self, parent, success=True, message="", pdf_path=None, parent_icon_loader=None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Success" if success else "Error")
        self.geometry("300x150")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill="both")

        icon_name = "check.png" if success else "error.png"
        icon_size = (32, 32)
        if parent_icon_loader:
            self.icon_image = parent_icon_loader(icon_name, icon_size)
            if self.icon_image:
                icon_label = ttk.Label(frame, image=self.icon_image)
                icon_label.pack(pady=(0, 10))

        message_label = ttk.Label(frame, text=message, wraplength=250, justify=tk.CENTER)
        message_label.pack(pady=(0, 10))

        if pdf_path:
            open_button = ttk.Button(frame, text="Open Report Folder",
                                     command=lambda: self._open_report_folder(pdf_path))
            open_button.pack(pady=(5, 0))

        ok_button = ttk.Button(frame, text="OK", command=self.destroy)
        ok_button.pack(pady=(10, 0))

        self.center_window()

    def _open_report_folder(self, pdf_path):
        folder_path = os.path.dirname(pdf_path)
        try:
            if os.path.exists(folder_path):
                os.startfile(folder_path)  # For Windows
            else:
                messagebox.showerror("Error", f"Report folder not found: {folder_path}")
        except AttributeError:
            # For macOS/Linux
            import subprocess
            try:
                subprocess.Popen(['xdg-open', folder_path])  # Linux
            except FileNotFoundError:
                subprocess.Popen(['open', folder_path])  # macOS
        except Exception as e:
            messagebox.showerror("Error", f"Could not open report folder: {e}")

    def center_window(self):
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        win_width = self.winfo_width()
        win_height = self.winfo_height()

        x = parent_x + (parent_width // 2) - (win_width // 2)
        y = parent_y + (parent_height // 2) - (win_height // 2)

        self.geometry(f'+{x}+{y}')