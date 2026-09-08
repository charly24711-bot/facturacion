import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer

from ui.main_window import MainWindow

def run_visual_test():
    app = QApplication(sys.argv)
    
    # Asegurarnos de que hay un producto de prueba
    from database import SessionLocal
    import models
    from decimal import Decimal
    db = SessionLocal()
    prod = db.query(models.Product).filter_by(art_codigo="7840001").first()
    if not prod:
        prod = models.Product(
            art_codigo="7840001",
            art_descri="CERVEZA TEST ROBOT",
            art_cbarra="7840001",
            art_costo=Decimal('5000'),
            art_preven=Decimal('8000'),
            art_impu=Decimal('10'),
            art_stkini=50,
            uom="Un",
            is_fractional=False
        )
        db.add(prod)
        db.commit()
    db.close()

    window = MainWindow()
    window.show()

    def step1_focus():
        print("[Robot] Enfocando buscador de código...")
        window.txt_codigo.setFocus()
        QTimer.singleShot(1000, step2_type_code)

    def step2_type_code():
        print("[Robot] Escribiendo código de barras '7840001'...")
        QTest.keyClicks(window.txt_codigo, "7840001")
        QTimer.singleShot(1000, step3_enter)

    def step3_enter():
        print("[Robot] Presionando ENTER para buscar...")
        QTest.keyClick(window.txt_codigo, Qt.Key.Key_Return)
        QTimer.singleShot(1500, step4_quantity)
        
    def step4_quantity():
        print("[Robot] Modificando cantidad a 3...")
        # Al presionar enter, el cursor saltó a cantidad
        widget = QApplication.focusWidget()
        if widget and hasattr(widget, 'clear'):
            widget.clear()
            QTest.keyClicks(widget, "3")
            QTest.keyClick(widget, Qt.Key.Key_Return)
        QTimer.singleShot(1500, step5_pay)

    def step5_pay():
        print("[Robot] Presionando F2 para cobrar...")
        QTest.keyClick(window, Qt.Key.Key_F2)
        QTimer.singleShot(4000, step6_finish)
        
    def step6_finish():
        print("[Robot] Fin de la simulación visual. Cerrando...")
        window.close()
        app.quit()

    QTimer.singleShot(1000, step1_focus)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    run_visual_test()
