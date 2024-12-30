from flask import Flask, request, jsonify
import sys
import json
from services.pinecone_service import PineconeService
from services.openai_service import OpenAIService
from functions.product_search import ProductSearch
from functions.order_creation import OrderCreation
from utils.helpers import cargar_json

app = Flask(__name__)

# Almacenaremos las conversaciones en RAM. En producción conviene algo más robusto (DB/Redis).
conversations = {}

# Inicializar servicios
pinecone_service = PineconeService()
openai_service = OpenAIService()

# Inicializar funciones
product_search = ProductSearch(pinecone_service, openai_service)
order_creation = OrderCreation()

# Definir tools con JSON Schema (igual que en main.py)
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

# Mensaje system inicial (igual que en main.py)
SYSTEM_MESSAGE = {
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

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Endpoint para interactuar con la lógica del asistente que antes estaba en main.py.
    - Espera JSON con al menos {"session_id": "abc123", "user_input": "Hola, quiero comprar..."}.
    - Devuelve la respuesta final del asistente después de ejecutar las funciones correspondientes.
    """

    data = request.get_json()
    if not data:
        return jsonify({"error": "Debe enviar un cuerpo JSON."}), 400

    session_id = data.get("session_id")
    user_input = data.get("user_input", "").strip()

    if not session_id:
        return jsonify({"error": "Falta session_id en la petición."}), 400

    # Si el usuario escribe 'salir', finalizamos la conversación
    if user_input.lower() == "salir":
        # Eliminar la conversación de la memoria si existe
        if session_id in conversations:
            del conversations[session_id]
        return jsonify({"message": "Saliendo..."}), 200

    # Obtener o crear el historial de mensajes para esta sesión
    if session_id not in conversations:
        # Creamos una nueva conversación con el mensaje system inicial
        conversations[session_id] = [SYSTEM_MESSAGE]

    messages = conversations[session_id]

    # Agregar el mensaje del usuario al historial
    messages.append({"role": "user", "content": user_input})

    # 1) Llamar a la API de OpenAI con la lista actualizada de mensajes
    response = openai_service.chat_completion(messages=messages, functions=tools)

    if response is None:
        return jsonify({"error": "No se obtuvo respuesta de OpenAI."}), 500

    assistant_msg = response
    tool_call = assistant_msg.get("function_call")

    if not tool_call:
        # Respuesta normal (sin función)
        assistant_content = assistant_msg.get("content")
        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})
            return jsonify({"assistant": assistant_content})
        else:
            return jsonify({"assistant": "", "info": "Asistente no devolvió texto."})
    else:
        # La IA está invocando una función
        fn_name = tool_call.get("name")
        fn_args_str = tool_call.get("arguments")

        fn_args = cargar_json(fn_args_str)

        funcion_resultado = None

        if fn_name == "buscar_producto":
            query_text = fn_args.get("query", "")
            funcion_resultado = product_search.buscar_producto(query_text)

        elif fn_name == "crear_pedido":
            datos_cliente = fn_args.get("datos_cliente", {})
            productos = fn_args.get("productos", [])
            funcion_resultado = order_creation.crear_pedido(datos_cliente, productos)

        else:
            funcion_resultado = {"error": f"Función '{fn_name}' no existe."}

        # Crear un mensaje de función con el resultado
        tool_message = {
            "role": "function",
            "name": fn_name,
            "content": json.dumps(funcion_resultado)
        }
        messages.append(tool_message)

        # 2) Llamar nuevamente a la API de OpenAI con la respuesta de la función
        response2 = openai_service.chat_completion(messages=messages, functions=tools)
        if response2 is None:
            return jsonify({"error": "No se obtuvo respuesta de OpenAI en la segunda llamada."}), 500

        msg2 = response2
        tool_call2 = msg2.get("function_call")

        if not tool_call2:
            # Respuesta final del asistente
            assistant_content2 = msg2.get("content")
            if assistant_content2:
                messages.append({"role": "assistant", "content": assistant_content2})
                return jsonify({"assistant": assistant_content2})
            else:
                return jsonify({"assistant": "", "info": "Asistente no devolvió texto en la segunda llamada."})
        else:
            # La IA hace una segunda llamada a función
            fn2_name = tool_call2.get("name")
            fn2_args_str = tool_call2.get("arguments")

            fn2_args = cargar_json(fn2_args_str)

            if fn2_name == "buscar_producto":
                query_text2 = fn2_args.get("query", "")
                funcion_resultado2 = product_search.buscar_producto(query_text2)

            elif fn2_name == "crear_pedido":
                datos_cliente2 = fn2_args.get("datos_cliente", {})
                productos2 = fn2_args.get("productos", [])
                funcion_resultado2 = order_creation.crear_pedido(datos_cliente2, productos2)
            else:
                funcion_resultado2 = {"error": f"Función '{fn2_name}' no existe."}

            tool_message2 = {
                "role": "function",
                "name": fn2_name,
                "content": json.dumps(funcion_resultado2)
            }
            messages.append(tool_message2)

            # 3) Tercera llamada
            response3 = openai_service.chat_completion(messages=messages, functions=tools)
            if response3 is None:
                return j
