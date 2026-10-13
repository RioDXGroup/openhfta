"""Optional AI explanation layer over deterministic OpenHFTA results."""
import json
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import dotenv_values, load_dotenv
    # Resolve from the repository instead of depending on the process cwd.
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_ENV_PATH, override=True)
    _DOTENV_VALUES = dotenv_values(_ENV_PATH)
except ImportError:
    _DOTENV_VALUES = {}

class AIUnavailable(RuntimeError):
    pass

AI_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "for_leigo": {"type": "string"},
        "melhor_cenario": {"type": "string"},
        "cenarios_analisados": {"type": "array", "items": {"type": "string"}},
        "por_que": {"type": "array", "items": {"type": "string"}},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "cuidados": {"type": "array", "items": {"type": "string"}},
        "confianca": {"type": "string", "enum": ["baixa", "media", "alta"]},
    },
    "required": ["headline", "for_leigo", "melhor_cenario", "cenarios_analisados", "por_que", "recomendacoes", "cuidados", "confianca"],
    "additionalProperties": False,
}

def ai_status() -> dict[str, Any]:
    models = _models()
    return {
        "enabled": bool(_setting("OPENROUTER_API_KEY")),
        "provider": "openrouter",
        "model": models[0],
        "fallback_models": models[1:],
    }


def _setting(name: str) -> str | None:
    return os.getenv(name) or _DOTENV_VALUES.get(name)


def _models() -> list[str]:
    configured = _setting("OPENROUTER_MODELS") or _setting("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
    return [model.strip() for model in configured.split(",") if model.strip()]


def explain_with_ai(analysis_payload: dict[str, Any]) -> dict[str, Any]:
    api_key = _setting("OPENROUTER_API_KEY")
    if not api_key:
        raise AIUnavailable("IA não configurada. Defina OPENROUTER_API_KEY para habilitar esta explicação.")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": _setting("OPENROUTER_SITE_URL") or "http://localhost:8000",
                "X-Title": _setting("OPENROUTER_APP_NAME") or "OpenHFTA",
            },
        )
        models = _models()
        response = client.chat.completions.create(
            model=models[0],
            extra_body={"models": models[1:]} if len(models) > 1 else {},
            messages=[
                {"role": "system", "content": "Você é um especialista em antenas e propagação de ondas curtas (HF), especificamente no tipo de análise de elevação sobre terreno realizado pelo OpenHFTA. Dê uma opinião técnica sincera e útil sobre o cenário ou comparação: indique claramente o melhor cenário somente quando os dados sustentarem a conclusão; se houver empate, conflito entre métricas ou dados insuficientes, diga que a decisão é inconclusiva e explique o que falta. Não trate este sistema como um analisador VHF/UHF de linha de visada. A frequência pode vir como banda: por exemplo, 20m significa aproximadamente 14,2 MHz. Explique em português claro e aprofunde a análise em três camadas: (1) padrão calculado, picos, nulos, largura e faixas de elevação; (2) perfil do terreno, relevo, declives, ponto mais alto/baixo e linha de visada aproximada; (3) traçado geométrico, distinguindo caminhos diretos, refletidos, difratados e de dupla difração, seus ângulos de saída e contatos com o terreno. Use a contagem de trajetórias apenas como geometria: ela não é potência recebida. Relacione os ângulos de saída ao padrão de ganho da antena e sinalize trajetórias muito inclinadas ou fora do objetivo de longa distância sem chamá-las automaticamente de sinais úteis. Quando existir terrain_profiles ou terrain_profile, analise também esses dados: compare a forma do relevo, os pontos altos e baixos, as inclinações e as diferenças de perfil entre os cenários/azimutes. Use sempre as unidades informadas pelo usuário; se a entrada estiver em metros, escreva alturas, distâncias e elevações em metros. Os campos *_ft são apenas detalhes internos da ABI e não devem ser usados na explicação principal quando houver campos *_m. Analise obrigatoriamente todos os itens de scenarios e de scenario_summary, inclusive C e D quando existirem; nunca reduza a análise ao primeiro par A e B. Relacione o padrão de elevação de cada cenário ao respectivo perfil de terreno e recomende o melhor cenário entre todos. Em por_que, cite evidências concretas de padrão, propagação e terreno para cada cenário. Em recomendacoes, sugira mudanças práticas somente quando forem justificadas pelos dados, como altura, tipo de antena, fase, posição da torre ou comparação de outro perfil; não invente tilt, frente/costas ou parâmetros que o modelo não recebeu. Se não houver base suficiente, recomende medir, comparar ou simular a alteração antes de adotá-la. O modelo representa um perfil 2D por azimute, usa polarização horizontal e não calcula acoplamento mútuo entre elementos. A saída é uma estimativa de padrão de elevação, dependente do perfil/DEM, com possíveis artefatos no passo de 0,25 graus; não é garantia de enlace. Em HF, linha de visada geométrica bloqueada não significa automaticamente enlace inviável: considere difração, que pode estar habilitada, o ângulo do padrão, a distância e os limites do modelo. Use somente os dados fornecidos. Não invente medições, não trate linha de visada aproximada como zona de Fresnel nem recomendação como garantia de enlace; declare limitações e peça contexto quando o objetivo não estiver claro."},
                {"role": "user", "content": "Analise estes resultados estruturados do OpenHFTA e recomende o melhor cenário para uma pessoa leiga. A lista scenario_summary foi preparada para garantir que nenhum cenário seja omitido:\n" + json.dumps(analysis_payload, ensure_ascii=False)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "openhfta_explanation",
                    "strict": True,
                    "schema": AI_SCHEMA,
                },
            },
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise AIUnavailable("O provedor de IA não retornou escolhas de resposta. Verifique o modelo configurado ou o limite de contexto.")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not content or not isinstance(content, str):
            raise AIUnavailable("O provedor de IA retornou uma resposta vazia. Verifique o modelo configurado ou o limite de contexto.")
        return json.loads(content)
    except ImportError as exc:
        raise AIUnavailable("Instale a dependência 'openai' para habilitar a IA.") from exc
    except Exception as exc:
        raise AIUnavailable(f"Falha ao consultar a IA: {exc}") from exc
