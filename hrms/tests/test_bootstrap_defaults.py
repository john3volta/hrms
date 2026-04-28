"""Tests for HR bootstrap defaults (setup.py helpers).

Run via:
    python3 -m unittest hrms.tests.test_bootstrap_defaults
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.utils import getdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_employee(name_suffix: str) -> str:
	"""Insert a minimal Active Employee and return its name."""
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": f"Bootstrap_{name_suffix}",
			"status": "Active",
			"date_of_joining": "2024-01-01",
			"gender": "Male",
			"company": frappe.db.get_single_value("Global Defaults", "default_company") or "_Test Company",
		}
	)
	emp.insert(ignore_permissions=True)
	return emp.name


def _cleanup(*doctypes_names):
	"""Delete test records; swallow DoesNotExist."""
	for doctype, name in doctypes_names:
		try:
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
		except Exception:
			pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBootstrapDefaults(unittest.TestCase):

	# ------------------------------------------------------------------
	# Task 1 — Leave Period idempotency
	# ------------------------------------------------------------------

	def test_idempotent_leave_period(self):
		"""Calling create_default_leave_period(year) twice must not create duplicates."""
		from hrms.setup import create_default_leave_period

		test_year = 2099
		from_date, to_date = f"{test_year}-01-01", f"{test_year}-12-31"

		try:
			create_default_leave_period(test_year)
			create_default_leave_period(test_year)  # second call — must be a no-op

			count = frappe.db.count(
				"Leave Period",
				{"hr_organization": "HO", "from_date": from_date, "to_date": to_date},
			)
			self.assertEqual(count, 1, "Leave Period must exist exactly once after two calls")
		finally:
			names = frappe.get_all(
				"Leave Period",
				filters={"hr_organization": "HO", "from_date": from_date, "to_date": to_date},
				pluck="name",
			)
			for n in names:
				frappe.delete_doc("Leave Period", n, ignore_permissions=True, force=True)

	# ------------------------------------------------------------------
	# Task 3 — Holiday List extends child-table idempotently
	# ------------------------------------------------------------------

	def test_idempotent_holiday_list_extends_child_table(self):
		"""Second call with a new year must add holidays without recreating the list."""
		from hrms.setup import _ensure_holiday_list_for_year

		year_a, year_b = 2097, 2098

		# Ensure we start clean
		if frappe.db.exists("Holiday List", "Holidays"):
			frappe.delete_doc("Holiday List", "Holidays", ignore_permissions=True, force=True)

		try:
			_ensure_holiday_list_for_year(year_a)
			count_after_first = frappe.db.count("Holiday", {"parent": "Holidays"})
			self.assertGreaterEqual(count_after_first, 3, "Should have at least 3 holidays for year_a")

			_ensure_holiday_list_for_year(year_b)
			count_after_second = frappe.db.count("Holiday", {"parent": "Holidays"})
			self.assertGreater(
				count_after_second,
				count_after_first,
				"year_b holidays should be added to the existing list",
			)

			# List must still exist as a single doc named 'Holidays'
			self.assertTrue(
				frappe.db.exists("Holiday List", "Holidays"),
				"Holiday List 'Holidays' must still exist after second call",
			)
		finally:
			if frappe.db.exists("Holiday List", "Holidays"):
				frappe.delete_doc("Holiday List", "Holidays", ignore_permissions=True, force=True)

	# ------------------------------------------------------------------
	# Task 2 — Leave Policy creates Annual and Sick Leave Types
	# ------------------------------------------------------------------

	def test_default_leave_policy_creates_types(self):
		"""_get_or_create_default_leave_policy() must create Annual Leave and Sick Leave types."""
		from hrms.setup import _get_or_create_default_leave_policy, STANDARD_POLICY_TITLE

		# Remove types and policy so we test creation path
		for lt in ("Annual Leave", "Sick Leave"):
			if frappe.db.exists("Leave Type", lt):
				frappe.delete_doc("Leave Type", lt, ignore_permissions=True, force=True)

		existing_policy = frappe.db.get_value("Leave Policy", {"title": STANDARD_POLICY_TITLE}, "name")
		if existing_policy:
			frappe.delete_doc("Leave Policy", existing_policy, ignore_permissions=True, force=True)

		try:
			policy_name = _get_or_create_default_leave_policy()

			self.assertTrue(
				frappe.db.exists("Leave Type", "Annual Leave"),
				"Annual Leave type must be created",
			)
			self.assertTrue(
				frappe.db.exists("Leave Type", "Sick Leave"),
				"Sick Leave type must be created",
			)
			self.assertTrue(bool(policy_name), "Policy name must be returned")

			# Calling again must return same name (idempotent)
			policy_name_2 = _get_or_create_default_leave_policy()
			self.assertEqual(policy_name, policy_name_2, "Must return same policy on second call")
		finally:
			existing_policy = frappe.db.get_value("Leave Policy", {"title": STANDARD_POLICY_TITLE}, "name")
			if existing_policy:
				frappe.delete_doc("Leave Policy", existing_policy, ignore_permissions=True, force=True)

	# ------------------------------------------------------------------
	# Task 4 — LPA skips employees that already have an assignment
	# ------------------------------------------------------------------

	def test_lpa_skips_existing_employees(self):
		"""Employees with an existing submitted LPA must not receive a duplicate."""
		from hrms.setup import (
			create_default_leave_period,
			_get_or_create_default_leave_policy,
			_ensure_lpa_for_year,
		)

		test_year = 2098
		from_date = getdate(f"{test_year}-01-01")
		to_date = getdate(f"{test_year}-12-31")

		create_default_leave_period(test_year)
		leave_period = frappe.db.get_value(
			"Leave Period",
			{"hr_organization": "HO", "from_date": str(from_date), "to_date": str(to_date)},
			"name",
		)
		policy_name = _get_or_create_default_leave_policy()

		emp_name = None
		try:
			emp_name = _make_employee("lpa_skip_test")

			# First assignment
			_ensure_lpa_for_year(emp_name, policy_name, leave_period, from_date, to_date)
			count_before = frappe.db.count(
				"Leave Policy Assignment",
				{"employee": emp_name, "docstatus": 1},
			)

			# Second call — must be skipped
			_ensure_lpa_for_year(emp_name, policy_name, leave_period, from_date, to_date)
			count_after = frappe.db.count(
				"Leave Policy Assignment",
				{"employee": emp_name, "docstatus": 1},
			)

			self.assertEqual(
				count_before,
				count_after,
				"No duplicate LPA should be created for an already-assigned employee",
			)
		finally:
			if emp_name:
				# Cancel submitted LPAs first
				for lpa in frappe.get_all(
					"Leave Policy Assignment",
					filters={"employee": emp_name},
					pluck="name",
				):
					try:
						doc = frappe.get_doc("Leave Policy Assignment", lpa)
						if doc.docstatus == 1:
							doc.cancel()
						frappe.delete_doc("Leave Policy Assignment", lpa, ignore_permissions=True, force=True)
					except Exception:
						pass
				frappe.delete_doc("Employee", emp_name, ignore_permissions=True, force=True)

			periods = frappe.get_all(
				"Leave Period",
				filters={"hr_organization": "HO", "from_date": str(from_date), "to_date": str(to_date)},
				pluck="name",
			)
			for n in periods:
				frappe.delete_doc("Leave Period", n, ignore_permissions=True, force=True)


if __name__ == "__main__":
	unittest.main()
