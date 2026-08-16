# Ferramentas de imagem — o que dá pra usar de graça

Critério desta lista: **cota real, não promessa de marketing**. Cada entrada
responde quatro perguntas que decidem se serve pra este projeto:

1. Quantas imagens por dia antes de pedir cartão
2. Se dá pra usar comercialmente (as prévias são material de venda)
3. Se tem MCP — se sim, eu gero daqui, em lote; se não, é você colando prompt
4. Se faz upscale ou edição (consertar sai mais barato que regerar)

---

## O que estamos usando hoje

### Higgsfield — **em uso, é o melhor que temos**
- **Cota:** 100 créditos no plano Plus. **Imagem custa 0,12** → ~800 imagens.
- **Vídeo custa 65 por 10 segundos** → os 90s pedidos dariam ~585 créditos.
- **MCP: sim.** É o único que roda em lote daqui. As 31 imagens dos 23 bares
  saíram assim, e custaram 3,7 créditos.
- **Extras que ainda não usamos:** `upscale_image` (resolve resolução sem
  gastar geração nova), `remove_background`, `outpaint_image` (estende a foto
  pras bordas — útil pra transformar 4:3 em 16:10 sem cortar).
- Modelo que funcionou: `soul_location`. Também tem `soul_2`, `nano_banana_pro`
  (4K e texto), `flux_2`, `seedream`.

### Unsplash — **conectado, ilimitado**
- Foto real, licença livre, sem cota.
- **Bom em:** ambiente, bebida, balcão, cerveja.
- **Ruim em:** comida brasileira específica — buscar "caipirinha" devolveu um
  limão numa tábua. Prato de boteco não existe em banco internacional.
- MCP: sim.

### Gamma — **1 imagem restante**
- 70 créditos por imagem, restam 70. A capa do Bar do Zé saiu dele e ficou
  ótima. Guardar pra quando precisar de uma imagem só, muito boa.

---

## O que vale abrir conta (nenhum pede cartão)

### Leonardo.ai — **a mais generosa**
- **150 créditos por dia**, ~25 a 50 imagens diárias.
- Uso comercial permitido no plano grátis (licença não exclusiva; a Leonardo
  mantém direitos).
- MCP: não. É você gerando na interface e salvando.
- **Por que vale:** 25–50 imagens/dia cobre os 6 bares-vitrine numa tarde, sem
  gastar crédito do Higgsfield.

### Ideogram
- **10 créditos toda sexta** (~40 imagens/semana), sem marca d'água.
- Uso comercial explicitamente permitido — raro em plano grátis.
- Forte em **texto dentro da imagem**, que nenhum outro acerta. Serviria pra
  material de campanha (cartaz, story), não pra foto de bar.

### Recraft
- **30 créditos por dia**, 2 imagens por prompt, 3 uploads/dia.
- Uso comercial permitido, exceto revenda em banco de imagens.
- Também disponível **dentro do Higgsfield** (`recraft_v4_1`) — dá pra testar
  por lá primeiro, gastando 0,12.

### Krea
- 100 unidades por dia.
- **Uso comercial NÃO incluído no grátis.** Para prévia de venda, isso
  desqualifica — a imagem vai numa página comercial.

### Bing / Copilot Image Creator
- Grátis, DALL·E 3, sem cartão.
- Bom pra teste rápido de conceito. Qualidade fotográfica abaixo do Higgsfield.

---

## O que descartamos, e por quê

| Ferramenta | Motivo |
|---|---|
| **Google Places API** | A conta exige depósito de **R$ 200** pra ativar. Chave criada e API ativada, mas `PERMISSION_DENIED`. |
| **Instagram / Instaloader** | Vetado. Cobre 22 de 75 leads, arrisca a conta pessoal, e é foto de terceiro em página comercial. |
| **Hugging Face Spaces** | Tem FLUX e Qwen de graça, mas o `invoke` está desabilitado no conector (`gradio=none`). Destravável se valer. |
| **Openverse** | Sem chave, mas só 7 a 14 resultados CC0 por busca. |
| **Wikimedia Commons** | Sem chave (precisa `gsrnamespace=6`), qualidade irregular. Tapa-buraco de galeria. |

---

## A ordem que eu seguiria

1. **Higgsfield** pra tudo que precisa de lote e consistência — é o único
   automatizável, e a 0,12 por imagem os 100 créditos não acabam tão cedo.
2. **`upscale_image` do próprio Higgsfield** antes de gerar de novo: as capas
   saem em 2048px e o upscale custa menos que uma geração nova.
3. **Leonardo.ai** quando precisar de volume manual sem gastar crédito.
4. **Unsplash** pra ambiente genérico — foto real ganha de imagem gerada quando
   o assunto é bar cheio, balcão, cerveja.
5. **Ideogram** só se precisar de texto dentro da imagem.

## O aprendizado que vale mais que a ferramenta

O que definiu a qualidade não foi o modelo — foi o prompt vindo do YAML do bar.
A receita do tema `neon-noite` pedia "neon magenta refletindo em superfícies
escuras, contraste alto" e o modelo devolveu uma caverna roxa onde não se via o
bar. Trocada por "luz quente de trabalho no balcão, neon só como acento nas
bordas, ambiente legível e bem exposto", a mesma ferramenta entregou uma
hamburgueria reconhecível.

Antes de trocar de ferramenta, troque o prompt.
