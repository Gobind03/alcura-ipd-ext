// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// Client-side enhancements for the standard Inpatient Record form.
// US-D1: Admission order details display
// US-D2: Admission checklist integration
// US-D3: Print labels dropdown
// US-B3: Allocate Bed
// US-B4: Transfer Bed
// US-C3: Eligibility verification UI
// US-E1: Intake assessment integration
// US-E2: Nursing risk indicators
// US-E3: Consultant admission notes
// US-E5: Problem list and round notes

frappe.ui.form.on("Inpatient Record", {
	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;

		_show_admission_order_banner(frm);
		_show_nursing_risk_banners(frm);

		if (frm.doc.status === "Admission Scheduled") {
			_show_eligibility_banner(frm);
			_add_eligibility_check_button(frm);
			_show_checklist_banner(frm);
			_add_checklist_button(frm);
			_add_allocate_bed_button(frm);
			_show_intake_banner(frm);
			_add_intake_button(frm);
		}

		if (frm.doc.status === "Admitted") {
			_add_transfer_bed_button(frm);
			_add_print_labels_buttons(frm);
			_show_intake_banner(frm);
			_add_intake_button(frm);
			_add_recalculate_risk_button(frm);
			_add_clinical_note_buttons(frm);
			_add_charting_buttons(frm);
			_show_charting_banner(frm);
			_show_problem_list_banner(frm);
			_add_problem_list_buttons(frm);
			_add_round_note_button(frm);
			_add_order_buttons(frm);
			_show_orders_banner(frm);
			_add_tpa_billing_buttons(frm);
			_show_tpa_billing_banner(frm);
			_show_discharge_journey_banner(frm);
			_add_discharge_journey_buttons(frm);
		}
	},
});

// ── US-D1: Admission Order Details ──────────────────────────────────

function _show_admission_order_banner(frm) {
	if (!frm.doc.custom_requesting_encounter) return;

	const priority = frm.doc.custom_admission_priority || "Routine";
	const ward = frm.doc.custom_requested_ward || __("Not specified");
	const los = frm.doc.custom_expected_los_days || "-";
	const enc_link = `<a href="/app/patient-encounter/${frm.doc.custom_requesting_encounter}">${frm.doc.custom_requesting_encounter}</a>`;

	const priority_colors = { Emergency: "red", Urgent: "orange", Routine: "blue" };
	const color = priority_colors[priority] || "blue";

	frm.dashboard.add_comment(
		__("Admission ordered from {0} — Priority: {1}, Ward: {2}, LOS: {3} days", [
			enc_link,
			`<strong>${priority}</strong>`,
			`<strong>${ward}</strong>`,
			los,
		]),
		color,
		true
	);
}

// ── US-D2: Admission Checklist ──────────────────────────────────────

function _show_checklist_banner(frm) {
	if (!frm.doc.custom_admission_checklist) return;

	const status = frm.doc.custom_checklist_status || "Incomplete";
	const color_map = {
		Incomplete: "orange",
		Complete: "green",
		Overridden: "blue",
	};
	const color = color_map[status] || "orange";
	const link = `<a href="/app/admission-checklist/${frm.doc.custom_admission_checklist}">${frm.doc.custom_admission_checklist}</a>`;

	frm.dashboard.add_comment(
		__("Admission Checklist: {0} — Status: {1}", [link, `<strong>${status}</strong>`]),
		color,
		true
	);
}

function _add_checklist_button(frm) {
	if (frm.doc.custom_admission_checklist) {
		frm.add_custom_button(__("View Checklist"), () => {
			frappe.set_route("Form", "Admission Checklist", frm.doc.custom_admission_checklist);
		}, __("Actions"));
	} else {
		frm.add_custom_button(__("Create Checklist"), () => {
			frappe.call({
				method: "alcura_ipd_ext.api.admission.create_admission_checklist",
				args: { inpatient_record: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating checklist..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Admission Checklist {0} created.", [r.message.checklist]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		}, __("Actions"));
	}
}

// ── US-D3: Print Labels ─────────────────────────────────────────────

function _add_print_labels_buttons(frm) {
	const formats = [
		{ label: __("Wristband Label"), format: "IPD Wristband Label" },
		{ label: __("Bed Tag"), format: "IPD Bed Tag" },
		{ label: __("File Cover"), format: "IPD File Cover" },
	];

	for (const fmt of formats) {
		frm.add_custom_button(fmt.label, () => {
			const url = frappe.urllib.get_full_url(
				`/api/method/frappe.utils.print_format.download_pdf?doctype=Inpatient+Record&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(fmt.format)}`
			);
			window.open(url, "_blank");
		}, __("Print Labels"));
	}
}

// ── US-C3: Eligibility Verification ─────────────────────────────────

function _show_eligibility_banner(frm) {
	if (!frm.doc.custom_patient_payer_profile) return;

	frappe.call({
		method: "alcura_ipd_ext.api.admission.check_eligibility_for_admission",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const result = r.message;

			const color_map = {
				Verified: "green",
				Conditional: "blue",
				Cash: "green",
				Skipped: "light",
				"No Profile": "light",
				"Not Verified": "orange",
			};
			const color = color_map[result.status] || "orange";
			const icon = result.eligible ? "check" : "alert-circle";
			const css_class = result.eligible ? `alert-${color}` : "alert-warning";

			const html = `<div class="alert ${css_class} d-flex align-items-center"
				style="margin-bottom: 0; padding: 8px 12px;">
				<span>${frappe.utils.icon(icon, "sm")} &nbsp;</span>
				<span><strong>${__("Eligibility")}:</strong> ${frappe.utils.escape_html(result.message)}</span>
			</div>`;

			const wrapper = frm.fields_dict.custom_payer_eligibility_check
				? frm.fields_dict.custom_payer_eligibility_check.$wrapper
				: null;
			if (wrapper) {
				wrapper.closest(".frappe-control").before(
					$(`<div class="eligibility-banner">${html}</div>`)
				);
			} else {
				frm.dashboard.add_comment(result.message, color, true);
			}
		},
	});
}

function _add_eligibility_check_button(frm) {
	if (!frm.doc.custom_patient_payer_profile) return;

	frm.add_custom_button(__("Create Eligibility Check"), () => {
		frappe.new_doc("Payer Eligibility Check", {
			patient: frm.doc.patient,
			patient_payer_profile: frm.doc.custom_patient_payer_profile,
			inpatient_record: frm.doc.name,
			company: frm.doc.company,
		});
	}, __("Actions"));
}

// ── US-B3: Allocate Bed ─────────────────────────────────────────────

function _add_allocate_bed_button(frm) {
	frm.add_custom_button(__("Allocate Bed"), () => {
		_run_preflight_then_allocate(frm);
	}, __("Actions"));
	frm.change_custom_button_type(__("Allocate Bed"), __("Actions"), "primary");
}

function _run_preflight_then_allocate(frm) {
	// US-D2: Check checklist completion before allocation
	if (frm.doc.custom_admission_checklist) {
		const status = frm.doc.custom_checklist_status;
		if (status === "Incomplete") {
			frappe.confirm(
				__("The Admission Checklist is still incomplete. Do you want to proceed with bed allocation anyway?"),
				() => _run_eligibility_then_allocate(frm)
			);
			return;
		}
	}
	_run_eligibility_then_allocate(frm);
}

function _run_eligibility_then_allocate(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.admission.check_eligibility_for_admission",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			const result = r.message || {};

			if (!result.eligible && result.enforcement === "Strict") {
				frappe.msgprint({
					title: __("Admission Blocked"),
					message: result.message,
					indicator: "red",
				});
				return;
			}

			if (!result.eligible && result.enforcement === "Advisory") {
				frappe.confirm(
					__("{0}<br><br>Do you want to proceed anyway?", [
						frappe.utils.escape_html(result.message),
					]),
					() => _open_bed_picker(frm)
				);
				return;
			}

			_open_bed_picker(frm);
		},
	});
}

function _open_bed_picker(frm) {
	_show_bed_picker(frm, {
		title: __("Allocate Bed for Admission"),
		on_submit(bed, reservation) {
			frappe.call({
				method: "alcura_ipd_ext.api.admission.allocate_bed",
				args: {
					inpatient_record: frm.doc.name,
					hospital_bed: bed,
					reservation: reservation || null,
				},
				freeze: true,
				freeze_message: __("Allocating bed..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Bed {0} allocated successfully.", [bed]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
}

// ── US-B4: Transfer Bed ─────────────────────────────────────────────

function _add_transfer_bed_button(frm) {
	frm.add_custom_button(__("Transfer Bed"), () => {
		_show_transfer_dialog(frm);
	}, __("Actions"));
}

function _show_transfer_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Transfer Patient to Another Bed"),
		size: "extra-large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "current_bed_info",
				options: _build_current_bed_html(frm),
			},
			{ fieldtype: "Section Break", label: __("Select Destination Bed") },
			{
				fieldtype: "Link",
				fieldname: "ward_filter",
				label: __("Filter by Ward"),
				options: "Hospital Ward",
				change() {
					_refresh_transfer_beds(d, frm);
				},
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "room_type_filter",
				label: __("Filter by Room Type"),
				options: "Healthcare Service Unit Type",
				get_query() {
					return { filters: { inpatient_occupancy: 1 } };
				},
				change() {
					_refresh_transfer_beds(d, frm);
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "HTML",
				fieldname: "bed_list_html",
			},
			{ fieldtype: "Section Break", label: __("Transfer Details") },
			{
				fieldtype: "Link",
				fieldname: "selected_bed",
				label: __("Destination Bed"),
				options: "Hospital Bed",
				reqd: 1,
				read_only: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "ordered_by",
				label: __("Ordered By Practitioner"),
				options: "Healthcare Practitioner",
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Reason for Transfer"),
				reqd: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Select",
				fieldname: "source_bed_action",
				label: __("Source Bed Action"),
				options: "Mark Dirty\nMark Vacant\nNo Change",
				default: "Mark Dirty",
			},
		],
		primary_action_label: __("Transfer"),
		primary_action(values) {
			if (!values.selected_bed) {
				frappe.msgprint(__("Please select a destination bed."));
				return;
			}
			if (!values.reason) {
				frappe.msgprint(__("Please provide a reason for the transfer."));
				return;
			}

			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.admission.transfer_patient",
				args: {
					inpatient_record: frm.doc.name,
					to_bed: values.selected_bed,
					reason: values.reason,
					ordered_by: values.ordered_by || null,
					source_bed_action: values.source_bed_action || null,
				},
				freeze: true,
				freeze_message: __("Transferring patient..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Patient transferred to {0}.", [values.selected_bed]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});

	_refresh_transfer_beds(d, frm);
	d.show();
}

function _build_current_bed_html(frm) {
	const bed = frm.doc.custom_current_bed || "-";
	const room = frm.doc.custom_current_room || "-";
	const ward = frm.doc.custom_current_ward || "-";
	return `<div class="alert alert-info" style="margin-bottom: 0;">
		<strong>${__("Current Location")}:</strong>
		${__("Bed")}: <strong>${bed}</strong> |
		${__("Room")}: <strong>${room}</strong> |
		${__("Ward")}: <strong>${ward}</strong>
	</div>`;
}

// ── Shared Bed Picker ───────────────────────────────────────────────

function _show_bed_picker(frm, opts) {
	let active_reservation = null;

	const d = new frappe.ui.Dialog({
		title: opts.title,
		size: "extra-large",
		fields: [
			{
				fieldtype: "Link",
				fieldname: "ward_filter",
				label: __("Filter by Ward"),
				options: "Hospital Ward",
				change() {
					_refresh_bed_list(d, frm);
				},
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "room_type_filter",
				label: __("Filter by Room Type"),
				options: "Healthcare Service Unit Type",
				get_query() {
					return { filters: { inpatient_occupancy: 1 } };
				},
				change() {
					_refresh_bed_list(d, frm);
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "HTML",
				fieldname: "bed_list_html",
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Link",
				fieldname: "selected_bed",
				label: __("Selected Bed"),
				options: "Hospital Bed",
				reqd: 1,
				read_only: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "reservation",
				label: __("Reservation"),
				options: "Bed Reservation",
			},
		],
		primary_action_label: __("Allocate"),
		primary_action(values) {
			if (!values.selected_bed) {
				frappe.msgprint(__("Please select a bed."));
				return;
			}
			d.hide();
			opts.on_submit(values.selected_bed, values.reservation);
		},
	});

	if (frm.doc.patient) {
		frappe.call({
			method: "alcura_ipd_ext.api.admission.get_active_reservation_for_patient",
			args: { patient: frm.doc.patient, company: frm.doc.company },
			async: false,
			callback(r) {
				if (r.message) {
					active_reservation = r.message;
					d.set_value("reservation", r.message.name);
					if (r.message.hospital_bed) {
						d.set_value("selected_bed", r.message.hospital_bed);
					}
					if (r.message.hospital_ward) {
						d.set_value("ward_filter", r.message.hospital_ward);
					}
				}
			},
		});
	}

	_refresh_bed_list(d, frm);
	d.show();
}

function _refresh_bed_list(dialog, frm) {
	const filters = {};
	const ward = dialog.get_value("ward_filter");
	const room_type = dialog.get_value("room_type_filter");
	if (ward) filters.ward = ward;
	if (room_type) filters.room_type = room_type;
	if (frm.doc.company) filters.company = frm.doc.company;

	frappe.call({
		method: "alcura_ipd_ext.api.admission.get_available_beds_for_admission",
		args: { filters },
		callback(r) {
			const beds = r.message || [];
			const html = _build_bed_table(beds, dialog, "selected_bed");
			dialog.fields_dict.bed_list_html.$wrapper.html(html);
			_attach_bed_click_handlers(dialog, "selected_bed");
		},
	});
}

function _refresh_transfer_beds(dialog, frm) {
	const filters = {};
	const ward = dialog.get_value("ward_filter");
	const room_type = dialog.get_value("room_type_filter");
	if (ward) filters.ward = ward;
	if (room_type) filters.room_type = room_type;
	if (frm.doc.company) filters.company = frm.doc.company;

	frappe.call({
		method: "alcura_ipd_ext.api.admission.get_available_beds_for_admission",
		args: { filters },
		callback(r) {
			const beds = r.message || [];
			const html = _build_bed_table(beds, dialog, "selected_bed");
			dialog.fields_dict.bed_list_html.$wrapper.html(html);
			_attach_bed_click_handlers(dialog, "selected_bed");
		},
	});
}

function _build_bed_table(beds, dialog, target_field) {
	if (!beds.length) {
		return `<div class="text-muted text-center" style="padding: 20px;">
			${__("No available beds found for the selected filters.")}
		</div>`;
	}

	let rows = beds.map((b) => {
		const availability_class = b.availability === "Available" ? "text-success" : "text-warning";
		return `<tr class="bed-row" data-bed="${b.bed}" style="cursor: pointer;">
			<td><strong>${b.bed}</strong></td>
			<td>${b.bed_label || b.bed_number || ""}</td>
			<td>${b.room || ""}</td>
			<td>${b.ward_name || b.ward || ""}</td>
			<td>${b.room_type || ""}</td>
			<td>${b.floor || ""}</td>
			<td class="${availability_class}">${b.availability || ""}</td>
			<td>${b.daily_rate != null ? frappe.format(b.daily_rate, { fieldtype: "Currency" }) : "-"}</td>
		</tr>`;
	});

	return `<div style="max-height: 300px; overflow-y: auto;">
		<table class="table table-bordered table-hover table-sm">
			<thead><tr>
				<th>${__("Bed")}</th>
				<th>${__("Label")}</th>
				<th>${__("Room")}</th>
				<th>${__("Ward")}</th>
				<th>${__("Type")}</th>
				<th>${__("Floor")}</th>
				<th>${__("Status")}</th>
				<th>${__("Rate")}</th>
			</tr></thead>
			<tbody>${rows.join("")}</tbody>
		</table>
	</div>`;
}

function _attach_bed_click_handlers(dialog, target_field) {
	dialog.$wrapper.find(".bed-row").on("click", function () {
		dialog.$wrapper.find(".bed-row").removeClass("highlight");
		$(this).addClass("highlight");
		const bed = $(this).data("bed");
		dialog.set_value(target_field, bed);
	});
}

// ── US-E2: Nursing Risk Indicators ──────────────────────────────────

function _show_nursing_risk_banners(frm) {
	if (!frm.doc.custom_risk_flags_updated_on) return;

	const badges = [];

	if (frm.doc.custom_allergy_alert) {
		const summary = frm.doc.custom_allergy_summary || __("Allergy present");
		badges.push(`<span class="indicator-pill red">${__("ALLERGY")}: ${frappe.utils.escape_html(summary)}</span>`);
	}

	const fall = frm.doc.custom_fall_risk_level;
	if (fall) {
		const color = { High: "red", Moderate: "orange", Low: "green" }[fall] || "grey";
		badges.push(`<span class="indicator-pill ${color}">${__("Fall")}: ${fall}</span>`);
	}

	const pressure = frm.doc.custom_pressure_risk_level;
	if (pressure) {
		const color = { "Very High": "red", High: "red", Moderate: "orange", Low: "blue", "No Risk": "green" }[pressure] || "grey";
		badges.push(`<span class="indicator-pill ${color}">${__("Pressure")}: ${pressure}</span>`);
	}

	const nutrition = frm.doc.custom_nutrition_risk_level;
	if (nutrition) {
		const color = { High: "red", Medium: "orange", Low: "green" }[nutrition] || "grey";
		badges.push(`<span class="indicator-pill ${color}">${__("Nutrition")}: ${nutrition}</span>`);
	}

	if (badges.length) {
		frm.dashboard.add_comment(
			`<strong>${__("Nursing Risk")}:</strong> ${badges.join(" ")}`,
			frm.doc.custom_allergy_alert ? "red" : "blue",
			true
		);
	}
}

function _add_recalculate_risk_button(frm) {
	frm.add_custom_button(__("Recalculate Risks"), () => {
		frappe.call({
			method: "alcura_ipd_ext.api.nursing.recalculate_risks",
			args: { inpatient_record: frm.doc.name },
			freeze: true,
			freeze_message: __("Recalculating risk flags..."),
			callback(r) {
				if (r.message) {
					frappe.show_alert({
						message: __("Risk flags updated."),
						indicator: "green",
					});
					frm.reload_doc();
				}
			},
		});
	}, __("Assessment"));
}

// ── US-E1: Intake Assessment ────────────────────────────────────────

function _show_intake_banner(frm) {
	if (!frm.doc.custom_intake_assessment) return;

	const status = frm.doc.custom_intake_status || "Draft";
	const color_map = { Draft: "orange", "In Progress": "blue", Completed: "green" };
	const color = color_map[status] || "orange";
	const link = `<a href="/app/ipd-intake-assessment/${frm.doc.custom_intake_assessment}">${frm.doc.custom_intake_assessment}</a>`;

	frm.dashboard.add_comment(
		__("Intake Assessment: {0} — Status: {1}", [link, `<strong>${status}</strong>`]),
		color,
		true
	);
}

function _add_intake_button(frm) {
	if (frm.doc.custom_intake_assessment) {
		frm.add_custom_button(__("View Intake Assessment"), () => {
			frappe.set_route("Form", "IPD Intake Assessment", frm.doc.custom_intake_assessment);
		}, __("Assessment"));
	}

	frm.add_custom_button(__("Create Intake Assessment"), () => {
		_show_intake_template_picker(frm);
	}, __("Assessment"));
}

function _show_intake_template_picker(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Select Intake Assessment Template"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "template",
				label: __("Assessment Template"),
				options: "IPD Intake Assessment Template",
				reqd: 1,
				get_query() {
					return { filters: { is_active: 1 } };
				},
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.intake.create_intake_assessment",
				args: {
					inpatient_record: frm.doc.name,
					template_name: values.template,
				},
				freeze: true,
				freeze_message: __("Creating assessment..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Intake Assessment {0} created.", [r.message.assessment]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

// ── US-E3: Consultant Admission Notes ───────────────────────────────

function _add_clinical_note_buttons(frm) {
	if (!frappe.perm.has_perm("Patient Encounter", 0, "create")) return;

	frappe.call({
		method: "alcura_ipd_ext.api.consultation.get_clinical_context",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const ctx = r.message;

			const has_admission_note = (ctx.recent_encounters || []).some(
				(e) => e.custom_ipd_note_type === "Admission Note"
			);

			if (!has_admission_note) {
				frm.add_custom_button(
					__("Record Admission Note"),
					() => _create_clinical_note(frm, "Admission Note"),
					__("Clinical")
				);
			}

			frm.add_custom_button(
				__("Record Progress Note"),
				() => _create_clinical_note(frm, "Progress Note"),
				__("Clinical")
			);

			if ((ctx.recent_encounters || []).length > 0) {
				frm.add_custom_button(
					__("View Encounters"),
					() => {
						frappe.set_route("List", "Patient Encounter", {
							custom_linked_inpatient_record: frm.doc.name,
						});
					},
					__("Clinical")
				);
			}
		},
	});
}

// ── US-E4: Bedside Charts ───────────────────────────────────────────

function _show_charting_banner(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.charting.get_charts_for_admission",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			if (!r.message || !r.message.length) return;
			const charts = r.message;
			const active = charts.filter((c) => c.status === "Active");
			const overdue = charts.filter((c) => c.is_overdue);

			if (overdue.length) {
				const overdueNames = overdue.map(
					(c) => `${c.chart_type} (${c.overdue_minutes} min)`
				).join(", ");
				frm.dashboard.add_comment(
					__("OVERDUE Charts: {0}", [overdueNames]),
					"red",
					true
				);
			} else if (active.length) {
				frm.dashboard.add_comment(
					__("{0} active bedside chart(s).", [active.length]),
					"blue",
					true
				);
			}
		},
	});
}

function _add_charting_buttons(frm) {
	frm.add_custom_button(__("Start Chart"), () => {
		_show_chart_template_picker(frm);
	}, __("Charting"));

	frm.add_custom_button(__("Record Vitals"), () => {
		_quick_chart_entry(frm, "Vitals");
	}, __("Charting"));

	frm.add_custom_button(__("Record I/O"), () => {
		frappe.new_doc("IPD IO Entry", {
			patient: frm.doc.patient,
			inpatient_record: frm.doc.name,
		});
	}, __("Charting"));

	frm.add_custom_button(__("Nursing Note"), () => {
		frappe.new_doc("IPD Nursing Note", {
			patient: frm.doc.patient,
			inpatient_record: frm.doc.name,
		});
	}, __("Charting"));

	frm.add_custom_button(__("MAR Entry"), () => {
		frappe.new_doc("IPD MAR Entry", {
			patient: frm.doc.patient,
			inpatient_record: frm.doc.name,
		});
	}, __("Charting"));

	frm.add_custom_button(__("View Charts"), () => {
		frappe.set_route("List", "IPD Bedside Chart", {
			inpatient_record: frm.doc.name,
		});
	}, __("Charting"));
}

function _show_chart_template_picker(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Start Bedside Chart"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "chart_template",
				label: __("Chart Template"),
				options: "IPD Chart Template",
				reqd: 1,
				get_query() {
					return { filters: { is_active: 1 } };
				},
			},
			{
				fieldtype: "Int",
				fieldname: "frequency_minutes",
				label: __("Frequency (minutes)"),
				description: __("Leave blank to use the template default"),
			},
		],
		primary_action_label: __("Start"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.charting.start_chart",
				args: {
					inpatient_record: frm.doc.name,
					chart_template: values.chart_template,
					frequency_minutes: values.frequency_minutes || null,
				},
				freeze: true,
				freeze_message: __("Starting chart..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("{0} chart started.", [r.message.chart_type]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

function _quick_chart_entry(frm, chart_type) {
	frappe.call({
		method: "alcura_ipd_ext.api.charting.get_charts_for_admission",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			const charts = (r.message || []).filter(
				(c) => c.chart_type === chart_type && c.status === "Active"
			);
			if (!charts.length) {
				frappe.msgprint(
					__("No active {0} chart found. Start one first.", [chart_type])
				);
				return;
			}
			frappe.new_doc("IPD Chart Entry", {
				bedside_chart: charts[0].name,
				patient: frm.doc.patient,
				inpatient_record: frm.doc.name,
				chart_type: chart_type,
			});
		},
	});
}

function _create_clinical_note(frm, note_type) {
	const d = new frappe.ui.Dialog({
		title: __(note_type),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "practitioner",
				label: __("Practitioner"),
				options: "Healthcare Practitioner",
				default: frm.doc.primary_practitioner,
				reqd: 1,
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.consultation.create_admission_note",
				args: {
					inpatient_record: frm.doc.name,
					note_type: note_type,
					practitioner: values.practitioner,
				},
				freeze: true,
				freeze_message: __("Creating {0}...", [note_type]),
				callback(r) {
					if (r.message) {
						frappe.set_route(
							"Form",
							"Patient Encounter",
							r.message.encounter
						);
					}
				},
			});
		},
	});
	d.show();
}

// ── US-E5: Problem List ─────────────────────────────────────────────

function _show_problem_list_banner(frm) {
	const count = frm.doc.custom_active_problems_count || 0;
	const last_note = frm.doc.custom_last_progress_note_date;

	if (!count && !last_note) return;

	const parts = [];
	if (count) {
		parts.push(`<strong>${__("Active Problems")}:</strong> ${count}`);
	}
	if (last_note) {
		parts.push(`<strong>${__("Last Progress Note")}:</strong> ${frappe.datetime.str_to_user(last_note)}`);
	}

	frm.dashboard.add_comment(parts.join(" &nbsp;|&nbsp; "), "blue", true);
}

function _add_problem_list_buttons(frm) {
	frm.add_custom_button(__("View Problems"), () => {
		frappe.set_route("List", "IPD Problem List Item", {
			inpatient_record: frm.doc.name,
		});
	}, __("Problem List"));

	frm.add_custom_button(__("Add Problem"), () => {
		_show_ir_add_problem_dialog(frm);
	}, __("Problem List"));
}

function _show_ir_add_problem_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Add Problem"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "problem_description",
				label: __("Problem Description"),
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Select",
				fieldname: "severity",
				label: __("Severity"),
				options: "\nMild\nModerate\nSevere",
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Date",
				fieldname: "onset_date",
				label: __("Onset Date"),
				default: frappe.datetime.get_today(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Data",
				fieldname: "icd_code",
				label: __("ICD Code"),
			},
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.round_sheet.add_problem",
				args: {
					inpatient_record: frm.doc.name,
					problem_description: values.problem_description,
					onset_date: values.onset_date || null,
					severity: values.severity || null,
					icd_code: values.icd_code || null,
				},
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Problem added."),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

// ── US-F1–F3: Clinical Orders ───────────────────────────────────────

function _show_orders_banner(frm) {
	const med = frm.doc.custom_active_medication_orders || 0;
	const lab = frm.doc.custom_active_lab_orders || 0;
	const proc = frm.doc.custom_active_procedure_orders || 0;
	const pending = frm.doc.custom_pending_orders_count || 0;
	const total = med + lab + proc;
	if (!total) return;

	const parts = [];
	if (med) parts.push(`${__("Meds")}: ${med}`);
	if (lab) parts.push(`${__("Labs")}: ${lab}`);
	if (proc) parts.push(`${__("Proc")}: ${proc}`);
	if (pending) parts.push(`<strong>${__("Pending")}: ${pending}</strong>`);

	frm.dashboard.add_comment(
		`<strong>${__("Active Orders")}:</strong> ${parts.join(" | ")}`,
		pending > 0 ? "orange" : "blue",
		true
	);
}

function _add_order_buttons(frm) {
	frm.add_custom_button(__("Medication"), () => {
		_show_medication_order_dialog(frm);
	}, __("Place Order"));

	frm.add_custom_button(__("Lab Test"), () => {
		_show_lab_order_dialog(frm);
	}, __("Place Order"));

	frm.add_custom_button(__("Radiology"), () => {
		_show_procedure_order_dialog(frm, "Radiology");
	}, __("Place Order"));

	frm.add_custom_button(__("Procedure"), () => {
		_show_procedure_order_dialog(frm, "Procedure");
	}, __("Place Order"));

	frm.add_custom_button(__("View Orders"), () => {
		frappe.set_route("List", "IPD Clinical Order", {
			inpatient_record: frm.doc.name,
		});
	}, __("Place Order"));
}

function _show_medication_order_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Place Medication Order"),
		size: "large",
		fields: [
			{
				fieldtype: "Link", fieldname: "medication_item",
				label: __("Medication Item"), options: "Item",
				get_query() { return { filters: { is_stock_item: 1 } }; },
				change() {
					const item = d.get_value("medication_item");
					if (item) {
						frappe.db.get_value("Item", item, "item_name", (r) => {
							if (r) d.set_value("medication_name", r.item_name);
						});
					}
				},
			},
			{ fieldtype: "Data", fieldname: "medication_name", label: __("Medication Name"), reqd: 1 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Data", fieldname: "dose", label: __("Dose") },
			{ fieldtype: "Data", fieldname: "dose_uom", label: __("UOM") },
			{
				fieldtype: "Select", fieldname: "route", label: __("Route"),
				options: "\nOral\nIV\nIM\nSC\nSL\nTopical\nInhaled\nRectal\nPR\nOther",
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Select", fieldname: "frequency", label: __("Frequency"),
				options: "\nOnce\nOD\nBD\nTDS\nQID\nQ4H\nQ6H\nQ8H\nQ12H\nPRN\nSTAT\nContinuous",
			},
			{
				fieldtype: "Select", fieldname: "urgency", label: __("Urgency"),
				options: "Routine\nUrgent\nSTAT\nEmergency", default: "Routine",
			},
			{ fieldtype: "Check", fieldname: "is_stat", label: __("STAT"), default: 0 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Datetime", fieldname: "start_datetime", label: __("Start") },
			{ fieldtype: "Int", fieldname: "duration_days", label: __("Duration (Days)") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Small Text", fieldname: "indication", label: __("Indication") },
			{ fieldtype: "Small Text", fieldname: "clinical_notes", label: __("Notes") },
		],
		primary_action_label: __("Place Order"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.create_medication_order",
				args: {
					patient: frm.doc.patient,
					inpatient_record: frm.doc.name,
					...values,
				},
				freeze: true,
				freeze_message: __("Placing medication order..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({ message: __("Order {0} placed.", [r.message.order]), indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

function _show_lab_order_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Place Lab Test Order"),
		fields: [
			{
				fieldtype: "Link", fieldname: "lab_test_template",
				label: __("Lab Test Template"), options: "Lab Test Template",
				change() {
					const tmpl = d.get_value("lab_test_template");
					if (tmpl) {
						frappe.db.get_value("Lab Test Template", tmpl, "lab_test_name", (r) => {
							if (r) d.set_value("lab_test_name", r.lab_test_name);
						});
					}
				},
			},
			{ fieldtype: "Data", fieldname: "lab_test_name", label: __("Test Name"), reqd: 1 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "sample_type", label: __("Sample Type") },
			{ fieldtype: "Check", fieldname: "is_fasting_required", label: __("Fasting Required") },
			{
				fieldtype: "Select", fieldname: "urgency", label: __("Urgency"),
				options: "Routine\nUrgent\nSTAT\nEmergency", default: "Routine",
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "collection_instructions", label: __("Collection Instructions") },
			{ fieldtype: "Small Text", fieldname: "clinical_notes", label: __("Notes") },
		],
		primary_action_label: __("Place Order"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.create_lab_order",
				args: {
					patient: frm.doc.patient,
					inpatient_record: frm.doc.name,
					...values,
				},
				freeze: true,
				freeze_message: __("Placing lab order..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({ message: __("Order {0} placed.", [r.message.order]), indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

// ── US-I1/I4/I5: TPA & Billing ─────────────────────────────────────

function _show_tpa_billing_banner(frm) {
	const parts = [];
	if (frm.doc.custom_preauth_request) {
		const status = frm.doc.custom_preauth_status || "Draft";
		const color_map = {
			Draft: "grey", Submitted: "blue", "Query Raised": "orange",
			Resubmitted: "blue", Approved: "green", "Partially Approved": "cyan",
			Rejected: "red", Closed: "darkgrey",
		};
		const color = color_map[status] || "grey";
		const link = `<a href="/app/tpa-preauth-request/${frm.doc.custom_preauth_request}">${frm.doc.custom_preauth_request}</a>`;
		parts.push(`${__("Preauth")}: ${link} <span class="indicator-pill ${color}">${status}</span>`);
	}
	if (frm.doc.custom_discharge_checklist) {
		const status = frm.doc.custom_discharge_checklist_status || "Pending";
		const link = `<a href="/app/discharge-billing-checklist/${frm.doc.custom_discharge_checklist}">${frm.doc.custom_discharge_checklist}</a>`;
		parts.push(`${__("Discharge Checklist")}: ${link} (${status})`);
	}
	if (frm.doc.custom_claim_pack) {
		const link = `<a href="/app/tpa-claim-pack/${frm.doc.custom_claim_pack}">${frm.doc.custom_claim_pack}</a>`;
		parts.push(`${__("Claim Pack")}: ${link}`);
	}
	if (parts.length) {
		frm.dashboard.add_comment(parts.join(" &nbsp;|&nbsp; "), "blue", true);
	}
}

function _add_tpa_billing_buttons(frm) {
	const payer_type = frm.doc.custom_payer_type || "Cash";
	const is_non_cash = payer_type !== "Cash";

	if (is_non_cash && !frm.doc.custom_preauth_request) {
		frm.add_custom_button(__("Raise Preauth"), () => {
			frappe.call({
				method: "alcura_ipd_ext.api.preauth.create_preauth_from_admission",
				args: { inpatient_record: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating pre-auth request..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Pre-auth {0} created.", [r.message]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		}, __("TPA & Billing"));
	}

	if (frm.doc.custom_preauth_request) {
		frm.add_custom_button(__("View Preauth"), () => {
			frappe.set_route("Form", "TPA Preauth Request", frm.doc.custom_preauth_request);
		}, __("TPA & Billing"));
	}

	if (!frm.doc.custom_discharge_checklist) {
		frm.add_custom_button(__("Create Discharge Checklist"), () => {
			frappe.call({
				method: "alcura_ipd_ext.services.discharge_checklist_service.create_discharge_checklist",
				args: { inpatient_record: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating discharge checklist..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Discharge checklist {0} created.", [r.message]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		}, __("TPA & Billing"));
	} else {
		frm.add_custom_button(__("View Discharge Checklist"), () => {
			frappe.set_route("Form", "Discharge Billing Checklist", frm.doc.custom_discharge_checklist);
		}, __("TPA & Billing"));
	}

	frm.add_custom_button(__("Interim Bill"), () => {
		frappe.set_route("query-report", "IPD Interim Bill", {
			inpatient_record: frm.doc.name,
		});
	}, __("TPA & Billing"));

	if (is_non_cash && !frm.doc.custom_claim_pack) {
		frm.add_custom_button(__("Generate Claim Pack"), () => {
			frappe.call({
				method: "alcura_ipd_ext.services.claim_pack_service.create_claim_pack",
				args: { inpatient_record: frm.doc.name },
				freeze: true,
				freeze_message: __("Generating claim pack..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Claim pack {0} created.", [r.message]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		}, __("TPA & Billing"));
	} else if (frm.doc.custom_claim_pack) {
		frm.add_custom_button(__("View Claim Pack"), () => {
			frappe.set_route("Form", "TPA Claim Pack", frm.doc.custom_claim_pack);
		}, __("TPA & Billing"));
	}
}

function _show_procedure_order_dialog(frm, order_type) {
	const d = new frappe.ui.Dialog({
		title: __("Place {0} Order", [order_type]),
		fields: [
			{
				fieldtype: "Link", fieldname: "procedure_template",
				label: __("Template"), options: "Clinical Procedure Template",
			},
			{ fieldtype: "Data", fieldname: "procedure_name", label: __("Name"), reqd: 1 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "body_site", label: __("Body Site") },
			{ fieldtype: "Check", fieldname: "is_bedside", label: __("Bedside"), default: 0 },
			{
				fieldtype: "Select", fieldname: "urgency", label: __("Urgency"),
				options: "Routine\nUrgent\nSTAT\nEmergency", default: "Routine",
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "prep_instructions", label: __("Prep Instructions") },
			{ fieldtype: "Small Text", fieldname: "clinical_notes", label: __("Notes") },
		],
		primary_action_label: __("Place Order"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.create_procedure_order",
				args: {
					patient: frm.doc.patient,
					inpatient_record: frm.doc.name,
					order_type: order_type,
					...values,
				},
				freeze: true,
				freeze_message: __("Placing order..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({ message: __("Order {0} placed.", [r.message.order]), indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

// ── US-E5: Round Note ───────────────────────────────────────────────

function _add_round_note_button(frm) {
	if (!frappe.perm.has_perm("Patient Encounter", 0, "create")) return;

	frm.add_custom_button(__("Round Note"), () => {
		const d = new frappe.ui.Dialog({
			title: __("Start Round Note"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "practitioner",
					label: __("Practitioner"),
					options: "Healthcare Practitioner",
					default: frm.doc.primary_practitioner,
					reqd: 1,
				},
			],
			primary_action_label: __("Start"),
			primary_action(values) {
				d.hide();
				frappe.call({
					method: "alcura_ipd_ext.api.round_sheet.create_round_note",
					args: {
						inpatient_record: frm.doc.name,
						practitioner: values.practitioner,
					},
					freeze: true,
					freeze_message: __("Creating Progress Note..."),
					callback(r) {
						if (r.message) {
							frappe.set_route(
								"Form",
								"Patient Encounter",
								r.message.encounter
							);
						}
					},
				});
			},
		});
		d.show();
	}, __("Clinical"));
}

// ── US-J1/J2/J3: Discharge Journey ─────────────────────────────────

function _show_discharge_journey_banner(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.discharge.get_discharge_status",
		args: { inpatient_record: frm.doc.name },
		callback(r) {
			if (!r.message) return;
			const ds = r.message;
			if (!ds.advice) return;

			const parts = [];

			const advice_color_map = {
				Draft: "orange", Advised: "blue", Acknowledged: "cyan",
				Completed: "green", Cancelled: "red",
			};
			const ac = advice_color_map[ds.advice.status] || "grey";
			const advice_link = `<a href="/app/ipd-discharge-advice/${ds.advice.name}">${ds.advice.name}</a>`;
			parts.push(
				`${__("Advice")}: ${advice_link} <span class="indicator-pill ${ac}">${ds.advice.status}</span>`
			);

			if (ds.advice.expected_discharge_datetime) {
				parts.push(
					`${__("EDD")}: <strong>${frappe.datetime.str_to_user(ds.advice.expected_discharge_datetime)}</strong>`
				);
			}

			if (ds.billing_checklist) {
				const bl = `<a href="/app/discharge-billing-checklist/${ds.billing_checklist.name}">${ds.billing_checklist.status}</a>`;
				parts.push(`${__("Billing")}: ${bl}`);
			}

			if (ds.nursing_checklist) {
				const nl = `<a href="/app/nursing-discharge-checklist/${ds.nursing_checklist.name}">${ds.nursing_checklist.status}</a>`;
				parts.push(`${__("Nursing")}: ${nl}`);
			}

			const color = ds.ready_to_vacate ? "green" : "blue";
			frm.dashboard.add_comment(
				`<strong>${__("Discharge")}:</strong> ${parts.join(" &nbsp;|&nbsp; ")}`,
				color,
				true
			);
		},
	});
}

function _add_discharge_journey_buttons(frm) {
	if (!frm.doc.custom_discharge_advice) {
		frm.add_custom_button(__("Initiate Discharge"), () => {
			_show_discharge_advice_dialog(frm);
		}, __("Discharge"));
		frm.change_custom_button_type(__("Initiate Discharge"), __("Discharge"), "warning");
	} else {
		frm.add_custom_button(__("View Discharge Advice"), () => {
			frappe.set_route("Form", "IPD Discharge Advice", frm.doc.custom_discharge_advice);
		}, __("Discharge"));

		const advice_status = frm.doc.custom_discharge_advice_status;

		if (advice_status === "Advised") {
			frm.add_custom_button(__("Acknowledge Discharge"), () => {
				frappe.call({
					method: "alcura_ipd_ext.api.discharge.acknowledge_discharge_advice",
					args: { advice_name: frm.doc.custom_discharge_advice },
					freeze: true,
					freeze_message: __("Acknowledging..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({ message: __("Discharge acknowledged."), indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			}, __("Discharge"));
		}

		if (!frm.doc.custom_nursing_discharge_checklist && advice_status !== "Cancelled") {
			frm.add_custom_button(__("Create Nursing Checklist"), () => {
				frappe.call({
					method: "alcura_ipd_ext.api.discharge.create_nursing_checklist",
					args: {
						inpatient_record: frm.doc.name,
						discharge_advice: frm.doc.custom_discharge_advice || "",
					},
					freeze: true,
					freeze_message: __("Creating nursing checklist..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Nursing Checklist {0} created.", [r.message.checklist]),
								indicator: "green",
							});
							frm.reload_doc();
						}
					},
				});
			}, __("Discharge"));
		}

		if (frm.doc.custom_nursing_discharge_checklist) {
			frm.add_custom_button(__("View Nursing Checklist"), () => {
				frappe.set_route("Form", "Nursing Discharge Checklist", frm.doc.custom_nursing_discharge_checklist);
			}, __("Discharge"));
		}

		if (advice_status === "Acknowledged" || advice_status === "Completed") {
			frm.add_custom_button(__("Vacate Bed"), () => {
				frappe.confirm(
					__("Vacate the bed and trigger housekeeping? This will release the bed."),
					() => {
						frappe.call({
							method: "alcura_ipd_ext.api.discharge.vacate_bed",
							args: { inpatient_record: frm.doc.name },
							freeze: true,
							freeze_message: __("Processing bed vacate..."),
							callback(r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Bed vacated successfully."),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					}
				);
			}, __("Discharge"));
		}
	}
}

function _show_discharge_advice_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Initiate Discharge Advice"),
		size: "extra-large",
		fields: [
			{
				fieldtype: "Link", fieldname: "consultant",
				label: __("Consultant"), options: "Healthcare Practitioner",
				default: frm.doc.primary_practitioner, reqd: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Datetime", fieldname: "expected_discharge_datetime",
				label: __("Expected Discharge Date/Time"), reqd: 1,
			},
			{
				fieldtype: "Section Break", label: __("Discharge Details"),
			},
			{
				fieldtype: "Select", fieldname: "discharge_type",
				label: __("Discharge Type"),
				options: "Normal\nLAMA\nAgainst Medical Advice\nTransfer\nDeath\nAbsconded",
				default: "Normal",
			},
			{
				fieldtype: "Select", fieldname: "condition_at_discharge",
				label: __("Condition"),
				options: "\nImproved\nUnchanged\nDeteriorated\nLAMA\nExpired\nReferred",
			},
			{
				fieldtype: "Section Break", label: __("Clinical Summary"),
			},
			{
				fieldtype: "Small Text", fieldname: "primary_diagnosis",
				label: __("Primary Diagnosis"),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Small Text", fieldname: "secondary_diagnoses",
				label: __("Secondary Diagnoses"),
			},
			{
				fieldtype: "Section Break", label: __("Medications & Follow-up"),
			},
			{
				fieldtype: "Text Editor", fieldname: "discharge_medications",
				label: __("Discharge Medications"),
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldtype: "Text Editor", fieldname: "follow_up_instructions",
				label: __("Follow-Up Instructions"),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Date", fieldname: "follow_up_date",
				label: __("Follow-Up Date"),
			},
			{
				fieldtype: "Section Break", label: __("Additional"), collapsible: 1,
			},
			{
				fieldtype: "Text Editor", fieldname: "diet_instructions",
				label: __("Diet Instructions"),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Text Editor", fieldname: "warning_signs",
				label: __("Warning Signs"),
			},
		],
		primary_action_label: __("Submit Discharge Advice"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.discharge.create_discharge_advice",
				args: {
					inpatient_record: frm.doc.name,
					...values,
				},
				freeze: true,
				freeze_message: __("Submitting discharge advice..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Discharge advice {0} submitted.", [r.message.advice]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}
