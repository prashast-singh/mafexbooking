from fastapi import HTTPException, status


def parse_comma_separated_ints(raw: str | None, *, param_name: str = "parameter") -> list[int] | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        ids = [int(p.strip()) for p in str(raw).split(",") if p.strip()]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name} (comma-separated integers)",
        ) from e
    return ids or None
