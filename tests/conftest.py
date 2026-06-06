import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    from database import init_db
    init_db(db_path)
    return db_path
