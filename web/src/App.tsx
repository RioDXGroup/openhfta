import { CSSProperties, FormEvent, MouseEvent as ReactMouseEvent, useEffect, useRef, useState } from 'react'
import Plot from 'react-plotly.js'

type Result = {
  angles_deg: number[]
  pattern_db: number[]
  profile: { source_units: string; points: number; distances_m: number[]; heights_m: number[]; terrain?: Record<string, unknown> }
  configuration: {
    frequency_mhz: number
    antenna_heights_ft: number[]
    antenna_heights_m?: number[]
    antenna_phases: number[]
    diffraction_disable: boolean
    polarization?: 'horizontal' | 'vertical'
  }
  metadata: { profile_points?: number }
  limitations?: string[]
  sources?: { profile_name?: string | null; prn_name?: string | null }
  metrics?: { peak: { angle_deg: number; value_db: number }; integrated_average_gain: { average_db: number }; beamwidth_3db: { width_deg: number | null }; nulls: { angle_deg: number; value_db: number }[]; figure_of_merit_db?: number }
  flat_pattern_db?: number[]
  aoa?: { band?: string | null; source?: string | null; angles_deg: number[]; probabilities_pct: number[]; available?: boolean; message?: string | null }
  interpretation?: { headline: string; beginner: string; technical: string; observations: string[] }
  ray_trace?: { available: boolean; paths: { kind: string; angle_deg: number; distances_m: number[]; heights_m: number[] }[]; counts: Record<string, number> }
}
type Interpretation = { headline: string; beginner: string; technical: string; observations: string[] }
type Scenario = { name: string; heights_input?: string; antenna_type?: string; polarization?: 'horizontal' | 'vertical'; profile_name?: string; prn_name?: string; angles_deg?: number[]; pattern_db: number[]; flat_pattern_db?: number[]; aoa?: Result['aoa']; metrics?: Result['metrics']; configuration?: Result['configuration']; metadata?: Result['metadata']; profile?: Result['profile']; ray_trace?: Result['ray_trace']; interpretation?: Interpretation; warnings?: string[] }
type CompareResult = { angles_deg: number[]; scenarios: Scenario[]; comparison: { rmse_db: number; max_absolute_delta_db: number; integrated_average_delta_db: number; peak_delta_db: number; pairwise?: { rmse_db: number; max_absolute_delta_db: number; integrated_average_delta_db: number; peak_delta_db: number }[] }; interpretation?: Interpretation; limitations?: string[] }
type AIExplanation = { headline: string; for_leigo: string; melhor_cenario: string; cenarios_analisados: string[]; por_que: string[]; recomendacoes: string[]; cuidados: string[]; confianca: string }
type ScenarioConfig = { name: string; heights: string; antenna_type: string; polarization?: 'horizontal' | 'vertical'; prn_default?: string }
type ColorPalette = { rays: Record<string, string>; scenarios: string[]; flatScenarios: string[]; terrain: string; flat: string; aoa: string; event: string; corner: string; antenna: string }
type Locale = 'pt-BR' | 'en' | 'es'

const LOCALE_OPTIONS: { value: Locale; label: string }[] = [
  { value: 'pt-BR', label: 'Português (Brasil)' },
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Español' },
]

const UI_TEXT: Record<Locale, Record<string, string>> = {
  'pt-BR': {
    language: 'Idioma', accessibleColors: 'Cores acessíveis', accessiblePatterns: 'Linhas e símbolos', online: 'núcleo Fortran online',
    heroTitle: 'Veja o terreno', heroTitleEm: 'moldar o sinal.', heroLede: 'Envie um perfil de terreno e explore o padrão de elevação da sua antena em segundos.',
    helpImprove: 'Ajude a melhorar o OpenHFTA', feedbackBanner: 'Encontrou algo estranho ou tem uma sugestão? Sua experiência ajuda a tornar a ferramenta mais útil para toda a comunidade.', sendSuggestion: 'Enviar sugestão',
    configuration: 'Configuração', defineScenario: 'Defina o cenário de análise', explainFields: 'Explicar campos do formulário', uploadProfile: 'Solte seu perfil .PRO aqui', browseComputer: 'ou clique para procurar no computador',
    frequency: 'Frequência', units: 'Unidade', meters: 'Metros', feet: 'Pés', antennaHeights: 'Alturas da antena', antennaType: 'Tipo de antena', polarization: 'Polarização', terrainType: 'Tipo de terreno', soilPermittivity: 'Permissividade do solo', soilConductivity: 'Condutividade (S/m)', towerOffset: 'Deslocamento da torre',
    includeDiffraction: 'Incluir difração no cálculo', compareScenarios: 'Comparar cenários', calculate: 'Executar análise', calculating: 'Calculando...',
    result: 'Resultado', waitingAnalysis: 'Aguardando uma análise', patternCalculated: 'Padrão calculado pelo núcleo', comparisonCalculated: 'Comparação calculada pelo núcleo', processing: 'Processando análise…',
    terrainProfile: 'PERFIL DO TERRENO', rayTraceCore: 'TRAÇADO DE RAIOS DO NÚCLEO', export: 'EXPORTAR', emptyTitle: 'Seu padrão aparecerá aqui', emptyText: 'Preencha a configuração ao lado e execute a primeira análise.',
    elevation: 'Elevação (°)', elevationStats: 'Estatística de elevação (%)', height: 'Altura (m)', distance: 'Distância (m)', gain: 'Ganho (dB)', nullsLabel: 'Nulos',
    noDiffraction: 'Difração desativada', diffraction: 'Difração incluída', automaticReading: 'LEITURA AUTOMÁTICA', modelLimits: 'LIMITES DO MODELO',
    explainResult: '✦ Explicar resultado com IA', interpreting: 'Interpretando...', quickGuide: 'GUIA RÁPIDO', close: 'Fechar', helpTitle: 'O que significa cada campo?', helpIntro: 'Esses parâmetros descrevem uma análise de padrão de elevação de uma antena HF sobre um perfil de terreno. O núcleo calcula em pés internamente, mas você pode informar e interpretar os valores em metros.', helpTip: 'Dica para começar', rayHelpTitle: 'Como ler as trajetórias?', rayHelpIntro: 'O gráfico mostra caminhos geométricos calculados sobre o perfil. A linha representa o percurso; ela não é, sozinha, uma medição de potência recebida.', rayTip: 'Interações no gráfico',
    explainTerrainTypes: 'Explicar tipos de terreno', soilHelpTitle: 'O que significa cada tipo de terreno?', soilHelpIntro: 'Cada tipo de terreno preenche a permissividade do solo e a condutividade (S/m) com valores de referência da tabela clássica de tipos de terreno usada em modelagem de antenas (mesma linhagem citada pelo ARRL Antenna Book). Selecione o mais próximo do seu local ou ajuste os campos manualmente.', soilHelpTip: 'Como escolher',
    feedbackTitle: 'Conte como podemos melhorar', feedbackIntro: 'Sugestões, correções e ideias de novos recursos são muito bem-vindas. Se quiser uma resposta, informe seu e-mail; ele será usado apenas para retornarmos sobre esta mensagem.',
    optionalName: 'Nome (opcional)', replyEmail: 'E-mail para retorno', subject: 'Assunto', message: 'Mensagem', sendMessage: 'Enviar mensagem', sending: 'Enviando…', securityCheck: 'Verificação de segurança para evitar mensagens automáticas.', newSuggestion: 'Enviar outra sugestão',
    footer: 'preservando a inteligência do HFTA para sistemas modernos',
    errProfileRequired: 'Selecione um arquivo .PRO antes de analisar.', errSharedProfileRequired: 'Selecione um .PRO compartilhado no formulário.', errAllScenarioProfiles: 'Informe um .PRO em todos os cenários.', errSharedPrnRequired: 'Informe um arquivo .PRN compartilhado ou selecione um PRN padrão.', errAllScenarioPrns: 'Informe um .PRN em todos os cenários ou selecione um PRN padrão para cada um.',
    errAnalysisFailed: 'Não foi possível executar a análise.', errApiGeneric: 'Erro de comunicação com a API.', errAiExplain: 'Não foi possível obter a explicação da IA.', errAiFailed: 'Falha ao consultar a IA.', errFeedbackSend: 'Não foi possível enviar sua mensagem.', feedbackThanksDefault: 'Obrigado pela colaboração! Sua mensagem foi enviada.',
    errExportPrn: 'Envie um arquivo .PRN próprio ou selecione um PRN padrão do projeto.', errExportFailed: 'Não foi possível gerar a exportação.', errProfileIndividualMode: 'O PRO está no modo individual. Selecione o arquivo dentro de um dos cenários.', errPrnIndividualMode: 'O PRN está no modo individual. Selecione o arquivo dentro de um dos cenários.',
    upToFourScenarios: 'Dois ou mais cenários', sharedPrn: 'PRN compartilhado', individualPrn: 'PRN individual', sharedProfile: 'PRO compartilhado', individualProfile: 'PRO individual', addScenario: '+ adicionar',
    scenarioHelpText: 'Você pode informar `.PRO` em cada linha. Escolha acima se o `.PRO` e o `.PRN` serão compartilhados pelo formulário ou individuais por cenário.',
    scenarioNameLabel: 'Nome do cenário', scenarioNameTooltip: 'Nome usado nos gráficos e resultados', scenarioHeightsShort: 'Alturas', scenarioHeightsTooltip: 'Altura de cada elemento; use espaços entre valores e * para inverter a fase',
    scenarioAntennaLabel: 'Antena', scenarioAntennaTooltip: 'Modelo de antena deste cenário', scenarioPolarizationTooltip: 'Polarização calculada neste cenário',
    scenarioProfileLabel: 'Perfil .PRO', scenarioProfileTooltip: 'Perfil de terreno usado neste cenário', topBlockPlaceholder: 'bloco superior', scenarioPrnStatLabel: 'Estatística .PRN', scenarioPrnTooltip: 'Estatística dos ângulos de chegada', filePlaceholder: 'arquivo',
    scenarioDefaultPrnLabel: 'PRN padrão', scenarioDefaultPrnTooltip: 'PRN padrão selecionado para este cenário', selectGeneric: 'Selecione',
    comparisonWithScenarioA: 'Comparação com o cenário A', maxDifference: 'MAIOR DIFERENÇA', peakDifference: 'DIFERENÇA DE PICO', integratedAvgDiff: 'DIF. MÉDIA INTEGRADA',
    peakOfPattern: 'PICO DO PADRÃO', peakAngleLabel: 'ÂNGULO DO PICO', integratedAverageLabel: 'MÉDIA INTEGRADA', beamwidth3db: 'LARGURA −3 dB', profilePointsLabel: 'PONTOS DO PERFIL', unitNotInformed: 'unidade não informada',
    distanceAxis: 'Distância (m)', altitudeAxis: 'Altitude (m)', pointsWord: 'pontos', compatibleBand: 'banda compatível', projectDefault: 'padrão do projeto',
    openSourceCollab: 'COLABORAÇÃO OPEN SOURCE',
    heroEyebrow: 'PROJETO OPEN SOURCE', heroMaintainedBy: 'Projeto mantido pelo', heroDevContributions: 'Desenvolvimento e contribuições técnicas:', heroAuthorBio: 'Radioamador, doutor pelo IFSC/USP, atua com Large Language Models na UFSCar e participa de competições de segurança da informação e CTF pela Epic Leet.', heroOriginalProject: 'Projeto original no GitHub ↗', heroWebIntegration: 'Integração da versão web:', heroWebAuthorBio: 'Analista de sistemas e radioamador, responsável pela transformação do OpenHFTA em uma aplicação web moderna, com API, interface gráfica, análises comparativas, métricas e visualização dos resultados.',
    footerMaintained: 'Projeto mantido pelo Rio DX Group · Desenvolvimento técnico:', footerWebIntegration: 'Integração web: Fernando Fernandes —',
  },
  en: {
    language: 'Language', accessibleColors: 'Accessible colors', accessiblePatterns: 'Lines and symbols', online: 'Fortran core online',
    heroTitle: 'See how terrain', heroTitleEm: 'shapes the signal.', heroLede: 'Upload a terrain profile and explore your antenna elevation pattern in seconds.',
    helpImprove: 'Help improve OpenHFTA', feedbackBanner: 'Found something unusual or have a suggestion? Your experience helps make the tool more useful to the whole community.', sendSuggestion: 'Send suggestion',
    configuration: 'Configuration', defineScenario: 'Define the analysis scenario', explainFields: 'Explain the form fields', uploadProfile: 'Drop your .PRO profile here', browseComputer: 'or click to browse your computer',
    frequency: 'Frequency', units: 'Units', meters: 'Meters', feet: 'Feet', antennaHeights: 'Antenna heights', antennaType: 'Antenna type', polarization: 'Polarization', terrainType: 'Terrain type', soilPermittivity: 'Ground dielectric constant', soilConductivity: 'Ground conductivity (S/m)', towerOffset: 'Tower offset',
    includeDiffraction: 'Include diffraction in the calculation', compareScenarios: 'Compare scenarios', calculate: 'Run analysis', calculating: 'Calculating...',
    result: 'Result', waitingAnalysis: 'Waiting for an analysis', patternCalculated: 'Pattern calculated by the HFTA core', comparisonCalculated: 'Comparison calculated by the HFTA core', processing: 'Processing analysis…',
    terrainProfile: 'TERRAIN PROFILE', rayTraceCore: 'CORE RAY TRACE', export: 'EXPORT', emptyTitle: 'Your pattern will appear here', emptyText: 'Complete the configuration and run the first analysis.',
    elevation: 'Elevation (°)', elevationStats: 'Elevation statistics (%)', height: 'Height (m)', distance: 'Distance (m)', gain: 'Gain (dB)', nullsLabel: 'Nulls',
    noDiffraction: 'Diffraction disabled', diffraction: 'Diffraction included', automaticReading: 'AUTOMATIC READING', modelLimits: 'MODEL LIMITS',
    explainResult: '✦ Explain result with AI', interpreting: 'Interpreting...', quickGuide: 'QUICK GUIDE', close: 'Close', helpTitle: 'What does each field mean?', helpIntro: 'These parameters describe an HF antenna elevation-pattern analysis over a terrain profile. The core calculates internally in feet, but you can enter and interpret values in meters.', helpTip: 'Getting started', rayHelpTitle: 'How should the paths be read?', rayHelpIntro: 'The chart shows geometric paths calculated over the profile. The line represents the path; by itself, it is not a measurement of received power.', rayTip: 'Chart interactions',
    explainTerrainTypes: 'Explain terrain types', soilHelpTitle: 'What does each terrain type mean?', soilHelpIntro: "Each terrain type fills the ground dielectric constant and conductivity (S/m) with reference values from the classic ground-type table used in antenna modeling (the same lineage cited by the ARRL Antenna Book). Pick the closest match for your location or adjust the fields manually.", soilHelpTip: 'How to choose',
    feedbackTitle: 'Tell us how we can improve', feedbackIntro: 'Suggestions, corrections, and ideas for new features are welcome. If you want a reply, provide your email; it will only be used to respond to this message.',
    optionalName: 'Name (optional)', replyEmail: 'Reply email address', subject: 'Subject', message: 'Message', sendMessage: 'Send message', sending: 'Sending…', securityCheck: 'Security check to prevent automated messages.', newSuggestion: 'Send another suggestion',
    footer: 'preserving HFTA intelligence for modern systems',
    errProfileRequired: 'Select a .PRO file before analyzing.', errSharedProfileRequired: 'Select a shared .PRO in the form.', errAllScenarioProfiles: 'Provide a .PRO for every scenario.', errSharedPrnRequired: 'Provide a shared .PRN file or select a default PRN.', errAllScenarioPrns: 'Provide a .PRN for every scenario or select a default PRN for each one.',
    errAnalysisFailed: 'Could not run the analysis.', errApiGeneric: 'API communication error.', errAiExplain: 'Could not get the AI explanation.', errAiFailed: 'Failed to query the AI.', errFeedbackSend: 'Could not send your message.', feedbackThanksDefault: 'Thanks for your feedback! Your message was sent.',
    errExportPrn: 'Upload your own .PRN file or select a default PRN from the project.', errExportFailed: 'Could not generate the export.', errProfileIndividualMode: 'The PRO is in individual mode. Select the file inside one of the scenarios.', errPrnIndividualMode: 'The PRN is in individual mode. Select the file inside one of the scenarios.',
    upToFourScenarios: 'Two or more scenarios', sharedPrn: 'Shared PRN', individualPrn: 'Individual PRN', sharedProfile: 'Shared PRO', individualProfile: 'Individual PRO', addScenario: '+ add',
    scenarioHelpText: 'You can provide a `.PRO` on each row. Choose above whether the `.PRO` and `.PRN` are shared across the form or individual per scenario.',
    scenarioNameLabel: 'Scenario name', scenarioNameTooltip: 'Name used in charts and results', scenarioHeightsShort: 'Heights', scenarioHeightsTooltip: 'Height of each element; use spaces between values and * to flip the phase',
    scenarioAntennaLabel: 'Antenna', scenarioAntennaTooltip: 'Antenna model for this scenario', scenarioPolarizationTooltip: 'Polarization calculated for this scenario',
    scenarioProfileLabel: '.PRO profile', scenarioProfileTooltip: 'Terrain profile used in this scenario', topBlockPlaceholder: 'top block', scenarioPrnStatLabel: '.PRN statistics', scenarioPrnTooltip: 'Arrival-angle statistics', filePlaceholder: 'file',
    scenarioDefaultPrnLabel: 'Default PRN', scenarioDefaultPrnTooltip: 'Default PRN selected for this scenario', selectGeneric: 'Select',
    comparisonWithScenarioA: 'Comparison with scenario A', maxDifference: 'MAXIMUM DIFFERENCE', peakDifference: 'PEAK DIFFERENCE', integratedAvgDiff: 'INTEGRATED AVG. DIFF.',
    peakOfPattern: 'PATTERN PEAK', peakAngleLabel: 'PEAK ANGLE', integratedAverageLabel: 'INTEGRATED AVERAGE', beamwidth3db: '−3 dB BEAMWIDTH', profilePointsLabel: 'PROFILE POINTS', unitNotInformed: 'unit not provided',
    distanceAxis: 'Distance (m)', altitudeAxis: 'Altitude (m)', pointsWord: 'points', compatibleBand: 'compatible band', projectDefault: 'project default',
    openSourceCollab: 'OPEN SOURCE COLLABORATION',
    heroEyebrow: 'OPEN SOURCE PROJECT', heroMaintainedBy: 'Project maintained by', heroDevContributions: 'Development and technical contributions:', heroAuthorBio: 'Ham radio operator, PhD from IFSC/USP, works with Large Language Models at UFSCar and takes part in information-security and CTF competitions with Epic Leet.', heroOriginalProject: 'Original project on GitHub ↗', heroWebIntegration: 'Web version integration:', heroWebAuthorBio: 'Systems analyst and ham radio operator, responsible for turning OpenHFTA into a modern web application, with an API, graphical interface, comparative analyses, metrics, and result visualization.',
    footerMaintained: 'Project maintained by Rio DX Group · Technical development:', footerWebIntegration: 'Web integration: Fernando Fernandes —',
  },
  es: {
    language: 'Idioma', accessibleColors: 'Colores accesibles', accessiblePatterns: 'Líneas y símbolos', online: 'núcleo Fortran conectado',
    heroTitle: 'Vea cómo el terreno', heroTitleEm: 'moldea la señal.', heroLede: 'Cargue un perfil de terreno y explore el patrón de elevación de su antena en segundos.',
    helpImprove: 'Ayude a mejorar OpenHFTA', feedbackBanner: '¿Encontró algo extraño o tiene una sugerencia? Su experiencia ayuda a que la herramienta sea más útil para toda la comunidad.', sendSuggestion: 'Enviar sugerencia',
    configuration: 'Configuración', defineScenario: 'Defina el escenario de análisis', explainFields: 'Explicar los campos del formulario', uploadProfile: 'Suelte aquí su perfil .PRO', browseComputer: 'o haga clic para buscar en el equipo',
    frequency: 'Frecuencia', units: 'Unidad', meters: 'Metros', feet: 'Pies', antennaHeights: 'Alturas de la antena', antennaType: 'Tipo de antena', polarization: 'Polarización', terrainType: 'Tipo de terreno', soilPermittivity: 'Constante dieléctrica del suelo', soilConductivity: 'Conductividad del suelo (S/m)', towerOffset: 'Desplazamiento de la torre',
    includeDiffraction: 'Incluir difracción en el cálculo', compareScenarios: 'Comparar escenarios', calculate: 'Ejecutar análisis', calculating: 'Calculando...',
    result: 'Resultado', waitingAnalysis: 'Esperando un análisis', patternCalculated: 'Patrón calculado por el núcleo HFTA', comparisonCalculated: 'Comparación calculada por el núcleo HFTA', processing: 'Procesando análisis…',
    terrainProfile: 'PERFIL DEL TERRENO', rayTraceCore: 'TRAZADO DE RAYOS DEL NÚCLEO', export: 'EXPORTAR', emptyTitle: 'Su patrón aparecerá aquí', emptyText: 'Complete la configuración y ejecute el primer análisis.',
    elevation: 'Elevación (°)', elevationStats: 'Estadística de elevación (%)', height: 'Altura (m)', distance: 'Distancia (m)', gain: 'Ganancia (dB)', nullsLabel: 'Nulos',
    noDiffraction: 'Difracción desactivada', diffraction: 'Difracción incluida', automaticReading: 'LECTURA AUTOMÁTICA', modelLimits: 'LÍMITES DEL MODELO',
    explainResult: '✦ Explicar resultado con IA', interpreting: 'Interpretando...', quickGuide: 'GUÍA RÁPIDA', close: 'Cerrar', helpTitle: '¿Qué significa cada campo?', helpIntro: 'Estos parámetros describen un análisis del patrón de elevación de una antena HF sobre un perfil del terreno. El núcleo calcula internamente en pies, pero puede introducir e interpretar los valores en metros.', helpTip: 'Para comenzar', rayHelpTitle: '¿Cómo se leen las trayectorias?', rayHelpIntro: 'El gráfico muestra trayectorias geométricas calculadas sobre el perfil. La línea representa el recorrido; por sí sola no es una medición de potencia recibida.', rayTip: 'Interacciones del gráfico',
    explainTerrainTypes: 'Explicar tipos de terreno', soilHelpTitle: '¿Qué significa cada tipo de terreno?', soilHelpIntro: 'Cada tipo de terreno completa la constante dieléctrica del suelo y la conductividad (S/m) con valores de referencia de la tabla clásica de tipos de terreno usada en modelado de antenas (la misma línea citada por el ARRL Antenna Book). Elija el más parecido a su ubicación o ajuste los campos manualmente.', soilHelpTip: 'Cómo elegir',
    feedbackTitle: 'Cuéntenos cómo podemos mejorar', feedbackIntro: 'Las sugerencias, correcciones e ideas para nuevas funciones son bienvenidas. Si desea una respuesta, indique su correo; se usará únicamente para responder a este mensaje.',
    optionalName: 'Nombre (opcional)', replyEmail: 'Correo electrónico de respuesta', subject: 'Asunto', message: 'Mensaje', sendMessage: 'Enviar mensaje', sending: 'Enviando…', securityCheck: 'Verificación de seguridad para evitar mensajes automáticos.', newSuggestion: 'Enviar otra sugerencia',
    footer: 'preservando la inteligencia de HFTA para sistemas modernos',
    errProfileRequired: 'Seleccione un archivo .PRO antes de analizar.', errSharedProfileRequired: 'Seleccione un .PRO compartido en el formulario.', errAllScenarioProfiles: 'Indique un .PRO en todos los escenarios.', errSharedPrnRequired: 'Indique un archivo .PRN compartido o seleccione un PRN predeterminado.', errAllScenarioPrns: 'Indique un .PRN en todos los escenarios o seleccione un PRN predeterminado para cada uno.',
    errAnalysisFailed: 'No fue posible ejecutar el análisis.', errApiGeneric: 'Error de comunicación con la API.', errAiExplain: 'No fue posible obtener la explicación de la IA.', errAiFailed: 'Fallo al consultar la IA.', errFeedbackSend: 'No fue posible enviar su mensaje.', feedbackThanksDefault: '¡Gracias por colaborar! Su mensaje fue enviado.',
    errExportPrn: 'Cargue su propio archivo .PRN o seleccione un PRN predeterminado del proyecto.', errExportFailed: 'No fue posible generar la exportación.', errProfileIndividualMode: 'El PRO está en modo individual. Seleccione el archivo dentro de uno de los escenarios.', errPrnIndividualMode: 'El PRN está en modo individual. Seleccione el archivo dentro de uno de los escenarios.',
    upToFourScenarios: 'Dos o más escenarios', sharedPrn: 'PRN compartido', individualPrn: 'PRN individual', sharedProfile: 'PRO compartido', individualProfile: 'PRO individual', addScenario: '+ agregar',
    scenarioHelpText: 'Puede indicar un `.PRO` en cada fila. Elija arriba si el `.PRO` y el `.PRN` serán compartidos por el formulario o individuales por escenario.',
    scenarioNameLabel: 'Nombre del escenario', scenarioNameTooltip: 'Nombre usado en los gráficos y resultados', scenarioHeightsShort: 'Alturas', scenarioHeightsTooltip: 'Altura de cada elemento; use espacios entre valores y * para invertir la fase',
    scenarioAntennaLabel: 'Antena', scenarioAntennaTooltip: 'Modelo de antena de este escenario', scenarioPolarizationTooltip: 'Polarización calculada para este escenario',
    scenarioProfileLabel: 'Perfil .PRO', scenarioProfileTooltip: 'Perfil de terreno usado en este escenario', topBlockPlaceholder: 'bloque superior', scenarioPrnStatLabel: 'Estadística .PRN', scenarioPrnTooltip: 'Estadística de los ángulos de llegada', filePlaceholder: 'archivo',
    scenarioDefaultPrnLabel: 'PRN predeterminado', scenarioDefaultPrnTooltip: 'PRN predeterminado seleccionado para este escenario', selectGeneric: 'Seleccione',
    comparisonWithScenarioA: 'Comparación con el escenario A', maxDifference: 'DIFERENCIA MÁXIMA', peakDifference: 'DIFERENCIA DE PICO', integratedAvgDiff: 'DIF. MEDIA INTEGRADA',
    peakOfPattern: 'PICO DEL PATRÓN', peakAngleLabel: 'ÁNGULO DEL PICO', integratedAverageLabel: 'MEDIA INTEGRADA', beamwidth3db: 'ANCHO DE HAZ −3 dB', profilePointsLabel: 'PUNTOS DEL PERFIL', unitNotInformed: 'unidad no informada',
    distanceAxis: 'Distancia (m)', altitudeAxis: 'Altitud (m)', pointsWord: 'puntos', compatibleBand: 'banda compatible', projectDefault: 'predeterminado del proyecto',
    openSourceCollab: 'COLABORACIÓN OPEN SOURCE',
    heroEyebrow: 'PROYECTO OPEN SOURCE', heroMaintainedBy: 'Proyecto mantenido por', heroDevContributions: 'Desarrollo y contribuciones técnicas:', heroAuthorBio: 'Radioaficionado, doctor por el IFSC/USP, trabaja con Large Language Models en la UFSCar y participa en competiciones de seguridad de la información y CTF con Epic Leet.', heroOriginalProject: 'Proyecto original en GitHub ↗', heroWebIntegration: 'Integración de la versión web:', heroWebAuthorBio: 'Analista de sistemas y radioaficionado, responsable de transformar OpenHFTA en una aplicación web moderna, con API, interfaz gráfica, análisis comparativos, métricas y visualización de resultados.',
    footerMaintained: 'Proyecto mantenido por Rio DX Group · Desarrollo técnico:', footerWebIntegration: 'Integración web: Fernando Fernandes —',
  },
}

function initialLocale(): Locale {
  const saved = window.localStorage.getItem('openhfta-locale')
  return saved === 'en' || saved === 'es' || saved === 'pt-BR' ? saved : 'pt-BR'
}

const DEFAULT_PALETTE: ColorPalette = { rays: { direct: '#287bb0', reflected: '#78b7d9', diffracted: '#174f91', reflected_diffracted: '#f2a65a', double_diffracted: '#102f59', reflected_double_diffracted: '#c58cff' }, scenarios: ['#f2a65a', '#6bd48b', '#78b7d9', '#c58cff', '#ff7a8a', '#f0e06a', '#4fd1c5', '#b0bec5'], flatScenarios: ['#c76b5a', '#4f9f78', '#5f8fa8', '#9a6bc0', '#b85563', '#b3a64a', '#38958c', '#7f8c91'], terrain: '#171717', flat: '#d93636', aoa: '#d92fc4', event: '#f2a65a', corner: '#ff594f', antenna: '#f2a65a' }
const COLORBLIND_PALETTE: ColorPalette = { rays: { direct: '#0072b2', reflected: '#56b4e9', diffracted: '#d55e00', reflected_diffracted: '#e69f00', double_diffracted: '#cc79a7', reflected_double_diffracted: '#f0e442' }, scenarios: ['#0072b2', '#e69f00', '#009e73', '#cc79a7', '#d55e00', '#56b4e9', '#f0e442', '#999999'], flatScenarios: ['#d55e00', '#56b4e9', '#f0e442', '#0072b2', '#e69f00', '#009e73', '#cc79a7', '#666666'], terrain: '#222222', flat: '#d55e00', aoa: '#009e73', event: '#e69f00', corner: '#cc79a7', antenna: '#0072b2' }
const SCENARIO_DASHES = ['solid', 'dash', 'dot', 'dashdot'] as const
// Once the colors run out, later scenarios reuse them with another dash style.
const scenarioDash = (index: number, accessible: boolean, colorCount: number) => SCENARIO_DASHES[(accessible ? index : Math.floor(index / colorCount)) % SCENARIO_DASHES.length]
const SCENARIO_SYMBOLS = ['circle', 'square', 'diamond', 'triangle-up'] as const
const RAY_DASHES: Record<string, 'solid' | 'dash' | 'dot' | 'dashdot'> = { direct: 'solid', reflected: 'dash', diffracted: 'dot', reflected_diffracted: 'dashdot', double_diffracted: 'dashdot', reflected_double_diffracted: 'dashdot' }
const RAY_LABELS_BY_LOCALE: Record<Locale, Record<string, string>> = {
  'pt-BR': { direct: 'Direto', reflected: 'Reflexão', diffracted: 'Difração', reflected_diffracted: 'Reflexão + difração', double_diffracted: 'Difração dupla', reflected_double_diffracted: 'Reflexão + dupla difração' },
  en: { direct: 'Direct', reflected: 'Reflection', diffracted: 'Diffraction', reflected_diffracted: 'Reflection + diffraction', double_diffracted: 'Double diffraction', reflected_double_diffracted: 'Reflection + double diffraction' },
  es: { direct: 'Directo', reflected: 'Reflexión', diffracted: 'Difracción', reflected_diffracted: 'Reflexión + difracción', double_diffracted: 'Doble difracción', reflected_double_diffracted: 'Reflexión + doble difracción' },
}
const RAY_LIMIT_UI_BY_LOCALE: Record<Locale, { group: string; upTo: string; all: string }> = {
  'pt-BR': { group: 'Limite dos ângulos exibidos', upTo: 'Exibir até', all: 'Exibir todos' },
  en: { group: 'Displayed angle limit', upTo: 'Show up to', all: 'Show all' },
  es: { group: 'Límite de los ángulos mostrados', upTo: 'Mostrar hasta', all: 'Mostrar todos' },
}
const RAY_UI_BY_LOCALE: Record<Locale, { title: string; distance: string; height: string; elevation: string; visible: string; calculated: string; profile: string; explain: string; departureAngle: string; antennaGain: string; terrainPointLabel: string; reflectionPointHover: string; directionChangeLabel: string; antennaLabel: string; terrainLabel: string }> = {
  'pt-BR': { title: 'TRAÇADO DE RAIOS', distance: 'Distância (m)', height: 'Altura (m)', elevation: 'Elevação (°)', visible: 'trajetórias visíveis', calculated: 'calculadas', profile: 'perfil', explain: 'Explicar os tipos de trajetória', departureAngle: 'ângulo de saída', antennaGain: 'ganho da antena', terrainPointLabel: 'Ponto no terreno', reflectionPointHover: 'Ponto de reflexão/difração', directionChangeLabel: 'Mudança de direção', antennaLabel: 'Antena', terrainLabel: 'TERRENO' },
  en: { title: 'RAY TRACE', distance: 'Distance (m)', height: 'Height (m)', elevation: 'Elevation (°)', visible: 'visible paths', calculated: 'calculated', profile: 'profile', explain: 'Explain path types', departureAngle: 'departure angle', antennaGain: 'antenna gain', terrainPointLabel: 'Terrain point', reflectionPointHover: 'Reflection/diffraction point', directionChangeLabel: 'Direction change', antennaLabel: 'Antenna', terrainLabel: 'TERRAIN' },
  es: { title: 'TRAZADO DE RAYOS', distance: 'Distancia (m)', height: 'Altura (m)', elevation: 'Elevación (°)', visible: 'trayectorias visibles', calculated: 'calculadas', profile: 'perfil', explain: 'Explicar los tipos de trayectoria', departureAngle: 'ángulo de salida', antennaGain: 'ganancia de la antena', terrainPointLabel: 'Punto en el terreno', reflectionPointHover: 'Punto de reflexión/difracción', directionChangeLabel: 'Cambio de dirección', antennaLabel: 'Antena', terrainLabel: 'TERRENO' },
}
const RAY_LABELS = RAY_LABELS_BY_LOCALE['pt-BR']
const RAY_KINDS = Object.keys(RAY_LABELS)
const rayWithinLimit = (angle: number, limit: number | null) => limit === null || Math.abs(angle) <= limit

function gainAt(angles: number[], pattern: number[], angle: number) {
  if (!angles.length || !pattern.length) return 0
  const target = Math.abs(angle)
  let nearest = 0
  let distance = Infinity
  angles.forEach((candidate, index) => { const current = Math.abs(candidate - target); if (current < distance) { distance = current; nearest = index } })
  return pattern[nearest] || 0
}

function summarizeRayTrace(rayTrace?: Result['ray_trace']) {
  if (!rayTrace) return null
  const angle_ranges: Record<string, { min_deg: number; max_deg: number }> = {}
  for (const kind of Object.keys(rayTrace.counts || {})) {
    const angles = rayTrace.paths.filter(path => path.kind === kind).map(path => path.angle_deg)
    if (angles.length) angle_ranges[kind] = { min_deg: Math.min(...angles), max_deg: Math.max(...angles) }
  }
  return { available: rayTrace.available, counts: rayTrace.counts, angle_ranges }
}

const BAND_RANGES_MHZ: [string, number, number][] = [['160m', 1.8, 2], ['80m', 3.5, 4], ['60m', 5.3, 5.4], ['40m', 7, 7.3], ['30m', 10.1, 10.15], ['20m', 14, 14.35], ['17m', 18.068, 18.168], ['15m', 21, 21.45], ['12m', 24.89, 24.99], ['10m', 28, 29.7], ['6m', 50, 54]]

function scenarioBand(scenario: Scenario) {
  const frequency = scenario.configuration?.frequency_mhz
  if (scenario.aoa?.band) return scenario.aoa.band
  if (frequency == null) return ''
  return BAND_RANGES_MHZ.find(([, low, high]) => frequency >= low && frequency <= high)?.[0] || `${frequency.toFixed(2)} MHz`
}

function scenarioHeights(scenario: Scenario, locale: Locale) {
  const typed = scenario.heights_input?.trim().split(/[\s,]+/).filter(Boolean) || []
  // Prefer the heights the core actually used (always metres); keep the typed "*" phase marks.
  const metres = scenario.configuration?.antenna_heights_m
  const heights = metres?.length ? metres.map((height, index) => `${Number(height.toFixed(1))}${typed[index]?.endsWith('*') ? '*' : ''}`) : typed
  if (!heights.length) return ''
  const word = locale === 'en' ? (heights.length > 1 ? 'heights' : 'height') : (heights.length > 1 ? 'alturas' : 'altura')
  return `${word} ${heights.join(' / ')} m`
}

// "Name — band · antenna height(s) · terrain": the name stands apart from its attributes.
function scenarioNameLabel(scenario: Scenario, locale: Locale, terrain: string | null | undefined = scenario.profile_name) {
  const details = [scenarioBand(scenario), scenarioHeights(scenario, locale), terrain].filter(Boolean).join(' · ')
  return details ? `${scenario.name} — ${details}` : scenario.name
}

function scenarioDisplayLabel(scenario: Scenario, locale: Locale) {
  return `${scenarioNameLabel(scenario, locale, scenario.antenna_type)} · PRO: ${scenario.profile_name || 'compartilhado'} · PRN: ${scenario.prn_name || 'compartilhado'}`
}

function ScenarioRayTrace({ scenario, index, angles, rayKinds, rayAngleLimit, onToggle, onHelp, accessibleColors, accessiblePatterns, locale }: { scenario: Scenario; index: number; angles: number[]; rayKinds: Record<string, boolean>; rayAngleLimit: number | null; onToggle: (kind: string) => void; onHelp: () => void; accessibleColors: boolean; accessiblePatterns: boolean; locale: Locale }) {
  if (!scenario.ray_trace?.available || !scenario.profile) return null
  const labels = RAY_LABELS_BY_LOCALE[locale]
  const rayUi = RAY_UI_BY_LOCALE[locale]
  const palette = accessibleColors ? COLORBLIND_PALETTE : DEFAULT_PALETTE
  const colors = palette.rays
  const count = Math.min(scenario.profile.points, scenario.profile.distances_m.length, scenario.profile.heights_m.length)
  const distances = scenario.profile.distances_m.slice(0, count)
  const terrain = scenario.profile.heights_m.slice(0, count)
  const end = distances[distances.length - 1] || 0
  const axisEnd = Math.max(500, Math.ceil(end / 500) * 500)
  const terrainAt = (x: number) => { for (let i = 1; i < distances.length; i += 1) if (x <= distances[i]) { const q = distances[i] === distances[i - 1] ? 0 : (x - distances[i - 1]) / (distances[i] - distances[i - 1]); return terrain[i - 1] + (terrain[i] - terrain[i - 1]) * q } return terrain[terrain.length - 1] || 0 }
  const antennaPattern = scenario.flat_pattern_db || scenario.pattern_db
  const paths = scenario.ray_trace?.paths.filter(path => RAY_KINDS.includes(path.kind) && rayKinds[path.kind] !== false && rayWithinLimit(path.angle_deg, rayAngleLimit)) || []
  const clip = (path: NonNullable<Result['ray_trace']>['paths'][number]) => path.distances_m.reduce<[number, number][]>((points, x, i) => { if (x <= end && path.heights_m[i] !== undefined) points.push([x, path.heights_m[i]]); return points }, [])
  const visible = paths.map(path => ({ path, points: clip(path) })).filter(item => item.points.length > 1)
  const gains = visible.map(({ path }) => gainAt(angles, antennaPattern, path.angle_deg))
  const lowGain = Math.min(...gains, 0); const highGain = Math.max(...gains, 1)
  const data: any[] = visible.map(({ path, points }, pathIndex) => { const gain = gains[pathIndex]; const weight = highGain === lowGain ? .45 : .14 + .38 * ((gain - lowGain) / (highGain - lowGain)); return { x: points.map(p => p[0]), y: points.map(p => p[1]), type: 'scatter', mode: 'lines', name: labels[path.kind], legendgroup: path.kind, showlegend: visible.findIndex(item => item.path.kind === path.kind) === pathIndex, line: { color: colors[path.kind], width: .65 + weight, opacity: weight, dash: accessiblePatterns ? RAY_DASHES[path.kind] : 'solid' }, hovertemplate: `${labels[path.kind]}<br>${rayUi.departureAngle}: ${path.angle_deg.toFixed(2)}°<br>${rayUi.antennaGain}: ${gain.toFixed(1)} dB<br>%{x:.0f} m · %{y:.1f} m<extra></extra>` } })
  data.push({ x: distances, y: terrain, type: 'scatter', mode: 'lines+markers', name: rayUi.terrainLabel, line: { color: palette.terrain, width: 2 }, marker: { color: palette.terrain, size: 3 }, fill: 'tozeroy', fillcolor: 'rgba(194,174,162,.42)' })
  data.push({ x: [0, end], y: [0, 25], yaxis: 'y2', type: 'scatter', mode: 'lines', line: { color: 'transparent', width: 0 }, opacity: 0, showlegend: false, hoverinfo: 'skip' })
  return <article className="scenario-ray"><div className="terrain-heading"><small>{rayUi.title} · {scenarioDisplayLabel(scenario, locale)}</small><span>{visible.length} {rayUi.visible} · {scenario.ray_trace.paths.length} {rayUi.calculated} · {rayUi.profile} {end.toFixed(0)} m</span><button type="button" className="ray-help-button" onClick={onHelp} aria-label={rayUi.explain}>?</button></div><div className="ray-controls">{Object.entries(labels).map(([kind, label]) => <button type="button" key={`${index}-${kind}`} className={rayKinds[kind] ? 'ray-toggle active' : 'ray-toggle'} onClick={() => onToggle(kind)} style={{ '--ray-color': colors[kind] } as CSSProperties}><i />{label} <small>{scenario.ray_trace?.counts[kind] || 0}</small></button>)}</div><div className="ray-plot-wrap"><div className="degree-scale" aria-label={rayUi.elevation}>{Array.from({ length: 26 }, (_, degree) => <span key={degree}>{degree}°</span>)}</div><Plot className="ray-chart" data={data} layout={{ autosize: true, margin: { l: 62, r: 100, t: 42, b: 54 }, title: { text: 'RAY TRACE OVER TERRAIN', font: { size: 13, color: '#7dff9b' } }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: rayUi.distance }, range: [0, axisEnd], dtick: 500, gridcolor: '#263943' }, yaxis: { title: { text: rayUi.height }, range: [Math.max(0, Math.min(...terrain) - 30), 1000], dtick: 100, gridcolor: '#263943' }, yaxis2: { title: { text: rayUi.elevation }, overlaying: 'y', anchor: 'x', side: 'right', range: [0, 25], tickmode: 'linear', dtick: 1, ticksuffix: '°', showticklabels: false, showline: false, showgrid: false, zeroline: false, ticks: '' }, legend: { orientation: 'h' as const, y: -.15 } }} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '100%' }} /></div></article>
}

const helpItems = [
  ['Perfil .PRO', 'Arquivo com as distâncias e altitudes do terreno entre a estação e o horizonte analisado. Ele é a base geométrica do cálculo.'],
  ['Estatística de elevação (.PRN)', 'Arquivo com a distribuição percentual dos ângulos de chegada dos sinais para cada banda. A coluna compatível com a frequência selecionada aparece como barras no gráfico e é usada para calcular o Figure of Merit.'],
  ['Frequência', 'Informe a banda, como 20m, ou a frequência em MHz, como 14.2. A frequência altera o comprimento de onda, a reflexão no solo e a difração.'],
  ['Polarização', 'A análise usa polarização horizontal (H), com o coeficiente de reflexão TE no solo.'],
  ['Unidade', 'Unidade usada nos campos de altura e deslocamento da torre. Escolha metros ou pés; a conversão interna para o núcleo Fortran é automática.'],
  ['Alturas da antena', 'Altura de cada elemento da antena em relação ao terreno. Separe elementos por espaço. Um asterisco após a altura indica fase invertida, por exemplo 10*.'],
  ['Tipo de antena', 'Modelo de antena usado pelo OpenHFTA: dipolo ou conjunto direcional de 2, 3, 4, 5, 6 ou 8 elementos. Isso muda o padrão de elevação calculado.'],
  ['Empilhamento (stack)', 'Para simular antenas empilhadas na mesma torre, informe de duas a quatro alturas separadas por espaço no campo de alturas: 10 20 representa duas antenas iguais, a 10 m e a 20 m, alimentadas em fase. Um asterisco inverte a fase daquela antena (10 20*), o que eleva o lóbulo e costuma servir a contatos de curta distância. Todas as antenas usam o mesmo tipo, azimute e perfil .PRO. Para avaliar, use a comparação de cenários com as alturas isoladas (20 e 10), o stack em fase (10 20) e o invertido (10 20*), e veja qual curva tem mais ganho nos ângulos em que as barras do .PRN são mais altas; o Figure of Merit resume isso. O modelo não calcula o acoplamento entre antenas, então espaçamentos menores que meia onda tendem a parecer melhores do que são na prática.'],
  ['Permissividade do solo', 'Capacidade relativa do solo de armazenar energia elétrica. É usada no cálculo da reflexão do sinal. O valor padrão 13 é uma aproximação comum.'],
  ['Condutividade (S/m)', 'Capacidade do solo de conduzir corrente. Solos mais condutivos normalmente refletem o sinal de forma diferente. O valor padrão é 0.005 S/m.'],
  ['Deslocamento da torre', 'Move o ponto inicial da torre para trás no perfil, usando a unidade escolhida. Use para testar outra posição da estação no mesmo terreno.'],
  ['Incluir difração', 'Mantém habilitado o efeito do terreno sobre a propagação HF. Em geral, deixe ligado; desative apenas para comparar a influência da difração.'],
  ['Comparar cenários e azimutes', 'Executa dois ou mais cenários; adicione quantos precisar. Você pode reutilizar um perfil para comparar antenas e alturas, ou selecionar um arquivo .PRO por cenário para representar azimutes diferentes.'],
  ['RMSE', 'Erro quadrático médio da raiz entre duas curvas, em dB. Ele resume a diferença média entre os padrões em todos os ângulos: quanto menor o RMSE, mais parecidas são as curvas. Não indica sozinho qual cenário é melhor.'],
  ['Maior diferença', 'Maior diferença absoluta encontrada entre as duas curvas em qualquer ângulo de elevação. Mostra o pior afastamento pontual entre os cenários, em dB.'],
  ['Diferença de pico', 'Diferença entre os maiores ganhos dos dois cenários, em dB. Valor positivo indica que o cenário comparado tem pico maior que o cenário A; valor negativo indica pico menor.'],
  ['Dif. média integrada', 'Diferença entre os ganhos médios integrados ao longo de toda a faixa angular analisada, em dB. Ajuda a comparar o desempenho geral, não apenas o pico.'],
  ['Pico do padrão', 'Maior ganho encontrado na curva de elevação, informado em dB. Representa o ponto de melhor resposta da antena no perfil analisado.'],
  ['Ângulo do pico', 'Ângulo de elevação em que ocorre o maior ganho do padrão. Ângulos baixos normalmente favorecem contatos de longa distância em HF.'],
  ['Média integrada', 'Média do ganho calculada ao longo de toda a faixa de ângulos analisada. Resume o desempenho geral da curva, e não somente seu maior valor.'],
  ['Largura −3 dB', 'Largura angular do feixe principal medida 3 dB abaixo do pico. Feixe mais estreito indica maior concentração de energia em uma faixa menor de ângulos.'],
  ['Pontos do perfil', 'Quantidade de pontos de distância e altitude efetivamente usados no cálculo e exibidos no gráfico do terreno.'],
  ['Figure of Merit', 'Métrica ponderada pelo arquivo .PRN de estatística de elevação. Combina o ganho da antena com a probabilidade dos ângulos de chegada; quanto maior, melhor a adequação ao cenário estatístico.'],
]

const rayHelpItems = [
  ['Direta', 'Caminho que sai da antena e chega ao horizonte sem tocar o relevo. É a referência de visibilidade geométrica.'],
  ['Reflexão', 'Caminho que toca o terreno e muda de direção segundo a geometria local. O núcleo também aplica o coeficiente de Fresnel, que altera amplitude e fase.'],
  ['Difração', 'Caminho que passa por uma aresta ou ponto de relevo e é calculado pelo modelo UTD. Ele permite a propagação além de uma obstrução.'],
  ['Reflexão + difração', 'Caminho composto: ocorre uma reflexão e uma difração na mesma trajetória. Ele não deve ser contado apenas como reflexão ou apenas como difração.'],
  ['Difração dupla', 'Caminho que passa por duas arestas de relevo em sequência. Os dois pontos de difração são preservados no traçado.'],
  ['Reflexão + dupla difração', 'Caminho composto com duas difrações e uma reflexão no percurso.'],
  ['Como ler o gráfico', 'As linhas mostram a geometria do caminho, não a potência recebida. A espessura/opacidade prioriza trajetórias com maior ganho estimado; os marcadores mostram interações com o terreno.'],
]

const helpItemsByLocale: Record<Locale, string[][]> = {
  'pt-BR': helpItems,
  en: [
    ['.PRO profile', 'File containing terrain distances and elevations between the station and the analyzed horizon. It is the geometric basis of the calculation.'],
    ['Elevation statistics (.PRN)', 'File containing the percentage distribution of signal arrival angles for each band. The column matching the selected frequency is shown as bars and used to calculate the Figure of Merit.'],
    ['Frequency', 'Enter a band such as 20m, or a frequency in MHz such as 14.2. Frequency changes wavelength, ground reflection, and diffraction.'],
    ['Polarization', 'The analysis uses horizontal polarization (H), with the TE ground reflection coefficient.'],
    ['Units', 'Units used for antenna-height and tower-offset fields. Choose meters or feet; conversion to the Fortran core is automatic.'],
    ['Antenna heights', 'Height of each antenna element above the terrain. Separate elements with spaces. An asterisk after a height indicates out-of-phase drive, for example 10*.'],
    ['Antenna type', 'Antenna model used by OpenHFTA: dipole or directional arrays with 2, 3, 4, 5, 6, or 8 elements. This changes the calculated elevation pattern.'],
    ['Stacking', 'To simulate stacked antennas on the same tower, enter two to four heights separated by spaces in the heights field: 10 20 means two identical antennas, at 10 m and 20 m, fed in phase. An asterisk flips the phase of that antenna (10 20*), which raises the lobe and usually suits short-distance contacts. All antennas share the same type, azimuth, and .PRO profile. To evaluate a stack, use scenario comparison with the single heights (20 and 10), the in-phase stack (10 20), and the out-of-phase stack (10 20*), then check which curve has more gain at the angles where the .PRN bars are tallest; the Figure of Merit summarizes this. The model does not compute coupling between antennas, so spacings below half a wavelength tend to look better than they are in practice.'],
    ['Ground dielectric constant', 'Relative ability of the ground to store electrical energy. It is used when calculating signal reflection. The default value 13 is a common approximation.'],
    ['Ground conductivity (S/m)', 'Ground ability to conduct current. More conductive ground generally reflects the signal differently. The default is 0.005 S/m.'],
    ['Tower offset', 'Moves the tower starting point backward along the profile using the selected unit. Use it to test another station position on the same terrain.'],
    ['Include diffraction', 'Keeps terrain effects on HF propagation enabled. Normally leave it on; disable it only to compare diffraction influence.'],
    ['Compare scenarios and azimuths', 'Runs two or more scenarios; add as many as you need. Reuse a profile to compare antennas and heights, or select one .PRO file per scenario for different azimuths.'],
    ['RMSE', 'Root mean square error between two curves, in dB. It summarizes the average difference across all angles; lower RMSE means more similar curves.'],
    ['Maximum difference', 'Largest absolute difference between the two curves at any elevation angle. It shows the worst point-to-point separation, in dB.'],
    ['Peak difference', 'Difference between the highest gains of the two scenarios, in dB. A positive value means the compared scenario has the higher peak.'],
    ['Integrated average difference', 'Difference between integrated average gains across the analyzed angular range, in dB. It compares overall performance, not just the peak.'],
    ['Pattern peak', 'Highest gain found on the elevation curve, reported in dB. It represents the antenna response peak for the analyzed profile.'],
    ['Peak angle', 'Elevation angle where the pattern gain is highest. Lower angles generally favor long-distance HF paths.'],
    ['Integrated average', 'Average gain calculated across the full analyzed angular range. It summarizes overall curve performance.'],
    ['−3 dB beamwidth', 'Main-beam angular width measured 3 dB below the peak. A narrower beam concentrates energy over a smaller angle range.'],
    ['Profile points', 'Number of distance and elevation points actually used in the calculation and shown in the terrain chart.'],
    ['Figure of Merit', 'Metric weighted by the .PRN elevation-statistics file. It combines antenna gain with arrival-angle probability; higher is better for the statistical scenario.'],
  ],
  es: [
    ['Perfil .PRO', 'Archivo con las distancias y elevaciones del terreno entre la estación y el horizonte analizado. Es la base geométrica del cálculo.'],
    ['Estadística de elevación (.PRN)', 'Archivo con la distribución porcentual de los ángulos de llegada de las señales para cada banda. La columna compatible con la frecuencia seleccionada aparece como barras y se usa para calcular el Figure of Merit.'],
    ['Frecuencia', 'Indique una banda, como 20m, o una frecuencia en MHz, como 14.2. La frecuencia cambia la longitud de onda, la reflexión del suelo y la difracción.'],
    ['Polarización', 'El análisis usa polarización horizontal (H), con el coeficiente de reflexión TE en el suelo.'],
    ['Unidad', 'Unidad usada en los campos de altura y desplazamiento de la torre. Elija metros o pies; la conversión al núcleo Fortran es automática.'],
    ['Alturas de la antena', 'Altura de cada elemento de la antena sobre el terreno. Separe los elementos con espacios. Un asterisco después de la altura indica alimentación fuera de fase, por ejemplo 10*.'],
    ['Tipo de antena', 'Modelo de antena usado por OpenHFTA: dipolo o arreglos directivos de 2, 3, 4, 5, 6 u 8 elementos. Esto cambia el patrón de elevación calculado.'],
    ['Apilamiento (stack)', 'Para simular antenas apiladas en la misma torre, indique de dos a cuatro alturas separadas por espacios en el campo de alturas: 10 20 representa dos antenas iguales, a 10 m y 20 m, alimentadas en fase. Un asterisco invierte la fase de esa antena (10 20*), lo que eleva el lóbulo y suele servir para contactos de corta distancia. Todas las antenas usan el mismo tipo, azimut y perfil .PRO. Para evaluar, use la comparación de escenarios con las alturas aisladas (20 y 10), el stack en fase (10 20) y el invertido (10 20*), y vea qué curva tiene más ganancia en los ángulos donde las barras del .PRN son más altas; el Figure of Merit lo resume. El modelo no calcula el acoplamiento entre antenas, por lo que las separaciones menores que media onda tienden a parecer mejores de lo que son en la práctica.'],
    ['Constante dieléctrica del suelo', 'Capacidad relativa del suelo para almacenar energía eléctrica. Se usa en el cálculo de la reflexión de la señal. El valor predeterminado 13 es una aproximación común.'],
    ['Conductividad del suelo (S/m)', 'Capacidad del suelo para conducir corriente. Los suelos más conductivos normalmente reflejan la señal de forma diferente. El valor predeterminado es 0.005 S/m.'],
    ['Desplazamiento de la torre', 'Mueve el punto inicial de la torre hacia atrás en el perfil usando la unidad elegida. Úselo para probar otra posición de la estación en el mismo terreno.'],
    ['Incluir difracción', 'Mantiene habilitado el efecto del terreno sobre la propagación HF. Normalmente déjelo activado; desactívelo solo para comparar la influencia de la difracción.'],
    ['Comparar escenarios y azimuts', 'Ejecuta dos o más escenarios; agregue los que necesite. Puede reutilizar un perfil para comparar antenas y alturas, o seleccionar un archivo .PRO por escenario para distintos azimuts.'],
    ['RMSE', 'Error cuadrático medio entre dos curvas, en dB. Resume la diferencia media en todos los ángulos; un RMSE menor indica curvas más parecidas.'],
    ['Diferencia máxima', 'Mayor diferencia absoluta entre las dos curvas en cualquier ángulo de elevación. Muestra la separación puntual más grande, en dB.'],
    ['Diferencia de pico', 'Diferencia entre las mayores ganancias de los dos escenarios, en dB. Un valor positivo indica que el escenario comparado tiene el pico mayor.'],
    ['Diferencia media integrada', 'Diferencia entre las ganancias medias integradas en todo el rango angular analizado, en dB. Compara el rendimiento general, no solo el pico.'],
    ['Pico del patrón', 'Mayor ganancia encontrada en la curva de elevación, expresada en dB. Representa la mejor respuesta de la antena para el perfil analizado.'],
    ['Ángulo del pico', 'Ángulo de elevación donde la ganancia del patrón es máxima. Los ángulos bajos normalmente favorecen los contactos HF de larga distancia.'],
    ['Media integrada', 'Ganancia media calculada en todo el rango de ángulos analizado. Resume el rendimiento general de la curva.'],
    ['Ancho de haz −3 dB', 'Ancho angular del haz principal medido 3 dB por debajo del pico. Un haz más estrecho concentra la energía en un rango menor de ángulos.'],
    ['Puntos del perfil', 'Cantidad de puntos de distancia y elevación usados en el cálculo y mostrados en el gráfico del terreno.'],
    ['Figure of Merit', 'Métrica ponderada por el archivo .PRN de estadística de elevación. Combina la ganancia de la antena con la probabilidad de los ángulos de llegada; cuanto mayor, mejor.'],
  ],
}

const rayHelpItemsByLocale: Record<Locale, string[][]> = {
  'pt-BR': rayHelpItems,
  en: [
    ['Direct', 'Path leaving the antenna and reaching the horizon without touching the terrain. It is the geometric-visibility reference.'],
    ['Reflection', 'Path that touches the terrain and changes direction according to local geometry. The core also applies the Fresnel coefficient, which changes amplitude and phase.'],
    ['Diffraction', 'Path passing an edge or terrain feature calculated with the UTD model. It allows propagation beyond an obstruction.'],
    ['Reflection + diffraction', 'Composite path with one reflection and one diffraction. It should not be counted as reflection or diffraction alone.'],
    ['Double diffraction', 'Path passing two terrain edges in sequence. Both diffraction points are preserved in the trace.'],
    ['Reflection + double diffraction', 'Composite path with two diffractions and one reflection.'],
    ['Reading the chart', 'Lines show path geometry, not received power. Thickness and opacity prioritize paths with higher estimated gain; markers show terrain interactions.'],
  ],
  es: [
    ['Directo', 'Trayectoria que sale de la antena y llega al horizonte sin tocar el relieve. Es la referencia de visibilidad geométrica.'],
    ['Reflexión', 'Trayectoria que toca el terreno y cambia de dirección según la geometría local. El núcleo también aplica el coeficiente de Fresnel, que modifica la amplitud y la fase.'],
    ['Difracción', 'Trayectoria que pasa por un borde o relieve y se calcula con el modelo UTD. Permite la propagación más allá de una obstrucción.'],
    ['Reflexión + difracción', 'Trayectoria compuesta con una reflexión y una difracción. No debe contarse solo como reflexión o solo como difracción.'],
    ['Doble difracción', 'Trayectoria que pasa sucesivamente por dos bordes del relieve. Los dos puntos de difracción se conservan en el trazado.'],
    ['Reflexión + doble difracción', 'Trayectoria compuesta con dos difracciones y una reflexión.'],
    ['Cómo leer el gráfico', 'Las líneas muestran la geometría de la trayectoria, no la potencia recibida. El grosor y la opacidad priorizan las trayectorias con mayor ganancia estimada; los marcadores muestran interacciones con el terreno.'],
  ],
}

const API_URL = import.meta.env.VITE_API_URL || (
  ['5173', '5174'].includes(window.location.port)
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin
)
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''
type SoilPreset = { key: string; epsr: number; sigma: number }
// Values follow the classic NEC ground-type table (conductivity/permittivity
// ranges midpointed), the same lineage cited by the ARRL Antenna Book. The
// "average" entry keeps HFTA's own literal default (5 mS/m, er=13) instead of
// the NEC range midpoint so it matches this app's default soil fields.
const SOIL_PRESETS: SoilPreset[] = [
  { key: 'poor', epsr: 4.5, sigma: 0.001 },
  { key: 'moderate', epsr: 4, sigma: 0.003 },
  { key: 'average', epsr: 13, sigma: 0.005 },
  { key: 'good', epsr: 17, sigma: 0.015 },
  { key: 'sandyCoastal', epsr: 10, sigma: 0.002 },
  { key: 'pastoralHills', epsr: 17, sigma: 0.0065 },
  { key: 'pastoralForest', epsr: 13, sigma: 0.005 },
  { key: 'fertile', epsr: 10, sigma: 0.002 },
  { key: 'richAgricultural', epsr: 15, sigma: 0.01 },
  { key: 'rockySteep', epsr: 12.5, sigma: 0.002 },
  { key: 'marshyWooded', epsr: 12, sigma: 0.0075 },
  { key: 'marshyFlat', epsr: 12, sigma: 0.008 },
  { key: 'mountainous', epsr: 5, sigma: 0.001 },
  { key: 'moistGround', epsr: 30, sigma: 0.0125 },
  { key: 'cityAvg', epsr: 5, sigma: 0.001 },
  { key: 'cityMax', epsr: 3, sigma: 0.0004 },
  { key: 'cityIndustrial', epsr: 3, sigma: 0.0001 },
  { key: 'freshWater', epsr: 80.5, sigma: 0.006 },
  { key: 'freshWater10', epsr: 84, sigma: 0.0055 },
  { key: 'freshWater20', epsr: 80, sigma: 0.0055 },
  { key: 'seaWater', epsr: 80.5, sigma: 4.5 },
  { key: 'seaWater10', epsr: 80, sigma: 4.5 },
  { key: 'seaWater20', epsr: 73, sigma: 4.5 },
  { key: 'seaIce', epsr: 4, sigma: 0.001 },
  { key: 'polarIce', epsr: 3, sigma: 0.00025 },
  { key: 'polarIceCap', epsr: 1, sigma: 0.0001 },
  { key: 'arcticLand', epsr: 3, sigma: 0.0005 },
]
const SOIL_PRESET_LABELS: Record<Locale, Record<string, string>> = {
  'pt-BR': {
    poor: 'Pobre', moderate: 'Moderado', average: 'Média (padrão HFTA)', good: 'Boa',
    sandyCoastal: 'Arenoso, seco (costeiro)', pastoralHills: 'Pasto / colinas férteis', pastoralForest: 'Pasto / colinas com floresta',
    fertile: 'Terra fértil', richAgricultural: 'Solo agrícola rico (colinas baixas)', rockySteep: 'Pedregoso / rochoso, íngreme',
    marshyWooded: 'Pantanoso, densamente arborizado', marshyFlat: 'Pantanoso, arborizado, plano', mountainous: 'Montanhoso (até ~1000 m)',
    moistGround: 'Solo muito úmido', cityAvg: 'Urbano/industrial (atenuação média)', cityMax: 'Urbano/industrial (atenuação máxima)',
    cityIndustrial: 'Urbano/industrial', freshWater: 'Água doce', freshWater10: 'Água doce a 10°C (100 MHz)', freshWater20: 'Água doce a 20°C (100 MHz)',
    seaWater: 'Água do mar', seaWater10: 'Água do mar a 10°C (≤1 GHz)', seaWater20: 'Água do mar a 20°C (≤1 GHz)',
    seaIce: 'Gelo marinho', polarIce: 'Gelo polar', polarIceCap: 'Calota polar', arcticLand: 'Terreno ártico', custom: 'Personalizado',
  },
  en: {
    poor: 'Poor', moderate: 'Moderate', average: 'Average (HFTA default)', good: 'Good',
    sandyCoastal: 'Dry, sandy, flat (coastal)', pastoralHills: 'Pastoral hills, rich soil', pastoralForest: 'Pastoral, medium hills and forestation',
    fertile: 'Fertile land', richAgricultural: 'Rich agricultural land (low hills)', rockySteep: 'Rocky land, steep hills',
    marshyWooded: 'Marshy land, densely wooded', marshyFlat: 'Marshy, forested, flat', mountainous: 'Mountainous/hilly (to ~1000 m)',
    moistGround: 'Highly moist ground', cityAvg: 'City/industrial (average attenuation)', cityMax: 'City/industrial (maximal attenuation)',
    cityIndustrial: 'City/industrial area', freshWater: 'Fresh water', freshWater10: 'Fresh water at 10°C (100 MHz)', freshWater20: 'Fresh water at 20°C (100 MHz)',
    seaWater: 'Sea water', seaWater10: 'Sea water at 10°C (≤1 GHz)', seaWater20: 'Sea water at 20°C (≤1 GHz)',
    seaIce: 'Sea ice', polarIce: 'Polar ice', polarIceCap: 'Polar ice cap', arcticLand: 'Arctic land', custom: 'Custom',
  },
  es: {
    poor: 'Pobre', moderate: 'Moderado', average: 'Media (predeterminado HFTA)', good: 'Buena',
    sandyCoastal: 'Arenoso, seco (costero)', pastoralHills: 'Pastizal / colinas fértiles', pastoralForest: 'Pastizal / colinas con bosque',
    fertile: 'Tierra fértil', richAgricultural: 'Suelo agrícola rico (colinas bajas)', rockySteep: 'Rocoso / pedregoso, empinado',
    marshyWooded: 'Pantanoso, densamente boscoso', marshyFlat: 'Pantanoso, boscoso, plano', mountainous: 'Montañoso (hasta ~1000 m)',
    moistGround: 'Suelo muy húmedo', cityAvg: 'Urbano/industrial (atenuación media)', cityMax: 'Urbano/industrial (atenuación máxima)',
    cityIndustrial: 'Urbano/industrial', freshWater: 'Agua dulce', freshWater10: 'Agua dulce a 10°C (100 MHz)', freshWater20: 'Agua dulce a 20°C (100 MHz)',
    seaWater: 'Agua de mar', seaWater10: 'Agua de mar a 10°C (≤1 GHz)', seaWater20: 'Agua de mar a 20°C (≤1 GHz)',
    seaIce: 'Hielo marino', polarIce: 'Hielo polar', polarIceCap: 'Casquete polar', arcticLand: 'Terreno ártico', custom: 'Personalizado',
  },
}
const SOIL_PRESET_DESCRIPTIONS: Record<Locale, Record<string, string>> = {
  'pt-BR': {
    poor: 'Solo seco e pouco condutor, ex.: rocha nua ou areia muito seca.', moderate: 'Solo seco de condutividade baixa a moderada, entre pobre e médio.',
    average: 'Valor padrão do HFTA, típico de solo comum a levemente melhor que a média.', good: 'Solo bem condutivo, geralmente mais úmido ou rico em minerais.',
    sandyCoastal: 'Solo arenoso e seco, típico de faixa litorânea plana.', pastoralHills: 'Colinas de pasto com solo rico, retém boa umidade.',
    pastoralForest: 'Colinas médias de pasto com cobertura florestal.', fertile: 'Terra agrícola fértil, moderadamente condutiva.',
    richAgricultural: 'Terra agrícola rica em colinas baixas, boa condutividade.', rockySteep: 'Terreno rochoso e íngreme, condutividade baixa a moderada.',
    marshyWooded: 'Área pantanosa e densamente arborizada, alta umidade.', marshyFlat: 'Área pantanosa plana e arborizada.',
    mountainous: 'Terreno montanhoso ou de colinas até ~1000 m de altitude.', moistGround: 'Solo muito úmido, condutividade e permissividade elevadas.',
    cityAvg: 'Área urbana/industrial com atenuação média do RF por construções.', cityMax: 'Área urbana/industrial densa, atenuação máxima do sinal.',
    cityIndustrial: 'Área urbana/industrial genérica, baixa condutividade de solo.', freshWater: 'Corpo de água doce (lago, rio), alta permissividade.',
    freshWater10: 'Água doce a 10°C, medida em 100 MHz.', freshWater20: 'Água doce a 20°C, medida em 100 MHz.',
    seaWater: 'Água do mar, condutividade muito alta.', seaWater10: 'Água do mar a 10°C, até 1 GHz.', seaWater20: 'Água do mar a 20°C, até 1 GHz.',
    seaIce: 'Gelo marinho, baixa condutividade.', polarIce: 'Gelo polar, condutividade muito baixa.', polarIceCap: 'Calota de gelo polar, quase isolante.',
    arcticLand: 'Terreno ártico congelado, baixa condutividade.',
  },
  en: {
    poor: 'Dry, poorly conductive ground, e.g. bare rock or very dry sand.', moderate: 'Dry ground with low-to-moderate conductivity, between poor and average.',
    average: "HFTA's default value, typical of common to slightly better-than-average ground.", good: 'Well-conductive ground, usually moister or mineral-rich.',
    sandyCoastal: 'Dry, sandy ground typical of flat coastal areas.', pastoralHills: 'Pastoral hills with rich soil, holds moisture well.',
    pastoralForest: 'Medium pastoral hills with forest cover.', fertile: 'Fertile farmland, moderately conductive.',
    richAgricultural: 'Rich farmland on low hills, good conductivity.', rockySteep: 'Rocky, steep terrain with low-to-moderate conductivity.',
    marshyWooded: 'Densely wooded marshland, high moisture.', marshyFlat: 'Flat, wooded marshland.',
    mountainous: 'Mountainous or hilly terrain up to about 1000 m.', moistGround: 'Highly moist ground, high conductivity and permittivity.',
    cityAvg: 'Urban/industrial area with average RF attenuation from buildings.', cityMax: 'Dense urban/industrial area with maximal signal attenuation.',
    cityIndustrial: 'Generic urban/industrial area, low ground conductivity.', freshWater: 'Fresh-water body (lake, river), high permittivity.',
    freshWater10: 'Fresh water at 10°C, measured at 100 MHz.', freshWater20: 'Fresh water at 20°C, measured at 100 MHz.',
    seaWater: 'Sea water, very high conductivity.', seaWater10: 'Sea water at 10°C, up to 1 GHz.', seaWater20: 'Sea water at 20°C, up to 1 GHz.',
    seaIce: 'Sea ice, low conductivity.', polarIce: 'Polar ice, very low conductivity.', polarIceCap: 'Polar ice cap, nearly insulating.',
    arcticLand: 'Frozen arctic terrain, low conductivity.',
  },
  es: {
    poor: 'Suelo seco y poco conductor, p. ej. roca desnuda o arena muy seca.', moderate: 'Suelo seco de conductividad baja a moderada, entre pobre y medio.',
    average: 'Valor predeterminado del HFTA, típico de suelo común a algo mejor que el promedio.', good: 'Suelo bien conductor, generalmente más húmedo o rico en minerales.',
    sandyCoastal: 'Suelo arenoso y seco, típico de franjas costeras planas.', pastoralHills: 'Colinas de pastizal con suelo rico, retiene bien la humedad.',
    pastoralForest: 'Colinas medias de pastizal con cobertura forestal.', fertile: 'Tierra agrícola fértil, moderadamente conductora.',
    richAgricultural: 'Tierra agrícola rica en colinas bajas, buena conductividad.', rockySteep: 'Terreno rocoso y empinado, conductividad baja a moderada.',
    marshyWooded: 'Zona pantanosa densamente boscosa, alta humedad.', marshyFlat: 'Zona pantanosa plana y boscosa.',
    mountainous: 'Terreno montañoso o de colinas hasta unos 1000 m.', moistGround: 'Suelo muy húmedo, conductividad y permitividad elevadas.',
    cityAvg: 'Área urbana/industrial con atenuación media de RF por edificaciones.', cityMax: 'Área urbana/industrial densa, atenuación máxima de la señal.',
    cityIndustrial: 'Área urbana/industrial genérica, baja conductividad del suelo.', freshWater: 'Cuerpo de agua dulce (lago, río), alta permitividad.',
    freshWater10: 'Agua dulce a 10°C, medida a 100 MHz.', freshWater20: 'Agua dulce a 20°C, medida a 100 MHz.',
    seaWater: 'Agua de mar, conductividad muy alta.', seaWater10: 'Agua de mar a 10°C, hasta 1 GHz.', seaWater20: 'Agua de mar a 20°C, hasta 1 GHz.',
    seaIce: 'Hielo marino, baja conductividad.', polarIce: 'Hielo polar, conductividad muy baja.', polarIceCap: 'Casquete de hielo polar, casi aislante.',
    arcticLand: 'Terreno ártico congelado, baja conductividad.',
  },
}
const DEFAULT_PRN_OPTIONS = [
  'PP5-AF.PRN', 'PP5-AS.PRN', 'PP5-EU.PRN', 'PP5-JA.PRN', 'PP5-OC.PRN', 'PP5-SA.PRN', 'PP5-US.PRN',
  'PT9-AF.PRN', 'PT9-AS.PRN', 'PT9-BR.PRN', 'PT9-BR-CO.PRN', 'PT9-BR-N.PRN', 'PT9-BR-NE.PRN', 'PT9-BR-S.PRN', 'PT9-BR-SE.PRN', 'PT9-EU.PRN', 'PT9-JA.PRN', 'PT9-OC.PRN', 'PT9-SA.PRN', 'PT9-US.PRN',
  'PY1-AF.PRN', 'PY1-AS.PRN', 'PY1-EU.PRN', 'PY1-JA.PRN', 'PY1-OC.PRN', 'PY1-SA.PRN', 'PY1-US.PRN',
  'PY5-AF.PRN', 'PY5-AS.PRN', 'PY5-EU.PRN', 'PY5-JA.PRN', 'PY5-OC.PRN', 'PY5-SA.PRN', 'PY5-US.PRN',
]

function App() {
  const [locale, setLocale] = useState<Locale>(initialLocale)
  const t = (key: string) => UI_TEXT[locale][key] || UI_TEXT['pt-BR'][key] || key
  const tr = (pt: string, en: string, es: string) => locale === 'en' ? en : locale === 'es' ? es : pt
  const scenarioTag = (index: number) => index < 26 ? String.fromCharCode(65 + index) : String(index + 1)
  const scenarioName = (index: number) => tr(`Cenário ${scenarioTag(index)}`, `Scenario ${scenarioTag(index)}`, `Escenario ${scenarioTag(index)}`)
  const rayUi = RAY_UI_BY_LOCALE[locale]
  const rayLimitUi = RAY_LIMIT_UI_BY_LOCALE[locale]
  const localizedHelpItems = helpItemsByLocale[locale]
  const localizedRayHelpItems = rayHelpItemsByLocale[locale]
  const localizedSoilHelpItems: [string, string][] = SOIL_PRESETS.map(preset => [
    SOIL_PRESET_LABELS[locale][preset.key],
    `${SOIL_PRESET_DESCRIPTIONS[locale][preset.key]} ${tr('Condutividade', 'Conductivity', 'Conductividad')}: ${preset.sigma} S/m · ${tr('Permissividade', 'Permittivity', 'Permitividad')}: ${preset.epsr}`,
  ])
  const [files, setFiles] = useState<File[]>([])
  const [aoaFile, setAoaFile] = useState<File | null>(null)
  const [prnOptions, setPrnOptions] = useState<string[]>([])
  const [selectedPrn, setSelectedPrn] = useState('')
  const [frequency, setFrequency] = useState('20m')
  const [units, setUnits] = useState('meters')
  const [heights, setHeights] = useState('10')
  const [antennaType, setAntennaType] = useState('Dipole')
  const [polarization, setPolarization] = useState<'horizontal' | 'vertical'>('horizontal')
  const [soilEpsr, setSoilEpsr] = useState('13')
  const [soilSigma, setSoilSigma] = useState('0.005')
  const [soilPreset, setSoilPreset] = useState('average')
  const [moveTower, setMoveTower] = useState('0')
  const [noDiffraction, setNoDiffraction] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [prnMode, setPrnMode] = useState<'shared' | 'individual'>('shared')
  const [profileMode, setProfileMode] = useState<'shared' | 'individual'>('shared')
  const [scenarioConfigs, setScenarioConfigs] = useState<ScenarioConfig[]>([
    { name: scenarioName(0), heights: '10', antenna_type: 'Dipole', polarization: 'horizontal' },
    { name: scenarioName(1), heights: '10', antenna_type: 'Dipole', polarization: 'horizontal' },
  ])
  const [scenarioPrnFiles, setScenarioPrnFiles] = useState<(File | null)[]>([null, null])
  const [scenarioProfileFiles, setScenarioProfileFiles] = useState<(File | null)[]>([null, null])
  const [result, setResult] = useState<Result | null>(null)
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiExplanation, setAiExplanation] = useState<AIExplanation | null>(null)
  const [aiError, setAiError] = useState('')
  const [showHelp, setShowHelp] = useState(false)
  const [showRayHelp, setShowRayHelp] = useState(false)
  const [showSoilHelp, setShowSoilHelp] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackName, setFeedbackName] = useState('')
  const [feedbackEmail, setFeedbackEmail] = useState('')
  const [feedbackCategory, setFeedbackCategory] = useState('suggestion')
  const [feedbackMessage, setFeedbackMessage] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState('')
  const [feedbackError, setFeedbackError] = useState('')
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [feedbackFormHidden, setFeedbackFormHidden] = useState(false)
  const [feedbackCountdown, setFeedbackCountdown] = useState(0)
  const [feedbackCaptchaToken, setFeedbackCaptchaToken] = useState('')
  const feedbackCaptchaRef = useRef<HTMLDivElement | null>(null)
  const feedbackWidgetId = useRef<string | null>(null)
  const [colorblindMode, setColorblindMode] = useState(() => window.localStorage.getItem('openhfta-colorblind-mode') === 'true')
  const [accessiblePatterns, setAccessiblePatterns] = useState(() => window.localStorage.getItem('openhfta-accessible-patterns') === 'true')
  const [rayKinds, setRayKinds] = useState<Record<string, boolean>>(() => Object.fromEntries(RAY_KINDS.map(kind => [kind, true])))
  const [rayAngleLimit, setRayAngleLimit] = useState<number | null>(15)
  const file = files[0] || null
  const profilePointCount = (profile?: Result['profile']) => profile
    ? Math.min(profile.points, profile.distances_m.length, profile.heights_m.length)
    : 0
  const antennaTypes = ['Dipole', '2-Ele', '3-Ele', '4-Ele', '5-Ele', '6-Ele', '8-Ele']

  function updateScenario(index: number, patch: Partial<ScenarioConfig>) {
    setScenarioConfigs(current => current.map((scenario, scenarioIndex) => scenarioIndex === index ? { ...scenario, ...patch } : scenario))
  }

  function updateScenarioPrn(index: number, file: File | null) {
    setScenarioPrnFiles(current => current.map((currentFile, fileIndex) => fileIndex === index ? file : currentFile))
    if (file) updateScenario(index, { prn_default: '' })
  }

  function updateScenarioProfile(index: number, file: File | null) {
    if (profileMode === 'shared') return
    setScenarioProfileFiles(current => current.map((currentFile, fileIndex) => fileIndex === index ? file : currentFile))
  }

  function notifySharedResourceClick(event: ReactMouseEvent<HTMLFormElement>) {
    const target = event.target as HTMLElement
    if (compareMode && profileMode === 'individual' && target.closest('.file-drop')) {
      event.preventDefault()
      setError(t('errProfileIndividualMode'))
    } else if (compareMode && prnMode === 'individual' && target.closest('.aoa-upload')) {
      event.preventDefault()
      setError(t('errPrnIndividualMode'))
    }
  }

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) { if (event.key === 'Escape') { setShowHelp(false); setShowRayHelp(false); setShowSoilHelp(false); setShowFeedback(false) } }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])

  useEffect(() => { window.localStorage.setItem('openhfta-colorblind-mode', String(colorblindMode)) }, [colorblindMode])
  useEffect(() => { window.localStorage.setItem('openhfta-accessible-patterns', String(accessiblePatterns)) }, [accessiblePatterns])
  useEffect(() => { window.localStorage.setItem('openhfta-locale', locale); document.documentElement.lang = locale === 'pt-BR' ? 'pt-BR' : locale }, [locale])

  useEffect(() => {
    if (!showFeedback || !TURNSTILE_SITE_KEY) return
    const renderWidget = () => {
      const turnstile = (window as Window & { turnstile?: { render: (element: HTMLElement, options: Record<string, unknown>) => string; reset: (id: string) => void } }).turnstile
      if (!turnstile || !feedbackCaptchaRef.current || feedbackWidgetId.current) return
      feedbackWidgetId.current = turnstile.render(feedbackCaptchaRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        action: 'turnstile-spin-v2',
        theme: 'dark',
        callback: (token: string) => setFeedbackCaptchaToken(token),
        'expired-callback': () => setFeedbackCaptchaToken(''),
        'error-callback': () => setFeedbackCaptchaToken(''),
      })
    }
    if ((window as Window & { turnstile?: unknown }).turnstile) renderWidget()
    else {
      const script = document.querySelector('script[data-openhfta-turnstile]') || document.createElement('script')
      script.setAttribute('src', 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit')
      script.setAttribute('async', '')
      script.setAttribute('defer', '')
      script.setAttribute('data-openhfta-turnstile', 'true')
      script.addEventListener('load', renderWidget, { once: true })
      document.head.appendChild(script)
    }
    return () => {
      feedbackWidgetId.current = null
      setFeedbackCaptchaToken('')
    }
  }, [showFeedback])

  useEffect(() => {
    if (!feedbackSent || feedbackCountdown <= 0) return
    const timer = window.setTimeout(() => setFeedbackCountdown(current => current - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [feedbackSent, feedbackCountdown])

  useEffect(() => {
    if (feedbackSent && feedbackCountdown === 0) setFeedbackFormHidden(true)
  }, [feedbackSent, feedbackCountdown])

  useEffect(() => {
    fetch(`${API_URL}/api/prns`).then(response => response.ok ? response.json() : { files: [] }).then(payload => setPrnOptions(payload.files?.length ? payload.files : DEFAULT_PRN_OPTIONS)).catch(() => setPrnOptions(DEFAULT_PRN_OPTIONS))
  }, [])

  function buildAnalysisForm(): FormData {
    const individualPrnMode = compareMode && prnMode === 'individual'
    const individualProfileMode = compareMode && profileMode === 'individual'
    const form = new FormData()
    if (compareMode) {
      const profileUploadIndexes = individualProfileMode ? scenarioProfileFiles.map((scenarioFile, index) => {
        if (scenarioFile) form.append('profiles', scenarioFile)
        return index
      }) : []
      if (!individualProfileMode) files.forEach(selectedFile => form.append('profiles', selectedFile))
      let prnUploadIndex = 0
      const configs = scenarioConfigs.map((scenario, index) => {
        const { prn_default, ...scenarioWithoutPrn } = scenario
        const config: ScenarioConfig & { prn_upload_index?: number } = { ...scenarioWithoutPrn, name: scenario.name || scenarioName(index) }
        if (individualPrnMode && prn_default) config.prn_default = prn_default
        if (individualProfileMode) (config as ScenarioConfig & { profile_upload_index?: number }).profile_upload_index = profileUploadIndexes[index]
        const customPrn = individualPrnMode ? scenarioPrnFiles[index] : null
        if (customPrn) {
          form.append('scenario_prns', customPrn)
          config.prn_upload_index = prnUploadIndex++
        }
        return config
      })
      form.append('scenario_configs', JSON.stringify(configs))
    } else if (file) form.append('profile', file)
    if (aoaFile) form.append('aoa_file', aoaFile)
    if (selectedPrn) form.append('aoa_default', selectedPrn)
    form.append('frequency', frequency)
    form.append('units', units)
    form.append('polarization', polarization)
    form.append('heights', heights)
    form.append('antenna_type', antennaType)
    form.append('soil_epsr', soilEpsr)
    form.append('soil_sigma', soilSigma)
    form.append('move_tower', moveTower)
    form.append('no_diffraction', String(noDiffraction))
    return form
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    const individualPrnMode = compareMode && prnMode === 'individual'
    const individualProfileMode = compareMode && profileMode === 'individual'
    const scenarioPrnCount = scenarioConfigs.filter((scenario, index) => Boolean(scenario.prn_default || scenarioPrnFiles[index])).length
    const scenarioHasPrn = individualPrnMode && scenarioPrnCount === scenarioConfigs.length
    const scenarioProfileCount = scenarioProfileFiles.filter(Boolean).length
    const hasCompleteScenarioProfiles = compareMode && scenarioProfileCount === scenarioConfigs.length
    if (!compareMode && !file) { setError(t('errProfileRequired')); return }
    if (compareMode && !individualProfileMode && !file) { setError(t('errSharedProfileRequired')); return }
    if (compareMode && individualProfileMode && !hasCompleteScenarioProfiles) { setError(t('errAllScenarioProfiles')); return }
    if (!individualPrnMode && !aoaFile && !selectedPrn) { setError(t('errSharedPrnRequired')); return }
    if (individualPrnMode && !scenarioHasPrn) { setError(t('errAllScenarioPrns')); return }
    setLoading(true)
    const form = buildAnalysisForm()
    try {
      const response = await fetch(`${API_URL}${compareMode ? '/api/compare' : '/api/analyze'}`, { method: 'POST', body: form })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || t('errAnalysisFailed'))
      if (compareMode) { setCompareResult(payload); setResult(null) } else { setResult(payload); setCompareResult(null) }
      setAiExplanation(null); setAiError('')
    } catch (cause) {
      setError(cause instanceof TypeError ? tr(`Não foi possível conectar à API em ${API_URL}. Inicie o backend na porta 8000.`, `Could not connect to the API at ${API_URL}. Start the backend on port 8000.`, `No fue posible conectar con la API en ${API_URL}. Inicie el backend en el puerto 8000.`) : cause instanceof Error ? cause.message : t('errApiGeneric'))
    } finally { setLoading(false) }
  }

  async function askAI() {
    const analysis = compareResult || result
    if (!analysis) return
    const singleResult = result
    const compactScenario = (scenario: Scenario) => ({
      name: scenario.name,
      profile_name: scenario.profile_name,
      prn_name: scenario.prn_name,
      metrics: scenario.metrics,
      terrain: scenario.profile?.terrain,
      configuration: scenario.configuration,
      interpretation: scenario.interpretation,
      ray_trace: summarizeRayTrace(scenario.ray_trace),
    })
    const analysisForAI = compareResult
      ? {
          comparison: compareResult.comparison,
          limitations: compareResult.limitations,
          scenarios: compareResult.scenarios.map(compactScenario),
          terrain_profiles: compareResult.scenarios.map(scenario => ({
            scenario: scenario.name,
            profile_name: scenario.profile_name,
            profile: scenario.profile,
          })),
          scenario_summary: compareResult.scenarios.map(scenario => ({
            name: scenario.name,
            profile_name: scenario.profile_name,
            metrics: scenario.metrics,
            terrain: scenario.profile?.terrain,
            configuration: scenario.configuration,
            interpretation: scenario.interpretation,
            ray_trace: summarizeRayTrace(scenario.ray_trace),
          })),
        }
      : {
          metrics: singleResult?.metrics,
          profile: singleResult?.profile,
          configuration: singleResult?.configuration,
          interpretation: singleResult?.interpretation,
          limitations: singleResult?.limitations,
          ray_trace: summarizeRayTrace(singleResult?.ray_trace),
          terrain_profile: singleResult?.profile,
        }
    setAiLoading(true); setAiError('')
    try {
      const response = await fetch(`${API_URL}/api/ai/explain`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ analysis: analysisForAI }) })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || t('errAiExplain'))
      setAiExplanation(payload)
    } catch (cause) { setAiError(cause instanceof Error ? cause.message : t('errAiFailed')) }
    finally { setAiLoading(false) }
  }

  async function submitFeedback(event: FormEvent) {
    event.preventDefault()
    setFeedbackStatus('')
    setFeedbackError('')
    setFeedbackLoading(true)
    const form = new FormData()
    form.append('name', feedbackName)
    form.append('email', feedbackEmail)
    form.append('category', feedbackCategory)
    form.append('message', feedbackMessage)
    form.append('cf-turnstile-response', feedbackCaptchaToken)
    form.append('website', '')
    try {
      const response = await fetch(`${API_URL}/api/feedback`, { method: 'POST', body: form })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || t('errFeedbackSend'))
      setFeedbackStatus(payload.message || t('feedbackThanksDefault'))
      setFeedbackSent(true)
      setFeedbackFormHidden(false)
      setFeedbackCountdown(10)
      setFeedbackName(''); setFeedbackEmail(''); setFeedbackMessage('')
    } catch (cause) {
      setFeedbackError(cause instanceof Error ? cause.message : t('errFeedbackSend'))
    } finally { setFeedbackLoading(false) }
  }

  function startNewFeedback() {
    setFeedbackSent(false)
    setFeedbackFormHidden(false)
    setFeedbackCountdown(0)
    setFeedbackStatus('')
    setFeedbackError('')
    setFeedbackCaptchaToken('')
    if (feedbackWidgetId.current) {
      const turnstile = (window as Window & { turnstile?: { reset: (id: string) => void } }).turnstile
      turnstile?.reset(feedbackWidgetId.current)
    }
  }

  async function exportResult(format: string) {
    if (!file) return
    if (!aoaFile && !selectedPrn) { setError(t('errExportPrn')); return }
    const form = new FormData()
    form.append('profile', file); form.append('frequency', frequency); form.append('units', units)
    form.append('heights', heights); form.append('antenna_type', antennaType); form.append('soil_epsr', soilEpsr)
    form.append('soil_sigma', soilSigma); form.append('move_tower', moveTower)
    form.append('no_diffraction', String(noDiffraction)); form.append('polarization', polarization); form.append('export_format', format); form.append('locale', locale)
    if (aoaFile) form.append('aoa_file', aoaFile)
    if (selectedPrn) form.append('aoa_default', selectedPrn)
    let response: Response
    try { response = await fetch(`${API_URL}/api/analyze`, { method: 'POST', body: form }) }
    catch { setError(tr(`Não foi possível conectar à API em ${API_URL}.`, `Could not connect to the API at ${API_URL}.`, `No fue posible conectar con la API en ${API_URL}.`)); return }
    if (!response.ok) { setError(t('errExportFailed')); return }
    const blob = await response.blob(); const link = document.createElement('a')
    link.href = URL.createObjectURL(blob); link.download = `openhfta-pattern.${format}`; link.click(); URL.revokeObjectURL(link.href)
  }

  async function exportComparison(format: string) {
    if (!compareResult) return
    const individualPrnMode = prnMode === 'individual'
    const individualProfileMode = profileMode === 'individual'
    const scenarioPrnCount = scenarioConfigs.filter((scenario, index) => Boolean(scenario.prn_default || scenarioPrnFiles[index])).length
    const scenarioHasPrn = individualPrnMode && scenarioPrnCount === scenarioConfigs.length
    const scenarioProfileCount = scenarioProfileFiles.filter(Boolean).length
    const hasCompleteScenarioProfiles = scenarioProfileCount === scenarioConfigs.length
    if (!individualProfileMode && !file) { setError(t('errSharedProfileRequired')); return }
    if (individualProfileMode && !hasCompleteScenarioProfiles) { setError(t('errAllScenarioProfiles')); return }
    if (!individualPrnMode && !aoaFile && !selectedPrn) { setError(t('errSharedPrnRequired')); return }
    if (individualPrnMode && !scenarioHasPrn) { setError(t('errAllScenarioPrns')); return }
    const form = buildAnalysisForm()
    form.append('export_format', format)
    form.append('locale', locale)
    let response: Response
    try { response = await fetch(`${API_URL}/api/compare`, { method: 'POST', body: form }) }
    catch { setError(tr(`Não foi possível conectar à API em ${API_URL}.`, `Could not connect to the API at ${API_URL}.`, `No fue posible conectar con la API en ${API_URL}.`)); return }
    if (!response.ok) { setError(t('errExportFailed')); return }
    const blob = await response.blob(); const link = document.createElement('a')
    link.href = URL.createObjectURL(blob); link.download = `openhfta-comparison.${format}`; link.click(); URL.revokeObjectURL(link.href)
  }

  const peak = result ? Math.max(...result.pattern_db) : null
  const peakAngle = result && peak !== null ? result.angles_deg[result.pattern_db.indexOf(peak)] : null
  const palette = colorblindMode ? COLORBLIND_PALETTE : DEFAULT_PALETTE
  const aoaTrace = (aoa: Result['aoa']) => aoa && aoa.available !== false && aoa.angles_deg.length ? { x: aoa.angles_deg, y: aoa.probabilities_pct, type: 'bar' as const, name: `PRN${aoa.band ? ` · ${aoa.band}` : ''}`, yaxis: 'y2' as const, width: 0.72, marker: { color: palette.aoa, opacity: 0.35, line: { color: palette.aoa, width: 0.7 } }, hovertemplate: '%{x}°<br>%{y:.1f}%<extra></extra>' } : null
  const scenarioLabel = (scenario: Scenario) => scenarioDisplayLabel(scenario, locale)
  const nullsTrace = (nulls: { angle_deg: number; value_db: number }[] | undefined, name: string, color: string) =>
    nulls?.length ? [{ x: nulls.map(item => item.angle_deg), y: nulls.map(item => item.value_db), type: 'scatter', mode: 'markers', name, marker: { symbol: 'x', size: 9, color, line: { color: '#1a0505', width: 1.5 } }, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' }] : []
  const resultPatternData: any[] = result ? [
    { x: result.angles_deg, y: result.pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: 'PRO', line: { color: palette.scenarios[0], width: 2.5 }, marker: { symbol: 'circle', size: 5, color: palette.scenarios[0] }, fill: 'tozeroy', fillcolor: `${palette.scenarios[0]}22`, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' },
    ...(result.flat_pattern_db ? [{ x: result.angles_deg, y: result.flat_pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: 'FLAT.PRO', line: { color: palette.flat, width: 2, dash: accessiblePatterns ? 'dash' : 'solid' }, marker: { symbol: 'x', size: 5, color: palette.flat }, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' }] : []),
    ...nullsTrace(result.metrics?.nulls, t('nullsLabel'), '#ff5f5f'),
    ...(result.aoa ? [aoaTrace(result.aoa)] : []),
  ].filter(Boolean) : []
  const comparePatternData: any[] = compareResult ? [
    ...compareResult.scenarios.flatMap((scenario, index) => [
      { x: compareResult.angles_deg, y: scenario.pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: scenarioNameLabel(scenario, locale), line: { color: palette.scenarios[index % palette.scenarios.length], width: 2.5, dash: scenarioDash(index, accessiblePatterns, palette.scenarios.length) }, marker: { symbol: SCENARIO_SYMBOLS[index % SCENARIO_SYMBOLS.length], size: 5, color: palette.scenarios[index % palette.scenarios.length] }, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' },
    ...(scenario.flat_pattern_db ? [{ x: compareResult.angles_deg, y: scenario.flat_pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: scenarioNameLabel(scenario, locale, 'FLAT.PRO'), line: { color: palette.scenarios[index % palette.scenarios.length], width: 1.5, dash: 'dot' }, marker: { symbol: 'x', size: 5, color: palette.scenarios[index % palette.scenarios.length] }, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' }] : []),
    ...nullsTrace(scenario.metrics?.nulls, `${scenario.name} · ${t('nullsLabel')}`, palette.scenarios[index % palette.scenarios.length]),
    ]),
    ...(compareResult.scenarios[0]?.aoa ? [aoaTrace(compareResult.scenarios[0].aoa)] : []),
  ].filter(Boolean) : []
  const scenarioPatternData = (scenario: Scenario, index: number): any[] => [
    { x: compareResult?.angles_deg || scenario.angles_deg || [], y: scenario.pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: 'PRO', line: { color: palette.scenarios[index % palette.scenarios.length], width: 2.5 }, marker: { symbol: SCENARIO_SYMBOLS[index % SCENARIO_SYMBOLS.length], size: 5, color: palette.scenarios[index % palette.scenarios.length] }, fill: 'tozeroy', fillcolor: `${palette.scenarios[index % palette.scenarios.length]}22`, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' },
    ...(scenario.flat_pattern_db ? [{ x: compareResult?.angles_deg || scenario.angles_deg || [], y: scenario.flat_pattern_db, type: 'scatter', mode: accessiblePatterns ? 'lines+markers' : 'lines', name: 'FLAT.PRO', line: { color: palette.flatScenarios[index % palette.flatScenarios.length], width: 2, dash: 'dot' }, marker: { symbol: 'x', size: 5, color: palette.flatScenarios[index % palette.flatScenarios.length] }, hovertemplate: '%{x:.2f}°<br>%{y:.2f} dB<extra></extra>' }] : []),
    ...nullsTrace(scenario.metrics?.nulls, t('nullsLabel'), '#ff5f5f'),
    ...(scenario.aoa ? [aoaTrace(scenario.aoa)] : []),
  ].filter(Boolean)
  const patternLayout = { autosize: true, margin: { l: 64, r: 84, t: 28, b: 58 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', barmode: 'overlay' as const, font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: t('elevation') }, automargin: true, range: [0, 36], tick0: 0, gridcolor: '#263943', zeroline: false, dtick: 1, nticks: 37 }, yaxis: { title: { text: t('gain') }, automargin: true, range: [-10, 20], gridcolor: '#263943', zeroline: false, dtick: 1, nticks: 31 }, yaxis2: { title: { text: t('elevationStats') }, automargin: true, overlaying: 'y', side: 'right', range: [0, 20], dtick: 5, showgrid: false }, hovermode: 'x unified' }
  const rayLabels = RAY_LABELS_BY_LOCALE[locale]
  const rayColors = palette.rays
  const traceSource = result || compareResult?.scenarios[0] || null
  const terrainDistances = traceSource?.profile?.distances_m?.slice(0, profilePointCount(traceSource?.profile)) || []
  const terrainHeights = traceSource?.profile?.heights_m?.slice(0, profilePointCount(traceSource?.profile)) || []
  const terrainOrigin = terrainHeights[0] || 0
  const relativeTerrainHeights = terrainHeights.map(height => height - terrainOrigin)
  const terrainYMin = relativeTerrainHeights.length ? Math.min(...relativeTerrainHeights) : -10
  const terrainAbsMin = terrainHeights.length ? Math.min(...terrainHeights) : 0
  const terrainAbsMax = terrainHeights.length ? Math.max(...terrainHeights) : 100
  const terrainEnd = terrainDistances.length ? terrainDistances[terrainDistances.length - 1] : 0
  const rayAxisEnd = Math.max(500, Math.ceil(terrainEnd / 500) * 500)
  const terrainAt = (distance: number) => {
    if (!terrainDistances.length) return 0
    for (let index = 1; index < terrainDistances.length; index += 1) {
      if (distance <= terrainDistances[index]) {
        const x0 = terrainDistances[index - 1]; const x1 = terrainDistances[index]
        const ratio = x1 === x0 ? 0 : (distance - x0) / (x1 - x0)
        return terrainHeights[index - 1] + (terrainHeights[index] - terrainHeights[index - 1]) * ratio
      }
    }
    return terrainHeights[terrainHeights.length - 1] || 0
  }
  const clipRay = (path: NonNullable<Result['ray_trace']>['paths'][number]) => {
    const points: Array<[number, number]> = []
    path.distances_m.forEach((distance, index) => {
      if (distance <= terrainEnd && path.heights_m[index] !== undefined) points.push([distance, path.heights_m[index]])
    })
    const crossing = path.distances_m.findIndex(distance => distance > terrainEnd)
    if (crossing > 0 && points.length && path.distances_m[crossing - 1] < terrainEnd) {
      const x0 = path.distances_m[crossing - 1]; const x1 = path.distances_m[crossing]
      const y0 = path.heights_m[crossing - 1]; const y1 = path.heights_m[crossing]
      const ratio = x1 === x0 ? 0 : (terrainEnd - x0) / (x1 - x0)
      points.push([terrainEnd, y0 + (y1 - y0) * ratio])
    }
    return points
  }
  const selectedRayPaths = traceSource?.ray_trace?.paths.filter(path => RAY_KINDS.includes(path.kind) && rayKinds[path.kind] !== false && rayWithinLimit(path.angle_deg, rayAngleLimit)) || []
  const visibleRays = selectedRayPaths.map(path => ({ path, points: clipRay(path) })).filter(item => item.points.length >= 2)
  const rayInteractions = visibleRays.flatMap(({ path, points }) => points.filter(([distance, height]) => Math.abs(height - terrainAt(distance)) < 4).map(([distance, height]) => ({ distance, height, kind: path.kind })))
  const rayCorners = visibleRays.flatMap(({ path, points }) => points.slice(1, -1).flatMap((point, index) => {
    const previous = points[index]; const next = points[index + 2]
    const incoming = Math.atan2(point[1] - previous[1], point[0] - previous[0])
    const outgoing = Math.atan2(next[1] - point[1], next[0] - point[0])
    const turnDegrees = Math.abs(outgoing - incoming) * 180 / Math.PI
    const nearTerrain = Math.abs(point[1] - terrainAt(point[0])) < 4
    return turnDegrees > 2 && turnDegrees < 170 && nearTerrain ? [{ distance: point[0], height: point[1], kind: path.kind }] : []
  }))
  const rayOriginHeight = terrainHeights[0] !== undefined ? terrainHeights[0] + (traceSource?.configuration?.antenna_heights_m?.[0] || 0) : 0
  const rayReferenceDistance = Math.max(1, rayAxisEnd)
  const rayDegreeMax = rayAngleLimit === null ? Math.max(20, ...selectedRayPaths.map(path => Math.abs(path.angle_deg))) : rayAngleLimit
  const rayYMin = Math.max(0, Math.min(terrainAbsMin - 30, rayOriginHeight))
  const rayYMax = Math.max(1000, rayOriginHeight + Math.tan(rayDegreeMax * Math.PI / 180) * rayReferenceDistance, ...visibleRays.flatMap(({ points }) => points.map(point => point[1])))
  const rayDegreeRange: [number, number] = [Math.atan2(rayYMin - rayOriginHeight, rayReferenceDistance) * 180 / Math.PI, Math.atan2(rayYMax - rayOriginHeight, rayReferenceDistance) * 180 / Math.PI]
  const rayAntennaPattern = result?.flat_pattern_db || result?.pattern_db || []
  const rayGains = visibleRays.map(({ path }) => gainAt(result?.angles_deg || [], rayAntennaPattern, path.angle_deg))
  const rayLowGain = Math.min(...rayGains, 0); const rayHighGain = Math.max(...rayGains, 1)
  const rayTraceData: any[] = [
    ...visibleRays.map(({ path }, index) => {
      const points = clipRay(path)
      const gain = rayGains[index]; const weight = rayHighGain === rayLowGain ? .45 : .14 + .38 * ((gain - rayLowGain) / (rayHighGain - rayLowGain))
      return { x: points.map(point => point[0]), y: points.map(point => point[1]), type: 'scatter', mode: 'lines', name: rayLabels[path.kind] || path.kind, legendgroup: path.kind, showlegend: visibleRays.findIndex(candidate => candidate.path.kind === path.kind) === index, line: { color: rayColors[path.kind] || '#78b7d9', width: (path.kind === 'direct' ? 1.05 : .65) + weight, opacity: weight, dash: accessiblePatterns ? RAY_DASHES[path.kind] : 'solid' }, hovertemplate: `${rayLabels[path.kind] || path.kind}<br>saída: ${path.angle_deg.toFixed(2)}°<br>ganho da antena: ${gain.toFixed(1)} dB<br>%{x:.0f} m · %{y:.1f} m<extra></extra>` }
    }),
    { x: rayInteractions.map(point => point.distance), y: rayInteractions.map(point => point.height), type: 'scatter', mode: 'markers', name: rayUi.terrainPointLabel, legendgroup: 'events', marker: { color: palette.event, size: 7, symbol: 'diamond', line: { color: '#081923', width: 1 } }, hovertemplate: `${rayUi.reflectionPointHover}<br>%{x:.0f} m · %{y:.1f} m<extra></extra>` },
    { x: rayCorners.map(point => point.distance), y: rayCorners.map(point => point.height), type: 'scatter', mode: 'markers', name: rayUi.directionChangeLabel, legendgroup: 'corners', marker: { color: palette.corner, size: 8, symbol: 'triangle-down', line: { color: '#fff1dc', width: 1 } }, hovertemplate: `${rayUi.directionChangeLabel}<br>%{x:.0f} m · %{y:.1f} m<extra></extra>` },
    { x: [0], y: [terrainHeights[0] !== undefined ? terrainHeights[0] + (traceSource?.configuration?.antenna_heights_m?.[0] || 0) : 0], type: 'scatter', mode: 'markers', name: rayUi.antennaLabel, legendgroup: 'antenna', marker: { color: palette.antenna, size: 9, symbol: 'triangle-up' }, hovertemplate: `${rayUi.antennaLabel}<br>%{y:.1f} m<extra></extra>` },
    { x: terrainDistances, y: terrainHeights, type: 'scatter', mode: 'lines+markers', name: rayUi.terrainLabel, legendgroup: 'terrain', line: { color: palette.terrain, width: 2 }, marker: { color: palette.terrain, size: 4, symbol: 'diamond' }, fill: 'tozeroy', fillcolor: 'rgba(194, 174, 162, .42)', hovertemplate: `${rayUi.terrainLabel}<br>%{x:.0f} m · %{y:.1f} m<extra></extra>` },
    { x: [0, terrainEnd], y: rayDegreeRange, yaxis: 'y2', type: 'scatter', mode: 'lines', line: { color: 'transparent', width: 0 }, opacity: 0, showlegend: false, hoverinfo: 'skip' },
  ]
  const rayTraceLayout = { autosize: true, margin: { l: 62, r: 100, t: 42, b: 54 }, title: { text: 'RAY TRACE OVER TERRAIN', font: { size: 13, color: '#7dff9b' } }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: rayUi.distance }, range: [0, rayAxisEnd], dtick: 500, gridcolor: '#263943', zeroline: false }, yaxis: { title: { text: t('height') }, range: [rayYMin, rayYMax], dtick: 100, gridcolor: '#263943', zeroline: false }, yaxis2: { title: { text: t('elevation'), font: { color: '#c7d4d7', size: 12 } }, overlaying: 'y', anchor: 'x', side: 'right', range: rayDegreeRange, tickmode: 'linear', tick0: 0, dtick: 1, ticksuffix: '°', showticklabels: true, showline: true, ticks: 'outside', tickfont: { color: '#c7d4d7', size: 11 }, gridcolor: 'transparent', zeroline: false }, legend: { orientation: 'h' as const, y: -0.2 }, hovermode: 'closest' as const }

  return <main className="shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">↗</span><span>Open<span>HFTA</span></span></div>
      <div className="topbar-actions"><label className="language-switcher"><span>{t('language')}</span><select value={locale} onChange={event => setLocale(event.target.value as Locale)} aria-label={t('language')}>{LOCALE_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><button type="button" className={colorblindMode ? 'accessibility-toggle active' : 'accessibility-toggle'} onClick={() => setColorblindMode(current => !current)} aria-pressed={colorblindMode} title={t('accessibleColors')}>{colorblindMode ? '◉' : '○'} {t('accessibleColors')}</button><button type="button" className={accessiblePatterns ? 'accessibility-toggle active' : 'accessibility-toggle'} onClick={() => setAccessiblePatterns(current => !current)} aria-pressed={accessiblePatterns} title={t('accessiblePatterns')}>{accessiblePatterns ? '◉' : '○'} {t('accessiblePatterns')}</button><div className="status"><i /> {t('online')}</div></div>
    </header>

    <section className="intro">
      <div className="intro-copy">
        <p className="eyebrow">HF TERRAIN ANALYSIS</p>
        <h1>{t('heroTitle')}<br /><em>{t('heroTitleEm')}</em></h1>
        <p className="lede">{t('heroLede')}</p>
      </div>
      <aside className="project-hero-credit">
        <small>{t('heroEyebrow')}</small>
        <strong>OpenHFTA<br /><em>HF Terrain Analysis</em></strong>
        <p>{t('heroMaintainedBy')} <a href="https://github.com/RioDXGroup" target="_blank" rel="noreferrer">Rio DX Group</a>.</p>
        <p><b>{t('heroDevContributions')}</b> <a href="https://www.qrz.com/db/PY2UID" target="_blank" rel="noreferrer">Paulo Matias — PY2UID</a> · <a href="https://github.com/thotypous" target="_blank" rel="noreferrer">GitHub ↗</a></p>
        <p>{t('heroAuthorBio')}</p>
        <a className="project-link" href="https://github.com/RioDXGroup/openhfta" target="_blank" rel="noreferrer">{t('heroOriginalProject')}</a>
        <p><b>{t('heroWebIntegration')}</b> <a href="https://www.qrz.com/db/PT9TI" target="_blank" rel="noreferrer">Fernando Fernandes — PT9TI ↗</a></p>
        <p>{t('heroWebAuthorBio')}</p>
      </aside>
    </section>

    <aside className="feedback-banner" aria-label={tr('Convite para colaboração', 'Invitation to collaborate', 'Invitación a colaborar')}>
      <div><span className="feedback-mark" aria-hidden="true">✦</span><div><strong>{t('helpImprove')}</strong><p>{t('feedbackBanner')}</p></div></div>
      <button type="button" onClick={() => { setFeedbackStatus(''); setFeedbackError(''); setShowFeedback(true) }}>{t('sendSuggestion')} <span>→</span></button>
    </aside>

    <section className="workspace">
      <form className="panel controls" onSubmit={submit} onClickCapture={notifySharedResourceClick}>
        <div className="panel-heading"><span className="step">01</span><div><h2>{t('configuration')}</h2><p>{t('defineScenario')}</p></div><button type="button" className="help-button" onClick={() => setShowHelp(true)} aria-label={t('explainFields')}>?</button></div>
        {(!compareMode || profileMode === 'shared') && <label className="file-drop">
          <input disabled={compareMode && profileMode === 'individual'} type="file" accept=".pro,.PRO" multiple onChange={event => {
            const selected = Array.from(event.target.files || [])
            const selectingMultiple = compareMode || files.length + selected.length > 1
            const nextFiles = selectingMultiple
              ? [...files, ...selected].filter((file, index, all) => all.findIndex(candidate => candidate.name === file.name && candidate.size === file.size && candidate.lastModified === file.lastModified) === index)
              : selected.slice(0, 1)
            setFiles(nextFiles)
            if (nextFiles.length > 1) {
              setCompareMode(true)
              setScenarioConfigs(current => {
              const next = [...current]
              while (next.length < nextFiles.length) next.push({ name: scenarioName(next.length), heights: '10', antenna_type: 'Dipole', polarization: 'horizontal' })
              setScenarioPrnFiles(currentPrns => {
                const nextPrns = [...currentPrns]
                while (nextPrns.length < next.length) nextPrns.push(null)
                return nextPrns.slice(0, next.length)
              })
              setScenarioProfileFiles(currentProfiles => {
                const nextProfiles = [...currentProfiles]
                while (nextProfiles.length < next.length) nextProfiles.push(null)
                return nextProfiles.slice(0, next.length)
              })
              return next.slice(0, Math.max(2, Math.min(4, nextFiles.length)))
              })
            }
            // Permite escolher novamente o mesmo arquivo em uma nova seleção.
            event.currentTarget.value = ''
          }} />
          <span className="upload-icon">↑</span>
          {files.length ? <div className="selected-files">{files.map((selectedFile, index) => <span className="selected-file" key={`${selectedFile.name}-${selectedFile.size}-${selectedFile.lastModified}`}><strong>{compareMode ? files.length === 1 ? `${tr('Todos os cenários', 'All scenarios', 'Todos los escenarios')} · ${selectedFile.name}` : `${scenarioName(index)} · ${selectedFile.name}` : selectedFile.name}</strong><button type="button" aria-label={tr(`Remover ${selectedFile.name}`, `Remove ${selectedFile.name}`, `Quitar ${selectedFile.name}`)} onClick={event => { event.preventDefault(); event.stopPropagation(); setFiles(current => current.filter((_, fileIndex) => fileIndex !== index)) }}>×</button></span>)}</div> : <strong>{t('uploadProfile')}</strong>}
          <small>{files.length ? tr(`${files.length} perfil(is) selecionado(s)`, `${files.length} profile(s) selected`, `${files.length} perfil(es) seleccionado(s)`) : compareMode ? tr('selecione 1 perfil para todos ou até 4 perfis por azimute', 'select 1 profile for all or up to 4 profiles per azimuth', 'seleccione 1 perfil para todos o hasta 4 perfiles por azimut') : t('browseComputer')}</small>
        </label>}

        {(!compareMode || prnMode === 'shared') && <label className="aoa-upload"><input type="file" accept=".prn,.PRN" onChange={event => { const selected = event.target.files?.[0] || null; setAoaFile(selected); if (selected) setSelectedPrn('') }} /><span>{tr('Estatística de elevação (.PRN) — compartilhado', 'Elevation statistics (.PRN) — shared', 'Estadística de elevación (.PRN) — compartida')}</span><strong>{aoaFile ? aoaFile.name : tr('Envie seu arquivo .PRN', 'Upload your .PRN file', 'Cargue su archivo .PRN')}</strong></label>}
        <div className="field-grid">
          {(!compareMode || prnMode === 'shared') && <label>{tr('PRN padrão compartilhado', 'Shared default PRN', 'PRN predeterminado compartido')}<select value={selectedPrn} onChange={event => { setSelectedPrn(event.target.value); if (event.target.value) setAoaFile(null) }}><option value="">{tr('Selecione um padrão', 'Select a default', 'Seleccione un valor predeterminado')}</option>{prnOptions.map(name => <option key={name} value={name}>{name}</option>)}</select><small>{aoaFile ? tr('O arquivo próprio foi selecionado; escolher um padrão o substitui.', 'A custom file is selected; choosing a default replaces it.', 'Se seleccionó un archivo propio; elegir un valor predeterminado lo reemplaza.') : tr('Ou escolha um padrão compartilhado para todos os cenários.', 'Or choose a shared default for all scenarios.', 'O elija un valor predeterminado compartido para todos los escenarios.')}</small></label>}
          <label>{t('frequency')}<input value={frequency} onChange={e => setFrequency(e.target.value)} placeholder="20m ou 14.2" /></label>
          <label>{t('units')}<select value={units} onChange={e => setUnits(e.target.value)}><option value="meters">{t('meters')}</option><option value="feet">{t('feet')}</option></select></label>
          <label className={compareMode ? 'field-disabled' : ''}>{t('antennaHeights')}<input disabled={compareMode} value={heights} onChange={e => setHeights(e.target.value)} placeholder="10 20*" /><small>{compareMode ? tr('Use as alturas de cada cenário abaixo.', 'Use the heights for each scenario below.', 'Use las alturas de cada escenario.') : tr('Separe elementos por espaço; * = 180°', 'Separate elements with spaces; * = 180°', 'Separe los elementos con espacios; * = 180°')}</small></label>
          <label className={compareMode ? 'field-disabled' : ''}>{t('antennaType')}<select disabled={compareMode} value={antennaType} onChange={e => setAntennaType(e.target.value)}>{['Dipole','2-Ele','3-Ele','4-Ele','5-Ele','6-Ele','8-Ele'].map(type => <option key={type}>{type}</option>)}</select></label>
          <label className={compareMode ? 'field-disabled' : ''}>{t('polarization')}<select disabled={compareMode} value={polarization} onChange={e => setPolarization(e.target.value as 'horizontal' | 'vertical')}><option value="horizontal">Horizontal (H)</option></select><small>{compareMode ? tr('Use a polarização de cada cenário abaixo.', 'Use the polarization for each scenario below.', 'Use la polarización de cada escenario.') : tr('H usa TE na reflexão do solo.', 'H uses TE for ground reflection.', 'H usa TE en la reflexión del suelo.')}</small></label>
          <label><span className="field-label-with-help">{t('terrainType')}<button type="button" className="ray-help-button" onClick={() => setShowSoilHelp(true)} aria-label={t('explainTerrainTypes')}>?</button></span><select value={soilPreset} onChange={event => { const key = event.target.value; setSoilPreset(key); const preset = SOIL_PRESETS.find(candidate => candidate.key === key); if (preset) { setSoilEpsr(String(preset.epsr)); setSoilSigma(String(preset.sigma)) } }}>{SOIL_PRESETS.map(preset => <option key={preset.key} value={preset.key}>{SOIL_PRESET_LABELS[locale][preset.key]}</option>)}<option value="custom">{SOIL_PRESET_LABELS[locale].custom}</option></select></label>
          <label>{t('soilPermittivity')}<input type="number" step="any" value={soilEpsr} onChange={e => { setSoilEpsr(e.target.value); setSoilPreset('custom') }} /></label>
          <label>{t('soilConductivity')}<input type="number" step="any" value={soilSigma} onChange={e => { setSoilSigma(e.target.value); setSoilPreset('custom') }} /></label>
          <label>{t('towerOffset')}<input type="number" step="any" value={moveTower} onChange={e => setMoveTower(e.target.value)} /></label>
        </div>
        <label className="toggle"><input type="checkbox" checked={!noDiffraction} onChange={e => setNoDiffraction(!e.target.checked)} /><span />{t('includeDiffraction')}</label>
        <label className="toggle"><input type="checkbox" checked={compareMode} onChange={e => { setCompareMode(e.target.checked); if (!e.target.checked && files.length > 1) setFiles([files[0]]) }} /><span />{t('compareScenarios')}</label>
        {compareMode && <div className="scenario-editor"><div className="scenario-editor-title"><span>{t('upToFourScenarios')}</span><span className="prn-mode"><label><input type="radio" name="prn-mode" checked={prnMode === 'shared'} onChange={() => setPrnMode('shared')} /> {t('sharedPrn')}</label><label><input type="radio" name="prn-mode" checked={prnMode === 'individual'} onChange={() => setPrnMode('individual')} /> {t('individualPrn')}</label><label><input type="radio" name="profile-mode" checked={profileMode === 'shared'} onChange={() => setProfileMode('shared')} /> {t('sharedProfile')}</label><label><input type="radio" name="profile-mode" checked={profileMode === 'individual'} onChange={() => setProfileMode('individual')} /> {t('individualProfile')}</label></span><button type="button" onClick={() => { setScenarioConfigs(current => [...current, { name: scenarioName(current.length), heights: '10', antenna_type: 'Dipole', polarization: 'horizontal' }]); setScenarioPrnFiles(current => [...current, null]); setScenarioProfileFiles(current => [...current, null]) }}>{t('addScenario')}</button></div><p className="scenario-help">{t('scenarioHelpText')}</p>{scenarioConfigs.map((scenario, index) => <div className="scenario-row" key={index}><label className="scenario-control"><span title={t('scenarioNameTooltip')}>{t('scenarioNameLabel')}</span><input aria-label={`${t('scenarioNameLabel')} ${index + 1}`} value={scenario.name} onChange={event => updateScenario(index, { name: event.target.value })} placeholder={scenarioName(index)} /></label><label className="scenario-control"><span title={t('scenarioHeightsTooltip')}>{t('scenarioHeightsShort')}</span><input aria-label={`${t('scenarioHeightsShort')} ${index + 1}`} value={scenario.heights} onChange={event => updateScenario(index, { heights: event.target.value })} placeholder="10 20*" /></label><label className="scenario-control"><span title={t('scenarioAntennaTooltip')}>{t('scenarioAntennaLabel')}</span><select aria-label={`${t('scenarioAntennaLabel')} ${index + 1}`} value={scenario.antenna_type} onChange={event => updateScenario(index, { antenna_type: event.target.value })}>{antennaTypes.map(type => <option key={type}>{type}</option>)}</select></label><label className="scenario-control"><span title={t('scenarioPolarizationTooltip')}>{t('polarization')}</span><select aria-label={`${t('polarization')} ${index + 1}`} value={scenario.polarization || 'horizontal'} onChange={event => updateScenario(index, { polarization: event.target.value as 'horizontal' | 'vertical' })}><option value="horizontal">Horizontal (H)</option></select></label><label className={`scenario-file scenario-control ${profileMode === 'shared' ? 'field-disabled' : ''}`}><span title={t('scenarioProfileTooltip')}>{t('scenarioProfileLabel')}</span><input disabled={profileMode === 'shared'} type="file" accept=".pro,.PRO" onChange={event => updateScenarioProfile(index, event.target.files?.[0] || null)} /><strong>{scenarioProfileFiles[index]?.name || t('topBlockPlaceholder')}</strong></label>{prnMode === 'individual' ? <><label className="scenario-file scenario-control"><span title={t('scenarioPrnTooltip')}>{t('scenarioPrnStatLabel')}</span><input type="file" accept=".prn,.PRN" onChange={event => updateScenarioPrn(index, event.target.files?.[0] || null)} /><strong>{scenarioPrnFiles[index]?.name || t('filePlaceholder')}</strong></label><label className="scenario-control"><span title={t('scenarioDefaultPrnTooltip')}>{t('scenarioDefaultPrnLabel')}</span><select aria-label={`${t('scenarioDefaultPrnLabel')} ${index + 1}`} value={scenario.prn_default || ''} onChange={event => { updateScenario(index, { prn_default: event.target.value }); if (event.target.value) updateScenarioPrn(index, null) }}><option value="">{t('selectGeneric')}</option>{prnOptions.map(name => <option key={name} value={name}>{name}</option>)}</select></label></> : <span className="scenario-shared-prn scenario-control">{t('sharedPrn')}</span>}{scenarioConfigs.length > 2 && <button type="button" className="remove-scenario" aria-label={tr(`Remover cenário ${index + 1}`, `Remove scenario ${index + 1}`, `Quitar escenario ${index + 1}`)} onClick={() => { setScenarioConfigs(current => current.filter((_, scenarioIndex) => scenarioIndex !== index)); setScenarioPrnFiles(current => current.filter((_, fileIndex) => fileIndex !== index)); setScenarioProfileFiles(current => current.filter((_, fileIndex) => fileIndex !== index)) }}>×</button>}</div>)}</div>}
        {error && <div className="error" role="alert">{error}</div>}
        <button className="submit" disabled={loading}>{loading ? t('calculating') : t('calculate')} <span>→</span></button>
      </form>

      <section className="panel results">
        <div className="panel-heading"><span className="step">02</span><div><h2>{t('result')}</h2><p>{compareResult ? t('comparisonCalculated') : result ? t('patternCalculated') : t('waitingAnalysis')}</p></div></div>
        {loading && <div className="analysis-loading" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><div><strong>{t('processing')}</strong><p>{tr('O núcleo Fortran está calculando o padrão, a difração e as trajetórias sobre o terreno.', 'The Fortran core is calculating the pattern, diffraction, and paths over the terrain.', 'El núcleo Fortran está calculando el patrón, la difracción y las trayectorias sobre el terreno.')}</p><small>{tr('Não feche esta página. O tempo depende do perfil e da quantidade de trajetórias.', 'Do not close this page. Time depends on the profile and number of paths.', 'No cierre esta página. El tiempo depende del perfil y de la cantidad de trayectorias.')}</small></div></div>}
        {compareResult ? <>
          <div className="comparison-pairs">{(compareResult.comparison.pairwise || [compareResult.comparison]).map((pair, index) => <article key={index}><div className="terrain-heading"><small>A × {String.fromCharCode(66 + index)}</small><span>{t('comparisonWithScenarioA')}</span></div><div className="metrics"><div><small>RMSE</small><strong>{pair.rmse_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('maxDifference')}</small><strong>{pair.max_absolute_delta_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('peakDifference')}</small><strong>{pair.peak_delta_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('integratedAvgDiff')}</small><strong>{pair.integrated_average_delta_db.toFixed(2)} <b>dB</b></strong></div></div></article>)}</div>
          <div className="scenario-details">{compareResult.scenarios.map(scenario => <article key={scenario.name}><div className="terrain-heading"><small>{scenarioLabel(scenario)}</small></div><div className="metrics"><div><small>{t('peakOfPattern')}</small><strong>{scenario.metrics?.peak.value_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('peakAngleLabel')}</small><strong>{scenario.metrics?.peak.angle_deg.toFixed(2)} <b>°</b></strong></div><div><small>{t('integratedAverageLabel')}</small><strong>{scenario.metrics?.integrated_average_gain.average_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('beamwidth3db')}</small><strong>{scenario.metrics?.beamwidth_3db?.width_deg?.toFixed(2) ?? '—'} <b>°</b></strong></div><div><small>{t('profilePointsLabel')}</small><strong>{scenario.profile ? profilePointCount(scenario.profile) : '—'}</strong></div><div><small>FIGURE OF MERIT</small><strong>{scenario.metrics?.figure_of_merit_db?.toFixed(2) ?? '—'} <b>dB</b></strong></div></div><div className="result-note">{scenario.configuration?.diffraction_disable ? t('noDiffraction') : t('diffraction')} · {scenario.configuration?.frequency_mhz?.toFixed(2)} MHz · {scenario.profile?.source_units || t('unitNotInformed')} · {scenario.configuration?.antenna_heights_m?.map(height => height.toFixed(2)).join(' / ')} m</div></article>)}</div>
          {prnMode === 'individual' ? <div className="scenario-visuals">{compareResult.scenarios.map((scenario, index) => <article className="scenario-visual" key={scenario.name}><div className="terrain-heading"><small>{scenarioLabel(scenario)}</small></div><Plot className="chart" data={scenarioPatternData(scenario, index)} layout={patternLayout} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '300px' }} />{scenario.profile && <Plot className="terrain-chart" data={[{ x: scenario.profile.distances_m.slice(0, profilePointCount(scenario.profile)), y: scenario.profile.heights_m.slice(0, profilePointCount(scenario.profile)), type: 'scatter', mode: 'lines', name: scenarioNameLabel(scenario, locale), line: { color: palette.scenarios[index % palette.scenarios.length], width: 2 }, hovertemplate: '%{x:.0f} m<br>%{y:.1f} m<extra></extra>' }]} layout={{ autosize: true, margin: { l: 48, r: 16, t: 12, b: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: t('distanceAxis') }, gridcolor: '#263943', nticks: 14 }, yaxis: { title: { text: t('altitudeAxis') }, gridcolor: '#263943', nticks: 10 } }} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />}</article>)}</div> : <><Plot className="chart" data={comparePatternData} layout={patternLayout} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '300px' }} /><div className="scenario-averages">{compareResult.scenarios.map(scenario => <span key={scenario.name}><small>{scenarioNameLabel(scenario, locale)}</small><strong>{scenario.metrics?.integrated_average_gain.average_db.toFixed(2)} dB</strong></span>)}</div><Plot className="terrain-chart" data={compareResult.scenarios.filter(scenario => scenario.profile).map((scenario, index) => ({ x: scenario.profile?.distances_m, y: scenario.profile?.heights_m, type: 'scatter' as const, mode: 'lines' as const, name: scenarioNameLabel(scenario, locale), line: { color: palette.scenarios[index % palette.scenarios.length], width: 2, dash: scenarioDash(index, accessiblePatterns, palette.scenarios.length) } }))} layout={{ autosize: true, margin: { l: 48, r: 16, t: 12, b: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: t('distanceAxis') }, gridcolor: '#263943', nticks: 14 }, yaxis: { title: { text: t('altitudeAxis') }, gridcolor: '#263943', nticks: 10 }, legend: { orientation: 'h' } }} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '100%' }} /></>}
          <div className="scenario-ray-list">{compareResult.scenarios.map((scenario, index) => <ScenarioRayTrace key={scenario.name} scenario={scenario} index={index} angles={compareResult.angles_deg} rayKinds={rayKinds} rayAngleLimit={rayAngleLimit} onToggle={kind => setRayKinds(current => ({ ...current, [kind]: !current[kind] }))} onHelp={() => setShowRayHelp(true)} accessibleColors={colorblindMode} accessiblePatterns={accessiblePatterns} locale={locale} />)}</div>
          {compareResult.interpretation && <div className="interpretation"><small>{t('automaticReading')}</small><strong>{compareResult.interpretation.headline}</strong><p>{compareResult.interpretation.beginner}</p><p className="technical">{compareResult.interpretation.technical}</p><ul>{compareResult.interpretation.observations.map((observation, index) => <li key={index}>{observation}</li>)}</ul></div>}
          {compareResult.limitations && <div className="limitations"><small>{t('modelLimits')}</small>{compareResult.limitations.map((limitation, index) => <p key={index}>• {limitation}</p>)}</div>}
          <div className="exports"><small>{t('export')}</small>{['json', 'csv', 'png', 'svg', 'pdf'].map(format => <button key={format} type="button" onClick={() => exportComparison(format)}>{format.toUpperCase()}</button>)}</div>
        </> : result ? <>
          <div className="metrics"><div><small>{t('peakOfPattern')}</small><strong>{peak?.toFixed(2)} <b>dB</b></strong></div><div><small>{t('peakAngleLabel')}</small><strong>{peakAngle?.toFixed(2)} <b>°</b></strong></div><div><small>{t('integratedAverageLabel')}</small><strong>{result.metrics?.integrated_average_gain.average_db.toFixed(2)} <b>dB</b></strong></div><div><small>{t('beamwidth3db')}</small><strong>{result.metrics?.beamwidth_3db?.width_deg?.toFixed(2) ?? '—'} <b>°</b></strong></div><div><small>{t('profilePointsLabel')}</small><strong>{profilePointCount(result.profile)}</strong></div><div><small>FIGURE OF MERIT</small><strong>{result.metrics?.figure_of_merit_db?.toFixed(2) ?? '—'} <b>dB</b></strong></div></div>
          {result.aoa?.message && <div className="aoa-status">{result.aoa.message}</div>}
          {result.aoa?.available && <div className="aoa-status">{tr('Estatística carregada:', 'Statistics loaded:', 'Estadística cargada:')} {result.aoa.band || t('compatibleBand')} · {result.aoa.angles_deg.length} {tr('ângulos', 'angles', 'ángulos')} · {result.aoa.source || t('projectDefault')}</div>}
          <Plot className="chart" data={resultPatternData} layout={patternLayout} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '300px' }} />
          <div className="terrain-heading"><small>{t('terrainProfile')}</small><span>{profilePointCount(result.profile)} {t('pointsWord')} · {t('distance').toLowerCase()}</span></div>
          <Plot className="terrain-chart" data={[{ x: result.profile.distances_m.slice(0, profilePointCount(result.profile)), y: result.profile.heights_m.slice(0, profilePointCount(result.profile)), type: 'scatter', mode: 'lines', line: { color: '#6bd48b', width: 2 }, hovertemplate: '%{x:.0f} m<br>%{y:.1f} m<extra></extra>' }]} layout={{ autosize: true, margin: { l: 48, r: 16, t: 12, b: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#9aabb5', family: 'Inter, sans-serif' }, xaxis: { title: { text: t('distanceAxis') }, gridcolor: '#263943', nticks: 14 }, yaxis: { title: { text: t('altitudeAxis') }, gridcolor: '#263943', autorange: true, nticks: 10 } }} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '100%' }} />
          {result.ray_trace?.available && <><div className="terrain-heading"><small>{t('rayTraceCore')}</small><span>{visibleRays.length} {rayUi.visible} · {Object.values(result.ray_trace.counts).reduce((total, count) => total + count, 0)} {rayUi.calculated}</span><div className="ray-limit-controls" role="group" aria-label={rayLimitUi.group}>{[10, 15, 20, 30].map(limit => <button type="button" key={limit} className={rayAngleLimit === limit ? 'accessibility-toggle active' : 'accessibility-toggle'} onClick={() => setRayAngleLimit(limit)} aria-pressed={rayAngleLimit === limit}>{rayLimitUi.upTo} {limit}º</button>)}<button type="button" className={rayAngleLimit === null ? 'accessibility-toggle active' : 'accessibility-toggle'} onClick={() => setRayAngleLimit(null)} aria-pressed={rayAngleLimit === null}>{rayLimitUi.all}</button></div><button type="button" className="ray-help-button" onClick={() => setShowRayHelp(true)} aria-label={rayUi.explain}>?</button></div><div className="ray-controls">{Object.entries(rayLabels).map(([kind, label]) => <button type="button" key={kind} className={rayKinds[kind] ? 'ray-toggle active' : 'ray-toggle'} onClick={() => setRayKinds(current => ({ ...current, [kind]: !current[kind] }))} style={{ '--ray-color': rayColors[kind] } as CSSProperties}><i />{label} <small>{result.ray_trace?.counts[kind] || 0}</small></button>)}</div><Plot className="ray-chart" data={rayTraceData} layout={rayTraceLayout} config={{ responsive: true, displaylogo: false }} useResizeHandler style={{ width: '100%', height: '100%' }} /></>}
          <div className="result-note">{result.configuration.diffraction_disable ? t('noDiffraction') : t('diffraction')} · {tr('reflexão e difração dupla do terreno · atmosfera não modelada', 'terrain reflection and double diffraction · atmosphere not modeled', 'reflexión y doble difracción del terreno · atmósfera no modelada')} · {result.configuration.frequency_mhz.toFixed(2)} MHz · {result.profile.source_units}</div>
          {result.interpretation && <div className="interpretation"><small>{t('automaticReading')}</small><strong>{result.interpretation.headline}</strong><p>{result.interpretation.beginner}</p><p className="technical">{result.interpretation.technical}</p><ul>{result.interpretation.observations.map((observation, index) => <li key={index}>{observation}</li>)}</ul></div>}
          {result.limitations && <div className="limitations"><small>{t('modelLimits')}</small>{result.limitations.map((limitation, index) => <p key={index}>• {limitation}</p>)}</div>}
          <div className="exports"><small>{t('export')}</small>{['json', 'csv', 'png', 'svg', 'pdf'].map(format => <button key={format} type="button" onClick={() => exportResult(format)}>{format.toUpperCase()}</button>)}</div>
        </> : <div className="empty"><div className="empty-graphic"><span>⌁</span></div><strong>{t('emptyTitle')}</strong><p>{t('emptyText')}</p></div>}
        {(result || compareResult) && <div className="ai-box"><button type="button" className="ai-button" onClick={askAI} disabled={aiLoading}>{aiLoading ? t('interpreting') : t('explainResult')}</button>{aiError && <p className="ai-error">{aiError}</p>}{aiExplanation && <div className="ai-answer"><small>{tr('OPINIÃO TÉCNICA', 'TECHNICAL OPINION', 'OPINIÓN TÉCNICA')} · {tr('confiança', 'confidence', 'confianza')} {aiExplanation.confianca}</small><strong>{aiExplanation.headline}</strong><p>{aiExplanation.for_leigo}</p>{compareResult && <p><b>{tr('Cenários analisados:', 'Scenarios analyzed:', 'Escenarios analizados:')}</b> {aiExplanation.cenarios_analisados.join(', ')}</p>}<b>{tr('Melhor cenário:', 'Best scenario:', 'Mejor escenario:')} {aiExplanation.melhor_cenario}</b><ul>{aiExplanation.por_que.map((reason, index) => <li key={index}>{reason}</li>)}</ul><b>{tr('Recomendações:', 'Recommendations:', 'Recomendaciones:')}</b><ul>{aiExplanation.recomendacoes.map((recommendation, index) => <li key={index}>{recommendation}</li>)}</ul><p className="technical">{tr('Cuidados:', 'Cautions:', 'Precauciones:')} {aiExplanation.cuidados.join(' ')}</p></div>}</div>}
      </section>
    </section>
    {showHelp && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowHelp(false) }}>
      <section className="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <div className="help-modal-header"><div><p className="eyebrow">{t('quickGuide')}</p><h2 id="help-title">{t('helpTitle')}</h2></div><button type="button" className="modal-close" onClick={() => setShowHelp(false)} aria-label={t('close')}>×</button></div>
        <p className="help-intro">{t('helpIntro')}</p>
        <div className="help-list">{localizedHelpItems.map(([title, description]) => <article key={title}><h3>{title}</h3><p>{description}</p></article>)}</div>
        <div className="help-tip"><strong>{t('helpTip')}</strong><p>{locale === 'en' ? 'Use the real profile, your band frequency, measured antenna height, diffraction enabled, and the default ground values. Then compare heights or antenna types to see which scenario best serves your objective.' : locale === 'es' ? 'Use el perfil real, la frecuencia de su banda, la altura medida de la antena, la difracción activada y los valores predeterminados del suelo. Después compare alturas o tipos de antena para entender qué escenario favorece su objetivo.' : 'Use o perfil real, frequência da sua banda, altura medida da antena, difração ligada e os valores de solo padrão. Depois compare alturas ou tipos de antena para entender qual cenário favorece seu objetivo.'}</p></div>
      </section>
    </div>}
    {showRayHelp && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowRayHelp(false) }}>
      <section className="help-modal" role="dialog" aria-modal="true" aria-labelledby="ray-help-title">
        <div className="help-modal-header"><div><p className="eyebrow">{t('rayTraceCore')}</p><h2 id="ray-help-title">{t('rayHelpTitle')}</h2></div><button type="button" className="modal-close" onClick={() => setShowRayHelp(false)} aria-label={t('close')}>×</button></div>
        <p className="help-intro">{t('rayHelpIntro')}</p>
        <div className="help-list">{localizedRayHelpItems.map(([title, description]) => <article key={title}><h3>{title}</h3><p>{description}</p></article>)}</div>
        <div className="help-tip"><strong>{t('rayTip')}</strong><p>{locale === 'en' ? 'Use the colored buttons to hide or show categories. The legend and hover text identify the type, departure angle, estimated gain, and distance.' : locale === 'es' ? 'Use los botones de colores para ocultar o mostrar categorías. La leyenda y el texto al pasar el cursor identifican el tipo, el ángulo de salida, la ganancia estimada y la distancia.' : 'Use os botões coloridos para ocultar ou exibir categorias. A legenda e o texto ao passar o mouse identificam o tipo, o ângulo de saída, o ganho estimado e a distância.'}</p></div>
      </section>
    </div>}
    {showSoilHelp && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowSoilHelp(false) }}>
      <section className="help-modal" role="dialog" aria-modal="true" aria-labelledby="soil-help-title">
        <div className="help-modal-header"><div><p className="eyebrow">{t('terrainType')}</p><h2 id="soil-help-title">{t('soilHelpTitle')}</h2></div><button type="button" className="modal-close" onClick={() => setShowSoilHelp(false)} aria-label={t('close')}>×</button></div>
        <p className="help-intro">{t('soilHelpIntro')}</p>
        <div className="help-list">{localizedSoilHelpItems.map(([title, description]) => <article key={title}><h3>{title}</h3><p>{description}</p></article>)}</div>
        <div className="help-tip"><strong>{t('soilHelpTip')}</strong><p>{tr('Se não souber o tipo exato, use "Média (padrão HFTA)" — é o valor de referência do próprio HFTA e funciona bem para a maioria dos terrenos. Para antenas horizontais (Yagi, dipolo), mudar o tipo de terreno altera o padrão só em ângulos de elevação bem altos.', 'If you are not sure of the exact type, use "Average (HFTA default)" — it is HFTA\'s own reference value and works well for most terrain. For horizontally polarized antennas (Yagi, dipole), changing the terrain type only shifts the pattern at very high elevation angles.', 'Si no sabe el tipo exacto, use "Media (predeterminado HFTA)" — es el valor de referencia del propio HFTA y funciona bien para la mayoría de los terrenos. Para antenas de polarización horizontal (Yagi, dipolo), cambiar el tipo de terreno solo afecta el patrón en ángulos de elevación muy altos.')}</p></div>
      </section>
    </div>}
    {showFeedback && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowFeedback(false) }}>
      <section className="help-modal feedback-modal" role="dialog" aria-modal="true" aria-labelledby="feedback-title">
        <div className="help-modal-header"><div><p className="eyebrow">{t('openSourceCollab')}</p><h2 id="feedback-title">{t('feedbackTitle')}</h2></div><button type="button" className="modal-close" onClick={() => setShowFeedback(false)} aria-label={t('close')}>×</button></div>
        <p className="help-intro">{t('feedbackIntro')}</p>
        <div className={`feedback-form-shell${feedbackFormHidden ? ' feedback-form-shell-hidden' : ''}`}>
          {feedbackSent && <div className="feedback-success-overlay" role="status" aria-live="polite"><strong>{feedbackStatus || tr('Obrigado pela colaboração!', 'Thank you for helping!', '¡Gracias por colaborar!')}</strong>{feedbackFormHidden ? <button type="button" className="submit feedback-new-button" onClick={startNewFeedback}>{t('newSuggestion')} <span>→</span></button> : <small>{tr(`O formulário será liberado novamente em ${feedbackCountdown}s.`, `The form will be available again in ${feedbackCountdown}s.`, `El formulario estará disponible nuevamente en ${feedbackCountdown}s.`)}</small>}</div>}
          {!feedbackFormHidden && <form className={`feedback-form${feedbackSent ? ' feedback-form-obscured' : ''}`} onSubmit={submitFeedback}>
          <label className="feedback-honeypot" aria-hidden="true">Website<input tabIndex={-1} autoComplete="off" name="website" /></label>
          <div className="feedback-fields"><label>{t('optionalName')}<input value={feedbackName} onChange={event => setFeedbackName(event.target.value)} maxLength={120} placeholder={tr('Como podemos chamar você?', 'How should we address you?', '¿Cómo podemos llamarle?')} /></label><label>{t('replyEmail')}<input required type="email" value={feedbackEmail} onChange={event => setFeedbackEmail(event.target.value)} placeholder="you@example.com" /></label></div>
          <label>{t('subject')}<select value={feedbackCategory} onChange={event => setFeedbackCategory(event.target.value)}><option value="suggestion">{tr('Sugestão', 'Suggestion', 'Sugerencia')}</option><option value="result-correction">{tr('Correção de resultado', 'Result correction', 'Corrección de resultado')}</option><option value="interface-issue">{tr('Problema na interface', 'Interface issue', 'Problema en la interfaz')}</option><option value="new-feature">{tr('Novo recurso', 'New feature', 'Nueva función')}</option><option value="other">{tr('Outro', 'Other', 'Otro')}</option></select></label>
          <label>{t('message')}<textarea required value={feedbackMessage} onChange={event => setFeedbackMessage(event.target.value)} maxLength={4000} rows={7} placeholder={tr('Descreva sua ideia, dificuldade ou sugestão…', 'Describe your idea, difficulty, or suggestion…', 'Describa su idea, dificultad o sugerencia…')} /></label>
          <div className="feedback-captcha"><div ref={feedbackCaptchaRef} className="cf-turnstile" data-sitekey={TURNSTILE_SITE_KEY} data-action="turnstile-spin-v2" /><small>{t('securityCheck')}</small></div>
          {feedbackError && <div className="error" role="alert">{feedbackError}</div>}
          <button className="submit" disabled={feedbackLoading}>{feedbackLoading ? t('sending') : t('sendMessage')} <span>→</span></button>
          </form>}
        </div>
      </section>
    </div>}
    <footer className="site-footer">
      <strong>OpenHFTA <span>·</span> {t('footer')}</strong>
      <small>{t('footerMaintained')} <a href="https://www.qrz.com/db/PY2UID" target="_blank" rel="noreferrer">Paulo Matias — PY2UID ↗</a> · {t('footerWebIntegration')} <a href="https://www.qrz.com/db/PT9TI" target="_blank" rel="noreferrer">PT9TI ↗</a></small>
    </footer>
  </main>
}

export default App
