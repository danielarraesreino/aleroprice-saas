"""Agenda de Barão e "o que abre hoje".

Três fontes, nenhuma inventada:
  1. a Feira (horário confirmado pelo organizador, `seo.HORARIOS_FEIRA`);
  2. o horário que cada bar escreveu no próprio site (`SiteConfig.horario`),
     só quando o parser lê com segurança (tudo ou nada, como no SEO);
  3. eventos: os que os bares cadastram no painel (`Evento`) e os do arquivo
     `app/data/agenda/*.yml`, que o operador preenche com o que o bar mandou.

Dado velho é o maior risco de uma agenda. Por isso evento de arquivo SEM
`verificado_em` não aparece, evento passado some e a página mostra a data da
conferência mais antiga que ainda está valendo.

Funções puras (recebem `hoje`/`agora` e linhas simples) para testar sem banco.
"""
import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import yaml

from app.utils import seo

FUSO = ZoneInfo('America/Sao_Paulo')
TIPOS = ('feira', 'bar', 'unicamp', 'cultura')
ROTULO_TIPO = {'feira': 'Feira', 'bar': 'Bar', 'unicamp': 'Unicamp', 'cultura': 'Cultura'}
PASTA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'agenda')
DIAS_ABREV = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')
DIAS_LONGO = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
log = logging.getLogger(__name__)


def agora_br():
    return datetime.now(FUSO)


def _texto(valor):
    texto = ('' if valor is None else str(valor)).strip()
    return '' if texto.lower() in ('none', 'null') else texto


def _data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(_texto(valor))
    except ValueError:
        return None


def _hora(valor):
    try:
        h, m = (int(x) for x in _texto(valor).split(':'))
        return f'{h:02d}:{m:02d}' if 0 <= h < 24 and 0 <= m < 60 else ''
    except ValueError:
        return ''


def rotulo_dia(dia, hoje):
    if dia == hoje:
        return 'Hoje'
    if dia == hoje + timedelta(days=1):
        return 'Amanhã'
    return f'{DIAS_ABREV[dia.weekday()]}, {dia.day}/{dia.month}'


def evento(titulo, dia, hoje, hora='', local='', tipo='cultura', link='', fonte='', verificado_em=None):
    """Normaliza um evento. Devolve None se faltar o essencial ou já passou."""
    titulo, dia = _texto(titulo), _data(dia)
    if not titulo or dia is None or dia < hoje:
        return None
    tipo = _texto(tipo).lower()
    link = _texto(link)
    return {
        'titulo': titulo, 'data': dia, 'rotulo': rotulo_dia(dia, hoje),
        'hora': _hora(hora), 'local': _texto(local),
        'tipo': tipo if tipo in TIPOS else 'cultura',
        'link': link if link.startswith(('http://', 'https://', '/')) else '',
        'fonte': _texto(fonte), 'verificado_em': _data(verificado_em),
    }


def eventos_do_arquivo(hoje, pasta=PASTA):
    """Eventos dos .yml. Sem `verificado_em`, o evento não entra (dado sem conferência)."""
    saida = []
    if not os.path.isdir(pasta):
        return saida
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith('.yml'):
            continue
        try:
            with open(os.path.join(pasta, nome), encoding='utf-8') as f:
                dados = yaml.safe_load(f) or {}
        except Exception:
            log.warning('agenda: %s ilegível', nome)
            continue
        for bruto in (dados.get('eventos') or []) if isinstance(dados, dict) else []:
            if not isinstance(bruto, dict):
                continue
            ev = evento(bruto.get('titulo'), bruto.get('data'), hoje, bruto.get('hora'),
                        bruto.get('local'), bruto.get('tipo'), bruto.get('link'),
                        bruto.get('fonte'), bruto.get('verificado_em'))
            if ev and ev['verificado_em']:
                saida.append(ev)
    return saida


def proximos(hoje, do_painel=(), do_arquivo=None, dias=14):
    """Eventos dos próximos `dias`, em ordem. `do_painel`: tuplas (titulo, data, hora, bar, url)."""
    limite = hoje + timedelta(days=dias)
    lista = list(eventos_do_arquivo(hoje) if do_arquivo is None else do_arquivo)
    for titulo, dia, hora, bar, url in do_painel:
        ev = evento(titulo, dia, hoje, hora, bar, 'bar', url, 'cadastrado pelo bar', None)
        if ev:
            lista.append(ev)
    lista = [e for e in lista if e['data'] <= limite]
    lista.sort(key=lambda e: (e['data'], e['hora'] or '99:99', e['titulo']))
    return lista


def conferido_em(eventos):
    """Data de conferência mais antiga entre os eventos de arquivo (None se não houver)."""
    datas = [e['verificado_em'] for e in eventos if e['verificado_em']]
    return min(datas) if datas else None


def _minutos(hhmm):
    h, m = hhmm.split(':')
    return int(h) * 60 + int(m)


def _fmt(minutos):
    h, m = divmod(minutos % (24 * 60), 60)
    return f'{h}h' if m == 0 else f'{h}h{m:02d}'


def _faixas_de_hoje(especificacoes, agora):
    """[(abre, fecha|None)] em minutos, para o dia da semana de `agora`."""
    nome = DIAS_LONGO[agora.weekday()]
    faixas = []
    for esp in especificacoes:
        dias = esp.get('dayOfWeek')
        if nome in (dias if isinstance(dias, list) else [dias]):
            faixas.append((_minutos(esp['opens']),
                           _minutos(esp['closes']) if esp.get('closes') else None))
    return faixas


def status_do_dia(especificacoes, agora):
    """('aberto'|'abre'|'encerrado'|None, texto curto). None = não abre hoje ou sem dado."""
    faixas = _faixas_de_hoje(especificacoes, agora)
    if not faixas:
        return None, ''
    atual = agora.hour * 60 + agora.minute
    for abre, fecha in sorted(faixas):
        fim = None if fecha is None else (fecha if fecha > abre else fecha + 24 * 60)
        if atual >= abre and (fim is None or atual < fim):
            return 'aberto', ('aberto agora' if fim is None else f'aberto até {_fmt(fecha)}')
        if atual < abre:
            return 'abre', f'abre às {_fmt(abre)}' + ('' if fecha is None else f', fecha às {_fmt(fecha)}')
    return 'encerrado', 'já encerrou hoje'


def abre_hoje(agora, bares=()):
    """A Feira (se hoje é dia de feira) e os bares que abrem hoje, só com horário lido.

    `bares`: dicts {nome, url, horario}. Quem tem horário que o parser não lê com
    segurança fica de fora; não se chuta (SEO e agenda seguem a mesma regra).
    """
    saida = []
    feira = [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': dia, 'opens': abre, 'closes': fecha}
             for dia, abre, fecha in seo.HORARIOS_FEIRA]
    estado, texto = status_do_dia(feira, agora)
    if estado:
        saida.append({'nome': 'Feira de Barão', 'local': seo.LOCAL_FEIRA, 'tipo': 'feira',
                      'estado': estado, 'texto': texto, 'url': '/feira'})
    for bar in bares:
        nome, horario = _texto(bar.get('nome')), _texto(bar.get('horario'))
        if not nome or not horario:
            continue
        espec = (seo._especificacoes_de_horario(seo.horario_schema(horario))
                 or seo.abertura_schema(horario))
        estado, texto = status_do_dia(espec, agora)
        if estado:
            saida.append({'nome': nome, 'local': '', 'tipo': 'bar', 'estado': estado,
                          'texto': texto, 'url': _texto(bar.get('url'))})
    ordem = {'aberto': 0, 'abre': 1, 'encerrado': 2}
    saida.sort(key=lambda b: (b['tipo'] != 'feira', ordem[b['estado']], b['nome']))
    return saida


def json_ld(eventos, origem):
    """Event por item (só o que existe; sem `offers` inventado)."""
    nos = []
    for e in eventos:
        inicio = e['data'].isoformat() + (f"T{e['hora']}:00-03:00" if e['hora'] else '')
        no = {'@type': 'Event', 'name': e['titulo'], 'startDate': inicio,
              'eventStatus': 'https://schema.org/EventScheduled',
              'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode'}
        if e['local']:
            no['location'] = {'@type': 'Place', 'name': e['local'],
                              'address': {'@type': 'PostalAddress', 'addressLocality': 'Campinas',
                                          'addressRegion': 'SP', 'addressCountry': 'BR'}}
        if e['link']:
            no['url'] = e['link'] if e['link'].startswith('http') else origem + e['link']
        nos.append(no)
    return nos
