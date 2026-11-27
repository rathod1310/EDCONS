frappe.ui.form.on("Rejection Report", {
	refresh(frm) {
		edcons_foundry.setup(frm);
		if (frm.doc.reference_name) {
			frm.add_custom_button(__(frm.doc.reference_doctype), () => frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name), __("View"));
		}
		const missing = (frm.doc.items || []).filter((r) => !r.reason).length;
		if (missing && frm.doc.docstatus === 0) frm.dashboard.add_comment(__("{0} row(s) still need a reason", [missing]), "orange", true);
	},
	produced_nos: (frm) => frm.trigger("calc"),
	calc(frm) {
		const items = frm.doc.items || [];
		const n = edcons_foundry.sum(items, "qty_nos");
		frm.set_value({ total_nos: n, total_kg: edcons_foundry.sum(items, "weight_kg"),
			rejection_pct: cint(frm.doc.produced_nos) ? (n / cint(frm.doc.produced_nos)) * 100 : 0 });
	},
});
frappe.ui.form.on("Rejection Item", {
	qty_nos: rr_row, unit_weight: rr_row,
	items_remove: (frm) => frm.trigger("calc"),
});
function rr_row(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "weight_kg", cint(r.qty_nos) * flt(r.unit_weight));
	frm.trigger("calc");
}
