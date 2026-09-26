import database
import time
import uuid

def inicializar_servidor():
    """Asegura que exista al menos un servidor en la base de datos."""
    print("\n[0] Inicializando servidor...")
    conn = database.get_db_connection()
    if not conn:
        print("Error: No se pudo conectar a la base de datos para inicializar.")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM T_Servidor")
        if cursor.fetchone()[0] == 0:
            print("T_Servidor está vacía. Insertando servidor inicial...")
            sql = """
            INSERT INTO T_Servidor
            (nombre, porcentaje_comision, limite_bienes_por_jugador, tiempo_enfriamiento_min)
            VALUES ('Servidor Principal', 5.00, 10, 30)
            """
            cursor.execute(sql)
            conn.commit()
            print("Servidor inicial insertado exitosamente.")
        else:
            print("Servidor ya configurado.")
        return True
    except Exception as e:
        print(f"Error al inicializar servidor: {e}")
        return False
    finally:
        conn.close()

def limpiar_datos_prueba():
    """Limpia datos que permitan ser borrados. Ignora tablas inmutables."""
    print("\n[0.1] Limpiando datos de prueba (omitiendo inmutables)...")
    conn = database.get_db_connection()
    if not conn: return

    # Eliminamos solo lo que no es inmutable según el brief (T_Transaccion y T_Detalle_Transaccion son inmutables)
    tablas = [
        "T_Negociacion_Tradeo",
        "T_Item",
        "T_Jornada_Laboral",
        "T_Cuenta",
        "T_Jugador"
    ]

    try:
        cursor = conn.cursor()
        for tabla in tablas:
            try:
                cursor.execute(f"DELETE FROM {tabla}")
            except Exception as e:
                print(f"Aviso: No se pudo limpiar {tabla}: {e}")
        conn.commit()
        print("Limpieza de datos completada.")
    except Exception as e:
        print(f"Error crítico en limpieza: {e}")
    finally:
        conn.close()

def setup_sp_data(id_jugador):
    """Crea datos necesarios para probar los SPs (Cuenta Sistema, Empleo, Items)."""
    print("\n[Setup] Creando entidades para pruebas de SPs...")
    conn = database.get_db_connection()
    if not conn: return None, None, None

    try:
        cursor = conn.cursor()
        # 1. Obtener id_servidor
        cursor.execute("SELECT id_servidor FROM T_Servidor LIMIT 1")
        servidor_row = cursor.fetchone()
        if not servidor_row:
            print("Error: No se encontró servidor.")
            return None, None, None
        id_servidor = servidor_row[0]

        # 2. Crear Cuenta de SISTEMA si no existe
        cursor.execute("SELECT COUNT(*) FROM T_Cuenta WHERE tipo_cuenta = 'SISTEMA' AND id_servidor = %s", (id_servidor,))
        if cursor.fetchone()[0] == 0:
            print("Creando cuenta de SISTEMA...")
            cursor.execute("""
                INSERT INTO T_Cuenta (id_jugador, id_servidor, tipo_cuenta, saldo_inicial, saldo_disponible)
                VALUES (NULL, %s, 'SISTEMA', 100000.00, 100000.00)
            """, (id_servidor,))

        # 3. Crear Empleo (T_Empleo) - Manejamos duplicados
        try:
            cursor.execute("INSERT INTO T_Empleo (id_servidor, nombre_empleo, tarifa_base) VALUES (%s, 'Obrero', 100.00)", (id_servidor,))
            id_empleo = cursor.lastrowid
        except Exception:
            cursor.execute("SELECT id_empleo FROM T_Empleo WHERE nombre_empleo = 'Obrero' AND id_servidor = %s LIMIT 1", (id_servidor,))
            id_empleo = cursor.fetchone()[0]

        # 4. Fondos para Jugador 1
        cursor.execute("UPDATE T_Cuenta SET saldo_disponible = 1000.00 WHERE id_jugador = %s AND tipo_cuenta = 'PERSONAL'", (id_jugador,))

        # 5. Crear Items para tradeo (T_Item)
        cursor.execute("INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (%s, 'Item J1', 500.00, FALSE)", (id_jugador,))
        id_item_j1 = cursor.lastrowid

        # 6. Segundo Jugador para tradeos (T_Jugador) - Nombre y correo dinámicos
        import bcrypt
        u2_name = f"test_user2_{int(time.time())}"
        u2_email = f"test2_{int(time.time())}@mail.com"
        hashed_pw = bcrypt.hashpw("pass2".encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO T_Jugador (id_servidor, nombre_usuario, correo, contrasena_hash) VALUES (%s, %s, %s, %s)", (id_servidor, u2_name, u2_email, hashed_pw))
        id_jugador2 = cursor.lastrowid

        # 7. Cuenta para el jugador 2 (T_Cuenta)
        cursor.execute("INSERT INTO T_Cuenta (id_jugador, id_servidor, tipo_cuenta, saldo_inicial, saldo_disponible) VALUES (%s, %s, 'PERSONAL', 1000.00, 1000.00)", (id_jugador2, id_servidor))

        # 8. Item para el jugador 2 (T_Item)
        cursor.execute("INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (%s, 'Item J2', 600.00, FALSE)", (id_jugador2,))
        id_item_j2 = cursor.lastrowid

        conn.commit()
        return id_empleo, id_jugador2, (id_item_j1, id_item_j2)
    except Exception as e:
        print(f"Error en setup de SPs: {e}")
        return None, None, None
    finally:
        conn.close()

def test_dal():
    print("--- Iniciando Pruebas Completas de la Capa de Acceso a Datos ---")

    if not inicializar_servidor():
        print("Abortando pruebas: Error en la inicialización del servidor.")
        return

    limpiar_datos_prueba()

    # 1. Prueba de Registro con nombre dinámico
    u_name = f"test_user_{int(time.time())}"
    u_email = f"test_{int(time.time())}@mail.com"
    print(f"\n[1] Probando registrar_jugador ({u_name})...")
    success, msg = database.registrar_jugador(u_name, u_email, "password123")
    print(f"Resultado: {'✅' if success else '❌'} - {msg}")

    # 2. Prueba de Login
    print("\n[2] Probando iniciar_sesion...")
    success, result = database.iniciar_sesion(u_name, "password123")
    if success:
        user_id = result
        print(f"Resultado: ✅ - Login exitoso. ID Jugador: {user_id}")
    else:
        print(f"Resultado: ❌ - {result}")
        user_id = None

    if user_id:
        # 3. Prueba de Saldo
        print("\n[3] Probando consultar_saldo...")
        saldo, msg = database.consultar_saldo(user_id)
        print(f"Resultado: {'✅' if saldo is not None else '❌'} - {msg} (Saldo: {saldo})")

        # --- PRUEBAS DE PROCEDIMIENTOS ALMACENADOS ---
        id_empleo, id_user2, items = setup_sp_data(user_id)

        if id_empleo:
            # 4. Prueba sp_pagar_jornada
            print("\n[4] Probando sp_pagar_jornada...")
            success, msg = database.pagar_jornada(user_id, id_empleo, 8)
            print(f"Resultado: {'✅' if success else '❌'} - {msg}")

            # Verificar que el saldo aumentó
            saldo_nuevo, _ = database.consultar_saldo(user_id)
            print(f"Nuevo saldo tras jornada: {saldo_nuevo}")

            # 5. Prueba sp_abrir_negociacion
            print("\n[5] Probando sp_abrir_negociacion...")
            success, msg = database.abrir_negociacion(user_id, id_user2, items[0], items[1], 100.0, 200.0, 10)
            print(f"Resultado: {'✅' if success else '❌'} - {msg}")

            if success:
                # Necesitamos el id de la negociación para confirmar
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id_negociacion FROM T_Negociacion_Tradeo ORDER BY id_negociacion DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    id_neg = row[0]
                    conn.close()

                    # 6. Prueba sp_confirmar_tradeo (Ambos deben confirmar)
                    print("\n[6] Probando sp_confirmar_tradeo...")
                    # Confirmación J1
                    s1, m1 = database.confirmar_tradeo(id_neg, user_id)
                    print(f"Confirmación J1: {'✅' if s1 else '❌'} - {m1}")

                    # Confirmación J2
                    s2, m2 = database.confirmar_tradeo(id_neg, id_user2)
                    print(f"Confirmación J2: {'✅' if s2 else '❌'} - {m2}")

                    # Verificar cambio de propiedad del item
                    saldo_final, _ = database.consultar_saldo(user_id)
                    print(f"Saldo final J1: {saldo_final}")
                else:
                    print("Error: No se encontró la negociación creada.")
                    conn.close()

    print("\n--- Fin de Pruebas ---")

if __name__ == "__main__":
    test_dal()
