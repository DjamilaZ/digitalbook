#!/usr/bin/env python3
"""
Script de test simple pour vérifier le parsing du PDF et l'assignation des ordres
"""

import os
import sys
import json

# Ajouter le répertoire courant au chemin Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from books.pdf_parser import parse_pdf_to_structured_json

def test_parsing():
    """Teste le parsing du PDF et vérifie les ordres"""
    
    print("=== TEST DE PARSING PDF ===\n")
    
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
        
        # Vérifier la structure
        chapters = structured_data.get('chapters', [])
        print(f"\nNombre de chapitres trouvés: {len(chapters)}")
        
        # Afficher les 3 premiers chapitres pour vérifier les ordres
        for i, chapter in enumerate(chapters[:3]):
            print(f"\nChapitre {i}:")
            print(f"  - Titre: {chapter.get('title', 'N/A')}")
            print(f"  - Order: {chapter.get('order', 'N/A')}")
            print(f"  - Number: {chapter.get('number', 'N/A')}")
            
            # Vérifier les sections
            sections = chapter.get('sections', [])
            print(f"  - Nombre de sections: {len(sections)}")
            
            for j, section in enumerate(sections[:2]):  # Limiter à 2 sections par chapitre
                print(f"    Section {j}:")
                print(f"      - Titre: {section.get('title', 'N/A')}")
                print(f"      - Order: {section.get('order', 'N/A')}")
                print(f"      - Number: {section.get('number', 'N/A')}")
                
                # Vérifier les sous-sections
                subsections = section.get('subsections', [])
                print(f"      - Nombre de sous-sections: {len(subsections)}")
                
                for k, subsection in enumerate(subsections[:2]):  # Limiter à 2 sous-sections
                    print(f"        Sous-section {k}:")
                    print(f"          - Titre: {subsection.get('title', 'N/A')}")
                    print(f"          - Order: {subsection.get('order', 'N/A')}")
                    print(f"          - Number: {subsection.get('number', 'N/A')}")
        
        # Sauvegarder le résultat
        output_path = os.path.join(os.path.dirname(__file__), 'test_parsing_result.json')
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
    success = test_parsing()
    sys.exit(0 if success else 1)
