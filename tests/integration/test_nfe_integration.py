"""Teste de integração da importação de NF-e (XML) e atualização de estoque.

Migrado de app/tests/test_nfe_integration.py para a suíte principal, usando as
fixtures padrão (auth_client, restaurant) em vez de unittest + app próprio.
"""
from io import BytesIO

from app.models.modelo_produto import Produto
from app.models.modelo_estoque import EstoqueMovimentacao


def test_nfe_upload_and_stock_update(auth_client, restaurant):
    xml_content = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
    <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
        <infNFe Id="NFe35230112345678000199550010000001001000000100" versao="4.00">
            <ide>
                <cUF>35</cUF><cNF>000000100</cNF><natOp>Venda</natOp><mod>55</mod>
                <serie>1</serie><nNF>100</nNF><dhEmi>2023-01-01T10:00:00-03:00</dhEmi>
                <tpNF>1</tpNF><idDest>1</idDest><cMunFG>3550308</cMunFG><tpImp>1</tpImp>
                <tpEmis>1</tpEmis><cDV>0</cDV><tpAmb>2</tpAmb><finNFe>1</finNFe>
                <indFinal>1</indFinal><indPres>1</indPres><procEmi>0</procEmi><verProc>1.0</verProc>
            </ide>
            <emit>
                <CNPJ>12345678000199</CNPJ><xNome>Fornecedor QA Ltda</xNome>
                <enderEmit>
                    <xLgr>Rua Fornecedor</xLgr><nro>100</nro><xBairro>Centro</xBairro>
                    <xMun>Sao Paulo</xMun><UF>SP</UF><CEP>01001000</CEP><cPais>1058</cPais><xPais>BRASIL</xPais>
                </enderEmit>
                <IE>123456789012</IE><CRT>3</CRT>
            </emit>
            <dest>
                <CNPJ>{restaurant.cnpj}</CNPJ><xNome>Restaurante Teste</xNome>
                <enderDest>
                    <xLgr>Rua QA</xLgr><nro>999</nro><xBairro>Bairro QA</xBairro>
                    <xMun>Sao Paulo</xMun><UF>SP</UF><CEP>01001001</CEP><cPais>1058</cPais><xPais>BRASIL</xPais>
                </enderDest>
                <indIEDest>1</indIEDest><IE>999999999999</IE>
            </dest>
            <det nItem="1">
                <prod>
                    <cProd>PROD-QA-001</cProd><cEAN>SEM GTIN</cEAN><xProd>Produto Teste QA</xProd>
                    <NCM>21069090</NCM><CFOP>5102</CFOP><uCom>KG</uCom><qCom>10.0000</qCom>
                    <vUnCom>50.0000</vUnCom><vProd>500.00</vProd><cEANTrib>SEM GTIN</cEANTrib>
                    <uTrib>KG</uTrib><qTrib>10.0000</qTrib><vUnTrib>50.0000</vUnTrib><indTot>1</indTot>
                </prod>
                <imposto>
                    <ICMS>
                        <ICMS00>
                            <orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>500.00</vBC>
                            <pICMS>18.00</pICMS><vICMS>90.00</vICMS>
                        </ICMS00>
                    </ICMS>
                </imposto>
            </det>
            <total>
                <ICMSTot>
                    <vBC>500.00</vBC><vICMS>90.00</vICMS><vICMSDeson>0.00</vICMSDeson>
                    <vFCP>0.00</vFCP><vBCST>0.00</vBCST><vST>0.00</vST><vFCPST>0.00</vFCPST>
                    <vFCPSTRet>0.00</vFCPSTRet><vProd>500.00</vProd><vFrete>0.00</vFrete>
                    <vSeg>0.00</vSeg><vDesc>0.00</vDesc><vII>0.00</vII><vIPI>0.00</vIPI>
                    <vIPIDevol>0.00</vIPIDevol><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS>
                    <vOutro>0.00</vOutro><vNF>500.00</vNF><vTotTrib>0.00</vTotTrib>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
</nfeProc>"""

    data = {'xml_file': (BytesIO(xml_content.encode('utf-8')), 'nota_qa.xml')}
    resp = auth_client.post('/nfe/importar', data=data,
                            content_type='multipart/form-data',
                            follow_redirects=True)
    assert resp.status_code == 200
    assert b'Nota fiscal 100/1 importada com sucesso!' in resp.data

    produto = Produto.query.filter_by(codigo='PROD-QA-001',
                                      restaurant_id=restaurant.id).first()
    assert produto is not None
    assert produto.nome == 'Produto Teste QA'
    assert produto.estoque_atual == 10.0

    movimento = EstoqueMovimentacao.query.filter_by(produto_id=produto.id).first()
    assert movimento is not None
    assert movimento.quantidade == 10.0
    assert movimento.tipo == 'entrada'
    assert movimento.restaurant_id == restaurant.id


def test_nfe_ocr_import(session, restaurant):
    """Importa o JSON extraído pelo OCR (NVIDIA Vision) e atualiza estoque.

    Não depende da API externa: exercita só o caminho `importar_nfe_ocr` com um
    resultado de OCR pronto, validando que produto/NFItem/movimentação são
    criados com os campos corretos do modelo.
    """
    from app.routes.nfe.views import importar_nfe_ocr
    from app.models.modelo_produto import Produto
    from app.models.modelo_nfe import NFItem
    from app.models.modelo_estoque import EstoqueMovimentacao

    ocr_data = {
        'fornecedor': 'Supermercado OCR LTDA',
        'cnpj': '12.345.678/0001-90',
        'numero_nota': '555',
        'data_emissao': '2026-07-09',
        'valor_total': 50.0,
        'itens': [
            {
                'codigo': 'OCR-1',
                'descricao': 'Arroz 5kg',
                'quantidade': 2,
                'unidade': 'UN',
                'valor_unitario': 25.0,
                'valor_total': 50.0,
            },
        ],
    }

    nota = importar_nfe_ocr(ocr_data, 'foto.jpg', restaurant.id)
    nota.atualizar_estoque()

    produto = session.query(Produto).filter_by(
        codigo='OCR-1', restaurant_id=restaurant.id).first()
    item = session.query(NFItem).filter_by(nf_nota_id=nota.id).first()
    mov = session.query(EstoqueMovimentacao).filter_by(
        produto_id=produto.id).first()

    assert produto is not None
    assert produto.nome == 'Arroz 5kg'
    assert float(produto.preco_unitario) == 25.0
    assert float(produto.estoque_atual) == 2.0
    assert item.unidade_medida == 'UN'
    assert mov.tipo == 'entrada'
    assert float(mov.quantidade) == 2.0
    assert mov.restaurant_id == restaurant.id
