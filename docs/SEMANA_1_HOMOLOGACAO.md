# Adam — Semana 1: ensaios e evidências

**Status: protocolo pronto; nenhuma evidência de funcionamento GNOME/Wayland no notebook foi coletada.**

**Restrição de autoria:** um engenheiro humano implementará e depurará Core, máquina de estados e adaptadores AT-SPI/Wayland. Este documento contém apenas ensaios manuais, contratos e um benchmark de Playwright de alto nível. Não escrever código de SLM nem ElevenLabs antes da aprovação do gate Wayland.

## Gate W1 — Sessão real GNOME/Wayland

Na máquina-alvo, com **sessão gráfica ativa do próprio usuário**:

```bash
echo "SESSION=$XDG_SESSION_TYPE DESKTOP=$XDG_CURRENT_DESKTOP"
loginctl show-session "$XDG_SESSION_ID" -p Type -p Desktop -p Name 2>/dev/null || true
sudo apt install accerciser libglib2.0-bin
gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus --method org.a11y.Bus.GetAddress
gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop | grep -E "RemoteDesktop|ScreenCast" || true
firefox
accerciser
```

Observação: `gdbus` vem de `libglib2.0-bin` nas versões usuais do Ubuntu. A existência de uma interface RemoteDesktop ou ScreenCast na introspecção **não comprova consentimento nem controle da janela**.

**Spike AT-SPI conduzido por humano:**
1. Abra Firefox nativo, não em contêiner, numa página de teste sem dados privados.
2. No Accerciser, localize o processo/janela Firefox; registre nome, role, children e ações expostas.
3. Selecione um elemento de ação (por exemplo, botão de uma página de teste).
4. Acione a função disponível pelo **próprio Accerciser** e documente o estado antes/depois; não use cliques por coordenada para alegar êxito AT-SPI.
5. Repita depois de reiniciar o Firefox, verificando se o identificador estável é role/nome/caminho semântico, não um índice de árvore fixo.
6. Um engenheiro humano documentará o próximo spike de controle por portal Wayland com autorização explícita (fluxo do RemoteDesktop/libei, dependendo do sistema); registrar recusa de permissão e comportamento seguro.
7. D-Bus: registrar disponibilidade de `org.a11y.Bus` e `org.freedesktop.portal.Desktop`; isso comprova apenas os serviços, não que um adaptador de controle foi validado.

**Evidências obrigatórias:** `preflight.json`, versão Ubuntu/Firefox, captura do Accerciser mostrando alvo e ações, captura antes/depois da ação real, resultado do consentimento do portal, notas de falha e autoria/revisão humana dos testes de baixo nível.

**Gate W1 aprovado somente quando:** um humano conseguir identificar e efetivamente ativar um elemento do Firefox via AT-SPI, e demonstrar sob autorização uma interação de entrada de desktop no Wayland. Se o Firefox não expuser o elemento, registrar bloqueio e alternativa por CDP; não substituir a evidência de AT-SPI por um resultado CDP.

## Gate R1 — RAM + Playwright

O ensaio `scripts/bench_playwright_ram.py` abre um perfil isolado do Chromium/Playwright, aplica bloqueio de imagens, mídia e fontes, desativa Service Workers, limita a duas abas por interface controlada (com fechamento defensivo de popups extras), registra memória disponível e PSS dos processos Chromium do perfil.

```bash
cd ~/adam-core
python3 -m venv .venv
source .venv/bin/activate
python -m pip install playwright
python -m playwright install chromium
mkdir -p artifacts/week1
python3 scripts/preflight.py --json > artifacts/week1/preflight.json
python3 scripts/bench_playwright_ram.py --seconds 120 --headed --out artifacts/week1/browser_ram.jsonl
htop
```

Tire uma captura de tela do `htop` durante o teste, mostrando RAM e processos. Guarde a captura como `artifacts/week1/htop.png`. Os dados primários devem ser os logs JSONL, não apenas uma foto.

**Teste mais realista:** repetir com duas páginas públicas e consentidas usando `--url https://example.com` (ou outra URL de teste aprovada). Não usar páginas pessoais, privadas ou logadas. Interceptar mídia pode quebrar sites que dependem de imagens ou vídeos; em produção a política será adaptada por tarefa.

**Limites iniciais (hipóteses):** máximo de 2 abas, PSS do Chromium até 1.280 MiB e `MemAvailable` mínimo de 1.536 MiB. O teste não reserva memória para SLM e STT ainda não implementados; logo não pode provar o orçamento final de 6,95 GiB. Para o benchmark, falha é `fail`, falta de medição confiável é `inconclusive` e as duas impedem aprovação.

**Importante:** um handler de evento que fecha popups extras não é garantia de limite atômico contra aplicativos maliciosos. O ensaio comprova a política do nosso controlador, não segurança adversarial nem uso permanente máximo de RAM.

**Gate R1 aprovado somente quando:** teste repetível na máquina-alvo, duas abas estáveis, bloqueio de imagens demonstrado, PSS e MemAvailable registrados durante toda a janela do teste, sem OOM e dentro dos tetos; anexar screenshot htop e logs. Repetir em sessão normal com carga real para validar os limites.

## Gate C1 — Contratos

Ver `docs/CONTRATOS_EXECUCAO.md` e `contracts/*.schema.json`. O planejamento do executor está definido, mas sua implementação e validação de políticas dependerão da equipe humana da Semana 2.

## Política de evidências

- NÃO registrar chaves de API, conteúdo de abas privadas ou dados pessoais.
- Não fazer commit dos `artifacts/` gerados na máquina-alvo (ignorado no Git).
- Não chamar inspeção de porta D-Bus de automação real.
- Não chamar benchmark isolado de Playwright de homologação do Adam.
- Evidência coletada em CI, contêiner ou outra máquina é apenas técnica auxiliar, **não o Gate**.
