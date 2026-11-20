# UCSC Test Watermark

Install only on the v16 TEST server (10.22.200.93). Adds the text
"ERP16-Test Server" as a watermark on:

- every Desk page (`public/css/desk_watermark.css`, via `app_include_css`)
- every print format, print preview, PDF and report print/PDF
  (`print_watermark.py` appends CSS to `frappe.www.printview.get_print_style`,
  which all of those share)

Remove with: `bench --site erp16-test.ucsc.cmb.ac.lk uninstall-app ucsc_test_watermark`
