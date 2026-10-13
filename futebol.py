"""Operações do futebol; cada gravação é confirmada em uma única transação."""
import math
import random
from datetime import datetime

from sqlalchemy import func, select

from db import SessionLocal
from models import (MatchHistory, MatchTeam, PlayerMatchRating, Position,
                    Role, Team, TeamPlayer, User)


def exigir(session, model, ident, descricao):
    registro = session.get(model, ident)
    if registro is None:
        raise ValueError(f'{descricao} não encontrado: {ident}.')
    return registro


def nome_valido(nome):
    nome = nome.strip()
    if not nome or len(nome) > 100:
        raise ValueError('O nome deve ter entre 1 e 100 caracteres.')
    return nome


def nota_valida(nota):
    if not math.isfinite(nota) or not 0 <= nota <= 10:
        raise ValueError('A nota deve estar entre 0 e 10.')


def referencias(model):
    if model not in (Position, Role):
        raise ValueError('Tabela de referência inválida.')
    with SessionLocal() as session:
        coluna = model.position_title if model is Position else model.role_name
        return session.execute(select(model.id, coluna).order_by(model.id)).all()


def editar_atleta(ident, nome, posicao_id, role_id):
    nome = nome_valido(nome)
    with SessionLocal.begin() as session:
        atleta = exigir(session, User, ident, 'Atleta')
        exigir(session, Position, posicao_id, 'Posição')
        if role_id is not None:
            exigir(session, Role, role_id, 'Função')
        if atleta.current_position_id != posicao_id:
            atleta.last_position_id = atleta.current_position_id
            atleta.current_position_id = posicao_id
        atleta.username = nome
        atleta.role_id = role_id


def excluir_atleta(ident):
    with SessionLocal.begin() as session:
        atleta = exigir(session, User, ident, 'Atleta')
        vinculos = ((TeamPlayer, TeamPlayer.user_id),
                    (PlayerMatchRating, PlayerMatchRating.user_id))
        for model, coluna in vinculos:
            if session.scalar(select(model.id).where(coluna == ident).limit(1)) is not None:
                raise ValueError('Atleta vinculado a um time ou partida; exclusão bloqueada para preservar o histórico.')
        session.delete(atleta)


def detalhes_atletas():
    with SessionLocal() as session:
        atletas = session.scalars(select(User).order_by(User.id)).all()
        return [dict(id=a.id, nome=a.username,
                     posicao=a.current_position.position_title if a.current_position else 'Sem posição selecionada',
                     anterior=a.last_position.position_title if a.last_position else 'Nenhuma',
                     funcao=a.role.role_name if a.role else 'Sem função',
                     nota=a.rating, criado_em=a.created_at) for a in atletas]


def sortear_times(ids, nomes):
    if len(ids) != len(set(ids)):
        raise ValueError('Não repita IDs de atletas.')
    if len(nomes) != 2:
        raise ValueError('Informe os nomes dos dois times.')
    nomes = [nome_valido(n) for n in nomes]
    with SessionLocal.begin() as session:
        atletas = [exigir(session, User, ident, 'Atleta') for ident in ids]
        goleiros = [a for a in atletas if a.current_position and
                    a.current_position.position_title.strip().casefold() == 'goleiro']
        if len(goleiros) < 2:
            raise ValueError('Selecione pelo menos dois goleiros para criar os times.')
        random.shuffle(goleiros)
        grupos = [[goleiros[0]], [goleiros[1]]]
        restantes = [a for a in atletas if a.id not in {goleiros[0].id, goleiros[1].id}]
        random.shuffle(restantes)
        for atleta in restantes:
            grupos[0 if len(grupos[0]) <= len(grupos[1]) else 1].append(atleta)
        resultado = []
        for nome, grupo in zip(nomes, grupos):
            time = Team(team_name=nome)
            session.add(time)
            session.flush()
            session.add_all([TeamPlayer(team_id=time.id, user_id=a.id) for a in grupo])
            resultado.append((time.id, nome, [a.username for a in grupo]))
        return resultado


def consultar_times(partida_id=None):
    with SessionLocal() as session:
        consulta = select(Team).order_by(Team.id)
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
        medias_por_partida = (select(func.avg(PlayerMatchRating.rating).label('nota'))
                              .where(PlayerMatchRating.user_id == atleta_id)
                              .group_by(PlayerMatchRating.match_id).subquery())
        atleta.rating = session.scalar(select(func.avg(medias_por_partida.c.nota)))


def consultar_partidas():
    with SessionLocal() as session:
        resultado = []
        for partida in session.scalars(select(MatchHistory).order_by(MatchHistory.id)):
            placar = session.execute(select(Team.team_name, MatchTeam.goals)
                      .join(MatchTeam, MatchTeam.team_id == Team.id)
                      .where(MatchTeam.match_id == partida.id).order_by(MatchTeam.id)).all()
            notas = session.execute(select(User.username, PlayerMatchRating.rating)
                     .join(PlayerMatchRating, PlayerMatchRating.user_id == User.id)
                     .where(PlayerMatchRating.match_id == partida.id)
                     .order_by(PlayerMatchRating.id)).all()
            resultado.append(dict(id=partida.id, data=partida.match_date,
                             placar=placar, notas=notas))
        return resultado
