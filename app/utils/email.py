import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
 
def enviar_alerta_stock(descripcion_producto, nombre_almacen, stock_actual, min_stock):
    remitente = os.getenv("MAIL_SENDER")
    destinatario = os.getenv("MAIL_RECEIVER")
    password = os.getenv("MAIL_PASSWORD")
 
    asunto = f"⚠️ Alerta de stock mínimo — {descripcion_producto}"
 
    cuerpo = f"""
    Se ha detectado que el siguiente producto ha alcanzado su stock mínimo:
 
    Producto:       {descripcion_producto}
    Almacén:        {nombre_almacen}
    Stock actual:   {stock_actual}
    Stock mínimo:   {min_stock}
 
    Por favor tome las medidas necesarias para reabastecer el inventario.
    """
 
    msg = MIMEMultipart()
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.attach(MIMEText(cuerpo, "plain"))
 
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remitente, password)
            smtp.sendmail(remitente, destinatario, msg.as_string())
    except Exception as e:
        print(f"Error al enviar alerta de stock: {str(e)}")
