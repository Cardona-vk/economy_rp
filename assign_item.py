import database
import mysql.connector

def assign_test_item():
    conn = database.get_db_connection()
    if not conn:
        print("Error de conexión")
        return
    
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO T_Item (id_jugador, nombre, precio, tiene_deuda) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (23, 'Coche de Lujo', 50000.00, 0))
        conn.commit()
        print("Item asignado exitosamente al jugador 23")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    assign_test_item()
