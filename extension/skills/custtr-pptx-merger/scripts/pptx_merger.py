#!/usr/bin/env python3
"""
Merge PPTX files by properly copying slide masters, layouts, themes, media,
charts, and all other embedded parts. Requires Python 3 and lxml. No watermarks.

Usage:
    python pptx_merger.py <output.pptx> <src1.pptx>[:<slides>] [<src2.pptx>[:<slides>] ...]

Where <slides> is optional and may be:
    all                      every slide (the default if omitted)
    1,3,5                    explicit 1-based slide numbers
    2-7                      an inclusive range
    1,3,5-9,12               any combination of the above

Examples:
    python pptx_merger.py out.pptx deck1.pptx deck2.pptx deck3.pptx
    python pptx_merger.py out.pptx deck1.pptx:1,3,5 deck2.pptx:all deck3.pptx:2-7

For full CLI options run `python pptx_merger.py --help`.
"""

import os, re, sys, json, mimetypes, logging, zipfile, hashlib
from collections import defaultdict
from lxml import etree

# Module-level logger. Configured by main() based on CLI flags. Library users
# importing Merger get a NullHandler-attached logger so we never spam their
# output unless they configure logging themselves.
log = logging.getLogger("pptx_merge")
log.addHandler(logging.NullHandler())

__version__ = "1.0.0"

# OOXML namespace URIs. Centralized so a future Office namespace bump can be
# made in one place; also ensures every part of the script uses byte-identical
# URI strings (subtle XPath bugs occur if even one character differs).
REL_NS  = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS   = "http://schemas.openxmlformats.org/package/2006/content-types"
PPT_NS  = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS    = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P188_NS = "http://schemas.microsoft.com/office/powerpoint/2018/8/main"  # modern comments / authors

KNOWN_CT = {
    "slide":           "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
    "slideMaster":     "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml",
    "slideLayout":     "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml",
    "theme":           "application/vnd.openxmlformats-officedocument.theme+xml",
    "chart":           "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
    "chartStyle":      "application/vnd.ms-office.chartstyle+xml",
    "chartColorStyle": "application/vnd.ms-office.chartcolorstyle+xml",
    "drawing":         "application/vnd.openxmlformats-officedocument.drawing+xml",
    "notesSlide":      "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    "notesMaster":     "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
    "diagramData":     "application/vnd.openxmlformats-officedocument.drawingml.diagramData+xml",
    "diagramLayout":   "application/vnd.openxmlformats-officedocument.drawingml.diagramLayout+xml",
    "diagramStyle":    "application/vnd.openxmlformats-officedocument.drawingml.diagramStyle+xml",
    "diagramColors":   "application/vnd.openxmlformats-officedocument.drawingml.diagramColors+xml",
}

MEDIA_MIME = {
    # Images
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
    "bmp": "image/bmp", "svg": "image/svg+xml", "wmf": "image/x-wmf", "emf": "image/x-emf",
    "tiff": "image/tiff", "tif": "image/tiff", "wdp": "image/vnd.ms-photo",
    "webp": "image/webp", "ico": "image/x-icon", "heic": "image/heic", "heif": "image/heif",
    # Video
    "mp4": "video/mp4", "m4v": "video/mp4", "mov": "video/quicktime",
    "avi": "video/x-msvideo", "wmv": "video/x-ms-wmv", "webm": "video/webm",
    "mkv": "video/x-matroska",
    # Audio
    "wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4",
    "aac": "audio/aac", "ogg": "audio/ogg", "flac": "audio/flac",
    "opus": "audio/opus", "wma": "audio/x-ms-wma",
}


def _media_mime_for(ext):
    """Resolve a content type for a media file extension.

    Tries our curated MEDIA_MIME table first (covers OOXML-specific quirks
    like `image/x-emf`), then falls back to Python's stdlib mimetypes
    database, then to application/octet-stream as last resort. Falling back
    to octet-stream is risky — PowerPoint may refuse to embed media without
    a recognised type — so the curated table should be kept current as new
    formats are encountered.
    """
    ext = ext.lower().lstrip(".")
    if ext in MEDIA_MIME:
        return MEDIA_MIME[ext]
    guessed, _ = mimetypes.guess_type(f"x.{ext}")
    return guessed or "application/octet-stream"

# OOXML PresentationML schema constants. All sld*Id values (sldId,
# sldMasterId, sldLayoutId) share one id namespace and must satisfy
# 256 <= id < 2^31 (ECMA-376 §19.2.1.40-42). Naming these makes the
# allocator code self-documenting and the call sites grep-able.
SLIDE_ID_MIN          = 256
SLIDE_MASTER_ID_MIN   = 0x80000000   # 2_147_483_648 — schema lower bound for sldMasterId
SLIDE_MASTER_ID_FLOOR = SLIDE_MASTER_ID_MIN - 1  # sentinel "one below" used as max_seen seed

# EMU = English Metric Unit. 1 inch = 914400 EMU (OOXML standard).
EMU_PER_INCH = 914400


def pxml(data):  return etree.fromstring(data)
def sxml(el):    return etree.tostring(el, xml_declaration=True, encoding="UTF-8", standalone=True)

def rels_path(part):
    d, f = part.rsplit("/", 1) if "/" in part else ("", part)
    return (f"{d}/_rels/{f}.rels" if d else f"_rels/{f}.rels")

def resolve(base, target):
    """Resolve a rels Target relative to its owning part path.

    Returns a package-root-relative path. Excess `..` segments (more parents
    than the path has depth) are silently dropped — the previous behaviour
    appended them to the stack and produced paths like `../foo.xml` that
    escape the package, which would then dangle in dest. Real-world source
    files don't have escaping rels, but defending against it costs nothing.
    """
    if target.startswith("/"):
        return target.lstrip("/")
    base_dir = base.rsplit("/", 1)[0] if "/" in base else ""
    raw = f"{base_dir}/{target}" if base_dir else target
    stack = []
    for p in raw.split("/"):
        if p == "..":
            if stack:
                stack.pop()
            # else: clamp at root (silently drop excess ..)
        elif p and p != ".":
            stack.append(p)
    return "/".join(stack)

def rel_target_from(dest_part, dest_resource):
    src_dir   = dest_part.rsplit("/", 1)[0] if "/" in dest_part else ""
    res_parts = dest_resource.split("/")
    src_parts = src_dir.split("/") if src_dir else []
    common = 0
    for a, b in zip(src_parts, res_parts[:-1]):
        if a == b: common += 1
        else: break
    up = len(src_parts) - common
    return "../" * up + "/".join(res_parts[common:])

def parse_rels(parts, part_path):
    rp = rels_path(part_path)
    if rp not in parts:
        return []
    root = pxml(parts[rp])
    return [(r.get("Id",""), r.get("Type",""),
             r.get("Target",""), r.get("TargetMode","")) for r in root]

def make_rels(entries):
    # Use a default namespace so lxml writes <Relationships xmlns="...">
    # instead of <ns0:Relationships>.
    root = etree.Element("Relationships", nsmap={None: REL_NS})
    for rid, rtype, target, mode in entries:
        r = etree.SubElement(root, "Relationship")
        r.set("Id", rid); r.set("Type", rtype); r.set("Target", target)
        if mode: r.set("TargetMode", mode)
    return root

def slide_num(target):
    m = re.search(r"(\d+)\.xml$", target)
    return int(m.group(1)) if m else 0


# Pre-flight validation parts. Every source file must have these for the
# merger to do anything meaningful; if a source is missing them, fail
# early with a clear message instead of an opaque XML parse error 30
# seconds into the run.
REQUIRED_PARTS = (
    "[Content_Types].xml",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
)


def preflight_source(path, max_bytes=None):
    """Validate a source PPTX file before passing it to the Merger.

    Raises ValueError with a precise message if the file:
      - doesn't exist
      - exceeds max_bytes (if set)
      - isn't a valid zip
      - is missing one of REQUIRED_PARTS
      - contains zero slides

    Successful pre-flight returns the file's size in bytes — useful for
    telemetry / quota accounting in the caller.
    """
    if not os.path.exists(path):
        raise ValueError(f"Source not found: {path}")
    size = os.path.getsize(path)
    if max_bytes is not None and size > max_bytes:
        raise ValueError(
            f"Source exceeds size limit ({size:,} > {max_bytes:,} bytes): {path}"
        )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as e:
        raise ValueError(f"Source is not a valid zip: {path}: {e}") from e
    missing = [p for p in REQUIRED_PARTS if p not in names]
    if missing:
        raise ValueError(
            f"Source is missing required PPTX parts {missing}: {path}"
        )
    has_slide = any(
        re.match(r"ppt/slides/slide\d+\.xml$", n) for n in names
    )
    if not has_slide:
        raise ValueError(f"Source has zero slides: {path}")
    return size


class Merger:
    def __init__(self, base_path):
        self.base_path = base_path
        with zipfile.ZipFile(base_path) as zf:
            self.parts = {n: zf.read(n) for n in zf.namelist()}

        ct_root = pxml(self.parts["[Content_Types].xml"])
        self.ct_defaults  = {e.get("Extension"): e.get("ContentType")
                             for e in ct_root if "Extension" in e.attrib}
        self.ct_overrides = {e.get("PartName"):  e.get("ContentType")
                             for e in ct_root if "PartName"  in e.attrib}

        def count(pat): return sum(1 for p in self.parts if re.match(pat, p))
        def max_num(pat):
            nums = [int(m.group(1)) for p in self.parts if (m := re.match(pat, p))]
            return max(nums) if nums else 0
        self.n_masters  = count(r"ppt/slideMasters/slideMaster\d+\.xml$")
        self.n_layouts  = count(r"ppt/slideLayouts/slideLayout\d+\.xml$")
        self.n_themes   = count(r"ppt/theme/theme\d+\.xml$")
        self.n_slides   = count(r"ppt/slides/slide\d+\.xml$")
        self.n_charts   = count(r"ppt/charts/chart\d+\.xml$")
        self.n_drawings = count(r"ppt/drawings/drawing\d+\.xml$")
        self.n_notes    = count(r"ppt/notesSlides/notesSlide\d+\.xml$")
        self.n_tags     = count(r"ppt/tags/tag\d+\.xml$")
        # Count any pre-existing diagram parts in base. Hardcoding to 0 here
        # would let the first merged diagram step on a base diagram with the
        # same dN_<name> prefix. Match only the actual XML parts, not their
        # `_rels/` siblings — counting both inflates the prefix counter and
        # produces gaps like d11_data1.xml when only 5 diagrams exist.
        self.n_diagrams = count(r"ppt/diagrams/[^/]+\.xml$")
        self.n_media    = sum(1 for p in self.parts if p.startswith("ppt/media/"))
        # Track max used filename number separately from count, so filtering
        # base slides (which leaves gaps) doesn't cause new merges to reuse
        # numbers that still belong to surviving base parts.
        self.next_slide_num = max_num(r"ppt/slides/slide(\d+)\.xml$") + 1
        self.next_notes_num = max_num(r"ppt/notesSlides/notesSlide(\d+)\.xml$") + 1

        self.pres_el  = pxml(self.parts["ppt/presentation.xml"])
        self.pres_rel = pxml(self.parts["ppt/_rels/presentation.xml.rels"])
        self.pns = {"p": PPT_NS, "r": R_NS}

        # Capture base slide size — every merged source MUST match this. PPTX
        # has exactly one <p:sldSz> applied to every slide; mixing sources with
        # different sizes makes content from the smaller source render at
        # wrong coordinates against the larger canvas (and vice versa).
        self.base_sldsz = self._read_sldsz(self.pres_el)

        # Note: avoid `or []` on the lxml element — element truthiness is
        # deprecated. Use explicit `is not None`.
        sld_lst = self.pres_el.find("p:sldIdLst", self.pns)
        sld_ids = [int(e.get("id", 0)) for e in sld_lst] if sld_lst is not None else []
        self.next_slide_id = max(sld_ids) + 1 if sld_ids else SLIDE_ID_MIN

        # sldId, sldMasterId and sldLayoutId share a single id namespace across the
        # whole package and must all be unique (ECMA-376 §19.2.1.40-42). Start the
        # next-master-id allocation above the max of every existing master id AND
        # every existing sldLayoutId inside any slide master, otherwise newly
        # assigned master ids will collide with layout ids already inside the
        # base file's master(s) and PowerPoint will offer to repair on open.
        self.next_master_id = max(self._max_master_layout_id() + 1,
                                  SLIDE_MASTER_ID_MIN)

        rids = [int(m.group(1)) for r in self.pres_rel
                if (m := re.search(r"rId(\d+)", r.get("Id","")))]
        self.next_pres_rid = max(rids) + 1 if rids else 1

        # Strip changesInfos — author-specific metadata, invalid in a merged context;
        # PowerPoint repairs (and removes) this on open, which triggers the repair dialog.
        for key in list(self.parts):
            if key.startswith("ppt/changesInfos/") or key.startswith("changesInfos/"):
                del self.parts[key]
        for key in list(self.ct_overrides):
            if "changesInfo" in key:
                del self.ct_overrides[key]

        self.media_map = {}
        for p in self.parts:
            if p.startswith("ppt/media/"):
                self.media_map[hashlib.sha256(self.parts[p]).hexdigest()] = p

        # Dedup customXml items by hash of bytes with ANY xml declaration
        # stripped. Templafy emits the same logical item with assorted decls
        # (`utf-8` lowercase, `UTF-8 standalone="yes"`, none at all). We want
        # all those to dedup against each other; otherwise PowerPoint detects
        # the surviving duplicates and removes them, taking out every slide
        # rel that referenced them with it.
        self.custom_xml_map = {}  # sha256(content_sans_decl) -> dest_path
        for p in self.parts:
            if re.match(r"customXml/item\d+\.xml$", p):
                content = self._strip_xml_decl(self.parts[p])
                self.custom_xml_map[hashlib.sha256(content).hexdigest()] = p
        self.n_custom_xml = sum(1 for p in self.parts if re.match(r"customXml/item\d+\.xml$", p))
        self.n_custom_xml_props = max_num(r"customXml/itemProps(\d+)\.xml$")

        # Stack tracking the "currently active" chart number so helper
        # parts (chartStyle, chartColorStyle, embedded xlsx) always carry
        # the same cN_ / eN_ prefix as their owning chart even if recursion
        # bumps the global counter mid-stream.
        self._chart_stack = []

        # Find the base file's actual notesMaster (don't hardcode notesMaster1).
        # The redirect in _route_dep needs a real target in self.parts,
        # otherwise every source-derived notesSlide ends up with a dangling
        # notesMaster rel that PowerPoint will repair-strip.
        nm_files = sorted(p for p in self.parts
                          if re.match(r"ppt/notesMasters/notesMaster\d+\.xml$", p))
        self.base_notes_master = nm_files[0] if nm_files else None

        # Base file's comment parts are bulk-loaded above and never visit
        # _route_dep, so strip reaction extLst here too.
        for p in [k for k in self.parts if k.startswith("ppt/comments/") and k.endswith(".xml")]:
            self._strip_reaction_extlst(p)

        # Same problem for customXml — base file's items are bulk-loaded.
        # If any lack the <?xml ?> declaration, PowerPoint will repair-delete
        # them along with every slide rel that referenced them.
        for p in [k for k in self.parts if re.match(r"customXml/item(?:Props)?\d+\.xml$", k)]:
            self.parts[p] = self._ensure_xml_declaration(self.parts[p])

    def _pres_rid(self):
        r = f"rId{self.next_pres_rid}"; self.next_pres_rid += 1; return r

    @staticmethod
    def _warn(msg):
        """Emit a non-fatal warning via the module logger.

        Used in place of silently swallowing XMLSyntaxError / Exception in
        defensive code paths. In production, operators need to see when a
        part fails to parse (it usually masks a real corruption that will
        bite later) — silent `except: continue` hides bugs.
        """
        log.warning(msg)

    def _read_sldsz(self, pres_el):
        """Return (cx, cy) in EMU from <p:sldSz>, or (None, None) if missing."""
        sz = pres_el.find("p:sldSz", self.pns)
        if sz is None: return (None, None)
        try:
            return (int(sz.get("cx", 0)), int(sz.get("cy", 0)))
        except (TypeError, ValueError):
            return (None, None)

    @staticmethod
    def _fmt_sldsz(cx, cy):
        """Pretty-print a slide size: EMU + inches + named alias if recognised."""
        if cx is None or cy is None:
            return "<missing>"
        in_w, in_h = cx / EMU_PER_INCH, cy / EMU_PER_INCH
        named = {
            (9144000, 6858000):  "4:3 standard",
            (9144000, 5143500):  "16:9 (older 'On-screen Show 16:9')",
            (12192000, 6858000): "16:9 widescreen (PowerPoint 2013+ default)",
            (10080000, 7560000): "Letter portrait-ish",
            (12700000, 9525000): "Banner",
        }.get((cx, cy), "custom")
        return f"{cx}x{cy} EMU ({in_w:g}\"x{in_h:g}\", {named})"

    def _max_master_layout_id(self):
        """Max id used by any sldMasterId or sldLayoutId currently in self.parts.
        Returns SLIDE_MASTER_ID_FLOOR (one below the schema minimum) if none
        found, so the caller can safely use max(result + 1, SLIDE_MASTER_ID_MIN)."""
        mx = SLIDE_MASTER_ID_FLOOR
        mid_lst = self.pres_el.find("p:sldMasterIdLst", self.pns)
        if mid_lst is not None:
            for el in mid_lst:
                try: mx = max(mx, int(el.get("id", 0)))
                except (TypeError, ValueError): pass
        for p in self.parts:
            if not re.match(r"ppt/slideMasters/slideMaster\d+\.xml$", p):
                continue
            try:
                root = pxml(self.parts[p])
            except etree.XMLSyntaxError as e:
                self._warn(f"_max_master_layout_id: cannot parse {p}: {e}")
                continue
            for el in root.findall("p:sldLayoutIdLst/p:sldLayoutId", self.pns):
                try: mx = max(mx, int(el.get("id", 0)))
                except (TypeError, ValueError): pass
        return mx

    def _copy_media(self, src, path):
        if path not in src: return None
        data = src[path]
        h = hashlib.sha256(data).hexdigest()
        if h in self.media_map:
            return self.media_map[h]
        ext = os.path.splitext(path)[1]
        self.n_media += 1
        dest = f"ppt/media/media{self.n_media}{ext}"
        self.parts[dest] = data
        self.media_map[h] = dest
        ext_nd = ext.lstrip(".")
        if ext_nd not in self.ct_defaults:
            self.ct_defaults[ext_nd] = _media_mime_for(ext_nd)
        return dest

    def _copy_theme(self, src, path, remap):
        if path in remap: return remap[path]
        self.n_themes += 1
        dest = f"ppt/theme/theme{self.n_themes}.xml"
        remap[path] = dest
        self.parts[dest] = src.get(path, b"")
        self.ct_overrides[f"/{dest}"] = KNOWN_CT["theme"]
        return dest

    def _route_dep(self, src, src_res, dest_parent, processed, remap,
                   src_ct_overrides):
        """Route a source-side dependency path to its dest path.

        `remap`            — src_path -> dest_path cache shared across one
                             source-merge call. Used both for dedup and as
                             the resolution source for slideMaster, theme,
                             and other cross-references.
        `src_ct_overrides` — content-type Overrides parsed from the source's
                             [Content_Types].xml. Used to recover content
                             types for parts not in our KNOWN_CT table.
        """
        def rel(d): return rel_target_from(dest_parent, d)

        if src_res in remap:
            return remap[src_res], rel(remap[src_res])

        if src_res.startswith("ppt/media/"):
            d = self._copy_media(src, src_res)
            return (d, rel(d)) if d else (None, None)

        if re.match(r"ppt/theme/theme\d+\.xml$", src_res):
            # Themes share the same remap dict as everything else; once one
            # source theme is copied, every subsequent reference to it
            # short-circuits via the `if src_res in remap` check above.
            d = self._copy_theme(src, src_res, remap)
            return d, rel(d)

        if re.match(r"ppt/charts/chart\d+\.xml$", src_res):
            self.n_charts += 1
            chart_no = self.n_charts
            dest = f"ppt/charts/chart{chart_no}.xml"
            remap[src_res] = dest
            # Push so any helpers / embeddings discovered while recursing
            # tag themselves with THIS chart's number, not whatever the
            # global counter happens to be later.
            self._chart_stack.append(chart_no)
            try:
                self._copy_recursive(src, src_res, dest, "chart",
                                     processed, remap, src_ct_overrides)
            finally:
                self._chart_stack.pop()
            return dest, rel(dest)

        if re.match(r"ppt/charts/", src_res) and src_res.endswith(".xml"):
            fname = os.path.basename(src_res)
            chart_no = self._chart_stack[-1] if self._chart_stack else self.n_charts
            dest = f"ppt/charts/c{chart_no}_{fname}"
            remap[src_res] = dest
            ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, ct, processed, remap, src_ct_overrides)
            return dest, rel(dest)

        if re.match(r"ppt/embeddings/", src_res) or (src_res in src and src_res.endswith(".xlsx")):
            fname = os.path.basename(src_res)
            chart_no = self._chart_stack[-1] if self._chart_stack else self.n_charts
            dest = f"ppt/embeddings/e{chart_no}_{fname}"
            remap[src_res] = dest
            if src_res in src:
                self.parts[dest] = src[src_res]
                src_ct = src_ct_overrides.get(f"/{src_res}")
                if src_ct: self.ct_overrides[f"/{dest}"] = src_ct
            return dest, rel(dest)

        if re.match(r"ppt/drawings/drawing\d+\.xml$", src_res):
            self.n_drawings += 1
            dest = f"ppt/drawings/drawing{self.n_drawings}.xml"
            remap[src_res] = dest
            self._copy_recursive(src, src_res, dest, "drawing", processed, remap, src_ct_overrides)
            return dest, rel(dest)

        if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", src_res):
            dest = f"ppt/notesSlides/notesSlide{self.next_notes_num}.xml"
            self.next_notes_num += 1
            self.n_notes += 1
            remap[src_res] = dest
            self._copy_recursive(src, src_res, dest, "notesSlide", processed, remap, src_ct_overrides)
            return dest, rel(dest)

        if re.match(r"ppt/notesMasters/notesMaster\d+\.xml$", src_res):
            # PowerPoint supports exactly one notesMaster per presentation.
            # Redirect every source notesMaster to whichever notesMaster the
            # base actually carries. If the base lacks one, copy the source's
            # wholesale (and let _copy_recursive register the content type).
            if self.base_notes_master:
                remap[src_res] = self.base_notes_master
                return self.base_notes_master, rel(self.base_notes_master)
            dest = "ppt/notesMasters/notesMaster1.xml"
            self.base_notes_master = dest
            remap[src_res] = dest
            self._copy_recursive(src, src_res, dest, "notesMaster", processed, remap, src_ct_overrides)
            # Register at presentation level so PowerPoint discovers it
            new_rid = self._pres_rid()
            rel_el = etree.SubElement(self.pres_rel, f"{{{REL_NS}}}Relationship")
            rel_el.set("Id", new_rid)
            rel_el.set("Type", f"{R_NS}/notesMaster")
            rel_el.set("Target", dest[len("ppt/"):])
            return dest, rel(dest)

        if re.match(r"customXml/item\d+\.xml$", src_res):
            # Hash on content sans XML declaration so items with different
            # decl styles (or none) still dedup against equivalent existing
            # ones. Any XML decl is added by _ensure_xml_declaration after
            # the dedup decision so the persisted bytes always start with one.
            content_h = None
            if src_res in src:
                content_h = hashlib.sha256(
                    self._strip_xml_decl(src[src_res])).hexdigest()
                if content_h in self.custom_xml_map:
                    d = self.custom_xml_map[content_h]
                    remap[src_res] = d
                    return d, rel(d)
            self.n_custom_xml += 1
            dest = f"customXml/item{self.n_custom_xml}.xml"
            remap[src_res] = dest
            if content_h is not None:
                self.custom_xml_map[content_h] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed, remap, src_ct_overrides)
            self.parts[dest] = self._ensure_xml_declaration(self.parts.get(dest, b""))
            # Every customXml item must ALSO be registered as a relationship
            # from presentation.xml.rels — without this, PowerPoint flags the
            # item as orphan during cross-deck consistency checks and Repair
            # deletes it (and strips every slide rel referencing it). Slide-
            # level rels alone are not enough: presentation rels are the
            # canonical "registry" for customXml in OOXML.
            new_rid = self._pres_rid()
            rel_el = etree.SubElement(self.pres_rel, f"{{{REL_NS}}}Relationship")
            rel_el.set("Id", new_rid)
            rel_el.set("Type", f"{R_NS}/customXml")
            rel_el.set("Target", f"../{dest}")  # ppt/* -> ../customXml/*
            return dest, rel(dest)

        if re.match(r"customXml/itemProps\d+\.xml$", src_res):
            # itemProps files are referenced from customXml/_rels/itemN.xml.rels
            # via a customXmlProps relationship. Allocate a fresh sequential
            # number; without this, they fall through to the mg_ catchall.
            self.n_custom_xml_props += 1
            dest = f"customXml/itemProps{self.n_custom_xml_props}.xml"
            remap[src_res] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed, remap, src_ct_overrides)
            self.parts[dest] = self._ensure_xml_declaration(self.parts.get(dest, b""))
            return dest, rel(dest)

        if re.match(r"ppt/diagrams/", src_res):
            # SmartArt comes as a 5-part bundle (data, layout, colors,
            # quickStyle, drawing). Slides reference each part directly —
            # there is no "primary" part whose recursion drags in the
            # rest — so we can't group them under a shared prefix without
            # cross-rel inspection. Per-file bump is the safe choice; the
            # dN_ prefix is just a disambiguator (PowerPoint reads parts
            # via slide rels, not by filename pattern).
            self.n_diagrams += 1
            fname = os.path.basename(src_res)
            dest = f"ppt/diagrams/d{self.n_diagrams}_{fname}"
            remap[src_res] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed,
                                 remap, src_ct_overrides)
            return dest, rel(dest)

        if re.match(r"ppt/tags/tag\d+\.xml$", src_res):
            self.n_tags += 1
            dest = f"ppt/tags/tag{self.n_tags}.xml"
            remap[src_res] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed, remap, src_ct_overrides)
            return dest, rel(dest)

        if re.match(r"ppt/comments/", src_res) and src_res in src:
            # Comment files use GUID-based names that are inherently unique
            # in their source deck, but two sources can ship a comment file
            # with the same filename (different content). Don't overwrite.
            fname = os.path.basename(src_res)
            dest = f"ppt/comments/{fname}"
            # Bug fix: prior version used `dest != src_res` which compared
            # paths rather than content, so a same-name comment from a
            # source silently overwrote the base's. Compare content instead.
            if dest in self.parts and self.parts[dest] != src[src_res]:
                h = hashlib.sha256(src[src_res]).hexdigest()[:8]
                dest = f"ppt/comments/{os.path.splitext(fname)[0]}_{h}.xml"
            remap[src_res] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed, remap, src_ct_overrides)
            # Microsoft authoring tools emit <p:ext> (legacy 2006 namespace)
            # inside <p188:extLst> (PowerPoint 2018 comments namespace), which
            # the OOXML SDK validator flags as Sch_UndeclaredAttribute and
            # PowerPoint sometimes silently repairs on open. The only payload
            # in those extLst blocks is reaction emoji metadata; strip the
            # whole extLst to silence the warning and prevent the Repair
            # dialog. Comment text and threaded replies are preserved.
            self._strip_reaction_extlst(dest)
            return dest, rel(dest)

        if src_res in src:
            fname = os.path.basename(src_res)
            src_dir_p = os.path.dirname(src_res)
            dest = f"{src_dir_p}/mg_{fname}"
            # If this catchall path already exists in dest with different
            # content, suffix with a content hash so we don't overwrite.
            if dest in self.parts and self.parts[dest] != src[src_res]:
                h = hashlib.sha256(src[src_res]).hexdigest()[:8]
                stem, ext = os.path.splitext(fname)
                dest = f"{src_dir_p}/mg_{stem}_{h}{ext}"
            remap[src_res] = dest
            src_ct = src_ct_overrides.get(f"/{src_res}")
            self._copy_recursive(src, src_res, dest, src_ct, processed, remap, src_ct_overrides)
            return dest, rel(dest)

        return None, None

    def _copy_recursive(self, src, src_path, dest_path, ct_key, processed,
                        remap, src_ct_overrides):
        """Copy a part and recursively all its dependencies.

        `src_ct_overrides` is the source's [Content_Types].xml Override map,
        threaded explicitly so callers don't depend on a stale instance attr.
        """
        if src_path in processed: return
        processed.add(src_path)
        remap[src_path] = dest_path  # pre-register to break circular refs
        self.parts[dest_path] = src.get(src_path, b"")
        if ct_key:
            resolved_ct = KNOWN_CT.get(ct_key, ct_key)
            if resolved_ct:
                self.ct_overrides[f"/{dest_path}"] = resolved_ct
        else:
            # Try to recover CT from source file's content types
            src_ct = src_ct_overrides.get(f"/{src_path}")
            if src_ct:
                self.ct_overrides[f"/{dest_path}"] = src_ct

        new_rels = []
        for rid, rtype, target, mode in parse_rels(src, src_path):
            if mode == "External":
                new_rels.append((rid, rtype, target, mode)); continue
            res = resolve(src_path, target)
            d, rel_tgt = self._route_dep(src, res, dest_path, processed,
                                         remap, src_ct_overrides)
            if d:
                new_rels.append((rid, rtype, rel_tgt, ""))
            else:
                new_rels.append((rid, rtype, target, mode))
        # Only write rels file if there are actual relationships (leaf parts have none)
        if new_rels:
            self.parts[rels_path(dest_path)] = sxml(make_rels(new_rels))

    def _copy_layout(self, src, src_layout, src_master, dest_master,
                     layout_remap, processed, src_ct_overrides):
        """Copy a slide layout via the unified _copy_recursive engine.

        Previously this was a parallel implementation of _copy_recursive with
        two special-case rel branches (slideMaster and theme). Both are now
        unnecessary: _route_dep handles theme via the shared remap dict, and
        slideMaster is resolved by pre-registering the parent master in
        `remap` so _route_dep's `if src_res in remap` shortcut returns the
        correct destination master path. Eliminating the duplicate engine
        removes a real drift risk — any future fix to _copy_recursive now
        applies to layouts automatically.
        """
        if src_layout in layout_remap:
            return layout_remap[src_layout]
        self.n_layouts += 1
        dest_layout = f"ppt/slideLayouts/slideLayout{self.n_layouts}.xml"
        # Pre-register so the layout's slideMaster rel resolves to the
        # parent master via _route_dep's remap shortcut.
        layout_remap[src_master] = dest_master
        self._copy_recursive(src, src_layout, dest_layout, "slideLayout",
                             processed, layout_remap, src_ct_overrides)
        return dest_layout

    @staticmethod
    def _strip_xml_decl(data):
        """Strip BOM + leading <?xml ... ?> declaration so content can be hashed
        in a declaration-agnostic way. Used for customXml dedup, where two
        items can be byte-different (one has 'utf-8' lowercase, another has
        'UTF-8 standalone="yes"') yet carry identical Templafy/SharePoint
        payloads. PowerPoint detects the logical duplicate and Repair-removes
        one of them (also stripping every slide rel that pointed to it),
        which destroys the binding. Hash on stripped content to dedup at the
        merger level instead.
        """
        if not data: return data
        if data[:3] == b"\xef\xbb\xbf":
            data = data[3:]
        s = data.lstrip()
        if s[:5] == b"<?xml":
            end = s.find(b"?>")
            if end != -1:
                s = s[end + 2:]
        return s.lstrip()

    @staticmethod
    def _ensure_xml_declaration(data):
        """Prepend an XML declaration if `data` (bytes) doesn't start with one.

        Some authoring tools (notably Templafy) emit customXml parts without
        the leading `<?xml ?>`. PowerPoint accepts that in a single-deck
        context but flags it during cross-deck consistency checks; on
        Repair it deletes the offending part AND strips every slide rel
        that referenced it, which is destructive. Normalise on copy.
        """
        if not data:
            return data
        # Skip BOM if present
        bom = b""
        if data[:3] == b"\xef\xbb\xbf":
            bom, data = data[:3], data[3:]
        if data.lstrip()[:5] == b"<?xml":
            return bom + data
        return bom + b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + data

    def _strip_reaction_extlst(self, dest_part):
        """Remove <p188:extLst> blocks whose only children are <p:ext> elements
        carrying reaction (emoji) metadata. These trigger Sch_UndeclaredAttribute
        in the OOXML SDK validator and can cause PowerPoint Repair pop-ups.

        Operates in-place on a comment part already in self.parts.
        """
        if dest_part not in self.parts:
            return
        try:
            root = pxml(self.parts[dest_part])
        except etree.XMLSyntaxError as e:
            self._warn(f"_strip_reaction_extlst: cannot parse {dest_part}: {e}")
            return
        changed = False
        # Find every <p188:extLst> anywhere in the tree
        for extlst in root.iter(f"{{{P188_NS}}}extLst"):
            children = list(extlst)
            # Drop only if every child is a <p:ext> from the legacy namespace
            # (those are the schema-flagged ones — purely reactions in
            # observed source decks). Leave any <p188:ext> children alone.
            if children and all(c.tag == f"{{{PPT_NS}}}ext" for c in children):
                parent = extlst.getparent()
                if parent is not None:
                    parent.remove(extlst)
                    changed = True
        if changed:
            self.parts[dest_part] = sxml(root)

    def _merge_author_registry(self, src, src_path, base_path, id_attr,
                               src_ct_overrides):
        """Merge author entries from a source's author registry file into the
        base's. Dedups by `id_attr` (the unique-author key for that file).

        Comments reference authors by id; if the merger copies comments
        without also copying their authors, PowerPoint flags the file
        as inconsistent and offers Repair.

        - For modern co-authoring (`ppt/authors.xml`, p188:authorLst), id is
          a GUID — globally unique by design, so simple dedup is correct.
        - For legacy comments (`ppt/commentAuthors.xml`, p:cmAuthorLst), id is
          an integer that's only unique within one deck; collisions can occur
          when merging multiple sources. We append-with-warn rather than
          remap (would require rewriting every comment's authorId reference).
        """
        if src_path not in src:
            return
        if base_path not in self.parts:
            # Base lacks this registry — copy source's wholesale and register
            # the rel + content-type so PowerPoint discovers it.
            self.parts[base_path] = src[src_path]
            src_ct = src_ct_overrides.get(f"/{src_path}")
            if src_ct:
                self.ct_overrides[f"/{base_path}"] = src_ct
            # Copy the rel from presentation.xml.rels so PowerPoint sees it
            src_pres_rel_root = pxml(src["ppt/_rels/presentation.xml.rels"])
            for r in src_pres_rel_root:
                tgt = r.get("Target", "")
                resolved = resolve("ppt/presentation.xml", tgt)
                if resolved == src_path:
                    new_rid = self._pres_rid()
                    rel_el = etree.SubElement(self.pres_rel,
                                              f"{{{REL_NS}}}Relationship")
                    rel_el.set("Id", new_rid)
                    rel_el.set("Type", r.get("Type", ""))
                    rel_el.set("Target", tgt)
                    break
            return

        base_root = pxml(self.parts[base_path])
        src_root  = pxml(src[src_path])
        existing  = {a.get(id_attr) for a in base_root if a.get(id_attr)}
        added = collisions = 0
        for a in src_root:
            aid = a.get(id_attr)
            if not aid:
                continue
            if aid in existing:
                # Same id; assume same author. Conservative: skip.
                # For legacy int ids this may be wrong (different authors
                # using the same int id across decks) but remapping is out
                # of scope here.
                if id_attr == "id" and not aid.startswith("{"):
                    collisions += 1
                continue
            # lxml doesn't like cross-tree appends; deepcopy via etree
            base_root.append(etree.fromstring(etree.tostring(a)))
            existing.add(aid)
            added += 1
        if collisions:
            log.warning(
                "%d legacy author id collisions in %s (skipped — comments "
                "may reference the wrong person)",
                collisions, os.path.basename(src_path)
            )
        if added:
            self.parts[base_path] = sxml(base_root)

    def merge_file(self, src_path, wanted=None):
        """Merge slides from src_path. wanted=None means all slides; otherwise
        a set of 1-based slide positions (in source's sldIdLst order)."""
        log.info("loading %s ...", os.path.basename(src_path))
        with zipfile.ZipFile(src_path) as zf:
            src = {n: zf.read(n) for n in zf.namelist()}

        # Refuse to merge sources with a different slide size than the base.
        # PPTX has only one <p:sldSz> per presentation; mixing canvases makes
        # the smaller source's content render off-canvas (or the larger's
        # content shrink into the upper-left). This is unrecoverable without
        # rescaling every shape, which we do not attempt.
        src_pres_el = pxml(src["ppt/presentation.xml"])
        src_sldsz   = self._read_sldsz(src_pres_el)
        if src_sldsz != self.base_sldsz:
            raise ValueError(
                f"Slide size mismatch: {os.path.basename(src_path)} has "
                f"{self._fmt_sldsz(*src_sldsz)} but {os.path.basename(self.base_path)} uses "
                f"{self._fmt_sldsz(*self.base_sldsz)}. Merge sources with the same slide size only."
            )

        # Absorb all Override content types from source so fallback parts get
        # correct CTs. Threaded explicitly to _route_dep / _copy_recursive
        # rather than stashed on `self` — that pattern caused subtle
        # temporal-coupling bugs (entry points other than merge_file would
        # silently use stale data from a previous source).
        src_ct_root = pxml(src["[Content_Types].xml"])
        src_ct_overrides = {e.get("PartName"): e.get("ContentType")
                            for e in src_ct_root if "PartName" in e.attrib}

        # Merge author registries BEFORE copying any comment parts. Comments
        # carry authorId references; if we copy them without first ensuring
        # the referenced authors live in the destination's authors.xml /
        # commentAuthors.xml, PowerPoint flags the file and offers Repair.
        self._merge_author_registry(src, "ppt/authors.xml",
                                    "ppt/authors.xml", "id", src_ct_overrides)
        self._merge_author_registry(src, "ppt/commentAuthors.xml",
                                    "ppt/commentAuthors.xml", "id",
                                    src_ct_overrides)

        src_pres_rel = pxml(src["ppt/_rels/presentation.xml.rels"])
        layout_remap = {}
        processed    = set()

        # ---- Copy slide masters ----
        master_targets = [(r.get("Target",""), r.get("Id",""))
                          for r in src_pres_rel if r.get("Type","").endswith("/slideMaster")]

        for m_target, _ in master_targets:
            src_master = resolve("ppt/presentation.xml", m_target)
            self.n_masters += 1
            dest_master = f"ppt/slideMasters/slideMaster{self.n_masters}.xml"

            new_rels = []
            for rid, rtype, target, mode in parse_rels(src, src_master):
                if mode == "External":
                    new_rels.append((rid, rtype, target, mode)); continue
                res = resolve(src_master, target)
                if rtype.endswith("/slideLayout"):
                    dl = self._copy_layout(src, res, src_master, dest_master,
                                           layout_remap, processed,
                                           src_ct_overrides)
                    new_rels.append((rid, rtype, rel_target_from(dest_master, dl), ""))
                elif rtype.endswith("/theme"):
                    # Themes share the same remap dict as everything else;
                    # _copy_theme dedups via that dict against earlier
                    # references to the same source theme.
                    dt = self._copy_theme(src, res, layout_remap)
                    new_rels.append((rid, rtype, rel_target_from(dest_master, dt), ""))
                else:
                    d, rel_tgt = self._route_dep(src, res, dest_master,
                                                 processed, layout_remap,
                                                 src_ct_overrides)
                    if d:
                        new_rels.append((rid, rtype, rel_tgt, ""))
                    else:
                        new_rels.append((rid, rtype, target, mode))

            # Re-key sldLayoutId values inside this master into a reserved
            # contiguous block. Source masters typically carry ids starting at
            # 2147484036 which collide with the new sldMasterId we're about to
            # assign and with every other merged master's layouts. r:id values
            # stay as-is because they're local to the master's rels part.
            master_root = pxml(src.get(src_master, b""))
            layout_id_lst = master_root.find("p:sldLayoutIdLst", self.pns)
            n_layouts_in_master = len(layout_id_lst) if layout_id_lst is not None else 0

            new_master_id = self.next_master_id
            self.next_master_id += 1 + n_layouts_in_master  # reserve master + its layouts

            if layout_id_lst is not None:
                for i, el in enumerate(layout_id_lst, start=1):
                    el.set("id", str(new_master_id + i))

            self.parts[dest_master] = sxml(master_root)
            self.parts[rels_path(dest_master)] = sxml(make_rels(new_rels))
            self.ct_overrides[f"/{dest_master}"] = KNOWN_CT["slideMaster"]

            pres_rid = self._pres_rid()
            rel_el = etree.SubElement(self.pres_rel, f"{{{REL_NS}}}Relationship")
            rel_el.set("Id", pres_rid)
            rel_el.set("Type", f"{R_NS}/slideMaster")
            rel_el.set("Target", f"slideMasters/slideMaster{self.n_masters}.xml")
            mid_lst = self.pres_el.find("p:sldMasterIdLst", self.pns)
            if mid_lst is not None:
                el = etree.SubElement(mid_lst, f"{{{PPT_NS}}}sldMasterId")
                el.set("id", str(new_master_id))
                el.set(f"{{{R_NS}}}id", pres_rid)

        # ---- Copy slides ----
        # Order slides by sldIdLst position (canonical presentation order),
        # falling back to slide{N}.xml number if sldIdLst is absent. This
        # matches what users mean by "slide 3" in the CLI selector.
        ordered_slides = self._src_slides_in_order(src, src_pres_rel)
        if wanted is not None:
            ordered_slides = [p for i, p in enumerate(ordered_slides, start=1) if i in wanted]
        n_slides_picked = 0

        for src_slide in ordered_slides:
            if src_slide not in src: continue

            dest_slide = f"ppt/slides/slide{self.next_slide_num}.xml"
            self.next_slide_num += 1
            self.n_slides += 1
            n_slides_picked += 1
            layout_remap[src_slide] = dest_slide  # pre-register so notes back-refs resolve

            new_rels = []
            for rid, rtype, target, mode in parse_rels(src, src_slide):
                if mode == "External":
                    new_rels.append((rid, rtype, target, mode)); continue
                res = resolve(src_slide, target)
                if rtype.endswith("/slideLayout"):
                    dl = layout_remap.get(res)
                    if dl:
                        new_rels.append((rid, rtype, rel_target_from(dest_slide, dl), ""))
                    else:
                        new_rels.append((rid, rtype, target, mode))
                else:
                    d, rel_tgt = self._route_dep(src, res, dest_slide,
                                                 processed, layout_remap,
                                                 src_ct_overrides)
                    if d:
                        new_rels.append((rid, rtype, rel_tgt, ""))
                    else:
                        new_rels.append((rid, rtype, target, mode))

            self.parts[dest_slide] = src.get(src_slide, b"")
            self.parts[rels_path(dest_slide)] = sxml(make_rels(new_rels))
            self.ct_overrides[f"/{dest_slide}"] = KNOWN_CT["slide"]

            pres_rid = self._pres_rid()
            rel_el = etree.SubElement(self.pres_rel, f"{{{REL_NS}}}Relationship")
            rel_el.set("Id", pres_rid)
            rel_el.set("Type", f"{R_NS}/slide")
            rel_el.set("Target", dest_slide[len("ppt/"):])  # rel to ppt/
            sld_id_lst = self.pres_el.find("p:sldIdLst", self.pns)
            if sld_id_lst is not None:
                el = etree.SubElement(sld_id_lst, f"{{{PPT_NS}}}sldId")
                el.set("id", str(self.next_slide_id))
                el.set(f"{{{R_NS}}}id", pres_rid)
                self.next_slide_id += 1

        log.info(
            "  +%d slides; cumulative: %d slides, %d masters, %d layouts",
            n_slides_picked, self.n_slides, self.n_masters, self.n_layouts
        )
        return n_slides_picked

    def _src_slides_in_order(self, src, src_pres_rel):
        """Return source slide part paths in canonical sldIdLst order.
        Falls back to slide{N}.xml number ordering when sldIdLst is missing."""
        target_for = {r.get("Id"): r.get("Target", "") for r in src_pres_rel
                      if r.get("Type", "").endswith("/slide")}
        order = []
        try:
            src_pres = pxml(src["ppt/presentation.xml"])
            sld_lst = src_pres.find("p:sldIdLst", self.pns)
        except (KeyError, etree.XMLSyntaxError) as e:
            self._warn(f"_src_slides_in_order: cannot read presentation.xml: {e}")
            sld_lst = None
        if sld_lst is not None and len(sld_lst) > 0:
            for sld in sld_lst:
                rid = sld.get(f"{{{R_NS}}}id")
                t = target_for.get(rid)
                if t:
                    p = resolve("ppt/presentation.xml", t)
                    if p in src:
                        order.append(p)
            if order:
                return order
        # Fallback
        for t in sorted(target_for.values(), key=slide_num):
            p = resolve("ppt/presentation.xml", t)
            if p in src:
                order.append(p)
        return order

    def filter_base_slides(self, wanted):
        """Drop unwanted slides from the base file.

        wanted is a set of 1-based positions in sldIdLst order. Removes the
        slide part, its .rels, the linked notesSlide (if any) and its .rels,
        the corresponding sldId entry, and the presentation rel pointing at
        the slide. Recomputes n_slides / n_notes after removal.
        """
        if wanted is None:
            return 0
        sld_lst = self.pres_el.find("p:sldIdLst", self.pns)
        if sld_lst is None:
            return 0
        target_for = {r.get("Id"): r.get("Target", "") for r in self.pres_rel
                      if r.get("Type", "").endswith("/slide")}

        drop_rids, drop_slides, kept = [], [], 0
        for i, sld_el in enumerate(list(sld_lst), start=1):
            if i in wanted:
                kept += 1
                continue
            sld_lst.remove(sld_el)
            rid = sld_el.get(f"{{{R_NS}}}id")
            drop_rids.append(rid)
            t = target_for.get(rid, "")
            if t:
                drop_slides.append(resolve("ppt/presentation.xml", t))

        # Drop slide rels from presentation.xml.rels
        for r in list(self.pres_rel):
            if r.get("Id") in drop_rids:
                self.pres_rel.remove(r)

        # For each dropped slide, also drop its .rels and the linked notesSlide
        for sp in drop_slides:
            notes_path = None
            rp = rels_path(sp)
            if rp in self.parts:
                try:
                    root = pxml(self.parts[rp])
                except etree.XMLSyntaxError as e:
                    self._warn(f"filter_base_slides: cannot parse {rp}: {e}; "
                               f"orphan notesSlide may remain")
                else:
                    for r in root:
                        if r.get("Type", "").endswith("/notesSlide"):
                            notes_path = resolve(sp, r.get("Target", ""))
                            break
            for p in (sp, rp, notes_path,
                      rels_path(notes_path) if notes_path else None):
                if not p: continue
                self.parts.pop(p, None)
                self.ct_overrides.pop(f"/{p}", None)

        # Recompute counts; next_*_num stays as-is (filenames left as gaps)
        self.n_slides = sum(1 for p in self.parts
                            if re.match(r"ppt/slides/slide\d+\.xml$", p))
        self.n_notes  = sum(1 for p in self.parts
                            if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", p))
        return kept

    def _audit_repair_risks(self):
        """Final pre-save sanity check for every PowerPoint repair trigger
        we've identified. Each check is keyed to a real failure we hit; if
        you see a warning here, the corresponding part of the merged file
        is likely to provoke the Repair pop-up.

        Returns a list of (severity, message) tuples. severity is "WARN" for
        cosmetic / probable issues and "ERROR" for things almost-certain to
        trigger Repair.
        """
        issues = []
        ns = self.pns

        # 1. sld* ID namespace uniqueness. Cross-collisions between
        #    sldMasterId, sldLayoutId, sldId trigger immediate Repair.
        ids = defaultdict(list)
        for el in self.pres_el.findall("p:sldMasterIdLst/p:sldMasterId", ns):
            ids[int(el.get("id", 0))].append("sldMasterId")
        for el in self.pres_el.findall("p:sldIdLst/p:sldId", ns):
            ids[int(el.get("id", 0))].append("sldId")
        unparseable = []
        for p in self.parts:
            if not re.match(r"ppt/slideMasters/slideMaster\d+\.xml$", p): continue
            try: root = pxml(self.parts[p])
            except etree.XMLSyntaxError as e:
                unparseable.append((p, str(e))); continue
            for el in root.findall("p:sldLayoutIdLst/p:sldLayoutId", ns):
                ids[int(el.get("id", 0))].append(f"sldLayoutId({p})")
        if unparseable:
            issues.append(("ERROR", f"{len(unparseable)} slideMasters failed to "
                           f"parse for sld*Id audit: {unparseable[0]}"))
        dups = {i: locs for i, locs in ids.items() if len(locs) > 1}
        if dups:
            issues.append(("ERROR", f"{len(dups)} duplicate sld*Id values "
                           f"(e.g. id={next(iter(dups))})"))

        # 2. Every customXml item must be registered at presentation level.
        pres_targets = set()
        for r in self.pres_rel:
            t = r.get("Target", "")
            if "customXml/item" in t and "itemProps" not in t:
                pres_targets.add(t.rsplit("/", 1)[-1])
        items = {os.path.basename(p) for p in self.parts
                 if re.match(r"customXml/item\d+\.xml$", p)}
        unregistered = items - pres_targets
        if unregistered:
            issues.append(("ERROR", f"customXml items missing pres-level rel: "
                           f"{sorted(unregistered)[:3]}"))

        # 3. Every customXml item must start with <?xml ... ?>. Templafy
        #    sometimes omits this; PowerPoint repair-deletes the part and
        #    every slide rel that referenced it.
        no_decl = []
        for p in self.parts:
            if re.match(r"customXml/item(?:Props)?\d+\.xml$", p):
                if not self.parts[p].lstrip().startswith(b"<?xml"):
                    no_decl.append(p)
        if no_decl:
            issues.append(("ERROR", f"customXml without <?xml ?> decl: "
                           f"{no_decl[:3]}"))

        # 4. No customXml item should be a logical-content duplicate of
        #    another (PowerPoint dedups the survivors and strips refs).
        seen = {}
        dup_groups = {}
        for p in sorted(self.parts):
            if not re.match(r"customXml/item\d+\.xml$", p): continue
            h = hashlib.sha256(self._strip_xml_decl(self.parts[p])).hexdigest()
            if h in seen:
                dup_groups.setdefault(h, [seen[h]]).append(p)
            else:
                seen[h] = p
        if dup_groups:
            issues.append(("WARN", f"{len(dup_groups)} customXml duplicate "
                           f"groups remain (Templafy quirk; usually tolerated)"))

        # 5. Comment files must not contain <p188:extLst> with <p:ext>
        #    children (Sch_UndeclaredAttribute → Repair).
        offending = []
        unparseable_comments = []
        for p in self.parts:
            if not (p.startswith("ppt/comments/") and p.endswith(".xml")): continue
            try: root = pxml(self.parts[p])
            except etree.XMLSyntaxError as e:
                unparseable_comments.append((p, str(e))); continue
            for el in root.iter(f"{{{P188_NS}}}extLst"):
                if any(c.tag == f"{{{PPT_NS}}}ext" for c in el):
                    offending.append(p); break
        if offending:
            issues.append(("ERROR", f"comments with <p:ext> in <p188:extLst>: "
                           f"{offending[:3]}"))
        if unparseable_comments:
            issues.append(("ERROR", f"{len(unparseable_comments)} comments "
                           f"failed to parse: {unparseable_comments[0]}"))

        # 6. Every authorId referenced by a comment must exist in
        #    authors.xml (modern) or commentAuthors.xml (legacy).
        modern_a = set()
        if "ppt/authors.xml" in self.parts:
            for a in pxml(self.parts["ppt/authors.xml"]):
                if a.get("id"): modern_a.add(a.get("id"))
        legacy_a = set()
        if "ppt/commentAuthors.xml" in self.parts:
            for a in pxml(self.parts["ppt/commentAuthors.xml"]):
                if a.get("id"): legacy_a.add(a.get("id"))
        ref_modern = ref_legacy = 0
        miss_modern = set(); miss_legacy = set()
        for p in self.parts:
            if not p.startswith("ppt/comments/"): continue
            try: root = pxml(self.parts[p])
            except etree.XMLSyntaxError: continue  # already reported above
            for el in root.iter():
                aid = el.get("authorId")
                if not aid: continue
                if aid.startswith("{"):
                    ref_modern += 1
                    if aid not in modern_a: miss_modern.add(aid)
                else:
                    ref_legacy += 1
                    if aid not in legacy_a: miss_legacy.add(aid)
        if miss_modern:
            issues.append(("ERROR", f"{len(miss_modern)} modern authorIds in comments "
                           f"missing from authors.xml"))
        if miss_legacy:
            issues.append(("ERROR", f"{len(miss_legacy)} legacy authorIds in comments "
                           f"missing from commentAuthors.xml"))

        # 7. notesMaster reference must resolve.
        nm_el = self.pres_el.find("p:notesMasterIdLst/p:notesMasterId", ns)
        if nm_el is not None:
            rid = nm_el.get(f"{{{R_NS}}}id")
            target = None
            for r in self.pres_rel:
                if r.get("Id") == rid: target = r.get("Target"); break
            if target:
                resolved = resolve("ppt/presentation.xml", target)
                if resolved not in self.parts:
                    issues.append(("ERROR", f"notesMaster rel points at missing "
                                   f"part: {resolved}"))

        # 8a. Body r:id references must resolve via the part's rels. After
        #     verbatim copy of slides/layouts/masters, an unhandled dep gets
        #     written to rels with the original target which then dangles
        #     and is purged at save — leaving body refs pointing nowhere.
        #     PowerPoint repair-removes those body elements (drops shapes!).
        body_rid_misses = []
        unparseable_bodies = []
        for p in self.parts:
            if not re.match(r"ppt/(slides|slideLayouts|slideMasters|notesSlides|notesMasters|handoutMasters)/[^/]+\.xml$", p):
                continue
            try:
                root = pxml(self.parts[p])
            except etree.XMLSyntaxError as e:
                unparseable_bodies.append((p, str(e)))
                continue
            refs = set()
            for el in root.iter():
                for attr in (f"{{{R_NS}}}id", f"{{{R_NS}}}embed",
                             f"{{{R_NS}}}link"):
                    v = el.get(attr)
                    if v: refs.add(v)
            rp = rels_path(p)
            rels = set()
            if rp in self.parts:
                try:
                    for r in pxml(self.parts[rp]):
                        rels.add(r.get("Id"))
                except etree.XMLSyntaxError as e:
                    self._warn(f"audit body-rid: cannot parse rels {rp}: {e}")
            missing = refs - rels
            if missing:
                body_rid_misses.append((p, sorted(missing)[:3]))
        if body_rid_misses:
            issues.append(("ERROR", f"{len(body_rid_misses)} parts have body "
                           f"r:id refs missing from rels (e.g. {body_rid_misses[0]})"))
        if unparseable_bodies:
            issues.append(("ERROR", f"{len(unparseable_bodies)} part bodies "
                           f"failed to parse: {unparseable_bodies[0]}"))

        # 8. Every part in [Content_Types].xml Override must exist; every
        #    part in the package must have an Override or matching Default.
        orphan = [pn for pn in self.ct_overrides if pn.lstrip("/") not in self.parts]
        if orphan:
            issues.append(("WARN", f"{len(orphan)} orphan content-type "
                           f"Overrides (purged at save anyway): {orphan[:3]}"))
        no_ct = []
        for p in self.parts:
            if p == "[Content_Types].xml" or p.endswith(".rels"): continue
            if f"/{p}" in self.ct_overrides: continue
            ext = p.rsplit(".", 1)[-1] if "." in p else ""
            if ext in self.ct_defaults: continue
            no_ct.append(p)
        if no_ct:
            issues.append(("ERROR", f"{len(no_ct)} parts have no content type: "
                           f"{no_ct[:3]}"))

        return issues

    def _purge_dangling_rels(self):
        """Remove rels entries pointing to parts that don't exist in the archive."""
        rels_parts = [p for p in list(self.parts) if p.endswith(".rels")]
        for rp in rels_parts:
            # Derive the owner part path from the rels path.
            # "ppt/slides/_rels/slide1.xml.rels" -> "ppt/slides/slide1.xml"
            # "_rels/.rels"                       -> ""   (package root)
            split = rp.rsplit("_rels/", 1)
            if len(split) != 2:
                continue  # unexpected format, skip
            prefix, fname = split
            if not fname.endswith(".rels"):
                continue
            owner = prefix + fname[:-len(".rels")]  # strip trailing .rels
            # owner="" means package root; resolve() handles that correctly
            try:
                root = pxml(self.parts[rp])
            except etree.XMLSyntaxError as e:
                self._warn(f"_purge_dangling_rels: cannot parse {rp}: {e}; "
                           f"dangling rels in this file remain")
                continue
            changed = False
            for r in list(root):
                if r.get("TargetMode") == "External":
                    continue
                target = r.get("Target", "")
                resolved = resolve(owner, target)
                if resolved not in self.parts:
                    root.remove(r)
                    changed = True
            if changed:
                if len(root) == 0:
                    del self.parts[rp]
                else:
                    self.parts[rp] = sxml(root)

    def save(self, output_path):
        # Remove dangling rels from presentation.xml.rels before saving
        for r in list(self.pres_rel):
            target = r.get("Target", "")
            resolved = resolve("ppt/presentation.xml", target)
            if r.get("TargetMode") != "External" and resolved not in self.parts:
                self.pres_rel.remove(r)

        # Purge dangling rels from all parts
        self._purge_dangling_rels()

        # The audit lives in `_audit_repair_risks()` and is exposed for
        # callers (the CLI in main() runs it explicitly so it can decide
        # how to react under --strict / --lenient). save() no longer logs
        # the audit itself — that produced duplicate lines when the CLI
        # also called it. Library users wanting the audit should call
        # `_audit_repair_risks()` directly before/after save().

        self.parts["ppt/presentation.xml"]            = sxml(self.pres_el)
        self.parts["ppt/_rels/presentation.xml.rels"] = sxml(self.pres_rel)

        # Use default namespace (no prefix) — Open XML SDK requires <Types xmlns="..."> not <ns0:Types>
        ct_root = etree.Element("Types", nsmap={None: CT_NS})
        for ext, ct in self.ct_defaults.items():
            el = etree.SubElement(ct_root, "Default")
            el.set("Extension", ext); el.set("ContentType", ct)
        seen_overrides = set()
        for pname, ct in self.ct_overrides.items():
            if ct and pname not in seen_overrides:
                seen_overrides.add(pname)
                el = etree.SubElement(ct_root, "Override")
                el.set("PartName", pname); el.set("ContentType", ct)
        self.parts["[Content_Types].xml"] = sxml(ct_root)

        tmp = output_path + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in self.parts.items():
                zf.writestr(name, data)
        os.replace(tmp, output_path)


def parse_slide_selector(s):
    """Parse a slide selector string into a set of 1-based positions.

    Returns None for "all" or an empty selector (means "every slide").
    Accepts comma-separated tokens; each token is either a positive integer
    or an inclusive A-B range. Examples: "1,3,5", "2-7", "1,3,5-9,12".

    Raises ValueError on malformed input or non-positive slide numbers.
    """
    if s is None:
        return None

    s = s.strip()
    if not s or s.lower() == "all":
        return None

    out = set()
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue

        if "-" in tok:
            a_str, b_str = tok.split("-", 1)
            try:
                a, b = int(a_str.strip()), int(b_str.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid range token: {tok!r}") from exc
            if a < 1 or b < 1:
                raise ValueError(f"Slide numbers must be >= 1: {tok!r}")
            if a > b:
                a, b = b, a
            out.update(range(a, b + 1))
        else:
            try:
                n = int(tok)
            except ValueError as exc:
                raise ValueError(f"Invalid slide token: {tok!r}") from exc
            if n < 1:
                raise ValueError(f"Slide numbers must be >= 1: {tok!r}")
            out.add(n)

    return out

def parse_source_arg(arg):
    """'<path>[:<slides>]' -> (path, wanted_set_or_None).

    Uses rsplit so Windows drive letters survive ('C:\\foo\\deck.pptx:1,2').
    A bare '<path>' (no colon) means 'all slides'.
    """
    if ":" not in arg:
        return arg, None
    path, sel = arg.rsplit(":", 1)
    # If the right-hand side doesn't look like a selector (e.g. it's a Windows
    # drive letter and there's no further colon), treat the whole arg as path.
    try:
        wanted = parse_slide_selector(sel)
    except ValueError:
        return arg, None
    return path, wanted


def _build_arg_parser():
    """Return the argparse.ArgumentParser used by main().

    Kept as a module-level function so tests can introspect the parser
    without invoking main() (e.g. `parser.parse_args([...])`).
    """
    import argparse
    p = argparse.ArgumentParser(
        prog="pptx-merge",
        description=(
            "Merge multiple PPTX files into one, preserving each source's "
            "masters/layouts/themes/media. Output passes the OOXML SDK "
            "validator and opens in PowerPoint without the Repair dialog."
        ),
        epilog=(
            "Examples:\n"
            "  pptx-merge out.pptx deck1.pptx deck2.pptx\n"
            "  pptx-merge out.pptx deck1.pptx:1,3,5 deck2.pptx:all\n"
            "  pptx-merge --strict --log-level=DEBUG out.pptx deck1.pptx deck2.pptx\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("output", help="Path to the merged PPTX to create")
    p.add_argument(
        "sources", nargs="+",
        help="One or more <pptx>[:<slides>] sources (slides='all'|'1,3'|'2-7')",
    )
    p.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if the audit emits any ERROR (recommended for CI)",
    )
    p.add_argument(
        "--lenient", action="store_true",
        help="Suppress audit WARN-level findings (errors still surface)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Validate, merge, audit — but don't write the output file",
    )
    p.add_argument(
        "--audit-only", action="store_true",
        help="Pre-flight every source then exit. No merging.",
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: INFO)",
    )
    p.add_argument(
        "--max-input-mb", type=float, default=None, metavar="MB",
        help="Refuse any single source larger than this (default: no limit)",
    )
    p.add_argument(
        "--version", action="version", version=f"pptx-merge {__version__}",
    )
    return p


def _configure_logging(level_name):
    """Wire the module logger to a stderr StreamHandler at the given level.

    main() invokes this once, after parsing args. Library users importing
    Merger directly are unaffected (the NullHandler attached at module
    import-time keeps logger output silent for them).
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(getattr(logging, level_name))


def _emit_result(result, exit_code=0):
    """Print the JSON result line and exit. Used by main() for both success
    and failure paths so the caller always gets one parseable JSON line."""
    print(json.dumps(result, separators=(",", ": ")))
    sys.exit(exit_code)


def main(argv=None):
    """CLI entry point. argv is overrideable for in-process testing."""
    import time
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    started = time.monotonic()
    max_bytes = int(args.max_input_mb * 1024 * 1024) if args.max_input_mb else None

    # ---- Parse + pre-flight every source up front ----
    sources = []
    input_bytes = 0
    for arg in args.sources:
        try:
            path, wanted = parse_source_arg(arg)
        except ValueError as e:
            _emit_result({"error": f"Bad selector in {arg!r}: {e}"}, 2)
        try:
            input_bytes += preflight_source(path, max_bytes=max_bytes)
        except ValueError as e:
            _emit_result({"error": str(e)}, 2)
        sources.append((path, wanted))

    base_path, base_wanted = sources[0]
    result = {
        "output": args.output if not args.dry_run else None,
        "version": __version__,
        "sources": [],
        "input_bytes": input_bytes,
        "dry_run": args.dry_run,
    }

    if args.audit_only:
        result["audit_only"] = True
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        log.info("audit-only: %d sources OK", len(sources))
        _emit_result(result, 0)

    try:
        log.info("base: %s", os.path.basename(base_path))
        m = Merger(base_path)
        if base_wanted is not None:
            kept = m.filter_base_slides(base_wanted)
            log.info("filtered base to %d slides", kept)
        log.info("base loaded: %d slides, %d masters, %d layouts",
                 m.n_slides, m.n_masters, m.n_layouts)
        result["sources"].append({"file": base_path, "slides": m.n_slides})

        for path, wanted in sources[1:]:
            n_added = m.merge_file(path, wanted)
            result["sources"].append({"file": path, "slides": n_added})

        # Run audit BEFORE save so --dry-run still validates.
        audit_results = m._audit_repair_risks()
        errors  = [msg for sev, msg in audit_results if sev == "ERROR"]
        warnings = [msg for sev, msg in audit_results if sev == "WARN"]
        result["audit"] = {"errors": errors}
        if not args.lenient:
            result["audit"]["warnings"] = warnings
        for msg in errors:
            log.error("audit: %s", msg)
        if not args.lenient:
            for msg in warnings:
                log.warning("audit: %s", msg)

        if args.dry_run:
            log.info("dry-run: skipping save")
        else:
            log.info("saving -> %s", args.output)
            m.save(args.output)
            result["output_bytes"] = os.path.getsize(args.output)

        result.update({
            "slides_total":  m.n_slides,
            "masters_total": m.n_masters,
            "layouts_total": m.n_layouts,
            "duration_seconds": round(time.monotonic() - started, 3),
        })
        log.info("done — %d slides, audit errors=%d warnings=%d",
                 m.n_slides, len(errors), len(warnings))

        # --strict promotes audit errors to a non-zero exit code so CI
        # pipelines fail loud on a likely-broken output.
        if args.strict and errors:
            _emit_result(result, 3)
        _emit_result(result, 0)

    except ValueError as e:
        # Expected validation errors (slide-size mismatch, etc.). Already
        # logged inside the Merger — surface clean exit code 2.
        log.error("%s", e)
        result["error"] = str(e)
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        _emit_result(result, 2)
    except Exception as e:
        log.exception("merge failed")
        result["error"] = f"{type(e).__name__}: {e}"
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        _emit_result(result, 1)


if __name__ == "__main__":
    main()
