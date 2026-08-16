"""
One-off script applying the 2026-08-15 job-description research sweep
(Anduril, Rocket Lab, Impulse Space, SpaceX, Blue Origin, Boeing, Hadrian)
to the keyword database: adds newly-observed terms and upgrades existing
terms' source_confidence to "C" with real citations, wherever the sweep
actually confirmed them in a live posting.

Run once: venv\\Scripts\\python.exe scripts\\apply_jd_sweep.py
Safe to re-run (idempotent -- checks for existing terms by name before adding).
"""
from __future__ import annotations

import json
from pathlib import Path

KB = Path(__file__).resolve().parent.parent / "app" / "knowledge_base" / "keywords"
DATE = "2026-08-15"


def src(company, role, url):
    return {"company": company, "role_title": role, "url": url, "date_accessed": DATE}


def load(name):
    with open(KB / name, "r", encoding="utf-8") as f:
        return json.load(f)


def save(name, data):
    with open(KB / name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def upsert_term(data, term_name, abbreviations=None, synonyms=None, sources=None):
    """Adds a new term, or if term_name already exists, merges sources onto
    it and upgrades source_confidence to C. Idempotent on re-run."""
    for t in data["terms"]:
        if t["term"].lower() == term_name.lower():
            existing_sources = t.get("sources", [])
            existing_urls = {s["url"] for s in existing_sources}
            for s in sources or []:
                if s["url"] not in existing_urls:
                    existing_sources.append(s)
            t["sources"] = existing_sources
            t["source_confidence"] = "C"
            return
    data["terms"].append(
        {
            "term": term_name,
            "abbreviations": abbreviations or [],
            "synonyms": synonyms or [],
            "source_confidence": "C",
            "sources": sources or [],
        }
    )


# ---------------------------------------------------------------------------
# manufacturing_quality.json
# ---------------------------------------------------------------------------
mq = load("manufacturing_quality.json")

upsert_term(mq, "AS9100", sources=[
    src("Hadrian", "Manufacturing Engineer, Production", "https://builtin.com/job/manufacturing-engineer-production/7830562"),
    src("Rocket Lab", "Manager, Mechanical Engineering", "https://job-boards.greenhouse.io/rocketlab/jobs/7782679003"),
    src("Blue Origin", "Launch Ops Manufacturing Engineers", "https://builtin.com/job/launch-ops-manufacturing-engineers-all-levels-all-shifts/8114719"),
])
upsert_term(mq, "Failure modes and effects analysis", sources=[
    src("Boeing", "Experienced Systems Engineer", "https://builtin.com/job/experienced-systems-engineer/10699253"),
])
upsert_term(mq, "New product introduction", sources=[
    src("Hadrian", "Quality Engineer, NPI", "https://builtin.com/job/quality-engineer-npi/10675432"),
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
    src("Anduril", "Senior Manager, Manufacturing Engineering, Space", "https://job-boards.greenhouse.io/andurilindustries/jobs/5083648007"),
])
upsert_term(mq, "Six Sigma", sources=[
    src("Hadrian", "Quality Engineer, NPI", "https://builtin.com/job/quality-engineer-npi/10675432"),
    src("Boeing", "Experienced Supplier Program Manager", "https://builtin.com/job/experienced-supplier-program-manager-strategic-sourcing-supplier-development/10699257"),
])
upsert_term(mq, "Geometric Dimensioning and Tolerancing", abbreviations=["GD&T"], sources=[
    src("Hadrian", "Manufacturing Engineer, Production", "https://builtin.com/job/manufacturing-engineer-production/7830562"),
    src("Rocket Lab", "Manager, Mechanical Engineering", "https://job-boards.greenhouse.io/rocketlab/jobs/7782679003"),
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
])
upsert_term(mq, "Production Part Approval Process", abbreviations=["PPAP"], sources=[
    src("Hadrian", "Manufacturing Engineer, Production", "https://builtin.com/job/manufacturing-engineer-production/7830562"),
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
])
upsert_term(mq, "Advanced Product Quality Planning", abbreviations=["APQP"], sources=[
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
])
upsert_term(mq, "First Article Inspection Report", abbreviations=["FAIR"], sources=[
    src("Hadrian", "Manufacturing Engineer, Production", "https://builtin.com/job/manufacturing-engineer-production/7830562"),
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
])
upsert_term(mq, "8D problem solving", abbreviations=["8D"], sources=[
    src("SpaceX", "Supplier Development Engineer (Mechanical)", "https://builtin.com/job/supplier-development-engineer-mechanical-engineering/10695748"),
])
upsert_term(mq, "Poka-yoke", synonyms=["error-proofing", "mistake-proofing"], sources=[
    src("SpaceX", "Manufacturing Build Engineer (Starship)", "https://www.themuse.com/jobs/spacex/manufacturing-build-engineer-starship"),
])
upsert_term(mq, "Design for Manufacturability and Assembly", abbreviations=["DFMA", "DFM"], sources=[
    src("Anduril", "Senior Manager, Manufacturing Engineering, Space", "https://job-boards.greenhouse.io/andurilindustries/jobs/5083648007"),
    src("SpaceX", "Manufacturing Build Engineer (Starship)", "https://www.themuse.com/jobs/spacex/manufacturing-build-engineer-starship"),
    src("Hadrian", "Quality Engineer, NPI", "https://builtin.com/job/quality-engineer-npi/10675432"),
])
upsert_term(mq, "Should-cost analysis", sources=[
    src("Rocket Lab", "Senior Global Supply Manager I - PCBA", "https://builtin.com/job/senior-global-supply-manager-i/10557822"),
])
upsert_term(mq, "APICS certification", sources=[
    src("Rocket Lab", "Senior Global Supply Manager I - PCBA", "https://builtin.com/job/senior-global-supply-manager-i/10557822"),
])
upsert_term(mq, "Manufacturing Execution System", abbreviations=["MES"], sources=[
    src("Anduril", "Senior Manager, Manufacturing Engineering, Space", "https://job-boards.greenhouse.io/andurilindustries/jobs/5083648007"),
])
save("manufacturing_quality.json", mq)

# ---------------------------------------------------------------------------
# systems_engineering_certification.json
# ---------------------------------------------------------------------------
se = load("systems_engineering_certification.json")

upsert_term(se, "Interface control document", abbreviations=["ICD"], sources=[
    src("Blue Origin", "Systems Engineer Integration and Testing", "https://builtin.com/job/systems-engineer-integration-and-testing/10271577"),
])
upsert_term(se, "Fault tree analysis", abbreviations=["FTA"], sources=[
    src("Boeing", "Experienced Systems Engineer", "https://builtin.com/job/experienced-systems-engineer/10699253"),
])
upsert_term(se, "Model-based systems engineering", sources=[
    src("Boeing", "Systems Engineer (Experienced or Lead)", "https://jobs.boeing.com/job/huntsville/systems-engineer-experienced-or-lead/185/92218285648"),
])
upsert_term(se, "MIL-STD-882E", synonyms=["system safety standard"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
])
upsert_term(se, "MIL-HDBK-516C", synonyms=["airworthiness certification criteria"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
    src("Boeing", "Aircraft Stability & Control Engineer", "https://builtin.com/job/aircraft-stability-control-engineer/10387516"),
])
upsert_term(se, "ARP-4754A", synonyms=["development of civil aircraft and systems"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
])
upsert_term(se, "ARP-4761", synonyms=["safety assessment process"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
])
upsert_term(se, "SysML", synonyms=["systems modeling language"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
])
upsert_term(se, "Cameo MagicDraw", synonyms=["MBSE modeling tool"], sources=[
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
    src("Boeing", "Systems Engineer (Experienced or Lead)", "https://jobs.boeing.com/job/huntsville/systems-engineer-experienced-or-lead/185/92218285648"),
])
upsert_term(se, "Hardware-in-the-loop testing", abbreviations=["HIL", "HITL"], sources=[
    src("Anduril", "Manufacturing Test Engineer, Fury", "https://job-boards.greenhouse.io/andurilindustries/jobs/4862526007"),
    src("Impulse Space", "Senior GNC Engineer (Propulsive Controls)", "https://builtin.com/job/senior-gnc-engineer-propulsive-controls/10224372"),
])
upsert_term(se, "Software-in-the-loop testing", abbreviations=["SITL"], sources=[
    src("Impulse Space", "Senior GNC Engineer (Propulsive Controls)", "https://builtin.com/job/senior-gnc-engineer-propulsive-controls/10224372"),
])
upsert_term(se, "Reliability modeling", sources=[
    src("Boeing", "Experienced Systems Engineer", "https://builtin.com/job/experienced-systems-engineer/10699253"),
])
upsert_term(se, "Requirements traceability", sources=[
    src("Boeing", "Experienced Systems Engineer", "https://builtin.com/job/experienced-systems-engineer/10699253"),
    src("Anduril", "Principal Systems Engineer, Air Vehicle Systems", "https://job-boards.greenhouse.io/andurilindustries/jobs/5174440007"),
])
save("systems_engineering_certification.json", se)

# ---------------------------------------------------------------------------
# program_management.json
# ---------------------------------------------------------------------------
pm = load("program_management.json")

upsert_term(pm, "Integrated master schedule", sources=[
    src("Hadrian", "Master Scheduler", "https://builtin.com/job/master-scheduler/10698723"),
    src("Blue Origin", "Program Manager (S&OP)", "https://builtin.com/job/program-manager/7710841"),
])
upsert_term(pm, "Earned value management", sources=[
    src("Blue Origin", "Program Manager (S&OP)", "https://builtin.com/job/program-manager/7710841"),
])
upsert_term(pm, "Primavera P6", sources=[
    src("Hadrian", "Master Scheduler", "https://builtin.com/job/master-scheduler/10698723"),
])
upsert_term(pm, "Project Management Professional certification", abbreviations=["PMP"], sources=[
    src("Blue Origin", "Program Manager (S&OP)", "https://builtin.com/job/program-manager/7710841"),
])
upsert_term(pm, "Sales and Operations Planning", abbreviations=["S&OP", "SIOP"], sources=[
    src("Blue Origin", "Program Manager (S&OP)", "https://builtin.com/job/program-manager/7710841"),
])
upsert_term(pm, "Program governance", sources=[
    src("Hadrian", "Technical Program Manager, Capabilities", "https://builtin.com/job/technical-program-manager-faas/8710513"),
])
upsert_term(pm, "Milestone-driven schedule", synonyms=["logic-linked scheduling"], sources=[
    src("Blue Origin", "Program Manager (S&OP)", "https://builtin.com/job/program-manager/7710841"),
])
upsert_term(pm, "Agile ceremonies", synonyms=["sprint planning", "standups", "retrospectives"], sources=[
    src("Blue Origin", "Systems Engineer Integration and Testing", "https://builtin.com/job/systems-engineer-integration-and-testing/10271577"),
])
upsert_term(pm, "Strategic sourcing", sources=[
    src("Boeing", "Experienced Supplier Program Manager", "https://builtin.com/job/experienced-supplier-program-manager-strategic-sourcing-supplier-development/10699257"),
    src("Rocket Lab", "Senior Global Supply Manager I - PCBA", "https://builtin.com/job/senior-global-supply-manager-i/10557822"),
])
save("program_management.json", pm)

# ---------------------------------------------------------------------------
# aerospace_defense.json
# ---------------------------------------------------------------------------
ad = load("aerospace_defense.json")

upsert_term(ad, "Thrust vector control", abbreviations=["TVC", "TVCA"], sources=[
    src("Impulse Space", "Senior GNC Engineer (Propulsive Controls)", "https://builtin.com/job/senior-gnc-engineer-propulsive-controls/10224372"),
])
upsert_term(ad, "Reaction control system", abbreviations=["RCS"], sources=[
    src("Impulse Space", "Senior GNC Engineer (Propulsive Controls)", "https://builtin.com/job/senior-gnc-engineer-propulsive-controls/10224372"),
])
upsert_term(ad, "Slosh modeling", sources=[
    src("Impulse Space", "Senior GNC Engineer (Propulsive Controls)", "https://builtin.com/job/senior-gnc-engineer-propulsive-controls/10224372"),
])
upsert_term(ad, "Turbomachinery", sources=[
    src("Impulse Space", "Staff Turbomachinery Engineer", "https://builtin.com/job/staff-turbomachinery-engineer/10567235"),
])
upsert_term(ad, "Combustion devices", sources=[
    src("Rocket Lab", "Senior Combustion Devices Engineer II", "https://builtin.com/job/senior-combustion-devices-engineer-ii-principal-combustion-devices-engineer/3646792"),
])
upsert_term(ad, "Cryogenic ground systems", synonyms=["industrial gases"], sources=[
    src("Impulse Space", "Senior Ground Systems Engineer (Cryogenics & Industrial Gases)", "https://builtin.com/job/senior-ground-systems-engineer-cryogenics-industrial-gases/10224381"),
])
upsert_term(ad, "Aircraft stability and control", abbreviations=["S&C"], sources=[
    src("Boeing", "Aircraft Stability & Control Engineer", "https://builtin.com/job/aircraft-stability-control-engineer/10387516"),
])
save("aerospace_defense.json", ad)

# ---------------------------------------------------------------------------
# tools_systems.json
# ---------------------------------------------------------------------------
ts = load("tools_systems.json")

upsert_term(ts, "LabVIEW", sources=[
    src("Anduril", "Manufacturing Test Engineer, Fury", "https://job-boards.greenhouse.io/andurilindustries/jobs/4862526007"),
    src("Impulse Space", "Test Automation Engineer (Propulsion)", "https://builtin.com/job/test-automation-engineer-propulsion/10528684"),
])
upsert_term(ts, "Power BI", sources=[
    src("Blue Origin", "Sr. Industrial Engineer-Blue Ring", "https://builtin.com/job/sr-industrial-engineer-blue-ring/10697586"),
])
upsert_term(ts, "Databricks", sources=[
    src("Blue Origin", "Sr. Industrial Engineer-Blue Ring", "https://builtin.com/job/sr-industrial-engineer-blue-ring/10697586"),
])
upsert_term(ts, "ANSYS", sources=[
    src("SpaceX", "Propulsion Engineer (Merlin Hardware Development)", "https://builtin.com/job/propulsion-engineer-merlin-hardware-development/10171253"),
])
upsert_term(ts, "Siemens NX", sources=[
    src("SpaceX", "Propulsion Engineer (Merlin Hardware Development)", "https://builtin.com/job/propulsion-engineer-merlin-hardware-development/10171253"),
    src("Impulse Space", "Senior Manufacturing Engineer (Spacecraft Machining)", "https://builtin.com/job/senior-manufacturing-engineer-spacecraft-machining/9902341"),
])
save("tools_systems.json", ts)

print("Applied JD sweep updates to 5 category files.")
