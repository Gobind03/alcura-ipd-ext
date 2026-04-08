# Alcura IPD Extensions

Custom Frappe/ERPNext app for extending Inpatient (IPD) workflows in Healthcare.

Built for **Frappe Framework v16** and **ERPNext v16**.

---

## Prerequisites

| Tool    | Version       |
| ------- | ------------- |
| Python  | >= 3.11       |
| Node.js | >= 20         |
| MariaDB | >= 10.11      |
| Redis   | >= 6          |
| Bench   | latest (`pip install frappe-bench`) |

## Installation

```bash
# Inside an existing bench directory
bench get-app https://github.com/<org>/alcura_ipd_ext.git
bench --site <site-name> install-app alcura_ipd_ext
bench --site <site-name> migrate
```

## Development Setup

```bash
# Clone into the bench apps directory
cd ~/frappe-bench/apps
git clone https://github.com/<org>/alcura_ipd_ext.git

# Install the app on your dev site
bench --site dev.localhost install-app alcura_ipd_ext

# Install dev dependencies
pip install -r dev-requirements.txt

# Set up pre-commit hooks
pre-commit install
```

## Running Tests

```bash
bench --site dev.localhost run-tests --app alcura_ipd_ext
```

## Project Structure

```
alcura_ipd_ext/
├── .github/workflows/ci.yml    # GitHub Actions CI pipeline
├── .editorconfig                # Editor formatting rules
├── .pre-commit-config.yaml      # Pre-commit hooks (ruff, etc.)
├── pyproject.toml               # Build config, ruff, pytest settings
├── requirements.txt             # Runtime Python dependencies
├── dev-requirements.txt         # Dev-only Python dependencies
├── package.json                 # Node.js dependencies
├── MANIFEST.in                  # sdist packaging manifest
│
└── alcura_ipd_ext/              # App source package
    ├── __init__.py              # App version
    ├── hooks.py                 # Frappe hooks (events, includes, etc.)
    ├── modules.txt              # Registered Frappe modules
    ├── patches.txt              # DB migration patches
    │
    ├── alcura_ipd_ext/          # Default module (DocTypes live here)
    ├── api/                     # Whitelisted API endpoints
    │   └── ipd.py
    ├── config/                  # Desktop & workspace config
    │   └── desktop.py
    ├── overrides/               # doc_events & class overrides
    ├── patches/                 # Migration patch scripts
    ├── setup/                   # Install / uninstall lifecycle hooks
    │   └── install.py
    ├── utils/                   # Shared utilities
    │   └── helpers.py
    │
    ├── public/                  # Static assets (served by nginx)
    │   ├── css/
    │   ├── js/
    │   └── icons/
    ├── templates/               # Jinja templates
    │   ├── includes/
    │   └── pages/
    ├── www/                     # Portal pages (URL-mapped)
    │
    └── tests/                   # Test suite
        ├── conftest.py          # Shared pytest fixtures
        ├── test_setup.py        # Smoke tests
        └── test_api_ipd.py      # API tests
```

## Adding a New DocType

```bash
bench --site dev.localhost new-doctype "My DocType" --module "Alcura IPD Extensions"
```

This creates the JSON definition and boilerplate Python/JS under
`alcura_ipd_ext/alcura_ipd_ext/doctype/my_doctype/`.

## Contributing

1. Create a feature branch from `develop`
2. Make changes and add tests
3. Run `ruff check . && ruff format --check .`
4. Open a pull request

## License

MIT
