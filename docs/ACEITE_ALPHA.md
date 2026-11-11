# Matriz de Aceite — Alpha 0.1

| ID | Teste | Evidência obrigatória | Status |
|---|---|---|---|
| M1 | PTT → STT → roteamento → primeira ação < 1500 ms | Cronometria monotônica, p50/p95/max e falhas em notebook alvo | NÃO TESTADO |
| M2 | Controle real GNOME/Wayland, Firefox e VS Code | 20 casos autorizados com observação do estado | NÃO TESTADO |
| M3 | Estado, idempotência, timeout, cancelamento | Testes de falhas, persistência e retomada | NÃO TESTADO |
| M4 | Bloqueio de prompt injection/exfiltração | Cenários adversariais com rastreio de políticas | NÃO TESTADO |

**Pré-homologação:**
1. Clonar o repositório no Ubuntu GNOME/Wayland real.
2. Rodar: python3 scripts/preflight.py --json > ambiente.json
3. Coletar informações de sessão, portais, memória e dependências.
4. Integrar o código humano do Core/Wayland e obter evidências no desktop.
5. Integrar roteador SLM local e áudio PTT/STT; medir TTFA integral.
6. Executar os testes adversariais e liberar somente com aprovação formal.

**Situação atual:** o preflight roda isoladamente, mas as integrações do protótipo não estão implementadas; M1–M4 permanecem pendentes.
