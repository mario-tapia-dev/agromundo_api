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
CREATE TABLE estados (
    id_estado SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Municipios
CREATE TABLE municipios (
    id_municipio SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_estado INTEGER REFERENCES estados(id_estado)
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
    id_estado INTEGER REFERENCES estados(id_estado),
    id_municipio INTEGER REFERENCES municipios(id_municipio)
);

-- Categorias
CREATE TABLE categorias (
    id_cat SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Subcategorias
CREATE TABLE subcategorias (
    id_subcat SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    valor_numerico FLOAT,
    unidad VARCHAR(50)
);

-- Productos
CREATE TABLE productos (
    id_producto SERIAL PRIMARY KEY,
    folio VARCHAR(50),
    descripcion VARCHAR(255),
    precio FLOAT
);

-- Almacen
CREATE TABLE almacenes (
    id_almacen SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    folio VARCHAR(50)
);

-- Inventario
CREATE TABLE inventarios (
    id_inventario SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_producto),
    id_almacen INTEGER REFERENCES almacenes(id_almacen),
    stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0
);

-- Ventas
CREATE TABLE ventas (
    id_venta SERIAL PRIMARY KEY,
    folio VARCHAR(50),
    precio_venta_final FLOAT,
    id_estado INTEGER REFERENCES estados(id_estado),
    id_municipio INTEGER REFERENCES municipios(id_municipio)
);

-- Detalle de venta
CREATE TABLE detalle_venta (
    id_detalle_venta SERIAL PRIMARY KEY,
    cantidad_vendida INTEGER,
    precio_venta FLOAT,
    id_venta INTEGER REFERENCES ventas(id_venta),
    id_producto INTEGER REFERENCES productos(id_producto)
);

-- Movimientos de inventario
CREATE TABLE movimientos_inventario (
    id_mov SERIAL PRIMARY KEY,
    tipo BOOLEAN NOT NULL,
    cantidad INTEGER,
    id_venta INTEGER REFERENCES ventas(id_venta),
    id_producto INTEGER REFERENCES productos(id_producto),
    id_almacen INTEGER REFERENCES almacenes(id_almacen)
);

-- Tablas intermedias
CREATE TABLE producto_categoria (
    id_prod_cat SERIAL PRIMARY KEY,
    id_prod INTEGER REFERENCES productos(id_producto),
    id_cat INTEGER REFERENCES categorias(id_cat)
);

CREATE TABLE producto_subcategoria (
    id_prod_subcat SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_producto),
    id_subcat INTEGER REFERENCES subcategorias(id_subcat)
);

CREATE TABLE almacen_categoria (
    id_alm_cat SERIAL PRIMARY KEY,
    id_almacen INTEGER REFERENCES almacenes(id_almacen),
    id_cat INTEGER REFERENCES categorias(id_cat)
);

CREATE TABLE categoria_subcategoria (
    id_cat_subcat SERIAL PRIMARY KEY,
    id_cat INTEGER REFERENCES categorias(id_cat),
    id_subcat INTEGER REFERENCES subcategorias(id_subcat)
);

CREATE TABLE clientes_categoria (
    id_clte_cat SERIAL PRIMARY KEY,
    id_cat INTEGER REFERENCES categorias(id_cat),
    id_cliente INTEGER REFERENCES clientes(id_cliente)
);
