import cv2
import numpy as np
import os
import json
import snap7
from snap7.util import get_int, set_int
from pypylon import pylon
from concurrent.futures import ThreadPoolExecutor    

# Calibration factor (mm per pixel)
MM_PER_PIXEL = 0.1  # Example: 1 pixel = 0.1 mm
HOLE_DISTANCE_THRESHOLD = 15  # Minimum distance between holes to consider them separate

# Connect to PLC
def connect_to_plc(plc_ip, rack, slot):
    try:
        plc = snap7.client.Client()
        plc.connect(plc_ip, rack, slot)
        if plc.get_connected():
            print("Connected to PLC.")                          
            return plc                                     
        else:
            print("Failed to connect to PLC.")
            return None
    except Exception as e:
        print(f"Failed to connect to PLC: {e}")
        return None

# Detect and count holes in the image
def detect_and_count_holes(frame, existing_holes):
    if len(frame.shape) == 3 and frame.shape[2] == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)

    mask = np.zeros_like(edges)
    frame_height, frame_width = edges.shape
    roi = (100, 100, frame_width - 200, frame_height - 200)
    cv2.rectangle(mask, (roi[0], roi[1]), (roi[0] + roi[2], roi[1] + roi[3]), 255, -1)
    edges = cv2.bitwise_and(edges, mask)

    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_contour_area = 100
    max_contour_area = frame.shape[0] * frame.shape[1] * 0.5
    filtered_contours = [cnt for cnt in contours if min_contour_area < cv2.contourArea(cnt) < max_contour_area]

    def is_circular(contour):
        if len(contour) < 5:
            return False
        (x, y), radius = cv2.minEnclosingCircle(contour)
        area = cv2.contourArea(contour)
        circularity = (4 * np.pi * area) / (cv2.arcLength(contour, True) ** 2)
        return 0.7 < circularity < 1.2

    filtered_contours = [cnt for cnt in filtered_contours if is_circular(cnt)]

    frame_with_holes = frame.copy()
    cv2.drawContours(frame_with_holes, filtered_contours, -1, (0, 255, 0), 2)

    new_holes = []
    existing_hole_positions = {(x, y) for _, _, (x, y) in existing_holes}

    def is_within_distance(hole, existing_holes):
        _, _, (x_mm, y_mm) = hole
        for _, _, (ex_mm, ey_mm) in existing_holes:
            distance = np.sqrt((x_mm - ex_mm)**2 + (y_mm - ey_mm)**2)
            if distance < HOLE_DISTANCE_THRESHOLD:
                return True
        return False

    for i, cnt in enumerate(filtered_contours):
        ((x, y), radius) = cv2.minEnclosingCircle(cnt)
        diameter_px = 2 * radius
        diameter_mm = round(diameter_px * MM_PER_PIXEL, 2)
        x_mm = round(x * MM_PER_PIXEL, 2)
        y_mm = round(y * MM_PER_PIXEL, 2)

        if diameter_mm > 5:
            hole_id = len(existing_holes) + 1
            hole = (hole_id, diameter_mm, (x_mm, y_mm))
            if not is_within_distance(hole, existing_holes):
                new_holes.append(hole)
                existing_holes.append(hole)
                existing_hole_positions.add((x_mm, y_mm))

    num_holes = len(new_holes)
    print(f"Detected {num_holes} holes.")
    print("Hole info:", new_holes)
    return frame_with_holes, num_holes, new_holes

# Preprocess images
def preprocess_images(images, target_size=(1024, 768)):
    preprocessed_images = []
    for img in images:
        if img is None or img.size == 0:
            print("Warning: Skipping an empty or None image.")
            continue

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        resized_img = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)
        preprocessed_images.append(resized_img)
    
    return preprocessed_images

# Stitch images
def stitch_images(images):
    print("Attempting to stitch images using OpenCV...")
    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)

    if not images:
        print("No images to stitch.")
        return None

    try:
        status, stitched = stitcher.stitch(images)
        if status != cv2.Stitcher_OK:
            print(f"Error during stitching: {status} (error code {status})")
            if status == cv2.Stitcher_ERR_NEED_MORE_IMGS:
                print("Need more images for stitching.")
            elif status == cv2.Stitcher_ERR_NOT_ENOUGH_FEAT:
                print("Not enough features detected.")
            elif status == cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL:
                print("Homography estimation failed.")
            elif status == cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL:
                print("Camera parameters adjustment failed.")
            return None
    except cv2.error as e:
        print(f"OpenCV error during stitching: {e}")
        return None

    return stitched

# Save hole info to text file
def save_hole_info_to_txt(hole_info, txt_path):
    try:
        with open(txt_path, 'w') as file:
            file.write("Hole Detection Report\n\n")
            file.write(f"{'Hole ID':<10}{'Diameter (mm)':<20}{'Coordinates (x, y) in mm':<30}\n")
            for hole_id, diameter, (x_mm, y_mm) in hole_info:
                file.write(f"{hole_id:<10}{diameter:<20.2f}{f'({x_mm:.2f}, {y_mm:.2f})':<30}\n")
        print(f"Hole information successfully saved to '{txt_path}'")
    except Exception as e:
        print(f"Failed to save hole information to file: {e}")

# Read PLC value
def read_plc_value(plc, db_number, start, size):
    try:
        data = plc.read_area(snap7.types.Areas.DB, db_number, start, size)
        value = get_int(data, 0)
        return value
    except Exception as e:
        print(f"Failed to read PLC value: {e}")
        return None

# Write PLC value
def write_plc_value(plc, db_number, start, value):
    try:
        data = bytearray(2)
        set_int(data, 0, value)
        plc.write_area(snap7.types.Areas.DB, db_number, start, data)
        print(f"Wrote value {value} to PLC DB{db_number}.DBW{start}")
    except Exception as e:
        print(f"Failed to write value to PLC: {e}")

# Save dashboard data to JSON file
def save_dashboard_data(plc_status, capture_status, total_holes, hole_info, stitched_img_path):
    data = {
        "plc_status": plc_status,
        "capture_status": capture_status,
        "total_holes": total_holes,
        "hole_info": hole_info,
        "stitched_image_path": f"/images/{os.path.basename(stitched_img_path)}"  # Use relative path
    }
    with open('dashboard_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Dashboard data successfully saved to 'dashboard_data.json'")

# Update dashboard variables
def update_dashboard_variables(plc_status_val, capture_status_val, total_holes_val, stitched_img_path_val):
    global plc_status, capture_status, total_holes, stitched_image_path
    plc_status = plc_status_val
    capture_status = capture_status_val
    total_holes = total_holes_val
    stitched_image_path = stitched_img_path_val

# Load and preprocess image
def load_and_preprocess_image(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image at {image_path}.")
            return None
        preprocessed_image = preprocess_images([image])[0]
        return preprocessed_image
    except Exception as e:
        print(f"Error processing image at {image_path}: {e}")
        return None

def main():
    global plc_status, capture_status, total_holes, stitched_image_path

    plc_ip = "192.168.0.1"  # Replace with your PLC IP address
    plc_rack = 0
    plc_slot = 2
    plc = connect_to_plc(plc_ip, plc_rack, plc_slot)

    hole_info = []
    frames = []

    if plc:
        try:
            plc_status = "Connected"
            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            camera.Open()
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            save_dir = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1'
            os.makedirs(save_dir, exist_ok=True)
            print(f"Directory '{save_dir}' is ready.")

            frame_count = 1

            while True:
                try:
                    grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                    if grab_result.GrabSucceeded():
                        image = grab_result.Array
                        num_channels = 1 if len(image.shape) == 2 else image.shape[2]

                        if num_channels == 2:
                            image = cv2.cvtColor(image, cv2.COLOR_BayerBG2BGR)
                        elif num_channels == 1:
                            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

                        frame_with_holes, num_holes_in_frame, hole_info_in_frame = detect_and_count_holes(image, hole_info)
                        total_holes = len(hole_info)

                        cv2.imshow("Detected Holes", frame_with_holes)

                        frame_path = os.path.join(save_dir, f'frame_{frame_count}.jpg')
                        cv2.imwrite(frame_path, image)
                        frames.append(frame_path)
                        print(f"Saved frame {frame_count} to {frame_path}")

                        update_dashboard_variables(plc_status, "Capturing", total_holes, frame_path)
                        frame_count += 1

                        key = cv2.waitKey(1)
                        if key == ord('q'):
                            break

                    grab_result.Release()
                except Exception as e:
                    print(f"Error during frame capture: {e}")
        except Exception as e:
            print(f"Error accessing camera: {e}")
        finally:
            camera.Close()
            cv2.destroyAllWindows()
            if plc:
                plc.disconnect()

    if len(frames) >= 2:
        print("Preparing to stitch images...")

        # Load and preprocess images in parallel
        with ThreadPoolExecutor() as executor:
            preprocessed_images = list(executor.map(load_and_preprocess_image, frames))

        # Filter out None values
        preprocessed_images = [img for img in preprocessed_images if img is not None]
        
        # Limit the number of images if necessary
        preprocessed_images = preprocessed_images[:5]
        
        if len(preprocessed_images) < 2:
            print("Not enough valid images for stitching.")
            stitched_image_path = 'None'
        else:
            stitched_image = stitch_images(preprocessed_images)
            if isinstance(stitched_image, np.ndarray):
                stitched_image_path = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1/stitched_image_v1.jpg'
                cv2.imwrite(stitched_image_path, stitched_image)
                print(f"Stitched image saved to '{stitched_image_path}'")
                
                # Detect holes in stitched image
                stitched_image_with_holes, num_holes_in_stitched, hole_info_in_stitched = detect_and_count_holes(stitched_image, hole_info)
                
                if isinstance(stitched_image_with_holes, np.ndarray):
                    cv2.imwrite('/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1/stitched_image_with_holes.jpg', stitched_image_with_holes)
                
                update_dashboard_variables(plc_status, capture_status, total_holes, stitched_image_path)
            else:
                print("Failed to stitch images.")
                stitched_image_path = 'None'
    else:
        print("Not enough images to perform stitching.")
        stitched_image_path = 'None'

    if hole_info:
        save_hole_info_to_txt(hole_info, '/home/jetson/Documents/testing/testing_program_v1/hole_info.txt')
    
    save_dashboard_data(plc_status, "Not Capturing", total_holes, hole_info, stitched_image_path)

if __name__ == "__main__":
    main()

