// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Payout Register", {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Confirmed") {
			frm.add_custom_button(__("Mark All Paid"), function () {
				frm.call("mark_paid").then(() => frm.reload_doc());
			}).addClass("btn-primary");
		}
	},
});
