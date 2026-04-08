# US-G1: Pharmacy Dispense Tests

## Test File

`alcura_ipd_ext/tests/test_pharmacy_dispense_service.py`

## Test Classes and Coverage

### TestStockVerification

| Test | What it validates |
|------|------------------|
| `test_verify_stock_no_bin` | Returns zero quantities when no Bin exists |
| `test_verify_stock_requires_item_code` | Throws ValidationError for empty item code |

### TestDispenseMedication

| Test | What it validates |
|------|------------------|
| `test_dispense_full` | Full dispense creates entry with correct qty, type, status |
| `test_dispense_partial` | Two partial dispenses update aggregate status (Partially → Fully Dispensed) |
| `test_dispense_fails_for_cancelled_order` | Cannot dispense against cancelled orders |
| `test_dispense_fails_for_non_medication` | Cannot dispense against Lab Test orders |

### TestSubstitution

| Test | What it validates |
|------|------------------|
| `test_request_substitution` | Sets substitution_status to Requested, puts order On Hold |
| `test_approve_substitution` | Approves and resumes order |
| `test_reject_substitution` | Rejects and resumes order with original item |

### TestReturnDispense

| Test | What it validates |
|------|------------------|
| `test_return_dispense` | Marks entry as Returned, reverts order dispense status to Pending |
| `test_double_return_fails` | Prevents returning an already-returned entry |

### TestDispenseHistory

| Test | What it validates |
|------|------------------|
| `test_get_dispense_history` | Returns all dispense entries for an order |

## Running

```bash
bench --site <site> run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_pharmacy_dispense_service
```
