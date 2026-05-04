from flask import Blueprint, request
from app.database import get_connection
from app.utils.response import success, error
from app.utils.jwt import verificar_token, requiere_admin
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


# ─────────────────────────────────────────
# GET /usuarios/ → Listar todos los usuarios
# ─────────────────────────────────────────
@bp.route("/", methods=["GET"])
@requiere_admin
def listar_usuarios():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                u.id_usuario,
                u.nombre_usuario,
                u.telefono,
                u.email,
                r.nombre AS rol
            FROM usuarios u
            LEFT JOIN roles r ON u.id_rol = r.id_rol
            ORDER BY u.id_usuario ASC
        """)
        usuarios = cur.fetchall()
        return success(data=usuarios, message="Usuarios obtenidos correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# GET /usuarios/<id> → Detalle de un usuario
# ─────────────────────────────────────────
@bp.route("/<int:id_usuario>", methods=["GET"])
@requiere_admin
def obtener_usuario(id_usuario):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                u.id_usuario,
                u.nombre_usuario,
                u.telefono,
                u.email,
                r.nombre AS rol
            FROM usuarios u
            LEFT JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s
        """, (id_usuario,))
        usuario = cur.fetchone()
        if usuario is None:
            return error(message="Usuario no encontrado", status=404)
        return success(data=usuario, message="Usuario obtenido correctamente")
    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /usuarios/ → Crear un usuario
# ─────────────────────────────────────────
@bp.route("/", methods=["POST"])
@requiere_admin
def crear_usuario():
    conn = None
    try:
        data = request.get_json()

        campos_requeridos = ["nombre_usuario", "email", "password"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que el email no esté ya registrado
        cur.execute("SELECT id_usuario FROM usuarios WHERE email = %s", (data["email"],))
        if cur.fetchone():
            return error(message="El email ya está registrado", status=400)

        # Encriptar la contraseña
        # bcrypt.hashpw espera bytes, por eso el .encode()
        # El resultado también es bytes, por eso el .decode() al final
        hashed = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cur.execute("""
            INSERT INTO usuarios (nombre_usuario, telefono, email, hashed_password, id_rol)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_usuario
        """, (
            data["nombre_usuario"],
            data.get("telefono"),
            data["email"],
            hashed,
            data.get("id_rol")
        ))
        conn.commit()
        nuevo_id = cur.fetchone()["id_usuario"]
        return success(data={"id_usuario": nuevo_id}, message="Usuario creado correctamente", status=201)
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# PUT /usuarios/<id> → Actualizar un usuario
# ─────────────────────────────────────────
@bp.route("/<int:id_usuario>", methods=["PUT"])
@requiere_admin
def actualizar_usuario(id_usuario):
    conn = None
    try:
        data = request.get_json()

        campos_requeridos = ["nombre_usuario", "email"]
        for campo in campos_requeridos:
            if not data.get(campo):
                return error(message=f"El campo '{campo}' es obligatorio", status=400)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_usuario FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        if cur.fetchone() is None:
            return error(message="Usuario no encontrado", status=404)

        # Si mandan nueva contraseña la encriptamos, si no la dejamos como está
        if data.get("password"):
            hashed = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cur.execute("""
                UPDATE usuarios SET
                    nombre_usuario = %s,
                    telefono = %s,
                    email = %s,
                    hashed_password = %s,
                    id_rol = %s
                WHERE id_usuario = %s
            """, (
                data["nombre_usuario"],
                data.get("telefono"),
                data["email"],
                hashed,
                data.get("id_rol"),
                id_usuario
            ))
        else:
            cur.execute("""
                UPDATE usuarios SET
                    nombre_usuario = %s,
                    telefono = %s,
                    email = %s,
                    id_rol = %s
                WHERE id_usuario = %s
            """, (
                data["nombre_usuario"],
                data.get("telefono"),
                data["email"],
                data.get("id_rol"),
                id_usuario
            ))

        conn.commit()
        return success(message="Usuario actualizado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# DELETE /usuarios/<id> → Eliminar un usuario
# ─────────────────────────────────────────
@bp.route("/<int:id_usuario>", methods=["DELETE"])
@requiere_admin
def eliminar_usuario(id_usuario):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id_usuario FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        if cur.fetchone() is None:
            return error(message="Usuario no encontrado", status=404)

        cur.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        conn.commit()
        return success(message="Usuario eliminado correctamente")
    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /usuarios/login → Login
# ─────────────────────────────────────────
@bp.route("/login", methods=["POST"])
def login():
    conn = None
    try:
        data = request.get_json()

        if not data.get("email") or not data.get("password"):
            return error(message="Email y password son obligatorios", status=400)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                u.id_usuario,
                u.nombre_usuario,
                u.email,
                u.hashed_password,
                r.nombre AS rol
            FROM usuarios u
            LEFT JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.email = %s
        """, (data["email"],))
        usuario = cur.fetchone()

        if usuario is None:
            return error(message="Credenciales incorrectas", status=401)

        # Verificar contraseña
        # bcrypt.checkpw compara el password ingresado con el hash guardado
        password_valido = bcrypt.checkpw(
            data["password"].encode("utf-8"),
            usuario["hashed_password"].encode("utf-8")
        )

        if not password_valido:
            return error(message="Credenciales incorrectas", status=401)

        token = jwt.encode(
        {
        "id_usuario": usuario["id_usuario"],
        "nombre_usuario": usuario["nombre_usuario"],
        "email": usuario["email"],
        "rol": usuario["rol"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=16)
        },
        os.getenv("SECRET_KEY"),
        algorithm="HS256")

        return success(data={
        "id_usuario": usuario["id_usuario"],
        "nombre_usuario": usuario["nombre_usuario"],
        "email": usuario["email"],
        "rol": usuario["rol"],
        "token": token
        }, message="Login exitoso")

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
