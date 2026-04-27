import frappe
from frappe.utils import getdate


def run_year_rollover():
	from frappe.utils import now_datetime

	year = now_datetime().year
	_create_leave_period(year)
	_create_payroll_period(year)
	_create_holiday_list(year)
	_create_lpa_for_active_employees(year)


def _create_leave_period(year):
	from_date, to_date = f"{year}-01-01", f"{year}-12-31"
	if frappe.db.exists(
		"Leave Period", {"hr_organization": "HO", "from_date": from_date, "to_date": to_date}
	):
		return
	frappe.get_doc(
		{
			"doctype": "Leave Period",
			"hr_organization": "HO",
			"from_date": from_date,
			"to_date": to_date,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


def _create_payroll_period(year):
	start_date, end_date = f"{year}-01-01", f"{year}-12-31"
	if frappe.db.exists(
		"Payroll Period",
		{"hr_organization": "HO", "start_date": start_date, "end_date": end_date},
	):
		return
	frappe.get_doc(
		{
			"doctype": "Payroll Period",
			"hr_organization": "HO",
			"start_date": start_date,
			"end_date": end_date,
		}
	).insert(ignore_permissions=True)


def _create_holiday_list(year):
	name = f"Default Holidays {year}"
	if frappe.db.exists("Holiday List", name):
		return
	frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": f"{year}-01-01",
			"to_date": f"{year}-12-31",
			"holidays": [],
		}
	).insert(ignore_permissions=True)


def _create_lpa_for_active_employees(year):
	from_date, to_date = f"{year}-01-01", f"{year}-12-31"
	leave_period = frappe.db.get_value(
		"Leave Period",
		{"hr_organization": "HO", "from_date": from_date, "to_date": to_date},
		"name",
	)
	if not leave_period:
		return

	employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	for employee in employees:
		try:
			overlapping = frappe.db.sql(
				"""
                SELECT name FROM `tabLeave Policy Assignment`
                WHERE employee = %s AND docstatus = 1
                  AND effective_from <= %s AND effective_to >= %s
                LIMIT 1
                """,
				(employee, to_date, from_date),
			)
			if overlapping:
				continue

			lpa = frappe.get_doc(
				{
					"doctype": "Leave Policy Assignment",
					"employee": employee,
					"leave_policy": "Standard Policy",
					"assignment_based_on": "Leave Period",
					"leave_period": leave_period,
					"effective_from": from_date,
				}
			)
			lpa.insert(ignore_permissions=True)
			lpa.submit()
		except Exception as e:
			frappe.log_error(f"Year rollover LPA failed for {employee}: {e}", "Year Rollover")
