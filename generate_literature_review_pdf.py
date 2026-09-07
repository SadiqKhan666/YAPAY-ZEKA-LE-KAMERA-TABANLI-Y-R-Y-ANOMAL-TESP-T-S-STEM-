from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import textwrap

input_path = 'literature_review.md'
output_path = 'Literature_Review_GaitProject.pdf'

with open(input_path, 'r', encoding='utf-8') as f:
    text = f.read()

pages = text.split('\n\n\n')

c = canvas.Canvas(output_path, pagesize=letter)
width, height = letter
margin = 0.75 * inch
max_width = width - 2 * margin

for page_text in pages:
    text_obj = c.beginText(margin, height - margin)
    text_obj.setFont('Helvetica', 11)
    for paragraph in page_text.split('\n\n'):
        lines = textwrap.wrap(paragraph, width=95)
        for line in lines:
            text_obj.textLine(line)
        text_obj.textLine('')
    c.drawText(text_obj)
    c.showPage()

c.save()
print(f'Created PDF: {output_path}')
