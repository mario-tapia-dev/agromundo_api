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
                c.id_cliente,
                c.folio,
                c.nombre,
                c.apellido_paterno,
                c.apellido_materno,
                c.telefono,
                c.email,
                e.nombre AS estado,
                m.nombre AS municipio
            FROM clientes c
            LEFT JOIN estado e ON c.id_estado = e.id_estado
            LEFT JOIN municipio m ON c.id_municipio = m.id_municipio
            WHERE c.id_cliente = %s
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

        conn = get_connection()
        cur = conn.cursor()
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
            data.get("id_municipio")       # Opcional
        ))
        conn.commit()
        nuevo_id = cur.fetchone()["id_cliente"]
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
            data["folio"],
            data["nombre"],
            data["apellido_paterno"],
            data.get("apellido_materno"),
            data["telefono"],
            data["email"],
            data.get("id_estado"),
            data.get("id_municipio"),
            id_cliente
        ))
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
