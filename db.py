from google.api_core import exceptions
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

db = firestore.Client()

REFERENCE_DEFAULTS = {
    "day": 0.0,
    "pages": 0.0,
    "course_hours": 0.0,
    "podcast_hours": 0.0,
    "bible_verses": 0.0,
    "golden_training": 0.0,
}


def init_db() -> None:
    for key, value in REFERENCE_DEFAULTS.items():
        doc_ref = db.collection("reference_values").document(key)
        try:
            doc_ref.create({"value": value})
        except exceptions.AlreadyExists:
            pass


# ---------- users ----------

def get_user_name(user_id: int) -> str | None:
    doc = db.collection("users").document(str(user_id)).get()
    return doc.to_dict()["name"] if doc.exists else None


def register_user(user_id: int, name: str) -> None:
    db.collection("users").document(str(user_id)).set({"name": name})


def get_users() -> dict[int, str]:
    return {
        int(doc.id): doc.to_dict()["name"]
        for doc in db.collection("users").stream()
    }


# ---------- reference_values ----------

def get_reference_value(key: str) -> float:
    doc = db.collection("reference_values").document(key).get()
    if not doc.exists:
        raise ValueError(f"Valor de referência '{key}' não encontrado.")
    return doc.to_dict()["value"]


def set_reference_value(key: str, value: float) -> None:
    db.collection("reference_values").document(key).update({"value": value})


def list_reference_values() -> list[tuple[str, float]]:
    values = {
        doc.id: doc.to_dict()["value"]
        for doc in db.collection("reference_values").stream()
    }
    return [(key, values[key]) for key in REFERENCE_DEFAULTS if key in values]


# ---------- movements ----------

@firestore.transactional
def _create_movement_in_transaction(transaction, user_id, amount, description, movement_date):
    counter_ref = db.collection("counters").document("movements")
    snapshot = counter_ref.get(transaction=transaction)
    current = snapshot.get("value") if snapshot.exists else 0
    movement_id = current + 1

    transaction.set(counter_ref, {"value": movement_id})
    transaction.set(
        db.collection("movements").document(str(movement_id)),
        {
            "id": movement_id,
            "user_id": user_id,
            "amount": amount,
            "description": description,
            "movement_date": movement_date,
            "movement_day": movement_date.date().isoformat(),
            "created_at": firestore.SERVER_TIMESTAMP,
        },
    )
    return movement_id


def create_movement(user_id: int, amount: float, description: str, movement_date) -> int:
    transaction = db.transaction()
    return _create_movement_in_transaction(
        transaction, user_id, amount, description, movement_date
    )


def get_movement(movement_id: int) -> dict | None:
    doc = db.collection("movements").document(str(movement_id)).get()
    return doc.to_dict() if doc.exists else None


def delete_movement(movement_id: int) -> None:
    db.collection("movements").document(str(movement_id)).delete()


def update_movement_description(movement_id: int, description: str) -> None:
    db.collection("movements").document(str(movement_id)).update(
        {"description": description}
    )


def list_movements(limit: int, exclude_ganhei: bool = False) -> list[dict]:
    query = db.collection("movements").order_by(
        "id", direction=firestore.Query.DESCENDING
    )
    if not exclude_ganhei:
        query = query.limit(limit)

    result = []
    for doc in query.stream():
        data = doc.to_dict()
        if exclude_ganhei and data["description"] == "ganhei":
            continue
        result.append(data)
        if len(result) >= limit:
            break
    return result


def find_ganhei_id(user_id: int, day: str) -> int | None:
    query = (
        db.collection("movements")
        .where(filter=FieldFilter("user_id", "==", user_id))
        .where(filter=FieldFilter("description", "==", "ganhei"))
        .where(filter=FieldFilter("movement_day", "==", day))
        .limit(1)
    )
    docs = list(query.stream())
    return int(docs[0].id) if docs else None


def get_ganhei_days(user_id: int) -> set[str]:
    query = (
        db.collection("movements")
        .where(filter=FieldFilter("user_id", "==", user_id))
        .where(filter=FieldFilter("description", "==", "ganhei"))
    )
    return {doc.to_dict()["movement_day"] for doc in query.stream()}


# ---------- saldos ----------

def get_user_balance(user_id: int) -> float:
    query = db.collection("movements").where(filter=FieldFilter("user_id", "==", user_id))
    results = query.sum("amount", alias="total").get()
    return float(results[0][0].value or 0)


def get_balances() -> list[tuple[str, float]]:
    return [
        (name, get_user_balance(user_id))
        for user_id, name in get_users().items()
    ]