frappe.pages["mar-board"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("MAR Board"),
		single_column: true,
	});
	page.main.addClass("frappe-card");
	page.mar_board = new MARBoard({ page });
};

class MARBoard {
	constructor({ page }) {
		this.page = page;
		this.$container = $('<div class="mar-board-container"></div>').appendTo(page.main);
		this._setup_filters();
		this.refresh();
		this._start_auto_refresh();
		frappe.realtime.on("mar_missed_alert", () => this.refresh());
		frappe.realtime.on("ipd_order_notification", () => this.refresh());
	}

	_setup_filters() {
		this.ward_filter = this.page.add_field({
			fieldtype: "Link", fieldname: "ward", label: __("Ward"),
			options: "Hospital Ward", change: () => this.refresh(), reqd: 1,
		});
		this.date_filter = this.page.add_field({
			fieldtype: "Date", fieldname: "date", label: __("Date"),
			default: frappe.datetime.get_today(), change: () => this.refresh(),
		});
		this.shift_filter = this.page.add_field({
			fieldtype: "Select", fieldname: "shift", label: __("Shift"),
			options: "\nMorning\nAfternoon\nNight", change: () => this.refresh(),
		});
		this.page.add_inner_button(__("Refresh"), () => this.refresh());
	}

	refresh() {
		const ward = this.ward_filter?.get_value();
		if (!ward) {
			this.$container.html(
				`<div class="text-muted text-center" style="padding:40px;">${__("Select a ward to view the MAR board.")}</div>`
			);
			return;
		}

		frappe.call({
			method: "alcura_ipd_ext.api.mar.get_ward_mar_board",
			args: {
				ward,
				date: this.date_filter?.get_value() || undefined,
				shift: this.shift_filter?.get_value() || undefined,
			},
			callback: (r) => {
				this._render(r.message || {});
			},
		});
	}

	_render(data) {
		if (!data.patients || !data.patients.length) {
			this.$container.html(
				`<div class="text-muted text-center" style="padding:40px;">${__("No medication entries for this ward/shift.")}</div>`
			);
			return;
		}

		const summary = this._build_summary(data);
		const patients_html = data.patients.map((p) => this._build_patient_section(p)).join("");

		this.$container.html(`
			${summary}
			<div class="mar-patients">${patients_html}</div>
		`);

		this._bind_actions();
	}

	_build_summary(data) {
		const sc = data.status_counts || {};
		const items = [
			{ label: __("Total"), count: data.total || 0, cls: "" },
			{ label: __("Given"), count: sc["Given"] || 0, cls: "green" },
			{ label: __("Scheduled"), count: sc["Scheduled"] || 0, cls: "blue" },
			{ label: __("Held"), count: sc["Held"] || 0, cls: "yellow" },
			{ label: __("Delayed"), count: sc["Delayed"] || 0, cls: "orange" },
			{ label: __("Missed"), count: sc["Missed"] || 0, cls: "red" },
			{ label: __("Refused"), count: sc["Refused"] || 0, cls: "grey" },
		];

		const pills = items.map((i) =>
			`<span class="indicator-pill ${i.cls}" style="margin:0 4px;">${i.label}: <strong>${i.count}</strong></span>`
		).join("");

		return `<div class="mar-summary" style="padding:10px 12px;background:var(--bg-light-gray);border-bottom:1px solid var(--border-color);">
			${pills}
		</div>`;
	}

	_build_patient_section(patient) {
		const time_slots = this._group_by_time(patient.entries);
		const slot_keys = Object.keys(time_slots).sort();

		let cells = "";
		for (const slot of slot_keys) {
			const entries = time_slots[slot];
			const pills = entries.map((e) => this._build_med_pill(e)).join(" ");
			cells += `<div class="mar-time-slot" style="display:inline-block;vertical-align:top;min-width:120px;padding:4px 8px;border-right:1px solid var(--border-color);">
				<div class="text-muted" style="font-size:11px;font-weight:bold;">${slot}</div>
				<div style="margin-top:4px;">${pills}</div>
			</div>`;
		}

		return `<div class="mar-patient-row" style="border:1px solid var(--border-color);margin-top:8px;">
			<div style="padding:6px 12px;background:var(--bg-light-gray);border-bottom:1px solid var(--border-color);">
				<strong>${frappe.utils.escape_html(patient.patient_name || patient.patient)}</strong>
				${patient.bed ? ` | ${__("Bed")}: ${patient.bed}` : ""}
				<a href="/app/inpatient-record/${patient.inpatient_record}" class="btn btn-xs btn-default pull-right">${__("Chart")}</a>
			</div>
			<div style="padding:8px;overflow-x:auto;white-space:nowrap;">
				${cells || `<span class="text-muted">${__("No entries")}</span>`}
			</div>
		</div>`;
	}

	_group_by_time(entries) {
		const groups = {};
		for (const e of entries) {
			const dt = moment(e.scheduled_time);
			const slot = dt.format("HH:mm");
			if (!groups[slot]) groups[slot] = [];
			groups[slot].push(e);
		}
		return groups;
	}

	_build_med_pill(entry) {
		const status_colors = {
			Scheduled: "grey",
			Given: "green",
			Held: "yellow",
			Refused: "dark-grey",
			Missed: "red",
			Delayed: "orange",
			"Self-Administered": "green",
		};
		const color = status_colors[entry.administration_status] || "grey";
		const clickable = ["Scheduled", "Delayed"].includes(entry.administration_status)
			? `cursor:pointer;` : "";
		const data_attr = clickable ? `data-entry="${entry.name}"` : "";

		return `<span class="indicator-pill ${color} mar-pill" style="display:inline-block;margin:2px;font-size:11px;${clickable}" ${data_attr} title="${entry.administration_status}">
			${frappe.utils.escape_html(entry.medication_name || "")}
			<small>${entry.dose || ""}</small>
		</span>`;
	}

	_bind_actions() {
		const self = this;

		this.$container.find(".mar-pill[data-entry]").on("click", function () {
			const entry_name = $(this).data("entry");
			_show_mar_action_dialog(entry_name, self);
		});
	}

	_start_auto_refresh() {
		this._refresh_interval = setInterval(() => this.refresh(), 60000);
	}

	destroy() {
		if (this._refresh_interval) clearInterval(this._refresh_interval);
	}
}

function _show_mar_action_dialog(entry_name, board) {
	const d = new frappe.ui.Dialog({
		title: __("Medication Administration"),
		fields: [
			{
				fieldtype: "Select", fieldname: "action", label: __("Action"),
				options: "Given\nHeld\nRefused\nDelayed\nSelf-Administered", reqd: 1,
			},
			{
				fieldtype: "Small Text", fieldname: "hold_reason", label: __("Hold Reason"),
				depends_on: "eval:doc.action === 'Held'",
				mandatory_depends_on: "eval:doc.action === 'Held'",
			},
			{
				fieldtype: "Small Text", fieldname: "refusal_reason", label: __("Refusal Reason"),
				depends_on: "eval:doc.action === 'Refused'",
				mandatory_depends_on: "eval:doc.action === 'Refused'",
			},
			{
				fieldtype: "Small Text", fieldname: "delay_reason", label: __("Delay Reason"),
				depends_on: "eval:doc.action === 'Delayed'",
				mandatory_depends_on: "eval:doc.action === 'Delayed'",
			},
			{
				fieldtype: "Int", fieldname: "delay_minutes", label: __("Delay (Minutes)"),
				depends_on: "eval:doc.action === 'Delayed'",
			},
			{ fieldtype: "Data", fieldname: "site", label: __("Administration Site") },
			{ fieldtype: "Link", fieldname: "witness", label: __("Witness"), options: "User" },
			{ fieldtype: "Small Text", fieldname: "notes", label: __("Notes") },
		],
		primary_action_label: __("Record"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.mar.administer_medication",
				args: {
					mar_entry: entry_name,
					administration_status: values.action,
					hold_reason: values.hold_reason || undefined,
					refusal_reason: values.refusal_reason || undefined,
					delay_reason: values.delay_reason || undefined,
					delay_minutes: values.delay_minutes || undefined,
					site: values.site || undefined,
					witness: values.witness || undefined,
					notes: values.notes || undefined,
				},
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Recorded."), indicator: "green" });
					board.refresh();
				},
			});
		},
	});
	d.show();
}
