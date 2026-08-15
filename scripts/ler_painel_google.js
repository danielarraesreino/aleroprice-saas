/* Lê o painel do Google de um bar. Cole no console do navegador na página da
   busca; a saída vai direto pro scripts/coletar_google.py.

   Por que existe em arquivo, e não solto no console:
   a primeira versão deste regex leu "4,6 1.951 avaliações" como nota 1.9 com 51
   avaliações — quebrou o número de milhar no meio e quase publicou nota 1,9 num
   bar que tem 4,6. Nota errada no site do cliente é o pior defeito possível
   deste produto, então o padrão que acerta fica versionado e testado, não
   reescrito de memória a cada bar. */
(() => {
  const texto = document.body.innerText;

  /* O painel escreve de dois jeitos, e os dois precisam casar:
       "Maria Bonjour Bar 4,6 1.951 avaliações no Google"
       "Cervejaria Tábuas 4,7 (504)"
     O ponto de milhar é o que derruba padrão ingênuo: [\d.]+ tem que vir
     inteiro, nunca fatiado. */
  const comPalavra = texto.match(/(\d[,.]\d)\s+([\d.]+)\s*(?:mil\s*)?avaliaç/i);
  const entreParenteses = texto.match(/(\d[,.]\d)\s*\(\s*([\d.]+)\s*\)/);
  const achado = comPalavra || entreParenteses;

  /* "1.951" -> 1951. Em pt-BR o ponto aqui é milhar, nunca decimal: contagem de
     avaliação é inteira. */
  const inteiro = (s) => (s ? parseInt(s.replace(/\./g, ''), 10) : null);

  const primeiro = (re) => (texto.match(re) || [])[0] || null;

  const fotos = [...new Set(
    [...document.querySelectorAll('img')]
      .filter((i) => i.naturalWidth >= 80 && i.src.includes('googleusercontent'))
      .map((i) => i.src)
      .filter((s) => !s.includes('/-'))          // avatar de perfil, não do bar
  )]
    .map((s) => s.replace(/=[swh].*$/, '') + '=s2048')  // pede a versão grande
    .slice(0, 10);

  return JSON.stringify({
    nota: achado ? achado[1].replace('.', ',') : null,
    avaliacoes: achado ? inteiro(achado[2]) : null,
    telefone: primeiro(/\(\d{2}\)\s?\d{4,5}-?\d{4}/),
    endereco: primeiro(/(Av\.|Avenida|R\.|Rua|Praça)[^\n]{10,90}/),
    // "R$ 60–100" vira "$$" no schema; guardamos o texto e o motor decide
    faixa_preco: primeiro(/R\$\s?\d+\s*[–-]\s*\d+/),
    site: (document.querySelector('a[href^="http"][data-attrid*="website"]') || {}).href || null,
    fechado: /permanentemente fechado/i.test(texto),
  });
})()
