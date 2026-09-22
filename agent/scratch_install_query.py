import os
from dotenv import load_dotenv
load_dotenv()
import pyTigerGraph as tg

print("Connecting to TigerGraph...")
conn = tg.TigerGraphConnection(
    host=os.environ.get("TG_HOST", ""),
    graphname=os.environ.get("TG_GRAPH", "FraudGraph"),
    gsqlSecret=os.environ.get("TG_SECRET", ""),
    tgCloud=True
)
conn.getToken(conn.createSecret())
print("Connected. Installing query 'get_transaction_device'...")
try:
    res = conn.gsql("USE GRAPH FraudGraph\nINSTALL QUERY get_transaction_device")
    print("Installation complete:")
    print(res)
except Exception as e:
    print(f"Error during installation: {e}")
