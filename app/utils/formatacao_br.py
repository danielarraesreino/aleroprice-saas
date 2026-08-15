# -*- coding: utf-8 -*-

import locale
from datetime import datetime
from decimal import Decimal

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
