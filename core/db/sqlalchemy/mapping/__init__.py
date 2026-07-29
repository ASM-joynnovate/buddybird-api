from .shared_kernel import init_shared_kernel_mappers
from .word import init_word_mappers


def init_orm_mappers() -> None:
    init_shared_kernel_mappers()
    init_word_mappers()


__all__ = ["init_orm_mappers"]