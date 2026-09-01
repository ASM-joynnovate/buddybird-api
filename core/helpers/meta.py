def generate_page_metadata(*, count: int, page: int, limit: int = 100) -> dict:
    return {
        "current_page": page,
        "total_page_count": count // limit + 1 if count % limit != 0 else count // limit,
        "is_first": page == 1,
        "is_last": page * limit >= count,
    }
