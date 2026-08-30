"""Workaround for a frappe core bug that crashes Document.insert() for any
user with User.follow_created_documents = 1, whenever that insert (directly
or as a side effect, e.g. a notification created in after_insert) creates a
document of a doctype with naming_rule = "Autoincrement" (PWA Notification,
HD Ticket, and others).

Root cause (confirmed against frappe 16.29.0 / hrms 16.4.8, the versions
running in production; NOT reproducible on frappe 16.10.7, where
follow_document has no type annotations at all):

    frappe/model/document.py:519, inside Document.insert():
        if frappe.get_cached_value("User", frappe.session.user, "follow_created_documents"):
            follow_document(self.doctype, self.name, frappe.session.user)

    follow_document is imported at module level in document.py
    (`from frappe.desk.form.document_follow import follow_document`), and is
    annotated in frappe 16.29.0:

        frappe/desk/form/document_follow.py:
            @frappe.whitelist()
            def follow_document(doctype: str, doc_name: str, user: str):

    For an autoincrement-named doctype, self.name is an int. Frappe's runtime
    argument-type validation (frappe/utils/typing_validations.py,
    transform_parameter_types) runs pydantic against every annotated
    parameter of a whitelisted function on every call, including plain
    in-process calls (guarded by the whitelist decorator's
    validate_argument_types wrapper, not just HTTP dispatch). pydantic 2.x
    does not coerce int -> str, so validating the int doc_name against the
    `str` annotation raises pydantic.ValidationError, which frappe converts
    to frappe.exceptions.FrappeTypeError. That exception propagates out of
    the follow_document call, out of Document.insert(), and rolls back the
    entire enclosing transaction -- e.g. an entire Leave Application vanishes
    because its after_insert hook created a PWA Notification, whose own
    insert() then tried (and failed) to follow itself.

    Unannotated functions are exempt: transform_parameter_types bails out
    immediately when func.__annotations__ is empty, before pydantic is ever
    invoked. That's the basis of the fix below -- replace follow_document
    with an equivalent, unannotated wrapper that coerces doc_name to str
    itself before delegating to the original.

Because `from frappe.desk.form.document_follow import follow_document` in
frappe/model/document.py binds a name in that module's own namespace at
import time (not a live alias back to
frappe.desk.form.document_follow.follow_document), patching only the source
module does not change what Document.insert() actually calls. Both bindings
must be rebound for the fix to take effect at the real call site.

Verified on an isolated frappe 16.29.0 / hrms 16.4.8 environment (its own
MariaDB and Redis instances, no shared state with any other bench): with
this patch absent, inserting an autoincrement-named doctype (PWA
Notification) as a user with follow_created_documents = 1 raised the exact
FrappeTypeError above. Under identical conditions, applying the patch
resolved it -- the insert succeeded with a real int doc name, and
follow_document/model.document's bound references, idempotency, and
whitelisting all held as designed.

DELETE THIS PATCH once frappe fixes the call site upstream -- either by
casting str(self.name) at frappe/model/document.py:519, or by relaxing the
`doc_name: str` annotation on follow_document (e.g. to `int | str`). As of
this writing frappe/develop still has the annotated signature, so there is no
fixed version to upgrade to yet.
"""

_applied = False


def apply():
	"""Idempotently monkey-patch follow_document to accept a non-str doc_name.

	Safe to call repeatedly and from multiple entry points (before_request,
	before_job) -- guarded by the module-level _applied flag so the function
	is only ever wrapped once per process.
	"""
	global _applied
	if _applied:
		return

	import frappe
	import frappe.desk.form.document_follow as document_follow_module
	import frappe.model.document as document_module

	original_follow_document = document_follow_module.follow_document

	# Deliberately no type annotations here -- annotating this wrapper would
	# re-trigger frappe's pydantic-based runtime validation on the very
	# argument we're trying to let through unvalidated.
	@frappe.whitelist()
	def follow_document(doctype, doc_name, user):
		return original_follow_document(doctype, str(doc_name), user)

	document_follow_module.follow_document = follow_document
	document_module.follow_document = follow_document

	_applied = True
