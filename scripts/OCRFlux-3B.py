from vllm import LLM
from ocrflux.inference import parse

file_path = 'LivreDigital.pdf'  # ou 'test.png'
llm = LLM(model="/path/to/OCRFlux-3B", gpu_memory_utilization=0.8, max_model_len=8192)
result = parse(llm, file_path)

if result is not None:
    document_markdown = result['document_text']
    print(document_markdown)
    with open('test.md', 'w') as f:
        f.write(document_markdown)
else:
    print("Échec de l'analyse.")