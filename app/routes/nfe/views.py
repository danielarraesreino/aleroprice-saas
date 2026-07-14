from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from app.extensions import db
from app.models.modelo_nfe import NFNota, NFItem
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_produto import Produto
from app.models.modelo_restaurante import Restaurante
from app.routes.nfe import bp
from app.utils.tenant import get_current_restaurant_id
import xmltodict
from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re

# Modelos Pydantic para validação do XML da NF-e
class NFeItemModel(BaseModel):
    num_item: int = Field(..., alias='nItem')
    codigo: str = Field(..., alias='cProd')
    descricao: str = Field(..., alias='xProd')
    ncm: Optional[str] = Field(None, alias='NCM')
    cfop: Optional[str] = Field(None, alias='CFOP')
    unidade: str = Field(..., alias='uCom')
    quantidade: float = Field(..., alias='qCom')
    valor_unitario: float = Field(..., alias='vUnCom')
    valor_total: float = Field(..., alias='vProd')
    icms_valor: Optional[float] = None
    icms_aliquota: Optional[float] = None
    ipi_valor: Optional[float] = None
    ipi_aliquota: Optional[float] = None
    
    class Config:
        extra = 'ignore'  # Ignora campos não mapeados

class NFeDestinatarioModel(BaseModel):
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    razao_social: str = Field(..., alias='xNome')
    
    class Config:
        extra = 'ignore'

class NFeFornecedorModel(BaseModel):
    cnpj: str
    razao_social: str = Field(..., alias='xNome')
    inscricao_estadual: Optional[str] = Field(None, alias='IE')
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    
    class Config:
        extra = 'ignore'  # Ignora campos não mapeados

class NFeModel(BaseModel):
    chave_acesso: str
    numero: str = Field(..., alias='nNF')
    serie: str = Field(..., alias='serie')
    data_emissao: datetime
    valor_produtos: float = Field(..., alias='vProd')
    valor_total: float = Field(..., alias='vNF')
    valor_frete: Optional[float] = Field(0, alias='vFrete')
    valor_seguro: Optional[float] = Field(0, alias='vSeg')
    valor_desconto: Optional[float] = Field(0, alias='vDesc')
    valor_impostos: Optional[float] = Field(0, alias='vImp')
    fornecedor: NFeFornecedorModel
    destinatario: NFeDestinatarioModel
    itens: List[NFeItemModel]
    
    class Config:
        extra = 'ignore'  # Ignora campos não mapeados

@bp.route('/')
@bp.route('/index')
def index():
    """Lista notas fiscais importadas"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Construir query base com filtro de tenant
    query = NFNota.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        query = query.filter(NFNota.data_emissao >= data_inicio)
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
        query = query.filter(NFNota.data_emissao <= data_fim)
    
    # Ordenar e paginar
    notas = query.order_by(NFNota.data_emissao.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter lista de fornecedores para filtro (apenas do tenant)
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    
    return render_template('nfe/index.html', 
                          notas=notas, 
                          fornecedores=fornecedores)

@bp.route('/importar', methods=['GET', 'POST'])
def importar():
    """Importa nota fiscal eletrônica via XML"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        # Verificar se um arquivo foi enviado
        if 'xml_file' not in request.files:
            flash('Nenhum arquivo enviado!', 'danger')
            return render_template('nfe/importar.html')
        
        arquivo = request.files['xml_file']
        
        # Verificar se o arquivo é válido
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'danger')
            return render_template('nfe/importar.html')
        
        if not arquivo.filename.lower().endswith('.xml'):
            flash('Apenas arquivos XML são permitidos!', 'danger')
            return render_template('nfe/importar.html')
        
        try:
            # Ler o conteúdo do XML
            xml_content = arquivo.read().decode('utf-8')
            
            # Processar o XML
            nfe_data = processar_xml_nfe(xml_content)
            
            # Validar CNPJ do Destinatário (Blindagem)
            restaurante = Restaurante.query.get(restaurant_id)
            if restaurante and restaurante.cnpj:
                dest_cnpj = nfe_data.destinatario.cnpj
                # Remover pontuação para comparação
                if dest_cnpj:
                    dest_cnpj_limpo = re.sub(r'\D', '', dest_cnpj)
                    rest_cnpj_limpo = re.sub(r'\D', '', restaurante.cnpj)
                    
                    if dest_cnpj_limpo != rest_cnpj_limpo:
                        flash(f'Bloqueio de Segurança: Esta nota fiscal é destinada ao CNPJ {dest_cnpj}, mas o seu restaurante é {restaurante.cnpj}.', 'danger')
                        return render_template('nfe/importar.html')
            
            # Verificar se a NF-e já existe no sistema (para este tenant ou globalmente? Chave é unica globalmente normaly, mas vamos filtrar por tenant por segurança)
            # Na verdade, a chave deve ser única. Se outro tenant importou a mesma nota, algo está errado (mesma nota em dois restaurantes?).
            # Vamos assumir que se existe, bloqueia. Mas para evitar colisão entre tenants se houver dados compartilhados errados, filtrar por tenant é bom, 
            # mas chave de acesso é única no mundo. Se já existe no DB, não importa o tenant, já foi importada?
            # Se for multi-tenancy real em SCHEMA compartilhado, a chave deve ser unique PER TENANT?
            # Não, uma nota fiscal é destinada a UM CNPJ destinatário. Se os tenants tem CNPJs diferentes, nunca colidirá.
            # Se tenants compartilham CNPJ (filiais), a nota é a mesma.
            # Vamos filtrar por existencia.
            nota_existente = NFNota.query.filter_by(chave_acesso=nfe_data.chave_acesso).first() # Check global ou tenant?
            # Se filtrar por tenant:
            # nota_existente = NFNota.query.filter_by(chave_acesso=nfe_data.chave_acesso, restaurant_id=restaurant_id).first()
            # Se já existir em OUTRO tenant, permitimos importar de novo? Talvez sim, se for um sistema multi-loja.
            # Vamos filtrar por tenant para isolamento.
            nota_existente = NFNota.query.filter_by(chave_acesso=nfe_data.chave_acesso, restaurant_id=restaurant_id).first()
            
            if nota_existente:
                flash(f'Nota fiscal {nfe_data.numero}/{nfe_data.serie} já importada anteriormente!', 'warning')
                return redirect(url_for('nfe.visualizar', id=nota_existente.id))
            
            # Importar a NF-e
            nova_nota = importar_nfe(nfe_data, xml_content, restaurant_id)
            
            # Atualizar estoque com base nos itens da NF-e
            nova_nota.atualizar_estoque()
            
            flash(f'Nota fiscal {nfe_data.numero}/{nfe_data.serie} importada com sucesso!', 'success')
            return redirect(url_for('nfe.visualizar', id=nova_nota.id))
            
        except ValueError as ve:
             flash(f'Erro de Validação: {str(ve)}', 'warning')
             return render_template('nfe/importar.html')
        except Exception as e:
            # Logar erro real no console para debug
            import traceback
            traceback.print_exc()
            flash(f'Não conseguimos ler esta nota. Verifique se é um XML de NFE válido (Erro: {str(e)})', 'danger')
            return render_template('nfe/importar.html')
    
    return render_template('nfe/importar.html')

@bp.route('/visualizar/<int:id>')
def visualizar(id):
    """Visualiza detalhes de uma nota fiscal"""
    restaurant_id = get_current_restaurant_id()
    nota = NFNota.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    return render_template('nfe/visualizar.html', nota=nota)

@bp.route('/item/<int:id>')
def visualizar_item(id):
    """Visualiza detalhes de um item da nota fiscal"""
    restaurant_id = get_current_restaurant_id()
    # NFItem não tem restaurant_id direto, mas NFNota tem. Join para verificar.
    item = NFItem.query.join(NFNota).filter(NFItem.id == id, NFNota.restaurant_id == restaurant_id).first_or_404()
    return render_template('nfe/item.html', item=item)

def processar_xml_nfe(xml_content):
    """Processa o XML da NF-e e retorna um modelo validado"""
    try:
        # Converter XML para dicionário
        # process_namespaces=True remove namespaces dos nomes das tags para facilitar acesso,
        # MAS apenas se fornecermos o mapa de namespaces para remover (None)
        ns_map = {'http://www.portalfiscal.inf.br/nfe': None}
        xml_dict = xmltodict.parse(xml_content, process_namespaces=True, namespaces=ns_map)
        
        # Função auxiliar para busca recursiva
        def buscar_chave(dados, chave):
            if isinstance(dados, dict):
                for k, v in dados.items():
                    if k == chave:
                        return v
                    if isinstance(v, (dict, list)):
                        res = buscar_chave(v, chave)
                        if res: return res
            elif isinstance(dados, list):
                for item in dados:
                    res = buscar_chave(item, chave)
                    if res: return res
            return None

        # Tentar encontrar infNFe recursivamente
        inf_nfe = buscar_chave(xml_dict, 'infNFe')
        
        if not inf_nfe:
             # Tentar encontrar com maiúsculas/minúsculas diferentes ou namespaces residuais
             for key in xml_dict:
                 if 'infNFe' in str(key):
                     # Se a chave contem infNFe (ex: ns:infNFe)
                    if isinstance(xml_dict[key], dict):
                        inf_nfe = xml_dict[key]
                        break
        
        if not inf_nfe:
            # Dump parcial para debug no log se falhar
            print(f"DEBUG XML KEYS: {list(xml_dict.keys())}")
            raise ValueError("Estrutura da NF-e inválida: Tag 'infNFe' não encontrada.")
            
        # inf_nfe encontrado diretamente
        
        # Extrair chave de acesso
        chave_acesso = None
        if 'nfeProc' in xml_dict and 'protNFe' in xml_dict['nfeProc']:
            prot = xml_dict['nfeProc']['protNFe']['infProt']
            chave_acesso = prot.get('chNFe')
        else:
            # Tentar extrair do attributo Id da infNFe
            chave_id = inf_nfe.get('@Id', '')
            if chave_id.startswith('NFe'):
                chave_acesso = chave_id[3:]
                
        if not chave_acesso:
            # Fallback final
            chave_acesso = "DESCONHECID_" + datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Informações da Nota
        ide = inf_nfe['ide']
        numero = ide['nNF']
        serie = ide['serie']
        data_str = ide.get('dhEmi', ide.get('dEmi'))
        if 'T' in data_str:
            data_emissao = datetime.strptime(data_str.split('T')[0], '%Y-%m-%d')
        else:
            data_emissao = datetime.strptime(data_str, '%Y-%m-%d')
        
        # Informações do Fornecedor (Emitente)
        emit = inf_nfe['emit']
        cnpj = emit.get('CNPJ', emit.get('CPF', ''))
        razao_social = emit['xNome']
        inscricao_estadual = emit.get('IE')
        
        # Informações do Destinatário (Comprador)
        dest = inf_nfe['dest']
        dest_cnpj = dest.get('CNPJ')
        dest_cpf = dest.get('CPF')
        dest_nome = dest.get('xNome')
        
        destinatario_model = NFeDestinatarioModel(
            cnpj=dest_cnpj,
            cpf=dest_cpf,
            xNome=dest_nome or "Consumidor"
        )
        
        # Endereço do Fornecedor
        endereco = None
        cidade = None
        estado = None
        if 'enderEmit' in emit:
            end = emit['enderEmit']
            logradouro = end.get('xLgr', '')
            numero_end = end.get('nro', '')
            bairro = end.get('xBairro', '')
            endereco = f"{logradouro}, {numero_end} - {bairro}"
            cidade = end.get('xMun')
            estado = end.get('UF')
        
        # Valores Totais
        total = inf_nfe['total']['ICMSTot']
        valor_produtos = float(total['vProd'])
        valor_total = float(total['vNF'])
        valor_frete = float(total.get('vFrete', 0))
        valor_seguro = float(total.get('vSeg', 0))
        valor_desconto = float(total.get('vDesc', 0))
        valor_impostos = float(total.get('vIPI', 0)) + float(total.get('vICMS', 0))
        
        # Itens da Nota
        itens_list = []
        det = inf_nfe['det']
        
        # Se tiver apenas um item, xmltodict retorna dict, não lista
        if isinstance(det, dict):
            det = [det]
        
        for item in det:
            num_item = int(item['@nItem'])
            prod = item['prod']
            
            # Extrair informações fiscais (ICMS, IPI)
            icms_valor = 0.0
            icms_aliquota = 0.0
            ipi_valor = 0.0
            ipi_aliquota = 0.0
            
            if 'imposto' in item:
                imposto = item['imposto']
                if 'ICMS' in imposto:
                    # ICMS pode estar em várias tags (ICMS00, ICMS20, etc.)
                    for key, val in imposto['ICMS'].items():
                        if key.startswith('ICMS') and isinstance(val, dict):
                            icms_valor = float(val.get('vICMS', 0))
                            icms_aliquota = float(val.get('pICMS', 0))
                            break
                
                if 'IPI' in imposto:
                     for key, val in imposto['IPI'].items():
                        if key.startswith('IPITrib') and isinstance(val, dict):
                            ipi_valor = float(val.get('vIPI', 0))
                            ipi_aliquota = float(val.get('pIPI', 0))
                            break
            
            item_dict = {
                'nItem': num_item,
                'cProd': prod['cProd'],
                'xProd': prod['xProd'],
                'NCM': prod.get('NCM'),
                'CFOP': prod.get('CFOP'),
                'uCom': prod['uCom'],
                'qCom': float(prod['qCom']),
                'vUnCom': float(prod['vUnCom']),
                'vProd': float(prod['vProd']),
                'icms_valor': icms_valor,
                'icms_aliquota': icms_aliquota,
                'ipi_valor': ipi_valor,
                'ipi_aliquota': ipi_aliquota
            }
            
            itens_list.append(item_dict)
        
        # Criar modelo de fornecedor
        fornecedor_model = NFeFornecedorModel(
            cnpj=cnpj,
            xNome=razao_social,
            IE=inscricao_estadual,
            endereco=endereco,
            cidade=cidade,
            estado=estado
        )
        
        # Criar modelo de itens
        itens_model = [NFeItemModel(**item) for item in itens_list]
        
        # Criar modelo completo da NF-e
        nfe_model = NFeModel(
            chave_acesso=chave_acesso,
            nNF=numero,
            serie=serie,
            data_emissao=data_emissao,
            vProd=valor_produtos,
            vNF=valor_total,
            vFrete=valor_frete,
            vSeg=valor_seguro,
            vDesc=valor_desconto,
            vImp=valor_impostos,
            fornecedor=fornecedor_model,
            destinatario=destinatario_model,
            itens=itens_model
        )
        
        return nfe_model
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ValueError(f"Erro ao processar XML: {str(e)}")

def importar_nfe(nfe_data, xml_content, restaurant_id):
    """Importa os dados da NF-e para o banco de dados"""
    # Verificar/criar fornecedor (no contexto do tenant)
    # Primeiro busca fornecedor pelo CNPJ dentro do tenant
    fornecedor = Fornecedor.query.filter_by(cnpj=nfe_data.fornecedor.cnpj, restaurant_id=restaurant_id).first()
    
    if not fornecedor:
        # Criar novo fornecedor para este tenant
        fornecedor = Fornecedor(
            cnpj=nfe_data.fornecedor.cnpj,
            razao_social=nfe_data.fornecedor.razao_social,
            inscricao_estadual=nfe_data.fornecedor.inscricao_estadual,
            endereco=nfe_data.fornecedor.endereco,
            cidade=nfe_data.fornecedor.cidade,
            estado=nfe_data.fornecedor.estado,
            restaurant_id=restaurant_id
        )
        db.session.add(fornecedor)
        db.session.flush()  # Para obter o ID sem commitar ainda
    
    # Criar registro da nota fiscal
    nota = NFNota(
        chave_acesso=nfe_data.chave_acesso,
        numero=nfe_data.numero,
        serie=nfe_data.serie,
        data_emissao=nfe_data.data_emissao,
        valor_total=nfe_data.valor_total,
        valor_produtos=nfe_data.valor_produtos,
        valor_frete=nfe_data.valor_frete,
        valor_seguro=nfe_data.valor_seguro,
        valor_desconto=nfe_data.valor_desconto,
        valor_impostos=nfe_data.valor_impostos,
        fornecedor_id=fornecedor.id,
        xml_data=xml_content,
        restaurant_id=restaurant_id
    )
    
    db.session.add(nota)
    db.session.flush()  # Para obter o ID da nota sem commitar ainda
    
    alertas_inflacao = []

    # Processar os itens da nota
    for item_data in nfe_data.itens:
        # Verificar/criar produto pelo código E tenant
        produto = Produto.query.filter_by(codigo=item_data.codigo, restaurant_id=restaurant_id).first()
        
        if produto:
            # Produto já existe: Verificar Inflação
            preco_antigo = float(produto.preco_unitario or 0)
            novo_preco = float(item_data.valor_unitario)
            
            if preco_antigo > 0:
                variacao = ((novo_preco - preco_antigo) / preco_antigo) * 100
                
                # Se variação > 10%, registrar alerta
                if variacao > 10.0:
                    produto.ultimo_custo_anterior = preco_antigo
                    produto.variacao_preco_pct = variacao
                    produto.data_alerta_inflacao = datetime.now()
                    alertas_inflacao.append(f"{produto.nome} (+{variacao:.0f}%)")
            
            # Atualizar preço de custo (sempre atualiza para o mais recente)
            produto.preco_unitario = novo_preco
            produto.nome = item_data.descricao # Atualiza nome também caso mude
            
        else:
            # Criar novo produto
            produto = Produto(
                codigo=item_data.codigo,
                nome=item_data.descricao,
                unidade=item_data.unidade,
                preco_unitario=item_data.valor_unitario,
                fornecedor_id=fornecedor.id,
                restaurant_id=restaurant_id
            )
            db.session.add(produto)
            db.session.flush()  # Para obter o ID sem commitar ainda
        
        # Criar item da nota fiscal
        item = NFItem(
            nf_nota_id=nota.id,
            produto_id=produto.id,
            num_item=item_data.num_item,
            quantidade=item_data.quantidade,
            valor_unitario=item_data.valor_unitario,
            valor_total=item_data.valor_total,
            unidade_medida=item_data.unidade,
            cfop=item_data.cfop,
            ncm=item_data.ncm,
            percentual_icms=item_data.icms_aliquota,
            valor_icms=item_data.icms_aliquota, # Corrigido mapeamento (era icms_valor? não, percentual e valor são separados no modelo, verificar correspondencia)
            # No código anterior: valor_icms=item_data.icms_valor
            # Aqui estava item_data.icms_aliquota. Vou corrigir para valor.
            percentual_ipi=item_data.ipi_aliquota,
            valor_ipi=item_data.ipi_valor
        )
        # Correção do campo valor_icms
        item.valor_icms = item_data.icms_valor
        
        db.session.add(item)
    
    # Commit todas as alterações
    db.session.commit()
    
    # Notificar sobre Inflação
    if alertas_inflacao:
        msg = f"⚠️ Alerta de Inflação: {len(alertas_inflacao)} itens subiram >10%: " + ", ".join(alertas_inflacao[:3])
        if len(alertas_inflacao) > 3:
            msg += "..."
        flash(msg, 'warning')
    
    return nota

# API Endpoints
@bp.route('/api/notas')
def api_listar_notas():
    """API para listar notas fiscais (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])

    notas = NFNota.query.filter_by(restaurant_id=restaurant_id).order_by(NFNota.data_emissao.desc()).limit(100).all()
    return jsonify([
        {
            'id': n.id,
            'numero': n.numero,
            'serie': n.serie,
            'data_emissao': n.data_emissao.strftime('%d/%m/%Y'),
            'valor_total': float(n.valor_total),
            'fornecedor': n.fornecedor.razao_social
        } for n in notas
    ])

@bp.route('/api/nota/<int:id>')
def api_detalhes_nota(id):
    """API para obter detalhes de uma nota fiscal (JSON)"""
    restaurant_id = get_current_restaurant_id()
    nota = NFNota.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    return jsonify({
        'id': nota.id,
        'chave_acesso': nota.chave_acesso,
        'numero': nota.numero,
        'serie': nota.serie,
        'data_emissao': nota.data_emissao.strftime('%d/%m/%Y'),
        'valor_total': float(nota.valor_total),
        'valor_produtos': float(nota.valor_produtos),
        'valor_impostos': float(nota.valor_impostos),
        'fornecedor': {
            'id': nota.fornecedor.id,
            'razao_social': nota.fornecedor.razao_social,
            'cnpj': nota.fornecedor.cnpj
        },
        'itens': [
            {
                'id': item.id,
                'num_item': item.num_item,
                'produto': {
                    'id': item.produto.id,
                    'codigo': item.produto.codigo,
                    'nome': item.produto.nome
                },
                'quantidade': item.quantidade,
                'valor_unitario': float(item.valor_unitario),
                'valor_total': float(item.valor_total)
            } for item in nota.itens
        ]
    })
