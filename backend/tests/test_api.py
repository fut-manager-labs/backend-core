import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import futebol
from db import Base
from main import app
from models import Position, User, Role, PlayerMatchRating, Team, MatchHistory, MatchTeam, TeamPlayer


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False},
                                    poolclass=StaticPool)

        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions.begin() as session:
            session.add_all([Position(id=1, position_title='Goleiro'),
                             Position(id=6, position_title='Linha')])
        patcher = patch.object(futebol, 'SessionLocal', self.sessions)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.engine.dispose)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_cadastra_e_lista_com_persistencia(self):
        response = self.client.post('/atletas', json={
            'nome': '  Ana  ', 'posicao_id': 1, 'rating_inicial': 8.5})
        self.assertEqual(response.status_code, 201)
        atleta = response.json()
        self.assertEqual(atleta['nome'], 'ANA')
        self.assertEqual(atleta['posicao'], 'Goleiro')
        self.assertEqual(atleta['rating'], 8.5)
        self.assertEqual(atleta['rating_inicial'], 8.5)
        self.assertIsNotNone(atleta['criado_em'])
        self.assertEqual(self.client.get('/atletas').json(), [atleta])
        with self.sessions() as session:
            self.assertEqual(session.get(User, atleta['id']).username, 'ANA')

    def test_posicao_zero_salva_linha_e_rating_zero(self):
        response = self.client.post('/atletas', json={
            'nome': 'Bia', 'posicao_id': 0, 'rating_inicial': 0})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['posicao_id'], 6)
        self.assertEqual(response.json()['rating'], 0)

    def test_rejeita_entrada_invalida_sem_gravar(self):
        valido = dict(nome='Ana', posicao_id=1, rating_inicial=8)
        casos = [{'nome': '   '}, {'nome': 'a' * 101}, {'posicao_id': -1},
                 {'posicao_id': 999}, {'posicao_id': 1.5}, {'rating_inicial': -1},
                 {'rating_inicial': 11}, {'rating_inicial': 'NaN'},
                 {'rating_inicial': 'Infinity'}, {'rating_inicial': 'abc'},
                 {'rating': 9}, {'role_id': 1}]
        for alteracao in casos:
            with self.subTest(alteracao=alteracao):
                response = self.client.post('/atletas', json=valido | alteracao)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post('/atletas', json={}).status_code, 422)
        self.assertEqual(self.client.get('/atletas').json(), [])

    def test_legado_sem_posicao_ou_nota_e_arredondamento(self):
        with self.sessions.begin() as session:
            session.add_all([User(username='Legado'),
                             User(username='Avaliado', rating=8.54321)])
        response = self.client.get('/atletas')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()[0]['rating'])
        self.assertIsNone(response.json()[0]['posicao_id'])
        self.assertEqual(response.json()[1]['rating'], 8.5)
        with self.sessions() as session:
            nota = session.scalar(select(User.rating).where(User.username == 'Avaliado'))
            self.assertAlmostEqual(float(nota), 8.54321)

    def test_falha_gravacao_desfaz_e_nao_expoe_credenciais(self):
        original_flush = Session.flush

        def falhar(session, *args, **kwargs):
            if session.new:
                raise OperationalError(None, None, Exception('senha-secreta'))
            return original_flush(session, *args, **kwargs)

        with patch.object(Session, 'flush', falhar):
            response = self.client.post('/atletas', json={
                'nome': 'Ana', 'posicao_id': 1, 'rating_inicial': 8})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('senha-secreta', response.text)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(User)), 0)

    def test_falha_listagem_retorna_erro_generico(self):
        with patch.object(futebol, 'detalhes_atletas', side_effect=OperationalError(
                None, None, Exception('senha-secreta'))):
            response = self.client.get('/atletas')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('senha-secreta', response.text)

    def test_documentacao_inclui_contratos(self):
        schema = self.client.get('/openapi.json').json()
        self.assertIn('get', schema['paths']['/atletas'])
        self.assertIn('post', schema['paths']['/atletas'])
        self.assertIn('201', schema['paths']['/atletas']['post']['responses'])

    def criar_atleta(self, nome='Ana', posicao=6, nota=8):
        response = self.client.post('/atletas', json=dict(
            nome=nome, posicao_id=posicao, rating_inicial=nota))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['id']

    def preparar_times(self):
        ids = [self.criar_atleta(str(i), 1 if i < 2 else 6, 5 + i) for i in range(4)]
        response = self.client.post('/times/sorteio', json={
            'atleta_ids': ids, 'nomes': ['Azul', 'Branco']})
        self.assertEqual(response.status_code, 201, response.text)
        return ids, response.json()['times']

    def preparar_partida(self):
        ids, times = self.preparar_times()
        response = self.client.post('/partidas', json=dict(
            time1_id=times[0]['id'], time2_id=times[1]['id'], gols1=2, gols2=1, data='2026-10-19'))
        self.assertEqual(response.status_code, 201, response.text)
        return ids, times, response.json()['id']

    def test_edicao_parcial_referencias_e_historico_posicao(self):
        with self.sessions.begin() as session:
            session.add(Role(id=1, role_name='Jogador'))
        self.assertEqual(len(self.client.get('/posicoes').json()), 2)
        self.assertEqual(self.client.get('/funcoes').json(), [dict(id=1, nome='Jogador')])
        ident = self.criar_atleta(posicao=1)
        response = self.client.patch(f'/atletas/{ident}', json={'nome': 'Bia'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['posicao_id'], 1)
        response = self.client.patch(f'/atletas/{ident}', json={'posicao_id': 0, 'funcao_id': 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['posicao_id'], 6)
        self.assertEqual(response.json()['posicao_anterior'], 'Goleiro')
        self.assertEqual(response.json()['funcao'], 'Jogador')
        response = self.client.patch(f'/atletas/{ident}', json={'funcao_id': None})
        self.assertIsNone(response.json()['funcao_id'])
        self.assertEqual(self.client.get(f'/atletas/{ident}').json()['nome'], 'Bia')
        for dados in ({}, {'nome': None}, {'posicao_id': None}, {'rating': 10}):
            self.assertEqual(self.client.patch(f'/atletas/{ident}', json=dados).status_code, 422)
        response = self.client.patch(f'/atletas/{ident}', json={'nome': 'Não salvar', 'funcao_id': 999})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f'/atletas/{ident}').json()['nome'], 'Bia')

    def test_exclusao_individual_e_multipla_com_vinculos(self):
        ids, _ = self.preparar_times()
        livre = self.criar_atleta('Livre')
        self.assertEqual(self.client.delete(f'/atletas/{ids[0]}').status_code, 409)
        response = self.client.post('/atletas/exclusao', json={'ids': [livre, ids[0], 999, livre]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['excluido'] for r in response.json()], [True, False, False])
        self.assertEqual(self.client.get(f'/atletas/{livre}').status_code, 404)
        self.assertEqual(self.client.get(f'/atletas/{ids[0]}').status_code, 200)
        outro = self.criar_atleta('Outro')
        response = self.client.delete(f'/atletas/{outro}')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')

    def test_sorteio_times_partida_e_avaliacao_com_media(self):
        ids, times, partida = self.preparar_partida()
        self.assertEqual(len(self.client.get('/times').json()), 2)
        self.assertEqual(self.client.get(f"/times/{times[0]['id']}").json()['id'], times[0]['id'])
        self.assertEqual(len(self.client.get(f'/partidas/{partida}/times').json()), 2)
        registro = self.client.get(f'/partidas/{partida}').json()
        self.assertEqual(registro['data'], '2026-10-19')
        self.assertEqual([t['gols'] for t in registro['times']], [2, 1])
        url = f'/partidas/{partida}/avaliacoes/{ids[0]}'
        response = self.client.put(url, json={'nota': 9})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['rating'], 7)
        response = self.client.put(url, json={'nota': 7})
        self.assertEqual(response.json()['rating'], 6)
        self.assertEqual(len(self.client.get('/partidas').json()), 1)
        notas = self.client.get(f'/partidas/{partida}').json()['avaliacoes']
        self.assertEqual(notas, [dict(atleta_id=ids[0], nome='0', nota=7)])
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(PlayerMatchRating)), 1)

    def test_consulta_partida_so_mostra_seus_times(self):
        _, times1, partida1 = self.preparar_partida()
        self.preparar_partida()
        self.assertEqual(len(self.client.get('/times').json()), 4)
        response = self.client.get(f'/partidas/{partida1}/times')
        self.assertEqual([t['id'] for t in response.json()], [t['id'] for t in times1])

    def test_registros_inexistentes_e_ids_invalidos(self):
        for rota in ('/atletas/999', '/times/999', '/partidas/999', '/partidas/999/times'):
            self.assertEqual(self.client.get(rota).status_code, 404)
        self.assertEqual(self.client.get('/atletas/0').status_code, 422)
        self.assertEqual(self.client.delete('/atletas/999').status_code, 404)
        self.assertEqual(self.client.patch('/atletas/999', json={'nome': 'A'}).status_code, 404)

    def test_pesquisa_por_id_retorna_dados_completos_apenas_do_selecionado(self):
        ident = self.criar_atleta('Ana', 1, 8.5)
        self.criar_atleta('Outra pessoa', 6, 5)
        response = self.client.get(f'/atletas/{ident}')
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertEqual(dados['id'], ident)
        self.assertEqual(dados['nome'], 'ANA')
        self.assertEqual(dados['posicao'], 'Goleiro')
        self.assertEqual(dados['rating'], 8.5)
        self.assertEqual(dados['rating_inicial'], 8.5)
        self.assertIn('funcao', dados)
        self.assertIn('posicao_anterior', dados)
        self.assertIn('criado_em', dados)

    def test_sorteio_invalido_nao_salva_times(self):
        ids = [self.criar_atleta('A'), self.criar_atleta('B')]
        for selecao in (ids, [ids[0], ids[0]], [ids[0], 999]):
            response = self.client.post('/times/sorteio', json={
                'atleta_ids': selecao, 'nomes': ['A', 'B']})
            self.assertIn(response.status_code, (404, 422))
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Team)), 0)

    def test_partida_invalida_e_atleta_fora_da_partida(self):
        ids, times = self.preparar_times()
        dados = dict(time1_id=times[0]['id'], time2_id=times[1]['id'],
                     gols1=0, gols2=0, data='2026-10-19')
        for alteracao in ({'time2_id': times[0]['id']}, {'gols1': -1},
                          {'data': '31/02/2026'}, {'gols1': 1.5}):
            self.assertEqual(self.client.post('/partidas', json=dados | alteracao).status_code, 422)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(MatchHistory)), 0)
        response = self.client.post('/partidas', json=dados)
        partida = response.json()['id']
        fora = self.criar_atleta('Fora')
        self.assertEqual(self.client.put(f'/partidas/{partida}/avaliacoes/{fora}', json={'nota': 8}).status_code, 422)
        self.assertEqual(self.client.put(f'/partidas/{partida}/avaliacoes/{ids[0]}', json={'nota': 11}).status_code, 422)

    def test_listagens_vazias(self):
        for rota in ('/times', '/partidas', '/funcoes'):
            response = self.client.get(rota)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

    def test_exclusao_time_sem_partida_preserva_atletas(self):
        ids, times = self.preparar_times()
        ident = times[0]['id']
        response = self.client.delete(f'/times/{ident}')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get(f'/times/{ident}').status_code, 404)
        self.assertEqual(len(self.client.get('/atletas').json()), len(ids))
        self.assertEqual(len(self.client.get('/times').json()), 1)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(TeamPlayer)
                             .where(TeamPlayer.team_id == ident)), 0)

    def test_exclusao_partida_recalcula_media_preserva_outros_dados(self):
        ids, times, partida = self.preparar_partida()
        segunda = self.client.post('/partidas', json=dict(time1_id=times[0]['id'],
                  time2_id=times[1]['id'], gols1=0, gols2=0, data='2026-10-20')).json()['id']
        self.client.put(f'/partidas/{partida}/avaliacoes/{ids[0]}', json={'nota': 9})
        self.client.put(f'/partidas/{segunda}/avaliacoes/{ids[0]}', json={'nota': 7})
        with self.sessions.begin() as session:
            session.get(User, ids[1]).initial_rating = None
        self.client.put(f'/partidas/{partida}/avaliacoes/{ids[1]}', json={'nota': 8})
        self.assertEqual(self.client.delete(f"/times/{times[0]['id']}").status_code, 409)
        self.assertEqual(self.client.delete(f'/partidas/{partida}').status_code, 204)
        self.assertEqual(self.client.get(f'/partidas/{partida}').status_code, 404)
        self.assertEqual(self.client.get(f"/atletas/{ids[0]}").json()['rating'], 6)
        self.assertIsNone(self.client.get(f"/atletas/{ids[1]}").json()['rating'])
        self.assertEqual(len(self.client.get('/times').json()), 2)
        self.assertEqual(len(self.client.get('/atletas').json()), 4)
        self.assertEqual(len(self.client.get('/partidas').json()), 1)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(MatchTeam)
                             .where(MatchTeam.match_id == partida)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(PlayerMatchRating)
                             .where(PlayerMatchRating.match_id == partida)), 0)
        self.assertEqual(self.client.delete(f"/times/{times[0]['id']}").status_code, 409)
        self.assertEqual(self.client.delete(f'/partidas/{segunda}').status_code, 204)
        self.assertEqual(self.client.get(f"/atletas/{ids[0]}").json()['rating'], 5)
        self.assertEqual(self.client.delete(f"/times/{times[0]['id']}").status_code, 204)

    def test_falha_recalculo_desfaz_exclusao_completa(self):
        ids, _, partida = self.preparar_partida()
        self.client.put(f'/partidas/{partida}/avaliacoes/{ids[0]}', json={'nota': 9})
        with patch.object(futebol, 'recalcular_rating', side_effect=OperationalError(None, None, Exception('falha'))):
            self.assertEqual(self.client.delete(f'/partidas/{partida}').status_code, 503)
        registro = self.client.get(f'/partidas/{partida}')
        self.assertEqual(registro.status_code, 200)
        self.assertEqual(len(registro.json()['times']), 2)
        self.assertEqual(len(registro.json()['avaliacoes']), 1)
        self.assertEqual(self.client.get(f"/atletas/{ids[0]}").json()['rating'], 7)

    def test_exclusao_time_partida_inexistentes(self):
        for rota in ('/times/999', '/partidas/999'):
            self.assertEqual(self.client.delete(rota).status_code, 404)


if __name__ == '__main__':
    unittest.main()
