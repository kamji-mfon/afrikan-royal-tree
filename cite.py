"""Attach source context to tree.json: hand-written notes (notes.json) plus the
book pages where each name appears.

    python3 royal_tree/cite.py "~/Downloads/LES DESCENDANTS i des PHARAONS a travers L’AFRIQUE.pdf"

The chart transcribes Dika Akwa, Les descendants des pharaons à travers
l'Afrique (the Sinegala genealogy is PDF page 430). A notes.json key is a name,
or "name@parent" when the name repeats in the tree.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PRINTED_OFFSET = 3  # printed page = PDF page + 3 (checked on PDF pp. 311, 317, 425, 428, 431)
MAX_AUTO = 6
# The book's spellings, where they differ from the chart's.
ALIASES = {
    "Mbe": ["Mbee"], "Muyenya": ["Muwenya"], "Essedi": ["Issedi"], "Mbupwet": ["Mboupwet", "Mbouepouet"],
    "Nyimbu": ["Nyimbou"], "Hosun": ["Hossoum"], "Mforifum": ["Mfenrifou"], "Nguti": ["Ngouti"],
    "Ntuno": ["Ntonno"], "Sow": ["Nsow"], "Ncharé": ["Nshare"], "Ndjiason": ["Njiasson"],
    "Ayoka": ["Ayoko"], "Sanda": ["Sukda"], "Hamidu Umar": ["Hamidou Oumar"],
}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def book_pages(pdf):
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], check=True, capture_output=True, text=True).stdout
    return [fold(p) for p in text.split("\f")]


def main(pdf):
    path = os.path.join(HERE, "tree.json")
    people = json.load(open(path, encoding="utf-8"))
    notes = json.load(open(os.path.join(HERE, "notes.json"), encoding="utf-8"))
    by_id = {p["id"]: p for p in people}
    pages = book_pages(pdf)
    patterns = {}
    for p in people:
        terms = [p["name"]] + ALIASES.get(p["name"], [])
        # Names of 3 letters or fewer (Ma, Ka, Doo...) match ordinary French words.
        terms = [t for t in terms if len(t) > 3]
        patterns[p["id"]] = re.compile(r"\b(" + "|".join(re.escape(fold(t)) for t in terms) + r")\b") if terms else None
    # A page that mentions many tree names is genealogy, not a passing namesake: rank those first.
    density = [sum(1 for rx in patterns.values() if rx and rx.search(t)) for t in pages]
    for p in people:
        rx = patterns[p["id"]]
        hits = [i for i, t in enumerate(pages) if rx and rx.search(t)]
        hits = sorted(sorted(hits, key=lambda i: -density[i])[:MAX_AUTO])
        p["mentions"] = [i + 1 + PRINTED_OFFSET for i in hits]
        p.pop("note", None)
        p.pop("pages", None)
    for key, v in notes.items():
        if key.startswith("_"):
            continue
        name, _, parent = key.partition("@")
        match = [p for p in people if p["name"] == name
                 and (not parent or (p["parent"] is not None and by_id[p["parent"]]["name"] == parent))]
        assert len(match) == 1, f"notes.json key {key!r} matches {len(match)} people"
        match[0].update(note=v["note"], pages=v["pages"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{sum('note' in p for p in people)} notes, {sum(bool(p['mentions']) for p in people)} people with book mentions")


if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1]))
