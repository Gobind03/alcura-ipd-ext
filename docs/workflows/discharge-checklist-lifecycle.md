# Discharge Checklist Lifecycle

## States

1. **Pending** — created, no items cleared yet
2. **In Progress** — some items cleared, some pending
3. **Cleared** — all items cleared, waived, or not applicable
4. **Overridden** — authorized override of pending items

## Auto-Check Refresh

- Triggered manually via "Refresh Auto-Checks" button
- Re-evaluates: pending meds, pending samples, unposted procedures, room rent, discharge summary, TPA preauth
- Does not override Waived or Not Applicable statuses

## Override Flow

1. User clicks "Override All"
2. Prompted for override reason (mandatory)
3. Override records: user, datetime, reason
4. Status set to Overridden
5. Discharge billing can proceed

## Integration

- Custom field `custom_discharge_checklist` on Inpatient Record links to the checklist
- Discharge flow can check `validate_discharge_ready()` before allowing final billing
