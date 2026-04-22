// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Holiday List", {
	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Add Weekly Offs"), function () {
				frm.trigger("add_weekly_offs");
			});
		}
	},
	add_weekly_offs: function (frm) {
		if (!frm.doc.weekly_off) {
			frappe.msgprint(__("Please select a Weekly Off day first"));
			return;
		}
		frappe.call({
			method: "hrms.hr.doctype.holiday_list.holiday_list.add_weekly_offs",
			args: {
				holiday_list: frm.doc.name,
				weekly_off: frm.doc.weekly_off,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date,
			},
			callback: function (r) {
				if (r.message) {
					frm.reload_doc();
				}
			},
		});
	},
});
