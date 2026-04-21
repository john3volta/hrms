import frappe
from frappe.tests import IntegrationTestCase


class TestDepartment(IntegrationTestCase):
	def test_create_department(self):
		dept = frappe.get_doc({
			"doctype": "Department",
			"department_name": "Engineering Test",
			"hr_organization": frappe.db.get_value("HR Organization", {}, "name"),
		})
		if dept.hr_organization:
			dept.insert(ignore_permissions=True)
			frappe.delete_doc("Department", dept.name, ignore_permissions=True)
