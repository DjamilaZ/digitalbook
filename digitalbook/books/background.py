from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

# Thread pool dédié aux tâches lourdes de création de livre (2 threads)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="book-worker")


def submit_process_book(
    book_id: int,
    json_structure_file_rel: Optional[str] = None,
    generate_qcm: bool = True,
    nb_questions_per_chapter: Optional[int] = None,
) -> None:
    """Soumet une tâche de traitement de livre au pool dédié.

    Args:
        book_id: ID du livre à traiter
        json_structure_file_rel: chemin RELATIF (depuis MEDIA_ROOT) vers un JSON de structure
        generate_qcm: si True, génère les QCM à la fin
        nb_questions_per_chapter: nombre de questions par chapitre (optionnel)
    """
    from .book_processing import process_book_sync

    _executor.submit(
        process_book_sync,
        book_id,
        json_structure_file_rel,
        generate_qcm,
        nb_questions_per_chapter,
    )


def submit_translate_book(
    book_id: int,
    target_langs: Optional[List[str]] = None,
) -> None:
    """Soumet une tâche de traduction du livre au pool dédié.

    Désactivé temporairement : aucune tâche de traduction n'est soumise.
    """
    # Fonction de traduction désactivée temporairement.
    # from .translation import translate_book_sync
    # _executor.submit(
    #     translate_book_sync,
    #     book_id,
    #     target_langs,
    # )
    return None
