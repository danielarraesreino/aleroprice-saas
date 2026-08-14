# Fotos das prévias

Uma pasta por bar, com o mesmo nome do arquivo em `app/data/leads/`.
Jogue as fotos aqui e rode o comando — nada de editar YAML.

## Como nomear (é o que decide onde a foto aparece)

| Nome do arquivo          | Onde aparece                                   |
|--------------------------|------------------------------------------------|
| `capa.jpg`               | foto grande do topo                            |
| `prato-costelinha.jpg`   | card no cardápio, com o nome tirado do arquivo |
| `prato-chopp.jpg`        | idem — vira "Chopp"                            |
| `ambiente-1.jpg`         | galeria                                        |
| qualquer outro nome      | galeria                                        |

Extensões aceitas: .jpg .jpeg .png .webp
Sem `capa.jpg`, a primeira foto da galeria assume o topo.

## Publicar

```bash
flask aplicar-demos --slug tatu-bola     # um bar
flask aplicar-demos                      # todos
```

Em produção (com SEED_TOKEN definido):
`/bootstrap-demo?token=$SEED_TOKEN&action=demos&slug=tatu-bola`

## Recado importante

As fotos precisam estar **commitadas** — o filesystem da Vercel é somente
leitura e não há upload no painel. Foto boa é o que separa um site que vende
de um esqueleto: sem imagem, a prévia abre só com a cor do tema.
