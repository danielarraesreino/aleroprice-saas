"""Personalidade de texto do site, por tipo de casa.

Mesmo truque do `temas.py`, aplicado à copy: em vez de N campos no CMS pro dono
escrever título de seção (que ele não vai escrever), ele escolhe **uma vibe** e
o site inteiro fala naquele tom.

`boteco` é o texto que já estava fixo no template — palavra por palavra. Com ele
como padrão, o Bar da Vila não muda nada. As outras vibes existem porque uma
hamburgueria em Vinhedo não pode receber uma prévia dizendo "samba ao vivo" e
"croquete da Bruna".

Cada vibe define:
  marquee      itens da faixa rolante
  cardapio     eyebrow / titulo / (lead opcional)
  historia     eyebrow / titulo / texto (recebe {nome})
  avaliacoes   eyebrow / titulo
  clima        eyebrow / titulo / 3 cards (emoji, titulo, sub)
  galeria      eyebrow / titulo
  promocoes    eyebrow / titulo — cabeçalho da seção de promoções
  agenda       eyebrow / titulo / lead — cabeçalho da seção de eventos
  reserva      eyebrow / titulo / lead
  reserva_ui   textos do widget de reserva: botao (submit do formulário),
               fallback (parágrafo quando reservas estão desativadas) e
               titulo (link "avisar no WhatsApp" que aparece após o envio)
  contato      eyebrow / titulo
  cta          titulo / linha — o cartão de chamada final da seção de contato
  rodape       linha final
  zap          mensagem que abre no WhatsApp (recebe {nome})
  scroll       microcopy da setinha do hero

Os campos `titulo` podem carregar HTML (<em>, <br>) — o template usa |safe
neles; o resto é texto puro.
"""

VIBE_PADRAO = 'boteco'

VIBES = {
    # ---------------------------------------------------------------- boteco
    # Texto original do template. Não altere sem rodar
    # tests/integration/test_landing_render.py — ele trava a vitrine.
    'boteco': {
        'label': 'Boteco de família',
        'descricao': 'Comida de vó, samba e mesa na calçada.',
        'marquee': ['COSTELINHA', 'CROQUETE DA CASA', 'CARBONARA', 'PASTÉIS',
                    'ORA-PRO-NÓBIS', 'SAMBA AO VIVO', 'CERVEJA GELADA'],
        'cardapio': {'eyebrow': 'O QUE SAI DA COZINHA',
                     'titulo': 'Comida de <em>buteco</em>, feita com amor',
                     'lead': 'Receita de família, tempero de vó. Porções generosas pra dividir na mesa.'},
        'historia': {'eyebrow': 'A FAMÍLIA',
                     'titulo': 'Cada um numa<br><em>posição do time</em>',
                     'texto': 'No {nome} cada pessoa da equipe trabalha junto, em time — e isso é '
                              'lindo de ver. É buteco raiz, acolhedor, onde você chega cliente e '
                              'sai da família.'},
        'avaliacoes': {'eyebrow': 'QUEM VEM, VOLTA', 'titulo': 'Nota <em>quase perfeita</em>'},
        'clima': {'eyebrow': 'O CLIMA DA CASA', 'titulo': 'Tem samba, tem <em>resenha</em>',
                  'cards': [('🎶', 'Samba ao vivo', 'Fim de semana tem festa rolando'),
                            ('🍺', 'Cerveja gelada', 'Do jeito que buteco bom exige'),
                            ('🍽️', 'Comida de verdade', 'Feita na hora, do jeito de casa')]},
        'galeria': {'eyebrow': 'DÁ UMA OLHADA', 'titulo': 'Momentos da <em>casa</em>',
                    'lead': 'Da chapa ao samba, da mesa cheia à cerveja gelada.'},
        'promocoes': {'eyebrow': 'TÁ ROLANDO AGORA', 'titulo': 'Promoções da <em>casa</em>'},
        'agenda': {'eyebrow': 'MARCA NA AGENDA', 'titulo': 'Próximos <em>eventos</em>',
                   'lead': 'Marque na agenda: tem sempre coisa boa rolando por aqui.'},
        'reserva': {'eyebrow': 'GARANTA SUA MESA', 'titulo': 'Reserve sua <em>mesa</em>',
                    'lead': 'Fim de semana lota rápido. Reserva em 30 segundos — a gente confirma '
                            'no seu WhatsApp.'},
        'reserva_ui': {'titulo': 'Avisar o bar no WhatsApp',
                       'botao': 'Reservar mesa 🍺',
                       'fallback': 'Chame a gente no WhatsApp para reservar sua mesa.'},
        'contato': {'eyebrow': 'VEM PRA CÁ', 'titulo': 'Onde a gente <em>te espera</em>'},
        'cta': {'titulo': 'Bateu a fome?',
                'linha': 'Chama no zap, reserva a mesa ou já vem chegando. A cerveja tá gelando.'},
        'rodape': 'Feito com samba e cerveja gelada 💛',
        'zap': 'Olá! Vim pelo site do {nome}',
        'scroll': '↓ role e sente o cheiro',
    },

    # ------------------------------------------------------------------- pub
    'pub': {
        'label': 'Pub / cervejaria',
        'descricao': 'Chope artesanal, rock e madeira escura.',
        'marquee': ['CHOPE ARTESANAL', 'IPA', 'TÁBUAS', 'HAMBÚRGUER',
                    'ROCK', 'MÚSICA AO VIVO', 'HAPPY HOUR'],
        'cardapio': {'eyebrow': 'PRA ACOMPANHAR', 'titulo': 'A cozinha do <em>pub</em>',
                     'lead': 'Feito pra harmonizar com o que está na torneira.'},
        'historia': {'eyebrow': 'A CASA',
                     'titulo': 'Feito por quem<br><em>bebe do bom</em>',
                     'texto': 'O {nome} nasceu do gosto por cerveja de verdade. Torneira que gira, '
                              'rótulo que muda e gente que entende do assunto atrás do balcão.'},
        'avaliacoes': {'eyebrow': 'QUEM PROVA, VOLTA', 'titulo': 'Aprovado <em>na régua</em>'},
        'clima': {'eyebrow': 'O CLIMA DA CASA', 'titulo': 'Chope gelado, som <em>bom</em>',
                  'cards': [('🍺', 'Chope artesanal', 'Torneiras girando o ano todo'),
                            ('🎸', 'Som ao vivo', 'Rock e blues no fim de semana'),
                            ('🪵', 'Ambiente', 'Madeira, meia-luz e conversa boa')]},
        'galeria': {'eyebrow': 'DÁ UMA OLHADA', 'titulo': 'A casa por <em>dentro</em>',
                    'lead': 'Do balcão à mesa cheia.'},
        'promocoes': {'eyebrow': 'TÁ NO QUADRO', 'titulo': 'Promoções da <em>semana</em>'},
        'agenda': {'eyebrow': 'ANOTA AÍ', 'titulo': 'Próximos <em>shows</em>',
                   'lead': 'Som ao vivo, rótulo novo na torneira e happy hour — o quadro muda toda semana.'},
        'reserva': {'eyebrow': 'GARANTA SUA MESA', 'titulo': 'Reserve sua <em>mesa</em>',
                    'lead': 'Sexta e sábado enchem cedo. Reserva rápido que a gente confirma no zap.'},
        'reserva_ui': {'titulo': 'Avisar o pub no WhatsApp',
                       'botao': 'Reservar mesa 🍻',
                       'fallback': 'Chame a gente no WhatsApp para garantir sua mesa perto das torneiras.'},
        'contato': {'eyebrow': 'VEM TOMAR UMA', 'titulo': 'Onde a gente <em>te espera</em>'},
        'cta': {'titulo': 'Bateu a sede?',
                'linha': 'Chama no zap, garante a mesa ou cola no balcão. O chope tá saindo gelado.'},
        # "som alto" saiu de propósito: o rodapé fala em nome do dono, e a maioria
        # destas casas fica em bairro residencial — anunciar barulho é dar munição
        # pra reclamação de vizinho e afastar quem quer conversar. Lúpulo e
        # paciência elogiam o processo da cerveja, sem prometer comportamento.
        'rodape': 'Feito com lúpulo e paciência 🍺',
        'zap': 'Olá! Vim pelo site do {nome}',
        'scroll': '↓ role e veja o que tem na torneira',
    },

    # --------------------------------------------------------- hamburgueria
    'hamburgueria': {
        'label': 'Hamburgueria',
        'descricao': 'Smash, brasa e batata crocante.',
        'marquee': ['SMASH', 'CHEDDAR', 'BACON', 'BATATA RÚSTICA',
                    'MILK-SHAKE', 'ARTESANAL', 'NA BRASA'],
        'cardapio': {'eyebrow': 'O QUE SAI DA CHAPA', 'titulo': 'Hambúrguer de <em>verdade</em>',
                     'lead': 'Carne fresca, pão macio e ponto na régua.'},
        'historia': {'eyebrow': 'A CASA',
                     'titulo': 'Obsessão por<br><em>um lanche bom</em>',
                     'texto': 'No {nome} a receita é simples: ingrediente bom, chapa quente e '
                              'nenhuma pressa na hora de montar. O resto é consequência.'},
        'avaliacoes': {'eyebrow': 'QUEM COME, VOLTA', 'titulo': 'Aprovado <em>na primeira mordida</em>'},
        'clima': {'eyebrow': 'COMO FUNCIONA', 'titulo': 'Rápido, quente e <em>do seu jeito</em>',
                  'cards': [('🔥', 'Na hora', 'Montado só depois que você pede'),
                            ('🍟', 'Batata crocante', 'Fritura na temperatura certa'),
                            ('🛵', 'Delivery', 'Chega quente na sua casa')]},
        'galeria': {'eyebrow': 'DÁ UMA OLHADA', 'titulo': 'Direto da <em>chapa</em>',
                    'lead': 'Porque lanche bom entra pelos olhos.'},
        'promocoes': {'eyebrow': 'SAINDO DA CHAPA', 'titulo': 'Promoções do <em>dia</em>'},
        'agenda': {'eyebrow': 'SE PROGRAMA', 'titulo': 'O que vem <em>por aí</em>',
                   'lead': 'Burger novo no cardápio, combo do mês e noite de lançamento: fica de olho.'},
        'reserva': {'eyebrow': 'GARANTA SUA MESA', 'titulo': 'Reserve sua <em>mesa</em>',
                    'lead': 'Evite a fila do fim de semana: reserva em 30 segundos.'},
        'reserva_ui': {'titulo': 'Avisar a hamburgueria no WhatsApp',
                       'botao': 'Reservar mesa 🍔',
                       'fallback': 'Chame a gente no WhatsApp para garantir sua mesa.'},
        'contato': {'eyebrow': 'VEM COMER', 'titulo': 'Onde a gente <em>te espera</em>'},
        'cta': {'titulo': 'Bateu a larica?',
                'linha': 'Pede no zap, reserva a mesa ou já vem. A chapa tá quente.'},
        'rodape': 'Feito com carne fresca e chapa quente 🍔',
        'zap': 'Olá! Vim pelo site do {nome}',
        'scroll': '↓ role e escolha o seu',
    },

    # ----------------------------------------------------------------- praia
    'praia': {
        'label': 'Praia / ao ar livre',
        'descricao': 'Petisco, sol e pé na areia.',
        'marquee': ['PETISCOS', 'FRUTOS DO MAR', 'CERVEJA GELADA',
                    'DRINKS', 'AO AR LIVRE', 'PÔR DO SOL'],
        'cardapio': {'eyebrow': 'PRA BELISCAR', 'titulo': 'Comida de <em>sol</em>',
                     'lead': 'Porção pra dividir, do jeito que combina com o dia.'},
        'historia': {'eyebrow': 'A CASA',
                     'titulo': 'Feito pra<br><em>ficar mais um pouco</em>',
                     'texto': 'O {nome} é daqueles lugares onde a tarde passa sem você perceber: '
                              'mesa boa, sombra na medida e ninguém com pressa.'},
        'avaliacoes': {'eyebrow': 'QUEM VEM, FICA', 'titulo': 'Nota <em>de quem volta</em>'},
        'clima': {'eyebrow': 'O CLIMA DA CASA', 'titulo': 'Sol, sombra e <em>copo cheio</em>',
                  'cards': [('🌅', 'Ao ar livre', 'Mesa na sombra e vista boa'),
                            ('🍹', 'Drinks', 'Gelado do começo ao fim'),
                            ('🎶', 'Som ambiente', 'No volume de conversar')]},
        'galeria': {'eyebrow': 'DÁ UMA OLHADA', 'titulo': 'Um dia por <em>aqui</em>',
                    'lead': 'Do almoço ao pôr do sol.'},
        'promocoes': {'eyebrow': 'APROVEITA ENQUANTO DURA', 'titulo': 'Promoções da <em>temporada</em>'},
        'agenda': {'eyebrow': 'MARCA NO CALENDÁRIO', 'titulo': 'Próximos <em>dias bons</em>',
                   'lead': 'Luau, música no fim de tarde e pôr do sol com copo cheio.'},
        'reserva': {'eyebrow': 'GARANTA SUA MESA', 'titulo': 'Reserve sua <em>mesa</em>',
                    'lead': 'Dia de sol lota. Reserva rápido que a gente confirma no seu WhatsApp.'},
        'reserva_ui': {'titulo': 'Avisar a casa no WhatsApp',
                       'botao': 'Reservar mesa 🌅',
                       'fallback': 'Chame a gente no WhatsApp para guardar sua mesa na sombra.'},
        'contato': {'eyebrow': 'VEM PASSAR O DIA', 'titulo': 'Onde a gente <em>te espera</em>'},
        'cta': {'titulo': 'Bateu a vontade?',
                'linha': 'Chama no zap, garante sua mesa e vem curtir o fim de tarde sem pressa.'},
        'rodape': 'Feito com sol e cerveja gelada 🌊',
        'zap': 'Olá! Vim pelo site do {nome}',
        'scroll': '↓ role e escolha sua mesa',
    },
}


def vibe_valida(nome):
    return nome in VIBES


def copy_da_vibe(nome, nome_bar=''):
    """Textos do site pra esta vibe, com {nome} já resolvido."""
    vibe = VIBES.get(nome or VIBE_PADRAO) or VIBES[VIBE_PADRAO]
    copia = {k: v for k, v in vibe.items() if k not in ('label', 'descricao')}
    copia['historia'] = dict(copia['historia'])
    copia['historia']['texto'] = copia['historia']['texto'].format(nome=nome_bar or 'nossa casa')
    copia['zap'] = copia['zap'].format(nome=nome_bar or 'seu site')
    return copia


def opcoes_de_vibe():
    """Lista pro seletor do /config-site."""
    return [{'valor': chave, 'label': v['label'], 'descricao': v['descricao']}
            for chave, v in VIBES.items()]
