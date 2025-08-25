import tkinter as tk
from tkinter import ttk, messagebox
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from database import DatabaseManager  # Assuming database.py is accessible


class DashboardForm(ttk.Frame):
    """
    A dashboard view that provides a visual overview of the system.
    """

    def __init__(self, master, db_manager, parent_icon_loader, user_type):
        super().__init__(master)
        self.db_manager = db_manager
        self.parent_icon_loader = parent_icon_loader
        self.user_type = user_type

        # Keep references to chart canvases to prevent them from being garbage collected
        self.prop_chart_canvas = None
        self.survey_chart_canvas = None

        self._create_widgets()
        self.populate_dashboard()

    def _create_widgets(self):
        """Builds the dashboard UI components."""
        title_label = ttk.Label(self, text="System Dashboard", font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=10)

        # Overview section
        overview_frame = ttk.Frame(self, padding="10")
        overview_frame.pack(fill="x", padx=20, pady=10)

        self.labels = {}
        data_points = [
            ("Total Properties", "TotalProperties.png"),
            ("Sold Properties", "SoldProperties.png"),
            ("Available Properties", "AvailableProperties.png"),
            ("Total Clients", "Clients.png"),
            ("Total Survey Jobs", "TotalSurveyJobs.png")
        ]

        for i, (text, icon) in enumerate(data_points):
            frame = ttk.Frame(overview_frame, relief="ridge", borderwidth=2, padding="10")
            frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

            try:
                icon_image = self.parent_icon_loader(icon, size=(48, 48))
                icon_label = ttk.Label(frame, image=icon_image)
                icon_label.image = icon_image  # Keep reference
                icon_label.pack(pady=(0, 5))
            except:
                # Fallback in case icons are not found
                print(f"Warning: Icon {icon} not found.")
                icon_label = ttk.Label(frame, text="[Icon]", font=('Helvetica', 10))
                icon_label.pack(pady=(0, 5))

            data_label = ttk.Label(frame, text="N/A", font=('Helvetica', 14, 'bold'))
            data_label.pack()
            self.labels[text] = data_label

            desc_label = ttk.Label(frame, text=text, font=('Helvetica', 10))
            desc_label.pack()

        for i in range(len(data_points)):
            overview_frame.grid_columnconfigure(i, weight=1)

        # Charts section
        charts_container = ttk.Frame(self)
        charts_container.pack(fill="both", expand=True, padx=20, pady=10)
        charts_container.columnconfigure(0, weight=1)
        charts_container.columnconfigure(1, weight=1)

        self.prop_chart_frame = ttk.Frame(charts_container, relief="ridge", borderwidth=2)
        self.prop_chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.survey_chart_frame = ttk.Frame(charts_container, relief="ridge", borderwidth=2)
        self.survey_chart_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    def populate_dashboard(self):
        """Fetches data from the database and updates the dashboard UI."""

        num_sold = self.db_manager.get_total_sold_properties_count()
        num_available = self.db_manager.count_available_properties()
        num_total_properties = num_sold + num_available
        num_clients = self.db_manager.get_total_clients()
        num_survey_jobs = self.db_manager.get_total_survey_jobs()

        self.labels["Total Properties"].config(text=str(num_total_properties))
        self.labels["Sold Properties"].config(text=str(num_sold))
        self.labels["Available Properties"].config(text=str(num_available))
        self.labels["Total Clients"].config(text=str(num_clients))
        self.labels["Total Survey Jobs"].config(text=str(num_survey_jobs))

        self._create_property_status_chart(num_available, num_sold)
        self._create_survey_jobs_chart()

    def _create_property_status_chart(self, available, sold):
        """Creates and displays a pie chart for property status."""
        for widget in self.prop_chart_frame.winfo_children():
            widget.destroy()

        if available + sold == 0:
            ttk.Label(self.prop_chart_frame, text="No property data available.",
                      anchor="center").pack(expand=True)
            return

        fig, ax = plt.subplots(figsize=(4, 3))
        labels = ['Available', 'Sold']
        sizes = [available, sold]
        colors = ['#4CAF50', '#FF5722']
        explode = (0.1, 0) if sold > 0 and available > 0 else (0, 0)

        def autopct_format(value):
            total = sum(sizes)
            if total == 0:
                return ""
            return f"{value:.1f}%\n({int(value / 100. * total)})"

        ax.pie(sizes, explode=explode, labels=labels, autopct=autopct_format,
               colors=colors, startangle=90, textprops={'fontsize': 8})
        ax.axis('equal')
        ax.set_title('Property Status Overview', fontsize=10)

        self.prop_chart_canvas = FigureCanvasTkAgg(fig, master=self.prop_chart_frame)
        self.prop_chart_canvas.draw()
        self.prop_chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)

    def _create_survey_jobs_chart(self):
        """Creates and displays a bar chart for survey job status."""
        for widget in self.survey_chart_frame.winfo_children():
            widget.destroy()

        status_counts = self.db_manager.get_survey_job_status_counts()

        if not status_counts:
            ttk.Label(self.survey_chart_frame, text="No survey data available.",
                      anchor="center").pack(expand=True)
            return

        labels = [status.capitalize() for status in status_counts.keys()]
        values = list(status_counts.values())

        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar(labels, values, color=['#2196F3', '#FFC107', '#9E9E9E', '#E91E63'])
        ax.set_title('Survey Jobs by Status', fontsize=10)
        ax.set_ylabel('Number of Jobs', fontsize=8)
        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', labelsize=8)

        for i, v in enumerate(values):
            ax.text(i, v + 0.5, str(v), ha='center', va='bottom', fontsize=8)

        self.survey_chart_canvas = FigureCanvasTkAgg(fig, master=self.survey_chart_frame)
        self.survey_chart_canvas.draw()
        self.survey_chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)