from django.db import transaction


def delete_file_on_commit(file) -> None:
    """
    Удаляет файл из хранилища после коммита текущей транзакции: при откате запись,
    которая на него ссылается, вернётся, и файл ещё нужен. Принимает FieldFile или None.
    """
    if not file:
        return
    storage, name = file.storage, file.name
    transaction.on_commit(lambda: storage.delete(name))
