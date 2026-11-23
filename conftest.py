import pytest

import main


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Give every test its own empty SQLite file instead of the shared habits.db."""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.db")
    main.init_db()
