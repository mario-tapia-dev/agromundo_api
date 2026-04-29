-- Agregar cliente público general
INSERT INTO clientes (folio, nombre, apellido_paterno, telefono, email)
VALUES ('PUB-001', 'Público', 'General', '0000000000', 'publico@general.com');

-- Agregar columna id_cliente a ventas
ALTER TABLE ventas ADD COLUMN id_cliente INTEGER REFERENCES clientes(id_cliente);

-- Asignar el id del cliente público general a las ventas existentes
UPDATE ventas SET id_cliente = (SELECT id_cliente FROM clientes WHERE folio = 'PUB-001');
