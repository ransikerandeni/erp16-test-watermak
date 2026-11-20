"""'ERP16-Test Server' watermark for every print output on the v16 test server.

1. CSS (Chrome PDF + browser print/preview)
   frappe.www.printview.get_print_style() builds the stylesheet for document
   print view / preview / Chrome PDFs (all print formats), frappe.boot.print_css
   (report "Print" from the desk) and report PDFs. We append watermark CSS to it.

2. PDF stamp (wkhtmltopdf)
   wkhtmltopdf (used for report PDFs, auto email reports and wkhtmltopdf print
   formats) does not repeat position:fixed on every page. So we wrap
   pdfkit.from_string: strip the CSS watermark from the HTML, render, then draw
   the watermark onto every page of the resulting PDF with pypdf.

Both patches are applied once per process from the before_request / before_job hooks.
"""

import io
import math
import re

import frappe.www.printview as printview
import pdfkit

WATERMARK_TEXT = "ERP16-Test Server"

_CSS_START = "/*UCSC-WM-START*/"
_CSS_END = "/*UCSC-WM-END*/"

# Scoped to .print-format-gutter so Chrome PDF header/footer strips are skipped.
WATERMARK_CSS = (
	_CSS_START
	+ """
.print-format-gutter .print-format::before {
	content: "%s";
	display: block;
	position: fixed;
	top: 320px;
	left: 0;
	right: 0;
	width: 100%%;
	text-align: center;
	-webkit-transform: rotate(-35deg);
	transform: rotate(-35deg);
	font-size: 56px;
	font-weight: 700;
	letter-spacing: 2px;
	white-space: nowrap;
	color: #f5d0d0;
	opacity: 0.9;
	z-index: 1000;
	pointer-events: none;
	-webkit-print-color-adjust: exact;
	print-color-adjust: exact;
}
"""
	% WATERMARK_TEXT
	+ _CSS_END
)

_CSS_RE = re.compile(re.escape(_CSS_START) + r".*?" + re.escape(_CSS_END), re.S)

# Helvetica-Bold AFM widths (1/1000 em) for measuring the stamp text
_HELV_BOLD = {
	" ": 278, "-": 333, "0": 556, "1": 556, "6": 556, "E": 667, "P": 667, "R": 722,
	"S": 667, "T": 611, "e": 556, "r": 389, "s": 556, "t": 333, "v": 556,
}


def apply(*args, **kwargs):
	_patch_print_style()
	_patch_wkhtmltopdf()


def _patch_print_style():
	original = printview.get_print_style
	if getattr(original, "_ucsc_watermark", False):
		return

	def get_print_style(*a, **kw):
		return (original(*a, **kw) or "") + "\n" + WATERMARK_CSS

	get_print_style._ucsc_watermark = True
	printview.get_print_style = get_print_style


def _patch_wkhtmltopdf():
	original = pdfkit.from_string
	if getattr(original, "_ucsc_watermark", False):
		return

	def from_string(input, output_path=None, *a, **kw):
		if isinstance(input, str):
			input = _CSS_RE.sub("", input)
		result = original(input, output_path, *a, **kw)
		if isinstance(result, bytes | bytearray) and result[:4] == b"%PDF":
			try:
				return stamp_pdf(bytes(result))
			except Exception:
				return result  # never break printing because of the watermark
		return result

	from_string._ucsc_watermark = True
	pdfkit.from_string = from_string


def stamp_pdf(data: bytes) -> bytes:
	from pypdf import PdfReader, PdfWriter
	from pypdf.generic import DecodedStreamObject, DictionaryObject, FloatObject, NameObject

	reader = PdfReader(io.BytesIO(data))
	writer = PdfWriter(clone_from=reader)

	for page in writer.pages:
		box = page.mediabox
		w, h = float(box.width), float(box.height)
		size = min(w, h) / 10.5  # ~56pt on A4
		text_w = sum(_HELV_BOLD.get(c, 556) for c in WATERMARK_TEXT) * size / 1000
		ang = math.radians(35)
		c, s = math.cos(ang), math.sin(ang)
		cx, cy = float(box.left) + w / 2, float(box.bottom) + h / 2

		ops = (
			f"q /UCSCWMGS gs 0.8 0 0 rg "
			f"1 0 0 1 {cx:.2f} {cy:.2f} cm {c:.4f} {s:.4f} {-s:.4f} {c:.4f} 0 0 cm "
			f"BT /UCSCWMF {size:.2f} Tf {-text_w / 2:.2f} {-size / 3:.2f} Td "
			f"({WATERMARK_TEXT}) Tj ET Q"
		).encode()

		resources = page.get("/Resources")
		resources = resources.get_object() if resources is not None else DictionaryObject()
		fonts = resources.get("/Font")
		fonts = fonts.get_object() if fonts is not None else DictionaryObject()
		fonts[NameObject("/UCSCWMF")] = DictionaryObject(
			{
				NameObject("/Type"): NameObject("/Font"),
				NameObject("/Subtype"): NameObject("/Type1"),
				NameObject("/BaseFont"): NameObject("/Helvetica-Bold"),
			}
		)
		resources[NameObject("/Font")] = fonts
		gstates = resources.get("/ExtGState")
		gstates = gstates.get_object() if gstates is not None else DictionaryObject()
		gstates[NameObject("/UCSCWMGS")] = DictionaryObject(
			{NameObject("/Type"): NameObject("/ExtGState"), NameObject("/ca"): FloatObject(0.15)}
		)
		resources[NameObject("/ExtGState")] = gstates
		page[NameObject("/Resources")] = resources

		existing = page.get_contents()
		# wrap original content in q/Q so its graphics state can't affect the stamp
		new = DecodedStreamObject()
		new.set_data(b"q\n" + (existing.get_data() if existing is not None else b"") + b"\nQ\n" + ops)
		page.replace_contents(new)

	out = io.BytesIO()
	writer.write(out)
	return out.getvalue()
