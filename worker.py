import pika
import smtplib
from email.mime.text import MIMEText
import json
import time

time.sleep(10)  # espera a que RabbitMQ esté listo

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq")
)
channel = connection.channel()
channel.queue_declare(queue="stock_alerts")

def enviar_email(producto):
    msg = MIMEText(
        f"⚠️ ALERTA DE STOCK BAJO\n\n"
        f"Producto: {producto['id']} - {producto['nombre']}\n"
        f"Stock actual: {producto['stock']}"
    )
    msg["Subject"] = "Alerta de Inventario"
    msg["From"] = "alertas@inventario.com"
    msg["To"] = "admin@empresa.com"

    with smtplib.SMTP("mailhog", 1025) as server:
        server.send_message(msg)

def callback(ch, method, properties, body):
    producto = json.loads(body)
    enviar_email(producto)

channel.basic_consume(
    queue="stock_alerts",
    on_message_callback=callback,
    auto_ack=True
)

print("📩 Esperando alertas de stock...")
channel.start_consuming()