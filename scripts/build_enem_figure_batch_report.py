#!/usr/bin/env python3
"""Gera data/audit/batch-NN-review.json para lotes de questões COM FIGURA (recorte original do PDF oficial).

Cada questão do lote é uma região única do caderno azul regular (cabeçalho "QUESTÃO n" até o fim da coluna), com
cinco alternativas A–E em texto, cuja identidade foi resolvida pelo ITENS_PROVA oficial. O aluno vê o recorte
original (apresentação `composition`, com o comando e as alternativas dentro da imagem); o texto da camada do PDF
fica como apoio (inclui rótulos das figuras). A caixa do recorte é a união de texto, imagens e desenhos da região,
sem as marcas escuras da margem da página. Gates automáticos por questão: nenhuma linha de texto cortada pela borda
do recorte, nenhum cabeçalho de outra questão dentro dele, resposta do ITENS_PROVA = gabarito do PDF.
A seleção está em data/audit/figure-batches/batch-NN-selection.json e foi conferida em folhas de contato.

Uso: python scripts/build_enem_figure_batch_report.py --batch 14 [--pdf-root data/enem-pdfs/oficiais]
"""
import argparse
import hashlib
import json
import re
import sys
from io import BytesIO
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_exam_candidates import candidates, raw_lines, clean, paragraphs  # noqa: E402
from publish_blue_candidates import record_digest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCALE = 2.5
PAD = 6.0
DESCRIPTION = "Recorte original da prova oficial (texto, figuras, comando e alternativas) para conferência. Abra para ampliar."
STRANGE = re.compile("[\ue000-\uf8ff\ufffd\x00-\x08\x0b-\x1f\x7f-\x9f]")
# Correções de texto conferidas na imagem do recorte, onde a camada de texto do PDF traz glifos privados de fórmulas
# (o texto é lido por leitores de tela quando a questão é exibida como recorte). id -> campos substituídos.
TEXT_OVERRIDES = {
    "2018_AZUL_D2_Q136": dict(
        enunciado="Com base nessas informações, o banco que transferiu a maior quantia via TED é o banco",
        texto_base_append=" Esta é a matriz obtida para essa análise: a matriz A é apresentada na imagem."),
    "2018_AZUL_D2_Q152": dict(enunciado="Esse conjunto é dado pelos pares ordenados (x ; y) ∈ ℕ × ℕ, tais que"),
    "2021_AZUL_D1_Q43": dict(enunciado="A sequência dos quadrinhos conjuga lirismo e violência ao"),
    "2021_AZUL_D2_Q130": dict(
        enunciado="O aroma do flavorizante derivado do ácido etanoico e que apresenta cadeia carbônica saturada é de",
        texto_base_append="Com o objetivo de proporcionar aroma e sabor a diversos alimentos, a indústria alimentícia se utiliza de flavorizantes. "
                          "Em geral, essas substâncias são ésteres, como as apresentadas no quadro (nome, fórmula e aroma)."),
    "2022_AZUL_D2_Q112": dict(enunciado="Qual é a tensão de ruptura da corda escolhida?"),
    "2021_AZUL_D2_Q116": dict(enunciado="O teste positivo será observado com o pesticida"),
    "2021_AZUL_D2_Q139": dict(enunciado="Com base nessas informações, a gerência decidiu incluir no cardápio o lanche de tipo"),
    "2021_AZUL_D2_Q147": dict(enunciado="As quatro letras mais frequentes, em ordem decrescente de frequência, do texto codificado são"),
    "2021_AZUL_D2_Q179": dict(
        enunciado="A quantidade de fantasias com materiais diferentes que podem ser produzidas é representada pela expressão",
        texto_base_append="Uma pessoa produzirá uma fantasia utilizando como materiais: 2 tipos de tecidos diferentes e 5 tipos distintos de pedras "
                          "ornamentais. Essa pessoa tem à sua disposição 6 tecidos diferentes e 15 pedras ornamentais distintas."),
    "2021_AZUL_D2_Q156": dict(
        enunciado="A expressão algébrica que representa as posições P(t) da massa m, ao longo do tempo, no gráfico, é",
        texto_base_append="Uma mola é solta da posição distendida conforme a figura. A figura à direita representa o gráfico da posição P (em cm) da massa m "
                          "em função do tempo t (em segundo) em um sistema de coordenadas cartesianas. Esse movimento periódico é descrito por uma expressão do "
                          "tipo P(t) = ± A cos (ωt) ou P(t) = ± A sen (ωt), em que A > 0 é a amplitude de deslocamento máximo e ω é a frequência, que se "
                          "relaciona com o período T pela fórmula ω = 2π/T. Considere a ausência de quaisquer forças dissipativas."),
    "2021_AZUL_D2_Q157": dict(
        enunciado="Qual região foi selecionada para o investimento da construtora?",
        texto_base_append="Uma construtora, pretendendo investir na construção de imóveis em uma metrópole com cinco grandes regiões, fez uma pesquisa sobre a "
                          "quantidade de famílias que mudaram de uma região para outra, de modo a determinar qual região foi o destino do maior fluxo de "
                          "famílias, sem levar em consideração o número de famílias que deixaram a região. Os valores da pesquisa estão dispostos em uma "
                          "matriz A = [aij], i, j ∈ {1, 2, 3, 4, 5}, em que o elemento aij corresponde ao total de famílias (em dezena) que se mudaram da "
                          "região i para a região j durante um certo período, e o elemento aii é considerado nulo, uma vez que somente são consideradas "
                          "mudanças entre regiões distintas. A seguir, está apresentada a matriz com os dados da pesquisa."),
    "2021_AZUL_D2_Q144": dict(enunciado="Qual é a média das idades, em ano, desses alunos?"),
}
GRAPHIC_ALTS = {k: f"Alternativa {k}: reprodução gráfica oficial." for k in "ABCDE"}
# Conteúdo completo transcrito da imagem (camada de texto com glifos privados de fórmulas ou alternativas fora de sequência).
def _full(enunciado, texto_base, alternativas=None):
    return dict(enunciado=enunciado, texto_base=texto_base, alternativas=alternativas or GRAPHIC_ALTS)


FULL_OVERRIDES = {
    "2017_AZUL_D2_Q136": _full(
        "A expressão que corresponde ao valor total pago pela quitação do empréstimo é",
        "Um empréstimo foi feito à taxa mensal de i %, usando juros compostos, em oito parcelas fixas e iguais a P. O devedor tem a possibilidade de "
        "quitar a dívida antecipadamente a qualquer momento, pagando para isso o valor atual das parcelas ainda a pagar. Após pagar a 5ª parcela, "
        "resolve quitar a dívida no ato de pagar a 6ª parcela.",
        {"A": "P[1 + 1/(1 + i/100) + 1/(1 + i/100)²]", "B": "P[1 + 1/(1 + i/100) + 1/(1 + 2i/100)]",
         "C": "P[1 + 1/(1 + i/100)² + 1/(1 + i/100)²]", "D": "P[1/(1 + i/100) + 1/(1 + 2i/100) + 1/(1 + 3i/100)]",
         "E": "P[1/(1 + i/100) + 1/(1 + i/100)² + 1/(1 + i/100)³]"}),
    "2022_AZUL_D2_Q108": _full(
        "A concentração de ácido tartárico no vinho analisado é mais próxima de:",
        "O ácido tartárico é o principal ácido do vinho e está diretamente relacionado com sua qualidade. Na avaliação de um vinho branco em produção, "
        "uma analista neutralizou uma alíquota de 25,0 mL do vinho com NaOH a 0,10 mol L−1, consumindo um volume igual a 8,0 mL dessa base. A reação "
        "para esse processo de titulação é representada pela equação química apresentada na imagem: ácido tartárico + 2 NaOH → sal de sódio + 2 H2O. "
        "Ácido tartárico (massa molar: 150 g mol−1).",
        {"A": "1,8 g L−1", "B": "2,4 g L−1", "C": "3,6 g L−1", "D": "4,8 g L−1", "E": "9,6 g L−1"}),
    "2022_AZUL_D2_Q115": _full(
        "A razão entre as variações de temperatura nas áreas concretada e alagada é mais próxima de",
        "A variação da incidência de radiação solar sobre a superfície da Terra resulta em uma variação de temperatura ao longo de um dia denominada "
        "amplitude térmica. Edificações e pavimentações realizadas nas áreas urbanas contribuem para alterar as amplitudes térmicas dessas regiões, em "
        "comparação com regiões que mantêm suas características naturais, com presença de vegetação e água, já que o calor específico do concreto é "
        "inferior ao da água. Assim, parte da avaliação do impacto ambiental que a presença de concreto proporciona às áreas urbanas consiste em "
        "considerar a substituição da área concretada por um mesmo volume de água e comparar as variações de temperatura devido à absorção da radiação "
        "solar nas duas situações (concretada e alagada). Desprezando os efeitos da evaporação e considerando que toda a radiação é absorvida, essa "
        "avaliação pode ser realizada com os seguintes dados: água, densidade de 1 000 kg/m³ e calor específico de 4,2 J/(g °C); concreto, densidade de "
        "2 500 kg/m³ e calor específico de 0,8 J/(g °C). ROMERO, M. A. B. et al. Mudanças climáticas e ilhas de calor urbanas. Brasília: UnB; ETB, 2019 (adaptado).",
        {"A": "1,0.", "B": "2,1.", "C": "2,5.", "D": "5,3.", "E": "13,1."}),
    "2022_AZUL_D2_Q116": _full(
        "O disjuntor adequado para a proteção dessa ducha é especificado por:",
        "O manual de uma ducha elétrica informa que seus três níveis de aquecimento (morno, quente e superquente) apresentam as seguintes variações de "
        "temperatura da água em função de sua vazão: com vazão de 3 L/min, ΔT de 10 °C (morno), 20 °C (quente) e 30 °C (superquente); com vazão de "
        "6 L/min, ΔT de 5 °C (morno), 10 °C (quente) e 15 °C (superquente). Utiliza-se um disjuntor para proteger o circuito dessa ducha contra "
        "sobrecargas elétricas em qualquer nível de aquecimento. Por padrão, o disjuntor é especificado pela corrente nominal igual ao múltiplo de 5 A "
        "imediatamente superior à corrente máxima do circuito. Considere que a ducha deve ser ligada em 220 V e que toda a energia é dissipada através "
        "da resistência do chuveiro e convertida em energia térmica transferida para a água, que apresenta calor específico de 4,2 J/(g °C) e densidade "
        "de 1 000 g/L.",
        {"A": "60 A", "B": "30 A", "C": "20 A", "D": "10 A", "E": "5 A"}),
    "2023_AZUL_D2_Q170": _full(
        "No caso analisado, qual seria a classificação do desempenho da empresa?",
        "Analisando as vendas de uma empresa, o gerente concluiu que o montante diário arrecadado, em milhar de real, poderia ser calculado pela "
        "expressão V(x) = x²/4 − 10x + 105, em que os valores de x representam os dias do mês, variando de 1 a 30. Um dos fatores para avaliar o "
        "desempenho mensal da empresa é verificar qual é o menor montante diário V0 arrecadado ao longo do mês e classificar o desempenho conforme as "
        "categorias apresentadas a seguir, em que as quantidades estão expressas em milhar de real. Ótimo: V0 ≥ 24. Bom: 20 ≤ V0 < 24. Normal: "
        "10 ≤ V0 < 20. Ruim: 4 ≤ V0 < 10. Péssimo: V0 < 4.",
        {"A": "Ótimo.", "B": "Bom.", "C": "Normal.", "D": "Ruim.", "E": "Péssimo."}),
    "2024_AZUL_D2_Q127": _full(
        "Ao repetir o experimento colocando um cilindro metálico oco entre as placas, o esquema que representa o formato das linhas de campo "
        "assumido pelo farelo é:",
        "Em um experimento de laboratório, duas barras metálicas, A e B, são carregadas com cargas opostas e imersas em óleo. Farelo de milho é jogado "
        "sobre o óleo e, após um certo tempo, o farelo assume o formato das linhas de campo elétrico entre as barras. A figura representa a vista "
        "superior desse experimento. ALMEIDA, M. A. T. Introdução às ciências físicas 2 — volume 4: módulo 4. Rio de Janeiro: Fundação CECIERJ, 2007 (adaptado)."),
    "2024_AZUL_D2_Q148": _full(
        "Os valores das constantes a e b são",
        "Uma caneca com água fervendo é retirada de um forno de micro-ondas. A temperatura T, em grau Celsius, da caneca, em função do tempo t, em "
        "minuto, pode ser modelada pela função T(t) = a + 80 b^t, representada no gráfico a seguir (temperatura da caneca em grau Celsius em função do "
        "tempo em minuto, de 0 a 20 minutos, decrescendo de 100 a 40).",
        {"A": "a = 20; b = log(0,5)", "B": "a = 100; b = 0,5", "C": "a = 20; b = (0,5)^(1/10)",
         "D": "a = 20; b = (40)^(1/10)/80", "E": "a = 20; b = 40"}),
    "2024_AZUL_D2_Q174": _full(
        "A projeção ortogonal, sobre o plano da base, da trajetória ABCDEF descrita pelo personagem é",
        "Em um jogo virtual para celular, um personagem pode percorrer trajetórias retilíneas voando ou se deslocando ao longo de paredes. Considere que "
        "o personagem descreve a trajetória ABCDEF, em que os pontos A, D e E estão em um plano paralelo ao que contém os pontos B e C, sendo esses dois "
        "planos ortogonais ao plano da base que contém o ponto F, conforme a figura."),
    "2017_AZUL_D2_Q121": _full(
        "Qual associação em série de pilhas fornece diferença de potencial, nas condições-padrão, suficiente para acender o LED azul?",
        "A invenção do LED azul, que permite a geração de outras cores para compor a luz branca, permitiu a construção de lâmpadas energeticamente mais "
        "eficientes e mais duráveis do que as incandescentes e fluorescentes. Em um experimento de laboratório, pretende-se associar duas pilhas em série "
        "para acender um LED azul que requer 3,6 volts para o seu funcionamento. Considere as semirreações de redução e seus respectivos potenciais "
        "mostrados no quadro: Ce4+ (aq) + e− → Ce3+ (aq), +1,61 V; Cr2O7 2− (aq) + 14 H+ (aq) + 6 e− → 2 Cr3+ (aq) + 7 H2O (l), +1,33 V; "
        "Ni2+ (aq) + 2 e− → Ni (s), −0,25 V; Zn2+ (aq) + 2 e− → Zn (s), −0,76 V."),
    "2017_AZUL_D2_Q152": _full(
        "Qual dos gráficos melhor descreverá a altura h do nível da água no Reservatório 1, em função do volume V de água no sistema?",
        "A água para o abastecimento de um prédio é armazenada em um sistema formado por dois reservatórios idênticos, em formato de bloco retangular, "
        "ligados entre si por um cano igual ao cano de entrada, conforme ilustra a figura. A água entra no sistema pelo cano de entrada no Reservatório 1 "
        "a uma vazão constante e, ao atingir o nível do cano de ligação, passa a abastecer o Reservatório 2. Suponha que, inicialmente, os dois "
        "reservatórios estejam vazios."),
    "2018_AZUL_D2_Q159": _full(
        "O formato da peça capaz de completar o cubo 4 × 4 × 4 é",
        "Minecraft é um jogo virtual que pode auxiliar no desenvolvimento de conhecimentos relacionados a espaço e forma. É possível criar casas, edifícios, "
        "monumentos e até naves espaciais, tudo em escala real, através do empilhamento de cubinhos. Um jogador deseja construir um cubo com dimensões "
        "4 × 4 × 4. Ele já empilhou alguns dos cubinhos necessários, conforme a figura. Os cubinhos que ainda faltam empilhar para finalizar a construção "
        "do cubo, juntos, formam uma peça única, capaz de completar a tarefa."),
    "2018_AZUL_D2_Q173": _full(
        "O gráfico que descreve a distância do ponto M ao ponto O, em função do tempo, entre t = 0 e tf, é",
        "Os guindastes são fundamentais em canteiros de obras, no manejo de materiais pesados como vigas de aço. A figura ilustra uma sequência de estágios "
        "em que um guindaste iça uma viga de aço que se encontra inicialmente no solo. Na figura, o ponto O representa a projeção ortogonal do cabo de aço "
        "sobre o plano do chão e este se mantém na vertical durante todo o movimento de içamento da viga, que se inicia no tempo t = 0 (estágio 1) e "
        "finaliza no tempo tf (estágio 3). Uma das extremidades da viga é içada verticalmente a partir do ponto O, enquanto que a outra extremidade "
        "desliza sobre o solo em direção ao ponto O. Considere que o cabo de aço utilizado pelo guindaste para içar a viga fique sempre na posição "
        "vertical. Na figura, o ponto M representa o ponto médio do segmento que representa a viga."),
    "2019_AZUL_D2_Q139": _full(
        "O gráfico que melhor descreve o valor P, em real, a ser pago por mês, em função do volume V de água consumido, em metro cúbico, é",
        "Uma empresa presta serviço de abastecimento de água em uma cidade. O valor mensal a pagar por esse serviço é determinado pela aplicação de "
        "tarifas, por faixas de consumo de água, sendo obtido pela adição dos valores correspondentes a cada faixa. Faixa 1: para consumo de até 6 m³, "
        "valor fixo de R$ 12,00; Faixa 2: para consumo superior a 6 m³ e até 10 m³, tarifa de R$ 3,00 por metro cúbico ao que exceder a 6 m³; Faixa 3: "
        "para consumo superior a 10 m³, tarifa de R$ 6,00 por metro cúbico ao que exceder a 10 m³. Sabe-se que nessa cidade o consumo máximo de água por "
        "residência é de 15 m³ por mês."),
    "2020_AZUL_D1_Q58": _full(
        "O modelo de planejamento urbano problematizado no texto é marcado pelo(a)",
        "O planejamento deixou de controlar o crescimento urbano e passou a encorajá-lo por todos os meios possíveis e imagináveis. Cidades, a nova "
        "mensagem soou em alto e bom som, eram máquinas de produzir riquezas; o primeiro e principal objetivo do planejamento devia ser o de azeitar a "
        "máquina. HALL, P. Cidades do amanhã: uma história intelectual do planejamento e do projeto urbanos no século XX. São Paulo: Perspectiva, 2016 (adaptado).",
        {"A": "primazia da gestão popular.", "B": "uso de práticas sustentáveis.", "C": "construção do bem-estar social.",
         "D": "soberania do poder governamental.", "E": "ampliação da participação empresarial."}),
    "2022_AZUL_D2_Q95": _full(
        "Considerando apenas o campo magnético por causa da corrente i, as respectivas configurações das bússolas nos pontos A, B e C serão",
        "O físico Hans C. Oersted observou que um fio transportando corrente elétrica produz um campo magnético. A presença do campo magnético foi "
        "verificada ao aproximar uma bússola de um fio conduzindo corrente elétrica. A figura ilustra um fio percorrido por uma corrente elétrica i, "
        "constante e com sentido para cima. Os pontos A, B e C estão num plano transversal e equidistantes do fio. Em cada ponto foi colocada uma bússola."),
    "2022_AZUL_D2_Q103": _full(
        "O esquema que representa corretamente todas as forças que atuam sobre a muleta quando ela atinge o ângulo crítico é:",
        "Tribologia é o estudo da interação entre duas superfícies em contato, como desgaste e atrito, sendo de extrema importância na avaliação de "
        "diferentes produtos e de bens de consumo em geral. Para testar a conformidade de uma muleta, realiza-se um ensaio tribológico, pressionando-a "
        "verticalmente contra o piso com uma força F, conforme ilustra a imagem, em que CM representa o centro de massa da muleta. Mantendo-se a força F "
        "paralela à muleta, varia-se lentamente o ângulo entre a muleta e a vertical, até o máximo ângulo imediatamente anterior ao de escorregamento, "
        "denominado ângulo crítico. Esse ângulo também pode ser calculado a partir da identificação dos pontos de aplicação, da direção e do sentido das "
        "forças peso (P), normal (N) e de atrito estático (fe)."),
    "2022_AZUL_D2_Q156": _full(
        "Após desdobrado o papel que restou na Figura 5, a figura plana que os estudantes obterão será",
        "O professor de artes orientou seus estudantes a realizarem a seguinte sequência de atividades: Dobrar uma folha de papel em formato quadrado duas "
        "vezes, em sequência, ao longo das linhas tracejadas, conforme ilustrado nas figuras 1 e 2, para obter o papel dobrado, conforme Figura 3. Em "
        "seguida, no papel dobrado da Figura 3, considerar o ponto R, sobre o segmento OM, sendo M o ponto médio do lado do quadrado original, de modo "
        "que OR = 1/4 OM, traçar um arco de circunferência de raio medindo 1/2 OM com centro no ponto R, obtendo a Figura 4. Por último, recortar o "
        "papel ao longo do arco de circunferência e excluir a parte que contém o setor circular, obtendo o papel dobrado, conforme Figura 5."),
    "2023_AZUL_D2_Q132": _full(
        "Durante o processo de resfriamento, os valores de pressão em relação à temperatura (P × T) são representados pelo gráfico:",
        "O manual de um automóvel alerta sobre os cuidados em relação à pressão do ar no interior dos pneus. Recomenda-se que a pressão seja verificada "
        "com os pneus frios (à temperatura ambiente). Um motorista, desatento a essa informação, realizou uma viagem longa sobre o asfalto quente e, em "
        "seguida, verificou que a pressão P0 no interior dos pneus não era a recomendada pelo fabricante. Na ocasião, a temperatura dos pneus era T0. Após "
        "um longo período em repouso, os pneus do carro atingiram a temperatura ambiente T. Durante o resfriamento, não há alteração no volume dos pneus e "
        "na quantidade de ar no seu interior. Considere o ar dos pneus um gás perfeito (também denominado gás ideal)."),
    "2024_AZUL_D2_Q161": _full(
        "O gráfico que descreve, em cada instante, a maior altura de coluna de água, dentre aquelas que vão sendo formadas ao longo do enchimento do "
        "tanque, é",
        "Um tanque, em formato de paralelepípedo reto retângulo, tem em seu interior dois anteparos verticais, fixados na sua base e em duas paredes "
        "opostas, sendo perpendiculares a elas, conforme a figura. Esses anteparos, de espessuras desprezíveis, estão instalados de maneira a dividir a "
        "base do tanque em três retângulos congruentes, tendo suas alturas iguais à metade e a um quarto da altura do tanque. O tanque é abastecido por "
        "uma entrada situada no teto, através de um duto que despeja água a uma vazão constante, sendo necessárias 12 horas para finalizar o seu enchimento."),
    "2024_AZUL_D2_Q168": _full(
        "O tipo de gráfico que descreve o comportamento oscilatório de um amortecedor aprovado nesse experimento é",
        "Projetistas de uma fábrica de amortecedores realizaram uma série de experimentos que produziram oscilações semelhantes ao comportamento do gráfico "
        "de uma senoide, para qualquer tipo de estrada. Cada experimento teve duração de 20 minutos, sendo os 9 primeiros minutos em superfície que simula "
        "uma rodovia asfaltada, e os 11 minutos restantes em superfície que simula uma estrada de chão. Para os amortecedores serem aprovados no "
        "experimento, exige-se que as amplitudes das ondas oscilatórias, em cada tipo de superfície, sejam constantes e, ainda, que a amplitude da "
        "oscilação do amortecedor no asfalto seja menor do que sua amplitude da oscilação na estrada de chão."),
    "2025_AZUL_D2_Q135": _full(
        "Os espectros de fotoluminescência do sensor no início e no final do tratamento estão esboçados no gráfico:",
        "A icterícia é uma doença que acomete recém-nascidos e pode ser tratada com um método de fototerapia conhecido como banho de luz, que consiste na "
        "exposição do recém-nascido a uma fonte luminosa equipada com LEDs azuis. Para o monitoramento da dosagem dessa radiação, é utilizada a resposta "
        "óptica de um sensor constituído de materiais orgânicos que luminescem quando expostos à luz azul. Com o passar do tempo, essa radiação oxida os "
        "materiais do sensor, alterando sua coloração de vermelho-laranja para verde, o que indica o final do tratamento. O gráfico apresenta o espectro "
        "de fotoluminescência do sensor em função do comprimento de onda da luz emitida no início do tratamento, quando o sensor, colado na fralda do bebê "
        "(Figura 1), luminesce na região do vermelho-laranja (∼600 nm). A Figura 2 apresenta a evolução da coloração do sensor, mostrando que a frequência "
        "da luz emitida por ele aumenta em função do tempo de exposição à luz azul. SILVA, M. M. et al. Fabricação de sensor orgânico flexível para "
        "aplicação em terapia com luz azul. Tecnol. Metal. Mater. Miner., n. 3, jul.-set. 2011 (adaptado)."),
    "2025_AZUL_D2_Q138": _full(
        "A figura que apresenta as projeções ortogonais desse cubo sobre os três planos coordenados, após efetuar as movimentações descritas, é",
        "Em um jogo de computador, um cubo se encontra inicialmente posicionado conforme indicado na figura. Cada deslocamento efetuado por esse cubo se "
        "dá sempre em uma das direções definidas pelos três eixos coordenados. Ao se movimentar a partir da posição inicial, esse cubo se aproximou "
        "3 unidades do plano yz, se afastou 5 unidades do plano xz e se aproximou 4 unidades do plano xy."),
    "2025_AZUL_D2_Q169": _full(
        "O gráfico de linhas que representa a produção de soja dessa propriedade, em tonelada, nessas cinco safras é",
        "A produtividade de soja em uma área cultivada é a média da quantidade de sacas de 50 quilogramas que são produzidas por hectare. O quadro "
        "apresenta a área cultivada e a produtividade de soja em certa propriedade, ao longo de cinco safras, com períodos de um ano, de 2011 a 2016. "
        "Safras 11-12, 12-13, 13-14, 14-15 e 15-16: área cultivada (hectare) de 200, 220, 250, 250 e 200; produtividade (sacas de 50 kg por hectare) "
        "de 40, 30, 45, 45 e 50."),
    "2025_AZUL_D2_Q160": _full(
        "A expressão algébrica que representa a relação entre D e T é",
        "Um recipiente tem um formato que faz com que, ao ser enchido de água com uma vazão constante, a distância D da lâmina de água ao tampo da mesa, "
        "em centímetro, aumente em relação ao tempo T, em minuto, de acordo com uma função do tipo D = k + tg[p(T + m)], sendo os parâmetros k, p e m "
        "números reais, para T variando entre 0 e 4 minutos, conforme ilustrado na figura, na qual estão apresentadas assíntotas verticais da função "
        "tangente utilizada na definição de D.",
        {"A": "D = 2,5 + tg[30(T − (5 − 2π)/2)]", "B": "D = 4 + tg[30(T + 5/2)]", "C": "D = 4 + tg[2,5(T + (5 + 2π)/2)]",
         "D": "D = 30 + tg[(1/2)(T − 5)]", "E": "D = 30 + tg[(1/2)(T − 5/2)]"}),
}
WATERMARK = re.compile(r"^(ENEM\s*20\d\d\s*)+$")  # marca-d'água diagonal repetida da página (não é tinta da questão anterior)
HEADER = re.compile(r"^\s*Quest[ãa]o\s+(\d+)\s*$", re.I)


RECOVERY_PATH = ROOT / "data/audit/text-recovery-2021.json"
RECOVERY = json.loads(RECOVERY_PATH.read_text()) if RECOVERY_PATH.exists() else {"items": {}}


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


UNSAFE_OPT = re.compile(r"[A-Za-z]\d|\d[A-Za-z]|×|\^|=|[<>]|[\u2070-\u209f\u00b2\u00b3\u00b9]|\b[A-Z]\s[A-Z]\b")


def safe_alternativas(alts, flags):
    """Questões com fórmulas (sobrescritos e índices): a camada de texto achata expoentes e índices ('x2', '16o', 'C C 4 2'),
    e as alternativas aparecem como cartões na tela. Se algum texto for suspeito, as cinco ficam com o texto de apoio padrão
    (o recorte original mostra as alternativas corretas)."""
    if any(f.startswith("sobrescrito_ou_indice") for f in flags) and any(UNSAFE_OPT.search(t) for t in alts.values()):
        return {k: f"Alternativa {k}: reprodução gráfica oficial." for k in "ABCDE"}, True
    return alts, False


def replay_png(pdf, renders):
    """PNG gerado exatamente como o replay (documento novo + store_shrink antes do primeiro render), para que o hash bata:
    o cache de imagens do MuPDF faz o mesmo recorte variar de um processo/estado para outro."""
    from PIL import Image
    with fitz.open(pdf) as document:
        fitz.TOOLS.store_shrink(100)
        panels = []
        for r in renders:
            sc = r["scale"]
            pix = document[r["page"] - 1].get_pixmap(matrix=fitz.Matrix(sc, sc), clip=fitz.Rect(r["bbox"]), alpha=False)
            panels.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples).crop(tuple(r["pixel_trim"])))
    img = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)), "white")
    top = 0
    for p in panels:
        img.paste(p, (0, top)); top += p.height
    buf = BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue(), img.size


def content_rect(page, rect):
    """União de texto, imagens e desenhos da região (sem marcas escuras da margem e sem a barra do cabeçalho)."""
    boxes = []
    for blk in page.get_text("dict", clip=rect)["blocks"]:
        if blk.get("type") == 0:
            for ln in blk["lines"]:
                if "".join(s["text"] for s in ln["spans"]).strip():
                    boxes.append(fitz.Rect(ln["bbox"]))
    pw = page.rect.width
    for i in page.get_image_info():
        r = fitz.Rect(i["bbox"])
        if r.width < 40 and (r.x1 <= 30 or r.x0 >= pw - 30 or r.height > 600):
            continue  # faixa decorativa da margem da página (2024)
        if r.intersects(rect):
            boxes.append(r & rect)
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if not (r.intersects(rect) and r.width > 3 and r.height > 3) or (r.width > 200 and r.height < 16):
            continue
        if r.x1 <= 24 or r.x0 >= pw - 24:
            continue  # desenho dentro da faixa da margem
        f = d.get("fill")
        if f and all(0.28 <= c <= 0.33 for c in f) and (r.width < 35 or r.height < 35) and (r.x0 < 25 or r.x1 > page.rect.width - 25 or r.x0 < 0):
            continue  # marca escura da margem da página
        pr = page.rect
        if f and r.width < 60 and (r.x0 < pr.x0 or r.y0 < pr.y0 or r.x1 > pr.x1 or r.y1 > pr.y1):
            continue  # marca preenchida que sai da página (aba de margem)
        if r.x0 >= rect.x0 + 1 and r.width < 500:
            boxes.append(r & rect)
    if not boxes:
        return rect
    u = boxes[0]
    for b in boxes[1:]:
        u |= b
    return fitz.Rect(u.x0 - PAD, u.y0 - PAD, u.x1 + PAD, u.y1 + PAD) & rect


MARK = re.compile(r"^([A-E])(?:[\s\t]+\S.{0,14})?$")


def find_letters(lines):
    """Índices das linhas das letras A–E em sequência na mesma coluna (ou None)."""
    best = None
    for col in sorted({round(x / 8) for _, x in lines}):
        seq = [(i, MARK.match(t).group(1)) for i, (t, x) in enumerate(lines) if round(x / 8) == col and MARK.match(t)]
        for start in range(len(seq)):
            want, idx = "A", []
            for i, letter in seq[start:]:
                if letter == want:
                    idx.append(i); want = chr(ord(want) + 1)
                    if want == "F":
                        break
            if len(idx) == 5:
                best = best or idx
                break
        if best:
            break
    return best


def graphic_content(doc, regions, number, lines=None):
    """Conteúdo de questões cujas alternativas são gráficas ou não saem como texto: o comando vem das linhas antes
    da primeira letra da sequência A–E (mesma coluna), e as alternativas recebem o texto de apoio padrão.
    Reprova (ValueError) se as cinco letras A–E não aparecerem em sequência na mesma coluna."""
    relative = None
    if lines is None:
        lines, relative = [], []
        for reg in regions:
            page = doc[reg["page"] - 1]
            got = [(clean(t.strip()), x) for t, x, z in raw_lines(page, fitz.Rect(reg["bbox"])) if t.strip()]
            left = min((x for _, x in got), default=0.0)
            lines += got
            relative += [(t, x - left) for t, x in got]  # recuo relativo à margem da região (colunas diferentes)
    head = next((i for i, (t, _) in enumerate(lines[:3]) if HEADER.match(t)), None)
    if head is not None:
        lines = lines[head + 1:]  # descarta ruído antes do cabeçalho "Questão n"
        if relative is not None:
            relative = relative[head + 1:]
    best = find_letters(lines)
    if not best and relative is not None and len(regions) > 1:  # A–E espalhadas em colunas/páginas diferentes da mesma questão
        lines = relative
        best = find_letters(lines)
    if not best:
        raise ValueError("letras A–E não encontradas em sequência na mesma coluna")
    stem = " ".join(t for t, _ in lines[:best[0]]).strip()
    stem = re.sub(r"\s+", " ", stem)
    if not stem:
        raise ValueError("comando vazio")
    return dict(enunciado=stem, texto_base="", alternativas={k: f"Alternativa {k}: reprodução gráfica oficial." for k in "ABCDE"})


def trim_to_header(page, crop, number):
    """Corta a caixa entre o fim da tinta da linha anterior (linha base + descendente) e o início da tinta do cabeçalho
    'Questão n' quando o fim da questão anterior fica colado nele (as caixas das linhas se sobrepõem).
    Devolve (caixa, ok); ok é False quando a tinta das duas linhas se sobrepõe."""
    lines = []
    for blk in page.get_text("dict", clip=crop + (0, -30, 0, 0))["blocks"]:
        for ln in blk.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                sp = ln["spans"][0]
                lines.append((ln["bbox"], sp["origin"][1], sp["size"], t))
    head = next(((b, o, z) for b, o, z, t in lines if (m := HEADER.match(t)) and int(m.group(1)) == number and b[1] > crop.y0 - 5), None)
    if head is None:
        return crop, True
    hb, ho, hz = head
    prev = [(b, o, z) for b, o, z, t in lines if b[1] < hb[1] and b[3] > hb[1] - 1.0 and not HEADER.match(t) and z > 3 and not WATERMARK.match(t)]
    if not prev:
        return crop, True
    prev_ink = max(o + 0.28 * z for b, o, z in prev)
    head_ink = ho - 0.78 * hz
    if prev_ink >= head_ink:
        return crop, False
    return fitz.Rect(crop.x0, max(crop.y0, (prev_ink + head_ink) / 2), crop.x1, crop.y1), True


def _lines(page, window):
    out = []
    for blk in page.get_text("dict", clip=window)["blocks"]:
        for ln in blk.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                sp = max(ln["spans"], key=lambda q: q["size"])
                out.append((fitz.Rect(ln["bbox"]), ln["spans"][0]["origin"][1], sp["size"], t))
    return out


def extend_cut_lines(page, crop, number):
    """Estende a caixa na vertical até conter a tinta (linha base + descendente) das linhas que a borda corta, sem entrar
    na tinta do cabeçalho de outra questão (corta no meio do vão entre elas)."""
    for _ in range(3):
        lines = _lines(page, crop + (-3, -3, 3, 40))
        heads = [(b, o, z) for b, o, z, t in lines if (m := HEADER.match(t)) and int(m.group(1)) != number]
        for b, o, z, t in lines:
            if b.height >= 40 or HEADER.match(t):
                continue
            ink_bottom, ink_top = o + 0.28 * z, o - 0.78 * z
            if o <= crop.y1 + 1 and ink_bottom > crop.y1 + 0.3:  # corta a base
                target = ink_bottom + 0.8
                below = [hb for hb, ho, hz in heads if hb.y0 > o - 2]
                if below:
                    head_ink = min(ho - 0.78 * hz for hb, ho, hz in heads if hb.y0 > o - 2)
                    if ink_bottom >= head_ink:
                        continue
                    target = min(target, (ink_bottom + head_ink) / 2)
                crop = fitz.Rect(crop.x0, crop.y0, crop.x1, max(crop.y1, target))
            if o >= crop.y0 - 1 and ink_top < crop.y0 - 0.3:  # corta o topo
                crop = fitz.Rect(crop.x0, ink_top - 0.8, crop.x1, crop.y1)
    return crop


def gates(page, crop, number):
    """Linhas de texto cortadas (pela tinta) e cabeçalhos de outras questões dentro do recorte."""
    problems = []
    for b, o, z, t in _lines(page, crop + (-3, -3, 3, 3)):
        if b.height >= 40:
            continue
        m = HEADER.match(t)
        if m and int(m.group(1)) != number:
            problems.append("cabeçalho de outra questão: " + t)
            continue
        if o <= crop.y1 + 1 and o + 0.28 * z > crop.y1 + 0.3 and o > crop.y0:
            problems.append("linha cortada na borda inferior: " + t[:30])
        if o >= crop.y0 - 1 and o - 0.78 * z < crop.y0 - 0.3 and o < crop.y1 and not HEADER.match(t):
            problems.append("linha cortada na borda superior: " + t[:30])
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--pdf-root", type=Path, default=ROOT / "data/enem-pdfs/oficiais")
    args = ap.parse_args()
    batch = args.batch
    selection = {tuple(map(int, k.split("-"))): v for k, v in json.loads((ROOT / f"data/audit/figure-batches/batch-{batch}-selection.json").read_text()).items()}
    out_path = ROOT / f"data/audit/batch-{batch}-review.json"
    exams = {(int(e["year"]), int(e["day"])): e for e in json.loads((ROOT / "data/enem-pdfs/manifest.json").read_text())["exams"]
             if e["application"] == "regular" and e["color"] == "azul"}
    ident = json.loads((ROOT / "data/audit/identity-resolution.json").read_text())["items"]
    manifest_ids = {e["id"] for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]}
    results, sources, failures = [], [], []
    for (year, day), numbers in sorted(selection.items()):
        ex = dict(exams[(year, day)])
        if "source_sha256" not in ex:  # 2024 D1: o inventário não traz as fontes; usa as já auditadas no manifesto de publicação
            ref = next(e for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]
                       if e["year"] == year and e["day"] == day and e.get("application") == "regular")
            ex.update(source_url=ref["source_url"], source_sha256=ref["source_sha256"],
                      answer_key_url=ref["answer_source_url"], answer_key_sha256=ref["answer_source_sha256"])
        pdf = args.pdf_root / f"{year}-regular-d{day}-azul.pdf"
        key = args.pdf_root / f"{year}-regular-d{day}-azul-gabarito.pdf"
        assert sha_bytes(pdf.read_bytes()) == ex["source_sha256"], pdf
        assert sha_bytes(key.read_bytes()) == ex["answer_key_sha256"], key
        source = dict(year=year, day=day, source_url=ex["source_url"], source_sha256=ex["source_sha256"],
                      answer_source_url=ex["answer_key_url"], answer_source_sha256=ex["answer_key_sha256"])
        sources.append(dict(source, source_file=pdf.name, key_file=key.name))
        cand = candidates(year, day)
        doc = fitz.open(pdf)
        for n in numbers:
            uid = f"{year}_AZUL_D{day}_Q{n:02d}"
            assert uid not in manifest_ids, uid
            c, r = cand[n], ident[uid]
            assert c["regions"], uid
            lang = r.get("lingua")  # posições de idioma (1–5 de LC): vale a versão em inglês, conferida pela seção do caderno
            answer = c["answer_by_language"][lang] if lang else c["answer"]
            assert r["tx_gabarito"] == answer == r["official_key"], f"identidade não corroborada: {uid}"
            if lang:
                from resolve_identity_idioma import section_language
                assert section_language(doc, c["regions"][0]) == lang, f"seção do caderno diferente do idioma: {uid}"
            src, rec = c["content"], RECOVERY["items"].get(uid)
            if rec:  # 2021: camada de texto do azul corrompida; texto recuperado de outros cadernos pelo CO_ITEM
                if rec["lacunas"] and not rec["transcricao_manual"]:
                    failures.append((uid, ["texto corrompido sem transcrição"])); continue
                src = rec["content"]
            if uid in FULL_OVERRIDES:  # conteúdo transcrito à mão e conferido na imagem do recorte (camada de texto inutilizável)
                src = FULL_OVERRIDES[uid]
            elif not (src and len(src["alternativas"]) == 5):
                try:
                    src = graphic_content(doc, c["regions"], n, lines=list(zip(map(clean, rec["text_lines"]), rec["line_x"])) if rec else None)
                except ValueError as e:
                    failures.append((uid, [str(e)])); continue
            alts, replaced = safe_alternativas(src["alternativas"], c["flags"])
            src = dict(src, alternativas=alts)
            fix = TEXT_OVERRIDES.get(uid, {})
            enun = fix.get("enunciado", src["enunciado"])
            base_text = (src["texto_base"] or "").replace("\x07", "") + fix.get("texto_base_append", "")  # \x07: marcador do travessão de diálogo
            if c.get("shared_prefix"):  # texto compartilhado que precede as questões: entra no texto de apoio, antes do texto próprio
                reg0 = c["regions"][0]
                pl = [(clean(t.strip()), x, z) for t, x, z in raw_lines(doc[reg0["page"] - 1], fitz.Rect(reg0["bbox"])) if t.strip()]
                pl = [(t, x, z) for t, x, z in pl if not re.fullmatch(r"\d{1,3}", t) and not t.startswith("Texto para as Quest")]
                base_text = (paragraphs(pl) + "\n\n" + base_text).strip()
            if any(STRANGE.search(v) for v in [enun, base_text, *src["alternativas"].values()]):
                failures.append((uid, ["glifo privado no texto"])); continue
            provisional = dict(enunciado=enun, texto_base=base_text,
                               alternativas=src["alternativas"],
                               metadados_visual=dict(contem_imagem=False, descricao_imagem=None, caminho_local_imagem=None))
            pending = dict(id_unico_sistema=uid, co_item=r["co_item"], ano=year, dia=day, cor_prova="AZUL", posicao_prova=n,
                           area_conhecimento=r["area"], gabarito_oficial=None, co_habilidade=r["co_habilidade"],
                           in_item_aban=r["in_item_aban"], conteudo=provisional, parametros_tri=None,
                           preview_status="REVIEW_TEXT", preview_unverified=True, scoring_enabled=False,
                           preview_warning="Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação.")
            from PIL import Image
            fitz.TOOLS.store_shrink(100)  # igual ao replay: o cache de imagens do MuPDF pode mudar o primeiro render
            texts, renders, panels, bad_all = [], [], [], []
            for k, reg in enumerate(c["regions"]):
                page = doc[reg["page"] - 1]
                rect = fitz.Rect(reg["bbox"])
                crop = content_rect(page, rect)
                if k == (1 if c.get("shared_prefix") else 0):
                    crop, ok_trim = trim_to_header(page, crop, n)
                    if not ok_trim:
                        bad_all.append("tinta da linha anterior sobreposta ao cabeçalho")
                crop = extend_cut_lines(page, crop, n)
                bad_all += gates(page, crop, n)
                texts.append(page.get_text(clip=rect))
                pm = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=crop, alpha=False)
                renders.append(dict(page=reg["page"], bbox=[round(v, 3) for v in crop], scale=SCALE, pixel_trim=[0, 0, pm.width, pm.height]))
                panels.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))
            if bad_all:
                failures.append((uid, bad_all)); continue
            text = "\n".join(rec["text_lines"]) if rec else "\n".join(texts)
            data, size = replay_png(pdf, renders)
            image = f"/images/verified/batch{batch}-{year}-azul-d{day}-q{n:03d}-source.png"
            content = dict(provisional, metadados_visual=dict(contem_imagem=True, descricao_imagem=DESCRIPTION, caminho_local_imagem=image))
            q = dict(pending, conteudo=content, gabarito_oficial=answer)
            digest = record_digest(q)
            results.append(dict(
                id=uid, year=year, day=day, number=n, application="regular", language=lang,
                regions=[dict(page=g["page"], bbox=g["bbox"], is_prefix=False) for g in c["regions"]],
                pending_row=pending, before_content=provisional, official_answer=answer, source=source,
                source_file=pdf.name, key_file=key.name, source_text=text, source_text_sha256=sha_bytes(text.encode()),
                status="APPROVED", classification="RECOVERABLE",
                decision="Recorte original da região da questão (texto, figuras, comando e alternativas), gabarito oficial e identidade resolvida; região conferida em folha de contato.",
                after_content=content, record_sha256=digest,
                presentation_metadata=dict(mode="composition", includes_command=True, source=image, source_sha256=sha_bytes(data),
                                           evidence=f"data/audit/batch-{batch}-review.json", record_sha256=digest),
                assets=dict(source=dict(image=image, sha256=sha_bytes(data), render=renders, width=size[0], height=size[1])),
                visual_review=dict.fromkeys(["text", "options", "graphics", "credits", "continuity", "answer"], True),
                identity_reconciliation=dict(
                    method="official ITENS_PROVA: the azul CO_PROVA whose answer sequence equals the official key (data/audit/identity-resolution.json)",
                    co_item=r["co_item"], co_prova=r["co_prova"], tx_gabarito=r["tx_gabarito"], official_answer=answer,
                    independent_item_csv="official Inep ITENS_PROVA (see data/audit/identity/sources.json)",
                    note="CO_ITEM não vem do fused (CO_PROVA azul diferente do caderno do PDF)."),
                parser_flags=c["flags"] + (["texto_recuperado_de_outros_cadernos"] if rec else []),
                text_recovery=dict(file="data/audit/text-recovery-2021.json", co_item=rec["co_item"], cadernos_usados=rec["cadernos_usados"],
                                   lacunas_transcritas=rec["lacunas"], linhas_por_origem=rec["linhas_por_origem"]) if rec else None,
                manual_text_overrides=sorted(fix) or None, options_replaced_by_placeholder=replaced))
    release_path = ROOT / "data/blue-published/questions.jsonl"
    lines = release_path.read_bytes().splitlines(keepends=True)
    prev = {json.loads(l)["id_unico_sistema"]: l for l in lines}
    assert not {r["id"] for r in results} & set(prev), "o lote só adiciona identificadores novos"
    report = dict(schema_version=1, batch=batch, examined=len(results), approved_before=len(prev), newly_approved=len(results),
                  approved_after=len(prev) + len(results), previous_catalog_sha256=sha_bytes(b"".join(lines)),
                  previous_lines_sha256={uid: sha_bytes(l) for uid, l in prev.items()}, sources=sources, results=results,
                  gate_failures=[dict(id=u, problemas=p) for u, p in failures],
                  limitations=["Questões com figura: o aluno vê o recorte original do PDF; o texto de apoio vem da camada de texto e inclui rótulos das figuras.",
                               "Parâmetros TRI permanecem nulos no registro; o carregador junta o TRI oficial pelo CO_ITEM resolvido.",
                               "A conferência visual foi feita por folhas de contato das regiões, não pixel a pixel."])
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(results), "questões →", out_path, "| gates reprovados:", len(failures))
    for u, p in failures:
        print(" ", u, p)


if __name__ == "__main__":
    main()
