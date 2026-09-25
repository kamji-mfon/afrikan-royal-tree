"""Rebuild the Afrikan royal dynasty tree as data from Royal_Family_Tree_flat.pdf.

The PDF is a flat CAD export (one 5760x6480 pt page): names are a text layer,
lineage is drawn as vector strokes with triangle arrowheads pointing at the
child. We read both with poppler (no Python PDF dependency) and join them by
geometry, so the data is traceable to the drawing rather than retyped.

    python3 royal_tree/extract.py ~/Downloads/Royal_Family_Tree_flat.pdf

Writes royal_tree/tree.json. The PDF itself is not kept in the repo.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile

PAGE_H = 6480
HERE = os.path.dirname(os.path.abspath(__file__))

# Junctions the geometry cannot decide: plain bus bars with no arrowhead, where
# siblings share a row with their parent's bar. Checked by eye against the PDF.
EXTRA_EDGES = [
    ("Ewanjè", "Mahénjama"), ("Ewanjè", "Ekande"), ("Ewanjè", "Bangi"),
    ("Nya 2", "Ngassam II"), ("Nya 2", "Yomi"), ("Nya 2", "Tchatchoua"),
    ("Ngami", "Nenaton"), ("Ngami", "Tchamgo"),
    ("Essedi", "Nsien"), ("Nebijou", "Nsien"),
    ("Essedi", "Mbupwet"), ("Nebijou", "Mbupwet"),
    ("Mbupwet", "Nyimbu"), ("Mbupwet", "Mbon Papi"),
    # The chart hangs Yen's children under her alone; the book (printed p. 434)
    # makes them children of Yen AND Mforifum, and Mforifum carries the lineage.
    ("Mforifum", "Ndjiason"), ("Mforifum", "Nditam"), ("Mforifum", "Sow"),
    ("Mforifum", "Ncharé"), ("Mforifum", "Mbam"),
]
# Horizontal marriage lines (a bar between two names on the same row).
SPOUSES = [("Essedi", "Nebijou"), ("Mbupwet", "Mbum Ngan Ha"),
           ("Nguti", "Ntuno"), ("Nyanci Nuko", "Menshi"), ("Yen", "Mforifum")]

# Branch labels are an ADDITION, not in the source drawing: each names the
# historical polity a sub-lineage matches by its king list. Shown flagged in the UI.
BRANCHES = {
    "Balali Bunama": "Mali (Keita)",
    "Ndiaye (Njai)": "Jolof (Wolof)",
    "Oraniyan": "Benin (Oba)",
    "Sanda": "Kanem–Bornu (Sayfawa)",
    "Mbèdi": "Duala (Sawa)",
    "Ncharé": "Bamum",
}


def poppler(pdf, tmp):
    words, svg = os.path.join(tmp, "w.html"), os.path.join(tmp, "t.svg")
    subprocess.run(["pdftotext", "-bbox", pdf, words], check=True)
    subprocess.run(["pdftocairo", "-svg", pdf, svg], check=True)
    return open(words, encoding="utf-8").read(), open(svg, encoding="utf-8").read()


def names(words_html):
    """Words -> name boxes: join same-baseline words (gap <= 15 pt, a space is
    ~10) and stack two-line names (vertical gap < 10 pt, overlapping x)."""
    w = [dict(x0=float(a), y0=float(b), x1=float(c), y1=float(d), t=html.unescape(t))
         for a, b, c, d, t in re.findall(
             r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)',
             words_html)]
    w = [x for x in w if x["y1"] - x["y0"] < 100]  # the title is ~200 pt tall
    w.sort(key=lambda r: (round(r["y0"]), r["x0"]))
    rows = []
    for x in w:
        r = rows[-1] if rows else None
        if r and abs(r["y0"] - x["y0"]) < 2 and 0 <= x["x0"] - r["x1"] <= 15:
            r["t"] += " " + x["t"]
            r["x1"] = x["x1"]
        else:
            rows.append(dict(x))
    out = []
    for n in sorted(rows, key=lambda r: (r["y0"], r["x0"])):
        for m in out:
            if 0 <= n["y0"] - m["y1"] < 10 and min(n["x1"], m["x1"]) > max(n["x0"], m["x0"]):
                m["t"] += " " + n["t"]
                m["x0"], m["x1"], m["y1"] = min(m["x0"], n["x0"]), max(m["x1"], n["x1"]), n["y1"]
                break
        else:
            out.append(n)
    return out


def strokes(svg):
    """Connector strokes -> (segments, arrow tips). Glyphs are filled, so only
    fill="none" paths are lines; a closed 3-point path is an arrowhead whose
    middle vertex is the tip."""
    segs, tips = [], []
    for d in re.findall(r'<path fill="none" stroke-width="(?:0\.25|0\.5|1)"[^>]*d="([^"]+)"', svg):
        pts = [(float(a), PAGE_H - float(b)) for a, b in re.findall(r"([\d.\-]+) ([\d.\-]+)", d)]
        if "Z" in d and len(pts) >= 3:
            tips.append(pts[1])
        else:
            segs += list(zip(pts, pts[1:]))
    return segs, tips


def on_segment(p, s, tol=3):
    (ax, ay), (bx, by) = s
    l2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if l2 == 0 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / l2))
    return ((ax + t * (bx - ax) - p[0]) ** 2 + (ay + t * (by - ay) - p[1]) ** 2) ** 0.5 < tol


def connectors(segs):
    """Group segments that touch (shared end or T-junction) into one connector.
    ponytail: O(n^2) over ~360 segments; grid-bucket if a bigger chart appears."""
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, s in enumerate(segs):
        for j in range(i):
            u = segs[j]
            if any(on_segment(p, u) for p in s) or any(on_segment(p, s) for p in u):
                parent[find(i)] = find(j)
    groups = {}
    for i, s in enumerate(segs):
        groups.setdefault(find(i), []).append(s)
    return list(groups.values())


def edges(nodes, segs, tips):
    def nearest(p, tol=14):
        best, bd = None, tol
        for i, n in enumerate(nodes):
            dx = max(n["x0"] - p[0], 0, p[0] - n["x1"])
            dy = max(n["y0"] - p[1], 0, p[1] - n["y1"])
            if (dx * dx + dy * dy) ** 0.5 < bd:
                best, bd = i, (dx * dx + dy * dy) ** 0.5
        return best

    out = set()
    for group in connectors(segs):
        touched, tipped = set(), set()
        for p in (p for s in group for p in s):
            i = nearest(p)
            if i is None:
                continue
            touched.add(i)
            if any(abs(p[0] - t[0]) < 2 and abs(p[1] - t[1]) < 2 for t in tips):
                tipped.add(i)
        if tipped and touched - tipped:
            out |= {(a, b) for a in touched - tipped for b in tipped}
        elif len(touched) > 1:  # bare bus bar: the name clearly above it is the parent
            top = min(touched, key=lambda i: nodes[i]["y0"])
            rest = touched - {top}
            if all(nodes[i]["y0"] - nodes[top]["y0"] > 15 for i in rest):
                out |= {(top, i) for i in rest}
    return out


def build(pdf):
    with tempfile.TemporaryDirectory() as tmp:
        words_html, svg = poppler(pdf, tmp)
    nodes = names(words_html)
    idx = {n["t"]: i for i, n in enumerate(nodes)}
    # Names repeat (Dika, Eweka, Ngala II...), so a by-name override must hit exactly one person.
    named = {x for pair in EXTRA_EDGES + SPOUSES for x in pair} | set(BRANCHES)
    for name in named:
        assert sum(n["t"] == name for n in nodes) == 1, f"override name not unique/found: {name}"
    links = edges(nodes, *strokes(svg))
    for a, b in EXTRA_EDGES:
        links.add((idx[a], idx[b]))
    parents = {}
    for a, b in links:
        parents.setdefault(b, set()).add(a)
    # A couple's child hangs under the partner who is in the lineage (has a
    # parent); the other partner is shown as a spouse.
    people = []
    for i, n in enumerate(nodes):
        ps = sorted(parents.get(i, ()), key=lambda p: (p not in parents, nodes[p]["x0"]))
        people.append(dict(id=i, name=n["t"], parent=ps[0] if ps else None,
                           co_parents=ps[1:], x=round(n["x0"]), y=round(n["y0"])))
    for a, b in SPOUSES:
        people[idx[a]].setdefault("spouses", []).append(idx[b])
        people[idx[b]].setdefault("spouses", []).append(idx[a])
    for name, label in BRANCHES.items():
        people[idx[name]]["branch"] = label
    return people


def check(people):
    roots = [p for p in people if p["parent"] is None and "spouses" not in p]
    assert len(roots) == 1 and roots[0]["name"] == "Ikale", [r["name"] for r in roots]
    by = {p["id"]: p for p in people}
    for p in people:  # no cycles: every chain reaches the root
        seen, q = set(), p
        while q["parent"] is not None:
            assert q["id"] not in seen, p["name"]
            seen.add(q["id"])
            q = by[q["parent"]]


if __name__ == "__main__":
    people = build(os.path.expanduser(sys.argv[1]))
    check(people)
    with open(os.path.join(HERE, "tree.json"), "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(people)} people, {sum(p['parent'] is not None for p in people)} parent links")
