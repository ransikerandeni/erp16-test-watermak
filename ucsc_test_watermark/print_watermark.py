"""Append a watermark to the CSS Frappe uses for every print output.

frappe.www.printview.get_print_style() builds the stylesheet for:
  - document print view / print preview and PDFs (all print formats)
  - frappe.boot.print_css -> report "Print" from Query/Script Reports
  - report PDF (frappe.utils.print_format.report_to_pdf)
Wrapping it once per process covers all of them.
"""

import frappe.www.printview as printview

WATERMARK_TEXT = "ERP16-Test Server"

WATERMARK_CSS = """
/* UCSC test-server watermark.
   Uses only px offsets + rotate so it renders in both Chrome PDF (print formats)
   and wkhtmltopdf (report PDFs); position:fixed repeats it on every page.
   Scoped to .print-format-gutter so Chrome PDF header/footer strips are skipped. */
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
""" % WATERMARK_TEXT


def apply(*args, **kwargs):
	original = printview.get_print_style
	if getattr(original, "_ucsc_watermark", False):
		return

	def get_print_style(*a, **kw):
		return (original(*a, **kw) or "") + "\n" + WATERMARK_CSS

	get_print_style._ucsc_watermark = True
	printview.get_print_style = get_print_style
