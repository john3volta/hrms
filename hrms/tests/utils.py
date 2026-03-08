import frappe
from frappe.utils import getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class HRMSTestSuite(ERPNextTestSuite):
	"""Class for creating HRMS test records"""

	@classmethod
	def setUpClass(cls):
		cls.make_presets()
		cls.make_persistent_master_data()

	@classmethod
	def make_presets(cls):
		cls.make_designations()

	@classmethod
	def make_designations(cls):
		designations = [
			"Engineer",
			"Project Manager",
			"Researcher",
			"Accountant",
			"Manager",
			"Software Developer",
			"UX Designer",
			"Designer",
		]
		records = [{"doctype": "Designation", "designation_name": x} for x in designations]
		cls.make_records(["designation_name"], records, "designations")

	@classmethod
	def make_persistent_master_data(cls):
		cls.make_company()
		cls.make_holiday_list()
		cls.make_holiday_list_assignment()
		cls.make_leave_types()
		cls.make_leave_allocations()
		cls.update_email_account_settings()
		# TODO: clean up
		if frappe.db.get_value("Holiday List Assignment", {"assigned_to": "_Test Company"}, "docstatus") == 0:
			frappe.get_doc("Holiday List Assignment", {"assigned_to": "_Test Company"}).submit()
		frappe.db.commit()

	@classmethod
	def make_company(cls):
		records = [
			{
				"abbr": "_TC",
				"company_name": "_Test Company",
				"country": "India",
				"default_currency": "INR",
				"doctype": "Company",
				"chart_of_accounts": "Standard",
			}
		]
		cls.make_records(["company_name"], records, "companies")

	@classmethod
	def make_holiday_list_assignment(cls):
		fiscal_year = get_fiscal_year(getdate())
		records = [
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Company",
				"assigned_to": "_Test Company",
				"holiday_list": "Salary Slip Test Holiday List",
				"from_date": fiscal_year[1],
				"to_date": fiscal_year[2],
			}
		]
		cls.make_records(["assigned_to", "from_date"], records, "holiday_list_assignment")

	@classmethod
	def make_holiday_list(cls):
		fiscal_year = get_fiscal_year(getdate())
		records = [
			{
				"doctype": "Holiday List",
				"from_date": fiscal_year[1],
				"to_date": fiscal_year[2],
				"holiday_list_name": "Salary Slip Test Holiday List",
				"weekly_off": "Sunday",
			}
		]
		cls.make_records(["from_date", "to_date", "holiday_list_name"], records, "holiday_list")

	@classmethod
	def make_leave_types(cls):
		"""Create test leave types"""
		# Create test leave types here
		records = [
			{"doctype": "Leave Type", "leave_type_name": "_Test Leave Type", "include_holiday": 1},
			{
				"doctype": "Leave Type",
				"is_lwp": 1,
				"leave_type_name": "_Test Leave Type LWP",
				"include_holiday": 1,
			},
			{
				"doctype": "Leave Type",
				"leave_type_name": "_Test Leave Type Encashment",
				"include_holiday": 1,
				"allow_encashment": 1,
				"non_encashable_leaves": 5,
				"earning_component": "Leave Encashment",
			},
			{
				"doctype": "Leave Type",
				"leave_type_name": "_Test Leave Type Earned",
				"include_holiday": 1,
				"is_earned_leave": 1,
			},
		]
		cls.leave_types = []
		cls.make_records(["leave_type_name"], records, "leave_types")

	@classmethod
	def make_leave_allocations(cls):
		"""Create test leave applications"""
		# Create test leave applications here
		records = [
			{
				"docstatus": 1,
				"doctype": "Leave Allocation",
				"employee": "_T-Employee-00001",
				"from_date": "2013-01-01",
				"to_date": "2013-12-31",
				"leave_type": "_Test Leave Type",
				"new_leaves_allocated": 15,
			},
			{
				"docstatus": 1,
				"doctype": "Leave Allocation",
				"employee": "_T-Employee-00002",
				"from_date": "2013-01-01",
				"to_date": "2013-12-31",
				"leave_type": "_Test Leave Type",
				"new_leaves_allocated": 15,
			},
		]
		cls.make_records(["employee", "from_date", "to_date"], records, "leave_allocations")

	@classmethod
	def update_email_account_settings(cls):
		email_account = frappe.get_doc("Email Account", "Jobs")
		email_account.enable_outgoing = 1
		email_account.default_outgoing = 1
		email_account.save()

	@classmethod
	def make_records(self, key, records, attr):
		doctype = records[0].get("doctype")

		def get_filters(record):
			filters = {}
			for x in key:
				filters[x] = record.get(x)
			return filters

		for x in records:
			filters = get_filters(x)
			if not frappe.db.exists(doctype, filters):
				doc = frappe.get_doc(x).insert()
				if doctype == "Holiday List":
					doc.get_weekly_off_dates()
					doc.save()

	def tearDown(self):
		frappe.db.rollback()
