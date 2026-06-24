"""
AirMouse — Camera Picker GUI
Allows the user to preview and select the correct webcam.
"""

import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class CameraPicker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AirMouse — Select Webcam")
        
        # Center the window
        window_width = 680
        window_height = 750
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))
        self.root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        
        # Style
        self.root.configure(bg="#1e1e1e")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background="#1e1e1e", foreground="white", font=("Segoe UI", 12))
        style.configure('TButton', font=("Segoe UI", 11, "bold"))
        
        # Variables
        self.selected_cap = None
        self.current_backend = None
        self.result = None
        self.is_running = True
        
        # UI Elements
        title = ttk.Label(self.root, text="Select Webcam for AirMouse", font=("Segoe UI", 18, "bold"), foreground="#00dcff")
        title.pack(pady=(15, 5))
        
        desc = ttk.Label(self.root, text="Pick the camera that shows your face (not a black OBS screen)", font=("Segoe UI", 10))
        desc.pack(pady=(0, 15))
        
        ctrl_frame = tk.Frame(self.root, bg="#1e1e1e")
        ctrl_frame.pack(pady=5)
        
        ttk.Label(ctrl_frame, text="Camera Index:").pack(side=tk.LEFT, padx=5)
        
        self.combo = ttk.Combobox(ctrl_frame, values=[f"Camera {i}" for i in range(10)], state="readonly", width=15)
        self.combo.current(0)
        self.combo.pack(side=tk.LEFT, padx=5)
        self.combo.bind("<<ComboboxSelected>>", self.on_camera_change)
        
        # Preview
        self.preview_label = tk.Label(self.root, bg="black", width=640, height=480)
        self.preview_label.pack(pady=10)
        
        # Start button
        self.start_btn = tk.Button(self.root, text="START AIRMOUSE 🚀", font=("Segoe UI", 14, "bold"), 
                                   bg="#00dcff", fg="black", activebackground="#00b0cc", 
                                   padx=20, pady=10, cursor="hand2", command=self.start)
        self.start_btn.pack(pady=10)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start feed
        self.change_camera(0)
        self.update_frame()
        
    def change_camera(self, idx):
        if self.selected_cap:
            self.selected_cap.release()
            
        # Try MSMF first, then default
        self.selected_cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
        self.current_backend = cv2.CAP_MSMF
        
        if not self.selected_cap.isOpened() or not self.selected_cap.read()[0]:
            self.selected_cap.release()
            self.selected_cap = cv2.VideoCapture(idx)
            self.current_backend = cv2.CAP_ANY
            
    def on_camera_change(self, event):
        idx = int(self.combo.get().split()[1])
        self.preview_label.configure(image='', text="Loading...", fg="white")
        self.root.update()
        self.change_camera(idx)
        
    def update_frame(self):
        if not self.is_running:
            return
            
        if self.selected_cap and self.selected_cap.isOpened():
            ret, frame = self.selected_cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 480))
                
                # Detect and warn about completely black frames (OBS Virtual Camera etc.)
                if frame.mean() < 1.0:
                    cv2.putText(frame, "BLACK FRAME DETECTED", (140, 230), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame, "(Likely a Virtual Camera. Please select a different index)", (70, 270), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                
                cv_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cv_rgb)
                imgtk = ImageTk.PhotoImage(image=pil_img)
                self.preview_label.imgtk = imgtk
                self.preview_label.configure(image=imgtk)
            else:
                self.preview_label.configure(image='', text="No Signal", fg="white")
        else:
            self.preview_label.configure(image='', text="Camera Unavailable", fg="white")
            
        self.root.after(30, self.update_frame)
        
    def start(self):
        self.is_running = False
        idx = int(self.combo.get().split()[1])
        self.result = (idx, self.current_backend)
        if self.selected_cap:
            self.selected_cap.release()
        self.root.destroy()
        
    def on_closing(self):
        self.is_running = False
        self.result = None
        if self.selected_cap:
            self.selected_cap.release()
        self.root.destroy()

def pick_camera():
    """Launch the GUI and return (index, backend) or None."""
    picker = CameraPicker()
    picker.root.mainloop()
    return picker.result
