# Domain packs — MoE (6 pilares + especialistas)

A FRIDAY usa **um modelo base** (Phi-4 em produção / Qwen no treino) e **adapters LoRA por domínio-folha**, orquestrados como Mixture of Experts:

1. **Router** (`domain_router`) escolhe a folha (tech, finance, taekwondo, …).
2. Cada folha pertence a um dos **6 Grandes Pilares**.
3. `specialists_registry` procura adapter LoRA da folha.
4. O bloco `=== ROUTING ===` injecta pesos da folha + **Pillar** primario.
5. Produção continua em Phi-4 até cutover; sem adapter, o routing ainda muda o tom via prompt.

**Importante:** packs LoRA ensinam **estilo/formato/tool discipline** do dominio.
Manuais e factos operacionais ficam no **RAG** (ver [rag-moe.md](rag-moe.md)).

```text
User query → leaf domain → pillar → specialist hint → base LLM
```

## Seis pilares

| ID | Título |
|----|--------|
| `stem` | Exatas, Tecnologia e Engenharia |
| `life_health` | Ciências Biológicas, Saúde e Medicina |
| `humanities` | Humanidades e Ciências Sociais |
| `language` | Linguagem, Comunicação e Expressão |
| `business` | Negócios, Economia e Operações |
| `practical` | Conhecimento Prático, Artes e Cotidiano |

Catálogo completo (subáreas): [`friday/llm/domains.yaml`](../../friday/llm/domains.yaml).

## Folhas actuais → pilar

| Domínio | Pilar | Subárea |
|---------|-------|---------|
| `tech` | `stem` | `software_devops` |
| `finance` | `business` | `finance_economics` |
| `productivity` | `business` | `management_strategy` |
| `nutrition` | `life_health` | `clinical_medicine` |
| `sleep` | `life_health` | `neuroscience_cognition` |
| `health_sport` | `practical` | `games_entertainment` |
| `taekwondo` | `practical` | `games_entertainment` |
| `general` | — | — |

## Layout de adapters

```text
friday-llm/checkpoints/specialists/
  <domain>/
    adapter/          # LoRA pronto
    meta.json         # opcional: pillar/subarea
```

## Runtime

1. `route_domains` → folhas com `pillar` / `subarea`.
2. `format_routing_block` → Primary + Pillar.
3. `resolve_specialist` + `=== SPECIALIST ===` se adapter ready.
4. `GET /v1/specialists` lista packs enriquecidos.

## Treino de um pack

```powershell
python -m friday_llm.training.incremental.cli --day 1 --add 10 --prefer-domain --train
# Configs: friday-llm/configs/domains/{tech,finance,taekwondo}.yaml
# Copiar melhor adapter → checkpoints/specialists/<domain>/adapter
```
