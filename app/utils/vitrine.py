"""Agenda e promoção de demonstração na prévia comercial.

O problema que isto resolve
---------------------------
A agenda ("quem toca sexta") e a promoção são o que o dono de bar mais quer ver
— é o recurso que ele entende sem explicação. Mas a prévia é montada a partir de
dados públicos, e evento futuro não está no Google: das 17 casas no banco, só uma
tem agenda cadastrada.

Como o site esconde seção vazia (e deve mesmo — título com corpo vazio denuncia
site inacabado), o resultado era o pior possível: o vendedor abre a prévia na
frente do dono e justamente o recurso que venderia não aparece em lugar nenhum.

A saída
-------
**Só na prévia**, quando o bar não tem agenda própria, a seção aparece preenchida
com exemplos marcados como exemplos. Não é invenção passada por real: cada item
carrega `exemplo=True`, o template estampa o selo, e a página inteira já vem com
banner de "prévia não oficial" e `noindex`.

Cliente pagante nunca vê isto: ali é agenda de verdade ou seção nenhuma. É a
mesma regra do resto do produto — a prévia demonstra, o site publica.
"""
from datetime import date, timedelta


class ItemDeExemplo:
    """Espelha a interface que os templates esperam de Evento/Promocao.

    Objeto solto de propósito: nada disto encosta no banco. Assim a demonstração
    não vira dado do bar, não sobrevive à conversão e não precisa de limpeza.
    """
    exemplo = True

    def __init__(self, **campos):
        self.__dict__.update(campos)


# Sexta e sábado são as noites que enchem — é quando a agenda importa.
def _proxima(dia_semana):
    """A próxima ocorrência do dia, incluindo hoje.

    Incluir hoje importa: numa sexta-feira, o show "de sexta" é hoje à noite, não
    daqui a uma semana — pular para a semana seguinte deixava o sábado de amanhã
    aparecendo antes da sexta na lista.
    """
    hoje = date.today()
    return hoje + timedelta(days=(dia_semana - hoje.weekday()) % 7)


def eventos_de_exemplo(vibe=None):
    """Dois shows plausíveis para a casa, na sexta e no sábado que vêm.

    Sempre em ordem cronológica: agenda fora de ordem é a primeira coisa que
    denuncia dado falso.
    """
    por_vibe = {
        'pub': [('Noite de lançamento', 'Chope novo na torneira, direto do tanque.'),
                ('Música ao vivo', 'Banda convidada tocando no salão.')],
        'hamburgueria': [('Combo da sexta', 'Smash duplo com batata e chope.'),
                         ('Sábado na chapa', 'Rodízio de burgers até acabar.')],
        'praia': [('Pôr do sol com música', 'Voz e violão na beira.'),
                  ('Luau de sábado', 'Fogueira, roda de violão e petisco.')],
    }
    padrao = [('Samba de roda', 'Roda de samba no salão, entrada franca.'),
              ('Música ao vivo', 'Voz e violão a partir das 20h.')]
    base = por_vibe.get(vibe, padrao)

    agenda = [
        ItemDeExemplo(data=_proxima(4), hora='20h', titulo=base[0][0], descricao=base[0][1]),
        ItemDeExemplo(data=_proxima(5), hora='21h', titulo=base[1][0], descricao=base[1][1]),
    ]
    agenda.sort(key=lambda ev: ev.data)
    return agenda


def promocoes_de_exemplo(vibe=None):
    """Uma promoção só: mais que isso vira ruído e tira o foco do recurso."""
    por_vibe = {
        'pub': ('Happy hour', 'Chope em dobro das 17h às 19h.', 'TODA QUINTA'),
        'hamburgueria': ('Dobro na terça', 'Peça um burger, leve dois.', 'TODA TERÇA'),
        'praia': ('Balde gelado', 'Balde de long neck com preço de fim de tarde.', 'TODO SÁBADO'),
    }
    titulo, descricao, rotulo = por_vibe.get(
        vibe, ('Happy hour', 'Chope e porção com preço de balcão até as 19h.', 'DE SEG A SEX'))

    return [ItemDeExemplo(titulo=titulo, descricao=descricao, rotulo=rotulo,
                          acontece_hoje=False, dia_semana=None, validade=None)]
