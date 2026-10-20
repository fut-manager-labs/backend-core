# Fut Manager

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
```

### 2. Configurar Variáveis de Ambiente

Crie o arquivo `.env` dentro de `backend/` com base no exemplo:

```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fut_manager
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

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
```

---

## Próximos Passos

- Implementação de API RESTful para comunicação com clientes externos.
- Desenvolvimento da interface frontend (SPA/Mobile) dentro do diretório `frontend/`.
- Configuração de pipeline de CI/CD (GitHub Actions) com execução automatizada da suíte de testes.
