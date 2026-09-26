-- FIX CRITICAL: Actualizar restricciones de estado para el sistema de tradeo en tiempo real.
-- Permite los estados necesarios para el flujo: PENDIENTE -> EN_PROCESO -> ESPERANDO_CONFIRMACION_FINAL -> CONFIRMADO/CANCELADO/EXPIRADO.

-- Para MySQL 8.0.16+ (donde se soportan CHECK constraints)
ALTER TABLE T_Negociacion_Tradeo
DROP CHECK IF EXISTS T_Negociacion_Tradeo_chk_1; -- Nombre genérico, puede variar según la DB

ALTER TABLE T_Negociacion_Tradeo
ADD CONSTRAINT CHK_Estado_Tradeo
CHECK (estado IN ('PENDIENTE', 'EN_PROCESO', 'ESPERANDO_CONFIRMACION_FINAL', 'CONFIRMADO', 'CANCELADO', 'EXPIRADO'));

-- Nota: Si la base de datos es una versión antigua de MySQL que ignora CHECK,
-- la validación se maneja estrictamente en la capa de aplicación (app.py).
