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
	from_date = f"{year}-01-01"
	if not frappe.db.exists("Holiday List", name):
		frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": name,
				"from_date": from_date,
				"to_date": f"{year}-12-31",
				"holidays": [],
			}
		).insert(ignore_permissions=True)

	# Always ensure HLA and default_holiday_list are up-to-date
	if not frappe.db.exists(
		"Holiday List Assignment",
		{"applicable_for": "HR Organization", "assigned_to": "HO", "holiday_list": name},
	):
		hla = frappe.get_doc(
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "HR Organization",
				"assigned_to": "HO",
				"holiday_list": name,
				"from_date": from_date,
			}
		)
		hla.insert(ignore_permissions=True)
		frappe.flags.ignore_permissions = True
		try:
			hla.submit()
		finally:
			frappe.flags.ignore_permissions = False

	if frappe.db.exists("HR Organization", "HO"):
		frappe.db.set_value("HR Organization", "HO", "default_holiday_list", name)


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
			# Skip only when existing LPA covers the FULL target range.
			# TODO Phase 8: partial LPA coverage for mid-year hires — set_dates() on
			# LeavePolicyAssignment.validate() overwrites effective_from/effective_to with
			# Leave Period dates, making follow-on LPAs impossible without cancel/recreate.
			covers_full_year = frappe.db.exists(
				"Leave Policy Assignment",
				{
					"employee": employee,
					"docstatus": 1,
					"effective_from": ["<=", target_from],
					"effective_to": [">=", target_to],
				},
			)
			if covers_full_year:
				continue

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
