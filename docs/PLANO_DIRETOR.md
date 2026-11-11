# Projeto Adam — Plano Diretor Consolidado (Revisão 1.1)

**Aprovação:** diretoria, com quatro emendas obrigatórias.  
**Data:** 11/11/2026  
**Alvo:** Adam Alpha 0.1 em 6 semanas (marco de decisão 23/12/2026).  
**Plataforma de referência:** Ubuntu GNOME/Wayland, notebook com 8 GB de RAM.

## 1. Visão

Criar um assistente pessoal local, nativo para Linux, capaz de receber comandos de voz ou texto e executar tarefas no computador com segurança, validação de resultados e recuperação de falhas. Não é um chatbot nem um executor irrestrito de shell.

**Princípios:** execução verificável, estado operacional persistente, privilégios mínimos, processamento local prioritário, arquitetura híbrida, métricas ponta a ponta, arquitetura modular e controle de recursos. O Adam antigo fica preservado como referência, mas não será reutilizado como arquitetura.

**Fora do Alpha:** escuta contínua, memória semântica/vetorial, equipes multiagentes em produção, automação residencial, portabilidade universal, TTS local e execução arbitrária de comandos.

## 2. Emendas oficiais

### E1 — RAM microgerenciada e TTS remoto

O sistema-alvo possui aproximadamente 7,45 GiB físicos (8 GB comerciais). **TTS somente na nuvem**, por ElevenLabs ou equivalente; sem fallback local no Alpha.

Envelope inicial de orçamento, a confirmar em hardware real:

| Componente | Teto planejado |
|---|---:|
| GNOME/sistema e aplicativos de usuário | 2,25 GiB |
| Navegador automatizado | 1,25 GiB |
| STT + roteador local (por carga sob demanda) | 1,60 GiB |
| Núcleo + interface | 0,35 GiB |
| Folga operacional | 1,50 GiB |
| **Total** | **6,95 GiB** |

Esses valores são limites de desenho, **não medições**. Medir picos RSS/PSS, RAM disponível e latência; estabelecer comportamento de degradação/cancelamento em pressão de memória.

Playwright com sessão controlada, limite inicial de duas abas ativas, descarte de abas ociosas e bloqueio de imagens/vídeos em tarefas textuais, sempre permitindo mídia necessária à tarefa.

### E2 — Código crítico escrito e depurado por humanos

**Core, máquina de estados e integrações Wayland/AT-SPI/D-Bus/libei** devem ser escritos, validados e depurados por engenheiros humanos responsáveis. IA pode auxiliar em documentação, testes e integrações de alto nível, mas não substitui autoria nem revisão humana nessas camadas. Evidência em simulação não substitui a execução no desktop real.

### E3 — Memória operacional desde a Fase 1

Persistir tarefas, estado, checkpoint, última ação, evidência, tentativas, erro e identificadores de idempotência junto ao núcleo. SQLite WAL é candidato inicial; Redis é opcional e não deve ser dependência obrigatória de um programa pessoal. Reinícios exigem reconciliação com o SO antes de reexecutar ações. Memória de longo prazo/semântica só na Fase 9.

### E4 — Apenas Alpha tem prazo

O planejamento oficial vincula **seis semanas exclusivamente ao Alpha 0.1**. Não há data prometida para Beta ou versão 1.0. Falha dos critérios de aceite obriga relatório com bloqueios e ação corretiva; é proibido cortar testes de segurança para proteger prazo.

## 3. Arquitetura

Usuário (Push-to-Talk/texto) → STT local → roteador local (regras + SLM pequeno) → executor direto ou LLM planejador → gerenciador de tarefa/estados → política de segurança → seleção de ferramenta → validação de pós-condição → memória operacional → retorno por texto/TTS remoto.

**Hierarquia preferencial de ferramentas:**
1. API / CLI estruturada.
2. CDP / WebDriver / Playwright, para aplicações web e Electron compatíveis e autorizadas.
3. AT-SPI / D-Bus / XDG Desktop Portal e mecanismos Wayland autorizados.
4. Visão sob demanda, quando mecanismos anteriores forem insuficientes.

Não se trata de uma cascata fixa: o sistema seleciona pelo tipo da tarefa. CDP não fornece acesso universal a Electron nem ao perfil privado do navegador do usuário.

### Contratos de execução

Toda solicitação inclui: task_id, origem, intenção, parâmetros, contexto de autorização e prazo. Toda ação inclui: ferramenta, argumentos tipados, capacidade exigida, idempotency_key, timeout, orçamento de retries e condição de sucesso. Retorno inclui estado, evidências, observação, erro e duração.

Máquina de estados básica: accepted → routed → authorized → executing → verifying → completed. Transições alternativas: blocked, failed, cancelled, timed_out, needs_user. Nunca retentar sem verificar o estado real do sistema.

### SLM local obrigatório

Comandos evidentes podem seguir regras determinísticas sem LLM. O roteador SLM local deve tratar classificação não trivial, sem autorização para conceder privilégios. Selecionar modelo pequeno quantizado que caiba na RAM e satisfaça desempenho real, não fixar modelo 8B. Meta hipotética de 50 ms por inferência **não validada**.

### Dual-LLM e exfiltração

Um modelo sem ferramentas lê e resume conteúdo externo. O planejador privilegiado recebe sua saída **ainda tratada como dado não confiável**. Políticas independentes do modelo controlam origem, escopo, destinos de rede, fluxo de dados, execução de comandos e consentimento. Isolar dois modelos sozinho não impede prompt injection nem exfiltração; usar allowlist e auditoria.

## 4. Fases do projeto

| Fase | Área | Condição de saída |
|---|---|---|
| 0 | Preparação | Projeto reproduzível, arquitetura, preflight, matriz de hardware |
| 1 | Núcleo + memória operacional | Estado persistido, idempotência, erro, timeout, cancelamento; revisão humana |
| 2 | Inteligência | Regras e SLM local; avaliação de rota e RAM |
| 3 | Ferramentas | Executor tipado, políticas de acesso e evidências |
| 4 | Desktop | Wayland/portais/AT-SPI com testes reais |
| 5 | Navegador | Playwright/CDP/WebDriver com limites de abas e mídia |
| 6 | Visão | Captura e interpretação sob demanda, verificações |
| 7 | Voz e interface | PTT, STT local, TTS nuvem, UI nativa e TTFA |
| 8 | Segurança ampliada | Fortalecer Dual-LLM e testes adversariais; segurança mínima existe desde Fase 1 |
| 9 | Memória semântica | Preferências com consentimento e busca contextual |
| 10 | Autonomia avançada | Planejamento de múltiplas etapas; subagentes apenas se úteis |
| 11 | Estabilização/release | Regressão, auditoria, compatibilidade e lançamento após aceite |

Fases 0–7 compõem o escopo mínimo do Alpha; requisitos de defesa contra conteúdo não confiável não podem ficar para a Fase 8.

## 5. Cronograma oficial — 6 semanas

| Semana | Intervalo | Entrega |
|---|---|---|
| 1 | 11–17/11 | Preflight no notebook, contratos, instrumentação, spike humano Wayland |
| 2 | 18–24/11 | Core humano, estados, memória operacional, idempotência, timeout |
| 3 | 25/11–01/12 | Roteamento regras + SLM quantizado real, avaliação de RAM e acerto |
| 4 | 02–08/12 | Ferramentas, desktop GNOME, navegador com CDP/WebDriver |
| 5 | 09–15/12 | PTT + STT, TTS remoto, visão sob demanda, coleta de TTFA |
| 6 | 16–22/12 | Integração, testes adversariais, estabilidade, homologação |
| **Decisão** | **23/12/2026** | **Aceitar ou devolver Alpha com bloqueios explícitos** |

O prazo é agressivo e condicionado à viabilidade dos spikes iniciais. Beta e v1.0 só serão planejados após avaliação formal do Alpha.

## 6. Quatro metas de aceite obrigatórias

**M1 — TTFA < 1.500 ms.** Medir desde o evento de soltura do PTT até a primeira ação observável, incluindo STT, roteamento e autorização. Registrar p50, p95, máximo, cold/warm start, falhas e configuração do notebook. Um TTFA excedente é falha a investigar, mesmo quando a média é boa.

**M2 — Desktop real.** Demonstrar automação autorizada no GNOME/Wayland, incluindo Firefox e VS Code quando instalados, com evidência em pelo menos vinte cenários previamente acordados.

**M3 — Verificação e recuperação.** Persistência operacional, timeout, cancelamento, idempotência, reconciliação de estado e reação a aplicativos lentos ou janela ausente; não abrir quinze janelas por retries cegos.

**M4 — Segurança.** Em bateria obrigatória com páginas, emails e arquivos maliciosos, bloquear 100% das tentativas de comandos privilegiados e envio não autorizado de dados. Isso não significa proteção absoluta contra ataques não testados.

**Métrica auxiliar:** conclusão de 95% de cem tarefas simples previamente definidas, com denominador, exclusões e logs publicados. **Nenhuma simulação equivale ao aceite M1–M4.**

## 7. Homologação e limites

Homologar **no notebook Ubuntu GNOME/Wayland com 8 GB**, registrando GNOME, kernel, portais, AT-SPI, SLM, STT, latências, RSS/PSS, browser, número de abas, conexão e voz remota. O script preflight apenas relata o ambiente, **não prova funcionamento do Alpha**. Nenhuma chave de API será gravada em Git ou logs.

Testar falhas de rede TTS, Wayland sem autorização, conteúdo externo malicioso, execução interrompida, RAM pressionada e aplicativos lentos. Degradação deve ser visível e controlada.

## 8. Governança

Mudanças têm contratos, testes, evidência, rollback e revisão proporcional ao risco. Código crítico de SO e Core exige autoria/revisão humana documentada. Funcionalidades não são concluídas por demonstração isolada. O chefe decide formalmente o aceite após M1–M4 e riscos críticos resolvidos.

**Deliberação:** Plano consolidado e aprovado para desenvolvimento. Criar documentação/diagnóstico/commits não equivale a ter o protótipo rodando no computador-alvo.
