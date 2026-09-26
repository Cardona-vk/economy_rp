DROP DATABASE IF EXISTS economy_rp;
CREATE DATABASE economy_rp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE economy_rp;

CREATE TABLE T_Servidor (
  id_servidor INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  porcentaje_comision DECIMAL(5,2) NOT NULL,
  limite_bienes_por_jugador INT NOT NULL,
  tiempo_enfriamiento_min INT NOT NULL
) ENGINE=InnoDB;

CREATE TABLE T_Jugador (
  id_jugador INT AUTO_INCREMENT PRIMARY KEY,
  id_servidor INT NOT NULL,
  nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
  correo VARCHAR(150) NOT NULL UNIQUE,
  contrasena_hash VARCHAR(255) NOT NULL,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
  CONSTRAINT fk_jugador_servidor FOREIGN KEY (id_servidor) REFERENCES T_Servidor(id_servidor),
  CONSTRAINT chk_jugador_estado CHECK (estado IN ('ACTIVO','BANCARROTA','SUSPENDIDO'))
) ENGINE=InnoDB;

CREATE TABLE T_Empleo (
  id_empleo INT AUTO_INCREMENT PRIMARY KEY,
  id_servidor INT NOT NULL,
  nombre_empleo VARCHAR(100) NOT NULL,
  tarifa_base DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_empleo_servidor FOREIGN KEY (id_servidor) REFERENCES T_Servidor(id_servidor)
) ENGINE=InnoDB;

CREATE TABLE T_Jornada_Laboral (
  id_jornada INT AUTO_INCREMENT PRIMARY KEY,
  id_jugador INT NOT NULL,
  id_empleo INT NOT NULL,
  horas_trabajadas DECIMAL(6,2) NOT NULL,
  fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  monto_pagado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT fk_jornada_jugador FOREIGN KEY (id_jugador) REFERENCES T_Jugador(id_jugador),
  CONSTRAINT fk_jornada_empleo FOREIGN KEY (id_empleo) REFERENCES T_Empleo(id_empleo)
) ENGINE=InnoDB;

CREATE TABLE T_Cuenta (
  id_cuenta INT AUTO_INCREMENT PRIMARY KEY,
  id_jugador INT NULL,
  id_servidor INT NULL,
  tipo_cuenta VARCHAR(20) NOT NULL,
  saldo_inicial DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  saldo_disponible DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT fk_cuenta_jugador FOREIGN KEY (id_jugador) REFERENCES T_Jugador(id_jugador),
  CONSTRAINT fk_cuenta_servidor FOREIGN KEY (id_servidor) REFERENCES T_Servidor(id_servidor),
  CONSTRAINT uq_cuenta_jugador UNIQUE (id_jugador),
  CONSTRAINT chk_cuenta_tipo CHECK (tipo_cuenta IN ('PERSONAL','SISTEMA'))
) ENGINE=InnoDB;

ALTER TABLE T_Cuenta
  ADD COLUMN clave_sistema_unica INT GENERATED ALWAYS AS
    (CASE WHEN tipo_cuenta = 'SISTEMA' THEN id_servidor ELSE NULL END) STORED,
  ADD UNIQUE KEY uq_cuenta_sistema_por_servidor (clave_sistema_unica);

CREATE TABLE T_Item (
  id_item INT AUTO_INCREMENT PRIMARY KEY,
  id_jugador INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  precio DECIMAL(12,2) NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tiene_deuda BOOLEAN NOT NULL DEFAULT FALSE,
  antiguedad_dias INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_item_jugador FOREIGN KEY (id_jugador) REFERENCES T_Jugador(id_jugador)
) ENGINE=InnoDB;

CREATE TABLE T_Negociacion_Tradeo (
  id_negociacion INT AUTO_INCREMENT PRIMARY KEY,
  id_jugador_1 INT NOT NULL,
  id_jugador_2 INT NOT NULL,
  id_item_j1 INT NULL,
  id_item_j2 INT NULL,
  monto_j1 DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  monto_j2 DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  confirmacion_j1 BOOLEAN NOT NULL DEFAULT FALSE,
  confirmacion_j2 BOOLEAN NOT NULL DEFAULT FALSE,
  estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_expiracion DATETIME NOT NULL,
  CONSTRAINT fk_negociacion_jugador1 FOREIGN KEY (id_jugador_1) REFERENCES T_Jugador(id_jugador),
  CONSTRAINT fk_negociacion_jugador2 FOREIGN KEY (id_jugador_2) REFERENCES T_Jugador(id_jugador),
  CONSTRAINT fk_negociacion_item_j1 FOREIGN KEY (id_item_j1) REFERENCES T_Item(id_item),
  CONSTRAINT fk_negociacion_item_j2 FOREIGN KEY (id_item_j2) REFERENCES T_Item(id_item),
  CONSTRAINT chk_negociacion_estado CHECK (estado IN ('PENDIENTE','CONFIRMADO','CANCELADO','EXPIRADO')),
  CONSTRAINT chk_negociacion_no_vacia CHECK (
    id_item_j1 IS NOT NULL OR id_item_j2 IS NOT NULL OR monto_j1 > 0 OR monto_j2 > 0
  )
) ENGINE=InnoDB;

CREATE TABLE T_Transaccion (
  id_transaccion INT AUTO_INCREMENT PRIMARY KEY,
  id_item_afectado INT NULL,
  id_negociacion INT NULL,
  id_jornada INT NULL,
  tipo_transaccion VARCHAR(30) NOT NULL,
  estado_transaccion VARCHAR(20) NOT NULL DEFAULT 'COMPLETADA',
  monto DECIMAL(12,2) NOT NULL,
  fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_transaccion_item FOREIGN KEY (id_item_afectado) REFERENCES T_Item(id_item),
  CONSTRAINT fk_transaccion_negociacion FOREIGN KEY (id_negociacion) REFERENCES T_Negociacion_Tradeo(id_negociacion),
  CONSTRAINT fk_transaccion_jornada FOREIGN KEY (id_jornada) REFERENCES T_Jornada_Laboral(id_jornada),
  CONSTRAINT chk_transaccion_tipo CHECK (tipo_transaccion IN ('PAGO_SALARIO','TRADEO_P2P','COMPRA_COMERCIANTE')),
  CONSTRAINT chk_transaccion_estado CHECK (estado_transaccion IN ('COMPLETADA','CANCELADA','REVERTIDA'))
) ENGINE=InnoDB;

CREATE TABLE T_Detalle_Transaccion (
  id_detalle INT AUTO_INCREMENT PRIMARY KEY,
  id_transaccion INT NOT NULL,
  cuenta_origen INT NOT NULL,
  cuenta_destino INT NOT NULL,
  tipo_movimiento VARCHAR(10) NOT NULL,
  monto_detalle DECIMAL(12,2) NOT NULL,
  concepto VARCHAR(80),
  CONSTRAINT fk_detalle_transaccion FOREIGN KEY (id_transaccion) REFERENCES T_Transaccion(id_transaccion),
  CONSTRAINT fk_detalle_origen FOREIGN KEY (cuenta_origen) REFERENCES T_Cuenta(id_cuenta),
  CONSTRAINT fk_detalle_destino FOREIGN KEY (cuenta_destino) REFERENCES T_Cuenta(id_cuenta),
  CONSTRAINT chk_detalle_tipo CHECK (tipo_movimiento IN ('DEBITO','CREDITO'))
) ENGINE=InnoDB;

DELIMITER //

CREATE TRIGGER trg_item_limite_bienes
BEFORE INSERT ON T_Item
FOR EACH ROW
BEGIN
  DECLARE v_cantidad INT;
  DECLARE v_limite INT;
  SELECT COUNT(*) INTO v_cantidad FROM T_Item WHERE id_jugador = NEW.id_jugador;
  SELECT s.limite_bienes_por_jugador INTO v_limite
  FROM T_Jugador j JOIN T_Servidor s ON j.id_servidor = s.id_servidor
  WHERE j.id_jugador = NEW.id_jugador;
  IF v_cantidad >= v_limite THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador ya alcanzo el limite maximo de bienes permitido por el servidor';
  END IF;
END //

CREATE TRIGGER trg_jornada_enfriamiento
BEFORE INSERT ON T_Jornada_Laboral
FOR EACH ROW
BEGIN
  DECLARE v_ultima DATETIME;
  DECLARE v_minutos INT;
  SELECT MAX(fecha_hora) INTO v_ultima FROM T_Jornada_Laboral
  WHERE id_jugador = NEW.id_jugador AND id_empleo = NEW.id_empleo;
  SELECT s.tiempo_enfriamiento_min INTO v_minutos
  FROM T_Jugador j JOIN T_Servidor s ON j.id_servidor = s.id_servidor
  WHERE j.id_jugador = NEW.id_jugador;
  IF v_ultima IS NOT NULL AND TIMESTAMPDIFF(MINUTE, v_ultima, NEW.fecha_hora) < v_minutos THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador todavia esta en periodo de enfriamiento para este empleo';
  END IF;
END //

CREATE TRIGGER trg_jornada_calcular_pago
BEFORE INSERT ON T_Jornada_Laboral
FOR EACH ROW
BEGIN
  DECLARE v_tarifa DECIMAL(10,2);
  SELECT tarifa_base INTO v_tarifa FROM T_Empleo WHERE id_empleo = NEW.id_empleo;
  SET NEW.monto_pagado = v_tarifa * NEW.horas_trabajadas;
END //

CREATE TRIGGER trg_detalle_origen_salario
BEFORE INSERT ON T_Detalle_Transaccion
FOR EACH ROW
BEGIN
  DECLARE v_tipo VARCHAR(30);
  DECLARE v_tipo_cuenta_origen VARCHAR(20);
  SELECT tipo_transaccion INTO v_tipo FROM T_Transaccion WHERE id_transaccion = NEW.id_transaccion;
  IF v_tipo = 'PAGO_SALARIO' AND NEW.tipo_movimiento = 'DEBITO' THEN
    SELECT tipo_cuenta INTO v_tipo_cuenta_origen FROM T_Cuenta WHERE id_cuenta = NEW.cuenta_origen;
    IF v_tipo_cuenta_origen != 'SISTEMA' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Todo pago de salario debe originarse desde la cuenta Sistema del servidor';
    END IF;
  END IF;
END //

CREATE TRIGGER trg_transaccion_no_update
BEFORE UPDATE ON T_Transaccion
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Las transacciones son inmutables, no se pueden modificar';
END //

CREATE TRIGGER trg_transaccion_no_delete
BEFORE DELETE ON T_Transaccion
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Las transacciones son inmutables, no se pueden eliminar';
END //

CREATE TRIGGER trg_detalle_no_update
BEFORE UPDATE ON T_Detalle_Transaccion
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El detalle de una transaccion es inmutable, no se puede modificar';
END //

CREATE TRIGGER trg_detalle_no_delete
BEFORE DELETE ON T_Detalle_Transaccion
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El detalle de una transaccion es inmutable, no se puede eliminar';
END //

CREATE TRIGGER trg_cuenta_bancarrota
AFTER UPDATE ON T_Cuenta
FOR EACH ROW
BEGIN
  IF NEW.saldo_disponible < 0 AND OLD.saldo_disponible >= 0 THEN
    UPDATE T_Jugador SET estado = 'BANCARROTA' WHERE id_jugador = NEW.id_jugador;
  END IF;
  IF NEW.saldo_disponible >= 0 AND OLD.saldo_disponible < 0 THEN
    UPDATE T_Jugador SET estado = 'ACTIVO' WHERE id_jugador = NEW.id_jugador AND estado = 'BANCARROTA';
  END IF;
END //

CREATE PROCEDURE sp_pagar_jornada(IN p_id_jugador INT, IN p_id_empleo INT, IN p_horas DECIMAL(6,2))
sp_pago: BEGIN
  DECLARE v_id_jornada INT;
  DECLARE v_monto DECIMAL(10,2);
  DECLARE v_id_cuenta_jugador INT;
  DECLARE v_id_cuenta_sistema INT;
  DECLARE v_id_transaccion INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  INSERT INTO T_Jornada_Laboral (id_jugador, id_empleo, horas_trabajadas)
  VALUES (p_id_jugador, p_id_empleo, p_horas);
  SET v_id_jornada = LAST_INSERT_ID();

  SELECT monto_pagado INTO v_monto FROM T_Jornada_Laboral WHERE id_jornada = v_id_jornada;
  SELECT id_cuenta INTO v_id_cuenta_jugador FROM T_Cuenta WHERE id_jugador = p_id_jugador;

  SELECT c.id_cuenta INTO v_id_cuenta_sistema
  FROM T_Cuenta c JOIN T_Jugador j ON j.id_servidor = c.id_servidor
  WHERE j.id_jugador = p_id_jugador AND c.tipo_cuenta = 'SISTEMA';

  INSERT INTO T_Transaccion (id_jornada, tipo_transaccion, estado_transaccion, monto)
  VALUES (v_id_jornada, 'PAGO_SALARIO', 'COMPLETADA', v_monto);
  SET v_id_transaccion = LAST_INSERT_ID();

  INSERT INTO T_Detalle_Transaccion (id_transaccion, cuenta_origen, cuenta_destino, tipo_movimiento, monto_detalle, concepto)
  VALUES
    (v_id_transaccion, v_id_cuenta_sistema, v_id_cuenta_jugador, 'DEBITO', v_monto, 'PAGO_SALARIO'),
    (v_id_transaccion, v_id_cuenta_sistema, v_id_cuenta_jugador, 'CREDITO', v_monto, 'PAGO_SALARIO');

  UPDATE T_Cuenta SET saldo_disponible = saldo_disponible - v_monto WHERE id_cuenta = v_id_cuenta_sistema;
  UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + v_monto WHERE id_cuenta = v_id_cuenta_jugador;

  COMMIT;
END //

CREATE PROCEDURE sp_abrir_negociacion(
  IN p_id_jugador_1 INT, IN p_id_jugador_2 INT,
  IN p_id_item_j1 INT, IN p_id_item_j2 INT,
  IN p_monto_j1 DECIMAL(12,2), IN p_monto_j2 DECIMAL(12,2),
  IN p_minutos_expiracion INT)
sp_abrir: BEGIN
  DECLARE v_pendientes INT;
  DECLARE v_tradeos_hoy INT;

  SELECT COUNT(*) INTO v_pendientes FROM T_Negociacion_Tradeo
  WHERE estado = 'PENDIENTE' AND (id_jugador_1 IN (p_id_jugador_1, p_id_jugador_2)
                                OR id_jugador_2 IN (p_id_jugador_1, p_id_jugador_2));
  IF v_pendientes > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Uno de los jugadores ya tiene una negociacion pendiente abierta';
    LEAVE sp_abrir;
  END IF;

  SELECT COUNT(*) INTO v_tradeos_hoy FROM T_Transaccion
  WHERE tipo_transaccion = 'TRADEO_P2P' AND DATE(fecha_hora) = CURDATE()
    AND id_negociacion IN (SELECT id_negociacion FROM T_Negociacion_Tradeo WHERE id_jugador_1 = p_id_jugador_1 OR id_jugador_2 = p_id_jugador_1);
  IF v_tradeos_hoy >= 5 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador ya alcanzo el limite diario de 5 tradeos';
    LEAVE sp_abrir;
  END IF;

  INSERT INTO T_Negociacion_Tradeo
    (id_jugador_1, id_jugador_2, id_item_j1, id_item_j2, monto_j1, monto_j2, fecha_expiracion)
  VALUES
    (p_id_jugador_1, p_id_jugador_2, p_id_item_j1, p_id_item_j2, p_monto_j1, p_monto_j2,
     DATE_ADD(NOW(), INTERVAL p_minutos_expiracion MINUTE));
END //

CREATE PROCEDURE sp_confirmar_tradeo(IN p_id_negociacion INT, IN p_id_jugador INT)
sp_confirmar: BEGIN
  DECLARE v_j1 INT; DECLARE v_j2 INT;
  DECLARE v_item_j1 INT; DECLARE v_item_j2 INT;
  DECLARE v_monto_j1 DECIMAL(12,2); DECLARE v_monto_j2 DECIMAL(12,2);
  DECLARE v_c1 BOOLEAN; DECLARE v_c2 BOOLEAN; DECLARE v_estado VARCHAR(20);
  DECLARE v_deuda_j1 BOOLEAN; DECLARE v_deuda_j2 BOOLEAN;
  DECLARE v_cuenta_j1 INT; DECLARE v_cuenta_j2 INT; DECLARE v_cuenta_sistema INT;
  DECLARE v_saldo_j1 DECIMAL(12,2); DECLARE v_saldo_j2 DECIMAL(12,2);
  DECLARE v_comision_j1 DECIMAL(12,2); DECLARE v_neto_j1 DECIMAL(12,2);
  DECLARE v_comision_j2 DECIMAL(12,2); DECLARE v_neto_j2 DECIMAL(12,2);
  DECLARE v_porcentaje DECIMAL(5,2);
  DECLARE v_id_transaccion INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SELECT id_jugador_1, id_jugador_2, id_item_j1, id_item_j2, monto_j1, monto_j2,
         confirmacion_j1, confirmacion_j2, estado
  INTO v_j1, v_j2, v_item_j1, v_item_j2, v_monto_j1, v_monto_j2, v_c1, v_c2, v_estado
  FROM T_Negociacion_Tradeo WHERE id_negociacion = p_id_negociacion;

  IF v_estado != 'PENDIENTE' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Esta negociacion ya no esta pendiente';
    LEAVE sp_confirmar;
  END IF;

  IF p_id_jugador = v_j1 THEN
    UPDATE T_Negociacion_Tradeo SET confirmacion_j1 = TRUE WHERE id_negociacion = p_id_negociacion;
    SET v_c1 = TRUE;
  ELSEIF p_id_jugador = v_j2 THEN
    UPDATE T_Negociacion_Tradeo SET confirmacion_j2 = TRUE WHERE id_negociacion = p_id_negociacion;
    SET v_c2 = TRUE;
  ELSE
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ese jugador no participa en esta negociacion';
    LEAVE sp_confirmar;
  END IF;

  IF v_c1 = TRUE AND v_c2 = TRUE THEN
    IF v_item_j1 IS NOT NULL THEN
      SELECT tiene_deuda INTO v_deuda_j1 FROM T_Item WHERE id_item = v_item_j1;
      IF v_deuda_j1 = TRUE THEN
        UPDATE T_Negociacion_Tradeo SET estado = 'CANCELADO' WHERE id_negociacion = p_id_negociacion;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El bien del jugador 1 tiene una deuda pendiente, tradeo cancelado';
        LEAVE sp_confirmar;
      END IF;
    END IF;

    IF v_item_j2 IS NOT NULL THEN
      SELECT tiene_deuda INTO v_deuda_j2 FROM T_Item WHERE id_item = v_item_j2;
      IF v_deuda_j2 = TRUE THEN
        UPDATE T_Negociacion_Tradeo SET estado = 'CANCELADO' WHERE id_negociacion = p_id_negociacion;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El bien del jugador 2 tiene una deuda pendiente, tradeo cancelado';
        LEAVE sp_confirmar;
      END IF;
    END IF;

    SELECT id_cuenta, saldo_disponible INTO v_cuenta_j1, v_saldo_j1 FROM T_Cuenta WHERE id_jugador = v_j1;
    SELECT id_cuenta, saldo_disponible INTO v_cuenta_j2, v_saldo_j2 FROM T_Cuenta WHERE id_jugador = v_j2;

    IF v_monto_j1 > 0 AND v_saldo_j1 < v_monto_j1 THEN
      UPDATE T_Negociacion_Tradeo SET estado = 'CANCELADO' WHERE id_negociacion = p_id_negociacion;
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador 1 no tiene saldo suficiente, tradeo cancelado';
      LEAVE sp_confirmar;
    END IF;

    IF v_monto_j2 > 0 AND v_saldo_j2 < v_monto_j2 THEN
      UPDATE T_Negociacion_Tradeo SET estado = 'CANCELADO' WHERE id_negociacion = p_id_negociacion;
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador 2 no tiene saldo suficiente, tradeo cancelado';
      LEAVE sp_confirmar;
    END IF;

    START TRANSACTION;

    IF v_item_j1 IS NOT NULL THEN
      UPDATE T_Item SET id_jugador = v_j2 WHERE id_item = v_item_j1;
    END IF;
    IF v_item_j2 IS NOT NULL THEN
      UPDATE T_Item SET id_jugador = v_j1 WHERE id_item = v_item_j2;
    END IF;

    SELECT c.id_cuenta INTO v_cuenta_sistema
    FROM T_Cuenta c JOIN T_Jugador j ON j.id_servidor = c.id_servidor
    WHERE j.id_jugador = v_j1 AND c.tipo_cuenta = 'SISTEMA';

    SELECT s.porcentaje_comision INTO v_porcentaje
    FROM T_Jugador j JOIN T_Servidor s ON j.id_servidor = s.id_servidor
    WHERE j.id_jugador = v_j1;

    SET v_comision_j1 = ROUND(v_monto_j1 * v_porcentaje / 100, 2);
    SET v_neto_j1 = v_monto_j1 - v_comision_j1;
    SET v_comision_j2 = ROUND(v_monto_j2 * v_porcentaje / 100, 2);
    SET v_neto_j2 = v_monto_j2 - v_comision_j2;

    INSERT INTO T_Transaccion (id_item_afectado, id_negociacion, tipo_transaccion, estado_transaccion, monto)
    VALUES (COALESCE(v_item_j1, v_item_j2), p_id_negociacion, 'TRADEO_P2P', 'COMPLETADA', v_monto_j1 + v_monto_j2);
    SET v_id_transaccion = LAST_INSERT_ID();

    IF v_monto_j1 > 0 THEN
      INSERT INTO T_Detalle_Transaccion (id_transaccion, cuenta_origen, cuenta_destino, tipo_movimiento, monto_detalle, concepto)
      VALUES
        (v_id_transaccion, v_cuenta_j1, v_cuenta_j2, 'DEBITO', v_neto_j1, 'PAGO_TRADEO_J1'),
        (v_id_transaccion, v_cuenta_j1, v_cuenta_j2, 'CREDITO', v_neto_j1, 'COBRO_TRADEO_J1'),
        (v_id_transaccion, v_cuenta_j1, v_cuenta_sistema, 'DEBITO', v_comision_j1, 'COMISION_DRENAJE_SISTEMA'),
        (v_id_transaccion, v_cuenta_j1, v_cuenta_sistema, 'CREDITO', v_comision_j1, 'COMISION_DRENAJE_SISTEMA');
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible - v_monto_j1 WHERE id_cuenta = v_cuenta_j1;
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + v_neto_j1 WHERE id_cuenta = v_cuenta_j2;
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + v_comision_j1 WHERE id_cuenta = v_cuenta_sistema;
    END IF;

    IF v_monto_j2 > 0 THEN
      INSERT INTO T_Detalle_Transaccion (id_transaccion, cuenta_origen, cuenta_destino, tipo_movimiento, monto_detalle, concepto)
      VALUES
        (v_id_transaccion, v_cuenta_j2, v_cuenta_j1, 'DEBITO', v_neto_j2, 'PAGO_TRADEO_J2'),
        (v_id_transaccion, v_cuenta_j2, v_cuenta_j1, 'CREDITO', v_neto_j2, 'COBRO_TRADEO_J2'),
        (v_id_transaccion, v_cuenta_j2, v_cuenta_sistema, 'DEBITO', v_comision_j2, 'COMISION_DRENAJE_SISTEMA'),
        (v_id_transaccion, v_cuenta_j2, v_cuenta_sistema, 'CREDITO', v_comision_j2, 'COMISION_DRENAJE_SISTEMA');
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible - v_monto_j2 WHERE id_cuenta = v_cuenta_j2;
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + v_neto_j2 WHERE id_cuenta = v_cuenta_j1;
      UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + v_comision_j2 WHERE id_cuenta = v_cuenta_sistema;
    END IF;

    UPDATE T_Negociacion_Tradeo SET estado = 'CONFIRMADO' WHERE id_negociacion = p_id_negociacion;

    COMMIT;
  END IF;
END //

CREATE EVENT ev_expirar_negociaciones
ON SCHEDULE EVERY 1 MINUTE
DO
  UPDATE T_Negociacion_Tradeo
  SET estado = 'EXPIRADO'
  WHERE estado = 'PENDIENTE' AND fecha_expiracion < NOW() //

DELIMITER ;

SET GLOBAL event_scheduler = ON;