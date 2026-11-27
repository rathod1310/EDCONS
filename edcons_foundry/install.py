import frappe

REASONS = [
	("Shrinkage", "Melting"), ("Blow Hole", "Moulding"), ("Sand Inclusion", "Moulding"), ("Sandfall", "Moulding"),
	("Cold Shut", "Pouring"), ("Misrun", "Pouring"), ("Short Pour", "Pouring"), ("Mismatch", "Moulding"),
	("Core", "Moulding"), ("Crack", "Melting"), ("Slag Inclusion", "Melting"), ("Key Hole Sand", "Finishing"),
	("Fitment / Rocking", "Finishing"), ("Frame Height", "Finishing"), ("Dimensional", "Pattern"),
	("Overweight", "Pattern"), ("Underweight", "Pattern"), ("Grinding Damage", "Finishing"), ("Other", "Other"),
]
# PR 46 limits; PR 32 prints different ones, confirm with the client
SAND = [
	("Machine", "Moisture", 2.8, 3.6), ("Machine", "GCS", 1000, 1500), ("Machine", "Compactability", 38, 45),
	("Machine", "Permeability", 155, 200), ("Machine", "Mould Hardness", 80, 0),
	("Hand", "Moisture", 3.3, 4.5), ("Hand", "GCS", 500, 0), ("Hand", "Compactability", 40, 55),
	("Hand", "Permeability", 150, 185), ("Hand", "Mould Hardness", 70, 90),
]
# BOM operation -> log that completes it; only operations that exist are added
OPS = [
	("Melting", "Production Entry", "Total"), ("Sand Mixing", "Production Entry", "Total"),
	("Moulding", "Production Entry", "Total"), ("Pouring", "Production Entry", "Total"),
	("Knockout", "Shot Blast Log", "Total"), ("Shot Blasting", "Shot Blast Log", "Total"),
	("Fettling", "Finishing Log", "Total"), ("Grinding", "Finishing Log", "Total"),
	("Inspection", "Visual Inspection", "Good"),
]


def _refresh_module_map():
	# apps.txt edited by hand leaves a stale module map in Redis; then no DocTypes get synced
	try:
		frappe.clear_cache()
	except Exception:
		pass
	cache = frappe.cache() if callable(frappe.cache) else frappe.cache
	for key in ("app_modules", "module_app", "app_hooks", "installed_apps", "all_apps"):
		try:
			cache.delete_value(key)
		except Exception:
			pass
	for attr in ("app_modules", "module_app"):
		if hasattr(frappe.local, attr):
			setattr(frappe.local, attr, None)
	frappe.setup_module_map()


def before_install():
	_refresh_module_map()
	if "edcons_foundry" not in (frappe.local.app_modules or {}):
		frappe.throw("edcons_foundry is not in the module map. Run: bench --site <site> clear-cache, then install again.")


def after_install():
	if not frappe.db.exists("DocType", "Rejection Reason"):
		frappe.throw("edcons_foundry DocTypes were not synced. Run: bench --site <site> clear-cache, then "
			"bench --site <site> install-app edcons_foundry --force")
	for name, group in REASONS:
		if not frappe.db.exists("Rejection Reason", name):
			frappe.get_doc({"doctype": "Rejection Reason", "reason_name": name, "defect_group": group}).insert(ignore_permissions=True)
	s = frappe.get_single("Foundry Settings")
	if not s.sand_limits:
		for mt, p, lo, hi in SAND:
			s.append("sand_limits", {"mould_type": mt, "parameter": p, "min_value": lo, "max_value": hi})
	if not s.company:
		s.company = frappe.defaults.get_global_default("company")
	s.weight_tolerance_pct = s.weight_tolerance_pct or 3
	s.kwh_target = s.kwh_target or 630
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)
	after_migrate()


def after_migrate():
	if not frappe.db.exists("DocType", "Foundry Settings"):
		return
	s = frappe.get_single("Foundry Settings")
	have = {r.operation for r in s.operation_map}
	added = False
	for op, src, basis in OPS:
		if op not in have and frappe.db.exists("Operation", op):
			s.append("operation_map", {"operation": op, "posted_from": src, "qty_basis": basis})
			added = True
	if added:
		s.flags.ignore_mandatory = True
		s.save(ignore_permissions=True)
