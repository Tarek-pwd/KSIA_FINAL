import os
import matplotlib
matplotlib.use('Agg')  # Avoid GUI error on macOS
from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import cv2
import numpy as np
import json
from ultralytics import YOLO
import pdfplumber
from docx import Document
from vec_trial import query_vectara_check_violations
from vec_trial import query_vectara
from vec_agentic import run_query
from vec_agentic_room_comparison import execute_query_with_streaming
from smart_vectara_report import run_smart_query
from query_database import execute_query
import shutil
from fpdf import FPDF
from datetime import datetime
import openai
from PyPDF2 import PdfReader
import time
import threading

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Register an Arabic font like Amiri or Noto
pdfmetrics.registerFont(TTFont('Amiri', 'Amiri-Regular.ttf'))  

# Import your reporting code - make sure this import path is correct
from vec_reporting import run_query as report_run_query
from vec_reporting import list_available_templates, process_templates, reset_agent

app = Flask(__name__)

# Add curriculum folder to your existing folders
CURRICULUM_FOLDER = 'curriculum_outputs'
os.makedirs(CURRICULUM_FOLDER, exist_ok=True)
app.config['CURRICULUM_FOLDER'] = CURRICULUM_FOLDER

# Store curriculum processing progress
curriculum_progress = {}
generated_curricula= {}
curriculum_rag_data = {}  # Store RAG data for each curriculum
curriculum_chat_history = {}  # Store chat history for each curriculum
embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# Set your OpenAI API key - IMPORTANT: Use environment variable in production
openai.api_key = os.getenv('OPENAI_API_KEY')

# === Config ===
UPLOAD_FOLDER = 'uploads'
IMAGE_FOLDER = 'converted_images'
TEMPLATE_FOLDER = 'my_templates'
ALLOWED_DXF = {'dxf'}
ALLOWED_DOCS = {'pdf', 'doc', 'docx', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER
app.config['TEMPLATE_FOLDER'] = TEMPLATE_FOLDER

# Store uploaded documents for reports
uploaded_documents = {}

# === Helper: Check file type ===
def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

# === Curriculum Processing Functions ===
def extract_and_chunk_pdf(pdf_path, pages_per_chunk=3):
    """Extract PDF in small chunks for MAXIMUM detail."""
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    chunks = []
    
    for i in range(0, total_pages, pages_per_chunk):
        chunk_pages = []
        end = min(i + pages_per_chunk, total_pages)
        
        for j in range(i, end):
            page_text = reader.pages[j].extract_text()
            if page_text:
                chunk_pages.append(page_text)
        
        if chunk_pages:
            chunk_text = "\n\n".join(chunk_pages)
            chunks.append({
                'text': chunk_text,
                'start_page': i + 1,
                'end_page': end,
                'page_count': end - i
            })
    
    return chunks, total_pages

def generate_mega_curriculum(chunks, total_pages, model="gpt-4o", task_id=None):
    """Generate MASSIVE, DETAILED curriculum - 20% of original length!"""
    target_output_pages = total_pages * 0.2
    pages_per_chunk = target_output_pages / len(chunks)
    words_per_chunk = int(pages_per_chunk * 500)
    
    curricula = []
    total = len(chunks)
    
    for idx, chunk_data in enumerate(chunks):
        chunk = chunk_data['text']
        start_page = chunk_data['start_page']
        end_page = chunk_data['end_page']
        
        # Update progress
        if task_id:
            progress = int((idx / total) * 100)
            curriculum_progress[task_id] = {
                'progress': progress,
                'current_chunk': idx + 1,
                'total_chunks': total,
                'status': f'معالجة الصفحات {start_page}-{end_page}'
            }
        
        prompt = f"""
أنت خبير في تطوير المناهج التدريبية العسكرية. مهمتك هي تحويل النص التالي إلى منهج تدريبي مفصل للغاية.

⚠️ مهم جداً: يجب أن يكون المنهج طويل جداً ومفصل للغاية!
📏 الطول المطلوب: {words_per_chunk} كلمة على الأقل (حوالي {pages_per_chunk:.1f} صفحة)

المطلوب في المنهج:
1. عنوان الوحدة التدريبية
2. الأهداف التعليمية التفصيلية (10-15 هدف)
3. المحتوى النظري المفصل جداً
4. التطبيقات العملية
5. طرق التقييم
6. الجدول الزمني التفصيلي
7. المصادر والمراجع
8. ملاحظات للمدرب

النص المصدر:
{chunk}
"""
        
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "أنت خبير في كتابة المناهج التدريبية المفصلة للغاية."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            
            curriculum = response.choices[0].message.content
            formatted_curriculum = f"""
{'='*80}
📚 الوحدة التدريبية: الصفحات {start_page} إلى {end_page}
{'='*80}

{curriculum}

{'='*80}
"""
            curricula.append(formatted_curriculum)
            
        except Exception as e:
            curricula.append(f"\n[خطأ في معالجة الصفحات {start_page}-{end_page}]\n")
        
        time.sleep(1)  # Avoid rate limits
    
    return "".join(curricula)


def process_curriculum_pdf(pdf_path, output_file, task_id):
    """Process PDF and generate curriculum in background"""
    try:
        curriculum_progress[task_id] = {
            'progress': 0,
            'status': 'بدء المعالجة...',
            'current_chunk': 0,
            'total_chunks': 0
        }
        
        chunks, total_pages = extract_and_chunk_pdf(pdf_path, pages_per_chunk=3)
        curriculum_progress[task_id]['total_chunks'] = len(chunks)
        
        full_curriculum = generate_mega_curriculum(chunks, total_pages, task_id=task_id)
        print(f"Creating RAG index for task {task_id}")
        create_curriculum_rag(full_curriculum, task_id)
        
        # Create PDF instead of TXT
        output_pdf = output_file.replace('.txt', '.pdf')
        doc = SimpleDocTemplate(output_pdf, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Create Arabic-friendly style
        arabic_style = ParagraphStyle(
    'Arabic',
    parent=styles['Normal'],
    fontName='Amiri',  # <-- Use registered font here
    fontSize=12,
    leading=16,
    alignment=2  # Right alignment
)
        
        # Add title
        title_style = ParagraphStyle(
    'ArabicTitle',
    parent=styles['Title'],
    fontName='Amiri',
    fontSize=18,
    leading=22,
    alignment=1
)

        
        # Process Arabic text properly
        def process_arabic_text(text):
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        
        # Add header
        header_text = f"""منهج تدريبي شامل ومفصل
الكتاب المصدر: {os.path.basename(pdf_path)}
تاريخ الإعداد: {time.strftime('%Y-%m-%d %H:%M')}
عدد صفحات الكتاب: {total_pages}"""
        
        for line in header_text.split('\n'):
            story.append(Paragraph(process_arabic_text(line), title_style))
            story.append(Spacer(1, 0.2*inch))
        
        story.append(PageBreak())
        
        # Add curriculum content
        for line in full_curriculum.split('\n'):
            if line.strip():
                if line.startswith('='):
                    story.append(Spacer(1, 0.3*inch))
                else:
                    story.append(Paragraph(process_arabic_text(line), arabic_style))
                    story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        total_words = len(full_curriculum.split())
        total_output_pages = total_words / 500
        
        
        # Create PDF (rest of your PDF generation code...)
        # ... (keep the rest of the PDF generation code as before)
        
        curriculum_progress[task_id] = {
            'progress': 100,
            'status': 'اكتمل!',
            'current_chunk': len(chunks),
            'total_chunks': len(chunks),
            'completed': True,
            'output_file': output_pdf,
            'curriculum_id': task_id,  # Add this for chatbot reference
            'stats': {
                'total_words': total_words,
                'total_pages': total_output_pages,
                'compression_ratio': (total_output_pages/total_pages)*100
            }
        }
        
    except Exception as e:
        curriculum_progress[task_id] = {
            'progress': 0,
            'status': f'خطأ: {str(e)}',
            'error': True
        }


def chunk_text(text, chunk_size=500, overlap=100):
    """Split text into chunks by words"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk = ' '.join(chunk_words)
        chunks.append(chunk)
    
    return chunks

# Add this function to create RAG index
def create_curriculum_rag(curriculum_content, task_id):
    """Create RAG index for the curriculum"""
    try:
        # Create chunks
        chunks = chunk_text(curriculum_content, chunk_size=500, overlap=100)
        
        # Create embeddings
        chunk_embeddings = embedding_model.encode(chunks, show_progress_bar=False)
        
        # Create FAISS index
        dimension = chunk_embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(chunk_embeddings).astype('float32'))
        
        # Store in global dictionary
        curriculum_rag_data[task_id] = {
            'chunks': chunks,
            'index': index,
            'embeddings': chunk_embeddings
        }
        
        return True
    except Exception as e:
        print(f"Error creating RAG index: {str(e)}")
        return False

# === Helper: Convert DXF to JPG ===
def convert_dxf_to_jpg(dxf_path, jpg_path, dpi=300 , bg_color ='white'):
    print("converting file to image")
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    if bg_color == 'white':
        fig = plt.figure(figsize=(10, 10), dpi=dpi, facecolor='white')
    else:
        fig = plt.figure(figsize=(10, 10), dpi=dpi, facecolor='black')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    ax.axis("off")
    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    frontend = Frontend(ctx, backend)
    frontend.draw_layout(msp, finalize=True)
    fig.savefig(jpg_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
    plt.close(fig)


  

def clean_sql_response(my_string):
    indeces = []
    final_statements = []
    for i in range(len(my_string) -3):
        if my_string[i:i+3] == 'sql':
            print("index" , i)
            indeces.append(i)
    print(indeces)
    for i in range(len(indeces)-1):
        final_statements.append(my_string[indeces[i]+3:indeces[i+1]].strip().replace("\n" ," "))
    final_statements.append(my_string[indeces[len(indeces)-1]+3:].strip().replace("\n"," ")) 
    
    return final_statements

# === Helper: Extract text from document ===
def extract_text(filepath, flg):
    try:
        if filepath.endswith('.pdf'):
            with pdfplumber.open(filepath) as pdf:
                text = ''.join(page.extract_text() or '' for page in pdf.pages)

        elif filepath.endswith('.docx'):
            doc = Document(filepath)
            text = '\n'.join([p.text for p in doc.paragraphs])
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        if flg:
            return text
        else:
            return text[:1500] + ('...' if len(text) > 1500 else '')
    except Exception as e:
        return f"⚠️ Error reading file: {e}"

# === Routes ===



# Legal Chatbot page
@app.route('/legal-chatbot.html')
def legal_chatbot():
    return render_template('legal-chatbot.html')



@app.route('/signature-detection.html')
def signature_detection():
    return render_template('signature-detection.html')

@app.route('/')
def landing_page():
    return render_template('landing-page.html')

@app.route('/trial')
def kk():
    return render_template('trial.html')

# Original upload page for Architect Detection
@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

# Results page
@app.route('/results')
def results_page():
    return render_template('index.html')

# HR Chatbot page
@app.route('/hr-chatbot.html')
def hr_chatbot():
    return render_template('hr-chatbot.html')

# # Legal Chatbot page
# @app.route('/legal-chatbot.html')
# def legal_chatbot():
#     return render_template('legal-chatbot.html')

# Finance Chatbot page
@app.route('/finance-chatbot.html')
def finance_chatbot():
    return render_template('finance-chatbot.html')

#Curicculum
@app.route('/curriculum')
def cur():
    return render_template('Curriculum.html')

#report
@app.route('/report')
def report():
    return render_template('reports.html')

# ========== REPORTS FUNCTIONALITY ==========

@app.route('/api/reports/upload', methods=['POST'])
def upload_report_file():
    try:
        if 'report' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
       
        file = request.files['report']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
       
        # Check if it's a template upload
        is_template = request.form.get('is_template', 'false').lower() == 'true'
        
        filename = secure_filename(file.filename)
        
        if is_template:
            # Save to templates directory
            template_path = os.path.join(app.config['TEMPLATE_FOLDER'], filename)
            file.save(template_path)
            
            # Reload templates in the vec_reporting module
            reset_agent()  # Reset the agent to reload templates
            process_templates()  # Reprocess templates
            
            return jsonify({
                'message': 'Template uploaded successfully',
                'filename': filename,
                'is_template': True
            })
        else:
            # Regular file upload
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extract text content
            content = extract_text(file_path, True)
            uploaded_documents[filename] = content
            word_count = len(content.split())
            
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'word_count': word_count,
                'is_template': False
            })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/reports/refresh-templates', methods=['GET'])
def refresh_templates():
    try:
        # Reset and reload templates
        reset_agent()
        process_templates()
        
        # Get updated list
        templates = list_available_templates()
        
        return jsonify({
            'templates': templates,
            'count': len(templates)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to refresh templates: {str(e)}'}), 500

@app.route('/api/reports/chat', methods=['POST'])
def chat_reports():
    try:
        data = request.get_json()
        query = data.get('query')
        filename = data.get('filename')
       
        if not query:
            return jsonify({'error': 'No query provided'}), 400
       
        if filename and filename in uploaded_documents:
            document_content = uploaded_documents[filename]
            full_query = f"Based on this document: {document_content}\n\nUser question: {query}"
        else:
            full_query = query
       
        response = report_run_query(full_query)
       
        return jsonify({
            'response': str(response),
            'message': 'Response generated successfully'
        })
       
    except Exception as e:
        return jsonify({'error': f'Chat failed: {str(e)}'}), 500
# Replace the export_report_pdf function in your app.py with this:

# Replace your export_report_pdf function with this Word export function:

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from datetime import datetime

@app.route('/api/reports/export-pdf', methods=['POST'])  # Keep the same route name for compatibility
def export_report_word():
    try:
        data = request.get_json()
        content = data.get('content', '')
        filename = data.get('filename', 'report')
        
        if not content:
            return jsonify({'error': 'No content to export'}), 400
        
        # Create a new Document
        doc = Document()
        
        # Add title
        title = doc.add_heading('Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add date
        date_para = doc.add_paragraph()
        date_run = date_para.add_run(f'Generated on: {datetime.now().strftime("%B %d, %Y")}')
        date_run.italic = True
        date_run.font.size = Pt(10)
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add document name if provided
        if filename and filename != 'report':
            doc.add_paragraph()
            info_para = doc.add_paragraph()
            info_para.add_run('Document: ').bold = True
            info_para.add_run(filename)
        
        # Add a line break
        doc.add_paragraph()
        doc.add_paragraph('_' * 50)
        doc.add_paragraph()
        
        # Process content
        paragraphs = content.split('\n\n')
        
        for para_text in paragraphs:
            if para_text.strip():
                # Check if it's a heading (starts with # or **)
                if para_text.startswith('#'):
                    heading_text = para_text.replace('#', '').strip()
                    doc.add_heading(heading_text, level=2)
                elif para_text.startswith('**') and para_text.endswith('**'):
                    # Bold text
                    p = doc.add_paragraph()
                    p.add_run(para_text.replace('**', '')).bold = True
                else:
                    # Regular paragraph
                    # Split by single newlines to preserve line breaks
                    lines = para_text.split('\n')
                    p = doc.add_paragraph()
                    
                    for i, line in enumerate(lines):
                        if line.strip():
                            # Check if line contains Arabic
                            has_arabic = any('\u0600' <= char <= '\u06FF' for char in line)
                            
                            if has_arabic:
                                # For Arabic text, set right-to-left
                                run = p.add_run(line)
                                run.font.size = Pt(12)
                                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                            else:
                                # Regular text
                                run = p.add_run(line)
                                run.font.size = Pt(11)
                            
                            # Add line break if not the last line
                            if i < len(lines) - 1:
                                p.add_run('\n')
        
        # Add footer
        doc.add_paragraph()
        doc.add_paragraph('_' * 50)
        footer = doc.add_paragraph()
        footer.add_run('End of Report').italic = True
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Save to BytesIO object
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        # Return as downloadable file
        return Response(
            file_stream.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={
                'Content-Disposition': f'attachment; filename={filename}_{datetime.now().strftime("%Y%m%d")}.docx'
            }
        )
        
    except Exception as e:
        print(f"Word Export Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/reports/analyze', methods=['POST'])
def analyze_document():
    try:
        data = request.get_json()
        filename = data.get('filename')
       
        if not filename or filename not in uploaded_documents:
            return jsonify({'error': 'Document not found'}), 404
       
        document_content = uploaded_documents[filename]
        query = f"Analyze this document and provide insights: {document_content}"
       
        analysis = report_run_query(query)
       
        return jsonify({
            'analysis': str(analysis),
            'message': 'Document analysis completed successfully'
        })
       
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/reports/summary', methods=['POST'])
def generate_summary():
    try:
        data = request.get_json()
        filename = data.get('filename')
       
        if not filename or filename not in uploaded_documents:
            return jsonify({'error': 'Document not found'}), 404
       
        document_content = uploaded_documents[filename]
        query = f"Generate a summary of this document: {document_content}"
       
        summary = report_run_query(query)
       
        return jsonify({
            'summary': str(summary),
            'message': 'Summary generated successfully'
        })
       
    except Exception as e:
        return jsonify({'error': f'Summary generation failed: {str(e)}'}), 500



# ========== END REPORTS FUNCTIONALITY ==========

# ========== OTHER EXISTING ROUTES ==========

@app.route('/ask_HR', methods=["POST"])
def ask_hr_bot():
    try:
        data = request.get_json()
        if not data or 'user_message' not in data:
            return jsonify({"error": "Invalid request format"}), 400
           
        message = data['user_message']
        print(f"Backend processing message: {message}")
       
        # Run the query
        response = run_query(message)
        print(f"Backend generated response: {response}")
       
        return jsonify({
            "bot_response": response,
            "status": "success"
        })
       
    except Exception as e:
        print(f"Error in ask_hr_bot: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "An error occurred processing your request",
            "status": "error"
        }), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_query = data.get("query", "")

    def generate():
        try:
            for chunk in query_vectara(user_query):
                yield chunk
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"

    return Response(stream_with_context(generate()), content_type='text/plain')

@app.route("/check-violations", methods=["POST"])
def check_violations():
    data = request.get_json()
    doc_path = data["doc_path"]
    rules = extract_text(doc_path,1)
    with open('output/room_summary.json', "r") as f:
        detection_data =  json.load(f)
   
    user_q_t = f"The detected data from the  rooms is {detection_data} \n and the rules file is {rules}"
       
    def generate():
        for chunk in execute_query_with_streaming(user_q_t,0):
            print(chunk, end='', flush=True)
            yield chunk

    return Response(stream_with_context(generate()), content_type='text/plain')

@app.route('/generate_smart_report', methods=["POST"])
def generate_smart():
    print("getting smart!")

    queries_dict = {}

    data = request.get_json()
    query = data['smart_query']
    print("backend recieved the smart query ")
    recieved = run_smart_query(query)
    print("recieved answer at backend " , recieved)
    cleaned_version = clean_sql_response(recieved)
    print("cleaned version! ---- ")
    for elem in cleaned_version:
        res = execute_query(elem)
        queries_dict[elem] = res

    print("----- FINALYYYYY ----")
    print(queries_dict)
    print(" ----- END HERE ----")

    def generate():
        user_query = f"This is the data that you should use to produce the report {queries_dict}  "
        for chunk in execute_query_with_streaming(user_query,1):
            print(chunk, end='', flush=True)
            yield chunk
    return Response(stream_with_context(generate()), content_type='text/plain')

@app.route('/export_docx', methods=["POST"])
def export_docx():
    from flask import send_file
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import io
    from datetime import datetime
   
    data = request.get_json()
    report_content = data.get('report_content', '')
   
    # Create a new Document
    doc = Document()
   
    # Add title
    title = doc.add_heading('HR Smart Report', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
   
    # Add date
    date_para = doc.add_paragraph()
    date_para.add_run(f'Generated on: {datetime.now().strftime("%B %d, %Y")}').italic = True
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
   
    # Add a line break
    doc.add_paragraph()
   
    # Parse and format the report content
    sections = report_content.split('\n\n')
   
    for section in sections:
        if section.strip():
            # Check if it's a header
            if section.startswith('#'):
                heading_text = section.replace('#', '').strip()
                doc.add_heading(heading_text, level=2)
            elif section.startswith('**') and section.endswith('**'):
                # Bold text
                p = doc.add_paragraph()
                p.add_run(section.replace('**', '')).bold = True
            else:
                # Regular paragraph
                doc.add_paragraph(section)
   
    # Save to a BytesIO object
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
   
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=f'HR_Smart_Report_{datetime.now().strftime("%Y%m%d")}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
   
@app.route("/get-room-data", methods=["GET"])
def get_room_data():
    """
    Endpoint to retrieve room data from the latest analysis
    """
    try:
        # Path to the room summary file generated by run_full_analysis
        room_data_path = "output/room_summary.json"
       
        # Check if the file exists
        if not os.path.exists(room_data_path):
            return jsonify({"error": "Room data not found. Please run analysis first."}), 404
       
        # Read the room data
        with open(room_data_path, "r") as f:
            room_data = json.load(f)
       
        return jsonify(room_data), 200
       
    except Exception as e:
        print(f"Error getting room data: {str(e)}")
        return jsonify({"error": "Failed to retrieve room data"}), 500

@app.route('/upload', methods=['POST'])
def upload():
    print("Upload was called!")
    dxf_file = request.files.get('dxf')
    doc_file = request.files.get('doc')

    if not dxf_file or not doc_file:
        return "Missing file(s)", 400

    if not allowed_file(dxf_file.filename, ALLOWED_DXF):
        return "Invalid DXF file", 400
    if not allowed_file(doc_file.filename, ALLOWED_DOCS):
        return "Invalid document file", 400

    dxf_filename = secure_filename(dxf_file.filename)
    doc_filename = secure_filename(doc_file.filename)

    dxf_path = os.path.join(app.config['UPLOAD_FOLDER'], dxf_filename)
    doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)

    dxf_file.save(dxf_path)
    doc_file.save(doc_path)

    # Create TWO versions of the image
    base_name = os.path.splitext(dxf_filename)[0]
    
    # 1. Black background version for display
    display_filename = f"{base_name}_display.jpg"
    display_path = os.path.join(app.config['IMAGE_FOLDER'], display_filename)
    convert_dxf_to_jpg(dxf_path, display_path, bg_color='black')
    
    # 2. White background version for YOLO analysis
    analysis_filename = f"{base_name}_analysis.jpg"
    analysis_path = os.path.join(app.config['IMAGE_FOLDER'], analysis_filename)
    convert_dxf_to_jpg(dxf_path, analysis_path, bg_color='white')

    # Extract document text
    doc_text = extract_text(doc_path, 0)

    print("doc text", doc_text)

    return jsonify({
        "message": "Files uploaded and DXF converted",
        "image_url": f"/converted_images/{display_filename}",  # Black version for display
        "doc_filename": doc_filename,
        "doc_text": doc_text,
        "dxf_path": dxf_path,
        "image_path": analysis_path,  # White version for analysis
        "display_path": display_path,  # Black version path
        "analysis_path": analysis_path,  # White version path
        "doc_path": doc_path
    })
@app.route('/converted_images/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['IMAGE_FOLDER'], filename)

@app.route('/analysis_outputs/<filename>')
def serve_analysis_preview(filename):
    return send_from_directory('analysis_outputs', filename)

from analysis_core import run_full_analysis
@app.route('/run-analysis', methods=['POST'])
def run_analysis():
    print("Run analysis called!")
    data = request.get_json()
    
    # Get both paths
    analysis_path = data["image_path"]  # White background for YOLO
    display_path = data.get("display_path", analysis_path)  # Black background for display
    dxf_path = data["dxf_path"]
  
    try:
        # Run analysis on WHITE background image
        run_full_analysis(analysis_path, dxf_path)
        print("Done full analysis")

        # Load models
        det_model = YOLO("final_detection.pt")
        seg_model = YOLO("best.pt")

        # Run detection with custom confidence threshold
        # You can adjust these confidence values as needed
        det_result = det_model(analysis_path, conf=0.25)[0]  # Lower conf = more detections
        seg_result = seg_model(analysis_path, conf=0.25)[0]  # Adjust as needed

        # Load the BLACK background image for display
        black_img = cv2.imread(display_path)
        
        # For detection (objects) - use normal plot
        det_img = det_result.plot(
            img=black_img.copy(),  # Use copy to not modify original
            conf=False,            # Don't show confidence numbers
            labels=True,           # Show object names
            line_width=3,          # Thicker lines
            masks=False            # No masks for detection
        )
        
        # For segmentation (rooms) - plot with masks
        seg_img = seg_result.plot(
            img=black_img.copy(),  # Use copy
            conf=False,            # Don't show confidence numbers
            labels=True,           # Show room labels
            line_width=2,          # Thinner lines for rooms
            masks=True,            # SHOW ACTUAL ROOM SHAPES (masks)
            boxes=False            # DON'T show bounding boxes for rooms
        )

        # Alternative: If the above doesn't work, manually draw masks
        if seg_result.masks is not None:
            # Create a colored overlay for room masks
            seg_img_manual = black_img.copy()
            
            # Define colors for different room types (BGR format)
            room_colors = {
                0: (255, 0, 0),      # Blue
                1: (0, 255, 0),      # Green
                2: (0, 0, 255),      # Red
                3: (255, 255, 0),    # Cyan
                4: (255, 0, 255),    # Magenta
                5: (0, 255, 255),    # Yellow
            }
            
            # Draw each room mask
            masks = seg_result.masks.data.cpu().numpy()
            classes = seg_result.boxes.cls.cpu().numpy()
            
            for i, (mask, cls) in enumerate(zip(masks, classes)):
                # Resize mask to image size
                mask_resized = cv2.resize(mask, (black_img.shape[1], black_img.shape[0]))
                mask_binary = (mask_resized > 0.5).astype(np.uint8)
                
                # Create colored mask
                color = room_colors.get(int(cls), (128, 128, 128))
                colored_mask = np.zeros_like(seg_img_manual)
                colored_mask[mask_binary == 1] = color
                
                # Blend with original image (transparency)
                seg_img_manual = cv2.addWeighted(seg_img_manual, 1, colored_mask, 0.3, 0)
                
                # Draw room contours
                contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(seg_img_manual, contours, -1, color, 2)
                
                # Add room label
                if contours:
                    # Get centroid of largest contour
                    largest_contour = max(contours, key=cv2.contourArea)
                    M = cv2.moments(largest_contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        room_name = seg_model.names[int(cls)]
                        cv2.putText(seg_img_manual, room_name, (cx-30, cy), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Use the manually drawn version if needed
            seg_img = seg_img_manual

        # Save the results
        os.makedirs("analysis_outputs", exist_ok=True)
        det_path = os.path.join("analysis_outputs", "detection.jpg")
        seg_path = os.path.join("analysis_outputs", "segmentation.jpg")
        cv2.imwrite(det_path, det_img)
        cv2.imwrite(seg_path, seg_img)

        return jsonify({
            "message": "✅ Analysis complete.",
            "detection_url": "/analysis_outputs/detection.jpg",
            "segmentation_url": "/analysis_outputs/segmentation.jpg"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
# ========== CURRICULUM ROUTES ==========

@app.route('/api/curriculum/upload', methods=['POST'])
def upload_curriculum_pdf():
    """Upload PDF for curriculum generation"""
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        task_id = f"curriculum_{int(time.time())}_{filename}"
        
        output_file = os.path.join(app.config['CURRICULUM_FOLDER'], f"curriculum_{filename}.pdf")  # Changed from .txt to .pdf
        thread = threading.Thread(
            target=process_curriculum_pdf,
            args=(pdf_path, output_file, task_id)
        )
        thread.start()
        
        return jsonify({
            'message': 'تم رفع الملف بنجاح! بدأت المعالجة...',
            'task_id': task_id,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/curriculum/progress/<task_id>', methods=['GET'])
def get_curriculum_progress(task_id):
    """Get progress of curriculum generation"""
    if task_id not in curriculum_progress:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(curriculum_progress[task_id])

@app.route('/api/curriculum/download/<task_id>', methods=['GET'])
def download_curriculum(task_id):
    """Download generated curriculum"""
    if task_id not in curriculum_progress:
        return jsonify({'error': 'Task not found'}), 404
    
    progress = curriculum_progress[task_id]
    if not progress.get('completed'):
        return jsonify({'error': 'Curriculum not ready yet'}), 400
    
    output_file = progress.get('output_file')
    if not output_file or not os.path.exists(output_file):
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_from_directory(
        os.path.dirname(output_file),
        os.path.basename(output_file),
        as_attachment=True,
        download_name=f"منهج_تدريبي_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )


@app.route('/api/curriculum/chat', methods=['POST'])
def curriculum_chat():
    """Chat using RAG over the generated curriculum with conversation history"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        curriculum_id = data.get('curriculum_id', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Check if we have RAG data for this curriculum
        if not curriculum_id or curriculum_id not in curriculum_rag_data:
            return jsonify({
                'response': 'لم يتم العثور على منهج. يرجى رفع ملف PDF أولاً وانتظار اكتمال المعالجة.',
                'status': 'success'
            })
        
        # Initialize chat history for this curriculum if not exists
        if curriculum_id not in curriculum_chat_history:
            curriculum_chat_history[curriculum_id] = [
                {
                    "role": "system",
                    "content": "أنت مساعد خبير في المناهج التعليمية. استخدم المعلومات المقدمة من المنهج للإجابة على أسئلة المستخدم. احتفظ بسياق المحادثة واربط الإجابات بالأسئلة السابقة عند الحاجة."
                }
            ]
        
        # Get RAG data
        rag_data = curriculum_rag_data[curriculum_id]
        index = rag_data['index']
        chunks = rag_data['chunks']
        
        # Encode the query
        query_embedding = embedding_model.encode([message])
        
        # Search for top 3 most relevant chunks
        D, I = index.search(np.array(query_embedding).astype('float32'), k=3)
        
        # Retrieve relevant chunks
        retrieved_chunks = []
        for idx in I[0]:
            if 0 <= idx < len(chunks):
                retrieved_chunks.append(chunks[idx])
        
        context = "\n\n".join(retrieved_chunks)
        
        # Create prompt with context and conversation history
        user_prompt = f"""المعلومات ذات الصلة من المنهج:
{context}

سؤال المستخدم: {message}"""
        
        # Add user message to history
        curriculum_chat_history[curriculum_id].append({
            "role": "user",
            "content": user_prompt
        })
        
        # Keep only last 10 messages to avoid token limits (plus system message)
        if len(curriculum_chat_history[curriculum_id]) > 21:  # 1 system + 10 user/assistant pairs
            # Keep system message and last 10 exchanges
            curriculum_chat_history[curriculum_id] = [curriculum_chat_history[curriculum_id][0]] + curriculum_chat_history[curriculum_id][-20:]
        
        # Call OpenAI with conversation history
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=curriculum_chat_history[curriculum_id],
            temperature=0.7,
            max_tokens=2000
        )
        
        bot_response = response.choices[0].message.content
        
        # Add assistant response to history
        curriculum_chat_history[curriculum_id].append({
            "role": "assistant",
            "content": bot_response
        })
        
        return jsonify({
            'response': bot_response,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500
    
           
if __name__ == '__main__':
    app.run(debug=True)