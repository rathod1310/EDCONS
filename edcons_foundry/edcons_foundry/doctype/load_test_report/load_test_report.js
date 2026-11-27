frappe.ui.form.on("Load Test Report", {
	refresh(frm) {
		edcons_foundry.setup(frm);
		frm.set_query("sales_order", () => ({ filters: { customer: frm.doc.customer, docstatus: 1 } }));
	},
	sales_order(frm) {
		if (!frm.doc.sales_order) return;
		frappe.db.get_value("Sales Order", frm.doc.sales_order, ["customer", "po_no"]).then(({ message: so }) => {
			frm.set_value("customer", so.customer);
			if (so.po_no) frm.set_value("po_no", so.po_no);
		});
	},
	calc(frm) {
		const res = (frm.doc.items || []).map((r) => r.result).filter(Boolean);
		frm.set_value("overall_result", res.length ? (res.includes("Fail") ? "Fail" : "Pass") : "");
	},
});
frappe.ui.form.on("Load Test Item", {
	items_add(frm, cdt, cdn) { edcons_foundry.copy_previous_row(frm, cdt, cdn, ["heat", "standard", "required_load_kn", "allowed_set_mm"]); },
	required_load_kn: lt_row, applied_load_kn: lt_row, permanent_set_mm: lt_row, allowed_set_mm: lt_row,
	items_remove: (frm) => frm.trigger("calc"),
});
function lt_row(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	let res = "";
	if (flt(r.applied_load_kn)) {
		let ok = flt(r.applied_load_kn) >= flt(r.required_load_kn);
		if (flt(r.allowed_set_mm)) ok = ok && flt(r.permanent_set_mm) <= flt(r.allowed_set_mm);
		res = ok ? "Pass" : "Fail";
	}
	frappe.model.set_value(cdt, cdn, "result", res);
	frm.trigger("calc");
}
