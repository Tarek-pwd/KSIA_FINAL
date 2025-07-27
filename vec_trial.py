import os
import json
import requests
from docx import Document
from dotenv import load_dotenv
load_dotenv()
# ========== CONFIGURATION ==========

VECTARA_API_KEY = os.getenv('VECTARA_API_KEY')
VECTARA_CUSTOMER_ID = "3685563981"
VECTARA_CORPUS_KEY = "autocad_demo"
VECTARA_UPLOAD_ENDPOINT = f"https://api.vectara.io/v2/corpora/{VECTARA_CORPUS_KEY}/upload_file"
VECTARA_QUERY_ENDPOINT = f"https://api.vectara.io/v2/query"

JSON_INPUT_FILE = "output/room_summary.json"
TEXT_OUTPUT_FILE = "described_rooms.txt"
DOCX_OUTPUT_FILE = "described_rooms.docx"

# ========== STEP 1: Describe Rooms ==========
def describe_rooms(json_data):
    output = []
    room_count = 0

    for room_name, room_info in json_data.items():
        room_count += 1
        room_lines = []

        room_type = room_info.get("room_type", "unknown")
        area = room_info.get("room_area", 0)
        bbox = room_info.get("room_dxf_bbox", [])
        symbols = room_info.get("contained_symbols", [])
        doors = room_info.get("doors", [])

        room_lines.append(f"=== {room_name.upper()} ===")
        room_lines.append(f"- Type: {room_type.replace('_', ' ').title()}")
        room_lines.append(f"- Area: {area:.2f} square units")
        if bbox:
            room_lines.append(f"- Bounding Box: ({bbox[0]:.2f}, {bbox[1]:.2f}) to ({bbox[2]:.2f}, {bbox[3]:.2f})")

        if symbols:
            room_lines.append(f"- Contains {len(symbols)} symbol(s):")
            for sym in symbols:
                sym_class = sym["symbol_class"]
                width = sym["width"]
                height = sym["height"]
                sym_area = sym["area"]
                sym_center = sym["dxf_center"]
                room_lines.append(f"  • {sym_class} at {tuple(map(lambda x: round(x, 2), sym_center))}, area: {sym_area:.2f}")
                room_lines.append(f"width : {width} height : {height}" ) 
        else:
            room_lines.append("- Contains no symbols")

        if doors:
            room_lines.append("- Doors:")
            for door in doors:
                door_center = door.get("dxf_center", [])
                room_lines.append(f"  • Door at {tuple(map(lambda x: round(x, 2), door_center))}")
        else:
            room_lines.append("- No doors listed")

        output.append("\n\n\n".join(room_lines))

    output.append(f"Abatement:\nThe total number of rooms detected in this house is {room_count}.")
    return output

# ========== STEP 2: Convert to DOCX ==========
def convert_to_docx(blocks, output_docx_path):
    doc = Document()
    for block in blocks:
        doc.add_paragraph(block)
        doc.add_paragraph("")  # space between blocks
    doc.save(output_docx_path)
    print(f"✅ DOCX saved to: {output_docx_path}")

# ========== STEP 3: Upload DOCX ==========
def upload_docx_to_vectara(docx_path):
    with open(docx_path, "rb") as f:
        files = {
            "file": (os.path.basename(docx_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "metadata": (None, '{"uploaded_by":"room_bot"}', "application/json")
        }
        headers = {"x-api-key": VECTARA_API_KEY}
        response = requests.post(VECTARA_UPLOAD_ENDPOINT, files=files, headers=headers)
    print("📤 Upload status:", response.status_code)
    print(response.text)
    return response.status_code, response.text

# ========== STEP 4: Query Vectara ==========

  
def query_vectara(query):
    write_vectara()
    print("hereeeeeee called")
    url = "https://api.vectara.io/v2/corpora/autocad_demo/query"
    prompt_template = [
        {
        "role": "system",
        "content": (
            "You are a smart assistant that helps users understand objects and layout of rooms detected in an AutoCAD floor plan.\n"
            "Be concise and helpful. Mention what room it is, what it contains, and its position if asked.\n"
            "DO NOT fabricate information.\n STRICTLY DO NOT EXCEED 60 words (this is important). Follow these step-by-step instructions to answer the question: '$esc.java($vectaraQuery)' in the '$vectaraLangName' language using only the search results and metadata provided.\n\n"
            "Step 1 - Each search result is enclosed in triple quotes and may include metadata fields like 'title', 'document_type', 'tags', 'description', and 'id'.\n"
            "Step 2 - Understand the employee's question and identify its scope (e.g., whether it's about environmental policy, procurement guidelines, human rights, or safety procedures).\n"
            "Step 3 - Only use content from documents relevant to the question's topic. Match based on context and document metadata.\n"
            "Step 4 - If the search results do not contain relevant information, respond in '$vectaraLangName' stating that no sufficient information is available.\n"
            "Step 5 - If there is relevant content, provide a brief, accurate answer (maximum $vectaraOutChars characters).\n"
            "Step 6 - Ensure that your answer is concise (no more than four sentences), grammatically correct, and tailored for internal bank use.\n"
            "Step 7 - Use only the information in the search results. Do not assume, guess, or generate answers beyond what is provided.\n"
            "Step 8 - Cite supporting content using this format: '$vectaraCitationInstructions'.\n"
            "Step 9 - Do not refer to metadata, source documents, or the process of searching in your answer.\n"
            "Step 10 - If multiple documents mention the same policy area (e.g., ESG), synthesize their content where relevant, but be precise.\n"
            "Step 11 - If the question asks about a specific document (e.g., ISO 14001, CSR policy), limit the response to that document only.\n"
            "Step 12 - If the context requires prioritization, prefer documents that are more recent or have highly relevant metadata tags.\n"
            "Step 13 - Always align the response content with the metadata provided for each result, and base your logic on the 'id' field if applicable.\n"
            "Step 14 - Just repond to the question from the search results. Do not at any circumestance reply from outside the search result."
            )
        },
        {
            "role": "user",
            "content": "#foreach ($qResult in $vectaraQueryResults) Search Result $esc.java($foreach.index + 1): '''$esc.java($qResult.text())'''.#end"
        }
    ]

 
    payload = json.dumps({
 
    "query": query,

    "search": {
        "custom_dimensions": {},
        "metadata_filter": "",
        "lexical_interpolation": 0.0075,
        "offset": 0,
        "limit": 10,
        "context_configuration": {
        "sentences_before": 2,
        "sentences_after": 2,
        "start_tag": "%START_SNIPPET%",
        "end_tag": "%END_SNIPPET%"
 
        },
 
        "reranker": {

        "type": "customer_reranker",
        "reranker_id": "rnk_272725719"
        }
 
    },
 
    "generation": {
 
        "generation_preset_name": "vectara-summary-ext-v1.3.0",
        "prompt_template": json.dumps(prompt_template),
        "max_used_search_results": 2,
        "response_language": "eng",
        "enable_factual_consistency_score": True
 
    },
 
        "stream_response": True,
        "save_history": True,
        "intelligent_query_rewriting": False
 
    })
 
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'x-api-key': VECTARA_API_KEY
    }
 
    
    response = requests.post(url, headers=headers, data=payload, stream=True)
 
    print("Streaming response...\n")
 
    collected = ""
    
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data:"):
                data_json = decoded.replace("data:", "").strip()
                try:
                    data = json.loads(data_json)
                    chunk = data.get("generation_chunk", "")
                   ## print("chunk is ", chunk)
                   ## print( chunk, end='', flush=True)
                    yield chunk
                    collected += chunk
                except json.JSONDecodeError:
                    print(f"[error parsing JSON] {data_json}")
 
    print("\n\n✅ Finished streaming.")
    return collected




def query_vectara_check_violations(query):
    write_vectara()
    print("hereeeeeee called")
    print("check violations called ")
    print("reqs file  >>", query)
    url = "https://api.vectara.io/v2/corpora/autocad_demo/query"
    prompt_template = [
        {
        "role": "system",
        "content": (
           "You are an Expert room data violation assistant you are given with a file contaning some requirements which is the RULES_FILE you should compare every single rule you have in that file to the data that you have of the detections and yield a statement that summarizes if there is a violation by anymeans of that rule.\n"
            "THE RULES_FILE is the one you are given in the query "
            "THE RULES_FILE is the file that I will give you ina  bit in the query and it should be compared agianst the described_rooms.docx file that you have in the corpus. The file int he corpus is the actual detections that was present in the apartmentand i WANT you to compare the  detections against the RULES_FILE to know if the apartment complies with the RULES "
            "For EVERY SINGLE requirement in the REQUIREMENTS_FILE, you MUST provide a compliance check in the following EXACT format:\n\n"
            "REQUIREMENT: [Name of the requirement]\n"
            "STATUS: [PASS/VIOLATION/UNCLEAR]\n"
            "REASON: [Brief explanation why it passed/failed/unclear]\n"
            "---\n\n"
            "Guidelines:\n"
            "1. Check EVERY requirement mentioned in the REQUIREMENTS_FILE\n"
            "2. Use STATUS: PASS if the requirement is met\n"
            "3. Use STATUS: VIOLATION if the requirement is not met\n"
            "4. Use STATUS: UNCLEAR if you cannot determine compliance\n"
            "5. Keep REASON brief and specific\n"
            "6. Always use the exact format above with '---' as separator\n"
            "7. Do not add any text outside this format\n\n"
           
           
        )
        },
        {
            "role": "user",
            "content": "#foreach ($qResult in $vectaraQueryResults) Search Result $esc.java($foreach.index + 1): '''$esc.java($qResult.text())'''.#end"
        }
    ]

    payload = json.dumps({
        "query": query,
        "search": {
            "custom_dimensions": {},
            "metadata_filter": "",
            "lexical_interpolation": 0.0075,
            "offset": 0,
            "limit": 10,
            "context_configuration": {
                "sentences_before": 2,
                "sentences_after": 2,
                "start_tag": "%START_SNIPPET%",
                "end_tag": "%END_SNIPPET%"
            },
            "reranker": {
                "type": "customer_reranker",
                "reranker_id": "rnk_272725719"
            }
        },
        "generation": {
            "generation_preset_name": "vectara-summary-ext-v1.3.0",
            "prompt_template": json.dumps(prompt_template),
            "max_used_search_results": 10,  # Increased to get more comprehensive results
            "response_language": "eng",
            "enable_factual_consistency_score": True
        },
        "stream_response": True,
        "save_history": False,
        "intelligent_query_rewriting": False
    })
 
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'x-api-key': VECTARA_API_KEY
    }
    
    response = requests.post(url, headers=headers, data=payload, stream=True)
    print("Streaming response...\n")
    
    collected = ""
    
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data:"):
                data_json = decoded.replace("data:", "").strip()
                try:
                    data = json.loads(data_json)
                    chunk = data.get("generation_chunk", "")
                    yield chunk
                    collected += chunk
                except json.JSONDecodeError:
                    print(f"[error parsing JSON] {data_json}")
    
    print("\n\n✅ Finished streaming.")
    return collected
    

    


# ========== MAIN ==========
def write_vectara():
    with open(JSON_INPUT_FILE, "r", encoding="utf-8") as f:
        room_data = json.load(f)
    blocks = describe_rooms(room_data)
    with open(TEXT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks))
    print(f"✅ Text saved to: {TEXT_OUTPUT_FILE}")
    convert_to_docx(blocks, DOCX_OUTPUT_FILE)
    upload_docx_to_vectara(DOCX_OUTPUT_FILE)
    print("uploaded to vectara " + DOCX_OUTPUT_FILE)
   
    

    
    
