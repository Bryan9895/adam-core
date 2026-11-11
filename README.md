# Adam Core — Alpha 0.1

Assistente pessoal nativo para Ubuntu GNOME/Wayland. **Em construção.**

O repositório começa com o Plano Diretor aprovado e um diagnóstico reproduzível de pré-homologação. O Core, a máquina de estados e os adaptadores de SO ainda **não foram implementados**. Por exigência do projeto, essas partes dependem de implementação e depuração humanas.

## Documentos

- [Plano Diretor (rev. 1.1)](docs/PLANO_DIRETOR.md) — quatro emendas, arquitetura, seis semanas e critérios.
- [Matriz de Aceite](docs/ACEITE_ALPHA.md) — M1 a M4, todos ainda pendentes.

## Diagnóstico (não é protótipo funcional)

Em Python 3.10+:

    python3 scripts/preflight.py --json
    python3 -m unittest discover -s tests -v

O script é somente leitura: não abre programas, não toca mouse/teclado, não envia dados à internet e não imprime chaves. Executar no **Ubuntu GNOME/Wayland do usuário** para registrar informações de hardware/sessão.

## Requisitos congelados

- RAM de 8 GB: orçamento, contenção de abas, TTS exclusivamente na nuvem.
- Roteamento local por regras e SLM quantizado, com Dual-LLM e políticas contra exfiltração.
- Preferência: API/CLI → CDP/WebDriver → AT-SPI/D-Bus/portais → visão.
- Memória operacional junto ao Core na Fase 1.
- Autoria humana do Core, máquina de estados e integrações Wayland/AT-SPI.
- TTFA de comando determinístico < 1,5 s desde soltar PTT até primeira ação real.
- Seis semanas apenas para Alpha 0.1; Beta/v1.0 sem cronograma.

## Situação

✅ Documento e matriz criados. Diagnóstico e testes de preflight disponíveis.  
⏳ Core, voz, SLM, navegador, controle Wayland e segurança operacional por implementar.  
⏳ Homologação oficial em máquina GNOME/Wayland não realizada.

**Não confundir testes do preflight com as quatro metas de aceite do produto.**
