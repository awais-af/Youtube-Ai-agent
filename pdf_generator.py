"""
Lightweight Pure-Python PDF Generator for YouTube Tutorial Reports.
Generates fully compliant, valid PDF files with zero external C/binary dependencies.
Supports multi-page documents, headings, badges, and Fact Check sections.
"""

import io
from typing import List, Dict, Any, Optional


class SimplePDFCanvas:
    """
    Minimal, robust PDF generator that constructs standard PDF 1.4 documents.
    """

    def __init__(self, page_width: float = 612.0, page_height: float = 792.0):
        # Default US Letter: 612 x 792 pt (8.5 x 11 inches)
        self.width = page_width
        self.height = page_height
        self.margin = 54.0  # 0.75 in
        
        self.pages: List[str] = []
        self.current_stream: List[str] = []
        self.y = self.height - self.margin

    def _flush_page(self):
        if self.current_stream:
            self.pages.append("\n".join(self.current_stream))
            self.current_stream = []
        self.y = self.height - self.margin

    def new_page(self):
        self._flush_page()

    def ensure_space(self, space_pt: float):
        if self.y - space_pt < self.margin:
            self.new_page()

    @staticmethod
    def _escape(text: str) -> str:
        """Escapes parentheses and backslashes for PDF literal strings."""
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def draw_text(self, text: str, font: str = "F1", size: float = 10.0, color: tuple = (0.1, 0.1, 0.1), x: Optional[float] = None):
        """Draws a single line of text."""
        pos_x = x if x is not None else self.margin
        r, g, b = color
        safe_text = self._escape(text)
        self.current_stream.append(f"BT /{font} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {pos_x:.2f} {self.y:.2f} Td ({safe_text}) Tj ET")

    def draw_rect(self, x: float, y: float, w: float, h: float, fill_color: tuple, stroke_color: Optional[tuple] = None):
        """Draws a filled and optionally stroked rectangle."""
        r, g, b = fill_color
        stream_cmd = f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f"
        if stroke_color:
            sr, sg, sb = stroke_color
            stream_cmd += f" {sr:.3f} {sg:.3f} {sb:.3f} RG {x:.2f} {y:.2f} {w:.2f} {h:.2f} re s"
        self.current_stream.append(stream_cmd)

    def add_heading(self, text: str, level: int = 1):
        size = 18.0 if level == 1 else (14.0 if level == 2 else 11.0)
        leading = size + 6
        self.ensure_space(leading + 10)
        self.y -= 8
        color = (0.12, 0.18, 0.32) if level == 1 else (0.2, 0.25, 0.4)
        self.draw_text(text[:85], font="F2", size=size, color=color)
        self.y -= leading

    def add_paragraph(self, text: str, font: str = "F1", size: float = 9.5, color: tuple = (0.2, 0.2, 0.2), indent: float = 0.0):
        """Wraps text into lines and draws paragraph."""
        max_chars_per_line = int((self.width - 2 * self.margin - indent) / (size * 0.52))
        words = text.split()
        if not words:
            self.y -= size
            return

        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 <= max_chars_per_line:
                cur_line.append(w)
                cur_len += len(w) + 1
            else:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
        if cur_line:
            lines.append(" ".join(cur_line))

        leading = size + 3.5
        for line in lines:
            self.ensure_space(leading)
            self.draw_text(line, font=font, size=size, color=color, x=self.margin + indent)
            self.y -= leading
        self.y -= 4

    def build_pdf(self) -> bytes:
        """Serializes pages into valid PDF 1.4 bytes."""
        self._flush_page()
        if not self.pages:
            self.pages.append("")

        num_pages = len(self.pages)
        objects: List[bytes] = []
        
        # Object 1: Catalog
        # Object 2: Pages root
        # Objects 3..2+N: Page objects
        # Objects 3+N..2+2N: Content streams
        # Object 3+2N: Font Helvetica (F1)
        # Object 4+2N: Font Helvetica-Bold (F2)
        # Object 5+2N: Font Helvetica-Oblique (F3)

        pages_root_id = 2
        first_page_id = 3
        first_stream_id = 3 + num_pages
        font1_id = 3 + 2 * num_pages
        font2_id = font1_id + 1
        font3_id = font2_id + 1

        # Obj 1: Catalog
        catalog = f"1 0 obj\n<< /Type /Catalog /Pages {pages_root_id} 0 R >>\nendobj\n".encode("latin1")
        
        # Obj 2: Pages
        kids_refs = " ".join([f"{first_page_id + i} 0 R" for i in range(num_pages)])
        pages_root = f"2 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {num_pages} >>\nendobj\n".encode("latin1")

        # Page Objs & Stream Objs
        page_objs = []
        stream_objs = []
        for i in range(num_pages):
            p_id = first_page_id + i
            s_id = first_stream_id + i
            page_str = (
                f"{p_id} 0 obj\n"
                f"<< /Type /Page /Parent {pages_root_id} 0 R "
                f"/MediaBox [0 0 {self.width:.1f} {self.height:.1f}] "
                f"/Contents {s_id} 0 R "
                f"/Resources << /Font << /F1 {font1_id} 0 R /F2 {font2_id} 0 R /F3 {font3_id} 0 R >> >> >>\n"
                f"endobj\n"
            )
            page_objs.append(page_str.encode("latin1"))

            stream_content = self.pages[i].encode("latin1", "replace")
            stream_str = (
                f"{s_id} 0 obj\n"
                f"<< /Length {len(stream_content)} >>\n"
                f"stream\n"
            ).encode("latin1") + stream_content + b"\nendstream\nendobj\n"
            stream_objs.append(stream_str)

        # Fonts
        font1 = f"{font1_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode("latin1")
        font2 = f"{font2_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n".encode("latin1")
        font3 = f"{font3_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>\nendobj\n".encode("latin1")

        all_objs = [catalog, pages_root] + page_objs + stream_objs + [font1, font2, font3]
        
        # Build file with xref table
        pdf_out = io.BytesIO()
        pdf_out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        
        xref_offsets = []
        for obj in all_objs:
            xref_offsets.append(pdf_out.tell())
            pdf_out.write(obj)

        xref_start = pdf_out.tell()
        total_objs = len(all_objs) + 1
        pdf_out.write(f"xref\n0 {total_objs}\n0000000000 65535 f \n".encode("latin1"))
        for offset in xref_offsets:
            pdf_out.write(f"{offset:010d} 00000 n \n".encode("latin1"))

        pdf_out.write(
            f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("latin1")
        )
        return pdf_out.getvalue()


def generate_tutorial_pdf(
    metadata: Dict[str, Any],
    description_text: str = "",
    curriculum_text: str = "",
    fact_check_data: Optional[Dict[str, Any]] = None,
    notes_text: str = "",
    quiz_text: str = ""
) -> bytes:
    """
    Generates a full tutorial report PDF with the Fact Check audit section.
    """
    canvas = SimplePDFCanvas()

    # Title Banner Card
    canvas.draw_rect(canvas.margin, canvas.y - 65, canvas.width - 2 * canvas.margin, 70, fill_color=(0.94, 0.96, 1.0), stroke_color=(0.7, 0.78, 0.95))
    canvas.y -= 20
    canvas.draw_text("Awais(YT) Ai Agent Report", font="F2", size=16, color=(0.1, 0.2, 0.5), x=canvas.margin + 14)
    canvas.y -= 16
    video_title = metadata.get("title", "Tutorial Video")
    canvas.draw_text(video_title[:65], font="F2", size=11, color=(0.15, 0.15, 0.15), x=canvas.margin + 14)
    canvas.y -= 14
    author = metadata.get("author_name", "Creator")
    duration = metadata.get("duration", "N/A")
    canvas.draw_text(f"Instructor: {author}  |  Duration: {duration}", font="F1", size=9, color=(0.4, 0.45, 0.55), x=canvas.margin + 14)
    canvas.y -= 35

    # ==========================================
    # SECTION 1: INTERNET FACT CHECK SECTION
    # ==========================================
    canvas.add_heading("Live Internet Fact Check (DuckDuckGo + Groq AI)", level=1)
    
    if fact_check_data and fact_check_data.get("claims"):
        claims = fact_check_data.get("claims", [])
        canvas.add_paragraph(
            "The AI agent extracted checkable technical claims from this tutorial and audited them "
            "against live web search to identify breaking changes, deprecations, or outdated commands.",
            font="F3", size=9.0, color=(0.35, 0.35, 0.35)
        )
        canvas.y -= 6

        for i, c in enumerate(claims, 1):
            canvas.ensure_space(75)
            status = c.get("status", "unverified")
            
            # Status badge styling
            if status == "still_valid":
                badge_text = " [STILL VALID] "
                badge_bg = (0.86, 0.96, 0.88)
                badge_border = (0.2, 0.65, 0.3)
                badge_color = (0.1, 0.45, 0.15)
            elif status == "outdated":
                badge_text = " [OUTDATED - CHANGES DETECTED] "
                badge_bg = (1.0, 0.93, 0.85)
                badge_border = (0.9, 0.5, 0.1)
                badge_color = (0.7, 0.3, 0.0)
            else:
                badge_text = " [UNVERIFIED] "
                badge_bg = (0.92, 0.94, 0.96)
                badge_border = (0.6, 0.65, 0.7)
                badge_color = (0.3, 0.35, 0.45)

            # Draw claim card box
            ts = c.get("timestamp", "")
            ts_label = f" ({ts})" if ts else ""
            
            canvas.draw_text(f"Claim {i}{ts_label}: {badge_text}", font="F2", size=9.5, color=badge_color)
            canvas.y -= 12
            
            claim_text = c.get("claim", "")
            canvas.add_paragraph(f"Statement: \"{claim_text}\"", font="F2", size=9.0, color=(0.15, 0.15, 0.2), indent=10)
            
            explanation = c.get("explanation", "")
            if explanation:
                canvas.add_paragraph(f"Audit: {explanation}", font="F1", size=8.5, color=(0.25, 0.25, 0.3), indent=10)

            corrected = c.get("corrected_info", "")
            if corrected and status == "outdated":
                canvas.add_paragraph(f"Modern Replacement: {corrected}", font="F2", size=8.5, color=(0.75, 0.2, 0.0), indent=10)

            sources = c.get("sources", [])
            if sources:
                src_line = "Sources: " + " | ".join(sources[:2])
                canvas.add_paragraph(src_line[:110], font="F3", size=7.5, color=(0.3, 0.45, 0.7), indent=10)

            canvas.y -= 6

    elif fact_check_data and not fact_check_data.get("needs_verification"):
        skip_msg = fact_check_data.get("skip_reason", "Non-technical video; live software verification skipped.")
        canvas.add_paragraph(f"Status: Skipped - {skip_msg}", font="F3", size=9)
    else:
        canvas.add_paragraph("Fact check not performed or no perishable claims detected.", font="F3", size=9)

    canvas.y -= 10

    # ==========================================
    # SECTION 2: TUTORIAL OVERVIEW / DESCRIPTION
    # ==========================================
    if description_text:
        canvas.add_heading("Executive Overview & Breakdown", level=1)
        # Strip markdown headers and print paragraphs
        clean_desc = "\n".join([line for line in description_text.splitlines() if not line.startswith("#") and line.strip()])
        canvas.add_paragraph(clean_desc[:3000], font="F1", size=9.0)
        canvas.y -= 8

    # ==========================================
    # SECTION 3: STEP-BY-STEP ROADMAP
    # ==========================================
    if curriculum_text:
        canvas.add_heading("Step-by-Step Curriculum & Roadmap", level=1)
        clean_curr = "\n".join([line for line in curriculum_text.splitlines() if not line.startswith("#") and line.strip()])
        canvas.add_paragraph(clean_curr[:3000], font="F1", size=9.0)
        canvas.y -= 8

    # ==========================================
    # SECTION 4: STUDY GUIDE & QUIZ
    # ==========================================
    if quiz_text:
        canvas.add_heading("Comprehension Quiz & Practice", level=1)
        clean_quiz = "\n".join([line for line in quiz_text.splitlines() if not line.startswith("#") and line.strip()])
        canvas.add_paragraph(clean_quiz[:2500], font="F1", size=9.0)

    return canvas.build_pdf()
