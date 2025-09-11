#!/usr/bin/env python3
"""
Script de test pour vérifier que les ordres sont correctement assignés
lors de la création de la hiérarchie des chapitres, sections et sous-sections.
"""

import json
import os
import sys

# Ajouter le répertoire courant au chemin Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from books.pdf_parser import parse_pdf_to_structured_json, create_book_hierarchy_from_json
from books.models import Book, Chapter, Section, Subsection

def test_order_assignment():
    """Teste l'assignation des ordres dans la structure JSON"""
    
    print("=== TEST D'ASSIGNATION DES ORDRES ===\n")
    
    # Tester avec un fichier PDF existant
    pdf_path = os.path.join(os.path.dirname(__file__), 'Livretdigital.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"✗ Fichier PDF non trouvé: {pdf_path}")
        return False
    
    print(f"✓ Fichier PDF trouvé: {pdf_path}")
    
    try:
        # Parser le PDF
        print("\n--- Parsing du PDF ---")
        structured_data = parse_pdf_to_structured_json(pdf_path)
        print("✓ Parsing terminé")
        
        # Vérifier que les ordres sont assignés
        print("\n--- Vérification des ordres dans la structure JSON ---")
        
        chapters = structured_data.get('chapters', [])
        print(f"Nombre de chapitres trouvés: {len(chapters)}")
        
        for i, chapter in enumerate(chapters):
            print(f"\nChapitre {i}:")
            print(f"  - Titre: {chapter.get('title', 'N/A')}")
            print(f"  - Order: {chapter.get('order', 'N/A')}")
            print(f"  - Number: {chapter.get('number', 'N/A')}")
            
            # Vérifier que l'ordre correspond à l'index
            expected_order = i
            actual_order = chapter.get('order')
            if actual_order == expected_order:
                print(f"  ✓ Order correct: {actual_order}")
            else:
                print(f"  ✗ Order incorrect: attendu {expected_order}, obtenu {actual_order}")
            
            # Vérifier les sections
            sections = chapter.get('sections', [])
            print(f"  - Nombre de sections: {len(sections)}")
            
            for j, section in enumerate(sections):
                print(f"    Section {j}:")
                print(f"      - Titre: {section.get('title', 'N/A')}")
                print(f"      - Order: {section.get('order', 'N/A')}")
                print(f"      - Number: {section.get('number', 'N/A')}")
                
                # Vérifier que l'ordre correspond à l'index
                expected_order = j
                actual_order = section.get('order')
                if actual_order == expected_order:
                    print(f"      ✓ Order correct: {actual_order}")
                else:
                    print(f"      ✗ Order incorrect: attendu {expected_order}, obtenu {actual_order}")
                
                # Vérifier les sous-sections
                subsections = section.get('subsections', [])
                print(f"      - Nombre de sous-sections: {len(subsections)}")
                
                for k, subsection in enumerate(subsections):
                    print(f"        Sous-section {k}:")
                    print(f"          - Titre: {subsection.get('title', 'N/A')}")
                    print(f"          - Order: {subsection.get('order', 'N/A')}")
                    print(f"          - Number: {subsection.get('number', 'N/A')}")
                    
                    # Vérifier que l'ordre correspond à l'index
                    expected_order = k
                    actual_order = subsection.get('order')
                    if actual_order == expected_order:
                        print(f"          ✓ Order correct: {actual_order}")
                    else:
                        print(f"          ✗ Order incorrect: attendu {expected_order}, obtenu {actual_order}")
        
        # Sauvegarder le résultat dans un fichier JSON pour vérification
        output_path = os.path.join(os.path.dirname(__file__), 'test_order_result.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Résultat sauvegardé dans: {output_path}")
        print("\n=== TEST TERMINÉ AVEC SUCCÈS ===")
        return True
        
    except Exception as e:
        print(f"\n✗ Erreur lors du test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_order_assignment()
    sys.exit(0 if success else 1)
