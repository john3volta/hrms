import frappe
from frappe.utils import getdate


def execute():
	from hrms.setup import (
		create_default_holiday_list,
		create_default_hr_organization,
		create_default_leave_period,
		create_default_leave_policy,
		create_default_payroll_period,
		create_default_salary_components,
		create_default_salary_structure,
	)

	create_default_hr_organization()
	create_default_holiday_list()
	create_default_leave_period()
	create_default_leave_policy()
	create_default_salary_components()
	create_default_salary_structure()
	create_default_payroll_period()

	_assign_lpa_ssa_for_active_employees()


def _assign_lpa_ssa_for_active_employees():
	employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	for employee in employees:
		_ensure_lpa(employee)
		_ensure_ssa(employee)


def _ensure_lpa(employee):
	try:
		from frappe.utils import now_datetime

		from hrms.setup import _get_or_create_default_leave_policy

		date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
		if not date_of_joining:
			return
		joining_date = getdate(date_of_joining)

		year = now_datetime().year
		year_start = getdate(f"{year}-01-01")
		year_end = getdate(f"{year}-12-31")

		existing = frappe.db.sql(
			"""
            SELECT name FROM `tabLeave Policy Assignment`
            WHERE employee = %s
              AND docstatus = 1
              AND effective_from <= %s
              AND (effective_to IS NULL OR effective_to >= %s)
            LIMIT 1
            """,
			(employee, joining_date, joining_date),
		)
		if existing:
			return

		policy_name = _get_or_create_default_leave_policy()

		if joining_date >= year_start:
			# New employee this year — assign from joining date
			lpa = frappe.get_doc(
				{
					"doctype": "Leave Policy Assignment",
					"employee": employee,
					"leave_policy": policy_name,
					"assignment_based_on": "Joining Date",
					"effective_from": joining_date,
				}
			)
		else:
			# Long-tenured employee — assign current calendar year leave period
			leave_period = frappe.db.get_value(
				"Leave Period",
				{"hr_organization": "HO", "from_date": str(year_start), "to_date": str(year_end)},
				"name",
			)
			lpa = frappe.get_doc(
				{
					"doctype": "Leave Policy Assignment",
					"employee": employee,
					"leave_policy": policy_name,
					"assignment_based_on": "Leave Period",
					"leave_period": leave_period,
					"effective_from": year_start,
				}
			)

		lpa.insert(ignore_permissions=True)
		lpa.submit()
	except frappe.ValidationError:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap: employee={employee}")
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap: employee={employee}")
		raise


def _ensure_ssa(employee):
	try:
		date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
		if not date_of_joining:
			return
		joining_date = getdate(date_of_joining)
		existing = frappe.db.sql(
			"""
            SELECT name FROM `tabSalary Structure Assignment`
            WHERE employee = %s
              AND docstatus = 1
              AND from_date <= %s
            LIMIT 1
            """,
			(employee, joining_date),
		)
		if existing:
			return
		ssa = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": employee,
				"salary_structure": "Default Structure",
				"from_date": joining_date,
				"hr_organization": "HO",
			}
		)
		ssa.insert(ignore_permissions=True)
		ssa.submit()
	except frappe.ValidationError:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap SSA: employee={employee}")
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap SSA: employee={employee}")
		raise
