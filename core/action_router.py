from core.gmail.leer import (
    contar_correos_no_leidos,
    remitentes_hoy,
    resumen_correos_hoy,
    leer_ultimo_correo  # 🆕 agregado
)

def ejecutar_accion(intencion, comando=None, contexto=None, filtros=None):
    print("🎯 Ejecutando acción:", intencion)
    print("🔍 Tipo de intención:", type(intencion))

    if not isinstance(intencion, dict):
        return "Lo siento, no entendí lo que quieres hacer."

    accion = intencion.get("accion")
    if accion == "resumen":
        accion = "resumen_hoy"
    print("🔄 Acción original:", accion)
    filtros = intencion.get("filtros") or {}

    # 🆕 Acción: leer último correo
    if accion == "leer_ultimo":
        return f"El correo más reciente es:\n\n{leer_ultimo_correo(contexto['service'])}"

    # Acción: contar no leídos
    if accion == "contar_no_leidos":
        cantidad = contar_correos_no_leidos(contexto["service"])
        return f"Tienes {cantidad} correos sin leer."

    # Acción: remitentes de hoy
    if accion == "remitentes_hoy":
        return remitentes_hoy(contexto["service"])

    # Acción: resumen de correos de hoy
    if accion == "resumen_hoy":
        return resumen_correos_hoy(contexto["service"])

    # 🆕 Acción: detectar correos importantes
    if accion == "correos_importantes":
        raw = resumen_correos_hoy(contexto["service"], cantidad=50)
        urgentes = [
            m for m in raw.split("-----")
            if any(x in m.lower() for x in ["urgente", "importante", "reunión", "responder", "hoy"])
        ]
        if not urgentes:
            return "No hay correos marcados como urgentes o importantes."
        return f"⚠️ Tienes {len(urgentes)} correos importantes:\n\n" + "\n\n".join(urgentes[:3])

    # Acción: listar correos recientes (resumidos)
    if accion == "listar_correos":
        print("✔️ Ejecutando listar_correos con filtros:", filtros)
        raw = resumen_correos_hoy(contexto["service"], cantidad=50)
        lista = [m.strip() for m in raw.split("-----") if m.strip()]

        remitente_filtro = filtros.get("remite", "").lower().strip()
        if remitente_filtro:
            lista = [m for m in lista if remitente_filtro in m.lower()]

        if filtros.get("orden") == "ascendente":
            lista = list(reversed(lista))

        cantidad = filtros.get("cantidad", len(lista))
        lista = lista[:cantidad]

        if not lista:
            return "No encontré correos que coincidan con tu solicitud."

        if cantidad == 1 or len(lista) == 1:
            return f"El correo más reciente es:\n\n{lista[0]}"
        else:
            return f"Aquí tienes los {len(lista)} correos más recientes:\n\n" + "\n\n".join(lista)

    # Acción: buscar correo por remitente
    elif accion in ["buscar_correo", "buscar_correos"]:
        remitente_filtro = filtros.get("remite", "").lower().strip()
        raw = resumen_correos_hoy(contexto["service"], cantidad=10)
        lista = [m.strip() for m in raw.split("-----") if m.strip()]
        encontrados = [m for m in lista if remitente_filtro in m.lower()]

        if not encontrados:
            return f"No encontré correos de {remitente_filtro}."
        return f"El correo más reciente de {remitente_filtro} es:\n\n{encontrados[0]}"

    return "Lo siento, no entendí lo que quieres hacer."
