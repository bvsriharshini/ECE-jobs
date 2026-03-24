"""
apify_scraper.py
Pulls ECE/hardware new-grad jobs from LinkedIn and Indeed
using Apify's free-tier actors. Merges results into jobs.json.
Run AFTER filter_jobs.py so it appends to existing jobs.
"""

import json, os, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")

# Search terms tailored to your background
SEARCH_QUERIES = [
    "ASIC Design Verification Engineer new grad",
    "Hardware Verification Engineer entry level",
    "FPGA Engineer new grad",
    "Analog IC Design Engineer entry level",
    "SOC Verification Engineer new grad",
    "Physical Design Engineer entry level",
    "Embedded Hardware Engineer new grad",
    "Semiconductor Engineer entry level 2026",
]

LOCATIONS = ["United States"]

# ── BLOCKLIST (same as filter_jobs.py) ───────────────────────────────────────
BLOCKED = [
    "lockheed","raytheon","northrop","general dynamics","l3harris",
    "bae systems","leidos","saic","booz allen","caci","mit lincoln",
    "draper","mitre","huntington ingalls","hii","textron","dynetics",
    "peraton","parsons","general atomics","mercury systems","kratos",
    "aerojet","mantech","vectrus","amentum","darpa","disa",
    "u.s. army","us army","u.s. navy","us navy","u.s. air force",
    "department of defense","nasa ","federal bureau","dept of homeland",
    "clearance required","secret clearance","top secret","ts/sci",
    "us citizenship required","must be a us citizen","us citizen only",
    "requires us citizenship","security clearance required",
]

SPONSORS = {
    "nvidia":"yes","qualcomm":"yes","amd":"yes","intel":"yes","apple":"yes",
    "google":"yes","meta":"yes","microsoft":"yes","amazon":"yes","cisco":"yes",
    "broadcom":"yes","marvell":"yes","synopsys":"yes","cadence":"yes",
    "arm":"yes","texas instruments":"yes","analog devices":"yes",
    "micron":"yes","samsung":"yes","tsmc":"yes","globalfoundries":"yes",
    "nxp":"yes","infineon":"yes","cirrus logic":"yes","waymo":"yes",
    "etched":"yes","sk hynix":"yes","openai":"yes",
    "spacex":"open","tesla":"open","tenstorrent":"open","verkada":"open",
    "lattice":"open","microchip":"open","onsemi":"open","weride":"open",
}

ECE_KEYWORDS = [
    "verification","soc","asic","fpga","analog","mixed-signal",
    "physical design","hardware engineer","chip design","vlsi","rtl",
    "verilog","systemverilog","uvm","digital design","memory","gpu",
    "semiconductor","silicon","layout","firmware","embedded","zynq",
    "process engineer","product engineer","applications engineer",
    "signal integrity","power integrity","pcb","synthesis","dft",
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def apify_post(url, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIFY_TOKEN}"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  Apify POST error: {e}")
        return None

def apify_get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {APIFY_TOKEN}"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  Apify GET error: {e}")
        return None

def wait_for_run(run_id, actor_id, max_wait=120):
    """Poll until Apify run finishes"""
    url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    for _ in range(max_wait // 5):
        time.sleep(5)
        data = apify_get(url)
        if not data: break
        status = data.get("data", {}).get("status", "")
        print(f"    Status: {status}")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            return status == "SUCCEEDED"
    return False

def fetch_dataset(dataset_id):
    url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json&limit=100"
    data = apify_get(url)
    return data if isinstance(data, list) else []

def is_blocked(text):
    t = text.lower()
    return any(kw in t for kw in BLOCKED)

def is_ece(text):
    t = text.lower()
    return any(kw in t for kw in ECE_KEYWORDS)

def sponsor_status(company):
    n = company.lower()
    for k, v in SPONSORS.items():
        if k in n: return v
    return "open"

def categorize(role):
    r = role.lower()
    if any(k in r for k in ["verification","dv ","uvm","soc verif","formal"]): return "DV"
    if any(k in r for k in ["analog","mixed-signal","memory","dram","ldo"]): return "Analog"
    if any(k in r for k in ["fpga","bring-up","embedded","firmware"]): return "FPGA"
    if any(k in r for k in ["physical design","layout","asic design","process","dft"]): return "ASIC"
    if any(k in r for k in ["software","sw ","firmware"]): return "SW"
    return "HW"

def normalize(item, source):
    """Normalize Apify result → our job format"""
    # LinkedIn and Indeed have slightly different field names
    company  = (item.get("companyName") or item.get("company") or "").strip()
    role     = (item.get("title") or item.get("positionName") or "").strip()
    location = (item.get("location") or item.get("jobLocation") or "US").strip()
    link     = (item.get("jobUrl") or item.get("url") or "#").strip()
    desc     = (item.get("description") or item.get("descriptionText") or "")

    if not company or not role: return None
    if not is_ece(role + " " + desc): return None
    if is_blocked(company + " " + role + " " + desc): return None

    return {
        "company":    company,
        "role":       role,
        "location":   location,
        "link":       link,
        "source":     source,
        "sponsor":    sponsor_status(company),
        "cat":        categorize(role),
        "urgent":     any(s in (role+desc).lower() for s in
                          ["urgent","immediate","hiring now","asap","rolling"]),
        "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

# ── LINKEDIN SCRAPER ──────────────────────────────────────────────────────────
def scrape_linkedin():
    """Uses Apify's free LinkedIn Jobs scraper actor"""
    print("\n🔗 Scraping LinkedIn Jobs via Apify…")
    if not APIFY_TOKEN:
        print("  ⚠️  No APIFY_TOKEN — skipping LinkedIn")
        return []

    all_jobs = []
    # Actor: bebity/linkedin-jobs-scraper (free tier)
    ACTOR_ID = "bebity~linkedin-jobs-scraper"

    for query in SEARCH_QUERIES[:4]:  # limit to 4 queries to stay in free tier
        print(f"  → LinkedIn: '{query}'")
        payload = {
            "title": query,
            "location": "United States",
            "publishedAt": "r86400",   # last 24 hours
            "contractType": "F",        # full time
            "experienceLevel": "1,2",   # entry + associate
            "rows": 25,
        }
        run = apify_post(
            f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
            payload
        )
        if not run: continue

        run_id      = run.get("data", {}).get("id")
        dataset_id  = run.get("data", {}).get("defaultDatasetId")
        if not run_id: continue

        success = wait_for_run(run_id, ACTOR_ID)
        if not success:
            print(f"    ⚠️  Run failed for '{query}'")
            continue

        items = fetch_dataset(dataset_id)
        print(f"    Raw items: {len(items)}")
        for item in items:
            job = normalize(item, "LinkedIn")
            if job: all_jobs.append(job)

        time.sleep(2)  # be polite

    print(f"  ✅ LinkedIn: {len(all_jobs)} ECE jobs found")
    return all_jobs

# ── INDEED SCRAPER ────────────────────────────────────────────────────────────
def scrape_indeed():
    """Uses Apify's free Indeed scraper actor"""
    print("\n📋 Scraping Indeed via Apify…")
    if not APIFY_TOKEN:
        print("  ⚠️  No APIFY_TOKEN — skipping Indeed")
        return []

    all_jobs = []
    # Actor: misceres/indeed-scraper (free tier)
    ACTOR_ID = "misceres~indeed-scraper"

    for query in SEARCH_QUERIES[:4]:
        print(f"  → Indeed: '{query}'")
        payload = {
            "position": query,
            "country": "US",
            "location": "United States",
            "maxItems": 25,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
            "followApplyRedirects": False,
        }
        run = apify_post(
            f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
            payload
        )
        if not run: continue

        run_id     = run.get("data", {}).get("id")
        dataset_id = run.get("data", {}).get("defaultDatasetId")
        if not run_id: continue

        success = wait_for_run(run_id, ACTOR_ID)
        if not success:
            print(f"    ⚠️  Run failed for '{query}'")
            continue

        items = fetch_dataset(dataset_id)
        print(f"    Raw items: {len(items)}")
        for item in items:
            job = normalize(item, "Indeed")
            if job: all_jobs.append(job)

        time.sleep(2)

    print(f"  ✅ Indeed: {len(all_jobs)} ECE jobs found")
    return all_jobs

# ── DEDUP ─────────────────────────────────────────────────────────────────────
def dedup(jobs):
    seen, out = set(), []
    for j in jobs:
        key = (j["company"].lower(), j["role"].lower()[:40])
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # Load existing jobs.json
    existing = []
    if Path("jobs.json").exists():
        with open("jobs.json") as f:
            data = json.load(f)
        existing = data.get("jobs", [])
        print(f"📋 Existing jobs from filter_jobs.py: {len(existing)}")
    else:
        data = {}
        print("⚠️  No jobs.json found — creating fresh")

    # Scrape LinkedIn + Indeed
    linkedin_jobs = scrape_linkedin()
    indeed_jobs   = scrape_indeed()

    # Merge all
    all_jobs = existing + linkedin_jobs + indeed_jobs
    all_jobs = dedup(all_jobs)

    blocked = [j for j in all_jobs if is_blocked(j["company"]+" "+j["role"])]
    clean   = [j for j in all_jobs if not is_blocked(j["company"]+" "+j["role"])]

    print(f"\n📊 Summary:")
    print(f"  Existing jobs:  {len(existing)}")
    print(f"  LinkedIn new:   {len(linkedin_jobs)}")
    print(f"  Indeed new:     {len(indeed_jobs)}")
    print(f"  After dedup:    {len(clean)}")
    print(f"  Blocked:        {len(blocked)}")

    data["jobs"]          = clean
    data["total"]         = len(clean)
    data["updated"]       = datetime.now(timezone.utc).isoformat()
    data["blocked_count"] = len(blocked)
    data["sources"]       = ["GitHub repos","Greenhouse","Ashby","Lever","LinkedIn","Indeed"]

    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n💾 Saved {len(clean)} total OPT-friendly jobs to jobs.json ✅")

if __name__ == "__main__":
    main()
