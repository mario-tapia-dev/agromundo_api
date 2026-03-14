from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("subcategorias", __name__)


# ─────────────────────────────────────────
# GET /subcategorias/ → Listar todas las subcategorías
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_subcategorias():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                s.id_subcategoria,
                s.nombre,
                s.descripcion,
                s.valor_numerico,
                s.unidad,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_categoria', c.id_categoria, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_categoria IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM subcategoria s
            LEFT JOIN categoria_subcategoria cs ON s.id_subcategoria = cs.id_subcategoria
            LEFT JOIN categoria c ON cs.id_categoria = c.id_categoria
            GROUP BY s.id_subcategoria
            ORDER BY s.id_subcategoria ASC
        """)
        subcategorias = cur.fetchall()
        return success(data=subcategorias, message="Subcategorías obtenidas correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# GET /subcategorias/<id> → Detalle de una subcategoría
# ─────────────────────────────────────────
@bp.route("/<int:id_subcategoria>", methods=["GET"])
def obtener_subcategoria(id_subcategoria):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                s.id_subcategoria,
                s.nombre,
                s.descripcion,
                s.valor_numerico,
                s.unidad,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_categoria', c.id_categoria, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_categoria IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM subcategoria s
            LEFT JOIN categoria_subcategoria cs ON s.id_subcategoria = cs.id_subcategoria
            LEFT JOIN categoria c ON cs.id_categoria = c.id_categoria
            WHERE s.id_subcategoria = %s
            GROUP BY s.id_subcategoria
        """, (id_subcategoria,))
        subcategoria = cur.fetchone()
        if subcategoria is None:
            return error(message="Subcategoría no encontrada", status=404)
        return success(data=subcategoria, message="Subcategoría obtenida correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /subcategorias/ → Crear una subcategoría
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_subcategoria():
    conn = None
    try:
        data = request.get_json()

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        # categorias_ids es opcional, pero si viene debe ser una lista
        categorias_ids = data.get("categorias_ids", [])

        conn = get_connection()
        cur = conn.cursor()

        # Insertar la subcategoría
        cur.execute("""
            INSERT INTO subcategoria (nombre, descripcion, valor_numerico, unidad)
            VALUES (%s, %s, %s, %s)
            RETURNING id_subcategoria
        """, (
            data["nombre"],
            data.get("descripcion"),
            data.get("valor_numerico"),
            data.get("unidad")
        ))
        nuevo_id = cur.fetchone()["id_subcategoria"]

        # Insertar relaciones con categorías si vienen
        for id_categoria in categorias_ids:
            cur.execute("""
                INSERT INTO categoria_subcategoria (id_categoria, id_subcategoria)
                VALUES (%s, %s)
            """, (id_categoria, nuevo_id))

        conn.commit()
        return success(data={"id_subcategoria": nuevo_id}, message="Subcategoría creada correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# PUT /subcategorias/<id> → Actualizar una subcategoría
# ─────────────────────────────────────────
@bp.route("/<int:id_subcategoria>", methods=["PUT"])
def actualizar_subcategoria(id_subcategoria):
    conn = None
    try:
        data = request.get_json()

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_subcategoria FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        if cur.fetchone() is None:
            return error(message="Subcategoría no encontrada", status=404)

        # Actualizar datos principales
        cur.execute("""
            UPDATE subcategoria SET
                nombre = %s,
                descripcion = %s,
                valor_numerico = %s,
                unidad = %s
            WHERE id_subcategoria = %s
        """, (
            data["nombre"],
            data.get("descripcion"),
            data.get("valor_numerico"),
            data.get("unidad"),
            id_subcategoria
        ))

        # Si vienen categorias_ids, actualizamos las relaciones
        # Primero borramos las existentes y luego insertamos las nuevas
        if "categorias_ids" in data:
            cur.execute("DELETE FROM categoria_subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
            for id_categoria in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO categoria_subcategoria (id_categoria, id_subcategoria)
                    VALUES (%s, %s)
                """, (id_categoria, id_subcategoria))

        conn.commit()
        return success(message="Subcategoría actualizada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# DELETE /subcategorias/<id> → Eliminar una subcategoría
# ─────────────────────────────────────────
@bp.route("/<int:id_subcategoria>", methods=["DELETE"])
def eliminar_subcategoria(id_subcategoria):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_subcategoria FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        if cur.fetchone() is None:
            return error(message="Subcategoría no encontrada", status=404)

        # Primero eliminamos las relaciones en la tabla intermedia
        cur.execute("DELETE FROM categoria_subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        cur.execute("DELETE FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        conn.commit()
        return success(message="Subcategoría eliminada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
