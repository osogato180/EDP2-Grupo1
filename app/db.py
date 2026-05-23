import psycopg2
import os

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def obtener_productos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, stock, precio FROM productos")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "nombre": r[1],
            "stock": r[2],
            "precio": float(r[3])
        }
        for r in rows
    ]

def insertar_producto(id, nombre, stock, precio):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO productos (id, nombre, stock, precio) VALUES (%s, %s, %s, %s)",
        (id, nombre, stock, precio)
    )
    conn.commit()
    cur.close()
    conn.close()

def eliminar_producto(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM productos WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
