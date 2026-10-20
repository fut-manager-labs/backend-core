"""Mapeamento das oito tabelas existentes em fut_manager."""
from sqlalchemy import ForeignKey, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import DOUBLE
from sqlalchemy.orm import mapped_column, relationship

from db import Base


class Position(Base):
    __tablename__ = "positions"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_title = mapped_column(String(100), nullable=False)


class Role(Base):
    __tablename__ = "roles"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name = mapped_column(String(100), nullable=False)


class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    username = mapped_column(String(100), nullable=False)
    role_id = mapped_column(Integer, ForeignKey("roles.id", name="fk_users_roles"), nullable=True)
    created_at = mapped_column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP"))
    rating = mapped_column(DOUBLE, nullable=True)
    current_position_id = mapped_column(Integer, ForeignKey("positions.id", name="fk_users_current_position"), nullable=True)
    last_position_id = mapped_column(Integer, ForeignKey("positions.id", name="fk_users_last_position"), nullable=True)
    role = relationship("Role")
    current_position = relationship("Position", foreign_keys=[current_position_id])
    last_position = relationship("Position", foreign_keys=[last_position_id])


class Team(Base):
    __tablename__ = "teams"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name = mapped_column(String(100), nullable=True)
    created_at = mapped_column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP"))


class TeamPlayer(Base):
    __tablename__ = "team_players"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id = mapped_column(Integer, ForeignKey("teams.id", name="fk_team_players_team"), nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id", name="fk_team_players_user"), nullable=False)
    team = relationship("Team")
    user = relationship("User")


class MatchHistory(Base):
    __tablename__ = "match_history"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_date = mapped_column(TIMESTAMP, nullable=True)


class MatchTeam(Base):
    __tablename__ = "match_teams"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id = mapped_column(Integer, ForeignKey("match_history.id", name="fk_match_teams_match"), nullable=False)
    team_id = mapped_column(Integer, ForeignKey("teams.id", name="fk_match_teams_team"), nullable=False)
    goals = mapped_column(Integer, nullable=True, server_default=text("0"))
    match = relationship("MatchHistory")
    team = relationship("Team")


class PlayerMatchRating(Base):
    __tablename__ = "player_match_ratings"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id = mapped_column(Integer, ForeignKey("match_history.id", name="fk_player_match_ratings_match"), nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id", name="fk_player_match_ratings_user"), nullable=False)
    rating = mapped_column(DOUBLE, nullable=True)
    match = relationship("MatchHistory")
    user = relationship("User")
