# backend-core
Core da aplicação de gerenciamento de jogos de futebol. O SQLAlchemy mapeia as oito tabelas existentes em `fut_manager`. O menu cadastra e lista atletas no banco e consulta as posições cadastradas. A opção `0` (sem posição selecionada) salva o atleta como Linha (`current_position_id=6`).

Para abrir o menu, execute `.\.venv\Scripts\python.exe menu.py` dentro de `backend-core`.

## Operações do menu

- Cadastro: nome, posição e habilidade inicial obrigatória de 0 a 10. A nota inicial fica em `users.initial_rating`, e `users.rating` começa com o mesmo valor. A listagem mostra ambas. Use a edição para atribuir uma função.
- Exclusão: aceita um ID ou vários separados por vírgula (ex.: `3, 5, 8`); `0` cancela. Mostra os selecionados e pede uma única confirmação. IDs repetidos são processados uma vez e inexistentes são ignorados. Exclui individualmente os atletas livres e informa os bloqueados por vínculos com times ou avaliações; uma falha não desfaz exclusões anteriores já confirmadas. Não apaga histórico em cascata.
- Edição de atleta: altera nome, posição e função consultando `positions` e `roles`. Ao mudar de posição, a anterior vai para `last_position_id`.
- Sorteio: permite informar IDs dos participantes ou selecionar todos. Busca a menor diferença possível entre as somas dos ratings, usando os valores arredondados a uma casa decimal. Exige ao menos um goleiro em cada time e diferença máxima de um atleta; todos os participantes são incluídos, inclusive goleiros extras. Entre soluções ótimas há escolha aleatória, sem garantia de distribuição uniforme. Para atletas antigos sem rating, usa 5.0 apenas no cálculo e informa os nomes no resultado, sem alterar o cadastro. O menu mostra soma, média e diferença dos ratings no momento do sorteio. Salva `teams` e `team_players` juntos. Cada sorteio cria novos times; times existentes não são sobrescritos. Equilíbrio exato nem sempre é possível, e a soma dos ratings é apenas uma estimativa de força.
- Consulta de times: mostra os IDs e os atletas de cada time.
- Registro de partida: seleciona dois times diferentes, placar e data no formato `DD/MM/AAAA`. O campo TIMESTAMP existente recebe a data, que é mostrada também no menu. Salva `match_history` e `match_teams` juntos. Bloqueia times vazios e participantes presentes nos dois times.
- Avaliação: aceita notas finitas de 0 a 10 apenas para participantes da partida e permite avaliar outros jogadores sem selecionar a partida novamente. Uma nova avaliação para o mesmo atleta e partida corrige a nota existente. `users.rating = (initial_rating + soma das notas por partida) / (1 + número de partidas avaliadas)`. A nota inicial conta uma vez. Atletas antigos sem nota inicial continuam com a média apenas das partidas. As notas são exibidas com uma casa decimal, preservando a precisão armazenada. O sorteio usa o rating geral atual, incluindo as avaliações mais recentes.

Para atualizar bancos existentes, execute `.\.venv\Scripts\python.exe migrate_initial_rating.py` antes de abrir o menu. O script adiciona a coluna nullable `users.initial_rating` e preserva todos os valores existentes; não atribui notas iniciais a atletas antigos. Pode ser executado novamente sem recriar a coluna.
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
