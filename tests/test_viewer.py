import json
import re

from token_saver.viewer import build_html, event_view


def _event(**overrides) -> dict:
    defaults = dict(
        timestamp="2026-10-15T17:16:58+00:00",
        command="manage.py test",
        command_type="django_test",
        exit_code=1,
        raw_output="FAIL: test_a (x.T.test_a)\n\x1b[31mvermelho\x1b[0m\n",
        raw_tokens=100,
        s2a_output="... cortado ...",
        s2a_tokens=10,
        s2b_output="FAIL: test_a",
        s2b_tokens=10,
        s2b_metadata={"parsed": True},
    )
    defaults.update(overrides)
    return defaults


def test_event_view_marks_which_failure_markers_survive():
    view = event_view(_event())
    assert view["markers"] == [{"name": "test_a", "s2a": False, "s2b": True}]
    assert view["parsed"] is True
    assert view["failed"] is True


def test_event_view_strips_ansi_codes():
    assert "\x1b" not in event_view(_event())["raw_output"]


def test_build_html_embeds_events_safely():
    html = build_html([_event(s2b_output="</script><b>x</b>")])
    payload = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    events = json.loads(payload.group(1))
    assert events[0]["s2b_output"] == "</script><b>x</b>"
