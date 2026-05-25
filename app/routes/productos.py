from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
from app.utils.jwt import verificar_token, requiere_admin
 
bp = Blueprint("productos", __name__)
 
# ─────────────────────────────────────────
# GET /productos/ → Listar todos los productos
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_productos():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM productos p
            LEFT JOIN producto_categoria prod_cat ON prod_cat.id_prod = p.id_producto
            LEFT JOIN categorias c ON c.id_cat = prod_cat.id_cat
            WHERE p.folio != 'PROD-GEN'
            GROUP BY
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda
            ORDER BY p.id_producto ASC
        """)
        productos = cur.fetchall()
        return success(data=productos, message="Productos obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
 
# ─────────────────────────────────────────
# GET /productos/<id> → Detalle de un producto (sin márgenes)
# ─────────────────────────────────────────
@bp.route("/<int:id_producto>", methods=["GET"])
def obtener_producto(id_producto):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda,
                COALESCE(
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM productos p
            LEFT JOIN producto_categoria prod_cat ON prod_cat.id_prod = p.id_producto
            LEFT JOIN categorias c ON c.id_cat = prod_cat.id_cat
            WHERE p.id_producto = %s
            GROUP BY
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda
        """, (id_producto,))
        producto = cur.fetchone()

        if producto is None:
            return error(message="Producto no encontrado", status=404)

        # Traer precios sin márgenes
        cur.execute("""
            SELECT precio_margen
            FROM productos_precios
            WHERE id_producto = %s
            ORDER BY precio_margen ASC
        """, (id_producto,))
        precios = [row["precio_margen"] for row in cur.fetchall()]

        resultado = dict(producto)
        resultado["precios"] = precios

        return success(data=resultado, message="Producto obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /productos/<id>/admin → Detalle de un producto con márgenes (solo admin)
# ─────────────────────────────────────────
@bp.route("/<int:id_producto>/admin", methods=["GET"])
@requiere_admin
def obtener_producto_editar(id_producto):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda,
                COALESCE(
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM productos p
            LEFT JOIN producto_categoria prod_cat ON prod_cat.id_prod = p.id_producto
            LEFT JOIN categorias c ON c.id_cat = prod_cat.id_cat
            WHERE p.id_producto = %s
            GROUP BY
                p.id_producto,
                p.folio,
                p.descripcion,
                p.costo,
                p.moneda
        """, (id_producto,))
        producto = cur.fetchone()

        if producto is None:
            return error(message="Producto no encontrado", status=404)

        # Traer precios con márgenes
        cur.execute("""
            SELECT id_productos_precios, margen, precio_margen
            FROM productos_precios
            WHERE id_producto = %s
            ORDER BY margen ASC
        """, (id_producto,))
        precios = cur.fetchall()

        resultado = dict(producto)
        resultado["precios"] = precios

        return success(data=resultado, message="Producto obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# GET /productos/<search> → Buscar un producto
# ─────────────────────────────────────────
@bp.route("/<string:search>", methods=["GET"])
def buscar_producto(search):
    if not search or not search.strip():
        return error(message="El parámetro de búsqueda es requerido", status=400)

    conn = None
    cur = None  
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM productos
            WHERE folio ILIKE %s OR descripcion ILIKE %s
        """, (f"%{search}%", f"%{search}%"))
        productos = cur.fetchall()

        if not productos:
            return error(message="No se encontraron productos", status=404)

        return success(data=productos, message="Productos obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if cur:  
            cur.close()
        if conn:
            conn.close()
 
# ─────────────────────────────────────────
# POST /productos/ → Crear un producto
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
@requiere_admin
def crear_producto():
    conn = None
    try:
        data = request.get_json()

        # Validar campos obligatorios
        campos_requeridos = ["folio", "costo", "moneda"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)

        if data["moneda"] not in ["MXN", "USD"]:
            return error(message="El campo 'moneda' debe ser 'MXN' o 'USD'", status=400)

        margenes = data.get("margenes", [])
        if not margenes or not isinstance(margenes, list) or len(margenes) == 0:
            return error(message="El campo 'margenes' es obligatorio y debe ser un array con al menos un elemento", status=400)

        categorias_ids = data.get("categorias_ids", [])

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el folio no esté repetido
        cur.execute("SELECT folio FROM productos WHERE folio = %s", (data["folio"],))
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        cur.execute("""
            INSERT INTO productos (folio, descripcion, costo, moneda)
            VALUES (%s, %s, %s, %s)
            RETURNING id_producto
        """, (
            data["folio"],
            data.get("descripcion"),
            data["costo"],
            data["moneda"],
        ))
        nuevo_id = cur.fetchone()["id_producto"]

        # Insertar precios por margen
        for margen in margenes:
            precio_margen = data["costo"] / ( 1 - (margen / 100))
            cur.execute("""
                INSERT INTO productos_precios (id_producto, margen, precio_margen)
                VALUES (%s, %s, %s)
            """, (nuevo_id, margen, round(precio_margen, 2)))

        for id_cat in categorias_ids:
            cur.execute("""
                INSERT INTO producto_categoria (id_prod, id_cat)
                VALUES (%s, %s)
            """, (nuevo_id, id_cat))

        conn.commit()
        return success(data={"id_producto": nuevo_id}, message="Producto creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
 
# ─────────────────────────────────────────
# PUT /productos/<id> → Actualizar un producto
# ─────────────────────────────────────────
@bp.route("/<int:id_producto>", methods=["PUT"])
@requiere_admin
def actualizar_producto(id_producto):
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el producto existe antes de actualizar
        cur.execute("SELECT * FROM productos WHERE id_producto = %s", (id_producto,))
        producto_actual = cur.fetchone()
        if producto_actual is None:
            return error(message="Producto no encontrado", status=404)

        # Verificar que el folio no esté repetido
        if data.get("folio"):
            cur.execute("SELECT folio FROM productos WHERE folio = %s", (data.get("folio"),))
            if cur.fetchone() is not None:
                return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        # Validar moneda si se manda
        if data.get("moneda") and data["moneda"] not in ["MXN", "USD"]:
            return error(message="El campo 'moneda' debe ser 'MXN' o 'USD'", status=400)

        cur.execute("""
            UPDATE productos SET
                folio = %s,
                descripcion = %s,
                costo = %s,
                moneda = %s
            WHERE id_producto = %s
        """, (
            data.get("folio", producto_actual["folio"]),
            data.get("descripcion", producto_actual["descripcion"]),
            data.get("costo", producto_actual["costo"]),
            data.get("moneda", producto_actual["moneda"]),
            id_producto
        ))

        # Si vienen márgenes, recalcular todos los precios
        if "margenes" in data:
            if not isinstance(data["margenes"], list) or len(data["margenes"]) == 0:
                return error(message="El campo 'margenes' debe ser un array con al menos un elemento", status=400)

            costo_actual = data.get("costo", producto_actual["costo"])

            cur.execute("DELETE FROM productos_precios WHERE id_producto = %s", (id_producto,))
            for margen in data["margenes"]:
                precio_margen = costo_actual / ( 1 - (margen / 100))
                cur.execute("""
                    INSERT INTO productos_precios (id_producto, margen, precio_margen)
                    VALUES (%s, %s, %s)
                """, (id_producto, margen, round(precio_margen, 2)))

        if "categorias_ids" in data:
            cur.execute("DELETE FROM producto_categoria WHERE id_prod = %s", (id_producto,))
            for id_cat in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO producto_categoria (id_prod, id_cat)
                    VALUES (%s, %s)
                """, (id_producto, id_cat))

        conn.commit()
        return success(message="Producto actualizado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()

# ─────────────────────────────────────────
# DELETE /productos/<id> → Eliminar un producto
# ─────────────────────────────────────────
@bp.route("/<int:id_producto>", methods=["DELETE"])
@requiere_admin
def eliminar_producto(id_producto):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el producto existe antes de eliminar
        cur.execute("SELECT id_producto, folio FROM productos WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        if producto is None:
            return error(message="Producto no encontrado", status=404)

        if producto["folio"] == "PROD-GEN":
            return error(message="El producto genérico no puede eliminarse", status=403)

        cur.execute("SELECT id_producto FROM productos WHERE folio = 'PROD-GEN'")
        producto_generico = cur.fetchone()
        if producto_generico is None:
            return error(message="No se encuentra el producto genérico, confirmar con el administrador de sistemas", status=404)

        cur.execute("""
            UPDATE detalle_venta SET id_producto = %s
            WHERE id_producto = %s
        """, (producto_generico["id_producto"], id_producto))

        cur.execute("DELETE FROM producto_categoria WHERE id_prod = %s", (id_producto,))
        cur.execute("DELETE FROM productos_precios WHERE id_producto = %s", (id_producto,))
        cur.execute("DELETE FROM movimientos_inventario WHERE id_producto = %s", (id_producto,))
        cur.execute("DELETE FROM inventarios WHERE id_producto = %s", (id_producto,))
        cur.execute("DELETE FROM productos WHERE id_producto = %s", (id_producto,))

        conn.commit()
        return success(message="Producto eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
