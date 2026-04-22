# Copyright (c) 2026, contributors
# Contract tests for Payout Register state machine.

import frappe
from frappe.utils import today

from hrms.tests.utils import HRMSTestSuite


class TestPayoutRegister(HRMSTestSuite):
	def test_status_transitions_defined(self):
		meta = frappe.get_meta("Payout Register")
		status_field = next((f for f in meta.fields if f.fieldname == "status"), None)
		self.assertIsNotNone(status_field)
		options = status_field.options.split("\n")
		for expected in ["Draft", "Confirmed", "Paid", "Cancelled"]:
			self.assertIn(expected, options)

	def test_lines_child_table_exists(self):
		meta = frappe.get_meta("Payout Register")
		lines_field = next((f for f in meta.fields if f.fieldname == "lines"), None)
		self.assertIsNotNone(lines_field)
		self.assertEqual(lines_field.options, "Payout Register Line")

	def test_payout_register_line_has_status(self):
		meta = frappe.get_meta("Payout Register Line")
		status_field = next((f for f in meta.fields if f.fieldname == "status"), None)
		self.assertIsNotNone(status_field)
		options = status_field.options.split("\n")
		self.assertIn("Unpaid", options)
		self.assertIn("Paid", options)

	def test_validate_paid_requires_confirmed_date(self):
		pr = frappe.new_doc("Payout Register")
		pr.status = "Paid"
		pr.confirmed_date = None
		with self.assertRaises(frappe.ValidationError):
			pr._validate_state_transition()
