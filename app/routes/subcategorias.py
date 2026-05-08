from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
from app.utils.jwt import verificar_token, requiere_admin

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
                s.id_subcat,
                s.nombre,
                s.descripcion,
                s.valor_numerico,
                s.unidad,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias 
            FROM subcategorias s
            LEFT JOIN categoria_subcategoria cs ON s.id_subcat = cs.id_subcat
            LEFT JOIN categorias c ON cs.id_cat = c.id_cat
            GROUP BY s.id_subcat
            ORDER BY s.id_subcat ASC
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
@bp.route("/<int:id_subcat>", methods=["GET"])
def obtener_subcategoria(id_subcat):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                s.id_subcat,
                s.nombre,
                s.descripcion,
                s.valor_numerico,
                s.unidad,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM subcategorias s
            LEFT JOIN categoria_subcategoria cs ON s.id_subcat = cs.id_subcat
            LEFT JOIN categorias c ON cs.id_cat = c.id_cat
            WHERE s.id_subcat = %s
            GROUP BY s.id_subcat
        """, (id_subcat,))
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
@requiere_admin
def crear_subcategoria():
    conn = None
    try:
        data = request.get_json()

        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        if not data.get("nombre"):
            return error(message="El campo 'nombre' es obligatorio", status=400)

        # categorias_ids es opcional, pero si viene debe ser una lista
        categorias_ids = data.get("categorias_ids", [])

        conn = get_connection()
        cur = conn.cursor()

        # Insertar la subcategoría
        cur.execute("""
            INSERT INTO subcategorias (nombre, descripcion, valor_numerico, unidad)
            VALUES (%s, %s, %s, %s)
            RETURNING id_subcat
        """, (
            data["nombre"],
            data.get("descripcion"),
            data.get("valor_numerico"),
            data.get("unidad")
        ))
        nuevo_id = cur.fetchone()["id_subcat"]

        # Insertar relaciones con categorías si vienen
        for id_cat in categorias_ids:
            cur.execute("""
                INSERT INTO categoria_subcategoria (id_cat, id_subcat)
                VALUES (%s, %s)
            """, (id_cat, nuevo_id))

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
@bp.route("/<int:id_subcat>", methods=["PUT"])
@requiere_admin
def actualizar_subcategoria(id_subcat):
    conn = None
    try:
        data = request.get_json()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_subcat FROM subcategorias WHERE id_subcat = %s", (id_subcat,))
        if cur.fetchone() is None:
            return error(message="Subcategoría no encontrada", status=404)
        
        cur.execute("SELECT * FROM subcategorias WHERE id_subcat = %s" , (id_subcat,))
        subcategoria_actual = cur.fetchone()

        # Actualizar datos principales
        cur.execute("""
            UPDATE subcategorias SET
                nombre = %s,
                descripcion = %s,
                valor_numerico = %s,
                unidad = %s
            WHERE id_subcat = %s
        """, (
            data.get("nombre", subcategoria_actual["nombre"]),
            data.get("descripcion", subcategoria_actual["descripcion"]),
            data.get("valor_numerico", subcategoria_actual["valor_numerico"]),
            data.get("unidad", subcategoria_actual["unidad"]),
            id_subcat
        ))

        # Si vienen categorias_ids, actualizamos las relaciones
        # Primero borramos las existentes y luego insertamos las nuevas
        if "categorias_ids" in data:
            cur.execute("DELETE FROM categoria_subcategoria WHERE id_subcat = %s", (id_subcat,))
            for id_cat in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO categoria_subcategoria (id_cat, id_subcat)
                    VALUES (%s, %s)
                """, (id_cat, id_subcat))

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
@bp.route("/<int:id_subcat>", methods=["DELETE"])
@requiere_admin
def eliminar_subcategoria(id_subcat):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_subcat FROM subcategorias WHERE id_subcat = %s", (id_subcat,))
        if cur.fetchone() is None:
            return error(message="Subcategoría no encontrada", status=404)

        # Primero eliminamos las relaciones en la tabla intermedia
        cur.execute("DELETE FROM categoria_subcategoria WHERE id_subcat = %s", (id_subcat,))
        cur.execute("DELETE FROM producto_subcategoria WHERE id_subcat = %s", (id_subcat,))
        cur.execute("DELETE FROM subcategorias WHERE id_subcat = %s", (id_subcat,))
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
