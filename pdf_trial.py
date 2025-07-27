from PyPDF2 import PdfReader

pdf_file = "TarekCV.pdf"

reader = PdfReader(pdf_file)

print(len(reader.pages))
for i in range(len(reader.pages)):
    print (f" page {i} -----  {reader.pages[i].extract_text()} ----  " )

