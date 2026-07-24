# NanoSIP

Sistema de telefonia IP (PABX) baseado em Asterisk, desenvolvido para atender portarias de condomínios com uma solução de baixo custo, fácil de administrar e com licenciamento recorrente.

## Sobre o projeto

O NanoSIP nasceu da necessidade de oferecer uma alternativa acessível aos sistemas de interfonia/portaria tradicionais, unindo a robustez do Asterisk a uma interface web simples de gerenciamento, pensada para instaladores e integradores de pequeno e médio porte.

O sistema é distribuído em três formatos, conforme a necessidade do cliente:
- **Instalação padrão** — servidor Linux dedicado;
- **NanoSIP VM** — appliance virtual pronto para importar em ambientes já virtualizados (Proxmox, VirtualBox, VMware);
- **NanoSIP Raspberry Pi** — versão embarcada, voltada a instalações compactas e de baixo consumo energético.

## Funcionalidades

- Gerenciamento de ramais, filas e troncos SIP via interface web;
- Cadastro e administração de clientes/licenças;
- Recarregamento de configurações do Asterisk (dialplan, filas, SIP) sem necessidade de reiniciar o serviço;
- Monitoramento de informações do sistema e da rede;
- Sistema de licenciamento próprio, com controle de validade e tipo de instalação (padrão, VM ou embarcado).

## Arquitetura e tecnologias

- **Backend:** Python (Flask)
- **Telefonia:** Asterisk (SIP/VoIP)
- **Banco de dados:** SQLite, gerenciado via `database.py`
- **Autenticação:** módulo próprio (`auth.py`)
- **Automação:** scripts de recarga de configuração do Asterisk (`reload_sip.py`, `reload_queues.py`, `reload_extensions.py`)
- **Gerenciamento do sistema:** `system_manager.sh` / `system_info.py`

## Estrutura do projeto
```
nanosip/
├── app.py                     # Aplicação principal (Flask)
├── auth.py                    # Autenticação de usuários
├── cadastro.py                 # Cadastro de clientes/licenças
├── database.py                 # Camada de acesso a dados (SQLite)
├── get_network_info.py         # Coleta de informações de rede
├── reload_extensions.py        # Recarga de ramais no Asterisk
├── reload_queues.py            # Recarga de filas no Asterisk
├── reload_sip.py               # Recarga de configurações SIP
├── system_info.py              # Informações do sistema
├── system_manager.sh           # Script de gerenciamento do sistema
├── update_network_files.py     # Atualização de configurações de rede
├── blueprints/                 # Módulos da aplicação (Flask Blueprints)
├── config/                     # Arquivos de configuração
├── scripts/                    # Scripts auxiliares de instalação/manutenção
├── static/                     # Arquivos estáticos (CSS/JS/imagens)
└── templates/                  # Templates HTML da interface web
```
## Licenciamento

Projeto de uso comercial, com controle de licenciamento próprio. Distribuição e uso sujeitos a licença adquirida junto ao autor.

## Autor

**Guto Campos**
[github.com/gutosolar72](https://github.com/gutosolar72)
