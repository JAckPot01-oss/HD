from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_loads_without_exception():
    app=Path(__file__).parents[1]/"streamlit_app.py"
    at=AppTest.from_file(str(app),default_timeout=20).run()
    assert not at.exception
    assert at.title[0].value == "液压爬模设计辅助系统"
    assert len(at.metric) >= 4
