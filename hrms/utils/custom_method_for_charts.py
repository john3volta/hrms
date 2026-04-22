import frappe
from frappe.utils import get_first_day, get_last_day, getdate

from hrms.utils.compat import get_holiday_list_for_employee

from hrms.utils.holiday_list import get_assigned_holiday_list


@frappe.whitelist()
def get_upcoming_holidays():
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if employee:
		holiday_list = get_holiday_list_for_employee(employee, raise_exception=False, as_on=getdate())
	else:
		first_org = frappe.db.get_value("HR Organization", {}, "name")
		holiday_list = get_assigned_holiday_list(first_org, as_on=getdate()) if first_org else None

	if not holiday_list:
		return 0

	month_start = get_first_day(getdate())
	month_end = get_last_day(getdate())

	holidays = frappe.db.get_all(
		"Holiday", {"parent": holiday_list, "holiday_date": ("between", (month_start, month_end))}
	)

	return len(holidays)
