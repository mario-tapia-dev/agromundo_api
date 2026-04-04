from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("categorias", __name__)


# ─────────────────────────────────────────
# GET /categorias/ → Listar todas las categorías
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_categorias():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id_cat, nombre
            FROM categorias
            ORDER BY id_cat ASC
        """)
        categorias = cur.fetchall()
        return success(data=categorias, message="Categorías obtenidas correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# GET /categorias/<id> → Detalle de una categoría
# ─────────────────────────────────────────
@bp.route("/<int:id_cat>", methods=["GET"])
def obtener_categoria(id_cat):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id_cat, nombre
            FROM categorias
            WHERE id_cat = %s
        """, (id_cat,))
        categoria = cur.fetchone()
        if categoria is None:
            return error(message="Categoría no encontrada", status=404)
        return success(data=categoria, message="Categoría obtenida correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /categorias/ → Crear una categoría
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_categoria():
    conn = None
    try:
        data = request.get_json()

        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categorias (nombre)
            VALUES (%s)
            RETURNING id_cat
        """, (data["nombre"],))
        conn.commit()
        nuevo_id = cur.fetchone()["id_cat"]
        return success(data={"id_cat": nuevo_id}, message="Categoría creada correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# PUT /categorias/<id> → Actualizar una categoría
# ─────────────────────────────────────────
@bp.route("/<int:id_cat>", methods=["PUT"])
def actualizar_categoria(id_cat):
    conn = None
    try:
        data = request.get_json()

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_cat FROM categorias WHERE id_cat = %s", (id_cat,))
        if cur.fetchone() is None:
            return error(message="Categoría no encontrada", status=404)

        cur.execute("""
            UPDATE categorias SET nombre = %s
            WHERE id_cat = %s
        """, (data["nombre"], id_cat))
        conn.commit()
        return success(message="Categoría actualizada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# DELETE /categorias/<id> → Eliminar una categoría
# ─────────────────────────────────────────
@bp.route("/<int:id_cat>", methods=["DELETE"])
def eliminar_categoria(id_cat):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_cat FROM categorias WHERE id_cat = %s", (id_cat,))
        if cur.fetchone() is None:
            return error(message="Categoría no encontrada", status=404)

        cur.execute("DELETE FROM categorias WHERE id_cat = %s", (id_cat,))
        conn.commit()
        return success(message="Categoría eliminada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
