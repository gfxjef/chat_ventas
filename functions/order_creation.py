# functions/order_creation.py
import uuid
import os
import json
from config.settings import settings

class OrderCreation:
    def __init__(self):
        self.archivo_ventas = settings.VENTAS_FILE
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(self.archivo_ventas), exist_ok=True)
    
    def crear_pedido(self, datos_cliente: dict, productos: list):
        id_unico = str(uuid.uuid4())[:8]
        
        pedido = {
            "Pedido": {
                "accion": "agregar_pedido",
                "id_unico": id_unico,
                "datos_cliente": datos_cliente,
                "productos": productos
            }
        }
        
        try:
            if os.path.exists(self.archivo_ventas):
                with open(self.archivo_ventas, 'r', encoding='utf-8') as f:
                    ventas = json.load(f)
            else:
                ventas = []
            
            ventas.append(pedido)
            
            with open(self.archivo_ventas, 'w', encoding='utf-8') as f:
                json.dump(ventas, f, indent=4, ensure_ascii=False)
            
            print(f"Pedido {id_unico} agregado exitosamente a {self.archivo_ventas}.")
        except Exception as e:
            print(f"Error al escribir en {self.archivo_ventas}: {e}")
        
        return pedido
