# utils/helpers.py
import json

def cargar_json(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("[ERROR] No se pudo decodificar el JSON.")
        return {}
