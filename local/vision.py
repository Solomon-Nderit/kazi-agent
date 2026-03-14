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
        success, buffer = cv2.imencode('.jpg', img_bgr)
        if success:
            return base64.b64encode(buffer).decode('utf-8')
        return ""
