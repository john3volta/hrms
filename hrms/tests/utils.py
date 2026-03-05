import frappe
from frappe.utils import getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class HRMSTestSuite(ERPNextTestSuite):
	"""Class for creating HRMS test records"""

	@classmethod
	def setUpClass(cls):
		if not hasattr(cls, "globalTestRecords"):
			cls.globalTestRecords = {}

		if not hasattr(cls, "bootstrap_testsite"):
			cls.bootstrap_testsite = False

		if not cls.bootstrap_testsite:
			super().make_presets()
			cls.make_persistent_master_data()
			cls.bootstrap_testsite = True

	@classmethod
	def make_persistent_master_data(cls):
		super().make_fiscal_year()
		super().make_role()
		super().make_user()
		cls.make_company()
		cls.make_holiday_list_assignment()
		super().make_department()
		cls.make_employees()
		cls.update_system_settings()
		cls.update_email_account_settings()
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
	def make_department(cls):
		"""Create test departments"""
		# Create test departments here
		super().make_department()

	@classmethod
	def make_employees(cls):
		"""Create test employees"""
		# Create test employees here
		super().make_employees()

	@classmethod
	def make_holiday_list_assignment(cls):
		cls.make_holiday_list()
		records = [
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Company",
				"assigned_to": cls.companies[0].name,
				"holiday_list": cls.holiday_list[0].name,
				"from_date": cls.holiday_list[0].from_date,
				"to_date": cls.holiday_list[0].to_date,
			}
		]
		cls.make_records(["assigned_to", "from_date"], records, "holiday_list_assignment")

	@classmethod
	def make_holiday_list(cls):
		fiscal_year = get_fiscal_year(getdate())
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"from_date": fiscal_year[1],
				"to_date": fiscal_year[2],
				"holiday_list_name": "Salary Slip Test Holiday List",
			}
		).insert()
		holiday_list.weekly_off = "Sunday"
		holiday_list.save()
		cls.holiday_list = []
		cls.holiday_list.append(holiday_list)

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
	def update_system_settings(cls):
		system_settings = frappe.get_doc("System Settings")
		system_settings.time_zone = "Asia/Kolkata"
		system_settings.language = "en"
		system_settings.currency_precision = system_settings.float_precision = 3
		system_settings.save()

	@classmethod
	def update_email_account_settings(cls):
		email_account = frappe.get_doc("Email Account", "Jobs")
		email_account.enable_outgoing = 1
		email_account.default_outgoing = 1
		email_account.save()

	@classmethod
	def make_records(cls, key, records, attr):
		super().make_records(key, records, attr)

	def tearDown(self):
		frappe.db.rollback()
