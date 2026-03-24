"""
resume_tailor.py — Harshini's ATS Resume Tailor
Rules:
- Filename: Sriharshini_[Company]_[Role].pdf
- Summary: 2-3 lines max, from JD qualifications
- Skills: add JD keywords, NO vague words (fundamentals/familiarity/basics/exposure/knowledge)
- 6 best-matched projects only, ranked by relevance
- Each project/exp: 2-3 bullets, each bullet = 1 line, impact+results+numbers
- Strictly 1 page
- LaTeX format with exact spacing/margins specified
- Flag citizenship/clearance/export control jobs — skip them
- OPT/F1 friendly only
"""

import json, os, re, time, urllib.request, subprocess
from datetime import datetime, timezone
from pathlib import Path

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── ALL 22 PROJECTS (full descriptions for Claude to pick best 6) ─────────────
ALL_PROJECTS = """
1. AXI-Lite Memory Verification (UVM) | May 2025–Jul 2025
   - Constrained random UVM testbench verifying AXI-Lite read/write transactions and protocol handshakes
   - Identified 7 RTL corner-case bugs using SVA assertions and scoreboard comparison
   - Automated Python regression suite cutting debug turnaround by 50%

2. AMBA AHB Protocol Verification (UVM) | Jun 2025–Aug 2025
   - Verified AHB burst, single, split transfers using coverage-driven verification, 100% functional coverage
   - SVA assertions validating HREADY, HRESP, address-phase timing compliance
   - Detected 6 protocol timing violations under randomized stress

3. FIFO Design & SystemVerilog Verification | May 2025–Jul 2025
   - Designed synthesizable 16x8 FIFO with 4-bit pointers and full/empty gating for SOC/ASIC-style RTL
   - Validated 256 memory locations under back-to-back transactions with 60% randomized stimulus
   - Verified pointer wrap and overflow/underflow across 2,000+ transactions with zero mismatches

4. 4x4 Combinational Multiplier Verification (UVM) | May 2025–Jul 2025
   - UVM environment with driver, monitor, scoreboard achieving 100% functional coverage
   - 5,000 constrained random transactions, caught 3 corner-case bugs, cut debug time 45%

5. D Flip-Flop Verification (UVM Configurable Agent) | May 2025–Jun 2025
   - Reusable UVM agent supporting active/passive modes for sequential logic verification
   - 100% toggle and branch coverage; identified setup/hold violation via assertion-based checks

6. Wishbone Memory Verification | Sep 2025–Dec 2025
   - FSM-based Wishbone slave memory in SystemVerilog with protocol-compliant handshaking
   - RTL synthesis and STA validating setup/hold closure under SDC constraints
   - Detected timing violations and handshake errors using SVA and constrained random stimulus

7. FPGA-Based Pipeline Processor (DE1-SoC) | Oct 2024–Dec 2024
   - 5-stage pipelined processor in Verilog with stall detection and data forwarding
   - Reduced CPI from 2.23 to 0.87, improved throughput 143% via hazard mitigation
   - Verified pipeline timing via RTL simulation and waveform debugging in ModelSim

8. QLC NAND SSD Architecture Optimization | Jan 2026–Mar 2026
   - Modeled 16 GB QLC SSD in VSSIM, optimizing channel parallelism to reduce runtime
   - Designed 25% SLC cache hybrid architecture improving write performance and storage efficiency
   - Analyzed MQSim queue depth contention, proposed FTL scheduling for IO fairness

9. Buck Converter PCB Layout (Altium Designer) | Oct 2025–Dec 2025
   - Designed 2-layer buck converter PCB with schematic capture, layout, DRC validation in Altium
   - Solid ground plane, via stitching, EMI layout; delivered fabrication-ready Gerbers and BOM

10. Step-Up DC-DC Boost Regulator (Cadence Virtuoso) | Jan 2024–Apr 2024
    - 2 MHz CMOS boost regulator based on LM2621, 1.2–4V input, 2.5A switch current
    - Multistage OTA compensation for stable closed-loop regulation across -40°C to 125°C
    - Validated line, load, transient stability via SPICE under dynamic conditions

11. VLSI LDO Linear Regulator (Cadence Virtuoso) | Oct 2023–Dec 2023
    - LDO based on TPS786 using folded cascode amplifier and bandgap reference
    - High PSRR, low output noise, fast startup via compensation tuning and bias optimization
    - Verified line/load/transient response from -40°C to 125°C

12. 8x2 SRAM Array (6T Cell, 180nm CMOS) | Jan 2024–Mar 2024
    - Designed 8x2 SRAM with 6T cell, decoders, sense amplifiers, write drivers in 180nm CMOS
    - Verified read stability and write margin across voltage/temperature corners via SPICE

13. MEMS-Based Varactor Fabrication (Cleanroom) | Jan 2025–Mar 2025
    - Fabricated MEMS varactors using S1813 lithography, Al sputtering, ICP RIE, XeF2 release
    - RF S-parameter extraction via VNA; derived kt2, Q factor, motional parameters in MATLAB

14. CNTFET ALU at 32nm | Jan 2023–Mar 2023
    - 8-bit ALU in Cadence using CNTFET, 8 arithmetic/logic ops, 32% lower power vs CMOS at 0.6V
    - Simulated delay, PDP, voltage swing across process corners using SPICE

15. 16-Bit Vedic Multiplier | Jan 2024–Mar 2024
    - Urdhva Tiryakbhyam multiplier in Cadence, 28% propagation delay reduction over array multiplier
    - 18% area reduction via partial product optimization; verified across 10,000 random test vectors

16. High-k Dielectrics for CMOS (XRR) | Jan 2024–May 2024
    - HfO2/ZrO2 gate stacks achieving 50% leakage reduction vs SiO2 baseline
    - Extracted dielectric constant, thickness uniformity via XRR and spectroscopic ellipsometry

17. Ruthenium Thin Films for Interconnects | Sep 2024–Dec 2024
    - ALD optimized for sub-2.5nm Ru films with improved resistivity
    - Characterized via XRR, TEM, XPS, SIMS for nucleation efficiency and uniform growth

18. CNTFET Ultra-Low Voltage Level Shifter (Cadence) | Jan 2023–Mar 2023
    - Ultra-low voltage level shifter using CNTFET for energy-efficient logic level conversion
    - SPICE simulation for delay, power, output swing; compared vs CMOS for energy efficiency

19. MEMS-Based Thin Film Capacitor for RF | Sep 2023–Dec 2023
    - Comb-structured MEMS capacitor for RF impedance tuning; 50% insertion loss reduction
    - Characterized surface morphology and residual stress via SEM and profilometry

20. Valgrind Memory Page Access Analysis | Oct 2024–Dec 2024
    - Traced memory accesses with Valgrind Lackey across Linpack matrix sizes 5–50
    - Python automation computing unique 2KB pages; analyzed memory footprint growth

21. Multithreaded C: Parallel Computation of e^x | Oct 2024–Dec 2024
    - Multithreaded C program for Taylor series with workloads up to 6.4M terms across 1–64 threads
    - Achieved 15.31x speedup, reducing runtime from 0.0779s to 0.00509s

22. Arduino GPS Vehicle Alert System | May 2023–Jul 2023
    - MEMS accelerometer with Arduino detecting impact >3g within 200ms
    - GPS coordinates via GSM, alert delivery under 10 seconds; 25% false trigger reduction

23. Edge AI IoT Optimization | Jan 2024–Apr 2024
    - Lightweight CNN on edge platform reducing inference latency by 35%
    - Model quantization achieving 40% memory reduction with <3% accuracy loss at 1W power budget
"""

# ── CITIZENSHIP/CLEARANCE FLAGS ───────────────────────────────────────────────
CITIZENSHIP_FLAGS = [
    "us citizenship required","must be a us citizen","us citizen only",
    "requires us citizenship","citizen only","clearance required",
    "secret clearance","top secret","ts/sci","security clearance",
    "export control","itar","ear compliance","government clearance",
    "dod clearance","active clearance","usg clearance",
]

def is_citizenship_required(job):
    txt = (job.get("role","") + " " + job.get("company","") + " " +
           job.get("description","")).lower()
    return any(flag in txt for flag in CITIZENSHIP_FLAGS)

# ── CLAUDE API CALL ───────────────────────────────────────────────────────────
def call_claude(prompt):
    if not ANTHROPIC_API_KEY:
        print("  ⚠️  No ANTHROPIC_API_KEY")
        return None
    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 4000,
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
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode())
        text = data["content"][0]["text"]
        text = re.sub(r"```json|```latex|```", "", text).strip()
        return text
    except Exception as e:
        print(f"  ⚠️  Claude API error: {e}")
        return None

# ── STEP 1: GET TAILORING DECISIONS FROM CLAUDE ───────────────────────────────
def get_tailoring_plan(job):
    # Keep prompt concise to avoid token limit errors
    prompt = f"""Expert ATS resume optimizer for ECE/hardware roles.

JOB: {job['company']} | {job['role']} | {job.get('location','')}
JD: {str(job.get('description',''))[:800]}

PROJECTS AVAILABLE (pick best 6 for this job, ranked):
{ALL_PROJECTS}

EXPERIENCE:
1. Research Assistant, Elon University (Oct 2025–Present): Python data pipelines, biomechanics data processing, automation
2. Digital Design Engineer, Community Dreams Foundation (Jul–Oct 2025): Wishbone memory SV, UVM verification, SVA assertions
3. Intern CoreEl Technologies (Jan–Mar 2023): Zynq-7000 RTL verification VCS/ModelSim, TCL/Vivado, AXI PS/PL integration

STRICT RULES:
- Summary: 2-3 lines MAX from JD qualifications. ZERO vague words (no: fundamentals/familiarity/basics/exposure/knowledge of)
- Skills: extract ALL JD keywords. Categories: Verification Languages & Methodologies | Scripting & Automation | Simulation Tools | EDA Tools | Protocols & Architecture | RTL & Design Tools | Certifications
- Pick EXACTLY 6 most relevant projects, best match first
- Each bullet = 1 line, impact+numbers only, 2-3 bullets max per entry
- Must fit 1 page
- citizenship_required: true if job needs US citizenship/clearance/export control/ITAR

Return ONLY valid JSON, no markdown:
{{"ats_score":94,"citizenship_required":false,"summary":"2-3 line summary","skills":{{"verification":"...","scripting":"...","simulation":"...","eda":"...","protocols":"...","rtl":"...","certifications":"..."}},"experience":[{{"title":"Research Assistant, Elon University","date":"Oct 2025 -- Present","bullets":["bullet1","bullet2"]}},{{"title":"Digital Design Engineer, Community Dreams Foundation","date":"Jul 2025 -- Oct 2025","bullets":["bullet1","bullet2"]}},{{"title":"Intern, CoreEl Technologies","date":"Jan 2023 -- Mar 2023","bullets":["bullet1","bullet2"]}}],"projects":[{{"name":"Project Name","date":"Mon Year -- Mon Year","bullets":["b1","b2","b3"]}}],"education":{{"ms_coursework":"...","bs_coursework":"..."}}}}"""

    raw = call_claude(prompt)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠️  JSON parse error: {e}")
        print(f"  Raw: {raw[:300]}")
        return None

# ── STEP 2: GENERATE LATEX ────────────────────────────────────────────────────
def generate_latex(job, plan):
    company  = re.sub(r'[^\w\s]', '', job['company']).strip().replace(' ', '_')
    role_str = re.sub(r'[^\w\s]', '', job['role'])[:40].strip().replace(' ', '_')
    filename = f"resumes/Sriharshini_{company}_{role_str}"

    Path("resumes").mkdir(exist_ok=True)

    def escape(s):
        """Escape LaTeX special characters"""
        s = str(s)
        for old, new in [('&','\\&'),('%','\\%'),('$','\\$'),('#','\\#'),
                         ('^','\\^{}'),('_','\\_'),('~','\\~{}'),
                         ('{','\\{'),( '}','\\}')]:
            s = s.replace(old, new)
        return s

    def bullets(items, max_b=3):
        lines = []
        for b in items[:max_b]:
            lines.append(f"  \\bitem{{{escape(b)}}}")
        return "\n".join(lines)

    sk = plan.get("skills", {})
    exp = plan.get("experience", [])
    projects = plan.get("projects", [])[:6]
    edu = plan.get("education", {})
    summary = escape(plan.get("summary", ""))

    # Build experience blocks
    exp_blocks = ""
    for e in exp:
        exp_blocks += f"""
\\EntryB{{{escape(e['title'])}}}{{{escape(e['date'])}}}
\\blist
{bullets(e.get('bullets',[]))}
\\blistend
"""

    # Build project blocks
    proj_blocks = ""
    for p in projects:
        proj_blocks += f"""
\\EntryB{{{escape(p['name'])}}}{{{escape(p['date'])}}}
\\blist
{bullets(p.get('bullets',[]))}
\\blistend
"""

    latex = f"""%-------------------------
% Sriharshini – {job['company']} {job['role']}
% Auto-generated by ECE Job Board AI Tailor
%-------------------------

\\documentclass[letterpaper,9.5pt]{{article}}

\\usepackage{{titlesec}}
\\usepackage[usenames,dvipsnames]{{color}}
\\usepackage{{enumitem}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{geometry}}
\\usepackage{{mathpazo}}

\\geometry{{top=0.3in, bottom=0.3in, left=0.5in, right=0.5in}}

\\pagestyle{{empty}}
\\raggedbottom
\\setlength{{\\tabcolsep}}{{0in}}
\\setlength{{\\parindent}}{{0pt}}

\\titleformat{{\\section}}{{
  \\vspace{{-7pt}}\\scshape\\bfseries\\fontsize{{12}}{{14}}\\selectfont
}}{{}}{{0em}}{{}}[\\color{{black}}\\titlerule\\vspace{{-3pt}}]

\\newcommand{{\\EntryA}}[4]{{%
  \\vspace{{1pt}}%
  \\begin{{tabular*}}{{\\textwidth}}{{l@{{\\extracolsep{{\\fill}}}}r}}
    \\textbf{{\\small #1}} & \\small #2 \\\\
    \\textit{{\\small #3}} & \\textit{{\\small #4}} \\\\
  \\end{{tabular*}}%
  \\vspace{{1pt}}%
}}

\\newcommand{{\\EntryB}}[2]{{%
  \\vspace{{1pt}}%
  \\begin{{tabular*}}{{\\textwidth}}{{l@{{\\extracolsep{{\\fill}}}}r}}
    \\textbf{{\\small #1}} & \\small #2 \\\\
  \\end{{tabular*}}%
  \\vspace{{1pt}}%
}}

\\newcommand{{\\blist}}{{%
  \\begin{{itemize}}[leftmargin=0.15in, itemsep=-1pt, topsep=0pt, parsep=0pt, partopsep=0pt]%
}}
\\newcommand{{\\blistend}}{{\\end{{itemize}}\\vspace{{0pt}}}}
\\newcommand{{\\bitem}}[1]{{\\item[\\textbullet] \\small #1}}

%===========================================
\\begin{{document}}
\\hyphenpenalty=10000
\\exhyphenpenalty=10000

%---------- HEADING ----------
\\begin{{center}}
  {{\\fontsize{{22}}{{18}}\\selectfont\\textbf{{VENKATA SRI HARSHINI BOORELA}}}}\\\\[3pt]
  \\small +1(617)-922-9643 \\;$|$\\;
  \\href{{mailto:sriharshiniboorela@gmail.com}}{{sriharshiniboorela@gmail.com}} \\;$|$\\;
  \\href{{https://www.linkedin.com/in/sriharshini-bv-05092001s/}}{{linkedin.com/in/sriharshini-bv-05092001s}}
\\end{{center}}
\\vspace{{-18pt}}

%---------- SUMMARY ----------
\\section{{SUMMARY}}
\\vspace{{-1pt}}
{{\\small {summary}}}
\\vspace{{-7pt}}

%---------- EDUCATION ----------
\\section{{EDUCATION}}
\\vspace{{-6pt}}
\\EntryA{{Northeastern University}}{{Boston, MA}}
       {{Master of Science, Electrical and Computer Engineering \\textnormal{{(GPA: 3.5/4)}}}}{{Sep 2023 -- May 2025}}
\\blist
\\vspace{{-2pt}}
  \\bitem{{Coursework: {escape(edu.get('ms_coursework','VLSI Design, Analog IC Design, Solid State Devices, Power Management IC'))}}}
\\blistend
\\vspace{{-2pt}}
\\EntryA{{Jawaharlal Nehru Technological University}}{{Vizianagaram, Andhra Pradesh}}
       {{Bachelor of Technology, Electronics and Communication Engineering \\textnormal{{(GPA: 3.7/4)}}}}{{Aug 2019 -- May 2023}}
\\blist
\\vspace{{-2pt}}
  \\bitem{{Coursework: {escape(edu.get('bs_coursework','Electronic Devices, Digital Electronics, Digital IC Design, Verilog HDL'))}}}
\\blistend
\\vspace{{-4pt}}

%---------- TECHNICAL SKILLS ----------
\\section{{TECHNICAL SKILLS}}
\\vspace{{-2pt}}
\\begin{{itemize}}[leftmargin=0.18in, itemsep=0pt, topsep=0pt, parsep=0pt, partopsep=0pt]
  \\item[\\textbullet] \\small\\textbf{{Verification Languages \\& Methodologies:}} {escape(sk.get('verification','SystemVerilog, UVM, Constrained Random Verification, Coverage-Driven Verification, SVA'))}
  \\item[\\textbullet] \\small\\textbf{{Scripting \\& Automation:}} {escape(sk.get('scripting','Python, TCL, Perl, Bash, Linux, C'))}
  \\item[\\textbullet] \\small\\textbf{{Simulation Tools:}} {escape(sk.get('simulation','VCS, Incisive, QuestaSim, ModelSim'))}
  \\item[\\textbullet] \\small\\textbf{{EDA Tools:}} {escape(sk.get('eda','Cadence Virtuoso, Synopsys VCS, Vivado, Altium Designer'))}
  \\item[\\textbullet] \\small\\textbf{{Protocols \\& Architecture:}} {escape(sk.get('protocols','AXI, AHB, APB, PCIe, Wishbone, FSM design, pipelining'))}
  \\item[\\textbullet] \\small\\textbf{{RTL \\& Design Tools:}} {escape(sk.get('rtl','Verilog, Vivado, Quartus Prime, synthesis, static timing analysis'))}
  \\item[\\textbullet] \\small\\textbf{{Certifications:}} {escape(sk.get('certifications','Verification using SystemVerilog and UVM, VSD Physical Design Flow, VSD Static Timing Analysis'))}
\\end{{itemize}}
\\vspace{{-10pt}}

%---------- EXPERIENCE ----------
\\vspace{{4pt}}
\\section{{EXPERIENCE}}
\\vspace{{-6pt}}
{exp_blocks}
\\vspace{{-10pt}}

%---------- ACADEMIC PROJECTS ----------
\\vspace{{4pt}}
\\section{{ACADEMIC PROJECTS}}
\\vspace{{-6pt}}
{proj_blocks}

\\end{{document}}
"""

    # Save .tex file
    tex_path = filename + ".tex"
    with open(tex_path, "w") as f:
        f.write(latex)
    print(f"  📝 LaTeX saved: {tex_path}")

    # Try to compile to PDF using pdflatex
    pdf_path = filename + ".pdf"
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory=resumes", tex_path],
            capture_output=True, text=True, timeout=60
        )
        # Run twice for proper rendering
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory=resumes", tex_path],
            capture_output=True, text=True, timeout=60
        )
        if Path(pdf_path).exists():
            print(f"  📄 PDF generated: {pdf_path}")
            # Clean up aux files
            for ext in [".aux", ".log", ".out"]:
                try: os.remove(filename + ext)
                except: pass
            return pdf_path
        else:
            print(f"  ⚠️  PDF not generated, keeping .tex file")
            return tex_path
    except FileNotFoundError:
        print("  ⚠️  pdflatex not found — saving .tex only (install texlive)")
        return tex_path
    except Exception as e:
        print(f"  ⚠️  PDF compile error: {e}")
        return tex_path

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not Path("jobs.json").exists():
        print("❌ jobs.json not found — run filter_jobs.py first")
        return

    with open("jobs.json") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])

    # Only tailor ECE-relevant jobs, skip QA/unrelated roles
    ECE_CATS = ["DV","Analog","FPGA","ASIC","HW","SW"]
    SKIP_ROLES = ["qa analyst","quality assurance","qa engineer trainee",
                  "qa trainee","jr. qa","junior qa","scrum master",
                  "project manager","business analyst","data analyst",
                  "marketing","sales","recruiter","hr "]

    def is_relevant(j):
        role = j.get("role","").lower()
        if any(s in role for s in SKIP_ROLES): return False
        if j.get("cat") not in ECE_CATS: return False
        return True

    new_jobs = [j for j in jobs
                if not j.get("resume_path") and is_relevant(j)]

    # Limit to 50 most recent to avoid long runs
    new_jobs = new_jobs[:50]

    print(f"📋 Total jobs: {len(jobs)}")
    print(f"🎯 ECE-relevant new jobs to tailor: {len(new_jobs)}")
    print(f"⏭️  Skipping non-ECE/QA/unrelated roles automatically")

    skipped_citizenship = 0
    updated = 0

    for i, job in enumerate(new_jobs):
        print(f"\n[{i+1}/{len(new_jobs)}] {job['company']} — {job['role']}")

        # Flag citizenship/clearance required jobs
        if is_citizenship_required(job):
            print(f"  🚫 SKIPPED — citizenship/clearance/export control required")
            for j in jobs:
                if j["company"]==job["company"] and j["role"]==job["role"]:
                    j["citizenship_required"] = True
                    j["skipped_reason"] = "citizenship/clearance/export control required"
            skipped_citizenship += 1
            continue

        # Get tailoring plan from Claude
        plan = get_tailoring_plan(job)
        if not plan:
            print("  ⏭️  Skipped (AI unavailable)")
            continue

        # Double-check if Claude flagged citizenship requirement
        if plan.get("citizenship_required"):
            print(f"  🚫 SKIPPED — Claude flagged citizenship required in JD")
            for j in jobs:
                if j["company"]==job["company"] and j["role"]==job["role"]:
                    j["citizenship_required"] = True
            skipped_citizenship += 1
            continue

        # Generate LaTeX + PDF
        file_path = generate_latex(job, plan)

        # Update job record
        for j in jobs:
            if j["company"]==job["company"] and j["role"]==job["role"]:
                j["resume_path"]      = file_path
                j["ats_score"]        = plan.get("ats_score", "N/A")
                j["citizenship_required"] = False
                break

        updated += 1
        time.sleep(1.5)  # rate limit

    # Save updated jobs.json
    data["jobs"] = jobs
    data["last_tailored"] = datetime.now(timezone.utc).isoformat()
    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Done!")
    print(f"   Tailored:  {updated} resumes")
    print(f"   Skipped:   {skipped_citizenship} (citizenship/clearance required)")
    print(f"   Saved to:  /resumes/Sriharshini_[Company]_[Role].pdf")

if __name__ == "__main__":
    main()
