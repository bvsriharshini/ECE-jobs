import urllib.request
import re
from datetime import datetime, timezone

SOURCE_URL = "https://raw.githubusercontent.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026/main/README.md"

INCLUDE_KEYWORDS = [
    "verification", "design verification", "asic verification", "soc verification",
    "asic design", "fpga", "asic", "soc", "gpu",
    "analog", "mixed.signal", "memory design", "memory controller",
    "physical design", "layout engineer",
    "bring.up", "bringup",
    "board", "hardware engineer", "hardware design",
    "application engineer", "field application",
    "product engineer",
    "rtl", "timing engineer",
    "new college grad", "new grad", "entry level", "associate.*engineer",
]

EXCLUDE_KEYWORDS = [
    "plasma center", "nurse", "hvac", "mechanical engineer",
    "procurement", "graphic designer",
    "site reliability", "software.*reliability", "data platform",
    "brand", "ui/ux", "front.end design", "web design",
    "logistics", "supply chain", "legal", "marketing",
    "propulsion", "aero", "turbomachinery", "thermal engineer",
    "gmp", "clinical", "pharma", "medical",
    "compressor", "facilities.*mechanical",
    "cnc", "tooling",
]

TARGET_SECTIONS = ["Hardware Engineer", "FPGA/ASIC", "Embedded Systems"]

CATEGORIES = [
    {
        "key": "dv",
        "title": "Design Verification / SOC / GPU DV",
        "color": "#378ADD",
        "btn_bg": "#E6F1FB", "btn_color": "#0C447C", "btn_border": "#85B7EB",
        "keywords": ["verification", "asic verif", "soc verif"],
    },
    {
        "key": "asic_fpga",
        "title": "ASIC / FPGA / Physical Design / RTL",
        "color": "#1D9E75",
        "btn_bg": "#E1F5EE", "btn_color": "#085041", "btn_border": "#5DCAA5",
        "keywords": ["fpga", "rtl", "asic design", "timing", "physical design", "layout"],
    },
    {
        "key": "analog",
        "title": "Analog & Mixed-Signal / Memory",
        "color": "#BA7517",
        "btn_bg": "#FAEEDA", "btn_color": "#633806", "btn_border": "#EF9F27",
        "keywords": ["analog", "mixed", "memory design", "memory controller"],
    },
    {
        "key": "board",
        "title": "Board Bring-up / Hardware Engineer",
        "color": "#D4537E",
        "btn_bg": "#FBEAF0", "btn_color": "#4B1528", "btn_border": "#ED93B1",
        "keywords": ["board", "bring", "hardware design", "hardware engineer", "avionics hardware"],
    },
    {
        "key": "app",
        "title": "Application / Field / Product Engineer",
        "color": "#7F77DD",
        "btn_bg": "#EEEDFE", "btn_color": "#26215C", "btn_border": "#AFA9EC",
        "keywords": ["application engineer", "field application", "product engineer"],
    },
    {
        "key": "other",
        "title": "Other Relevant Roles",
        "color": "#888780",
        "btn_bg": "#F1EFE8", "btn_color": "#2C2C2A", "btn_border": "#B4B2A9",
        "keywords": [],
    },
]

def fetch_source():
    with urllib.request.urlopen(SOURCE_URL) as r:
        return r.read().decode("utf-8")

def matches(role_text, keywords):
    t = role_text.lower()
    return any(re.search(kw, t) for kw in keywords)

def extract_table_rows(md, section_name):
    pattern = rf"<summary>.*?{re.escape(section_name)}.*?</summary>(.*?)</details>"
    m = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
    if not m:
        print(f"  WARNING: section '{section_name}' not found!")
        return []
    block = m.group(1)
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("|") and "---" not in line and "Company" not in line and len(line) > 10:
            rows.append(line)
    return rows

def parse_row(row):
    cols = [c.strip() for c in row.strip("|").split("|")]
    if len(cols) < 5:
        return None
    company = re.sub(r"[🏢*]", "", cols[0]).strip()
    role = cols[1]
    location = cols[2]
    posted = cols[3]
    apply_col = cols[4]
    url_match = re.search(r'\(https?://[^\)]+\)', apply_col)
    apply_url = url_match.group(0)[1:-1] if url_match else "#"
    return company, role, location, posted, apply_url

def filter_rows(rows):
    kept = []
    for row in rows:
        parsed = parse_row(row)
        if not parsed:
            continue
        _, role, _, _, _ = parsed
        if matches(role, EXCLUDE_KEYWORDS):
            continue
        if matches(role, INCLUDE_KEYWORDS):
            kept.append(parsed)
    return kept

def categorize(jobs):
    result = {cat["key"]: [] for cat in CATEGORIES}
    for job in jobs:
        _, role, _, _, _ = job
        r = role.lower()
        placed = False
        for cat in CATEGORIES[:-1]:
            if any(k in r for k in cat["keywords"]):
                result[cat["key"]].append(job)
                placed = True
                break
        if not placed:
            result["other"].append(job)
    return result

def card_html(job, cat):
    company, role, location, posted, url = job
    return f"""
        <div class="card">
          <div class="card-top">
            <span class="card-company">{company}</span>
            <span class="card-posted">{posted}</span>
          </div>
          <div class="card-role">{role}</div>
          <div class="card-footer">
            <span class="card-location">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
              {location}
            </span>
            <a class="apply-btn" href="{url}" target="_blank" style="background:{cat['btn_bg']};color:{cat['btn_color']};border-color:{cat['btn_border']};">Apply →</a>
          </div>
        </div>"""

def section_html(cat, jobs):
    if not jobs:
        return ""
    cards = "".join(card_html(j, cat) for j in jobs)
    return f"""
    <div class="section">
      <div class="section-header">
        <div class="section-dot" style="background:{cat['color']}"></div>
        <span class="section-title">{cat['title']}</span>
        <span class="section-count">{len(jobs)} roles</span>
      </div>
      <div class="cards">{cards}</div>
    </div>"""

def build_html(categorized, total, companies, now):
    sections = "".join(
        section_html(cat, categorized[cat["key"]])
        for cat in CATEGORIES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Harshini's ECE Job Tracker – 2026</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:#f4f6f9;color:#1a1a1a;min-height:100vh}}
.hero{{background:#fff;border-bottom:1px solid #e5e7eb;padding:2rem 2rem 0;position:relative;overflow:hidden}}
.hero-grid{{position:absolute;inset:0;background-image:linear-gradient(#e5e7eb 1px,transparent 1px),linear-gradient(90deg,#e5e7eb 1px,transparent 1px);background-size:32px 32px;opacity:0.5}}
.hero-content{{position:relative;z-index:1}}
.badge-row{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1rem}}
.badge{{font-family:'Space Mono',monospace;font-size:10px;padding:3px 10px;border-radius:100px;letter-spacing:0.05em;border:1px solid}}
.badge-blue{{background:#E6F1FB;color:#0C447C;border-color:#85B7EB}}
.badge-green{{background:#E1F5EE;color:#085041;border-color:#5DCAA5}}
.badge-amber{{background:#FAEEDA;color:#633806;border-color:#EF9F27}}
h1{{font-family:'Space Mono',monospace;font-size:clamp(1.1rem,3vw,1.6rem);font-weight:700;color:#111;line-height:1.3;margin-bottom:0.5rem}}
h1 span{{color:#378ADD}}
.hero-sub{{font-size:13px;color:#555;line-height:1.6;max-width:700px;margin-bottom:1.5rem}}
.stats-bar{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e5e7eb;margin-top:0}}
.stat{{background:#fff;padding:1rem 1.25rem;text-align:center;border-right:1px solid #e5e7eb}}
.stat:last-child{{border-right:none}}
.stat-num{{font-family:'Space Mono',monospace;font-size:1.4rem;font-weight:700;color:#378ADD;display:block}}
.stat-label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-top:2px}}
.tips-bar{{background:#fff;border-bottom:1px solid #e5e7eb;padding:0.75rem 2rem;display:flex;align-items:center;gap:1rem;overflow-x:auto;flex-wrap:wrap}}
.tips-label{{font-family:'Space Mono',monospace;font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap}}
.tip-chip{{font-size:12px;color:#555;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:3px 10px;white-space:nowrap}}
.tip-chip strong{{color:#111;font-weight:500}}
.main{{padding:1.5rem 2rem;max-width:1300px;margin:0 auto}}
.section{{margin-bottom:2rem;animation:fadeUp 0.4s ease both}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.section:nth-child(1){{animation-delay:0.05s}}
.section:nth-child(2){{animation-delay:0.1s}}
.section:nth-child(3){{animation-delay:0.15s}}
.section:nth-child(4){{animation-delay:0.2s}}
.section:nth-child(5){{animation-delay:0.25s}}
.section:nth-child(6){{animation-delay:0.3s}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:0.75rem}}
.section-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.section-title{{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#555}}
.section-count{{font-family:'Space Mono',monospace;font-size:10px;color:#aaa;margin-left:auto}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:1rem 1.1rem;transition:border-color 0.15s,transform 0.15s,box-shadow 0.15s}}
.card:hover{{border-color:#c0c7d0;transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,0.07)}}
.card-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px}}
.card-company{{font-weight:600;font-size:13px;color:#111}}
.card-posted{{font-family:'Space Mono',monospace;font-size:10px;color:#aaa;white-space:nowrap;margin-left:8px}}
.card-role{{font-size:13px;color:#555;line-height:1.4;margin-bottom:10px}}
.card-footer{{display:flex;align-items:center;justify-content:space-between;gap:8px}}
.card-location{{font-size:11px;color:#aaa;display:flex;align-items:center;gap:4px}}
.apply-btn{{font-family:'Space Mono',monospace;font-size:10px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;padding:5px 12px;border-radius:8px;text-decoration:none;border:1px solid;transition:all 0.15s;white-space:nowrap}}
.apply-btn:hover{{opacity:0.85;transform:scale(1.03)}}
.footer{{text-align:center;padding:1.5rem;font-family:'Space Mono',monospace;font-size:10px;color:#aaa;letter-spacing:0.05em;border-top:1px solid #e5e7eb;margin-top:1rem}}
.footer a{{color:#378ADD;text-decoration:none}}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-grid"></div>
  <div class="hero-content">
    <div class="badge-row">
      <span class="badge badge-green">OPT / F1 Friendly</span>
      <span class="badge badge-blue">No Clearance Required</span>
      <span class="badge badge-amber">Auto-updates every 6h</span>
    </div>
    <h1>Harshini's ECE Job Tracker<br><span>2026 Entry-Level / New Grad</span></h1>
    <p class="hero-sub">Design Verification · SOC · GPU DV · Analog/Mixed-Signal · Board Bring-up · ASIC · Physical Design · Layout · Memory Controller · Hardware &amp; Applications Engineer</p>
  </div>
  <div class="stats-bar">
    <div class="stat"><span class="stat-num">{total}</span><span class="stat-label">Jobs</span></div>
    <div class="stat"><span class="stat-num">{companies}</span><span class="stat-label">Companies</span></div>
    <div class="stat"><span class="stat-num">{len([c for c in CATEGORIES if categorized[c['key']]])}</span><span class="stat-label">Categories</span></div>
    <div class="stat"><span class="stat-num" style="font-size:1rem;">6h</span><span class="stat-label">Refresh rate</span></div>
  </div>
</div>

<div class="tips-bar">
  <span class="tips-label">Resume highlights →</span>
  <span class="tip-chip"><strong>UVM FIFO</strong> 100% coverage, 2000+ txns</span>
  <span class="tip-chip"><strong>Pipeline</strong> CPI 2.23 → 0.87 · 156% gain</span>
  <span class="tip-chip"><strong>Cadence Virtuoso</strong> LDO/boost · PVT stable</span>
  <span class="tip-chip"><strong>Zynq-7000</strong> rails · JTAG · AXI bring-up</span>
</div>

<div class="main">
  {sections}
</div>

<div class="footer">
  Last updated: {now} · Source: <a href="https://github.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026">zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026</a>
</div>

</body>
</html>"""

def main():
    print("Fetching source...")
    md = fetch_source()

    all_rows = []
    for section in TARGET_SECTIONS:
        rows = extract_table_rows(md, section)
        print(f"  {section}: {len(rows)} rows found")
        all_rows.extend(rows)

    filtered = filter_rows(all_rows)
    print(f"  After filtering: {len(filtered)} jobs kept")

    categorized = categorize(filtered)
    total = len(filtered)
    companies = len(set(j[0] for j in filtered))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = build_html(categorized, total, companies, now)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html written.")

if __name__ == "__main__":
    main()
