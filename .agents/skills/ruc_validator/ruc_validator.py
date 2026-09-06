import re
from typing import Optional, Tuple, Dict, Any

def calcular_dv_ruc(ruc_base: str, basemax: int = 11) -> int:
    """
    Calcula el Dígito Verificador (DV) según el algoritmo oficial Módulo 11
    de la DNIT / SET Paraguay (Resolución General 1530/05).
    
    :param ruc_base: Cadena con el RUC sin el DV (ej. '80001234' o '4455667')
    :param basemax: Base ponderada máxima (estándar 11)
    :return: Dígito Verificador (entero 0 a 9)
    """
    if not ruc_base:
        return 0
    
    # Limpiar cualquier caracter que no sea alfanumérico
    ruc_clean = str(ruc_base).strip().split('-')[0]
    
    total = 0
    factor = 2
    
    # Recorrer de derecha a izquierda
    for char in reversed(ruc_clean):
        if char.isdigit():
            k = int(char)
        else:
            # En caso de RUC alfanumérico tradicional
            k = ord(char.upper())
        total += k * factor
        factor = 2 if factor >= basemax else factor + 1
        
    resto = total % 11
    if resto > 1:
        return 11 - resto
    else:
        return 0

def formatear_ruc(ruc_input: str) -> str:
    """
    Normaliza y formatea una cadena a RUC paraguayo estándar 'NUMERO-DV'.
    - Si el usuario ingresa con guion (ej. '806333-8'), extrae y valida.
    - Si el usuario ingresa todos los números juntos con el DV al final (ej. '8063338' o '32009674'),
      detecta automáticamente si el último dígito coincide con el Módulo 11 de los dígitos anteriores.
    - Si el usuario ingresa solo el número base (ej. '806333' o '3200967'), calcula y añade el DV.
    """
    if not ruc_input:
        return ""
    
    texto = str(ruc_input).strip()
    if '-' in texto:
        partes = texto.split('-')
        base = re.sub(r'\D', '', partes[0])
        if not base:
            return ""
        dv_calculado = str(calcular_dv_ruc(base))
        return f"{base}-{dv_calculado}"
    else:
        clean = re.sub(r'\D', '', texto)
        if not clean:
            return ""
            
        # Detección inteligente: ¿El último dígito ya es el DV? (ej. 8063338 -> 806333 con DV 8)
        if len(clean) >= 6:
            posible_base = clean[:-1]
            posible_dv = clean[-1]
            if str(calcular_dv_ruc(posible_base)) == posible_dv:
                return f"{posible_base}-{posible_dv}"
                
        dv_calculado = str(calcular_dv_ruc(clean))
        return f"{clean}-{dv_calculado}"

def validar_ruc(ruc_completo: str) -> Tuple[bool, Optional[str]]:
    """
    Valida si un RUC con formato 'NUMERO-DV' tiene el Dígito Verificador correcto.
    :return: (es_valido, mensaje_o_dv_esperado)
    """
    if not ruc_completo or '-' not in ruc_completo:
        return False, "Formato inválido. Debe contener guion (ej: 80001234-8)."
    
    partes = ruc_completo.split('-')
    base = partes[0].strip()
    dv_provisto = partes[1].strip()
    
    if not base.isdigit():
        return False, "La base del RUC debe contener solo dígitos."
    
    dv_esperado = str(calcular_dv_ruc(base))
    if dv_provisto == dv_esperado:
        return True, "RUC válido."
    else:
        return False, f"Dígito verificador incorrecto. El DV correcto es -{dv_esperado}."

def buscar_en_padron(db_session, busqueda: str, limite: int = 10):
    """
    Busca un contribuyente en la tabla local padron_ruc por RUC o por Razón Social.
    """
    import models
    from database import strip_accents
    from sqlalchemy import func
    
    termino = str(busqueda).strip()
    if not termino:
        return []
    
    clean_termino = strip_accents(termino)
    base_limpia = termino.split('-')[0].strip() if '-' in termino else termino
    
    query = db_session.query(models.TaxpayerRegistry).filter(
        (models.TaxpayerRegistry.ruc == base_limpia) |
        (models.TaxpayerRegistry.ruc.like(f"%{base_limpia}%")) |
        (func.unaccent(models.TaxpayerRegistry.razon_social).like(f"%{clean_termino}%"))
    ).limit(limite).all()
    
    return query

import urllib.request
import json

def consultar_ruc_dnit_online(ruc_query: str, timeout: int = 3) -> Optional[Dict[str, Any]]:
    """
    Consulta en tiempo real la base oficial de contribuyentes de Paraguay (DNIT/SET)
    mediante los servicios públicos en línea de consulta de RUC.
    Soporta número base, RUC completo con guion o RUC pegado sin guion (ej. 8063338).
    """
    if not ruc_query:
        return None
        
    raw_str = str(ruc_query).strip()
    clean_digits = re.sub(r'\D', '', raw_str)
    if not clean_digits:
        return None
        
    candidates = []
    if '-' in raw_str:
        candidates.append(raw_str.split('-')[0].strip())
    else:
        # Si el último dígito coincide con el Módulo 11 de los anteriores (ej. 8063338 -> 806333)
        if len(clean_digits) >= 6:
            prefix = clean_digits[:-1]
            last_d = clean_digits[-1]
            if str(calcular_dv_ruc(prefix)) == last_d:
                candidates.append(prefix)
        candidates.append(clean_digits)
        
    # 1. Intentar consulta directa en turuc.com.py con cada candidato
    for c in candidates:
        try:
            url = f"https://turuc.com.py/api/contribuyente/{c}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data and data.get('data'):
                        d = data['data']
                        return {
                            'ruc': str(d.get('doc')),
                            'dv': str(d.get('dv')),
                            'razon_social': str(d.get('razonSocial', '')).strip().upper(),
                            'estado': str(d.get('estado', 'ACTIVO')).upper()
                        }
        except Exception:
            pass
            
    # 2. Intentar consulta por búsqueda en ruc.sun.com.py como respaldo
    try:
        url_search = f"https://ruc.sun.com.py/api/search?q={clean_digits}"
        req = urllib.request.Request(url_search, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data and data.get('results'):
                    first = data['results'][0]
                    return {
                        'ruc': str(first.get('ruc')),
                        'dv': str(first.get('dv')),
                        'razon_social': str(first.get('name', '')).strip().upper(),
                        'estado': str(first.get('state', 'ACTIVO')).upper()
                    }
    except Exception:
        pass
        
    return None

def obtener_contribuyente(db_session, ruc_base: str, auto_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Busca un contribuyente primero en la base local SQLite (padron_ruc) y,
    si no está presente, consulta la base de datos de la DNIT en línea.
    Si se encuentra en línea y auto_cache=True, lo guarda automáticamente en SQLite.
    """
    import models
    raw_str = str(ruc_base).strip()
    clean_digits = re.sub(r'\D', '', raw_str)
    if not clean_digits:
        return None
        
    # Generar candidatos de búsqueda (ej. para '8063338', probar '806333' y '8063338')
    candidates = []
    if '-' in raw_str:
        candidates.append(raw_str.split('-')[0].strip())
    else:
        if len(clean_digits) >= 6:
            prefix = clean_digits[:-1]
            last_d = clean_digits[-1]
            if str(calcular_dv_ruc(prefix)) == last_d:
                candidates.append(prefix)
        candidates.append(clean_digits)
        
    # 1. Buscar en SQLite local
    for c in candidates:
        local = db_session.query(models.TaxpayerRegistry).filter_by(ruc=c).first()
        if local:
            return {
                'ruc': local.ruc,
                'dv': local.dv,
                'razon_social': local.razon_social,
                'estado': local.estado,
                'origen': 'LOCAL'
            }
        
    # 2. Consultar en línea DNIT
    online_data = consultar_ruc_dnit_online(raw_str)
    if online_data:
        online_data['origen'] = 'ONLINE'
        if auto_cache:
            try:
                nuevo = models.TaxpayerRegistry(
                    ruc=online_data['ruc'],
                    dv=online_data['dv'],
                    razon_social=online_data['razon_social'],
                    estado=online_data.get('estado', 'ACTIVO')[:1]
                )
                db_session.add(nuevo)
                db_session.commit()
            except Exception:
                db_session.rollback()
        return online_data
        
    return None

