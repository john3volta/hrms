import datetime

import frappe
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import getdate, nowdate


class InactiveEmployeeStatusError(frappe.ValidationError):
	pass


class AccountsController(Document):
	def get_gl_dict(self, args, item=None):
		return frappe._dict(args)


class PaymentEntry(Document):
	pass


class Project(Document):
	pass


class Timesheet(Document):
	pass


class TransactionBase(Document):
	pass


def allow_regional(fn):
	return fn


def get_holiday_list_for_employee(employee, raise_exception=True, **kwargs):
	from hrms.utils.holiday_list import get_holiday_list_for_employee as _get
	return _get(employee, raise_exception=raise_exception, **kwargs)


def is_holiday(holiday_list, date=None, **kwargs):
	return False


def is_half_holiday(holiday_list, date=None, **kwargs):
	return False


def get_employee_email(employee):
	return frappe.db.get_value("Employee", employee, "user_id") or frappe.db.get_value(
		"Employee", employee, "personal_email"
	)


def get_employee_emails(employee_list):
	return []


def get_all_employee_emails(company):
	return []


def get_default_company():
	return frappe.defaults.get_global_default("company")


def get_company_currency(company=None):
	company = company or get_default_company()
	return frappe.db.get_value("Company", company, "default_currency")


def get_default_cost_center(company=None):
	company = company or get_default_company()
	return frappe.db.get_value("Company", company, "cost_center")


def get_region(company=None):
	company = company or get_default_company()
	return frappe.db.get_value("Company", company, "country") or ""


def make_gl_entries(*args, **kwargs):
	return None


def get_fiscal_year(date=None, company=None, as_dict=False, **kwargs):
	current_date = getdate(date) if date else getdate()
	year_start = datetime.date(current_date.year, 1, 1)
	year_end = datetime.date(current_date.year, 12, 31)
	if as_dict:
		return frappe._dict(
			name=str(current_date.year), year_start_date=year_start, year_end_date=year_end
		)
	return str(current_date.year), year_start, year_end


def get_account_currency(account):
	return frappe.db.get_value("Account", account, "account_currency")


def get_exchange_rate(*args, **kwargs):
	return 1


def get_bank_cash_account(*args, **kwargs):
	return frappe._dict(account=None, account_currency=None)


def get_default_bank_cash_account(*args, **kwargs):
	return None


def get_reference_details(*args, **kwargs):
	return {}


def validate_docs_for_voucher_types(*args, **kwargs):
	return None


def create_gain_loss_journal(*args, **kwargs):
	return None


def unlink_ref_doc_from_payment_entries(*args, **kwargs):
	return None


def update_reference_in_payment_entry(*args, **kwargs):
	return None


def repost_accounting_ledger(*args, **kwargs):
	return None


def get_accounting_dimensions(*args, **kwargs):
	return []


def build_qb_match_conditions(*args, **kwargs):
	return Criterion.all()


def daterange(start, end):
	current = start
	while current <= end:
		yield current
		current += datetime.timedelta(days=1)


def validate_status(*args, **kwargs):
	return None


def get_period_list(*args, **kwargs):
	return []


def validate_employee_role(*args, **kwargs):
	return None


def set_by_naming_series(*args, **kwargs):
	return None


def get_abbreviated_name(name, company=None):
	return name


def create_designation(name):
	if frappe.db.exists("Designation", name):
		return name
	doc = frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert()
	return doc.name


def enable_all_roles_and_domains():
	return None
