# CV Fit Score

Aplicação web em Streamlit que compara um currículo com a descrição de uma vaga. Ela usa modelos do Google Gemini e do Groq para identificar requisitos técnicos, avaliar as evidências presentes no currículo e produzir insights. O score numérico é calculado pela aplicação a partir das classificações dos requisitos.

## Como funciona

1. **Upload do currículo:** a pessoa envia um arquivo PDF de até 5 MB. A aplicação extrai o texto de todas as páginas com `pdfplumber` e permite visualizá-lo em uma janela. Não há etapa de OCR; PDFs compostos apenas por imagens podem não fornecer texto para análise.
2. **Descrição da vaga:** a pessoa cola o texto da vaga. Espaços no início e no fim são removidos; a análise só é habilitada quando o texto tem entre 1.000 e 5.000 caracteres.
3. **Análise:** ao clicar em **Analisar aderência do CV**, a aplicação mostra um status de processamento e envia o texto do currículo e da vaga ao provedor do modelo que estiver sendo tentado. Os modelos são consultados em sequência; se uma chamada ou o processamento da resposta falhar, a aplicação tenta o próximo modelo. A resposta deve seguir um esquema JSON definido no projeto. Se o texto extraído do currículo ou a descrição da vaga mudar depois de uma análise, o resultado anterior é descartado e uma nova análise pode ser iniciada.
4. **Resultado:** a aplicação calcula e exibe o score de 0 a 100. Um botão permite consultar os quatro parágrafos de insights gerados pelo modelo.

O modelo deve usar apenas evidências explícitas no currículo, sem inventar qualificações. Ele identifica requisitos técnicos (não comportamentais), classifica cada requisito como essencial ou desejável e avalia a correspondência como forte, parcial ou ausente. Um requisito só deve ser considerado essencial quando a vaga o descreve claramente como obrigatório. Os insights são escritos no idioma da descrição da vaga e não devem incluir nomes ou dados pessoais.

## Como o score é calculado

Cada requisito recebe uma importância e uma classificação de correspondência:

| Campo | Valor | Efeito no cálculo |
|---|---|---:|
| Importância | `essential` | Peso 2 |
| Importância | `desirable` | Peso 1 |
| Correspondência | `strong` | Contribuição de 1 × o peso |
| Correspondência | `partial` | Contribuição de 0,5 × o peso |
| Correspondência | `absent` | Contribuição de 0 × o peso |

A fórmula usada é:

```text
score = round(100 × soma(peso × valor_da_correspondência) / soma(pesos))
```

Por exemplo, para um requisito essencial forte, um essencial parcial e um desejável ausente:

```text
score = round(100 × (2 × 1 + 2 × 0,5 + 1 × 0) / (2 + 2 + 1))
      = 60
```

Se a lista de requisitos estiver vazia, o score é `0`. Requisitos ausentes também contribuem com zero, mas continuam no denominador; portanto, requisitos essenciais ausentes reduzem o resultado mais do que requisitos desejáveis ausentes.

O valor numérico é apresentado com um rótulo visual:

| Score | Rótulo |
|---:|---|
| 0–30 | Baixo |
| 31–50 | Regular |
| 51–70 | Bom |
| 71–100 | Excelente |

Essas faixas são apenas a apresentação do resultado; não alteram a fórmula.

## Insights gerados

Além dos requisitos estruturados usados no cálculo, a resposta JSON contém quatro parágrafos:

- **Evidências:** destaca as correspondências técnicas mais fortes e as relaciona a evidências específicas do currículo.
- **Lacunas:** aponta requisitos ausentes ou parcialmente atendidos, priorizando os essenciais.
- **Ações:** sugere próximos passos práticos sem afirmar que a pessoa já os realizou ou que tem qualificações não descritas.
- **Veredito:** resume a aderência geral sem repetir as listas nem declarar um score numérico.

O formato esperado e os valores permitidos para cada campo estão definidos em `prompts.py`. O score é calculado localmente pela função `calculate_fit_score` em `page_1.py`, não pelo modelo.

## Tecnologias e estrutura

- **Streamlit:** interface web e gerenciamento do estado da sessão.
- **Google Gen AI SDK:** chamadas aos modelos Gemini.
- **Groq Python SDK:** chamadas aos modelos hospedados no Groq.
- **pdfplumber:** extração de texto dos PDFs.

Arquivos principais:

| Arquivo | Responsabilidade |
|---|---|
| `streamlit_app.py` | Configura a navegação e abre a página principal. |
| `page_1.py` | Interface, extração do PDF, chamadas à API, cálculo do score e exibição dos resultados. |
| `prompts.py` | Instruções enviadas ao modelo e esquema JSON da resposta. |
| `assets/styles/style_1.css` | Estilos da interface. |
| `assets/icons/favicon.png` | Ícone da página. |
| `requirements.txt` | Dependências Python da aplicação. |

## Como executar localmente

É necessário ter Python e chaves de API do Google Gemini e do Groq para habilitar toda a sequência de fallback.

1. Clone o repositório e entre na pasta do projeto.
2. Crie e ative um ambiente virtual:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instale as dependências:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Crie `.streamlit\secrets.toml` na raiz do projeto com as chaves de API:

   ```toml
   GEMINI_API_KEY = "sua-chave"
   GROQ_API_KEY = "sua-chave"
   ```

   Configure as duas chaves para que os modelos dos dois provedores possam ser usados. Não compartilhe nem versione esse arquivo. `.streamlit/secrets.toml` está listado no `.gitignore`.

5. Inicie a aplicação:

   ```powershell
   streamlit run streamlit_app.py
   ```

## Modelos, cache e falhas

A aplicação tenta os modelos nesta ordem:

1. Gemini: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite` e `gemini-2.5-flash-lite`.
2. Groq: `openai/gpt-oss-120b`, `openai/gpt-oss-20b` e `qwen/qwen3.8-27b`.

Se uma chamada ou o processamento da resposta falhar, o próximo modelo é tentado. As solicitações pedem uma resposta JSON conforme o esquema definido em `prompts.py`. Para Gemini, a resposta é limitada a 2.048 tokens e a seed é 42; para Groq, o limite é de 5.000 tokens e é solicitada saída estruturada estrita.

O texto extraído do currículo é armazenado em cache por 1 hora. O resultado da análise, incluindo score, também é armazenado em cache por 1 hora para as mesmas entradas. Os quatro parágrafos de insight são normalizados para remover quebras de linha internas antes de serem exibidos.

Se a extração do PDF falhar, a interface informa que não foi possível ler o arquivo. Se todos os modelos falharem, a aplicação mantém o resultado vazio e informa que não foi possível concluir a análise, permitindo uma nova tentativa. O detalhe técnico da falha não é mostrado na interface.
