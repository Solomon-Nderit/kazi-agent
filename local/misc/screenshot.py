import mss
import numpy as np
import cv2

def capture_screen(monitor_index: int = 1) -> np.ndarray:
    """
    Captures the screen and returns it as a NumPy array (BGR format).
    Args:
        monitor_index (int): 1 is usually the primary monitor. 0 is all monitors combined.
    """
    with mss.mss() as sct:
        # mss uses 1-based indexing for monitors (1 is main, 0 is all)
        monitor = sct.monitors[monitor_index]
        
        # Grab raw screen pixels
        sct_img = sct.grab(monitor)
        
        # mss natively returns BGRA. Convert to standard BGR for OpenCV
        img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        
        return img_bgr

def _get_column_label(n: int) -> str:
    """Converts a 0-based index to Excel-style column labels (A, B, C... Z, AA...)."""
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label

def add_grid(img: np.ndarray, step_size: int = 50) -> np.ndarray:
    """
    Draws an Excel-style A1/B2 grid overlay on the image and returns a new array.
    This uses native OpenCV operations for maximum speed in memory.
    """
    # Create a copy so we don't mutate the raw image passing through our pipeline
    overlayed = img.copy()
    height, width = overlayed.shape[:2]

    grid_color = (128, 128, 128)  # Mid-gray lines
    text_color = (255, 255, 255)  # White text 
    box_color = (0, 0, 0)         # Black background for contrast

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1

    # Fast vertical line draw
    for x in range(0, width, step_size):
        cv2.line(overlayed, (x, 0), (x, height), grid_color, 1)

    # Fast horizontal line draw
    for y in range(0, height, step_size):
        cv2.line(overlayed, (0, y), (width, y), grid_color, 1)

    # Draw the Text Labels (A1, B2)
    for row_idx, y in enumerate(range(0, height, step_size)):
        for col_idx, x in enumerate(range(0, width, step_size)):
            
            col_str = _get_column_label(col_idx)
            label = f"{col_str}{row_idx + 1}"

            # Calculate the drawing anchor for OpenCV text (bottom-left of text string)
            # Add a 2 pixel pad to push it slightly off the top-left crosshair
            text_x = x + 2
            text_y = y + 14 
            
            # Determine the bounding box size of the text to draw a black rectangle behind it
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Draw the black background box (filled rectangle)
            cv2.rectangle(
                overlayed, 
                (text_x, text_y - text_height - 2), 
                (text_x + text_width, text_y + baseline - 2), 
                box_color, 
                cv2.FILLED
            )
            
            # Draw the white text on top
            cv2.putText(overlayed, label, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)

    return overlayed

def get_screen_with_grid(monitor_index: int = 1, step_size: int = 50) -> tuple:
    """
    Convenience function that captures the screen and returns both the 
    raw image and the image with the grid overlay applied simultaneously.
    
    Returns:
        tuple: (raw_image_array, overlayed_image_array)
    """
    raw_img = capture_screen(monitor_index)
    overlayed_img = add_grid(raw_img, step_size)
    return raw_img, overlayed_img

