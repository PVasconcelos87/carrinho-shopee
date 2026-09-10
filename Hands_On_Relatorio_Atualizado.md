# Projeto Hands-On de Engenharia de Dados

## Relatório Atualizado de Implementação --- Sprints 1 a 4

**MBA em Engenharia de Dados --- Universidade Presbiteriana Mackenzie**\
**Disciplina:** Hands-On Fundamentos de Dados e Analytics

**Alunos:** Arthur Henrique Coelho Peres; Bianca Rodrigues Paulino; Joao
Vitor Carvalho Camargo; Maria Luiza Alves de Macedo; Paulo Vasconcelos
Paes de Barros.

# 1. Problema e contexto

O projeto desenvolve uma solução de Engenharia de Dados para e-commerce,
utilizando a Shopee somente como inspiração de negócio. Os dados são
públicos e não representam dados internos da empresa.

O foco é o abandono de carrinho: usuários visualizam produtos, adicionam
itens ao carrinho e não apresentam uma compra observável posteriormente.

**Pergunta de negócio:** Quais padrões comportamentais e fatores de
navegação estão associados ao abandono de carrinho, qual é o potencial
de receita não capturada e como esses sinais podem direcionar ações de
recuperação?

A solução evoluiu da análise do funil para uma abordagem preditiva e
prescritiva, com dois gatilhos: Cart + 5 minutos (lembrete sem desconto)
e Cart + 1 hora (inferência ML e benefício por perfil).

# 2. Dataset

Dataset: **eCommerce behavior data from multi category store**,
novembro/2019.\
Arquivo: `2019-Nov.csv`\
Volume validado: aproximadamente **8,4 GB** e **67.501.979 eventos** na
Bronze.

Campos principais: `event_time`, `event_type`, `product_id`,
`category_id`, `category_code`, `brand`, `price`, `user_id`,
`user_session`.

Eventos: `view`, `cart`, `purchase`.

# 3. Arquitetura atual

A solução combina **Lambda Architecture** e **Medallion Architecture**.

-   Batch Layer: dataset histórico.
-   Speed Layer: simulação de eventos com Python + Kafka.
-   Data Lake: Amazon S3.
-   Processamento: Apache Spark / PySpark em Docker.
-   Medallion: Bronze, Silver e Gold.
-   Serving: PostgreSQL e Streamlit.
-   ML: Scikit-Learn / Random Forest.
-   Simulação operacional: engine dos gatilhos + interface
    HTML/JavaScript.

O Data Lake inicialmente considerado em MinIO foi substituído por
**Amazon S3**, que representa a arquitetura atual.

``` mermaid
flowchart TB
  E["E-COMMERCE EVENTS<br/>view • cart • purchase"]
  subgraph B["BATCH LAYER"]
    CSV["2019-Nov.csv<br/>8,4 GB • 67,5M eventos"] --> ING["Python + boto3"]
  end
  subgraph S["SPEED LAYER — SIMULADA"]
    PROD["Python Producer"] --> K["Apache Kafka"] --> CONS["Python Consumer"]
  end
  E --> CSV
  E --> PROD
  subgraph DL["DATA LAKE — AMAZON S3"]
    BR["BRONZE / RAW"] --> SI["SILVER / TRUSTED"] --> GO["GOLD / CURATED"]
  end
  ING --> BR
  CONS --> BR
  BR --> SP["PySpark<br/>Docker Linux"]
  SP --> SI
  SI --> SP
  SP --> GO
  GO --> PG["PostgreSQL<br/>Serving / Modelo dimensional"]
  GO --> WT["session_features<br/>Wide Table"]
  EX["Excel de treinamento<br/>1.500 registros"] --> ML["Random Forest<br/>Scikit-Learn"]
  WT -. integração final .-> ML
  ML --> AB["Modelo de abandono"]
  ML --> PF["Modelo de perfil"]
  CART["Evento CART"] --> T1["+5 min<br/>Lembrete"]
  T1 --> T2["+1 hora<br/>Inferência ML"]
  AB --> T2
  PF --> T2
  T2 --> ACT["Perfil + probabilidade<br/>Benefício recomendado"]
  PG --> ST["Streamlit<br/>Dashboard"]
  GO --> ST
  ACT --> SIM["Simulador Web<br/>HTML + JavaScript"]
```

# 4. Data Lake no Amazon S3

Bucket acadêmico: `ecommerce-data-platform-mack-lab`

``` text
ecommerce-data-platform-mack-lab/
├── bronze/ecommerce_events/year=2019/month=11/2019-Nov.csv
├── silver/ecommerce_events/year=2019/month=11/part-*.parquet
└── gold/
```

A Bronze preserva o arquivo original. A Silver contém os eventos
tratados em Parquet. A Gold concentrará regras de negócio, métricas e
features.

# 5. Pipeline Batch

`app/batch_ingestion.py` realiza o upload para a Bronze usando boto3.

`app/ecommerce_spark_processor.py` executa Bronze → Silver.

Fluxo real:
`CSV local → boto3 → S3 Bronze → PySpark/Docker → tratamento → Parquet → S3 Silver`.

Tratamentos: timestamp, normalização de event_type, tipagem, price
double, validação view/cart/purchase, remoção de timestamps inválidos,
registros sem produto/usuário, preços negativos e duplicidades.

**Status: Bronze e Silver concluídas e validadas.**

# 6. Gold e Wide Table

Estruturas previstas: `fact_events`, `dim_users`, `dim_products`,
`dim_categories`, `dim_date`, `funnel_metrics`, `abandoned_carts` e
`session_features`.

`session_features` será a Wide Table que conecta o pipeline ao ML.

Campos definidos: `session_id`, `user_id`, `total_cart_value`,
`num_cart_items`, `num_views_before_cart`, `session_duration_sec`,
`hour_of_day`, `is_night`, `user_profile`, `is_abandoned`.

**Status: em desenvolvimento.**

# 7. Speed Layer

Fluxo: `Python Producer → Apache Kafka → Python Consumer`.

Kafka e Zookeeper executam via Docker Compose. Como a origem é
histórica, a Speed Layer é simulada.

**Status: ambiente configurado; integração E2E em evolução.**

# 8. Machine Learning

Foi implementada uma camada de ML com dois classificadores Random
Forest.

Script: `src/train_excel_model.py`

Aceita `.xlsx` e `.xls`. Sem arquivo de entrada, gera
`modelo_carrinho_excel.xlsx` com **1.500 registros calibrados para
demonstração**.

Modelos: - `cart_coupon_model_excel.joblib`: probabilidade de
abandono. - `user_profile_model_excel.joblib`: perfil comportamental.

Perfis: - `high_intent`: alta intenção; lembrete/benefício leve. -
`bargain_hunter`: sensível a preço; 10--15% OFF e/ou frete grátis. -
`browser`: navegação longa/indecisa; frete grátis + 5% OFF.

Documentação: `DOCUMENTACAO_MODELO_EXCEL_GATILHOS.md`.

# 9. Engine dos dois gatilhos

Arquivo: `src/kafka_triggers_simulator.py`

**Gatilho 1 --- Cart + 5 minutos**\
Função: `execute_trigger_1_5min()`\
Ação: lembrete sem desconto --- "Realize sua compra! Olha o seu produto
aqui te esperando!"

**Gatilho 2 --- Cart + 1 hora**\
Função: `execute_trigger_2_1hour()`\
Sem compra observada, executa os modelos `.joblib`, estima abandono,
identifica perfil e prescreve benefício.

Fluxo:
`Cart → +5 min → lembrete → sem conversão → +1h → ML → perfil → benefício`.

**Status: implementado.**

# 10. Simulador e Dashboard

`index.html` e `app.js` possuem o painel **Execução dos 2 Gatilhos
Temporais de Eventos**, exibindo o gatilho de 5 minutos e a decisão do
modelo em 1 hora, inclusive com simulação randômica.

O **Streamlit** permanece como dashboard analítico, com KPIs, funil,
conversão, categorias, marcas, evolução temporal, preços e abandono.

O simulador web demonstra os gatilhos; o Streamlit apresenta análises e
indicadores.

# 11. PostgreSQL

PostgreSQL e pgAdmin estão configurados via Docker. O banco
`ecommerce_db` será a camada estruturada de serving para dados Gold,
modelo dimensional e consultas.

**Status: ambiente pronto; carga Gold → PostgreSQL pendente.**

# 12. Ambiente e DevOps

Docker Compose: Zookeeper, Kafka, PostgreSQL, pgAdmin e Apache Spark.

Cloud: AWS Academy Learner Lab / Amazon S3 (`us-east-1`).

DevOps: Git/GitHub, Terraform e GitHub Actions.

CI/CD proposto:
`Push/PR → dependências → validação Python → testes → PySpark → Terraform fmt/validate → Docker`.

Terraform deve ser adaptado para refletir a infraestrutura AWS
efetivamente utilizada.

# 13. Premissas e limitações

A base é pública e a Shopee é somente referência de domínio. O abandono
é inferido pelos eventos observados. Receita potencial é estimativa. A
Speed Layer é simulada.

A versão atual do ML utiliza 1.500 registros calibrados para
demonstração. Métricas dessa base não devem ser apresentadas como
validação real sobre os 67,5 milhões de eventos. A evolução prevista é
alimentar treinamento/inferência com `session_features` derivada da
Gold.

Os gatilhos de 5 minutos e 1 hora são regras de protótipo; em produção
deveriam ser validados com experimentos e testes A/B.

# 14. Status consolidado

  Etapa                            Status
  -------------------------------- -----------------------
  Problema e pergunta de negócio   ✅
  Dataset                          ✅
  Lambda + Medallion               ✅
  GitHub                           ✅
  Docker                           ✅
  Amazon S3                        ✅
  Batch ingestion                  ✅
  Bronze                           ✅
  PySpark em Docker                ✅
  Bronze → Silver                  ✅
  Silver Parquet                   ✅
  Kafka/Zookeeper                  🟡 Configurado
  Gold                             🟡 Em desenvolvimento
  `session_features`               🟡 Em desenvolvimento
  PostgreSQL                       🟡 Ambiente pronto
  Excel de treinamento             ✅
  Modelo de abandono               ✅
  Modelo de perfil                 ✅
  Gatilho +5 min                   ✅
  Gatilho +1 hora                  ✅
  Engine dos gatilhos              ✅
  Simulador visual                 ✅
  Documentação ML                  ✅
  Protótipo dashboard              ✅
  Dashboard conectado à Gold       ⬜
  Data Quality estruturada         ⬜
  Terraform AWS                    🟡
  GitHub Actions                   🟡 Proposto
  Testes finais                    ⬜

# 15. Evolução por Sprint

**Sprint 1:** problema, dataset, arquitetura, stack e Kanban.

**Sprint 2:** Bronze/Silver/Gold, CI/CD e IaC propostos, EDA inicial e
protótipo de dashboard.

**Sprint 3:** Docker, Kafka, PostgreSQL, Amazon S3, Batch, Bronze,
PySpark e Silver.

**Sprint 4 --- atual:** modelos de abandono e perfil, treinamento Excel,
dois gatilhos, simulador visual e documentação técnica. Integração
Silver → Gold → `session_features` em andamento.

# 16. Próximos passos

Prioridade: **Silver → Gold → session_features → ML → gatilhos**.

Depois: carga Gold no PostgreSQL, Streamlit conectado à Gold, Data
Quality, Terraform AWS, GitHub Actions, testes funcionais/integrados e
revisão final.

# 17. Fluxo final

``` text
2019-Nov.csv
   ↓
Python / boto3
   ↓
S3 Bronze
   ↓
PySpark / Docker
   ↓
S3 Silver
   ↓
S3 Gold ───────────────→ PostgreSQL ─→ Streamlit
   │
   └→ session_features ─→ Machine Learning
                              │
Evento CART → Kafka/Engine → +5 min → +1h
                            lembrete   │
                                      ↓
                              Perfil + probabilidade
                                      ↓
                              Benefício recomendado
                                      ↓
                               Simulador Web
```
