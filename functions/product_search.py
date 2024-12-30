# functions/product_search.py
from services.pinecone_service import PineconeService
from services.openai_service import OpenAIService
import json

class ProductSearch:
    def __init__(self, pinecone_service: PineconeService, openai_service: OpenAIService):
        self.pinecone = pinecone_service
        self.openai = openai_service

    def buscar_producto(self, query: str):
        embedding = self.openai.generar_embedding(query)
        if embedding is None:
            return {"message": "Error generando embedding."}
        
        matches = self.pinecone.query_index(embedding)
        if matches is None:
            return {"message": "Error al consultar Pinecone."}
        
        productos_encontrados = []
        for match in matches:
            meta = match.metadata
            nombre = meta.get("nombre", "Producto sin nombre")
            sku = meta.get("sku", "SKU-no-disponible")
            precio_bayovar = meta.get("precio_base", 0.0)
            
            # Manejo adicional si "atributos" está presente
            if precio_bayovar == 0.0 and "atributos" in meta:
                try:
                    atributos = json.loads(meta["atributos"])
                    precio_bayovar = atributos.get("precio_base", 0.0)
                except:
                    pass
            
            producto = {
                "nombre": nombre,
                "sku": sku,
                "precio_bayovar": precio_bayovar
            }
            productos_encontrados.append(producto)
        
        if productos_encontrados:
            return {"productos_encontrados": productos_encontrados}
        else:
            return {"message": "No se encontraron productos que coincidan con la búsqueda."}
