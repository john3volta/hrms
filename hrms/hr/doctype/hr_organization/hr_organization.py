import frappe
from frappe import _
from frappe.model.document import Document


class HROrganization(Document):
	def validate(self):
		self._validate_parent_not_self()

	def _validate_parent_not_self(self):
		if self.parent_organization == self.name:
			frappe.throw(_("Parent Organization cannot be the same as this organization"))
