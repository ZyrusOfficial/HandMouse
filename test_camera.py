import cv2
import time

print("Scanning for cameras...")
backends = [
    (cv2.CAP_MSMF, "Media Foundation"),
    (cv2.CAP_DSHOW, "DirectShow"),
    (cv2.CAP_ANY, "Default")
]

working_cameras = []

for idx in range(5):
    for backend, name in backends:
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                mean_color = frame.mean()
                print(f"[+] Camera {idx} ({name}) works! Frame shape: {frame.shape}, Mean pixel value: {mean_color:.2f}")
                if mean_color < 1.0:
                    print("    -> WARNING: Frame is completely black! (Virtual camera or locked hardware?)")
                working_cameras.append((idx, backend, name))
            cap.release()

if not working_cameras:
    print("No working cameras found.")
else:
    print(f"\nTesting the first working camera: Index {working_cameras[0][0]} ({working_cameras[0][2]})")
    cap = cv2.VideoCapture(working_cameras[0][0], working_cameras[0][1])
    
    frames_read = 0
    start_time = time.time()
    
    while time.time() - start_time < 5.0: # Test for 5 seconds
        ret, frame = cap.read()
        if ret:
            frames_read += 1
            cv2.imshow("Camera Test", frame)
            cv2.waitKey(1)
        else:
            print("Failed to read frame.")
            break
            
    print(f"Read {frames_read} frames in 5 seconds.")
    cap.release()
    cv2.destroyAllWindows()
