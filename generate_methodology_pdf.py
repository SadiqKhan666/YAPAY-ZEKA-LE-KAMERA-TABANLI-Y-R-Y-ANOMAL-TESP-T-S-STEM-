from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import textwrap

input_path = 'methodology.md'
output_path = 'Methodology_GaitProject.pdf'

with open(input_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Split into roughly 12-15 pages by headings; use double blank lines as paragraph separators
paragraphs = text.split('\n\n')

c = canvas.Canvas(output_path, pagesize=letter)
width, height = letter
margin = 0.75 * inch

lines_per_page = 50
current_lines = []

for para in paragraphs:
    wrapped = textwrap.wrap(para, width=100)
    if not wrapped:
        current_lines.append('')
    else:
        for w in wrapped:
            current_lines.append(w)
    # flush page if too long
    if len(current_lines) >= lines_per_page:
        text_obj = c.beginText(margin, height - margin)
        text_obj.setFont('Helvetica', 11)
        for ln in current_lines:
            text_obj.textLine(ln)
        c.drawText(text_obj)
        c.showPage()
        current_lines = []

# write remaining
if current_lines:
    text_obj = c.beginText(margin, height - margin)
    text_obj.setFont('Helvetica', 11)
    for ln in current_lines:
        text_obj.textLine(ln)
    c.drawText(text_obj)
    c.showPage()

c.save()
print('Created PDF:', output_path)
