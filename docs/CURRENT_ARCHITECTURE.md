# Arquitetura atual

## Organização dos projetos

O projeto é uma CLI Python que chama um núcleo numérico Fortran por `ctypes`.
O repositório mantém o núcleo compartilhado e dois projetos de aplicação:
`api/` (FastAPI) e `web/` (React/Vite). A CLI continua na raiz para preservar o
uso legado.

```text
CLI (hfta.py)
  -> parser de argumentos e conversões de unidades
  -> openhfta_core.models.AnalysisConfig
  -> openhfta_core.analysis
  -> openhfta_core.profiles / library
  -> ytwcore1_ (src/YTWCore1.f90, ctypes)
  -> AnalysisResult (ângulos, padrão, metadados)
  -> openhfta_core.metrics / plotting

API FastAPI (`api/`)
  -> multipart UploadFile + campos do formulário
  -> validação e AnalysisConfig
  -> openhfta_core.analysis
  -> JSON com ângulos, padrão, configuração efetiva e metadados
```

`web/` é uma aplicação Vite + React + TypeScript. Ela envia o formulário
como `multipart/form-data` para a API e usa Plotly para renderizar os 140
pontos do padrão de elevação. `VITE_API_URL` controla a origem da API e, por
padrão, aponta para `http://127.0.0.1:8000`.

`hfta.py` mantém wrappers públicos para os imports históricos (`parse_profile`,
`analyze`, `compute_fom` etc.). A lógica reutilizável vive em `openhfta_core`:

- `library.py`: descoberta, carregamento e ABI da biblioteca;
- `profiles.py`: `.PRO`, alturas e fases;
- `aoa.py`: frequência, bandas e `.PRN`;
- `models.py`: dataclasses de configuração, perfil e resultado;
- `analysis.py`: preparação dos arrays e chamada do Fortran;
- `metrics.py`: FOM compatível;
- `plotting.py`: figuras Matplotlib com fechamento explícito;
- `exceptions.py`: erros de domínio.

As métricas determinísticas incluem pico principal, picos e nulos locais,
menor valor, largura de feixe em −3 dB e estatísticas nas faixas `0-5`,
`5-10`, `10-20` e `20-35` graus.

## API atual

- `GET /health`: informa a disponibilidade da biblioteca Fortran;
- `POST /api/analyze`: recebe um perfil `.PRO` e executa uma análise síncrona.

O formulário aceita `frequency`, `units`, `heights`, `antenna_type`, parâmetros
de solo, difração e deslocamento de torre. A resposta contém `angles_deg`,
`pattern_db`, métricas, interpretação em português, configuração efetiva e
metadados. Com `export_format`, o mesmo endpoint retorna JSON, CSV, PNG, SVG ou
PDF. Arquivos acima de 5 MiB são rejeitados e o arquivo temporário é removido
ao fim da requisição.

O Makefile compila `src/*.f90` em `build/native` e gera
`libopenytwcore.so` (Linux), `libOpenYTWCore.dylib` (macOS) ou
`OpenYTWCore.dll` (Windows). O alvo diferencial depende de `YTWCore.dll` e
`DFORRT.DLL` legados, que não estão presentes neste checkout.

## ABI preservada

`YTWCore1` exporta o símbolo `ytwcore1_`. Todos os escalares são passados por
referência. O contrato usa `REAL*4` (`ctypes.c_float`), `INTEGER*2`
(`ctypes.c_int16`), `DG0/HG0(0:150)`, `HantFeetIn(0:3)`,
`Pattern_dB(0:139)` e `AntPhase(0:3)`. A análise limita o perfil efetivo a 148
pontos para manter o marcador final zero usado pelo núcleo; o cartão e o
gráfico inferior usam essa mesma lista.

## Compatibilidade relevante

Perfis com cabeçalho `meters` são convertidos para pés; `feet` permanece em
pés. Perfil sem cabeçalho preserva o comportamento observado da CLI: valores
são tratados como pés. Alturas e deslocamento de torre são convertidos pela
CLI segundo `--units`; a configuração interna do núcleo é sempre em pés.
