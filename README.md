# Fut Manager

<<<<<<< HEAD
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
=======
Plataforma desenvolvida para gestão de partidas esportivas, distribuição algorítmica de equipes, avaliação estatística de desempenho individual e garantia de integridade histórica de dados.

Projetada com foco em padrões modernos de engenharia de software, modelagem relacional estrita, controle transacional e testes automatizados.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Destaques de Engenharia](#destaques-de-engenharia)
- [Arquitetura do Repositório](#arquitetura-do-repositório)
- [Modelo de Dados](#modelo-de-dados)
- [Stack Tecnológica](#stack-tecnológica)
- [Guia Rápido de Execução](#guia-rápido-de-execução)
- [Testes e Qualidade de Código](#testes-e-qualidade-de-código)
- [Próximos Passos](#próximos-passos)

---

## Visão Geral

O **Fut Manager** soluciona problemas clássicos de organização esportiva: balanceamento de times baseado em posições críticas (goleiros e atletas de linha), rastreabilidade de partidas e avaliação contínua de jogadores por meio de médias aritméticas recalculadas dinamicamente.

O projeto foi construído priorizando robustez arquitetural, separação de responsabilidades e garantia de consistência de dados em nível de banco relacional e aplicação.

---

## Destaques de Engenharia

- **Controle Transacional Robusto (ACID)**: Todas as operações de escrita que envolvem múltiplos registros (como criação de times com vínculo de jogadores ou registro de confrontos e gols) utilizam transações atômicas com `SessionLocal.begin()`, garantindo rollback automático em caso de falha.
- **Integridade Referencial e Proteção de Histórico**: Políticas estritas de integridade impedem a exclusão acidental de atletas vinculados a partidas ou equipes passadas, evitando registros órfãos sem recorrer a deleções em cascata destrutivas.
- **Algoritmo de Balanceamento de Equipes**: Sorteio que valida regras de negócio essenciais (obrigatoriedade e alocação equitativa de goleiros) e distribui os demais jogadores com diferença de no máximo um atleta por equipe.
- **Agregação e Normalização Dinâmica**: O rating dos atletas é calculado dinamicamente no banco via subqueries e agregação (`func.avg`), assegurando precisão estatística sem redundância de estado.
- **Auditoria de Schema em Runtime (`check_db.py`)**: Módulo de diagnóstico que inspeciona conexões, tipos de colunas, nulabilidade, constraints e chaves estrangeiras em modo somente leitura antes de operações de I/O.
- **Testes com Banco em Memória**: Suíte de testes unitários executada com SQLite em memória, garantindo isolamento completo, rapidez na execução e independência de serviços externos para pipelines de CI/CD.

---

## Arquitetura do Repositório

O projeto adota uma organização monorepo modular, desacoplando o núcleo de regras de negócio da camada de apresentação:

```text
fut-manager/
├── backend/
│   ├── tests/                # Testes unitários cobrindo regras de negócio, banco e CLI
│   ├── check_db.py           # Ferramenta de inspeção e auditoria de schema
│   ├── db.py                 # Configuração do engine, pooling e session factory
│   ├── futebol.py            # Camada de serviços, algoritmos e regras de domínio
│   ├── menu.py               # Interface de interação via linha de comando
│   ├── models.py             # Mapeamento relacional (ORM declarativo do SQLAlchemy 2.0)
│   ├── requirements.txt      # Gerenciamento de dependências
│   └── .env.example          # Modelo seguro de variáveis de ambiente
├── frontend/                 # Camada de apresentação do usuário (em estruturação)
├── .gitignore
└── README.md
```

---

## Modelo de Dados

O banco relacional normalizado é composto por 8 entidades mapeadas via SQLAlchemy 2.0:

- **users**: Cadastro do atleta, nota média (`rating`), posição atual e histórico da posição anterior (`last_position_id`).
- **positions & roles**: Catálogos normalizados de posições em campo e papéis táticos.
- **teams & team_players**: Estrutura N:N entre equipes e atletas participantes.
- **match_history & match_teams**: Registro de confrontos, timestamps de partidas e contagem de gols por equipe.
- **player_match_ratings**: Registro granular de avaliações individuais por partida.

---

## Stack Tecnológica

- **Linguagem**: Python 3.10+
- **ORM**: SQLAlchemy 2.0 (mapeamento declarativo com tipagem estrita)
- **Banco de Dados Principal**: MySQL 8.x / MariaDB
- **Banco de Dados para Testes**: SQLite (em memória)
- **Driver de Conexão**: PyMySQL com suporte a autenticação RSA
- **Framework de Testes**: Python `unittest` com mocks e injeção de dependência

---

## Guia Rápido de Execução

### Pré-requisitos
- Python 3.10 ou superior instalado
- Instância MySQL com o banco `fut_manager` criado

### 1. Clonar e Instalar Dependências

```bash
cd backend
python -m venv .venv

# No Windows:
.\.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
>>>>>>> 56693bbf554fe74e91e8134a3d659f8d94e56957
```
*(ou `cp .env.example .env` no Linux/macOS)*

<<<<<<< HEAD
Abra o arquivo `.env` e preencha com as credenciais do seu banco MySQL:

=======
### 2. Configurar Variáveis de Ambiente

Crie o arquivo `.env` dentro de `backend/` com base no exemplo:

>>>>>>> 56693bbf554fe74e91e8134a3d659f8d94e56957
```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fut_manager
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

<<<<<<< HEAD
> **Dica**: Se a senha contiver caracteres especiais (`#`, `@`, espaços), envolva-a entre aspas (ex: `DB_PASSWORD="p@ss#word"`).

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
=======
### 3. Validar Schema e Executar

```bash
# Validar integridade do banco:
python check_db.py

# Iniciar interface interativa:
python menu.py
```

---

## Testes e Qualidade de Código

A suíte cobre cenários de validação de dados, integridade referencial, balanceamento de sorteio e tratamento de concorrência/exceções.

Para executar os testes:

```bash
python -m unittest discover -s backend/tests -v
>>>>>>> 56693bbf554fe74e91e8134a3d659f8d94e56957
```

---

<<<<<<< HEAD
## Próximos Passos (Frontend)

O diretório `frontend/` está reservado para a implementação da interface gráfica (Web/Mobile), que consumirá as regras de negócio e dados do `backend`.
=======
## Próximos Passos

- Implementação de API RESTful para comunicação com clientes externos.
- Desenvolvimento da interface frontend (SPA/Mobile) dentro do diretório `frontend/`.
- Configuração de pipeline de CI/CD (GitHub Actions) com execução automatizada da suíte de testes.
>>>>>>> 56693bbf554fe74e91e8134a3d659f8d94e56957
