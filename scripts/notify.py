def notify(subject: str, body: str, meta: dict | None = None) -> None:
    print(f"[NOTIFY] {subject}")
    print(body)
    if meta:
        print(f"[NOTIFY meta] {meta}")
