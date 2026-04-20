from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("movimientos", __name__)

# ─────────────────────────────────────────
# GET /inventarios/ → Listar todos los inventarios
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_inventarios():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT 
            movimientos.id_mov,
            movimientos.tipo,
            inventarios.min_stock,
            almacenes.nombre AS nombre_almacen,
            productos.descripcion AS descripcion_producto
        FROM inventarios
        LEFT JOIN almacenes ON almacenes.id_almacen = inventarios.id_almacen
        LEFT JOIN productos ON productos.id_producto = inventarios.id_producto
        ORDER BY id_mov ASC
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
# POST /inventarios/ → Crear un movimiento
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_movimiento():
    conn = None
    try:
        data = request.get_json()

        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        # Validar campos obligatorios
        campos_requeridos = ["cantidad", "id_producto", "id_almacen"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)
        
        if data.get("tipo") is None:
            return error(message=f"El campo tipo es obligatorio", status=400)

        if data["cantidad"] <= 0:
            return error(message=f"La cantidad debe ser mayor a 0 para que un movimiento sea válido", status=400)
        
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
        SELECT * FROM inventarios WHERE id_producto = %s AND id_almacen = %s
        """, (data["id_producto"], data["id_almacen"]
        ))

        inventario_actual = cur.fetchone()

        if inventario_actual is None:
            return error(message="No hay inventario registrado del producto seleccionado en el almacen seleccionado", status=404)

        if data["tipo"]:
            modificador = 1
        else:
            if data["cantidad"] > inventario_actual["stock"]:
                return error(message="No hay suficiente stock en el inventario del producto seleccionado en el almacen seleccionado para la cantidad del movimiento", status=422)
            else:
                modificador = -1

        cur.execute("""
        INSERT INTO movimientos_inventario (
            tipo,
            cantidad,
            id_producto,
            id_almacen
        ) VALUES (%s, %s, %s, %s)
        RETURNING id_mov
        """, (
            data["tipo"],
            data["cantidad"],
            data["id_producto"],
            data["id_almacen"]
        ))

        nuevo_id = cur.fetchone()["id_mov"]

        cur.execute("""
        UPDATE inventarios SET
            stock = %s
        WHERE id_producto = %s AND id_almacen = %s
        """, (inventario_actual["stock"] + (data["cantidad"] * modificador), data["id_producto"], data["id_almacen"]
        ))


        conn.commit()
        return success(data={"id_mov": nuevo_id}, message="Movimiento creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()