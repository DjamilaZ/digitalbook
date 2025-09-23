import logging
from typing import List, Dict, Optional
from django.conf import settings
from .models import QCM, Question, Reponse
from .ai_generator import QCMGenerator
from books.models import Book, Chapter

logger = logging.getLogger(__name__)


class QCMBookGenerator:
    """
    Classe pour générer automatiquement des QCM pour tous les chapitres d'un livre
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le générateur avec la clé API
        
        :param api_key: Clé API OpenAI, si None, utilise settings.OPENAI_API_KEY
        """
        self.qcm_generator = QCMGenerator(api_key)
    
    def generate_qcm_for_chapter(self, chapter: Chapter, 
                                title: Optional[str] = None, 
                                description: str = "",
                                nb_questions: int = None) -> Optional[QCM]:
        """
        Génère un QCM pour un chapitre spécifique
        
        :param chapter: Objet Chapter
        :param title: Titre personnalisé pour le QCM (optionnel)
        :param description: Description du QCM
        :param nb_questions: Nombre de questions à générer
        :return: Objet QCM créé ou None si échec
        """
        try:
            # Vérifier que le chapitre a des sections
            if not chapter.sections.exists():
                logger.warning(f"Le chapitre {chapter.title} n'a pas de sections, génération ignorée")
                return None
            
            # Définir le nombre de questions
            if nb_questions is None:
                nb_questions = settings.QCM_DEFAULT_QUESTIONS
            nb_questions = min(nb_questions, settings.QCM_MAX_QUESTIONS)
            
            # Générer le titre si non fourni
            if not title:
                title = f"QCM - {chapter.title}"
            
            # Générer les questions avec l'IA
            logger.info(f"Génération du QCM pour le chapitre: {chapter.title}")
            qcm_data = self.qcm_generator.generate_qcm_from_chapter(
                chapter=chapter,
                nb_questions=nb_questions
            )
            
            # Créer le QCM
            qcm = QCM.objects.create(
                book=chapter.book,
                chapter=chapter,
                title=title,
                description=description
            )
            
            # Créer les questions et réponses
            for i, question_data in enumerate(qcm_data):
                question = Question.objects.create(
                    qcm=qcm,
                    text=question_data['question'],
                    order=i + 1
                )
                
                # Créer les réponses
                for j, option in enumerate(question_data['options']):
                    is_correct = (option == question_data['reponse_correcte'])
                    Reponse.objects.create(
                        question=question,
                        text=option,
                        is_correct=is_correct,
                        order=j + 1
                    )
            
            logger.info(f"QCM créé avec succès pour {chapter.title}: {len(qcm_data)} questions")
            return qcm
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du QCM pour {chapter.title}: {e}")
            return None
    
    def generate_qcms_for_book(self, book: Book, 
                             nb_questions_per_chapter: int = None,
                             generate_for_all_chapters: bool = True) -> Dict[str, List[QCM]]:
        """
        Génère des QCM pour tous les chapitres d'un livre
        
        :param book: Objet Book
        :param nb_questions_per_chapter: Nombre de questions par chapitre
        :param generate_for_all_chapters: Si True, génère pour tous les chapitres, sinon seulement ceux sans QCM
        :return: Dictionnaire avec les résultats {'success': [QCM], 'failed': [{'chapter': Chapter, 'error': str}]}
        """
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        chapters = book.chapters.all().order_by('order')
        
        if not chapters.exists():
            logger.warning(f"Le livre {book.title} n'a pas de chapitres")
            return results
        
        logger.info(f"Début de la génération des QCM pour le livre: {book.title}")
        
        for chapter in chapters:
            try:
                # Vérifier si on doit générer un QCM pour ce chapitre
                if not generate_for_all_chapters:
                    existing_qcm = QCM.objects.filter(chapter=chapter).first()
                    if existing_qcm:
                        logger.info(f"Chapitre {chapter.title} a déjà un QCM, génération ignorée")
                        results['skipped'].append(chapter)
                        continue
                
                # Générer le QCM
                qcm = self.generate_qcm_for_chapter(
                    chapter=chapter,
                    nb_questions=nb_questions_per_chapter
                )
                
                if qcm:
                    results['success'].append(qcm)
                else:
                    results['failed'].append({
                        'chapter': chapter,
                        'error': 'Échec de la génération du QCM'
                    })
                    
            except Exception as e:
                logger.error(f"Erreur lors du traitement du chapitre {chapter.title}: {e}")
                results['failed'].append({
                    'chapter': chapter,
                    'error': str(e)
                })
        
        logger.info(f"Génération terminée pour {book.title}: "
                   f"{len(results['success'])} succès, "
                   f"{len(results['failed'])} échecs, "
                   f"{len(results['skipped'])} ignorés")
        
        return results
    
    def generate_qcms_for_book_async(self, book: Book, 
                                   nb_questions_per_chapter: int = None):
        """
        Version asynchrone pour générer des QCM (à implémenter avec Celery si nécessaire)
        """
        # Pour l'instant, version synchrone
        # TODO: Implémenter avec Celery pour le traitement en arrière-plan
        return self.generate_qcms_for_book(book, nb_questions_per_chapter)


# Fonctions utilitaires pour une utilisation simple
def generate_qcm_for_chapter(chapter: Chapter, 
                           title: Optional[str] = None, 
                           description: str = "",
                           nb_questions: int = None) -> Optional[QCM]:
    """
    Génère un QCM pour un chapitre spécifique
    
    :param chapter: Objet Chapter
    :param title: Titre personnalisé pour le QCM (optionnel)
    :param description: Description du QCM
    :param nb_questions: Nombre de questions à générer
    :return: Objet QCM créé ou None si échec
    """
    generator = QCMBookGenerator()
    return generator.generate_qcm_for_chapter(chapter, title, description, nb_questions)


def generate_qcms_for_book(book: Book, 
                         nb_questions_per_chapter: int = None,
                         generate_for_all_chapters: bool = True) -> Dict[str, List[QCM]]:
    """
    Génère des QCM pour tous les chapitres d'un livre
    
    :param book: Objet Book
    :param nb_questions_per_chapter: Nombre de questions par chapitre
    :param generate_for_all_chapters: Si True, génère pour tous les chapitres, sinon seulement ceux sans QCM
    :return: Dictionnaire avec les résultats
    """
    generator = QCMBookGenerator()
    return generator.generate_qcms_for_book(book, nb_questions_per_chapter, generate_for_all_chapters)
