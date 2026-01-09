
import unittest
import io
import os
from app import create_app, db
from app.models.modelo_produto import Produto
from app.models.modelo_restaurante import Restaurante
from datetime import datetime

class TestSprint5(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Ensure user is logged in
        self.client.post('/auth/login', data={'email': 'admin@teste.com', 'senha': 'password123'}, follow_redirects=True)

    def tearDown(self):
        self.ctx.pop()

    def test_inflation_alert(self):
        """Test if price increase > 10% triggers alert and updates DB"""
        
        # 1. Create a product with price 10.00
        prod = Produto.query.filter_by(codigo='12345').first()
        if not prod:
            prod = Produto(codigo='12345', nome='Teste Inflacao', unidade='UN', preco_unitario=10.00, restaurant_id=1)
            db.session.add(prod)
        else:
            prod.preco_unitario = 10.00
            prod.variacao_preco_pct = None
        db.session.commit()
        
        # 2. Upload XML with price 12.00 (+20%)
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35210100000000000000550010000000011000000001" version="4.00">
      <ide>
        <cUF>35</cUF>
        <cNF>00000001</cNF>
        <natOp>Venda</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>999</nNF>
        <dhEmi>2023-10-25T14:30:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <idDest>1</idDest>
        <cMunFG>3550308</cMunFG>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>1</cDV>
        <tpAmb>2</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>1</indFinal>
        <indPres>1</indPres>
        <procEmi>0</procEmi>
        <verProc>1.0</verProc>
      </ide>
      <emit>
        <CNPJ>00000000000000</CNPJ>
        <xNome>FORNECEDOR TESTE</xNome>
        <enderEmit>
          <xLgr>RUA TESTE</xLgr>
          <nro>123</nro>
          <xBairro>BAIRRO</xBairro>
          <cMun>3550308</cMun>
          <xMun>SAO PAULO</xMun>
          <UF>SP</UF>
        </enderEmit>
      </emit>
      <dest>
        <CNPJ>12345678000199</CNPJ>
        <xNome>RESTAURANTE TESTE</xNome>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>12345</cProd>
          <cEAN>SEM GTIN</cEAN>
          <xProd>Teste Inflacao</xProd>
          <NCM>00000000</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>1.0000</qCom>
          <vUnCom>12.0000</vUnCom>
          <vProd>12.00</vProd>
          <cEANTrib>SEM GTIN</cEANTrib>
          <uTrib>UN</uTrib>
          <qTrib>1.0000</qTrib>
          <vUnTrib>12.0000</vUnTrib>
          <indTot>1</indTot>
        </prod>
        <imposto>
          <ICMS>
             <ICMS00>
                <orig>0</orig>
                <CST>00</CST>
                <modBC>3</modBC>
                <vBC>12.00</vBC>
                <pICMS>18.00</pICMS>
                <vICMS>2.16</vICMS>
             </ICMS00>
          </ICMS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vBC>12.00</vBC>
          <vICMS>2.16</vICMS>
          <vICMSDeson>0.00</vICMSDeson>
          <vFCP>0.00</vFCP>
          <vBCST>0.00</vBCST>
          <vST>0.00</vST>
          <vFCPST>0.00</vFCPST>
          <vFCPSTRet>0.00</vFCPSTRet>
          <vProd>12.00</vProd>
          <vFrete>0.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vII>0.00</vII>
          <vIPI>0.00</vIPI>
          <vIPIDevol>0.00</vIPIDevol>
          <vPIS>0.00</vPIS>
          <vCOFINS>0.00</vCOFINS>
          <vOutro>0.00</vOutro>
          <vNF>12.00</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>"""
        
        data = {
            'xml_file': (io.BytesIO(xml_content.encode('utf-8')), 'test_inflation.xml')
        }
        
        response = self.client.post('/nfe/importar', data=data, content_type='multipart/form-data', follow_redirects=True)
        html = response.data.decode('utf-8')
        
        # 3. Assert Response contains Alert
        if "Alerta de Inflação" in html:
            print("✅ PASSED: Inflation Alert displayed.")
        else:
            print("❌ FAILED: Inflation Alert NOT found in HTML.")
            
        # 4. Assert DB state
        prod = Produto.query.filter_by(codigo='12345').first()
        if prod.variacao_preco_pct and prod.variacao_preco_pct > 19.9:
             print(f"✅ PASSED: DB updated with variation {prod.variacao_preco_pct:.2f}%")
        else:
             print(f"❌ FAILED: DB variation not correct. Val: {prod.variacao_preco_pct}")

    def test_resilience(self):
        """Test resilience against bad XMLs"""
        bad_xmls = [
            ("empty", ""),
            ("garbage", "<xml>Trash</xml>"),
            ("missing_tags", "<nfeProc><NFe></NFe></nfeProc>"),
            ("wrong_ext", (io.BytesIO(b"content"), "test.txt")),
        ]
        
        for name, content in bad_xmls:
            if isinstance(content, tuple):
                 data = {'xml_file': content}
            else:
                 data = {'xml_file': (io.BytesIO(content.encode('utf-8') if isinstance(content, str) else content), 'test.xml')}
            
            try:
                response = self.client.post('/nfe/importar', data=data, content_type='multipart/form-data', follow_redirects=True)
                if response.status_code == 200:
                     print(f"✅ PASSED: Handled bad XML '{name}' gracefully.")
                else:
                     print(f"❌ FAILED: Bad XML '{name}' caused status {response.status_code}")
            except Exception as e:
                print(f"❌ FAILED: Bad XML '{name}' caused Exception: {e}")

if __name__ == "__main__":
    unittest.main()
