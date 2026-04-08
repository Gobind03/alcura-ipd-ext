"""Central test suite for US-A4: Room Tariff Mapping.

Re-exports the per-doctype test class so that both `bench run-tests` and
`pytest alcura_ipd_ext/tests/` discover the suite.
"""

from alcura_ipd_ext.alcura_ipd_extensions.doctype.room_tariff_mapping.test_room_tariff_mapping import (  # noqa: F401
	TestRoomTariffMapping,
)
