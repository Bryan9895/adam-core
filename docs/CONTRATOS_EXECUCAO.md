# Contratos de execução — rascunho para revisão humana (rev. 0.2)

Os contratos abaixo são **desenho de interface**, não implementação do Core ou da máquina de estados, cuja autoria é humana.

## Fluxo

`TaskRequest` (orquestração) → política independente do LLM → `ToolAction` tipada → `ToolResult` verificável → checkpoint operacional.

- `task_id`: UUID emitido pelo núcleo confiável; correlaciona logs, estados e recursos.
- `intent`: nome estável da ação (por exemplo, `open_app`, `focus_window`), sempre validado contra catálogo.
- `idempotency_key`: chave opaca emitida pela camada confiável para deduplicação/reconciliação, **não recebida de conteúdo externo**.
- `auth_context_ref`: identificador opaco de autorização emitido pela sessão do usuário. Nunca confiar em um modelo para estabelecer suas próprias permissões.
- `trace_id`: correlaciona eventos e evidências sem transportar segredos.
- `deadline_ms`: limite de duração, sempre imposto por código.
- `preconditions` e `postcondition`: verificações estruturadas obrigatórias antes/depois de executar ações.
- `ToolResult.evidence`: metadados minimizados e sem conteúdo de usuários.
- `ToolResult.observed_state`: retorno obrigatório (pode ser null se impossível observar), com momento, origem, alvo e atributos minimizados.
- `ToolResult.postcondition_check`: comparação independente com a pós-condição. Um status completed exige verified=true, observed_state não nulo e matched=true.

## Invariantes da futura máquina de estados

`accepted → routed → authorized → executing → verifying → completed`, com `failed`, `blocked`, `cancelled`, `timed_out` e `needs_user` como saídas. Retorno bem-sucedido de um clique não significa que a tarefa foi concluída. A última ação é verificada por observação posterior antes de retentar. Operações não idempotentes nunca são repetidas automaticamente sem confirmação de ausência do efeito anterior.

## Exemplo

```json
{
  "schema_version": "0.1",
  "task_id": "8be21031-80dd-42db-b194-2b96033e4fd6",
  "trace_id": "f9d4f706-e866-4eec-ac96-e3c252441eb0",
  "source": "ptt",
  "intent": "open_app",
  "params": {"app_id": "org.mozilla.firefox"},
  "auth_context_ref": "local-session:opaque-reference",
  "idempotency_key": "task:8be21031:open_firefox",
  "deadline_ms": 10000
}
```

Ver esquemas em `contracts/task_request.schema.json`, `tool_action.schema.json` e `tool_result.schema.json`.


## ToolResult 0.2 — confirmação de efeito

```json
{
  "schema_version": "0.2",
  "task_id": "8be21031-80dd-42db-b194-2b96033e4fd6",
  "action_id": "f9d4f706-e866-4eec-ac96-e3c252441eb0",
  "status": "completed",
  "verified": true,
  "elapsed_ms": 77,
  "error_code": null,
  "evidence": [
    {
      "kind": "window",
      "ref": "window:firefox"
    }
  ],
  "observed_state": {
    "observed_at": "2026-11-11T18:00:00Z",
    "source": "at_spi",
    "target_ref": "window:firefox",
    "attributes": {
      "visible": true
    }
  },
  "postcondition_check": {
    "check": "window_visible",
    "matched": true,
    "observation_fresh_ms": 21
  }
}
```

Uma chamada ao driver sem observação posterior não permite marcar `completed`. Se a observação falhar, o estado pode ser nulo, mas o status deverá indicar falha/incerteza, nunca sucesso.

## Versão 0.2: decisões ainda abertas

1. Modelo concreto de `auth_context_ref` (sessão e revogação).
2. Persistência operacional: transações SQLite WAL versus journal append-only; decisão humana Semana 2.
3. Pós-condições tipadas por `intent`, incluindo janela visível/focada.
4. Semântica de rollback e reconciliação após crash.
5. Modelo de qualidade de evidência para Wayland e CDP.

**Gate da Semana 1:** contratos versionados e revistos; não equivale a executor pronto.
