from datetime import datetime, time
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import futebol
from models import Position, Role
from schemas import (AtletaCadastro, AtletaResposta, AtletaEdicao, ExclusaoMultipla,
                     ResultadoExclusao, ReferenciaResposta, TimeResposta,
                     SorteioEntrada, SorteioResposta, PartidaCadastro,
                     PartidaResposta, AvaliacaoEntrada)

IdRota = Annotated[int, Path(gt=0)]

app = FastAPI(title="Fut Manager API")


@app.get("/")
def inicio():
    return {"mensagem": "Fut Manager API funcionando"}


@app.exception_handler(SQLAlchemyError)
async def erro_banco(request, error):
    return JSONResponse(status_code=503, content={
        'detail': 'Não foi possível concluir a operação no banco. Tente novamente.'})


@app.exception_handler(futebol.NaoEncontrado)
async def erro_nao_encontrado(request, error):
    return JSONResponse(status_code=404, content={'detail': str(error)})


@app.exception_handler(futebol.Conflito)
async def erro_conflito(request, error):
    return JSONResponse(status_code=409, content={'detail': str(error)})


@app.exception_handler(ValueError)
async def erro_regra(request, error):
    return JSONResponse(status_code=422, content={'detail': str(error)})


@app.get('/atletas', response_model=list[AtletaResposta], tags=['Atletas'])
def listar_atletas():
    return futebol.detalhes_atletas()


@app.post('/atletas', response_model=AtletaResposta, status_code=201, tags=['Atletas'])
def cadastrar_atleta(dados: AtletaCadastro):
    try:
        return futebol.cadastrar_atleta(dados.nome, dados.posicao_id, dados.rating_inicial)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from None


@app.get('/atletas/{ident}', response_model=AtletaResposta, tags=['Atletas'],
         summary='Pesquisar atleta por ID',
         description='Retorna nome, posição, função, posição anterior, ratings e data de cadastro. ID inexistente retorna 404.')
def consultar_atleta(ident: IdRota):
    return futebol.consultar_atleta(ident)


@app.patch('/atletas/{ident}', response_model=AtletaResposta, tags=['Atletas'])
def editar_atleta(ident: IdRota, dados: AtletaEdicao):
    campos = dados.model_dump(exclude_unset=True)
    if 'funcao_id' in campos:
        campos['role_id'] = campos.pop('funcao_id')
    return futebol.editar_atleta(ident, **campos)


@app.delete('/atletas/{ident}', status_code=204, tags=['Atletas'])
def excluir_atleta(ident: IdRota):
    futebol.excluir_atleta(ident)
    return Response(status_code=204)


@app.post('/atletas/exclusao', response_model=list[ResultadoExclusao], tags=['Atletas'],
          description='Exclui individualmente os IDs livres; preserva vinculados. Pode haver sucesso parcial.')
def excluir_atletas(dados: ExclusaoMultipla):
    resultados = []
    for ident in dict.fromkeys(dados.ids):
        try:
            futebol.excluir_atleta(ident)
        except ValueError as erro:
            resultados.append(dict(id=ident, excluido=False, motivo=str(erro)))
        except SQLAlchemyError:
            resultados.append(dict(id=ident, excluido=False, motivo='Falha no banco; exclusão não confirmada.'))
        else:
            resultados.append(dict(id=ident, excluido=True))
    return resultados


@app.get('/posicoes', response_model=list[ReferenciaResposta], tags=['Referências'])
def listar_posicoes():
    return [dict(id=ident, nome=nome) for ident, nome in futebol.referencias(Position)]


@app.get('/funcoes', response_model=list[ReferenciaResposta], tags=['Referências'])
def listar_funcoes():
    return [dict(id=ident, nome=nome) for ident, nome in futebol.referencias(Role)]


def resposta_time(time):
    return dict(id=time['id'], nome=time['nome'],
                atletas=[dict(id=ident, nome=nome) for ident, nome in time['membros']])


@app.get('/times', response_model=list[TimeResposta], tags=['Times'])
def listar_times():
    return [resposta_time(t) for t in futebol.consultar_times()]


@app.get('/times/{ident}', response_model=TimeResposta, tags=['Times'])
def consultar_time(ident: IdRota):
    return resposta_time(futebol.consultar_times(time_id=ident)[0])


@app.delete('/times/{ident}', status_code=204, tags=['Times'],
            description='Exclui o time e seus vínculos com atletas. Times ligados a partidas retornam 409. Os atletas são preservados.')
def excluir_time(ident: IdRota):
    futebol.excluir_time(ident)
    return Response(status_code=204)


@app.post('/times/sorteio', response_model=SorteioResposta, status_code=201, tags=['Times'])
def sortear_times(dados: SorteioEntrada):
    times = []
    for ident, nome, atletas, resumo in futebol.sortear_times(dados.atleta_ids, dados.nomes):
        times.append(dict(id=ident, nome=nome,
                     atletas=[dict(id=i, nome=n) for i, n in zip(resumo['ids'], atletas)],
                     rating_total=resumo['total'],
                     rating_medio=round(resumo['total'] / resumo['quantidade'], 1),
                     sem_rating=resumo['sem_rating']))
    return dict(times=times, diferenca=round(abs(times[0]['rating_total'] - times[1]['rating_total']), 1))


def resposta_partida(partida):
    return dict(id=partida['id'], data=partida['data'].date() if partida['data'] else None,
                times=partida['times'], avaliacoes=partida['avaliacoes'])


@app.get('/partidas', response_model=list[PartidaResposta], tags=['Partidas'])
def listar_partidas():
    return [resposta_partida(p) for p in futebol.consultar_partidas()]


@app.get('/partidas/{ident}', response_model=PartidaResposta, tags=['Partidas'])
def consultar_partida(ident: IdRota):
    return resposta_partida(futebol.consultar_partidas(ident)[0])


@app.delete('/partidas/{ident}', status_code=204, tags=['Partidas'],
            description='Exclui a partida, seus placares e avaliações. Recalcula os ratings dos avaliados. Preserva times e atletas.')
def excluir_partida(ident: IdRota):
    futebol.excluir_partida(ident)
    return Response(status_code=204)


@app.get('/partidas/{ident}/times', response_model=list[TimeResposta], tags=['Partidas'])
def times_da_partida(ident: IdRota):
    return [resposta_time(t) for t in futebol.consultar_times(partida_id=ident)]


@app.post('/partidas', response_model=PartidaResposta, status_code=201, tags=['Partidas'])
def registrar_partida(dados: PartidaCadastro):
    ident = futebol.registrar_partida(dados.time1_id, dados.time2_id, dados.gols1, dados.gols2,
                                      datetime.combine(dados.data, time.min))
    return resposta_partida(futebol.consultar_partidas(ident)[0])


@app.put('/partidas/{partida_id}/avaliacoes/{atleta_id}', response_model=AtletaResposta, tags=['Avaliações'])
def avaliar_atleta(partida_id: IdRota, atleta_id: IdRota, dados: AvaliacaoEntrada):
    return futebol.avaliar_atleta(partida_id, atleta_id, dados.nota)
