import requests
import re
from datetime import datetime, timezone

SOURCE_URL = "https://raw.githubusercontent.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026/main/README.md"

# Keywords to keep (ECE-relevant roles)
KEEP_KEYWORDS = [
    "verification", "asic", "fpga", "soc", "embedded", "firmware",
    "analog", "mixed.signal", "electrical", "signal integrity", "layout",
    "physical design", "dft", "bring.up", "hardware engineer", "circuit design",
    "rtl", "chip", "vlsi", "memory", "dsp", "rf", "pcb", "ams"
]

# Keywords that disqualify a row (noise)
DROP_KEYWORDS = [
    "hvac", "fitness", "graphic designer", "supply chain", "facilities",
    "manufacturing tech", "civil", "reliability technician", "clerical",
    "cosmoquick", "accounting", "medical", "dental", "site reliability engineer"
]

def matches(text):
    t = text.lower()
    if any(re.search(k, t) for k in DROP_KEYWORDS):
        return False
    return any(re.search(k, t) for k in KEEP_KEYWORDS)

def fetch_and_filter():
    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()
    lines = r.text.splitlines()

    # Find table rows (lines starting with | 🏢)
    job_rows = []
    for line in lines:
        if line.startswith("| 🏢") and "[Apply]" in line:
            if matches(line):
                job_rows.append(line)

    return job_rows

def write_readme(rows):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"""<style>
body {{ font-family: Arial; max-width: 1100px; margin: 0 auto; padding: 30px; background: #f9fbfd; color: #333; line-height: 1.6; }}
h1 {{ color: #1e40af; }}
h2 {{ color: #1e3a8a; border-bottom: 2px solid #ddd; padding-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
th {{ background: #eff6ff; font-weight: bold; }}
a {{ color: #2563eb; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>

# Harshini's ECE Job Board – Auto-Updated
**OPT/F1 Friendly | Entry-Level & New Grad | Focus: DV, ASIC, FPGA, Analog, Embedded**

🕐 Last updated: **{now}**  
📌 Source: [zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026](https://github.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026)  
🌐 Live site: [bvsriharshini.github.io/ECE-jobs](https://bvsriharshini.github.io/ECE-jobs/)

---

**My Focus Areas:** Design Verification · SOC · GPU DV · Analog/Mixed-Signal · ASIC · FPGA · Embedded Systems · Board Bring-up · Physical Design

**Quick Resume Highlights:**
- UVM FIFO: 100% coverage, 2000+ transactions
- Pipeline processor: CPI 2.23 → 0.87, 156% gain
- Cadence Virtuoso LDO/boost: PVT stability
- Zynq-7000 bring-up: rails, JTAG, AXI

---

## 🔄 Latest ECE Jobs ({len(rows)} filtered from source)

| Company | Role | Location | Posted | Apply |
|---------|------|----------|--------|-------|
"""
    body = "\n".join(rows)
    footer = f"\n\n---\n_Auto-filtered from source repo. Refreshes every 4 hours._\n"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(header + body + footer)

if __name__ == "__main__":
    rows = fetch_and_filter()
    print(f"Found {len(rows)} matching ECE jobs")
    write_readme(rows)
