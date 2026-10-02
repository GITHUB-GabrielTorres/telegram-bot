from dotenv import load_dotenv
load_dotenv()

from google.cloud import firestore

db = firestore.Client()

doc_ref = db.collection("test").document("ping")
doc_ref.set({"mensagem": "funcionando"})

print(doc_ref.get().to_dict())