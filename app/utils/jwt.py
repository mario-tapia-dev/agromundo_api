import jwt
import os
from functools import wraps
from flask import request
from app.utils.response import error

def verificar_token(f):
    """
    Decorador que verifica que el token JWT sea válido.
    Si es válido, inyecta los datos del usuario en la función.
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        token = None

        # El token viene en el encabezado Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return error(message="Token de autenticación requerido", status=401)

        try:
            payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
            request.usuario_actual = payload
        except jwt.ExpiredSignatureError:
            return error(message="El token ha expirado", status=401)
        except jwt.InvalidTokenError:
            return error(message="Token inválido", status=401)

        return f(*args, **kwargs)
    return decorador


def requiere_admin(f):
    """
    Decorador que verifica que el token sea válido
    y que el usuario tenga rol de Administrador.
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        token = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return error(message="Token de autenticación requerido", status=401)

        try:
            payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
            request.usuario_actual = payload
        except jwt.ExpiredSignatureError:
            return error(message="El token ha expirado", status=401)
        except jwt.InvalidTokenError:
            return error(message="Token inválido", status=401)

        if payload.get("rol") != "Administrador":
            return error(message="No tienes permisos para acceder a este recurso", status=403)

        return f(*args, **kwargs)
    return decorador
