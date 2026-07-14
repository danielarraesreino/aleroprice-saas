# Instruções para Gerar o PDF do Guia do Usuário

## 📋 Checklist de Screenshots

Salve os screenshots com os nomes exatos abaixo na pasta `/home/dan/Área de Trabalho/AleroPriceSaaS/`:

### 1.png - Dashboard Principal
- **URL:** http://localhost:5000/index
- **O que mostrar:** Visão geral com cards de faturamento, custo e lucro
- **Dica:** Certifique-se de que há dados para exibir

### 2.png - Página de Importação
- **URL:** http://localhost:5000/previsao/historico/importar
- **O que mostrar:** Área de upload (dropzone) e lista de recursos inteligentes
- **Dica:** Capture a tela completa mostrando o formulário

### 3.png - Mensagem de Sucesso
- **Como tirar:** Após fazer upload de `vendas_teste.csv`
- **O que mostrar:** Mensagem verde com estatísticas (X linhas → Y registros)
- **Dica:** Capture logo após clicar em "Importar Dados"

### 4.png - Histórico de Vendas
- **URL:** http://localhost:5000/previsao/historico
- **O que mostrar:** Tabela com vendas agregadas por data e produto
- **Dica:** Mostre pelo menos 5-10 registros

### 5.png - Dashboard com Cards de Lucro
- **URL:** http://localhost:5000/index
- **O que mostrar:** Mesma tela do 1.png, mas com foco nos cards de lucro
- **Dica:** Pode ser a mesma imagem do 1.png

### 6.png - Gestão de Estoque
- **URL:** http://localhost:5000/estoque
- **O que mostrar:** Lista de produtos com saldos e botões de ação
- **Dica:** Mostre produtos com estoque atualizado

### 7.png - Dashboard de Previsão
- **URL:** http://localhost:5000/previsao/index
- **O que mostrar:** Gráficos de tendência e estatísticas de previsão
- **Dica:** Capture a visão geral do módulo de previsão

### 8.png - Fluxo Completo ou Menu
- **Opção A:** Montagem mostrando: Upload → Preview → Sucesso → Dashboard
- **Opção B:** Screenshot do menu lateral mostrando todos os módulos
- **Dica:** Use uma ferramenta de edição para criar uma montagem

---

## 🚀 Como Gerar o PDF

### Método 1: Pandoc (Recomendado)

```bash
# Instalar Pandoc (se não tiver)
sudo apt-get install pandoc wkhtmltopdf

# Gerar PDF
cd /home/dan/Área\ de\ Trabalho/AleroPriceSaaS
pandoc GUIA_USUARIO.md -o GUIA_USUARIO.pdf \
  --pdf-engine=wkhtmltopdf \
  --toc \
  --toc-depth=2 \
  -V geometry:margin=1in \
  -V fontsize=11pt
```

### Método 2: Typora (GUI)

1. Abra `GUIA_USUARIO.md` no Typora
2. File → Export → PDF
3. Salve como `GUIA_USUARIO.pdf`

### Método 3: Online

1. Acesse: https://www.markdowntopdf.com/
2. Faça upload de `GUIA_USUARIO.md`
3. Faça upload das 8 imagens (1.png até 8.png)
4. Clique em "Convert"
5. Baixe o PDF gerado

### Método 4: VSCode + Extension

1. Instale a extensão "Markdown PDF"
2. Abra `GUIA_USUARIO.md`
3. Ctrl+Shift+P → "Markdown PDF: Export (pdf)"

---

## ⚠️ Importante

- **Todas as 8 imagens devem estar na mesma pasta** que o GUIA_USUARIO.md
- **Nomes devem ser exatos:** 1.png, 2.png, 3.png, etc.
- **Formato PNG recomendado** (mas JPG também funciona)
- **Resolução mínima:** 1280x720 para boa qualidade no PDF

---

## 🎨 Dicas de Screenshot

### Para Windows:
- Use `Win + Shift + S` para captura de área
- Ou use Snipping Tool

### Para Linux:
- Use `gnome-screenshot -a` para captura de área
- Ou use Flameshot: `flameshot gui`

### Para Mac:
- Use `Cmd + Shift + 4` para captura de área

---

## ✅ Verificação Final

Antes de gerar o PDF, verifique:

- [ ] Servidor está rodando (`python3 run.py`)
- [ ] Todas as 8 imagens foram salvas
- [ ] Nomes das imagens estão corretos (1.png, 2.png, etc.)
- [ ] Imagens estão na mesma pasta que GUIA_USUARIO.md
- [ ] Arquivo GUIA_USUARIO.md está atualizado

---

*Após gerar o PDF, você terá um guia completo e profissional para seus usuários!*
