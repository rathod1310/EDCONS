frappe.pages["shop-floor"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Shop Floor"), single_column: true });
	page.set_primary_action(__("Refresh"), () => hub.load(), "refresh");
	page.add_menu_item(__("Foundry Settings"), () => frappe.set_route("Form", "Foundry Settings"));
	const hub = new ShopFloorHub(page);
	wrapper.hub = hub;
};
frappe.pages["shop-floor"].on_page_show = function (wrapper) {
	wrapper.hub && wrapper.hub.load();
};

const STAGES = [
	{ dt: "Furnace Heat", title: "1 · Melt", pr: "Induction charging PR 2, Cupola CI 1, spectro, kWh", who: "Melter" },
	{ dt: "Sand Mix Log", title: "2 · Sand", pr: "Mixer batches PR 32, limits PR 46", who: "Mixer operator" },
	{ dt: "Production Entry", title: "3 · Mould & Pour", pr: "Production PR 1 / CI 2, pouring velocity PR 4", who: "Moulding supervisor" },
	{ dt: "Shot Blast Log", title: "4 · Shot Blast", pr: "Shot blasting PR 16, parts PR 29", who: "Shot blast operator" },
	{ dt: "Finishing Log", title: "5 · Finish", pr: "Grinding PR 20, casting weights PR 19", who: "Finishing supervisor" },
	{ dt: "Visual Inspection", title: "6 · Inspect", pr: "Visual inspection PR 21", who: "Inspector" },
	{ dt: "Load Test Report", title: "7 · Load Test", pr: "Load test certificate PR 33", who: "Lab" },
	{ dt: "Rejection Report", title: "Rejections", pr: "Reasons, stage and rejection %", who: "Quality" },
];
const MORE = [
	["Quality Inspection", "Raw material test PR 34"], ["Pattern", "Pattern list PR 48"], ["Furnace", "Furnaces and lining"],
	["Rejection Reason", "Defect master"], ["Work Order", "Open Work Orders"], ["Job Card", "Job Cards"],
];

class ShopFloorHub {
	constructor(page) {
		this.page = page;
		this.$b = $(`<div class="ef-hub">
			<div class="ef-kpis"></div>
			<div class="ef-search"></div>
			<div class="ef-section">${__("Start here: pick your stage")}</div>
			<div class="ef-stages"></div>
			<div class="ef-section">${__("Drafts waiting to be submitted")}</div>
			<div class="ef-wrap ef-drafts"></div>
			<div class="ef-section">${__("Latest heats")}</div>
			<div class="ef-wrap ef-heats"></div>
			<div class="ef-section">${__("Masters and standard documents")}</div>
			<div class="ef-stages ef-more"></div>
		</div>`).appendTo(page.main);
		this.make_search();
		this.make_stages();
		this.load();
		this.timer = setInterval(() => { if (frappe.get_route_str() === "shop-floor") this.load(); }, 60000);
	}
	make_search() {
		const $s = this.$b.find(".ef-search");
		this.heat = frappe.ui.form.make_control({
			parent: $s, df: { fieldtype: "Link", options: "Furnace Heat", label: __("Trace a heat"), placeholder: "HT-26-11-014" },
			render_input: true,
		});
		$(`<button class="btn btn-primary ef-btn">${__("Trace")}</button>`).appendTo($s).on("click", () => {
			const h = this.heat.get_value();
			if (h) frappe.set_route("heat-trace", h);
		});
	}
	make_stages() {
		const card = (dt, title, pr, who, primary) => {
			const $c = $(`<div class="ef-stage">
				<h4>${__(title)}</h4><div class="pr">${__(pr)}</div>${who ? `<div class="pr">${__("Filled by")}: ${__(who)}</div>` : ""}
				<div class="acts">
					<button class="btn ${primary ? "btn-primary" : "btn-default"} ef-btn ef-new">${__("New")}</button>
					<button class="btn btn-default ef-btn ef-list">${__("List")}</button>
				</div></div>`);
			$c.find(".ef-new").on("click", () => frappe.new_doc(dt));
			$c.find(".ef-list").on("click", () => frappe.set_route("List", dt));
			return $c;
		};
		const $s = this.$b.find(".ef-stages").first();
		STAGES.forEach((s) => frappe.model.can_read(s.dt) && $s.append(card(s.dt, s.title, s.pr, s.who, true)));
		const $m = this.$b.find(".ef-more");
		MORE.forEach(([dt, pr]) => frappe.model.can_read(dt) && $m.append(card(dt, dt, pr, null, false)));
	}
	load() {
		frappe.call("edcons_foundry.api.get_hub_data").then(({ message: d }) => d && this.render(d));
	}
	render(d) {
		const k = d.kpis, n = (v, p = 0) => format_number(v || 0, null, p);
		const kpi = (v, l, bad) => `<div class="ef-kpi${bad ? " bad" : ""}"><div class="v">${v}</div><div class="l">${l}</div></div>`;
		this.$b.find(".ef-kpis").html([
			kpi(n(k.heats), __("Heats today")),
			kpi(n(k.melt_kg / 1000, 2) + " t", __("Metal melted")),
			kpi(n(k.kwh_per_tonne), __("kWh per tonne (target {0})", [n(k.kwh_target)]), k.kwh_target && k.kwh_per_tonne > k.kwh_target),
			kpi(n(k.cast_nos), __("Castings poured, {0} kg", [n(k.cast_kg)])),
			kpi(n(k.rejection_pct, 1) + "%", __("Rejection ({0} pcs)", [n(k.rejected)]), k.rejection_pct > 5),
			kpi(n(k.sand_out_of_spec), __("Sand batches out of spec"), k.sand_out_of_spec > 0),
			kpi(n(k.weight_alerts), __("Casting weight alerts"), k.weight_alerts > 0),
		].join(""));
		const esc = frappe.utils.escape_html;
		const link = (dt, name) => `<a href="/app/${frappe.router.slug(dt)}/${encodeURIComponent(name)}">${esc(name)}</a>`;
		this.$b.find(".ef-drafts").html(d.drafts.length ? `<table class="ef-table"><thead><tr>
			<th>${__("Document")}</th><th>${__("Type")}</th><th>${__("Date")}</th><th>${__("By")}</th></tr></thead><tbody>
			${d.drafts.map((r) => `<tr><td>${link(r.doctype, r.name)}</td><td>${__(r.doctype)}</td>
				<td>${frappe.datetime.str_to_user(r.posting_date)}</td><td>${r.mine ? __("You") : esc(frappe.user.full_name(r.owner))}</td></tr>`).join("")}
			</tbody></table>` : `<div class="ef-empty">${__("No drafts. Everything is submitted.")}</div>`);
		this.$b.find(".ef-heats").html(d.recent_heats.length ? `<table class="ef-table"><thead><tr>
			<th>${__("Heat")}</th><th>${__("Date")}</th><th>${__("Shift")}</th><th>${__("Furnace")}</th><th>${__("Grade")}</th>
			<th>${__("Charge kg")}</th><th>${__("kWh/t")}</th><th>${__("Poured")}</th><th>${__("Yield %")}</th><th>${__("Lab")}</th><th></th></tr></thead><tbody>
			${d.recent_heats.map((h) => `<tr><td>${link("Furnace Heat", h.name)}${h.docstatus ? "" : ` <span class="indicator-pill red">${__("Draft")}</span>`}</td>
				<td>${frappe.datetime.str_to_user(h.posting_date)}</td><td>${esc(h.shift || "")}</td><td>${esc(h.furnace || "")}</td>
				<td>${esc(h.grade || "")}</td><td>${n(h.total_charge_kg)}</td><td>${n(h.kwh_per_tonne)}</td><td>${n(h.poured_nos)}</td>
				<td>${n(h.yield_pct, 1)}</td><td>${esc(h.chemistry_status || "")}</td>
				<td><a href="/app/heat-trace/${encodeURIComponent(h.name)}">${__("Trace")}</a></td></tr>`).join("")}
			</tbody></table>` : `<div class="ef-empty">${__("No heats yet.")}</div>`);
	}
}
