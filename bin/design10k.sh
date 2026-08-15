#!/usr/bin/env bash
# design-10k — teste dos 5 segundos.  uso: bash design10k.sh arquivo.html
f="$1"; [ -f "$f" ] || { echo "uso: bash design10k.sh arquivo.html"; exit 1; }
F=$(tr '\n' ' ' < "$f")
IMGS=$(printf '%s' "$F" | grep -oE '<img[^>]*>')
n(){ printf '%s' "$1" | grep -c "$2"; }
r(){ printf '%-30s %-8s %s\n' "$1" "$2" "$3"; }
le(){ [ "$1" -le "$2" ] && echo "OK" || echo "FALHA  (teto $2)"; }
ge(){ [ "$1" -ge "$2" ] && echo "OK" || echo "FALHA  (min $2)"; }
eq(){ [ "$1" -eq "$2" ] && echo "OK" || echo "FALHA  (exato $2)"; }

FS=$(grep -ohE 'font-size:[^;}]+' "$f" | sort -u | wc -l)
FSH=$(grep -ohE 'font-size:[^;}]+' "$f" | grep -v 'var(' | sort -u | wc -l)
PAD=$(grep -ohE '(padding|margin|gap)[a-z-]*:[^;}]+' "$f" | sort -u | wc -l)
OFF=$(grep -ohE '[0-9]+px' "$f" | grep -oE '[0-9]+' | sort -un | awk '$1>2 && $1%4!=0' | wc -l)
NI=$(printf '%s' "$IMGS" | grep -c '<img'); [ -z "$IMGS" ] && NI=0
OP=$(n "$IMGS" 'object-position'); SS=$(n "$IMGS" 'srcset')
WH=$(n "$IMGS" 'width=');          ALT=$(n "$IMGS" 'alt=')
H1=$(n "$F" '<h1');                LD=$(n "$F" 'application/ld+json')
OG=$(printf '%s' "$F" | grep -o 'property="og:' | wc -l)
MD=$(n "$F" 'name="description"'); VH=$(printf '%s' "$F" | grep -o '100vh' | wc -l)
EMO=$(grep -oP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' "$f" | wc -l)

echo "=== $f ==="
r "font-size distintos"      "$FS"      "$(le "$FS" 12)"
r "font-size sem var()"      "$FSH"     "$(le "$FSH" 2)"
r "padding/margin/gap uniq"  "$PAD"     "$(le "$PAD" 14)"
r "px fora da grade de 4"    "$OFF"     "$(le "$OFF" 0)"
r "img com object-position"  "$OP/$NI"  "$(ge "$OP" "$NI")"
r "img com srcset"           "$SS/$NI"  "$(ge "$SS" "$NI")"
r "img com width+height"     "$WH/$NI"  "$(ge "$WH" "$NI")"
r "img com alt"              "$ALT/$NI" "$(ge "$ALT" "$NI")"
r "<h1>"                     "$H1"      "$(eq "$H1" 1)"
r "JSON-LD"                  "$LD"      "$(ge "$LD" 1)"
r "og: tags"                 "$OG"      "$(ge "$OG" 4)"
r "meta description"         "$MD"      "$(ge "$MD" 1)"
r "100vh (usar 100svh)"      "$VH"      "$(le "$VH" 0)"
r "emoji como icone"         "$EMO"     "$(le "$EMO" 0)"
