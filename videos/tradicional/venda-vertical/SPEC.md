# SPEC — "Um dia na esquina" (mundo tradicional · piloto Empório do Nono)

GOAL:    quem assiste sente que a casa vive o dia inteiro (almoço, balcão, chorinho) e
         termina sabendo como pedir: o nome da casa e o WhatsApp na tela.
OUTPUT:  HyperFrames, 1080 x 1920, 30 fps (vertical: WhatsApp, Status, Reels, prévia de venda)
TIME:    15 s x 30 = 450 frames. Sem música definida ainda (ver SOUND).

LOOK (o meio é o do modelo tradicional: parede de papel com retratos pregados)
  ground   dia #f6eddd (papel), tarde #ecd9b6, noite #22160d (madeira escura do modo
           escuro do modelo). Grão de papel: turbulência estática, 6% multiply.
  ink      dia #2d1e13 / noite #f3e6cf. Secundário madeira #6b4526 / noite #c99a63.
  accent   esmalte #b32a1e (noite #e85b49): SÓ nos ponteiros do relógio e na hora.
  display  Playfair Display 900, hora 168 px, tracking -2%; nome da casa 150 px.
  body     Playfair Display 700, 60 px (linhas), itálico 30 px nas legendas dos retratos.
  medium   retratos: foto real em moldura #fffaf0, borda 18 px e base 64 px com legenda,
           fita crepe rgba(199,166,108,.6) 120x36 a -3°, sombra 0 18px 40px rgba(61,36,21,.30),
           inclinação de ±2,5°. Foto nunca maior que o original (fotos de delivery 300 px
           entram em 300 px).
  depth    sombra só nos retratos e no relógio (0 16px 30px rgba(0,0,0,.25)); sem vinheta.

OBJECTS
  relógio  de parede, Ø 400 px, centro (540, 390): aro de madeira 30 px #6b4526 com
           filete interno #43290f, mostrador #fffaf0, 60 traços (12 grossos), números
           12/3/6/9 em Playfair 900 52 px, ponteiros esmalte (hora 16x120, minuto 9x170),
           pino central 22 px. É o fio da história: o ponteiro gira e o dia muda.
  retrato  ver medium.
  placa    a marca da casa (marca.png 242 px) em placa #fffaf0 260 px, -2°, no fecho.

MOTION
  enter    expo.out 0.55 s (retratos), letras da hora 0.3→1 + blur 4→0 a 0.06 s
  move     power2.inOut (varredura do relógio 1.0 s, empurrão de retrato 0.5 s)
  exit     power3.in 0.35 s (retrato arrancado da parede), stagger 0.05 s
  flood    cor do papel power2.inOut 0.5 s, causada pela virada do relógio

SHOTS (segundos do filme)
  0.0–3.8   ALMOÇO. Frame 0 já é o pôster: relógio em 11:30, "11h30", "Sai o almoço do dia",
            retrato do almoço assentando (-4°→-2,5°). 1.3 s: retrato do PF do Nono (300 px)
            entra pela direita; 2.3 s: feijoada (300 px) pela esquerda. 3.4 s: retratos
            arrancados; o relógio gira 11:30→18:00 (causa) e o papel esquenta para a tarde.
  3.6–7.6   BALCÃO. "18h" · "O balcão vira mesa de frios: mais de 40 acepipes". Bolinhos,
            coxinhas, caldinho. 7.2 s: relógio vai a 20:00, o papel vira madeira (noite).
  7.4–11.4  CHORINHO. "20h" · "Segunda tem roda de chorinho". Chorinho (800 px), chopp tirado,
            brinde. 11.0 s: o relógio encolhe e vira a placa da marca (carry across); papel
            volta ao dia.
  11.2–15.0 FECHO. Placa da marca, "Empório / do Nono", "Almoço todo dia · Barão Geraldo",
            "Peça pelo WhatsApp (19) 99922-4806". Tudo assentado até 12.6 s e parado ≥ 2 s.

SAFE    palavras e produto entre y 168 e 1330; abaixo só papel e a faixa de azulejo.

SOUND   15 s que contam algo: pede trilha (choro instrumental ~100 bpm) e nenhum efeito
        fora de causa. Sem fonte de música configurada ainda: entregar mudo e dizer.

BANNED  fundo escuro vazio com coisas flutuando no meio; brilho/neon/partículas; tudo
        centrado (texto alinhado à esquerda em x 96); todo elemento entrando com fade e
        subida; texto que se mexe enquanto é lido; logo no canto; selos "01/02";
        foto esticada além do original; bloco pronto do registry (vídeo exclusivo).

QA      0 (pôster), 1.8, 3.5 (varredura), 5.0, 7.3 (virada pra noite), 9.0, 11.1 (relógio →
        placa), 13.0 e 14.9 (fecho parado).
