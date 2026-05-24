from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("reportes", __name__)

def get_filtro_fechas():
    """
    Extrae y valida los parámetros de fecha_inicio y fecha_fin de la query string.
    Retorna una tupla (fecha_inicio, fecha_fin, error_response).
    Si hay error retorna (None, None, error_response), si no hay error retorna (fecha_inicio, fecha_fin, None).
    """
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    if fecha_inicio and not fecha_fin:
        return None, None, error(message="Si se manda fecha_inicio también se debe mandar fecha_fin", status=400)
    if fecha_fin and not fecha_inicio:
        return None, None, error(message="Si se manda fecha_fin también se debe mandar fecha_inicio", status=400)

    return fecha_inicio, fecha_fin, None

def build_fecha_filter(fecha_inicio, fecha_fin, alias="v"):
    """
    Retorna el fragmento SQL y los parámetros para filtrar por fecha.
    alias: el alias de la tabla ventas en el query.
    """
    if fecha_inicio and fecha_fin:
        return f"AND {alias}.fecha_creacion::date BETWEEN %s AND %s", (fecha_inicio, fecha_fin)
    return "", ()

# ─────────────────────────────────────────
# GET /reportes/kpis → KPIs generales
# ─────────────────────────────────────────
@bp.route("/kpis", methods=["GET"])
def kpis():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        # Importe total de ventas
        cur.execute(f"""
            SELECT COALESCE(SUM(precio_venta_final), 0) AS total_ventas
            FROM ventas v
            WHERE 1=1 {fecha_sql}
        """, fecha_params)
        total_ventas = cur.fetchone()["total_ventas"]

        # Producto más vendido por cantidad
        cur.execute(f"""
            SELECT
                p.descripcion,
                SUM(dv.cantidad_vendida) AS total_vendido
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE 1=1 {fecha_sql}
            GROUP BY p.id_producto, p.descripcion
            ORDER BY total_vendido DESC
            LIMIT 1
        """, fecha_params)
        producto_mas_vendido = cur.fetchone()

        # Cliente principal por importe total de ventas 
        cur.execute(f"""
            SELECT
                c.nombre || ' ' || c.apellido_paterno AS cliente,
                SUM(v.precio_venta_final) AS total_ventas_cliente
            FROM ventas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            GROUP BY c.id_cliente, c.nombre, c.apellido_paterno
            ORDER BY total_ventas_cliente DESC
            LIMIT 1
        """, fecha_params)
        cliente_principal = cur.fetchone()

        # Categoría con más ventas por importe
        cur.execute(f"""
            SELECT
                cat.nombre AS categoria,
                SUM(dv.cantidad_vendida * dv.precio_venta) AS total_ventas_categoria
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE 1=1 {fecha_sql}
            GROUP BY cat.id_cat, cat.nombre
            ORDER BY total_ventas_categoria DESC
            LIMIT 1
        """, fecha_params)
        categoria_top = cur.fetchone()

        return success(data={
            "total_ventas": total_ventas,
            "producto_mas_vendido": producto_mas_vendido["descripcion"] if producto_mas_vendido else None,
            "cliente_principal": cliente_principal["cliente"] if cliente_principal else None,
            "categoria_top": categoria_top["categoria"] if categoria_top else None
        }, message="KPIs obtenidos correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /reportes/ventas-por-categoria → Ventas y utilidad por categoría
# ─────────────────────────────────────────
@bp.route("/ventas-por-categoria", methods=["GET"])
def ventas_por_categoria():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        cur.execute(f"""
            SELECT DISTINCT cat.id_cat, cat.nombre
            FROM categorias cat
            LEFT JOIN producto_categoria pc ON pc.id_cat = cat.id_cat
            LEFT JOIN detalle_venta dv ON dv.id_producto = pc.id_prod
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE dv.id_detalle_venta IS NOT NULL {fecha_sql}
            ORDER BY cat.id_cat ASC
        """, fecha_params)
        categorias = cur.fetchall()

        resultado = []
        for categoria in categorias:
            cur.execute(f"""
                SELECT
                    COALESCE(SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)), 0) AS utilidad_total
                FROM detalle_venta dv
                LEFT JOIN productos p ON p.id_producto = dv.id_producto
                LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
                LEFT JOIN ventas v ON v.id_venta = dv.id_venta
                WHERE pc.id_cat = %s {fecha_sql}
            """, (categoria["id_cat"],) + fecha_params)
            utilidad_categoria = cur.fetchone()["utilidad_total"]

            cur.execute(f"""
                SELECT
                    p.descripcion,
                    SUM(dv.cantidad_vendida) AS cantidad_vendida,
                    SUM(dv.cantidad_vendida * dv.precio_venta) AS total_ventas,
                    SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad
                FROM detalle_venta dv
                LEFT JOIN productos p ON p.id_producto = dv.id_producto
                LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
                LEFT JOIN ventas v ON v.id_venta = dv.id_venta
                WHERE pc.id_cat = %s {fecha_sql}
                GROUP BY p.id_producto, p.descripcion
                ORDER BY cantidad_vendida DESC
            """, (categoria["id_cat"],) + fecha_params)
            productos = cur.fetchall()

            resultado.append({
                "categoria": categoria["nombre"],
                "utilidad_total": utilidad_categoria,
                "productos": productos
            })

        return success(data=resultado, message="Reporte de ventas por categoría obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /reportes/ventas-por-cliente → Utilidad de ventas por cliente
# ─────────────────────────────────────────
@bp.route("/ventas-por-cliente", methods=["GET"])
def ventas_por_cliente():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        cur.execute(f"""
            SELECT
                c.nombre || ' ' || c.apellido_paterno AS cliente,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad_total
            FROM ventas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            LEFT JOIN detalle_venta dv ON dv.id_venta = v.id_venta
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            GROUP BY c.id_cliente, c.nombre, c.apellido_paterno
            HAVING SUM(dv.cantidad_vendida) > 0
            ORDER BY utilidad_total DESC
        """, fecha_params)
        clientes = cur.fetchall()

        return success(data=clientes, message="Reporte de ventas por cliente obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /reportes/top-productos → Top 6 productos más vendidos
# ─────────────────────────────────────────
@bp.route("/top-productos", methods=["GET"])
def top_productos():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        cur.execute(f"""
            SELECT
                p.descripcion,
                cat.nombre AS categoria,
                SUM(dv.cantidad_vendida) AS cantidad_vendida,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE 1=1 {fecha_sql}
            GROUP BY p.id_producto, p.descripcion, cat.id_cat, cat.nombre
            ORDER BY cantidad_vendida DESC
            LIMIT 6
        """, fecha_params)
        productos = cur.fetchall()

        return success(data=productos, message="Top 6 productos más vendidos obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /reportes/top-por-categoria → Producto más vendido por categoría
# ─────────────────────────────────────────
@bp.route("/top-por-categoria", methods=["GET"])
def top_por_categoria():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        cur.execute(f"""
            SELECT DISTINCT ON (cat.id_cat)
                cat.nombre AS categoria,
                p.descripcion,
                SUM(dv.cantidad_vendida) OVER (PARTITION BY p.id_producto) AS cantidad_vendida,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) OVER (PARTITION BY p.id_producto) AS utilidad
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE cat.id_cat IS NOT NULL {fecha_sql}
            ORDER BY cat.id_cat, cantidad_vendida DESC
        """, fecha_params)
        resultado = cur.fetchall()

        return success(data=resultado, message="Producto más vendido por categoría obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /reportes/cantidad-vendida → Cantidad vendida de todos los productos
# ─────────────────────────────────────────
@bp.route("/cantidad-vendida", methods=["GET"])
def cantidad_vendida():
    conn = None
    try:
        fecha_inicio, fecha_fin, err = get_filtro_fechas()
        if err:
            return err

        conn = get_connection()
        cur = conn.cursor()

        fecha_sql, fecha_params = build_fecha_filter(fecha_inicio, fecha_fin)

        cur.execute(f"""
            SELECT
                p.descripcion,
                SUM(dv.cantidad_vendida) AS cantidad_vendida
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE 1=1 {fecha_sql}
            GROUP BY p.id_producto, p.descripcion
            HAVING SUM(dv.cantidad_vendida) > 0
            ORDER BY cantidad_vendida DESC
        """, fecha_params)
        productos = cur.fetchall()

        return success(data=productos, message="Reporte de cantidad vendida obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
