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
        self.cadastrar(['S', 'Ana', 'invalida', '6', 'abc', '-1', '11', 'nan', 'inf', '8,5', 'N'])
        with self.sessions() as session:
            atleta = session.scalar(select(User))
            self.assertEqual(atleta.username, 'ANA')
            self.assertEqual(atleta.current_position_id, 6)
            self.assertEqual(atleta.initial_rating, 8.5)
            self.assertEqual(atleta.rating, 8.5)
        output = io.StringIO()
        with redirect_stdout(output):
            menu.listar()
        self.assertIn('Nome: ANA | Posição: Linha', output.getvalue())

    def test_sem_posicao_e_usuario_preexistente(self):
        with self.sessions.begin() as session:
            session.add(User(username='Gabriel'))
        self.cadastrar(['S', 'Bia', '0', '0', 'N'])
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
            output = self.cadastrar(['S', 'Teste', '1', '7'])
        self.assertIn('Nenhum cadastro foi confirmado', output)
        self.assertNotIn('senha-secreta', output)
        self.assertEqual(menu.consultar_atletas(), [])


class MenuFluxoTests(unittest.TestCase):
    def test_pesquisa_mostra_somente_atleta_do_id_informado(self):
        atleta = dict(id=7, nome='Ana', posicao='Linha', anterior='Goleiro',
                      funcao='Jogador', nota=8.543, nota_inicial=9, criado_em=None)
        output = io.StringIO()
        with patch.object(futebol, 'consultar_atleta', return_value=atleta) as consultar, \
             patch('builtins.input', side_effect=['abc', '-1', '7']), redirect_stdout(output):
            menu.pesquisar_atleta()
        consultar.assert_called_once_with(7)
        self.assertIn('ID: 7 | Nome: Ana | Posição: Linha', output.getvalue())
        self.assertIn('Posição anterior: Goleiro | Nota: 8.5', output.getvalue())
        self.assertIn('Habilidade inicial: 9.0', output.getvalue())

    def test_pesquisa_cancelada_nao_consulta(self):
        with patch.object(futebol, 'consultar_atleta') as consultar, \
             patch('builtins.input', return_value='0'), redirect_stdout(io.StringIO()):
            menu.pesquisar_atleta()
        consultar.assert_not_called()

    def test_pesquisa_inexistente_informa_sem_encerrar_menu(self):
        output = io.StringIO()
        with patch.object(futebol, 'consultar_atleta', side_effect=futebol.NaoEncontrado('Atleta não encontrado: 999.')), \
             patch('builtins.input', side_effect=['11', '999', '14', 'S']), redirect_stdout(output):
            menu.menu()
        self.assertIn('Atleta não encontrado: 999.', output.getvalue())
        self.assertIn('Obrigado, volte sempre!', output.getvalue())

    def test_exclusao_multipla_deduplica_e_continua_apos_bloqueio(self):
        atletas = [dict(Id=1, Nome='Ana'), dict(Id=2, Nome='Bia'), dict(Id=3, Nome='Caio')]
        output = io.StringIO()
        with patch.object(menu, 'listar'), \
             patch.object(menu, 'consultar_atletas', return_value=atletas), \
             patch.object(futebol, 'excluir_atleta', side_effect=[None, ValueError('Atleta vinculado'), None]) as excluir, \
             patch('builtins.input', side_effect=['1, 2, 1, 99, 3', 'S']), redirect_stdout(output):
            menu.deletar()
        self.assertEqual(excluir.call_args_list, [call(1), call(2), call(3)])
        self.assertIn('ID 99: não encontrado', output.getvalue())
        self.assertIn('ID 2 não excluído: Atleta vinculado', output.getvalue())
        self.assertIn('Atleta excluído: ID 3', output.getvalue())

    def test_exclusao_rejeita_entrada_invalida_e_permite_cancelar(self):
        with patch.object(menu, 'listar'), patch.object(futebol, 'excluir_atleta') as excluir, \
             patch('builtins.input', side_effect=['1, abc', '0, 2', '-1', '', '0']), \
             redirect_stdout(io.StringIO()):
            menu.deletar()
        excluir.assert_not_called()

    def test_exclusao_nao_confirmada_preserva_atletas(self):
        with patch.object(menu, 'listar'), \
             patch.object(menu, 'consultar_atletas', return_value=[dict(Id=1, Nome='Ana')]), \
             patch.object(futebol, 'excluir_atleta') as excluir, \
             patch('builtins.input', side_effect=['1', 'N']), redirect_stdout(io.StringIO()):
            menu.deletar()
        excluir.assert_not_called()

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
             patch('builtins.input', side_effect=['5', '14', 'S']), redirect_stdout(output):
            menu.menu()
        editar.assert_called_once()
        self.assertIn('12. Excluir time\n13. Excluir partida\n14. Sair', output.getvalue())

    def test_exclusoes_time_partida_exigem_confirmacao(self):
        for funcao, listagem, consulta, excluir, retorno in (
                (menu.deletar_time, 'listar_times', 'consultar_times', 'excluir_time', [dict(id=1, nome='Azul')]),
                (menu.deletar_partida, 'listar_partidas', 'consultar_partidas', 'excluir_partida', [dict(id=1, data=None)])):
            for resposta in ('S', 'N'):
                with patch.object(menu, listagem), patch.object(futebol, consulta, return_value=retorno), \
                     patch.object(futebol, excluir) as operacao, \
                     patch('builtins.input', side_effect=['1', resposta]), redirect_stdout(io.StringIO()):
                    funcao()
                if resposta == 'S':
                    operacao.assert_called_once_with(1)
                else:
                    operacao.assert_not_called()

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
