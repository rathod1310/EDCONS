// Shared shop-floor helpers: flow bar, next-step buttons, link filters, shift default.
frappe.provide("edcons_foundry");

edcons_foundry.FLOW = [
	{ doctype: "Furnace Heat", label: "Melt", pr: "PR 2 · CI 1" },
	{ doctype: "Sand Mix Log", label: "Sand", pr: "PR 32" },
	{ doctype: "Production Entry", label: "Mould & Pour", pr: "PR 1 · PR 4" },
	{ doctype: "Shot Blast Log", label: "Shot Blast", pr: "PR 16 · PR 29" },
	{ doctype: "Finishing Log", label: "Finish", pr: "PR 19 · PR 20" },
	{ doctype: "Visual Inspection", label: "Inspect", pr: "PR 21" },
	{ doctype: "Load Test Report", label: "Load Test", pr: "PR 33" },
	{ doctype: "Rejection Report", label: "Rejections", pr: "" },
];

// what each document can make next, after submit
edcons_foundry.NEXT = {
	"Furnace Heat": ["Production Entry", "Load Test Report"],
	"Production Entry": ["Shot Blast Log", "Finishing Log"],
	"Shot Blast Log": ["Finishing Log"],
	"Finishing Log": ["Visual Inspection"],
	"Visual Inspection": ["Load Test Report"],
};

edcons_foundry.current_shift = function () {
	const h = new Date().getHours();
	return h >= 8 && h < 20 ? "Day" : "Night";
};

edcons_foundry.heat_of = function (frm) {
	if (frm.doc.doctype === "Furnace Heat") return frm.doc.__islocal ? null : frm.doc.name;
	const row = (frm.doc.items || []).find((r) => r.heat);
	return row ? row.heat : null;
};

edcons_foundry.render_flow_bar = function (frm) {
	frm.$wrapper.find(".ef-flow").remove();
	const heat = edcons_foundry.heat_of(frm);
	const chips = edcons_foundry.FLOW.map((s, i) => {
		const active = s.doctype === frm.doctype ? " ef-active" : "";
		return `<button type="button" class="ef-chip${active}" data-dt="${s.doctype}">
			<span class="ef-num">${i + 1}</span><span class="ef-lbl">${__(s.label)}</span>
			${s.pr ? `<span class="ef-pr">${s.pr}</span>` : ""}</button>`;
	}).join('<span class="ef-sep" aria-hidden="true">›</span>');
	const trace = heat ? `<button type="button" class="ef-trace">${__("Trace heat")} ${frappe.utils.escape_html(heat)}</button>` : "";
	const $bar = $(`<div class="ef-flow"><a class="ef-home" href="/app/shop-floor">${__("Shop Floor")}</a>${chips}${trace}</div>`);
	$bar.on("click", ".ef-chip", function () {
		const dt = $(this).attr("data-dt");
		if (dt !== frm.doctype) frappe.set_route("List", dt);
	});
	$bar.on("click", ".ef-trace", () => frappe.set_route("heat-trace", heat));
	frm.$wrapper.find(".form-layout").first().before($bar);
};

edcons_foundry.make_next = function (frm, target) {
	frappe.call({
		method: "edcons_foundry.api.make_next",
		args: { source_doctype: frm.doctype, source_name: frm.doc.name, target_doctype: target },
		freeze: true,
		callback(r) {
			if (!r.message) return;
			const doc = frappe.model.sync(r.message)[0];
			frappe.set_route("Form", doc.doctype, doc.name);
		},
	});
};

edcons_foundry.add_buttons = function (frm) {
	if (frm.doc.docstatus === 1) {
		(edcons_foundry.NEXT[frm.doctype] || []).forEach((target) => {
			frm.add_custom_button(__(target), () => edcons_foundry.make_next(frm, target), __("Next step"));
		});
		if (frm.doc.erp_posting_status && frm.doc.erp_posting_status.includes("⚠")) {
			frm.add_custom_button(__("Retry ERP Posting"), () => {
				frappe.call({
					method: "edcons_foundry.api.retry_posting",
					args: { doctype: frm.doctype, name: frm.doc.name },
					freeze: true,
				}).then(() => frm.reload_doc());
			});
		}
		["rejection_report", "return_metal_entry", "charge_entry"].forEach((f) => {
			if (frm.doc[f]) {
				const dt = f === "rejection_report" ? "Rejection Report" : "Stock Entry";
				frm.add_custom_button(__(frappe.meta.get_label(frm.doctype, f)), () => frappe.set_route("Form", dt, frm.doc[f]), __("View"));
			}
		});
	}
	if (frm.doc.erp_posting_status) {
		const warn = frm.doc.erp_posting_status.includes("⚠");
		frm.dashboard.set_headline_alert(
			`<div class="small">${frappe.utils.escape_html(frm.doc.erp_posting_status).replace(/\n/g, "<br>")}</div>`,
			warn ? "orange" : "green"
		);
	}
};

edcons_foundry.set_filters = function (frm, table) {
	table = table || "items";
	if (!frm.fields_dict[table]) return;
	const grid = frm.fields_dict[table].grid;
	if (frappe.meta.has_field(grid.doctype, "heat")) {
		frm.set_query("heat", table, () => ({ filters: { docstatus: 1 } }));
	}
	if (frappe.meta.has_field(grid.doctype, "work_order")) {
		frm.set_query("work_order", table, (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { docstatus: 1, status: ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]] };
			if (row.item_code) filters.production_item = row.item_code;
			return { filters };
		});
	}
};

edcons_foundry.setup = function (frm, opts) {
	opts = opts || {};
	if (frm.is_new()) {
		if (frm.fields_dict.shift && !frm.doc.shift) frm.set_value("shift", edcons_foundry.current_shift());
	}
	edcons_foundry.set_filters(frm, "items");
	(opts.tables || []).forEach((t) => edcons_foundry.set_filters(frm, t));
	edcons_foundry.render_flow_bar(frm);
	edcons_foundry.add_buttons(frm);
};

// copy the previous row's heat, moulder, item and work order into a new row
edcons_foundry.copy_previous_row = function (frm, cdt, cdn, fields) {
	const rows = frm.doc.items || [];
	const row = locals[cdt][cdn];
	const prev = rows[rows.indexOf(row) - 1];
	if (!prev) return;
	fields.forEach((f) => {
		if (prev[f] && !row[f]) frappe.model.set_value(cdt, cdn, f, prev[f]);
	});
};

edcons_foundry.sum = function (rows, field) {
	return (rows || []).reduce((a, r) => a + flt(r[field]), 0);
};
