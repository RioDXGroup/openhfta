# Plano de implementação

## Concluído nesta entrega

1. Registrar arquitetura, ABI, dependências e baseline numérico.
2. Extrair a biblioteca Python reutilizável `openhfta_core`.
3. Manter `hfta.py` como adaptador de CLI e preservar imports públicos.
4. Validar o mesmo núcleo Fortran sem alterar suas fórmulas.
5. Adicionar regressões para parsing, ABI, validação e análise de referência.
6. Criar API FastAPI síncrona com `/health` e `/api/analyze`.
7. Criar projeto web React/TypeScript com upload, formulário e gráfico Plotly.
8. Adicionar métricas determinísticas de picos, nulos, largura de feixe, faixas angulares e comparação.
9. Adicionar interpretação determinística em português e exportações JSON, CSV, PNG, SVG e PDF.
10. Adicionar gráfico do terreno, comparação de 2 a 4 cenários e até 4 perfis/azimutes.
11. Exibir limitações do modelo e registrar o limite efetivo de 148 pontos e a faixa angular compatível.
12. Integrar análise explicativa opcional por IA via OpenRouter, mantendo a camada determinística como fonte dos dados.

## Próximas fases

1. Docker/Compose e documentação de implantação.
2. Métricas e comparação avançadas orientadas ao objetivo de enlace.
3. Exportação e persistência de relatórios completos de cenários.
4. Modelo de antena mais completo: adicionar tilt elétrico/mecânico,
   relação frente/costas e lóbulos laterais calibrados. Hoje o núcleo já
   diferencia ganho, largura de feixe, alturas e fases dos elementos, mas usa
   uma aproximação de padrão vertical, sem esses parâmetros como entradas
   independentes.

Enquanto essa fase não for implementada, a melhoria deve usar o que já existe:
ganho por elevação, largura de feixe por tipo, empilhamento coerente, alturas,
fases e o padrão calculado pelo núcleo para ponderar os trajetos exibidos.

A IA não substitui o cálculo do OpenHFTA: recebe resultados estruturados,
explica em português e deve declarar as limitações do modelo.
