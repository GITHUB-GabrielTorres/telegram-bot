from db import get_connection


def reset_movements() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM movements")
    conn.commit()
    conn.close()
    print("Todas as movimentações foram apagadas.")


if __name__ == "__main__":
    confirm = input("Isso vai apagar TODAS as movimentações. Digite 'sim' pra confirmar: ")
    if confirm.strip().lower() == "sim":
        reset_movements()
    else:
        print("Cancelado.")