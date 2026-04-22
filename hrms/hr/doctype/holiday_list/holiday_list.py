# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

DAY_MAP = {
	"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
	"Friday": 4, "Saturday": 5, "Sunday": 6,
}


class HolidayList(Document):
	def validate(self):
		self.validate_dates()
		self.set_total_holidays()

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To Date must be after From Date"))

	def set_total_holidays(self):
		self.total_holidays = len(self.holidays) if self.holidays else 0

	def get_weekly_off_dates(self):
		"""Populate weekly-off rows from self.weekly_off; compat with upstream callers."""
		if not self.weekly_off:
			return
		if self.weekly_off not in DAY_MAP:
			frappe.throw(_("Invalid Weekly Off day: {0}").format(self.weekly_off))

		target_weekday = DAY_MAP[self.weekly_off]
		existing_dates = {getdate(h.holiday_date) for h in self.holidays}

		current = getdate(self.from_date)
		end = getdate(self.to_date)
		while current <= end:
			if current.weekday() == target_weekday and current not in existing_dates:
				self.append("holidays", {
					"holiday_date": current,
					"description": self.weekly_off,
					"weekly_off": 1,
				})
				existing_dates.add(current)
			current += timedelta(days=1)


@frappe.whitelist()
def add_weekly_offs(holiday_list: str, weekly_off: str, from_date: str, to_date: str):
	if weekly_off not in DAY_MAP:
		frappe.throw(_("Invalid Weekly Off day: {0}").format(weekly_off))

	doc = frappe.get_doc("Holiday List", holiday_list)

	# clamp caller dates to list boundaries
	start = max(getdate(from_date), getdate(doc.from_date))
	end = min(getdate(to_date), getdate(doc.to_date))
	if start > end:
		return 0

	target_weekday = DAY_MAP[weekly_off]
	existing_dates = {getdate(h.holiday_date) for h in doc.holidays}

	current = start
	added = 0
	while current <= end:
		if current.weekday() == target_weekday and current not in existing_dates:
			doc.append("holidays", {
				"holiday_date": current,
				"description": weekly_off,
				"weekly_off": 1,
			})
			existing_dates.add(current)
			added += 1
		current += timedelta(days=1)

	if added:
		doc.save()
	return added
