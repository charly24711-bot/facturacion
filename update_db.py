import sqlite3

conn = sqlite3.connect('stock_control.db')
conn.execute("UPDATE products SET image_path = 'assets/images/escoba.png' WHERE art_codigo = '000014'")
conn.execute("UPDATE products SET image_path = 'assets/images/arroz.png' WHERE art_codigo = '000043'")
conn.commit()
conn.close()
print("Base de datos actualizada con las rutas de las imagenes.")
