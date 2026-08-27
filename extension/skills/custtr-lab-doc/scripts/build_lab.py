"""
AMD Lab Document Builder
Generates a .docm file that precisely matches the AMD training lab template.

Key facts verified against real reference labs (C:/SET2/F3/Lab Docs/):
  - LabListNumber1/2 use SEQ field codes (NOT w:numPr list numbering)
  - Number prefix font: Segoe UI Bold, sz=24 (L1) / sz=20 (L2)
  - Images use VML format (<w:pict><v:shape><v:imagedata>), NOT DrawingML
  - QuestionHeading uses SEQ QNum field for auto-numbering
  - QuestionLine uses the QuestionLine style (tab + underline in style definition)
  - AllowPageBreak (1pt invisible) is the section spacer between H2 sections
  - StepHeading: left text + <w:tab/> + "Step " + SEQ StepHeading field
  - Version string appears in Sub-title style immediately after Heading1
  - Colors: AMD teal = 007C97, dark blue heading = 003366

Usage:
    python build_lab.py --config lab_config.json
                        --template <path_to_.docm>
                        --output <output.docm>
"""

import argparse
import datetime
import json
import os
import re
import shutil
import urllib.request
import zipfile


# ── XML character escaping ─────────────────────────────────────────────────────

def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ── Basic run builders ─────────────────────────────────────────────────────────

def run(text, extra_rpr=''):
    return f'<w:r><w:rPr>{extra_rpr}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def run_bold(text):
    return f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def run_special_bold(text):
    """SpecialBold character style — used for UI element names (menu items, buttons)."""
    return (f'<w:r><w:rPr><w:rStyle w:val="SpecialBold"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>')


def run_monospace(text):
    """Monospace character style for inline code."""
    return (f'<w:r><w:rPr><w:rStyle w:val="Monospace"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>')


def run_plain(text):
    return f'<w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


# ── SEQ field builder (the actual numbering mechanism in real AMD labs) ────────

def seq_field(seq_name, instruction, display_value):
    """
    Build a complete w:fldChar begin/instrText/separate/value/end block.
    instruction: e.g. ' SEQ StepHeading \\C \\* MERGEFORMAT '
    display_value: the pre-calculated numeric value (for Word to show before field update)
    """
    return (
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/></w:rPr>'
        f'<w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/></w:rPr>'
        f'<w:instrText xml:space="preserve">{esc(instruction)}</w:instrText></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/></w:rPr>'
        f'<w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>'
        f'<w:noProof/></w:rPr>'
        f'<w:t>{esc(str(display_value))}</w:t></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/></w:rPr>'
        f'<w:fldChar w:fldCharType="end"/></w:r>'
    )


def seq_field_sz20(seq_name, instruction, display_value):
    """Same as seq_field but sz=20 (10pt) for LabListNumber2 prefix runs."""
    SZ = '<w:sz w:val="20"/>'
    return (
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
        f'<w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
        f'<w:instrText xml:space="preserve">{esc(instruction)}</w:instrText></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
        f'<w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>'
        f'<w:noProof/>{SZ}</w:rPr>'
        f'<w:t>{esc(str(display_value))}</w:t></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
        f'<w:fldChar w:fldCharType="end"/></w:r>'
    )


def dash_run(sz20=False):
    SZ = '<w:sz w:val="20"/>' if sz20 else ''
    return (f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
            f'<w:t>-</w:t></w:r>')


def dot_run(sz20=False):
    SZ = '<w:sz w:val="20"/>' if sz20 else ''
    return (f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
            f'<w:t>.</w:t></w:r>')


def tab_run(sz20=False):
    SZ = '<w:sz w:val="20"/>' if sz20 else ''
    return (f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Bold" w:hAnsi="Segoe UI Bold"/>{SZ}</w:rPr>'
            f'<w:tab/></w:r>')


# ── Global step counters ───────────────────────────────────────────────────────

_step_heading_num = 0   # current StepHeading group (1, 2, 3…)
_stepx_num = 0          # LabListNumber1 counter within current group
_stepxx_num = 0         # LabListNumber2 counter within current L1
_qnum = 0               # Question counter


def reset_counters():
    global _step_heading_num, _stepx_num, _stepxx_num, _qnum
    _step_heading_num = 0
    _stepx_num = 0
    _stepxx_num = 0
    _qnum = 0


def next_step_heading():
    global _step_heading_num, _stepx_num, _stepxx_num
    _step_heading_num += 1
    _stepx_num = 0
    _stepxx_num = 0
    return _step_heading_num


def next_stepx():
    global _stepx_num, _stepxx_num
    _stepx_num += 1
    _stepxx_num = 0
    return _stepx_num


def next_stepxx():
    global _stepxx_num
    _stepxx_num += 1
    return _stepxx_num


def next_qnum():
    global _qnum
    _qnum += 1
    return _qnum


# ── Paragraph style wrapper ────────────────────────────────────────────────────

def para(style, *content, extra_ppr=''):
    body = ''.join(content)
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra_ppr}</w:pPr>{body}</w:p>')


def para_keep(style, *content, extra_ppr=''):
    body = ''.join(content)
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/><w:keepNext/>{extra_ppr}</w:pPr>{body}</w:p>')


# ── Smart text run (auto-bold Note:/Important:/Warning: prefix) ────────────────

def smart_runs(text):
    """Auto-bold Note:/Important:/Warning: prefixes using SpecialBold character style."""
    m = re.match(r'^(Note|Important|Warning|Caution|Tip)(:\s*)(.*)', text, re.DOTALL)
    if m:
        return run_special_bold(m.group(1) + m.group(2)) + run_plain(m.group(3))
    return run_plain(text)


# ── Section spacer ─────────────────────────────────────────────────────────────

def allow_page_break():
    """1pt invisible spacer paragraph (AllowPageBreak) between major sections."""
    return '<w:p><w:pPr><w:pStyle w:val="AllowPageBreak"/></w:pPr></w:p>'


def spacer():
    return '<w:p><w:pPr><w:pStyle w:val="GeneralFlowSpacer"/></w:pPr></w:p>'


# ── Common paragraph builders ──────────────────────────────────────────────────

def h2(text):
    return para_keep('Heading2', run_plain(text))


def body_text(text):
    return f'<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr>{smart_runs(text)}</w:p>'


def body_text_mixed(*runs_xml):
    return f'<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr>{"".join(runs_xml)}</w:p>'


def general(text):
    return f'<w:p><w:pPr><w:pStyle w:val="General"/></w:pPr>{smart_runs(text)}</w:p>'


def bullet(text):
    return para('ListBullet', run_plain(text))


def list_continue(text):
    return f'<w:p><w:pPr><w:pStyle w:val="ListContinue"/></w:pPr>{smart_runs(text)}</w:p>'


def list_continue2(text, keep_next=False):
    kn = '<w:keepNext/>' if keep_next else ''
    return (f'<w:p><w:pPr><w:pStyle w:val="ListContinue2"/>{kn}</w:pPr>'
            f'{smart_runs(text)}</w:p>')


def list_continue2_code(text, keep_next=False):
    kn = '<w:keepNext/>' if keep_next else ''
    return (f'<w:p><w:pPr><w:pStyle w:val="ListContinue2"/>{kn}</w:pPr>'
            f'<w:r><w:rPr><w:rStyle w:val="Monospace"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def warning_box(text):
    """Warning/Note box with border."""
    return (f'<w:p><w:pPr><w:pStyle w:val="Warning"/>'
            f'<w:ind w:left="120"/></w:pPr>'
            f'{smart_runs(text)}</w:p>')


def lab_list_number1_continue(text):
    """LabListNumber1Continue — bold continuation of an L1 step."""
    return (f'<w:p><w:pPr><w:pStyle w:val="LabListNumber1Continue"/></w:pPr>'
            f'{smart_runs(text)}</w:p>')


def lab_list_number1_continue_nb(text):
    """LabListNumber1ContinueNotBold — plain (non-bold) continuation of an L1 step.
    Used for cross-references, hints, and instructional notes under a primary step."""
    return (f'<w:p><w:pPr><w:pStyle w:val="LabListNumber1ContinueNotBold"/></w:pPr>'
            f'{smart_runs(text)}</w:p>')


def table_and_question_spacer():
    """TableandQuestionSpacer — vertical spacer used after questions near tables."""
    return '<w:p><w:pPr><w:pStyle w:val="TableandQuestionSpacer"/></w:pPr></w:p>'


def caption_para(text):
    """Caption paragraph — auto-increments figure counter."""
    fig_n = next_figure()
    lab = _lab_num
    cleaned = re.sub(r'^Figure\s+[\d\-‑]+[:\s]*', '', str(text)).strip()
    label = f'Figure {lab}-{fig_n}: {cleaned}' if cleaned else f'Figure {lab}-{fig_n}'
    return para('Caption', run_plain(label))


def lab_list_number2_bullet(text):
    no_bold = f'<w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    return para_keep('LabListNumber2Bullet', no_bold)


# ── StepHeading builder (exact SEQ field pattern from real docs) ───────────────

def step_heading(title):
    """
    Builds a StepHeading paragraph:
      [title text] <tab> Step [SEQ StepHeading \\R N or \\C]
    First step in the document resets with \\R 1; subsequent steps use \\C.
    """
    n = next_step_heading()
    instr = f' SEQ StepHeading \\R {n} \\* MERGEFORMAT '
    seq = (
        f'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{esc(instr)}</w:instrText></w:r>'
        f'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:rPr><w:noProof/></w:rPr><w:t>{n}</w:t></w:r>'
        f'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )
    return (
        f'<w:p><w:pPr><w:pStyle w:val="StepHeading"/><w:keepNext/></w:pPr>'
        f'<w:r><w:t>{esc(title)}</w:t></w:r>'
        f'<w:r><w:tab/><w:t xml:space="preserve">Step </w:t></w:r>'
        f'{seq}</w:p>'
    )


# ── LabListNumber1 builder (exact SEQ field pattern) ──────────────────────────

def lab1(text, is_first_in_step=False):
    """
    LabListNumber1: format [S]-[N].  tab  bold-text
    S = StepHeading counter (\\C — always continue)
    N = Stepx counter (\\R 1 on first in step, then \\* MERGEFORMAT to continue)
    Number prefix: Segoe UI Bold, 12pt (sz=24)
    Body text: plain Arial (inherits from style)
    """
    n = next_stepx()
    s = _step_heading_num

    instr_s = ' SEQ StepHeading \\C \\* MERGEFORMAT '
    instr_n_first = ' SEQ Stepx \\R 1 \\* MERGEFORMAT '
    instr_n_cont = ' SEQ Stepx \\* MERGEFORMAT '
    instr_n = instr_n_first if n == 1 else instr_n_cont

    prefix = (
        seq_field('StepHeading', instr_s, s)
        + dash_run()
        + seq_field('Stepx', instr_n, n)
        + dot_run()
        + tab_run()
    )
    body_run = f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    return (f'<w:p><w:pPr><w:pStyle w:val="LabListNumber1"/><w:keepNext/></w:pPr>'
            f'{prefix}{body_run}</w:p>')


# ── LabListNumber2 builder ─────────────────────────────────────────────────────

def lab2(text):
    """
    LabListNumber2: format [S]-[N]-[M].  tab  plain-text
    Number prefix: Segoe UI Bold, sz=20 (10pt)
    """
    m = next_stepxx()
    s = _step_heading_num
    n = _stepx_num

    instr_s = ' SEQ StepHeading \\C \\* MERGEFORMAT '
    instr_n = ' SEQ Stepx \\C  \\* MERGEFORMAT '
    instr_m_first = ' SEQ Stepxx \\R 1 \\* MERGEFORMAT '
    instr_m_cont = ' SEQ Stepxx \\C \\* MERGEFORMAT '
    instr_m = instr_m_first if m == 1 else instr_m_cont

    prefix = (
        seq_field_sz20('StepHeading', instr_s, s)
        + dash_run(sz20=True)
        + seq_field_sz20('Stepx', instr_n, n)
        + dash_run(sz20=True)
        + seq_field_sz20('Stepxx', instr_m, m)
        + dot_run(sz20=True)
        + tab_run(sz20=True)
    )
    body_run = f'<w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    return (f'<w:p><w:pPr><w:pStyle w:val="LabListNumber2"/><w:keepNext/></w:pPr>'
            f'{prefix}{body_run}</w:p>')


# ── QuestionHeading (SEQ QNum field) ──────────────────────────────────────────

def question_heading():
    n = next_qnum()
    instr = f' SEQ QNum \\R {n} \\* MERGEFORMAT ' if n == 1 else ' SEQ QNum \\C \\* MERGEFORMAT '
    seq = (
        f'<w:fldSimple w:instr="{esc(instr)}">'
        f'<w:r><w:rPr><w:noProof/></w:rPr><w:t>{n}</w:t></w:r>'
        f'</w:fldSimple>'
    )
    return (f'<w:p><w:pPr><w:pStyle w:val="QuestionHeading"/><w:keepNext/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">Question </w:t></w:r>'
            f'{seq}</w:p>')


def question_body(text):
    return para('QuestionBody', run_plain(text))


def question_line():
    """QuestionLine — one underlined answer line with explicit underline on the tab run."""
    return (
        '<w:p><w:pPr><w:pStyle w:val="QuestionLine"/></w:pPr>'
        '<w:r><w:rPr><w:u w:val="single"/></w:rPr><w:tab/></w:r>'
        '</w:p>'
    )


def question_in_answer(text):
    return para('QuestioninAnswerSection', run_plain(text),
                extra_ppr='<w:ind w:left="360"/>')


def answer_body(text):
    return para('AnswerBody', run_plain(text))


# ── Figure counter ─────────────────────────────────────────────────────────────

_figure_counter = 0
_lab_num = 1


def reset_figures(lab_num=1):
    global _figure_counter, _lab_num
    _figure_counter = 0
    _lab_num = lab_num


def next_figure():
    global _figure_counter
    _figure_counter += 1
    return _figure_counter


# ── Image embedding (VML format — matching real AMD labs) ─────────────────────

# Local images folder — sibling of this script's parent directory
IMAGE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'images')

_images = {}       # rel_id -> (fname, data, ext)
_img_counter = 100  # start above template's own media files (image1.jpg–image5.png)


def reset_images():
    global _images, _img_counter
    _images = {}
    _img_counter = 100  # start above template's own media files (image1.jpg–image5.png)


def get_image_dims(data):
    import struct
    if data[:8] == bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]):
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:2] == bytes([0xFF, 0xD8]):
        i = 2
        while i < len(data) - 4:
            if data[i] != 0xFF:
                break
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + length
    return None, None


def embed_image(url_or_path):
    """Store image for embedding. Returns (rel_id, width_pt, height_pt) or None.

    Accepts:
      - http/https URL  — fetched directly
      - absolute path   — read from disk as-is
    """
    global _img_counter
    _img_counter += 1
    rel_id = f'rImgId{_img_counter}'

    if url_or_path.startswith('http'):
        try:
            req = urllib.request.Request(url_or_path, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            ext = '.png'
        except Exception as e:
            print(f'  [warn] Could not fetch image {url_or_path}: {e}')
            return None
    else:
        candidates = [
            os.path.join(IMAGE_DB, url_or_path),                        # local images/ folder (downloaded from GitHub)
            os.path.join('Y:/Graphics_Repository', url_or_path),        # network graphics repository
            url_or_path,                                                  # absolute path fallback
        ]
        resolved = next((p for p in candidates if os.path.exists(p)), None)
        if resolved is None:
            print(f'  [warn] Image not found: {url_or_path}')
            return None
        ext = os.path.splitext(resolved)[1].lower() or '.png'
        with open(resolved, 'rb') as f:
            data = f.read()

    fname = f'image{_img_counter}{ext}'
    _images[rel_id] = (fname, data)

    w_px, h_px = get_image_dims(data)
    if w_px and h_px:
        # Scale to fit 5.5 inches at 96 dpi, convert to points
        max_w_pt = 396  # 5.5in × 72pt/in
        w_pt = w_px * 72 / 96
        h_pt = h_px * 72 / 96
        if w_pt > max_w_pt:
            h_pt = h_pt * max_w_pt / w_pt
            w_pt = max_w_pt
    else:
        w_pt, h_pt = 360, 216  # 5in × 3in fallback

    return rel_id, w_pt, h_pt


def vml_image_para(rel_id, w_pt, h_pt, style_name='ListContinue2', keep_next=True):
    """
    Embed image using VML format (matching real AMD lab docs exactly).
    Uses <w:pict><v:shape><v:imagedata> — not DrawingML.
    """
    global _img_counter
    shape_id = f'_x0000_i{5000 + _img_counter}'
    kn = '<w:keepNext/><w:spacing w:before="160"/>' if keep_next else ''
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{style_name}"/>{kn}</w:pPr>'
        f'<w:r><w:pict>'
        f'<v:shape id="{shape_id}" type="#_x0000_t75" '
        f'style="width:{w_pt:.0f}pt;height:{h_pt:.0f}pt"'
        f' xmlns:v="urn:schemas-microsoft-com:vml"'
        f' xmlns:o="urn:schemas-microsoft-com:office:office"'
        f' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<v:imagedata r:id="{rel_id}" o:title=""/>'
        f'<o:lock v:ext="edit" aspectratio="f"/>'
        f'</v:shape>'
        f'</w:pict></w:r></w:p>'
    )


def write_images_to_zip(work_dir):
    if not _images:
        return
    media_dir = os.path.join(work_dir, 'word', 'media')
    os.makedirs(media_dir, exist_ok=True)
    rels_path = os.path.join(work_dir, 'word', '_rels', 'document.xml.rels')
    with open(rels_path, 'r', encoding='utf-8') as f:
        rels_xml = f.read()
    new_rels = ''
    for rel_id, (fname, data) in _images.items():
        with open(os.path.join(media_dir, fname), 'wb') as f:
            f.write(data)
        new_rels += (
            f'<Relationship Id="{rel_id}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{fname}"/>'
        )
    rels_xml = rels_xml.replace('</Relationships>', new_rels + '</Relationships>')
    with open(rels_path, 'w', encoding='utf-8') as f:
        f.write(rels_xml)


# ── Table builder ──────────────────────────────────────────────────────────────

def tbl_cell(text, width, style='TableBodyText', bold=False, center=False, monospace=False):
    cell_style = 'TableBodyTextCenter' if center else style
    lines = str(text).split('\n')
    cell_xml = ''
    for line in lines:
        if monospace:
            cell_xml += (
                f'<w:p><w:pPr><w:pStyle w:val="{cell_style}"/></w:pPr>'
                f'<w:r><w:rPr><w:rStyle w:val="Monospace"/></w:rPr>'
                f'<w:t xml:space="preserve">{esc(line)}</w:t></w:r></w:p>'
            )
        else:
            b = '<w:b/>' if bold else ''
            cell_xml += (
                f'<w:p><w:pPr><w:pStyle w:val="{cell_style}"/></w:pPr>'
                f'<w:r><w:rPr>{b}</w:rPr>'
                f'<w:t xml:space="preserve">{esc(line)}</w:t></w:r></w:p>'
            )
    return f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>{cell_xml}</w:tc>'


def make_table(rows, widths, monospace_cols=None):
    mono = set(monospace_cols or [])
    total = sum(widths)
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    xml = (
        f'<w:tbl><w:tblPr>'
        f'<w:tblStyle w:val="TableGrid"/>'
        f'<w:tblW w:w="{total}" w:type="dxa"/>'
        f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
    )
    for i, row in enumerate(rows):
        is_hdr = (i == 0)
        cells = ''
        for j, cell in enumerate(row):
            cells += tbl_cell(
                str(cell), widths[j],
                bold=is_hdr,
                center=is_hdr,
                monospace=(j in mono and not is_hdr)
            )
        xml += f'<w:tr>{cells}</w:tr>'
    xml += '</w:tbl>'
    return xml


# ── General Flow table (step boxes with arrow cells) ──────────────────────────

def _general_flow_arrow_vml(rel_id):
    """
    VML arrow image cell — 18pt x 15pt, matching real AMD lab General Flow exactly.
    Arrow cell has only a right border (single sz=6), top/left/bottom are nil.
    """
    global _img_counter
    shape_id = f'_x0000_i{7000 + _img_counter}'
    return (
        f'<w:tc><w:tcPr>'
        f'<w:tcW w:w="576" w:type="dxa"/>'
        f'<w:tcBorders>'
        f'<w:top w:val="nil"/>'
        f'<w:left w:val="nil"/>'
        f'<w:bottom w:val="nil"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
        f'</w:tcBorders>'
        f'<w:tcMar>'
        f'<w:top w:w="0" w:type="dxa"/><w:left w:w="62" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="62" w:type="dxa"/>'
        f'</w:tcMar>'
        f'<w:vAlign w:val="center"/></w:tcPr>'
        f'<w:p><w:pPr>'
        f'<w:pStyle w:val="TableBodyTextCenter"/>'
        f'<w:spacing w:before="160"/>'
        f'</w:pPr>'
        f'<w:r><w:pict>'
        f'<v:shape id="{shape_id}" type="#_x0000_t75" style="width:18pt;height:15pt"'
        f' xmlns:v="urn:schemas-microsoft-com:vml"'
        f' xmlns:o="urn:schemas-microsoft-com:office:office"'
        f' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<v:imagedata r:id="{rel_id}" o:title=""/>'
        f'<o:lock v:ext="edit" aspectratio="f"/>'
        f'</v:shape>'
        f'</w:pict></w:r></w:p></w:tc>'
    )


def make_general_flow(steps_list, max_per_row=4):
    """
    General Flow table matching real AMD lab format exactly:
    - Step boxes: bordered cells with 'Step N:\\n<title>' using TableBodyTextCenter style
    - Arrow cells: VML PNG arrow image (18pt x 15pt), right-border only
    - Cell margins: left/right = 62 dxa (matching reference labs)
    - Table width: auto (w=0, type=auto) with fixed layout
    """
    # Embed the arrow image once
    arrow_path = os.path.join(IMAGE_DB, 'general_flow_arrow.png')
    arrow_rel_id = None
    if os.path.exists(arrow_path):
        global _img_counter
        _img_counter += 1
        arrow_rel_id = f'rImgId{_img_counter}'
        with open(arrow_path, 'rb') as f:
            arrow_data = f.read()
        _images[arrow_rel_id] = ('general_flow_arrow.png', arrow_data)

    box_border = (
        '<w:tcBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
        '</w:tcBorders>'
    )
    box_margin = (
        '<w:tcMar>'
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="62" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="62" w:type="dxa"/>'
        '</w:tcMar>'
    )

    parts = []
    rows = [steps_list[i:i + max_per_row] for i in range(0, len(steps_list), max_per_row)]

    for row_items in rows:
        n = len(row_items)
        step_w = 1440  # each step box = 1 inch (1440 dxa), matching real labs
        arrow_w = 576  # arrow cell width from real lab XML

        col_widths, col_labels = [], []
        for idx, label in enumerate(row_items):
            col_widths.append(step_w)
            col_labels.append(label)
            if idx < n - 1:
                col_widths.append(arrow_w)
                col_labels.append(None)  # None = arrow cell

        total = sum(col_widths)
        grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)

        tbl_xml = (
            f'<w:tbl><w:tblPr>'
            f'<w:tblW w:w="0" w:type="auto"/>'
            f'<w:tblLayout w:type="fixed"/>'
            f'<w:tblCellMar>'
            f'<w:left w:w="62" w:type="dxa"/>'
            f'<w:right w:w="62" w:type="dxa"/>'
            f'</w:tblCellMar>'
            f'<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" '
            f'w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0"/>'
            f'</w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid>'
            f'<w:tr><w:trPr><w:cantSplit/></w:trPr>'
        )

        step_num = 0
        for label, w in zip(col_labels, col_widths):
            if label is None:
                # Arrow cell — use VML image if available, else fall back to text
                if arrow_rel_id:
                    tbl_xml += _general_flow_arrow_vml(arrow_rel_id)
                else:
                    tbl_xml += (
                        f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
                        f'<w:vAlign w:val="center"/></w:tcPr>'
                        f'<w:p><w:pPr><w:pStyle w:val="TableBodyTextCenter"/></w:pPr>'
                        f'<w:r><w:t>&#x21D2;</w:t></w:r></w:p></w:tc>'
                    )
            else:
                step_num += 1
                # Step box: "Step N:\n<title>" with line breaks, TableBodyTextCenter
                # Build paragraph with runs and <w:br/> separating step number from title
                cell_p = (
                    f'<w:p><w:pPr><w:pStyle w:val="TableBodyTextCenter"/></w:pPr>'
                    f'<w:r><w:t xml:space="preserve">Step {step_num}: </w:t></w:r>'
                    f'<w:r><w:br/>'
                )
                # Split long titles across multiple lines using <w:br/>
                words = label.split()
                # wrap at ~20 chars per line
                line, cell_runs = '', []
                for word in words:
                    if len(line) + len(word) + 1 > 18 and line:
                        cell_runs.append(line.strip())
                        line = word + ' '
                    else:
                        line += word + ' '
                if line.strip():
                    cell_runs.append(line.strip())

                for i, ln in enumerate(cell_runs):
                    if i == 0:
                        cell_p += f'<w:t xml:space="preserve">{esc(ln)}</w:t></w:r>'
                    else:
                        cell_p += f'<w:r><w:br/><w:t xml:space="preserve">{esc(ln)}</w:t></w:r>'
                cell_p += '</w:p>'

                tbl_xml += (
                    f'<w:tc><w:tcPr>'
                    f'<w:tcW w:w="{step_w}" w:type="dxa"/>'
                    f'{box_border}{box_margin}'
                    f'<w:vAlign w:val="center"/>'
                    f'</w:tcPr>{cell_p}</w:tc>'
                )

        tbl_xml += '</w:tr></w:tbl>'
        parts.append(tbl_xml)
        parts.append(spacer())

    return ''.join(parts)


# ── TOC helpers ────────────────────────────────────────────────────────────────

def toc_title(text):
    return (
        f'<w:p><w:pPr><w:pStyle w:val="TOCTitle"/>'
        f'<w:pBdr><w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/></w:pBdr>'
        f'</w:pPr><w:r><w:t>{esc(text)}</w:t></w:r></w:p>'
    )


def toc1(text, page=''):
    content = f'<w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    if page:
        content += f'<w:r><w:tab/></w:r><w:r><w:t>{esc(str(page))}</w:t></w:r>'
    return f'<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr>{content}</w:p>'


# ── Nomenclature table (fixed AMD standard) ────────────────────────────────────

NOMENCLATURE_ROWS = [
    ['Symbol', 'Description', 'Example', 'Explanation'],
    ['<text>', 'Indicates a field', 'cd <dir>',
     '<dir> represents the name of the directory. The < and > symbols are NOT entered. '
     'If the directory to change to is XYZ, then you would enter cd XYZ into the environment.'],
    ['[text]', 'Indicates an optional argument', 'ls [ | more]',
     'This could be interpreted as ls <Enter> or ls | more <Enter>. The first instance lists '
     'the files in the current Linux directory, and the second lists the files in the current '
     'Linux directory, but additionally runs the output through the more tool, which paginates '
     'the output. Here, the pipe symbol (|) is a Linux operator.'],
    ['|', 'Indicates choices', 'cmd <ZCU104 | VCK190>',
     'The cmd command takes a single argument, which could be ZCU104 OR VCK190. '
     'You would enter either cmd ZCU104 or cmd VCK190.'],
]
NOMENCLATURE_WIDTHS = (1200, 1800, 1800, 4560)


# ── Instruction renderer ───────────────────────────────────────────────────────

def render_instruction(instruction, parts):
    """
    Render a single instruction dict. Keys:
      action          — LabListNumber1 primary step (auto-increments L1 counter)
      substep         — LabListNumber2 sub-step (auto-increments L2 counter)
      command         — ListContinue2 monospace code block
      note            — ListContinue2 plain (smart Note:/Important: bolding)
      continue        — ListContinue plain continuation
      lab1_continue   — LabListNumber1Continue (bold continuation of L1 step)
      lab1_continue_nb— LabListNumber1ContinueNotBold (plain hint/cross-ref under L1)
      warning         — Warning box with border
      bullet2         — LabListNumber2Bullet
      image           — URL/path to image (relative to images/ or T:\\Graphics_Repository\\)
      caption         — figure caption (auto-numbered as Figure N-M)
      question        — QuestionHeading + QuestionBody + N QuestionLines (default 3)
      question_body   — standalone QuestionBody paragraph
      answer          — AnswerBody paragraph (used in answers section rendering)
      table           — inline table dict {rows, widths, monospace_cols}

    Real AMD lab pattern for questions (verified from C:\\SET2\\F3\\Lab Docs):
      Questions appear INLINE within steps — immediately after the relevant numbered step,
      before the next step continues. Each question has exactly 3 QuestionLine paragraphs.
      All answers are collected and rendered together in the Answers section at the end.
    """
    if 'action' in instruction:
        parts.append(lab1(instruction['action']))
    if 'substep' in instruction:
        parts.append(lab2(instruction['substep']))
    if 'command' in instruction:
        parts.append(list_continue2_code(instruction['command'], keep_next=True))
    if 'note' in instruction:
        parts.append(list_continue2(instruction['note']))
    if 'continue' in instruction:
        parts.append(list_continue(instruction['continue']))
    if 'lab1_continue' in instruction:
        parts.append(lab_list_number1_continue(instruction['lab1_continue']))
    if 'lab1_continue_nb' in instruction:
        parts.append(lab_list_number1_continue_nb(instruction['lab1_continue_nb']))
    if 'warning' in instruction:
        parts.append(warning_box(instruction['warning']))
    if 'bullet2' in instruction:
        parts.append(lab_list_number2_bullet(instruction['bullet2']))
    if 'image' in instruction:
        result = embed_image(instruction['image'])
        if result:
            rel_id, w_pt, h_pt = result
            parts.append(vml_image_para(rel_id, w_pt, h_pt, keep_next=True))
        if 'caption' in instruction:
            parts.append(caption_para(instruction['caption']))
    elif 'caption' in instruction:
        parts.append(caption_para(instruction['caption']))
    if 'question' in instruction:
        parts.append(question_heading())
        parts.append(question_body(instruction['question']))
        n_lines = instruction.get('answer_lines', 3)
        for _ in range(n_lines):
            parts.append(question_line())
    elif 'question_body' in instruction:
        parts.append(question_body(instruction['question_body']))
    if 'answer' in instruction:
        parts.append(answer_body(instruction['answer']))
    if 'table' in instruction:
        tbl = instruction['table']
        rows = tbl.get('rows', [])
        widths = tuple(tbl.get('widths', [3120, 3120, 3120]))
        mc = tbl.get('monospace_cols')
        if rows:
            parts.append(make_table(rows, widths, monospace_cols=mc))


def render_step(step, parts):
    """Render a full step: StepHeading + intro + instructions + outcome."""
    parts.append(step_heading(step['title']))

    if step.get('intro'):
        parts.append(general(step['intro']))

    for instruction in step.get('instructions', []):
        render_instruction(instruction, parts)

    # outcome field is intentionally not rendered — real AMD labs do not print
    # "Expected Outcome" text in the student document. Use it for author notes only.
    parts.append(allow_page_break())


# ── Section break helpers ──────────────────────────────────────────────────────

def make_first_pages_sectPr(base_sectPr):
    if '<w:titlePg/>' not in base_sectPr and '<w:titlePg ' not in base_sectPr:
        base_sectPr = base_sectPr.replace('</w:sectPr>', '<w:titlePg/></w:sectPr>')
    return base_sectPr


# ── Main document assembler ────────────────────────────────────────────────────

def build_document(config, template_docm, output_path):
    reset_counters()
    reset_figures(lab_num=config.get('lab_number', 1))
    reset_images()

    work_dir = output_path + '_work'
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    with zipfile.ZipFile(template_docm, 'r') as z:
        z.extractall(work_dir)

    doc_path = os.path.join(work_dir, 'word', 'document.xml')
    with open(doc_path, 'r', encoding='utf-8') as f:
        original_xml = f.read()

    doc_open = original_xml[:original_xml.find('<w:body>') + 8]
    sect_start = original_xml.rfind('<w:sectPr')
    sect_end = original_xml.find('</w:sectPr>', sect_start) + len('</w:sectPr>')
    sectPr = original_xml[sect_start:sect_end]

    # Version: derive from current year if not provided
    current_year = datetime.datetime.now().year
    default_version = f'{current_year}.1'
    version = config.get('version', default_version)

    lab_num = config.get('lab_number', 1)
    title = config['title']

    parts = []

    # ── Cover page ────────────────────────────────────────────────────────────
    parts.append('<w:p><w:pPr><w:pStyle w:val="SuperTitle"/></w:pPr></w:p>')
    parts.append(f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr>'
                 f'<w:r><w:t>{esc(title)}</w:t></w:r></w:p>')
    parts.append('<w:p><w:pPr><w:pStyle w:val="Version"/></w:pPr></w:p>')
    parts.append('<w:p><w:pPr><w:pStyle w:val="Byline"/></w:pPr></w:p>')
    parts.append('<w:p><w:pPr><w:pStyle w:val="Byline"/></w:pPr></w:p>')
    parts.append('<w:p><w:pPr><w:pStyle w:val="Byline"/></w:pPr></w:p>')

    # Cover section break (oddPage, no header/footer refs, titlePg)
    cover_sect = re.sub(r'<w:headerReference[^/]*/>', '', sectPr)
    cover_sect = re.sub(r'<w:footerReference[^/]*/>', '', cover_sect)
    cover_sect = re.sub(r'<w:type w:val="[^"]*"/>', '<w:type w:val="oddPage"/>', cover_sect)
    if '<w:type ' not in cover_sect:
        cover_sect = cover_sect.replace('</w:sectPr>', '<w:type w:val="oddPage"/></w:sectPr>')
    cover_sect = make_first_pages_sectPr(cover_sect)
    no_border_ppr = (
        '<w:pBdr>'
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '</w:pBdr>'
    )
    parts.append(f'<w:p><w:pPr>{no_border_ppr}{cover_sect}</w:pPr></w:p>')

    # ── TOC page ──────────────────────────────────────────────────────────────
    parts.append(toc_title('Table of Contents'))
    parts.append(toc1(f'{title}', page=3))
    parts.append('<w:p><w:pPr></w:pPr></w:p>')
    parts.append('<w:p><w:pPr></w:pPr></w:p>')

    # TOC section break (oddPage, with footer refs for AMD footer)
    toc_sect = re.sub(r'<w:type w:val="[^"]*"/>', '<w:type w:val="oddPage"/>', sectPr)
    if '<w:type ' not in toc_sect:
        toc_sect = toc_sect.replace('</w:sectPr>', '<w:type w:val="oddPage"/></w:sectPr>')
    if '<w:titlePg/>' not in toc_sect:
        toc_sect = toc_sect.replace('</w:sectPr>', '<w:titlePg/></w:sectPr>')
    toc_footer_refs = (
        '<w:footerReference w:type="first" r:id="rId18"/>'
        '<w:footerReference w:type="even" r:id="rId15"/>'
        '<w:footerReference w:type="default" r:id="rId16"/>'
    )
    toc_sect = toc_sect.replace('</w:sectPr>', toc_footer_refs + '</w:sectPr>')
    parts.append(f'<w:p><w:pPr>{toc_sect}</w:pPr></w:p>')

    # ── Heading1 + Sub-title (version) ────────────────────────────────────────
    parts.append(f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
                 f'<w:r><w:t>{esc(title)}</w:t></w:r></w:p>')
    parts.append(f'<w:p><w:pPr><w:pStyle w:val="Sub-title"/></w:pPr>'
                 f'<w:r><w:t>{esc(version)}</w:t></w:r></w:p>')
    parts.append(allow_page_break())

    # ── Abstract ──────────────────────────────────────────────────────────────
    parts.append(h2('Abstract'))
    abstract = config.get('abstract', [])
    if isinstance(abstract, str):
        abstract = [abstract]
    for p in abstract:
        parts.append(body_text(p))
    parts.append(allow_page_break())

    # ── CloudShare Users Only (optional) ──────────────────────────────────────
    if config.get('cloudshare_note'):
        parts.append(h2('CloudShare Users Only'))
        note = config['cloudshare_note']
        if isinstance(note, str):
            note = [note]
        for p in note:
            parts.append(body_text(p))
        parts.append(allow_page_break())

    # ── Objectives ────────────────────────────────────────────────────────────
    parts.append(h2('Objectives'))
    parts.append(body_text('After completing this lab, you will be able to:'))
    for obj in config.get('objectives', []):
        parts.append(bullet(obj))
    parts.append(allow_page_break())

    # ── Introduction ──────────────────────────────────────────────────────────
    if config.get('introduction'):
        parts.append(h2('Introduction'))
        for item in config['introduction']:
            if isinstance(item, str):
                parts.append(body_text(item))
            elif isinstance(item, dict):
                itype = item.get('type', 'body')
                text_val = item.get('text', '')
                if itype == 'body':
                    parts.append(body_text(text_val))
                elif itype == 'general':
                    parts.append(general(text_val))
                elif itype == 'bullet':
                    parts.append(bullet(text_val))
                elif itype == 'image':
                    result = embed_image(item['image'])
                    if result:
                        rel_id, w_pt, h_pt = result
                        parts.append(vml_image_para(rel_id, w_pt, h_pt,
                                                    style_name='BodyText', keep_next=True))
                    if 'caption' in item:
                        parts.append(caption_para(item['caption']))
                elif itype == 'table':
                    rows = item.get('rows', [])
                    widths = tuple(item.get('widths', [2340, 2340, 2340, 2340]))
                    if rows:
                        parts.append(make_table(rows, widths))

    # ── Prerequisites table (if provided) ─────────────────────────────────────
    if config.get('prerequisites'):
        prereq_rows = config['prerequisites']
        if prereq_rows:
            ncols = len(prereq_rows[0])
            base_w = 9360 // ncols
            parts.append(make_table(prereq_rows, tuple(base_w for _ in range(ncols))))
        parts.append(allow_page_break())

    # ── Nomenclature (always present, AMD standard) ───────────────────────────
    parts.append(h2('Nomenclature'))
    parts.append(body_text(
        'Formal nomenclature is used to explain how different arguments are used. '
        'The following are some of the more commonly used symbols:'
    ))
    parts.append(make_table(NOMENCLATURE_ROWS, NOMENCLATURE_WIDTHS, monospace_cols=[0, 2]))
    parts.append('<w:p><w:pPr><w:pStyle w:val="TableBodyText"/></w:pPr></w:p>')
    parts.append(allow_page_break())

    # ── General Flow (optional) ───────────────────────────────────────────────
    if config.get('general_flow'):
        parts.append(h2('General Flow'))
        parts.append(make_general_flow(
            config['general_flow'],
            max_per_row=config.get('general_flow_per_row', 4)
        ))
        parts.append(allow_page_break())

    # ── Steps ─────────────────────────────────────────────────────────────────
    for step in config.get('steps', []):
        render_step(step, parts)

    # ── Final Validation Checkpoint ───────────────────────────────────────────
    if config.get('validation'):
        val = config['validation']
        parts.append(h2('Final Validation Checkpoint'))
        parts.append(body_text(val.get('intro', '')))
        val_rows = val.get('rows', [])
        if val_rows:
            ncols = len(val_rows[0])
            base_w = 9360 // ncols
            parts.append(make_table(val_rows, tuple(base_w for _ in range(ncols))))
        parts.append(spacer())
        if val.get('pass_statement'):
            parts.append(body_text(val['pass_statement']))
        parts.append(allow_page_break())

    # ── Troubleshooting tip ───────────────────────────────────────────────────
    if config.get('troubleshooting'):
        tip = config['troubleshooting']
        parts.append(h2('Troubleshooting Tip'))
        parts.append(question_heading())
        parts.append(question_body(f'Problem: {tip["problem"]}'))
        parts.append(body_text(tip.get('cause', '')))
        for fix_step in tip.get('steps', []):
            render_instruction(fix_step, parts)
        if tip.get('reference'):
            parts.append(list_continue(tip['reference']))
        parts.append(spacer())
        parts.append(allow_page_break())

    # ── Summary ───────────────────────────────────────────────────────────────
    if config.get('summary'):
        parts.append(h2('Summary'))
        summary = config['summary']
        if isinstance(summary, str):
            summary = [summary]
        for p in summary:
            parts.append(body_text(p))
        parts.append(spacer())

    # ── Answers section ───────────────────────────────────────────────────────
    if config.get('answers'):
        parts.append(allow_page_break())
        parts.append(h2('Answers'))
        for qa in config['answers']:
            parts.append(question_in_answer(qa.get('question', '')))
            ans = qa.get('answer', '')
            if isinstance(ans, str):
                parts.append(answer_body(ans))
            else:
                for a in ans:
                    parts.append(answer_body(a))

    # ── Assemble final XML ────────────────────────────────────────────────────
    new_xml = doc_open + '\n'.join(parts) + '\n' + sectPr + '</w:body>\n</w:document>'

    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_xml)

    write_images_to_zip(work_dir)

    if os.path.exists(output_path):
        os.remove(output_path)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root_dir, dirs, files in os.walk(work_dir):
            for file in files:
                fp = os.path.join(root_dir, file)
                z.write(fp, os.path.relpath(fp, work_dir))

    shutil.rmtree(work_dir)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Build AMD lab document (.docm)')
    parser.add_argument('--config', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    result = build_document(config, args.template, args.output)
    print(f'Created: {result} ({os.path.getsize(result) // 1024} KB)')


if __name__ == '__main__':
    main()
