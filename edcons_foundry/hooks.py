app_name = "edcons_foundry"
app_title = "Edcons Foundry"
app_publisher = "Edcons (MKS) Castings"
app_description = "Shop-floor and lab logs for a DI / CI foundry on ERPNext"
app_email = "info@edconscastings.com"
app_license = "mit"
required_apps = ["erpnext"]

add_to_apps_screen = [
	{"name": "edcons_foundry", "logo": "/assets/edcons_foundry/images/foundry.svg", "title": "Foundry", "route": "/app/shop-floor"}
]

app_include_js = "edcons_foundry.bundle.js"
app_include_css = "edcons_foundry.bundle.css"

doctype_js = {"Work Order": "public/js/work_order.js"}

before_install = "edcons_foundry.install.before_install"
after_install = "edcons_foundry.install.after_install"
after_migrate = "edcons_foundry.install.after_migrate"

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Edcons Foundry"]]},
]
