import frappe
from frappe import _

from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

ALLOWED_SITE = "mysite.local"


def sync_pending_leave_approver(dry_run: bool = True) -> dict:
	"""Sync leave_approver on open draft Leave Applications on mysite.local only.

	Defaults to dry_run=True. When dry_run=False, suppresses Frappe notifications
	and outgoing emails via frappe.flags.in_import, frappe.flags.mute_emails, and
	frappe.flags.mute_messages before calling doc.save().
	"""
	site = getattr(frappe.local, "site", None)
	if site != ALLOWED_SITE:
		frappe.throw(
			_("sync_pending_leave_approver is restricted to {0} (current site: {1}).").format(
				ALLOWED_SITE, site
			)
		)

	pending_rows = frappe.get_all(
		"Leave Application",
		filters={"docstatus": 0, "status": "Open"},
		fields=["name", "employee", "leave_approver"],
		order_by="name asc",
	)

	approver_by_employee = {}
	changes = []
	for row in pending_rows:
		if not row.employee:
			continue
		if row.employee not in approver_by_employee:
			approver_by_employee[row.employee] = get_employee_leave_approver(row.employee)
		expected_approver = approver_by_employee[row.employee]
		if expected_approver and row.leave_approver != expected_approver:
			changes.append(
				{
					"name": row.name,
					"employee": row.employee,
					"old_approver": row.leave_approver,
					"new_approver": expected_approver,
				}
			)

	if dry_run or not changes:
		return {
			"site": site,
			"dry_run": bool(dry_run),
			"checked": len(pending_rows),
			"mismatched": len(changes),
			"updated": 0,
			"changes": changes,
		}

	prev_in_import = frappe.flags.in_import
	prev_mute_emails = frappe.flags.mute_emails
	prev_mute_messages = frappe.flags.mute_messages
	updated = 0
	try:
		frappe.flags.in_import = True
		frappe.flags.mute_emails = True
		frappe.flags.mute_messages = True

		for item in changes:
			doc = frappe.get_doc("Leave Application", item["name"])
			doc.leave_approver = item["new_approver"]
			doc.save(ignore_permissions=True)
			updated += 1
	finally:
		frappe.flags.in_import = prev_in_import
		frappe.flags.mute_emails = prev_mute_emails
		frappe.flags.mute_messages = prev_mute_messages

	return {
		"site": site,
		"dry_run": False,
		"checked": len(pending_rows),
		"mismatched": len(changes),
		"updated": updated,
		"changes": changes,
	}
