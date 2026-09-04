from dbfread import DBF
import json
import os

res = {}
tables = ['aventa.dbf', 'avenitem.dbf', 'cobranza.dbf', 'caja.dbf']

for f in tables:
    try:
        table = DBF(os.path.join('data', f), load=False)
        res[f] = [{'name': fld.name, 'type': fld.type, 'length': fld.length} for fld in table.fields]
    except Exception as e:
        res[f] = str(e)

with open('schema_ventas.json', 'w') as out:
    json.dump(res, out, indent=2)
