# Overrides

Place doc_event handlers and DocType class overrides here.

## Convention

- One file per DocType: `patient.py`, `inpatient_record.py`, etc.
- Wire them into `hooks.py` via `doc_events` or `override_doctype_class`.

```python
# Example: alcura_ipd_ext/overrides/patient.py
import frappe

def validate(doc, method):
    """Runs on Patient validate."""
    pass
```
