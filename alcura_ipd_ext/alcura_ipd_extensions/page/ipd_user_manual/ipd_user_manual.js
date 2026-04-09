frappe.pages["ipd-user-manual"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("IPD User Manual"),
		single_column: true,
	});

	page.main.addClass("frappe-card");

	const $container = $(`
		<div class="ipd-manual-container" style="padding: 30px; max-width: 960px; margin: 0 auto;">
			<div class="text-center text-muted" style="padding: 60px 0;">
				${__("Loading manual...")}
			</div>
		</div>
	`).appendTo(page.main);

	page.set_secondary_action(__("Print"), () => {
		const content = $container.find(".ipd-manual-content").html();
		const win = window.open("", "_blank");
		win.document.write(`
			<html>
			<head>
				<title>IPD User Manual</title>
				<style>
					body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
						   max-width: 800px; margin: 40px auto; padding: 0 20px; font-size: 13px;
						   line-height: 1.6; color: #333; }
					h1 { font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 8px; }
					h2 { font-size: 18px; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
					h3 { font-size: 15px; margin-top: 20px; }
					table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }
					th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
					th { background: #f5f5f5; font-weight: 600; }
					code { background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
					pre { background: #f8f8f8; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
					@media print { body { font-size: 11px; } }
				</style>
			</head>
			<body>${content}</body>
			</html>
		`);
		win.document.close();
		win.print();
	}, "printer");

	_add_toc_navigation(page);

	frappe.call({
		method: "alcura_ipd_ext.alcura_ipd_extensions.page.ipd_user_manual.ipd_user_manual.get_manual_html",
		callback(r) {
			if (!r.message) {
				$container.html(`<div class="text-muted text-center" style="padding: 60px 0;">
					${__("Manual content not available.")}
				</div>`);
				return;
			}

			$container.html(`<div class="ipd-manual-content">${r.message}</div>`);
			_apply_styles($container);
			_build_toc($container, page);
		},
	});
};

function _add_toc_navigation(page) {
	page.add_field({
		fieldtype: "Select",
		fieldname: "section",
		label: __("Jump to Section"),
		options: [{ label: __("Loading..."), value: "" }],
		change() {
			const val = page.fields_dict.section.get_value();
			if (!val) return;
			const el = document.getElementById(val);
			if (el) {
				el.scrollIntoView({ behavior: "smooth", block: "start" });
			}
		},
	});
}

function _build_toc($container, page) {
	const headings = $container.find("h2");
	const options = [{ label: __("-- Select Section --"), value: "" }];

	headings.each(function (i) {
		const $h = $(this);
		const id = "manual-section-" + i;
		$h.attr("id", id);
		options.push({ label: $h.text(), value: id });
	});

	const field = page.fields_dict.section;
	if (field) {
		field.df.options = options;
		field.refresh();
	}
}

function _apply_styles($container) {
	$container.find("table").addClass("table table-bordered table-sm");
	$container.find("h1").first().css({
		"font-size": "24px",
		"font-weight": "700",
		"border-bottom": "2px solid var(--primary)",
		"padding-bottom": "10px",
		"margin-bottom": "20px",
	});
	$container.find("h2").css({
		"font-size": "19px",
		"font-weight": "600",
		"margin-top": "36px",
		"padding-bottom": "6px",
		"border-bottom": "1px solid var(--border-color)",
	});
	$container.find("h3").css({
		"font-size": "16px",
		"font-weight": "600",
		"margin-top": "24px",
	});
	$container.find("pre").css({
		"background": "var(--bg-light-gray)",
		"padding": "12px",
		"border-radius": "6px",
		"overflow-x": "auto",
		"font-size": "13px",
	});
	$container.find("code").css({
		"font-size": "13px",
	});
}
