from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
from app.utils.email import enviar_alerta_stock

bp = Blueprint("movimientos", __name__)

# ─────────────────────────────────────────
# GET /movimientos/ → Listar todos los movimientos
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_movimientos():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                m.id_mov,
                m.tipo,
                m.cantidad,
                TO_CHAR(m.fecha_creacion, 'DD-MM-YYYY HH24:MI:SS') AS fecha_creacion,
                p.descripcion AS descripcion_producto,
                a.nombre AS nombre_almacen
            FROM movimientos_inventario m
            LEFT JOIN productos p ON p.id_producto = m.id_producto
            LEFT JOIN almacenes a ON a.id_almacen = m.id_almacen
            ORDER BY m.id_mov ASC
        """)
        movimientos = cur.fetchall()
        return success(data=movimientos, message="Movimientos obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /movimientos/<id> → Detalle de un movimiento
# ─────────────────────────────────────────
@bp.route("/<int:id_mov>", methods=["GET"])
def obtener_movimiento(id_mov):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                m.id_mov,
                m.tipo,
                m.cantidad,
                TO_CHAR(m.fecha_creacion, 'DD-MM-YYYY HH24:MI:SS') AS fecha_creacion,
                m.id_venta,
                p.id_producto,
                p.folio AS folio_producto,
                p.descripcion AS descripcion_producto,
                a.id_almacen,
                a.nombre AS nombre_almacen
            FROM movimientos_inventario m
            LEFT JOIN productos p ON p.id_producto = m.id_producto
            LEFT JOIN almacenes a ON a.id_almacen = m.id_almacen
            WHERE m.id_mov = %s
        """, (id_mov,))
        movimiento = cur.fetchone()

        if movimiento is None:
            return error(message="Movimiento no encontrado", status=404)

        resultado = dict(movimiento)

        # Si el movimiento tiene una venta asociada, traer su detalle completo
        if movimiento["id_venta"] is not None:
            cur.execute("""
                SELECT
                    v.id_venta,
                    v.folio,
                    v.precio_venta_final,
                    TO_CHAR(v.fecha_creacion, 'DD-MM-YYYY HH24:MI:SS') AS fecha_creacion,
                    e.nombre AS estado,
                    m2.nombre AS municipio
                FROM ventas v
                LEFT JOIN estados e ON e.id_estado = v.id_estado
                LEFT JOIN municipios m2 ON m2.id_municipio = v.id_municipio
                WHERE v.id_venta = %s
            """, (movimiento["id_venta"],))
            venta = cur.fetchone()

            cur.execute("""
                SELECT
                    dv.id_detalle_venta,
                    dv.cantidad_vendida,
                    dv.precio_venta,
                    p2.id_producto,
                    p2.folio AS folio_producto,
                    p2.descripcion
                FROM detalle_venta dv
                LEFT JOIN productos p2 ON p2.id_producto = dv.id_producto
                WHERE dv.id_venta = %s
            """, (movimiento["id_venta"],))
            detalle_venta = cur.fetchall()

            resultado["venta"] = dict(venta) if venta else None
            resultado["venta"]["detalle"] = detalle_venta if detalle_venta else []

        return success(data=resultado, message="Movimiento obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# POST /movimientos/ → Crear un movimiento
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
            return error(message="El campo 'tipo' es obligatorio", status=400)
        if data["cantidad"] <= 0:
            return error(message="La cantidad debe ser mayor a 0 para que un movimiento sea válido", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el producto existe
        cur.execute("SELECT id_producto FROM productos WHERE id_producto = %s", (data["id_producto"],))
        if cur.fetchone() is None:
            return error(message="El producto seleccionado no existe", status=404)

        # Verificar que el almacén existe
        cur.execute("SELECT id_almacen FROM almacenes WHERE id_almacen = %s", (data["id_almacen"],))
        if cur.fetchone() is None:
            return error(message="El almacén seleccionado no existe", status=404)

        # Verificar que existe inventario para ese producto/almacén
        cur.execute("""
            SELECT * FROM inventarios
            WHERE id_producto = %s AND id_almacen = %s
        """, (data["id_producto"], data["id_almacen"]))
        inventario_actual = cur.fetchone()

        if inventario_actual is None:
            return error(message="No hay inventario registrado del producto seleccionado en el almacén seleccionado", status=404)

        # Si es salida, validar stock suficiente
        if not data["tipo"]:
            if data["cantidad"] > inventario_actual["stock"]:
                return error(
                    message=f"No hay suficiente stock en el inventario. Stock disponible: {inventario_actual['stock']}",
                    status=422
                )

        # Insertar movimiento
        cur.execute("""
            INSERT INTO movimientos_inventario (tipo, cantidad, id_producto, id_almacen)
            VALUES (%s, %s, %s, %s)
            RETURNING id_mov
        """, (
            data["tipo"],
            data["cantidad"],
            data["id_producto"],
            data["id_almacen"],
        ))
        nuevo_id = cur.fetchone()["id_mov"]

        # Actualizar stock según tipo
        modificador = 1 if data["tipo"] else -1
        cur.execute("""
            UPDATE inventarios SET
                stock = stock + %s
            WHERE id_producto = %s AND id_almacen = %s
        """, (
            data["cantidad"] * modificador,
            data["id_producto"],
            data["id_almacen"],
        ))

        # Verificar si se alcanzó el stock mínimo
        cur.execute("""
            SELECT
                i.stock,
                i.min_stock,
                p.descripcion,
                a.nombre AS nombre_almacen
            FROM inventarios i
            LEFT JOIN productos p ON p.id_producto = i.id_producto
            LEFT JOIN almacenes a ON a.id_almacen = i.id_almacen
            WHERE i.id_producto = %s AND i.id_almacen = %s
        """, (data["id_producto"], data["id_almacen"]))
        inventario_actualizado = cur.fetchone()
 
        if inventario_actualizado["stock"] <= inventario_actualizado["min_stock"]:
            enviar_alerta_stock(
                descripcion_producto=inventario_actualizado["descripcion"],
                nombre_almacen=inventario_actualizado["nombre_almacen"],
                stock_actual=inventario_actualizado["stock"],
                min_stock=inventario_actualizado["min_stock"]
            )

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

# ─────────────────────────────────────────
# PUT /movimientos/<id> → Actualizar un movimiento
# ─────────────────────────────────────────
@bp.route("/<int:id_mov>", methods=["PUT"])
def actualizar_movimiento(id_mov):
    conn = None
    try:
        data = request.get_json()
        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el movimiento existe
        cur.execute("""
            SELECT * FROM movimientos_inventario WHERE id_mov = %s
        """, (id_mov,))
        mov_actual = cur.fetchone()

        if mov_actual is None:
            return error(message="Movimiento no encontrado", status=404)

        tipo_nuevo = data.get("tipo", mov_actual["tipo"])
        cantidad_nueva = data.get("cantidad", mov_actual["cantidad"])
        id_producto_nuevo = data.get("id_producto", mov_actual["id_producto"])
        id_almacen_nuevo = data.get("id_almacen", mov_actual["id_almacen"])

        # Si vienen tipo o cantidad, hay que revertir el efecto original y aplicar el nuevo
        if "tipo" in data or "cantidad" in data:

            # Revertir efecto original en inventario
            modificador_revert = -1 if mov_actual["tipo"] else 1
            cur.execute("""
                UPDATE inventarios SET
                    stock = stock + %s
                WHERE id_producto = %s AND id_almacen = %s
            """, (
                mov_actual["cantidad"] * modificador_revert,
                mov_actual["id_producto"],
                mov_actual["id_almacen"],
            ))

            # Si el nuevo movimiento es salida, validar stock suficiente
            if not tipo_nuevo:
                cur.execute("""
                    SELECT stock FROM inventarios
                    WHERE id_producto = %s AND id_almacen = %s
                """, (id_producto_nuevo, id_almacen_nuevo))
                inventario = cur.fetchone()

                if inventario is None:
                    return error(message="No hay inventario registrado del producto en el almacén seleccionado", status=404)
                if cantidad_nueva > inventario["stock"]:
                    # Revertir la reversión antes de retornar el error
                    cur.execute("""
                        UPDATE inventarios SET
                            stock = stock + %s
                        WHERE id_producto = %s AND id_almacen = %s
                    """, (
                        mov_actual["cantidad"] * (1 if mov_actual["tipo"] else -1),
                        mov_actual["id_producto"],
                        mov_actual["id_almacen"],
                    ))
                    return error(
                        message=f"No hay suficiente stock para aplicar el movimiento. Stock disponible: {inventario['stock']}",
                        status=422
                    )

            # Actualizar el movimiento
            cur.execute("""
                UPDATE movimientos_inventario SET
                    tipo = %s,
                    cantidad = %s,
                    id_producto = %s,
                    id_almacen = %s
                WHERE id_mov = %s
            """, (tipo_nuevo, cantidad_nueva, id_producto_nuevo, id_almacen_nuevo, id_mov))

            # Aplicar nuevo efecto en inventario
            modificador_nuevo = 1 if tipo_nuevo else -1
            cur.execute("""
                UPDATE inventarios SET
                    stock = stock + %s
                WHERE id_producto = %s AND id_almacen = %s
            """, (
                cantidad_nueva * modificador_nuevo,
                id_producto_nuevo,
                id_almacen_nuevo,
            ))

            # Verificar si se alcanzó el stock mínimo
            cur.execute("""
                SELECT
                    i.stock,
                    i.min_stock,
                    p.descripcion,
                    a.nombre AS nombre_almacen
                FROM inventarios i
                LEFT JOIN productos p ON p.id_producto = i.id_producto
                LEFT JOIN almacenes a ON a.id_almacen = i.id_almacen
                WHERE i.id_producto = %s AND i.id_almacen = %s
            """, (id_producto_nuevo, id_almacen_nuevo))
            inventario_actualizado = cur.fetchone()
 
            if inventario_actualizado["stock"] <= inventario_actualizado["min_stock"]:
                enviar_alerta_stock(
                    descripcion_producto=inventario_actualizado["descripcion"],
                    nombre_almacen=inventario_actualizado["nombre_almacen"],
                    stock_actual=inventario_actualizado["stock"],
                    min_stock=inventario_actualizado["min_stock"]
                )

        else:
            # Sin cambios de tipo/cantidad, solo actualizar campos restantes
            cur.execute("""
                UPDATE movimientos_inventario SET
                    id_producto = %s,
                    id_almacen = %s
                WHERE id_mov = %s
            """, (id_producto_nuevo, id_almacen_nuevo, id_mov))

        conn.commit()
        return success(message="Movimiento actualizado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# DELETE /movimientos/<id> → Eliminar un movimiento
# ─────────────────────────────────────────
@bp.route("/<int:id_mov>", methods=["DELETE"])
def eliminar_movimiento(id_mov):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el movimiento existe
        cur.execute("SELECT * FROM movimientos_inventario WHERE id_mov = %s", (id_mov,))
        mov = cur.fetchone()

        if mov is None:
            return error(message="Movimiento no encontrado", status=404)

        # Revertir el efecto del movimiento en el inventario
        modificador = -1 if mov["tipo"] else 1
        cur.execute("""
            UPDATE inventarios SET
                stock = stock + %s
            WHERE id_producto = %s AND id_almacen = %s
        """, (
            mov["cantidad"] * modificador,
            mov["id_producto"],
            mov["id_almacen"],
        ))

        cur.execute("DELETE FROM movimientos_inventario WHERE id_mov = %s", (id_mov,))

        conn.commit()
        return success(message="Movimiento eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
