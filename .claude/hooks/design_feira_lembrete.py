#!/usr/bin/env python3
"""Lembrete de design: nunca bloqueia, só injeta contexto para o Claude.

PreToolUse (Edit/Write/MultiEdit): se o arquivo é de site/portal/CSS, lembra da skill.
UserPromptSubmit: se o pedido fala de hotsite/modelo/expositor/tenant, lembra da skill.
"""
import json
import re
import sys

SITE = 'app/templates/site/'
PORTAL = ('app/templates/produto/', 'app/static/css/')
PALAVRAS = re.compile(r'hotsite|modelo de (site|bar|artes)|expositor|tenant|pr[eé]via|bardavila|design do site', re.I)

try:
    dados = json.load(sys.stdin)
except Exception:
    sys.exit(0)

evento = dados.get('hook_event_name', '')
msg = None
if evento == 'PreToolUse':
    caminho = (dados.get('tool_input') or {}).get('file_path', '').replace('\\', '/')
    if SITE in caminho:
        msg = ('Antes de editar este arquivo de site: invoque a skill design-feira (regras R1-R12), leia o modelo '
               'de bar-fonte em references/receitas.md, e ao terminar rode o checklist (capturas 320/390/768/1440, '
               'claro/escuro, com e sem foto) e a suíte. Sem deploy sem OK do dono.')
    elif any(p in caminho for p in PORTAL):
        msg = ('Alteração visual do portal: use impeccable + frontend-design, siga docs/DESIGN.md e confira '
               'capturas antes de pedir OK ao dono.')
elif evento == 'UserPromptSubmit':
    if PALAVRAS.search(dados.get('prompt', '')):
        msg = ('Pedido sobre site de expositor/bar/tenant: invoque a skill design-feira e consulte '
               '~/Documentos/FEIRADEBARAO/documentacao/09_SKILLS_MAPA_E_ACIONAMENTO.md.')

if msg:
    print(json.dumps({'hookSpecificOutput': {'hookEventName': evento, 'additionalContext': msg}}))
