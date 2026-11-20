app_name = "ucsc_test_watermark"
app_title = "UCSC Test Watermark"
app_publisher = "UCSC"
app_description = "ERP16-Test Server watermark for desk, print formats and reports"
app_email = "admin@ucsc.cmb.ac.lk"
app_license = "mit"

# Desk: watermark on every page
app_include_css = "/assets/ucsc_test_watermark/css/desk_watermark.css"

# Print formats / reports / PDFs: extend the shared print stylesheet
before_request = ["ucsc_test_watermark.print_watermark.apply"]
before_job = ["ucsc_test_watermark.print_watermark.apply"]
