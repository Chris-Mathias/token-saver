from token_saver.report import failure_markers, fidelity, summarize


def _event(**overrides) -> dict:
    defaults = dict(
        command_type="django_test",
        exit_code=0,
        raw_output="",
        raw_tokens=100,
        s2a_output="",
        s2a_tokens=10,
        s2b_output="",
        s2b_tokens=10,
        s2b_metadata={"parsed": True},
    )
    defaults.update(overrides)
    return defaults


def test_failure_markers_django():
    raw = (
        "ERROR: test_a (app.tests.T.test_a)\n"
        "Traceback...\n"
        "FAIL: test_b (app.tests.T.test_b)\n"
        "FAIL: test_b (app.tests.T.test_b)\n"
        "FAILED (failures=1, errors=1)\n"
    )
    assert failure_markers(raw) == ["test_a", "test_b"]


def test_failure_markers_vitest():
    raw = (
        " FAIL  src/app/seo.test.tsx [ src/app/seo.test.tsx ]\n"
        "     × funciona sem autor 46ms\n"
        "     ✓ passa 3ms\n"
    )
    assert failure_markers(raw) == ["src/app/seo.test.tsx", "funciona sem autor"]


def test_failure_markers_empty_on_success():
    assert failure_markers("Ran 3 tests in 0.1s\n\nOK\n") == []


def test_summarize_groups_by_slice():
    rows = [
        _event(raw_tokens=100, s2b_tokens=10),
        _event(raw_tokens=50, s2b_tokens=50, exit_code=1, s2b_metadata={"parsed": False}),
        _event(command_type="git_diff", raw_tokens=20, s2b_tokens=10, s2b_metadata={"hunks": 1}),
    ]
    table = {s.label: s for s in summarize(rows)}
    assert table["Total"].events == 3
    assert table["Total"].raw_tokens == 170
    assert table["Total"].s2b_tokens == 70
    assert table["Não interpretadas"].events == 1
    assert table["Interpretadas"].events == 2
    assert table["django_test"].events == 2
    assert round(table["Interpretadas"].reduction, 2) == 0.83


def test_fidelity_counts_markers_kept_in_each_version():
    raw = "FAIL: test_a (x.T.test_a)\nFAIL: test_b (x.T.test_b)\n"
    rows = [
        _event(
            exit_code=1,
            raw_output=raw,
            s2a_output="FAIL: test_a (x.T.test_a)\n... cortado ...",
            s2b_output="FAIL: test_a\nFAIL: test_b",
        ),
        _event(exit_code=0, raw_output="OK"),
    ]
    result = fidelity(rows)
    assert result.events == 1
    assert result.markers == 2
    assert result.kept_s2a == 1
    assert result.kept_s2b == 2
    assert result.events_s2a_lost == 1
    assert result.events_s2b_lost == 0


def test_fidelity_ignores_unparsed_events():
    raw = "FAIL: test_a (x.T.test_a)\n"
    rows = [_event(exit_code=1, raw_output=raw, s2b_metadata={"parsed": False})]
    assert fidelity(rows).events == 0
