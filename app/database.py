import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Crea y retorna una conexión a la base de datos.
    RealDictCursor hace que los resultados lleguen como
    diccionarios en lugar de tuplas, por ejemplo:
        Tupla:      (1, 'Juan', 'García')
        Diccionario: {'id': 1, 'nombre': 'Juan', 'apellido': 'García'}
    """
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor
    )
    return connection
