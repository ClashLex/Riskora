"""Build the six-slide AIBoomi review deck (requires python-pptx)."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "event-submission" / "Riskora-pitch-deck.pptx"
BG = RGBColor(248, 248, 246)
INK = RGBColor(24, 27, 27)
MUTED = RGBColor(86, 94, 92)
LINE = RGBColor(216, 220, 216)
ACCENT = RGBColor(33, 94, 78)
PALE = RGBColor(233, 241, 236)
WHITE = RGBColor(255, 255, 255)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]


def rect(slide, x, y, w, h, fill=WHITE, line=LINE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.adjustments[0] = 0.08
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.8)
    return shape


def label(slide, value, x, y, w, h=0.28, color=MUTED, size=10, bold=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    para = frame.paragraphs[0]
    para.text = value
    para.font.name = "Aptos"
    para.font.size = Pt(size)
    para.font.bold = bold
    para.font.color.rgb = color
    return box


def text(slide, value, x, y, w, h, size=20, bold=False, color=INK, align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    para = frame.paragraphs[0]
    para.text = value
    para.font.name = "Aptos Display" if size >= 30 else "Aptos"
    para.font.size = Pt(size)
    para.font.bold = bold
    para.font.color.rgb = color
    if align is not None:
        para.alignment = align
    return box


def base(number, section, title, subtitle=None):
    slide = prs.slides.add_slide(blank)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    label(slide, "RISKORA  /  AIBOOMI STARTUP WEEKEND", 0.62, 0.37, 6.5, color=ACCENT, size=10, bold=True)
    label(slide, section.upper(), 10.2, 0.37, 2.5, color=MUTED, size=10)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.62), Inches(0.83), Inches(12.08), Inches(0.012))
    rule.fill.solid()
    rule.fill.fore_color.rgb = LINE
    rule.line.fill.background()
    text(slide, title, 0.62, 1.12, 12, 0.82, size=30, bold=True)
    if subtitle:
        text(slide, subtitle, 0.62, 1.94, 11.95, 0.45, size=15, color=MUTED)
    label(slide, f"{number:02d} / 06", 12.02, 7.07, 0.72, color=MUTED, size=9)
    return slide


def card(slide, x, y, w, h, eyebrow, title, body, fill=WHITE):
    rect(slide, x, y, w, h, fill=fill)
    label(slide, eyebrow.upper(), x + 0.24, y + 0.25, w - 0.48, color=ACCENT, size=10, bold=True)
    text(slide, title, x + 0.24, y + 0.63, w - 0.48, 0.62, size=19, bold=True)
    text(slide, body, x + 0.24, y + 1.3, w - 0.48, h - 1.49, size=14, color=MUTED)


# 1 — Problem and who is affected
s = base(1, "Problem", "A fund statement shows positions after the fact.", "Researchers still need a disciplined way to ask what may appear next.")
card(s, 0.62, 2.76, 3.88, 3.22, "User", "Research analysts", "Initial audience: analysts and small teams studying Indian equity mutual-fund disclosures.")
card(s, 4.72, 2.76, 3.88, 3.22, "Work", "Compare dated holdings", "A new position must be separated from an existing holding, a missing row, or a late publication.")
card(s, 8.82, 2.76, 3.88, 3.22, "Boundary", "Disclosure ≠ trade", "A portfolio report cannot reveal the order, execution date, or manager intent.", fill=PALE)
text(s, "Riskora is a research prototype; user need and willingness to pay are still hypotheses.", 0.62, 6.3, 11.7, 0.38, size=12, color=MUTED)
label(s, "ANSIL MUHAMMED N S  ·  MUHAMMED IHSAN K I", 0.62, 6.76, 9.0, color=ACCENT, size=10, bold=True)

# 2 — Insight and why now
s = base(2, "Insight", "A trustworthy ranking starts with what was knowable.", "The key object is a comparable pair of published snapshots and a strict information cutoff.")
card(s, 0.62, 2.71, 5.72, 3.64, "Insight", "Turn disclosures into testable labels", "Only complete, comparable statements can establish absence. Unknown cases stay unknown. Candidate signals must exist by the earlier publication cutoff.", fill=PALE)
card(s, 6.57, 2.71, 6.13, 3.64, "Why this approach", "Auditable over opaque", "The app links a ranked candidate to dated holdings and market inputs, then shows later-period evaluation against simpler baselines.")
text(s, "Public disclosure routes exist; this prototype still requires user-normalized imports. No automatic historical feed is verified.", 0.62, 6.6, 12, 0.3, size=11, color=MUTED)

# 3 — Solution demo flow
s = base(3, "Solution demo", "Four steps from statement to shortlist.", "Show the actual application live. This slide is a flow schematic, not a product screenshot.")
steps = [
    ("01", "Load data", "Labelled synthetic sample or attributed CSV"),
    ("02", "Inspect", "Dated fund holdings and changes"),
    ("03", "Evaluate", "Later-period holdout and baselines"),
    ("04", "Review", "Candidate ranking and supporting signals"),
]
for i, (num, title, body) in enumerate(steps):
    x = 0.62 + i * 3.07
    rect(s, x, 3.03, 2.84, 2.85, fill=PALE if i == 3 else WHITE)
    text(s, num, x + 0.23, 3.27, 0.65, 0.45, size=23, bold=True, color=ACCENT)
    text(s, title, x + 0.23, 3.88, 2.38, 0.42, size=18, bold=True)
    text(s, body, x + 0.23, 4.53, 2.38, 0.9, size=13, color=MUTED)
    if i < 3:
        text(s, "→", x + 2.88, 4.04, 0.2, 0.35, size=17, color=ACCENT, align=PP_ALIGN.CENTER)
text(s, "Bundled sample = fictional funds and market observations. It checks the workflow, not Indian-market accuracy.", 0.62, 6.31, 12, 0.5, size=12, color=MUTED)

# 4 — Technology
s = base(4, "Technical approach", "Point-in-time data in; inspectable rankings out.", "FastAPI + SQLite + React/Vite + scikit-learn")
flow = [
    ("01", "Validate & store", "Source URL, dates, completeness, identifiers"),
    ("02", "Label & featurize", "Comparable statements and cutoff-dated signals"),
    ("03", "Train & compare", "Logistic model; frequency and sector baselines"),
    ("04", "Explain & review", "Ranked candidates, evidence, walk-forward and holdout"),
]
for i, (num, title, body) in enumerate(flow):
    y = 2.58 + i * 0.9
    rect(s, 0.62, y, 8.05, 0.72, fill=WHITE if i % 2 == 0 else PALE)
    text(s, num, 0.82, y + 0.12, 0.56, 0.42, size=18, bold=True, color=ACCENT)
    text(s, title, 1.55, y + 0.13, 2.15, 0.4, size=15, bold=True)
    text(s, body, 3.68, y + 0.14, 4.6, 0.37, size=12, color=MUTED)
rect(s, 8.93, 2.58, 3.77, 3.44, fill=PALE)
label(s, "OPTIONAL AI EXTRACTION", 9.17, 2.85, 3.3, color=ACCENT, size=10, bold=True)
text(s, "User-supplied event excerpt → verbatim checked facts", 9.17, 3.37, 3.26, 1.0, size=18, bold=True)
text(s, "No hosted LLM is required or configured by default.", 9.17, 4.83, 3.18, 0.75, size=13, color=MUTED)
text(s, "Synthetic and imported data are kept in separate source classes. Ranking scores are uncalibrated.", 0.62, 6.4, 12, 0.42, size=12, color=MUTED)

# 5 — Business hypothesis
s = base(5, "Value & GTM", "A research workflow hypothesis to test with users.", "Potential value: less manual sorting and a clearer audit trail.")
card(s, 0.62, 2.76, 3.88, 3.22, "User", "Research teams", "Interview analysts and independent research desks that already compare disclosures.")
card(s, 4.72, 2.76, 3.88, 3.22, "Buyer hypothesis", "Team license", "Test whether teams would pay for source tracking, evaluation, and repeatable shortlists.")
card(s, 8.82, 2.76, 3.88, 3.22, "First channel", "Supervised pilots", "Observe the workflow with permissioned data before proposing price or scale.", fill=PALE)
text(s, "No customer interviews, paying users, conversion rate, or market-size estimate are claimed.", 0.62, 6.31, 12, 0.42, size=12, color=MUTED)

# 6 — Roadmap and risks
s = base(6, "Next steps", "Prove data quality and usefulness before scale.", "The working synthetic prototype is a starting point, not a validated market model.")
card(s, 0.62, 2.76, 3.88, 3.22, "Data", "Permissioned history", "Validate source rights, publication dates, comparable statements, and corporate actions.")
card(s, 4.72, 2.76, 3.88, 3.22, "Model", "Real holdouts", "Test across funds and periods; audit missing data, survivorship, and calibration.")
card(s, 8.82, 2.76, 3.88, 3.22, "Product", "User pilots", "Test whether an auditable shortlist changes analyst decisions and saves time.", fill=PALE)
text(s, "Risk boundary: a future disclosed position is not an observed trade; outputs are not investment advice.", 0.62, 6.31, 12, 0.42, size=12, color=MUTED)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUTPUT)
print(f"Wrote {len(prs.slides)} slides to {OUTPUT}")
