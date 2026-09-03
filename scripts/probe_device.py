"""Script de diagnóstico para sondear conectividad y lectura de marcaciones en reloj ZKTeco.

Lee las variables de entorno ZK_DEVICE_IP, ZK_DEVICE_PORT y ZK_TIMEOUT si están definidas,
o utiliza los valores predeterminados de prueba.
"""

import os

from zk import ZK

ip = os.getenv("ZK_DEVICE_IP", "192.168.0.233")
port = int(os.getenv("ZK_DEVICE_PORT", "4370"))
timeout = int(os.getenv("ZK_TIMEOUT", "60"))

print(f"Iniciando sondeo de dispositivo en {ip}:{port} (timeout={timeout}s)...")

conn = None
zk = ZK(ip, port=port, timeout=timeout, ommit_ping=True)
device_disable = False

try:
    conn = zk.connect()
    conn.disable_device()  # Pausa el reloj durante la lectura para evitar inconsistencias
    device_disable = True

    print("=== Conexión exitosa ===")
    attendance = conn.get_attendance()
    print(f"Total de registros de asistencia: {len(attendance)}")
    if attendance:
        a = attendance[0]
        print("Ejemplo de registro:", vars(a))
        print("Atributos disponibles:", list(a.__dict__.keys()))

except Exception as e:
    print(f"Error durante el sondeo: {e}")

finally:
    if conn and device_disable:
        try:
            conn.enable_device()  # Reactiva el reloj, fundamental no dejarlo deshabilitado
            print("Reloj reactivado correctamente")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo activar el reloj: {e}")
            print("Verifica manualmente que el reloj esté aceptando marcaciones")
    if conn:
        try:
            conn.disconnect()
        except Exception:
            pass  # Se perdió la conexión
