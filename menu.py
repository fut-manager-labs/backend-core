# Lista vai ter que salvar dicionarios. chaves: jogador, posicao FEITO
# Dividir a lista em 2, mesmo se forem número impares FEITO
# Nenhum time não pode ficar sem goleiro
# Divisão deve ser aleatória FEITO
# Depois divisão tem que por cada time em sua própria lista, com as posições também
# Verificar se posição existe (exemplo: se digitar 'teste' não pode entrar) -> criar lista de posições
# Opção de listar ambos times ou só um dos times

# cadastro da lista

import random

lista_fut = []

def cadastrar():
    while True:
        resp = input("Deseja inserir um atleta? S ou N ").upper().strip()
        
        if resp == "S":
            nome = str(input("Digite o nome do atleta: ").upper().strip())
            posicao = int(input("Digite 1 para goleiro e 2 para jogador de linha: ").strip())

            posicao_string = str(posicao)

            posicoes = {'1': 'GOLEIRO', '2': 'LINHA'}
            
            atleta = {"Nome": nome, "Posicao": posicoes[posicao_string]}
            
            lista_fut.append(atleta)

            print("Atleta cadastrado! ")

        elif resp == "N":
            break

        else:
            print("Resposta inválida, responda com S ou N ")

# listagem da lista
def listar():
    if not lista_fut:
        print("A lista está vazia!")
    else:
        for atleta in lista_fut:
            print(f"Nome: {atleta['Nome']} | Posição: {atleta['Posicao']}")


def menu():
    while True:
        print("\nMenu de sorteio do futebol semanal \n \n1. Cadastrar\n2. Listar\n3. Excluir atleta\n4. Criar times\n5. Sair\n ")

        opcao = int(input("Selecione a opção desejada: "))

        if opcao == 1:
            cadastrar()

        elif opcao == 2:
            listar()

        elif opcao == 3:
            deletar()

        elif opcao == 4:
            criar_times(lista_fut)

        elif opcao == 5:
            sair = str(input("Digite S para confirmar: ")).upper().strip()

            if sair == "S": # sair da lista
                print("Obrigado, volte sempre! ")
                exit()

            else:
                continue

        else:
            print("Digite uma opção válida ")
            continue

def deletar():
    deletar_fut = input("Digite o nome que você quer remover: ").upper().strip()

    if not lista_fut:
        print("A lista está vazia, não há o que remover.")

    else:
        for atleta in lista_fut:
            if atleta["Nome"] == deletar_fut:
                lista_fut.remove(atleta)
                print("Atleta removido. Veja como ficou a lista:")
                listar()
                return

        print("Esse atleta não está na lista!")

def dividir_ao_meio(lista_fut):
    meio = len(lista_fut) // 2
    return lista_fut[:meio], lista_fut[meio:]

def criar_times(lista_fut):
    goleiros = []
    jogadores = []

    for atleta in lista_fut:
        if atleta['Posicao'] == "GOLEIRO":
            goleiros.append(atleta)
        else:
            jogadores.append(atleta)

    random.shuffle(goleiros)
    random.shuffle(jogadores)

    time_1 = [goleiros[0]]
    time_2 = [goleiros[1]]
    
    jogadores_time_1, jogadores_time_2 = dividir_ao_meio(jogadores)
    time_1.extend(jogadores_time_1)
    time_2.extend(jogadores_time_2)
    
    print(f"Time 1: {time_1}")
    print(f"Time 2: {time_2}")


menu()