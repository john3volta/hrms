# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class PayoutRegister(Document):
	def validate(self):
		self._validate_state_transition()

	def before_submit(self):
		self._populate_lines_if_empty()

	def on_submit(self):
		self.db_set("status", "Confirmed")
		self.db_set("confirmed_date", today())

	def on_cancel(self):
		self._cancel_lines()
		self.db_set("status", "Cancelled")

	def _validate_state_transition(self):
		if self.status == "Paid" and not self.confirmed_date:
			frappe.throw(
				_("Payout Register must be Confirmed before marking as Paid."),
				title=_("Invalid State"),
			)

	def _populate_lines_if_empty(self):
		if self.lines:
			return
		filters = {"docstatus": 1, "withheld": 0}
		if self.payroll_entry:
			filters["payroll_entry"] = self.payroll_entry
		salary_slips = frappe.get_all(
			"Salary Slip",
			filters=filters,
			fields=["name", "employee", "net_pay"],
		)
		for ss in salary_slips:
			self.append(
				"lines",
				{
					"salary_slip": ss.name,
					"employee": ss.employee,
					"net_pay": ss.net_pay or 0,
					"status": "Unpaid",
				},
			)

	def _cancel_lines(self):
		for line in self.lines:
			if line.status != "Paid":
				line_doc = frappe.get_doc("Payout Register Line", line.name)
				line_doc.db_set("status", "Cancelled")

	@frappe.whitelist()
	def mark_paid(self, salary_slips=None):
		"""Mark specific (or all Unpaid) lines as Paid."""
		self.check_permission("write")
		paid_date = today()

		for line in self.lines:
			if salary_slips and line.salary_slip not in salary_slips:
				continue
			if line.status == "Unpaid":
				line_doc = frappe.get_doc("Payout Register Line", line.name)
				line_doc.db_set("status", "Paid")
				line_doc.db_set("paid_date", paid_date)

		self.reload()
		if all(l.status == "Paid" for l in self.lines):
			self.db_set("status", "Paid")
			self.db_set("paid_date", paid_date)
