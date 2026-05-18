import os
import sys
import json

def resource_path(relative_path):
    """ Encuentra imágenes dentro del ejecutable """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def obtener_ruta_datos(nombre_archivo):
    """ Ruta blindada en Windows (AppData) """
    carpeta_segura = os.path.join(os.environ['APPDATA'], 'COMUNAPP')
    if not os.path.exists(carpeta_segura):
        os.makedirs(carpeta_segura)
    return os.path.join(carpeta_segura, nombre_archivo)

def cargar_json(nombre_archivo, valor_por_defecto):
    """ Lee datos de forma segura """
    ruta = obtener_ruta_datos(nombre_archivo)
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return valor_por_defecto
    return valor_por_defecto

def guardar_json(nombre_archivo, datos):
    """ Escribe datos en el disco duro de forma permanente """
    ruta = obtener_ruta_datos(nombre_archivo)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4)