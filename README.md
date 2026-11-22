# Vibe Atlas

A reference gallery and poster studio for collecting visual styles and mixing them into posters and design systems.

**Open it online:** https://coastal-andy.github.io/vibe-atlas/

## What's inside

| View | What it does |
|---|---|
| **Gallery** | ~7,300 reference images in a masonry grid. Filter by source, style family, style, Gurafiku tag or archive group. Click for a large viewer (← → to browse). Select images and download them, or send them to the Studio tray. |
| **Styles** | 174 niche visual styles with color palettes, a type / texture / layout recipe, matching archive finds and search links to other libraries. |
| **Studio** | Mix images from your tray into a poster: drag, resize, rotate, blend modes, image treatments, text layers, textures. **Mix it** auto-composes a layout. Export a 2400px PNG and copy the design tokens. |
| **Archive** | Internet Archive scans (zines, rave flyers, Soviet books, Bryce/KPT manuals, Emigre, pulp, Haeckel…). |
| **Libraries** | All sources with usage notes, plus the Instagram reels that started it. |

## Sources

- **EF // visual cores** (Pinterest board by Electroforma): 4,197 pins across 174 styles
- **Gurafiku**: 2,587 images of Japanese graphic design (via Tumblr's public API)
- **Internet Archive**: 510 hand-picked items
- **CARI** (Consumer Aesthetics Research Institute): 89 aesthetics, **local version only**. CARI asks that its images be used for inspiration and analysis with credit, not as free assets, so its data isn't published here.
- **Link only:** Design Reviewed, Artvee, eMuseum Zürich

Images are shown from their original hosts and belong to their creators. Use them as study material and credit designers when you publish.

## Two ways to run it

### On the web (GitHub Pages)
Open the link above. Downloads go to your Downloads folder (several images come as one zip), and poster PNGs download directly. Pinterest and archive.org images are fetched through the free [wsrv.nl](https://wsrv.nl) image proxy so the browser is allowed to download and export them.

### Locally (Mac): saves to disk, works offline, includes CARI
Double-click **`Vibe Atlas.command`**. The first time, macOS may ask you to confirm: right-click it, choose **Open**, then **Open** again.
It starts a small Python server (`explorer/server.py`, Python 3 built in on macOS) and opens `http://127.0.0.1:8765/explorer/`.

- Saved originals go to `refs/images/<style>/` and are shown from disk afterwards, so they work offline.
- Exported posters go to `posters/`.
- Downloads are queued in small batches, retry on bad connections, and resume after a reload.

Or from a terminal:
```bash
python3 explorer/server.py
```

## Files

```
explorer/index.html      the whole app (one file)
explorer/server.py       local server: static files + saving images + poster export
explorer/receive.html    helper used when importing data from a source site
refs/                    data: Pinterest pins, Gurafiku, Internet Archive finds, reels
Vibe Atlas.command       double-click launcher for the local version
```
