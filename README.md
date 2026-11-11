# Adam Core — Alpha 0.1

Assistente pessoal nativo para Ubuntu GNOME/Wayland. **Em construção.**

O repositório é novo; o código antigo permanece como referência. A arquitetura foi aprovada com quatro emendas oficiais e **a homologação real ainda não foi executada**.

## Plano Diretor aprovado (revisão 1.1)

O Adam será um agente pessoal com voz, execução verificável, estado operacional e automação híbrida. Ordem preferencial das ferramentas: **API/CLI → CDP/WebDriver → AT-SPI/D-Bus/portais → visão sob demanda**.

### Emendas obrigatórias

1. **RAM 8 GB:** orçamento de memória com limites e redução de carga sob pressão; TTS somente em nuvem (ElevenLabs ou similar) e navegador automatizado com bloqueio condicional de mídia, limpeza de abas e limites de consumo.
2. **Autoria humana:** Core, máquina de estados e integrações Wayland/AT-SPI implementados e depurados por engenheiros humanos. IA poderá auxiliar em testes, documentação e integrações de alto nível.
3. **Memória operacional:** nasce na Fase 1, com estados, checkpoints, última ação, erros e idempotência; memória semântica fica para Fase 9.
4. **Prazo:** seis semanas somente para o Alpha 0.1 (11/11 a 23/12/2026). Beta e V1.0 não têm cronograma aprovado.

### Metas obrigatórias do Alpha

- **M1:** TTFA inferior a 1,5 s desde soltar Push-to-Talk até a primeira ação real em comandos locais determinísticos; incluir STT, roteamento e execução, registrando p50/p95/máximo e falhas.
- **M2:** controle efetivo do desktop GNOME/Wayland com autorização e validação em Firefox e VS Code.
- **M3:** máquina de estados com confirmação de resultado, cancelamento, timeout, idempotência e sem loops.
- **M4:** bloqueio de instruções externas maliciosas e exfiltração sem autorização, em testes adversariais.

SLM local para roteamento, regras para caminho determinístico, Dual-LLM com fronteiras de confiança e políticas independentes do modelo. **É proibido anunciar simulações como homologação.**

## Estado

- ✅ Aprovação e planejamento de arquitetura.
- ⏳ Código de núcleo de SO a ser escrito e validado por humanos.
- ⏳ Voice/PTT/SLM/Playwright/AT-SPI/visão a implementar.
- ⏳ Homologação oficial em Ubuntu GNOME/Wayland de 8 GB não realizada.

Consulte o documento `docs/PLANO_DIRETOR.md` para o plano completo quando publicado.