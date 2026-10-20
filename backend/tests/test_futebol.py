import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError

import futebol
from db import Base
from models import (MatchHistory, MatchTeam, PlayerMatchRating, Position,
                    Role, Team, TeamPlayer, User)


class FutebolTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')

        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions.begin() as session:
            session.add_all([Position(id=1, position_title='Goleiro'),
                             Position(id=6, position_title='Linha'),
                             Role(id=1, role_name='Jogador')])
            session.flush()
            session.add_all([User(id=i, username=f'Atleta {i}',
                                  current_position_id=1 if i <= 3 else 6)
                             for i in range(1, 8)])
        patcher = patch.object(futebol, 'SessionLocal', self.sessions)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.engine.dispose)

    def times(self):
        return futebol.sortear_times(list(range(1, 8)), ['Azul', 'Branco'])

    def partida(self):
        times = self.times()
        return futebol.registrar_partida(times[0][0], times[1][0], 2, 1,
                                         datetime(2026, 10, 12, 20)), times

    def test_sorteio_salva_todos_inclusive_goleiro_extra(self):
        self.times()
        with self.sessions() as session:
            times = session.scalars(select(Team)).all()
            self.assertEqual(len(times), 2)
            ids = session.scalars(select(TeamPlayer.user_id)).all()
            self.assertEqual(sorted(ids), list(range(1, 8)))
            tamanhos = []
            for time in times:
                membros = session.scalars(select(User).join(TeamPlayer)
                          .where(TeamPlayer.team_id == time.id)).all()
                tamanhos.append(len(membros))
                self.assertTrue(any(a.current_position_id == 1 for a in membros))
            self.assertEqual(sorted(tamanhos), [3, 4])

    def test_sorteio_invalido_nao_grava_parcialmente(self):
        for ids in ([1, 4], [1, 2, 99], [1, 2, 2]):
            with self.assertRaises(ValueError):
                futebol.sortear_times(ids, ['A', 'B'])
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Team)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(TeamPlayer)), 0)

    def test_falha_ao_salvar_segundo_time_desfaz_primeiro(self):
        original_flush = Session.flush
        chamadas = 0

        def falhar_segundo_time(session, *args, **kwargs):
            nonlocal chamadas
            if any(isinstance(obj, Team) for obj in session.new):
                chamadas += 1
                if chamadas == 2:
                    raise OperationalError(None, None, Exception('falha simulada'))
            return original_flush(session, *args, **kwargs)

        with patch.object(Session, 'flush', falhar_segundo_time):
            with self.assertRaises(OperationalError):
                self.times()
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Team)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(TeamPlayer)), 0)

    def test_edicao_posicao_anterior_e_funcao(self):
        futebol.editar_atleta(1, 'Novo nome', 6, 1)
        futebol.editar_atleta(1, 'Outro nome', 6, None)
        with self.sessions() as session:
            atleta = session.get(User, 1)
            self.assertEqual(atleta.last_position_id, 1)
            self.assertEqual(atleta.current_position_id, 6)
            self.assertIsNone(atleta.role_id)
        with self.assertRaises(ValueError):
            futebol.editar_atleta(1, 'Inválido', 99, None)
        self.assertEqual(futebol.detalhes_atletas()[0]['nome'], 'Outro nome')

    def test_exclusao_livre_e_bloqueio_com_time(self):
        futebol.excluir_atleta(7)
        with self.sessions() as session:
            self.assertIsNone(session.get(User, 7))
        futebol.sortear_times([1, 2, 3, 4, 5, 6], ['A', 'B'])
        with self.assertRaises(ValueError):
            futebol.excluir_atleta(1)
        with self.sessions() as session:
            self.assertIsNotNone(session.get(User, 1))

    def test_partida_placar_e_consultas(self):
        times = self.times()
        ident = futebol.registrar_partida(times[0][0], times[1][0], 3, 2,
                                          datetime(2026, 10, 12, 20))
        partida = futebol.consultar_partidas()[0]
        self.assertEqual(partida['id'], ident)
        self.assertEqual([p[1] for p in partida['placar']], [3, 2])
        self.assertEqual(len(futebol.consultar_times()), 2)

    def test_consulta_times_filtra_partida_selecionada(self):
        primeira, times1 = self.partida()
        segunda, times2 = self.partida()
        self.assertEqual(len(futebol.consultar_times()), 4)
        for ident, times in ((primeira, times1), (segunda, times2)):
            resultado = futebol.consultar_times(ident)
            self.assertEqual([t['id'] for t in resultado], [t[0] for t in times])
            self.assertEqual(sum(len(t['membros']) for t in resultado), 7)
        with self.assertRaises(ValueError):
            futebol.consultar_times(999)

    def test_partida_invalida_nao_cria_historico(self):
        times = self.times()
        for t1, t2, g1 in ((times[0][0], times[0][0], 0),
                            (times[0][0], times[1][0], -1)):
            with self.assertRaises(ValueError):
                futebol.registrar_partida(t1, t2, g1, 0, datetime.now())
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(MatchHistory)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(MatchTeam)), 0)

    def test_avaliacao_media_e_correcao_sem_duplicar(self):
        partida, times = self.partida()
        futebol.avaliar_atleta(partida, 1, 8)
        futebol.avaliar_atleta(partida, 1, 10)
        segunda = futebol.registrar_partida(times[0][0], times[1][0], 0, 0, datetime.now())
        futebol.avaliar_atleta(segunda, 1, 6)
        with self.sessions() as session:
            self.assertEqual(session.get(User, 1).rating, 8)
            self.assertEqual(session.scalar(select(func.count()).select_from(PlayerMatchRating)), 2)

    def test_avaliacao_valida_participante_e_escala(self):
        partida, _ = self.partida()
        for nota in (-1, 11, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                futebol.avaliar_atleta(partida, 1, nota)
        with self.sessions.begin() as session:
            session.add(User(id=99, username='Fora da partida'))
        with self.assertRaises(ValueError):
            futebol.avaliar_atleta(partida, 99, 5)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(PlayerMatchRating)), 0)

    def test_bloqueia_times_com_mesmo_participante(self):
        times = self.times()
        with self.sessions.begin() as session:
            session.add(TeamPlayer(team_id=times[0][0], user_id=1))
            session.add(TeamPlayer(team_id=times[1][0], user_id=1))
        with self.assertRaises(ValueError):
            futebol.registrar_partida(times[0][0], times[1][0], 0, 0, datetime.now())


if __name__ == '__main__':
    unittest.main()
