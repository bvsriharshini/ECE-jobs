import urllib.request
import re
from datetime import datetime, timezone

SOURCE_URL = "https://raw.githubusercontent.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026/main/README.md"

# Keywords to INCLUDE (role must match at least one)
INCLUDE_KEYWORDS = [
    "verification", "design verification", "asic verification", "soc verification",
    "asic design", "fpga", "asic", "soc", "gpu",
    "analog", "mixed.signal", "memory design", "memory controller",
    "physical design", "layout engineer",
    "bring.up", "bringup",
    "board", "hardware engineer", "hardware design",
    "application engineer", "field application",
    "product engineer", "process engineer.*semiconductor",
    "rtl", "timing engineer",
    "new college grad", "new grad", "entry level", "associate.*engineer",
]

# Keywords to EXCLUDE — skip roles that are clearly not ECE hardware
EXCLUDE_KEYWORDS = [
    "plasma center", "nurse", "hvac", "manufacturing engineer",
    "mechanical engineer", "procurement", "graphic designer",
    "site reliability", "software.*reliability", "data platform",
    "brand", "ui/ux", "front.end design", "web design",
    "logistics", "supply chain", "legal", "marketing",
    "propulsion", "aero", "turbomachinery", "thermal engineer",
    "cfpd", "cfd", "gmp", "clinical", "pharma", "medical",
    "compressor", "hvac", "facilities.*mechanical",
    "quality engineer.*manufacturing",
    "cnc", "tooling",
]

# Sections to scrape from the source
TARGET_SECTIONS = [
    "Hardware Engineer",
    "FPGA/ASIC",
    "Embedded Systems",
]

def fetch_source():
    with urllib.request.urlopen(SOURCE_URL) as r:
        return r.read().decode("utf-8")

def matches(role_text, keywords):
    t = role_text.lower()
    return any(re.search(kw, t) for kw in keywords)

def extract_table_rows(md, section_name):
    """Extract markdown table rows from a named <details> section."""
    # Find the section
    pattern = rf"<summary>.*?{re.escape(section_name)}.*?</summary>(.*?)</details>"
    m = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1)
    rows = []
    for line in block.splitlines():
        line = line.strip()
        # Table rows start with | and have actual content (not header/separator)
        if line.startswith("|") and not line.startswith("| ---") and not line.startswith("| Company"):
            rows.append(line)
    return rows

def parse_row(row):
    """Return (company, role, location, posted, apply_url) from a table row."""
    # Strip leading/trailing pipes
    cols = [c.strip() for c in row.strip("|").split("|")]
    if len(cols) < 5:
        return None
    company_raw = cols[0]
    role = cols[1]
    location = cols[2]
    posted = cols[3]
    apply_col = cols[4]

    # Clean company name — strip emoji and bold markers
    company = re.sub(r"[🏢*]", "", company_raw).strip()

    # Extract URL from apply column (markdown link or img link)
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

# --- Category labels for Harshini's sections ---
def categorize(role):
    r = role.lower()
    if any(k in r for k in ["verification", "asic verif", "soc verif", "dv"]):
        return "dv"
    if any(k in r for k in ["fpga", "rtl", "asic design", "timing", "physical design", "layout"]):
        return "asic_fpga"
    if any(k in r for k in ["analog", "mixed", "memory design", "memory controller"]):
        return "analog"
    if any(k in r for k in ["board", "bring", "hardware design", "hardware engineer", "avionics hardware"]):
        return "board"
    if any(k in r for k in ["application engineer", "field application", "product engineer"]):
        return "app"
    return "other"

def build_readme(categorized):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def table(rows):
        if not rows:
            return "_No matching jobs found right now — check back in 6 hours._\n"
        lines = ["| Company | Role | Location | Posted | Apply |",
                 "|---------|------|----------|--------|-------|"]
        for company, role, location, posted, url in rows:
            lines.append(f"| {company} | {role} | {location} | {posted} | [Apply]({url}) |")
        return "\n".join(lines) + "\n"

    dv    = table(categorized.get("dv", []))
    asic  = table(categorized.get("asic_fpga", []))
    analog= table(categorized.get("analog", []))
    board = table(categorized.get("board", []))
    app   = table(categorized.get("app", []))
    other = table(categorized.get("other", []))

    return f"""<style>
body {{ font-family: Arial, sans-serif; max-width: 1100px; margin: 0 auto; padding: 40px 20px; background: #f9fbfd; color: #333; line-height: 1.6; }}
h1 {{ color: #1e40af; font-size: 2.2em; margin-bottom: 10px; }}
h2 {{ color: #1e3a8a; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 40px; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
th, td {{ border: 1px solid #d1d5db; padding: 14px 16px; text-align: left; }}
th {{ background: #eff6ff; font-weight: bold; color: #1e40af; }}
tr:nth-child(even) {{ background: #f8fafc; }}
a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
a:hover {{ text-decoration: underline; color: #1d4ed8; }}
.tips {{ background: #fefce8; padding: 16px; border-left: 4px solid #ca8a04; margin: 20px 0; border-radius: 4px; }}
</style>

# Harshini's Personal ECE Job Tracker – 2026 Entry-Level / New Grad (OPT/F1)

**My Focus**
Entry-level / new college grad roles in US (no citizenship/clearance required).
Target: Design Verification • SOC Verification • GPU DV • Analog/Mixed-Signal • Board Bring-up • ASIC • Physical Design • Layout • Memory Controller • Hardware/Process/Product/Field/System Applications Engineer

**Auto-update**: Every ~6 hours · Bookmark: https://bvsriharshini.github.io/ECE-jobs/

<div class="tips">

**Quick Apply Tips**
- UVM FIFO: 100% coverage, 2000+ transactions
- Pipeline processor: CPI 2.23 → 0.87, 156% gain
- Cadence Virtuoso LDO/boost: PVT stability
- Zynq-7000 bring-up: rails, JTAG, AXI

</div>

**Last updated:** {now}

---

## Design Verification / SOC / GPU DV

{dv}
## ASIC / FPGA / Physical Design / RTL

{asic}
## Analog & Mixed-Signal / Memory Controller

{analog}
## Board Bring-up / Hardware Engineer

{board}
## Application / Product / Field Engineer

{app}
## Other Relevant Roles

{other}
---
*Source: [zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026](https://github.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026)*
"""

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

    categorized = {}
    for row in filtered:
        cat = categorize(row[1])
        categorized.setdefault(cat, []).append(row)

    readme = build_readme(categorized)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("README.md written.")

if __name__ == "__main__":
    main()
