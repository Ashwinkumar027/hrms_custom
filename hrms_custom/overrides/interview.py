import frappe
from frappe import _
import datetime
from hrms.hr.doctype.interview.interview import Interview, get_recipients

class CustomInterview(Interview):
    @frappe.whitelist()
    def reschedule_interview(
        self, scheduled_on: datetime.date, from_time: datetime.time, to_time: datetime.time
    ) -> None:
        if scheduled_on == self.scheduled_on and from_time == self.from_time and to_time == self.to_time:
            frappe.msgprint(
                _("No changes found in timings."), indicator="orange", title=_("Interview Not Rescheduled")
            )
            return

        original_date = self.scheduled_on
        original_from_time = self.from_time
        original_to_time = self.to_time

        self.db_set({"scheduled_on": scheduled_on, "from_time": from_time, "to_time": to_time})
        self.notify_update()

        recipients = get_recipients(self.name)

        # Get Applicant Name
        applicant_name = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name") or "Candidate"

        message = (
            "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>"
            "<div style='background: #1B4F8A; padding: 25px; text-align: center;'>"
            "<h2 style='color: white; margin: 0; font-size: 22px;'>Interview Rescheduled</h2>"
            "<p style='color: #cce0ff; margin: 5px 0 0 0; font-size: 14px;'>Please note the updated timings</p>"
            "</div>"
            "<div style='padding: 30px; background: #fdfdfd;'>"
            "<p style='font-size: 15px; color: #333; margin-top: 0;'>Hello <b>" + applicant_name + "</b>,</p>"
            "<p style='font-size: 15px; color: #555; line-height: 1.5;'>Your interview session has been rescheduled. Please review the updated schedule below.</p>"
            "<div style='background: #f4f7f6; border-left: 4px solid #1B4F8A; padding: 15px; margin: 25px 0;'>"
            "<p style='margin: 5px 0; font-size: 14px;'><strong>Interview ID:</strong> " + self.name + "</p>"
            "<p style='margin: 5px 0; font-size: 14px;'><strong>Interview Type:</strong> " + (self.interview_type or "") + "</p>"
            "<p style='margin: 5px 0; font-size: 14px;'><strong>Location / Link:</strong> " + (self.custom_interview_location or "TBD") + "</p>"
            "<p style='margin: 15px 0 5px 0; font-size: 14px; color:#555;'><s>Old Date: " + str(original_date) + " (" + str(original_from_time) + " to " + str(original_to_time) + ")</s></p>"
            "<p style='margin: 5px 0; font-size: 14px; font-weight: bold; color: #1B4F8A;'>New Date: " + str(self.scheduled_on) + "</p>"
            "<p style='margin: 5px 0; font-size: 14px; font-weight: bold; color: #1B4F8A;'>New Time: " + str(self.from_time) + " to " + str(self.to_time) + "</p>"
            "</div>"
            "<p style='font-size: 14px; color: #555;'>Please ensure you are available and prepared at the new specified time.</p>"
            "<div style='margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;'>"
            "<p style='font-size: 14px; color: #333; margin: 0;'>Warm Regards,</p>"
            "<p style='font-size: 14px; color: #333; font-weight: bold; margin: 5px 0 0 0;'>HR Team</p>"
            "</div>"
            "</div>"
            "<div style='background: #1B4F8A; padding: 12px; text-align: center;'>"
            "<p style='color: #cce0ff; margin: 0; font-size: 12px;'>HRMS \u2014 Confidential</p>"
            "</div>"
            "</div>"
        )

        try:
            frappe.sendmail(
                recipients=recipients,
                subject=_("Interview Rescheduled: {0}").format(self.name),
                message=message,
                reference_doctype=self.doctype,
                reference_name=self.name,
            )
        except Exception:
            frappe.msgprint(
                _(
                    "Failed to send the Interview Reschedule notification. Please configure your email account."
                )
            )

        frappe.msgprint(_("Interview Rescheduled successfully"), indicator="green")
