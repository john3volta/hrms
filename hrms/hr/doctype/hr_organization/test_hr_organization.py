import frappe
from frappe.tests import IntegrationTestCase


class TestHROrganization(IntegrationTestCase):
	def test_create_hr_organization(self):
		org = frappe.get_doc({
			"doctype": "HR Organization",
			"organization_name": "Test Org",
			"organization_code": "TEST-ORG-001",
			"country": "India",
			"default_currency": "INR",
		})
		org.insert(ignore_permissions=True)
		self.assertEqual(org.organization_code, "TEST-ORG-001")
		frappe.delete_doc("HR Organization", org.name, ignore_permissions=True)
