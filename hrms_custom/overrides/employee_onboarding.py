import frappe
from hrms.hr.doctype.employee_onboarding.employee_onboarding import EmployeeOnboarding


class CustomEmployeeOnboarding(EmployeeOnboarding):

    def on_update(self):
        super().on_update()
        if self.workflow_state == "Onboarding In Progress":
            self._create_onboarding_tickets()

    def _create_onboarding_tickets(self):

        # 🔁 Change these emails tomorrow
        SIM_EMAIL             = "admin@example.com"
        IT_EMAIL              = "admin@example.com"
        EMAIL_ADMIN           = "admin@example.com"
        SW_EMAIL              = "admin@example.com"
        IDCARD_EMAIL          = "admin@example.com"
        BC_EMAIL              = "admin@example.com"
        IDCARD_DESIGNER_EMAIL = "ashwinkumar.k@quanticustech.com"

        base_info = {
            "name":    self.employee_name or "",
            "doj":     str(self.date_of_joining or ""),
            "dept":    self.department or "",
            "desig":   self.designation or "",
            "company": self.company or "",
        }

        def base_table(extra_rows=""):
            return (
                "<table border='1' cellpadding='6' cellspacing='0' "
                "style='border-collapse:collapse;width:100%'>"
                "<tr><td><b>Employee Name</b></td><td>{name}</td></tr>"
                "<tr><td><b>Date of Joining</b></td><td>{doj}</td></tr>"
                "<tr><td><b>Department</b></td><td>{dept}</td></tr>"
                "<tr><td><b>Designation</b></td><td>{desig}</td></tr>"
                "<tr><td><b>Company</b></td><td>{company}</td></tr>"
                "{extra}"
                "</table>"
            ).format(extra=extra_rows, **base_info)

        def make_ticket(subject, description):
            ticket = frappe.new_doc("HD Ticket")
            ticket.subject = subject
            ticket.description = description
            ticket.raised_by = frappe.session.user
            ticket.insert(ignore_permissions=True)

        def send_mail(to, subject, body, salutation):
            frappe.sendmail(
                recipients=[to],
                subject=subject,
                message=(
                    "<p>Dear {sal},</p>"
                    "<p>Please process the below request for new joiner.</p>"
                    "{body}"
                    "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
                ).format(sal=salutation, body=body)
            )

        tickets_created = 0

        # ✅ SIM CARD
        if self.custom_sim_card and self.custom_sim_card != "No":
            extra = "<tr><td><b>SIM Request</b></td><td>{}</td></tr>".format(
                self.custom_sim_card
            )
            if self.custom_sim_card == "Replace" and self.custom_sim_replacement_name:
                extra += (
                    "<tr><td><b>Replace For</b></td><td>{}</td></tr>".format(
                        self.custom_sim_replacement_name
                    )
                )
            table = base_table(extra)
            subject = "SIM Card {} Request - {}".format(
                self.custom_sim_card, self.employee_name
            )
            make_ticket(subject, table)
            send_mail(SIM_EMAIL, subject, table, "SIM Admin")
            tickets_created += 1

        # ✅ LAPTOP / DESKTOP
        if self.custom_laptop_type and self.custom_laptop_type != "No":
            extra = "<tr><td><b>Device Required</b></td><td>{}</td></tr>".format(
                self.custom_laptop_type
            )
            table = base_table(extra)
            subject = "{} Request - {}".format(
                self.custom_laptop_type, self.employee_name
            )
            make_ticket(subject, table)
            send_mail(IT_EMAIL, subject, table, "IT Admin")
            tickets_created += 1

        # ✅ EMAIL ID
        if self.custom_email_id and self.custom_email_id != "No":
            extra = "<tr><td><b>Email Request</b></td><td>{}</td></tr>".format(
                self.custom_email_id
            )
            if self.custom_email_id == "Replace" and self.custom_email_replacement_name:
                extra += (
                    "<tr><td><b>Replace For</b></td><td>{}</td></tr>".format(
                        self.custom_email_replacement_name
                    )
                )
            table = base_table(extra)
            subject = "Email ID {} Request - {}".format(
                self.custom_email_id, self.employee_name
            )
            make_ticket(subject, table)
            send_mail(EMAIL_ADMIN, subject, table, "Email Admin")
            tickets_created += 1

        # ✅ SOFTWARE ACCESS
        if self.custom_software_access:
            extra = "<tr><td><b>Software/CRM</b></td><td>{}</td></tr>".format(
                self.custom_software_access
            )
            table = base_table(extra)
            subject = "Software Access Request - {}".format(self.employee_name)
            make_ticket(subject, table)
            send_mail(SW_EMAIL, subject, table, "Software Admin")
            tickets_created += 1

        # ✅ ID CARD TICKET
        if self.custom_id_card:
            extra = "<tr><td><b>ID Card</b></td><td>Required</td></tr>"
            table = base_table(extra)
            subject = "ID Card Request - {}".format(self.employee_name)
            make_ticket(subject, table)
            send_mail(IDCARD_EMAIL, subject, table, "Admin")
            tickets_created += 1

        # ✅ BUSINESS CARD
        if self.custom_business_card:
            extra = "<tr><td><b>Business Card</b></td><td>Required</td></tr>"
            table = base_table(extra)
            subject = "Business Card Request - {}".format(self.employee_name)
            make_ticket(subject, table)
            send_mail(BC_EMAIL, subject, table, "Admin")
            tickets_created += 1

        # ✅ ID CARD DESIGN EMAIL
        self._send_idcard_design_email(IDCARD_DESIGNER_EMAIL)

        if tickets_created > 0:
            frappe.msgprint(
                "{} ticket(s) created and email(s) sent!".format(tickets_created),
                indicator="green",
                title="Success"
            )

    def _send_idcard_design_email(self, designer_email):

        # ✅ Correct fieldnames from console output
        employee_id  = self.custom_employee_id_ or "Not Assigned"
        emergency_ph = self.custom_emergency_phone_number or "Not Provided"
        blood_group  = self.custom_blood_group_ or "Not Provided"
        photo_url    = self.custom_candidate_passport_size_image_for_id_card or ""
        date_of_issue = str(self.date_of_joining or "")
        company      = self.company or ""
        emp_name     = self.employee_name or ""

        # Photo HTML
        photo_html = ""
        if photo_url:
            # Build full URL if relative path
            if photo_url.startswith("/files/"):
                from frappe.utils import get_url
                photo_url = get_url(photo_url)

            photo_html = (
                "<tr>"
                "<td><b>Passport Photo</b></td>"
                "<td><img src='{url}' style='width:120px;height:150px;"
                "object-fit:cover;border:1px solid #ccc;'/></td>"
                "</tr>"
            ).format(url=photo_url)

        subject = "ID Card Design Request - {} ({})".format(emp_name, company)

        message = (
            "<div style='font-family:Arial,sans-serif;max-width:650px;margin:0 auto;'>"

            "<div style='background:#1B4F8A;padding:20px;text-align:center;'>"
            "<h2 style='color:white;margin:0;'>ID Card Design Request</h2>"
            "<p style='color:#cce0ff;margin:5px 0;'>{company}</p>"
            "</div>"

            "<div style='padding:30px;background:#f9f9f9;'>"
            "<p>Dear ID Card Designer,</p>"
            "<p>Please design the ID card for the following new joiner:</p>"

            "<table border='1' cellpadding='8' cellspacing='0' "
            "style='border-collapse:collapse;width:100%;margin-top:15px;'>"
            "<tr style='background:#1B4F8A;color:white;'>"
            "<th colspan='2' style='padding:10px;'>Employee ID Card Details</th>"
            "</tr>"
            "<tr><td width='40%'><b>Employee Name</b></td>"
            "<td><b style='font-size:16px;'>{emp_name}</b></td></tr>"
            "<tr><td><b>Company</b></td><td>{company}</td></tr>"
            "<tr><td><b>Employee ID (ID Number)</b></td>"
            "<td><b style='color:#1B4F8A;font-size:15px;'>{emp_id}</b></td></tr>"
            "<tr><td><b>Blood Group</b></td><td>{blood}</td></tr>"
            "<tr><td><b>Emergency Phone</b></td><td>{emergency}</td></tr>"
            "<tr><td><b>Date of Issue</b></td><td>{doi}</td></tr>"
            "{photo}"
            "</table>"

            "<p style='margin-top:20px;color:#555;'>"
            "Please design the ID card as per company format and send for printing.</p>"
            "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
            "</div>"

            "<div style='background:#1B4F8A;padding:10px;text-align:center;'>"
            "<p style='color:#cce0ff;margin:0;font-size:11px;'>"
            "Aionion Capital HRMS — Confidential</p>"
            "</div>"
            "</div>"
        ).format(
            company=company,
            emp_name=emp_name,
            emp_id=employee_id,
            blood=blood_group,
            emergency=emergency_ph,
            doi=date_of_issue,
            photo=photo_html
        )

        frappe.sendmail(
            recipients=[designer_email],
            subject=subject,
            message=message,
            reference_doctype="Employee Onboarding",
            reference_name=self.name,
        )

        frappe.msgprint(
            "ID Card design email sent to {}".format(designer_email),
            indicator="blue",
            title="ID Card Email"
        )