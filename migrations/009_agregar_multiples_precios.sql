-- Crear tabla intermedia para guardar múltiples precios
CREATE TABLE productos_precios (id_productos_precios SERIAL PRIMARY KEY, id_producto INTEGER REFERENCES productos(id_producto), margen INTEGER, precio_margen FLOAT);

