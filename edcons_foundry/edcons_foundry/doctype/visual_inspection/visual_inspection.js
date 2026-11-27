const VI_DEFECTS = ["shrinkage", "cold_shut", "sandfall", "mismatch", "core", "keyhole_sand", "fitment_rocking", "frame_height", "other_defects"];
frappe.ui.form.on("Visual Inspection", {
	refresh(frm) { edcons_foundry.setup(frm); },
	calc(frm) {
		const items = frm.doc.items || [];
		const checked = edcons_foundry.sum(items, "qty_checked"), rej = edcons_foundry.sum(items, "total_rejected");
		frm.set_value({ total_checked: checked, total_rejected: rej, total_ok: checked - rej });
	},
});
const vi_handlers = {
	items_add(frm, cdt, cdn) { edcons_foundry.copy_previous_row(frm, cdt, cdn, ["heat"]); },
	qty_checked: vi_calc,
	items_remove: (frm) => frm.trigger("calc"),
};
VI_DEFECTS.forEach((f) => (vi_handlers[f] = vi_calc));
frappe.ui.form.on("Visual Inspection Item", vi_handlers);
function vi_calc(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	const rej = VI_DEFECTS.reduce((a, f) => a + cint(r[f]), 0);
	if (rej > cint(r.qty_checked)) frappe.show_alert({ message: __("Row {0}: rejected is more than checked", [r.idx]), indicator: "red" });
	frappe.model.set_value(cdt, cdn, { total_rejected: rej, ok_qty: cint(r.qty_checked) - rej });
	frm.trigger("calc");
}
