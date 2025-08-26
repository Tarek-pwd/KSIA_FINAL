import cv2
import numpy as np
import json
import ezdxf
from ultralytics import YOLO
import os
def run_full_analysis(image_path, dxf_path):

    print("calllllllllllllllled ")
    seg_model = YOLO("best-3.pt")
    det_model = YOLO("final_detection.pt")

    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]

    seg_result = seg_model(image_path)[0]
    det_result = det_model(image_path)[0]

    room_masks_raw = seg_result.masks.data.cpu().numpy()
    room_masks = [cv2.resize(mask, (img_w, img_h), interpolation=cv2.INTER_NEAREST) > 0.5 for mask in room_masks_raw]
    room_boxes = seg_result.boxes.xyxy.cpu().numpy()
    room_classes = seg_result.boxes.cls.cpu().numpy()
    room_names = seg_model.names

    symbol_boxes = det_result.boxes.xyxy.cpu().numpy()
    symbol_classes = det_result.boxes.cls.cpu().numpy()
    symbol_names = det_model.names

    def find_dxf_bbox():
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        for entity in msp:
            if entity.dxftype() == "LINE":
                start, end = entity.dxf.start, entity.dxf.end
                x1, y1 = start[0], start[1]
                x2, y2 = end[0], end[1]
                min_x = min(min_x, x1, x2)
                min_y = min(min_y, y1, y2)
                max_x = max(max_x, x1, x2)
                max_y = max(max_y, y1, y2)
            elif entity.dxftype() == "LWPOLYLINE":
                for point in entity.get_points():
                    x, y = point[0], point[1]
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        return (min_x, min_y), (max_x, max_y)

    def image_to_dxf_coords(x_img, y_img, width, height, min_x, min_y, max_x, max_y):
        norm_x = x_img / width
        norm_y = 1 - (y_img / height)
        x_dxf = min_x + norm_x * (max_x - min_x)
        y_dxf = min_y + norm_y * (max_y - min_y)
        return (x_dxf, y_dxf)

    def mask_to_polygon(mask):
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            return contours[0][:, 0, :]
        return []

    (min_x, min_y), (max_x, max_y) = find_dxf_bbox()

    room_summary = {}
    dxf_room_summary = {}

    for i, (mask, box, room_cls) in enumerate(zip(room_masks, room_boxes, room_classes)):
        room_id = f"room_{i+1}"
        contained_symbols = []

        for sym_box, sym_cls in zip(symbol_boxes, symbol_classes):
            xmin, ymin, xmax, ymax = map(int, sym_box)
            cx = (xmin + xmax) // 2
            cy = (ymin + ymax) // 2
            if 0 <= cy < mask.shape[0] and 0 <= cx < mask.shape[1] and mask[cy, cx]:
                contained_symbols.append({
                    "symbol_class": symbol_names[int(sym_cls)],
                    "bbox": [xmin, ymin, xmax, ymax],
                    "center": [cx, cy]
                })

        symbols_in_room = [s["symbol_class"] for s in contained_symbols]
        room_type = "unknown"
        if any(sym in symbols_in_room for sym in ["kitchen_sink", "hob"]):
            room_type = "kitchen"
        elif any(sym in symbols_in_room for sym in ["toilet", "bathtub", "bathroom_sink"]):
            room_type = "bathroom"
        elif any(sym in symbols_in_room for sym in ["bed"]):
            room_type = "bedroom"
        elif any(sym in symbols_in_room for sym in ["car"]):
            room_type = "garage"
        elif any(sym in symbols_in_room for sym in ["sofa"]):
            room_type = "living_room"
        elif any(sym in symbols_in_room for sym in ["dining_table"]):
            room_type = "dining_room--reception"

        doors = [s for s in contained_symbols if s["symbol_class"] == "door"]

        room_summary[room_id] = {
            "room_class": room_names[int(room_cls)],
            "room_type": room_type,
            "room_bbox": list(map(int, box)),
            "contained_symbols": contained_symbols,
            "doors": doors
        }

        polygon = mask_to_polygon(mask)
        dxf_polygon = [image_to_dxf_coords(x, y, img_w, img_h, min_x, min_y, max_x, max_y) for x, y in polygon]
        xs, ys = zip(*dxf_polygon) if dxf_polygon else ([0], [0])
        dxf_bbox = [min(xs), min(ys), max(xs), max(ys)]

        dxf_contour = np.array(dxf_polygon, dtype=np.float32).reshape(-1, 1, 2)
        room_area = cv2.contourArea(dxf_contour)

        dxf_symbols = []
        for s in contained_symbols:
            x1, y1, x2, y2 = s["bbox"]
            cx, cy = s["center"]
            p1 = image_to_dxf_coords(x1, y1, img_w, img_h, min_x, min_y, max_x, max_y)
            p2 = image_to_dxf_coords(x2, y2, img_w, img_h, min_x, min_y, max_x, max_y)
            height = abs(p2[1]-p1[1])
            width = abs(p2[0]-p1[0])
            sym_contour = np.array([
                [p1[0], p1[1]],
                [p2[0], p1[1]],
                [p2[0], p2[1]],
                [p1[0], p2[1]]
            ], dtype=np.float32).reshape(-1, 1, 2)
            symbol_area = cv2.contourArea(sym_contour)
            dxf_symbols.append({
                "symbol_class": s["symbol_class"],
                "dxf_bbox": [*p1, *p2],
                "dxf_center": image_to_dxf_coords(cx, cy, img_w, img_h, min_x, min_y, max_x, max_y),
                "area": symbol_area,
                "height" : height,
                "width" : width
                
                
            })

        dxf_doors = [s for s in dxf_symbols if s["symbol_class"] == "door"]

        dxf_room_summary[room_id] = {
            "room_class": room_names[int(room_cls)],
            "room_type": room_type,
            "room_dxf_bbox": dxf_bbox,
            "room_dxf_polygon": dxf_polygon,
            "room_area": room_area,
            "contained_symbols": dxf_symbols,
            "doors": dxf_doors
        }

    with open("room_summary_image_coords.json", "w") as f:
        json.dump(room_summary, f, indent=2)

    with open("room_summary_dxf_coords.json", "w") as f:
        json.dump(dxf_room_summary, f, indent=2)

    print("✅ Analysis complete.")

    os.makedirs("output", exist_ok=True)
    with open("output/room_summary.json", "w") as f:
        json.dump(dxf_room_summary, f, indent=2)
