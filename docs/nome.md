# Por que esse projeto se chama Prova dos Nove?

Porque existe um truque muito antigo para descobrir se uma conta está certa.
Ele é tão esperto que virou jeito de falar: quando alguém diz "essa é a prova
dos nove", está dizendo "esse é o teste de verdade".

Mas o truque tem uma falha. E é justamente por causa da falha que ele virou
nome deste projeto.

## O truque

Pegue uma conta de multiplicar:

**17 × 23 = 391**

Agora some os algarismos de cada número, até sobrar um só:

- 17 → 1 + 7 = **8**
- 23 → 2 + 3 = **5**
- 391 → 3 + 9 + 1 = 13 → 1 + 3 = **4**

Faça com os pedacinhos a mesma conta que você fez com os números grandes:

**8 × 5 = 40** → 4 + 0 = **4**

Deu 4 de um lado e 4 do outro. A conta fecha. 🎉

Se você tivesse escrito 381 por engano:

381 → 3 + 8 + 1 = 12 → 1 + 2 = **3**

Deu 3, mas o outro lado deu 4. A prova acusou o erro na hora — sem refazer a
multiplicação inteira.

Esse é o truque: **somar os algarismos** e comparar. É por isso que ele se
chama "tirar os noves fora": a cada soma, você está jogando fora pedaços de 9.

## Por que o 9?

Porque o nosso jeito de escrever números é feito de dez. Cada vez que você anda
uma casa para a esquerda, o número fica dez vezes maior. E dez é **nove mais
um**. Esse "mais um" que sobra é o que faz a soma dos algarismos cair sempre no
mesmo lugar que o número original, quando você divide por 9.

Traduzindo: o 9 é o único algarismo que não atrapalha a soma. Pode somar, pode
tirar, pode jogar fora — o resto não muda.

## A história

Ninguém sabe quem inventou. Sabe-se que a ideia é velha e viajou muito.

Há mais de 1.700 anos, matemáticos gregos já somavam algarismos assim — mas
usavam só para achar um número final, não para conferir contas. Quem teve a
ideia de usar como teste foi um matemático indiano, Aryabhata II, por volta do
ano 950. Um sábio persa, Avicena, aprendeu o método e o chamou de "método
hindu". Em 1202, um italiano chamado Fibonacci escreveu tudo num livro, o
*Liber Abaci*, e a ideia se espalhou pela Europa.

Séculos depois, ela chegou às escolas brasileiras e virou conteúdo de destaque
do ensino primário — gerações inteiras aprenderam a conferir contas assim. Hoje
ela saiu dos currículos, mas ficou na língua: "a prova dos nove" quer dizer "o
teste definitivo".

## A falha

Aqui está a parte divertida.

A prova dos nove **não pega todo erro**. Ela é cega para qualquer erro que seja
múltiplo de 9 — e o erro mais comum de todos é exatamente desse tipo: **trocar
dois algarismos de lugar**.

Olhe de novo:

**391** está certo.
**913** está errado.

Mas 9 + 1 + 3 = 13 → 4. Igualzinho. A prova dos nove olha para 913 e diz:
"tudo bem, pode passar". O erro mais bobo que existe passa batido pelo teste
que prometia ser definitivo.

E tem mais: um zero a mais ou a menos também engana a prova. `45` e `450` somam
9 nos dois casos.

## Por que esse nome, então?

Porque a lição vale para dados, não só para contas.

Uma conta que "fecha" ainda pode estar errada. Um número que parece razoável
ainda pode ser falso. A conferência que importa não é a que diz "passou" — é a
que mostra o caminho até a origem do número.

É isso que este projeto faz: cada número que aparece aqui tem que mostrar de
onde veio, de que ano e de que conta. Não basta parecer certo. Tem que dar para
conferir.

## Um desafio para você

1. Escolha um número grande, de três ou quatro algarismos.
2. Some os algarismos até sobrar um só. Anote.
3. Troque dois algarismos de lugar.
4. Some de novo.

Deu o mesmo resultado? Então você acabou de criar um erro que a prova dos nove
não consegue ver. Tente achar outro. Existem infinitos. 🕵️
