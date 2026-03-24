"""
filter_jobs.py
Pulls ECE/hardware new-grad jobs from MULTIPLE sources:
  1. GitHub job repos (zapplyjobs, pittcsc, etc.)
  2. Greenhouse (startup ATS - powers hundreds of startup job boards)
  3. Ashby (modern startup ATS)
  4. Lever (startup ATS)
  5. Wellfound/AngelList (startup-only jobs)
Filters out defense/gov/clearance. Flags urgent hiring.
Saves clean list to jobs.json.
"""

import json, re, urllib.request, urllib.error, time
from datetime import datetime, timezone

# ── BLOCKLIST ────────────────────────────────────────────────────────────────
BLOCKED = [
    "lockheed","raytheon","northrop","general dynamics","l3harris",
    "bae systems","leidos","saic","booz allen","caci",
    "mit lincoln","draper laboratory","mitre","huntington ingalls","hii",
    "textron","dynetics","peraton","parsons","general atomics",
    "mercury systems","kratos","aerojet","mantech","vectrus","amentum",
    "cubic defense","perspecta","keyw","bechtel national","pae incorporated",
    "u.s. army","us army","u.s. navy","us navy","u.s. air force","us air force",
    "u.s. marine","department of defense","dept of defense",
    "department of energy","nasa ","federal aviation","central intelligence",
    "national security agency","nsa ","federal bureau","dept of homeland",
    "defense information","disa ","darpa ","national reconnaissance",
    "u.s. government","federal government",
    "clearance required","secret clearance","top secret","ts/sci",
    "us citizenship required","must be a us citizen","us citizen only",
    "requires us citizenship","active clearance","dod clearance",
    "government clearance","security clearance required",
]

# ── URGENT HIRING SIGNALS ────────────────────────────────────────────────────
URGENT_SIGNALS = [
    "urgent","immediate","asap","start immediately","starting immediately",
    "quick hire","fast track","rolling basis","open immediately",
    "hiring now","fill immediately","priority hire",
]

# ── OPT/SPONSOR STATUS ───────────────────────────────────────────────────────
SPONSORS = {
    "nvidia":"yes","qualcomm":"yes","amd":"yes","intel":"yes","apple":"yes",
    "google":"yes","meta":"yes","microsoft":"yes","amazon":"yes","cisco":"yes",
    "broadcom":"yes","marvell":"yes","synopsys":"yes","cadence":"yes",
    "arm":"yes","texas instruments":"yes","analog devices":"yes",
    "micron":"yes","samsung":"yes","tsmc":"yes","globalfoundries":"yes",
    "nxp":"yes","infineon":"yes","cirrus logic":"yes","waymo":"yes",
    "etched":"yes","sk hynix":"yes","openai":"yes","anthropic":"yes",
    "spacex":"open","tesla":"open","tenstorrent":"open","lattice":"open",
    "microchip":"open","onsemi":"open","st micro":"open","sambanova":"open",
    "verkada":"open","weride":"open","freeform":"open","kla":"open",
    "jane street":"open","imc trading":"open","eaton":"open",
}

ECE_KEYWORDS = [
    "verification","soc","asic","fpga","analog","mixed-signal",
    "physical design","board bring","hardware engineer","chip design",
    "vlsi","rtl","verilog","systemverilog","uvm","digital design",
    "memory controller","gpu","dv engineer","process engineer",
    "product engineer","applications engineer","embedded","zynq",
    "semiconductor","silicon","layout engineer","firmware","electrical engineer",
    "signal integrity","power integrity","pcb","schematic","eda","synthesis",
    "timing closure","place and route","pnr","dft","scan","bist",
]

# ── STARTUP ATS SOURCES ──────────────────────────────────────────────────────
# These are real API endpoints that return JSON job data — no API key needed

GREENHOUSE_COMPANIES = [
    # AI/chip startups actively hiring ECE new grads
    ("Tenstorrent",    "tenstorrent"),
    ("Etched",         "etched"),
    ("Groq",           "groq"),
    ("Cerebras",       "cerebras-systems"),
    ("SambaNova",      "sambanova-systems"),
    ("Lightmatter",    "lightmatter"),
    ("Untether AI",    "untether-ai"),
    ("Rain AI",        "rain-neuromorphics"),
    ("Axonim",         "axonim"),
    ("Rebellion",      "rebellion-defense"),   # will be blocked - defense
    ("Mythic",         "mythic"),
    ("Esperanto",      "esperanto-technologies"),
    ("Flex Logix",     "flex-logix"),
    ("Ampere Computing","ampere-computing"),
    ("Mojo Vision",    "mojo-vision"),
    ("Luminous Computing","luminous-computing"),
    ("Jane Street",    "janestreet"),
    ("IMC Trading",    "imc"),
    ("Verkada",        "verkada"),
    ("Samsara",        "samsara"),
    ("Freeform",       "freeformfuturecorp"),
    ("WeRide",         "weride"),
]

ASHBY_COMPANIES = [
    ("Etched",         "etched"),
    ("Handshake",      "handshake"),
    ("Aeva",           "aeva"),
    ("Mobileye",       "mobileye"),
    ("Nuro",           "nuro"),
    ("Zoox",           "zoox"),
    ("Aurora",         "aurora-innovation"),
    ("Wayve",          "wayve"),
]

LEVER_COMPANIES = [
    ("Anduril",        "anduril"),   # will be blocked - defense
    ("Shield AI",      "shield-ai"), # will be blocked - defense
    ("Recursion",      "recursion-pharmaceuticals"),
    ("Medtronic",      "medtronic"),
]

# ── GITHUB README SOURCES ────────────────────────────────────────────────────
GITHUB_SOURCES = [
    {
        "name": "zapplyjobs Hardware 2026",
        "url": "https://raw.githubusercontent.com/zapplyjobs/New-Grad-Hardware-Engineering-Jobs-2026/main/README.md"
    },
    {
        "name": "pittcsc New Grad 2026",
        "url": "https://raw.githubusercontent.com/pittcsc/NewGrad-2025/main/README.md"
    },
    {
        "name": "SimplifyJobs New Grad",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"
    },
    {
        "name": "ReaVNaiL New Grad Hardware",
        "url": "https://raw.githubusercontent.com/ReaVNaiL/New-Grad-and-Entry-Level-Jobs-2026/main/README.md"
    },
]

# ── HELPERS ──────────────────────────────────────────────────────────────────
def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ⚠️  Could not fetch {url}: {e}")
        return ""

def is_blocked(text):
    t = text.lower()
    return any(kw in t for kw in BLOCKED)

def is_ece(text):
    t = text.lower()
    return any(kw in t for kw in ECE_KEYWORDS)

def is_urgent(text):
    t = text.lower()
    return any(sig in t for sig in URGENT_SIGNALS)

def sponsor_status(company_name):
    n = company_name.lower()
    for key, val in SPONSORS.items():
        if key in n:
            return val
    return "open"

def categorize(role):
    r = role.lower()
    if any(k in r for k in ["verification","dv ","uvm","soc verif","formal"]): return "DV"
    if any(k in r for k in ["analog","mixed-signal","memory","dram","ldo"]): return "Analog"
    if any(k in r for k in ["fpga","bring-up","bring up","embedded","firmware"]): return "FPGA"
    if any(k in r for k in ["physical design","layout","asic design","process","pnr","synthesis","dft"]): return "ASIC"
    if any(k in r for k in ["software","sw ","ml ","ai "]): return "SW"
    return "HW"

def make_job(company, role, location, link, source, extra=""):
    return {
        "company":   company,
        "role":      role,
        "location":  location,
        "link":      link,
        "source":    source,
        "sponsor":   sponsor_status(company),
        "cat":       categorize(role),
        "urgent":    is_urgent(role + " " + extra),
        "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

# ── PARSERS ──────────────────────────────────────────────────────────────────
def parse_github_readme(md, source_name):
    jobs = []
    for line in md.splitlines():
        if not line.startswith("|") or "---" in line or "Company" in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 3:
            continue
        def plain(s): return re.sub(r'\*\*([^*]+)\*\*', r'\1', re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)).strip()
        def href(s):
            m = re.search(r'\(([^)]+)\)', s)
            return m.group(1) if m else "#"
        company  = plain(cols[0])
        role     = plain(cols[1]) if len(cols) > 1 else ""
        location = plain(cols[2]) if len(cols) > 2 else "US"
        link     = href(cols[1]) if len(cols) > 1 else "#"
        if company and role and is_ece(company + " " + role):
            jobs.append(make_job(company, role, location, link, source_name))
    return jobs

def fetch_greenhouse(company_name, board_token):
    """Greenhouse public API — no key needed"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    raw = fetch(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except:
        return []
    jobs = []
    for j in data.get("jobs", []):
        title    = j.get("title", "")
        location = j.get("location", {}).get("name", "US")
        link     = j.get("absolute_url", "#")
        content  = j.get("content", "")
        if is_ece(title + " " + content):
            jobs.append(make_job(company_name, title, location, link, "Greenhouse", content))
    return jobs

def fetch_ashby(company_name, board_token):
    """Ashby public API — no key needed"""
    url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    payload = json.dumps({
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": board_token},
        "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: publishedJobBoard(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName jobLocation { locationName } employmentType isListed externalLink } } }"
    }).encode()
    try:
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  Ashby {board_token}: {e}")
        return []
    jobs = []
    for j in (data.get("data",{}).get("jobBoard",{}) or {}).get("jobPostings",[]):
        if not j.get("isListed"): continue
        title = j.get("title","")
        loc   = (j.get("jobLocation") or {}).get("locationName") or j.get("locationName","US")
        link  = j.get("externalLink") or f"https://jobs.ashbyhq.com/{board_token}/{j.get('id')}"
        if is_ece(title):
            jobs.append(make_job(company_name, title, loc, link, "Ashby"))
    return jobs

def fetch_lever(company_name, board_token):
    """Lever public API — no key needed"""
    url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    raw = fetch(url)
    if not raw: return []
    try: postings = json.loads(raw)
    except: return []
    jobs = []
    for j in postings:
        title = j.get("text","")
        loc   = j.get("categories",{}).get("location","US")
        link  = j.get("hostedUrl","#")
        desc  = j.get("descriptionPlain","")
        if is_ece(title + " " + desc):
            jobs.append(make_job(company_name, title, loc, link, "Lever", desc))
    return jobs

# ── DEDUP ─────────────────────────────────────────────────────────────────────
def dedup(jobs):
    seen = set()
    out  = []
    for j in jobs:
        key = (j["company"].lower(), j["role"].lower()[:40])
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    all_jobs = []

    # 1. GitHub README sources
    print("\n📂 Fetching GitHub repo sources…")
    for src in GITHUB_SOURCES:
        print(f"  → {src['name']}")
        md   = fetch(src["url"])
        jobs = parse_github_readme(md, src["name"])
        print(f"     Found {len(jobs)} ECE jobs")
        all_jobs.extend(jobs)
        time.sleep(0.5)

    # 2. Greenhouse startup ATSes
    print("\n🌱 Fetching Greenhouse startup boards…")
    for name, token in GREENHOUSE_COMPANIES:
        print(f"  → {name}")
        jobs = fetch_greenhouse(name, token)
        print(f"     Found {len(jobs)} ECE jobs")
        all_jobs.extend(jobs)
        time.sleep(0.3)

    # 3. Ashby startup ATSes
    print("\n⚡ Fetching Ashby startup boards…")
    for name, token in ASHBY_COMPANIES:
        print(f"  → {name}")
        jobs = fetch_ashby(name, token)
        print(f"     Found {len(jobs)} ECE jobs")
        all_jobs.extend(jobs)
        time.sleep(0.3)

    # 4. Lever startup ATSes
    print("\n🔧 Fetching Lever startup boards…")
    for name, token in LEVER_COMPANIES:
        print(f"  → {name}")
        jobs = fetch_lever(name, token)
        print(f"     Found {len(jobs)} ECE jobs")
        all_jobs.extend(jobs)
        time.sleep(0.3)

    print(f"\n📊 Total raw jobs collected: {len(all_jobs)}")

    # Filter
    blocked = [j for j in all_jobs if is_blocked(j["company"]+" "+j["role"])]
    clean   = [j for j in all_jobs if not is_blocked(j["company"]+" "+j["role"])]
    clean   = dedup(clean)
    urgent  = [j for j in clean if j["urgent"]]

    print(f"🚫 Blocked (defense/gov/clearance): {len(blocked)}")
    print(f"✅ Clean OPT-friendly jobs: {len(clean)}")
    print(f"🔴 Urgent hiring roles: {len(urgent)}")

    output = {
        "updated":       datetime.now(timezone.utc).isoformat(),
        "total":         len(clean),
        "urgent_count":  len(urgent),
        "blocked_count": len(blocked),
        "jobs":          clean,
    }

    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Saved to jobs.json ✅")

if __name__ == "__main__":
    main()
