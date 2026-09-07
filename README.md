# Projeto `<Título em Português>`
# Project `<Title in English>`

> Equipe: `<Nome 1>`, `<Nome 2>`

## Slides

> Coloque aqui o link para o PDF da apresentação (pasta `assets/slides/`).

## Metodologia

O grafo de conhecimento é extraído em um pipeline baseado 100% em técnicas
clássicas de NLP (nenhum modelo de linguagem é usado nesta etapa):

```
cases.csv ──▶ pré-processamento ──▶ NER por gazetteer (MeSH) ──▶ extração de   ──▶ regras de   ──▶ grafo canônico
              (segmentação de       exato (Aho-Corasick) +        valores/unidades   relação        (nós + arestas)
              sentenças, regex)     fuzzy (Damerau-Levenshtein    (regex + lista
                                    + BK-tree) p/ Symptom/Exam/    de unidades)
                                    AnatomicalSite; exato só p/
                                    Diagnosis/Treatment
```

Pontos-chave da abordagem:

- **Fonte do vocabulário — MeSH (Medical Subject Headings)**: um único
  descriptor file público da NLM (`desc2025.xml`, sem necessidade de
  cadastro/licença, ao contrário de UMLS/SNOMED CT) filtrado por prefixo de
  `TreeNumber` gera 5 gazetteers (`references/vocabularies/*.csv`):
  Symptom (`C23`), Diagnosis (`C*` exceto `C23`), Exam (`E01`),
  Treatment/Drug (`D*` + `E02`), AnatomicalSite (`A*`). Cada descritor MeSH
  já vem com sinônimos prontos (*Entry Terms*), resolvendo a unificação de
  diferentes formas de escrever o mesmo conceito. Bônus: como
  `metadata.csv` já rotula os artigos com `major_mesh_terms`, dá pra
  validar as entidades extraídas contra essa anotação externa.
- **Dicionário enxuto**: cada descritor MeSH carrega ~8-9 Entry Terms, mas a
  maioria é grafia rara/histórica. Mantemos só os marcados
  `ConceptPreferredTermYN="Y"` — reduz o total de termos de ~265 mil pra
  ~61 mil (~4.3x menor) sem colapsar pra um nome só por descritor.
- **NER exato via Aho-Corasick**: mesmo já reduzido, dicionário desse
  tamanho (Treatment sozinho ainda tem ~27 mil sinônimos, vindos do ramo
  "Chemicals and Drugs" do MeSH) não escala com um `re.compile` por
  sinônimo contra cada sentença — trocamos por um autômato de Aho-Corasick
  por tipo de entidade, que casa todos os padrões em uma única varredura
  O(tamanho do texto).
- **NER fuzzy via Damerau-Levenshtein + BK-tree**, só para Symptom/Exam/
  AnatomicalSite: cobre pequena variação de escrita (ex. "heart-attack" vs
  "heart attack") com uma distância de edição normalizada pelo tamanho do
  termo. Usa a variante **irrestrita** (não OSA) do algoritmo, condição
  necessária pra poda de BK-tree ser válida (desigualdade triangular).
  Desativado para Diagnosis/Treatment: medido empiricamente que a BK-tree
  poda mal em dicionário médico de dezenas/centenas de milhares de termos
  (distâncias de edição concentradas em valores baixos e próximos entre
  si), tornando o fuzzy inviável nessa escala — mitigado pela cobertura já
  ampla de Entry Terms do MeSH nesses dois ramos.
- **Extração de valores/unidades por regex**: construída dinamicamente a
  partir de uma lista controlada de unidades (`units.txt`, sem fuzzy —
  erro aqui gera falso positivo fácil), reconhecendo também faixas de
  referência (`reference range X-Y`).

Trecho de código ilustrando a distância de edição usada no fuzzy match:

~~~python
def damerau_levenshtein(a: str, b: str) -> int:
    """Distância irrestrita (Lowrance-Wagner) — necessária pra poda de
    BK-tree ser válida; a variante OSA não satisfaz desigualdade triangular.
    """
    ...
~~~

Código completo em [`src/kg_extraction/`](src/kg_extraction/) ([instruções de instalação/execução](src/README.md)).

## Trabalhos Estudados

> Debater brevemente outros trabalhos/abordagens pesquisados pela equipe
> (ex.: outras extrações de KG a partir de casos clínicos, uso de UMLS/cTAKES/
> MetaMap para linking terminológico, etc.).

## Modelo Lógico

O grafo é representado em duas tabelas (esquema livre, mantendo a ideia de
nós + arestas do enunciado):

**Nós** (`node_id`, `case_id`, `type`, `label`, `attributes`) — tipos usados:
`Patient`, `History`, `Symptom`, `Exam`, `ExamResult`, `Finding`,
`Treatment`, `AnatomicalSite`, `Unit`.

**Arestas** (`edge_id`, `case_id`, `source_id`, `target_id`, `relation`,
`attributes`) — relações usadas: `HAS_HISTORY`, `PRESENTS_WITH`,
`UNDERWENT_EXAM`, `UNDERWENT_TREATMENT`, `HAS_RESULT`, `HAS_UNIT`,
`DIAGNOSED_WITH`, `SUPPORTS`, `TREATED_BY`, `CONFIRMS`/`EXCLUDES`/`REVEALS`,
`LOCATED_IN`/`TARGETS`/`PERFORMED_ON` (ligam `AnatomicalSite` a
Diagnosis/Finding, Treatment e Exam por co-ocorrência na mesma sentença —
mesma regra de proximidade do `SUPPORTS`/`TREATED_BY`, sem isso o
`AnatomicalSite` ficava totalmente isolado no grafo). `Unit` é
compartilhado entre casos (mesma unidade em casos diferentes aponta pro
mesmo nó). Valor e faixa de referência ficam como texto em
`attributes` do `ExamResult`, não como nós/arestas próprios — decomposição
mínima o suficiente pra responder as análises propostas, sem inflar o
grafo.

> Decisão: não modelamos `VocabConcept`/`SAME_AS` (link de cada entidade
> pro seu código MeSH) — testado e removido: quase dobrava o nº de nós/
> arestas do grafo (~30%/45% do total) sem agregar valor pra um grafo
> básico. O código MeSH de cada match ainda existe internamente (usado só
> pra dedupe do gazetteer), só não vira nó.

> Coloque aqui a imagem do modelo lógico de propriedades da equipe (ver
> [modelo de base](https://docs.google.com/presentation/d/10RN7bDKUka_Ro2_41WyEE76Wxm4AioiJOrsh6BRY3Kk/edit?usp=sharing)),
> em `assets/images/modelo-logico-grafos.png`.

## Análises que podem ser realizadas

- Cruzar `major_mesh_terms` de `metadata.csv` com os `Diagnosis`/`Symptom`
  extraídos (ambos vêm de MeSH) para validar a extração contra uma
  anotação externa já existente no dataset.
- Medir cobertura do gazetteer (quantas sentenças não geraram nenhuma
  entidade) para orientar onde a taxonomia MeSH deixa lacunas (ex.: exames
  específicos que o MeSH não descreve como procedimento isolado).
- Comparar precisão de Symptom vs. Diagnosis: o ramo `C23` do MeSH inclui
  uma subárvore de "Chronic Disease" que cross-lista doenças específicas,
  gerando classificações de Diagnosis como Symptom — quantificar o
  impacto disso na amostra.
- Identificar quais `Exam` mais frequentemente co-ocorrem com cada
  `Diagnosis`, sugerindo protocolos diagnósticos recorrentes.

> Complementar com as análises efetivamente realizadas pela equipe.

## Ferramentas

- **Python** (pandas) para o pipeline de extração.
- Técnicas clássicas de NLP implementadas from-scratch: tokenização/
  normalização por regex, gazetteer com Aho-Corasick (exato) e
  Damerau-Levenshtein + BK-tree (fuzzy), regex de valores/unidades, regras
  de relação — sem bibliotecas de NER estatístico/neural, conforme
  exigido nesta etapa.
- **MeSH (NLM)** como fonte única de vocabulário controlado — público,
  sem necessidade de licença/cadastro (ao contrário de UMLS/SNOMED CT).
- Estrutura de projeto: [Cookiecutter Data Science](https://drivendata.github.io/cookiecutter-data-science/) (simplificada).

## Resultados

Pipeline completo rodado sobre os **56 casos / 50 artigos** da amostra
oficial (`data/raw/multicare/cases.csv` — o enunciado cita "246 casos", mas
o arquivo de amostra distribuído junto ao enunciado tem 56 linhas reais;
`metadata.csv` bate certinho com "50 artigos"). Tempo total: ~2 minutos.

**Nós**: AnatomicalSite 399, Exam 274, Treatment 249, Symptom 237,
Diagnosis 137, ExamResult 91, Finding 89, Patient 56, History 43,
Unit 18 — total 1593 (média de 28 nós/caso).

**Arestas**: UNDERWENT_EXAM 274, UNDERWENT_TREATMENT 249, PRESENTS_WITH 237,
PERFORMED_ON 216, TARGETS 197, TREATED_BY 179, LOCATED_IN 173,
DIAGNOSED_WITH 137, REVEALS 93, HAS_RESULT 91, HAS_UNIT 91, SUPPORTS 58,
HAS_HISTORY 43, CONFIRMS 15, EXCLUDES 4 — total 2057.

> Incluir capturas de tela da aplicação de visualização (`assets/images/`).

### Limitações conhecidas (taxonomia MeSH)

Usar MeSH como fonte única de vocabulário (ao invés de UMLS/SNOMED CT/
RxNorm combinados) simplificou bastante a implementação, mas a árvore do
MeSH não foi desenhada pra bater 1:1 com nossos 5 tipos de entidade.
Achados concretos rodando na amostra real, deixados como limitação
conhecida em vez de mais heurística de código:

- **Ramo `C23` (Signs and Symptoms) é mais largo que "sintoma"**: tem uma
  subárvore `Chronic Disease` que lista doenças crônicas específicas (ex.
  "Pancreatitis, Chronic") como se fossem sintomas. Algumas entidades que
  deveriam ser `Diagnosis` saem classificadas como `Symptom`.
- **Corpos/fluidos ficam sob `AnatomicalSite`**: "serum", "tail" (do
  ramo zoológico/anatômico geral do MeSH) casam tecnicamente certo com a
  árvore, mas fora do sentido clínico que o texto pretendia.
- **Cobertura de procedimento (`Exam`) tem buracos**: nem todo exame comum
  em texto clínico é um descritor MeSH isolado no ramo `E01` (ex.
  "Endoscopic ultrasound" sozinho não bate — só existe composto com
  "-Guided Fine Needle Aspiration"). Sub-reporta exames quando o MeSH não
  tem entrada específica.
- **Ambiguidade residual em `Treatment`**: a reclassificação Treatment→Exam
  (`relations.py`) resolve o caso claro de substância medida com valor
  logo depois ("Hemoglobin 9 g/dL"), mas quando o valor não está adjacente
  no texto a substância continua classificada como Treatment mesmo sendo
  um biomarcador, não uma droga administrada.
- **Termos genéricos além dos 3 já filtrados** (`EXCLUDED_MESH_UI` em
  `config.py`): é uma lista curada à mão a partir do que apareceu na
  amostra — não é exaustiva, outros casos de palavra comum colidindo com
  descritor MeSH genérico podem aparecer em texto novo.
- **`AnatomicalSite` só liga a algo quando co-ocorre na mesma sentença**
  com Diagnosis/Exam/Treatment (`LOCATED_IN`/`PERFORMED_ON`/`TARGETS`) —
  ~49% dos 399 nós desse tipo na amostra ainda ficam sem aresta (menção
  solta, sem outra entidade na mesma sentença). Mesma limitação inerente
  do `SUPPORTS`/`TREATED_BY`: regra de proximidade textual, não relação
  semântica de verdade.

## Como Modelos de Linguagem foram Usados

Conforme o enunciado, **nenhum LLM foi usado na etapa de extração do grafo**
(NER, extração de valores e extração de relações são 100% baseadas em
regras, dicionários MeSH e regex — ver `src/kg_extraction/features/`).

Modelos de linguagem foram usados apenas para:
- Apoiar o design e a implementação da **aplicação web de visualização**,
  que o enunciado explicitamente libera para uso de IA;
- `<a equipe deve completar aqui outros usos, ex.: revisão de texto, geração
  de rascunho dos slides, etc.>`

## Referências Bibliográficas

- Nievas Offidani, M., Roffet, F., González Galtier, M. C., Massiris, M., &
  Delrieux, C. (2025). An Open-Source Clinical Case Dataset for Medical Image
  Classification and Multimodal AI Applications. *Data*, 10(8), 123.
  https://doi.org/10.3390/DATA10080123
- Ji, S., Pan, S., Cambria, E., Marttinen, P., & Yu, P. S. (2022). A Survey on
  Knowledge Graphs: Representation, Acquisition, and Applications. *IEEE
  Transactions on Neural Networks and Learning Systems*, 33(2), 494–514.
  https://doi.org/10.1109/TNNLS.2021.3070843
- Lowrance, R., & Wagner, R. A. (1975). An Extension of the
  String-to-String Correction Problem. *Journal of the ACM*, 22(2), 177–183.
- `<demais referências da equipe>`
