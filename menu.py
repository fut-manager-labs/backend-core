# cadastro da lista
lista_fut = [] 

def cadastrar():
    while True:
        resp = input("Deseja inserir um atleta? S ou N ").upper()
        
        if resp == "S":
            nome = input("Digite o nome do atleta: ").upper()
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
        print("\nMenu de sorteio do futebol semanal \n \n1. Cadastrar\n2. Listar\n3. Excluir atleta\n4. Sair\n ")

        opcao = int(input("Selecione a opção desejada: "))

        if opcao == 1:
            cadastrar()

        elif opcao == 2:
            listar()

        elif opcao == 3:
            deletar()

        elif opcao == 4:
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
    deletar_fut = str(input("Digite o nome que você quer remover: ")).upper().strip()

    if not lista_fut:
        print("A lista está vazia, não há o que remover ")

    elif deletar_fut not in lista_fut:
        print("Esse atleta não está na lista! ")

    else:
        lista_fut.remove(deletar_fut)
        print("Atleta removido. Veja como ficou a lista: ")
        listar()


menu()