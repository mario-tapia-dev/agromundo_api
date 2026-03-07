-- Roles
CREATE TABLE roles (
    id_rol SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255)
);

-- Usuarios
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    id_rol INTEGER REFERENCES roles(id_rol)
);

-- Estados
CREATE TABLE estado (
    id_estado SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Municipios
CREATE TABLE municipio (
    id_municipio SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_estado INTEGER REFERENCES estado(id_estado)
);

-- Clientes
CREATE TABLE clientes (
    id_cliente SERIAL PRIMARY KEY,
    folio VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido_paterno VARCHAR(100),
    apellido_materno VARCHAR(100),
    telefono VARCHAR(20) UNIQUE,
    email VARCHAR(100) UNIQUE,
    id_estado INTEGER REFERENCES estado(id_estado),
    id_municipio INTEGER REFERENCES municipio(id_municipio)
);

-- Categorias
CREATE TABLE categoria (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Subcategorias
CREATE TABLE subcategoria (
    id_subcategoria SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    valor_numerico FLOAT,
    unidad VARCHAR(50)
);

-- Productos
CREATE TABLE productos (
    id_productos SERIAL PRIMARY KEY,
    codigo VARCHAR(50),
    descripcion VARCHAR(255),
    precio FLOAT,
    id_categoria INTEGER REFERENCES categoria(id_categoria)
);

-- Almacen
CREATE TABLE almacen (
    id_almacen SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    codigo VARCHAR(50)
);

-- Inventario
CREATE TABLE inventario (
    id_inventario SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_productos),
    id_almacen INTEGER REFERENCES almacen(id_almacen),
    stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0
);

-- Ventas
CREATE TABLE ventas (
    id_venta SERIAL PRIMARY KEY,
    folio VARCHAR(50),
    precio_venta_final FLOAT,
    id_estado INTEGER REFERENCES estado(id_estado),
    id_municipio INTEGER REFERENCES municipio(id_municipio)
);

-- Detalle de venta
CREATE TABLE detalle_venta (
    id_detalle_venta SERIAL PRIMARY KEY,
    cantidad_vendida INTEGER,
    precio_venta FLOAT,
    id_venta INTEGER REFERENCES ventas(id_venta),
    id_producto INTEGER REFERENCES productos(id_productos)
);

-- Movimientos de inventario
CREATE TABLE movimientos_inventario (
    id_movimiento SERIAL PRIMARY KEY,
    tipo BOOLEAN NOT NULL,
    cantidad INTEGER,
    id_venta INTEGER REFERENCES ventas(id_venta),
    id_producto INTEGER REFERENCES productos(id_productos),
    id_almacen INTEGER REFERENCES almacen(id_almacen)
);

-- Tablas intermedias
CREATE TABLE producto_subcategoria (
    id_prod_sub SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_productos),
    id_subcategoria INTEGER REFERENCES subcategoria(id_subcategoria)
);

CREATE TABLE almacen_categoria (
    id_almacen_categoria SERIAL PRIMARY KEY,
    id_almacen INTEGER REFERENCES almacen(id_almacen),
    id_categoria INTEGER REFERENCES categoria(id_categoria)
);

CREATE TABLE categoria_subcategoria (
    id_cat_subcat SERIAL PRIMARY KEY,
    id_categoria INTEGER REFERENCES categoria(id_categoria),
    id_subcategoria INTEGER REFERENCES subcategoria(id_subcategoria)
);

CREATE TABLE clientes_categoria (
    id_clte_cat SERIAL PRIMARY KEY,
    id_categoria INTEGER REFERENCES categoria(id_categoria),
    id_cliente INTEGER REFERENCES clientes(id_cliente)
);
