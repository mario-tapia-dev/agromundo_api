-- Agregar columna moneda para tipo de moneda
ALTER TABLE productos ADD COLUMN moneda VARCHAR(3) NOT NULL DEFAULT 'MXN';

-- Agrega una restricción para limitar a pesos y dólares
ALTER TABLE productos ADD CONSTRAINT check_moneda CHECK (moneda IN ('MXN', 'USD'));
  
