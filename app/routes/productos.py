from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
 
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
                p.precio,
                p.costo,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM productos p
            LEFT JOIN producto_categoria prod_cat ON prod_cat.id_prod = p.id_producto
            LEFT JOIN categorias c ON c.id_cat = prod_cat.id_cat
            GROUP BY
                p.id_producto,
                p.folio,
                p.descripcion,
                p.precio,
                p.costo
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
# GET /productos/<id> → Detalle de un producto
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
                p.precio,
                p.costo,
                COALESCE(
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias,
                COALESCE(
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'id_subcat', s.id_subcat,
                            'nombre', s.nombre,
                            'descripcion', s.descripcion,
                            'valor_numerico', s.valor_numerico,
                            'unidad', s.unidad
                        )
                    ) FILTER (WHERE s.id_subcat IS NOT NULL),
                    '[]'
                ) AS subcategorias
            FROM productos p
            LEFT JOIN producto_categoria prod_cat ON prod_cat.id_prod = p.id_producto
            LEFT JOIN categorias c ON c.id_cat = prod_cat.id_cat
            LEFT JOIN producto_subcategoria prod_subcat ON prod_subcat.id_producto = p.id_producto
            LEFT JOIN subcategorias s ON s.id_subcat = prod_subcat.id_subcat
            WHERE p.id_producto = %s
            GROUP BY
                p.id_producto,
                p.folio,
                p.descripcion,
                p.precio,
                p.costo
        """, (id_producto,))
        producto = cur.fetchone()
        if producto is None:
            return error(message="Producto no encontrado", status=404)
        return success(data=producto, message="Producto obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
 
# ─────────────────────────────────────────
# POST /productos/ → Crear un producto
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_producto():
    conn = None
    try:
        data = request.get_json()
 
        # Validar campos obligatorios
        campos_requeridos = ["folio", "costo"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)
 
        categorias_ids = data.get("categorias_ids", [])
        subcategorias_ids = data.get("subcategorias_ids", [])
 
        conn = get_connection()
        cur = conn.cursor()
 
        # Verificar que el folio no esté repetido
        cur.execute("""
            SELECT folio FROM productos WHERE folio = %s
        """, (data["folio"],))
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)
 
        cur.execute("""
            INSERT INTO productos (folio, descripcion, precio, costo)
            VALUES (%s, %s, %s, %s)
            RETURNING id_producto
        """, (
            data["folio"],
            data.get("descripcion"),  # Opcional
            data.get("precio"),       # Opcional
            data["costo"],
        ))
        nuevo_id = cur.fetchone()["id_producto"]
 
        for id_cat in categorias_ids:
            cur.execute("""
                INSERT INTO producto_categoria (id_prod, id_cat)
                VALUES (%s, %s)
            """, (nuevo_id, id_cat))
 
        for id_subcat in subcategorias_ids:
            cur.execute("""
                INSERT INTO producto_subcategoria (id_producto, id_subcat)
                VALUES (%s, %s)
            """, (nuevo_id, id_subcat))
 
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
def actualizar_producto(id_producto):
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cur = conn.cursor()
 
        # Verificar que el producto existe antes de actualizar
        cur.execute("SELECT id_producto FROM productos WHERE id_producto = %s", (id_producto,))
        if cur.fetchone() is None:
            return error(message="Producto no encontrado", status=404)
 
        # Verificar que el folio no esté repetido
        cur.execute("""
            SELECT folio FROM productos WHERE folio = %s
        """, (data.get("folio"),))
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)
 
        cur.execute("SELECT * FROM productos WHERE id_producto = %s", (id_producto,))
        producto_actual = cur.fetchone()
 
        cur.execute("""
            UPDATE productos SET
                folio = %s,
                descripcion = %s,
                precio = %s,
                costo = %s
            WHERE id_producto = %s
        """, (
            data.get("folio", producto_actual["folio"]),
            data.get("descripcion", producto_actual["descripcion"]),
            data.get("precio", producto_actual["precio"]),
            data.get("costo", producto_actual["costo"]),
            id_producto
        ))
 
        if "categorias_ids" in data:
            cur.execute("DELETE FROM producto_categoria WHERE id_prod = %s", (id_producto,))
            for id_cat in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO producto_categoria (id_prod, id_cat)
                    VALUES (%s, %s)
                """, (id_producto, id_cat))
 
        if "subcategorias_ids" in data:
            cur.execute("DELETE FROM producto_subcategoria WHERE id_producto = %s", (id_producto,))
            for id_subcat in data["subcategorias_ids"]:
                cur.execute("""
                    INSERT INTO producto_subcategoria (id_producto, id_subcat)
                    VALUES (%s, %s)
                """, (id_producto, id_subcat))
 
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
def eliminar_producto(id_producto):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
 
        # Verificar que el producto existe antes de eliminar
        cur.execute("SELECT id_producto FROM productos WHERE id_producto = %s", (id_producto,))
        if cur.fetchone() is None:
            return error(message="Producto no encontrado", status=404)
 
        cur.execute("DELETE FROM producto_categoria WHERE id_prod = %s", (id_producto,))
        cur.execute("DELETE FROM producto_subcategoria WHERE id_producto = %s", (id_producto,))
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
