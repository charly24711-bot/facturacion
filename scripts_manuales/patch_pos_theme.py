import sys
import re

def main():
    file_path = r"c:\ENTORNO LOCAL\Control\ui\main_window.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_str = "        main_bottom_widget.setStyleSheet(\"\"\""
    end_str = "        main_bottom_layout = QHBoxLayout(main_bottom_widget)"

    start_idx = content.find(start_str)
    end_idx = content.find(end_str)

    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end string.")
        return

    new_style = """        main_bottom_widget.setStyleSheet(\"\"\"
            QWidget {
                background-color: #2c3e50; /* Fondo gris oscuro corporativo */
                border: 2px solid #34495e;
                border-radius: 4px;
            }
            QLabel {
                background: transparent;
                border: none;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                font-size: 15px;
                color: #ecf0f1; /* Letras blancas para contraste */
            }
            QLabel[is_value="true"] {
                color: #00ff00; /* Numeros verde fosforescente estilo cajero */
                background-color: #000000; /* Fondo negro tipo pantalla digital */
                border: 2px inset #7f8c8d;
                padding: 4px;
                font-size: 18px;
                font-family: 'Consolas', 'Courier New', monospace; /* Letra digital */
                font-weight: bold;
            }
        \"\"\")
"""

    new_content = content[:start_idx] + new_style + content[end_idx:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Theme applied successfully.")

if __name__ == "__main__":
    main()
