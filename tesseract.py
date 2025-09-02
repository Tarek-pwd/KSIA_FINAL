from pdf2image import convert_from_path
import cv2
import numpy as np
import pytesseract
import ast
import openai
from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import json
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai = OpenAI(api_key=api_key)
all_words = []
keys_of_interest = ['block_num','left','top','width','height' ,'text']
def plot_boxes(curr_elem_idx,img):
    for elem in all_words[curr_elem_idx:]:
        pt1 = (elem['left'], elem['top'])
        pt2 = (elem['left'] + elem['width'] , elem['top'] + elem['height'])
        cv2.rectangle(img, pt1, pt2, (0,255,0), 1)

def show_img(img):
    while True:
        cv2.namedWindow("PDF Page", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("PDF Page", 800, 600)
        cv2.imshow("PDF Page", img)
        if cv2.waitKey(1) == 27:
            break
    cv2.destroyAllWindows() 


    
def ask_llm(content):
    print("got content " , content)
    response = openai.chat.completions.create(
        model="gpt-4o",  
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert signature detection assistant. "
                    "A detection model has already been run to find a signature, "
                    "but it likely failed because the signature looks more like a regular handwritten name "
                    "rather than a typical signature. "
                    "You are provided with OCR-extracted text and bounding box data from the document. "
                    "Your task is to analyze the flow of the text in the document and determine "
                    "the most probable bounding box coordinates where the signature is located."
                    "with that i mean you shoould look for the word signature or something that means that there is a signature coming such as 'i hereby acknowledge that ...' in such case make the boundning box the last word of the statement"
                    "the signature will probably be in one or more pages but not all or many pages."
                    "the output should only be the page number and the bounding box coordinates as an array [pagenum , xmin, ymin , xmax, ymax]."
                    "you should output  nothing but an array of arrays containing [pagenum , xmin, ymin , xmax, ymax] "
                    "DO NOT INCLUDE ANYTHING IN THE OUTpUT EXCEPT AN ARRAY OF ARRAYS this is strict"
                )
            },
            {
                "role": "user",
                "content": f'Here is the outputof the OCR {content} '
            }
        ]
    )
    return response.choices[0].message.content


def box_to_point(top_left, bottom_right):
    xmin = top_left[0]
    ymin = top_left[1]
    xmax = bottom_right[0]
    ymax = bottom_right[1]
    width = xmax - xmin
    height = ymax - ymin 
    xfinal = xmin + width//2
    yfinal = ymin + height//2

    return (xfinal,yfinal)


def find_nearest_box(points,sig):
    mini = float('inf')
    mini_idx = float('inf')
    for idx , point in enumerate(points):
        euclidean_distance = abs(point[0] - sig[0] ) **2  + abs(point[1] - sig[1])**2
        if euclidean_distance < mini:
            mini = euclidean_distance
            mini_idx = idx
    print("returning index " , mini_idx)
    return mini_idx
image_exts= ['.jpg', '.png', '.jpeg']
def check_context(text_arr,pdf_file):
    final_llm_res  = []
    if pdf_file.endswith('.pdf'):
        print("converting pdf file to images >> ")
        images = convert_from_path(pdf_file)
        curr_elem_idx = 0
        for idx, image in enumerate(images):
            img = np.array(image)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            for i in range(len(data['level'])):
                curr_word = {}
                for j in keys_of_interest:
                    curr_word[j] = data[j][i]
                curr_word['page_num'] = idx + 1
                all_words.append(curr_word)
            #plot_boxes(curr_elem_idx , img)
            #show_img(img)
            curr_elem_idx+=len(data['level'])
    ##print(all_words)
        final_res = ask_llm(content=all_words)
        print("Raw LLM output:", final_res)

        # Remove any characters before or after the array
        match = re.search(r'\[\s*\[.*\]\s*\]', final_res.replace('\n',''))
        if match:
            final_res_clean = match.group(0)
            final_res = ast.literal_eval(final_res_clean)
        else:
            final_res = []

        print("Parsed array:", final_res)
        print("parsed ARRAY TYPE" ,  type(final_res))
        box_points_arr = []

        for elem in final_res:
            sig = box_to_point((elem[1],elem[2]),(elem[3],elem[4]))
            llm_page =  elem[0]
            print("LLM POTENTIAL page >> ",llm_page)
            text_boxes = text_arr[llm_page]
            for i in  text_boxes:
                box_points_arr.append(box_to_point(i[0],i[1]))

            if box_points_arr:
                idx = find_nearest_box(box_points_arr,sig)
                print('closest to llm ====  ' ,text_boxes[idx])
                final_llm_res.append((llm_page,idx))
        return final_llm_res
















                
                



                
            

            
            

                
        
            

        

        

        

