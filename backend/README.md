# backend
Core da aplicação de gerenciamento de jogos de futebol. O SQLAlchemy mapeia as oito tabelas existentes em `fut_manager`. O menu cadastra e lista atletas no banco e consulta as posições cadastradas. A opção `0` (sem posição selecionada) salva o atleta como Linha (`current_position_id=6`).

Para abrir o menu, execute `.\.venv\Scripts\python.exe menu.py` dentro de `backend`.

## API FastAPI

No PowerShell:

```powershell
cd C:\Users\Gabriel\Desktop\projeto\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Abra `http://127.0.0.1:8000/docs`. Mantenha o servidor rodando para usar a API; `Ctrl+C` encerra. O modo `--reload` é para desenvolvimento local.

- `GET /`: resposta inicial da API.
- `GET /atletas`: lista os atletas por ID, com posição, função, posição anterior, rating geral, rating inicial e data de cadastro. Retorna `200` e uma lista (vazia quando não há atletas). Notas são exibidas com uma casa decimal, mantendo a precisão armazenada; dados antigos sem nota são retornados como `null`.
- `POST /atletas`: cadastra e retorna o atleta com status `201`. Usa a mesma operação de `futebol.py` que o menu. O nome é normalizado para maiúsculas. A posição `0` seleciona Linha (ID 6). A função fica sem definição; o rating geral começa com a nota inicial.

Exemplo de corpo do POST no Swagger, em **Try it out → Execute**:

```json
{
  "nome": "Gabriel",
  "posicao_id": 1,
  "rating_inicial": 8.5
}
```

O nome deve ter entre 1 e 100 caracteres úteis, a posição precisa existir e a nota deve ser finita de 0 a 10. Campos extras são rejeitados; o cliente não define diretamente o rating calculado. Dados inválidos retornam `422`; falhas no banco retornam `503`, sem detalhes de credenciais. Executar o POST no Swagger grava no banco configurado no `.env`.

Para instalar as dependências dos testes e executar a suíte (que usa bancos SQLite temporários):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

As operações do menu também estão disponíveis nas rotas abaixo:

| Método | Rota | Operação |
| --- | --- | --- |
| GET | `/atletas/{ident}` | Consultar um atleta |
| PATCH | `/atletas/{ident}` | Editar nome, posição e/ou função |
| DELETE | `/atletas/{ident}` | Excluir atleta livre de vínculos (204) |
| POST | `/atletas/exclusao` | Excluir vários atletas, com resultado por ID |
| GET | `/posicoes` | Consultar posições |
| GET | `/funcoes` | Consultar funções |
| POST | `/times/sorteio` | Sortear e salvar dois times equilibrados (201) |
| GET | `/times` | Listar todos os times e integrantes |
| GET | `/times/{ident}` | Consultar um time |
| DELETE | `/times/{ident}` | Excluir time sem partidas; preserva atletas |
| POST | `/partidas` | Registrar data e placar entre dois times (201) |
| GET | `/partidas` | Listar partidas, placares e avaliações |
| GET | `/partidas/{ident}` | Consultar uma partida |
| DELETE | `/partidas/{ident}` | Excluir partida, placares e avaliações; recalcular ratings |
| GET | `/partidas/{ident}/times` | Consultar somente os times e participantes dessa partida |
| PUT | `/partidas/{partida_id}/avaliacoes/{atleta_id}` | Criar ou corrigir uma avaliação e retornar o atleta com a média atualizada |

Exemplos de corpos JSON (substitua os IDs pelos registros retornados pela sua API):

```json
{"nome": "Gabriel", "posicao_id": 6, "funcao_id": 1}
```

O PATCH aceita qualquer subconjunto desses campos. Campos omitidos são preservados; `funcao_id: null` remove a função. Nome e posição não aceitam `null`. Não permite editar diretamente rating ou nota inicial.

```json
{"ids": [3, 5, 8]}
```

A exclusão múltipla processa cada ID uma vez e pode ter sucesso parcial, como no menu. O pedido é a confirmação da operação; o Swagger não pede confirmação adicional.

`DELETE /times/{ident}` remove o time e seus registros em `team_players`, preservando atletas. Se o time estiver ligado a qualquer partida, retorna `409`; exclua as partidas correspondentes primeiro.

`DELETE /partidas/{ident}` remove a partida, seus registros de `match_teams` e suas avaliações. Recalcula o rating dos atletas avaliados usando a nota inicial e as partidas restantes. Sem avaliações restantes, volta à nota inicial; sem nota inicial nem avaliações, fica `null`. Times, integrantes e atletas são preservados. A exclusão e os recálculos usam uma única transação. Ambas as rotas retornam `204` sem corpo no sucesso e `404` para ID inexistente.

```json
{"atleta_ids": [1, 2, 3, 4], "nomes": ["Azul", "Branco"]}
```

O sorteio exige os IDs explícitos dos participantes, sem duplicatas, incluindo pelo menos dois goleiros. Retorna os dois times com integrantes, totais, médias e diferença de ratings. Para atletas sem rating, a resposta informa quais receberam a referência temporária 5.0.

```json
{"time1_id": 1, "time2_id": 2, "gols1": 2, "gols2": 1, "data": "2026-10-19"}
```

Na API, use a data ISO `AAAA-MM-DD`; no menu, continua `DD/MM/AAAA`. O histórico da API exibe somente a data.

```json
{"nota": 8.5}
```

Use esse último corpo no PUT da avaliação, preenchendo os IDs da partida e do atleta nos parâmetros da rota. Repetir o PUT corrige a avaliação existente; não cria uma segunda nota. A resposta inclui o rating geral recalculado com a nota inicial.

Referências e registros inexistentes retornam `404` nas novas rotas. Exclusão de atleta vinculado retorna `409`; dados inválidos retornam `422`. O POST de cadastro mantém `422` para posição inexistente. Falhas de banco retornam `503` sem credenciais; na exclusão múltipla a falha fica no resultado individual. Todas as operações de gravação no Swagger afetam o banco configurado no `.env`.

## Operações do menu

A opção **11 — Pesquisar atleta por ID** consulta um atleta e mostra seus dados (nome, posição atual e anterior, função, nota geral, habilidade inicial e data de cadastro). `0` cancela. Um ID inexistente apresenta uma mensagem sem encerrar o programa. Na API, a mesma consulta é `GET /atletas/{ident}`; preencha o ID no Swagger em **Try it out**.

As opções **12 — Excluir time** e **13 — Excluir partida** mostram os registros, pedem um ID (`0` cancela) e solicitam confirmação. As regras são as mesmas das rotas DELETE descritas acima. **14 — Sair** é a última opção.

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

Execute dentro de `backend`, com Python 3.10 ou superior:

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

Exemplos para executar a partir de `backend`:

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
