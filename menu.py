# cadastro da lista
lista_fut = [] 

def cadastrar():
    while True:
        resp = input("Deseja inserir um atleta? S ou N ").upper()
        
        if resp == "S":
            nome = input("Digite o nome do atleta: ")
            lista_fut.append(nome)

        elif resp == "N":
            break

        else:
            print("Resposta inválida, responda com S ou N ")

# listagem da lista
def listar():
    print(lista_fut)

def menu():
    while True:
        print("Menu de sorteio do futebol semanal \n \n1. Cadastrar\n2. Listar\n3. Sair\n ")

        opcao = int(input("Selecione a opção desejada: "))

        if opcao == 1:
            cadastrar()

        elif opcao == 2:
            listar()

        elif opcao == 3:
            sair = str(input("Digite S para confirmar: ")).upper()

            if sair == "S": # sair da lista
                print("Obrigado, volte sempre! ")
                exit()

            else:
                continue

        else:
            print("Digite uma opção válida ")
            continue

menu()