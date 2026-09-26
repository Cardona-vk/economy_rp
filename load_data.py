import database
from mysql.connector import Error

def load_test_data():
    print("--- Iniciando Carga de Datos de Prueba ---")
    conn = database.get_db_connection()
    if not conn:
        print("Error: No se pudo conectar a la base de datos.")
        return

    try:
        cursor = conn.cursor()

        # 1. Definir jugadores y sus saldos
        jugadores = [17, 19]
        saldo_inicial = 50000.00

        for jid in jugadores:
            print(f"Asignando saldo a Jugador ID {jid}...")
            # Asegurar que tenga cuenta PERSONAL
            cursor.execute("""
                INSERT INTO T_Cuenta (id_jugador, id_servidor, tipo_cuenta, saldo_inicial, saldo_disponible)
                SELECT id_jugador, id_servidor, 'PERSONAL', %s, %s
                FROM T_Jugador WHERE id_jugador = %s
                ON DUPLICATE KEY UPDATE saldo_disponible = %s
            """, (saldo_inicial, saldo_inicial, jid, saldo_inicial))

        # 2. Definir Items
        # Jugador 17: 1x AK-47, 5x Kit de Reparación
        items_j17 = [
            ('AK-47', 2500.00, 1),
            ('Kit de Reparación', 150.00, 5)
        ]

        # Jugador 19: 2x AK-47, 1x Medicamentos
        items_j19 = [
            ('AK-47', 2500.00, 2),
            ('Medicamentos', 100.00, 1)
        ]

        # Inyectar items para Jugador 17
        for nombre, precio, cant in items_j17:
            for _ in range(cant):
                cursor.execute("INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (%s, %s, %s, FALSE)", (17, nombre, precio))

        # Inyectar items para Jugador 19
        for nombre, precio, cant in items_j19:
            for _ in range(cant):
                cursor.execute("INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (%s, %s, %s, FALSE)", (19, nombre, precio))

        conn.commit()
        print("\nDatos inyectados exitosamente.")
        print("- Saldo: $50,000 asignados a ID 17 y 19.")
        print("- Inventario J17: AK-47 x1, Kit Rep. x5.")
        print("- Inventario J19: AK-47 x2, Medicamentos x1.")

    except Error as e:
        print(f"Error durante la carga de datos: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    load_test_data()
