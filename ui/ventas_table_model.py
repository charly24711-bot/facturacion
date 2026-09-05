import sys
import os
from decimal import Decimal
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

# Importar Skill de Impuestos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills/tax_calculator/scripts')))
import tax_calculator

from PyQt6.QtCore import pyqtSignal

class VentasTableModel(QAbstractTableModel):
    qty_changed_for_tier = pyqtSignal(int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ["Nro", "Codigo", "Descripcion", "Dp", "Cantidad", "Imp", "Iva", "Precio", "Total"]
        self.items = [] # Lista de diccionarios

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        row = index.row()
        col = index.column()
        item = self.items[row]

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 0: return str(row + 1)
            if col == 1: return item['codigo']
            if col == 2: return item['descripcion']
            if col == 3: return "DC"
            if col == 4: return f"{float(item['cantidad']):g}"
            if col == 5: return str(item['impuesto_porc'])
            if col == 6: return f"{item['iva_monto']:,.0f}"
            if col == 7: return f"{item['precio']:,.0f}"
            if col == 8: return f"{item['total']:,.0f}"
            
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [4, 6, 7, 8]:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole:
            row = index.row()
            col = index.column()
            
            # Solo permitimos editar la Cantidad (columna 4)
            if col == 4:
                try:
                    nueva_cantidad = Decimal(str(value))
                    self.items[row]['cantidad'] = nueva_cantidad
                    self.qty_changed_for_tier.emit(row, nueva_cantidad)
                    self._recalcular_fila(row)
                    self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
                    return True
                except ValueError:
                    return False
        return False

    def flags(self, index):
        default_flags = super().flags(index)
        if index.column() == 4:
            return default_flags | Qt.ItemFlag.ItemIsEditable
        return default_flags

    def add_item(self, product, cantidad=1.0, precio_override=None, promo_label=None):
        precio_final = precio_override if precio_override is not None else Decimal(str(product.art_preven or 0))
        
        # Si ya existe el producto, incrementamos cantidad
        for idx, item in enumerate(self.items):
            if item['codigo'] == product.art_codigo:
                self.items[idx]['cantidad'] += Decimal(str(cantidad))
                self.items[idx]['precio'] = precio_final
                
                # Update promo label
                desc_base = self.items[idx]['descripcion']
                for badge in ["📊 ", "🏷️ ", "📋 "]:
                    if badge in desc_base:
                        desc_base = desc_base.split("  " + badge)[0].strip()
                if promo_label:
                    self.items[idx]['descripcion'] = f"{desc_base}  {promo_label}"
                else:
                    self.items[idx]['descripcion'] = desc_base
                    
                self._recalcular_fila(idx)
                self.dataChanged.emit(self.index(idx, 0), self.index(idx, self.columnCount() - 1))
                return idx

        # Si no existe, agregar nueva fila
        descri = product.art_descri
        if product.is_fractional:
            descri += " (Fracc.)"
        if promo_label:
            descri += f"  🏷️ {promo_label}"

        nuevo_item = {
            'codigo': product.art_codigo,
            'descripcion': descri,
            'cantidad': Decimal(str(cantidad)),
            'precio': precio_final,
            'impuesto_porc': int(product.art_impu),
            'total': 0.0,
            'iva_monto': 0.0
        }
        
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.items.append(nuevo_item)
        self._recalcular_fila(self.rowCount() - 1)
        self.endInsertRows()
        return self.rowCount() - 1

    def remove_item(self, row):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.items[row]
            self.endRemoveRows()
            
            # Notificar cambios en la columna Nro para que se renumere
            if self.rowCount() > 0:
                self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0))

    def _recalcular_fila(self, row):
        item = self.items[row]
        total = item['cantidad'] * item['precio']
        item['total'] = total
        
        # Skill: Tax Calculator
        # Desglose impositivo según Paraguay
        res = tax_calculator.calcular_iva_linea(Decimal(str(total)), item['impuesto_porc'])
        if item['impuesto_porc'] == 10:
            item['iva_monto'] = float(res['iva_10'])
        elif item['impuesto_porc'] == 5:
            item['iva_monto'] = float(res['iva_5'])
        else:
            item['iva_monto'] = 0.0

    def clear(self):
        self.beginResetModel()
        self.items = []
        self.endResetModel()

    def get_total_pyg(self):
        return sum(item['total'] for item in self.items)
