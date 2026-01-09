
import unittest
from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
from flask_login import login_user

class TestNFEShielding(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_cnpj_mismatch_blocking(self):
        # 1. Setup Restaurant and User
        # Ensure Restaurant 1 has a known CNPJ
        rest = Restaurante.query.get(1)
        if not rest:
            print("Skipping: Restaurant 1 not found")
            return
        
        # Set a known CNPJ for the restaurant
        rest.cnpj = "12345678000199"
        db.session.commit()
        
        # Determine a user for this restaurant (e.g. admin@teste.com)
        user = Usuario.query.filter_by(email="admin@teste.com").first()
        if not user:
            print("Skipping: Admin user not found")
            return

        # 2. Craft XML with DIFFERENT destination CNPJ
        # Restaurant is 12345678000199, XML will be 99999999000199
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc version="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
    <NFe>
        <infNFe Id="NFe35220207374789000190550010000030581000030588" version="4.00">
            <ide>
                <cUF>35</cUF>
                <cNF>00003058</cNF>
                <natOp>VENDAS DE MERCADORIAS</natOp>
                <mod>55</mod>
                <serie>1</serie>
                <nNF>999999</nNF>
                <dhEmi>2026-01-01T12:00:00-03:00</dhEmi>
                <tpNF>1</tpNF>
                <idDest>1</idDest>
                <cMunFG>3509502</cMunFG>
                <tpImp>1</tpImp>
                <tpEmis>1</tpEmis>
                <cDV>8</cDV>
                <tpAmb>1</tpAmb>
                <finNFe>1</finNFe>
                <indFinal>0</indFinal>
                <indPres>9</indPres>
                <procEmi>0</procEmi>
                <verProc>4.00</verProc>
            </ide>
            <emit>
                <CNPJ>07374789000190</CNPJ>
                <xNome>FORNECEDOR TESTE SHIELD</xNome>
                <enderEmit>
                    <xLgr>RUA TESTE</xLgr>
                    <nro>123</nro>
                    <xBairro>BAIRRO</xBairro>
                    <cMun>3509502</cMun>
                    <xMun>CAMPINAS</xMun>
                    <UF>SP</UF>
                    <CEP>13000000</CEP>
                </enderEmit>
                <IE>123456789</IE>
                <CRT>3</CRT>
            </emit>
            <dest>
                <CNPJ>99999999000199</CNPJ> 
                <xNome>RESTAURANTE OUTRO</xNome>
                <enderDest>
                    <xLgr>AVENIDA OUTRA</xLgr>
                    <nro>999</nro>
                    <xBairro>CENTRO</xBairro>
                    <cMun>3509502</cMun>
                    <xMun>CAMPINAS</xMun>
                    <UF>SP</UF>
                    <CEP>13000000</CEP>
                </enderDest>
            </dest>
            <det nItem="1">
                <prod>
                    <cProd>PROD-SHIELD-01</cProd>
                    <cEAN>SEM GTIN</cEAN>
                    <xProd>PRODUTO TESTE SHIELD</xProd>
                    <NCM>21039091</NCM>
                    <CFOP>5102</CFOP>
                    <uCom>UN</uCom>
                    <qCom>1.0000</qCom>
                    <vUnCom>100.0000</vUnCom>
                    <vProd>100.00</vProd>
                    <cEANTrib>SEM GTIN</cEANTrib>
                    <uTrib>UN</uTrib>
                    <qTrib>1.0000</qTrib>
                    <vUnTrib>100.0000</vUnTrib>
                    <indTot>1</indTot>
                </prod>
                <imposto>
                    <ICMS>
                        <ICMS00>
                            <orig>0</orig>
                            <CST>00</CST>
                            <modBC>3</modBC>
                            <vBC>100.00</vBC>
                            <pICMS>18.00</pICMS>
                            <vICMS>18.00</vICMS>
                        </ICMS00>
                    </ICMS>
                </imposto>
            </det>
            <total>
                <ICMSTot>
                    <vBC>100.00</vBC>
                    <vICMS>18.00</vICMS>
                    <vICMSDeson>0.00</vICMSDeson>
                    <vFCP>0.00</vFCP>
                    <vBCST>0.00</vBCST>
                    <vST>0.00</vST>
                    <vFCPST>0.00</vFCPST>
                    <vFCPSTRet>0.00</vFCPSTRet>
                    <vProd>100.00</vProd>
                    <vFrete>0.00</vFrete>
                    <vSeg>0.00</vSeg>
                    <vDesc>0.00</vDesc>
                    <vII>0.00</vII>
                    <vIPI>0.00</vIPI>
                    <vIPIDevol>0.00</vIPIDevol>
                    <vPIS>0.00</vPIS>
                    <vCOFINS>0.00</vCOFINS>
                    <vOutro>0.00</vOutro>
                    <vNF>100.00</vNF>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
</nfeProc>
"""
        
        # 3. Login
        with self.client:
            self.client.post('/auth/login', data={'email': 'admin@teste.com', 'senha': 'password123'}, follow_redirects=True)
            
            # 4. Upload XML
            data = {
                'xml_file': (io.BytesIO(xml_content.encode('utf-8')), 'test_shield.xml')
            }
            response = self.client.post('/nfe/importar', data=data, content_type='multipart/form-data', follow_redirects=True)
            
            # 5. Check response
            response_text = response.data.decode('utf-8')
            
            if "Bloqueio de Segurança" in response_text:
                print("✅ PASSED: Shield blocked XML with wrong CNPJ.")
            else:
                print("❌ FAILED: Shield did NOT block XML.")
                if "importada com sucesso" in response_text:
                    print("--> XML was imported despite mismatch!")
                elif "Erro" in response_text or "Exception" in response_text:
                    print(f"--> Another error occurred: {response_text[:200]}...")
                
import io

if __name__ == "__main__":
    unittest.main()
