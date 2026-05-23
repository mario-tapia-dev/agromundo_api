import os
import requests

def enviar_alerta_stock(descripcion_producto, nombre_almacen, stock_actual, min_stock):

    api_key = os.getenv("RESEND_API_KEY")
    remitente = os.getenv("MAIL_SENDER")
    destinatario = os.getenv("MAIL_RECEIVER")

    asunto = f"⚠️ Alerta de stock mínimo — {descripcion_producto}"

    cuerpo = f"""
    Se ha detectado que el siguiente producto ha alcanzado su stock mínimo:

    Producto:       {descripcion_producto}
    Almacén:        {nombre_almacen}
    Stock actual:   {stock_actual}
    Stock mínimo:   {min_stock}

    Por favor tome las medidas necesarias para reabastecer el inventario.
    """

    try:

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": remitente,
                "to": destinatario,
                "subject": asunto,
                "text": cuerpo
            }
        )

        print(response.status_code)
        print(response.text)

    except Exception as e:
        print(f"Error al enviar alerta de stock: {str(e)}")
