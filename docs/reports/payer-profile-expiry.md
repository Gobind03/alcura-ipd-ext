# Report: Payer Profile Expiry

## Purpose

Proactive monitoring report that shows active Patient Payer Profiles expiring within a configurable number of days. Enables TPA desk and operations teams to renew or update profiles before they lapse, preventing admission delays.

## Type

Script Report

## Reference DocType

Patient Payer Profile

## Filters

| Filter | Type | Default | Required | Notes |
|--------|------|---------|----------|-------|
| Expiry Within (Days) | Int | 30 | Yes | Number of days from today |
| Payer Type | Select | (all) | No | Cash / Corporate / Insurance TPA / PSU / Government Scheme |
| Insurance Payor | Link → Insurance Payor | (all) | No | Filter by specific payor |
| Company | Link → Company | User default | No | Filter by company |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Profile ID | Link → Patient Payer Profile | 140 | |
| Patient | Link → Patient | 130 | |
| Patient Name | Data | 160 | |
| Payer Type | Data | 130 | |
| Insurance Payor | Link → Insurance Payor | 150 | |
| Payer (Customer) | Link → Customer | 150 | |
| Policy Number | Data | 130 | |
| Valid From | Date | 110 | |
| Valid To | Date | 110 | |
| Days Until Expiry | Int | 120 | Computed: valid_to - today |
| Sum Insured | Currency | 120 | |

## Sort Order

By `valid_to` ascending (soonest expiring first).

## Access Roles

- Healthcare Administrator
- TPA Desk User
- Healthcare Receptionist
- Accounts User

## Workspace

Available from IPD Desk workspace under the Reports card.

## Related

- Scheduled task `notify_expiring_payer_profiles` sends in-app notifications for profiles expiring within 7 days
