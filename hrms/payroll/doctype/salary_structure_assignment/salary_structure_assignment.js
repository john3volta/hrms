// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salary Structure Assignment", {
	setup: function (frm) {
		frm.set_query("employee", function () {
			return {
				query: "erpnext.controllers.queries.employee_query",
				filters: { hr_organization: frm.doc.hr_organization },
			};
		});
		frm.set_query("salary_structure", function () {
			return {
				filters: {
					hr_organization: frm.doc.hr_organization,
					docstatus: 1,
					is_active: "Yes",
				},
			};
		});

		frm.set_query("income_tax_slab", function () {
			return {
				filters: {
					docstatus: 1,
					disabled: 0,
					currency: frm.doc.currency,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.trigger("toggle_opening_balances_section");

		if (frm.doc.docstatus != 1) return;

		frm.add_custom_button(
			__("Payroll Entry"),
			() => {
				frappe.model.with_doctype("Payroll Entry", () => {
					const doc = frappe.model.get_new_doc("Payroll Entry");
					frappe.set_route("Form", "Payroll Entry", doc.name);
				});
			},
			__("Create"),
		);
		frm.page.set_inner_btn_group_as_primary(__("Create"));

		frm.add_custom_button(
			__("Preview Salary Slip"),
			function () {
				frm.trigger("preview_salary_slip");
			},
			__("Actions"),
		);
	},

	employee: function (frm) {
		frm.trigger("toggle_opening_balances_section");
	},

	salary_structure: (frm) => {
		if (frm.doc.salary_structure) {
			frappe.db.get_doc("Salary Structure", frm.doc.salary_structure).then((doc) => {
				frm.clear_table("employee_benefits");
				doc.employee_benefits.forEach((benefit) => {
					const row = frm.add_child("employee_benefits");
					row.salary_component = benefit.salary_component;
					row.amount = benefit.amount;
				});
				refresh_field("employee_benefits");
				calculate_max_benefit_amount(frm.doc);
			});
		}
	},

	preview_salary_slip: function (frm) {
		frappe.db.get_value(
			"Salary Structure",
			frm.doc.salary_structure,
			"salary_slip_based_on_timesheet",
			(r) => {
				const print_format = r.salary_slip_based_on_timesheet
					? "Salary Slip based on Timesheet"
					: "Salary Slip Standard";
				frappe.call({
					method: "hrms.payroll.doctype.salary_structure.salary_structure.make_salary_slip",
					args: {
						source_name: frm.doc.salary_structure,
						employee: frm.doc.employee,
						posting_date: frm.doc.from_date,
						as_print: 1,
						print_format: print_format,
						for_preview: 1,
					},
					callback: function (r) {
						const new_window = window.open();
						new_window.document.write(r.message);
					},
				});
			},
		);
	},

	toggle_opening_balances_section: function (frm) {
		if (!frm.doc.from_date || !frm.doc.employee || !frm.doc.salary_structure) return;

		frm.call("are_opening_entries_required").then((data) => {
			if (data.message) {
				frm.set_df_property("opening_balances_section", "hidden", 0);
			} else {
				frm.set_df_property("opening_balances_section", "hidden", 1);
			}
		});
	},

	from_date: function (frm) {
		if (frm.doc.from_date) {
			frm.trigger("toggle_opening_balances_section");
		}
	},
});

frappe.ui.form.on("Employee Benefit Detail", {
	amount: (frm) => calculate_max_benefit_amount(frm.doc),
});

let calculate_max_benefit_amount = (doc) => {
	let employee_benefits = doc.employee_benefits || [];
	let max_benefits = 0;
	if (employee_benefits.length > 0) {
		for (let i = 0; i < employee_benefits.length; i++) {
			max_benefits += flt(employee_benefits[i].amount) || 0;
		}
	}
	doc.max_benefits = max_benefits;
	refresh_field("max_benefits");
};
