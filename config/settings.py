import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env en la carpeta raíz de Chats
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    INDEX_NAME = "productos-index"
    PINECONE_DIMENSION = 1536
    PINECONE_METRIC = "cosine"
    PINECONE_CLOUD = 'aws'
    PINECONE_REGION = 'us-east-1'
    VENTAS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'ventas.json')

settings = Settings()
