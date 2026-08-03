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
