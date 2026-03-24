"""
filter_jobs.py
Fetches new-grad ECE hardware jobs and filters out any role that
requires US citizenship, security clearance, or is from a defense/
government employer. Saves the clean list to jobs.json.
"""

import json, re, urllib.request, urllib.error
from datetime import datetime, timezone

# ── BLOCKLIST ────────────────────────────────────────────────────────────────
BLOCKED = [
    # Defense / aerospace prime contractors
    "lockheed", "raytheon", "northrop", "general dynamics", "l3harris",
    "bae systems", "leidos", "saic", "booz allen", "caci",
    "mit lincoln", "draper laboratory", "mitre", "huntington ingalls", "hii",
    "textron", "dynetics", "peraton", "parsons", "general atomics",
    "mercury systems", "kratos", "aerojet", "mantech", "vectrus", "amentum",
    "cubic defense", "perspecta", "keyw", "bechtel national",
    "jacobs federal", "pae incorporated",
    # US government / federal agencies
    "u.s. army", "us army", "u.s. navy", "us navy", "u.s. air force",
    "us air force", "u.s. marine", "department of defense", "dept of defense",
    "department of energy", "nasa ", "federal aviation", "central intelligence",
    "national security agency", "nsa ", "federal bureau", "dept of homeland",
    "defense information", "disa ", "darpa ", "national reconnaissance",
    "u.s. government", "federal government",
    # Clearance / citizenship requirement phrases
    "clearance required", "secret clearance", "top secret", "ts/sci",
    "us citizenship required", "must be a us citizen", "us citizen only",
    "requires us citizenship", "active clearance", "dod clearance",
    "government clearance", "security clearance required",
]

# ── KNOWN OPT/SPONSOR-FRIENDLY COMPANIES ────────────────────────────────────
SPONSORS = {
    "nvidia": "yes", "qualcomm": "yes", "amd": "yes", "intel": "yes",
    "apple": "yes", "google": "yes", "meta": "yes", "microsoft": "yes",
    "amazon": "yes", "cisco": "yes", "broadcom": "yes", "marvell": "yes",
    "synopsys": "yes", "cadence": "yes", "arm ": "yes", "arm,": "yes",
    "texas instruments": "yes", "ti ": "yes", "analog devices": "yes",
    "micron": "yes", "samsung": "yes", "tsmc": "yes", "globalfoundries": "yes",
    "nxp": "yes", "infineon": "yes", "cirrus logic": "yes", "waymo": "yes",
    "etched": "yes", "sk hynix": "yes",
    # OPT-accepted (sponsor status not confirmed but OPT known OK)
    "spacex": "open", "tesla": "open", "tenstorrent": "open",
    "lattice": "open", "microchip": "open", "onsemi": "open",
    "on semiconductor": "open", "st micro": "open", "sambanova": "open",
}

ECE_KEYWORDS = [
    "verification", "soc", "asic", "fpga", "analog", "mixed-signal",
    "physical design", "board bring", "hardware engineer", "chip design",
    "vlsi", "rtl", "verilog", "systemverilog", "uvm", "digital design",
    "memory controller", "gpu", "dv engineer", "process engineer",
    "product engineer", "applications engineer", "embedded", "zynq",
    "semiconductor", "silicon", "layout engineer",
]

# ── FETCH SOURCE REPO README ──────────────────────────────────────────────────
SOURCE_URL = (
    "https://raw.githubusercontent.com/zapplyjobs/"
    "New-Grad-Hardware-Engineering-Jobs-2026/main/README.md"
)

def fetch_source():
    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=15) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Warning: could not fetch source ({e}). Using empty list.")
        return ""

# ── PARSE MARKDOWN TABLE ROWS ─────────────────────────────────────────────────
def parse_table(md_text):
    jobs = []
    for line in md_text.splitlines():
        if not line.startswith("|") or "---" in line or "Company" in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 3:
            continue
        # Extract plain text and href from markdown links  [text](url)
        def plain(s):
            return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s).strip()
        def href(s):
            m = re.search(r'\(([^)]+)\)', s)
            return m.group(1) if m else "#"

        company = plain(cols[0])
        role    = plain(cols[1]) if len(cols) > 1 else ""
        loc     = plain(cols[2]) if len(cols) > 2 else ""
        link    = href(cols[1]) if len(cols) > 1 else "#"
        date    = plain(cols[3]) if len(cols) > 3 else ""

        jobs.append({"company": company, "role": role,
                     "location": loc, "link": link, "date_added": date})
    return jobs

# ── FILTER ───────────────────────────────────────────────────────────────────
def is_blocked(job):
    haystack = " ".join([
        job.get("company",""), job.get("role",""), job.get("location","")
    ]).lower()
    return any(kw in haystack for kw in BLOCKED)

def is_ece(job):
    haystack = (job.get("company","") + " " + job.get("role","")).lower()
    return any(kw in haystack for kw in ECE_KEYWORDS)

def sponsor_status(job):
    name = job.get("company","").lower()
    for key, val in SPONSORS.items():
        if key in name:
            return val
    return "open"   # default: assume OPT ok unless proven otherwise

def categorize(job):
    r = job.get("role","").lower()
    if any(k in r for k in ["verification","dv ","uvm","soc verif"]): return "DV"
    if any(k in r for k in ["analog","mixed-signal","memory","dram"]): return "Analog"
    if any(k in r for k in ["fpga","bring-up","bring up","embedded"]): return "FPGA"
    if any(k in r for k in ["physical design","layout","asic design","process"]): return "ASIC"
    if any(k in r for k in ["software","firmware","sw "]): return "SW"
    return "HW"

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("Fetching jobs from source repo…")
    md = fetch_source()
    raw = parse_table(md)
    print(f"  Raw rows found: {len(raw)}")

    ece     = [j for j in raw if is_ece(j)]
    clean   = [j for j in ece  if not is_blocked(j)]
    blocked = [j for j in ece  if is_blocked(j)]
    print(f"  ECE-relevant: {len(ece)}  |  Blocked (defense/gov/clearance): {len(blocked)}  |  Clean: {len(clean)}")

    for j in clean:
        j["sponsor"] = sponsor_status(j)
        j["cat"]     = categorize(j)

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total": len(clean),
        "jobs": clean,
        "blocked_count": len(blocked),
    }

    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(clean)} OPT-friendly jobs to jobs.json ✅")

if __name__ == "__main__":
    main()
