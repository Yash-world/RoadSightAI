from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import cv2
from ultralytics import YOLO
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

model = YOLO("yolov8s.pt")

VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

@app.route("/")
def index():
    return render_template("index.html")


# ================= VIDEO =================
@app.route("/upload", methods=["POST"])
def upload_video():
    file = request.files.get("video")

    if not file:
        return jsonify({"error": "No video uploaded"}), 400

    filename = secure_filename(file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(video_path)

    output_path = os.path.join(OUTPUT_FOLDER, "output.mp4")

    result = process_video(video_path, output_path)

    return jsonify({**result, "video_url": "/output/output.mp4"})


def process_video(video_path, output_path):
    cap = cv2.VideoCapture(video_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 25

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    unique_ids = set()

    # ✅ FIX: unique tracking per class
    class_counts = {
        "car": set(),
        "motorcycle": set(),
        "bus": set(),
        "truck": set()
    }

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        resized = cv2.resize(frame, (640, 640))
        results = model.track(resized, conf=0.3, iou=0.5, persist=True)

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                cls = int(box.cls[0])

                if cls in VEHICLE_CLASSES:
                    label = VEHICLE_CLASSES[cls]

                    if box.id is not None:
                        obj_id = int(box.id[0])
                        unique_ids.add(obj_id)
                        class_counts[label].add(obj_id)

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    x1 = int(x1 * width / 640)
                    x2 = int(x2 * width / 640)
                    y1 = int(y1 * height / 640)
                    y2 = int(y2 * height / 640)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 255, 0), 2)

        total = len(unique_ids)

        cv2.putText(frame, f"Total: {total}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 0, 0), 3)

        out.write(frame)

    cap.release()
    out.release()

    total = len(unique_ids)

    # ✅ FIX: better density
    density = min(100, int((total / 20) * 100))

    if total <= 5:
        status = "LOW"
        green_time = 10
        risk = "SAFE"
    elif total <= 15:
        status = "MEDIUM"
        green_time = 20
        risk = "ALERT"
    else:
        status = "HIGH"
        green_time = 40
        risk = "DANGER"

    return {
        "total": total,
        "cars": len(class_counts["car"]),
        "bikes": len(class_counts["motorcycle"]),
        "bus": len(class_counts["bus"]),
        "truck": len(class_counts["truck"]),
        "density": density,
        "traffic_status": status,
        "green_time": green_time,
        "risk": risk
    }


# ================= IMAGE =================
@app.route("/upload_image", methods=["POST"])
def upload_image():
    file = request.files.get("image")

    if not file:
        return jsonify({"error": "No image"}), 400

    filename = secure_filename(file.filename)
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(img_path)

    output_path = os.path.join(OUTPUT_FOLDER, "output.jpg")

    result = process_image(img_path, output_path)

    return jsonify({**result, "image_url": "/output/output.jpg"})


def process_image(img_path, output_path):
    img = cv2.imread(img_path)

    results = model(img, conf=0.3)

    count = 0
    cars = bikes = buses = trucks = 0

    for r in results:
        if r.boxes is None:
            continue

        for box in r.boxes:
            cls = int(box.cls[0])

            if cls in VEHICLE_CLASSES:
                count += 1

                if cls == 2: cars += 1
                elif cls == 3: bikes += 1
                elif cls == 5: buses += 1
                elif cls == 7: trucks += 1

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = model.names[cls]

                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)

    cv2.putText(img, f"Total: {count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (255, 0, 0), 3)

    cv2.imwrite(output_path, img)

    density = min(100, int((count / 20) * 100))

    if count <= 5:
        status = "LOW"
        green_time = 10
        risk = "SAFE"
    elif count <= 15:
        status = "MEDIUM"
        green_time = 20
        risk = "ALERT"
    else:
        status = "HIGH"
        green_time = 40
        risk = "DANGER"

    return {
        "total": count,
        "cars": cars,
        "bikes": bikes,
        "bus": buses,
        "truck": trucks,
        "density": density,
        "traffic_status": status,
        "green_time": green_time,
        "risk": risk
    }


# ================= SERVE =================
@app.route("/output/<filename>")
def serve_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)