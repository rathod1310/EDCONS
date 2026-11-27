frappe.ui.form.on("Pattern", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.castings_required && frm.doc.shots_used >= frm.doc.castings_required) {
			frm.dashboard.add_comment(__("All required castings are made. Return the pattern to the customer?"), "blue", true);
		}
	},
	receiving_qty: (frm) => frm.set_value("balance_qty", cint(frm.doc.receiving_qty) - cint(frm.doc.return_qty)),
	return_qty: (frm) => frm.set_value("balance_qty", cint(frm.doc.receiving_qty) - cint(frm.doc.return_qty)),
});
