# Royal tree — sources, method, open items

Live site: https://kamji-mfon.github.io/afrikan-royal-tree/ (public repo `kamji-mfon/afrikan-royal-tree`,
a manual copy of this folder — re-copy `index.html tree.json notes.json cite.py extract.py` after edits).
Preview locally: `.claude/launch.json` → `royal-tree` (python http.server on 8781).

## Inputs (not in git)
- Chart: `Royal_Family_Tree_flat.pdf` — Google Drive id `1vWFoF87au8vtddwawEOmJJUuOxb35ZG_`, local copy
  `~/Downloads/`. One 5760×6480 pt CAD export ("RoofDwg Model"), text layer + vector strokes over a photo.
- Book: Prince Dika Akwa nya Bonambela, *Les descendants des pharaons à travers l'Afrique*
  (Éditions Osiris-Africa), `~/Downloads/LES DESCENDANTS i des PHARAONS a travers L’AFRIQUE.pdf`, 438 pp,
  text layer (OCR, accents often dropped). **Printed page = PDF page + 3.** The chart transcribes the book's
  "Généalogie de la nationalité Sinegala en Afrique centrale" (PDF p. 430).

## Pipeline
1. `python3 royal_tree/extract.py <chart.pdf>` → `tree.json` (names + parent links by geometry: arrowhead tip
   = child; bare bus bars → name clearly above is parent). `EXTRA_EDGES`/`SPOUSES` hold hand fixes checked
   against the PDF; `BRANCHES` are added polity labels (not in the chart).
2. `python3 royal_tree/cite.py <book.pdf>` → adds `note`/`pages` from `notes.json` and `mentions`
   (printed pages where the name matches by spelling, ≤6, genealogy-dense pages first). Run after step 1.

## Book coverage (done 2026-09-25)
- Prose genealogy: printed pp. 313–337 (Ngala-Dwala ancestors ↔ pharaoh table; Ikale ≈ end of 17th dynasty,
  p. 320) and pp. 428–434 (Wandala/Mandara, Bamum, Mboum). 63 notes from these.
- Chart pages, all ~56 layout-detected pages vision-read. Real genealogies: Fig. 1 p. 14 (Duala houses,
  Bonadika → Bétotè Akwa → the author), Fig. 4 p. 173 (Lozi — unrelated dynasty), PDF p. 430 (the source
  chart). p. 417 prose: Kota and Ngala II sons of Mbu. Everything else = lexical/mythology tables
  (Tableaux II–XXX, dictionary pp. 337–366). 5 notes from these. Total 68/312.
- ~100 names never occur in the book text (mostly recent Bamum, Duala, Njike/Pokam generations): need
  other sources (Bamum palace histories, Duala genealogies).

## Corrections and contradictions
- Applied: Yen is Nyimbu's **daughter**; her children (Ndjiason, Nditam, Sow, Ncharé, Mbam) hang under
  Mforifum with Yen as co-parent (p. 434).
- Flagged, tree unchanged: Adjara is son of Dawa (p. 428) vs son of Adjia Makia (p. 430) — book is
  inconsistent. "Soka Wandala" reads as one person (p. 428); the chart splits Soka → Wandala.
- "Apfalaska" on the chart is a title (prince) of Djilé II, not a separate person.
- Unverified: order of the boustrophedon top lineage Ikale → … → Mandenge was read from arrow directions
  only; check against the Ngala-Dwala table (PDF p. 317).

## Open items
- Hi-res re-read of the Mali/Songhay dynasty charts, PDF pp. 180–181 (names too small at first pass) for
  the Mali branch (Mangala, Balali Bunama, Lawalo, Kulibali).
- Matchi, Aldawa Bara, Amiri Biri: placement off Djilé III is garbled in the p. 433 chart OCR.
- Confirm or correct the six `BRANCHES` labels.
