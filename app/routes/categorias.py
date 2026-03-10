from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


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
            SELECT id_categoria, nombre
            FROM categoria
            ORDER BY id_categoria ASC
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
@bp.route("/<int:id_categoria>", methods=["GET"])
def obtener_categoria(id_categoria):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id_categoria, nombre
            FROM categoria
            WHERE id_categoria = %s
        """, (id_categoria,))
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

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categoria (nombre)
            VALUES (%s)
            RETURNING id_categoria
        """, (data["nombre"],))
        conn.commit()
        nuevo_id = cur.fetchone()["id_categoria"]
        return success(data={"id_categoria": nuevo_id}, message="Categoría creada correctamente", status=201)
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
@bp.route("/<int:id_categoria>", methods=["PUT"])
def actualizar_categoria(id_categoria):
    conn = None
    try:
        data = request.get_json()

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_categoria FROM categoria WHERE id_categoria = %s", (id_categoria,))
        if cur.fetchone() is None:
            return error(message="Categoría no encontrada", status=404)

        cur.execute("""
            UPDATE categoria SET nombre = %s
            WHERE id_categoria = %s
        """, (data["nombre"], id_categoria))
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
@bp.route("/<int:id_categoria>", methods=["DELETE"])
def eliminar_categoria(id_categoria):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_categoria FROM categoria WHERE id_categoria = %s", (id_categoria,))
        if cur.fetchone() is None:
            return error(message="Categoría no encontrada", status=404)

        cur.execute("DELETE FROM categoria WHERE id_categoria = %s", (id_categoria,))
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
