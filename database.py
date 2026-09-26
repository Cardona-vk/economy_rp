import mysql.connector
from mysql.connector import Error
import bcrypt
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Establece una conexión con la base de datos MySQL."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'economy_rp')
        )
        return connection
    except Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def registrar_jugador(usuario, correo, password):
    """Registra un nuevo jugador cifrando la contraseña con bcrypt y crea su cuenta inicial."""
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt)

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a la base de datos"

    try:
        cursor = conn.cursor()
        # 1. Obtener id_servidor
        cursor.execute("SELECT id_servidor FROM T_Servidor LIMIT 1")
        servidor = cursor.fetchone()
        if not servidor:
            return False, "No hay servidores configurados en T_Servidor"
        id_servidor = servidor[0]

        # 2. Insertar Jugador
        query_jugador = "INSERT INTO T_Jugador (id_servidor, nombre_usuario, correo, contrasena_hash) VALUES (%s, %s, %s, %s)"
        cursor.execute(query_jugador, (id_servidor, usuario, correo, hashed_pw))
        id_jugador = cursor.lastrowid

        # 3. Crear Cuenta Personal Inicial
        query_cuenta = "INSERT INTO T_Cuenta (id_jugador, id_servidor, tipo_cuenta, saldo_inicial, saldo_disponible) VALUES (%s, %s, 'PERSONAL', 0.00, 0.00)"
        cursor.execute(query_cuenta, (id_jugador, id_servidor))

        conn.commit()
        return True, "Jugador registrado y cuenta creada exitosamente"
    except Error as e:
        conn.rollback()
        return False, f"Error al registrar jugador: {e}"
    finally:
        if conn: conn.close()

def iniciar_sesion(usuario, password):
    """Verifica las credenciales del jugador."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión a la base de datos"

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id_jugador, contrasena_hash FROM T_Jugador WHERE nombre_usuario = %s"
        cursor.execute(query, (usuario,))
        result = cursor.fetchone()

        if result and bcrypt.checkpw(password.encode('utf-8'), result['contrasena_hash'].encode('utf-8')):
            return True, {'id_usuario': result['id_jugador'], 'usuario': usuario}
        else:
            return False, "Usuario o contraseña incorrectos"
    except Error as e:
        return False, f"Error durante el login: {e}"
    finally:
        if conn: conn.close()

def pagar_jornada(id_jugador, id_empleo, horas):
    """Llama al SP sp_pagar_jornada."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"

    try:
        cursor = conn.cursor()
        cursor.callproc('sp_pagar_jornada', (id_jugador, id_empleo, horas))
        conn.commit()
        return True, "Pago de jornada procesado exitosamente"
    except Error as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def _ensure_scalar(val):
    """Helper para asegurar que el valor sea un entero simple o None, evitando diccionarios."""
    if val is None:
        return None
    if isinstance(val, dict):
        return val.get('id_usuario') or val.get('id_jugador') or val.get('id_item')
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def abrir_negociacion(id_j1, id_j2, item_j1, item_j2, monto_j1, monto_j2, exp):
    """Llama al SP sp_abrir_negociacion."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"

    try:
        cursor = conn.cursor()

        # Limpieza de datos según requerimiento
        # 1. Asegurar que remitente sea entero
        try:
            id_j1_clean = _ensure_scalar(id_j1)
            if id_j1_clean is None:
                return False, "ID de remitente inválido"
        except Exception:
            return False, "Error procesando ID de remitente"

        # 2. Manejo de valores vacíos para MySQL
        # monto_j1: si es None o vacio -> 0.0
        try:
            monto_j1_clean = float(monto_j1) if monto_j1 not in (None, '') else 0.0
        except (TypeError, ValueError):
            monto_j1_clean = 0.0

        # item_j1: si es None o vacio -> NULL
        item_j1_clean = _ensure_scalar(item_j1) if item_j1 not in (None, '') else None

        # Otros parámetros
        id_j2_clean = _ensure_scalar(id_j2)
        item_j2_clean = _ensure_scalar(item_j2) if item_j2 not in (None, '') else None
        monto_j2_clean = float(monto_j2) if monto_j2 not in (None, '') else 0.0
        exp_clean = _ensure_scalar(exp) or 10

        params = (
            id_j1_clean,
            id_j2_clean,
            item_j1_clean,
            item_j2_clean,
            monto_j1_clean,
            monto_j2_clean,
            exp_clean
        )
        cursor.callproc('sp_abrir_negociacion', params)
        conn.commit()
        return True, "Negociación abierta exitosamente"
    except Error as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def confirmar_tradeo(id_negociacion, id_jugador):
    """Llama al SP sp_confirmar_tradeo."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"

    try:
        cursor = conn.cursor()
        cursor.callproc('sp_confirmar_tradeo', (_ensure_scalar(id_negociacion), _ensure_scalar(id_jugador)))
        conn.commit()
        return True, "Confirmación de tradeo procesada"
    except Error as e:
        return False, str(e)
    finally:
        if conn: conn.close()

def consultar_saldo(id_jugador):
    """Consulta el saldo actual del jugador en T_Cuenta."""
    conn = get_db_connection()
    if not conn: return None, "Error de conexión"

    try:
        cursor = conn.cursor()
        query = "SELECT saldo_disponible FROM T_Cuenta WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'"
        cursor.execute(query, (id_jugador,))
        result = cursor.fetchone()
        return (result[0], "Saldo recuperado") if result else (None, "Cuenta no encontrada para este jugador")
    except Error as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def consultar_inventario(id_jugador):
    """Consulta los items del jugador y si tienen deuda."""
    conn = get_db_connection()
    if not conn: return None, "Error de conexión"

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM T_Item WHERE id_jugador = %s"
        cursor.execute(query, (id_jugador,))
        return cursor.fetchall(), "Inventario recuperado"
    except Error as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def obtener_detalle_trade(id_trade):
    """Devuelve toda la información del registro de T_Negociacion_Tradeo."""
    conn = get_db_connection()
    if not conn: return None, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM T_Negociacion_Tradeo WHERE id_negociacion = %s"
        cursor.execute(query, (id_trade,))
        return cursor.fetchone(), "Detalle recuperado"
    except Error as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def actualizar_oferta_jugador(id_trade, id_jugador, monto, id_item):
    """Actualiza la oferta de un jugador y resetea confirmaciones."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        # Determinamos si el jugador es el J1 o J2
        cursor.execute("SELECT id_jugador_1 FROM T_Negociacion_Tradeo WHERE id_negociacion = %s", (id_trade,))
        res = cursor.fetchone()
        if not res: return False, "Tradeo no encontrado"

        is_j1 = (res[0] == id_jugador)
        if is_j1:
            sql = "UPDATE T_Negociacion_Tradeo SET monto_j1 = %s, id_item_j1 = %s, confirmacion_j1 = 0, confirmacion_j2 = 0, estado = 'EN_PROCESO' WHERE id_negociacion = %s"
        else:
            sql = "UPDATE T_Negociacion_Tradeo SET monto_j2 = %s, id_item_j2 = %s, confirmacion_j1 = 0, confirmacion_j2 = 0, estado = 'EN_PROCESO' WHERE id_negociacion = %s"

        cursor.execute(sql, (monto, id_item, id_trade))
        conn.commit()
        return True, "Oferta actualizada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def confirmar_oferta_jugador(id_trade, id_jugador):
    """Marca al jugador como confirmado y finaliza si ambos lo están."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        # 1. Identificar jugador y marcar confirmación
        cursor.execute("SELECT id_jugador_1 FROM T_Negociacion_Tradeo WHERE id_negociacion = %s", (id_trade,))
        res = cursor.fetchone()
        if not res: return False, "Tradeo no encontrado"

        col_conf = 'confirmacion_j1' if res['id_jugador_1'] == id_jugador else 'confirmacion_j2'
        cursor.execute(f"UPDATE T_Negociacion_Tradeo SET {col_conf} = 1 WHERE id_negociacion = %s", (id_trade,))

        # 2. Verificar si ambos confirmaron
        cursor.execute("SELECT confirmacion_j1, confirmacion_j2 FROM T_Negociacion_Tradeo WHERE id_negociacion = %s", (id_trade,))
        status = cursor.fetchone()

        if status and status['confirmacion_j1'] == 1 and status['confirmacion_j2'] == 1:
            # Ejecutar transferencia (reutilizamos finalizar_tradeo)
            conn.commit() # Asegurar que la confirmación se guarde antes de llamar a finalizar
            conn.close()
            return finalizar_tradeo(id_trade)

        conn.commit()
        return True, "Oferta confirmada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn and conn.is_connected(): conn.close()

def update_trade_offer(id_negociacion, is_player_1, item_id, monto):
    """Actualiza la oferta de un jugador específico y resetea confirmaciones."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        if is_player_1:
            sql = "UPDATE T_Negociacion_Tradeo SET id_item_j1 = %s, monto_j1 = %s, confirmacion_j1 = FALSE, confirmacion_j2 = FALSE, estado = 'EN_PROCESO' WHERE id_negociacion = %s"
            params = (item_id, monto, id_negociacion)
        else:
            sql = "UPDATE T_Negociacion_Tradeo SET id_item_j2 = %s, monto_j2 = %s, confirmacion_j1 = FALSE, confirmacion_j2 = FALSE, estado = 'EN_PROCESO' WHERE id_negociacion = %s"
            params = (item_id, monto, id_negociacion)

        cursor.execute(sql, params)
        conn.commit()
        return True, "Oferta actualizada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def lock_trade_player(id_negociacion, is_player_1):
    """Bloquea la oferta de un jugador y verifica si ambos están listos."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        if is_player_1:
            cursor.execute("UPDATE T_Negociacion_Tradeo SET confirmacion_j1 = TRUE WHERE id_negociacion = %s", (id_negociacion,))
        else:
            cursor.execute("UPDATE T_Negociacion_Tradeo SET confirmacion_j2 = TRUE WHERE id_negociacion = %s", (id_negociacion,))

        conn.commit()

        cursor.execute("SELECT confirmacion_j1, confirmacion_j2 FROM T_Negociacion_Tradeo WHERE id_negociacion = %s", (id_negociacion,))
        res = cursor.fetchone()
        if res and res['confirmacion_j1'] and res['confirmacion_j2']:
            cursor.execute("UPDATE T_Negociacion_Tradeo SET estado = 'ESPERANDO_CONFIRMACION_FINAL' WHERE id_negociacion = %s", (id_negociacion,))
            conn.commit()

        return True, "Oferta bloqueada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def consultar_mesa_activa(id_jugador):
    """Obtiene la información de la mesa de comercio activa para el jugador."""
    conn = get_db_connection()
    if not conn: return None, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT n.*,
               i1.nombre as nombre_item_j1,
               i2.nombre as nombre_item_j2,
               (n.id_jugador_1 = %s) as es_jugador_1
        FROM T_Negociacion_Tradeo n
        LEFT JOIN T_Item i1 ON n.id_item_j1 = i1.id_item
        LEFT JOIN T_Item i2 ON n.id_item_j2 = i2.id_item
        WHERE (n.id_jugador_1 = %s OR n.id_jugador_2 = %s)
        AND n.estado IN ('PENDIENTE', 'EN_PROCESO', 'ESPERANDO_CONFIRMACION_FINAL')
        LIMIT 1
        """
        cursor.execute(query, (id_jugador, id_jugador, id_jugador))
        return cursor.fetchone(), "Mesa recuperada"
    except Error as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def limpieza_forzada_trades():
    """Borra todos los registros de negociaciones activas para resetear el sistema."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        sql = "DELETE FROM T_Negociacion_Tradeo WHERE estado IN ('PENDIENTE', 'EN_PROCESO', 'ACEPTADO', 'ABIERTO')"
        cursor.execute(sql)
        conn.commit()
        return True, f"Se han eliminado {cursor.rowcount} registros bloqueantes."
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def consultar_ofertas_pendientes(id_jugador):
    """Busca invitaciones entrantes donde el usuario es el destinatario."""
    conn = get_db_connection()
    if not conn: return None, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT n.*, j1.nombre_usuario as emisor, i1.nombre as item_ofrecido
        FROM T_Negociacion_Tradeo n
        JOIN T_Jugador j1 ON n.id_jugador_1 = j1.id_jugador
        LEFT JOIN T_Item i1 ON n.id_item_j1 = i1.id_item
        WHERE n.id_jugador_2 = %s AND n.estado = 'PENDIENTE'
        """
        cursor.execute(query, (id_jugador,))
        return cursor.fetchall(), "Ofertas recuperadas"
    except Error as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def aceptar_invitacion_trade(id_negociacion):
    """Cambia el estado a EN_PROCESO al aceptar invitación."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE T_Negociacion_Tradeo SET estado = 'EN_PROCESO' WHERE id_negociacion = %s", (id_negociacion,))
        conn.commit()
        return True, "Invitación aceptada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def actualizar_oferta_receptor(id_negociacion, id_item, monto):
    """Actualiza la oferta del jugador 2 y resetea confirmaciones."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        sql = """
        UPDATE T_Negociacion_Tradeo
        SET id_item_j2 = %s, monto_j2 = %s, confirmacion_j1 = FALSE, confirmacion_j2 = FALSE, estado = 'EN_PROCESO'
        WHERE id_negociacion = %s
        """
        cursor.execute(sql, (id_item, monto, id_negociacion))
        conn.commit()
        return True, "Oferta actualizada"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def finalizar_tradeo(id_negociacion):
    """Ejecuta la transferencia de items y dinero, y cierra el tradeo."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM T_Negociacion_Tradeo WHERE id_negociacion = %s", (id_negociacion,))
        n = cursor.fetchone()
        if not n: return False, "Negociación no encontrada"

        # Transacción atómica
        if n['id_item_j1']:
            cursor.execute("UPDATE T_Item SET id_jugador = %s WHERE id_item = %s", (n['id_jugador_2'], n['id_item_j1']))
        if n['id_item_j2']:
            cursor.execute("UPDATE T_Item SET id_jugador = %s WHERE id_item = %s", (n['id_jugador_1'], n['id_item_j2']))
        if n['monto_j1'] > 0:
            cursor.execute("UPDATE T_Cuenta SET saldo_disponible = saldo_disponible - %s WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'", (n['monto_j1'], n['id_jugador_1']))
            cursor.execute("UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + %s WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'", (n['monto_j1'], n['id_jugador_2']))
        if n['monto_j2'] > 0:
            cursor.execute("UPDATE T_Cuenta SET saldo_disponible = saldo_disponible - %s WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'", (n['monto_j2'], n['id_jugador_2']))
            cursor.execute("UPDATE T_Cuenta SET saldo_disponible = saldo_disponible + %s WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'", (n['monto_j2'], n['id_jugador_1']))

        cursor.execute("UPDATE T_Negociacion_Tradeo SET estado = 'COMPLETADO' WHERE id_negociacion = %s", (id_negociacion,))
        conn.commit()
        return True, "Comercio completado con éxito"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def cancelar_tradeo(id_negociacion):
    """Cancela una negociación activa."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión"
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE T_Negociacion_Tradeo SET estado = 'CANCELADO' WHERE id_negociacion = %s", (id_negociacion,))
        conn.commit()
        return True, "Tradeo cancelado"
    except Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def obtener_invitaciones_pendientes(id_jugador):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        # Extraer entero si id_jugador llega como diccionario
        if isinstance(id_jugador, dict):
            id_jugador = id_jugador.get('id_usuario') or id_jugador.get('id_jugador')
            
        query = "SELECT * FROM T_Negociacion_Tradeo WHERE id_jugador_2 = %s AND estado = 'PENDIENTE'"
        cursor.execute(query, (int(id_jugador),))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener invitaciones: {e}")
        return []
    finally:
        conn.close()

def aceptar_invitacion_trade(id_trade, id_jugador):
    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión con la base de datos"
    try:
        cursor = conn.cursor()
        if isinstance(id_jugador, dict):
            id_jugador = id_jugador.get('id_usuario') or id_jugador.get('id_jugador')

        # Cambiamos 'EN_PROCESO' por 'ACEPTADO'
        query = "UPDATE T_Negociacion_Tradeo SET estado = 'ACEPTADO' WHERE id_negociacion = %s AND id_jugador_2 = %s"
        cursor.execute(query, (int(id_trade), int(id_jugador)))
        conn.commit()
        return True, "Invitación aceptada"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()