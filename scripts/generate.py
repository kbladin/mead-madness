# Copyright (c) 2024 Kalle Bladin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import json
import collections
from collections import Counter

import pandas as pd


class IdNameMapper(collections.abc.Mapping):
    def __init__(self, id_name_map):
        self._id_name_map = id_name_map

    def __getitem__(self, key):
        return "({}) ".format(key) + self._id_name_map[key]

    def __iter__(self):
        return self._id_name_map.__iter__()

    def __len__(self):
        return self._id_name_map.__len__()


def clean_split(string):
    """Example input "hej,  Hej, haj"
    Example output: ["hej", "Hej", "haj"]
    """
    if not type(string) is str:
        return []
    return [" ".join(x.split()) for x in string.split(",")]


def collect_mead_data(df: pd.DataFrame, id: int, id_name_map: IdNameMapper) -> dict:
    """Collect all data for a single mead into a dict ready for HTML rendering."""
    this_df = df.query("Id == {}".format(id))

    rating_cols = ["Sötma", "Syrlighet", "Fyllighet", "Strävhet"]
    ratings = {
        col: [float(v) for v in this_df[col].dropna().tolist()]
        for col in rating_cols
    }

    notes = Counter(
        this_df.filter(["Smaknoter"])
        .transform({"Smaknoter": clean_split})
        .sum()
        .to_dict()["Smaknoter"]
    )
    off_flavors = Counter(
        this_df.filter(["Bismaker"])
        .transform({"Bismaker": clean_split})
        .sum()
        .to_dict()["Bismaker"]
    )
    other = (
        this_df.filter(["Övrigt"])
        .transform({"Övrigt": clean_split})
        .sum()
        .to_dict()["Övrigt"]
    )
    overall = [float(v) for v in this_df["Helhetsbetyg"].dropna().tolist()]

    return {
        "id": int(id),
        "title": id_name_map[id],
        "ratings": ratings,
        "overall": overall,
        "notes": dict(notes),
        "off_flavors": dict(off_flavors),
        "other": list(other),
    }


def collect_category_data(
    df: pd.DataFrame, category: str, id_name_map: IdNameMapper
) -> dict:
    """Collect per-mead values for a single rating category."""
    grouped = df.groupby("Id")[category].apply(list).to_dict()
    series = {
        id_name_map[k]: [float(x) for x in v] for k, v in sorted(grouped.items())
    }
    return {"category": category, "series": series}


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap');

  :root {{
    --bg:        #1a1410;
    --bg2:       #231c15;
    --bg3:       #2d2318;
    --card:      #2a1f14;
    --border:    #5c3d1e;
    --amber:     #c8892a;
    --amber-lt:  #e8b054;
    --amber-dim: #7a5018;
    --cream:     #f0e6d0;
    --muted:     #a08870;
    --red:       #c04838;
    --green:     #5a8c5a;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    height: 100%;
    background: var(--bg);
    color: var(--cream);
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 18px;
    overflow: hidden;
  }}

  /* ── SLIDE CONTAINER ── */
  .slides-viewport {{
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    position: relative;
  }}

  .slides-track {{
    display: flex;
    height: 100%;
    transition: transform 0.5s cubic-bezier(0.77,0,0.175,1);
  }}

  .slide {{
    min-width: 100vw;
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-bottom: 3.2rem;  /* keep content above the nav bar */
  }}

  /* ── TITLE SLIDE ── */
  .slide-title {{
    justify-content: center;
    align-items: center;
    background: radial-gradient(ellipse 80% 60% at 50% 40%, #3d2508 0%, transparent 70%), var(--bg);
  }}

  .title-inner {{ text-align: center; padding: 2rem; z-index: 1; }}

  .title-inner h1 {{
    font-family: 'IM Fell English', serif;
    font-size: clamp(2.5rem, 5vw, 4.5rem);
    color: var(--amber-lt);
    letter-spacing: 0.02em;
    text-shadow: 0 0 40px rgba(200,137,42,0.4);
    line-height: 1.15;
  }}

  .title-inner .subtitle {{
    font-size: 1.2rem;
    color: var(--muted);
    margin-top: 1rem;
    font-style: italic;
    letter-spacing: 0.06em;
  }}

  .divider {{
    width: 200px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--amber-dim), transparent);
    margin: 2rem auto;
  }}

  .tally {{
    display: flex;
    gap: 3rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 1rem;
  }}

  .tally-item {{ display: flex; flex-direction: column; align-items: center; }}
  .tally-item .num {{
    font-family: 'IM Fell English', serif;
    font-size: 2.8rem;
    color: var(--amber);
    line-height: 1;
  }}
  .tally-item .lbl {{
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 0.3rem;
  }}

  /* ── SLIDE HEADER ── */
  .slide-header {{
    padding: 0.9rem 2rem;
    border-bottom: 1px solid var(--border);
    background: var(--bg2);
    display: flex;
    align-items: baseline;
    gap: 1rem;
    flex-shrink: 0;
  }}

  .slide-number {{
    font-family: 'IM Fell English', serif;
    font-size: 2.8rem;
    color: var(--amber-dim);
    line-height: 1;
    opacity: 0.55;
  }}

  .slide-name {{
    font-family: 'IM Fell English', serif;
    font-size: clamp(1.4rem, 2.5vw, 2.2rem);
    color: var(--amber-lt);
    text-shadow: 0 0 20px rgba(200,137,42,0.25);
  }}

  /* ── MEAD SLIDE BODY ── */
  .mead-body {{
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 340px;
    min-height: 0;
  }}

  .chart-col {{
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }}

  .chart-wrap {{
    flex: 1;
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
  }}

  .chart-wrap canvas {{ max-height: 100%; max-width: 100%; }}

  .overall-bar {{
    padding: 0.6rem 1.5rem;
    border-top: 1px solid var(--border);
    background: var(--bg3);
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
  }}

  .overall-label {{
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    white-space: nowrap;
  }}

  .stars {{
    display: flex;
    gap: 3px;
    align-items: center;
  }}

  .star-wrap {{
    position: relative;
    width: 1.3rem;
    height: 1.3rem;
    flex-shrink: 0;
  }}

  .star-wrap svg {{
    width: 100%;
    height: 100%;
  }}

  .overall-value {{
    font-family: 'IM Fell English', serif;
    font-size: 1.4rem;
    color: var(--amber-lt);
    min-width: 2.5rem;
    text-align: right;
  }}

  /* ── SIDE PANEL ── */
  .side-panel {{
    border-left: 1px solid var(--border);
    background: var(--bg2);
    overflow-y: auto;
    padding: 1.2rem 1.4rem;
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
  }}

  .side-panel::-webkit-scrollbar {{ width: 4px; }}
  .side-panel::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

  .section-heading {{
    font-family: 'IM Fell English', serif;
    font-size: 0.95rem;
    color: var(--amber);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}

  .section-heading::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}

  .tag-list {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}

  .tag {{
    font-size: 0.82rem;
    padding: 0.18em 0.6em;
    border-radius: 3px;
    font-style: italic;
  }}

  .tag-note {{
    background: rgba(200,137,42,0.15);
    border: 1px solid var(--amber-dim);
    color: var(--amber-lt);
  }}

  .tag-off {{
    background: rgba(192,72,56,0.15);
    border: 1px solid var(--red);
    color: #e88070;
  }}

  .tag .cnt {{ font-style: normal; font-weight: 600; opacity: 0.65; font-size: 0.75em; margin-left: 0.2em; }}

  .other-list {{ list-style: none; display: flex; flex-direction: column; gap: 0.4rem; }}
  .other-list li {{
    font-size: 0.88rem;
    color: var(--muted);
    font-style: italic;
    padding-left: 1em;
    position: relative;
  }}
  .other-list li::before {{ content: '–'; position: absolute; left: 0; color: var(--border); }}

  /* ── CATEGORY SLIDE ── */
  .cat-body {{
    flex: 1;
    padding: 1.2rem 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
  }}

  .cat-body canvas {{ max-height: 100%; max-width: 100%; }}

  /* ── NAVIGATION ── */
  nav {{
    position: fixed;
    bottom: 1.1rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(15,10,5,0.92);
    border: 1px solid var(--border);
    border-radius: 50px;
    padding: 0.45rem 0.9rem;
    z-index: 200;
    backdrop-filter: blur(8px);
  }}

  nav button {{
    background: none;
    border: none;
    color: var(--amber);
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0.2rem 0.55rem;
    border-radius: 50px;
    transition: background 0.15s, color 0.15s;
    line-height: 1;
  }}

  nav button:hover {{ background: var(--amber-dim); color: var(--cream); }}
  nav button:disabled {{ opacity: 0.25; cursor: default; }}
  nav button:disabled:hover {{ background: none; color: var(--amber); }}

  .page-counter {{
    font-size: 0.8rem;
    color: var(--muted);
    letter-spacing: 0.05em;
    min-width: 70px;
    text-align: center;
    font-family: 'Crimson Pro', serif;
  }}

  .dots {{
    display: flex;
    gap: 5px;
    align-items: center;
    max-width: 240px;
    flex-wrap: wrap;
    justify-content: center;
  }}

  .dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--border);
    cursor: pointer;
    transition: background 0.2s, transform 0.2s;
    flex-shrink: 0;
  }}

  .dot.active {{ background: var(--amber); transform: scale(1.4); }}
  .dot:hover {{ background: var(--amber-lt); }}

  /* ── MOBILE RESPONSIVE ── */
  @media (max-width: 700px) {{
    html, body {{ font-size: 15px; }}

    .slide {{
      padding-bottom: 4rem;
    }}

    .slide-header {{
      padding: 0.6rem 1rem;
      gap: 0.5rem;
    }}

    .slide-number {{ font-size: 1.8rem; }}
    .slide-name   {{ font-size: 1.2rem; }}

    /* Stack mead body vertically on mobile */
    .mead-body {{
      grid-template-columns: 1fr;
      grid-template-rows: auto auto;
      overflow-y: auto;
    }}

    .chart-col {{
      grid-row: 1;
    }}

    .chart-wrap {{
      padding: 0.6rem 0.8rem;
      min-height: 200px;
    }}

    .side-panel {{
      grid-column: 1;
      grid-row: 2;
      border-left: none;
      border-top: 1px solid var(--border);
      padding: 0.8rem 1rem;
      max-height: none;
      overflow-y: visible;
    }}

    .overall-bar {{
      padding: 0.5rem 0.8rem;
      gap: 0.6rem;
    }}

    .star-wrap {{ width: 1rem; height: 1rem; }}

    /* Category slides: allow horizontal scroll for many labels */
    .cat-body {{
      padding: 0.6rem 0.5rem;
      overflow-x: auto;
    }}

    .cat-body canvas {{
      min-width: 500px;
    }}

    /* Title slide */
    .title-inner h1 {{ font-size: clamp(1.8rem, 8vw, 3rem); }}

    /* Nav */
    nav {{
      padding: 0.4rem 0.6rem;
      gap: 0.3rem;
    }}

    .dots {{ max-width: 160px; }}
    .page-counter {{ min-width: 50px; font-size: 0.75rem; }}
  }}
</style>
</head>
<body>

<div class="slides-viewport">
  <div class="slides-track" id="track">
{slides_html}
  </div>
</div>

<nav>
  <button id="btn-prev" onclick="navigate(-1)">&#8592;</button>
  <div class="dots" id="dots"></div>
  <span class="page-counter" id="counter"></span>
  <button id="btn-next" onclick="navigate(1)">&#8594;</button>
</nav>

<script>
const CHARTS_DATA = {charts_data_json};

let current = 0;
const total = document.querySelectorAll('.slide').length;
const track = document.getElementById('track');
const dotsEl = document.getElementById('dots');
const counter = document.getElementById('counter');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');

// Build dots
for (let i = 0; i < total; i++) {{
  const d = document.createElement('div');
  d.className = 'dot' + (i === 0 ? ' active' : '');
  d.onclick = () => goTo(i);
  dotsEl.appendChild(d);
}}

function updateNav() {{
  track.style.transform = `translateX(-${{current * 100}}vw)`;
  counter.textContent = (current + 1) + ' / ' + total;
  btnPrev.disabled = current === 0;
  btnNext.disabled = current === total - 1;
  document.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === current));
}}

function goTo(n) {{
  current = Math.max(0, Math.min(total - 1, n));
  updateNav();
  initChart(current);
}}

function navigate(dir) {{ goTo(current + dir); }}

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   navigate(-1);
}});

// Touch / swipe
let touchX = null;
document.addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }});
document.addEventListener('touchend',   e => {{
  if (touchX === null) return;
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 40) navigate(dx < 0 ? 1 : -1);
  touchX = null;
}});

// Chart.js initialisation (lazy – only render when slide is first visited)
const rendered = new Set();

const CHART_DEFAULTS = {{
  color: '#f0e6d0',
  plugins: {{ legend: {{ labels: {{ color: '#a08870', font: {{ family: 'Crimson Pro, Georgia, serif', size: 13 }} }} }} }},
  scales: {{
    x: {{ ticks: {{ color: '#a08870', font: {{ family: 'Crimson Pro, Georgia, serif', size: 12 }} }}, grid: {{ color: 'rgba(92,61,30,0.4)' }}, border: {{ color: '#5c3d1e' }} }},
    y: {{ ticks: {{ color: '#a08870', font: {{ family: 'Crimson Pro, Georgia, serif', size: 12 }} }}, grid: {{ color: 'rgba(92,61,30,0.4)' }}, border: {{ color: '#5c3d1e' }}, min: 1, max: 9 }}
  }}
}};

function deepMerge(target, source) {{
  for (const k of Object.keys(source)) {{
    if (source[k] && typeof source[k] === 'object' && !Array.isArray(source[k])) {{
      target[k] = target[k] || {{}};
      deepMerge(target[k], source[k]);
    }} else {{
      target[k] = source[k];
    }}
  }}
  return target;
}}

function initChart(idx) {{
  if (rendered.has(idx)) return;
  const data = CHARTS_DATA[idx];
  if (!data) return;
  rendered.add(idx);

  const canvas = document.querySelector(`.slide:nth-child(${{idx + 1}}) canvas`);
  if (!canvas) return;

  const opts = deepMerge(JSON.parse(JSON.stringify(CHART_DEFAULTS)), data.options || {{}});
  new Chart(canvas, {{ type: data.type, data: data.data, options: opts }});
}}

// Init first slide
updateNav();
initChart(0);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Slide builders – return (html_snippet, chart_data_dict_or_None)
# ---------------------------------------------------------------------------

def _mean(values):
    return round(sum(values) / len(values), 2) if values else 0.0


def _sd(values):
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return round(variance ** 0.5, 2)


def build_title_slide(title: str, n_meads: int, n_responses: int) -> tuple:
    html = f"""\
    <div class="slide slide-title">
      <div class="title-inner">
        <h1>{title}</h1>
        <div class="divider"></div>
        <div class="tally">
          <div class="tally-item"><span class="num">{n_meads}</span><span class="lbl">Mjöder</span></div>
          <div class="tally-item"><span class="num">{n_responses}</span><span class="lbl">Svar</span></div>
        </div>
      </div>
    </div>"""
    return html, None


def build_mead_slide(slide_index: int, mead: dict) -> tuple:
    """Build one per-mead slide.  Returns (html, chart_data)."""
    rating_cols = ["Sötma", "Syrlighet", "Fyllighet", "Strävhet"]
    labels = [
        "Sötma (Sweetness)",
        "Syrlighet (Acidity)",
        "Fyllighet (Mouthfeel)",
        "Strävhet (Astringency)",
    ]
    colors = ["#d4607a", "#a8c832", "#7b52a8", "#8b5e3c"]  # rose, citrus, purple, tannin

    means = []
    sds   = []
    for col in rating_cols:
        vals = mead["ratings"].get(col, [])
        means.append(_mean(vals))
        sds.append(_sd(vals))

    chart_data = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Värde",
                "data": means,
                "backgroundColor": [c + "cc" for c in colors],
                "borderColor": colors,
                "borderWidth": 2,
                "errorBars": {str(i): {"plus": sds[i], "minus": sds[i]} for i in range(len(rating_cols))},
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": True,
            "plugins": {
                "legend": {"display": False},
            },
            "scales": {
                "y": {"min": 1, "max": 9, "title": {"display": True, "text": "Värde (1–9)", "color": "#a08870"}},
                "x": {"ticks": {"color": "#a08870"}},
            },
            "animation": {"duration": 600},
        },
    }

    # Side panel HTML
    notes_html = ""
    if mead["notes"]:
        tags = "".join(
            f'<span class="tag tag-note">{k}<span class="cnt">×{v}</span></span>'
            for k, v in sorted(mead["notes"].items(), key=lambda x: -x[1])
        )
        notes_html = f'<div><div class="section-heading">Smaknoter</div><div class="tag-list">{tags}</div></div>'

    off_html = ""
    if mead["off_flavors"]:
        tags = "".join(
            f'<span class="tag tag-off">{k}<span class="cnt">×{v}</span></span>'
            for k, v in sorted(mead["off_flavors"].items(), key=lambda x: -x[1])
        )
        off_html = f'<div><div class="section-heading">Bismaker</div><div class="tag-list">{tags}</div></div>'

    other_html = ""
    if mead["other"]:
        items = "".join(f"<li>{t}</li>" for t in mead["other"])
        other_html = f'<div><div class="section-heading">Övrigt</div><ul class="other-list">{items}</ul></div>'

    # Overall rating – stars (scale 1-9 mapped to 0-10)
    overall_vals = mead["overall"]
    overall_mean = _mean(overall_vals)
    # Map 1–9 onto 0–10 stars linearly
    stars_fill = (overall_mean - 1) / 8 * 10  # float 0..10

    star_svgs = []
    for i in range(10):
        filled = max(0.0, min(1.0, stars_fill - i))  # fraction 0..1 for this star
        clip_id = f"sc-{slide_index}-{i}"
        # Full star path (standard 5-point, 20x20 viewBox)
        star_path = "M10 2 L12.35 7.6 H18.5 L13.7 11.3 L15.55 17 L10 13.4 L4.45 17 L6.3 11.3 L1.5 7.6 H7.65 Z"
        star_svgs.append(
            f'<div class="star-wrap">'
            f'<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">'
            f'<defs><clipPath id="{clip_id}"><rect x="0" y="0" width="{filled*20:.2f}" height="20"/></clipPath></defs>'
            f'<path d="{star_path}" fill="#3a2e1e"/>'
            f'<path d="{star_path}" fill="#e8b054" clip-path="url(#{clip_id})"/>'
            f'</svg>'
            f'</div>'
        )

    overall_html = f"""\
        <div class="overall-bar">
          <span class="overall-label">Helhetsbetyg</span>
          <div class="stars">{"".join(star_svgs)}</div>
          <span class="overall-value">{overall_mean:.1f}</span>
        </div>"""

    html = f"""\
    <div class="slide">
      <div class="slide-header">
        <span class="slide-number">{mead['id']}</span>
        <span class="slide-name">{mead['title']}</span>
      </div>
      <div class="mead-body">
        <div class="chart-col">
          <div class="chart-wrap"><canvas id="chart-{slide_index}"></canvas></div>
          {overall_html}
        </div>
        <div class="side-panel">
          {notes_html}
          {off_html}
          {other_html}
        </div>
      </div>
    </div>"""

    return html, chart_data


def _interpolate_color(t: float, low: tuple, high: tuple) -> str:
    """Interpolate between two RGB tuples at position t in [0,1], return hex."""
    r = int(low[0] + (high[0] - low[0]) * t)
    g = int(low[1] + (high[1] - low[1]) * t)
    b = int(low[2] + (high[2] - low[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# Swedish → "Swedish (English)" display labels for axes
_CATEGORY_LABELS = {
    "Sötma":      "Sötma (Sweetness)",
    "Syrlighet":  "Syrlighet (Acidity)",
    "Fyllighet":  "Fyllighet (Mouthfeel)",
    "Strävhet":   "Strävhet (Astringency)",
    "Helhetsbetyg": "Helhetsbetyg",
}


def build_category_slide(slide_index: int, cat_data: dict) -> tuple:
    """Build one per-category comparison slide."""
    category = cat_data["category"]
    series = cat_data["series"]

    # Interpolate bar colors from muted amber (low) to bright gold (high)
    COLOR_LOW  = (0x2a, 0x18, 0x05)  # very dark, almost black-brown
    COLOR_HIGH = (0xff, 0xd7, 0x00)  # pure gold

    labels = list(series.keys())
    means = [_mean(v) for v in series.values()]
    sds   = [_sd(v)   for v in series.values()]

    # Normalise each mean to [0,1] over the scale 1–9
    def bar_color(mean, alpha="bb"):
        t = (mean - 1) / 8
        return _interpolate_color(t, COLOR_LOW, COLOR_HIGH) + alpha

    datasets = [{
        "label": category,
        "data": means,
        "backgroundColor": [bar_color(m) for m in means],
        "borderColor":     [bar_color(m, "") for m in means],
        "borderWidth": 2,
        "errorBars": {str(i): {"plus": sds[i], "minus": sds[i]} for i in range(len(labels))},
    }]

    display_label = _CATEGORY_LABELS.get(category, category)
    y_title = f"{display_label} (1–9)"

    chart_data = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": datasets,
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "y": {"min": 1, "max": 9, "title": {"display": True, "text": y_title, "color": "#a08870"}},
                "x": {"ticks": {"maxRotation": 20, "autoSkip": False}},
            },
            "animation": {"duration": 600},
        },
    }

    html = f"""\
    <div class="slide">
      <div class="slide-header">
        <span class="slide-name">{display_label}</span>
      </div>
      <div class="cat-body"><canvas id="chart-{slide_index}"></canvas></div>
    </div>"""

    return html, chart_data


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{session_title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap');

  :root {{
    --bg:        #1a1410;
    --bg2:       #231c15;
    --border:    #5c3d1e;
    --amber:     #c8892a;
    --amber-lt:  #e8b054;
    --amber-dim: #7a5018;
    --cream:     #f0e6d0;
    --muted:     #a08870;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    min-height: 100vh;
    background: radial-gradient(ellipse 80% 50% at 50% 0%, #3d2508 0%, transparent 55%), var(--bg);
    color: var(--cream);
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: clamp(16px, 2vw, 22px);
  }}

  body {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 1fr auto;
    min-height: 100vh;
    padding: clamp(2rem, 5vw, 5rem) clamp(2rem, 6vw, 8rem);
    gap: clamp(1.5rem, 3vw, 3rem) clamp(3rem, 6vw, 8rem);
  }}

  /* ── TITLE (spans full width) ── */
  header {{
    grid-column: 1 / -1;
    border-bottom: 1px solid var(--border);
    padding-bottom: clamp(1rem, 2vw, 2rem);
  }}

  header h1 {{
    font-family: 'IM Fell English', serif;
    font-size: clamp(2rem, 5vw, 5rem);
    color: var(--amber-lt);
    text-shadow: 0 0 60px rgba(200,137,42,0.4);
    line-height: 1.1;
  }}

  /* ── LEFT COLUMN ── */
  .col-left {{
    display: flex;
    flex-direction: column;
    gap: clamp(1.2rem, 2.5vw, 2.5rem);
  }}

  .section-label {{
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--amber-dim);
    margin-bottom: 0.4em;
  }}

  /* Results button */
  .btn-results {{
    display: inline-block;
    font-family: 'IM Fell English', serif;
    font-size: clamp(1.1rem, 2.5vw, 2rem);
    color: var(--amber-lt);
    text-decoration: none;
    border-bottom: 1px solid var(--amber-dim);
    padding-bottom: 0.1em;
    transition: color 0.15s, border-color 0.15s;
  }}
  .btn-results:hover {{ color: #fff; border-color: var(--amber-lt); }}

  .not-ready {{
    font-size: clamp(0.9rem, 1.5vw, 1.1rem);
    color: var(--muted);
    font-style: italic;
  }}

  /* Form button – hidden on wide screens (TV), shown on narrow (mobile) */
  .btn-form {{
    display: inline-block;
    font-family: 'Crimson Pro', serif;
    font-size: clamp(1rem, 1.8vw, 1.3rem);
    font-weight: 600;
    color: #1a0e05;
    background: var(--amber);
    text-decoration: none;
    padding: 0.45em 1.1em;
    border-radius: 4px;
    transition: filter 0.15s;
  }}
  .btn-form:hover {{ filter: brightness(1.15); }}

  @media (min-width: 900px) {{
    .btn-form {{ display: none; }}
  }}

  /* Previous sessions */
  .prev-list {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.4em;
  }}

  .prev-list a {{
    color: var(--muted);
    text-decoration: none;
    font-size: clamp(0.85rem, 1.5vw, 1.1rem);
    transition: color 0.15s;
    display: flex;
    align-items: center;
    gap: 0.5em;
  }}
  .prev-list a::before {{ content: '→'; color: var(--border); font-size: 0.85em; }}
  .prev-list a:hover {{ color: var(--cream); }}

  .no-prev {{ color: var(--border); font-style: italic; font-size: 0.9em; }}

  /* ── RIGHT COLUMN ── */
  .col-right {{
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: clamp(0.8rem, 1.5vw, 1.5rem);
  }}

  #qr-code {{
    background: var(--cream);
    padding: 8px;
    border-radius: 4px;
    line-height: 0;
  }}

  #qr-code canvas, #qr-code img {{
    display: block;
    width: clamp(120px, 15vw, 200px) !important;
    height: clamp(120px, 15vw, 200px) !important;
  }}

  .qr-url {{
    font-size: clamp(0.75rem, 1.2vw, 0.95rem);
    color: var(--amber-dim);
    font-family: monospace;
    word-break: break-all;
  }}

  /* ── MOBILE: stack to single column ── */
  @media (max-width: 700px) {{
    body {{
      grid-template-columns: 1fr;
      padding: 1.5rem;
      gap: 1.5rem;
    }}
    header {{ grid-column: 1; }}
    .col-right {{ flex-direction: row; align-items: center; gap: 1rem; flex-wrap: wrap; }}
  }}
</style>
</head>
<body>

<header>
  <div class="section-label">Mjödprovning</div>
  <h1>{session_title}</h1>
</header>

<div class="col-left">
  <div>
    <div class="section-label">Resultat</div>
    {results_html}
  </div>

  {prev_html}

  <div class="btn-form-wrap">
    <a class="btn-form"
       href="{form_url}"
       target="_blank">✏️ Fyll i formuläret</a>
  </div>
</div>

<div class="col-right">
  <div class="section-label">Den här sidan</div>
  <div id="qr-code"></div>
  <span class="qr-url">{site_url}</span>
</div>

<script>
new QRCode(document.getElementById("qr-code"), {{
  text:         "{site_url}",
  width:        200,
  height:       200,
  colorDark:    "#1a1410",
  colorLight:   "#f0e6d0",
  correctLevel: QRCode.CorrectLevel.M,
}});
</script>
</body>
</html>
"""


def build_index(
    current_session: str,
    results_dir: str,
    site_dir: str,
    form_url: str,
    site_url: str,
):
    """Generate index.html, baking in all known sessions."""
    current_session = current_session.rstrip("/")
    current_html_name = current_session + ".html"
    current_html_path = os.path.join(results_dir, current_html_name)
    current_result_rel = "results/" + current_html_name

    # Results section
    if os.path.exists(current_html_path):
        results_html = f'''<a class="btn-results" href="{current_result_rel}">Visa resultat →</a>'''
    else:
        results_html = '''<p class="not-ready">Väntar på Resultat</p>'''

    # Previous sessions: all .html files in results/ except the current one
    prev_entries = sorted(
        f for f in os.listdir(results_dir)
        if f.endswith(".html") and f != current_html_name
    )
    if prev_entries:
        links = "\n".join(
            f'''    <li><a href="results/{f}">{f.replace(".html", "").replace("_", " ")}</a></li>'''
            for f in prev_entries
        )
        prev_html = f'''<div>
    <div class="section-label">Tidigare sessioner</div>
    <ul class="prev-list">
{links}
    </ul>
  </div>'''
    else:
        prev_html = ""

    output = _INDEX_TEMPLATE.format(
        session_title=current_session.replace("_", " "),
        results_html=results_html,
        prev_html=prev_html,
        form_url=form_url,
        site_url=site_url,
    )

    out_path = os.path.join(site_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ── CONFIG ──────────────────────────────────────────────────────────────────
FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdK0-LeTizBbqZXgOGMo20fqFEwdr3SQeIqy8Yjp190lpuClw/"
    "viewform?usp=sharing&ouid=117011815079806822734"
)
SITE_URL = "https://kbladin.github.io/mead-madness/"
# ── END CONFIG ──────────────────────────────────────────────────────────────


def generate_results(instance_folder: str, instances_dir: str, results_dir: str):
    """Generate the results HTML for one session. Returns True if written, False if skipped."""
    instance_dir = os.path.join(instances_dir, instance_folder)
    id_name_map_filepath = os.path.join(instance_dir, "id_name_map.csv")
    mead_data_filepath = os.path.join(instance_dir, instance_folder + ".csv")

    # Skip if the responses CSV doesn't exist yet
    if not os.path.exists(mead_data_filepath):
        print(f"Skipped (no CSV): {instance_folder}")
        return False

    df_id_name_map = pd.read_csv(
        id_name_map_filepath, sep=r"\s*,\s*", engine="python"
    )
    id_name_map = IdNameMapper(df_id_name_map.set_index("Id").to_dict()["Namn"])
    df = pd.read_csv(mead_data_filepath, skipinitialspace=True)

    # Skip if there are no actual responses (only the facit row or empty)
    n_responses = len(df[df["Id"] != 0])
    if n_responses == 0:
        print(f"Skipped (no responses yet): {instance_folder}")
        return False

    mead_ids = sorted(set(df["Id"]))
    slides_html_parts = []
    charts_data = {}
    slide_index = 0

    html, chart = build_title_slide(instance_folder, len(mead_ids), n_responses)
    slides_html_parts.append(html)
    charts_data[slide_index] = chart
    slide_index += 1

    for mead_id in mead_ids:
        mead = collect_mead_data(df, mead_id, id_name_map)
        html, chart = build_mead_slide(slide_index, mead)
        slides_html_parts.append(html)
        charts_data[slide_index] = chart
        slide_index += 1

    for category in ["Sötma", "Syrlighet", "Fyllighet", "Strävhet", "Helhetsbetyg"]:
        cat_data = collect_category_data(df, category, id_name_map)
        html, chart = build_category_slide(slide_index, cat_data)
        slides_html_parts.append(html)
        charts_data[slide_index] = chart
        slide_index += 1

    results_output = _HTML_TEMPLATE.format(
        title=instance_folder,
        slides_html="\n".join(slides_html_parts),
        charts_data_json=json.dumps(charts_data, ensure_ascii=False),
    )

    results_path = os.path.join(results_dir, instance_folder + ".html")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(results_output)
    print(f"Written: {results_path}")
    return True


def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generate.py <instance_folder>")
        print("Example: python generate.py Na_ra_Mjo_den-Upplevelse_2024")
        sys.exit(1)

    current_session = sys.argv[1].rstrip("/")
    # Normalise: if the user passed a path, take just the final component
    current_session = os.path.basename(current_session)
    instances_dir = "data/instances"
    site_dir = "kbladin.github.io/mead-madness"
    results_dir = os.path.join(site_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # Generate results for all sessions that have responses
    all_folders = sorted(
        x for x in os.listdir(instances_dir)
        if os.path.isdir(os.path.join(instances_dir, x))
    )
    for instance_folder in all_folders:
        generate_results(instance_folder, instances_dir, results_dir)

    # Resolve current_session against actual folder names on disk,
    # so the comparison in build_index matches what generate_results wrote.
    matched = [x for x in all_folders if x == current_session or os.path.basename(x) == current_session]
    if not matched:
        print(f"Error: '{current_session}' not found in {instances_dir}. Available: {all_folders}")
        sys.exit(1)
    current_session = matched[0]

    build_index(current_session, results_dir, site_dir, FORM_URL, SITE_URL)


if __name__ == "__main__":
    main()