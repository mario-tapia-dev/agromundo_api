from flask import Flask
from app.routes import clientes, productos, almacenes, inventario, ventas, usuarios, categorias, subcategorias

def create_app():
    """
    Función fábrica de la app. En lugar de crear la app
    directamente, la creamos dentro de una función.
    Esto facilita las pruebas y la configuración.
    """
    app = Flask(__name__)

    # Registrar los blueprints (módulos de rutas)
    app.register_blueprint(clientes.bp, url_prefix="/api/clientes")
    app.register_blueprint(productos.bp, url_prefix="/api/productos")
    app.register_blueprint(almacenes.bp, url_prefix="/api/almacenes")
    app.register_blueprint(inventario.bp, url_prefix="/api/inventario")
    app.register_blueprint(ventas.bp, url_prefix="/api/ventas")
    app.register_blueprint(usuarios.bp, url_prefix="/api/usuarios")
    app.register_blueprint(categorias.bp, url_prefix="/api/categorias")
    app.register_blueprint(subcategorias.bp, url_prefix="/api/subcategorias")

    return app
