| corrida | chunking | router | prompt RAG | Recuperación hit@4 | Ruteo | Herramienta | Rechazo | Acierto (juez) | Fidelidad (juez) | Acierto reglamentos | Acierto fechas/cálculos | Latencia mediana (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1_base | fijo | — | basico | 96% | 68% | 0% | 86% | 82% | 76% | 100% | 25% | 13.8 |
| 2_chunk_articulo | articulo | — | basico | 100% | 68% | 0% | 100% | 76% | 76% | 96% | 12% | 12.2 |
| 3_router_tools | articulo | v1 | basico | 100% | 92% | 100% | 100% | 88% | 94% | 84% | 100% | 14.1 |
| 4_prompt_v1 | articulo | v1 | v1 | 100% | 92% | 100% | 100% | 85% | 91% | 80% | 100% | 12.1 |
| 5_prompt_v2 | articulo | v1 | v2 | 100% | 92% | 100% | 100% | 88% | 94% | 84% | 100% | 12.5 |
| 6_final | articulo | v2 | v3 | 100% | 98% | 100% | 100% | 94% | 94% | 92% | 100% | 12.2 |
