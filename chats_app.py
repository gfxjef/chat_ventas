# /home/gfxjef/Chats/chats_app.py

import sys
import os

# Obtener la ruta absoluta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))

# Agregar el directorio actual al sys.path
if current_dir not in sys.path:
    sys.path.append(current_dir)

from flask import Flask, request, jsonify
from services.pinecone_service import PineconeService
from services.openai_service import OpenAIService
from functions.product_search import ProductSearch
from functions.order_creation import OrderCreation
from utils.helpers import cargar_json
import json

app = Flask(__name__)

# Inicializar servicios y funciones
pinecone_service = PineconeService()
openai_service = OpenAIService()

product_search = ProductSearch(pinecone_service, openai_service)
order_creation = OrderCreation()

# Definir tools con JSON Schema
tools = [
    {
        "name": "buscar_producto",
        "description": "Busca productos en Pinecone dada una query y retorna una lista con sus datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto que describe lo que el usuario busca, e.g. 'coca cola'."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "name": "crear_pedido",
        "description": "Crea un pedido con los datos del cliente y los productos elegidos.",
        "parameters": {
            "type": "object",
            "properties": {
                "datos_cliente": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string"},
                        "telefono": {"type": "string"},
                        "direccion": {"type": "string"},
                        "modalidad_entrega": {"type": "string"}
                    },
                    "required": ["nombre", "telefono", "direccion", "modalidad_entrega"]
                },
                "productos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string"},
                            "sku": {"type": "string"},
                            "precio_bayovar": {"type": "number"}
                        },
                        "required": ["nombre", "sku", "precio_bayovar"]
                    }
                }
            },
            "required": ["datos_cliente", "productos"],
            "additionalProperties": False
        }
    }
]

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('mensaje', '').strip()

    if not user_input:
        return jsonify({"error": "El campo 'mensaje' está vacío."}), 400
    if user_input.lower() == "salir":
        return jsonify({"message": "Saliendo..."}), 200

    # Inicializar historial de mensajes si no existe
    if 'messages' not in data:
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente de ventas que puede buscar productos en Pinecone y crear pedidos.\n"
                    "Reglas:\n"
                    "- Usa la función 'buscar_producto' cuando el usuario te pida buscar algo (por ejemplo, '¿Tienes alguna coca cola?').\n"
                    "- Cuando el usuario confirme la compra y proporcione sus datos, usa la función 'crear_pedido'.\n"
                    "- No muestres el SKU en la conversación, pero sí inclúyelo cuando crees el pedido.\n"
                    "- Muestra solo precios de Bayóvar (precio_bayovar).\n"
                    "- Después de crear el pedido, saluda con un mensaje como 'Perfecto, hemos tomado tu pedido...'\n"
                )
            }
        ]
    else:
        messages = data['messages']

    # Añadir mensaje del usuario
    messages.append({"role": "user", "content": user_input})

    # Llamar a la API de OpenAI
    response = openai_service.chat_completion(
        messages=messages,
        functions=tools
    )

    if response is None:
        return jsonify({"error": "Error al comunicarse con OpenAI."}), 500

    assistant_msg = response
    tool_call = assistant_msg.get("function_call")

    if not tool_call:
        # Respuesta normal
        assistant_content = assistant_msg.get("content")
        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})
            return jsonify({
                "respuesta": assistant_content,
                "messages": messages
            })
        else:
            return jsonify({"error": "El asistente no devolvió texto."}), 500

    # IA está invocando una función
    fn_name = tool_call.get("name")
    fn_args_str = tool_call.get("arguments")

    fn_args = cargar_json(fn_args_str)

    # Ejecutar la función real
    if fn_name == "buscar_producto":
        query_text = fn_args.get("query", "")
        funcion_resultado = product_search.buscar_producto(query_text)

    elif fn_name == "crear_pedido":
        datos_cliente = fn_args.get("datos_cliente", {})
        productos = fn_args.get("productos", [])
        funcion_resultado = order_creation.crear_pedido(datos_cliente, productos)

    else:
        funcion_resultado = {"error": f"Función '{fn_name}' no existe."}

    # Crear mensaje de la función
    tool_message = {
        "role": "function",
        "name": fn_name,
        "content": json.dumps(funcion_resultado)
    }

    # Añadir mensajes al historial
    messages.append(tool_message)

    # Llamar nuevamente a la API con la respuesta de la función
    response2 = openai_service.chat_completion(
        messages=messages,
        functions=tools
    )

    if response2 is None:
        return jsonify({"error": "Error al comunicarse con OpenAI en la segunda llamada."}), 500

    msg2 = response2
    tool_call2 = msg2.get("function_call")

    if not tool_call2:
        # Respuesta final del Asistente
        assistant_content2 = msg2.get("content")
        if assistant_content2:
            messages.append({"role": "assistant", "content": assistant_content2})
            return jsonify({
                "respuesta": assistant_content2,
                "messages": messages
            })
        else:
            return jsonify({"error": "El asistente no devolvió texto en la segunda llamada."}), 500
    else:
        # Manejar más llamadas si es necesario
        return jsonify({"error": "La IA ha realizado múltiples llamadas a funciones. Considera implementar un bucle para manejar más casos."}), 500

# Solo ejecutar el servidor Flask si este archivo es ejecutado directamente
if __name__ == "__main__":
    app.run(debug=True)
