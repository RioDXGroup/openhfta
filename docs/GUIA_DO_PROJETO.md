# Guia do projeto OpenHFTA

## 1. Objetivo

O OpenHFTA é uma reimplementação orientada à preservação do HFTA, ferramenta
de análise de terreno para antenas de HF. Ele calcula o padrão de elevação de
uma antena sobre um perfil de terreno, combinando:

- reflexão de Fresnel para um solo com permissividade e condutividade;
- difração baseada na Uniform Theory of Diffraction (UTD), habilitada por
  padrão;
- suporte a pilhas de até quatro elementos, com elementos em fase ou 180°
  fora de fase;
- cálculo opcional de Figure of Merit (FOM) a partir de dados de Angle of
  Arrival (AoA).

O objetivo principal é reproduzir o comportamento do HFTA original. Portanto,
alterações no modelo numérico devem ser avaliadas pela compatibilidade do
resultado, e não apenas por uma interpretação teórica mais moderna.

## 2. Organização dos arquivos

| Caminho | Responsabilidade |
| --- | --- |
| `hfta.py` | CLI Python, leitura dos arquivos, conversão de unidades, chamada da biblioteca e geração dos gráficos. |
| `src/YTWCore1.f90` | Rotina Fortran principal `YTWCore1`, que prepara o perfil, percorre os raios e sintetiza o padrão. |
| `src/OtherProgs.f90` | Rotinas auxiliares de reflexão, Fresnel, difração UTD, ângulos e traçado de raios. |
| `Makefile` | Compilação nativa, compilação cruzada para testes Windows, testes e instalação. |
| `api/` | Projeto FastAPI: endpoints, validação HTTP e serialização dos resultados. |
| `web/` | Projeto React/Vite: formulário, gráficos e interação com a API. |
| `test_hfta.py` | Testes unitários do parser, FOM e descoberta da biblioteca. |
| `test/` | Perfis `.PRO`, harness C e arquivos auxiliares dos testes diferenciais. |
| `docs/THEORY.md` | Fundamentação matemática e descrição detalhada do modelo. |
| `docs/PORTING_NOTES.md` | Notas de portabilidade e sensibilidade numérica do núcleo Fortran. |
| `docs/ADDR_MAP.md` | Mapeamento de endereços e referências úteis para a compatibilidade com o legado. |
| `flake.nix` / `default.nix` | Pacote Nix e ambiente reprodutível de desenvolvimento. |

## 3. Como o processamento funciona

O fluxo de uma análise é:

1. A CLI agrupa cada `--profile` com as opções específicas que aparecem até o
   próximo `--profile`.
2. A frequência é convertida de MHz ou da notação de banda, como `20m`, para
   MHz.
3. As alturas e o deslocamento da torre são convertidos conforme `--units`.
4. O perfil `.PRO` é lido e convertido para pés, unidade esperada pelo
   Fortran.
5. O Python prepara arrays compatíveis com a ABI Fortran e carrega
   `ytwcore1_` via `ctypes`.
6. O Fortran calcula 140 amostras do padrão, de `0,25°` a `35°`, em passos de
   `0,25°`.
7. O Python imprime o maior ganho e o ângulo correspondente e gera o gráfico
   de comparação.

A biblioteca nativa é procurada nesta ordem:

1. caminho fornecido por `--lib`;
2. variável de ambiente `OPENHFTA_LIB`;
3. biblioteca ao lado de `hfta.py` ou em um diretório `lib` próximo;
4. descoberta do sistema por `ctypes.util.find_library`.

O símbolo exportado precisa ser `ytwcore1_`, incluindo o sublinhado final
normalmente produzido pelo `gfortran`.

## 4. Instalação e execução

### Dependências

É necessário ter:

- Python 3;
- NumPy;
- Matplotlib;
- `gfortran` para compilar o núcleo nativo;
- `make`.

Em Debian/Ubuntu:

```bash
sudo apt install gfortran make python3-numpy python3-matplotlib
```

### Ambiente local

```bash
make
./hfta.py --help
```

O comando cria `libopenytwcore.so` em Linux, `libOpenYTWCore.dylib` em macOS
ou `OpenYTWCore.dll` em Windows, conforme a plataforma.

### Instalação no sistema

```bash
make
sudo make install
hfta --help
```

O prefixo pode ser alterado sem editar o Makefile:

```bash
make PREFIX="$HOME/.local"
make PREFIX="$HOME/.local" install
```

O alvo `install` instala o executável Python, a biblioteca nativa e os
arquivos Markdown em `share/doc/hfta` dentro do prefixo escolhido.

### Nix

Para usar o pacote:

```bash
nix shell github:riodxgroup/openhfta
hfta --help
```

Para desenvolvimento:

```bash
nix develop -c "$SHELL"
make
./hfta.py --help
```

## 5. Uso da CLI

Uma análise de elevação precisa de pelo menos um perfil e de uma frequência:

```bash
./hfta.py --profile test/pro/PR1T-torre1-332.00.PRO --freq 20m
```

A frequência também pode ser informada diretamente em MHz:

```bash
./hfta.py --profile terreno.pro --freq 14.2 --output padrao.svg
```

### Opções por perfil

Estas opções pertencem ao `--profile` imediatamente anterior:

| Opção | Descrição |
| --- | --- |
| `--profile ARQUIVO` | Perfil de terreno no formato `.PRO`. |
| `--heights H1 H2 ...` | Alturas dos elementos, no máximo quatro. Um `*` indica 180° fora de fase. |
| `--antenna-type TIPO` | `Dipole`, `2-Ele`, `3-Ele`, `4-Ele`, `5-Ele`, `6-Ele` ou `8-Ele`. |
| `--move-tower DISTÂNCIA` | Move o início do perfil para trás pela distância informada. |

Exemplo de pilha com um elemento fora de fase:

```bash
./hfta.py --profile terreno.pro --freq 14.2 \
  --antenna-type 2-Ele --heights 10 '20*'
```

O tipo `8-Ele` é convertido para o tipo interno `7` do núcleo Fortran. O
programa aceita até quatro alturas; valores adicionais são ignorados na
preparação dos arrays.

### Opções globais

| Opção | Padrão | Descrição |
| --- | --- | --- |
| `--freq` | obrigatório em modo `elevation` | Frequência em MHz ou banda, como `20m`. |
| `--units {meters,feet}` | `meters` | Unidade das alturas e de `--move-tower`. |
| `--soil-sigma` | `0.005` | Condutividade do solo em S/m. |
| `--soil-epsr` | `13.0` | Permissividade relativa do solo. |
| `--no-diffraction` | difração ligada | Desativa a contribuição de difração. |
| `--plot-mode {elevation,terrain}` | `elevation` | Escolhe padrão de elevação ou perfil de terreno. |
| `--lib CAMINHO` | descoberta automática | Caminho explícito da biblioteca OpenYTWCore. |
| `--aoa ARQUIVO` | nenhum | Arquivo AoA `.PRN`; habilita o FOM. |
| `--output ARQUIVO` | mostra na tela | Salva o gráfico, por exemplo em PNG, SVG ou PDF. |
| `--debug` | desligado | Habilita saídas de depuração do núcleo. |
| `--debug-angle ÂNGULO` | `0.0` | Ângulo usado pelo modo de depuração. |

Para visualizar somente os perfis, não é necessário informar `--freq`:

```bash
./hfta.py --profile norte.pro --profile sul.pro --plot-mode terrain
```

Para comparar configurações diferentes, as opções devem permanecer junto do
perfil a que pertencem:

```bash
./hfta.py \
  --profile norte.pro --antenna-type 2-Ele --heights 10 20 \
  --profile sul.pro --antenna-type Dipole --heights 15 \
  --freq 14.2 --output comparacao.pdf
```

## 6. Formatos de entrada

### Perfil `.PRO`

O primeiro registro deve declarar `meters` ou `feet`. As linhas seguintes têm
distância e altura:

```text
meters
0    187.1
30   187.8
60   191.2
90   195.0
```

Linhas vazias, comentários iniciados por `#` e linhas com valores inválidos
são ignorados. São necessários pelo menos dois pontos. O parser converte os
valores para pés antes de chamar o Fortran.

É importante não confundir as unidades do arquivo com `--units`: o cabeçalho
do `.PRO` controla o perfil, enquanto `--units` controla as alturas da antena
e o deslocamento da torre. Se o cabeçalho do perfil for omitido, a
implementação atual interpreta os valores como pés; por isso, declarar a
unidade explicitamente é recomendado.

O núcleo recebe arrays dimensionados para índices `0:150`; a camada Python
reserva espaço para 151 valores e copia no máximo 149 pontos do perfil para
preservar os marcadores finais. Perfis muito maiores devem ser simplificados
antes da análise.

### Arquivo AoA `.PRN`

O formato esperado é o formato multibanda da ARRL: uma linha de título, uma
linha começando por `Elev` e colunas como `80m`, `40m`, `20m` e `10m`.

```text
Perfil de exemplo
Elev      80m    40m    20m    10m
 1         1.0    2.0    3.0    4.0
 5         5.0    6.0    7.0    8.0
10        10.0   11.0   12.0   13.0
```

Os percentuais são convertidos para probabilidades. A banda é escolhida
automaticamente a partir de `--freq`. Se a banda não existir, nenhum dado AoA
é carregado e o FOM não é calculado.

## 7. Solo e interpretação do resultado

Os parâmetros mais comuns são:

| Tipo de solo | `--soil-sigma` (S/m) | `--soil-epsr` |
| --- | ---: | ---: |
| Muito ruim | `0.001` | `5` |
| Ruim | `0.002` | `13` |
| Médio (padrão) | `0.005` | `13` |
| Bom | `0.010` | `14` |
| Muito bom | `0.030` | `20` |
| Água salgada | `5.000` | `80` |

O gráfico de elevação apresenta o ganho em dB por ângulo. Quando AoA é
fornecido, as probabilidades aparecem como barras e o resumo inclui o FOM,
calculado como a soma ponderada do ganho linear nos ângulos disponíveis,
seguida de `10 log10`.

## 8. Desenvolvimento e testes

Teste rápido da biblioteca e da CLI:

```bash
make
./hfta.py --profile test/pro/PR1T-torre1-332.00.PRO --freq 20m --output /tmp/openhfta-test.png
```

Testes unitários:

```bash
python3 -m unittest test_hfta -v
```

Ou, para executar o fluxo definido pelo projeto:

```bash
make test
```

`make test` tenta também executar o teste diferencial do núcleo. Essa parte
fica automaticamente suspensa quando `test/YTWCore.dll` e `test/DFORRT.DLL`
não estão presentes. Esses DLLs legados não fazem parte do repositório.

Para limpar artefatos de compilação:

```bash
make clean
```

## 9. Portabilidade e compatibilidade

O Python chama o Fortran por `ctypes` usando a ABI de parâmetros por
referência. O código utiliza `INTEGER*2`, `INTEGER*4` e `REAL*4`; por isso,
alterações nos tipos, na ordem dos argumentos ou nas flags de compilação podem
alterar o resultado numérico ou quebrar a chamada.

As flags do Makefile priorizam a compatibilidade numérica do legado, incluindo
aritmética x87 e precisão excedente. A documentação de detalhes está em
[`PORTING_NOTES.md`](PORTING_NOTES.md). A explicação das equações e do traçado
de raios está em [`THEORY.md`](THEORY.md).

## 10. Problemas comuns

### Biblioteca não encontrada

Compile primeiro ou informe o caminho explicitamente:

```bash
make
./hfta.py --lib ./libopenytwcore.so --profile terreno.pro --freq 14.2
```

Também é possível usar `OPENHFTA_LIB`:

```bash
OPENHFTA_LIB="$PWD/libopenytwcore.so" ./hfta.py \
  --profile terreno.pro --freq 14.2
```

### Símbolo `ytwcore1_` ausente

Verifique se a biblioteca foi compilada a partir dos fontes deste projeto e
se o compilador Fortran exportou o símbolo com o sublinhado final.

### Gráfico vazio ou resultado inesperado

Confirme a unidade do cabeçalho `.PRO`, a unidade de `--units`, a frequência,
os parâmetros do solo e se o perfil tem pontos suficientes. Para investigar o
núcleo, use `--debug` e, quando necessário, `--debug-angle`.

### Teste diferencial ignorado

Isso é esperado sem os DLLs privados do HFTA. Os testes unitários Python
continuam disponíveis e devem ser executados independentemente.
