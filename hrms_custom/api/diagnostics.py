"""Temporary diagnostic endpoint for verifying the follow_document patch
(hrms_custom.monkey_patches) is actually active in a deployed environment.

Needed because System Console's RestrictedPython sandbox blocks import and
dunder attribute access, so this can't be checked from Desk directly.

Delete this file and its re-export in hrms_custom/api/__init__.py once the
patch itself (hrms_custom/monkey_patches.py) is no longer needed -- see that
file's docstring for the upstream condition that makes it removable.
"""

import frappe


@frappe.whitelist()
def check_patch_status():
	import frappe.desk.form.document_follow as m
	import frappe.model.document as d

	return {
		"document_follow_annotations": str(m.follow_document.__annotations__),
		"document_py_annotations": str(d.follow_document.__annotations__),
		"same_object": m.follow_document is d.follow_document,
		"is_whitelisted": m.follow_document in frappe.whitelisted,
	}
