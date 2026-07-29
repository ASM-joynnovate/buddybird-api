class MetaDataHelper:
    @staticmethod
    def generate_page_metadata(
            count: int,
            page: int,
            limit: int = 100,
    ) -> dict:
        return {
            "current_page": page,
            "total_page_count": count // limit + 1 if count % limit != 0 else count // limit,
            "is_first": True if page == 1 else False,
            "is_last": True if page * limit >= count else False,
        }
