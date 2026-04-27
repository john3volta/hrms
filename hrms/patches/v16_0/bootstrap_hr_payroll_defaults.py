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
		policy_name = _get_or_create_default_leave_policy()

		if joining_date < year_start:
			# Pre-existing employee: check full-year coverage for current year
			covers_full_year = frappe.db.exists(
				"Leave Policy Assignment",
				{
					"employee": employee,
					"docstatus": 1,
					"effective_from": ["<=", year_start],
					"effective_to": [">=", year_end],
				},
			)
			if covers_full_year:
				return
			hr_org = frappe.db.get_default("hr_organization") or "HO"
			leave_period = frappe.db.get_value(
				"Leave Period",
				{"hr_organization": hr_org, "from_date": str(year_start), "to_date": str(year_end)},
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
					"effective_to": year_end,
				}
			)
		else:
			# Current-year hire: check coverage from joining date
			existing = frappe.db.exists(
				"Leave Policy Assignment",
				{
					"employee": employee,
					"docstatus": 1,
					"effective_from": ["<=", joining_date],
					"effective_to": [">=", joining_date],
				},
			)
			if existing:
				return
			lpa = frappe.get_doc(
				{
					"doctype": "Leave Policy Assignment",
					"employee": employee,
					"leave_policy": policy_name,
					"assignment_based_on": "Joining Date",
					"effective_from": joining_date,
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
