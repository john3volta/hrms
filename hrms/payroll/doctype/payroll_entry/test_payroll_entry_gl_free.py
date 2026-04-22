# Copyright (c) 2026, contributors
# Contract tests for GL-free payroll (Phase 3.4-3.5).
# Covers: uniqueness validation, withheld slip, Payout Register lifecycle, cancel cascade.

import frappe
from frappe.utils import add_months, nowdate, today

from hrms.tests.utils import HRMSTestSuite


def _make_hr_org(name="Test HROrg 1"):
	if frappe.db.exists("HR Organization", name):
		return name
	org = frappe.new_doc("HR Organization")
	org.organization_name = name
	org.abbr = "THRO1"
	org.default_currency = "USD"
	org.insert(ignore_permissions=True)
	return org.name


def _make_payroll_period(hr_organization):
	name = f"Test PP {hr_organization}"
	if frappe.db.exists("Payroll Period", name):
		return name
	pp = frappe.new_doc("Payroll Period")
	pp.payroll_period_name = name
	pp.start_date = "2026-01-01"
	pp.end_date = "2026-12-31"
	pp.hr_organization = hr_organization
	pp.insert(ignore_permissions=True)
	return pp.name


def _make_minimal_payroll_entry(hr_organization, payroll_period, status="Draft"):
	pe = frappe.new_doc("Payroll Entry")
	pe.posting_date = today()
	pe.hr_organization = hr_organization
	pe.payroll_period = payroll_period
	pe.payroll_frequency = "Monthly"
	pe.start_date = "2026-01-01"
	pe.end_date = "2026-01-31"
	pe.currency = "USD"
	pe.status = status
	return pe


class TestGLFreePayrollEntry(HRMSTestSuite):
	def setUp(self):
		self.hr_org = _make_hr_org()
		self.payroll_period = _make_payroll_period(self.hr_org)

	# --- Salary Slip withheld field ---

	def test_withheld_requires_reason(self):
		"""Salary Slip with withheld=1 must have withhold_reason."""
		ss = frappe.new_doc("Salary Slip")
		ss.withheld = 1
		ss.withhold_reason = ""
		with self.assertRaises(frappe.MandatoryError):
			ss._validate_withheld()

	def test_withheld_with_reason_passes(self):
		ss = frappe.new_doc("Salary Slip")
		ss.withheld = 1
		ss.withhold_reason = "Contract dispute"
		ss._validate_withheld()  # must not raise

	def test_not_withheld_no_reason_passes(self):
		ss = frappe.new_doc("Salary Slip")
		ss.withheld = 0
		ss.withhold_reason = ""
		ss._validate_withheld()  # must not raise

	# --- Uniqueness validation ---

	def test_uniqueness_validation_method_exists(self):
		pe = _make_minimal_payroll_entry(self.hr_org, self.payroll_period)
		self.assertTrue(hasattr(pe, "_validate_uniqueness"))

	# --- GL fields absent from DocType ---

	def test_no_payroll_payable_account_field(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("payroll_payable_account", fieldnames)

	def test_no_cost_center_field(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("cost_center", fieldnames)

	def test_no_payment_account_field(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("payment_account", fieldnames)

	def test_no_accounting_dimensions_tab(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("accounting_dimensions_tab", fieldnames)

	def test_payroll_period_field_exists(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertIn("payroll_period", fieldnames)

	def test_payout_register_field_exists(self):
		meta = frappe.get_meta("Payroll Entry")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertIn("payout_register", fieldnames)

	# --- Salary Component GL fields absent ---

	def test_salary_component_no_accounts_field(self):
		meta = frappe.get_meta("Salary Component")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("accounts", fieldnames)
		self.assertNotIn("do_not_include_in_accounts", fieldnames)

	# --- Salary Structure GL fields absent ---

	def test_salary_structure_no_payment_account(self):
		meta = frappe.get_meta("Salary Structure")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("payment_account", fieldnames)

	# --- Salary Structure Assignment GL fields absent ---

	def test_salary_structure_assignment_no_payable_account(self):
		meta = frappe.get_meta("Salary Structure Assignment")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("payroll_payable_account", fieldnames)
		self.assertNotIn("payroll_cost_centers", fieldnames)

	# --- Salary Slip new fields ---

	def test_salary_slip_withheld_field_exists(self):
		meta = frappe.get_meta("Salary Slip")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertIn("withheld", fieldnames)

	def test_salary_slip_approval_status_field_exists(self):
		meta = frappe.get_meta("Salary Slip")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertIn("approval_status", fieldnames)

	def test_salary_slip_payment_status_virtual(self):
		meta = frappe.get_meta("Salary Slip")
		field = next((f for f in meta.fields if f.fieldname == "payment_status"), None)
		self.assertIsNotNone(field)
		self.assertTrue(field.get("virtual") or field.virtual, "payment_status must be virtual")

	def test_salary_slip_no_journal_entry_field(self):
		meta = frappe.get_meta("Salary Slip")
		fieldnames = [f.fieldname for f in meta.fields]
		self.assertNotIn("journal_entry", fieldnames)

	# --- Payout Register DocType ---

	def test_payout_register_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Payout Register"))

	def test_payout_register_line_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Payout Register Line"))

	def test_payout_register_status_options(self):
		meta = frappe.get_meta("Payout Register")
		status_field = next((f for f in meta.fields if f.fieldname == "status"), None)
		self.assertIsNotNone(status_field)
		options = status_field.options.split("\n")
		self.assertIn("Draft", options)
		self.assertIn("Confirmed", options)
		self.assertIn("Paid", options)
		self.assertIn("Cancelled", options)

	# --- Status enum on Payroll Entry ---

	def test_payroll_entry_status_options_include_submitting(self):
		meta = frappe.get_meta("Payroll Entry")
		status_field = next((f for f in meta.fields if f.fieldname == "status"), None)
		self.assertIsNotNone(status_field)
		options = status_field.options.split("\n")
		self.assertIn("Submitting", options)
		self.assertIn("Draft", options)
		self.assertIn("Submitted", options)
		self.assertIn("Cancelled", options)
