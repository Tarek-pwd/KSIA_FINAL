from pdf2image import convert_from_path
import cv2
import matplotlib.pyplot as plt
import numpy as np
print("some importa have been made ! ")
from ultralytics import YOLO
from collections import defaultdict
from run_extraction import run_extraction
from tesseract import check_context
 
def view_image(image,title,mask = False):
    if not mask:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    plt.imshow(image,cmap = 'gray')
    plt.axis('off')
    plt.title(f"page  {title}") 
    plt.show()

def add_label(img,text,x,y):
    fontFace = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1.5
    color = (255, 0 ,0)  # Green color (BGR)
    thickness = 2
    lineType = cv2.LINE_AA
    org = (x,y)
    cv2.putText(img, text, org, fontFace, fontScale, color, thickness, lineType)

            #cropped_with_sig = img[int(xyxy[1]):int(xyxy[3]), int(xyxy[0]):int(xyxy[2])]
            #view_image(cropped_with_sig,'cropped image')
            ##### will need the  page number in the image too as well as the signature bbox to crop #####

