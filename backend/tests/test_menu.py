import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import call, patch

from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

import menu
import futebol
from models import Position, Role, User


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        for table in (Position.__table__, Role.__table__, User.__table__):
            table.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions.begin() as session:
            session.add_all([Position(id=1, position_title='Goleiro'),
                             Position(id=6, position_title='Linha')])
        self.patcher = patch.object(menu, 'SessionLocal', self.sessions)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        service_patch = patch.object(futebol, 'SessionLocal', self.sessions)
        service_patch.start()
        self.addCleanup(service_patch.stop)
        self.addCleanup(self.engine.dispose)

    def cadastrar(self, respostas):
        output = io.StringIO()
        with patch('builtins.input', side_effect=respostas), redirect_stdout(output):
            menu.cadastrar()
        return output.getvalue()

    def test_cadastro_persiste_e_listagem_em_nova_sessao(self):
        self.cadastrar(['S', 'Ana', 'invalida', '6', 'N'])
        with self.sessions() as session:
            atleta = session.scalar(select(User))
            self.assertEqual(atleta.username, 'ANA')
            self.assertEqual(atleta.current_position_id, 6)
        output = io.StringIO()
        with redirect_stdout(output):
            menu.listar()
        self.assertIn('Nome: ANA | Posição: Linha', output.getvalue())

    def test_sem_posicao_e_usuario_preexistente(self):
        with self.sessions.begin() as session:
            session.add(User(username='Gabriel'))
        self.cadastrar(['S', 'Bia', '0', 'N'])
        atletas = menu.consultar_atletas()
        self.assertEqual([a['Nome'] for a in atletas], ['Gabriel', 'BIA'])
        self.assertEqual(atletas[0]['Posicao'], 'Sem posição selecionada')
        self.assertEqual(atletas[1]['Posicao'], 'Linha')
        with self.sessions() as session:
            usuarios = session.scalars(select(User).order_by(User.id)).all()
            self.assertIsNone(usuarios[0].current_position_id)
            self.assertEqual(usuarios[1].current_position_id, 6)

    def test_nome_invalido_nao_grava(self):
        self.cadastrar(['S', '   ', 'S', 'A' * 101, 'N'])
        self.assertEqual(menu.consultar_atletas(), [])

    def test_falha_gravacao_desfaz_cadastro(self):
        error = OperationalError(None, None, Exception('senha-secreta'))
        original_flush = Session.flush

        def falhar_gravacao(session, *args, **kwargs):
            if session.new:
                raise error
            return original_flush(session, *args, **kwargs)

        with patch.object(Session, 'flush', falhar_gravacao):
            output = self.cadastrar(['S', 'Teste', '1'])
        self.assertIn('Nenhum cadastro foi confirmado', output)
        self.assertNotIn('senha-secreta', output)
        self.assertEqual(menu.consultar_atletas(), [])


class MenuFluxoTests(unittest.TestCase):
    def test_registro_aceita_somente_data(self):
        with patch.object(menu, 'listar_times'), \
             patch.object(futebol, 'registrar_partida', return_value=3) as salvar, \
             patch('builtins.input', side_effect=['1', '2', '3', '0', '12/10/2026']), \
             redirect_stdout(io.StringIO()):
            menu.registrar_partida()
        salvar.assert_called_once_with(1, 2, 3, 0, datetime(2026, 10, 12))

    def test_avalia_dois_jogadores_sem_repetir_partida(self):
        with patch.object(menu, 'listar_partidas') as listar, \
             patch.object(menu, 'listar_times') as times, \
             patch.object(futebol, 'avaliar_atleta') as salvar, \
             patch('builtins.input', side_effect=['3', '1', '8.5', 'talvez', 's', '2', '9,5', 'n']), \
             redirect_stdout(io.StringIO()):
            menu.avaliar()
        listar.assert_called_once()
        times.assert_called_once_with(3)
        self.assertEqual(salvar.call_args_list, [call(3, 1, 8.5), call(3, 2, 9.5)])

    def test_sair_e_ultima_opcao_e_editar_ocupa_cinco(self):
        output = io.StringIO()
        with patch.object(menu, 'editar') as editar, \
             patch('builtins.input', side_effect=['5', '11', 'S']), redirect_stdout(output):
            menu.menu()
        editar.assert_called_once()
        self.assertIn('10. Consultar posições e funções\n11. Sair', output.getvalue())

    def test_historico_exibe_data_e_uma_casa_decimal(self):
        partidas = [dict(id=1, data=datetime(2026, 10, 12, 20, 30),
                         placar=[], notas=[('Ana', 8.54321)])]
        output = io.StringIO()
        with patch.object(futebol, 'consultar_partidas', return_value=partidas), redirect_stdout(output):
            menu.listar_partidas()
        self.assertIn('12/10/2026', output.getvalue())
        self.assertNotIn('20:30', output.getvalue())
        self.assertIn('Ana | 8.5\n', output.getvalue())


if __name__ == '__main__':
    unittest.main()
