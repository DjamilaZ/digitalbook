import os
import json
import re
import pdfplumber
import fitz
from PIL import Image
import io
import hashlib
from collections import defaultdict
import pytesseract

def normalize_ws(s: str) -> str:
    return (
        s.replace("\u00A0", " ")
         .replace("\u202F", " ")
         .replace("\u2009", " ")
         .replace("\u200A", " ")
         .replace("\u2007", " ")
         .replace("\u2002", " ")
         .replace("\u2003", " ")
         .replace("\u2004", " ")
         .replace("\u2005", " ")
         .replace("\u2006", " ")
         .replace("\u2008", " ")
         .replace("\u205F", " ")
         .replace("\u200B", "")
         .replace("\ufeff", "")
    )

def split_heading_title_and_content(s: str):
    if ":" in s:
        left, right = s.split(":", 1)
        left = left.strip()
        right = right.strip()
        return left, (right if right else None)
    return s.strip(), None

def is_page_number_line(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}", s))

def parse_marked_pdf(pdf_path: str):
    result = {"thematiques": [], "chapters_sans_thematique": []}
    structure = result["chapters_sans_thematique"]
    current_thematique = None
    current_chapter = None
    current_section = None
    current_subsection = None
    ignore_mode = False
    ignored_repeat = set()
    try:
        ignored_repeat = collect_repeating_headers_footers(pdf_path)
    except Exception:
        pass
    # Regions for typed zones (used to filter content inside !!! table areas)
    regions_by_page = {}
    try:
        regions_by_page = collect_capture_regions(pdf_path)
    except Exception:
        regions_by_page = {}
    # Auto-detected table regions (to avoid adding table body into textual content)
    auto_table_regions = {}
    try:
        auto_table_regions = collect_auto_table_regions(pdf_path)
    except Exception:
        auto_table_regions = {}
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages):
            page_height = float(page.height)
            page_width = float(page.width)
            lines = _page_lines_with_boxes(page)
            if not lines:
                continue
            # Cas particulier OCR : certaines pages scannées donnent une ligne '##' seule
            # puis la ligne suivante '1.3 ...'. On mémorise qu'un marqueur de section
            # vient d'apparaître pour promouvoir la ligne suivante en titre de section.
            pending_hash_section = False
            # Même idée pour une ligne '#' seule : la ligne suivante devient un titre
            # (chapitre si aucun chapitre courant, sinon section du chapitre courant).
            pending_hash_chapter = False
            # merge typed regions and auto-detected table regions
            page_regions = (regions_by_page.get(page_index + 1, []) or []) + (auto_table_regions.get(page_index + 1, []) or [])
            for ln in lines:
                line = normalize_ws(ln.get('text', '')).strip()
                if not line:
                    continue
                if is_page_number_line(line):
                    continue
                if line in ignored_repeat:
                    continue
                # Determine if this line lies inside a typed table region (to avoid false chapter detections)
                in_typed_table = False
                try:
                    if page_regions:
                        ymid = (float(ln.get('y0', 0.0)) + float(ln.get('y1', 0.0))) / 2.0
                        lx0 = float(ln.get('x0', 0.0))
                        lx1 = float(ln.get('x1', page_width))
                        def _overlap(a0, a1, b0, b1):
                            return not (a1 <= b0 or a0 >= b1)
                        in_typed_table = any(
                            (r.get('kind') == 'table')
                            and (float(r['y0']) <= ymid <= float(r['y1']))
                            and _overlap(lx0, lx1, float(r.get('x0', 0.0)), float(r.get('x1', page_width)))
                            for r in page_regions
                        )
                except Exception:
                    in_typed_table = False
                # Compute relative vertical position for heading heuristics
                ymid = (float(ln.get('y0', 0.0)) + float(ln.get('y1', 0.0))) / 2.0
                top_zone_ch = page_height * 0.35
                top_zone_sec = page_height * 0.5
                marker_bang = line.replace('！', '!').replace('﹗', '!').replace('︕', '!')
                if re.match(r'^\s*[\-\u2022•▪·»]*\s*!!\s*/\s*$', marker_bang):
                    ignore_mode = False
                    continue
                if re.match(r'^\s*[\-\u2022•▪·»]*\s*!!(?!/).*$' , marker_bang):
                    ignore_mode = True
                    continue
                if ignore_mode:
                    continue
                marker = marker_bang
                # Skip region capture markers from structure/content
                if re.match(r'^\s*!!!\s*/\s*$', marker) or re.match(r'^\s*!!!(?!/).*$' , marker):
                    continue
                # Skip typed region tags <table>, </table>, <img>, </img> from structure/content
                if re.match(r'^\s*<\s*/?\s*table\s*>\s*$', marker, flags=re.IGNORECASE) or \
                   re.match(r'^\s*<\s*/?\s*img\s*>\s*$', marker, flags=re.IGNORECASE):
                    continue
                if re.match(r'^\s*!\s*/\s*$', marker):
                    if current_thematique and 'end_page' not in current_thematique:
                        current_thematique['end_page'] = page_index + 1
                    current_thematique = None
                    structure = result["chapters_sans_thematique"]
                    current_chapter = None
                    current_section = None
                    current_subsection = None
                    continue
                m_theme = re.match(r'^\s*!\s*(.+)$', marker)
                m_sub = re.match(r'^\s*#{3,}\s*(.+)$', line)
                m_sec = re.match(r'^\s*##(?!#)\s*(.+)$', line)
                m_ch = re.match(r'^\s*#(?!#)\s*(.+)$', line)
                # Heuristics for numeric/keyword headings when '#' not present
                m_ch_num = None
                m_sec_num = None
                # Chapter-like: within top zone, accept even if inside typed table (to not miss headings near tables)
                if ymid <= top_zone_ch:
                    m_ch_num = re.match(r'^\s*\d{1,2}\s*[\.)]\s*(.+)$', line)
                    if not m_ch_num and re.match(r'^\s*(Appendix\s+[A-Z]|Glossary|Further\s+Reading)\b', line, flags=re.IGNORECASE):
                        m_ch_num = re.match(r'^(.*)$', line)
                # Section-like: allow a bit deeper zone
                if ymid <= top_zone_sec:
                    m_sec_num = re.match(r'^\s*\d{1,2}\.\d+\s+(.+)$', line)

                # Cas OCR : si la ligne précédente était exactement '##',
                # on traite cette ligne numérique comme un titre de section.
                if pending_hash_section and not m_sec and not m_sec_num:
                    m_sec_num = re.match(r'^\s*\d{1,2}\.\d+\s+(.+)$', line)
                # Une fois la ligne courante analysée, on réinitialise le flag
                # (on ne veut l'appliquer que sur la ligne immédiatement suivante).
                if not re.fullmatch(r'^\s*##\s*$', line):
                    pending_hash_section = False

                # Cas OCR : si la ligne précédente était exactement '#', cette ligne
                # devient toujours un titre de CHAPITRE (comme si on avait "# Titre" sur
                # une seule ligne), quel que soit l'état courant.
                if pending_hash_chapter:
                    pending_hash_chapter = False
                    ch_title = line.strip()
                    if ch_title:
                        # Fermer proprement la sous-structure en cours
                        if current_subsection and 'end_page' not in current_subsection:
                            current_subsection['end_page'] = page_index + 1
                        if current_section and 'end_page' not in current_section:
                            current_section['end_page'] = page_index + 1
                        if current_chapter and 'end_page' not in current_chapter:
                            current_chapter['end_page'] = page_index + 1
                        current_chapter = {"title": ch_title, "content": [], "sections": [], "images": [], "tables": [], "start_page": page_index + 1}
                        structure.append(current_chapter)
                        current_section = None
                        current_subsection = None
                        continue
                if m_theme:
                    if current_thematique and 'end_page' not in current_thematique:
                        current_thematique['end_page'] = page_index + 1
                    raw_theme = m_theme.group(1).strip()
                    left, right = split_heading_title_and_content(raw_theme)
                    theme = {"title": left, "description": right or "", "chapters": [], "start_page": page_index + 1}
                    result["thematiques"].append(theme)
                    current_thematique = theme
                    structure = current_thematique["chapters"]
                    current_chapter = None
                    current_section = None
                    current_subsection = None
                    continue
                if m_ch or (m_ch_num and not m_ch):
                    if current_subsection and 'end_page' not in current_subsection:
                        current_subsection['end_page'] = page_index + 1
                    if current_section and 'end_page' not in current_section:
                        current_section['end_page'] = page_index + 1
                    if current_chapter and 'end_page' not in current_chapter:
                        current_chapter['end_page'] = page_index + 1
                    ch_title = (m_ch.group(1) if m_ch else m_ch_num.group(1)).strip()
                    current_chapter = {"title": ch_title, "content": [], "sections": [], "images": [], "tables": [], "start_page": page_index + 1}
                    structure.append(current_chapter)
                    current_section = None
                    current_subsection = None
                    continue
                if m_sec or (m_sec_num and not m_sec):
                    if current_chapter is None:
                        # Ignore sections until a chapter '#' is explicitly set
                        continue
                    if current_subsection and 'end_page' not in current_subsection:
                        current_subsection['end_page'] = page_index + 1
                    if current_section and 'end_page' not in current_section:
                        current_section['end_page'] = page_index + 1
                    sec_title = (m_sec.group(1) if m_sec else m_sec_num.group(1)).strip()
                    current_section = {"title": sec_title, "content": [], "subsections": [], "images": [], "tables": [], "start_page": page_index + 1}
                    current_chapter["sections"].append(current_section)
                    current_subsection = None
                    continue
                if m_sub:
                    if current_chapter is None:
                        # Ignore subsections until a chapter '#' is explicitly set
                        continue
                    if current_subsection and 'end_page' not in current_subsection:
                        current_subsection['end_page'] = page_index + 1
                    sub_title = m_sub.group(1).strip()
                    if current_section is None:
                        # Create a default section only if a chapter exists
                        current_section = {"title": "Section", "content": [], "subsections": [], "images": [], "tables": [], "start_page": page_index + 1}
                        current_chapter["sections"].append(current_section)
                    current_subsection = {"title": sub_title, "content": [], "images": [], "tables": [], "start_page": page_index + 1}
                    current_section["subsections"].append(current_subsection)
                    continue
                # Si la ligne est exactement '##' (cas OCR), on ne l'ajoute pas au contenu
                # mais on marque que la prochaine ligne numérique pourra devenir une section.
                if re.fullmatch(r'^\s*##\s*$', line):
                    pending_hash_section = True
                    continue

                # Si la ligne est exactement '#' (cas OCR), on ne l'ajoute pas au contenu
                # mais on marque que la prochaine ligne deviendra un titre (chapitre ou section).
                if re.fullmatch(r'^\s*#\s*$', line):
                    pending_hash_chapter = True
                    continue

                # Skip figure/table caption lines from textual content
                if re.match(r"^(?:fig(?:ure)?\.?)[\s\u00A0]*\d*\s*[:.-]?\s*.+$", line, flags=re.IGNORECASE):
                    continue
                if re.match(r"^(?:tableau|table)\s*\d*\s*[:.-]?\s*.+$", line, flags=re.IGNORECASE):
                    continue
                if re.search(r"\*(.+?)\*", line):
                    continue
                # Skip lines inside typed table regions to avoid duplicating into textual content
                if in_typed_table:
                    continue
                if current_subsection is not None:
                    current_subsection["content"].append(line)
                elif current_section is not None:
                    current_section["content"].append(line)
                elif current_chapter is not None:
                    current_chapter["content"].append(line)
        if current_subsection and 'end_page' not in current_subsection:
            current_subsection['end_page'] = total_pages
        if current_section and 'end_page' not in current_section:
            current_section['end_page'] = total_pages
        if current_chapter and 'end_page' not in current_chapter:
            current_chapter['end_page'] = total_pages
        if current_thematique and 'end_page' not in current_thematique:
            current_thematique['end_page'] = total_pages
    return result

def ocr_page(page):
    """Retourne du texte OCR pour une page pdfplumber.

    Utilisé uniquement en secours quand extract_text() ne retourne rien.
    """
    try:
        try:
            # pdfplumber >=0.5: page.to_image
            pil_img = page.to_image(resolution=300).original
        except Exception:
            # Fallback: utiliser PyMuPDF si disponible via parent
            pdf = page.parent
            try:
                doc = pdf.doc  # type: ignore[attr-defined]
            except Exception:
                return ""
            try:
                pno = page.page_number - 1 if hasattr(page, "page_number") else None
            except Exception:
                pno = None
            if pno is None or pno < 0:
                return ""
            try:
                fpage = doc.load_page(pno)
            except Exception:
                return ""
            try:
                pix = fpage.get_pixmap(matrix=fitz.Matrix(300/72.0, 300/72.0))
            except Exception:
                return ""
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        text = pytesseract.image_to_string(pil_img)
        return text or ""
    except Exception:
        return ""

def collect_page_captions(pdf_path: str):
    page_image_caps = {}
    page_table_caps = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                if not text.strip():
                    # Fallback OCR pour les pages scannées
                    text = ocr_page(page)
                if not text:
                    continue
                img_caps = []
                tbl_caps = []
                lines = text.split("\n")
                i = 0
                while i < len(lines):
                    line = normalize_ws(lines[i]).strip()
                    # Détection Figure avec ou sans numéro + titre évent sur ligne suivante
                    m_fig = re.match(r"^(?:fig(?:ure)?\.?)\s*\d*\s*[:.-]?\s*(.*)$", line, flags=re.IGNORECASE)
                    if m_fig:
                        cap = m_fig.group(1).strip()
                        if not cap and i+1 < len(lines):
                            cap = normalize_ws(lines[i+1]).strip()
                            i += 1
                        if cap:
                            img_caps.append(cap)
                    # Même chose pour Table/Tableau – plus souple
                    m_tab = re.match(r"^(?:tableau|table)\s*\d+\s*[:.—–-]?\s*(.*)$", line, flags=re.IGNORECASE)
                    if m_tab:
                        cap = m_tab.group(1).strip()
                        if not cap and i+1 < len(lines):
                            next_line = normalize_ws(lines[i+1])
                            if not next_line.isupper() and len(next_line) > 5:  # évite les faux positifs
                                cap = next_line.strip()
                                i += 1
                        if cap or m_tab.group(0):  # accepte même sans titre
                            tbl_caps.append(cap or "Tableau sans titre")
                    elif re.search(r"\*(.+?)\*", line):
                        for c in re.findall(r"\*(.+?)\*", line):
                            c2 = c.strip()
                            if c2:
                                img_caps.append(c2)
                    i += 1

                if img_caps:
                    page_image_caps[page_index + 1] = img_caps
                if tbl_caps:
                    page_table_caps[page_index + 1] = tbl_caps
    except Exception as e:
        pass
    return page_image_caps, page_table_caps

def _page_lines_with_boxes(page):
    try:
        chars = list(page.chars) if hasattr(page, 'chars') else []
    except Exception:
        chars = []
    if not chars:
        # fallback to words-based (may lose punctuation)
        words = page.extract_words(use_text_flow=True, keep_blank_chars=True) or []
        words.sort(key=lambda w: (float(w.get('top', 0)), float(w.get('x0', 0))))
        lines = []
        current = []
        tol = 3.0
        cur_top = None
        for w in words:
            top = float(w.get('top', 0))
            if cur_top is None or abs(top - cur_top) <= tol:
                current.append(w)
                if cur_top is None:
                    cur_top = top
            else:
                text = " ".join(item.get('text', '') for item in sorted(current, key=lambda x: x.get('x0', 0)))
                y0 = min(float(it.get('top', 0)) for it in current)
                y1 = max(float(it.get('bottom', y0+1)) for it in current)
                x0 = min(float(it.get('x0', 0)) for it in current)
                x1 = max(float(it.get('x1', x0+1)) for it in current)
                lines.append({'text': normalize_ws(text).strip(), 'y0': y0, 'y1': y1, 'x0': x0, 'x1': x1})
                current = [w]
                cur_top = top
        if current:
            text = " ".join(item.get('text', '') for item in sorted(current, key=lambda x: x.get('x0', 0)))
            y0 = min(float(it.get('top', 0)) for it in current)
            y1 = max(float(it.get('bottom', y0+1)) for it in current)
            x0 = min(float(it.get('x0', 0)) for it in current)
            x1 = max(float(it.get('x1', x0+1)) for it in current)
            lines.append({'text': normalize_ws(text).strip(), 'y0': y0, 'y1': y1, 'x0': x0, 'x1': x1})
        return lines
    chars.sort(key=lambda c: (float(c.get('top', 0)), float(c.get('x0', 0))))
    lines = []
    current = []
    tol = 3.0
    cur_top = None
    for ch in chars:
        top = float(ch.get('top', 0))
        if cur_top is None or abs(top - cur_top) <= tol:
            current.append(ch)
            if cur_top is None:
                cur_top = top
        else:
            # flush current as a line
            text = "".join(item.get('text', '') for item in sorted(current, key=lambda x: x.get('x0', 0)))
            y0 = min(float(it.get('top', 0)) for it in current)
            y1 = max(float(it.get('bottom', y0+1)) for it in current)
            x0 = min(float(it.get('x0', 0)) for it in current)
            x1 = max(float(it.get('x1', x0+1)) for it in current)
            lines.append({'text': normalize_ws(text), 'y0': y0, 'y1': y1, 'x0': x0, 'x1': x1})
            current = [ch]
            cur_top = top
    if current:
        text = "".join(item.get('text', '') for item in sorted(current, key=lambda x: x.get('x0', 0)))
        y0 = min(float(it.get('top', 0)) for it in current)
        y1 = max(float(it.get('bottom', y0+1)) for it in current)
        x0 = min(float(it.get('x0', 0)) for it in current)
        x1 = max(float(it.get('x1', x0+1)) for it in current)
        lines.append({'text': normalize_ws(text), 'y0': y0, 'y1': y1, 'x0': x0, 'x1': x1})
    # strip line texts and collapse spaces
    for ln in lines:
        ln['text'] = ln['text'].strip()
    return lines

def collect_repeating_headers_footers(pdf_path: str):
    from collections import defaultdict as _dd
    repeats = _dd(int)
    total_pages = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                total_pages += 1
                h = float(page.height)
                lines = _page_lines_with_boxes(page)
                for ln in lines:
                    y0 = float(ln.get('y0', 0.0))
                    y1 = float(ln.get('y1', 0.0))
                    mid = (y0 + y1) / 2.0
                    top_zone = h * 0.14
                    bot_zone = h * 0.86
                    if mid <= top_zone or mid >= bot_zone:
                        t = ln.get('text', '').strip()
                        if t and not is_page_number_line(t):
                            repeats[t] += 1
    except Exception:
        return set()
    thr = max(3, int(0.4 * max(1, total_pages)))
    return {t for t, c in repeats.items() if c >= thr}

def collect_capture_regions(pdf_path: str):
    regions_by_page = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            active = None  # (start_page_idx, start_y, kind)
            for pi, page in enumerate(pdf.pages):
                page_height = float(page.height)
                lines = _page_lines_with_boxes(page)
                for ln in lines:
                    text = ln['text']
                    # Chapitres/sections (lignes commençant par '#') ont la priorité :
                    # on ne les utilise jamais pour ouvrir/fermer une région.
                    if re.match(r'^\s*#', text):
                        continue

                    marker_bang = text.replace('！', '!').replace('﹗', '!').replace('︕', '!')

                    lower = marker_bang.strip().lower()

                    # --- Fin de région sur balises fermantes </table> ou </img> ---
                    if re.match(r'^\s*</\s*table\s*>\s*$', lower) or re.match(r'^\s*</\s*img\s*>\s*$', lower):
                        if active is not None:
                            sp, sy, kind = active
                            if sp == pi:
                                regions_by_page.setdefault(pi + 1, []).append({
                                    'y0': sy,
                                    'y1': max(ln['y0'], sy),
                                    'kind': kind
                                })
                            else:
                                # first partial page
                                regions_by_page.setdefault(sp + 1, []).append({'y0': sy, 'y1': pdf.pages[sp].height, 'kind': kind})
                                # middle full pages
                                for mid in range(sp + 1, pi):
                                    regions_by_page.setdefault(mid + 1, []).append({'y0': 0.0, 'y1': pdf.pages[mid].height, 'kind': kind})
                                # last partial
                                regions_by_page.setdefault(pi + 1, []).append({'y0': 0.0, 'y1': max(ln['y0'], 0.0), 'kind': kind})
                            active = None
                        continue

                    # --- Début de région sur <table> ou <img> ---
                    if re.match(r'^\s*<\s*table\s*>\s*$', lower):
                        # début de région pour un tableau
                        active = (pi, float(ln['y1']), 'table')
                        continue
                    if re.match(r'^\s*<\s*img\s*>\s*$', lower):
                        # début de région pour une image
                        active = (pi, float(ln['y1']), 'image')
                        continue
                # page end: continue until an end marker appears on later page
            # document end: if still active, close to end of last page
            if active is not None:
                sp, sy, kind = active
                regions_by_page.setdefault(sp + 1, []).append({'y0': sy, 'y1': pdf.pages[sp].height, 'kind': kind})
    except Exception:
        pass
    return regions_by_page

def collect_auto_table_regions(pdf_path: str):
    regions_by_page = {}
    try:
        # only trust auto regions on pages that actually contain a table caption
        _, page_table_caps = collect_page_captions(pdf_path)
    except Exception:
        page_table_caps = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            last_caption_page = None
            for pi, ppage in enumerate(pdf.pages):
                has_caption = bool(page_table_caps.get(pi + 1))
                allow_from_caption_window = (last_caption_page is not None) and ((pi + 1) - last_caption_page <= 2)
                if not (has_caption or allow_from_caption_window):
                    if has_caption:
                        last_caption_page = pi + 1
                    continue
                if has_caption:
                    last_caption_page = pi + 1
                tables = []
                try:
                    if hasattr(ppage, 'find_tables'):
                        ts_line = {
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "intersection_tolerance": 5,
                            "snap_tolerance": 3,
                            "edge_min_length": 3,
                            "min_words_vertical": 1,
                            "min_words_horizontal": 1,
                            "join_tolerance": 3,
                            "text_x_tolerance": 2,
                            "text_y_tolerance": 2,
                        }
                        tables = ppage.find_tables(table_settings=ts_line) or []
                        if not tables:
                            ts_text = {
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text",
                                "snap_tolerance": 3,
                                "join_tolerance": 3,
                                "text_x_tolerance": 3,
                                "text_y_tolerance": 3,
                            }
                            tables = ppage.find_tables(table_settings=ts_text) or []
                except Exception:
                    tables = []
                try:
                    pw = float(ppage.width); ph = float(ppage.height)
                except Exception:
                    pw = 1.0; ph = 1.0
                pad_x = 0.02 * pw
                pad_y0 = 0.005 * ph
                pad_y1 = 0.01 * ph
                regions_local = []
                for t in tables or []:
                    try:
                        extracted = t.extract() if hasattr(t, 'extract') else []
                        nrows = len(extracted) if extracted else 0
                        ncols = max((len(r) if r else 0) for r in extracted) if nrows > 0 else 0
                        if nrows >= 2 and ncols >= 2:
                            x0, top, x1, bottom = t.bbox
                            regions_local.append((float(x0), float(top), float(x1), float(bottom)))
                    except Exception:
                        pass
                if not regions_local:
                    try:
                        drs = ppage.parent.load_page(pi).get_drawings()
                    except Exception:
                        drs = []
                    tmp = []
                    try:
                        area_min = 0.05 * (pw * ph)
                        area_max = 0.85 * (pw * ph)
                        for d in drs or []:
                            r = d.get('rect')
                            if r is not None:
                                bb = (float(r.x0), float(r.y0), float(r.x1), float(r.y1))
                            else:
                                items = d.get('items') or []
                                xs, ys = [], []
                                for it in items:
                                    pts = it[1] if len(it) > 1 else []
                                    for pt in pts:
                                        xs.append(pt[0]); ys.append(pt[1])
                                if xs and ys:
                                    bb = (float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)))
                                else:
                                    continue
                            area = (bb[2] - bb[0]) * (bb[3] - bb[1])
                            if area_min <= area <= area_max:
                                tmp.append(bb)
                        tmp.sort(key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
                        uniq = []
                        for b in tmp:
                            if not uniq:
                                uniq.append(b)
                                continue
                            iox0 = max(b[0], uniq[-1][0]); ioy0 = max(b[1], uniq[-1][1])
                            iox1 = min(b[2], uniq[-1][2]); ioy1 = min(b[3], uniq[-1][3])
                            iow = max(0.0, iox1 - iox0); ioh = max(0.0, ioy1 - ioy0)
                            inter = iow * ioh
                            ua = (b[2]-b[0])*(b[3]-b[1]) + (uniq[-1][2]-uniq[-1][0])*(uniq[-1][3]-uniq[-1][1]) - inter
                            if ua == 0 or (inter / ua) < 0.5:
                                uniq.append(b)
                        regions_local = uniq[:2]
                    except Exception:
                        regions_local = []
                for (x0, top, x1, bottom) in regions_local:
                    regions_by_page.setdefault(pi + 1, []).append({
                        'x0': 0.0,
                        'x1': float(pw),
                        'y0': float(max(0.0, top - pad_y0)),
                        'y1': float(bottom + pad_y1),
                        'kind': 'table'
                    })
    except Exception:
        pass
    return regions_by_page

def find_node_for_page(structured_data, page_num):
    node = {"thematique": None, "chapter": None, "section": None, "subsection": None}
    for th in structured_data.get("thematiques", []):
        ts = th.get("start_page", 0)
        te = th.get("end_page", 0)
        if ts and te and ts <= page_num <= te:
            node["thematique"] = th
            for ch in th.get("chapters", []):
                cs = ch.get("start_page", 0)
                ce = ch.get("end_page", 0)
                if cs and ce and cs <= page_num <= ce:
                    node["chapter"] = ch
                    for sec in ch.get("sections", []):
                        ss = sec.get("start_page", 0)
                        se = sec.get("end_page", 0)
                        if ss and se and ss <= page_num <= se:
                            node["section"] = sec
                            for sub in sec.get("subsections", []):
                                sss = sub.get("start_page", 0)
                                sse = sub.get("end_page", 0)
                                if sss and sse and sss <= page_num <= sse:
                                    node["subsection"] = sub
                                    return node
                            return node
                    return node
            return node
    for ch in structured_data.get("chapters_sans_thematique", []):
        cs = ch.get("start_page", 0)
        ce = ch.get("end_page", 0)
        if cs and ce and cs <= page_num <= ce:
            node["chapter"] = ch
            for sec in ch.get("sections", []):
                ss = sec.get("start_page", 0)
                se = sec.get("end_page", 0)
                if ss and se and ss <= page_num <= se:
                    node["section"] = sec
                    for sub in sec.get("subsections", []):
                        sss = sub.get("start_page", 0)
                        sse = sub.get("end_page", 0)
                        if sss and sse and sss <= page_num <= sse:
                            node["subsection"] = sub
                            return node
                    return node
            return node
    return node

def extract_assets(pdf_path, output_dir, structured_data):
    images_dir = os.path.join(output_dir, 'images')
    tables_dir = os.path.join(output_dir, 'tables')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)
    assets = {"images": [], "tables": [], "metadata": {"pdf_path": os.path.abspath(pdf_path), "images_dir": images_dir, "tables_dir": tables_dir}}
    image_hashes = set()
    page_image_caps, page_table_caps = collect_page_captions(pdf_path)
    capture_regions = collect_capture_regions(pdf_path)
    caption_ptr_img = {}
    caption_ptr_tbl = {}
    images_by_page = defaultdict(int)
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image.get("image")
                if not image_bytes:
                    continue
                img_hash = hashlib.md5(image_bytes).hexdigest()
                if img_hash in image_hashes:
                    continue
                image_hashes.add(img_hash)
                pil = Image.open(io.BytesIO(image_bytes))
                if pil.mode != 'RGB':
                    pil = pil.convert('RGB')
                filename = f"img_p{page_num+1}_{img_index}_{img_hash[:8]}.png"
                filepath = os.path.join(images_dir, filename)
                pil.save(filepath, 'PNG')
                node = find_node_for_page(structured_data, page_num + 1)
                context = {
                    "thematique": {"title": node["thematique"].get("title")} if node["thematique"] else None,
                    "chapter": {"title": node["chapter"].get("title")} if node["chapter"] else None,
                    "section": {"title": node["section"].get("title")} if node["section"] else None,
                    "subsection": {"title": node["subsection"].get("title")} if node["subsection"] else None,
                }
                image_data = {
                    "id": f"img_{page_num+1}_{img_index}",
                    "page": page_num + 1,
                    "index": img_index,
                    "filename": filename,
                    "filepath": filepath,
                    "url": f"/assets/images/{filename}",
                    "width": pil.width,
                    "height": pil.height,
                    "hash": img_hash,
                    "context": context,
                    "title": f"Figure {len(assets['images']) + 1}",
                    "description": f"Image {len(assets['images']) + 1} de la page {page_num + 1}"
                }
                caps_img = page_image_caps.get(page_num + 1)
                if caps_img:
                    ptr = caption_ptr_img.get(page_num + 1, 0)
                    if ptr < len(caps_img):
                        image_data["title"] = caps_img[ptr]
                        caption_ptr_img[page_num + 1] = ptr + 1
                assets["images"].append(image_data)
                images_by_page[page_num + 1] += 1
                if node["subsection"] is not None:
                    node["subsection"].setdefault("images", []).append(image_data)
                elif node["section"] is not None:
                    node["section"].setdefault("images", []).append(image_data)
                elif node["chapter"] is not None:
                    node["chapter"].setdefault("images", []).append(image_data)
        # Fallback: if there are more figure captions than images on a page, create region snapshots only when regions exist
        total_pages = len(doc)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        for p in range(total_pages):
            caps_img = page_image_caps.get(p + 1, []) or []
            extracted = images_by_page.get(p + 1, 0)
            # If a page has at least one figure caption, try to produce snapshots (to capture vector-only figures or multi-panel figures)
            if caps_img:
                page = doc.load_page(p)
                regions = capture_regions.get(p + 1, [])
                if not regions:
                    # Guess regions from drawings when no manual regions are provided
                    try:
                        drs = page.get_drawings()
                    except Exception:
                        drs = []
                    guess = []
                    try:
                        pxw = float(page.rect.width); pxh = float(page.rect.height)
                        area_min = 0.05 * (pxw * pxh)
                        area_max = 0.85 * (pxw * pxh)
                        for d in drs or []:
                            r = d.get('rect')
                            if r is not None:
                                bb = fitz.Rect(r.x0, r.y0, r.x1, r.y1)
                            else:
                                items = d.get('items') or []
                                xs, ys = [], []
                                for it in items:
                                    pts = it[1] if len(it) > 1 else []
                                    for pt in pts:
                                        xs.append(pt[0]); ys.append(pt[1])
                                if xs and ys:
                                    bb = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                                else:
                                    continue
                            area = bb.width * bb.height
                            if area_min <= area <= area_max:
                                guess.append(bb)
                        # sort by area desc
                        guess.sort(key=lambda r: r.width * r.height, reverse=True)
                        # Try to detect two side-by-side panels with similar height and overlapping Y
                        def _contains(a, b, eps=1.0):
                            return (a.x0 <= b.x0 + eps) and (a.y0 <= b.y0 + eps) and (a.x1 >= b.x1 - eps) and (a.y1 >= b.y1 - eps)
                        def _y_overlap_frac(a, b):
                            oy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
                            return oy / max(1.0, min(a.height, b.height))
                        best_pair = None
                        best_score = 0.0
                        for i in range(min(len(guess), 12)):
                            for j in range(i + 1, min(len(guess), 12)):
                                a, b = guess[i], guess[j]
                                # skip nested/containing frames
                                if _contains(a, b) or _contains(b, a):
                                    continue
                                # require strong Y overlap and similar heights
                                if _y_overlap_frac(a, b) < 0.6:
                                    continue
                                h_ratio = abs(a.height - b.height) / max(a.height, b.height)
                                if h_ratio > 0.25:
                                    continue
                                # ensure horizontal separation
                                if min(a.x1, b.x1) - max(a.x0, b.x0) > 0:
                                    # overlapping in X too much -> likely nested
                                    continue
                                score = (a.width * a.height) + (b.width * b.height)
                                if score > best_score:
                                    best_score = score
                                    best_pair = (a, b)
                        if best_pair and (len(caps_img) >= 1):
                            a, b = best_pair
                            # order left-to-right
                            panels = [a, b] if a.x0 <= b.x0 else [b, a]
                            regions = [{'y0': float(r.y0), 'y1': float(r.y1), 'x0': float(r.x0), 'x1': float(r.x1)} for r in panels]
                        else:
                            # fallback: choose up to 2 regions with maximum horizontal separation
                            if len(guess) >= 2:
                                best_pair2 = None
                                best_dx = 0.0
                                limit = min(len(guess), 12)
                                for i in range(limit):
                                    for j in range(i + 1, limit):
                                        a, b = guess[i], guess[j]
                                        # horizontal separation by centers
                                        dx = abs((a.x0 + a.x1) * 0.5 - (b.x0 + b.x1) * 0.5)
                                        if dx > best_dx:
                                            best_dx = dx
                                            best_pair2 = (a, b)
                                if best_pair2:
                                    a, b = best_pair2
                                    panels = [a, b] if a.x0 <= b.x0 else [b, a]
                                    regions = [{'y0': float(r.y0), 'y1': float(r.y1), 'x0': float(r.x0), 'x1': float(r.x1)} for r in panels]
                                else:
                                    regions = [{'y0': float(guess[0].y0), 'y1': float(guess[0].y1), 'x0': float(guess[0].x0), 'x1': float(guess[0].x1)}]
                            else:
                                # single large region: if sufficiently wide, split into two vertical panels
                                if guess:
                                    g = guess[0]
                                    try:
                                        if (g.width / max(1.0, g.height)) >= 1.2:
                                            mid = (g.x0 + g.x1) * 0.5
                                            pad = max(4.0, 0.01 * float(page.rect.width))
                                            left = fitz.Rect(g.x0, g.y0, max(g.x0, mid - pad), g.y1)
                                            right = fitz.Rect(min(g.x1, mid + pad), g.y0, g.x1, g.y1)
                                            regions = [
                                                {'y0': float(left.y0), 'y1': float(left.y1), 'x0': float(left.x0), 'x1': float(left.x1)},
                                                {'y0': float(right.y0), 'y1': float(right.y1), 'x0': float(right.x0), 'x1': float(right.x1)},
                                            ]
                                        else:
                                            regions = [{'y0': float(g.y0), 'y1': float(g.y1), 'x0': float(g.x0), 'x1': float(g.x1)}]
                                    except Exception:
                                        regions = [{'y0': float(g.y0), 'y1': float(g.y1), 'x0': float(g.x0), 'x1': float(g.x1)}]
                                else:
                                    regions = []
                    except Exception:
                        regions = []
                if not regions:
                    continue  # still nothing -> skip snapshots
                # Create snapshots for all detected regions (panels), not strictly limited by caption count
                snap_count = len(regions)
                for idx in range(snap_count):
                    k = extracted + idx
                    r = regions[idx]
                    rx0 = float(r.get('x0', 0.0))
                    rx1 = float(r.get('x1', page.rect.width))
                    rect = fitz.Rect(rx0, float(r['y0']), rx1, float(r['y1']))
                    pix = page.get_pixmap(matrix=mat, alpha=False, clip=rect)
                    snap_name = f"snapshot_p{p+1}_{k}.png"
                    snap_path = os.path.join(images_dir, snap_name)
                    pix.save(snap_path)
                    chnode = find_node_for_page(structured_data, p + 1)
                    image_data = {
                        "id": f"imgsnap_{p+1}_{k}",
                        "page": p + 1,
                        "index": k,
                        "filename": snap_name,
                        "filepath": snap_path,
                        "url": f"/assets/images/{snap_name}",
                        "width": pix.width,
                        "height": pix.height,
                        "hash": None,
                        "context": {
                            "thematique": {"title": chnode["thematique"].get("title")} if chnode["thematique"] else None,
                            "chapter": {"title": chnode["chapter"].get("title")} if chnode["chapter"] else None,
                            "section": {"title": chnode["section"].get("title")} if chnode["section"] else None,
                            "subsection": {"title": chnode["subsection"].get("title")} if chnode["subsection"] else None,
                        },
                        "title": caps_img[min(len(caps_img) - 1, max(0, k if len(caps_img) > 1 else 0))],
                        "description": f"Snapshot de la page {p+1}{' (zone)' if rect else ''}"
                    }
                    assets["images"].append(image_data)
                    if chnode["subsection"] is not None:
                        chnode["subsection"].setdefault("images", []).append(image_data)
                    elif chnode["section"] is not None:
                        chnode["section"].setdefault("images", []).append(image_data)
                    elif chnode["chapter"] is not None:
                        chnode["chapter"].setdefault("images", []).append(image_data)
    finally:
        if 'doc' in locals():
            doc.close()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Helper functions for enriched extraction
            def rect_intersect(a, b):
                return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])

            def _to_hex_color(col):
                try:
                    if col is None:
                        return None
                    if isinstance(col, (list, tuple)):
                        # normalize floats 0-1 to 0-255
                        vals = []
                        for v in col[:3]:
                            if isinstance(v, float) and 0.0 <= v <= 1.0:
                                vals.append(int(round(v * 255)))
                            else:
                                vals.append(int(v))
                        r, g, b = [max(0, min(255, x)) for x in vals]
                        return f"#{r:02X}{g:02X}{b:02X}"
                    # single int (e.g., grayscale)
                    v = int(col)
                    v = max(0, min(255, v))
                    return f"#{v:02X}{v:02X}{v:02X}"
                except Exception:
                    return None

            def _dominant_color_pil(img):
                try:
                    # Downscale for speed
                    small = img.resize((max(1, img.width // 4), max(1, img.height // 4)))
                    # Get colors frequency
                    colors = small.getcolors(maxcolors=small.width * small.height) or []
                    # Filter near-white
                    filtered = []
                    for cnt, rgb in colors:
                        if isinstance(rgb, tuple) and len(rgb) >= 3:
                            if not (rgb[0] >= 245 and rgb[1] >= 245 and rgb[2] >= 245):
                                filtered.append((cnt, rgb))
                        else:
                            filtered.append((cnt, rgb))
                    if not filtered and colors:
                        filtered = colors
                    if not filtered:
                        return None
                    best = max(filtered, key=lambda x: x[0])[1]
                    if isinstance(best, tuple):
                        return _to_hex_color(best[:3])
                    return _to_hex_color(best)
                except Exception:
                    return None

            def _is_structural_marker_text(s: str) -> bool:
                try:
                    if not s:
                        return False
                    marker_bang = s.replace('！', '!').replace('﹗', '!').replace('︕', '!').strip()
                    if re.match(r'^\s*[\-\u2022•▪·»]*\s*!!\s*/\s*$', marker_bang):
                        return True
                    if re.match(r'^\s*[\-\u2022•▪·»]*\s*!!(?!/).*$' , marker_bang):
                        return True
                    if re.match(r'^\s*!!!\s*/\s*$', marker_bang) or re.match(r'^\s*!!!(?!/).*$' , marker_bang):
                        return True
                    if re.match(r'^\s*!\s*[^!].*$', marker_bang):  # thematique line
                        return True
                    # typed region tags <table>, </table>, <img>, </img>
                    if re.match(r'^\s*<\s*/?\s*table\s*>\s*$', marker_bang, flags=re.IGNORECASE):
                        return True
                    if re.match(r'^\s*<\s*/?\s*img\s*>\s*$', marker_bang, flags=re.IGNORECASE):
                        return True
                except Exception:
                    return False
                return False

            def _cell_text_and_color(fpage, cell_rect):
                text = []
                colors = []
                try:
                    td = fpage.get_text("dict")
                    cx0, cy0, cx1, cy1 = cell_rect
                    for blk in td.get("blocks", []):
                        if blk.get("type") != 0:
                            continue
                        bx0, by0, bx1, by1 = blk.get("bbox", [0, 0, 0, 0])
                        if not rect_intersect((bx0, by0, bx1, by1), (cx0, cy0, cx1, cy1)):
                            continue
                        for line in blk.get("lines", []):
                            for span in line.get("spans", []):
                                sx0, sy0, sx1, sy1 = span.get("bbox", [0, 0, 0, 0])
                                if rect_intersect((sx0, sy0, sx1, sy1), (cx0, cy0, cx1, cy1)):
                                    val = span.get("text", "")
                                    if val:
                                        text.append(val)
                                    col = span.get("color", None)
                                    if col is not None:
                                        colors.append(col)
                except Exception:
                    pass
                txt = normalize_ws(" ".join(text)).strip()
                # Strip embedded structural markers that might have leaked into cell text
                try:
                    # remove explicit end marker anywhere
                    txt = txt.replace("!!/", " ")
                    # remove isolated !!! tokens
                    txt = re.sub(r"\b!!!\b", " ", txt)
                    # remove leading '!!' marker tokens
                    txt = re.sub(r"^\s*!!\s*", " ", txt)
                    # remove typed region tags <table>, </table>, <img>, </img>
                    txt = re.sub(r"<\s*/?\s*(table|img)\s*>", " ", txt, flags=re.IGNORECASE)
                    txt = normalize_ws(txt).strip()
                except Exception:
                    pass
                if _is_structural_marker_text(txt):
                    txt = ""
                # pick the most frequent color
                col_hex = None
                if colors:
                    try:
                        # normalize and count
                        norm = [_to_hex_color(c) for c in colors]
                        norm = [c for c in norm if c]
                        if norm:
                            from collections import Counter
                            col_hex = Counter(norm).most_common(1)[0][0]
                    except Exception:
                        pass
                return txt, col_hex

            def _cell_icons_and_bg(fpage, drawings, cell_rect, images_dir_local, page_num_local, idx_local, col_local, row_local):
                cx0, cy0, cx1, cy1 = cell_rect
                icons = []
                bg_color = None
                # background via drawings (rect fills)
                try:
                    for d in drawings or []:
                        # PyMuPDF drawings API varies; try common keys
                        rect = d.get("rect")
                        fill = d.get("fill") or d.get("fill_color") or d.get("color")
                        if rect and fill:
                            rx0, ry0, rx1, ry1 = float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)
                            if rect_intersect((rx0, ry0, rx1, ry1), (cx0, cy0, cx1, cy1)):
                                bg_color = _to_hex_color(fill)
                                break
                except Exception:
                    pass
                # fallback: sample pixmap for dominant color
                if bg_color is None:
                    try:
                        mat = fitz.Matrix(1.5, 1.5)
                        clip = fitz.Rect(cx0, cy0, cx1, cy1)
                        pm = fpage.get_pixmap(matrix=mat, alpha=False, clip=clip)
                        pil_img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                        bg_color = _dominant_color_pil(pil_img)
                    except Exception:
                        pass
                # image icons inside cell
                try:
                    for img in fpage.get_images(full=True) or []:
                        xref = img[0]
                        for rect in fpage.get_image_rects(xref) or []:
                            rx0, ry0, rx1, ry1 = rect.x0, rect.y0, rect.x1, rect.y1
                            if rect_intersect((rx0, ry0, rx1, ry1), (cx0, cy0, cx1, cy1)):
                                icons.append({"type": "image", "bbox": [rx0, ry0, rx1, ry1]})
                except Exception:
                    pass
                # vector icons (small filled paths)
                try:
                    for d in drawings or []:
                        if d.get("rect"):
                            continue  # already treated as background
                        fill = d.get("fill") or d.get("fill_color")
                        parts = d.get("items") or []
                        # approximate bbox from parts
                        xs, ys = [], []
                        for it in parts:
                            # it is a tuple: (op, points, ...)
                            pts = it[1] if len(it) > 1 else []
                            for p in pts:
                                xs.append(p[0])
                                ys.append(p[1])
                        if xs and ys and fill:
                            bb = (min(xs), min(ys), max(xs), max(ys))
                            if rect_intersect(bb, (cx0, cy0, cx1, cy1)):
                                icons.append({"type": "vector", "bbox": list(bb), "color": _to_hex_color(fill)})
                except Exception:
                    pass
                return icons, bg_color

            def _get_field(o, name, default=None):
                try:
                    if isinstance(o, dict):
                        return o.get(name, default)
                    if hasattr(o, name):
                        return getattr(o, name)
                except Exception:
                    return default
                return default

            def _cell_bbox(cell):
                x0 = _get_field(cell, 'x0')
                x1 = _get_field(cell, 'x1')
                top = _get_field(cell, 'top')
                bottom = _get_field(cell, 'bottom')
                if x0 is None or x1 is None or top is None or bottom is None:
                    if isinstance(cell, (list, tuple)) and len(cell) >= 4:
                        try:
                            x0, top, x1, bottom = cell[0], cell[1], cell[2], cell[3]
                        except Exception:
                            return None
                    else:
                        return None
                try:
                    return [float(x0), float(top), float(x1), float(bottom)]
                except Exception:
                    return None

            def _dedup(vals, tol=1.0):
                out = []
                for v in sorted(vals):
                    if not out or abs(v - out[-1]) > tol:
                        out.append(v)
                return out

            def _find_bucket(val, edges, tol=1.0):
                try:
                    for i in range(len(edges) - 1):
                        if edges[i] - tol <= val <= edges[i + 1] + tol:
                            return i
                except Exception:
                    pass
                if len(edges) >= 2:
                    try:
                        return max(0, min(len(edges) - 2, min(range(len(edges) - 1), key=lambda i: abs(val - edges[i]))))
                    except Exception:
                        return 0
                return 0

            tables_by_page = defaultdict(int)
            # Open once to analyze text/drawings/colors
            with fitz.open(pdf_path) as fdoc_tables:
                for page_num, ppage in enumerate(pdf.pages):
                    fpage = fdoc_tables.load_page(page_num)
                    drawings = []
                    try:
                        drawings = fpage.get_drawings()
                    except Exception:
                        drawings = []
                    def _edge_counts_in_bbox(tbbox, tol=1.0):
                        try:
                            x0, y0, x1, y1 = float(tbbox[0]), float(tbbox[1]), float(tbbox[2]), float(tbbox[3])
                        except Exception:
                            return 0, 0, 0, 0
                        v_cnt = 0
                        h_cnt = 0
                        long_v = 0
                        long_h = 0
                        try:
                            edges = getattr(ppage, 'edges', []) or []
                            w = max(1.0, x1 - x0)
                            h = max(1.0, y1 - y0)
                            for e in edges:
                                ex0 = float(e.get('x0', 0.0)); ey0 = float(e.get('y0', 0.0))
                                ex1 = float(e.get('x1', ex0)); ey1 = float(e.get('y1', ey0))
                                bb = (min(ex0, ex1), min(ey0, ey1), max(ex0, ex1), max(ey0, ey1))
                                if not rect_intersect(bb, (x0, y0, x1, y1)):
                                    continue
                                dx = abs(ex0 - ex1)
                                dy = abs(ey0 - ey1)
                                if dx <= tol:
                                    v_cnt += 1
                                    if dy >= 0.5 * h:  # long vertical line spans at least 50% of table height
                                        long_v += 1
                                if dy <= tol:
                                    h_cnt += 1
                                    if (max(ex0, ex1) - min(ex0, ex1)) >= 0.5 * w:  # long horizontal spans 50% width
                                        long_h += 1
                        except Exception:
                            return 0, 0, 0, 0
                        return v_cnt, h_cnt, long_v, long_h
                    def _is_plausible_table(t_obj):
                        tbbox = getattr(t_obj, 'bbox', None)
                        # shape of table from extract()
                        nrows = 0
                        ncols = 0
                        extracted = []
                        try:
                            extracted = t_obj.extract() if hasattr(t_obj, 'extract') else []
                        except Exception:
                            extracted = []
                        if extracted:
                            try:
                                nrows = len(extracted)
                                ncols = max((len(r) if r else 0) for r in extracted) if nrows > 0 else 0
                            except Exception:
                                nrows, ncols = 0, 0
                        if nrows < 2 or ncols < 2:
                            return False
                        has_caption = bool(page_table_caps.get(page_num + 1))
                        has_graphics = False
                        if tbbox:
                            try:
                                x0, top, x1, bottom = tbbox
                                v_cnt, h_cnt, long_v, long_h = _edge_counts_in_bbox((x0, top, x1, bottom))
                                has_graphics = (long_v >= 1 and long_h >= 1) or (v_cnt >= 4 and h_cnt >= 4)
                            except Exception:
                                has_graphics = False
                        # duplication heuristic: many identical cells across columns -> likely multicolumn text
                        try:
                            if extracted:
                                dup_rows = 0
                                total_rows = 0
                                from collections import Counter
                                for row in extracted:
                                    vals = [normalize_ws(str(c or "")).strip() for c in (row or []) if str(c or "").strip()]
                                    if not vals:
                                        continue
                                    total_rows += 1
                                    most = Counter(vals).most_common(1)[0][1]
                                    if most / max(1, len(vals)) >= 0.6:
                                        dup_rows += 1
                                if total_rows and (dup_rows / total_rows) >= 0.4:
                                    return False
                        except Exception:
                            pass
                        # require either real graphics (grid) or a true caption to accept as a table
                        if not has_graphics and not has_caption:
                            return False
                        # reject narrow-width candidates without caption (likely sidebars or color bars)
                        if tbbox and not has_caption:
                            try:
                                x0, top, x1, bottom = tbbox
                                w_ratio = (x1 - x0) / max(1.0, float(fpage.rect.width))
                                if w_ratio < 0.3:
                                    return False
                            except Exception:
                                pass
                        # for 1-2 column candidates without caption, require stronger grid complexity
                        if not has_caption and ncols <= 2:
                            try:
                                # need at least 2 long vertical AND 2 long horizontal or >=3 short edges each
                                if not ((long_v >= 2 and long_h >= 2) or (v_cnt >= 3 and h_cnt >= 3)):
                                    return False
                            except Exception:
                                return False
                        # reject if structural markers (!! or !!/) appear frequently inside extracted cells
                        try:
                            if extracted:
                                marker_rows = 0
                                tot = 0
                                for row in extracted:
                                    txt_line = " ".join([str(c or "") for c in (row or [])])
                                    if re.search(r"!!/?", txt_line):
                                        marker_rows += 1
                                    tot += 1
                                if (tot and (marker_rows / tot) >= 0.2) or (marker_rows >= 1 and not has_caption):
                                    return False
                        except Exception:
                            pass
                        # high empty-cell ratio and many columns without graphics/caption -> likely not a table
                        try:
                            if extracted and ncols >= 6 and not has_graphics and not has_caption:
                                total = sum(len(r or []) for r in extracted)
                                empties = sum(1 for r in extracted for c in (r or []) if (not str(c or "").strip()))
                                if total and (empties / total) >= 0.5:
                                    return False
                        except Exception:
                            pass
                        # overly wide, many columns, no graphics/caption -> likely not a table
                        if tbbox:
                            try:
                                x0, top, x1, bottom = tbbox
                                w_ratio = (x1 - x0) / max(1.0, float(fpage.rect.width))
                                h_ratio = (bottom - top) / max(1.0, float(fpage.rect.height))
                                if w_ratio > 0.85 and ncols >= 6 and not extracted:
                                    return False
                            except Exception:
                                pass
                        # otherwise, accept if we extracted some non-empty cells
                        try:
                            if extracted:
                                non_empty = any((str(c or "").strip() for r in extracted for c in (r or [])))
                                return bool(non_empty)
                        except Exception:
                            return False
                        return False
                    # Prefer find_tables for structure (cells), fallback to extract_tables for content
                    tables = []
                    try:
                        if hasattr(ppage, 'find_tables'):
                            # two strategies to improve recall
                            ts_line = {
                                "vertical_strategy": "lines",
                                "horizontal_strategy": "lines",
                                "intersection_tolerance": 5,
                                "snap_tolerance": 3,
                                "edge_min_length": 3,
                                "min_words_vertical": 1,
                                "min_words_horizontal": 1,
                                "join_tolerance": 3,
                                "text_x_tolerance": 2,
                                "text_y_tolerance": 2,
                            }
                            tables = ppage.find_tables(table_settings=ts_line) or []
                            if not tables:
                                ts_text = {
                                    "vertical_strategy": "text",
                                    "horizontal_strategy": "text",
                                    "snap_tolerance": 3,
                                    "join_tolerance": 3,
                                    "text_x_tolerance": 3,
                                    "text_y_tolerance": 3,
                                }
                                tables = ppage.find_tables(table_settings=ts_text) or []
                    except Exception:
                        tables = []
                    # filter out probable false positives (e.g., multicolumn body text)
                    try:
                        tables = [t for t in (tables or []) if _is_plausible_table(t)]
                    except Exception:
                        pass
                    if not tables:
                        # fallback: only textual extraction, no cells/bboxes
                        simple = []
                        # only allow textual fallback if a caption exists on the page
                        if page_table_caps.get(page_num + 1):
                            # also require graphics (grid) somewhere on the page to reduce false positives
                            try:
                                full_bb = (0.0, 0.0, float(fpage.rect.width), float(fpage.rect.height))
                                vcnt, hcnt, lv, lh = _edge_counts_in_bbox(full_bb)
                            except Exception:
                                vcnt, hcnt, lv, lh = 0, 0, 0, 0
                            if (lv >= 1 and lh >= 1) or (vcnt >= 4 and hcnt >= 4):
                                simple = ppage.extract_tables() or []
                        for table_index, table in enumerate(simple):
                            # sanitize cells for structural markers in textual fallback
                            cleaned_rows = []
                            for row in table:
                                out_cells = []
                                for cell in row:
                                    s = normalize_ws(str(cell or "")).strip()
                                    try:
                                        s = s.replace("!!/", " ")
                                        s = re.sub(r"\b!!!\b", " ", s)
                                        s = re.sub(r"^\s*!!\s*", " ", s)
                                        # remove typed region tags <table>, </table>, <img>, </img>
                                        s = re.sub(r"<\s*/?\s*(table|img)\s*>", " ", s, flags=re.IGNORECASE)
                                        s = normalize_ws(s).strip()
                                    except Exception:
                                        pass
                                    if _is_structural_marker_text(s):
                                        s = ""
                                    out_cells.append(s)
                                cleaned_rows.append(" | ".join(out_cells))
                            rows_text = cleaned_rows
                            filename = f"table_p{page_num+1}_{table_index+1}.txt"
                            filepath = os.path.join(tables_dir, filename)
                            try:
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    f.write("\n".join(rows_text))
                            except Exception:
                                pass
                            table_data = {
                                "id": f"table_{page_num+1}_{table_index}",
                                "page": page_num + 1,
                                "index": table_index,
                                "filename": filename,
                                "filepath": filepath,
                                "url": f"/assets/tables/{filename}",
                                "rows": len(table),
                                "columns": len(table[0]) if table else 0,
                                "title": f"Tableau {len(assets['tables']) + 1}",
                                "content": rows_text,
                            }
                            caps_tbl = page_table_caps.get(page_num + 1)
                            if caps_tbl:
                                ptrt = caption_ptr_tbl.get(page_num + 1, 0)
                                if ptrt < len(caps_tbl):
                                    table_data["title"] = caps_tbl[ptrt]
                                    caption_ptr_tbl[page_num + 1] = ptrt + 1
                            assets["tables"].append(table_data)
                            tables_by_page[page_num + 1] += 1
                            node = find_node_for_page(structured_data, page_num + 1)
                            if node["subsection"] is not None:
                                node["subsection"].setdefault("tables", []).append(table_data)
                            elif node["section"] is not None:
                                node["section"].setdefault("tables", []).append(table_data)
                            elif node["chapter"] is not None:
                                node["chapter"].setdefault("tables", []).append(table_data)
                        continue
                    # Enriched extraction using table cells
                    for table_index, t in enumerate(tables):
                        try:
                            tbbox = getattr(t, 'bbox', None)
                            cells = getattr(t, 'cells', None)
                        except Exception:
                            tbbox = None
                            cells = None
                        data_rows = []
                        rows_text = []
                        cell_matrix = []
                        nrows = 0
                        ncols = 0
                        # Build a grid from cell bboxes if available
                        if cells:
                            xs_all = []
                            ys_all = []
                            for c in cells:
                                bb = _cell_bbox(c)
                                if not bb:
                                    continue
                                cx0, cy0, cx1, cy1 = bb
                                xs_all.extend([cx0, cx1])
                                ys_all.extend([cy0, cy1])
                            xs = _dedup(xs_all)
                            ys = _dedup(ys_all)
                            ncols = max(0, len(xs) - 1)
                            nrows = max(0, len(ys) - 1)
                            # init matrix
                            cell_matrix = [[None for _ in range(ncols)] for _ in range(nrows)]
                            # map each cell to grid position
                            for c in cells:
                                bb = _cell_bbox(c)
                                if not bb:
                                    continue
                                x0, y0, x1, y1 = bb[0], bb[1], bb[2], bb[3]
                                try:
                                    col0 = _find_bucket(x0, xs)
                                    row0 = _find_bucket(y0, ys)
                                    if 0 <= row0 < nrows and 0 <= col0 < ncols:
                                        cell_matrix[row0][col0] = [x0, y0, x1, y1]
                                except Exception:
                                    continue
                        else:
                            # fallback: use extracted textual table for rows/cols
                            try:
                                extracted = t.extract() if hasattr(t, 'extract') else []
                            except Exception:
                                extracted = []
                            if extracted:
                                nrows = len(extracted)
                                ncols = len(extracted[0]) if extracted else 0
                                cell_matrix = [[None for _ in range(ncols)] for _ in range(nrows)]
                                # approximate bbox grid from tbbox
                                if tbbox and ncols and nrows:
                                    x0, top, x1, bottom = tbbox
                                    colw = (x1 - x0) / ncols
                                    rowh = (bottom - top) / nrows
                                    for r in range(nrows):
                                        for cidx in range(ncols):
                                            cx0 = x0 + cidx * colw
                                            cx1 = x0 + (cidx + 1) * colw
                                            cy0 = top + r * rowh
                                            cy1 = top + (r + 1) * rowh
                                            cell_matrix[r][cidx] = [cx0, cy0, cx1, cy1]
                        # Extract content/colors/icons per cell
                        for r in range(nrows):
                            row_texts = []
                            row_data = []
                            for cidx in range(ncols):
                                bbox = cell_matrix[r][cidx]
                                if not bbox:
                                    row_texts.append("")
                                    row_data.append("")
                                    continue
                                txt, txt_color = _cell_text_and_color(fpage, bbox)
                                icons, bg_color = _cell_icons_and_bg(fpage, drawings, bbox, images_dir, page_num + 1, table_index, cidx, r)
                                row_texts.append(txt)
                                row_data.append({
                                    "bbox": bbox,
                                    "text": txt,
                                    "text_color": txt_color,
                                    "background_color": bg_color,
                                    "icons": icons,
                                })
                            rows_text.append(" | ".join((t or "").strip() for t in row_texts))
                            data_rows.append(row_data)
                        # columns content aggregation
                        columns_content = []
                        for cidx in range(ncols):
                            col_texts = []
                            for r in range(nrows):
                                item = data_rows[r][cidx]
                                if isinstance(item, dict):
                                    if item.get("text"):
                                        col_texts.append(item.get("text"))
                                elif isinstance(item, str) and item:
                                    col_texts.append(item)
                            columns_content.append(" \n".join(col_texts))
                        # Capture PNG du tableau entier (bbox de table ou union des cellules)
                        snap_name = None
                        snap_path = None
                        try:
                            tbbox_final = None
                            if tbbox is not None:
                                try:
                                    tx0, ttop, tx1, tbottom = tbbox
                                    tbbox_final = (float(tx0), float(ttop), float(tx1), float(tbottom))
                                except Exception:
                                    tbbox_final = None
                            if tbbox_final is None and cell_matrix:
                                xs_all = []
                                ys_all = []
                                for r in range(nrows):
                                    for cidx in range(ncols):
                                        bb = cell_matrix[r][cidx]
                                        if not bb:
                                            continue
                                        xs_all.extend([bb[0], bb[2]])
                                        ys_all.extend([bb[1], bb[3]])
                                if xs_all and ys_all:
                                    tbbox_final = (min(xs_all), min(ys_all), max(xs_all), max(ys_all))
                            if tbbox_final is not None:
                                rx0, ry0, rx1, ry1 = tbbox_final
                                rect = fitz.Rect(rx0, ry0, rx1, ry1)
                                mat_snap = fitz.Matrix(2.0, 2.0)
                                pix_tbl = fpage.get_pixmap(matrix=mat_snap, alpha=False, clip=rect)
                                snap_name = f"table_snapshot_p{page_num+1}_{table_index+1}.png"
                                snap_path = os.path.join(tables_dir, snap_name)
                                pix_tbl.save(snap_path)
                        except Exception:
                            snap_name = None
                            snap_path = None
                        filename = f"table_p{page_num+1}_{table_index+1}.txt"
                        filepath = os.path.join(tables_dir, filename)
                        try:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write("\n".join(rows_text))
                        except Exception:
                            pass
                        table_data = {
                            "id": f"table_{page_num+1}_{table_index}",
                            "page": page_num + 1,
                            "index": table_index,
                            "filename": filename,
                            "filepath": filepath,
                            "url": f"/assets/tables/{filename}",
                            "rows": nrows,
                            "columns": ncols,
                            "title": f"Tableau {len(assets['tables']) + 1}",
                            "content": rows_text,
                            "cells": data_rows,
                            "columns_content": columns_content,
                        }
                        if snap_name and snap_path:
                            table_data["snapshot_filename"] = snap_name
                            table_data["snapshot_filepath"] = snap_path
                            table_data["snapshot_url"] = f"/assets/tables/{snap_name}"
                        caps_tbl = page_table_caps.get(page_num + 1)
                        if caps_tbl:
                            ptrt = caption_ptr_tbl.get(page_num + 1, 0)
                            if ptrt < len(caps_tbl):
                                table_data["title"] = caps_tbl[ptrt]
                                caption_ptr_tbl[page_num + 1] = ptrt + 1
                        assets["tables"].append(table_data)
                        tables_by_page[page_num + 1] += 1
                        node = find_node_for_page(structured_data, page_num + 1)
                        if node["subsection"] is not None:
                            node["subsection"].setdefault("tables", []).append(table_data)
                        elif node["section"] is not None:
                            node["section"].setdefault("tables", []).append(table_data)
                        elif node["chapter"] is not None:
                            node["chapter"].setdefault("tables", []).append(table_data)
            # Fallback: for pages with table captions but no table extracted, create a region snapshot only when regions exist
            try:
                with fitz.open(pdf_path) as doc2:
                    zoom = 2.0
                    mat = fitz.Matrix(zoom, zoom)
                    for p in range(len(doc2)):
                        caps_tbl = page_table_caps.get(p + 1, []) or []
                        extracted_t = tables_by_page.get(p + 1, 0)
                        if extracted_t < len(caps_tbl):
                            page2 = doc2.load_page(p)
                            regions = capture_regions.get(p + 1, [])
                            if not regions:
                                # try to guess regions from drawings if no manual regions
                                try:
                                    drs = page2.get_drawings()
                                except Exception:
                                    drs = []
                                guess = []
                                try:
                                    pxw = float(page2.rect.width); pxh = float(page2.rect.height)
                                    area_min = 0.05 * (pxw * pxh)
                                    area_max = 0.80 * (pxw * pxh)
                                    for d in drs or []:
                                        r = d.get('rect')
                                        if r is not None:
                                            bb = fitz.Rect(r.x0, r.y0, r.x1, r.y1)
                                        else:
                                            items = d.get('items') or []
                                            xs, ys = [], []
                                            for it in items:
                                                pts = it[1] if len(it) > 1 else []
                                                for pt in pts:
                                                    xs.append(pt[0]); ys.append(pt[1])
                                            if xs and ys:
                                                bb = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                                            else:
                                                continue
                                        area = bb.width * bb.height
                                        if area_min <= area <= area_max:
                                            guess.append(bb)
                                    # sort by area desc and deduplicate close boxes
                                    guess.sort(key=lambda r: r.width * r.height, reverse=True)
                                    uniq = []
                                    for g in guess:
                                        if not uniq:
                                            uniq.append(g)
                                            continue
                                        iou = max(0, min(g.x1, uniq[-1].x1) - max(g.x0, uniq[-1].x0)) * max(0, min(g.y1, uniq[-1].y1) - max(g.y0, uniq[-1].y0))
                                        uarea = g.width * g.height + uniq[-1].width * uniq[-1].height - iou
                                        if uarea == 0 or (iou / uarea) < 0.5:
                                            uniq.append(g)
                                    regions = [{'y0': float(r.y0), 'y1': float(r.y1), 'x0': float(r.x0), 'x1': float(r.x1)} for r in uniq[:len(caps_tbl)]]
                                except Exception:
                                    regions = []
                            if not regions:
                                continue  # still nothing -> skip
                            for k in range(extracted_t, len(caps_tbl)):
                                idx = k - extracted_t
                                if idx >= len(regions):
                                    break
                                r = regions[idx]
                                rx0 = float(r.get('x0', 0.0))
                                rx1 = float(r.get('x1', page2.rect.width))
                                rect = fitz.Rect(rx0, float(r['y0']), rx1, float(r['y1']))
                                pix2 = page2.get_pixmap(matrix=mat, alpha=False, clip=rect)
                                snap_name = f"table_snapshot_p{p+1}_{k}.png"
                                snap_path = os.path.join(tables_dir, snap_name)
                                pix2.save(snap_path)
                                node2 = find_node_for_page(structured_data, p + 1)
                                table_data = {
                                    "id": f"table_snap_{p+1}_{k}",
                                    "page": p + 1,
                                    "index": k,
                                    "filename": snap_name,
                                    "filepath": snap_path,
                                    "url": f"/assets/tables/{snap_name}",
                                    "rows": 0,
                                    "columns": 0,
                                    "title": caps_tbl[k],
                                    "content": [],
                                    "is_snapshot": True
                                }
                                assets["tables"].append(table_data)
                                if node2["subsection"] is not None:
                                    node2["subsection"].setdefault("tables", []).append(table_data)
                                elif node2["section"] is not None:
                                    node2["section"].setdefault("tables", []).append(table_data)
                                elif node2["chapter"] is not None:
                                    node2["chapter"].setdefault("tables", []).append(table_data)
            except Exception:
                pass
    except Exception as e:
        print(f"Erreur lors de l'extraction des tableaux : {str(e)}")
    # Force snapshots for typed regions (!!! image / !!! table), regardless of captions
    try:
        with fitz.open(pdf_path) as doc3:
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            total = len(doc3)
            for p in range(total):
                regions = [r for r in capture_regions.get(p + 1, []) if r.get('kind') in ('image', 'table')]
                if not regions:
                    continue
                page3 = doc3.load_page(p)
                for idx, r in enumerate(regions):
                    rect = fitz.Rect(0, float(r['y0']), page3.rect.width, float(r['y1']))
                    pix3 = page3.get_pixmap(matrix=mat, alpha=False, clip=rect)
                    node3 = find_node_for_page(structured_data, p + 1)
                    if r.get('kind') == 'table':
                        rows_cnt = 0
                        cols_cnt = 0
                        rows_text = []
                        data_2d = []
                        try:
                            with pdfplumber.open(pdf_path) as pdfp:
                                ppage = pdfp.pages[p]
                                crop = ppage.crop((0, float(r['y0']), ppage.width, float(r['y1'])))
                                ts1 = {
                                    "vertical_strategy": "lines",
                                    "horizontal_strategy": "lines",
                                    "intersection_tolerance": 5,
                                    "snap_tolerance": 3,
                                    "edge_min_length": 3,
                                    "min_words_vertical": 1,
                                    "min_words_horizontal": 1,
                                    "join_tolerance": 3,
                                    "text_x_tolerance": 2,
                                    "text_y_tolerance": 2,
                                }
                                tables1 = crop.extract_tables(table_settings=ts1)
                                tables = tables1
                                if not tables:
                                    ts2 = {
                                        "vertical_strategy": "text",
                                        "horizontal_strategy": "text",
                                        "snap_tolerance": 3,
                                        "join_tolerance": 3,
                                        "text_x_tolerance": 3,
                                        "text_y_tolerance": 3,
                                    }
                                    tables2 = crop.extract_tables(table_settings=ts2)
                                    tables = tables2
                                if tables:
                                    best = max(tables, key=lambda t: (len(t), max((len(rw) if rw else 0) for rw in t) if t else 0))
                                    rows_cnt = len(best)
                                    cols_cnt = max((len(rw) if rw else 0) for rw in best) if rows_cnt > 0 else 0
                                    for rw in best:
                                        cells = [(c or "").strip() for c in (rw or [])]
                                        data_2d.append(cells)
                                        rows_text.append(" | ".join(cells))
                                if not data_2d:
                                    # Fallback: raw lines from the cropped region
                                    try:
                                        # Try word-based lines
                                        words = crop.extract_words(use_text_flow=True) or []
                                        words.sort(key=lambda w: (float(w.get('top', 0)), float(w.get('x0', 0))))
                                        lines_tmp = []
                                        cur_top = None
                                        buf = []
                                        tol = 3.0
                                        for w in words:
                                            top = float(w.get('top', 0))
                                            if cur_top is None or abs(top - cur_top) <= tol:
                                                buf.append(w)
                                                if cur_top is None:
                                                    cur_top = top
                                            else:
                                                txt = " ".join(item['text'] for item in sorted(buf, key=lambda x: x.get('x0', 0)))
                                                lines_tmp.append(txt.strip())
                                                buf = [w]
                                                cur_top = top
                                        if buf:
                                            txt = " ".join(item['text'] for item in sorted(buf, key=lambda x: x.get('x0', 0)))
                                            lines_tmp.append(txt.strip())
                                        if not lines_tmp:
                                            raw_txt = (crop.extract_text() or "").splitlines()
                                            lines_tmp = [normalize_ws(t).strip() for t in raw_txt if t and normalize_ws(t).strip()]
                                        for tline in lines_tmp:
                                            data_2d.append([tline])
                                            rows_text.append(tline)
                                        rows_cnt = len(data_2d)
                                        cols_cnt = max((len(rw) for rw in data_2d), default=0)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # Always write textual export
                        txt_name = f"typed_table_p{p+1}_{idx}.txt"
                        txt_path = os.path.join(tables_dir, txt_name)
                        try:
                            with open(txt_path, 'w', encoding='utf-8') as f:
                                f.write("\n".join(rows_text))
                        except Exception:
                            pass
                        table_data = {
                            "id": f"table_typed_{p+1}_{idx}",
                            "page": p + 1,
                            "index": idx,
                            "filename": txt_name,
                            "filepath": txt_path,
                            "url": f"/assets/tables/{txt_name}",
                            "rows": rows_cnt,
                            "columns": cols_cnt,
                            "title": f"Table p{p+1}-{idx+1}",
                            "content": rows_text,
                            "data": data_2d
                        }
                        assets["tables"].append(table_data)
                        if node3["subsection"] is not None:
                            node3["subsection"].setdefault("tables", []).append(table_data)
                        elif node3["section"] is not None:
                            node3["section"].setdefault("tables", []).append(table_data)
                        elif node3["chapter"] is not None:
                            node3["chapter"].setdefault("tables", []).append(table_data)
                    else:
                        snap_name = f"typed_image_p{p+1}_{idx}.png"
                        snap_path = os.path.join(images_dir, snap_name)
                        pix3.save(snap_path)
                        image_data = {
                            "id": f"img_typed_{p+1}_{idx}",
                            "page": p + 1,
                            "index": idx,
                            "filename": snap_name,
                            "filepath": snap_path,
                            "url": f"/assets/images/{snap_name}",
                            "width": pix3.width,
                            "height": pix3.height,
                            "hash": None,
                            "context": {
                                "thematique": {"title": node3["thematique"].get("title")} if node3["thematique"] else None,
                                "chapter": {"title": node3["chapter"].get("title")} if node3["chapter"] else None,
                                "section": {"title": node3["section"].get("title")} if node3["section"] else None,
                                "subsection": {"title": node3["subsection"].get("title")} if node3["subsection"] else None,
                            },
                            "title": f"Snapshot p{p+1}-{idx+1}",
                            "description": f"Snapshot de la page {p+1} (zone) ",
                            "is_snapshot": True
                        }
                        assets["images"].append(image_data)
                        if node3["subsection"] is not None:
                            node3["subsection"].setdefault("images", []).append(image_data)
                        elif node3["section"] is not None:
                            node3["section"].setdefault("images", []).append(image_data)
                        elif node3["chapter"] is not None:
                            node3["chapter"].setdefault("images", []).append(image_data)
    except Exception:
        pass
    # Post-traitement: fusionner les tables tapées entourées par <table> ... </table>
    try:
        def _merge_typed_tag_tables(assets_local, structured_local):
            try:
                # Regrouper les tables tapées par page
                by_page = {}
                for tbl in assets_local.get("tables", []):
                    try:
                        if not isinstance(tbl, dict):
                            continue
                        tid = str(tbl.get("id", ""))
                        if not tid.startswith("table_typed_"):
                            continue
                        page = int(tbl.get("page", 0) or 0)
                        if page <= 0:
                            continue
                        by_page.setdefault(page, []).append(tbl)
                    except Exception:
                        continue

                # Petite fonction utilitaire pour savoir si une table est marquée par <table> ou </table>
                def _has_table_start(tbl):
                    for line in tbl.get("content", []) or []:
                        s = str(line).lstrip()
                        if s:
                            return s.startswith("<table>")
                    return False

                def _has_table_end(tbl):
                    for line in reversed(tbl.get("content", []) or []):
                        s = str(line).rstrip()
                        if s:
                            if "</table>" in s:
                                return True
                            if s.endswith("/table>"):
                                return True
                    return False

                # Mise à jour des références dans structured_data
                def _replace_tables_in_node(node, old_ids_set, new_tbl):
                    try:
                        if not isinstance(node, dict):
                            return
                        if "tables" in node and isinstance(node["tables"], list):
                            kept = []
                            for t in node["tables"]:
                                if isinstance(t, dict) and str(t.get("id", "")) in old_ids_set:
                                    continue
                                kept.append(t)
                            # insérer le nouveau tableau s'il est sur la bonne page
                            if kept and new_tbl is not None:
                                # si un des anciens tableaux était présent ici, on ajoute le nouveau
                                # pour rester simple, on ajoute en fin de liste
                                kept.append(new_tbl)
                            node["tables"] = kept
                    except Exception:
                        return

                def _walk_structure(struct):
                    if not isinstance(struct, dict):
                        return
                    # thematiques
                    for th in struct.get("thematiques", []) or []:
                        _walk_chapter_list(th.get("chapters", []))
                    _walk_chapter_list(struct.get("chapters_sans_thematique", []) or [])

                def _walk_chapter_list(chapters):
                    for ch in chapters or []:
                        _replace_tables_in_node(ch, old_ids_page, merged_tbl)  # old_ids_page/merged_tbl variables from closure
                        for sec in ch.get("sections", []) or []:
                            _replace_tables_in_node(sec, old_ids_page, merged_tbl)
                            for sub in sec.get("subsections", []) or []:
                                _replace_tables_in_node(sub, old_ids_page, merged_tbl)

                # Pour chaque page, fusionner les séquences <table> ... </table>
                new_tables_global = []
                all_tables = assets_local.get("tables", []) or []
                for page, tlist in by_page.items():
                    # trier par index
                    try:
                        tlist_sorted = sorted(tlist, key=lambda x: int(x.get("index", 0) or 0))
                    except Exception:
                        tlist_sorted = tlist
                    i = 0
                    while i < len(tlist_sorted):
                        tbl = tlist_sorted[i]
                        if not _has_table_start(tbl):
                            i += 1
                            continue
                        # démarrer une séquence
                        seq = [tbl]
                        j = i + 1
                        while j < len(tlist_sorted) and not _has_table_end(tlist_sorted[j]):
                            seq.append(tlist_sorted[j])
                            j += 1
                        if j < len(tlist_sorted):
                            seq.append(tlist_sorted[j])
                            end_idx = j
                        else:
                            end_idx = i
                        # vérifier fin </table>
                        if not any(_has_table_end(t) for t in seq):
                            i += 1
                            continue
                        # Construire le super-tableau
                        first = seq[0]
                        merged_content = []
                        merged_data = []
                        rows_cnt = 0
                        cols_cnt = 0
                        for t in seq:
                            lines = t.get("content", []) or []
                            merged_content.extend(lines)
                            d = t.get("data")
                            if isinstance(d, list):
                                merged_data.extend(d)
                            rows_cnt += int(t.get("rows", 0) or 0)
                            cols_cnt = max(cols_cnt, int(t.get("columns", 0) or 0))
                        if not merged_content:
                            i += 1
                            continue
                        merged_tbl = {
                            "id": first.get("id"),
                            "page": page,
                            "index": first.get("index", 0),
                            "filename": first.get("filename"),
                            "filepath": first.get("filepath"),
                            "url": first.get("url"),
                            "rows": rows_cnt,
                            "columns": cols_cnt,
                            "title": first.get("title"),
                            "content": merged_content,
                            "data": merged_data,
                        }
                        # Marquer les anciens à supprimer
                        old_ids_page = {str(t.get("id", "")) for t in seq}
                        # Mettre à jour structured_data pour cette page
                        _walk_structure(structured_local)
                        # Filtrer dans assets_local['tables']
                        kept_global = []
                        inserted = False
                        for t in all_tables:
                            tid = str(t.get("id", "")) if isinstance(t, dict) else ""
                            if tid in old_ids_page:
                                if not inserted:
                                    kept_global.append(merged_tbl)
                                    inserted = True
                                continue
                            kept_global.append(t)
                        all_tables = kept_global
                        i = end_idx + 1
                assets_local["tables"] = all_tables

            except Exception:
                return

        _merge_typed_tag_tables(assets, structured_data)
    except Exception:
        pass
    metadata_file = os.path.join(output_dir, 'assets_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)
    return assets, structured_data

def main():
    pdf_file = "NSL-Rigging-Lifting-Handbook-1-20.pdf"
    output_file = "nsl_rigging_lifting_handbook.json"
    assets_dir = "extracted_assets"
    os.makedirs(assets_dir, exist_ok=True)
    structured_data = parse_marked_pdf(pdf_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=4)
    assets, structured_data = extract_assets(pdf_file, assets_dir, structured_data)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=4)
    print(f"[SUCCES] Structure balisée + assets extraits. JSON: {output_file}")
    print(f"- {len(assets['images'])} images, {len(assets['tables'])} tableaux")

if __name__ == "__main__":
    main()
