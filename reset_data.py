import sys

from dotenv import load_dotenv

load_dotenv()

from db import db

COLLECTIONS_TO_WIPE = ["movements", "counters", "test"]

if "--users" in sys.argv:
    COLLECTIONS_TO_WIPE.append("users")


def delete_collection(name: str, batch_size: int = 200) -> int:
    collection = db.collection(name)
    deleted = 0

    while True:
        docs = list(collection.limit(batch_size).stream())
        if not docs:
            break

        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(docs)

    return deleted


if __name__ == "__main__":
    print("Isso vai apagar TODOS os documentos de:", ", ".join(COLLECTIONS_TO_WIPE))
    confirm = input("Digite 'sim' pra confirmar: ")

    if confirm.strip().lower() == "sim":
        for name in COLLECTIONS_TO_WIPE:
            count = delete_collection(name)
            print(f"{name}: {count} documento(s) apagado(s)")
    else:
        print("Cancelado.")