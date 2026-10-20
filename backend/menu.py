"""Menu de gerenciamento de atletas, times e partidas no MySQL."""

from datetime import datetime

import futebol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal
from models import Position, Role, User

def cadastrar():
    while True:
        resp = input("Deseja inserir um atleta? S ou N ").upper().strip()
        
        if resp == "S":
            nome = str(input("Digite o nome do atleta: ").upper().strip())
            if not nome or len(nome) > 100:
                print("O nome deve ter entre 1 e 100 caracteres.")
                continue
            try:
                with SessionLocal() as session:
                    posicoes = {
                        str(posicao.id): posicao.position_title
                        for posicao in session.scalars(select(Position).order_by(Position.id))
                    }
            except SQLAlchemyError:
                print("Não foi possível consultar as posições. Confira a conexão com o banco.")
                return

            posicoes['0'] = 'Sem posição selecionada (será cadastrado como Linha)'
            print("\nPosições disponíveis:")
            for codigo, titulo in posicoes.items():
                print(f"{codigo}. {titulo}")

            while True:
                posicao_string = input("Selecione a posição do atleta: ").strip()
                if posicao_string in posicoes:
                    break
                print("Posição inválida. Digite uma das opções acima.")

            while True:
                try:
                    nota_inicial = float(input('Nota inicial de habilidade (0 a 10): ').strip().replace(',', '.'))
                    futebol.nota_valida(nota_inicial)
                    break
                except ValueError:
                    print('Digite uma nota válida de 0 a 10.')
            
            try:
                futebol.cadastrar_atleta(nome, int(posicao_string), nota_inicial)
            except ValueError as erro:
                print(f'Cadastro não concluído: {erro}')
                continue
            except SQLAlchemyError:
                print("Não foi possível salvar o atleta. Nenhum cadastro foi confirmado.")
                return

            print("Atleta cadastrado! ")

        elif resp == "N":
            break

        else:
            print("Resposta inválida, responda com S ou N ")

# Consulta compartilhada pela listagem e pelo sorteio.
def consultar_atletas():
    with SessionLocal() as session:
        registros = session.execute(
            select(User.id, User.username, Position.position_title)
            .outerjoin(Position, User.current_position_id == Position.id)
            .order_by(User.id)
        ).all()
        return [
            {"Id": registro.id, "Nome": registro.username,
             "Posicao": registro.position_title or "Sem posição selecionada"}
            for registro in registros
        ]


def listar():
    try:
        atletas = futebol.detalhes_atletas()
    except SQLAlchemyError:
        print("Não foi possível listar os atletas. Confira a conexão com o banco.")
        return
    if not atletas:
        print("A lista está vazia!")
    else:
        for atleta in atletas:
            exibir_atleta(atleta)


def exibir_atleta(atleta):
    print(f"ID: {atleta['id']} | Nome: {atleta['nome']} | Posição: {atleta['posicao']}")
    nota = 'Sem avaliações' if atleta['nota'] is None else f"{atleta['nota']:.1f}"
    inicial = 'Não informada' if atleta['nota_inicial'] is None else f"{atleta['nota_inicial']:.1f}"
    print(f"  Função: {atleta['funcao']} | Posição anterior: {atleta['anterior']} | Nota: {nota} | Cadastro: {atleta['criado_em']}")
    print(f'  Habilidade inicial: {inicial}')


def pesquisar_atleta():
    while True:
        ident = ler_inteiro('ID do atleta para pesquisar (0 cancela): ')
        if ident == 0:
            return
        if ident > 0:
            break
        print('Digite um ID positivo ou 0 para cancelar.')
    try:
        atleta = futebol.consultar_atleta(ident)
    except futebol.NaoEncontrado as erro:
        print(erro)
        return
    exibir_atleta(atleta)


def menu():
    while True:
        print("\nMenu do futebol semanal\n"
              "1. Cadastrar atleta\n2. Listar atletas\n3. Excluir atleta\n"
              "4. Sortear e salvar times\n5. Editar atleta\n"
              "6. Listar times\n7. Registrar partida e placar\n"
              "8. Listar partidas e avaliações\n9. Avaliar atleta em partida\n"
              "10. Consultar posições e funções\n11. Pesquisar atleta por ID\n"
              "12. Excluir time\n13. Excluir partida\n14. Sair\n")

        try:
            opcao = int(input("Selecione a opção desejada: "))
        except ValueError:
            print("Digite uma opção válida.")
            continue

        if opcao == 14:
            sair = str(input("Digite S para confirmar: ")).upper().strip()

            if sair == "S": # sair da lista
                print("Obrigado, volte sempre! ")
                return

            else:
                continue

        acoes = {1: cadastrar, 2: listar, 3: deletar, 4: criar_times,
                 5: editar, 6: listar_times, 7: registrar_partida,
                 8: listar_partidas, 9: avaliar, 10: listar_referencias,
                 11: pesquisar_atleta, 12: deletar_time, 13: deletar_partida}
        if opcao not in acoes:
            print("Digite uma opção válida ")
            continue
        try:
            acoes[opcao]()
        except ValueError as erro:
            print(f"Operação não concluída: {erro}")
        except SQLAlchemyError:
            print("Não foi possível concluir a operação no banco. Confira a conexão e os vínculos dos registros.")

def deletar_time():
    listar_times()
    ident = ler_inteiro('ID do time para excluir (0 cancela): ')
    if ident == 0:
        return
    time = futebol.consultar_times(time_id=ident)[0]
    print(f"Time selecionado: {time['id']} | {time['nome']}")
    if input('Excluir o time e seus vínculos com atletas? S ou N: ').strip().upper() != 'S':
        return
    futebol.excluir_time(ident)
    print('Time excluído. Os atletas foram preservados.')


def deletar_partida():
    listar_partidas()
    ident = ler_inteiro('ID da partida para excluir (0 cancela): ')
    if ident == 0:
        return
    partida = futebol.consultar_partidas(ident)[0]
    print(f"Partida selecionada: {partida['id']} | {partida['data']}")
    print('A exclusão remove placares e avaliações e recalcula os ratings. Times e atletas serão preservados.')
    if input('Confirmar exclusão da partida? S ou N: ').strip().upper() != 'S':
        return
    futebol.excluir_partida(ident)
    print('Partida excluída e ratings recalculados.')


def deletar():
    listar()
    while True:
        entrada = input('IDs dos atletas para excluir, separados por vírgula (0 cancela): ').strip()
        if entrada == '0':
            return
        try:
            ids = list(dict.fromkeys(int(item.strip()) for item in entrada.split(',')))
            if any(ident <= 0 for ident in ids):
                raise ValueError
            break
        except ValueError:
            print('Digite IDs positivos separados por vírgula, por exemplo: 3, 5, 8. Ou somente 0 para cancelar.')
    atletas = {a['Id']: a['Nome'] for a in consultar_atletas()}
    selecionados = []
    print('Atletas selecionados:')
    for ident in ids:
        if ident not in atletas:
            print(f'ID {ident}: não encontrado; será ignorado.')
            continue
        selecionados.append(ident)
        print(f'ID {ident}: {atletas[ident]}')
    if not selecionados:
        return
    if input('Confirmar exclusão dos atletas selecionados? S ou N: ').strip().upper() != 'S':
        return
    for ident in selecionados:
        try:
            futebol.excluir_atleta(ident)
        except ValueError as erro:
            print(f'ID {ident} não excluído: {erro}')
        except SQLAlchemyError:
            print(f'ID {ident} não excluído: falha no banco. Os demais resultados são informados individualmente.')
        else:
            print(f'Atleta excluído: ID {ident} | {atletas[ident]}')


def ler_inteiro(pergunta):
    while True:
        try:
            return int(input(pergunta).strip())
        except ValueError:
            print('Digite um número inteiro.')


def escolher_referencia(model, opcional=False):
    registros = futebol.referencias(model)
    for ident, titulo in registros:
        print(f'{ident}. {titulo}')
    print('0. Sem função' if opcional else '0. Sem posição selecionada (Linha)')
    while True:
        ident = ler_inteiro('Escolha: ')
        if ident == 0:
            ident = None if opcional else 6
        if ident is None or ident in {r[0] for r in registros}:
            return ident
        print('Selecione uma opção cadastrada no banco.')


def editar():
    listar()
    ident = ler_inteiro('ID do atleta para editar (0 cancela): ')
    if ident == 0:
        return
    nome = input('Nome do atleta: ')
    print('Posição:')
    posicao = escolher_referencia(Position)
    print('Função:')
    funcao = escolher_referencia(Role, opcional=True)
    futebol.editar_atleta(ident, nome, posicao, funcao)
    print('Atleta atualizado. A mudança de posição foi registrada.')


def listar_referencias():
    for model, titulo in ((Position, 'Posições'), (Role, 'Funções')):
        print(titulo + ':')
        for ident, nome in futebol.referencias(model):
            print(f'{ident}. {nome}')

def criar_times():
    listar()
    selecao = input('IDs dos participantes separados por vírgula (ENTER para todos): ').strip()
    ids = [int(item.strip()) for item in selecao.split(',')] if selecao else [a['Id'] for a in consultar_atletas()]
    nomes = [input('Nome do time 1: '), input('Nome do time 2: ')]
    times = futebol.sortear_times(ids, nomes)
    for ident, nome, atletas, resumo in times:
        print(f'Time salvo: ID {ident} | {nome} | ' + ', '.join(atletas))
        print(f"  Rating total: {resumo['total']:.1f} | Média: {resumo['total'] / resumo['quantidade']:.1f}")
        if resumo['sem_rating']:
            print('  Sem rating: usado 5.0 apenas neste sorteio para ' + ', '.join(resumo['sem_rating']))
    diferenca = abs(times[0][3]['total'] - times[1][3]['total'])
    print(f'Diferença entre os totais: {diferenca:.1f} (menor possível com estes participantes).')


def listar_times(partida_id=None):
    times = futebol.consultar_times(partida_id)
    if not times:
        print('Nenhum time cadastrado.')
    for time in times:
        print(f"ID: {time['id']} | Time: {time['nome']}")
        for ident, nome in time['membros']:
            print(f'  Atleta ID {ident}: {nome}')


def registrar_partida():
    listar_times()
    time1 = ler_inteiro('ID do primeiro time: ')
    time2 = ler_inteiro('ID do segundo time: ')
    gols1 = ler_inteiro('Gols do primeiro time: ')
    gols2 = ler_inteiro('Gols do segundo time: ')
    data = input('Data da partida (DD/MM/AAAA): ').strip()
    try:
        data = datetime.strptime(data, '%d/%m/%Y')
    except ValueError:
        raise ValueError('Use uma data válida no formato DD/MM/AAAA.') from None
    ident = futebol.registrar_partida(time1, time2, gols1, gols2, data)
    print(f'Partida e placar salvos. ID: {ident}')


def listar_partidas():
    partidas = futebol.consultar_partidas()
    if not partidas:
        print('Nenhuma partida cadastrada.')
    for partida in partidas:
        data = partida['data'].strftime('%d/%m/%Y') if partida['data'] else 'Data não informada'
        print(f"Partida ID {partida['id']} | {data}")
        for time, gols in partida['placar']:
            print(f'  {time}: {gols} gols')
        for atleta, nota in partida['notas']:
            nota_exibida = 'Sem avaliação' if nota is None else f'{nota:.1f}'
            print(f'  Avaliação: {atleta} | {nota_exibida}')


def avaliar():
    listar_partidas()
    partida = ler_inteiro('ID da partida: ')
    print(f'Times e jogadores da partida {partida}:')
    listar_times(partida)
    while True:
        atleta = ler_inteiro('ID do atleta participante (0 para voltar ao menu): ')
        if atleta == 0:
            return
        try:
            nota = float(input('Nota de 0 a 10: ').strip().replace(',', '.'))
        except ValueError:
            print('Digite uma nota numérica de 0 a 10.')
            continue
        try:
            futebol.avaliar_atleta(partida, atleta, nota)
        except ValueError as erro:
            print(f'Avaliação não concluída: {erro}')
            continue
        print('Avaliação salva; nota geral recalculada com a habilidade inicial e as partidas.')
        while True:
            resposta = input('Deseja avaliar outro jogador desta partida? S ou N: ').strip().upper()
            if resposta in ('S', 'N'):
                break
            print('Responda com S ou N.')
        if resposta == 'N':
            return


if __name__ == "__main__":
    menu()
