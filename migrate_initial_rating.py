"""Adiciona a nota inicial sem modificar notas ou avaliações existentes."""
from sqlalchemy import inspect, text

from db import engine


def main():
    try:
        with engine.connect() as connection:
            colunas = {c['name'] for c in inspect(connection).get_columns('users')}
            if 'initial_rating' in colunas:
                print('Campo initial_rating já existe; nenhuma alteração necessária.')
                return
            connection.execute(text('ALTER TABLE users ADD COLUMN initial_rating DOUBLE NULL'))
            connection.commit()
            print('Campo initial_rating criado. Dados existentes preservados.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
