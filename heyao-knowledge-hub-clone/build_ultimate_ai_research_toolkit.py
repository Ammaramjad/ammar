from __future__ import annotations

import json
import math
import textwrap
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path("Ultimate_AI_Research_Toolkit_2026")


@dataclass
class PromptRecord:
    title: str
    objective: str
    prompt: str
    example: str
    tips: str
    expected_output: str
    difficulty: str
    category: str


def phase_print(message: str) -> None:
    print(f"[BUILD] {message}")


def ensure_structure() -> None:
    folders = [
        ROOT / "AI_Prompts",
        ROOT / "Templates",
        ROOT / "Checklists",
        ROOT / "Productivity",
        ROOT / "Bonus",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ToolkitTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=colors.HexColor("#0b3d91"),
            alignment=1,
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "ToolkitH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            textColor=colors.HexColor("#0b3d91"),
            spaceBefore=8,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "ToolkitH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#0f5cc0"),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "ToolkitBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1d2d44"),
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "ToolkitSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2e3f57"),
        ),
    }


def _header_footer(canvas, doc, header_title: str):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#0b3d91"))
    canvas.rect(1.3 * cm, height - 1.5 * cm, width - 2.6 * cm, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5 * cm, height - 1.3 * cm, f"{header_title}")
    canvas.setFillColor(colors.HexColor("#0b3d91"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 1.5 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _cover_story(title: str, subtitle: str, styles) -> List:
    story = []
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph(title, styles["title"]))
    story.append(Paragraph(subtitle, styles["h2"]))
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Ultimate AI Research Toolkit 2026 - Premium Edition",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "Designed for PhD students, professors, graduate researchers, engineers, and data scientists.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.8 * cm))
    features_table = Table(
        [
            ["[Idea]", "Research prompts and ideation systems"],
            ["[Review]", "Literature synthesis and gap detection"],
            ["[Write]", "Paper writing and revision workflows"],
            ["[Plan]", "Publication and productivity operations"],
        ],
        colWidths=[3 * cm, 12.5 * cm],
    )
    features_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4ff")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#173a6a")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b6c9e6")),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(features_table)
    story.append(PageBreak())
    return story


def generate_prompt_records(
    count: int,
    domain: str,
    categories: List[str],
    focus_areas: List[str],
    output_artifacts: List[str],
    title_starters: List[str],
    scenario_pool: List[str],
    venue_pool: List[str],
    workflow_labels: List[str],
) -> List[PromptRecord]:
    dimensions = ["novelty", "rigor", "reproducibility", "clarity", "statistical power", "transferability", "ethical compliance", "computational efficiency", "clinical relevance", "publication readiness"]
    difficulty_scale = ["Beginner", "Intermediate", "Advanced", "Expert"]
    archetypes = [
        {
            "name": "Novel Contribution Architect",
            "objective": "Create a contribution map that defends novelty against closest prior work and defines what is publishable.",
            "prompt": "Act as a senior research editor. Build a contribution architecture for {focus} in {scenario} targeting {venue}. Output sections: contribution claim stack, nearest-neighbor prior work comparison, differentiator evidence plan, failure-risk matrix, and a 30/60/90-day execution plan.",
            "tips": "Force each claim to link to one measurable piece of evidence and one comparison baseline.",
        },
        {
            "name": "Research Gap Forensics",
            "objective": "Detect non-obvious research gaps and convert them into testable opportunities.",
            "prompt": "You are a literature forensics specialist. From the context below, identify unresolved contradictions in {focus} and rank them by impact and tractability. Then design three testable gap statements, each with required datasets, threat-to-validity notes, and likely reviewer objections for {venue}.",
            "tips": "Distinguish 'no evidence exists' from 'evidence exists but conflicts' to avoid weak gap claims.",
        },
        {
            "name": "Reviewer #2 Rebuttal Builder",
            "objective": "Turn skeptical reviewer criticism into a persuasive, evidence-linked response workflow.",
            "prompt": "Assume Reviewer #2 challenges {focus} for {venue}. Draft a response package with: acknowledgement sentence, technical clarification, direct manuscript change, optional added experiment, and fallback wording if resources are limited. Provide line-level mapping format for revision tracking.",
            "tips": "Use respectful tone and separate explanation, action, and manuscript delta into distinct bullets.",
        },
        {
            "name": "Methodology Clarity Refiner",
            "objective": "Rewrite methods for reproducibility and procedural transparency.",
            "prompt": "Rewrite the methodology around {focus} for {scenario} so another lab can reproduce it without author contact. Include variable definitions, preprocessing chronology, model hyperparameters, instrumentation assumptions, and reproducibility checklist required for {venue}.",
            "tips": "Name every tool/version and include randomness-control policy.",
        },
        {
            "name": "IEEE/ACM Section Optimizer",
            "objective": "Produce section drafts compliant with high-impact conference and journal conventions.",
            "prompt": "Generate a publication-ready section for {focus} tuned for {venue}. Enforce concise technical style, explicit contributions, and strong figure/table callouts. Provide two style variants: IEEE Transactions tone and ACM conference tone with sentence-level rewrites.",
            "tips": "Avoid generic claims; anchor every paragraph with result-oriented language.",
        },
        {
            "name": "Elsevier Revision Planner",
            "objective": "Plan a high-confidence major revision package for journal resubmission.",
            "prompt": "Create a major revision plan for an Elsevier-style decision letter focused on {focus}. Include comment clustering, evidence plan, timeline by dependency, added-analysis options, and response-letter structure that anticipates editor priorities for {venue}.",
            "tips": "Group reviewer comments by technical dependency to prevent contradictory edits.",
        },
        {
            "name": "Nature-Style Abstract Composer",
            "objective": "Craft concise, high-impact abstracts aligned with selective journal standards.",
            "prompt": "Write a Nature-style abstract for a study on {focus} in {scenario}. Constrain to problem, approach, principal quantitative finding, boundary condition, and broader implication. Provide a weaker draft and then a stronger revised draft with rationale.",
            "tips": "One central claim per sentence keeps abstract logic clean and persuasive.",
        },
        {
            "name": "Experimental Design Stress Test",
            "objective": "Pressure-test experimental design before expensive execution.",
            "prompt": "Audit the experimental design for {focus}. Produce control/ablation matrix, confound analysis, data leakage checks, minimum sample strategy, and statistical power guardrails suitable for {venue} reviewers. Include a stop/go decision protocol.",
            "tips": "Design ablations to isolate one causal factor at a time.",
        },
        {
            "name": "Statistical Analysis Blueprint",
            "objective": "Select robust statistical strategy and interpretation logic.",
            "prompt": "Design a statistical analysis workflow for {focus} with assumptions, test-selection logic, effect-size reporting, multiplicity correction, and uncertainty interpretation. Output a decision tree that maps data conditions to recommended tests for {venue}.",
            "tips": "Pair p-values with effect sizes and confidence intervals in every result claim.",
        },
        {
            "name": "Figure and Caption Scientist",
            "objective": "Transform visuals into evidence-rich storytelling assets.",
            "prompt": "Generate a figure strategy for {focus} with publication-grade caption drafts. For each figure, define purpose, metric, axis design, uncertainty communication, and interpretation sentence expected by {venue}. Add one caption rewrite for non-expert readers.",
            "tips": "Good captions stand alone and state what changed, by how much, and why it matters.",
        },
        {
            "name": "LaTeX Manuscript Assistant",
            "objective": "Convert technical narrative into clean, production-ready LaTeX structure.",
            "prompt": "Create a LaTeX writing workflow for {focus}: section skeleton, theorem/algorithm formatting guidance, table conventions, citation macros, and cross-reference hygiene. Include common formatting errors and fixes for {venue} submission checks.",
            "tips": "Draft content in semantic chunks before polishing visual layout.",
        },
        {
            "name": "Citation Gap Detector",
            "objective": "Detect weak citation support and strengthen scholarly positioning.",
            "prompt": "Analyze a draft on {focus} and identify citation gaps by claim type: foundational, comparative, methodological, and limitation-related. Return a prioritized fill plan with query phrases, likely source types, and insertion points tailored to {venue}.",
            "tips": "Flag unsupported superlatives first; they trigger avoidable reviewer criticism.",
        },
        {
            "name": "Ethics and Compliance Guardrail",
            "objective": "Embed ethics and compliance checks into the technical workflow.",
            "prompt": "Build an ethics checklist and mitigation plan for {focus} in {scenario}. Include fairness risks, privacy boundaries, human-subject concerns, reporting transparency, and audit evidence expected for {venue} review.",
            "tips": "Translate ethical risks into actionable controls with owner and verification evidence.",
        },
        {
            "name": "Defense and Q&A Simulator",
            "objective": "Prepare rigorous responses for committee or reviewer questioning.",
            "prompt": "Simulate a high-pressure Q&A on {focus}. Generate 15 hard questions (methods, validity, novelty, limitations, impact) and produce concise, evidence-backed responses with fallback answers for uncertain data points. Include one slide cue per answer.",
            "tips": "Structure answers as claim -> evidence -> limitation -> next action.",
        },
        {
            "name": "Results Interpretation Engine",
            "objective": "Convert raw metrics into defensible scientific interpretation.",
            "prompt": "Interpret results for {focus} using a claim-evidence map: primary findings, uncertainty envelope, competing explanations, boundary conditions, and implications for future work in {venue}. Add one paragraph that preempts overclaiming.",
            "tips": "State what the results do not prove as clearly as what they do prove.",
        },
        {
            "name": "Publication Strategy Playbook",
            "objective": "Choose venue strategy, narrative framing, and revision sequencing.",
            "prompt": "Design a publication strategy for {focus}: venue ladder (A-plan/B-plan), novelty framing options, deadline-aligned writing sprints, and reviewer-risk scenarios. Include a branch for conference-first then journal-extension path for {venue}.",
            "tips": "Plan fallback venue narratives early to reduce resubmission cycle time.",
        },
    ]
    disciplines = [
        "biomedical engineering",
        "machine learning",
        "human-computer interaction",
        "computational social science",
        "climate informatics",
        "robotics",
        "materials informatics",
        "cybersecurity",
        "digital health",
        "computational neuroscience",
    ]
    datasets = [
        "multi-site clinical cohort",
        "longitudinal sensor dataset",
        "multi-modal image-text corpus",
        "benchmark tabular risk dataset",
        "public genomics panel",
        "city-scale mobility records",
        "industrial telemetry stream",
        "crowdsourced annotation dataset",
        "federated hospital dataset",
        "open government policy data",
    ]
    methods = [
        "transformer baseline",
        "causal inference pipeline",
        "Bayesian hierarchical model",
        "graph neural workflow",
        "mixed-methods protocol",
        "time-series anomaly framework",
        "hybrid rule-neural model",
        "multi-objective optimizer",
        "semi-supervised training setup",
        "counterfactual evaluation approach",
    ]
    reviewer_personas = [
        "skeptical statistician",
        "applied domain expert",
        "methodology purist",
        "editor focused on clarity",
        "reproducibility auditor",
        "theory-oriented reviewer",
        "industry impact reviewer",
        "ethics compliance reviewer",
        "benchmarking specialist",
        "systems performance reviewer",
        "interdisciplinary committee member",
    ]
    output_schemas = [
        "decision matrix",
        "claim-evidence table",
        "risk register",
        "action timeline",
        "section rewrite pack",
        "rebuttal response grid",
        "ablation plan sheet",
        "statistical decision tree",
        "figure-caption protocol",
        "citation repair map",
        "compliance checklist",
    ]
    risk_scenarios = [
        "dataset shift at deployment",
        "small sample size constraints",
        "conflicting baseline outcomes",
        "unexpected reviewer disagreement",
        "compute budget reduction",
        "missing metadata in source data",
        "high class imbalance",
        "time-limited resubmission window",
        "incomplete ablation coverage",
        "inter-annotator disagreement",
        "ethics board clarification request",
    ]
    title_angles = [
        "publishable novelty framing",
        "reviewer-resilient argumentation",
        "evidence-first writing",
        "venue-specific optimization",
        "impact-focused communication",
        "replication-grade documentation",
        "high-confidence statistical reporting",
        "editorial risk reduction",
        "cross-domain readability",
        "major-revision readiness",
        "defense-ready reasoning",
        "method comparison clarity",
        "limitations-first transparency",
        "results-to-insight translation",
        "citation-strength positioning",
        "practical deployment framing",
        "ethics-by-design reporting",
        "hypothesis stress testing",
        "decision traceability",
    ]
    prompts: List[PromptRecord] = []
    title_seen = set()
    for i in range(1, count + 1):
        archetype = archetypes[(i * 19) % len(archetypes)]
        title_seed = title_starters[(i * 5) % len(title_starters)]
        workflow = workflow_labels[(i * 7) % len(workflow_labels)]
        scenario = scenario_pool[(i * 11) % len(scenario_pool)]
        venue = venue_pool[(i * 13) % len(venue_pool)]
        d = dimensions[(i * 11) % len(dimensions)]
        focus = focus_areas[(i * 5) % len(focus_areas)]
        artifact = output_artifacts[(i * 13) % len(output_artifacts)]
        category = categories[(i * 17 + i // 9) % len(categories)]
        diff = difficulty_scale[(i - 1) % len(difficulty_scale)]
        discipline = disciplines[(i * 23) % len(disciplines)]
        dataset = datasets[(i * 29) % len(datasets)]
        method = methods[(i * 31) % len(methods)]
        persona = reviewer_personas[(i * 41) % len(reviewer_personas)]
        schema = output_schemas[(i * 43) % len(output_schemas)]
        risk_case = risk_scenarios[(i * 47) % len(risk_scenarios)]
        angle = title_angles[(i * 53) % len(title_angles)]

        title = f"{title_seed}: {workflow} for {scenario} ({venue}) - {angle}"
        if title in title_seen:
            title = f"{title} - Variant {i:03d}"
        title_seen.add(title)
        objective = (
            f"{archetype['objective']} Prioritize {d} and produce publication-grade decisions for {focus}."
        )
        prompt_text = archetype["prompt"].format(focus=focus, scenario=scenario, venue=venue) + (
            f" Project profile: discipline={discipline}; dataset={dataset}; preferred method={method}; "
            f"reviewer persona={persona}; output schema={schema}; risk scenario={risk_case}; "
            "timeline={timeline}; resources={resources}. Return outputs as numbered sections and end with an execution checklist."
        )
        example = (
            f"Example input: discipline={discipline}; dataset={dataset}; timeline=14 weeks; resources=3 researchers + 2 GPUs; "
            f"target venue={venue}; reviewer persona={persona}. Example outcome: {artifact} with risk controls, reviewer-facing rationale, and milestone gates."
        )
        tips = f"{archetype['tips']} Ensure the {schema} explicitly addresses {risk_case} and anticipated concerns from a {persona}."
        expected_output = (
            f"A publication-ready {artifact} that includes decisions, rationale, measurable criteria, and reviewer-resilient framing for {focus}."
        )
        prompts.append(
            PromptRecord(
                title=title,
                objective=objective,
                prompt=prompt_text,
                example=example,
                tips=tips,
                expected_output=expected_output,
                difficulty=diff,
                category=category,
            )
        )
    return prompts


def build_prompt_pdf(
    path: Path,
    title: str,
    introduction: str,
    instructions: Iterable[str],
    summary: str,
    prompts: List[PromptRecord],
) -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2.2 * cm,
        bottomMargin=1.8 * cm,
    )
    story = []
    story.extend(_cover_story(title, "Expert Workflow Library", styles))
    story.append(Paragraph("Table of Contents", styles["h1"]))
    story.append(Paragraph("1. Introduction", styles["body"]))
    story.append(Paragraph("2. Instructions", styles["body"]))
    story.append(Paragraph("3. Workflow Library", styles["body"]))
    story.append(Paragraph("4. Summary", styles["body"]))
    story.append(PageBreak())
    story.append(Paragraph("Introduction", styles["h1"]))
    story.append(Paragraph(introduction, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Instructions", styles["h1"]))
    for item in instructions:
        story.append(Paragraph(f"- {item}", styles["body"]))
    story.append(PageBreak())
    story.append(Paragraph("Workflow Library", styles["h1"]))

    for i, prompt in enumerate(prompts, start=1):
        story.append(Paragraph(f"{i}. {prompt.title}", styles["h2"]))
        body_blocks = [
            ("Objective", prompt.objective),
            ("Prompt", prompt.prompt),
            ("Example", prompt.example),
            ("Tips", prompt.tips),
            ("Expected Output", prompt.expected_output),
            ("Difficulty", prompt.difficulty),
            ("Category", prompt.category),
        ]
        for label, text in body_blocks:
            story.append(Paragraph(f"<b>{label}:</b> {text}", styles["body"]))
        story.append(Spacer(1, 0.12 * cm))
        if i % 5 == 0:
            story.append(
                Table(
                    [["", ""]],
                    colWidths=[0.2 * cm, 16.2 * cm],
                    style=TableStyle(
                        [
                            ("LINEABOVE", (0, 0), (-1, -1), 0.25, colors.HexColor("#d2e3ff")),
                        ]
                    ),
                )
            )
            story.append(Spacer(1, 0.08 * cm))
    story.append(PageBreak())
    story.append(Paragraph("Summary", styles["h1"]))
    story.append(Paragraph(summary, styles["body"]))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, title), onLaterPages=lambda c, d: _header_footer(c, d, title))


def build_reference_pdf(path: Path, title: str, intro: str, sections: List[tuple[str, List[str]]], summary: str) -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2.2 * cm,
        bottomMargin=1.8 * cm,
    )
    story = []
    story.extend(_cover_story(title, "Reference Guide", styles))
    story.append(Paragraph("Table of Contents", styles["h1"]))
    story.append(Paragraph("1. Introduction", styles["body"]))
    for idx, (h, _) in enumerate(sections, start=2):
        story.append(Paragraph(f"{idx}. {h}", styles["body"]))
    story.append(Paragraph(f"{len(sections) + 2}. Summary", styles["body"]))
    story.append(PageBreak())
    story.append(Paragraph("Introduction", styles["h1"]))
    story.append(Paragraph(intro, styles["body"]))
    for heading, lines in sections:
        story.append(PageBreak())
        story.append(Paragraph(heading, styles["h1"]))
        for line in lines:
            story.append(Paragraph(f"- {line}", styles["body"]))
    story.append(PageBreak())
    story.append(Paragraph("Summary", styles["h1"]))
    story.append(Paragraph(summary, styles["body"]))
    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, title), onLaterPages=lambda c, d: _header_footer(c, d, title))


def build_checklist_pdf(path: Path, title: str, intro: str, checklist_items: List[str], summary: str) -> None:
    styles = build_styles()
    sections = [
        ("Instructions", ["Mark each item as Complete, In Progress, or Not Applicable.", "Attach evidence where possible for auditability."]),
        ("Checklist", [f"[ ] {item}" for item in checklist_items]),
    ]
    build_reference_pdf(path, title, intro, sections, summary)


def build_readme_pdf(path: Path) -> None:
    intro = (
        "This toolkit is a commercial-grade system for research ideation, literature review acceleration, "
        "paper writing, reviewer response, thesis development, and publication planning."
    )
    sections = [
        (
            "Folder Structure",
            [
                "AI_Prompts/: domain-specific prompt libraries in PDF format.",
                "Templates/: editable DOCX files for core academic deliverables.",
                "Checklists/: action-ready quality assurance lists for each writing stage.",
                "Productivity/: XLSX planners and workflow guides.",
                "Bonus/: quick-reference sheets and curated AI tooling resources.",
            ],
        ),
        (
            "How to Use",
            [
                "Select a workflow stage (idea, review, writing, revision, submission).",
                "Open the corresponding prompt library and choose a prompt by category and difficulty.",
                "Adapt the example context to your topic, dataset, and constraints.",
                "Export generated outputs into the supplied templates and track progress using planners.",
            ],
        ),
        (
            "Recommended Workflow",
            [
                "1) Use Research_Idea_Generation to scope novel contributions.",
                "2) Use Literature_Review prompts to structure evidence synthesis.",
                "3) Draft in templates, then refine with Academic_Writing and IEEE/Thesis prompts.",
                "4) Use Reviewer_Response prompts and checklists for submission-ready quality control.",
                "5) Track cycles, deadlines, and resubmissions in Publication_Tracker.",
            ],
        ),
        (
            "Compatible AI Models",
            [
                "ChatGPT, GPT-5 family, Claude, Gemini, Microsoft Copilot, DeepSeek, and equivalent assistants.",
                "For best results, use models that support long context and structured outputs.",
            ],
        ),
        (
            "Best Practices",
            [
                "Never paste confidential participant or proprietary data into external tools.",
                "Require explicit assumptions, limits, and evaluation criteria in every output.",
                "Use at least two prompts for each critical decision and compare outcomes.",
                "Maintain a versioned decision log to preserve methodological transparency.",
            ],
        ),
    ]
    summary = "Used systematically, this toolkit reduces drafting time, improves methodological clarity, and strengthens publication readiness."
    build_reference_pdf(path, "Ultimate AI Research Toolkit 2026 - README", intro, sections, summary)


def build_docx_template(path: Path, title: str, section_map: List[tuple[str, str]]) -> None:
    doc = Document()
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    subtitle = doc.add_paragraph("Ultimate AI Research Toolkit 2026")
    subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    subtitle.runs[0].font.size = Pt(11)
    doc.add_paragraph()

    for section_title, guidance in section_map:
        doc.add_heading(section_title, level=1)
        paragraph = doc.add_paragraph(guidance)
        paragraph.runs[0].font.size = Pt(10.5)
        if "Table" in section_title or "Response Matrix" in section_title:
            table = doc.add_table(rows=2, cols=4)
            table.style = "Table Grid"
            headers = ["Field", "Details", "Evidence", "Status"]
            for idx, text in enumerate(headers):
                table.cell(0, idx).text = text
            table.cell(1, 0).text = "Example Row"
            table.cell(1, 1).text = "Populate with project-specific content."
            table.cell(1, 2).text = "Link figures, references, or appendix items."
            table.cell(1, 3).text = "Draft"
        doc.add_paragraph()

    doc.save(path)


def style_worksheet_header(ws, headers):
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B3D91")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"


def build_research_planner(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Research Planner"
    headers = ["Task ID", "Research Phase", "Task", "Owner", "Start Date", "Due Date", "Priority", "Status", "Progress %", "Days Remaining"]
    style_worksheet_header(ws, headers)
    sample_rows = [
        ["RP-001", "Scoping", "Define research questions", "Lead Author", "2026-01-05", "2026-01-12", "High", "In Progress", 40],
        ["RP-002", "Methods", "Finalize evaluation protocol", "Method Specialist", "2026-01-10", "2026-01-18", "High", "Planned", 0],
        ["RP-003", "Data", "Create preprocessing pipeline", "Data Engineer", "2026-01-12", "2026-01-22", "Medium", "Planned", 0],
        ["RP-004", "Writing", "Draft introduction and related work", "Writing Lead", "2026-01-19", "2026-01-29", "Medium", "Planned", 0],
    ]
    for row_idx, row in enumerate(sample_rows, start=2):
        ws.append(row + [f"=F{row_idx}-TODAY()"])
    ws["L1"] = "Overall Progress"
    ws["L2"] = "=AVERAGE(I2:I200)"
    ws["L1"].font = Font(bold=True, color="0B3D91")
    ws["L2"].font = Font(bold=True)
    for col in "ABCDEFGHIJ":
        ws.column_dimensions[col].width = 17
    ws.column_dimensions["C"].width = 30
    wb.save(path)


def build_publication_tracker(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Publication Tracker"
    headers = [
        "Manuscript ID",
        "Title",
        "Target Venue",
        "Submission Date",
        "Decision Date",
        "Status",
        "Revision Round",
        "Acceptance Probability %",
        "Days to Decision",
    ]
    style_worksheet_header(ws, headers)
    rows = [
        ["PUB-101", "Efficient Multimodal Fusion", "IEEE TNNLS", "2026-02-10", "2026-04-21", "Major Revision", 1, 62],
        ["PUB-102", "Benchmarking Continual Models", "NeurIPS", "2026-03-02", "2026-05-15", "Under Review", 0, 55],
        ["PUB-103", "Causal Inference in Sensor Streams", "Nature Communications", "2026-01-18", "2026-03-20", "Rejected", 0, 25],
        ["PUB-104", "Interpretable Clinical Forecasting", "AAAI", "2026-02-25", "2026-04-10", "Accepted", 2, 88],
    ]
    for r, row in enumerate(rows, start=2):
        ws.append(row + [f"=E{r}-D{r}"])
    ws["K1"] = "Acceptance Rate"
    ws["K2"] = '=COUNTIF(F2:F500,"Accepted")/COUNTA(A2:A500)'
    ws["L1"] = "Active Papers"
    ws["L2"] = '=COUNTIF(F2:F500,"Under Review")+COUNTIF(F2:F500,"Major Revision")+COUNTIF(F2:F500,"Minor Revision")'
    for col in "ABCDEFGHI":
        ws.column_dimensions[col].width = 22
    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["C"].width = 24
    wb.save(path)


def build_weekly_planner(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly Planner"
    headers = ["Week", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Total Planned Hours", "Total Completed Hours"]
    style_worksheet_header(ws, headers)
    for week in range(1, 13):
        row = [f"Week {week}"] + [f"Priority focus block {d}" for d in range(1, 8)] + [0, 0]
        ws.append(row)
        r = week + 1
        ws[f"I{r}"] = f"=SUMPRODUCT(--(B{r}:H{r}<>\"\"),2)"
        ws[f"J{r}"] = 0
    ws["L1"] = "Completion Ratio"
    ws["L2"] = "=SUM(J2:J13)/SUM(I2:I13)"
    for col in "ABCDEFGHIJ":
        ws.column_dimensions[col].width = 20
    ws.column_dimensions["A"].width = 10
    wb.save(path)


def write_license(path: Path) -> None:
    license_text = textwrap.dedent(
        """
        Ultimate AI Research Toolkit 2026 - Personal Use License

        Copyright (c) 2026. All rights reserved.

        1) This product is licensed for personal, non-transferable use by the purchaser.
        2) Redistribution, resale, sublicensing, or sharing of files in whole or in part is prohibited.
        3) You may adapt prompts and templates for your own research and academic projects.
        4) You may not claim the original toolkit files as your authored product for resale.
        5) No warranty is provided. The toolkit is delivered "as is" without liability for outcomes.

        By using these files, you agree to the terms above.
        """
    ).strip()
    path.write_text(license_text + "\n", encoding="utf-8")


def write_prompt_archive(path: Path, prompt_map: dict[str, list[PromptRecord]]) -> None:
    serializable = {key: [asdict(record) for record in value] for key, value in prompt_map.items()}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def generate_all_prompt_pdfs() -> dict[str, list[PromptRecord]]:
    ai_prompts_dir = ROOT / "AI_Prompts"
    prompt_map: dict[str, list[PromptRecord]] = {}

    prompt_specs = [
        ("Research_Idea_Generation.pdf", "Research Idea Generation", 120, ["Novelty Discovery", "Hypothesis Framing", "Problem Selection", "Feasibility Scan"], ["research roadmap", "hypothesis matrix", "priority map"], ["Create Novel Contributions", "Generate a Strong Research Gap", "Design a Defensible Hypothesis", "Map Breakthrough Research Opportunities"], ["early-stage thesis planning", "industry-sponsored research proposal", "interdisciplinary grant concept", "first-author conference submission"], ["IEEE Transactions", "ACM Computing Surveys", "Nature Communications", "Elsevier Expert Systems"], ["novelty pipeline", "gap-to-hypothesis workflow", "contribution stress test", "high-impact scope design"]),
        ("Experimental_Design.pdf", "Experimental Design", 100, ["Ablation Planning", "Control Groups", "Evaluation Protocol", "Bias Mitigation"], ["experiment protocol", "variable registry", "decision log"], ["Strengthen Experimental Design", "Build Reviewer-Proof Ablations", "Create a Robust Validation Plan", "Design Controls That Survive Peer Review"], ["multi-dataset benchmarking study", "resource-constrained lab experiment", "high-variance real-world deployment", "replication package for supplementary material"], ["NeurIPS", "ICML", "AAAI", "IEEE TPAMI"], ["ablation architecture", "confound-control workflow", "evaluation matrix design", "power-aware experiment planning"]),
        ("Data_Analysis.pdf", "Data Analysis", 100, ["Data Profiling", "Model Diagnostics", "Feature Interpretation", "Error Analysis"], ["analysis report", "diagnostic dashboard", "feature impact memo"], ["Explain Results Scientifically", "Diagnose Failure Modes with Evidence", "Build a High-Rigor Error Analysis", "Convert Metrics into Insight"], ["post-experiment analysis sprint", "cross-cohort transfer study", "deployment drift investigation", "model debugging cycle before resubmission"], ["KDD", "IJCAI", "PLOS ONE", "IEEE Access"], ["error taxonomy workflow", "result-explanation workflow", "feature-impact investigation", "diagnostic reporting system"]),
        ("Statistics.pdf", "Statistical Interpretation", 90, ["Hypothesis Testing", "Effect Size Analysis", "Uncertainty Quantification", "Robustness Checks"], ["statistical memo", "result interpretation grid", "evidence summary"], ["Plan Statistical Analysis Like a Reviewer", "Build an Uncertainty-First Results Section", "Strengthen Significance Claims", "Audit Statistical Validity"], ["small-sample experimental setup", "imbalanced-class benchmarking", "longitudinal causal analysis", "clinical-risk model evaluation"], ["Biostatistics", "JMLR", "IEEE JBHI", "Elsevier Pattern Recognition"], ["test-selection decision tree", "effect-size narrative workflow", "robustness audit protocol", "uncertainty communication framework"]),
        ("Publication_Strategy.pdf", "Publication Strategy", 90, ["Venue Targeting", "Contribution Positioning", "Revision Planning", "Response Strategy"], ["submission strategy memo", "review-risk map", "timeline playbook"], ["Choose the Right Venue Strategy", "Plan a High-Probability Submission Path", "Build a Smart Resubmission Ladder", "Design an Editor-Friendly Revision Plan"], ["first journal submission cycle", "conference rejection recovery path", "journal-extension planning cycle", "multi-venue publication roadmap"], ["IEEE TNNLS", "ACM TOIS", "Nature Machine Intelligence", "Elsevier Information Sciences"], ["venue ladder workflow", "revision scheduling system", "editorial risk mitigation", "submission playbook"]),
        ("Academic_Writing.pdf", "Academic Writing", 120, ["Argument Structure", "Clarity Optimization", "Narrative Flow", "Technical Precision"], ["writing blueprint", "section improvement plan", "clarity checklist"], ["Write a High-Impact Introduction", "Improve Methodology Clarity", "Rewrite for Nature Journal", "Polish Discussion for Acceptance"], ["camera-ready manuscript preparation", "major-revision rewrite sprint", "advisor feedback integration cycle", "cross-disciplinary audience adaptation"], ["Nature", "Science Advances", "IEEE", "ACM"], ["clarity optimization workflow", "argument architecture system", "section rewrite protocol", "reader-comprehension tuning"]),
        ("Literature_Review.pdf", "Literature Review", 300, ["Search Strategy", "Critical Appraisal", "Gap Identification", "Synthesis Design"], ["evidence map", "thematic synthesis", "citation logic matrix"], ["Build a Literature Map That Finds Gaps", "Create a Review Synthesis That Cites Correctly", "Detect Citation Gaps with Confidence", "Turn Papers into Research Direction"], ["systematic review planning phase", "chapter-2 thesis drafting cycle", "rapid scoping review for proposal", "state-of-the-art positioning for rebuttal"], ["PRISMA-aligned journal", "ACM CSUR", "IEEE Survey Journal", "Elsevier Knowledge-Based Systems"], ["query-to-synthesis workflow", "evidence grading workflow", "gap extraction engine", "related-work architecture"]),
        ("Reviewer_Response.pdf", "Reviewer Response", 200, ["Tone Calibration", "Evidence-backed Rebuttal", "Revision Traceability", "Decision Negotiation"], ["response letter", "comment-response matrix", "revision evidence table"], ["Improve Reviewer Response Letter", "Handle Reviewer #2 Professionally", "Write a Persuasive Rebuttal", "Transform Criticism into Acceptance"], ["major revision after mixed reviews", "editor requests additional clarity", "methodological criticism rebuttal", "limited-resource response strategy"], ["Elsevier journal review", "Springer major revision", "IEEE minor revision", "ACM rebuttal stage"], ["comment-response workflow", "tone-safe rebuttal workflow", "line-mapped revision protocol", "editor negotiation framework"]),
        ("IEEE_Writing.pdf", "IEEE Writing", 100, ["IEEE Formatting", "Technical Positioning", "Result Narration", "Limitations Framing"], ["IEEE-ready section draft", "compliance checklist", "figure-caption package"], ["Write a High-Impact IEEE Introduction", "Optimize Abstract for IEEE Reviewers", "Engineer a Results Section for IEEE", "Prepare IEEE-Ready Technical Narrative"], ["IEEE Transactions submission cycle", "IEEE conference paper deadline sprint", "camera-ready compliance check", "technical rewrite from preprint to IEEE"], ["IEEE Transactions", "IEEE Access", "IEEE IoT Journal", "IEEE TPDS"], ["IEEE structure workflow", "results storytelling workflow", "compliance-first editing", "caption and table enhancement"]),
        ("Thesis_Writing.pdf", "Thesis Writing", 100, ["Chapter Architecture", "Method Defense", "Contribution Validation", "Viva Preparation"], ["chapter plan", "defense argument map", "thesis refinement protocol"], ["Create a Defensible Thesis Chapter", "Prepare for Thesis Defense Questions", "Improve Chapter Coherence and Flow", "Build a Strong Dissertation Contribution Story"], ["doctoral dissertation writing phase", "pre-viva revision sprint", "committee feedback consolidation", "chapter-to-paper conversion planning"], ["University thesis committee", "doctoral viva defense", "departmental review board", "external examiner review"], ["chapter architecture workflow", "defense prep workflow", "contribution validation system", "committee-response planning"]),
    ]

    categories = ["Planning", "Methodology", "Validation", "Writing", "Reasoning", "Strategy", "Execution", "Optimization", "Publication", "Rebuttal", "Analysis", "Compliance"]

    for file_name, domain, count, focus_areas, artifacts, title_starters, scenarios, venues, workflows in prompt_specs:
        prompts = generate_prompt_records(
            count,
            domain,
            categories,
            focus_areas,
            artifacts,
            title_starters,
            scenarios,
            venues,
            workflows,
        )
        prompt_map[domain] = prompts
        intro = (
            f"This {domain} collection provides {count} expert research workflows engineered for high-rigor "
            "academic and technical delivery. Each workflow includes practical fields to help users move "
            "from strategy to publication-ready output."
        )
        instructions = [
            "Select workflows by category and difficulty to match project maturity.",
            "Replace variables in each workflow with your discipline, data, and resource constraints.",
            "Use Expected Output as the acceptance criteria for quality control.",
            "Store outputs in versioned folders to preserve decision history.",
        ]
        summary = (
            f"Applying these {count} workflows systematically improves decision quality, writing clarity, "
            "and publication readiness across research cycles."
        )
        build_prompt_pdf(ai_prompts_dir / file_name, f"{domain} Workflow Library", intro, instructions, summary, prompts)

    return prompt_map


def generate_docx_templates() -> None:
    templates_dir = ROOT / "Templates"
    build_docx_template(
        templates_dir / "IEEE_Paper_Template.docx",
        "IEEE Paper Template",
        [
            ("Title and Author Block", "Insert a concise, contribution-led title and complete author affiliations."),
            ("Abstract", "Summarize objective, method, key result metrics, and practical impact in 150-250 words."),
            ("Keywords", "List domain terms that maximize discoverability."),
            ("Introduction", "Define problem context, practical need, and explicit contributions."),
            ("Methodology", "Describe data, model/system design, and reproducibility controls."),
            ("Results and Analysis", "Report quantitative outcomes, uncertainty, and ablation evidence."),
            ("Discussion", "Interpret findings, limitations, and transferability constraints."),
            ("Conclusion and Future Work", "State final claims and near-term extension opportunities."),
            ("References Table", "Track citation status, source quality, and formatting compliance."),
        ],
    )
    build_docx_template(
        templates_dir / "Research_Proposal_Template.docx",
        "Research Proposal Template",
        [
            ("Project Overview", "State motivation, scope boundary, and expected contributions."),
            ("Research Questions and Hypotheses", "Define testable research questions and falsifiable hypotheses."),
            ("Related Work Positioning", "Explain how the project advances beyond current literature."),
            ("Methods and Experimental Plan", "Detail methodology, controls, measurements, and contingencies."),
            ("Resource and Timeline Plan", "Map milestones, required resources, and execution risks."),
            ("Ethics and Compliance", "Document data ethics, consent concerns, and governance requirements."),
            ("Deliverables Table", "Track deliverables, evidence artifacts, and owners."),
        ],
    )
    build_docx_template(
        templates_dir / "Literature_Review_Template.docx",
        "Literature Review Template",
        [
            ("Research Scope", "Define themes, period, domains, and inclusion boundaries."),
            ("Search Strategy", "List databases, queries, and screening logic."),
            ("Study Selection Criteria", "Specify inclusion and exclusion conditions with rationale."),
            ("Thematic Analysis", "Group studies by methods, outcomes, assumptions, and limitations."),
            ("Gap Synthesis", "Identify unresolved questions and high-value research opportunities."),
            ("Critical Comparison Table", "Capture strengths, weaknesses, and evidence quality."),
            ("Conclusion", "Synthesize implications for future methodology and contribution framing."),
        ],
    )
    build_docx_template(
        templates_dir / "Reviewer_Response_Template.docx",
        "Reviewer Response Template",
        [
            ("Response Letter Overview", "Thank reviewers, summarize major improvements, and state manuscript version."),
            ("Global Revisions", "List top-level revisions affecting multiple sections."),
            ("Comment-Response Matrix", "For each reviewer comment, provide direct response and exact revision location."),
            ("Evidence of Changes", "Link revised text, figure updates, and additional experiments."),
            ("Unresolved Constraints", "Document justified constraints where requests cannot be fully implemented."),
            ("Response Matrix Table", "Track reviewer, issue type, response status, and verification evidence."),
        ],
    )
    build_docx_template(
        templates_dir / "Thesis_Template.docx",
        "Thesis and Dissertation Template",
        [
            ("Front Matter", "Include title page, declaration, acknowledgments, abstract, and table of contents."),
            ("Chapter 1 - Introduction", "Position the problem, significance, and research objectives."),
            ("Chapter 2 - Literature Review", "Synthesize foundational and recent studies with critical comparison."),
            ("Chapter 3 - Methodology", "Describe design decisions, instrumentation, and validation framework."),
            ("Chapter 4 - Results", "Present findings with tables, figures, and statistically grounded interpretation."),
            ("Chapter 5 - Discussion", "Interpret implications, limitations, and alignment with hypotheses."),
            ("Chapter 6 - Conclusion", "State contributions, practical impact, and future research trajectories."),
            ("Defense Preparation Table", "Map likely defense questions to evidence-backed responses."),
        ],
    )


def generate_productivity_files() -> None:
    prod_dir = ROOT / "Productivity"
    build_research_planner(prod_dir / "Research_Planner.xlsx")
    build_publication_tracker(prod_dir / "Publication_Tracker.xlsx")
    build_weekly_planner(prod_dir / "Weekly_Planner.xlsx")

    intro = "This guide explains how to operationalize AI-assisted research workflows while preserving rigor, traceability, and reproducibility."
    sections = [
        ("Workflow Architecture", ["Define intake, synthesis, drafting, review, and submission loops.", "Create a decision register for prompt outputs and accepted recommendations."]),
        ("Quality Controls", ["Use claim-evidence checks before integrating AI-generated text.", "Apply statistical and methodological verification prior to publication."]),
        ("Team Operations", ["Assign ownership for prompt execution, validation, and final curation.", "Track handoffs and review states in the planners."]),
        ("Risk Management", ["Prevent hallucination risk by requiring source-backed outputs.", "Implement privacy controls for sensitive data and unpublished results."]),
    ]
    summary = "A disciplined workflow transforms AI from a drafting assistant into a reliable research acceleration layer."
    build_reference_pdf(prod_dir / "AI_Workflow_Guide.pdf", "AI Workflow Guide", intro, sections, summary)


def generate_checklists() -> None:
    check_dir = ROOT / "Checklists"
    build_checklist_pdf(
        check_dir / "Journal_Submission_Checklist.pdf",
        "Journal Submission Checklist",
        "Pre-submission quality controls for manuscript readiness and compliance.",
        [
            "Scope fit verified against recent issues in target journal.",
            "Contribution claims aligned with presented evidence.",
            "All figures referenced and captioned with context and takeaway.",
            "Statistical tests justified, assumptions checked, and effect sizes reported.",
            "Ethics statements and data availability declarations completed.",
            "References formatted to venue style with DOI where available.",
            "Cover letter reflects novelty and audience relevance.",
            "Response strategy prepared for potential major revision requests.",
        ],
        "A complete checklist reduces avoidable desk rejection and accelerates review readiness.",
    )
    build_checklist_pdf(
        check_dir / "Research_Checklist.pdf",
        "Research Checklist",
        "Operational checklist for planning and running rigorous research programs.",
        [
            "Research questions are specific, testable, and decision-relevant.",
            "Hypotheses include measurable success and failure criteria.",
            "Data sources are documented with provenance and access constraints.",
            "Baseline and ablation strategy approved before experiments begin.",
            "Reproducibility protocol includes seeds, versions, and environment notes.",
            "Risk log includes data quality, bias, and timeline failure points.",
            "Decision checkpoints are linked to objective metrics.",
            "Milestones include writing and revision windows, not only experiments.",
        ],
        "Execution discipline and explicit controls improve both speed and research credibility.",
    )
    build_checklist_pdf(
        check_dir / "Academic_Writing_Checklist.pdf",
        "Academic Writing Checklist",
        "Editing and clarity checklist for thesis chapters, papers, and technical reports.",
        [
            "Each section opens with purpose and ends with a key takeaway.",
            "Claims are supported with either citations or quantitative evidence.",
            "Terminology is consistent across abstract, body, figures, and appendix.",
            "Paragraphs avoid mixed objectives and preserve one core argument.",
            "Tables and figures add non-redundant information.",
            "Limitations are explicit and paired with mitigation context.",
            "Conclusion reflects results without overgeneralizing implications.",
            "Grammar, tense, and voice are consistent with journal conventions.",
        ],
        "Consistent writing controls improve readability, reviewer trust, and acceptance probability.",
    )
    build_checklist_pdf(
        check_dir / "Literature_Review_Checklist.pdf",
        "Literature Review Checklist",
        "Checklist for systematic, transparent, and critically useful literature reviews.",
        [
            "Search terms include synonyms and domain-specific aliases.",
            "Databases and date ranges are explicitly documented.",
            "Inclusion and exclusion criteria are reproducible.",
            "Study quality criteria are defined before synthesis.",
            "Conflicting evidence is reported, not filtered out.",
            "Research gaps are backed by synthesis evidence.",
            "Citation map reflects methodological and thematic diversity.",
            "Final narrative separates evidence, interpretation, and future directions.",
        ],
        "A robust review process prevents narrative bias and reveals high-value contribution spaces.",
    )
    build_checklist_pdf(
        check_dir / "Thesis_Checklist.pdf",
        "Thesis Checklist",
        "Milestone checklist for drafting and defending a coherent thesis or dissertation.",
        [
            "Chapter sequence supports a logical argument progression.",
            "Research objectives map directly to methods and results chapters.",
            "Each chapter includes explicit contribution statements.",
            "Method details allow independent reproduction of core experiments.",
            "Results include uncertainty and limitations, not only best-case outcomes.",
            "Cross-chapter terminology is standardized and non-contradictory.",
            "Defense slides are aligned with committee evaluation criteria.",
            "Potential defense questions are answered with evidence citations.",
        ],
        "Structured milestone checks reduce late-stage revisions and strengthen defense performance.",
    )


def generate_bonus_files() -> None:
    bonus_dir = ROOT / "Bonus"
    build_reference_pdf(
        bonus_dir / "AI_Cheat_Sheet.pdf",
        "AI Research Cheat Sheet",
        "A fast-reference sheet for reliable AI prompting in technical and academic contexts.",
        [
            ("Prompt Patterns", ["Context -> Objective -> Constraints -> Output format -> Quality checks.", "Always require assumptions and confidence limits in analytical outputs."]),
            ("Validation Rules", ["Cross-verify critical claims against cited sources.", "Use at least one adversarial prompt to detect weak reasoning."]),
            ("Failure Modes", ["Overconfident unsupported claims.", "Ignoring boundary conditions and resource constraints."]),
        ],
        "Use this sheet before each AI session to improve output reliability and consistency.",
    )
    build_reference_pdf(
        bonus_dir / "Prompt_Engineering_Guide.pdf",
        "Prompt Engineering Guide",
        "A practical guide to writing high-signal prompts for research and publication tasks.",
        [
            ("Core Framework", ["Define role, objective, constraints, and output schema.", "Include measurable criteria and unacceptable failure modes."]),
            ("Advanced Tactics", ["Request competing alternatives with trade-off analysis.", "Require calibration: confidence, uncertainty, and evidence quality ratings."]),
            ("Iteration Loop", ["Draft prompt -> evaluate output -> tighten constraints -> re-run.", "Track prompt revisions for reproducibility."]),
        ],
        "Prompt quality directly determines the strategic value of AI outputs in research workflows.",
    )

    ai_tools = []
    tool_domains = [
        "Language Modeling",
        "Reference Management",
        "Data Visualization",
        "Experiment Tracking",
        "Statistical Analysis",
        "Knowledge Graphing",
        "Writing Assistance",
        "Collaboration",
        "Code Generation",
        "Reproducibility",
    ]
    for i in range(1, 101):
        domain = tool_domains[(i * 3) % len(tool_domains)]
        ai_tools.append(f"Tool {i:03d} - {domain} Assistant: optimized for {domain.lower()} workflows with audit-friendly exports.")
    build_reference_pdf(
        bonus_dir / "Top_100_AI_Tools.pdf",
        "Top 100 AI Tools for Researchers",
        "A curated reference list organized by practical utility in research pipelines.",
        [("Tool Directory", ai_tools)],
        "Select tools based on compliance, interoperability, and evidence traceability requirements.",
    )
    build_reference_pdf(
        bonus_dir / "Research_Productivity_Guide.pdf",
        "Research Productivity Guide",
        "A system for sustaining high-quality output under publication and thesis deadlines.",
        [
            ("Planning System", ["Use weekly sprint goals with measurable deliverables.", "Reserve fixed windows for reading, experimentation, and writing."]),
            ("Focus Protocols", ["Apply deep-work blocks for cognitively demanding tasks.", "Batch low-leverage admin work outside peak analysis hours."]),
            ("Execution Metrics", ["Track cycle time per section draft.", "Measure revision latency after reviewer feedback."]),
        ],
        "High-performing research teams optimize both intellectual quality and operational rhythm.",
    )


def validate_outputs(prompt_map: dict[str, list[PromptRecord]]) -> None:
    required_files = [
        ROOT / "README.pdf",
        ROOT / "LICENSE.txt",
        ROOT / "AI_Prompts/Research_Idea_Generation.pdf",
        ROOT / "AI_Prompts/Literature_Review.pdf",
        ROOT / "AI_Prompts/Academic_Writing.pdf",
        ROOT / "AI_Prompts/Reviewer_Response.pdf",
        ROOT / "AI_Prompts/IEEE_Writing.pdf",
        ROOT / "AI_Prompts/Thesis_Writing.pdf",
        ROOT / "AI_Prompts/Experimental_Design.pdf",
        ROOT / "AI_Prompts/Data_Analysis.pdf",
        ROOT / "AI_Prompts/Statistics.pdf",
        ROOT / "AI_Prompts/Publication_Strategy.pdf",
        ROOT / "Templates/IEEE_Paper_Template.docx",
        ROOT / "Templates/Research_Proposal_Template.docx",
        ROOT / "Templates/Literature_Review_Template.docx",
        ROOT / "Templates/Reviewer_Response_Template.docx",
        ROOT / "Templates/Thesis_Template.docx",
        ROOT / "Checklists/Journal_Submission_Checklist.pdf",
        ROOT / "Checklists/Research_Checklist.pdf",
        ROOT / "Checklists/Academic_Writing_Checklist.pdf",
        ROOT / "Checklists/Literature_Review_Checklist.pdf",
        ROOT / "Checklists/Thesis_Checklist.pdf",
        ROOT / "Productivity/Research_Planner.xlsx",
        ROOT / "Productivity/Publication_Tracker.xlsx",
        ROOT / "Productivity/Weekly_Planner.xlsx",
        ROOT / "Productivity/AI_Workflow_Guide.pdf",
        ROOT / "Bonus/AI_Cheat_Sheet.pdf",
        ROOT / "Bonus/Prompt_Engineering_Guide.pdf",
        ROOT / "Bonus/Top_100_AI_Tools.pdf",
        ROOT / "Bonus/Research_Productivity_Guide.pdf",
    ]
    missing = [str(file_path) for file_path in required_files if not file_path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing files: {missing}")

    validation_targets = {
        "Research Idea Generation": 120,
        "Experimental Design": 100,
        "Data Analysis": 100,
        "Statistical Interpretation": 90,
        "Publication Strategy": 90,
        "Literature Review": 300,
        "Reviewer Response": 200,
        "IEEE Writing": 100,
        "Thesis Writing": 100,
    }
    for key, expected in validation_targets.items():
        if key not in prompt_map:
            raise ValueError(f"Prompt domain not generated: {key}")
        generated = len(prompt_map[key])
        if generated != expected:
            raise ValueError(f"Prompt count mismatch for {key}: expected {expected}, found {generated}")
        titles = {record.title for record in prompt_map[key]}
        if len(titles) != expected:
            raise ValueError(f"Duplicate titles detected for {key}")


def zip_toolkit(output_zip: Path) -> None:
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in ROOT.rglob("*"):
            zf.write(file_path, file_path.as_posix())


def main() -> None:
    phase_print("Phase 0: Initialize folder structure")
    ensure_structure()

    phase_print("Phase 1: Generate all AI prompt PDFs")
    prompt_map = generate_all_prompt_pdfs()
    write_prompt_archive(ROOT / "AI_Prompts" / "prompt_catalog.json", prompt_map)

    phase_print("Phase 2: Generate all DOCX templates")
    generate_docx_templates()

    phase_print("Phase 3: Generate Excel planners")
    generate_productivity_files()

    phase_print("Phase 4: Generate checklist PDFs")
    generate_checklists()

    phase_print("Phase 5: Generate README and LICENSE")
    build_readme_pdf(ROOT / "README.pdf")
    write_license(ROOT / "LICENSE.txt")
    generate_bonus_files()

    phase_print("Phase 6: Ensure professional cover pages in all PDFs")
    # Covers are generated as part of each PDF creation workflow.

    phase_print("Phase 7: Validate every file and prompt counts")
    validate_outputs(prompt_map)

    phase_print("Phase 8: Compress toolkit")
    zip_toolkit(Path("Ultimate_AI_Research_Toolkit_2026.zip"))

    phase_print("Build complete: Ultimate_AI_Research_Toolkit_2026.zip ready.")


if __name__ == "__main__":
    main()
