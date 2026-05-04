INSERT INTO usuarios (nombre_usuario, email, hashed_password, id_rol)
VALUES (
    'admin',
    'admin@admin.com',
    '$2b$12$LQv3c1yqBwlVHpPjrKNZO.Rf1TjCKjSJNQWIy3RJ5bWXqPjqiO6Hy',
    (SELECT id_rol FROM roles WHERE nombre = 'Administrador')
);
