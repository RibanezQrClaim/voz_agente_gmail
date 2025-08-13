# ✅ Versión final para entorno local
# Utiliza llama-cpp y el modelo quantizado phi-2 para resumir correos y detectar intenciones

import os
from llama_cpp import Llama

# Ruta al modelo local (.gguf)
modelo_path = os.path.join("models", "phi-2.Q4_K_M.gguf")

# Inicializar modelo una sola vez
llm = Llama(
    model_path=modelo_path,
    n_ctx=2048,
    n_threads=4,
    temperature=0.7,
    stop=["</s>", "Usuario:", "Asistente:"]
)

def resumir_texto_llm(texto):
    """
    Usa el modelo local phi-2 para resumir un conjunto de correos.
    El resumen es ejecutivo, claro y breve (máx. 300 caracteres).
    """
    if not texto:
        return "(Sin contenido)"

    prompt = f"""
Usuario: Tienes a continuación varios correos recibidos hoy. Genera un único resumen ejecutivo que sintetice los temas principales en un lenguaje claro y directo, en un máximo de 300 caracteres. No repitas texto literal. Agrupa ideas. Sé sintético.

Correos:
{texto}

Asistente: El resumen ejecutivo de los correos es:
""".strip()

    try:
        resultado = llm(
            prompt=prompt,
            max_tokens=300,
            echo=False
        )

        resumen = resultado["choices"][0]["text"].strip()
        print("🧠 Resumen generado por modelo local:\n", resumen)

        return resumen[:300] + ("..." if len(resumen) > 300 else "")

    except Exception as e:
        print("❌ Error al resumir con modelo local:", e)
        return f"(Error al resumir con modelo local: {e})"


def interpretar_comando(texto):
    """
    Usa el modelo local para interpretar la intención del comando del usuario.
    Devuelve una etiqueta como: leer_ultimo, resumir, sin_leer, importantes, saludos, desconocido
    """
    prompt = f"""
Tu tarea es clasificar el siguiente comando de voz en una sola palabra clave que represente su intención.

Responde solo con una de estas opciones exactas (sin explicar ni agregar nada): leer_ultimo, resumir, sin_leer, importantes, saludos, desconocido.

Ejemplos:

"¿Cuántos correos tengo sin leer?" → sin_leer
"¿Quién me escribió hoy?" → saludos
"Resúmeme los correos de hoy" → resumir
"Lee mi último correo" → leer_ultimo
"¿Tengo correos importantes?" → importantes
"¿Hay algo urgente?" → importantes
"¿Debo responder algo hoy?" → importantes
"¿Tienes algo que destacar hoy?" → importantes
"Cuéntame lo clave de hoy" → resumir

Comando del usuario: {texto}
→
""".strip()

    try:
        resultado = llm(
            prompt=prompt,
            max_tokens=5,
            echo=False
        )
        etiqueta = resultado["choices"][0]["text"].strip().lower()

        print("🔍 Intención detectada:", etiqueta)
        return etiqueta

    except Exception as e:
        print("❌ Error al interpretar el comando:", e)
        return "desconocido"
