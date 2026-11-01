import argparse
import os
import yaml
import sys
import time

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.utils.exa_miner import ExaMiner

def run_bares(limit=None):
    miner = ExaMiner()
    leads_dir = "app/data/leads"
    files = [f for f in os.listdir(leads_dir) if f.endswith('.yml') and f != 'EXEMPLO.yml.txt']
    
    if limit:
        files = files[:limit]
        
    print(f"Enriquecendo {len(files)} bares...")
    for f in files:
        filepath = os.path.join(leads_dir, f)
        print(f"Processando {f}...")
        success = miner.enrich_gastronomy_lead(filepath)
        if success:
            print("  -> Atualizado com sucesso.")
        time.sleep(1) # Rate limit

def run_advogados(nicho, regiao, limit=5):
    miner = ExaMiner()
    print(f"Prospectando {limit} escritórios de advocacia ({nicho}) em {regiao}...")
    
    leads = miner.prospect_law_firms(nicho, regiao, limit=limit)
    out_dir = "app/data/leads_juridico"
    os.makedirs(out_dir, exist_ok=True)
    
    for lead in leads:
        nome_arquivo = "".join([c if c.isalnum() else "-" for c in lead['nome'].lower()])
        nome_arquivo = nome_arquivo.strip('-') + ".yml"
        
        filepath = os.path.join(out_dir, nome_arquivo)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(lead, f, allow_unicode=True, sort_keys=False)
            
        print(f"Salvo lead: {lead['nome']} ({filepath})")
        print(f"  Diagnóstico: {lead['diagnostico_vendas']}")
        print(f"  Tech: {lead['tecnologias_antigas']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Alero Exa Miner")
    parser.add_argument('--target', choices=['bares', 'advogados'], required=True)
    parser.add_argument('--nicho', help="Nicho de atuação (ex: Trabalhista, Cível)")
    parser.add_argument('--regiao', help="Região (ex: São Paulo, Campinas)")
    parser.add_argument('--limit', type=int, default=5)
    
    args = parser.parse_args()
    
    if args.target == 'bares':
        run_bares(limit=args.limit)
    elif args.target == 'advogados':
        if not args.nicho or not args.regiao:
            print("Para advogados, --nicho e --regiao são obrigatórios.")
            sys.exit(1)
        run_advogados(args.nicho, args.regiao, limit=args.limit)
