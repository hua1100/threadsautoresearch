"""PDF generator — convert Markdown lazy pack content to styled PDF."""
import markdown
from weasyprint import HTML


CSS = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
}
h1 {
    font-size: 24px;
    color: #1a1a1a;
    border-bottom: 2px solid #333;
    padding-bottom: 8px;
    margin-bottom: 16px;
}
h2 {
    font-size: 18px;
    color: #2c2c2c;
    margin-top: 24px;
    margin-bottom: 8px;
}
ol, ul {
    padding-left: 24px;
}
li {
    margin-bottom: 8px;
}
.footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #ccc;
    font-size: 12px;
    color: #666;
    text-align: center;
}
"""

FOOTER_HTML = """
<div class="footer">
    AI for…？ | Threads @hualeee | LINE 官方帳號
</div>
"""


def generate_pdf(content: str, title: str, output_path: str) -> None:
    """Convert Markdown content to a styled PDF file.

    Args:
        content: Markdown text (the lazy pack body).
        title: Pack title (used in HTML <title>).
        output_path: Where to save the PDF.
    """
    html_body = markdown.markdown(content, extensions=["extra"])

    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
{html_body}
{FOOTER_HTML}
</body>
</html>"""

    HTML(string=full_html).write_pdf(output_path)
