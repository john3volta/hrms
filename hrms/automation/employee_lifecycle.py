import frappe
from frappe.utils import getdate


def on_employee_after_insert(doc, method):
	if doc.status != "Active":
		return

	_ensure_leave_policy_assignment(doc)
	_ensure_salary_structure_assignment(doc)


def _ensure_leave_policy_assignment(doc):
	try:
		from hrms.setup import _get_or_create_default_leave_policy

		joining_date = getdate(doc.date_of_joining)
		existing = frappe.db.sql(
			"""
            SELECT name FROM `tabLeave Policy Assignment`
            WHERE employee = %s
              AND docstatus = 1
              AND effective_from <= %s
              AND (effective_to IS NULL OR effective_to >= %s)
            LIMIT 1
            """,
			(doc.name, joining_date, joining_date),
		)
		if existing:
			return

		policy_name = _get_or_create_default_leave_policy()
		lpa = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": doc.name,
				"leave_policy": policy_name,
				"assignment_based_on": "Joining Date",
				"effective_from": joining_date,
			}
		)
		lpa.insert(ignore_permissions=True)
		lpa.submit()
	except frappe.ValidationError:
		frappe.log_error(frappe.get_traceback(), f"Employee Bootstrap: LPA employee={doc.name}")
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Employee Bootstrap: LPA employee={doc.name}")
		raise


def _ensure_salary_structure_assignment(doc):
	try:
		joining_date = getdate(doc.date_of_joining)
		existing = frappe.db.sql(
			"""
            SELECT name FROM `tabSalary Structure Assignment`
            WHERE employee = %s
              AND docstatus = 1
              AND from_date <= %s
            LIMIT 1
            """,
			(doc.name, joining_date),
		)
		if existing:
			return

		ssa = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": doc.name,
				"salary_structure": "Default Structure",
				"from_date": joining_date,
				"hr_organization": "HO",
			}
		)
		ssa.insert(ignore_permissions=True)
		ssa.submit()
	except frappe.ValidationError:
		frappe.log_error(frappe.get_traceback(), f"Employee Bootstrap: SSA employee={doc.name}")
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Employee Bootstrap: SSA employee={doc.name}")
		raise
