from flask import Flask, jsonify
import psycopg2
import os

app = Flask(__name__)

conn = psycopg2.connect(
    host=os.environ.get("DB_HOST"),
    database=os.environ.get("DB_NAME"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD")
)

@app.route('/')
def home():
    return jsonify({"mensaje": "Sistema de ventas en la nube funcionando correctamente"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
