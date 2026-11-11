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

**Spike AT-SPI dinâmico, executado por engenheiro humano:**

1. Com Firefox **nativo** aberto, iniciar a fixture local sem contas privadas:
   ```bash
   cd ~/adam-core/tests/fixtures
   python3 -m http.server 8765 --bind 127.0.0.1
   ```
   Em outra janela abrir `http://127.0.0.1:8765/atspi_dynamic.html` no Firefox.
2. Iniciar Accerciser, escolher o processo Firefox e localizar o documento. Observar três fases: **Carregando**, **Pronto** (botão nasce após ~1,2s) e **Processando/Concluído**.
3. Fazer amostragens AT-SPI separadas por **250ms**, aguardando, no máximo, **15s** até que o alvo exista com **role, nome acessível, estado e ação** esperados. Exigir **três observações consecutivas equivalentes**, abrangendo pelo menos **500ms**, antes da primeira ativação.
4. Invocar a ação disponível **via AT-SPI/Accerciser**, nunca por coordenadas. Anotar instante e evidência da chamada. Após a chamada, a página remove o botão por ~700ms, atualiza `role=status` e cria **novo nó** com o mesmo nome acessível.
5. Invalidar imediatamente a referência antiga quando o nó desaparecer; redescobrir o alvo por características semânticas. Novamente exigir três observações estáveis. Comparar o **estado observado** com a pós-condição, não com o retorno do método `doAction`.
6. Repetir dez ativações em horários variados; incluir uma amostragem imediatamente após a navegação e outra na substituição do botão. Registrar falso negativo, referência stale, timeout e atraso até estabilidade; **nenhum retry de ativação** antes de reconciliar o estado.
7. Fazer teste negativo: página carregada sem target no intervalo -> **timeout explícito**, sem clique alternativo silencioso. Reiniciar Firefox e repetir o procedimento. Alterações de Firefox/AT-SPI que impeçam acesso devem constar como **bloqueio**, não como resultado aprovado.
8. Inspecionar D-Bus de acessibilidade e disponibilidade de portal. O engenheiro humano deverá realizar separadamente uma interação de entrada pelo **RemoteDesktop/libei autorizado**; recusa de permissão deve produzir erro seguro.
9. Registrar `XDG_SESSION_TYPE`, GNOME, Firefox, Accerciser, capturas da árvore e da fase inicial/intermediária/final, carimbo de tempo de cada observação, eventos e identificação do responsável humano.

**Não presumir** que o Firefox sempre usa carregamento lazy: o teste deve provar se a árvore está pronta ou não em cada versão e, sobretudo, que o adaptador não trata nós ausentes como falha definitiva prematura.

**Gate W1 aprovado somente quando:** há evidência de dez ciclos AT-SPI de identificação/ação/reconciliação na fixture dinâmica **e** demonstração de entrada Wayland autorizada. A inspeção estática, CDP ou uma única ação no Accerciser não substituem esse requisito.

**Autoria humana:** a equipe de IA não escreveu nem validou o adaptador AT-SPI. A fixture HTML e este procedimento não constituem implementação desse adaptador.

## Gate R1 — RAM + Playwright (30 minutos, obrigatório)

O `scripts/bench_playwright_ram.py` executa **no mínimo 1800 segundos** em ciclos de criar aba, navegar por DOM sintético leve/pesado, aguardar readiness, inserir/remover nós, extrair dados, **fechar a aba**, pausar e repetir. Uma rotina paralela amostra processos Chromium/Playwright, PSS/RSS e `MemAvailable` a cada ~500ms; JSONL gravado progressivamente. Perfil isolado, no máximo duas abas, bloqueio de imagem, mídia e fonte, com Service Workers desligados. A página de teste é servida apenas em localhost, sem serviços externos.

```bash
cd ~/adam-core
git pull --ff-only
python3 -m venv .venv
source .venv/bin/activate
python -m pip install playwright
python -m playwright install chromium
sudo apt install htop
mkdir -p artifacts/week1
python3 scripts/preflight.py --json > artifacts/week1/preflight.json
python3 scripts/bench_playwright_ram.py \
  --seconds 1800 --headed --idle-s 1.5 \
  --out artifacts/week1/browser_ram.jsonl
```

Durante os 30 minutos, deixar `htop` aberto numa sessão gráfica visível e produzir **capturas no início, meio e fim**, com processos Chromium e RAM. Os JSONL são a fonte primária. A saída `browser_ram.summary.json` contém status e limites.

**Pré-ensaio:** `--seconds 60` apenas para testar instrumentação; sai como `inconclusive` mesmo que nenhum limite seja ultrapassado. Este modo não aprova o gate.

**Teto inicial:** PSS Chromium <= 1280 MiB, `MemAvailable` >= 1536 MiB, <= 2 abas; crescimento residual do PSS pós-fechamento <= 128 MiB (mediana das primeiras cinco contra últimas cinco observações pós-fechamento). Falta de amostras ou de ciclos suficientes gera `inconclusive`. Erros de navegação, aumento além dos tetos e criação de abas inesperadas geram `fail`. **Reinício/OOM deve ser documentado como falha; não aceitar JSONL interrompido como passe.**

**Limitação importante:** 30 minutos e um DOM sintético não comprovam a ausência de vazamentos na 15ª tarefa real, nem o orçamento global de 6,95 GiB, pois STT/SLM ainda não estão presentes. Na fase de integração, repetir com cargas concorrentes e páginas representativas. `htop` costuma exibir RSS dos processos, que **não deve ser somado diretamente** como estimativa de memória única (páginas compartilhadas); utilizar PSS para teto do navegador.

**Gate R1 aprovado somente quando:** teste completo realizado no notebook de 8 GB com JSONL íntegro, resumo `pass`, capturas htop, verificação de processos que permaneceram após o encerramento e anotação de eventuais intervenções.
## Gate C1 — Contratos

Ver `docs/CONTRATOS_EXECUCAO.md` e `contracts/*.schema.json`. O planejamento do executor está definido, mas sua implementação e validação de políticas dependerão da equipe humana da Semana 2.

## Política de evidências

- NÃO registrar chaves de API, conteúdo de abas privadas ou dados pessoais.
- Não fazer commit dos `artifacts/` gerados na máquina-alvo (ignorado no Git).
- Não chamar inspeção de porta D-Bus de automação real.
- Não chamar benchmark isolado de Playwright de homologação do Adam.
- Evidência coletada em CI, contêiner ou outra máquina é apenas técnica auxiliar, **não o Gate**.
