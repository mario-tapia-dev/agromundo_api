ALTER TABLE ventas ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();
ALTER TABLE movimientos_inventario ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();
