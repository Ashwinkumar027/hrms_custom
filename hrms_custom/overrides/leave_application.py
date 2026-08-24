import frappe
from frappe import _
from frappe.utils import cint, get_fullname

from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


class CustomLeaveApplication(LeaveApplication):
	def notify(self, args):
		args = frappe._dict(args)
		# args -> message, message_to, subject
		if cint(self.follow_via_email):
			contact = args.message_to
			if not isinstance(contact, list):
				if not args.notify == "employee":
					contact = frappe.get_doc("User", contact).email or contact

			sender = dict()
			sender["email"] = (
				frappe.db.get_single_value("HR Settings", "sender_email")
				or frappe.get_doc("User", frappe.session.user).email
			)
			sender["full_name"] = get_fullname(sender["email"])

			try:
				frappe.sendmail(
					recipients=contact,
					sender=sender["email"],
					subject=args.subject,
					message=args.message,
				)
				frappe.msgprint(_("Email sent to {0}").format(contact))
			except frappe.OutgoingEmailError:
				pass

	def before_cancel(self):
		if self.status == "Approved":
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user == frappe.session.user and frappe.session.user != "Administrator":
				frappe.throw(_("You cannot cancel your own approved Leave Application. Please contact your approver or HR."))
		super().before_cancel()

	def validate(self):
		super().validate()
		self._validate_self_approval_hardening()

	def _validate_self_approval_hardening(self):
		if self.status == "Approved":
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user == frappe.session.user and frappe.session.user != "Administrator":
				frappe.throw(_("Self-approval for leaves is not allowed"))
