"""
annotate_docx.py — Adds Word tracked changes comments to a lab DOCX.
Inserts w:ins (insertions) with validation notes at the end of relevant paragraphs.
Usage: python3 annotate_docx.py <input.docm> <results.json> <output.docm>
"""

import sys
import json
import zipfile
import shutil
import re
from datetime import datetime

AUTHOR = "Lab Validator"
DATE = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def esc(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def make_ins(text, rev_id):
    """Create a w:ins tracked change insertion."""
    return (
        f'<w:ins w:id="{rev_id}" w:author="{esc(AUTHOR)}" w:date="{DATE}">'
        f'<w:r><w:rPr><w:color w:val="FF0000"/></w:rPr>'
        f'<w:t xml:space="preserve"> [{esc(text)}]</w:t>'
        f'</w:r></w:ins>'
    )


def make_comment_ref(comment_id):
    return (
        f'<w:commentRangeStart w:id="{comment_id}"/>'
        f'<w:commentRangeEnd w:id="{comment_id}"/>'
        f'<w:r><w:commentReference w:id="{comment_id}"/></w:r>'
    )


def build_comments_xml(step_results):
    """Build word/comments.xml content."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<w:comments xmlns:w="{W}">',
    ]
    for i, r in enumerate(step_results):
        icon = 'PASS' if r['status'] == 'PASS' else ('WARN' if r['status'] == 'WARN' else 'FAIL')
        text = f"[{icon}] Step {r['step']}: {r['description']}"
        if r.get('notes'):
            text += f" | NOTE: {r['notes']}"
        if r.get('actual_output'):
            text += f" | OUTPUT: {r['actual_output'][:150]}"
        text_esc = esc(text)
        lines.append(
            f'<w:comment w:id="{i}" w:author="{esc(AUTHOR)}" '
            f'w:date="{DATE}" w:initials="LV">'
            f'<w:p><w:r><w:t xml:space="preserve">{text_esc}</w:t></w:r></w:p>'
            f'</w:comment>'
        )
    lines.append('</w:comments>')
    return '\n'.join(lines)


def insert_tracked_changes(doc_xml, step_results):
    """
    For WARN/FAIL steps, insert a tracked change (w:ins) after the first
    paragraph that contains a matching keyword from the step description.
    """
    rev_id_counter = [1000]

    def next_id():
        rid = rev_id_counter[0]
        rev_id_counter[0] += 1
        return rid

    for r in step_results:
        if r['status'] == 'PASS':
            continue

        icon = 'WARN' if r['status'] == 'WARN' else 'FAIL'
        note = r.get('notes', '') or r.get('actual_output', '')[:120]
        ins_text = f"{icon} - {note}"

        # Find a keyword from the step description to anchor the insertion
        keywords = [w for w in r['description'].split() if len(w) > 5]
        matched = False
        for kw in keywords:
            # Find closing </w:p> after a paragraph containing this keyword
            pattern = rf'(<w:t[^>]*>[^<]*{re.escape(kw)}[^<]*</w:t>.*?</w:p>)'
            match = re.search(pattern, doc_xml, re.DOTALL | re.IGNORECASE)
            if match:
                rid = next_id()
                ins = make_ins(ins_text, rid)
                old = match.group(0)
                new = old[:-len('</w:p>')] + ins + '</w:p>'
                doc_xml = doc_xml.replace(old, new, 1)
                matched = True
                break

    return doc_xml


def update_content_types(ct_xml):
    if 'comments' not in ct_xml:
        ct_xml = ct_xml.replace(
            '</Types>',
            '<Override PartName="/word/comments.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.comments+xml"/>\n</Types>'
        )
    return ct_xml


def update_rels(rels_xml):
    if 'comments' not in rels_xml:
        rels_xml = rels_xml.replace(
            '</Relationships>',
            '<Relationship Id="rIdComments" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" '
            'Target="comments.xml"/>\n</Relationships>'
        )
    return rels_xml


def annotate_docx(input_path, results_path, output_path):
    with open(results_path) as f:
        results = json.load(f)
    # Support both flat list and {"steps": [...]} format
    step_results = results if isinstance(results, list) else results.get('steps', [])

    # Read original zip
    with zipfile.ZipFile(input_path, 'r') as zin:
        file_data = {name: zin.read(name) for name in zin.namelist()}
        infos = {name: zin.getinfo(name) for name in zin.namelist()}

    # Modify document.xml — insert tracked changes for WARN/FAIL
    doc_xml = file_data['word/document.xml'].decode('utf-8')
    doc_xml = insert_tracked_changes(doc_xml, step_results)
    file_data['word/document.xml'] = doc_xml.encode('utf-8')

    # Add comments.xml
    file_data['word/comments.xml'] = build_comments_xml(step_results).encode('utf-8')

    # Update [Content_Types].xml
    ct = file_data['[Content_Types].xml'].decode('utf-8')
    file_data['[Content_Types].xml'] = update_content_types(ct).encode('utf-8')

    # Update rels
    rels_key = 'word/_rels/document.xml.rels'
    if rels_key in file_data:
        rels = file_data[rels_key].decode('utf-8')
        file_data[rels_key] = update_rels(rels).encode('utf-8')

    # Write output preserving original zip structure
    with zipfile.ZipFile(input_path, 'r') as zin:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for name in zin.namelist():
                info = zin.getinfo(name)
                zout.writestr(info, file_data.get(name, zin.read(name)))
                written.add(name)
            # Write new files not in original
            for name, data in file_data.items():
                if name not in written:
                    zout.writestr(name, data)

    print(f'Annotated DOCX written to: {output_path}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: annotate_docx.py <input.docm> <results.json> <output.docm>")
        sys.exit(1)
    annotate_docx(sys.argv[1], sys.argv[2], sys.argv[3])
