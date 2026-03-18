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
    "cnc", "tooling", "US citizenship", "Security Clearance","Defense", "itar", "secret clearance", "top secret", "security clearance",
    "us citizen", "u\.s\. citizen", "clearance required",
    "green card", "permanent resident.*required",
    "must be.*citizen", "citizenship required",
]
EXCLUDE_COMPANIES = [
    # Defense / Aerospace / ITAR
    "spacex", "anduril", "northrop grumman", "lockheed martin",
    "rtx", "raytheon", "l3harris", "boeing", "leidos",
    "booz allen", "caci", "saic", "general dynamics", "bae systems",
    "blue origin", "shield ai", "palantir", "northwood space",
    "muon space", "astranis", "rocket lab", "relativity space",
    "hermeus", "radiant industries", "kbr", "amentum",
    "naval nuclear laboratory", "mitre", "the mitre corporation",
    "draper", "charles stark draper", "applied signal technology",
    "sierra nevada", "textron", "curtiss-wright", "moog",
    "cubic", "mercury systems", "kratos", "parsons",
    "peraton", "maxar", "planet labs", "spire global",

    # Usually require clearance even if not defense
    "cia", "nsa", "nga", "nro", "dod", "darpa",
]
TARGET_SECTIONS = ["Hardware Engineer", "FPGA/ASIC", "Embedded Systems"]

CATEGORIES = [
    {
        "key": "dv",
        "title": "Design Verification / SOC / GPU DV",
        "color": "#378ADD",
        "light": "#E6F1FB",
        "keywords": ["verification", "asic verif", "soc verif"],
    },
    {
        "key": "asic_fpga",
        "title": "ASIC / FPGA / Physical Design / RTL",
        "color": "#1D9E75",
        "light": "#E1F5EE",
        "keywords": ["fpga", "rtl", "asic design", "timing", "physical design", "layout"],
    },
    {
        "key": "analog",
        "title": "Analog & Mixed-Signal / Memory",
        "color": "#BA7517",
        "light": "#FAEEDA",
        "keywords": ["analog", "mixed", "memory design", "memory controller"],
    },
    {
        "key": "board",
        "title": "Board Bring-up / Hardware Engineer",
        "color": "#D4537E",
        "light": "#FBEAF0",
        "keywords": ["board", "bring", "hardware design", "hardware engineer", "avionics hardware"],
    },
    {
        "key": "app",
        "title": "Application / Field / Product Engineer",
        "color": "#7F77DD",
        "light": "#EEEDFE",
        "keywords": ["application engineer", "field application", "product engineer"],
    },
    {
        "key": "other",
        "title": "Other Relevant Roles",
        "color": "#888780",
        "light": "#F1EFE8",
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
    seen = set()

    # Skip roles that imply too much experience
    SENIORITY_EXCLUDE = [
        r"\bsenior\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b",
        r"\bmanager\b", r"\bdirector\b", r"\bvp\b", r"\bhead of\b",
        r"\b\d{3,}\+?\s*years?\b",   # 3+ digit years (10+ years etc)
        r"\b[5-9]\+\s*years?\b",      # 5+ to 9+ years
        r"\b[5-9]\s*\+\s*yr",         # 5+ yr variants
        r"minimum\s+[5-9]\s+years?",
        r"minimum\s+1[0-9]\s+years?",
        r"\bexperienced\b",
    ]

    for row in rows:
        parsed = parse_row(row)
        if not parsed:
            continue
        company, role, location, posted, url = parsed

        # Dedup by company + role
        key = (company.lower().strip(), role.lower().strip())
        if key in seen:
            continue
        seen.add(key)
         # Skip defense/ITAR companies
        if any(exc in company.lower() for exc in EXCLUDE_COMPANIES):
            continue
        # Skip excluded roles
        if matches(role, EXCLUDE_KEYWORDS):
            continue

        # Skip senior/experienced roles
        if matches(role, SENIORITY_EXCLUDE):
            continue

        # Must match target keywords
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

def section_html(cat, jobs):
    if not jobs:
        return ""
    rows = ""
    for company, role, location, posted, url in jobs:
        rows += f"""
        <tr>
          <td class="td-company">{company}</td>
          <td class="td-role"><a href="{url}" target="_blank">{role}</a></td>
          <td class="td-location">{location}</td>
          <td class="td-posted">{posted}</td>
        </tr>"""
    return f"""
    <div class="section">
      <div class="section-header">
        <div class="section-dot" style="background:{cat['color']}"></div>
        <span class="section-title">{cat['title']}</span>
        <span class="section-count">{len(jobs)} roles</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width:160px">Company</th>
              <th>Role</th>
              <th style="width:160px">Location</th>
              <th style="width:70px">Posted</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>"""

def build_html(categorized, total, companies, now):
    sections = "".join(
        section_html(cat, categorized[cat["key"]])
        for cat in CATEGORIES
    )
    num_cats = len([c for c in CATEGORIES if categorized[c["key"]]])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Harshini's ECE Job Tracker – 2026</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'DM Sans', sans-serif; background: #f4f6f9; color: #1a1a1a; min-height: 100vh; }}

.hero {{ background: #fff; border-bottom: 1px solid #e5e7eb; padding: 2rem 2rem 0; position: relative; overflow: hidden; }}
.hero-grid {{ position: absolute; inset: 0; background-image: linear-gradient(#e5e7eb 1px, transparent 1px), linear-gradient(90deg, #e5e7eb 1px, transparent 1px); background-size: 32px 32px; opacity: 0.5; }}
.hero-content {{ position: relative; z-index: 1; }}
.badge-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 1rem; }}
.badge {{ font-family: 'Space Mono', monospace; font-size: 10px; padding: 3px 10px; border-radius: 100px; letter-spacing: 0.05em; border: 1px solid; }}
.badge-blue {{ background: #E6F1FB; color: #0C447C; border-color: #85B7EB; }}
.badge-green {{ background: #E1F5EE; color: #085041; border-color: #5DCAA5; }}
.badge-amber {{ background: #FAEEDA; color: #633806; border-color: #EF9F27; }}
h1 {{ font-family: 'Space Mono', monospace; font-size: clamp(1.1rem, 3vw, 1.55rem); font-weight: 700; color: #111; line-height: 1.3; margin-bottom: 0.5rem; }}
h1 span {{ color: #378ADD; }}
.hero-sub {{ font-size: 13px; color: #555; line-height: 1.6; max-width: 700px; margin-bottom: 1.5rem; }}

.stats-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid #e5e7eb; }}
.stat {{ background: #fff; padding: 1rem 1.25rem; text-align: center; border-right: 1px solid #e5e7eb; }}
.stat:last-child {{ border-right: none; }}
.stat-num {{ font-family: 'Space Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #378ADD; display: block; }}
.stat-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }}

.tips-bar {{ background: #fff; border-bottom: 1px solid #e5e7eb; padding: 0.75rem 2rem; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }}
.tips-label {{ font-family: 'Space Mono', monospace; font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: 0.1em; white-space: nowrap; }}
.tip-chip {{ font-size: 12px; color: #555; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 3px 10px; white-space: nowrap; }}
.tip-chip strong {{ color: #111; font-weight: 500; }}

.main {{ padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }}

.section {{ margin-bottom: 2.5rem; animation: fadeUp 0.4s ease both; }}
.section:nth-child(1) {{ animation-delay: 0.05s; }}
.section:nth-child(2) {{ animation-delay: 0.1s; }}
.section:nth-child(3) {{ animation-delay: 0.15s; }}
.section:nth-child(4) {{ animation-delay: 0.2s; }}
.section:nth-child(5) {{ animation-delay: 0.25s; }}
.section:nth-child(6) {{ animation-delay: 0.3s; }}
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.section-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 0.6rem; }}
.section-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.section-title {{ font-family: 'Space Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #444; }}
.section-count {{ font-family: 'Space Mono', monospace; font-size: 10px; color: #aaa; margin-left: auto; }}

.table-wrap {{ border-radius: 10px; border: 1px solid #e5e7eb; overflow: hidden; background: #fff; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
thead tr {{ background: #f9fafb; }}
th {{ padding: 10px 14px; text-align: left; font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid #e5e7eb; }}
td {{ padding: 11px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover {{ background: #fafbfc; }}

.td-company {{ font-weight: 500; color: #111; white-space: nowrap; }}
.td-role a {{ color: #2563eb; text-decoration: none; font-weight: 400; }}
.td-role a:hover {{ text-decoration: underline; }}
.td-location {{ color: #777; font-size: 12px; }}
.td-posted {{ font-family: 'Space Mono', monospace; font-size: 11px; color: #aaa; white-space: nowrap; }}

.footer {{ text-align: center; padding: 1.5rem; font-family: 'Space Mono', monospace; font-size: 10px; color: #aaa; letter-spacing: 0.05em; border-top: 1px solid #e5e7eb; margin-top: 1rem; }}
.footer a {{ color: #378ADD; text-decoration: none; }}
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
    <div class="stat"><span class="stat-num">{num_cats}</span><span class="stat-label">Categories</span></div>
    <div class="stat"><span class="stat-num" style="font-size:1rem">6h</span><span class="stat-label">Refresh rate</span></div>
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
