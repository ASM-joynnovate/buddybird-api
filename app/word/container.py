from dependency_injector import containers, providers

from app.word.application.use_cases.command.create_word import CreateWordUseCase
from app.word.application.use_cases.query.word import WordQueryUseCase
from app.word.infra.presistance import WordSQLAlchemyRepo


class WordContainer(containers.DeclarativeContainer):
    object_storage_client = providers.Dependency()
    file_analyzer = providers.Dependency()

    word_repo = providers.Singleton(WordSQLAlchemyRepo)

    word_query = providers.Factory(
        WordQueryUseCase,
        word_repo=word_repo,
    )
    create_word_command = providers.Factory(
        CreateWordUseCase,
        word_repo=word_repo,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
    )
