import openai
from PyPDF2 import PdfReader
import time
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from dotenv import load_dotenv
import os
load_dotenv()


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def extract_and_chunk_pdf(pdf_path, pages_per_chunk=3):
    """
    Extract PDF in small chunks for MAXIMUM detail.
    """
    print(f"📖 Opening PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"📄 Total pages: {total_pages}")
   
    chunks = []
   
    for i in range(0, total_pages, pages_per_chunk):
        chunk_pages = []
        end = min(i + pages_per_chunk, total_pages)
       
        print(f"📦 Creating chunk from pages {i+1} to {end}")
       
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
   
    print(f"✅ Created {len(chunks)} chunks")
    return chunks, total_pages

def generate_mega_curriculum(chunks, total_pages, model="gpt-4o"):
    """
    Generate MASSIVE, DETAILED curriculum - 20% of original length!
    """
    # Calculate how much content we need per chunk
    target_output_pages = total_pages * 0.2  # 20% of original
    pages_per_chunk = target_output_pages / len(chunks)
    words_per_chunk = int(pages_per_chunk * 500)  # ~500 words per page
   
    print(f"\n🎯 Target: {target_output_pages:.0f} output pages from {total_pages} input pages")
    print(f"📝 Each chunk should generate ~{words_per_chunk} words")
   
    curricula = []
    total = len(chunks)
   
    print(f"\n🤖 Generating DETAILED curriculum for {total} chunks...")
   
    for idx, chunk_data in enumerate(chunks):
        chunk = chunk_data['text']
        start_page = chunk_data['start_page']
        end_page = chunk_data['end_page']
       
        print(f"\n📝 Processing pages {start_page}-{end_page} (chunk {idx+1}/{total})")
       
        # MEGA DETAILED PROMPT
        prompt = f"""
أنت خبير في تطوير المناهج التدريبية العسكرية. مهمتك هي تحويل النص التالي إلى منهج تدريبي مفصل للغاية.

⚠️ مهم جداً: يجب أن يكون المنهج طويل جداً ومفصل للغاية!
📏 الطول المطلوب: {words_per_chunk} كلمة على الأقل (حوالي {pages_per_chunk:.1f} صفحة)

المطلوب في المنهج:
1. عنوان الوحدة التدريبية
2. الأهداف التعليمية التفصيلية (10-15 هدف)
3. المحتوى النظري المفصل جداً
   - شرح مفصل لكل مفهوم
   - أمثلة متعددة
   - حالات دراسية
   - رسوم توضيحية (وصف مفصل)
4. التطبيقات العملية
   - تمارين تفصيلية خطوة بخطوة
   - سيناريوهات تدريبية كاملة
   - تدريبات ميدانية
5. طرق التقييم
   - أسئلة نظرية (20+ سؤال)
   - تمارين عملية
   - معايير التقييم التفصيلية
6. الجدول الزمني التفصيلي
   - توزيع الساعات
   - الأنشطة لكل ساعة
7. المصادر والمراجع
8. ملاحظات للمدرب

⚠️ تذكر: اكتب بأكبر قدر ممكن من التفصيل! لا تختصر أبداً!
كل نقطة يجب شرحها في فقرات متعددة، ليس مجرد نقاط.

النص المصدر:
{chunk}
"""
       
        try:
            # Use higher token limit for massive output
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "أنت خبير في كتابة المناهج التدريبية المفصلة للغاية. تكتب محتوى طويل جداً ومفصل، ولا تختصر أبداً. هدفك هو إنتاج أكبر قدر ممكن من المحتوى التعليمي المفيد."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096  # Maximum possible
            )
           
            curriculum = response.choices[0].message.content
           
            # Check if we need more content
            word_count = len(curriculum.split())
            if word_count < words_per_chunk * 0.8:  # If less than 80% of target
                print(f"  ⚠️ Only got {word_count} words, requesting more...")
               
                # Second request for more detail
                expansion_prompt = f"""
المنهج السابق جيد، لكن نحتاج المزيد من التفصيل!

أضف المزيد من:
1. شرح أعمق لكل مفهوم (فقرات إضافية)
2. المزيد من الأمثلة التطبيقية (10+ مثال)
3. تمارين إضافية مفصلة
4. سيناريوهات تدريبية إضافية
5. جداول ونماذج تقييم مفصلة
6. خطط الدروس اليومية

المطلوب: {words_per_chunk - word_count} كلمة إضافية على الأقل!

المنهج الحالي:
{curriculum}
"""
               
                response2 = openai.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "أضف المزيد من التفاصيل والمحتوى. اكتب أطول قدر ممكن!"},
                        {"role": "user", "content": expansion_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096
                )
               
                curriculum += "\n\n" + response2.choices[0].message.content
           
            # Format nicely
            formatted_curriculum = f"""
{'='*80}
📚 الوحدة التدريبية: الصفحات {start_page} إلى {end_page}
{'='*80}

{curriculum}

{'='*80}
📊 إحصائيات الوحدة:
- عدد الكلمات: {len(curriculum.split())}
- الصفحات المقدرة: {len(curriculum.split())/500:.1f}
{'='*80}

"""
            curricula.append(formatted_curriculum)
            print(f"  ✅ Generated {len(curriculum.split())} words!")
           
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            curricula.append(f"\n[خطأ في معالجة الصفحات {start_page}-{end_page}]\n")
       
        # Small delay to avoid rate limits
        time.sleep(1)
   
    return "".join(curricula)

def create_mega_curriculum(pdf_path, output_file="mega_curriculum.txt", pages_per_chunk=3):
    """
    Create a MASSIVE curriculum that's 20% of the book length.
    """
    start_time = time.time()
   
    print("📚 MEGA CURRICULUM GENERATOR")
    print("="*80)
    print("🎯 Goal: Generate curriculum that's 20% of original book length")
    print("="*80)
   
    # Extract and chunk
    chunks, total_pages = extract_and_chunk_pdf(pdf_path, pages_per_chunk=pages_per_chunk)
   
    # Calculate expected output
    expected_output_pages = total_pages * 0.2
    expected_words = expected_output_pages * 500
   
    print(f"\n📊 Book Statistics:")
    print(f"  - Input pages: {total_pages}")
    print(f"  - Target output: {expected_output_pages:.0f} pages (~{expected_words:,} words)")
    print(f"  - Chunks to process: {len(chunks)}")
    print(f"  - Estimated cost: ${len(chunks) * 0.10:.2f}")
   
    # Warning for cost
    if len(chunks) > 20:
        print(f"\n⚠️ WARNING: This will make {len(chunks)} API calls!")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            return
   
    # Generate mega curriculum
    full_curriculum = generate_mega_curriculum(chunks, total_pages)
   
    # Add comprehensive header
    header = f"""
{'='*80}
منهج تدريبي شامل ومفصل
{'='*80}

📖 الكتاب المصدر: {pdf_path}
📅 تاريخ الإعداد: {time.strftime('%Y-%m-%d %H:%M')}
📄 عدد صفحات الكتاب: {total_pages}
📝 عدد صفحات المنهج المستهدف: {expected_output_pages:.0f} ({expected_words:,} كلمة)
📊 نسبة التفصيل: 20% من حجم الكتاب الأصلي

{'='*80}

فهرس المحتويات:
"""
   
    # Add table of contents
    for i, chunk in enumerate(chunks):
        header += f"\n{i+1}. الوحدة التدريبية {i+1}: الصفحات {chunk['start_page']}-{chunk['end_page']}"
   
    header += f"\n\n{'='*80}\n\n"
   
    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header + full_curriculum)
   
    # Calculate actual output
    total_words = len(full_curriculum.split())
    total_output_pages = total_words / 500
   
    elapsed = time.time() - start_time
    print(f"\n✅ MEGA CURRICULUM COMPLETED!")
    print(f"📊 Final Statistics:")
    print(f"  - Processing time: {elapsed/60:.1f} minutes")
    print(f"  - Total words generated: {total_words:,}")
    print(f"  - Total pages generated: {total_output_pages:.1f}")
    print(f"  - Compression ratio: {(total_output_pages/total_pages)*100:.1f}%")
    print(f"📄 Output saved to: {output_file}")

    print("returning all NOW!")
    return header + full_curriculum

def chunk_summary(text, chunk_size=300, overlap=100):
    """
    Fixed chunking function with proper encoding handling
    """
    chunks = []
    # Split by words instead of characters for better Arabic handling
    words = text.split()
    total_words = len(words)
    
    for i in range(0, total_words, chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk = ' '.join(chunk_words)
        chunks.append(chunk)
        print(f"Created chunk {len(chunks)}: {len(chunk_words)} words")
    
    return chunks

def add_message(content, role):
    """
    Add message to conversation history
    """
    message = {'role': role, 'content': content}
    messages.append(message)
    print(f"Added {role} message to conversation")

def query_rag(user_query, embedding_model, index, chunks, chat_model='gpt-4o', top_k=3):
    """
    Fixed RAG query function with proper encoding and error handling
    """
    try:
        # Encode the query
        print(f"Encoding query: {user_query}")
        query_embedding = embedding_model.encode([user_query])
        
        # Search in FAISS index
        D, I = index.search(np.array(query_embedding).astype('float32'), top_k)
        
        # Retrieve chunks
        retrieved_chunks = []
        for idx in I[0]:
            if 0 <= idx < len(chunks):
                retrieved_chunks.append(chunks[idx])
        
        context = "\n\n".join(retrieved_chunks)
        
        # Create prompt
        prompt = f"""استخدم المعلومات التالية للإجابة على السؤال:

السؤال: {user_query}

المعلومات ذات الصلة:
{context}

الرجاء تقديم إجابة شاملة ومفصلة."""
        
        add_message(prompt, 'user')
        
        # Get response from OpenAI
        response = openai.chat.completions.create(
            model=chat_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        model_output = response.choices[0].message.content
        add_message(model_output, 'assistant')
        
        return model_output
        
    except Exception as e:
        print(f"Error in query_rag: {str(e)}")
        return f"حدث خطأ: {str(e)}"

# Initialize conversation history
messages = [
    {
        "role": "system",
        "content": "أنت مساعد خبير في الإجابة على أسئلة المستخدم المتعلقة بكتاب معين. يتم استخدام RAG وستحصل على الأجزاء التي تطابق استعلام المستخدم. قدم إجابات شاملة ومفصلة باللغة العربية."
    }
]

# Main execution
if __name__ == "__main__":
    try:
        # Read the curriculum file with proper encoding
        print("Reading curriculum file...")
        with open('military_training_mega_curriculum.txt', 'r', encoding='utf-8') as f:
            my_text = f.read()
        
        print(f"File loaded successfully. Length: {len(my_text)} characters")
        
        # Create chunks
        print("\nCreating chunks...")
        chunks = chunk_summary(my_text, chunk_size=500, overlap=100)
        print(f"Created {len(chunks)} chunks")
        
        # Use a multilingual model that supports Arabic
        print("\nLoading embedding model...")
        # Options for Arabic support:
        # 1. multilingual model
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        # 2. Or use: 'sentence-transformers/distiluse-base-multilingual-cased-v2'
        
        # Create embeddings
        print("Creating embeddings...")
        chunk_embeddings = model.encode(chunks, show_progress_bar=True)
        
        # Create FAISS index
        print("\nCreating FAISS index...")
        dimension = chunk_embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(chunk_embeddings).astype('float32'))
        
        print(f"Index created with {index.ntotal} vectors")
        
        # Example queries
        test_queries = [
            'أهمية الأمن السيبراني في العصر',
            'التدريبات العسكرية',
            'الأهداف التعليمية'
        ]
        
        # Test the RAG system
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print('='*80)
            result = query_rag(query, model, index, chunks)
            print(f"Response:\n{result}")
            
    except FileNotFoundError:
        print("Error: Could not find 'military_training_mega_curriculum.txt'")
        print("Please make sure the file exists in the current directory")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()