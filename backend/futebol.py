"""Operações do futebol; cada gravação é confirmada em uma única transação."""
import math
import random
from datetime import datetime

from sqlalchemy import delete, func, select

from db import SessionLocal
from models import (MatchHistory, MatchTeam, PlayerMatchRating, Position,
                    Role, Team, TeamPlayer, User)


class NaoEncontrado(ValueError):
    pass


class Conflito(ValueError):
    pass


NAO_INFORMADO = object()


def exigir(session, model, ident, descricao):
    registro = session.get(model, ident)
    if registro is None:
        raise NaoEncontrado(f'{descricao} não encontrado: {ident}.')
    return registro


def nome_valido(nome):
    nome = nome.strip()
    if not nome or len(nome) > 100:
        raise ValueError('O nome deve ter entre 1 e 100 caracteres.')
    return nome


def nota_valida(nota):
    if not math.isfinite(nota) or not 0 <= nota <= 10:
        raise ValueError('A nota deve estar entre 0 e 10.')


def dados_atleta(atleta):
    return dict(id=atleta.id, nome=atleta.username,
                posicao_id=atleta.current_position_id,
                posicao=atleta.current_position.position_title if atleta.current_position else 'Sem posição selecionada',
                anterior=atleta.last_position.position_title if atleta.last_position else 'Nenhuma',
                funcao_id=atleta.role_id,
                funcao=atleta.role.role_name if atleta.role else 'Sem função',
                nota=atleta.rating, nota_inicial=atleta.initial_rating,
                criado_em=atleta.created_at)


def cadastrar_atleta(nome, posicao_id, rating_inicial):
    nome = nome_valido(nome.strip().upper())
    nota_valida(rating_inicial)
    posicao_id = 6 if posicao_id == 0 else posicao_id
    with SessionLocal.begin() as session:
        exigir(session, Position, posicao_id, 'Posição')
        atleta = User(username=nome, current_position_id=posicao_id,
                      initial_rating=rating_inicial, rating=rating_inicial)
        session.add(atleta)
        session.flush()
        resultado = dados_atleta(atleta)
    return resultado


def referencias(model):
    if model not in (Position, Role):
        raise ValueError('Tabela de referência inválida.')
    with SessionLocal() as session:
        coluna = model.position_title if model is Position else model.role_name
        return session.execute(select(model.id, coluna).order_by(model.id)).all()


def consultar_atleta(ident):
    with SessionLocal() as session:
        return dados_atleta(exigir(session, User, ident, 'Atleta'))


def editar_atleta(ident, nome=NAO_INFORMADO, posicao_id=NAO_INFORMADO, role_id=NAO_INFORMADO):
    with SessionLocal.begin() as session:
        atleta = exigir(session, User, ident, 'Atleta')
        if nome is not NAO_INFORMADO:
            atleta.username = nome_valido(nome)
        if posicao_id is not NAO_INFORMADO:
            posicao_id = 6 if posicao_id == 0 else posicao_id
            exigir(session, Position, posicao_id, 'Posição')
            if atleta.current_position_id != posicao_id:
                atleta.last_position_id = atleta.current_position_id
                atleta.current_position_id = posicao_id
        if role_id is not NAO_INFORMADO:
            if role_id is not None:
                exigir(session, Role, role_id, 'Função')
            atleta.role_id = role_id
        session.flush()
        # Expira relacionamentos caso a edição tenha alterado suas chaves.
        session.expire(atleta, ['current_position', 'last_position', 'role'])
        resultado = dados_atleta(atleta)
    return resultado


def excluir_atleta(ident):
    with SessionLocal.begin() as session:
        atleta = exigir(session, User, ident, 'Atleta')
        vinculos = ((TeamPlayer, TeamPlayer.user_id),
                    (PlayerMatchRating, PlayerMatchRating.user_id))
        for model, coluna in vinculos:
            if session.scalar(select(model.id).where(coluna == ident).limit(1)) is not None:
                raise Conflito('Atleta vinculado a um time ou partida; exclusão bloqueada para preservar o histórico.')
        session.delete(atleta)


def detalhes_atletas():
    with SessionLocal() as session:
        atletas = session.scalars(select(User).order_by(User.id)).all()
        return [dados_atleta(a) for a in atletas]


def rating_sorteio(atleta):
    nota = 5.0 if atleta.rating is None else float(atleta.rating)
    nota_valida(nota)
    return int(round(round(nota, 1) * 10))


def equilibrar_times(atletas):
    """Minimiza a diferença de somas em décimos, com tamanho e goleiros válidos."""
    atletas = list(atletas)
    random.shuffle(atletas)
    goleiros = [bool(a.current_position and
                     a.current_position.position_title.strip().casefold() == 'goleiro')
                for a in atletas]
    total_goleiros = sum(goleiros)
    if total_goleiros < 2:
        raise ValueError('Selecione pelo menos dois goleiros para criar os times.')
    notas = [rating_sorteio(a) for a in atletas]
    tamanho = len(atletas) // 2
    # Uma máscara de participantes por estado (quantidade, soma, goleiros).
    estados = {(0, 0, 0): 0}
    for indice, (nota, goleiro) in enumerate(zip(notas, goleiros)):
        novos = {}
        for (quantidade, soma, qtd_goleiros), mascara in estados.items():
            if quantidade >= tamanho or qtd_goleiros + goleiro >= total_goleiros:
                continue
            chave = (quantidade + 1, soma + nota, qtd_goleiros + goleiro)
            if chave not in estados and chave not in novos:
                novos[chave] = mascara | (1 << indice)
        estados.update(novos)
    total = sum(notas)
    melhores = []
    menor_diferenca = None
    for (quantidade, soma, qtd_goleiros), mascara in estados.items():
        if quantidade != tamanho or not 0 < qtd_goleiros < total_goleiros:
            continue
        diferenca = abs(total - 2 * soma)
        if menor_diferenca is None or diferenca < menor_diferenca:
            menor_diferenca = diferenca
            melhores = [mascara]
        elif diferenca == menor_diferenca:
            melhores.append(mascara)
    escolhidos = random.choice(melhores)
    grupos = [[], []]
    for indice, atleta in enumerate(atletas):
        grupos[0 if escolhidos & (1 << indice) else 1].append(atleta)
    random.shuffle(grupos)
    return grupos


def sortear_times(ids, nomes):
    if len(ids) != len(set(ids)):
        raise ValueError('Não repita IDs de atletas.')
    if len(nomes) != 2:
        raise ValueError('Informe os nomes dos dois times.')
    nomes = [nome_valido(n) for n in nomes]
    with SessionLocal.begin() as session:
        atletas = [exigir(session, User, ident, 'Atleta') for ident in ids]
        grupos = equilibrar_times(atletas)
        resultado = []
        for nome, grupo in zip(nomes, grupos):
            time = Team(team_name=nome)
            session.add(time)
            session.flush()
            session.add_all([TeamPlayer(team_id=time.id, user_id=a.id) for a in grupo])
            resumo = dict(total=sum(rating_sorteio(a) for a in grupo) / 10,
                          quantidade=len(grupo),
                          ids=[a.id for a in grupo],
                          sem_rating=[a.username for a in grupo if a.rating is None])
            resultado.append((time.id, nome, [a.username for a in grupo], resumo))
        return resultado


def consultar_times(partida_id=None, time_id=None):
    with SessionLocal() as session:
        consulta = select(Team).order_by(Team.id)
        if time_id is not None:
            exigir(session, Team, time_id, 'Time')
            consulta = consulta.where(Team.id == time_id)
        if partida_id is not None:
            exigir(session, MatchHistory, partida_id, 'Partida')
            consulta = (consulta.join(MatchTeam, MatchTeam.team_id == Team.id)
                        .where(MatchTeam.match_id == partida_id).distinct())
        times = session.scalars(consulta).all()
        resultado = []
        for time in times:
            membros = session.execute(
                select(User.id, User.username).join(TeamPlayer, TeamPlayer.user_id == User.id)
                .where(TeamPlayer.team_id == time.id).order_by(User.id)).all()
            resultado.append(dict(id=time.id, nome=time.team_name, membros=membros))
        return resultado


def registrar_partida(time1, time2, gols1, gols2, data):
    if time1 == time2:
        raise ValueError('Selecione dois times diferentes.')
    if any(type(g) is not int or g < 0 for g in (gols1, gols2)):
        raise ValueError('Os gols devem ser números inteiros não negativos.')
    if not isinstance(data, datetime):
        raise ValueError('Data da partida inválida.')
    with SessionLocal.begin() as session:
        for ident in (time1, time2):
            exigir(session, Team, ident, 'Time')
        membros = [set(session.scalars(select(TeamPlayer.user_id)
                   .where(TeamPlayer.team_id == ident))) for ident in (time1, time2)]
        if any(not grupo for grupo in membros):
            raise ValueError('Os dois times precisam ter atletas.')
        if membros[0] & membros[1]:
            raise ValueError('Um atleta não pode participar dos dois times na mesma partida.')
        partida = MatchHistory(match_date=data)
        session.add(partida)
        session.flush()
        session.add_all([MatchTeam(match_id=partida.id, team_id=ident, goals=gols)
                         for ident, gols in ((time1, gols1), (time2, gols2))])
        return partida.id


def avaliar_atleta(partida_id, atleta_id, nota):
    nota_valida(nota)
    with SessionLocal.begin() as session:
        exigir(session, MatchHistory, partida_id, 'Partida')
        atleta = exigir(session, User, atleta_id, 'Atleta')
        participante = session.scalar(
            select(TeamPlayer.id).join(MatchTeam, MatchTeam.team_id == TeamPlayer.team_id)
            .where(MatchTeam.match_id == partida_id, TeamPlayer.user_id == atleta_id).limit(1))
        if participante is None:
            raise ValueError('O atleta não participou dessa partida.')
        notas = session.scalars(select(PlayerMatchRating).where(
            PlayerMatchRating.match_id == partida_id, PlayerMatchRating.user_id == atleta_id)
            .order_by(PlayerMatchRating.id)).all()
        if notas:
            notas[0].rating = nota
            # Normaliza eventuais duplicatas preexistentes para uma nota por partida.
            for duplicada in notas[1:]:
                session.delete(duplicada)
        else:
            session.add(PlayerMatchRating(match_id=partida_id, user_id=atleta_id, rating=nota))
        session.flush()
        recalcular_rating(session, atleta)
        session.flush()
        resultado = dados_atleta(atleta)
    return resultado


def recalcular_rating(session, atleta):
    medias = (select(func.avg(PlayerMatchRating.rating).label('nota'))
              .where(PlayerMatchRating.user_id == atleta.id)
              .group_by(PlayerMatchRating.match_id).subquery())
    soma, quantidade = session.execute(select(
        func.coalesce(func.sum(medias.c.nota), 0), func.count(medias.c.nota))).one()
    soma = float(soma)
    if atleta.initial_rating is not None:
        soma += float(atleta.initial_rating)
        quantidade += 1
    atleta.rating = soma / quantidade if quantidade else None


def excluir_time(ident):
    with SessionLocal.begin() as session:
        time = exigir(session, Team, ident, 'Time')
        if session.scalar(select(MatchTeam.id).where(MatchTeam.team_id == ident).limit(1)) is not None:
            raise Conflito('Time vinculado a uma partida. Exclua a partida antes de excluir o time.')
        session.execute(delete(TeamPlayer).where(TeamPlayer.team_id == ident))
        session.delete(time)


def excluir_partida(ident):
    with SessionLocal.begin() as session:
        partida = exigir(session, MatchHistory, ident, 'Partida')
        atletas = session.scalars(select(User).where(User.id.in_(
            select(PlayerMatchRating.user_id).where(PlayerMatchRating.match_id == ident)))).all()
        session.execute(delete(PlayerMatchRating).where(PlayerMatchRating.match_id == ident))
        session.execute(delete(MatchTeam).where(MatchTeam.match_id == ident))
        session.delete(partida)
        session.flush()
        for atleta in atletas:
            recalcular_rating(session, atleta)


def consultar_partidas(partida_id=None):
    with SessionLocal() as session:
        resultado = []
        consulta = select(MatchHistory).order_by(MatchHistory.id)
        if partida_id is not None:
            exigir(session, MatchHistory, partida_id, 'Partida')
            consulta = consulta.where(MatchHistory.id == partida_id)
        for partida in session.scalars(consulta):
            placar = session.execute(select(Team.id, Team.team_name, MatchTeam.goals)
                      .join(MatchTeam, MatchTeam.team_id == Team.id)
                      .where(MatchTeam.match_id == partida.id).order_by(MatchTeam.id)).all()
            notas = session.execute(select(User.id, User.username, PlayerMatchRating.rating)
                     .join(PlayerMatchRating, PlayerMatchRating.user_id == User.id)
                     .where(PlayerMatchRating.match_id == partida.id)
                     .order_by(PlayerMatchRating.id)).all()
            resultado.append(dict(id=partida.id, data=partida.match_date,
                             placar=[(nome, gols) for _, nome, gols in placar],
                             notas=[(nome, nota) for _, nome, nota in notas],
                             times=[dict(id=ident, nome=nome, gols=gols) for ident, nome, gols in placar],
                             avaliacoes=[dict(atleta_id=ident, nome=nome, nota=nota)
                                         for ident, nome, nota in notas]))
        return resultado
