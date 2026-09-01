from dependency_injector import containers, providers

from app.word.application.use_cases.command.create_word import CreateWordUseCase
from app.word.application.use_cases.query.get_word import GetWordUseCase
from app.word.infra.persistence import WordSQLAlchemyRepo


class WordContainer(containers.DeclarativeContainer):
    object_storage_client = providers.Dependency()
    file_analyzer = providers.Dependency()

    word_repo = providers.Singleton(WordSQLAlchemyRepo)

    get_word_query = providers.Factory(
        GetWordUseCase,
        word_repo=word_repo,
    )
    create_word_command = providers.Factory(
        CreateWordUseCase,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
        word_repo=word_repo,
    )
