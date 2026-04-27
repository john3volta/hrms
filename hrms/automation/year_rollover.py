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

	from hrms.setup import _get_or_create_default_leave_policy

	policy_name = _get_or_create_default_leave_policy()
	target_from = getdate(from_date)
	target_to = getdate(to_date)
	employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	for employee in employees:
		try:
			# Fetch any submitted LPA that overlaps the target range
			overlapping = frappe.db.sql(
				"""
                SELECT name, effective_from, effective_to
                FROM `tabLeave Policy Assignment`
                WHERE employee = %s AND docstatus = 1
                  AND effective_from <= %s AND effective_to >= %s
                LIMIT 1
                """,
				(employee, to_date, from_date),
				as_dict=True,
			)
			if overlapping:
				existing_to = getdate(overlapping[0]["effective_to"])
				# Full coverage — skip entirely
				if getdate(overlapping[0]["effective_from"]) <= target_from and existing_to >= target_to:
					continue
				# Partial coverage — create follow-on LPA for uncovered remainder
				remainder_from = existing_to + frappe.utils.datetime.timedelta(days=1)
				if remainder_from > target_to:
					continue
				lpa = frappe.get_doc(
					{
						"doctype": "Leave Policy Assignment",
						"employee": employee,
						"leave_policy": policy_name,
						"assignment_based_on": "Leave Period",
						"leave_period": leave_period,
						"effective_from": remainder_from,
					}
				)
			else:
				lpa = frappe.get_doc(
					{
						"doctype": "Leave Policy Assignment",
						"employee": employee,
						"leave_policy": policy_name,
						"assignment_based_on": "Leave Period",
						"leave_period": leave_period,
						"effective_from": from_date,
					}
				)
			lpa.insert(ignore_permissions=True)
			lpa.submit()
		except frappe.ValidationError:
			frappe.log_error(frappe.get_traceback(), f"Year Rollover: employee={employee}, year={year}")
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Year Rollover: employee={employee}, year={year}")
			raise
