from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
from app.utils.jwt import verificar_token, requiere_admin

bp = Blueprint("inventarios", __name__)

# ─────────────────────────────────────────
# GET /inventarios/ → Listar todos los inventarios
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
@requiere_admin
def listar_inventarios():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT 
            inventarios.id_inventario,
            inventarios.stock,
            inventarios.min_stock,
            almacenes.nombre AS nombre_almacen,
            productos.descripcion AS descripcion_producto
        FROM inventarios
        LEFT JOIN almacenes ON almacenes.id_almacen = inventarios.id_almacen
        LEFT JOIN productos ON productos.id_producto = inventarios.id_producto
        ORDER BY id_inventario ASC
        """)

        inventarios = cur.fetchall()
        return success(data=inventarios, message="Inventarios obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /inventarios/<id> → Detalle de un inventario
# ─────────────────────────────────────────
@bp.route("/<int:id_inventario>", methods=["GET"])
@requiere_admin
def obtener_inventario(id_inventario):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT 
            inventarios.id_inventario,
            inventarios.stock,
            inventarios.min_stock,
            almacenes.folio AS folio_almacen,
            almacenes.nombre AS nombre_almacen,
            productos.folio AS folio_producto,
            productos.descripcion AS descripcion_producto,
            productos.costo AS costo_producto,
            productos.precio AS precio_producto
        FROM inventarios
        LEFT JOIN almacenes ON almacenes.id_almacen = inventarios.id_almacen
        LEFT JOIN productos ON productos.id_producto = inventarios.id_producto
        WHERE id_inventario = %s
        """, (id_inventario,))

        inventario = cur.fetchone()
        if inventario is None:
            return error(message="Inventario no encontrado", status=404)
        return success(data=inventario, message="Inventario obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# POST /inventarios/ → Crear un inventario
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
@requiere_admin
def crear_inventario():
    conn = None
    try:
        data = request.get_json()

        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        # Validar campos obligatorios
        campos_requeridos = ["id_producto", "id_almacen", "stock", "min_stock"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)
        
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT 
            id_almacen
        FROM almacenes
        WHERE id_almacen = %s
        """, (data["id_almacen"],))
        almacen = cur.fetchone()
        if almacen is None:
            return error(message="El almacen seleccionado no existe", status = 404)

        cur.execute("""
        SELECT 
            id_producto
        FROM productos
        WHERE id_producto = %s
        """, (data["id_producto"],))
        producto = cur.fetchone()
        if producto is None:
            return error(message="El producto seleccionado no existe", status = 404)

        cur.execute("""
        INSERT INTO inventarios (
            id_producto,
            id_almacen,
            stock,
            min_stock
        ) VALUES (%s, %s, %s, %s)
        RETURNING id_inventario
        """, (
            data["id_producto"],
            data["id_almacen"],
            data["stock"],
            data["min_stock"]
        ))

        nuevo_id = cur.fetchone()["id_inventario"]

        conn.commit()
        return success(data={"id_inventario": nuevo_id}, message="Inventario creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# DELETE /inventarios/<id> → Eliminar un cliente
# ─────────────────────────────────────────
@bp.route("/<int:id_inventario>", methods=["DELETE"])
@requiere_admin
def eliminar_cliente(id_inventario):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el cliente existe antes de eliminar
        cur.execute("SELECT id_inventario FROM inventarios WHERE id_inventario = %s", (id_inventario,))
        if cur.fetchone() is None:
            return error(message="Inventario no encontrado", status=404)

        cur.execute("DELETE FROM movimientos_inventario WHERE id_inventario = %s", (id_inventario,))
        cur.execute("DELETE FROM inventarios WHERE id_inventario = %s", (id_inventario,))
        conn.commit()
        return success(message="Inventario eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
