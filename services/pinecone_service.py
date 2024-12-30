from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from config.settings import settings
import sys

class PineconeService:
    def __init__(self):
        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.setup_index()
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar el cliente de Pinecone: {e}")
            sys.exit(1)

    def setup_index(self):
        try:
            if settings.INDEX_NAME not in self.pc.list_indexes():
                self.pc.create_index(
                    name=settings.INDEX_NAME,
                    dimension=settings.PINECONE_DIMENSION,
                    metric=settings.PINECONE_METRIC,
                    spec=ServerlessSpec(
                        cloud=settings.PINECONE_CLOUD,
                        region=settings.PINECONE_REGION
                    )
                )
                print(f"Índice '{settings.INDEX_NAME}' creado exitosamente.")
            else:
                print(f"Índice '{settings.INDEX_NAME}' ya existe.")
            self.index = self.pc.Index(settings.INDEX_NAME)
        except Exception as e:
            if "already exists" in str(e):
                print(f"Índice '{settings.INDEX_NAME}' ya existe.")
                self.index = self.pc.Index(settings.INDEX_NAME)
            else:
                print(f"[ERROR] No se pudo crear/listar índice Pinecone: {e}")
                sys.exit(1)

    def query_index(self, vector, top_k=5, namespace=""):
        try:
            response = self.index.query(
                vector=vector,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                namespace=namespace
            )
            return response.matches
        except Exception as e:
            print(f"[ERROR] Error al consultar Pinecone: {e}")
            return None
