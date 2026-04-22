# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class PayoutRegister(Document):
	def validate(self):
		self._validate_state_transition()

	def on_submit(self):
		self._populate_lines_if_empty()
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
		salary_slips = frappe.get_all(
			"Salary Slip",
			filters={"payroll_entry": self.payroll_entry, "docstatus": 1},
			fields=["name", "employee", "net_pay"],
		)
		for ss in salary_slips:
			self.append(
				"lines",
				{
					"salary_slip": ss.name,
					"employee": ss.employee,
					"net_pay": ss.net_pay,
					"status": "Unpaid",
				},
			)
		self.save(ignore_permissions=True)

	def _cancel_lines(self):
		for line in self.lines:
			if line.status != "Paid":
				line.status = "Cancelled"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def mark_paid(self, salary_slips=None):
		"""Mark specific (or all Unpaid) lines as Paid."""
		self.check_permission("write")
		paid_date = today()
		all_paid = True

		for line in self.lines:
			if salary_slips and line.salary_slip not in salary_slips:
				continue
			if line.status == "Unpaid":
				line.status = "Paid"
				line.paid_date = paid_date

		for line in self.lines:
			if line.status == "Unpaid":
				all_paid = False
				break

		if all_paid:
			self.db_set("status", "Paid")
			self.db_set("paid_date", paid_date)

		self.save(ignore_permissions=True)
