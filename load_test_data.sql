USE economy_rp;

-- 1. Dar saldo a Jugadores 17, 19 y 23
INSERT IGNORE INTO T_Cuenta (id_jugador, id_servidor, tipo_cuenta, saldo_inicial, saldo_disponible)
SELECT id_jugador, id_servidor, 'PERSONAL', 50000.00, 50000.00
FROM T_Jugador WHERE id_jugador IN (17, 19, 23);

UPDATE T_Cuenta SET saldo_disponible = 50000.00 WHERE id_jugador IN (17, 19, 23) AND tipo_cuenta = 'PERSONAL';

-- 2. Agregar items de prueba
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'AK-47', 2500.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'Kit de Reparación', 150.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'Kit de Reparación', 150.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'Kit de Reparación', 150.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'Kit de Reparación', 150.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (17, 'Kit de Reparación', 150.00, FALSE);

INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (19, 'AK-47', 2500.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (19, 'AK-47', 2500.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (19, 'Medicamentos', 100.00, FALSE);

-- Items para Jugador 23
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (23, 'Coche de Lujo', 50000.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (23, 'Reloj de Oro', 12000.00, FALSE);
INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (23, 'Propiedad Mansión', 150000.00, FALSE);
