import os
import sys
from decimal import Decimal

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from database import SessionLocal, resolve_image_path
import models
from ui.main_window import MainWindow
from ui.product_search_dialog import ProductSearchDialog
from ui.product_management import ProductManagementDialog

def test_images():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=== TEST VISUALIZACION DE IMAGENES DE PRODUCTOS ===")
    
    # 1. Test MainWindow Visor
    print("\n[1] Verificando Visor Lateral en MainWindow...")
    window = MainWindow()
    window.show()
    
    assert window.product_view_panel.isVisible(), "El panel visor de producto debe estar visible por defecto"
    print("    -> Panel visor visible por defecto: OK")
    
    db = SessionLocal()
    prod = db.query(models.Product).filter(models.Product.is_active == True).first()
    db.close()
    
    print(f"    -> Probando producto {prod.art_codigo} ({prod.art_descri})...")
    window.ventas_model.add_item(prod, Decimal('1'))
    window.table_detalle.selectRow(0)
    window.update_product_view(prod)
    
    pixmap = window.lbl_visor_img.pixmap()
    assert pixmap is not None, "lbl_visor_img no tiene pixmap asignado"
    assert not pixmap.isNull(), "El pixmap cargado en el visor es nulo"
    assert pixmap.width() > 0 and pixmap.height() > 0, "Dimensiones de pixmap invalidas"
    print(f"    -> Pixmap en MainWindow cargado con exito ({pixmap.width()}x{pixmap.height()} px): OK")
    
    if hasattr(window, 'sync_worker'):
        window.sync_worker.stop()
        window.sync_worker.wait(1000)
    window.close()
    
    # 2. Test ProductSearchDialog
    print("\n[2] Verificando Busqueda de Productos [F2] con Fotos...")
    search_dlg = ProductSearchDialog()
    assert search_dlg.table.rowCount() > 0, "La tabla de busqueda no cargo productos"
    
    # Verificar que el primer item tiene icono en la tabla
    item_desc = search_dlg.table.item(0, 1)
    assert not item_desc.icon().isNull(), "El item de la tabla debe tener un icono de producto"
    print("    -> Thumbnail icono en la grilla: OK")
    
    # Verificar tarjeta de vista previa a la derecha
    preview_pix = search_dlg.lbl_preview_img.pixmap()
    assert preview_pix is not None and not preview_pix.isNull(), "La tarjeta de vista previa debe mostrar la foto"
    print(f"    -> Foto grande en panel lateral de busqueda ({preview_pix.width()}x{preview_pix.height()} px): OK")
    search_dlg.close()
    
    # 3. Test ProductManagementDialog
    print("\n[3] Verificando Ficha de Gestion de Productos...")
    mgmt_dlg = ProductManagementDialog()
    if mgmt_dlg.table.rowCount() > 0:
        mgmt_dlg.table.selectRow(0)
        mgmt_dlg.on_selection_changed()
        photo_pix = mgmt_dlg.lbl_product_photo.pixmap()
        assert photo_pix is not None and not photo_pix.isNull(), "La foto en la ficha de producto debe cargarse"
        print(f"    -> Foto en dialogo de gestion ({photo_pix.width()}x{photo_pix.height()} px): OK")
    mgmt_dlg.close()
    
    print("\n========================================================")
    print(">>> TODAS LAS FOTOS E IMAGENES CARGAN CORRECTAMENTE <<<")
    print("========================================================")

if __name__ == '__main__':
    test_images()
