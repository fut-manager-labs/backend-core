# backend-core
Core da aplicação de gerenciamento de jogos de futebol. O SQLAlchemy mapeia as oito tabelas existentes em `fut_manager`. O menu cadastra e lista atletas no banco e consulta as posições cadastradas. A opção `0` (sem posição selecionada) salva o atleta como Linha (`current_position_id=6`).

Para abrir o menu, execute `.\.venv\Scripts\python.exe menu.py` dentro de `backend-core`.

## Operações do menu

- Cadastro e listagem: nome, posição, função, posição anterior, data de cadastro e nota geral. O cadastro inicial não define função nem nota; use a edição para atribuir uma função e as avaliações de partidas para gerar a nota.
- Exclusão: seleciona por ID, pede confirmação e bloqueia atletas vinculados a times ou avaliações. Não apaga histórico em cascata.
- Edição de atleta: altera nome, posição e função consultando `positions` e `roles`. Ao mudar de posição, a anterior vai para `last_position_id`.
- Sorteio: permite informar IDs dos participantes ou selecionar todos. Exige dois goleiros, distribui todos os participantes em dois times com diferença máxima de um atleta e salva `teams` e `team_players` juntos. Cada sorteio cria novos times; times existentes não são sobrescritos.
- Consulta de times: mostra os IDs e os atletas de cada time.
- Registro de partida: seleciona dois times diferentes, placar e data no formato `DD/MM/AAAA`. O campo TIMESTAMP existente recebe a data, que é mostrada também no menu. Salva `match_history` e `match_teams` juntos. Bloqueia times vazios e participantes presentes nos dois times.
- Avaliação: aceita notas finitas de 0 a 10 apenas para participantes da partida e permite avaliar outros jogadores sem selecionar a partida novamente. Uma nova avaliação para o mesmo atleta e partida corrige a nota existente. `users.rating` é recalculado como média das notas por partida; não é preenchido manualmente. As notas são exibidas com uma casa decimal, preservando a precisão armazenada.
- Histórico: consulta partidas, placares e avaliações.
- Posições e funções: consulta os dados existentes; o menu não cria nem remove essas referências.

As gravações usam transações; uma falha desfaz a operação. O programa não cria nem altera tabelas. Times salvos preservam sua composição, sem edição de membros pelo menu.

Para testar o fluxo: cadastre atletas, sorteie dois times (anote os IDs), registre uma partida entre esses times, avalie um participante e consulte a listagem e o histórico. Reinicie o menu para conferir a persistência. Esses passos gravam dados no banco configurado.

## Instalação (PowerShell)

Execute dentro de `backend-core`, com Python 3.10 ou superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha `DB_USER` e `DB_PASSWORD` no `.env` com suas credenciais locais. Os padrões são `DB_HOST=localhost`, `DB_PORT=3306` e `DB_NAME=fut_manager`. Variáveis do ambiente prevalecem sobre o arquivo. Senha vazia é aceita se configurada explicitamente; coloque senhas com `#`, espaços ou outros caracteres especiais entre aspas no `.env`.

O `.env` é ignorado pelo Git. A URL usa `URL.create`, sem concatenar ou escapar manualmente a senha. Não registre a URL completa. Importar `db` ou `models` não abre conexão; as credenciais são necessárias ao acessar o banco. O engine usa `utf8mb4`, `pool_pre_ping` e logs SQL desativados.

## Conferir conexão e estrutura

```powershell
.\.venv\Scripts\python.exe check_db.py
```

O comando executa `SELECT 1`, confirma `SELECT DATABASE()` e inspeciona as oito tabelas: colunas, tipos, nulabilidade, padrões, autoincremento, chaves primárias e estrangeiras. Tabelas extras são permitidas; colunas extras nas tabelas mapeadas são relatadas. Retorna código `0` no sucesso ou `1` para falhas e divergências, sem mostrar a senha.

Não executa `create_all`, migrações nem gravações. Se as tabelas estiverem em `meu_projeto` devido ao segundo `USE` do script original, a verificação relatará tabelas ausentes em `fut_manager`; nenhuma correção é automática.

## Consulta e transação

Exemplos para executar a partir de `backend-core`:

```python
from sqlalchemy import select
from db import SessionLocal
from models import User

with SessionLocal() as session:
    users = session.scalars(select(User).order_by(User.id)).all()
    for user in users:
        print(user.username, user.current_position, user.last_position)
```

O exemplo seguinte **insere um usuário** quando executado:

```python
from db import SessionLocal
from models import User

with SessionLocal.begin() as session:
    session.add(User(username="Gabriel"))
```

`SessionLocal.begin()` confirma no sucesso, desfaz em caso de exceção e fecha a sessão automaticamente. Os relacionamentos não possuem exclusão em cascata. `created_at` e `goals` usam os padrões do servidor; `DOUBLE` e campos opcionais seguem o SQL fornecido.

## Testes sem MySQL

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
