"""Low-level OOXML helpers for Word tracked changes and comments.

python-docx does not natively author the <w:ins> / <w:del> / <w:commentReference>
elements that "track changes" requires. We drop to lxml for those, while still
using python-docx for paragraph + run scaffolding.

Reference: ECMA-376 Part 1 §17.13 (revisions and tracked changes).
"""
from __future__ import annotations
import datetime as dt
from typing import TYPE_CHECKING, Optional
from lxml import etree

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph
    from docx.document import Document


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


_revision_counter = [0]


def _next_id() -> int:
    _revision_counter[0] += 1
    return _revision_counter[0]


def add_tracked_change(
    paragraph: "Paragraph",
    before: str,
    after: str,
    author: str,
    date: Optional[str] = None,
) -> None:
    """Append a w:del (before) + w:ins (after) pair to the paragraph."""
    if date is None:
        date = _now_iso()

    p_elem = paragraph._p

    del_elem = etree.SubElement(p_elem, _qn("del"))
    del_elem.set(_qn("id"), str(_next_id()))
    del_elem.set(_qn("author"), author)
    del_elem.set(_qn("date"), date)
    del_run = etree.SubElement(del_elem, _qn("r"))
    del_text = etree.SubElement(del_run, _qn("delText"))
    del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    del_text.text = before

    ins_elem = etree.SubElement(p_elem, _qn("ins"))
    ins_elem.set(_qn("id"), str(_next_id()))
    ins_elem.set(_qn("author"), author)
    ins_elem.set(_qn("date"), date)
    ins_run = etree.SubElement(ins_elem, _qn("r"))
    ins_text = etree.SubElement(ins_run, _qn("t"))
    ins_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ins_text.text = after


def add_change_bookmark(paragraph: "Paragraph", change_id: str) -> None:
    """Wrap the end of the paragraph with a bookmark named chg_<change_id>."""
    p_elem = paragraph._p
    bookmark_id = str(_next_id())
    name = f"chg_{change_id}"

    start = etree.SubElement(p_elem, _qn("bookmarkStart"))
    start.set(_qn("id"), bookmark_id)
    start.set(_qn("name"), name)

    end = etree.SubElement(p_elem, _qn("bookmarkEnd"))
    end.set(_qn("id"), bookmark_id)


def add_comment(
    document: "Document",
    paragraph: "Paragraph",
    author: str,
    text: str,
    comment_id: int,
) -> None:
    """Add a Word comment anchored at the end of the paragraph.

    SIMPLIFIED FALLBACK: append `[הערה: <text>]` as inline text to the paragraph
    body. Real Word comment balloons require registering a comments OPC part,
    which is awkward in python-docx and not strictly required by the spec.
    Inline rationale is human-readable in Word and survives docx round-trips.
    """
    p_elem = paragraph._p
    run = etree.SubElement(p_elem, _qn("r"))
    t = etree.SubElement(run, _qn("t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = f"  [הערה: {text}]"
