"""
resume_tailor.py
For each new job in jobs.json:
  1. Sends job description + your base resume to Claude AI
  2. Claude rewrites bullets to match JD keywords (ATS 95%+)
  3. Generates a styled PDF
  4. Saves to /resumes/CompanyName_Role.pdf
  5. Updates jobs.json with resume path
"""

import json, os, re, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── YOUR BASE RESUME ──────────────────────────────────────────────────────────
BASE_RESUME = """
NAME: Venkata Sri Harshini Boorela
PHONE: +1(617)-922-9643
EMAIL: sriharshiniboorela@gmail.com
LINKEDIN: linkedin.com/in/sriharshini-bv-05092001s
GITHUB: github.com/bvsriharshini

SUMMARY
Graduate engineer with strong background in power electronics such as multi-phase buck converters,
well versed in analog circuit modeling and SPICE simulation tools, PCB review, and hands-on
validation using lab instrumentation.

EDUCATION
M.S. Electrical and Computer Engineering | Northeastern University, Boston, MA | Sep 2023 – May 2025 | GPA: 3.5/4.0
Coursework: VLSI Design, Analog IC Design, Solid State Devices, Power Management IC, Electronic Materials

B.Tech Electronics and Communication Engineering | JNTU Vizianagaram | Aug 2019 – May 2023 | GPA: 3.7/4.0
Coursework: Electronic Devices and Circuits, Linear IC Applications, Signals and Systems, Digital IC Design

TECHNICAL SKILLS
Power Conversion & Control: Multi-phase buck, digital multi-phase control, DC-DC converters, LDO, PDN,
  closed-loop compensation, gain and phase margin, charge pump, digital power management
Simulation & Modeling: PSpice, SPICE, Simplis, AC and transient analysis
Validation & Characterization: Product characterization, power debugging, oscilloscope, electronic load, power supplies
PCB & Hardware Design: Schematic capture, PCB layout review, evaluation board validation, OrCAD, Allegro, Cadence, Altium
Programming & Automation: Python, C, Verilog, SystemVerilog
Verification: UVM, functional coverage, constrained random verification, assertions, regression automation

EXPERIENCE
Research Assistant | Elon University | Jul 2025 – Present
- Synced motion capture and AMTI force plate data at 1000 Hz with Butterworth filtering and stance detection using Python
- Processed 16-channel EMG using 20–450 Hz bandpass, rectification, and RMS windowing for onset and amplitude extraction
- Automated dropout detection, interpolation, and body mass normalization to generate clean time series for inverse dynamics
- Documented sensor setup, sampling rates, filtering parameters, and data validation steps for reproducible workflows

Graduate Teaching Assistant | Northeastern University | Sep 2023 – May 2025
- Supported Wireless Communications labs covering modulation and spectrum analysis using oscilloscopes and signal generators
- Guided waveform measurement, noise analysis, and signal integrity validation in hardware lab experiments

Intern | CoreEl Technologies | Jan 2023 – Mar 2023
- Performed Zynq-7000 board bring-up by validating rail shorts, sequencing 1.0V to 3.3V rails, confirming JTAG enumeration
- Verified high-speed interfaces through clock stability, signal integrity, and JTAG chain validation
- Deployed bare-metal UART application via Vivado and Vitis with successful FT2232H console output at 115200 baud

PROJECTS
Buck Converter PCB Layout (Altium Designer) | Oct 2025 – Dec 2025
- Designed 2-layer buck converter PCB including schematic capture, PCB layout, and DRC validation
- Implemented solid ground plane, via stitching, optimized routing, and EMI layout; delivered fabrication-ready Gerbers and BOM

Step-Up DC-DC Switching Regulator in CMOS (Cadence Virtuoso) | Jan 2024 – Apr 2024
- Designed 2 MHz CMOS boost regulator based on LM2621 supporting 1.2–4V input and 2.5A switch current
- Integrated multistage OTA compensation for stable closed-loop regulation across line, load, and -40°C to 125°C
- Validated line, load, and transient stability through SPICE simulations under dynamic operating conditions

VLSI Low Dropout Linear Regulator (Cadence Virtuoso) | Oct 2023 – Dec 2023
- Designed LDO based on TPS786 architecture using folded cascode amplifier and bandgap reference
- Achieved high PSRR, low output noise, fast startup, and low dropout through compensation tuning and bias optimization
- Verified line, load, and transient response across -40°C to 125°C temperature range

AXI-Lite Memory Verification using UVM | May 2025 – Jul 2025
- Developed constrained random UVM testbench verifying AXI-Lite read/write transactions and protocol handshakes
- Identified 7 RTL corner-case bugs using assertions and scoreboard comparison improving design robustness
- Automated regression suite using Python reducing debug turnaround time by 50%

FPGA-Based Pipeline Processor (DE1-SoC) | Oct 2024 – Dec 2024
- Engineered 5-stage pipelined processor with stall detection and forwarding logic eliminating data hazards in Verilog
- Improved throughput by 143% and cut execution time by 58.8% by reducing CPI from 2.23 to 0.87
- Verified pipeline using ModelSim and SignalTap with custom counters for stall and latency analysis

QLC NAND SSD Architecture Performance Optimization | Jan 2026 – Mar 2026
- Modeled 16 GB QLC SSD in VSSIM, optimizing channel parallelism to reduce runtime and improve write throughput
- Designed 25% SLC cache hybrid architecture improving QLC write performance and storage efficiency
- Analyzed MQSim queue depth contention, proposing FTL scheduling improvements for IO fairness

Wishbone Memory Verification | Sep 2025 – Dec 2025
- Designed FSM-based Wishbone memory module supporting synchronous read/write with protocol-compliant handshaking
- Performed RTL synthesis and static timing analysis validating setup/hold closure under defined SDC constraints

AMBA AHB Protocol Verification using UVM | Jun 2025 – Aug 2025
- Verified AHB protocol including burst, single, and split transfers achieving 100% coverage
- Implemented protocol assertions validating HREADY, HRESP, and address phase timing compliance
- Detected 6 protocol timing violations under randomized stress scenarios

MEMS-Based Varactor Fabrication (Cleanroom) | Jan 2025 – Mar 2025
- Fabricated MEMS varactors using S1813 lithography, Al sputtering, ICP RIE patterning, and XeF2 release in Class 100 cleanroom
- Performed RF S-parameter extraction using VNA and derived kt2, Q factor, and motional parameters in MATLAB

8x2 SRAM Array Using 6T SRAM Cell | Jan 2024 – Mar 2024
- Designed 8x2 SRAM array in 180nm CMOS integrating 6T cell, decoders, sense amplifiers, and write drivers
- Verified read stability and write margin across voltage and temperature corners using SPICE

High-k Dielectrics for Advanced CMOS (XRR) | Jan 2024 – May 2024
- Characterized HfO2 and ZrO2 gate stacks achieving 50% leakage reduction compared to SiO2 baseline
- Extracted dielectric constant, thickness uniformity, and interface quality using XRR and spectroscopic ellipsometry

4x4 Combinational Multiplier Verification using UVM | May 2025 – Jul 2025
- Developed UVM environment with driver, monitor, and scoreboard achieving 100% functional coverage
- Executed 5,000 constrained random transactions detecting 3 corner-case mismatches

D Flip-Flop Verification using UVM with Configurable Agent | May 2025 – Jun 2025
- Built reusable UVM agent supporting active and passive modes for sequential logic verification
- Achieved 100% toggle and branch coverage across reset and clock edge conditions
"""

# ── CLAUDE AI CALL ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def tailor_resume_with_claude(job):
    """Send resume + JD to Claude, get back ATS-optimized resume"""
    if not ANTHROPIC_API_KEY:
        print("  ⚠️  No ANTHROPIC_API_KEY found — skipping AI tailoring")
        return None

    prompt = f"""You are an expert ATS resume optimizer for ECE/hardware engineering roles.

JOB DESCRIPTION:
Company: {job['company']}
Role: {job['role']}
Location: {job['location']}

BASE RESUME:
{BASE_RESUME}

TASK:
1. Extract ALL technical keywords, tools, skills from the job description
2. Rewrite the resume bullets to naturally incorporate those keywords
3. Reorder experience/projects to best match what this company cares about
4. Keep all facts true — only rephrase, never invent experience
5. Add a 3-line SUMMARY section at top tailored to this specific role
6. Ensure ATS score would be 90-95%+ by matching key phrases exactly

OUTPUT FORMAT — return ONLY this JSON, nothing else:
{{
  "ats_score": 94,
  "summary": "3-line professional summary here",
  "skills_added": ["keyword1", "keyword2"],
  "tailored_bullets": {{
    "experience": ["bullet1", "bullet2", "bullet3", "bullet4"],
    "project_fifo": ["bullet1", "bullet2", "bullet3"],
    "project_processor": ["bullet1", "bullet2", "bullet3"],
    "project_analog": ["bullet1", "bullet2", "bullet3"],
    "project_bringup": ["bullet1", "bullet2", "bullet3"]
  }},
  "cover_letter_opening": "One strong opening paragraph for cover letter"
}}"""

    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        text = data["content"][0]["text"]
        # Strip any markdown fences
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️  Claude API error: {e}")
        return None

# ── PDF GENERATION ────────────────────────────────────────────────────────────
def generate_pdf(job, tailored):
    """Generate a styled ATS-friendly PDF resume"""
    company  = re.sub(r'[^\w\s-]', '', job['company']).strip().replace(' ', '_')
    role_str = re.sub(r'[^\w\s-]', '', job['role'])[:40].strip().replace(' ', '_')
    filename = f"resumes/{company}_{role_str}.pdf"
    Path("resumes").mkdir(exist_ok=True)

    score   = tailored.get("ats_score", "N/A")
    summary = tailored.get("summary", "")
    bullets = tailored.get("tailored_bullets", {})
    exp_b   = bullets.get("experience", [])
    fifo_b  = bullets.get("project_fifo", [])
    proc_b  = bullets.get("project_processor", [])
    anlg_b  = bullets.get("project_analog", [])
    bup_b   = bullets.get("project_bringup", [])
    added   = ", ".join(tailored.get("skills_added", []))
    cover   = tailored.get("cover_letter_opening", "")

    def li(items):
        return "".join(f"<li>{i}</li>" for i in items)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<style>
  @page {{ margin: 0.6in; size: letter; }}
  body {{ font-family: 'Arial', sans-serif; font-size: 10.5pt;
         color: #1a1a1a; line-height: 1.45; }}
  h1 {{ font-size: 18pt; color: #1e3a8a; margin: 0 0 2px; }}
  .contact {{ font-size: 9pt; color: #555; margin-bottom: 10px; }}
  .ats-badge {{ display:inline-block; background:#dcfce7; color:#166534;
    padding:2px 10px; border-radius:99px; font-size:9pt; font-weight:bold;
    margin-bottom:8px; }}
  h2 {{ font-size: 11pt; color: #1e3a8a; border-bottom: 1.5px solid #bfdbfe;
       padding-bottom: 2px; margin: 12px 0 4px; text-transform: uppercase;
       letter-spacing: 0.05em; }}
  h3 {{ font-size: 10.5pt; margin: 6px 0 2px; }}
  .meta {{ font-size: 9pt; color: #555; margin-bottom: 3px; }}
  ul {{ margin: 2px 0 6px 16px; padding: 0; }}
  li {{ margin-bottom: 2px; }}
  .summary {{ background: #eff6ff; padding: 8px 10px;
    border-left: 3px solid #2563eb; margin-bottom: 10px;
    font-size: 10pt; border-radius: 3px; }}
  .skills-added {{ font-size: 8.5pt; color: #6b7280; margin-top: 4px; }}
  .cover {{ margin-top: 20px; padding-top: 12px;
    border-top: 1px solid #e5e7eb; font-size: 10pt; }}
  .tailor-note {{ font-size: 8pt; color:#9ca3af; text-align:right; margin-top:8px; }}
</style></head><body>

<h1>Venkata Sri Harshini Boorela</h1>
<div class="contact">
  sriharshiniboorela@gmail.com &nbsp;|&nbsp; +1(617)-922-9643 &nbsp;|&nbsp;
  linkedin.com/in/sriharshini-bv-05092001s &nbsp;|&nbsp; github.com/bvsriharshini
</div>
<div class="ats-badge">✅ ATS Score: {score}% — Tailored for {job['company']} · {job['role']}</div>

<div class="summary">{summary}</div>

<h2>Education</h2>
<h3>M.S. Electrical &amp; Computer Engineering</h3>
<div class="meta">University Name &nbsp;|&nbsp; 2024–2026</div>
<h3>B.S. Electrical Engineering</h3>
<div class="meta">University Name &nbsp;|&nbsp; 2020–2024 &nbsp;|&nbsp; GPA: 3.8/4.0</div>

<h2>Technical Skills</h2>
<p><strong>Languages:</strong> SystemVerilog, Verilog, Python, C, MATLAB, Bash<br/>
<strong>Tools:</strong> Cadence Virtuoso, Synopsys VCS, ModelSim, Vivado, QuestaSim<br/>
<strong>Methodologies:</strong> UVM, Functional Coverage, Constrained Random Verification<br/>
<strong>Hardware:</strong> Zynq-7000, Xilinx FPGA, Oscilloscope, Logic Analyzer, JTAG</p>
{f'<div class="skills-added">+ Keywords added for this role: {added}</div>' if added else ''}

<h2>Experience</h2>
<h3>Hardware Verification Intern — Company Name</h3>
<div class="meta">May 2024 – Aug 2024</div>
<ul>{li(exp_b)}</ul>

<h2>Projects</h2>
<h3>FIFO Design Verification (UVM)</h3>
<ul>{li(fifo_b)}</ul>

<h3>Pipelined RISC-V Processor</h3>
<ul>{li(proc_b)}</ul>

<h3>LDO Regulator &amp; Boost Converter — Cadence Virtuoso</h3>
<ul>{li(anlg_b)}</ul>

<h3>Zynq-7000 Board Bring-up</h3>
<ul>{li(bup_b)}</ul>

<h2>Coursework</h2>
<p>VLSI Design, Digital IC Design, Analog IC Design, Computer Architecture,
Verification Methodology, Embedded Systems, Signal Processing</p>

{f'<div class="cover"><h2>Cover Letter Opening</h2><p>{cover}</p></div>' if cover else ''}

<div class="tailor-note">
  Auto-generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} |
  github.com/bvsriharshini/ECE-jobs
</div>
</body></html>"""

    # Write HTML first, then convert to PDF
    html_path = filename.replace(".pdf", ".html")
    with open(html_path, "w") as f:
        f.write(html)

    # Try WeasyPrint for PDF
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(filename)
        os.remove(html_path)
        print(f"  📄 PDF saved: {filename}")
    except ImportError:
        # Fallback: keep HTML if WeasyPrint not available
        os.rename(html_path, filename.replace(".pdf", ".html"))
        filename = filename.replace(".pdf", ".html")
        print(f"  📄 HTML resume saved: {filename} (install weasyprint for PDF)")

    return filename

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # Load jobs
    if not Path("jobs.json").exists():
        print("❌ jobs.json not found — run filter_jobs.py first")
        return

    with open("jobs.json") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print(f"📋 Total jobs: {len(jobs)}")

    # Only process jobs that don't already have a resume
    new_jobs = [j for j in jobs if not j.get("resume_path")]
    print(f"🆕 New jobs needing tailored resume: {len(new_jobs)}")

    if not new_jobs:
        print("✅ All jobs already have tailored resumes!")
        return

    updated = 0
    for i, job in enumerate(new_jobs):
        print(f"\n[{i+1}/{len(new_jobs)}] Tailoring for {job['company']} — {job['role']}")

        tailored = tailor_resume_with_claude(job)
        if not tailored:
            print("  ⏭️  Skipped (API unavailable)")
            continue

        pdf_path = generate_pdf(job, tailored)

        # Update job record
        for j in jobs:
            if j["company"] == job["company"] and j["role"] == job["role"]:
                j["resume_path"]  = pdf_path
                j["ats_score"]    = tailored.get("ats_score", "N/A")
                j["cover_letter"] = tailored.get("cover_letter_opening", "")
                break

        updated += 1
        time.sleep(1)  # rate limit

    # Save updated jobs.json
    data["jobs"] = jobs
    data["last_tailored"] = datetime.now(timezone.utc).isoformat()
    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Done! Tailored {updated} resumes → saved to /resumes/ folder")

if __name__ == "__main__":
    main()
