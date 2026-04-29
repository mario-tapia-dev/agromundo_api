from flask import Blueprint
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("reportes", __name__)

# ─────────────────────────────────────────
# GET /reportes/kpis → KPIs generales
# ─────────────────────────────────────────
@bp.route("/kpis", methods=["GET"])
def kpis():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Importe total de ventas
        cur.execute("""
            SELECT COALESCE(SUM(precio_venta_final), 0) AS total_ventas
            FROM ventas
        """)
        total_ventas = cur.fetchone()["total_ventas"]

        # Producto más vendido por cantidad
        cur.execute("""
            SELECT
                p.descripcion,
                SUM(dv.cantidad_vendida) AS total_vendido
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            GROUP BY p.id_producto, p.descripcion
            ORDER BY total_vendido DESC
            LIMIT 1
        """)
        producto_mas_vendido = cur.fetchone()

        # Cliente principal por importe total de ventas (excluyendo público general)
        cur.execute("""
            SELECT
                c.nombre || ' ' || c.apellido_paterno AS cliente,
                SUM(v.precio_venta_final) AS total_ventas_cliente
            FROM ventas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            WHERE c.folio != 'PUB-001'
            GROUP BY c.id_cliente, c.nombre, c.apellido_paterno
            ORDER BY total_ventas_cliente DESC
            LIMIT 1
        """)
        cliente_principal = cur.fetchone()

        # Categoría con más ventas por importe
        cur.execute("""
            SELECT
                cat.nombre AS categoria,
                SUM(dv.cantidad_vendida * dv.precio_venta) AS total_ventas_categoria
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            GROUP BY cat.id_cat, cat.nombre
            ORDER BY total_ventas_categoria DESC
            LIMIT 1
        """)
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
        conn = get_connection()
        cur = conn.cursor()

        # Traer categorías que tienen ventas
        cur.execute("""
            SELECT DISTINCT cat.id_cat, cat.nombre
            FROM categorias cat
            LEFT JOIN producto_categoria pc ON pc.id_cat = cat.id_cat
            LEFT JOIN detalle_venta dv ON dv.id_producto = pc.id_prod
            WHERE dv.id_detalle_venta IS NOT NULL
            ORDER BY cat.id_cat ASC
        """)
        categorias = cur.fetchall()

        resultado = []
        for categoria in categorias:
            # Utilidad total de la categoría
            cur.execute("""
                SELECT
                    COALESCE(SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)), 0) AS utilidad_total
                FROM detalle_venta dv
                LEFT JOIN productos p ON p.id_producto = dv.id_producto
                LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
                WHERE pc.id_cat = %s
            """, (categoria["id_cat"],))
            utilidad_categoria = cur.fetchone()["utilidad_total"]

            # Productos de esa categoría con sus ventas y utilidad
            cur.execute("""
                SELECT
                    p.descripcion,
                    SUM(dv.cantidad_vendida) AS cantidad_vendida,
                    SUM(dv.cantidad_vendida * dv.precio_venta) AS total_ventas,
                    SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad
                FROM detalle_venta dv
                LEFT JOIN productos p ON p.id_producto = dv.id_producto
                LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
                WHERE pc.id_cat = %s
                GROUP BY p.id_producto, p.descripcion
                ORDER BY cantidad_vendida DESC
            """, (categoria["id_cat"],))
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
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.nombre || ' ' || c.apellido_paterno AS cliente,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad_total
            FROM ventas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            LEFT JOIN detalle_venta dv ON dv.id_venta = v.id_venta
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            WHERE c.folio != 'PUB-001'
            GROUP BY c.id_cliente, c.nombre, c.apellido_paterno
            HAVING SUM(dv.cantidad_vendida) > 0
            ORDER BY utilidad_total DESC
        """)
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
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                p.descripcion,
                cat.nombre AS categoria,
                SUM(dv.cantidad_vendida) AS cantidad_vendida,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) AS utilidad
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            GROUP BY p.id_producto, p.descripcion, cat.id_cat, cat.nombre
            ORDER BY cantidad_vendida DESC
            LIMIT 6
        """)
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
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT ON (cat.id_cat)
                cat.nombre AS categoria,
                p.descripcion,
                SUM(dv.cantidad_vendida) OVER (PARTITION BY p.id_producto) AS cantidad_vendida,
                SUM(dv.cantidad_vendida * (dv.precio_venta - p.costo)) OVER (PARTITION BY p.id_producto) AS utilidad
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            LEFT JOIN producto_categoria pc ON pc.id_prod = p.id_producto
            LEFT JOIN categorias cat ON cat.id_cat = pc.id_cat
            WHERE cat.id_cat IS NOT NULL
            ORDER BY cat.id_cat, cantidad_vendida DESC
        """)
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
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                p.descripcion,
                SUM(dv.cantidad_vendida) AS cantidad_vendida
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id_producto = dv.id_producto
            GROUP BY p.id_producto, p.descripcion
            HAVING SUM(dv.cantidad_vendida) > 0
            ORDER BY cantidad_vendida DESC
        """)
        productos = cur.fetchall()

        return success(data=productos, message="Reporte de cantidad vendida obtenido correctamente")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
