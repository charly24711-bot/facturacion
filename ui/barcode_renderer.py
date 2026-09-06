"""
ui/barcode_renderer.py
======================
Motor universal de generación y renderizado de códigos de barras y etiquetas de góndola:
- EAN-13 (con cálculo de dígito verificador módulo 10 y estructura 95 módulos)
- Code-128 (Subset B completo con checksum módulo 103)
- Renderizado vectorial de alta nitidez para escáneres ópticos y láser
- Dibujado estético de etiquetas de góndola para rollos térmicos y pliegos A4
- Respeto estricto a Decimal para precios y cotizaciones (sin float)
"""

from decimal import Decimal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, QPointF

# ── EAN-13 Patterns ────────────────────────────────────────────────────────
_L_CODES = ['0001101', '0011001', '0010011', '0111101', '0100011',
            '0110001', '0101111', '0111011', '0110111', '0001011']
_G_CODES = ['0100111', '0110011', '0011011', '0100001', '0011101',
            '0111001', '0000101', '0010001', '0001001', '0010111']
_R_CODES = ['1110010', '1100110', '1101100', '1000010', '1011100',
            '1001110', '1010000', '1000100', '1001000', '1110100']
_PARITY = [
    'AAAAAA', 'AABABB', 'AABBAB', 'AABBBA', 'ABAABB',
    'ABBAAB', 'ABBBAA', 'ABABAB', 'ABABBA', 'ABBABA'
]

# ── Code 128 Patterns (Run-length bar/space widths, 107 symbols) ──────────
_C128_PATTERNS = [
    '212222', '222122', '222221', '121223', '121322', '131222', '122213', '122312', '132212', '221213',
    '221312', '231212', '112232', '122132', '122231', '113222', '123122', '123221', '223211', '221132',
    '221231', '213212', '223112', '312131', '311222', '321122', '321221', '312212', '322112', '322211',
    '212123', '212321', '232121', '111323', '131123', '131321', '112313', '132113', '132311', '211313',
    '231113', '231311', '112133', '112331', '132131', '113123', '113321', '133121', '313121', '211331',
    '231131', '213113', '213311', '213131', '311123', '311321', '331121', '312113', '312311', '332111',
    '314111', '221411', '431111', '111224', '111422', '121124', '121421', '141122', '141221', '112214',
    '112412', '122114', '122411', '142112', '142211', '241211', '221114', '413111', '241112', '134111',
    '111242', '121142', '121241', '114212', '124112', '124211', '411212', '421112', '421211', '212141',
    '214121', '412121', '111143', '111341', '131141', '114113', '114311', '411113', '411311', '113141',
    '114131', '311141', '411131', '211412', '211214', '211232', '2331112'
]


def calculate_ean13_checksum(digits12: str) -> str:
    """Calcula el dígito verificador estándar EAN-13 para los primeros 12 dígitos."""
    clean = "".join(filter(str.isdigit, digits12))[:12].zfill(12)
    s = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(clean))
    return str((10 - (s % 10)) % 10)


def encode_ean13(code: str) -> tuple[str, str]:
    """
    Codifica un código EAN-13 en una cadena de bits ('0' y '1').
    Retorna (bitstring_95_modules, full_13_digits_code).
    """
    clean = "".join(filter(str.isdigit, str(code)))
    if len(clean) < 12:
        clean = clean.zfill(12)
    
    if len(clean) == 12:
        chk = calculate_ean13_checksum(clean)
        full_code = clean + chk
    else:
        full_code = clean[:13]

    first = int(full_code[0])
    pattern = _PARITY[first]

    modules = "101"  # Left guard
    for i in range(6):
        d = int(full_code[i + 1])
        modules += _L_CODES[d] if pattern[i] == "A" else _G_CODES[d]

    modules += "01010"  # Center guard

    for i in range(6):
        d = int(full_code[i + 7])
        modules += _R_CODES[d]

    modules += "101"  # Right guard
    return modules, full_code


def encode_code128(text: str) -> tuple[str, str]:
    """
    Codifica cualquier texto alfanumérico en Code 128 (Subset B).
    Retorna (bitstring, text_limpio).
    """
    clean_text = "".join(c for c in str(text) if 32 <= ord(c) <= 126)
    if not clean_text:
        clean_text = "0"

    start_b = 104
    stop_code = 106
    values = [ord(c) - 32 for c in clean_text]
    checksum = (start_b + sum((i + 1) * v for i, v in enumerate(values))) % 103

    tokens = [start_b] + values + [checksum, stop_code]

    bitstring = ""
    for t in tokens:
        p = _C128_PATTERNS[t]
        bar = True
        for c in p:
            bitstring += ("1" if bar else "0") * int(c)
            bar = not bar

    return bitstring, clean_text


def get_barcode_bits(code_str: str) -> tuple[str, str, str]:
    """
    Selecciona automáticamente el mejor algoritmo de codificación:
    - Si tiene 12 o 13 dígitos numéricos -> EAN-13
    - En caso contrario -> Code-128
    Retorna (tipo, bitstring, texto_mostrado).
    """
    s = str(code_str).strip()
    digits_only = "".join(filter(str.isdigit, s))
    if len(digits_only) in (12, 13) and len(digits_only) == len(s):
        bits, full_code = encode_ean13(s)
        return "EAN13", bits, full_code
    else:
        bits, clean = encode_code128(s)
        return "CODE128", bits, clean


def draw_barcode(painter: QPainter, x: float, y: float, width: float, height: float,
                 code_str: str, show_text: bool = True, text_font_size: int = 8):
    """
    Dibuja un código de barras vectorial nítido en el QPainter en las coordenadas dadas.
    """
    btype, bits, display_text = get_barcode_bits(code_str)
    num_modules = len(bits)
    if num_modules == 0:
        return

    text_space = 14 if show_text else 0
    bar_height = max(5.0, height - text_space)
    module_width = width / float(num_modules)

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#000000"))

    # Dibujar las barras
    for i, bit in enumerate(bits):
        if bit == "1":
            bx = x + (i * module_width)
            painter.drawRect(QRectF(bx, y, module_width + 0.1, bar_height))

    # Dibujar el texto legible inferior
    if show_text:
        painter.setPen(QColor("#111827"))
        font = QFont("Arial", text_font_size, QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(font)
        text_rect = QRectF(x, y + bar_height + 1, width, text_space)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, display_text)

    painter.restore()


def render_barcode_pixmap(code_str: str, width: int = 220, height: int = 70,
                          show_text: bool = True) -> QPixmap:
    """Genera un QPixmap con el código de barras renderizado sobre fondo blanco."""
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("white"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    
    # Margen interno de quiet zone
    margin_x = 10
    margin_y = 5
    draw_barcode(
        painter,
        margin_x,
        margin_y,
        width - (margin_x * 2),
        height - (margin_y * 2),
        code_str,
        show_text=show_text,
        text_font_size=9
    )
    painter.end()
    return pixmap


def draw_shelf_label(painter: QPainter, rect: QRectF, item: dict,
                     store_name: str = "SUPERMERCADO CENTRAL",
                     show_usd: bool = True, show_date: bool = True,
                     rate_usd: Decimal = Decimal('7500')):
    """
    Dibuja una etiqueta de góndola profesional para supermercado dentro del QRectF dado.
    
    item contiene:
      - 'art_codigo': '000105'
      - 'art_descri': 'LECHE ENTERA LA FORTUNA 1L'
      - 'art_codbar': '7840001001054'
      - 'art_preven': Decimal('7500')
      - 'unidad': 'UN' (opcional)
    """
    painter.save()
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    # Fondo blanco con borde de corte suave
    painter.setPen(QPen(QColor("#d1d5db"), 1, Qt.PenStyle.DashLine))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRect(QRectF(x, y, w, h))

    pad = 6.0
    inner_x = x + pad
    inner_y = y + pad
    inner_w = w - (pad * 2)
    inner_h = h - (pad * 2)

    # 1. Cabecera / Comercio
    painter.setPen(QColor("#4b5563"))
    font_store = QFont("Arial", 7, QFont.Weight.Bold)
    painter.setFont(font_store)
    store_rect = QRectF(inner_x, inner_y, inner_w * 0.65, 12)
    painter.drawText(store_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, store_name.upper())

    # Cód Interno / Fecha
    cod_txt = f"CÓD: {item.get('art_codigo', '')}"
    painter.setFont(QFont("Arial", 7, QFont.Weight.Normal))
    meta_rect = QRectF(inner_x + (inner_w * 0.65), inner_y, inner_w * 0.35, 12)
    painter.drawText(meta_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, cod_txt)

    # 2. Descripción del Producto
    desc_y = inner_y + 13
    desc_h = 24
    desc_rect = QRectF(inner_x, desc_y, inner_w, desc_h)
    font_desc = QFont("Arial", 9, QFont.Weight.Bold)
    painter.setFont(font_desc)
    painter.setPen(QColor("#111827"))
    
    desc_text = str(item.get("art_descri", "PRODUCTO SIN NOMBRE")).strip().upper()
    metrics = QFontMetrics(font_desc)
    elided = metrics.elidedText(desc_text, Qt.TextElideMode.ElideRight, int(inner_w))
    painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, elided)

    # 3. Línea divisoria suave
    div_y = desc_y + desc_h + 2
    painter.setPen(QPen(QColor("#e5e7eb"), 1))
    painter.drawLine(QPointF(inner_x, div_y), QPointF(inner_x + inner_w, div_y))

    # 4. Sección Inferior:
    #    Izquierda: Código de barras con números legibles
    #    Derecha: Precio prominente en Gs. y opcional en USD
    bottom_y = div_y + 4
    bottom_h = inner_h - (bottom_y - inner_y)

    bar_w = inner_w * 0.52
    price_w = inner_w * 0.46
    price_x = inner_x + bar_w + (inner_w * 0.02)

    # Código de barras (usar código de barras si existe, sino código interno)
    cod_bar = item.get("art_codbar") or item.get("art_codigo") or "000000"
    draw_barcode(painter, inner_x, bottom_y, bar_w, bottom_h - 2, str(cod_bar), show_text=True, text_font_size=7)

    # Tarjeta de Precio (Fondo suave o texto resaltado grande)
    price_rect = QRectF(price_x, bottom_y, price_w, bottom_h)
    
    # Precio en Guaraníes (Decimal puro)
    precio_pyg = item.get("art_preven", Decimal("0"))
    if not isinstance(precio_pyg, Decimal):
        precio_pyg = Decimal(str(precio_pyg))

    formatted_pyg = f"₲ {int(precio_pyg):,}".replace(",", ".")
    
    # Etiqueta "PRECIO CONTADO"
    painter.setPen(QColor("#6b7280"))
    painter.setFont(QFont("Arial", 6, QFont.Weight.Bold))
    lbl_tag = QRectF(price_x, bottom_y, price_w, 10)
    painter.drawText(lbl_tag, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, "PRECIO CONTADO")

    # Monto Gigante en Gs.
    painter.setPen(QColor("#047857"))  # Verde esmeralda retail
    font_price = QFont("Arial", 14, QFont.Weight.Black)
    painter.setFont(font_price)
    lbl_val = QRectF(price_x, bottom_y + 8, price_w, 24)
    painter.drawText(lbl_val, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, formatted_pyg)

    # Precio en USD
    usd_y = bottom_y + 30
    if show_usd and rate_usd and rate_usd > Decimal("0"):
        precio_usd = (precio_pyg / rate_usd).quantize(Decimal("0.01"))
        painter.setPen(QColor("#1e40af"))  # Azul frontera
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        lbl_usd = QRectF(price_x, usd_y, price_w, 12)
        painter.drawText(lbl_usd, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"US$ {precio_usd}")
        usd_y += 12

    # Fecha pequeña al pie
    if show_date:
        import datetime
        today_str = datetime.date.today().strftime("%d/%m/%Y")
        painter.setPen(QColor("#9ca3af"))
        painter.setFont(QFont("Arial", 5, QFont.Weight.Normal))
        lbl_date = QRectF(price_x, usd_y, price_w, 8)
        painter.drawText(lbl_date, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"Emitido: {today_str}")

    painter.restore()
