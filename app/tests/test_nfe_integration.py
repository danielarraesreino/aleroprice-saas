import unittest
from app import create_app, db
from app.models.usuario import Usuario
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_produto import Produto
from app.models.modelo_estoque import EstoqueMovimentacao
from app.models.modelo_nfe import NFNota
from werkzeug.datastructures import FileStorage
from io import BytesIO

class NFeIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create Restaurant
        self.restaurante = Restaurante(
            nome='Restaurante Teste QA',
            cnpj='99999999000199',
            endereco='Rua QA, 999',
            telefone='11988888888'
        )
        db.session.add(self.restaurante)
        db.session.commit()
        
        # Create User
        self.usuario = Usuario(
            nome='QA Tester',
            email='qa@teste.com',
            senha='passwordqa',
            tipo='admin',
            restaurant_id=self.restaurante.id
        )
        db.session.add(self.usuario)
        db.session.commit()
        
        self.client = self.app.test_client()
        # Login
        self.client.post('/auth/login', data={
            'email': 'qa@teste.com',
            'senha': 'passwordqa'
        })
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        
    def test_nfe_upload_and_stock_update(self):
        # XML Sample
        xml_content = f"""
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
            <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
                <infNFe Id="NFe35230112345678000199550010000001001000000100" versao="4.00">
                    <ide>
                        <cUF>35</cUF>
                        <cNF>000000100</cNF>
                        <natOp>Venda</natOp>
                        <mod>55</mod>
                        <serie>1</serie>
                        <nNF>100</nNF>
                        <dhEmi>2023-01-01T10:00:00-03:00</dhEmi>
                        <tpNF>1</tpNF>
                        <idDest>1</idDest>
                        <cMunFG>3550308</cMunFG>
                        <tpImp>1</tpImp>
                        <tpEmis>1</tpEmis>
                        <cDV>0</cDV>
                        <tpAmb>2</tpAmb>
                        <finNFe>1</finNFe>
                        <indFinal>1</indFinal>
                        <indPres>1</indPres>
                        <procEmi>0</procEmi>
                        <verProc>1.0</verProc>
                    </ide>
                    <emit>
                        <CNPJ>12345678000199</CNPJ>
                        <xNome>Fornecedor QA Ltda</xNome>
                        <enderEmit>
                            <xLgr>Rua Fornecedor</xLgr>
                            <nro>100</nro>
                            <xBairro>Centro</xBairro>
                            <xMun>Sao Paulo</xMun>
                            <UF>SP</UF>
                            <CEP>01001000</CEP>
                            <cPais>1058</cPais>
                            <xPais>BRASIL</xPais>
                        </enderEmit>
                        <IE>123456789012</IE>
                        <CRT>3</CRT>
                    </emit>
                    <dest>
                        <CNPJ>99999999000199</CNPJ>
                        <xNome>Restaurante Teste QA</xNome>
                        <enderDest>
                            <xLgr>Rua QA</xLgr>
                            <nro>999</nro>
                            <xBairro>Bairro QA</xBairro>
                            <xMun>Sao Paulo</xMun>
                            <UF>SP</UF>
                            <CEP>01001001</CEP>
                            <cPais>1058</cPais>
                            <xPais>BRASIL</xPais>
                        </enderDest>
                        <indIEDest>1</indIEDest>
                        <IE>999999999999</IE>
                    </dest>
                    <det nItem="1">
                        <prod>
                            <cProd>PROD-QA-001</cProd>
                            <cEAN>SEM GTIN</cEAN>
                            <xProd>Produto Teste QA</xProd>
                            <NCM>21069090</NCM>
                            <CFOP>5102</CFOP>
                            <uCom>KG</uCom>
                            <qCom>10.0000</qCom>
                            <vUnCom>50.0000</vUnCom>
                            <vProd>500.00</vProd>
                            <cEANTrib>SEM GTIN</cEANTrib>
                            <uTrib>KG</uTrib>
                            <qTrib>10.0000</qTrib>
                            <vUnTrib>50.0000</vUnTrib>
                            <indTot>1</indTot>
                        </prod>
                        <imposto>
                            <ICMS>
                                <ICMS00>
                                    <orig>0</orig>
                                    <CST>00</CST>
                                    <modBC>3</modBC>
                                    <vBC>500.00</vBC>
                                    <pICMS>18.00</pICMS>
                                    <vICMS>90.00</vICMS>
                                </ICMS00>
                            </ICMS>
                        </imposto>
                    </det>
                    <total>
                        <ICMSTot>
                            <vBC>500.00</vBC>
                            <vICMS>90.00</vICMS>
                            <vICMSDeson>0.00</vICMSDeson>
                            <vFCP>0.00</vFCP>
                            <vBCST>0.00</vBCST>
                            <vST>0.00</vST>
                            <vFCPST>0.00</vFCPST>
                            <vFCPSTRet>0.00</vFCPSTRet>
                            <vProd>500.00</vProd>
                            <vFrete>0.00</vFrete>
                            <vSeg>0.00</vSeg>
                            <vDesc>0.00</vDesc>
                            <vII>0.00</vII>
                            <vIPI>0.00</vIPI>
                            <vIPIDevol>0.00</vIPIDevol>
                            <vPIS>0.00</vPIS>
                            <vCOFINS>0.00</vCOFINS>
                            <vOutro>0.00</vOutro>
                            <vNF>500.00</vNF>
                            <vTotTrib>0.00</vTotTrib>
                        </ICMSTot>
                    </total>
                </infNFe>
            </NFe>
        </nfeProc>
        """
        
        # Prepare file upload
        data = {
            'xml_file': (BytesIO(xml_content.encode('utf-8')), 'nota_qa.xml')
        }
        
        # Post to import
        response = self.client.post('/nfe/importar', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Nota fiscal 100/1 importada com sucesso!', response.data)
        
        # Verify Product Created
        produto = Produto.query.filter_by(codigo='PROD-QA-001', restaurant_id=self.restaurante.id).first()
        self.assertIsNotNone(produto)
        self.assertEqual(produto.nome, 'Produto Teste QA')
        self.assertEqual(produto.estoque_atual, 10.0) # 10 units imported
        
        # Verify Stock Movement
        movimentacao = EstoqueMovimentacao.query.filter_by(produto_id=produto.id).first()
        self.assertIsNotNone(movimentacao)
        self.assertEqual(movimentacao.quantidade, 10.0)
        self.assertEqual(movimentacao.tipo, 'entrada')
        self.assertEqual(movimentacao.restaurant_id, self.restaurante.id) # THIS SHOULD FAIL IF BUG EXISTS
        
if __name__ == '__main__':
    unittest.main()
