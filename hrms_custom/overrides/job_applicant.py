import frappe
from hrms.hr.doctype.job_applicant.job_applicant import JobApplicant
from frappe.model.naming import make_autoname, append_number_if_name_exists

class CustomJobApplicant(JobApplicant):
    def autoname(self):
        if self.job_title:
            self.name = make_autoname(f"{self.job_title}-.####")
        else:
            self.name = self.email_id
            if frappe.db.exists("Job Applicant", self.name):
                self.name = append_number_if_name_exists("Job Applicant", self.name)
