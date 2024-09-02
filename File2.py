import cv2
import numpy as np
import json
import os

def detect_holes(image_path, output_json_path):
    # Check if file exists
    if not os.path.isfile(image_path):
        print(f"File does not exist: {image_path}")
        return

    # Load the image
    image = cv2.imread(image_path)
    
    # Check if image is loaded successfully
    if image is None:
        print(f"Error loading image: {image_path}")
        return

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Preprocessing: Apply Gaussian Blur to reduce noise before thresholding
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive Thresholding to separate holes from the background
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological Operations to refine the binary image
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
    morphed = cv2.morphologyEx(morphed, cv2.MORPH_OPEN, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area and shape
    min_contour_area = 100  # Minimum area threshold for a valid hole
    max_contour_area = 5000  # Maximum area threshold to remove large false positives
    min_circularity = 0.7  # Minimum circularity threshold for a valid hole

    def circularity(contour):
        perimeter = cv2.arcLength(contour, True)
        area = cv2.contourArea(contour)
        if perimeter == 0:
            return 0
        return (4 * np.pi * area) / (perimeter * perimeter)

    hole_data = []
    hole_id = 1  # Start hole ID from 1

    for contour in contours:
        area = cv2.contourArea(contour)
        if min_contour_area < area < max_contour_area:
            # Check for circularity
            circ = circularity(contour)
            if circ >= min_circularity:
                # Get the bounding circle of the contour
                (x, y), radius = cv2.minEnclosingCircle(contour)
                center = (int(x), int(y))
                radius = int(radius)
                
                # Calculate diameter and convert to millimeters
                diameter_px = 2 * radius
                pixels_per_mm = 1  # Replace with actual scale if known
                diameter_mm = diameter_px / pixels_per_mm
                center_mm = (center[0] / pixels_per_mm, center[1] / pixels_per_mm)
                
                # Round values to 2 decimal places
                diameter_mm = round(diameter_mm, 2)
                center_mm = (round(center_mm[0], 2), round(center_mm[1], 2))
                
                # Save hole data
                hole_data.append({
                    'id': hole_id,
                    'diameter_mm': diameter_mm,
                    'coordinates_mm': center_mm
                })
                hole_id += 1  # Increment hole ID

    # Number of holes detected
    num_holes = len(hole_data)

    # Prepare the data to be saved in JSON
    result = {
        "plc_status": "Connected",
        "capture_status": "Not Capturing",
        "total_holes": num_holes,
        "hole_info": hole_data,
        "stitched_image_path": image_path
    }
    
    # Save to JSON file
    with open(output_json_path, 'w') as json_file:
        json.dump(result, json_file, indent=4)
    
    print(f"Results saved to {output_json_path}")

# Example usage
image_path = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1/stitched_image_with_holes.jpg'
output_json_path = 'hole_detection_results.json'
detect_holes(image_path, output_json_path)
