# -*- coding: utf-8 -*-

import locale
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Configura a localização brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            except locale.Error:
                print('Aviso: Não foi possível configurar locale brasileiro. Usando padrão do sistema.')
                pass

def formatar_moeda(valor):
    """
    Formata um valor para o padrão monetário brasileiro (R$)
    """
    if valor is None:
        return 'R$ 0,00'
    
    if isinstance(valor, str):
        try:
            valor = float(valor.replace('.', '').replace(',', '.'))
        except ValueError:
            return 'R$ 0,00'
    
    try:
        return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        try:
            return f'R$ {float(valor):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except Exception:
            # valor não numérico (ex.: atributo Jinja Undefined): não derruba a
            # página inteira por causa de um campo — mostra zero.
            return 'R$ 0,00'

# Tudo que não é dígito, vírgula ou ponto sai fora: "R$", espaço, espaço duro
# do teclado do celular, "reais", "/porção".
_SO_NUMERO = re.compile(r'[^\d,.]')

# Preço de prato cabe em Numeric(8,2) — ver DishCard.preco. Acima disso o banco
# recusaria a linha inteira; aqui vira "não entendi", que é recuperável.
_TETO_MOEDA = Decimal('1000000')


def ler_moeda(texto):
    """Caminho inverso de `formatar_moeda`: o que o dono digitou -> Decimal.

    O vendedor digita de pé, no celular, na frente do dono do bar. Os três
    jeitos que ele escreve dezoito e cinquenta são "18,50", "R$ 18,50" e
    "18.50" — e os três precisam virar o mesmo `Decimal('18.50')`. Exigir um
    formato só é transferir pro humano um trabalho que a máquina faz.

    Devolve `None` (nunca zero) para vazio, lixo, negativo e para o próprio
    zero: no site, "sem preço" esconde o campo e `R$ 0,00` seria um preço
    anunciado. É o mesmo princípio da regra de ouro de `app/utils/seo.py` —
    dado ausente não vira dado inventado.

    Cuidado com a assimetria do módulo: `formatar_moeda(None)` devolve
    'R$ 0,00' de propósito (o painel interno quer ver zero numa coluna de
    total). Por isso quem exibe preço de prato precisa checar antes de
    formatar, e não confiar no filtro para sumir com o campo.
    """
    if texto is None:
        return None

    if isinstance(texto, bool):     # True é int em Python; preço não é sim/não
        return None

    if isinstance(texto, (int, float, Decimal)):
        bruto = str(texto)
    else:
        original = str(texto).strip()
        bruto = _SO_NUMERO.sub('', original).strip('.,')
        if not bruto:
            return None
        # O sinal é apagado junto com o "R$", então é conferido no original:
        # sem isto "R$ -5,00" viraria R$ 5,00 — o oposto do que foi digitado.
        if re.match(r'^[^\d]*-', original):
            return None
        if ',' in bruto:
            # Vírgula presente = vírgula é o decimal (BR). Ponto vira milhar.
            # Mas em BR o ponto vem ANTES da vírgula ("1.234,56"); ponto depois
            # é notação americana ("1,234.56"), e chutar ali daria R$ 1,23 num
            # prato de R$ 1.234,56. Preço errado calado é pior que campo vazio.
            if '.' in bruto.rsplit(',', 1)[1]:
                return None
            bruto = bruto.replace('.', '').replace(',', '.')
        else:
            partes = bruto.split('.')
            # Separador de milhar só existe em grupos de 3 ("1.234.567").
            # Qualquer outro tamanho depois do ponto é centavo: "18.50", "18.5".
            if len(partes) == 1:
                pass                                  # "18" — inteiro puro
            elif all(len(p) == 3 for p in partes[1:]):
                bruto = ''.join(partes)               # "1.234" -> 1234
            else:
                bruto = ''.join(partes[:-1]) + '.' + partes[-1]

    try:
        valor = Decimal(bruto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, ArithmeticError):
        return None

    if valor <= 0 or valor >= _TETO_MOEDA:
        return None
    return valor


def formatar_peso(valor, unidade='kg'):
    """
    Formata um valor de peso no padrão brasileiro
    """
    if valor is None:
        return f'0,00 {unidade}'
    
    try:
        return f'{float(valor):,.3f} {unidade}'.replace('.', ',') if unidade == 'kg' else f'{float(valor):,.2f} {unidade}'.replace('.', ',')
    except:
        return f'0,00 {unidade}'

def formatar_percentual(valor):
    """
    Formata um valor para percentual no padrão brasileiro
    """
    if valor is None:
        return '0,00%'
    
    try:
        return f'{float(valor):,.2f}%'.replace('.', ',')
    except:
        return '0,00%'

def formatar_data(data, formato='%d/%m/%Y'):
    """
    Formata uma data para o padrão brasileiro
    """
    if not data:
        return ''
    
    if isinstance(data, str):
        try:
            # Tenta converter a string para datetime
            if '/' in data:
                partes = data.split('/')
                if len(partes) == 3 and len(partes[2]) == 4:
                    data = datetime.strptime(data, '%d/%m/%Y')
                else:
                    return data
            elif '-' in data:
                data = datetime.strptime(data, '%Y-%m-%d')
            else:
                return data
        except ValueError:
            return data
    
    try:
        return data.strftime(formato)
    except:
        return str(data)

def formatar_numero(valor, decimais=2):
    """
    Formata um número com separador de milhares e vírgula como separador decimal
    """
    if valor is None:
        return '0' if decimais == 0 else f'0,{"0" * decimais}'
    
    try:
        formato = f'{{:,.{decimais}f}}'
        return formato.format(float(valor)).replace('.', ',') if decimais > 0 else formato.format(float(valor)).replace(',', '.')
    except:
        return '0' if decimais == 0 else f'0,{"0" * decimais}'
