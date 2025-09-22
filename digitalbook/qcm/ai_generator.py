import json
import logging
import os
from typing import Dict, List, Optional, Union
from django.conf import settings
import openai

logger = logging.getLogger(__name__)


class QCMGenerator:
    """
    Classe pour générer des QCM en utilisant l'IA (OpenAI)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le générateur avec la clé API
        
        :param api_key: Clé API OpenAI, si None, utilise settings.OPENAI_API_KEY
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            raise ValueError("Clé API OpenAI non configurée")
        
        openai.api_key = self.api_key
    
    def _format_content(self, chapter_title: str, sections: Dict[str, str]) -> str:
        """
        Formate le contenu du chapitre et des sections pour l'IA
        
        :param chapter_title: Titre du chapitre
        :param sections: Dictionnaire {titre_section: contenu}
        :return: Contenu formaté en Markdown
        """
        content = f"# Chapitre: {chapter_title}\n\n"
        
        for section_title, section_content in sections.items():
            # Limiter la longueur du contenu pour éviter les tokens excessifs
            if len(section_content) > 2000:
                section_content = section_content[:2000] + "..."
            
            content += f"## {section_title}\n{section_content}\n\n"
        
        return content
    
    def _create_prompt(self, content: str, nb_questions: int = 5, avoid_questions: Optional[List[str]] = None) -> str:
        """
        Crée le prompt pour l'IA
        
        :param content: Contenu formaté du chapitre
        :param nb_questions: Nombre de questions à générer
        :return: Prompt pour l'IA
        """
        base = f"""
Tu es un expert en pédagogie et en création de contenu éducatif.
À partir du contenu ci-dessous, génère {nb_questions} questions de type QCM pertinentes et variées.

Consignes importantes :
1. Les questions doivent couvrir les concepts clés du contenu
2. Chaque question doit avoir 4 options (A, B, C, D)
3. Une seule réponse doit être correcte
4. Les mauvaises réponses doivent être plausibles mais incorrectes
5. Les questions doivent être claires et précises
6. Adapte le niveau de difficulté au contenu fourni
7. Ne répète pas de questions déjà utilisées; si une question ressemble fortement à une question donnée ci-dessous, propose une variante substantiellement différente.

Format attendu en JSON strict (sans aucun texte avant ou après) :
[
  {{
    "question": "Texte de la question ici",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "reponse_correcte": "Option A",
    "explication": "Brève explication de pourquoi cette réponse est correcte"
  }}
]

Contenu à analyser :
{content}
"""
        if avoid_questions:
            # Limiter la taille injectée pour ne pas exploser le prompt
            limited = avoid_questions[:50]
            avoid_block = "\nQuestions déjà utilisées (à éviter) :\n" + "\n".join(f"- {q}" for q in limited) + "\n"
            return base + avoid_block
        return base
    
    def _parse_response(self, raw_output: str) -> List[Dict]:
        """
        Parse la réponse de l'IA en JSON
        
        :param raw_output: Réponse brute de l'IA
        :return: Liste de questions formatées
        """
        try:
            # Nettoyer la réponse pour enlever les éventuels markdown ou texte avant/après le JSON
            raw_output = raw_output.strip()
            if raw_output.startswith('```json'):
                raw_output = raw_output[7:]
            if raw_output.endswith('```'):
                raw_output = raw_output[:-3]
            
            qcm_data = json.loads(raw_output.strip())
            
            # Valider la structure
            if not isinstance(qcm_data, list):
                raise ValueError("La réponse n'est pas une liste")
            
            for i, question in enumerate(qcm_data):
                required_fields = ['question', 'options', 'reponse_correcte']
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"Question {i}: champ '{field}' manquant")
                
                if not isinstance(question['options'], list) or len(question['options']) != 4:
                    raise ValueError(f"Question {i}: options doivent être une liste de 4 éléments")
                
                if question['reponse_correcte'] not in question['options']:
                    raise ValueError(f"Question {i}: réponse correcte pas dans les options")
            
            return qcm_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            logger.error(f"Réponse brute: {raw_output}")
            raise ValueError(f"La réponse de l'IA n'est pas un JSON valide: {e}")
        except ValueError as e:
            logger.error(f"Erreur de validation: {e}")
            raise
    
    def generate_qcm(self, chapter_title: str, sections: Dict[str, str], 
                    nb_questions: int = 5, model: str = "gpt-4o-mini",
                    avoid_questions_texts: Optional[List[str]] = None) -> List[Dict]:
        """
        Génère un QCM à partir d'un chapitre et de ses sections
        
        :param chapter_title: Titre du chapitre
        :param sections: Dict avec {"titre_section": "contenu..."}
        :param nb_questions: Nombre de questions à générer (max 10)
        :param model: Modèle OpenAI à utiliser
        :return: Liste de questions sous forme de dictionnaires
        """
        if nb_questions > 10:
            nb_questions = 10
            logger.warning("Nombre de questions limité à 10")
        
        try:
            # Formater le contenu
            content = self._format_content(chapter_title, sections)
            
            # Créer le prompt
            prompt = self._create_prompt(content, nb_questions, avoid_questions=avoid_questions_texts)
            
            # Appeler l'API OpenAI
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Tu es un expert en pédagogie spécialisé dans la création de QCM."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Récupérer la réponse
            raw_output = response.choices[0].message.content
            
            # Parser et valider la réponse
            qcm_data = self._parse_response(raw_output)
            
            logger.info(f"QCM généré avec succès: {len(qcm_data)} questions")
            return qcm_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du QCM: {e}")
            raise
    
    def generate_qcm_from_chapter(self, chapter, nb_questions: int = 5, 
                                  avoid_questions_texts: Optional[List[str]] = None) -> List[Dict]:
        """
        Génère un QCM à partir d'un objet Chapter Django
        
        :param chapter: Objet Chapter Django
        :param nb_questions: Nombre de questions à générer
        :return: Liste de questions formatées
        """
        sections = {}
        
        # Récupérer les sections et leur contenu
        for section in chapter.sections.all().order_by('order'):
            sections[section.title] = section.content
        
        return self.generate_qcm(
            chapter_title=chapter.title,
            sections=sections,
            nb_questions=nb_questions,
            avoid_questions_texts=avoid_questions_texts
        )


# Fonction utilitaire pour une utilisation simple
def generate_qcm(api_key: str, chapter_title: str, sections: Dict[str, str], 
                 nb_questions: int = 5) -> List[Dict]:
    """
    Fonction simplifiée pour générer un QCM
    
    :param api_key: Clé API OpenAI
    :param chapter_title: Titre du chapitre
    :param sections: Dict avec {"titre_section": "contenu..."}
    :param nb_questions: Nombre de questions à générer
    :return: Liste de questions sous forme de dictionnaires
    """
    generator = QCMGenerator(os.getenv("OPENAI_API_KEY"))
    return generator.generate_qcm(chapter_title, sections, nb_questions)
