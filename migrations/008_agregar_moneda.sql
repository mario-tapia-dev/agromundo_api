-- Agregar columna moneda para tipo de moneda
ALTER TABLE productos ADD COLUMN moneda VARCHAR(3);

-- Agrega una restricción para limitar a pesos y dólares
ALTER TABLE productos ADD CONSTRAINT check_moneda CHECK (moneda IN ('MXN', 'USD'));
  
