# services/openai_service.py
import openai
import sys
from config.settings import settings

class OpenAIService:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            print("Error: La variable de entorno 'OPENAI_API_KEY' no está configurada.")
            sys.exit(1)
        openai.api_key = settings.OPENAI_API_KEY

    def generar_embedding(self, texto: str):
        try:
            response = openai.Embedding.create(
                input=texto,
                model="text-embedding-ada-002"
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"[ERROR] No se pudo generar embedding para: {texto}\nError: {e}")
            return None

    def chat_completion(self, messages, functions=None, model="gpt-4", function_call="auto"):
        """
        Emula la forma en la que llamas a la API de ChatCompletion en main.py.
        """
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                functions=functions,
                function_call=function_call
            )
            return response.choices[0].message
        except openai.error.OpenAIError as e:
            print(f"Error al llamar a la API de OpenAI: {e}")
            return None
