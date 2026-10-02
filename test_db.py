from dotenv import load_dotenv
load_dotenv()

from datetime import datetime

import db

db.register_user(1, "Teste")
movement_id = db.create_movement(1, 8.0, "teste", datetime.now())

print("id criado:", movement_id)
print("saldos:", db.get_balances())