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
		date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
		if not date_of_joining:
			return
		joining_date = getdate(date_of_joining)
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
		lpa = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": employee,
				"leave_policy": "Standard Policy",
				"assignment_based_on": "Joining Date",
				"effective_from": joining_date,
			}
		)
		lpa.insert(ignore_permissions=True)
		lpa.submit()
	except frappe.ValidationError:
		frappe.log_error(
			title="Bootstrap LPA failed",
			message=f"Employee: {employee}\n{frappe.get_traceback()}",
		)


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
		frappe.log_error(
			title="Bootstrap SSA failed",
			message=f"Employee: {employee}\n{frappe.get_traceback()}",
		)
