from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("almacenes", __name__)

# ─────────────────────────────────────────
# GET /almacenes/ → Listar todos los almacenes
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_almacenes():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id_almacen,
                folio,
                nombre
            FROM almacenes
            ORDER BY id_almacen ASC
        """)
        almacenes = cur.fetchall()
        return success(data=almacenes, message="Almacenes obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /almacenes/<id> → Detalle de un almacén
# ─────────────────────────────────────────
@bp.route("/<int:id_almacen>", methods=["GET"])
def obtener_almacen(id_almacen):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id_almacen,
                a.folio,
                a.nombre,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM almacenes a
            LEFT JOIN almacen_categoria alm_cat ON alm_cat.id_almacen = a.id_almacen
            LEFT JOIN categorias c ON c.id_cat = alm_cat.id_cat
            WHERE a.id_almacen = %s
            GROUP BY
                a.id_almacen,
                a.folio,
                a.nombre
        """, (id_almacen,))
        almacen = cur.fetchone()
        if almacen is None:
            return error(message="Almacén no encontrado", status=404)
        return success(data=almacen, message="Almacén obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /almacenes/<search> → Buscar un producto
# ─────────────────────────────────────────
@bp.route("/<string:search>", methods=["GET"])
def buscar_almacen(search):
    if not search or not search.strip():
        return error(message="El parámetro de búsqueda es requerido", status=400)

    conn = None
    cur = None  
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM almacenes
            WHERE folio ILIKE %s OR nombre ILIKE %s
        """, (f"%{search}%", f"%{search}%"))
        productos = cur.fetchall()

        if not productos:
            return error(message="No se encontraron almacenes", status=404)

        return success(data=productos, message="Almacenes obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if cur:  
            cur.close()
        if conn:
            conn.close()

# ─────────────────────────────────────────
# GET /almacenes/por-producto/<id_producto> → Almacenes con inventario de un producto
# ─────────────────────────────────────────
@bp.route("/por-producto/<int:id_producto>", methods=["GET"])
def almacenes_por_producto(id_producto):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        
        cur.execute("SELECT id_producto FROM productos WHERE id_producto = %s", (id_producto,))
        if cur.fetchone() is None:
            return error(message="El producto seleccionado no existe", status=404)

        cur.execute("""
            SELECT
                a.id_almacen,
                a.folio,
                a.nombre,
                i.stock
            FROM inventarios i
            LEFT JOIN almacenes a ON a.id_almacen = i.id_almacen
            WHERE i.id_producto = %s AND i.stock > 0
            ORDER BY a.id_almacen ASC
        """, (id_producto,))
        almacenes = cur.fetchall()

        return success(data=almacenes, message="Almacenes obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# POST /almacenes/ → Crear un almacén
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_almacen():
    conn = None
    try:
        data = request.get_json()

        # Validar campos obligatorios
        campos_requeridos = ["nombre", "folio"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)

        categorias_ids = data.get("categorias_ids", [])

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el folio no esté repetido
        cur.execute("""
            SELECT folio FROM almacenes WHERE folio = %s
        """, (data["folio"],))
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        cur.execute("""
            INSERT INTO almacenes (nombre, folio)
            VALUES (%s, %s)
            RETURNING id_almacen
        """, (
            data["nombre"],
            data.get("folio"),  # Opcional
        ))
        nuevo_id = cur.fetchone()["id_almacen"]

        for id_cat in categorias_ids:
            cur.execute("""
                INSERT INTO almacen_categoria (id_almacen, id_cat)
                VALUES (%s, %s)
            """, (nuevo_id, id_cat))

        conn.commit()
        return success(data={"id_almacen": nuevo_id}, message="Almacén creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# PUT /almacenes/<id> → Actualizar un almacén
# ─────────────────────────────────────────
@bp.route("/<int:id_almacen>", methods=["PUT"])
def actualizar_almacen(id_almacen):
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el almacén existe antes de actualizar
        cur.execute("SELECT id_almacen FROM almacenes WHERE id_almacen = %s", (id_almacen,))
        if cur.fetchone() is None:
            return error(message="Almacén no encontrado", status=404)

        # Verificar que el folio no esté repetido
        cur.execute("""
            SELECT folio FROM almacenes WHERE folio = %s
        """, (data.get("folio"),))
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        cur.execute("SELECT * FROM almacenes WHERE id_almacen = %s", (id_almacen,))
        almacen_actual = cur.fetchone()

        cur.execute("""
            UPDATE almacenes SET
                nombre = %s,
                folio = %s
            WHERE id_almacen = %s
        """, (
            data.get("nombre", almacen_actual["nombre"]),
            data.get("folio", almacen_actual["folio"]),
            id_almacen
        ))

        if "categorias_ids" in data:
            cur.execute("DELETE FROM almacen_categoria WHERE id_almacen = %s", (id_almacen,))
            for id_cat in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO almacen_categoria (id_almacen, id_cat)
                    VALUES (%s, %s)
                """, (id_almacen, id_cat))

        conn.commit()
        return success(message="Almacén actualizado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# DELETE /almacenes/<id> → Eliminar un almacén
# ─────────────────────────────────────────
@bp.route("/<int:id_almacen>", methods=["DELETE"])
def eliminar_almacen(id_almacen):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el almacén existe antes de eliminar
        cur.execute("SELECT id_almacen FROM almacenes WHERE id_almacen = %s", (id_almacen,))
        if cur.fetchone() is None:
            return error(message="Almacén no encontrado", status=404)

        cur.execute("DELETE FROM almacen_categoria WHERE id_almacen = %s", (id_almacen,))
        cur.execute("DELETE FROM almacenes WHERE id_almacen = %s", (id_almacen,))

        conn.commit()
        return success(message="Almacén eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
