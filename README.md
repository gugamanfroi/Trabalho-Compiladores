# Trabalho Compiladores (Interpretador/Processador de Aritmética em Python)

Este repositório conterá uma aplicação web desenvolvida para o processamento e avaliação de expressões aritméticas.  
Por enquanto, a aplicação mostra apenas o texto "Hello, World!" na tela.

---

##  Escolha da Linguagem e Subconjunto

* **Linguagem:** **Python**
* **Subconjunto:** **Aritmética Básica e Expressões Numéricas** (operações de adição, subtração, multiplicação e divisão).

### Justificativa da Escolha
Python oferece uma sintaxe direta que simplifica a implementação da lógica de análise e processamento. O subconjunto aritmético foi definido por constituir a base dos compiladores e interpretadores.

---

## Pré-requisitos

Para executar o projeto localmente, é necessário possuir instalado na máquina:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/).
* [Git](https://git-scm.com/).

---

## Como Inicializar e Encerrar o Projeto

### Inicialização
Siga os passos abaixo para baixar e rodar a aplicação em sua máquina:

Clone este repositório:  
git clone [https://github.com/gugamanfroi/Trabalho-Compiladores.git](https://github.com/gugamanfroi/Trabalho-Compiladores.git)

Acesse a pasta do projeto:  
cd Trabalho-Compiladores

Certifique-se de que o Docker esteja em execução e rode o comando do Docker Compose para construir e subir os contêineres:  
docker compose up --build

Após a inicialização dos serviços, abra o seu navegador e acesse a aplicação pelo endereço:  
http://localhost:8080

### Encerramento
Para interromper a aplicação e liberar os recursos do ambiente:

No terminal em que o Docker Compose está sendo executado, pressione:  
Ctrl + C

Para remover completamente os contêineres e redes criadas pelo Docker, execute:  
docker compose down
