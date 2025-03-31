import customtkinter as ctk
from src.models import StudentRecord
from tkinter import ttk, messagebox
from tkinter import filedialog  # add this to the top if not already there



class MockAudit:
    def __init__(self, student_id, term, ptc_major, gpa, eligible):
        self.student_id = student_id
        self.term = term
        self.ptc_major = ptc_major
        self.gpa = gpa
        self.eligible = eligible


class RealAuditViewModel:
    def __init__(self):
        from src.models import StudentRecord, StudentAudit
        self.StudentRecord = StudentRecord
        self.StudentAudit = StudentAudit
        self.term_options = self.load_term_options()
        self.past_audits = self.load_audits()

    def load_term_options(self):
        terms = self.StudentAudit.objects.order_by('-term').values_list('term', flat=True).distinct()
        return [str(term) for term in terms]

    def load_audits(self):
        return self.StudentAudit.objects.select_related('student').order_by('-term', 'student__student_id')

    def run_audit(self, term):
        from src.eligibility import run_eligibility_audit
        run_eligibility_audit(int(term))
        
        
class NCAA_Audit_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NCAA Athletic Audit System (Template)")
        self.geometry("1000x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.viewmodel = RealAuditViewModel()
        # self.viewmodel = MockAuditViewModel()
        self.selected_term = ctk.StringVar(value=self.viewmodel.term_options[0])

        self.setup_ui()

    def setup_ui(self):
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(pady=10, padx=10, fill="x")

        # Term Dropdown
        self.term_menu = ctk.CTkOptionMenu(
            self.top_frame,
            variable=self.selected_term,
            values=self.viewmodel.term_options
        )
        self.term_menu.pack(side="left", padx=10)

        self.audit_btn = ctk.CTkButton(self.top_frame, text="Run Audit", command=self.audit)
        self.audit_btn.pack(side="left", padx=10)

        self.upload_btn = ctk.CTkButton(self.top_frame, text="Upload CSV", command=self.upload_csv)
        self.upload_btn.pack(side="left", padx=10)

        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.build_past_audits_table()

    def build_past_audits_table(self):
        from tkinter import ttk

        audits = self.viewmodel.past_audits

        columns = ["Student ID", "Term", "% Toward Degree", "GPA", "Eligibility"]
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")

        for audit in audits:
            self.tree.insert(
                "",
                "end",
                values=[
                    audit.student.student_id,
                    audit.term,
                    f"{audit.ptc_major}%",
                    f"{audit.gpa:.2f}" if audit.gpa is not None else "N/A",
                    "✅ Eligible" if audit.eligible else "❌ Ineligible"
                ]
            )

        self.tree.bind("<Double-1>", self.on_audit_double_click)
        self.tree.pack(fill="both", expand=True)

    def audit(self):
        term = self.selected_term.get()
        self.viewmodel.run_audit(term)

    def on_audit_double_click(self, event):
        item = self.tree.selection()
        if item:
            values = self.tree.item(item[0])["values"]
            student_id = values[0]
            term = values[1]
            messagebox.showinfo("Audit Detail", f"Open results for Student {student_id}, Term {term}")
            
    def upload_csv(self):
        from src.data import import_student_data_from_csv

        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            try:
                result = import_student_data_from_csv(file_path)

                if isinstance(result, dict) and not result.get("success", True):
                    messagebox.showerror("Import Failed", result.get("message", "Unknown error."))
                    return

                messagebox.showinfo("Success", "Data uploaded successfully.")
                self.refresh_terms_and_audits()

                # Automatically select the most recent term
                if self.viewmodel.term_options:
                    self.selected_term.set(self.viewmodel.term_options[0])

            except Exception as e:
                messagebox.showerror("Error", f"Failed to import CSV:\n{e}")

                
    def refresh_terms_and_audits(self):
        self.viewmodel = RealAuditViewModel()

        # Update the dropdown menu options and reset the selection
        self.term_menu.configure(values=self.viewmodel.term_options)
        if self.viewmodel.term_options:
            self.selected_term.set(self.viewmodel.term_options[0])
            self.term_menu.set(self.viewmodel.term_options[0])  # Also updates the visible menu

        # Rebuild the audit table
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.build_past_audits_table()





# if __name__ == "__main__":
#     app = NCAA_Audit_GUI()
#     app.mainloop()
