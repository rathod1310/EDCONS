frappe.ui.form.on("Finishing Log", {
	refresh(frm) {
		edcons_foundry.setup(frm);
		frappe.db.get_single_value("Foundry Settings", "weight_tolerance_pct").then((t) => (frm._tol = flt(t) || 3));
	},
	calc(frm) {
		const items = frm.doc.items || [];
		frm.set_value({
			total_finished_nos: edcons_foundry.sum(items, "finished_nos"),
			total_rejected_nos: edcons_foundry.sum(items, "rejected_nos"),
			total_finished_kg: edcons_foundry.sum(items, "finished_kg"),
			weight_alerts: items.filter((r) => ["Overweight", "Underweight"].includes(r.weight_flag)).length,
		});
	},
});
frappe.ui.form.on("Finishing Log Item", {
	items_add(frm, cdt, cdn) { edcons_foundry.copy_previous_row(frm, cdt, cdn, ["worker", "process"]); },
	sample_weights: weigh, book_weight: weigh, finished_nos: weigh, rejected_nos: weigh,
	items_remove: (frm) => frm.trigger("calc"),
});
function weigh(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	const w = (r.sample_weights || "").split(/[,\s;/]+/).map(flt).filter((x) => x > 0);
	const avg = w.length ? w.reduce((a, b) => a + b, 0) / w.length : flt(r.actual_weight);
	const tol = frm._tol || 3;
	let dev = 0, flag = "";
	if (avg && flt(r.book_weight)) {
		dev = ((avg - flt(r.book_weight)) / flt(r.book_weight)) * 100;
		flag = dev > tol ? "Overweight" : dev < -tol ? "Underweight" : "OK";
		if (flag !== "OK") frappe.show_alert({ message: __("Row {0}: {1} by {2}%", [r.idx, __(flag), Math.abs(dev).toFixed(1)]), indicator: "orange" });
	}
	frappe.model.set_value(cdt, cdn, { actual_weight: avg, weight_dev_pct: dev, weight_flag: flag,
		finished_kg: cint(r.finished_nos) * (avg || flt(r.book_weight)) });
	frm.trigger("calc");
}
