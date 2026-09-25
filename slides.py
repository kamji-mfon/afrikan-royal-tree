"""Build the royal-tree slide deck and standalone SVG graphics from tree.json.

    python3 royal_tree/slides.py <deck_root>

Writes <deck_root>/project/deck.json + project/slides/*.html (Slides artifact
files) and royal_tree/graphics/*.svg (each slide graphic plus a full poster).
Every number on a slide is computed here from tree.json, never typed in.
"""
import collections
import datetime
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BG, BG2, INK, MUTED = "#f6efe3", "#ead9bf", "#2b2118", "#5f4f3e"
RED, GOLD, DARK, LIGHT, LMUTED = "#9a3b1f", "#b8862b", "#1f1812", "#f1e7d8", "#cdbba3"
TRUNK = "#8a6a3a"
HEAD = "'Cormorant Garamond', Georgia, serif"
BODY = "'Libre Baskerville', Georgia, serif"
SVG_FONT = "Georgia, 'Times New Roman', serif"

# Branch head -> (slide id, title, colour). Titles follow the book's notes where
# they name the polity; the tree's own BRANCHES label is shown as unconfirmed.
BRANCHES = {
    "Sanda": ("mandara", "The Mandara sultans", "#2f5d8a"),
    "Ncharé": ("bamum", "The Bamum kings", "#a8323a"),
    "Mbèdi": ("duala", "The Duala (Sawa)", "#2a7f7a"),
    "Oraniyan": ("benin", "Oraniyan and Benin", "#c0632b"),
    "Balali Bunama": ("west", "Mali and Jolof", "#4f7a3a"),
    "Ndiaye (Njai)": ("west", "Mali and Jolof", "#7a4a8c"),
}


class Tree:
    def __init__(self, rows):
        self.rows = rows
        self.by = {r["id"]: r for r in rows}
        self.kids = collections.defaultdict(list)
        for r in rows:
            if r["parent"] is not None:
                self.kids[r["parent"]].append(r["id"])
        self.ids = {}
        for r in rows:
            self.ids.setdefault(r["name"], r["id"])

    def name(self, i):
        return self.by[i]["name"]

    def up(self, i):
        """i and its ancestors, nearest first."""
        out = []
        while i is not None:
            out.append(i)
            i = self.by[i]["parent"]
        return out

    def sub(self, i):
        return [i] + [d for k in self.kids[i] for d in self.sub(k)]

    def height(self, i):
        return 1 + max([self.height(k) for k in self.kids[i]] or [0])

    def colour(self, i):
        for a in self.up(i):
            if self.name(a) in BRANCHES:
                return BRANCHES[self.name(a)][2]
        return TRUNK


# ---------------------------------------------------------------- graphics

def esc(s):
    return html.escape(s, quote=False)


def forest_layout(t, roots, keep):
    """Tidy layout over the kept nodes: leaves get consecutive slots, a parent
    sits over the middle of its kept children. Returns {id: (level, slot)}."""
    kkids = collections.defaultdict(list)
    for i in keep:
        for a in t.up(i)[1:]:
            if a in keep:
                kkids[a].append(i)
                break
    pos, nxt = {}, [0]

    def walk(i, lvl):
        ks = sorted(kkids[i], key=lambda k: t.by[k]["x"])
        for k in ks:
            walk(k, lvl + 1)
        if ks:
            pos[i] = (lvl, (pos[ks[0]][1] + pos[ks[-1]][1]) / 2)
        else:
            pos[i] = (lvl, nxt[0])
            nxt[0] += 1

    for r in roots:
        walk(r, 0)
    return pos, kkids


def label(x, y, text, size, fill, weight=400):
    words = text.split()
    lines = [text]
    if len(text) > 14 and len(words) > 1:  # wrap long names to two lines
        cut = min(range(1, len(words)), key=lambda n: abs(len(" ".join(words[:n])) - len(text) / 2))
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    y0 = y - (len(lines) - 1) * size * 0.55
    spans = "".join(f'<tspan x="{x:.0f}" y="{y0 + n * size * 1.1:.0f}">{esc(s)}</tspan>'
                    for n, s in enumerate(lines))
    return (f'<text font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="middle" '
            f'dominant-baseline="middle" stroke="{BG}" stroke-width="7" paint-order="stroke" '
            f'stroke-linejoin="round">{spans}</text>')


def tree_svg(t, roots, keep, w, h, *, horizontal=False, font=24, labels=None, spouses=(), gaps=False):
    """Elbow dendrogram of the kept nodes. labels=None labels every node."""
    pos, kkids = forest_layout(t, roots, keep)
    levels = max(p[0] for p in pos.values()) + 1
    slots = max(p[1] for p in pos.values()) + 1
    pad = font * 3.2

    def xy(i):
        lvl, slot = pos[i]
        along = (w if horizontal else h) - 2 * pad
        across = (h if horizontal else w)
        a = pad + (lvl * along / (levels - 1) if levels > 1 else along / 2)
        b = (slot + 0.5) * across / slots
        return (a, b) if horizontal else (b, a)

    lines, dots, texts = [], [], []
    for p, ks in kkids.items():
        px, py = xy(p)
        for k in ks:
            cx, cy = xy(k)
            mid = f"H{(px + cx) / 2:.0f}V{cy:.0f}H{cx:.0f}" if horizontal else f"V{(py + cy) / 2:.0f}H{cx:.0f}V{cy:.0f}"
            lines.append(f'<path d="M{px:.0f} {py:.0f}{mid}" stroke="{t.colour(k)}"/>')
            gap = t.up(k).index(p)
            if gaps and gap > 1:
                texts.append(label((px + cx) / 2 if horizontal else cx + font * 1.6, (py + cy) / 2,
                                   f"+{gap - 1} gen.", font * 0.8, MUTED))
    for a, b in spouses:
        (ax, ay), (bx, by_) = xy(a), xy(b)
        lines.append(f'<path d="M{ax:.0f} {ay:.0f}L{bx:.0f} {by_:.0f}" stroke="{RED}" stroke-dasharray="8 8"/>')
    r = 3 if len(pos) > 100 else 6
    for i in pos:
        x, y = xy(i)
        dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{t.colour(i)}"/>')
        if labels is None or i in labels:
            texts.append(label(x, y, t.name(i), font, INK, 700 if t.by[i].get("note") else 400))
    width = 2 if len(pos) > 100 else 3
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'aria-label="{{alt}}"><g fill="none" stroke-width="{width}" stroke-linecap="round">'
            + "".join(lines) + "</g>" + "".join(dots) + f'<g font-family="{SVG_FONT}">' + "".join(texts) + "</g></svg>")


def snake_svg(t, chain, w, h, cols=12, font=22):
    """The single-line trunk as a boustrophedon of names; noted names in red."""
    rows = -(-len(chain) // cols)
    cw, rh = w / cols, h / rows

    def xy(n):
        row, col = divmod(n, cols)
        col = col if row % 2 == 0 else cols - 1 - col
        return (col + 0.5) * cw, (row + 0.35) * rh

    pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in map(xy, range(len(chain))))
    out = [f'<polyline points="{pts}" fill="none" stroke="{TRUNK}" stroke-width="3" stroke-linejoin="round"/>']
    for n, i in enumerate(chain):
        x, y = xy(n)
        noted = bool(t.by[i].get("note"))
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{8 if noted else 5}" fill="{RED if noted else TRUNK}"/>')
        out.append(label(x, y + font * 1.3, t.name(i), font, RED if noted else INK, 700 if noted else 400))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'aria-label="{{alt}}"><g font-family="{SVG_FONT}">' + "".join(out) + "</g></svg>")


# ---------------------------------------------------------------- slide markup

def section(sid, body, notes, bg=BG, fg=INK, layout="display:flex; flex-direction:column; gap:32px"):
    return (f'<section id="{sid}" data-transition="fade" style="background:{bg}; color:{fg}; '
            f'font-family:{BODY}; padding:128px; {layout}">\n{body}\n<aside>{esc(notes)}</aside>\n</section>\n')


def eyebrow(text, color=RED):
    return f'<p style="font-size:24px; letter-spacing:4px; text-transform:uppercase; color:{color}">{esc(text)}</p>'


def h2(text, color=INK):
    return f'<h2 style="font-family:{HEAD}; font-size:72px; font-weight:600; line-height:1.1; color:{color}">{esc(text)}</h2>'


def para(text, size=28, color=MUTED, extra=""):
    return f'<p style="font-size:{size}px; line-height:1.5; color:{color}{extra}">{text}</p>'


def card(title, text, bg="#fbf6ec"):
    return (f'<div style="flex:1; display:flex; flex-direction:column; gap:16px; background:{bg}; '
            f'padding:40px; border:1px solid #d9c6a8; border-radius:16px">'
            f'<h3 style="font-family:{HEAD}; font-size:40px; font-weight:600; color:{INK}">{esc(title)}</h3>'
            f'{para(text, 24)}</div>')


def figure(svg, alt):
    return svg.replace("{alt}", esc(alt).replace('"', "'"))


# ---------------------------------------------------------------- slides

def trunk_chain(t):
    i, chain = t.ids["Ikale"], []
    while len(t.kids[i]) == 1:
        chain.append(i)
        i = t.kids[i][0]
    return chain, i  # i = first node with more than one child


def s_cover(t):
    body = (f'<div style="flex:1"></div>{eyebrow("Genealogy of the Sinegala nationality in central Africa", GOLD)}'
            f'<h1 style="font-family:{HEAD}; font-size:120px; font-weight:600; line-height:1.05; color:{LIGHT}">Afrikan Royal Dynasty Tree</h1>'
            + para("From Ikale, placed by Prince Dika Akwa nya Bonambela at the end of Egypt's 17th dynasty, "
                   "to the royal houses of Mandara, Bamum, Duala and Benin.", 32, LMUTED, "; width:1300px"))
    return section("cover", body, "A walk through the royal tree rebuilt from the chart in Dika Akwa's book.", DARK, LIGHT), None


def s_sources(t):
    body = (eyebrow("Where it comes from") + h2("One chart, one book")
            + '<div style="display:flex; gap:32px">'
            + card("The chart", "A CAD export of the book's “Généalogie de la nationalité Sinegala en Afrique centrale” "
                   "(printed p. 433). Names and parent links were read from its geometry: an arrowhead marks the child.")
            + card("The book", "Prince Dika Akwa nya Bonambela, Les descendants des pharaons à travers l'Afrique "
                   "(Éditions Osiris-Africa), 438 pages. Notes paraphrase pp. 313–337 and 428–434.")
            + card("Hand fixes", "Where geometry and the book disagree, each fix was checked against the PDF and is listed "
                   "at the end of this deck. Branch names are our labels, not the chart's.")
            + "</div>")
    return section("sources", body, "Every name comes from the chart; every note from the book."), None


def s_numbers(t):
    chain, _ = trunk_chain(t)
    longest = max(len(t.up(r["id"])) for r in t.rows)
    noted = sum(bool(r.get("note")) for r in t.rows)
    unmatched = sum(not r["mentions"] for r in t.rows)
    stats = [(len(t.rows), "names on the chart"), (longest, "generations on the longest line"),
             (len(chain), "generations before the first fork"), (noted, "names with a note from the book")]
    tiles = "".join(
        f'<div style="flex:1; display:flex; flex-direction:column; gap:8px; border-top:4px solid {GOLD}; padding:24px 0px 0px 0px">'
        f'<p style="font-family:{HEAD}; font-size:120px; font-weight:600; line-height:1; color:{INK}">{n}</p>'
        f'{para(esc(lbl), 28)}</div>' for n, lbl in stats)
    body = (eyebrow("At a glance") + h2("A single line, then a fan") + f'<div style="display:flex; gap:48px">{tiles}</div>'
            + para(f"{unmatched} names never match a page of the book by spelling, mostly recent Bamum, Duala "
                   "and Njike/Pokam generations; they need other sources.", 28))
    return section("numbers", body, "All figures computed from tree.json by slides.py.", BG2), None


def s_overview(t):
    w, h = 1664, 680
    root = t.ids["Ikale"]
    heads = {t.ids[n] for n in BRANCHES} | {root, trunk_chain(t)[1]}
    svg = tree_svg(t, [root], set(t.sub(root)), w, h, horizontal=True, font=22, labels=heads)
    body = eyebrow("The whole tree") + h2("Ikale to the present, left to right") + figure(svg, "Dendrogram of all descendants of Ikale, coloured by branch")
    return section("overview", body, "Each column is one generation. Gold-brown is the shared line; colours mark the branches."), ("overview", svg)


def s_ikale(t):
    note = t.by[t.ids["Ikale"]]["note"]
    body = (f'<div style="flex:1"></div>{eyebrow("The first ancestor", GOLD)}'
            f'<h2 style="font-family:{HEAD}; font-size:120px; font-weight:600; line-height:1.05; color:{LIGHT}">Ikale</h2>'
            + para(esc(note), 36, LIGHT, "; width:1400px") + para("Dika Akwa, printed p. 320", 24, LMUTED))
    return section("ikale", body, "The book's dating counts three generations per century.", DARK, LIGHT), None


def s_trunk(t):
    chain, fork = trunk_chain(t)
    w, h = 1664, 640
    svg = snake_svg(t, chain, w, h)
    body = (eyebrow(f"{len(chain)} generations, one line") + h2(f"From Ikale to {t.name(fork)}")
            + figure(svg, f"The {len(chain)} generations from Ikale to {t.name(fork)}, read left to right then back"))
    return section("trunk", body, "Red names carry a note from the book. The order of this line was read from arrow "
                   "directions and still needs checking against the Ngala-Dwala table (PDF p. 317)."), ("trunk", svg)


PAIRINGS = ["Mosi", "Dimodi IV", "Mudeta I", "Keti", "Aku Malem", "Makale I", "Kupe", "Nsekele", "Sankare"]
PHARAOH = {"Mosi": "Ahmose I", "Dimodi IV": "Thutmose IV", "Mudeta I": "Ramesses I (tentative)", "Keti": "Seti I",
           "Aku Malem": "Merneptah (tentative)", "Makale I": "Maatkare", "Kupe": "Khufu (by name)",
           "Nsekele": "Seqenenre (by name)", "Sankare": "Senkare / Sesostris I"}


def s_pharaohs(t):
    rows = "".join(f'<tr><td>{esc(n)}</td><td>{esc(PHARAOH[n])}</td><td>{", ".join(map(str, t.by[t.ids[n]]["pages"]))}</td></tr>'
                   for n in PAIRINGS)
    table = (f'<table style="font-size:28px; color:{INK}"><tr><th style="width:34%">Ancestor on the line</th>'
             f'<th style="width:46%">Pharaoh the book pairs him with</th><th style="width:20%">Pages</th></tr>{rows}</table>')
    body = (eyebrow("The book's argument") + h2("Name by name against the pharaohs") + table
            + para("The book itself warns that some pairings may be coincidence; they are its claims, not ours.", 24))
    return section("pharaohs", body, "Pairings as stated in Dika Akwa's comparative tables, pp. 317–337."), None


def skeleton(t):
    heads = [t.ids[n] for n in BRANCHES]
    keep = {t.ids["Ikale"]} | set(heads)
    for i in heads:
        path = t.up(i)
        for a, child in zip(path[1:], path):
            if len(t.kids[a]) > 1:
                keep |= {a, child}
    return keep


def s_split(t):
    w, h = 1664, 700
    svg = tree_svg(t, [t.ids["Ikale"]], skeleton(t), w, h, font=24, gaps=True)
    body = (eyebrow("Where the houses part") + h2("Mbe's three sons")
            + figure(svg, "Skeleton of the tree: only the forks that lead to the named branches, with generation gaps"))
    return section("split", body, "Mbe, early 12th century per the book, fathered Kongo Matadi (Ngala of south-central "
                   "Africa), Muyenya (probably the Igala) and Alé (the Wandala Ngala). Gaps show skipped generations."), ("split", svg)


def ancestry(t, head):
    path = t.up(head)
    top = t.ids["Mbe"] if t.ids["Mbe"] in path else t.up(head)[path.index(trunk_chain(t)[1])]
    names = [t.name(i) for i in reversed(path[: path.index(top) + 1])]
    short = names if len(names) <= 5 else names[:2] + ["…"] + names[-2:]
    return f"{' → '.join(short)} ({len(names) - 1} generations)"


def s_branch(t, sid, heads):
    w, h = 1040, 824
    keep = {i for hd in heads for i in t.sub(hd)}
    svg = tree_svg(t, heads, keep, w, h, font=22)
    meta = "".join(para(f'<span style="color:{BRANCHES[t.name(hd)][2]}">●</span> {esc(ancestry(t, hd))}', 24) for hd in heads)
    label = " · ".join(t.by[hd]["branch"] for hd in heads)
    noted = [i for i in sorted(keep, key=lambda i: len(t.up(i))) if t.by[i].get("note")][:1]
    note = card(t.name(noted[0]), t.by[noted[0]]["note"]) if noted else ""
    left = (f'<div style="display:flex; flex-direction:column; gap:24px">{eyebrow(f"{len(keep)} names")}'
            f'{h2(BRANCHES[t.name(heads[0])][1])}{meta}{para("Tree label, unconfirmed: " + esc(label), 24)}{note}</div>')
    body = left + figure(svg, f"Descendants of {', '.join(t.name(hd) for hd in heads)}")
    return section(sid, body, "Bold names carry a note from the book.",
                   layout="display:grid; grid-template-columns:592px 1040px; gap:32px"), (sid, svg)


def s_yen(t):
    w, h = 1664, 640
    ayoka, yen, mfo = t.ids["Ayoka"], t.ids["Yen"], t.ids["Mforifum"]
    keep = set(t.up(yen)[: t.up(yen).index(ayoka) + 1]) | set(t.up(mfo)[: t.up(mfo).index(ayoka) + 1]) | set(t.kids[mfo])
    svg = tree_svg(t, [ayoka], keep, w, h, font=24, spouses=[(mfo, yen)])
    body = (eyebrow("A correction from the book") + h2("Yen, daughter of Nyimbu, and Mforifum")
            + figure(svg, "Yen and Mforifum both descend from Ayoka; their five children include Ncharé"))
    return section("yen", body, "The chart hung Yen's children under Yen as a son. The book (p. 434) makes Yen a daughter "
                   "married to Mforifum, both descended from Ayoka: an endogamous union. The dashed line is the marriage."), ("yen", svg)


def s_open(t):
    body = (eyebrow("Open questions") + h2("What the sources still leave open") + '<div style="display:flex; gap:32px">'
            + card("Contradictions", "Adjara is Dawa's son on p. 428 but Adjia Makia's on p. 430. “Soka Wandala” reads as one "
                   "person on p. 428; the chart splits him in two. “Apfalaska” is a title, not a person.")
            + card("Still to read", "The Mali and Songhay charts (PDF pp. 180–181) at higher resolution; the placement of "
                   "Matchi, Aldawa Bara and Amiri Biri under Djilé III.")
            + card("Other sources", "Bamum palace histories and Duala genealogies for the generations the book never names.")
            + "</div>" + para('Interactive tree: <a href="https://kamji-mfon.github.io/afrikan-royal-tree/">kamji-mfon.github.io/afrikan-royal-tree</a>', 28))
    return section("open", body, "Full list in royal_tree/SOURCES.md.", BG2), None


def build(t):
    parts = [s_cover(t), s_sources(t), s_numbers(t), s_overview(t), s_ikale(t), s_trunk(t), s_pharaohs(t), s_split(t)]
    seen = []
    for name, (sid, _, _) in BRANCHES.items():
        if sid not in seen:
            seen.append(sid)
            parts.append(s_branch(t, sid, [t.ids[n] for n, v in BRANCHES.items() if v[0] == sid]))
    return parts + [s_yen(t), s_open(t)]


def main(root):
    t = Tree(json.load(open(os.path.join(HERE, "tree.json"), encoding="utf-8")))
    parts = build(t)
    os.makedirs(os.path.join(root, "project", "slides"), exist_ok=True)
    gdir = os.path.join(HERE, "graphics")
    os.makedirs(gdir, exist_ok=True)
    order = []
    for html_, graphic in parts:
        sid = html_.split('"', 2)[1]
        order.append(sid)
        open(os.path.join(root, "project", "slides", sid + ".html"), "w", encoding="utf-8").write(html_)
        if graphic:
            name, svg = graphic
            assert len(svg.encode()) <= 52_000, f"{name} svg over 52 KB"
            open(os.path.join(gdir, name + ".svg"), "w", encoding="utf-8").write(figure(svg, name))
    ikale = t.ids["Ikale"]
    leaves = sum(1 for i in t.sub(ikale) if not t.kids[i])
    poster = tree_svg(t, [ikale], set(t.sub(ikale)), leaves * 200, t.height(ikale) * 44, font=22)
    open(os.path.join(gdir, "royal_tree_poster.svg"), "w", encoding="utf-8").write(figure(poster, "Full royal tree"))
    deck = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "title": "Afrikan Royal Dynasty Tree", "order": order,
            "sections": {"s1": {"description": "Where the tree comes from and its shape", "start": "cover"},
                         "s2": {"description": "The single line from Ikale and the book's pharaoh pairings", "start": "ikale"},
                         "s3": {"description": "The royal houses that branch from Mbe and Mandenge", "start": "split"},
                         "s4": {"description": "Corrections and open questions", "start": "yen"}},
            "faces": {"cormorant-garamond": {"family": "Cormorant Garamond", "href": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&display=swap"},
                      "libre-baskerville": {"family": "Libre Baskerville", "href": "https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap"}},
            "designSystems": []}
    json.dump(deck, open(os.path.join(root, "project", "deck.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(order)} slides, graphics in {gdir}")


if __name__ == "__main__":
    main(sys.argv[1])
