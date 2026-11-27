frappe.ui.form.on("Sand Mix Log", {
	refresh(frm) {
		edcons_foundry.setup(frm, { tables: [] });
		frappe.db.get_doc("Foundry Settings").then((s) => { frm._sand_limits = s.sand_limits || []; frm.trigger("check_all"); });
	},
	mould_type: (frm) => frm.trigger("check_all"),
	check_all(frm) {
		(frm.doc.batches || []).forEach((r) => check_batch(frm, r));
		frm.refresh_field("batches");
		const bad = (frm.doc.batches || []).filter((r) => r.result === "Out of Spec").length;
		frm.set_value("batch_count", (frm.doc.batches || []).length);
		frm.set_value("out_of_spec_count", bad);
		frm.set_value("status", bad ? "Out of Spec" : "OK");
	},
});

const SAND = { Moisture: "moisture_pct", Compactability: "compactability_pct", GCS: "gcs", Permeability: "permeability", "Mould Hardness": "mould_hardness" };
function check_batch(frm, r) {
	if (!frm._sand_limits) return;
	const fails = [];
	let any = false;
	Object.entries(SAND).forEach(([p, f]) => {
		const v = flt(r[f]);
		if (!v) return;
		any = true;
		const lim = frm._sand_limits.find((l) => l.mould_type === frm.doc.mould_type && l.parameter === p);
		if (!lim) return;
		if ((flt(lim.min_value) && v < flt(lim.min_value)) || (flt(lim.max_value) && v > flt(lim.max_value))) fails.push(p);
	});
	r.out_of_spec = fails.join(", ");
	r.result = fails.length ? "Out of Spec" : any ? "OK" : "";
}

frappe.ui.form.on("Sand Mix Batch", {
	batches_add(frm, cdt, cdn) {
		const rows = frm.doc.batches || [];
		frappe.model.set_value(cdt, cdn, "batch_no", String(rows.length));
		frappe.model.set_value(cdt, cdn, "batch_time", frappe.datetime.now_time());
	},
	moisture_pct: (frm) => frm.trigger("check_all"),
	compactability_pct: (frm) => frm.trigger("check_all"),
	gcs: (frm) => frm.trigger("check_all"),
	permeability: (frm) => frm.trigger("check_all"),
	mould_hardness: (frm) => frm.trigger("check_all"),
	batches_remove: (frm) => frm.trigger("check_all"),
});
