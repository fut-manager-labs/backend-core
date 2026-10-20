# Fut Manager

Sistema completo para organização e gestão de jogos de futebol semanais, abrangendo controle de atletas, sorteio equilibrado de times, registro de partidas, histórico de confrontos e avaliações de desempenho individual.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Funcionalidades e Regras de Negócio](#funcionalidades-e-regras-de-negócio)
- [Modelo de Dados](#modelo-de-dados)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Configuração](#instalação-e-configuração)
  - [1. Configurando o Backend](#1-configurando-o-backend)
  - [2. Configurando as Variáveis de Ambiente](#2-configurando-as-variáveis-de-ambiente)
  - [3. Verificação do Banco de Dados](#3-verificação-do-banco-de-dados)
- [Como Executar](#como-executar)
  - [Menu Interativo (CLI)](#menu-interativo-cli)
- [Segurança e Boas Práticas](#segurança-e-boas-práticas)
- [Testes Automatizados](#testes-automatizados)
- [Uso Programático (Exemplos de Código)](#uso-programático-exemplos-de-código)
- [Próximos Passos (Frontend)](#próximos-passos-frontend)

---

## Visão Geral

O **Fut Manager** foi idealizado para resolver os desafios comuns na gestão de partidas de futebol amador:
- Sorteio justo de equipes garantindo distribuição equilibrada de goleiros e jogadores de linha.
- Manutenção do histórico de pontuação e atuações de cada participante.
- Cálculo estatístico automatizado da nota média de cada atleta com base nas partidas disputadas.
- Preservação da integridade histórica dos dados (bloqueio de exclusões acidentais que corrompam o histórico).

---

## Estrutura do Projeto

O repositório é organizado no formato monorepo modular:

```text
fut-manager/
├── backend/                  # Núcleo da aplicação (Python / SQLAlchemy)
│   ├── tests/                # Suíte de testes unitários automatizados
│   │   ├── test_database.py  # Testes de configuração e mapeamento ORM
│   │   ├── test_futebol.py   # Testes das regras de negócio de partidas/times
│   │   └── test_menu.py      # Testes do fluxo de interface de linha de comando
│   ├── .env.example          # Modelo de configuração de variáveis de ambiente
│   ├── check_db.py           # Utilitário de inspeção e auditoria de schema do banco
│   ├── db.py                 # Conexão, engine e SessionLocal do SQLAlchemy
│   ├── futebol.py            # Regras de negócio e operações transacionais
│   ├── menu.py               # Menu interativo em terminal (CLI)
│   ├── models.py             # Mapeamento declarativo das 8 tabelas do banco
│   └── requirements.txt      # Dependências Python do backend
├── frontend/                 # Interface web / cliente do usuário (em estruturação)
│   └── .gitkeep
├── .gitignore
└── README.md                 # Documentação principal do projeto
```

---

## Funcionalidades e Regras de Negócio

### 1. Gestão de Atletas
- **Cadastro**: Registro por nome e posição. Se nenhuma posição for informada (opção `0`), o jogador é cadastrado automaticamente como **Linha** (`current_position_id = 6`).
- **Edição**: Atualização de nome, posição e função tática (`roles`). Ao alterar a posição de um jogador, a anterior é preservada no histórico (`last_position_id`).
- **Exclusão Segura**: Um atleta só pode ser excluído se não tiver vínculo com nenhum time ou avaliação de partida registrada, evitando órfãos no banco de dados.

### 2. Sorteio Balanceado de Times
- **Distribuição de Goleiros**: Exige a presença de pelo menos dois goleiros selecionados, alocando um para cada equipe.
- **Equilíbrio Numérico**: Distribui aleatoriamente os jogadores restantes de modo que a diferença entre as equipes seja no máximo de 1 atleta.
- **Persistência Imutável**: Cada sorteio gera novos registros nas tabelas `teams` e `team_players`.

### 3. Registro de Partidas e Placares
- **Validação de Times**: Impede o registro de partida entre o mesmo time ou com times vazios.
- **Validação de Integridade**: Bloqueia partidas se o mesmo atleta constar em ambas as equipes.
- **Dados Registrados**: Data da partida (`match_date`) e gols de cada equipe salvos em transação atômica.

### 4. Avaliações de Desempenho e Rating
- **Critérios**: Aceita notas de `0.0` a `10.0` exclusivamente para jogadores que participaram da partida selecionada.
- **Atualização de Avaliação**: Avaliar novamente o mesmo atleta na mesma partida atualiza a nota existente.
- **Recálculo do Rating**: O atributo `users.rating` é recalculado automaticamente após cada avaliação como a média aritmética das notas obtidas pelo jogador em todas as suas partidas.

### 5. Auditoria de Banco de Dados (`check_db.py`)
- Script de diagnóstico que inspeciona o banco MySQL configurado em modo somente leitura.
- Valida tabelas, colunas, tipos de dados, nulabilidade, valores padrão e chaves estrangeiras sem efetuar nenhuma alteração ou gravação.

---

## Modelo de Dados

O banco de dados relacional é composto por 8 tabelas mapeadas via SQLAlchemy:

| Tabela | Descrição |
|---|---|
| `positions` | Catálogo de posições dos jogadores (ex: Goleiro, Zagueiro, Linha). |
| `roles` | Funções táticas / papéis dos membros. |
| `users` | Dados dos atletas (nome, nota geral, posição atual e anterior, função). |
| `teams` | Equipes geradas para os jogos. |
| `team_players` | Associação N:N entre equipes e atletas participantes. |
| `match_history` | Cabeçalho das partidas disputadas com timestamp. |
| `match_teams` | Relação dos times envolvidos na partida e quantidade de gols marcados. |
| `player_match_ratings` | Notas individuais atribuídas aos atletas em cada partida. |

---

## Tecnologias Utilizadas

- **Linguagem**: [Python](https://www.python.org/) (versão 3.10 ou superior)
- **ORM / Banco de Dados**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Driver MySQL**: [PyMySQL](https://github.com/PyMySQL/PyMySQL) (com suporte a criptografia RSA)
- **Configuração**: [python-dotenv](https://github.com/theskumar/python-dotenv)
- **Testes**: Módulo padrão `unittest` com execução em memória via **SQLite**

---

## Pré-requisitos

- **Python 3.10+** instalado no sistema.
- Servidor **MySQL 8.x** ou **MariaDB** ativo (com a base de dados `fut_manager` criada).

---

## Instalação e Configuração

### 1. Configurando o Backend

Navegue até a pasta `backend`, crie e ative o ambiente virtual:

#### No Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### No Linux / macOS (Bash):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 2. Configurando as Variáveis de Ambiente

No diretório `backend`, crie um arquivo `.env` a partir do modelo `.env.example`:

```powershell
Copy-Item .env.example .env
```
*(ou `cp .env.example .env` no Linux/macOS)*

Abra o arquivo `.env` e preencha com as credenciais do seu banco MySQL local:

```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fut_manager
DB_USER=seu_usuario_aqui
DB_PASSWORD=sua_senha_aqui
```

> **Aviso de Segurança**: Nunca comite o arquivo `.env` com senhas reais no repositório. Certifique-se de que ele esteja devidamente listado no seu `.gitignore`. Caso a sua senha contenha caracteres especiais (como `#`, `@` ou espaços), mantenha o valor entre aspas (ex: `DB_PASSWORD="<sua_senha_com_aspas>"`).

---

### 3. Verificação do Banco de Dados

Antes de iniciar a aplicação, você pode validar se a conexão e o schema das tabelas estão corretos executando o script de auditoria:

```powershell
python check_db.py
```

- Retorna código `0` caso o schema esteja em conformidade.
- Aponta eventuais colunas ausentes, divergências de tipo ou chaves estrangeiras pendentes.

---

## Como Executar

### Menu Interativo (CLI)

Com o ambiente virtual ativado e dentro do diretório `backend`, execute:

```powershell
python menu.py
```

Opções disponíveis no menu:
1. **Cadastrar atleta**: Inclusão de novos jogadores.
2. **Listar atletas**: Exibe atletas cadastrados, posição, função, nota média e data de cadastro.
3. **Excluir atleta**: Exclusão com confirmação e validação de dependências.
4. **Sortear e salvar times**: Sorteio balanceado com seleção de participantes e obrigatoriedade de goleiros.
5. **Editar atleta**: Atualização de nome, função e mudança de posição.
6. **Listar times**: Visualização das equipes criadas e seus membros.
7. **Registrar partida e placar**: Registro de confronto entre duas equipes, gols e data.
8. **Listar partidas e avaliações**: Consulta do histórico de jogos, placares e notas atribuídas.
9. **Avaliar atleta em partida**: Atribuição de nota (0 a 10) a atletas que jogaram determinada partida.
10. **Consultar posições e funções**: Listagem das referências cadastradas no sistema.
11. **Sair**: Encerra a aplicação.

---

## Segurança e Boas Práticas

- **Segregação de Credenciais**: O arquivo `.env` é de uso exclusivamente local e deve permanecer sempre ignorado pelo Git. O repositório disponibiliza apenas o `.env.example` sem nenhuma informação sensível.
- **Não Exposição de Senhas**: A aplicação monta a conexão com o banco utilizando métodos seguros do SQLAlchemy (`URL.create`), evitando concatenação ou vazamento de senhas em URLs.
- **Tratamento de Exceções**: Falhas de autenticação e logs de erro são tratados para não expor senhas em saídas de terminal ou mensagens de erro não tratadas.
- **Modo Somente Leitura na Auditoria**: O script `check_db.py` inspeciona o banco em modo estritamente consultivo, sem alterar esquemas ou persistir dados.

---

## Testes Automatizados

A suíte de testes unitários cobre regras de negócio, sorteio de equipes, avaliações, transações e validações de banco de dados. Os testes utilizam um banco SQLite em memória, dispensando a necessidade de uma instância MySQL ativa.

Para executar os testes:

```powershell
# A partir do diretório raiz do projeto:
python -m unittest discover -s backend/tests -v
```

Ou a partir do diretório `backend`:
```powershell
cd backend
python -m unittest discover -s tests -v
```

---

## Uso Programático (Exemplos de Código)

Você também pode utilizar os modelos e sessões do SQLAlchemy diretamente em scripts Python:

```python
from sqlalchemy import select
from db import SessionLocal
from models import User

# Consulta de atletas
with SessionLocal() as session:
    users = session.scalars(select(User).order_by(User.id)).all()
    for user in users:
        posicao = user.current_position.position_title if user.current_position else "Sem posição"
        print(f"{user.username} - Posição: {posicao} - Nota: {user.rating}")

# Inserção com controle transacional automático
with SessionLocal.begin() as session:
    novo_atleta = User(username="Gabriel", current_position_id=6)
    session.add(novo_atleta)
```

---

## Próximos Passos (Frontend)

O diretório `frontend/` está reservado para a implementação da interface gráfica (Web/Mobile), que consumirá as regras de negócio e dados do `backend`.
