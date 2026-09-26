"""
make_theory_pdf.py
==================

Builds docs/NITK-UsoundSim_Theory_Guide.pdf: the theory behind every team's stage,
in simple language, with the equations exactly as the code uses them.

    python3 docs/source/make_theory_figures.py   # figures (needs results/*.npz from simulator/main.py)
    python3 docs/source/make_theory_pdf.py       # this PDF

Every number in the guide was either computed by make_theory_figures.py / the
project's code or measured by simulator/main.py and tests/parameter_tests.py
(see docs/MODULES.md).
"""
import io
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = HERE / "fig"
IMG = ROOT / "docs" / "images"
RES = ROOT / "results"
OUT = ROOT / "docs" / "NITK-UsoundSim_Theory_Guide.pdf"

# ---------------------------------------------------------------- fonts and colours
_ttf = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(_ttf / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", str(_ttf / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", str(_ttf / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", str(_ttf / "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFont(TTFont("DVM", str(_ttf / "DejaVuSansMono.ttf")))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402

registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

NAVY = colors.HexColor("#1b3a5c")
BLUE = colors.HexColor("#1f5f99")
LIGHT = colors.HexColor("#eef4fa")
GREEN_BG = colors.HexColor("#edf7ee")
GREEN = colors.HexColor("#2a7a3a")
ORANGE_BG = colors.HexColor("#fff4e5")
ORANGE = colors.HexColor("#b86200")
GREY_BG = colors.HexColor("#f4f4f4")
GREY = colors.HexColor("#555555")
RED = colors.HexColor("#b03a2e")
TEAM_COL = {
    "config": colors.HexColor("#7f8c8d"), "T1": colors.HexColor("#2e6da4"), "T2": colors.HexColor("#3d8fd1"),
    "T3": colors.HexColor("#2a8a3e"), "T4": colors.HexColor("#4aa35c"), "T5": colors.HexColor("#c77d0a"),
    "T6": colors.HexColor("#b0413e"), "T7": colors.HexColor("#8e44ad"), "basics": NAVY, "all": NAVY,
}

# ---------------------------------------------------------------- styles
S = {}
S["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.6, leading=14, spaceAfter=5, textColor=colors.HexColor("#1d1d1d"))
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=8.2, leading=11, spaceAfter=2)
S["cap"] = ParagraphStyle("cap", parent=S["body"], fontSize=8.2, leading=11, textColor=GREY, alignment=TA_CENTER, spaceAfter=10)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=13, bulletIndent=3, spaceAfter=2.5)
S["h1"] = ParagraphStyle("h1", fontName="DV-B", fontSize=19, leading=24, textColor=colors.white)
S["h1sub"] = ParagraphStyle("h1sub", fontName="DV", fontSize=10, leading=14, textColor=colors.white)
S["h2"] = ParagraphStyle("h2", fontName="DV-B", fontSize=12.5, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=4)
S["h3"] = ParagraphStyle("h3", fontName="DV-B", fontSize=10.3, leading=14, textColor=BLUE, spaceBefore=6, spaceAfter=2)
S["boxtitle"] = ParagraphStyle("boxtitle", fontName="DV-B", fontSize=9.6, leading=13, spaceAfter=3)
S["cell"] = ParagraphStyle("cell", fontName="DV", fontSize=8.3, leading=11)
S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="DV-B")
S["cellh"] = ParagraphStyle("cellh", parent=S["cell"], fontName="DV-B", textColor=colors.white)
S["code"] = ParagraphStyle("code", fontName="DVM", fontSize=8, leading=10.5, textColor=colors.HexColor("#222222"))
S["title"] = ParagraphStyle("title", fontName="DV-B", fontSize=30, leading=36, textColor=NAVY, alignment=TA_LEFT)
S["subtitle"] = ParagraphStyle("subtitle", fontName="DV", fontSize=14, leading=20, textColor=BLUE)
S["toc0"] = ParagraphStyle("toc0", fontName="DV-B", fontSize=10.5, leading=17, leftIndent=0)
S["toc1"] = ParagraphStyle("toc1", fontName="DV", fontSize=9.2, leading=13, leftIndent=16, textColor=GREY)

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
TEXT_W = PAGE_W - 2 * MARGIN


# ---------------------------------------------------------------- helpers
def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def steps(items):
    return [Paragraph(t, S["bullet"], bulletText=f"{i}.") for i, t in enumerate(items, 1)]


_eq_n = [0]


def eq(tex, size=13, note=None, width=None, align="CENTER"):
    """Render a LaTeX-style (matplotlib mathtext) equation to an image, centred."""
    _eq_n[0] += 1
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size, color="#111111")
    buf = io.BytesIO()
    fig.savefig(buf, dpi=240, bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close(fig)
    buf.seek(0)
    from PIL import Image as PILImage
    w, h = PILImage.open(buf).size
    buf.seek(0)
    img = Image(buf, width=w / 240 * 72, height=h / 240 * 72)
    rows = [[img]]
    if note:
        rows.append([P(note, "cap")])
    t = Table(rows, colWidths=[width or TEXT_W])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), align), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return KeepTogether([t]) if note else t


def fig(path, width_cm, caption=None):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    wpt = width_cm * cm
    out = [Image(str(path), width=wpt, height=wpt * h / w)]
    if caption:
        out.append(P(caption, "cap"))
    return KeepTogether(out)


def box(title, content, bg=LIGHT, edge=BLUE):
    """Coloured call-out box. content: list of flowables or strings."""
    items = [P(f'<font color="#{edge.hexval()[2:]}">{title}</font>', "boxtitle")] if title else []
    for c in content:
        items.append(P(c) if isinstance(c, str) else c)
    t = Table([[items]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 7)])


def key(title, content):
    return box("Key idea: " + title, content, LIGHT, BLUE)


def example(content, title="Worked example with our numbers"):
    return box(title, content, GREEN_BG, GREEN)


def incode(content, title="How our code does it"):
    return box(title, content, GREY_BG, GREY)


def check(qa):
    items = []
    for q, a in qa:
        items.append(P(f"<b>Q.</b> {q}"))
        items.append(P(f"<font color='#555555'><b>A.</b> {a}</font>"))
    return box("Check yourself", items, ORANGE_BG, ORANGE)


def table(rows, widths, header=True, zebra=True, head_bg=NAVY, font=None):
    data = []
    for i, r in enumerate(rows):
        st = "cellh" if (header and i == 0) else "cell"
        data.append([c if not isinstance(c, str) else Paragraph(c, S[st]) for c in r])
    t = Table(data, colWidths=[w * TEXT_W for w in widths], repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3de")),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), head_bg))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f8fb")))
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 8)]) if len(rows) < 14 else t


def io_table(receives, does, produces, code):
    return table([["Receives (input)", "Does", "Produces (output)", "Code"],
                  [receives, does, produces, code]], [0.24, 0.30, 0.26, 0.20])


class ChapterHeader(Table):
    """Coloured band at the top of a chapter; registered in the table of contents."""

    def __init__(self, number, title, subtitle, team):
        self.toc_title = f"{number}  {title}" if number else title
        col = TEAM_COL.get(team, NAVY)
        super().__init__([[P(self.toc_title, "h1")], [P(subtitle, "h1sub")]], colWidths=[TEXT_W])
        self.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col), ("LEFTPADDING", (0, 0), (-1, -1), 14),
                                  ("TOPPADDING", (0, 0), (0, 0), 12), ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))


def chapter(number, title, subtitle, team):
    return [PageBreak(), ChapterHeader(number, title, subtitle, team), Spacer(1, 10)]


def h2(text):
    p = P(text, "h2")
    p.toc_level = 1
    return CondPageBreak(3.2 * cm), p


def h3(text):
    return P(text, "h3")


# ---------------------------------------------------------------- document
class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.9 * cm,
                         bottomMargin=1.7 * cm, title="NITK-UsoundSim Theory Guide",
                         author="NITK-UsoundSim integration team", subject="Theory behind every pipeline stage")
        frame = Frame(MARGIN, 1.7 * cm, TEXT_W, PAGE_H - 3.6 * cm, id="f")
        self.addPageTemplates([PageTemplate("cover", [frame], onPage=self._cover),
                               PageTemplate("normal", [frame], onPageEnd=self._normal)])
        self.current_chapter = ""

    def beforeDocument(self):
        self.current_chapter = ""
        self.page_chapter = ""

    def afterFlowable(self, f):
        if isinstance(f, ChapterHeader):
            self.current_chapter = f.toc_title
            self.page_chapter = f.toc_title
            self.notify("TOCEntry", (0, f.toc_title, self.page))
        elif isinstance(f, Paragraph) and getattr(f, "toc_level", None) == 1:
            self.notify("TOCEntry", (1, f.getPlainText(), self.page))

    def _cover(self, canv, doc):
        canv.saveState()
        canv.setFillColor(NAVY); canv.rect(0, PAGE_H - 0.9 * cm, PAGE_W, 0.9 * cm, fill=1, stroke=0)
        canv.setFillColor(BLUE); canv.rect(0, 0, PAGE_W, 0.5 * cm, fill=1, stroke=0)
        canv.restoreState()

    def _normal(self, canv, doc):
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#c9d3de")); canv.setLineWidth(0.5)
        canv.line(MARGIN, PAGE_H - 1.35 * cm, PAGE_W - MARGIN, PAGE_H - 1.35 * cm)
        canv.setFont("DV", 7.8); canv.setFillColor(GREY)
        canv.drawString(MARGIN, PAGE_H - 1.2 * cm, "NITK-UsoundSim · Theory Guide")
        canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2 * cm, self.current_chapter[:80])
        canv.line(MARGIN, 1.3 * cm, PAGE_W - MARGIN, 1.3 * cm)
        canv.drawString(MARGIN, 0.9 * cm, "Simple-language theory for every team · all numbers from our own code and runs")
        canv.drawRightString(PAGE_W - MARGIN, 0.9 * cm, f"page {doc.page}")
        canv.restoreState()


story = []
A = story.append
X = story.extend

# ================================================================ COVER
A(Spacer(1, 2.2 * cm))
A(P("NITK-UsoundSim", "title"))
A(Spacer(1, 6))
A(P("Theory Guide: the physics and signal processing behind every team's task", "subtitle"))
A(Spacer(1, 14))
A(P("A 2-D ultrasound simulator that turns a tissue phantom into a B-mode image, "
    "built by seven teams. Probe: <b>Philips L12-4 (FUS4103) reference model</b>, "
    "a 128-element linear array with 0.30 mm pitch at 8 MHz."))
A(Spacer(1, 10))
X([fig(RES / "final_bmode.png", 12.5, "The simulator's final output: point targets, speckle, and an anechoic cyst.")])
A(Spacer(1, 8))
A(box("Who this guide is for", [
    "Every team member. You do not need a signal-processing background: each idea is explained in plain words first, "
    "then the equation our code really uses, then a worked example with our real numbers.",
    "Companion documents: <b>NITK-UsoundSim_Project_Flow.pdf</b> (who hands what to whom), "
    "<b>MODULES.md</b> (technical reference for each module), and <b>demo.ipynb</b> (runs every stage with plots).",
]))
A(P("NITK Surathkal · 2026 · Integration: Darshil Maniya (262SP009)", "small"))
A(NextPageTemplate("normal"))

# ================================================================ CONTENTS
A(PageBreak())
A(P("Contents", "h2"))
toc = TableOfContents()
toc.levelStyles = [S["toc0"], S["toc1"]]
toc.dotsMinLevel = 0
A(toc)

# ================================================================ HOW TO READ
X(chapter("", "How to read this guide", "Colour code, team numbering, symbols", "all"))
A(P("Each team chapter follows the same pattern, so you can jump straight to your own part:"))
X(bullets([
    "<b>What this team does</b>: one sentence.",
    "<b>Theory in simple words</b>: the idea, without equations first.",
    "<b>The equations</b>: exactly the ones in our code, with every symbol explained.",
    "<b>Worked example</b>: the equation filled in with our real numbers.",
    "<b>How our code does it</b>: the steps and the file name.",
    "<b>Input → output</b> and a figure from our own simulation.",
    "<b>Check yourself</b>: short questions a teacher might ask, with answers.",
]))
A(h3("Colour-coded boxes"))
A(table([["Box", "Meaning"],
         ["Blue", "Key idea: the one thing to remember"],
         ["Green", "Worked example with our numbers"],
         ["Grey", "How our code does it (file and steps)"],
         ["Orange", "Check yourself: viva-style questions"]], [0.25, 0.75], zebra=False))
X(h2("Team numbering used in this guide"))
A(P("This guide uses the same team split as the project-flow PDF. The code folders keep the original plan numbering. "
    "The table shows where each stage's code lives."))
A(table([
    ["Team", "Stage", "Code (folder / file)"],
    ["config", "Shared settings", "simulator/config.py"],
    ["T1", "Transducer (array geometry)", "teams/T1_Transducer (piezo registry); geometry via T3's create_linear_array()"],
    ["T2", "Transmit beamforming", "teams/T2_TX_Beamforming/Usound/src/beamformer.py"],
    ["T3", "Acoustic propagation", "teams/T3_Acoustic_Propagation/usound_sim/nitk_usoundsim/acoustic_propagation.py"],
    ["T4", "Tissue interaction + RF generation", "teams/T4_Tissue_Interaction: tissue_interaction.py, phantom.py, tissue_phantoms.py"],
    ["T5", "Receive beamforming (DAS)", "teams/T5_RX_Beamforming/receive_beamforming.py"],
    ["T6", "Image reconstruction: envelope + log compression", "teams/T6_B_mode/bmode_formation.py"],
    ["T7", "B-mode image formation: 50 dB gray map + scan conversion", "bmode_formation.py (gray map) + teams/T7_…/post_processing.py (scan_convert)"],
    ["T6", "Post-image processing: despeckling (guided filter)", "teams/T7_Image_Recon_Post_Processing/post_processing.py (postprocess)"],
], [0.1, 0.38, 0.52]))
X(h2("Symbols and the values we use"))
A(table([
    ["Symbol", "Meaning", "Our value"],
    ["c", "speed of sound in tissue", "1540 m/s"],
    ["f₀", "centre (transmit) frequency", "8 MHz (probe range 4–12 MHz)"],
    ["λ = c / f₀", "wavelength", "0.1925 mm"],
    ["N", "number of array elements", "128"],
    ["p (pitch)", "centre-to-centre element spacing", "0.30 mm (= 1.56 λ)"],
    ["w", "element width", "0.30 mm (= pitch, no gap assumed)"],
    ["D = N·p", "aperture (array length)", "38.4 mm"],
    ["f_s", "sampling frequency", "40 MHz (5 samples per 8 MHz cycle)"],
    ["α₀", "attenuation coefficient", "0.5 dB / (MHz·cm)"],
    ["DR", "display dynamic range", "50 dB"],
    ["F#", "receive F-number (depth / aperture width)", "1.0"],
    ["x, z", "lateral position, depth", "image: x = ±10 mm, z = 0–40 mm"],
    ["t_axis", "RF time axis", "3574 samples, starts at −0.75 µs"],
], [0.18, 0.47, 0.35]))

# ================================================================ BASICS
X(chapter("1", "Ultrasound in ten minutes", "The physics every team needs", "basics"))
A(P("Ultrasound imaging works like an echo in a valley. The probe sends a very short burst of sound into the body. "
    "Every small structure the sound hits sends a tiny echo back. The probe listens, and the <b>time</b> an echo takes to "
    "return tells us <b>how deep</b> the structure is. The <b>strength</b> of the echo tells us how bright to draw it."))
X(h2("1.1 Sound wave, frequency and wavelength"))
A(P("Sound is a pressure wave: tissue is squeezed and stretched many times per second. The number of squeezes per "
    "second is the <b>frequency f</b> (Hz). The distance between two squeezes is the <b>wavelength λ</b>. In soft tissue sound "
    "travels at about <b>c = 1540 m/s</b>."))
A(eq(r"\lambda = \dfrac{c}{f_0} = \dfrac{1540\ \mathrm{m/s}}{8\times10^{6}\ \mathrm{Hz}} = 0.1925\ \mathrm{mm}"))
A(key("smaller wavelength = finer detail", [
    "Higher frequency gives a smaller λ and therefore sharper images, but high frequencies are absorbed faster, so they "
    "cannot see deep. The L12-4 (4–12 MHz) is a high-frequency probe for shallow organs such as the breast, thyroid and blood vessels."]))
X(h2("1.2 Echo time tells depth"))
A(P("The pulse travels down to depth z and the echo travels back up, so the sound covers 2z in total:"))
A(eq(r"t = \dfrac{2z}{c}\qquad\Longleftrightarrow\qquad z = \dfrac{c\,t}{2}"))
X([fig(FIG / "basics_wave_echo.png", 16, "Left: an 8 MHz wave in tissue. Right: echoes from 10, 20 and 30 mm arrive after 13.0, 26.0 and 39.0 µs.")])
X(h2("1.3 Why echoes happen: acoustic impedance"))
A(P("Each tissue has an <b>acoustic impedance Z = ρ·c</b> (density × speed of sound), measured in MRayl. When sound meets a change "
    "in Z, part of it is reflected. The bigger the change, the stronger the echo. Soft tissue is about 1.63 MRayl in T4's model."))
A(eq(r"R = \dfrac{Z_2 - Z_1}{Z_2 + Z_1}", note="pressure reflection coefficient (T4's pressure_reflection_coefficient)"))
X(h2("1.4 Attenuation and decibels"))
A(P("Tissue absorbs sound as it travels. The loss grows with distance <b>and</b> with frequency. Ultrasound people measure "
    "ratios in <b>decibels (dB)</b>: −6 dB is half the amplitude, −20 dB is one tenth, −40 dB is one hundredth."))
A(eq(r"\mathrm{dB} = 20\,\log_{10}\!\left(\dfrac{A}{A_{\mathrm{ref}}}\right)"))
X(h2("1.5 From echoes to a picture"))
X(bullets([
    "The probe has many small elements side by side (a <b>linear array</b>). Each element records its own echo signal over time: the <b>RF signal</b> (radio-frequency, because it oscillates at MHz).",
    "<b>Beamforming</b> combines the elements' signals so that we listen to one point at a time.",
    "Each vertical <b>scan line</b> becomes a column of the image. Echo strength is shown as brightness: <b>B-mode</b> (Brightness mode).",
    "A few more steps (envelope, log compression, gray mapping, scan conversion, despeckling) make it a clean picture.",
]))
X([fig(IMG / "pipeline_flow.png", 11.5, "The whole pipeline. Each team's output is the next team's input.")])
X(h2("1.6 Resolution: how small a thing we can see"))
X(bullets([
    "<b>Axial resolution</b> (along depth) depends on the <b>pulse length</b>: a shorter pulse separates two close points in depth.",
    "<b>Lateral resolution</b> (sideways) depends on how narrow the <b>beam</b> is: about λ × F-number.",
    "Both are measured as the <b>−6 dB width</b> (full width at half maximum amplitude) of a point target's image.",
]))
A(check([
    ("An echo arrives 26 µs after transmit. How deep is the reflector?", "z = c·t/2 = 1540 × 26×10⁻⁶ / 2 ≈ 20 mm."),
    ("Why not always use 12 MHz for the sharpest image?", "Attenuation grows with frequency: 12 MHz loses 3 × more dB per cm than 4 MHz, so deep regions become too dark."),
    ("What does −20 dB mean?", "The amplitude is 1/10 of the reference."),
]))

# ================================================================ CONFIG
X(chapter("2", "Shared settings (config.py)", "One source of truth for every team", "config"))
A(P("<b>What it does:</b> keeps every number that more than one team needs (speed of sound, sampling rate, probe, image size) "
    "in one file, <b>simulator/config.py</b>. Teams import the values instead of typing their own copies, so two stages can "
    "never disagree about, for example, the speed of sound."))
X(h2("2.1 The RF time axis and the “time-axis rule”"))
A(P("The transmit pulse is centred at t = 0, but it starts a little earlier (its front edge). So the recorded RF starts at "
    "<b>t = −0.75 µs</b> (four pulse-widths σ before the centre), not at 0. The axis has 3574 samples at 40 MHz."))
A(key("the time-axis rule", [
    "To read the RF at a time τ, our code always uses <b>np.interp(τ, t_axis, rf)</b> on the real time axis, "
    "never “sample index = τ × f_s”. The shortcut would ignore the −0.75 µs start and put every target about "
    "0.58 mm too deep at 8 MHz (c × 0.75 µs / 2)."]))
A(eq(r"\Delta z = \dfrac{c}{2 f_s} = \dfrac{1540}{2\times 40\times10^{6}} = 0.0193\ \mathrm{mm\ per\ RF\ sample}"))
A(table([
    ["Setting", "Value", "Why"],
    ["Imaged width", "x = ±10 mm, 256 scan lines (0.078 mm apart)", "well inside the 38.4 mm array"],
    ["Displayed depth", "0–40 mm", "T3's field of view"],
    ["RF recorded to", "60 mm", "T5's own test checks a target at 55 mm"],
    ["Transmit", "one broadcast shot (all delays 0)", "one simulation serves all 256 lines"],
    ["Receive window", "Hann, F# = 1", "see Chapter 7"],
    ["Element directivity", "on", "see Chapter 3"],
], [0.22, 0.43, 0.35]))

# ================================================================ T1
X(chapter("3", "T1 · Transducer", "Piezoelectric elements and the geometry of the linear array", "T1"))
A(P("<b>What this team does:</b> describes the probe: the material that converts electricity into sound, and where the 128 "
    "elements sit."))
X(h2("3.1 Theory in simple words"))
A(P("A transducer element is a small piece of <b>piezoelectric</b> material (for example the ceramic PZT-5H). Piezoelectric "
    "means: apply a voltage and it changes shape (it sends sound); squeeze it with sound and it produces a voltage (it receives). "
    "The same element is used for both."))
A(P("A <b>linear array</b> puts many narrow elements in a row. Their spacing is the <b>pitch</b>, and the total length is the "
    "<b>aperture</b>. A wide aperture can focus more sharply; a small pitch avoids false copies of objects (grating lobes)."))
X(h2("3.2 The equations"))
A(eq(r"x_n = \left(n - \dfrac{N-1}{2}\right)\,p,\qquad n = 0,1,\ldots,N-1", note="element centres, symmetric around x = 0 (create_linear_array)"))
A(example([
    "N = 128, p = 0.30 mm → x₀ = −63.5 × 0.30 = <b>−19.05 mm</b>, x₁₂₇ = <b>+19.05 mm</b>; aperture D = 128 × 0.30 = <b>38.4 mm</b>.",
    "Pitch in wavelengths: p / λ = 0.30 / 0.1925 = <b>1.56 λ</b>.",
]))
X([fig(FIG / "t1_array.png", 16, "The first 8 of our 128 elements, numbered from 0. Each is 0.30 mm wide and they touch (no kerf assumed).")])
X(h2("3.3 The λ/2 rule and grating lobes"))
A(P("If elements are more than half a wavelength apart, the array can be “fooled”: a strong echo coming from a steep angle "
    "arrives at neighbouring elements with a delay of exactly one full wave, so it looks like it came from straight ahead. "
    "This creates a false copy of the object called a <b>grating lobe</b>. It appears at the angle where"))
A(eq(r"\sin\theta_g = \dfrac{\lambda}{p} = \dfrac{0.1925}{0.30}\ \Rightarrow\ \theta_g = 39.9^\circ"))
A(P("Our L12-4 model has p = 1.56 λ, well above λ/2, so grating lobes are a real risk. Two effects protect us:"))
X(bullets([
    "<b>Element directivity.</b> A real element of width w does not send and receive equally in all directions. It is "
    "strongest straight ahead and weaker at steep angles (a sinc pattern, as used in the Field II simulator).",
    "<b>F-number on receive</b> (Chapter 7) only listens up to ±26.6°, below the 39.9° grating angle.",
]))
A(eq(r"D_n(\theta) = \mathrm{sinc}\!\left(\dfrac{w\,\sin\theta}{\lambda}\right),\qquad \mathrm{sinc}(u)=\dfrac{\sin(\pi u)}{\pi u}",
     note="applied on transmit and on receive in tissue_phantoms.element_directivity()"))
X([fig(FIG / "t1_directivity.png", 14.5, "Directivity of one 0.30 mm element at 8 MHz. Because w = p, its null falls exactly on the grating-lobe angle.")])
A(example([
    "At the grating angle, sin θ_g = λ/p, so D = sinc(w/p) = sinc(1) = <b>0</b> at exactly 8 MHz: the element is “deaf” there.",
    "The pulse also contains nearby frequencies (about 7.1–8.9 MHz at −6 dB), where the null is not exact, so ghosts are reduced, not removed.",
    "Measured effect: without directivity the ghosts under each point target were only −11 to −13 dB; with it they are <b>−21 to −34 dB</b>.",
]))
X(h2("3.4 T1's own code"))
A(incode([
    "T1 delivered a <b>piezo-material registry</b> (teams/T1_Transducer/src): a Piezo class that stores a material name and its "
    "frequency range, checks the range (both values numeric, non-negative, min ≤ max), and a registry to add and look up "
    "materials such as Quartz and PZT-5H. process_material() returns a random frequency inside the material's range.",
    "Because T1's code has no element positions, the array geometry comes from T3's create_linear_array(), called through config.py. "
    "T2's probe file names the material as <b>PZT-5H</b>, matching T1's registry.",
]))
A(io_table("N_ELEMENTS = 128, PITCH = 0.30 mm (config)", "places elements symmetrically on the x-axis at z = 0",
           "element_positions, shape (128,), metres", "config.get_element_positions()"))
A(check([
    ("What is the pitch of our array in wavelengths, and why does it matter?", "1.56 λ. Above λ/2, grating lobes (false copies) can appear."),
    ("At what angle would a grating lobe appear?", "sin θ = λ/p → 39.9°."),
    ("Why does the element's width help?", "Its sinc directivity has a null at that same angle when w = p, so the element barely hears the grating direction."),
    ("What does piezoelectric mean?", "Voltage ↔ mechanical deformation: the element both transmits and receives sound."),
]))

# ================================================================ T2
X(chapter("4", "T2 · Transmit beamforming", "The pulse, focusing delays and apodization", "T2"))
A(P("<b>What this team does:</b> decides <b>what</b> each element sends (the pulse) and <b>when</b> (the delays), so that the "
    "sound goes where we want."))
X(h2("4.1 The transmit pulse"))
A(P("A short pulse gives good depth resolution, but it must still contain a few oscillations at the centre frequency. "
    "We use a sine wave at f₀ inside a smooth bell-shaped (Gaussian) envelope, 3 cycles long (T3's generate_pulse):"))
A(eq(r"p(t) = \sin(2\pi f_0 t)\;\exp\!\left(-\dfrac{t^2}{2\sigma^2}\right),\qquad \sigma = \dfrac{N_{\mathrm{cycles}}}{2 f_0} = \dfrac{3}{2\times 8\,\mathrm{MHz}} = 0.1875\ \mu\mathrm{s}"))
X([fig(FIG / "t2_pulse_spectrum.png", 16, "Our 8 MHz pulse (61 samples from −0.75 to +0.75 µs) and its spectrum. Its −6 dB band is 7.1–8.9 MHz.")])
A(key("pulse length ↔ axial resolution ↔ bandwidth", [
    "Short pulse → wide spectrum (bandwidth) → fine axial resolution. The −6 dB width of the envelope in time is 2.355 σ; "
    "converted to depth (divide by 2 for the round trip):"]))
A(eq(r"\Delta z_{-6\,\mathrm{dB}} = \dfrac{c}{2}\cdot 2.355\,\sigma = 770\times 2.355\times 0.1875\,\mu\mathrm{s} = 0.340\ \mathrm{mm}"))
A(P("Measured on our point targets: <b>0.327–0.346 mm</b>. Theory and simulation agree."))
X(h2("4.2 Focusing delays"))
A(P("To focus at a point (x_f, z_f), every element's wave must arrive there <b>at the same moment</b>. Edge elements are "
    "farther away, so they must fire <b>first</b>; the centre fires last:"))
A(eq(r"d_n = \sqrt{(x_n - x_f)^2 + z_f^2},\qquad \tau_n = \dfrac{\max_n d_n - d_n}{c}"))
A(P("To <b>steer</b> the beam by an angle θ without focusing, a linear delay is used instead: τ_n = x_n sin θ / c (shifted so the smallest is 0)."))
X([fig(FIG / "t2_focus_delays.png", 16, "Focus at (0, 20) mm: the delay curve is a dome, largest at the centre (4.95 µs).")])
X(h2("4.3 Apodization (weighting the elements)"))
A(P("If all elements send with equal strength (rectangular window), the beam has strong <b>side lobes</b>: weak copies of the beam "
    "beside the main one. Tapering the edges with a smooth window (Hann or Hamming) lowers the side lobes, but makes the main "
    "beam a little wider. This is the classic trade-off."))
A(eq(r"w_{\mathrm{Hann}}(n) = 0.5 - 0.5\cos\!\left(\dfrac{2\pi n}{N-1}\right),\qquad w_{\mathrm{Hamming}}(n) = 0.54 - 0.46\cos\!\left(\dfrac{2\pi n}{N-1}\right)"))
X([fig(FIG / "t2_windows.png", 12.5, "The three windows compared in the parameter tests.")])
X(h2("4.4 What our imaging chain uses, and why"))
A(key("one broadcast transmit", [
    "All 128 elements fire together (all delays 0). One transmit lights up the whole field, and one RF simulation serves "
    "all 256 scan lines. A focused transmit for every line would need 256 separate simulations of about 4 min each.",
    "Focusing then happens on <b>receive</b> (T5), at every depth.",
]))
A(example([
    "Parameter test: with T2's delays focused at 20 mm, the incident wave at a target at (0, 20) mm is <b>+18.36 dB</b> stronger than with the broadcast. "
    "With the focus at 10 mm it is +0.00 dB and at 30 mm +4.78 dB: focusing helps most at the target depth.",
]))
X([fig(IMG / "t2_transmit_field.png", 11, "Transmit field: broadcast (used) versus T2's focus at 20 mm.")])
A(incode([
    "T2's beamformer.py: create_linear_array(), make_apodization() (rect / Hann / Hamming, normalised to max 1), "
    "calculate_tx_delays() (focus or steering) and build_tx_package(). T2's probe file (config/transducer_interface.json) "
    "is where the L12-4 values come from: 128 elements, 0.30 mm, 4–12 MHz, 8 MHz.",
    "The imaging chain uses config.get_tx_delays() (zeros) and T3's pulse. T2's delays are used in the parameter tests and the demo notebook.",
]))
A(io_table("element_positions (T1), focus or angle, c", "pulse, per-element delays, apodization",
           "pulse (61,), tx_delays (128,) s, weights (128,)", "T2 beamformer.py; T3 generate_pulse()"))
A(check([
    ("Why do edge elements fire first when focusing?", "They are farther from the focus, so they need a head start to arrive at the same time."),
    ("What happens to side lobes and beam width with a Hann window?", "Side lobes go down (−18.2 dB → −32.7 dB on receive in our test); the main beam widens (0.30 → 0.46 mm)."),
    ("Why don't we focus on transmit in the images?", "One focused transmit per line would need 256 simulations; the broadcast needs one. Receive focusing does the rest."),
    ("How long is our pulse?", "3 cycles, σ = 0.1875 µs, stored as 61 samples (−0.75 to +0.75 µs)."),
]))

# ================================================================ T3
X(chapter("5", "T3 · Acoustic propagation", "How the pulse travels to a scatterer and back", "T3"))
A(P("<b>What this team does:</b> moves the pulse through tissue: from every element to a point (forward) and from that point "
    "back to every element (return), with the right delay and loss."))
X(h2("5.1 Time of flight"))
A(P("Sound goes in a straight line at constant speed c. The distance from element n at (x_n, 0) to a scatterer at (x_s, z_s) is"))
A(eq(r"d_n = \sqrt{(x_s - x_n)^2 + z_s^2},\qquad t_n = \dfrac{d_n}{c}"))
A(example([
    "Target at (0, 20) mm: the centre elements are 20 mm away → 20 mm / 1540 m/s = <b>12.99 µs</b>; the edge elements at ±19.05 mm are "
    "√(19.05² + 20²) = 27.6 mm away → <b>17.94 µs</b>. That spread of arrival times is the curve seen in the raw echoes.",
]))
X(h2("5.2 Attenuation"))
A(P("The amplitude drops exponentially with distance; in dB the loss is simply proportional to frequency × distance:"))
A(eq(r"\mathrm{loss_{dB}} = \alpha_0\, f_0[\mathrm{MHz}]\; d[\mathrm{cm}],\qquad A(d) = 10^{-\mathrm{loss_{dB}}/20}"))
A(example([
    "At 8 MHz: 0.5 × 8 = <b>4 dB per cm</b> one way. A target 2 cm deeper loses 2 × 2 × 4 = <b>16 dB</b> more (there and back).",
    "Parameter test: targets at 10 and 30 mm, α₀ = 0.5 → measured extra loss −16.11 dB (theory −16.00); α₀ = 1.0 → −32.21 dB (theory −32.00).",
]))
X([fig(FIG / "t3_attenuation.png", 12.5, "Round-trip attenuation versus depth for 4, 8 and 12 MHz.")])
X(h2("5.3 Forward and return propagation"))
A(P("<b>Forward:</b> the wave arriving at the scatterer is the sum of the pulses from all elements, each delayed by its own "
    "travel time and transmit delay, and weakened by its own path loss. <b>Return:</b> the scattered wave travels back to each "
    "element m with its own delay and loss."))
A(eq(r"\mathrm{incident}(t) = \sum_{n} D_n\,A(d_n)\;p\!\left(t - \tau_{\mathrm{TX},n} - \dfrac{d_n}{c}\right)"))
A(eq(r"\mathrm{rf}_m(t) = D_m\,A(d_m)\;\mathrm{reflected}\!\left(t - \dfrac{d_m}{c}\right)", note="D = element directivity (Chapter 3), added by T4's tissue_phantoms.py around T3's functions"))
X([fig(IMG / "t3_propagation.png", 16, "Incident wave at (0, 20) mm, one-way travel times from every element, and the echo received on all 128 elements.")])
X(h2("5.4 Linear superposition"))
A(key("echoes simply add", [
    "The medium is linear: the echo from many scatterers is the sum of their separate echoes. So the simulator handles one "
    "scatterer at a time and adds up the results. This is also why the work can be split across CPU cores and summed at the end.",
]))
X(h2("5.5 Sampling"))
A(P("The computer stores the RF only at discrete times, every 1/f_s = 25 ns. The <b>Nyquist rule</b> says we need more than two "
    "samples per cycle of the highest frequency: 2 × 12 MHz = 24 MHz < 40 MHz, so our sampling is enough. To read the signal "
    "<b>between</b> samples (delays are never exact multiples of 25 ns), the code joins samples with straight lines (linear "
    "interpolation, np.interp)."))
X([fig(FIG / "t3_sampling.png", 12.5, "At 40 MHz an 8 MHz wave gets 5 samples per cycle; np.interp joins them with straight lines.")])
A(P("Linear interpolation slightly smooths the peaks (it acts as a weak low-pass filter). The parameter test shows the peak "
    "level is about 2.8 dB lower at 4 samples per cycle than at 8, but the <b>position</b> of the target does not move. "
    "Because every image is normalised to its own peak, this uniform loss does not change the picture."))
A(incode([
    "forward_propagation(scatterer, element_x, t_axis, f0, tau_tx): distance → delay → attenuation → sum of delayed pulses.",
    "return_propagation(reflected, t_axis, scatterer, element_x, f0): shifts the reflected wave to every element with np.interp.",
    "T3's functions are used unchanged; f0 = 8 MHz is passed explicitly because T3's own default is 5 MHz.",
]))
A(io_table("element positions, tx_delays, pulse, one scatterer, t_axis", "straight-ray delay + attenuation, forward and back",
           "incident wave (3574,); echoes at the elements (128, 3574)", "acoustic_propagation.py (T3)"))
A(check([
    ("Why is the raw echo from one point a curve across the elements?", "Edge elements are farther away, so the echo reaches them later (12.99 µs at the centre versus 17.94 µs at the edges for 20 mm)."),
    ("Is 40 MHz sampling enough for a 12 MHz signal?", "Yes: Nyquist needs more than 24 MHz."),
    ("How much signal do we lose from 10 mm to 30 mm at 8 MHz?", "About 16 dB (2 cm × 2 ways × 4 dB/cm); measured 16.11 dB."),
    ("What does “linear superposition” let us do?", "Simulate each scatterer separately and add the echoes, in parallel on all CPU cores."),
]))

# ================================================================ T4
X(chapter("6", "T4 · Tissue interaction and RF generation", "Scatterers, speckle, the cyst, and the 128-channel RF", "T4"))
A(P("<b>What this team does:</b> builds the “patient” (a phantom made of point scatterers), decides how strongly each point "
    "reflects, and adds up all echoes into the raw RF data that a real scanner would record."))
X(h2("6.1 Scatterers: why tissue is modelled as many points"))
A(P("Real tissue is full of structures much smaller than a wavelength (cells, fibres). Each one reflects a tiny echo. We model "
    "tissue as many randomly placed point scatterers, each with a random strength. This is the standard approach of the Field II simulator."))
A(eq(r"x, z \sim \mathrm{Uniform},\qquad \mathrm{amp} \sim \mathcal{N}(0,\ \sigma^2 = 1)", note="T4's generate_liver_phantom(): uniform positions, Gaussian amplitudes (positive or negative)"))
A(example([
    "Phantom area: x = ±12 mm (24 mm) × z = 0–40 mm. Density 1×10⁸ scatterers/m² → 0.024 × 0.040 × 10⁸ = <b>96,000 scatterers</b>.",
    "That is about 15 scatterers per resolution cell (0.33 mm × 0.47 mm × 10⁸ m⁻² ≈ 15.5), enough for “fully developed” speckle.",
]))
X(h2("6.2 How one scatterer reflects"))
A(P("T4 multiplies the incident wave by a gain. If the scatterer carries its own impedance, the reflection coefficient R (Chapter 1) "
    "makes the echo stronger; an optional scale makes a region brighter or darker:"))
A(eq(r"\mathrm{reflected}(t) = G\cdot\mathrm{incident}(t),\qquad G = \mathrm{amp}\,(1+|R|)\,\mathrm{scale}"))
A(P("In our phantoms no local impedance is set, so G = amp × scale."))
X(h2("6.3 The three phantoms"))
A(table([
    ["Phantom", "What it is", "What it tests"],
    ["Point targets", "3 points at (−5, 10), (0, 20), (+5, 30) mm, amp 1", "position accuracy and resolution"],
    ["Scatterers (speckle)", "96,000 random scatterers", "speckle texture and brightness uniformity"],
    ["Cyst", "same 96,000, with an anechoic circle r = 6 mm at (0, 30) mm (11,169 scatterers inside, scale 0.0)", "contrast and edge sharpness"],
], [0.2, 0.47, 0.33]))
A(P("T4's code also supports lesion classes: <b>hypoechoic</b> (darker, scale 0.35), <b>isoechoic</b> (1.0) and "
    "<b>hyperechoic</b> (brighter, 1.8). Our cyst uses scale 0.0: <b>anechoic</b>, like a fluid-filled cyst that produces no echoes."))
X([fig(IMG / "t4_phantom.png", 14.5, "Left: the cyst phantom (colour = amplitude). Right: T4's tissue interaction at one scatterer.")])
X(h2("6.4 Speckle: the grainy texture of ultrasound"))
A(P("Inside one resolution cell, many scatterers echo at the same time. Their echoes have random phases, so they add up "
    "sometimes strongly, sometimes cancelling. The result is a granular pattern called <b>speckle</b>. It is not noise from the "
    "electronics; it is an interference pattern, and it looks the same every time for the same tissue."))
A(P("Theory (Burckhardt 1978; Wagner et al. 1983): with many random scatterers per cell, the envelope brightness follows a "
    "<b>Rayleigh distribution</b>, whose mean divided by its standard deviation is fixed:"))
A(eq(r"\mathrm{SNR}_{\mathrm{speckle}} = \dfrac{\mathrm{mean}}{\mathrm{std}} = \sqrt{\dfrac{\pi}{4-\pi}} = 1.91"))
X([fig(FIG / "t4_speckle_stats.png", 15, "Our speckle at 14–16 mm matches the Rayleigh curve (mean/std 1.86). Right: a random sum of echoes.")])
A(example(["Measured over depth bands from 6 to 38 mm: <b>1.73–1.92</b> (theory 1.91). Our speckle is fully developed, as in real tissue."]))
X(h2("6.5 From one echo to the full RF"))
A(eq(r"\mathrm{rf}_m(t) = \sum_{s=1}^{96\,000} \mathrm{echo}_{m,s}(t)", note="for every element m: add the echoes of all scatterers (linear superposition)"))
A(incode([
    "tissue_phantoms.py: build_phantom(kind) → list of {x, z, amp}.",
    "For each scatterer: incident_wave() (T3 forward × directivity) → tissue_interaction() (T4) → return_propagation() (T3) × directivity.",
    "simulate_rf() splits the scatterers into chunks and runs them in parallel processes on all CPU cores, then adds the chunks. "
    "About 3.6–4.4 min per 96,000-scatterer phantom on 8 cores.",
]))
X([fig(IMG / "t4_raw_rf.png", 16, "T4's output raw_rf (128 × 3574): a 20–24 µs zoom of all channels, and one full channel. Speckle echoes overlap everywhere.")])
A(io_table("T3's propagation functions, phantom settings (config)", "builds the phantom, reflects the wave at every scatterer, sums the echoes",
           "raw_rf (128, 3574) + t_axis", "tissue_interaction.py, phantom.py, tissue_phantoms.py"))
A(check([
    ("Is speckle noise that a better amplifier could remove?", "No. It is interference from many sub-wavelength scatterers; it is part of the signal."),
    ("What value of mean/std do we expect for fully developed speckle?", "1.91 (Rayleigh). We measured 1.73–1.92."),
    ("Why is our cyst black?", "Scatterers inside have scale 0.0 (anechoic), so no echoes come from inside."),
    ("How many scatterers, and how many inside the cyst?", "96,000 in total; 11,169 inside the 6 mm cyst."),
]))

# ================================================================ T5
X(chapter("7", "T5 · Receive beamforming (delay-and-sum)", "Listening to one point at a time", "T5"))
A(P("<b>What this team does:</b> turns 128 channels of raw echoes into 256 focused scan lines. It is the heart of the scanner."))
X(h2("7.1 The idea of delay-and-sum (DAS)"))
A(P("An echo from a point reaches the elements at different times (a curve, Chapter 5). If we <b>delay</b> each channel by exactly "
    "its extra travel time, the echoes from that point line up. Then we <b>sum</b> them: echoes from the chosen point add up "
    "strongly, while echoes from other places are misaligned and cancel. Doing this for every depth and every line gives the image."))
X([fig(FIG / "t5_das_alignment.png", 16.5, "Real point-target RF from our simulation. Aligning and adding gives a strong pulse on the target line; 2 mm to the side it cancels (about −40 dB).")])
X(h2("7.2 The delays"))
A(P("For a pixel at (x_l, z) on scan line l, the time the echo needs is the transmit time (the broadcast wave first reaches the "
    "point from the nearest element) plus the return time to element m:"))
A(eq(r"\tau_{\mathrm{TX}}(z) = \dfrac{\min_n \sqrt{(x_l-x_n)^2+z^2}}{c},\qquad \tau_{\mathrm{RX},m}(z) = \dfrac{\sqrt{(x_l-x_m)^2+z^2}}{c}"))
A(eq(r"s_l(z) = \dfrac{\sum_m w_m(z)\;\mathrm{rf}_m\!\left(\tau_{\mathrm{TX}}+\tau_{\mathrm{RX},m}\right)}{\sum_m w_m(z)}"))
A(P("Because the delays are recomputed for every depth, the receive focus follows the echo down: <b>dynamic receive focusing</b>. "
    "Every lookup rf_m(τ) uses np.interp on the real t_axis (the time-axis rule)."))
X(h2("7.3 Dynamic aperture and the F-number"))
A(P("The <b>F-number</b> is focal depth divided by aperture width. Near the surface only a few elements can usefully hear a point; deep "
    "down, more can. So the active aperture grows with depth, keeping F# constant:"))
A(eq(r"a(z) = \max\!\left(\dfrac{z}{2F_\#},\ 2p\right),\qquad w_m(z) = \cos^2\!\left(\dfrac{\pi\,|x_m-x_l|}{2a}\right)\ \mathrm{for}\ |x_m-x_l|<a",
     note="a = half-width of the active aperture; Hann-shaped weights centred on the line"))
X([fig(FIG / "t5_dynamic_aperture.png", 12.5, "With F# = 1 the aperture is as wide as the depth: 10 mm wide at 10 mm, 40 mm (whole array) near 38 mm.")])
A(key("why F# = 1", [
    "With F# = 1, the steepest angle any element listens at is atan(1/2) = <b>26.6°</b>, below the 39.9° grating angle. "
    "With the full fixed aperture, a grating-lobe streak appeared at −17 dB; with F# = 1 it is <b>below −100 dB</b>. "
    "Cost: the lateral −6 dB width grew from 0.31 to 0.47 mm (fewer elements at shallow depth).",
]))
X(h2("7.4 Resolution and side lobes"))
X([fig(FIG / "t5_psf.png", 16, "Image of the point at (0, 20) mm (point spread function) and its profiles. The red line is −6 dB.")])
A(table([
    ["Quantity", "Measured", "What controls it"],
    ["Axial −6 dB width", "0.327–0.346 mm", "pulse length (theory 0.340 mm)"],
    ["Lateral −6 dB width", "0.471 mm", "λ × F#, apodization window"],
    ["Position error", "≤ 0.04 mm", "correct delays + time-axis rule"],
    ["Highest side lobe (Hann)", "−32.7 dB", "window shape (rect −18.2 dB, Hamming −33.3 dB)"],
], [0.3, 0.25, 0.45]))
A(example([
    "Frequency test (fs 128 MHz): axial width 0.674 / 0.327 / 0.212 mm at 4 / 8 / 12 MHz (theory 0.680 / 0.340 / 0.227) and lateral "
    "0.820 / 0.460 / 0.340 mm: both shrink as frequency rises, as λ does.",
    "T5's own verification (4 tests) passes: depth errors 0.008–0.040 mm at 15, 40 and 55 mm.",
]))
X([fig(IMG / "t5_beamformed_rf.png", 15, "T5's output beamformed_rf (3118 × 256): zoom 15–20 mm, and the centre line before envelope detection.")])
A(io_table("raw_rf, t_axis, element positions, 256 scan-line positions", "per line and depth: delay, Hann weight over the F# aperture, sum",
           "beamformed_rf (3118, 256) + z_axis (0–60 mm)", "receive_beamforming.das_beamform()"))
A(check([
    ("What are the two steps of DAS?", "Delay each channel by its travel time to the point, then add them (with weights)."),
    ("Why does the aperture grow with depth?", "To keep the F-number constant, so focusing quality is similar at all depths, and to avoid steep angles near the surface."),
    ("What trade-off does the Hann window make?", "Much lower side lobes (−32.7 vs −18.2 dB) for a wider main lobe (0.46 vs 0.30 mm)."),
    ("Why is the output still RF, not an image?", "It still oscillates at 8 MHz; T6 takes the envelope next."),
]))

# ================================================================ T6 recon
X(chapter("8", "T6 · Image reconstruction", "Envelope detection and log compression", "T6"))
A(P("<b>What this team does:</b> turns each oscillating beamformed line into a smooth brightness profile, then compresses its "
    "huge range of values so that weak and strong echoes can be shown together."))
X(h2("8.1 Envelope detection with the Hilbert transform"))
A(P("The beamformed RF wiggles up and down 8 million times a second. For a picture we only need its <b>outline</b> (envelope). "
    "The Hilbert transform H{s} makes a copy of the signal shifted by a quarter wave. Combining the two gives the "
    "<b>analytic signal</b>, whose magnitude is the envelope. It is smooth even where the RF crosses zero:"))
A(eq(r"E(z) = \left|\, s(z) + j\,\mathcal{H}\{s\}(z) \,\right|"))
X([fig(FIG / "t6_envelope_log.png", 16, "Left: real beamformed RF on the centre line and its envelope. Right: the 50 dB log-compression curve.")])
X(h2("8.2 Log compression"))
A(P("Echoes range from very strong (a bright boundary) to very weak (deep speckle), a ratio of 1000 : 1 or more. The eye cannot "
    "see that range on a screen. Taking the logarithm (decibels) squeezes it:"))
A(eq(r"L(z) = 20\,\log_{10}\!\left(\dfrac{E(z)}{\max E}\right)\ \ [\mathrm{dB}],\qquad 0\ \mathrm{dB} = \mathrm{brightest\ point}"))
A(example([
    "An echo 1/100 of the peak: 20 log₁₀(0.01) = −40 dB. Shown on a linear scale it would be 1 % gray (invisible); after 50 dB log "
    "compression it becomes (−40 + 50)/50 = <b>20 % gray</b>, clearly visible.",
]))
A(incode([
    "bmode_formation.py: scipy.signal.hilbert along depth → |·| → divide by the frame maximum → 20 log₁₀ (values below 10⁻¹² are clipped to avoid log 0).",
    "Same algorithm as the team's real-carotid notebook; on the real carotid RF it matches the team's saved output to 5×10⁻⁶.",
]))
A(io_table("beamformed_rf (3118, 256)", "Hilbert envelope, normalise to peak, 20 log₁₀", "log-compressed envelope (3118, 256) in dB, 0 dB = peak",
           "teams/T6_B_mode/bmode_formation.py"))
A(check([
    ("Why can't we display the RF directly?", "It oscillates positive and negative at 8 MHz; we need its magnitude outline (envelope)."),
    ("What does the Hilbert transform add?", "A 90°-shifted copy; together they give the analytic signal whose magnitude is the envelope."),
    ("Why logarithm?", "It compresses a huge ratio of echo strengths into a range the eye can see."),
]))

# ================================================================ T7
X(chapter("9", "T7 · B-mode image formation", "Dynamic range, gray mapping and scan conversion", "T7"))
A(P("<b>What this team does:</b> turns the dB values into a gray-scale picture with real millimetre axes and square pixels."))
X(h2("9.1 Dynamic range and gray mapping"))
A(P("We choose to show a <b>50 dB dynamic range</b>: 0 dB (peak) is white, −50 dB and weaker is black, and everything in between "
    "is a shade of gray:"))
A(eq(r"B = \dfrac{\mathrm{clip}(L,\,-\mathrm{DR},\,0) + \mathrm{DR}}{\mathrm{DR}}\ \in [0,1],\qquad \mathrm{DR} = 50\ \mathrm{dB}"))
A(key("choosing the dynamic range", [
    "A larger DR shows weaker echoes but makes the background gray and noisy; a smaller DR gives more contrast but hides weak tissue. "
    "We kept 50 dB (T3's setting). The source of the carotid data displays it at 40 dB; the B-mode notebook used 60 dB without a source.",
]))
X(h2("9.2 Scan conversion"))
A(P("After beamforming, the data is a table: 3118 depth samples × 256 lines, with cells 0.019 mm tall and 0.078 mm wide. A "
    "screen needs square pixels on a regular grid. <b>Scan conversion</b> resamples the table onto that grid."))
X(bullets([
    "A <b>linear array</b> has parallel vertical lines, so this is a simple rectangular resampling. (Phased and curved arrays have fan-shaped lines and need polar-to-Cartesian conversion.)",
    "The depth is cropped to 0–40 mm, and every new pixel is computed by <b>bilinear interpolation</b>: a weighted average of the 4 nearest table values.",
    "Pixels are square (0.078 × 0.078 mm), so circles stay circles and the filter window in T6 is the same size in both directions.",
]))
A(eq(r"f(x,z) \approx (1-u)(1-v)\,f_{00} + u(1-v)\,f_{10} + (1-u)v\,f_{01} + uv\,f_{11}", note="u, v = fractional position between the 4 neighbours"))
X([fig(FIG / "t7_scan_conversion.png", 16, "Before: a data table indexed by sample and line. After: 512 × 256 square pixels with mm axes (0.078 mm per pixel).")])
A(incode([
    "Gray map: the last step of bmode_formation() (clip to −50 dB, rescale to 0–1).",
    "Scan conversion: post_processing.scan_convert() with scipy's RegularGridInterpolator (linear) onto a square-pixel grid.",
]))
A(io_table("log-compressed envelope (T6), scan-line x-positions, z_axis", "50 dB clip, 0–1 gray map, crop to 40 mm, bilinear resample",
           "B-mode gray image (512, 256), 0.078 mm/px, values 0–1", "bmode_formation.py, post_processing.scan_convert()"))
A(check([
    ("What gray value does an echo at −25 dB get with DR = 50 dB?", "(−25 + 50)/50 = 0.5, mid-gray."),
    ("Why is scan conversion simple for our probe?", "A linear array's lines are parallel, so no fan (polar) geometry is needed."),
    ("Why square pixels?", "So distances and shapes are the same in x and z, and the filter window is isotropic in mm."),
]))

# ================================================================ T6 post
X(chapter("10", "T6 · Post-image processing", "Despeckling with the guided filter", "T6"))
A(P("<b>What this team does:</b> reduces the grainy speckle so that tissue regions look smoother, <b>without</b> blurring the edges of "
    "structures such as the cyst."))
X(h2("10.1 Why not just blur?"))
A(P("An ordinary average (box or Gaussian blur) does smooth speckle, but it smooths everything, including the edges we want to see. "
    "An <b>edge-preserving</b> filter smooths only where the image is flat."))
X(h2("10.2 The guided filter (He, Sun and Tang, 2013)"))
A(P("Inside each small window (radius r, so (2r+1) × (2r+1) pixels), the filter assumes the output is a straight-line function of "
    "the guide image I: q = a·I + b. It chooses a and b to stay close to the input while keeping a small:"))
A(eq(r"a_k = \dfrac{\mathrm{cov}_k(I,\,p)}{\mathrm{var}_k(I) + \varepsilon},\qquad b_k = \bar p_k - a_k\,\bar I_k,\qquad q = \bar a\,I + \bar b",
     note="our code is self-guided (I = p = the image); bars are box-filter means over the window"))
A(key("what ε does", [
    "In a <b>flat, speckled</b> region the local variance is small compared with ε, so a ≈ 0 and q ≈ the local mean: <b>smoothing</b>.",
    "At an <b>edge</b> the local variance is large compared with ε, so a ≈ 1 and q ≈ I: the <b>edge is kept</b>.",
    "Bigger ε → more smoothing (and eventually softer edges). Bigger r → larger smoothing window.",
]))
X([fig(FIG / "post_guided_idea.png", 14.5, "1-D illustration (made-up data): the guided filter smooths the flat parts but keeps the steps; a plain average blurs them.")])
X(h2("10.3 Our settings and their effect"))
A(P("Our settings are <b>r = 4</b> (9 × 9 window) and <b>ε = 0.001</b> on intensities scaled to 0–1. They are from the team's "
    "post-processing notebook, where they were tuned on real breast images."))
A(table([
    ["ε", "Edge sharpness kept", "gCNR (cyst)", "Notebook rule: edge ≥ 0.90"],
    ["0.001 (used)", "0.96", "0.871", "pass"],
    ["0.002", "0.93", "0.881", "pass (an option for the team)"],
    ["0.005", "0.86", "–", "fail"],
    ["0.01", "0.78", "–", "fail"],
], [0.2, 0.25, 0.2, 0.35]))
X([fig(IMG / "t7_filter_zoom.png", 16, "Before and after the filter on our cyst image: zoom, difference, one row, and histogram.")])
A(incode([
    "post_processing.postprocess(image, method='guided', r=4, eps=0.001): float image → 8-bit gray (0–255) → the notebook's "
    "guided() (box means with cv2.blur) → back to 0–1 → optional gamma (1.0 = unchanged).",
]))
A(io_table("B-mode gray image (512, 256)", "self-guided filter, r = 4, ε = 0.001", "final_bmode (512, 256), values 0–1", "post_processing.postprocess()"))
A(check([
    ("Why use a guided filter and not a Gaussian blur?", "It smooths flat speckle regions but keeps edges, because a ≈ 1 where the local variance is large."),
    ("What happens if ε is made much larger?", "More smoothing, but edges soften: at ε = 0.01 only 78 % of the edge sharpness is kept."),
    ("Does despeckling add information?", "No. It makes regions easier to see; the underlying echo data is unchanged."),
]))

# ================================================================ METRICS
X(chapter("11", "Measuring image quality", "How we prove the images are right", "all"))
A(P("Every claim in the project is backed by a number measured on the images. These are the measurements, in plain words."))
A(table([
    ["Metric", "Simple meaning", "Formula in our code", "Better when"],
    ["−6 dB width (axial / lateral)", "size of the blur of a single point", "width where the envelope is ≥ half of its peak", "smaller"],
    ["Speckle SNR", "is the speckle realistic?", "mean(E) / std(E) of the envelope", "close to 1.91"],
    ["Speckle index SI", "how grainy the image is", "mean over the image of local std / local mean (7 × 7)", "smaller"],
    ["Contrast", "how dark the cyst is", "mean(lesion) − mean(ring), in displayed dB", "more negative"],
    ["CNR", "contrast compared with the graininess", "|μ_L − μ_B| / √(σ_L² + σ_B²)", "larger"],
    ["gCNR", "how separable lesion and background pixels are (0 = identical, 1 = fully separable)", "1 − Σ min(h_L, h_B) (histogram overlap)", "closer to 1"],
    ["Edge sharpness", "how crisp the cyst border is", "mean Sobel gradient on a 3-px band around the border", "larger"],
], [0.19, 0.27, 0.36, 0.18]))
A(P("Background “B” = a ring 10 pixels (0.78 mm) wide around the lesion. The gCNR follows Rodriguez-Molares et al. (2020)."))
X(h2("11.1 Our final results"))
A(table([
    ["Phantom", "Result"],
    ["Point targets", "found at (−4.98, 10.01), (−0.04, 20.00), (+4.98, 29.99) mm; axial 0.33–0.35 mm; lateral 0.471 mm"],
    ["Speckle", "SNR 1.73–1.92 (theory 1.91); uniform across ±10 mm within 0.2 dB; SI 0.178 → 0.163 after the filter"],
    ["Cyst, before filter", "contrast −19.40 dB, CNR 2.323, gCNR 0.860, SI 0.308"],
    ["Cyst, after filter", "contrast −19.32 dB, CNR 2.425, gCNR 0.871, SI 0.241, edge kept 96 %"],
], [0.22, 0.78]))
X([fig(IMG / "final_image.png", 7.5, "Final B-mode image of the cyst phantom (50 dB, after the guided filter).")])

# ================================================================ PARAMETER TESTS
X(chapter("12", "Parameter tests: theory checked by experiment", "tests/parameter_tests.py · 9 of 9 checks pass", "all"))
A(P("Each test changes one parameter, keeps everything else the same, and checks that the result moves the way theory predicts."))
A(table([
    ["Parameter", "Theory says", "We measured", "Verdict"],
    ["Centre frequency 4 / 8 / 12 MHz", "axial width = (c/2)·2.355σ: 0.680 / 0.340 / 0.227 mm; lateral width ∝ λ", "axial 0.674 / 0.327 / 0.212 mm; lateral 0.820 / 0.460 / 0.340 mm", "✓ within 10 %"],
    ["Attenuation α₀ = 0.5 / 1.0", "extra loss −16 / −32 dB (targets 10 vs 30 mm)", "−16.11 / −32.21 dB", "✓"],
    ["Transmit focus 10 / 20 / 30 mm", "strongest when focused at the target (20 mm)", "+0.00 / +18.36 / +4.78 dB vs broadcast", "✓"],
    ["Receive window rect / Hamming / Hann", "rect: narrowest beam, highest side lobes", "0.300 / 0.420 / 0.460 mm; −18.2 / −33.3 / −32.7 dB", "✓"],
    ["Sampling 32 / 64 / 128 MHz", "position unchanged (time-axis rule); level converges", "24.987 / 25.006 / 25.006 mm; +0.00 / +2.79 / +3.39 dB", "✓"],
], [0.22, 0.32, 0.34, 0.12]))
A(box("Honest note", [
    "Two first versions of these tests failed, and were corrected only after the cause was measured: linear interpolation lowers the "
    "level at low sampling rates (so the test now checks convergence), and 40 MHz under-samples 12 MHz for a width measurement "
    "(so the frequency test runs at 128 MHz). Details: docs/MODULES.md, Section 11."], ORANGE_BG, ORANGE))

# ================================================================ LIMITATIONS
X(chapter("13", "Assumptions and limitations", "What our model does not include", "all"))
A(table([
    ["Assumption", "What it means", "Effect"],
    ["2-D model", "no element height, no out-of-plane echoes", "real images have some extra blur and clutter"],
    ["Straight rays, one speed of sound", "no refraction, fat/muscle speed differences", "real images can have small position errors"],
    ["Linear, point scatterers", "no nonlinear (harmonic) propagation, no specular boundaries", "no tissue-harmonic imaging"],
    ["One broadcast transmit", "focusing only on receive", "transmit focus would add ~18 dB at its depth"],
    ["No TGC", "no depth gain correction", "at 8 MHz the image is 17.2 dB darker at 36–40 mm than at 8–12 mm"],
    ["Probe values", "pitch 0.30 mm and f₀ 8 MHz are T2's assumptions (Philips publishes 128 elements, 4–12 MHz)", "resolution numbers depend on them"],
    ["Phantoms, not organs", "points, speckle and a cyst; no anatomy", "a real body model would need CT/MRI tissue maps"],
    ["Residual artefact", "a faint −25 dB diagonal arc near the (−5, 10) mm target", "not fully explained (documented)"],
], [0.22, 0.43, 0.35]))
A(P("<b>TGC</b> (time-gain compensation) is what real scanners do to undo attenuation: they amplify later echoes more. Our model "
    "does not add it, so deep regions look darker, which is physically correct for the raw signal."))

# ================================================================ GLOSSARY
X(chapter("14", "Glossary", "Words used in this project, in one line each", "all"))
glossary = [
    ("Anechoic", "a region with no echoes; appears black (our cyst)."),
    ("Apodization", "weighting the elements (e.g. Hann) to reduce side lobes."),
    ("Aperture", "the part of the array in use; full array = 38.4 mm."),
    ("Attenuation", "loss of sound energy with distance; 0.5 dB/(MHz·cm)."),
    ("Axial / lateral", "along the beam (depth) / across it (sideways)."),
    ("B-mode", "brightness mode: echo strength shown as gray level."),
    ("Beamforming", "combining element signals to transmit or listen in one direction/point."),
    ("Broadcast transmit", "all elements fire together with no delays."),
    ("CNR / gCNR", "contrast-to-noise ratio / generalized CNR (0–1, lesion detectability)."),
    ("DAS", "delay-and-sum beamforming."),
    ("dB", "decibel, 20 log₁₀ of an amplitude ratio."),
    ("Directivity", "how an element's sensitivity changes with angle (sinc pattern)."),
    ("Dynamic range", "span of dB values displayed (50 dB)."),
    ("Dynamic receive focus", "receive delays recomputed at every depth."),
    ("Envelope", "smooth outline (magnitude) of an oscillating signal."),
    ("F-number (F#)", "depth ÷ active aperture width; ours = 1."),
    ("Grating lobe", "false copy of an object caused by pitch > λ/2."),
    ("Guided filter", "edge-preserving smoothing filter used for despeckling."),
    ("Hilbert transform", "90° phase-shifted copy of a signal, used to get the envelope."),
    ("Impedance (acoustic)", "Z = density × speed; changes in Z cause echoes."),
    ("Linear array", "elements in a straight row with parallel scan lines."),
    ("Nyquist rule", "sample at more than twice the highest frequency."),
    ("Phantom", "a test object (points, speckle, cyst) that stands in for a patient."),
    ("Piezoelectric", "material that converts voltage into vibration and back."),
    ("Pitch", "centre-to-centre element spacing (0.30 mm)."),
    ("RF signal", "raw echo signal oscillating at MHz."),
    ("Scan conversion", "resampling the line data onto a square-pixel display grid."),
    ("Scan line", "one vertical image column formed by beamforming."),
    ("Side lobe", "weaker beam beside the main beam; lowered by apodization."),
    ("Speckle", "granular interference pattern from many sub-wavelength scatterers."),
    ("Speckle index (SI)", "average local std / mean; lower = smoother."),
    ("TGC", "time-gain compensation: extra gain for deeper echoes (not modelled)."),
    ("Time of flight", "travel time of sound = distance / c."),
]
A(table([["Term", "Meaning"]] + [[f"<b>{a}</b>", b] for a, b in glossary], [0.27, 0.73]))

# ================================================================ FORMULA SHEET
X(chapter("15", "Formula sheet", "Every equation of the pipeline on one page", "all"))
formulas = [
    ("Wavelength", r"\lambda = c/f_0"),
    ("Depth from time", r"z = c\,t/2"),
    ("Element positions (T1)", r"x_n = (n-\frac{N-1}{2})\,p"),
    ("Grating angle", r"\sin\theta_g = \lambda/p"),
    ("Directivity", r"D = \mathrm{sinc}(w\,\sin\theta/\lambda)"),
    ("Pulse (T2/T3)", r"p(t)=\sin(2\pi f_0 t)\,e^{-t^2/2\sigma^2},\ \sigma = 3/(2f_0)"),
    ("Focus delays (T2)", r"\tau_n = (\max_n d_n - d_n)/c"),
    ("Attenuation (T3)", r"A = 10^{-\alpha_0 f_0 d/20}"),
    ("Reflection (T4)", r"R = (Z_2-Z_1)/(Z_2+Z_1),\ G = \mathrm{amp}(1+|R|)\,\mathrm{scale}"),
    ("Speckle SNR", r"\sqrt{\pi/(4-\pi)} = 1.91"),
    ("DAS (T5)", r"s(z) = \sum_m w_m\,\mathrm{rf}_m(\tau_{TX}+\tau_{RX,m}) / \sum_m w_m"),
    ("Aperture (T5)", r"a(z) = \max(z/2F_\#,\ 2p)"),
    ("Envelope (T6)", r"E = |s + j\mathcal{H}\{s\}|"),
    ("Log compression (T6)", r"L = 20\log_{10}(E/\max\,E)"),
    ("Gray map (T7)", r"B = (\mathrm{clip}(L,-50,0)+50)/50"),
    ("Guided filter (T6)", r"a = \mathrm{cov}/(\mathrm{var}+\varepsilon),\ q = \bar a I + \bar b"),
    ("CNR", r"|\mu_L-\mu_B|/\sqrt{\sigma_L^2+\sigma_B^2}"),
    ("gCNR", r"1-\sum\min(h_L,h_B)"),
]
rows = [["Quantity", "Equation"]]
for name, tex in formulas:
    rows.append([name, eq(tex, size=10.5, width=0.72 * TEXT_W - 12, align="LEFT")])
t = Table([[Paragraph(r[0], S["cellh" if i == 0 else "cellb"]), (Paragraph(r[1], S["cellh"]) if i == 0 else r[1])]
           for i, r in enumerate(rows)], colWidths=[0.28 * TEXT_W, 0.72 * TEXT_W])
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3de")),
                       ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]
                      + [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f8fb")) for i in range(2, len(rows), 2)]))
A(t)

# ================================================================ REFERENCES
X(chapter("16", "References and further reading", "", "all"))
refs = [
    "T. L. Szabo, <i>Diagnostic Ultrasound Imaging: Inside Out</i>, 2nd ed., Academic Press, 2014. (General textbook: propagation, attenuation, arrays, beamforming, B-mode.)",
    "J. A. Jensen, “Field: A program for simulating ultrasound systems,” <i>Medical &amp; Biological Engineering &amp; Computing</i>, 34 (Suppl. 1), 351–353, 1996. (Point-scatterer phantoms, element directivity.)",
    "C. B. Burckhardt, “Speckle in ultrasound B-mode scans,” <i>IEEE Trans. Sonics and Ultrasonics</i>, 25(1), 1–6, 1978.",
    "R. F. Wagner, S. W. Smith, J. M. Sandrik and H. Lopez, “Statistics of speckle in ultrasound B-scans,” <i>IEEE Trans. Sonics and Ultrasonics</i>, 30(3), 156–163, 1983. (Rayleigh statistics, SNR 1.91.)",
    "K. He, J. Sun and X. Tang, “Guided image filtering,” <i>IEEE Trans. Pattern Analysis and Machine Intelligence</i>, 35(6), 1397–1409, 2013.",
    "A. Rodriguez-Molares et al., “The generalized contrast-to-noise ratio: a formal definition for lesion detectability,” <i>IEEE Trans. Ultrasonics, Ferroelectrics and Frequency Control</i>, 67(4), 745–759, 2020.",
    "Philips L12-4 (FUS4103) linear transducer: product information (128 elements, 4–12 MHz).",
    "Project documents: docs/MODULES.md (per-module reference), docs/README.md (development log), docs/NITK-UsoundSim_Project_Flow.pdf, demo.ipynb.",
]
X([Paragraph(r, S["bullet"], bulletText=f"[{i}]") for i, r in enumerate(refs, 1)])
A(Spacer(1, 12))
A(box("How this guide was made", [
    "Figures: docs/source/make_theory_figures.py (from config.py, the teams' code and results/*.npz). PDF: docs/source/make_theory_pdf.py. "
    "Measured numbers come from simulator/main.py, tests/parameter_tests.py and T5's verify_beamformer.py, as recorded in docs/MODULES.md."]))

# ---------------------------------------------------------------- build
doc = Doc(OUT)
doc.multiBuild(story)
print("written", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB")
