#!/usr/bin/env python3
"""Measure and validate skill description budgets and phase routers.

Stdlib only when `yaml` is not importable (this file is copied byte-for-byte into
repos with no dependencies). Python 3.9-safe.

Subcommands (exit 0 pass, 1 real negative result, 2 usage or parse error):
  measure <skills_dir> [--commands <dir>] [--field listed_chars|listed_skills|stubs]
  check-routers <skills_dir> [--commands <dir>]
  gate <skills_dir> [--commands <dir>] --baseline <json> --min-cut N
  reads [--require-success]      (stdin: claude -p --output-format stream-json)
  final-text                     (stdin: same)
"""
import argparse
import json
import os
import re
import sys

MAX_SKILL_LINES = 150
MAX_DESCRIPTION_CHARS = 1536
MAX_PHASES_LINE = 60


class ParseError(Exception):
    pass


# --------------------------------------------------------------------------
# Frontmatter parsing
# --------------------------------------------------------------------------

try:
    if os.environ.get("SKILL_BUDGET_NO_YAML"):
        raise ImportError("yaml disabled by SKILL_BUDGET_NO_YAML")
    import yaml as _yaml  # type: ignore
except ImportError:
    _yaml = None


def split_frontmatter(text):
    """Return (frontmatter_text, body_text). Raise ParseError if absent/unterminated."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ParseError("no frontmatter (file must start with ---)")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise ParseError("unterminated frontmatter")


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        out = []
        i = 1
        end = len(s) - 1
        esc = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "r": "\r", "0": "\0"}
        while i < end:
            c = s[i]
            if c == "\\" and i + 1 < end:
                nxt = s[i + 1]
                out.append(esc.get(nxt, "\\" + nxt))
                i += 2
            else:
                out.append(c)
                i += 1
        return "".join(out)
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    return s


def _scalar(s):
    s = s.strip()
    if s[:1] in ('"', "'"):
        if len(s) < 2 or s[-1] != s[0]:
            raise ParseError("unterminated quoted scalar: %s" % s[:40])
        return _unquote(s)
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", ""):
        return None
    return s


def _split_flow(inner):
    parts, cur, quote, depth = [], [], None, 0
    i = 0
    while i < len(inner):
        c = inner[i]
        if quote:
            cur.append(c)
            if c == "\\" and quote == '"' and i + 1 < len(inner):
                cur.append(inner[i + 1])
                i += 1
            elif c == quote:
                quote = None
        elif c in ('"', "'"):
            quote = c
            cur.append(c)
        elif c in "{[":
            depth += 1
            cur.append(c)
        elif c in "}]":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if quote:
        raise ParseError("unterminated quote in flow collection")
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def _split_key(item):
    """Split 'key: value' (value may be quoted); return (key, value_str)."""
    item = item.strip()
    if item[:1] in ('"', "'"):
        q = item[0]
        j = 1
        while j < len(item):
            if item[j] == "\\" and q == '"':
                j += 2
                continue
            if item[j] == q:
                break
            j += 1
        key = _unquote(item[: j + 1])
        rest = item[j + 1:].lstrip()
        if not rest.startswith(":"):
            raise ParseError("bad mapping entry: %s" % item[:40])
        return key, rest[1:].strip()
    m = re.match(r"^([^:]+?)\s*:(?:\s+(.*))?$", item)
    if not m:
        raise ParseError("bad mapping entry: %s" % item[:40])
    return m.group(1).strip(), (m.group(2) or "").strip()


def _flow(s):
    s = s.strip()
    if s.startswith("{"):
        if not s.endswith("}"):
            raise ParseError("unterminated flow mapping")
        out = {}
        for part in _split_flow(s[1:-1]):
            k, v = _split_key(part)
            out[k] = _value(v)
        return out
    if s.startswith("["):
        if not s.endswith("]"):
            raise ParseError("unterminated flow list")
        return [_value(p) for p in _split_flow(s[1:-1])]
    return _scalar(s)


def _value(s):
    s = s.strip()
    if s[:1] in "{[":
        return _flow(s)
    return _scalar(s)


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _block_scalar(header, lines):
    """header like '>' '|-' '>+'; lines are raw (indented) content lines."""
    style = header[0]
    chomp = "clip"
    if "-" in header[1:]:
        chomp = "strip"
    elif "+" in header[1:]:
        chomp = "keep"
    # drop trailing blank lines for non-keep, remember count for keep
    trailing = 0
    while lines and not lines[-1].strip():
        lines = lines[:-1]
        trailing += 1
    ind = None
    for ln in lines:
        if ln.strip():
            ind = _indent(ln)
            break
    if ind is None:
        return ""
    content = [ln[ind:] if len(ln) >= ind else "" for ln in lines]
    if style == "|":
        text = "\n".join(content)
    else:
        text = ""
        prev_blank = False
        for idx, ln in enumerate(content):
            if idx == 0:
                text = ln
            elif not ln.strip():
                text += "\n"
                prev_blank = True
            elif prev_blank or ln.startswith(" ") or content[idx - 1].startswith(" "):
                text += ("" if prev_blank else "\n") + ln
                prev_blank = False
            else:
                text += " " + ln
                prev_blank = False
    if chomp == "strip":
        return text
    if chomp == "keep":
        return text + "\n" * (1 + trailing)
    return text + "\n"


def _fallback_parse(fm):
    lines = fm.split("\n")
    out = {}
    i = 0
    n = len(lines)

    def collect(start, parent_indent):
        j = start
        buf = []
        while j < n and (
            not lines[j].strip()
            or _indent(lines[j]) > parent_indent
            or (parent_indent == 0 and lines[j].startswith("- "))  # unindented block list
        ):
            buf.append(lines[j])
            j += 1
        return buf, j

    while i < n:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) != 0:
            raise ParseError("unexpected indentation: %s" % line[:40])
        key, rest = _split_key(line)
        buf, j = collect(i + 1, 0)
        if rest[:1] in (">", "|") and re.match(r"^[>|][+-]?\d*$", rest):
            out[key] = _block_scalar(rest, buf)
        elif rest == "" or rest.startswith("#"):
            nonblank = [b for b in buf if b.strip() and not b.lstrip().startswith("#")]
            if not nonblank:
                out[key] = None
            elif nonblank[0].lstrip().startswith("- "):
                out[key] = [_value(b.lstrip()[2:]) for b in nonblank if b.lstrip().startswith("- ")]
            else:
                sub = {}
                for b in nonblank:
                    k, v = _split_key(b)
                    sub[k] = _value(v)
                out[key] = sub
        else:
            cont = [b.strip() for b in buf if b.strip()]
            if rest[:1] in ('"', "'"):
                joined = " ".join([rest] + cont)
                out[key] = _scalar(joined)
            elif rest[:1] in "{[":
                out[key] = _flow(" ".join([rest] + cont))
            else:
                out[key] = _scalar(" ".join([rest] + cont))
        i = j
    return out


def parse_frontmatter(text):
    """Return (dict, body). Raise ParseError on anything unparseable."""
    fm, body = split_frontmatter(text)
    if _yaml is not None:
        try:
            data = _yaml.safe_load(fm)
        except _yaml.YAMLError as exc:
            raise ParseError("invalid YAML frontmatter: %s" % str(exc).splitlines()[0])
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ParseError("frontmatter is not a mapping")
        return data, body
    return _fallback_parse(fm), body


# --------------------------------------------------------------------------
# Collecting skills / commands
# --------------------------------------------------------------------------


def _truthy(v):
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


def _moved_to(meta):
    if isinstance(meta, dict):
        v = meta.get("moved-to")
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


class Item(object):
    def __init__(self, path, kind, fm, body, text):
        self.path = path
        self.kind = kind  # "skill" | "command"
        self.fm = fm
        self.body = body
        self.text = text
        self.hidden = _truthy(fm.get("disable-model-invocation"))
        self.moved_to = _moved_to(fm.get("metadata")) if self.hidden else None

    @property
    def is_stub(self):
        return self.hidden and self.moved_to is not None

    @property
    def chars(self):
        total = 0
        for key in ("description", "when_to_use"):
            v = self.fm.get(key)
            if v is not None:
                total += len(str(v))
        return total


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ParseError("cannot read %s: %s" % (path, exc))


def _load(path, kind):
    text = _read(path)
    try:
        fm, body = parse_frontmatter(text)
    except ParseError as exc:
        raise ParseError("%s: %s" % (path, exc))
    return Item(path, kind, fm, body, text)


def collect(skills_dir, commands_dir=None):
    if not os.path.isdir(skills_dir):
        raise ParseError("not a directory: %s" % skills_dir)
    items = []
    for name in sorted(os.listdir(skills_dir)):
        p = os.path.join(skills_dir, name, "SKILL.md")
        if os.path.isfile(p):
            items.append(_load(p, "skill"))
    if commands_dir is not None:
        if not os.path.isdir(commands_dir):
            raise ParseError("not a directory: %s" % commands_dir)
        for name in sorted(os.listdir(commands_dir)):
            p = os.path.join(commands_dir, name)
            if name.endswith(".md") and os.path.isfile(p):
                items.append(_load(p, "command"))
    return items


def measure(skills_dir, commands_dir=None):
    items = collect(skills_dir, commands_dir)
    listed = [it for it in items if not it.hidden]
    return {
        "listed_chars": sum(it.chars for it in listed),
        "listed_skills": len(listed),
        "stubs": sum(1 for it in items if it.is_stub),
    }


# --------------------------------------------------------------------------
# check-routers
# --------------------------------------------------------------------------

# Files that exist only in the built plugin (produced by `npm run build`), not in src/.
BUILD_GENERATED = {"bin/aw"}
_ROW_PHASE = re.compile(r"^`([^`\s|]+)`$")
_VAR_PATH = re.compile(r"\$\{(CLAUDE_SKILL_DIR|CLAUDE_PLUGIN_ROOT)\}/([^\s`)\]\"'>]+)")
_MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
_REL_TICK = re.compile(r"`(\.{1,2}/[^`\s]+)`")


def _phase_table(lines):
    """Return (heading_line_number or None, [phase names])."""
    heading = None
    for idx, ln in enumerate(lines):
        if re.match(r"^##\s+Phases\s*$", ln):
            heading = idx
            break
    if heading is None:
        return None, []
    phases = []
    started = False
    for ln in lines[heading + 1:]:
        s = ln.strip()
        if s.startswith("|"):
            started = True
            cells = [c.strip() for c in s.strip("|").split("|")]
            m = _ROW_PHASE.match(cells[0]) if cells else None
            if m:
                phases.append(m.group(1))
        elif started:
            break
        elif s.startswith("#"):
            break
    return heading + 1, phases


def _strip_target(t):
    return t.split("#", 1)[0].split("?", 1)[0]


def check_routers(skills_dir, commands_dir=None):
    items = collect(skills_dir, commands_dir)
    problems = []
    plugin_root = os.path.dirname(os.path.abspath(skills_dir.rstrip("/")))

    routers = {}
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if os.path.isdir(os.path.join(d, "phases")) and os.path.isfile(os.path.join(d, "SKILL.md")):
            routers[name] = d

    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if os.path.isdir(os.path.join(d, "phases")) and not os.path.isfile(os.path.join(d, "SKILL.md")):
            problems.append("router %s: has phases/ but no SKILL.md" % name)

    for name, d in routers.items():
        item = next(it for it in items if it.kind == "skill" and os.path.dirname(it.path) == d)
        label = "router %s" % name
        lines = item.text.split("\n")
        n_lines = len(lines) - 1 if item.text.endswith("\n") else len(lines)
        if n_lines > MAX_SKILL_LINES:
            problems.append("%s: SKILL.md has %d lines (max %d)" % (label, n_lines, MAX_SKILL_LINES))
        desc_len = item.chars  # description + when_to_use
        if desc_len > MAX_DESCRIPTION_CHARS:
            problems.append("%s: description + when_to_use is %d chars (max %d)" % (label, desc_len, MAX_DESCRIPTION_CHARS))
        if not item.fm.get("argument-hint"):
            problems.append("%s: missing argument-hint" % label)

        line_no, table = _phase_table(lines)
        if line_no is None:
            problems.append("%s: no '## Phases' table" % label)
        elif line_no > MAX_PHASES_LINE:
            problems.append("%s: '## Phases' at line %d (must be at or before line %d)" % (label, line_no, MAX_PHASES_LINE))
        phase_dir = os.path.join(d, "phases")
        files = sorted(f[:-3] for f in os.listdir(phase_dir) if f.endswith(".md"))
        for ph in table:
            if ph not in files:
                problems.append("%s: phase `%s` in table has no phases/%s.md" % (label, ph, ph))
        for f in files:
            if f not in table:
                problems.append("%s: phases/%s.md is missing from the '## Phases' table" % (label, f))

        for f in files:
            pf = os.path.join(phase_dir, f + ".md")
            text = _read(pf)
            for var, rel in _VAR_PATH.findall(text):
                rel = rel.rstrip(".,;:!?")
                base = d if var == "CLAUDE_SKILL_DIR" else plugin_root
                if "$" in rel:
                    # A runtime shell variable (e.g. ${LANG_LOWER}) cannot be resolved statically:
                    # verify the static directory prefix instead.
                    prefix = os.path.dirname(rel.split("$", 1)[0])
                    if prefix and not os.path.isdir(os.path.join(base, prefix)):
                        problems.append("%s: phases/%s.md: ${%s}/%s does not resolve" % (label, f, var, rel))
                    continue
                if var == "CLAUDE_PLUGIN_ROOT" and _strip_target(rel) in BUILD_GENERATED:
                    continue
                if not os.path.exists(os.path.join(base, _strip_target(rel))):
                    problems.append("%s: phases/%s.md: ${%s}/%s does not resolve" % (label, f, var, rel))
            rels = set()
            for t in _MD_LINK.findall(text):
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", t) or t.startswith(("#", "/", "$", "~")):
                    continue
                rels.add(t)
            for t in _REL_TICK.findall(text):
                rels.add(t)
            for t in sorted(rels):
                tt = _strip_target(t)
                if tt and not os.path.exists(os.path.join(phase_dir, tt)):
                    problems.append("%s: phases/%s.md: relative path %s does not resolve" % (label, f, t))

    for it in items:
        if not it.is_stub:
            continue
        label = "stub %s" % os.path.relpath(it.path, os.path.dirname(os.path.abspath(skills_dir.rstrip("/"))))
        parts = it.moved_to.split()
        if len(parts) != 2:
            problems.append('%s: moved-to "%s" must be "<router> <phase>"' % (label, it.moved_to))
        else:
            r, ph = parts
            if r not in routers:
                problems.append("%s: moved-to router '%s' does not exist" % (label, r))
            elif not os.path.isfile(os.path.join(routers[r], "phases", ph + ".md")):
                problems.append("%s: moved-to phase '%s %s' does not exist" % (label, r, ph))
        if "$ARGUMENTS" not in it.body:
            problems.append("%s: body has no $ARGUMENTS" % label)
    return problems


# --------------------------------------------------------------------------
# reads / final-text
# --------------------------------------------------------------------------


def _events(stream):
    for raw in stream:
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        if isinstance(ev, dict):
            yield ev


def stream_reads(stream):
    out = []
    for ev in _events(stream):
        if ev.get("type") != "assistant":
            continue
        msg = ev.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Read":
                inp = c.get("input")
                fp = inp.get("file_path") if isinstance(inp, dict) else None
                if fp:
                    out.append(fp)
    return out


def stream_result(stream):
    last = None
    for ev in _events(stream):
        if ev.get("type") == "result":
            last = ev
    return last


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("skill_budget: %s\n" % message)
        raise SystemExit(2)


def _build_parser():
    p = _Parser(prog="skill_budget.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd")
    sub.required = True

    m = sub.add_parser("measure")
    m.add_argument("skills_dir")
    m.add_argument("--commands")
    m.add_argument("--field", choices=["listed_chars", "listed_skills", "stubs"])

    c = sub.add_parser("check-routers")
    c.add_argument("skills_dir")
    c.add_argument("--commands")

    g = sub.add_parser("gate")
    g.add_argument("skills_dir")
    g.add_argument("--commands")
    g.add_argument("--baseline", required=True)
    g.add_argument("--min-cut", required=True, type=float)

    r = sub.add_parser("reads")
    r.add_argument("--require-success", action="store_true")

    sub.add_parser("final-text")
    return p


def _run(args):
    if args.cmd == "measure":
        res = measure(args.skills_dir, args.commands)
        print(res[args.field] if args.field else json.dumps(res))
        return 0

    if args.cmd == "check-routers":
        problems = check_routers(args.skills_dir, args.commands)
        for line in problems:
            print(line)
        return 1 if problems else 0

    if args.cmd == "gate":
        try:
            with open(args.baseline, encoding="utf-8") as fh:
                base = json.load(fh)
            base_chars = base["listed_chars"]
            if not isinstance(base_chars, int) or isinstance(base_chars, bool) or base_chars <= 0:
                raise ValueError("listed_chars must be a positive integer")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ParseError("bad baseline %s: %s" % (args.baseline, exc))
        now = measure(args.skills_dir, args.commands)["listed_chars"]
        cut = (1.0 - float(now) / base_chars) * 100.0
        ok = now * 100 <= base_chars * (100 - args.min_cut)
        print("baseline listed_chars=%d now=%d cut=%.1f%% required=%g%% %s"
              % (base_chars, now, cut, args.min_cut, "PASS" if ok else "FAIL"))
        return 0 if ok else 1

    if args.cmd == "reads":
        data = sys.stdin.read().splitlines()
        if not any(True for _ in _events(data)):
            sys.stderr.write("skill_budget: empty or non-JSON stream\n")
            return 2
        if args.require_success:
            res = stream_result(data)
            if not res or res.get("subtype") != "success":
                sys.stderr.write("skill_budget: stream did not end in a successful result\n")
                return 2
        for fp in stream_reads(data):
            print(fp)
        return 0

    if args.cmd == "final-text":
        res = stream_result(sys.stdin.read().splitlines())
        if res is None:
            raise ParseError("no result event in stream")
        text = res.get("result")
        print(text if isinstance(text, str) else "")
        return 0
    return 2


def main(argv=None):
    try:
        args = _build_parser().parse_args(argv)
        return _run(args)
    except ParseError as exc:
        sys.stderr.write("skill_budget: %s\n" % exc)
        return 2
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    except Exception as exc:  # a crash must never look like a gate result
        sys.stderr.write("skill_budget: unexpected error: %r\n" % (exc,))
        return 2


if __name__ == "__main__":
    sys.exit(main())
