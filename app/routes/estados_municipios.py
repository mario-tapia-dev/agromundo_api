from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("estados_municipios", __name__)

# ─────────────────────────────────────────
# GET /estados_municipios/ → Listar todos los estados
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_estados():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                e.id_estado,
                e.nombre
            FROM estados e
            ORDER BY e.id_estado ASC
        """)
        estados = cur.fetchall()
        return success(data=estados, message="Estados obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /estados_municipios/<id> → Listar todos los municipios de un estado
# ─────────────────────────────────────────
@bp.route("/<int:id_estado>", methods=["GET"])
def listar_municipios_por_estado(id_estado):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                m.id_municipio,
                m.nombre
            FROM municipios m
            WHERE id_estado = %s 
            ORDER BY m.id_municipio ASC
        """, (id_estado,))
        municipios = cur.fetchall()
        return success(data=municipios, message="Municipios obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
