import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

import tkinter as tk
from tkinter import ttk
from collections import defaultdict

from your_app.models import StudentRecord  #Replace 'your_app' with  Django app name


class StudentDetailViewModel:
    def __init__(self, student_id):
        self.student_id = student_id
        self.records = list(
            StudentRecord.objects.select_related("course").filter(student_id=student_id).order_by("term")
        )
        self.summary = self.calculate_summary()

    def calculate_summary(self):
        terms = set()
        total_credits = 0
        for record in self.records:
            terms.add(record.term)
            total_credits += record.credits
        return {
            "student_id": self.student_id,
            "num_terms": len(terms),
            "total_credits": total_credits
        }


class StudentDetailView(tk.Tk):
    def __init__(self, student_id):
        super().__init__()
        self.title("Student Detail View")
        self.geometry("950x500")

        self.vm = StudentDetailViewModel(student_id)
        self.create_widgets()

    def create_widgets(self):
        summary = self.vm.summary

        # Header
        header = tk.Frame(self)
        header.pack(pady=10)

        tk.Label(header, text=f"Student ID: {summary['student_id']}", font=('Arial', 12)).grid(row=0, column=0, padx=10)
        tk.Label(header, text=f"Total Credits: {summary['total_credits']}", font=('Arial', 12)).grid(row=0, column=1, padx=10)
        tk.Label(header, text=f"Terms Enrolled: {summary['num_terms']}", font=('Arial', 12)).grid(row=0, column=2, padx=10)

        # Table
        table_frame = tk.Frame(self)
        table_frame.pack()

        columns = ("term", "subject", "course_number", "course_id", "grade", "credits", "counts_toward_major")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())

        for record in self.vm.records:
            course = record.course
            tree.insert("", tk.END, values=(
                record.term,
                course.subject,
                course.course_number,
                course.course_id,
                record.grade,
                record.credits,
                "Yes" if record.counts_toward_major else "No"
            ))

        tree.pack(pady=10)

        # Back button
        back_btn = tk.Button(self, text="Back to Audit", command=self.destroy)
        back_btn.pack(pady=15)



if __name__ == "__main__":
    # Replace this with ID
    student_id_input = 1001
    app = StudentDetailView(student_id_input)
    app.mainloop()
