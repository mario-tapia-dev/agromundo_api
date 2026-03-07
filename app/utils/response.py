from flask import jsonify

def success(data=None, message="OK", status=200):
    """
    Respuesta exitosa estándar.
    data: los datos a retornar (lista, diccionario, etc.)
    message: mensaje descriptivo
    status: código HTTP (200, 201, etc.)
    """
    return jsonify({
        "success": True,
        "message": message,
        "data": data
    }), status


def error(message="Error", status=400):
    """
    Respuesta de error estándar.
    message: descripción del error
    status: código HTTP (400, 404, 500, etc.)
    """
    return jsonify({
        "success": False,
        "message": message,
        "data": None
    }), status
