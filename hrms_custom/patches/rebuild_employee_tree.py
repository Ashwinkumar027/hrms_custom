from hrms_custom.employee_tree import repair_if_broken


def execute():
	"""Idempotently repair the Employee nested-set tree if any corruption exists."""
	repair_if_broken()
