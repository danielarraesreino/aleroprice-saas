#!/usr/bin/env python3
"""
Script para converter formatação de números em templates HTML
de formato americano para formato brasileiro
"""

import re
import os
from pathlib import Path

def converter_template(arquivo):
    """Converte formatações de números em um arquivo de template"""
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    conteudo_original = conteudo
    
    # Substituir R$ {{ "%.2f"|format(valor) }} por {{ valor|moeda_br }}
    conteudo = re.sub(r'R\$\s*\{\{\s*"%.2f"\|format\(([^)]+)\)\s*\}\}', r'{{ \1|moeda_br }}', conteudo)
    
    # Substituir {{ "%.1f"|format(valor) }}% por {{ valor|percentual_br }}
    conteudo = re.sub(r'\{\{\s*"%.1f"\|format\(([^)]+)\)\s*\}\}%', r'{{ \1|percentual_br }}', conteudo)
    
    # Substituir {{ "%.2f"|format(valor) }}% por {{ valor|percentual_br }}
    conteudo = re.sub(r'\{\{\s*"%.2f"\|format\(([^)]+)\)\s*\}\}%', r'{{ \1|percentual_br }}', conteudo)
    
    if conteudo != conteudo_original:
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        return True
    return False

# Diretório de templates
templates_dir = Path('/home/dan/Área de Trabalho/AleroPriceSaaS/app/templates')

# Processar todos os arquivos HTML
arquivos_modificados = []
for arquivo_html in templates_dir.rglob('*.html'):
    if converter_template(arquivo_html):
        arquivos_modificados.append(str(arquivo_html))
        print(f'✓ Convertido: {arquivo_html.relative_to(templates_dir)}')

print(f'\n✅ Total de arquivos modificados: {len(arquivos_modificados)}')
