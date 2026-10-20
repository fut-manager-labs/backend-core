"""Contratos de entrada e saída da API de atletas."""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class AtletaCadastro(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    nome: str = Field(min_length=1, max_length=100, examples=['Gabriel'])
    posicao_id: int = Field(ge=0, description='ID da posição; 0 seleciona Linha (ID 6).', examples=[1])
    rating_inicial: float = Field(ge=0, le=10, allow_inf_nan=False, examples=[8.5])


class AtletaResposta(BaseModel):
    id: int
    nome: str
    posicao_id: int | None
    posicao: str
    funcao_id: int | None
    funcao: str
    posicao_anterior: str = Field(validation_alias='anterior')
    rating: float | None = Field(validation_alias='nota')
    rating_inicial: float | None = Field(validation_alias='nota_inicial')
    criado_em: datetime | None

    @field_serializer('rating', 'rating_inicial')
    def exibir_nota(self, nota: float | None):
        return round(nota, 1) if nota is not None else None


Id = Annotated[int, Field(gt=0)]
Nome = Annotated[str, Field(min_length=1, max_length=100)]


class Entrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class AtletaEdicao(Entrada):
    nome: Nome | None = None
    posicao_id: Annotated[int, Field(ge=0)] | None = None
    funcao_id: Id | None = None

    @model_validator(mode='after')
    def validar_campos(self):
        if not self.model_fields_set:
            raise ValueError('Informe ao menos um campo para editar.')
        for campo in ('nome', 'posicao_id'):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f'{campo} não pode ser nulo.')
        return self


class ExclusaoMultipla(Entrada):
    ids: list[Id] = Field(min_length=1)


class ResultadoExclusao(BaseModel):
    id: int
    excluido: bool
    motivo: str | None = None


class ReferenciaResposta(BaseModel):
    id: int
    nome: str


class MembroResposta(BaseModel):
    id: int
    nome: str


class TimeResposta(BaseModel):
    id: int
    nome: str | None
    atletas: list[MembroResposta]


class SorteioEntrada(Entrada):
    atleta_ids: list[Id] = Field(min_length=2, description='IDs dos participantes; não repita IDs.')
    nomes: list[Nome] = Field(min_length=2, max_length=2, examples=[['Azul', 'Branco']])


class TimeSorteado(TimeResposta):
    rating_total: float
    rating_medio: float
    sem_rating: list[str]


class SorteioResposta(BaseModel):
    times: list[TimeSorteado]
    diferenca: float


class PartidaCadastro(Entrada):
    time1_id: Id
    time2_id: Id
    gols1: int = Field(ge=0)
    gols2: int = Field(ge=0)
    data: date = Field(examples=['2026-10-19'])


class PlacarResposta(BaseModel):
    id: int
    nome: str | None
    gols: int | None


class AvaliacaoResposta(BaseModel):
    atleta_id: int
    nome: str
    nota: float | None

    @field_serializer('nota')
    def exibir_nota(self, nota):
        return round(nota, 1) if nota is not None else None


class PartidaResposta(BaseModel):
    id: int
    data: date | None
    times: list[PlacarResposta]
    avaliacoes: list[AvaliacaoResposta]


class AvaliacaoEntrada(Entrada):
    nota: float = Field(ge=0, le=10, allow_inf_nan=False, examples=[8.5])
