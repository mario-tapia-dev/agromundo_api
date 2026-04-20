from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("ventas", __name__)

# ─────────────────────────────────────────
# GET /ventas/ → Listar todas las ventas
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_ventas():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.precio_venta_final,
                e.nombre AS estado,
                m.nombre AS municipio
            FROM ventas v
            LEFT JOIN estados e ON e.id_estado = v.id_estado
            LEFT JOIN municipios m ON m.id_municipio = v.id_municipio
            ORDER BY v.id_venta ASC
        """)
        ventas = cur.fetchall()
        return success(data=ventas, message="Ventas obtenidas correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /ventas/<id> → Detalle de una venta
# ─────────────────────────────────────────
@bp.route("/<int:id_venta>", methods=["GET"])
def obtener_venta(id_venta):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.precio_venta_final,
                e.nombre AS estado,
                m.nombre AS municipio
            FROM ventas v
            LEFT JOIN estados e ON e.id_estado = v.id_estado
            LEFT JOIN municipios m ON m.id_municipio = v.id_municipio
            WHERE v.id_venta = %s
        """, (id_venta,))
        venta = cur.fetchone()

        if venta is None:
            return error(message="Venta no encontrada", status=404)

        cur.execute("""
            SELECT
                dv.id_detalle_venta,
                dv.cantidad_vendida,
                dv.precio_venta,
                p.id_producto,
                p.folio AS folio_producto,
                p.descripcion
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            WHERE dv.id_venta = %s
        """, (id_venta,))
        detalle = cur.fetchall()

        resultado = dict(venta)
        resultado["detalle"] = detalle if detalle else []

        return success(data=resultado, message="Venta obtenida correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# POST /ventas/ → Crear una venta
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_venta():
    conn = None
    try:
        data = request.get_json()
        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        # Validar campos obligatorios
        if not data.get("precio_venta_final"):
            return error(message="El campo 'precio_venta_final' es obligatorio", status=400)

        detalle = data.get("detalle")
        if not detalle or not isinstance(detalle, list) or len(detalle) == 0:
            return error(message="El campo 'detalle' es obligatorio y debe ser un array con al menos un elemento", status=400)

        # Validar campos obligatorios dentro de cada elemento del detalle
        for i, item in enumerate(detalle):
            for campo in ["id_producto", "cantidad_vendida", "precio_venta", "id_almacen"]:
                if item.get(campo) is None:
                    return error(message=f"El campo '{campo}' es obligatorio en el elemento {i + 1} del detalle", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Validar stock disponible por cada elemento del detalle antes de procesar
        for item in detalle:
            cur.execute("""
                SELECT stock FROM inventarios
                WHERE id_producto = %s AND id_almacen = %s
            """, (item["id_producto"], item["id_almacen"]))
            inventario = cur.fetchone()

            if inventario is None:
                return error(
                    message=f"No hay inventario registrado para el producto {item['id_producto']} en el almacén {item['id_almacen']}",
                    status=404
                )
            if item["cantidad_vendida"] > inventario["stock"]:
                return error(
                    message=f"Stock insuficiente para el producto {item['id_producto']} en el almacén {item['id_almacen']}. Stock disponible: {inventario['stock']}",
                    status=422
                )

        # Insertar la venta
        cur.execute("""
            INSERT INTO ventas (folio, precio_venta_final, id_estado, id_municipio)
            VALUES (%s, %s, %s, %s)
            RETURNING id_venta
        """, (
            data.get("folio"),
            data["precio_venta_final"],
            data.get("id_estado"),
            data.get("id_municipio"),
        ))
        nuevo_id = cur.fetchone()["id_venta"]

        # Procesar cada elemento del detalle
        for item in detalle:
            # Insertar detalle de venta
            cur.execute("""
                INSERT INTO detalle_venta (cantidad_vendida, precio_venta, id_venta, id_producto)
                VALUES (%s, %s, %s, %s)
            """, (
                item["cantidad_vendida"],
                item["precio_venta"],
                nuevo_id,
                item["id_producto"],
            ))

            # Insertar movimiento de salida
            cur.execute("""
                INSERT INTO movimientos_inventario (tipo, cantidad, id_venta, id_producto, id_almacen)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                False,
                item["cantidad_vendida"],
                nuevo_id,
                item["id_producto"],
                item["id_almacen"],
            ))

            # Actualizar stock
            cur.execute("""
                UPDATE inventarios SET
                    stock = stock - %s
                WHERE id_producto = %s AND id_almacen = %s
            """, (
                item["cantidad_vendida"],
                item["id_producto"],
                item["id_almacen"],
            ))

        conn.commit()
        return success(data={"id_venta": nuevo_id}, message="Venta creada correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# PUT /ventas/<id> → Actualizar una venta
# ─────────────────────────────────────────
@bp.route("/<int:id_venta>", methods=["PUT"])
def actualizar_venta(id_venta):
    conn = None
    try:
        data = request.get_json()
        if data is None:
            return error(message="El cuerpo debe ser un JSON válido", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que la venta existe
        cur.execute("SELECT * FROM ventas WHERE id_venta = %s", (id_venta,))
        venta_actual = cur.fetchone()
        if venta_actual is None:
            return error(message="Venta no encontrada", status=404)

        # Actualizar campos generales de la venta
        cur.execute("""
            UPDATE ventas SET
                folio = %s,
                precio_venta_final = %s,
                id_estado = %s,
                id_municipio = %s
            WHERE id_venta = %s
        """, (
            data.get("folio", venta_actual["folio"]),
            data.get("precio_venta_final", venta_actual["precio_venta_final"]),
            data.get("id_estado", venta_actual["id_estado"]),
            data.get("id_municipio", venta_actual["id_municipio"]),
            id_venta,
        ))

        # Si viene nuevo detalle, reemplazar todo
        if "detalle" in data:
            detalle = data["detalle"]

            if not isinstance(detalle, list) or len(detalle) == 0:
                return error(message="El campo 'detalle' debe ser un array con al menos un elemento", status=400)

            # Validar campos obligatorios dentro de cada elemento del nuevo detalle
            for i, item in enumerate(detalle):
                for campo in ["id_producto", "cantidad_vendida", "precio_venta", "id_almacen"]:
                    if item.get(campo) is None:
                        return error(message=f"El campo '{campo}' es obligatorio en el elemento {i + 1} del detalle", status=400)

            # Restaurar stock usando los movimientos anteriores de esta venta
            cur.execute("""
                SELECT id_mov, cantidad, id_producto, id_almacen
                FROM movimientos_inventario
                WHERE id_venta = %s
            """, (id_venta,))
            movimientos_anteriores = cur.fetchall()

            for mov in movimientos_anteriores:
                # Los movimientos de venta son siempre de tipo salida (false), restauramos sumando
                cur.execute("""
                    UPDATE inventarios SET
                        stock = stock + %s
                    WHERE id_producto = %s AND id_almacen = %s
                """, (mov["cantidad"], mov["id_producto"], mov["id_almacen"]))

                cur.execute("DELETE FROM movimientos_inventario WHERE id_mov = %s", (mov["id_mov"],))

            # Eliminar detalle anterior
            cur.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (id_venta,))

            # Validar stock disponible con el nuevo detalle antes de procesar
            for item in detalle:
                cur.execute("""
                    SELECT stock FROM inventarios
                    WHERE id_producto = %s AND id_almacen = %s
                """, (item["id_producto"], item["id_almacen"]))
                inventario = cur.fetchone()

                if inventario is None:
                    return error(
                        message=f"No hay inventario registrado para el producto {item['id_producto']} en el almacén {item['id_almacen']}",
                        status=404
                    )
                if item["cantidad_vendida"] > inventario["stock"]:
                    return error(
                        message=f"Stock insuficiente para el producto {item['id_producto']} en el almacén {item['id_almacen']}. Stock disponible: {inventario['stock']}",
                        status=422
                    )

            # Insertar nuevo detalle y movimientos
            for item in detalle:
                cur.execute("""
                    INSERT INTO detalle_venta (cantidad_vendida, precio_venta, id_venta, id_producto)
                    VALUES (%s, %s, %s, %s)
                """, (
                    item["cantidad_vendida"],
                    item["precio_venta"],
                    id_venta,
                    item["id_producto"],
                ))

                cur.execute("""
                    INSERT INTO movimientos_inventario (tipo, cantidad, id_venta, id_producto, id_almacen)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    False,
                    item["cantidad_vendida"],
                    id_venta,
                    item["id_producto"],
                    item["id_almacen"],
                ))

                cur.execute("""
                    UPDATE inventarios SET
                        stock = stock - %s
                    WHERE id_producto = %s AND id_almacen = %s
                """, (
                    item["cantidad_vendida"],
                    item["id_producto"],
                    item["id_almacen"],
                ))

        conn.commit()
        return success(message="Venta actualizada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# DELETE /ventas/<id> → Eliminar una venta
# ─────────────────────────────────────────
@bp.route("/<int:id_venta>", methods=["DELETE"])
def eliminar_venta(id_venta):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que la venta existe
        cur.execute("SELECT id_venta FROM ventas WHERE id_venta = %s", (id_venta,))
        if cur.fetchone() is None:
            return error(message="Venta no encontrada", status=404)

        # Restaurar stock usando los movimientos asociados
        cur.execute("""
            SELECT id_mov, cantidad, id_producto, id_almacen
            FROM movimientos_inventario
            WHERE id_venta = %s
        """, (id_venta,))
        movimientos = cur.fetchall()

        for mov in movimientos:
            cur.execute("""
                UPDATE inventarios SET
                    stock = stock + %s
                WHERE id_producto = %s AND id_almacen = %s
            """, (mov["cantidad"], mov["id_producto"], mov["id_almacen"]))

            cur.execute("DELETE FROM movimientos_inventario WHERE id_mov = %s", (mov["id_mov"],))

        cur.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (id_venta,))
        cur.execute("DELETE FROM ventas WHERE id_venta = %s", (id_venta,))

        conn.commit()
        return success(message="Venta eliminada correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
