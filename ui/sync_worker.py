from PyQt6.QtCore import QThread, pyqtSignal
import time
import requests
from database import SessionLocal
import models
import json

class SyncWorker(QThread):
    # Señales para comunicarse con la UI principal
    status_changed = pyqtSignal(bool) # True = Online, False = Offline
    sync_progress = pyqtSignal(int, int) # Pendientes, Procesados
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.is_online = False
        self.central_url = "http://localhost:8000/api/v1" # Simulado
        
    def run(self):
        while self.running:
            # 1. Detección de Estado de Red (Ping)
            self._check_connection()
            
            # 2. Si hay red, sincronizar Outbox
            if self.is_online:
                self._process_outbox()
                
            # Dormir 10 segundos antes de la próxima comprobación
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(1)
                
    def _check_connection(self):
        try:
            # En la vida real haríamos un requests.get a self.central_url + '/health'
            # Para esta demo, simularemos conectividad comprobando si google.com responde
            # o simplemente lo dejamos en True. Lo dejaremos en True por simplicidad
            # de demostración local.
            self.is_online = True
            self.status_changed.emit(True)
        except Exception:
            self.is_online = False
            self.status_changed.emit(False)
            
    def _process_outbox(self):
        db = SessionLocal()
        try:
            # Leer lotes de 20 registros
            pendientes = db.query(models.SyncOutbox).filter_by(synced=False).limit(20).all()
            
            if not pendientes:
                return
                
            self.sync_progress.emit(len(pendientes), 0)
            
            procesados = 0
            for item in pendientes:
                # Simular envío POST al servidor central
                # En la vida real: requests.post(self.central_url + f"/sync/{item.entity_name}", json=json.loads(item.payload_json))
                
                # Simular respuesta exitosa del servidor
                item.synced = True
                procesados += 1
                
            db.commit()
            self.sync_progress.emit(len(pendientes) - procesados, procesados)
            
        except Exception as e:
            db.rollback()
            # Falla silenciosa, reintentará en el próximo ciclo
            pass
        finally:
            db.close()
            
    def stop(self):
        self.running = False
        self.wait()
