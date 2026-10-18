import os
import requests
import re
import yaml
import json

EXA_API_KEY = "452381fe-f2fd-4956-99e6-78c181bc74b4"
EXA_ENDPOINT = "https://api.exa.ai/search"

class ExaMiner:
    def __init__(self):
        self.headers = {
            "x-api-key": EXA_API_KEY,
            "Content-Type": "application/json"
        }

    def _extract_contacts(self, text):
        contacts = {"whatsapp": None, "instagram": None}
        if not text:
            return contacts
            
        # Basic regex for Brazilian phones (11) 99999-9999 or 11999999999
        phone_matches = re.findall(r'\(?\d{2}\)?\s?(?:9\d{4}|\d{4})[-\s]?\d{4}', text)
        if phone_matches:
            # Pick the first one that looks like a mobile
            for p in phone_matches:
                clean = re.sub(r'\D', '', p)
                if len(clean) >= 10:
                    contacts['whatsapp'] = p
                    break
        
        # Regex for Instagram handles
        ig_matches = re.findall(r'instagram\.com/([A-Za-z0-9_.]+)/?', text)
        if ig_matches:
            contacts['instagram'] = f"https://www.instagram.com/{ig_matches[0]}/"

        return contacts

    def enrich_gastronomy_lead(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return False

        nome = data.get('nome', os.path.basename(filepath).replace('.yml', ''))
        
        payload = {
            "query": f"{nome} Barão Geraldo Campinas site oficial instagram telefone",
            "numResults": 2,
            "useAutoprompt": True,
            "contents": {"text": True}
        }
        
        try:
            resp = requests.post(EXA_ENDPOINT, headers=self.headers, json=payload)
            resp.raise_for_status()
            results = resp.json().get('results', [])
            
            best_ig = None
            best_phone = None
            
            for res in results:
                url = res.get('url', '')
                text = res.get('text', '')
                contacts = self._extract_contacts(text)
                
                if contacts['instagram']: best_ig = contacts['instagram']
                if contacts['whatsapp']: best_phone = contacts['whatsapp']
                if "instagram.com" in url:
                    best_ig = url
                    
            # Consolidate
            if 'site' not in data:
                data['site'] = {}
                
            if best_ig and not data['site'].get('instagram_url'):
                data['site']['instagram_url'] = best_ig
                
            if best_phone and not data['site'].get('telefone_exibicao'):
                data['site']['telefone_exibicao'] = best_phone
                
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
                
            return True
        except Exception as e:
            print(f"Error enriching {nome}: {e}")
            return False

    def prospect_law_firms(self, nicho, regiao, limit=5):
        prompt = f"Aqui está o site do nosso escritório de advocacia em {regiao} especializado em direito {nicho}:"
        
        payload = {
            "query": prompt,
            "numResults": limit,
            "useAutoprompt": False,
            "contents": {"text": True}
        }
        
        leads = []
        try:
            resp = requests.post(EXA_ENDPOINT, headers=self.headers, json=payload)
            resp.raise_for_status()
            results = resp.json().get('results', [])
            
            for res in results:
                url = res.get('url', '')
                title = res.get('title', 'Escritório Desconhecido')
                text = res.get('text', '')
                
                # Check for bad tech
                tech_stack = []
                text_lower = text.lower()
                if 'wp-content' in url or 'wordpress' in text_lower:
                    tech_stack.append('WordPress')
                if 'elementor' in text_lower:
                    tech_stack.append('Elementor')
                if 'wix' in url or 'wix' in text_lower:
                    tech_stack.append('Wix')
                
                contacts = self._extract_contacts(text)
                
                leads.append({
                    "nome": title.strip(),
                    "url": url,
                    "tecnologias_antigas": tech_stack if tech_stack else ["Desconhecida/Custom"],
                    "contatos": contacts,
                    "diagnostico_vendas": "Forte candidato para Luxury UX 50k" if tech_stack else "Analisar viabilidade"
                })
        except Exception as e:
            print(f"Error prospecting law firms: {e}")
            
        return leads
