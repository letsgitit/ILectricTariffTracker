import os, tempfile
os.environ["TARIFF_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

import pytest
from app import checker
from app.checker import _diff_line_items, check_document
from app.db import SessionLocal, init_db
from app.fetcher import FetchResult, _hash, html_to_text, normalize_text
from app.models import ChangeEvent, TrackedDocument

PAT = [{"label": "Fee", "pattern": r"Fee \$([\d,.]+)"}]


def test_diff_detects_lost_and_new_values():
    assert _diff_line_items({"a": "1"}, {"a": None}) == {"a": {"old": "1", "new": None}}
    assert _diff_line_items({"a": None}, {"a": "2"}) == {"a": {"old": None, "new": "2"}}
    assert _diff_line_items({"a": None}, {"a": None}) == {}
    assert _diff_line_items({"a": "1"}, {"a": "1"}) == {}


def test_whitespace_and_html_noise_not_a_change():
    assert normalize_text("Fee  $1\n.00") == normalize_text("Fee $1 .00")
    a = "<p>Rates</p><script>nonce=1</script><a href='/b.pdf'>b</a><a href='/a.pdf'>a</a>"
    b = "<p>Rates</p><script>nonce=2</script><a href='/a.pdf'>a</a><a href='/b.pdf'>b</a>"
    assert html_to_text(a) != html_to_text(b)  # order differs in raw text...
    assert _hash(normalize_text(html_to_text(a).split("\n")[0])) == _hash(normalize_text(html_to_text(b).split("\n")[0]))
    assert "nonce" not in html_to_text(a)
    assert html_to_text(a).splitlines()[-2:] == ["/a.pdf", "/b.pdf"] == html_to_text(b).splitlines()[-2:]


@pytest.fixture()
def session():
    init_db()
    s = SessionLocal()
    yield s
    s.close()


def _fake(monkeypatch, results):
    it = iter(results)
    monkeypatch.setattr(checker, "fetch_document", lambda url, t: next(it))


def _ok(text):
    return FetchResult(text=text, content_hash=_hash(normalize_text(text)), http_status=200)


ERR = FetchResult(text="", content_hash="", http_status=500, error="HTTP 500")


def test_change_during_outage_and_lost_pattern(session, monkeypatch):
    doc = TrackedDocument(doc_key="x", utility="u", rate_class="r", name="X", url="u", line_item_patterns=PAT)
    session.add(doc); session.commit()
    _fake(monkeypatch, [_ok("Fee $1.00"), ERR, _ok("Fee $2.00"), _ok("Fee is TBD")])
    for _ in range(3):
        check_document(session, doc)
    ev = session.query(ChangeEvent).all()
    assert len(ev) == 1 and ev[0].line_item_diffs == {"Fee": {"old": "1.00", "new": "2.00"}}
    check_document(session, doc)
    last = session.query(ChangeEvent).order_by(ChangeEvent.id.desc()).first()
    assert last.line_item_diffs == {"Fee": {"old": "2.00", "new": None}}
    assert "no longer matched" in last.summary
