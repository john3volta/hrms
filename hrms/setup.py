import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.install_fixtures import (
	_,  # NOTE: this is not the real translation function
)
from frappe.desk.page.setup_wizard.setup_wizard import make_records


def after_install():
	custom_fields = get_custom_fields()
	existing_doctypes = frappe.get_list("DocType", pluck="name")
	filtered = {dt: fields for dt, fields in custom_fields.items() if dt in existing_doctypes}
	if filtered:
		create_custom_fields(filtered, ignore_validate=True)
	create_salary_slip_loan_fields()
	make_fixtures()
	setup_notifications()
	update_hr_defaults()
	set_single_defaults()
	create_default_role_profiles()
	run_post_install_patches()
	create_default_hr_organization()
	create_default_holiday_list()
	create_default_leave_period()
	create_default_leave_policy()
	create_default_salary_components()
	create_default_salary_structure()
	# Payroll Period managed manually via ERPel admin (12 monthly cycles, not annual).


def before_uninstall():
	delete_custom_fields(get_custom_fields())
	delete_custom_fields(get_salary_slip_loan_fields())


def after_app_install(app_name):
	"""Set up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	custom_fields = get_salary_slip_loan_fields()
	existing_doctypes = frappe.get_list("DocType", pluck="name")
	filtered = {dt: fields for dt, fields in custom_fields.items() if dt in existing_doctypes}
	if filtered:
		create_custom_fields(filtered, ignore_validate=True)
	add_lending_docperms_to_ess()


def before_app_uninstall(app_name):
	"""Clean up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	delete_custom_fields(get_salary_slip_loan_fields())
	remove_lending_docperms_from_ess()


def get_custom_fields():
	"""HR specific custom fields that need to be added to the masters in ERPNext"""
	return {
		"Department": [
			{
				"description": _("Days for which Holidays are blocked for this department."),
				"fieldname": "leave_block_list",
				"fieldtype": "Link",
				"in_list_view": 1,
				"label": _("Leave Block List"),
				"options": "Leave Block List",
				"insert_after": "disabled",
			},
			{
				"description": _("The first Approver in the list will be set as the default Approver."),
				"fieldname": "approvers",
				"fieldtype": "Section Break",
				"label": _("Approvers"),
				"insert_after": "leave_block_list",
			},
			{
				"fieldname": "shift_request_approver",
				"fieldtype": "Table",
				"label": _("Shift Request Approver"),
				"options": "Department Approver",
				"insert_after": "approvers",
			},
			{
				"fieldname": "leave_approvers",
				"fieldtype": "Table",
				"label": _("Leave Approver"),
				"options": "Department Approver",
				"insert_after": "shift_request_approver",
			},
			{
				"fieldname": "expense_approvers",
				"fieldtype": "Table",
				"label": _("Expense Approver"),
				"options": "Department Approver",
				"insert_after": "leave_approvers",
			},
		],
		"Employee": [
			{
				"fieldname": "employment_type",
				"fieldtype": "Link",
				"ignore_user_permissions": 1,
				"label": _("Employment Type"),
				"options": "Employment Type",
				"insert_after": "department",
				"in_list_view": 1,
			},
			{
				"fieldname": "job_applicant",
				"fieldtype": "Link",
				"label": _("Job Applicant"),
				"options": "Job Applicant",
				"insert_after": "employment_details",
			},
			{
				"fieldname": "grade",
				"fieldtype": "Link",
				"label": _("Grade"),
				"options": "Employee Grade",
				"insert_after": "branch",
			},
			{
				"fieldname": "default_shift",
				"fieldtype": "Link",
				"label": _("Default Shift"),
				"options": "Shift Type",
				"insert_after": "holiday_list",
			},
			{
				"collapsible": 1,
				"fieldname": "health_insurance_section",
				"fieldtype": "Section Break",
				"label": _("Health Insurance"),
				"insert_after": "health_details",
			},
			{
				"fieldname": "health_insurance_provider",
				"fieldtype": "Link",
				"label": _("Health Insurance Provider"),
				"options": "Employee Health Insurance",
				"insert_after": "health_insurance_section",
			},
			{
				"depends_on": "eval:doc.health_insurance_provider",
				"fieldname": "health_insurance_no",
				"fieldtype": "Data",
				"label": _("Health Insurance No"),
				"insert_after": "health_insurance_provider",
			},
			{
				"fieldname": "approvers_section",
				"fieldtype": "Section Break",
				"label": _("Approvers"),
				"insert_after": "default_shift",
			},
			{
				"fieldname": "expense_approver",
				"fieldtype": "Link",
				"label": _("Expense Approver"),
				"options": "User",
				"insert_after": "approvers_section",
				"ignore_user_permissions": 1,
			},
			{
				"fieldname": "leave_approver",
				"fieldtype": "Link",
				"label": _("Leave Approver"),
				"options": "User",
				"insert_after": "expense_approver",
				"ignore_user_permissions": 1,
			},
			{
				"fieldname": "column_break_45",
				"fieldtype": "Column Break",
				"insert_after": "leave_approver",
			},
			{
				"fieldname": "shift_request_approver",
				"fieldtype": "Link",
				"label": _("Shift Request Approver"),
				"options": "User",
				"insert_after": "column_break_45",
				"ignore_user_permissions": 1,
			},
		],
	}


def make_fixtures():
	records = [
		# expense claim type
		{"doctype": "Expense Claim Type", "name": _("Calls"), "expense_type": _("Calls")},
		{"doctype": "Expense Claim Type", "name": _("Food"), "expense_type": _("Food")},
		{"doctype": "Expense Claim Type", "name": _("Medical"), "expense_type": _("Medical")},
		{"doctype": "Expense Claim Type", "name": _("Others"), "expense_type": _("Others")},
		{"doctype": "Expense Claim Type", "name": _("Travel"), "expense_type": _("Travel")},
		# vehicle service item
		{"doctype": "Vehicle Service Item", "service_item": "Brake Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Brake Pad"},
		{"doctype": "Vehicle Service Item", "service_item": "Clutch Plate"},
		{"doctype": "Vehicle Service Item", "service_item": "Engine Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Oil Change"},
		{"doctype": "Vehicle Service Item", "service_item": "Wheels"},
		# leave type
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Casual Leave"),
			"name": _("Casual Leave"),
			"allow_encashment": 1,
			"is_carry_forward": 1,
			"max_continuous_days_allowed": "3",
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Compensatory Off"),
			"name": _("Compensatory Off"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
			"is_compensatory": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Sick Leave"),
			"name": _("Sick Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Privilege Leave"),
			"name": _("Privilege Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Earned Leave"),
			"name": _("Earned Leave"),
			"allow_encashment": 1,
			"is_carry_forward": 1,
			"include_holiday": 1,
			"is_earned_leave": 1,
			"earned_leave_frequency": "Monthly",
			"rounding": 0.5,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Leave Without Pay"),
			"name": _("Leave Without Pay"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"is_lwp": 1,
			"include_holiday": 1,
		},
		# Employment Type
		{"doctype": "Employment Type", "employee_type_name": _("Full-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Part-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Probation")},
		{"doctype": "Employment Type", "employee_type_name": _("Contract")},
		{"doctype": "Employment Type", "employee_type_name": _("Commission")},
		{"doctype": "Employment Type", "employee_type_name": _("Piecework")},
		{"doctype": "Employment Type", "employee_type_name": _("Intern")},
		{"doctype": "Employment Type", "employee_type_name": _("Apprentice")},
		# Job Applicant Source
		{"doctype": "Job Applicant Source", "source_name": _("Website Listing")},
		{"doctype": "Job Applicant Source", "source_name": _("Walk In")},
		{"doctype": "Job Applicant Source", "source_name": _("Employee Referral")},
		{"doctype": "Job Applicant Source", "source_name": _("Campaign")},
		# Offer Term
		{"doctype": "Offer Term", "offer_term": _("Date of Joining")},
		{"doctype": "Offer Term", "offer_term": _("Annual Salary")},
		{"doctype": "Offer Term", "offer_term": _("Probationary Period")},
		{"doctype": "Offer Term", "offer_term": _("Employee Benefits")},
		{"doctype": "Offer Term", "offer_term": _("Working Hours")},
		{"doctype": "Offer Term", "offer_term": _("Stock Options")},
		{"doctype": "Offer Term", "offer_term": _("Department")},
		{"doctype": "Offer Term", "offer_term": _("Job Description")},
		{"doctype": "Offer Term", "offer_term": _("Responsibilities")},
		{"doctype": "Offer Term", "offer_term": _("Leaves per Year")},
		{"doctype": "Offer Term", "offer_term": _("Notice Period")},
		{"doctype": "Offer Term", "offer_term": _("Incentives")},
		# Email Account
		{"doctype": "Email Account", "email_id": "jobs@example.com", "append_to": "Job Applicant"},
	]

	make_records(records)


def setup_notifications():
	base_path = frappe.get_app_path("hrms", "hr", "doctype")

	# Leave Application
	response = frappe.read_file(
		os.path.join(base_path, "leave_application/leave_application_email_template.html")
	)
	records = [
		{
			"doctype": "Email Template",
			"name": _("Leave Approval Notification"),
			"response": response,
			"subject": _("Leave Approval Notification"),
			"owner": frappe.session.user,
		}
	]
	records += [
		{
			"doctype": "Email Template",
			"name": _("Leave Status Notification"),
			"response": response,
			"subject": _("Leave Status Notification"),
			"owner": frappe.session.user,
		}
	]

	# Interview
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_reminder_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Reminder"),
			"response": response,
			"subject": _("Interview Reminder"),
			"owner": frappe.session.user,
		}
	]
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_feedback_reminder_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Feedback Reminder"),
			"response": response,
			"subject": _("Interview Feedback Reminder"),
			"owner": frappe.session.user,
		}
	]

	# Exit Interview
	response = frappe.read_file(
		os.path.join(base_path, "exit_interview/exit_questionnaire_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Exit Questionnaire Notification"),
			"response": response,
			"subject": _("Exit Questionnaire Notification"),
			"owner": frappe.session.user,
		}
	]

	make_records(records)


def update_hr_defaults():
	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.emp_created_by = "Naming Series"
	hr_settings.leave_approval_notification_template = _("Leave Approval Notification")
	hr_settings.leave_status_notification_template = _("Leave Status Notification")

	hr_settings.send_interview_reminder = 1
	hr_settings.interview_reminder_template = _("Interview Reminder")
	hr_settings.remind_before = "00:15:00"

	hr_settings.send_interview_feedback_reminder = 1
	hr_settings.feedback_reminder_notification_template = _("Interview Feedback Reminder")

	hr_settings.exit_questionnaire_notification_template = _("Exit Questionnaire Notification")
	hr_settings.save()


def set_single_defaults():
	for dt in ("HR Settings", "Payroll Settings"):
		default_values = frappe.get_all(
			"DocField",
			filters={"parent": dt},
			fields=["fieldname", "default"],
			as_list=True,
		)
		if default_values:
			try:
				doc = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					doc.set(fieldname, value)
				doc.flags.ignore_mandatory = True
				doc.save()
			except frappe.ValidationError:
				pass


def create_default_role_profiles():
	for role_profile_name, roles in DEFAULT_ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", role_profile_name):
			continue

		role_profile = frappe.new_doc("Role Profile")
		role_profile.role_profile = role_profile_name
		for role in roles:
			role_profile.append("roles", {"role": role})

		role_profile.insert(ignore_permissions=True)


def get_post_install_patches():
	return (
		"update_allocate_on_in_leave_type",
		"update_performance_module_changes",
	)


def run_post_install_patches():
	print("\nPatching Existing Data...")

	POST_INSTALL_PATCHES = get_post_install_patches()
	frappe.flags.in_patch = True

	try:
		for patch in POST_INSTALL_PATCHES:
			patch_name = patch.split(".")[-1]
			if not patch_name:
				continue

			frappe.get_attr(f"hrms.patches.post_install.{patch_name}.execute")()
	finally:
		frappe.flags.in_patch = False


# LENDING APP SETUP & CLEANUP
def create_salary_slip_loan_fields():
	if "lending" in frappe.get_installed_apps():
		custom_fields = get_salary_slip_loan_fields()
		existing_doctypes = frappe.get_list("DocType", pluck="name")
		filtered = {dt: fields for dt, fields in custom_fields.items() if dt in existing_doctypes}
		if filtered:
			create_custom_fields(filtered, ignore_validate=True)


def add_lending_docperms_to_ess():
	if not frappe.db.exists("User Type", "Employee Self Service"):
		return

	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()
	append_docperms_to_user_type(loan_docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def remove_lending_docperms_from_ess():
	if not frappe.db.exists("User Type", "Employee Self Service"):
		return

	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()

	for row in list(doc.user_doctypes):
		if row.document_type in loan_docperms:
			doc.user_doctypes.remove(row)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


# ESS USER TYPE SETUP & CLEANUP
def add_non_standard_user_types():
	user_types = get_user_types_data()

	for user_type, data in user_types.items():
		create_custom_role(data)
		create_user_type(user_type, data)


def get_user_types_data():
	return {
		"Employee Self Service": {
			"role": "Employee Self Service",
			"apply_user_permission_on": "Employee",
			"user_id_field": "user_id",
			"doctypes": {
				# masters
				"Holiday List": ["read"],
				"Employee": ["read", "write"],
				# payroll
				"Salary Slip": ["read"],
				"Employee Benefit Application": ["read", "write", "create", "delete"],
				# expenses
				"Expense Claim": ["read", "write", "create", "delete"],
				"Expense Claim Type": ["read"],
				"Employee Advance": ["read", "write", "create", "delete"],
				# leave and attendance
				"Leave Type": ["read"],
				"Leave Application": ["read", "write", "create", "delete"],
				"Attendance Request": ["read", "write", "create", "delete"],
				"Compensatory Leave Request": ["read", "write", "create", "delete"],
				# tax
				"Employee Tax Exemption Declaration": ["read", "write", "create", "delete"],
				"Employee Tax Exemption Proof Submission": ["read", "write", "create", "delete"],
				# projects
				"Timesheet": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# trainings
				"Training Program": ["read"],
				"Training Feedback": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# shifts
				"Employee Checkin": ["read"],
				"Shift Request": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# misc
				"Employee Grievance": ["read", "write", "create", "delete"],
				"Employee Referral": ["read", "write", "create", "delete"],
				"Travel Request": ["read", "write", "create", "delete"],
			},
		}
	}


def get_lending_docperms_for_ess():
	return {
		"Loan": ["read"],
		"Loan Application": ["read", "write", "create", "delete", "submit"],
		"Loan Product": ["read"],
	}


def create_custom_role(data):
	if data.get("role") and not frappe.db.exists("Role", data.get("role")):
		frappe.get_doc(
			{"doctype": "Role", "role_name": data.get("role"), "desk_access": 1, "is_custom": 1}
		).insert(ignore_permissions=True)


def create_user_type(user_type, data):
	if frappe.db.exists("User Type", user_type):
		doc = frappe.get_cached_doc("User Type", user_type)
		doc.user_doctypes = []
	else:
		doc = frappe.new_doc("User Type")
		doc.update(
			{
				"name": user_type,
				"role": data.get("role"),
				"user_id_field": data.get("user_id_field"),
				"apply_user_permission_on": data.get("apply_user_permission_on"),
			}
		)

	docperms = data.get("doctypes")
	if doc.role == "Employee Self Service" and "lending" in frappe.get_installed_apps():
		docperms.update(get_lending_docperms_for_ess())

	append_docperms_to_user_type(docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def append_docperms_to_user_type(docperms, doc):
	existing_doctypes = [d.document_type for d in doc.user_doctypes]
	installed_doctypes = frappe.get_list("DocType", pluck="name")

	for doctype, perms in docperms.items():
		if doctype in existing_doctypes:
			continue
		if doctype not in installed_doctypes:
			continue

		args = {"document_type": doctype}
		for perm in perms:
			args[perm] = 1

		doc.append("user_doctypes", args)


def update_select_perm_after_install():
	if not frappe.flags.update_select_perm_after_migrate:
		return

	frappe.flags.ignore_select_perm = False
	for row in frappe.get_all("User Type", filters={"is_standard": 0}):
		print("Updating user type :- ", row.name)
		doc = frappe.get_doc("User Type", row.name)
		doc.flags.ignore_links = True
		doc.save()

	frappe.flags.update_select_perm_after_migrate = False


def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)


DEFAULT_ROLE_PROFILES = {
	"HR": [
		"HR User",
		"HR Manager",
		"Leave Approver",
		"Expense Approver",
	],
}


def get_salary_slip_loan_fields():
	return {
		"Salary Slip": [
			{
				"fieldname": "loan_repayment_sb_1",
				"fieldtype": "Section Break",
				"label": _("Loan Repayment"),
				"depends_on": "total_loan_repayment",
				"insert_after": "base_total_deduction",
			},
			{
				"fieldname": "loans",
				"fieldtype": "Table",
				"label": _("Employee Loan"),
				"options": "Salary Slip Loan",
				"print_hide": 1,
				"insert_after": "loan_repayment_sb_1",
			},
			{
				"fieldname": "loan_details_sb_1",
				"fieldtype": "Section Break",
				"depends_on": "eval:doc.docstatus != 0",
				"insert_after": "loans",
			},
			{
				"fieldname": "total_principal_amount",
				"fieldtype": "Currency",
				"label": _("Total Principal Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_details_sb_1",
			},
			{
				"fieldname": "total_interest_amount",
				"fieldtype": "Currency",
				"label": _("Total Interest Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "total_principal_amount",
			},
			{
				"fieldname": "loan_cb_1",
				"fieldtype": "Column Break",
				"insert_after": "total_interest_amount",
			},
			{
				"fieldname": "total_loan_repayment",
				"fieldtype": "Currency",
				"label": _("Total Loan Repayment"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_cb_1",
			},
		],
		"Loan": [
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "status",
			},
		],
		"Loan Repayment": [
			{
				"default": "0",
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "is_term_loan",
			},
			{
				"depends_on": "eval:doc.repay_from_salary",
				"fieldname": "payroll_payable_account",
				"fieldtype": "Link",
				"label": _("Payroll Payable Account"),
				"mandatory_depends_on": "eval:doc.repay_from_salary",
				"options": "Account",
				"insert_after": "payment_account",
			},
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "process_payroll_accounting_entry_based_on_employee",
				"hidden": 1,
				"fieldtype": "Check",
				"label": _("Process Payroll Accounting Entry based on Employee"),
				"insert_after": "repay_from_salary",
			},
		],
	}


def create_default_hr_organization():
	if not frappe.db.exists("HR Organization", "HO"):
		org = frappe.get_doc(
			{
				"doctype": "HR Organization",
				"organization_code": "HO",
				"organization_name": "Head Office",
				"country": "United States",
				"default_currency": "USD",
			}
		)
		org.insert(ignore_permissions=True)
	# Always restore default regardless of existence guard
	frappe.db.set_default("hr_organization", "HO")


def create_default_holiday_list(year=None):
	"""Create or extend the persistent 'Holidays' list with the given year's base holidays.

	Idempotent at two levels:
	  - If the 'Holidays' list doesn't exist → create it.
	  - If it already exists → extend child-table with any missing dates for *year*.
	  - Update from_date / to_date to cover the widest date range present.
	"""
	from frappe.utils import getdate

	if year is None:
		year = getdate().year

	_ensure_holiday_list_for_year(year)

	# Always upsert default_holiday_list on HO regardless of prior state
	if frappe.db.exists("HR Organization", "HO"):
		frappe.db.set_value("HR Organization", "HO", "default_holiday_list", "Holidays")


def _ensure_holiday_list_for_year(year: int) -> None:
	"""Insert missing base-holidays for *year* into the persistent 'Holidays' list."""
	base_holidays = [
		(f"{year}-01-01", "New Year"),
		(f"{year}-05-01", "Labour Day"),
		(f"{year}-12-25", "Christmas"),
	]

	if not frappe.db.exists("Holiday List", "Holidays"):
		hl = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "Holidays",
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"holidays": [
					{"holiday_date": date, "description": desc} for date, desc in base_holidays
				],
			}
		)
		hl.insert(ignore_permissions=True)
		return

	hl = frappe.get_doc("Holiday List", "Holidays")
	existing_dates = {str(row.holiday_date) for row in hl.holidays}

	added = False
	for date, desc in base_holidays:
		if date not in existing_dates:
			hl.append("holidays", {"holiday_date": date, "description": desc})
			added = True

	if added:
		# Expand from_date / to_date to cover all years present
		all_dates = sorted(existing_dates | {d for d, _ in base_holidays})
		hl.from_date = min(all_dates[0], str(hl.from_date))
		hl.to_date = max(all_dates[-1], str(hl.to_date))
		hl.save(ignore_permissions=True)


def create_default_leave_period(year=None):
	from frappe.utils import getdate

	if year is None:
		year = getdate().year
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


def create_default_salary_components():
	components = [
		{"salary_component": "Basic", "salary_component_abbr": "B", "type": "Earning", "is_tax_applicable": 0},
		{
			"salary_component": "HRA",
			"salary_component_abbr": "HRA",
			"type": "Earning",
			"formula": "0.2 * base",
			"amount_based_on_formula": 1,
		},
		{
			"salary_component": "PF",
			"salary_component_abbr": "PF",
			"type": "Deduction",
			"formula": "0.1 * base",
			"amount_based_on_formula": 1,
		},
	]
	for comp in components:
		if frappe.db.exists("Salary Component", comp["salary_component"]):
			continue
		frappe.get_doc({"doctype": "Salary Component", **comp}).insert(ignore_permissions=True)


def create_default_salary_structure():
	if frappe.db.exists("Salary Structure", "Default Structure"):
		return
	ss = frappe.get_doc(
		{
			"doctype": "Salary Structure",
			"name": "Default Structure",
			"is_active": "Yes",
			"payroll_frequency": "Monthly",
			"currency": "USD",
			"hr_organization": "HO",
			"earnings": [
				{"salary_component": "Basic", "amount_based_on_formula": 0, "amount": 0},
				{"salary_component": "HRA", "amount_based_on_formula": 1, "formula": "0.2 * base"},
			],
			"deductions": [
				{"salary_component": "PF", "amount_based_on_formula": 1, "formula": "0.1 * base"},
			],
		}
	)
	ss.insert(ignore_permissions=True)
	ss.submit()


STANDARD_POLICY_TITLE = "Standard"

_STANDARD_LEAVE_TYPES = [
	{"leave_type_name": "Annual Leave", "annual_allocation": 28, "max_leaves_allowed": 28},
	{"leave_type_name": "Sick Leave", "annual_allocation": 14, "max_leaves_allowed": 14},
]


def _ensure_leave_type(leave_type_name: str, max_leaves_allowed: int) -> None:
	"""Create Leave Type if absent (idempotent)."""
	if frappe.db.exists("Leave Type", leave_type_name):
		return
	frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": leave_type_name,
			"name": leave_type_name,
			"max_leaves_allowed": max_leaves_allowed,
			"is_lwp": 0,
		}
	).insert(ignore_permissions=True)


def _get_or_create_default_leave_policy() -> str:
	"""Return doc.name of the Standard leave policy, creating it (and required Leave Types) if absent."""
	existing_name = frappe.db.get_value("Leave Policy", {"title": STANDARD_POLICY_TITLE}, "name")
	if existing_name:
		return existing_name

	for lt in _STANDARD_LEAVE_TYPES:
		_ensure_leave_type(lt["leave_type_name"], lt["max_leaves_allowed"])

	doc = frappe.get_doc(
		{
			"doctype": "Leave Policy",
			"title": STANDARD_POLICY_TITLE,
			"leave_policy_details": [
				{"leave_type": lt["leave_type_name"], "annual_allocation": lt["annual_allocation"]}
				for lt in _STANDARD_LEAVE_TYPES
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def create_default_leave_policy():
	_get_or_create_default_leave_policy()


def create_default_payroll_period():
	from frappe.utils import getdate

	year = getdate().year
	start_date, end_date = f"{year}-01-01", f"{year}-12-31"
	if frappe.db.exists(
		"Payroll Period", {"hr_organization": "HO", "start_date": start_date, "end_date": end_date}
	):
		return
	frappe.get_doc(
		{
			"doctype": "Payroll Period",
			"name": f"HO-{year}",
			"hr_organization": "HO",
			"start_date": start_date,
			"end_date": end_date,
		}
	).insert(ignore_permissions=True)


def create_default_lpa_for_all_employees(year=None):
	"""Assign Leave Policy 'Standard' to all active Employees for the given year's Leave Period.

	Idempotent: employees that already have a submitted LPA covering the year are skipped.
	After LPA submit, Frappe HRMS triggers Leave Allocation creation automatically.
	"""
	from frappe.utils import getdate

	if year is None:
		year = getdate().year

	year_start = getdate(f"{year}-01-01")
	year_end = getdate(f"{year}-12-31")

	leave_period = frappe.db.get_value(
		"Leave Period",
		{"hr_organization": "HO", "from_date": str(year_start), "to_date": str(year_end)},
		"name",
	)
	if not leave_period:
		frappe.log_error(
			f"Leave Period for HO/{year} not found — run create_default_leave_period({year}) first",
			"HR Bootstrap LPA",
		)
		return

	policy_name = _get_or_create_default_leave_policy()

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "relieving_date": ["is", "not set"]},
		pluck="name",
	)

	for employee in employees:
		_ensure_lpa_for_year(employee, policy_name, leave_period, year_start, year_end)


def _ensure_lpa_for_year(employee, policy_name, leave_period, year_start, year_end):
	"""Create and submit LPA for employee+year if one doesn't already exist (idempotent)."""
	already_assigned = frappe.db.exists(
		"Leave Policy Assignment",
		{
			"employee": employee,
			"leave_policy": policy_name,
			"docstatus": 1,
			"effective_from": ["<=", year_start],
			"effective_to": [">=", year_end],
		},
	)
	if already_assigned:
		return

	try:
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
		lpa.insert(ignore_permissions=True)
		lpa.submit()
	except frappe.ValidationError:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap LPA: employee={employee}")
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"HR Bootstrap LPA: employee={employee}")
		raise


def bootstrap_next_year_defaults():
	"""Scheduled entry point: called on 1 Dec to prepare next year's HR defaults."""
	from frappe.utils import getdate

	next_year = getdate().year + 1
	create_default_leave_period(next_year)
	create_default_holiday_list(next_year)
	# Leave Policy and LPA for next year are done separately once employees are confirmed


def make_people_workspace_standard():
	if frappe.db.exists("Workspace Sidebar", "People"):
		frappe.db.set_value("Workspace Sidebar", "People", "standard", 1)
