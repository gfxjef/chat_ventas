# main.py
from services.pinecone_service import PineconeService
from services.openai_service import OpenAIService
from functions.product_search import ProductSearch
from functions.order_creation import OrderCreation
from utils.helpers import cargar_json
import json
import sys

def main():
    # Inicializar servicios
    pinecone_service = PineconeService()
    openai_service = OpenAIService()
    
    # Inicializar funciones
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
    
    # Mensajes iniciales (system)
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
    
    print("\n=== Asistente iniciado. Escribe 'salir' para terminar ===\n")
    
    while True:
        user_input = input("Usuario: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "salir":
            print("Saliendo...")
            sys.exit(0)
        
        # Añadir mensaje del usuario
        messages.append({"role": "user", "content": user_input})
        
        # Llamar a la API de OpenAI
        response = openai_service.chat_completion(
            messages=messages,
            functions=tools
        )
        
        if response is None:
            continue
        
        assistant_msg = response
        tool_call = assistant_msg.get("function_call")
        
        if not tool_call:
            # Respuesta normal
            assistant_content = assistant_msg.get("content")
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})
                print(f"\nAsistente: {assistant_content}\n")
            else:
                print("\nAsistente no devolvió texto.\n")
            continue
        
        # IA está invocando una función
        fn_name = tool_call.get("name")
        fn_args_str = tool_call.get("arguments")
        
        print(f"\n[DEBUG] La IA llama a la función '{fn_name}' con args: {fn_args_str}\n")
        
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
            continue
        
        msg2 = response2
        tool_call2 = msg2.get("function_call")
        
        if not tool_call2:
            # Respuesta final del Asistente
            assistant_content2 = msg2.get("content")
            if assistant_content2:
                messages.append({"role": "assistant", "content": assistant_content2})
                print(f"\nAsistente: {assistant_content2}\n")
            else:
                print("\nAsistente no devolvió texto en la segunda llamada.\n")
        else:
            # La IA está invocando otra función
            fn2_name = tool_call2.get("name")
            fn2_args_str = tool_call2.get("arguments")
            
            print(f"\n[DEBUG] La IA llama a la función '{fn2_name}' con args: {fn2_args_str}\n")
            
            fn2_args = cargar_json(fn2_args_str)
            
            # Ejecutar la segunda función
            if fn2_name == "buscar_producto":
                query_text2 = fn2_args.get("query", "")
                funcion_resultado2 = product_search.buscar_producto(query_text2)
            
            elif fn2_name == "crear_pedido":
                datos_cliente2 = fn2_args.get("datos_cliente", {})
                productos2 = fn2_args.get("productos", [])
                funcion_resultado2 = order_creation.crear_pedido(datos_cliente2, productos2)
            
            else:
                funcion_resultado2 = {"error": f"Función '{fn2_name}' no existe."}
            
            # Crear segundo mensaje de la función
            tool_message2 = {
                "role": "function",
                "name": fn2_name,
                "content": json.dumps(funcion_resultado2)
            }
            
            # Añadir mensajes al historial
            messages.append(tool_message2)
            
            # Tercera llamada a la API
            response3 = openai_service.chat_completion(
                messages=messages,
                functions=tools
            )
            
            if response3 is None:
                continue
            
            msg3 = response3
            tool_call3 = msg3.get("function_call")
            
            if not tool_call3:
                # Respuesta final del Asistente
                assistant_content3 = msg3.get("content")
                if assistant_content3:
                    messages.append({"role": "assistant", "content": assistant_content3})
                    print(f"\nAsistente: {assistant_content3}\n")
                else:
                    print("\nAsistente no devolvió texto en la tercera llamada.\n")
            else:
                # Manejar más llamadas si es necesario
                print("\n[INFO] La IA ha realizado múltiples llamadas a funciones. "
                      "Considera implementar un bucle para manejar más casos.\n")

if __name__ == "__main__":
    main()
