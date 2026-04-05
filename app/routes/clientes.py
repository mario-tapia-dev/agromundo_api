from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error

bp = Blueprint("clientes", __name__)


# ─────────────────────────────────────────
# GET /clientes/ → Listar todos los clientes
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
def listar_clientes():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id_cliente,
                folio,
                nombre,
                apellido_paterno,
                apellido_materno,
                telefono,
                email
            FROM clientes
            ORDER BY id_cliente ASC
        """)
        clientes = cur.fetchall()
        return success(data=clientes, message="Clientes obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# GET /clientes/<id> → Detalle de un cliente
# ─────────────────────────────────────────
@bp.route("/<int:id_cliente>", methods=["GET"])
def obtener_cliente(id_cliente):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                clientes.id_cliente,
                clientes.folio,
                clientes.nombre,
                clientes.apellido_paterno,
                clientes.apellido_materno,
                clientes.telefono,
                clientes.email,
                e.nombre AS estado,
                m.nombre AS municipio,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id_cat', c.id_cat, 'nombre', c.nombre)
                    ) FILTER (WHERE c.id_cat IS NOT NULL),
                    '[]'
                ) AS categorias
            FROM clientes 
            LEFT JOIN estados e ON clientes.id_estado = e.id_estado
            LEFT JOIN municipios m ON clientes.id_municipio = m.id_municipio
            LEFT JOIN clientes_categoria cltes_cat ON cltes_cat.id_cliente = clientes.id_cliente
            LEFT JOIN categorias c ON c.id_cat = cltes_cat.id_cat 
            WHERE clientes.id_cliente = %s
            GROUP BY 
                clientes.id_cliente,
                clientes.folio,
                clientes.nombre,
                clientes.apellido_paterno,
                clientes.apellido_materno,
                clientes.telefono,
                clientes.email,
                e.nombre,
                m.nombre
        """, (id_cliente,))
        cliente = cur.fetchone()
        if cliente is None:
            return error(message="Cliente no encontrado", status=404)
        return success(data=cliente, message="Cliente obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /clientes/ → Crear un cliente
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
def crear_cliente():
    conn = None
    try:
        data = request.get_json()

        # Validar campos obligatorios
        campos_requeridos = ["folio", "nombre", "apellido_paterno", "telefono", "email"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)
        
        categorias_ids = data.get("categorias_ids", [])

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el estado exista
        if data.get("id_estado") is not None:
            cur.execute("""
            SELECT 
                id_estado 
            FROM estados
            WHERE id_estado = %s
            """, (data.get("id_estado"),))
            estado = cur.fetchone()
            if estado is None:
                return error(message="El estado seleccionado no existe", status=404)

        # Verificar que el municipio exista
        if data.get("id_municipio") is not None:
            cur.execute("""
            SELECT
                id_municipio
            FROM municipios
            WHERE id_municipio = %s
            """, (data.get("id_municipio"),))
            municipio = cur.fetchone()
            if municipio is None:
                return error(message="El municipio seleccionado no existe", status=404)
        
        # Verificar que el folio no esté repetido
        cur.execute("""
        SELECT
            folio
        FROM clientes
        WHERE folio = %s 
        """, (data["folio"],))
        
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        # Verificar que el telefono no esté repetido
        cur.execute("""
        SELECT
            telefono
        FROM clientes
        WHERE telefono = %s 
        """, (data["telefono"],))
        
        if cur.fetchone() is not None:
            return error(message="El telefono asignado ya existe, coloque otro diferente", status=409)
        
        # Verificar que el email no esté repetido
        cur.execute("""
        SELECT
            email
        FROM clientes
        WHERE email = %s 
        """, (data["email"],))
        
        if cur.fetchone() is not None:
            return error(message="El email asignado ya existe, coloque otro diferente", status=409)

        cur.execute("""
            INSERT INTO clientes (
                folio, nombre, apellido_paterno, apellido_materno,
                telefono, email, id_estado, id_municipio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_cliente
        """, (
            data["folio"],
            data["nombre"],
            data["apellido_paterno"],
            data.get("apellido_materno"),  # Opcional
            data["telefono"],
            data["email"],
            data.get("id_estado"),         # Opcional
            data.get("id_municipio"),       # Opcional
        ))

        nuevo_id = cur.fetchone()["id_cliente"]

        for id_cat in categorias_ids:
            cur.execute("""
            INSERT INTO clientes_categoria (
                id_cat, id_cliente
            ) VALUES (%s, %s)
            """, (id_cat, nuevo_id))

        conn.commit()
        return success(data={"id_cliente": nuevo_id}, message="Cliente creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# PUT /clientes/<id> → Actualizar un cliente
# ─────────────────────────────────────────
@bp.route("/<int:id_cliente>", methods=["PUT"])
def actualizar_cliente(id_cliente):
    conn = None
    try:
        data = request.get_json()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el cliente existe antes de actualizar
        cur.execute("SELECT id_cliente FROM clientes WHERE id_cliente = %s", (id_cliente,))
        if cur.fetchone() is None:
            return error(message="Cliente no encontrado", status=404)

        # Verificar que el estado exista
        if data.get("id_estado") is not None:
            cur.execute("""
            SELECT 
                id_estado 
            FROM estados
            WHERE id_estado = %s
            """, (data.get("id_estado"),))
            estado = cur.fetchone()
            if estado is None:
                return error(message="El estado seleccionado no existe", status=404)

        # Verificar que el municipio exista
        if data.get("id_municipio") is not None:
            cur.execute("""
            SELECT
                id_municipio
            FROM municipios
            WHERE id_municipio = %s
            """, (data.get("id_municipio"),))
            municipio = cur.fetchone()
            if municipio is None:
                return error(message="El municipio seleccionado no existe", status=404)
        
        # Verificar que el folio no esté repetido
        cur.execute("""
        SELECT
            folio
        FROM clientes
        WHERE folio = %s 
        """, (data.get("folio"),))
        
        if cur.fetchone() is not None:
            return error(message="El folio asignado ya existe, coloque otro diferente", status=409)

        # Verificar que el telefono no esté repetido
        cur.execute("""
        SELECT
            telefono
        FROM clientes
        WHERE telefono = %s 
        """, (data.get("telefono"),))
        
        if cur.fetchone() is not None:
            return error(message="El telefono asignado ya existe, coloque otro diferente", status=409)
        
        # Verificar que el email no esté repetido
        cur.execute("""
        SELECT
            email
        FROM clientes
        WHERE email = %s 
        """, (data.get("email"),))
        
        if cur.fetchone() is not None:
            return error(message="El email asignado ya existe, coloque otro diferente", status=409)

        cur.execute("SELECT * FROM clientes WHERE id_cliente = %s" , (id_cliente,))
        cliente_actual = cur.fetchone()

        cur.execute("""
            UPDATE clientes SET
                folio = %s,
                nombre = %s,
                apellido_paterno = %s,
                apellido_materno = %s,
                telefono = %s,
                email = %s,
                id_estado = %s,
                id_municipio = %s
            WHERE id_cliente = %s
        """, (
            data.get("folio", cliente_actual["folio"]),
            data.get("nombre", cliente_actual["nombre"]),
            data.get("apellido_paterno", cliente_actual["apellido_paterno"]),
            data.get("apellido_materno", cliente_actual["apellido_materno"]),
            data.get("telefono", cliente_actual["telefono"]),
            data.get("email", cliente_actual["email"]),
            data.get("id_estado", cliente_actual["id_estado"]),
            data.get("id_municipio", cliente_actual["id_municipio"]),
            id_cliente
        ))

        if "categorias_ids" in data:
            cur.execute("DELETE FROM clientes_categoria WHERE id_cliente = %s", (id_cliente,))
            for id_cat in data["categorias_ids"]:
                cur.execute("""
                    INSERT INTO clientes_categoria (id_cat, id_cliente)
                    VALUES (%s, %s)
                """, (id_cat, id_cliente))

        conn.commit()
        return success(message="Cliente actualizado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# DELETE /clientes/<id> → Eliminar un cliente
# ─────────────────────────────────────────
@bp.route("/<int:id_cliente>", methods=["DELETE"])
def eliminar_cliente(id_cliente):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el cliente existe antes de eliminar
        cur.execute("SELECT id_cliente FROM clientes WHERE id_cliente = %s", (id_cliente,))
        if cur.fetchone() is None:
            return error(message="Cliente no encontrado", status=404)

        cur.execute("DELETE FROM clientes_categoria WHERE id_cliente = %s", (id_cliente,))
        cur.execute("DELETE FROM clientes WHERE id_cliente = %s", (id_cliente,))
        conn.commit()
        return success(message="Cliente eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
