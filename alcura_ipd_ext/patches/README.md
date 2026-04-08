# Patches

Database migration patches go here.

## Convention

Create files as `v{version}/patch_name.py` and register them in `patches.txt`:

```
[post_model_sync]
alcura_ipd_ext.patches.v0_1.rename_old_field
```

Each patch module must expose an `execute()` function:

```python
import frappe

def execute():
    frappe.reload_doc("alcura_ipd_ext", "doctype", "my_doctype")
    # migration logic ...
```
