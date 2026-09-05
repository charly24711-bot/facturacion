import cv2
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

class CameraDialog(QDialog):
    def __init__(self, product_code, parent=None):
        super().__init__(parent)
        self.product_code = product_code
        self.saved_image_path = None
        self.setWindowTitle("Captura de Producto")
        self.resize(640, 520)
        
        self.layout = QVBoxLayout(self)
        
        self.lbl_video = QLabel("Iniciando cámara...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet("background-color: black; color: white;")
        self.lbl_video.setMinimumSize(640, 480)
        self.layout.addWidget(self.lbl_video)
        
        btn_layout = QHBoxLayout()
        self.btn_capture = QPushButton("📸 Capturar Foto")
        self.btn_capture.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        self.btn_capture.clicked.connect(self.capture_photo)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_capture)
        btn_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(btn_layout)
        
        # Iniciar cámara
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "No se pudo acceder a la cámara web.")
            self.reject()
            return
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30) # 30 ms para aprox 30 fps
        
    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Convertir a RGB para PyQt
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)
            self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def capture_photo(self):
        self.timer.stop()
        ret, frame = self.cap.read()
        if ret:
            # Preguntar confirmación
            reply = QMessageBox.question(self, "Confirmar", "¿Guardar esta foto?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs("assets/images", exist_ok=True)
                file_path = f"assets/images/{self.product_code}.png"
                # OpenCV guarda en formato BGR por defecto
                cv2.imwrite(file_path, frame)
                self.saved_image_path = file_path
                self.accept()
            else:
                self.timer.start(30) # Reiniciar feed
        else:
            QMessageBox.warning(self, "Error", "Fallo al capturar el frame.")
            self.timer.start(30)

    def closeEvent(self, event):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)
