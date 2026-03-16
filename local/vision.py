import mss
import cv2
import numpy as np

def capture_screen_as_base64(monitor_index: int = 1) -> str:
    """Captures the screen and returns it as a base64 encoded JPEG string."""
    import base64
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        sct_img = sct.grab(monitor)
        img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        
        # Overlay 10x10 Grid for better spatial prediction
        height, width, _ = img_bgr.shape
        grid_color = (0, 0, 255) # Red lines
        text_color = (0, 0, 255)
        
        for i in range(1, 10):
            x = int(width * (i / 10.0))
            y = int(height * (i / 10.0))
            # Vertical lines (X Axis)
            cv2.line(img_bgr, (x, 0), (x, height), grid_color, 1)
            cv2.putText(img_bgr, f"X:{i * 100}", (x + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
            # Horizontal lines (Y Axis)
            cv2.line(img_bgr, (0, y), (width, y), grid_color, 1)
            cv2.putText(img_bgr, f"Y:{i * 100}", (5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)

        # Draw red crosshair for current mouse position to give feedback on clicks
        import pyautogui
        mx, my = pyautogui.position()
        # Ensure we scale the logical mouse pos to the physical screenshot if scales differ,
        # but for hackathon simplicity we assume mouse coords roughly map 1:1 or are relative to monitor 1
        cv2.drawMarker(img_bgr, (mx, my), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

        success, buffer = cv2.imencode('.jpg', img_bgr)
        if success:
            return base64.b64encode(buffer).decode('utf-8')
        return ""
