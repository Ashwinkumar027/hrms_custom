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

	def on_update(self):
		super().on_update()
		self._auto_submit_after_decision()

	def _auto_submit_after_decision(self):
		"""The PWA's RequestActionSheet.vue sets status and docstatus in two
		separate requests (Approve/Reject, then a follow-up Submit), so a
		decision alone always used to leave the record at docstatus=0 --
		easy to forget the second step (this is what left HR-LAP-2026-00009/
		00011 stuck Approved but never submitted). validate()'s self-approval
		checks above already ran earlier in this same save and would have
		thrown before we ever get here, so calling submit() here can't bypass
		them -- it only finalizes a decision that already passed validation.

		Gated on the current user actually holding submit rights: on_update()
		fires on every save of an already-decided record, including edits
		that have nothing to do with the decision itself (a remark, an
		attachment). Without this check, self.submit() would throw
		PermissionError for a write-but-not-submit editor and break that
		unrelated edit entirely. Deliberately not ignore_permissions=True --
		that would auto-submit under anyone's edit regardless of whether
		submitting is appropriate for their role. If the editor lacks submit
		rights, skip silently and leave docstatus as it was; a submit-eligible
		user's later save still finalizes it."""
		if self.docstatus == 0 and self.status in ("Approved", "Rejected"):
			if frappe.has_permission(doc=self, ptype="submit"):
				self.submit()
