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
    app.register_blueprint(clientes.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(almacenes.bp)
    app.register_blueprint(inventario.bp)
    app.register_blueprint(ventas.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(categorias.bp)
    app.register_blueprint(subcategorias.bp)

    return app
