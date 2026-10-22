import json

import pdfplumber
import streamlit as st
from google import genai
from google.genai import types
from groq import Groq

from prompts import RESPONSE_SCHEMA, SYSTEM_PROMPT

MIN_JOB_DESCRIPTION_LENGTH = 1000
PARAGRAPH_FIELDS = (
    "evidence_paragraph",
    "gaps_paragraph",
    "actions_paragraph",
    "verdict_paragraph",
)


def main():
    st.set_page_config(page_icon="assets/icons/favicon.png", page_title="CV Fit Score", layout="centered")

    with open("assets/styles/style_1.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.title("CV Fit Score")
    st.divider()

    st.markdown("#### 1. Upload do currículo")
    cv_file = st.file_uploader(label="", type=["pdf"], max_upload_size=5, label_visibility="collapsed")

    try:
        cv_text = extract_cv_text(cv_file)
    except Exception:
        cv_text = None

    st.button(
        "Visualizar texto do arquivo",
        icon=":material/text_snippet:",
        disabled=cv_text is None,
        on_click=show_cv_text,
        args=[cv_file, cv_text],
    )

    st.markdown("#### 2. Descrição da vaga")
    job_text = (
        st.text_area(
            label="",
            height=70,
            max_chars=5000,
            key="job_text",
            placeholder="Cole o texto aqui",
            label_visibility="collapsed",
        ).strip()
        or None
    )
    job_description_is_valid = job_text is not None and len(job_text) >= MIN_JOB_DESCRIPTION_LENGTH
    can_analyze = cv_file is not None and cv_text is not None and job_description_is_valid

    if (
        st.session_state.get("analysis_cv_text") != cv_text
        or st.session_state.get("analysis_job_description") != job_text
    ):
        st.session_state.update(analysis_result=None, analysis_failed=False)

    st.button(
        "Limpar descrição da vaga",
        icon=":material/ink_eraser:",
        disabled=job_text is None,
        on_click=lambda: st.session_state.update(job_text=""),
    )

    st.markdown("#### 3. Resultado do fit score")

    if cv_file is None:
        st.info("Faça o upload do currículo.", icon=":material/counter_1:")
    elif cv_text is None:
        st.error(f"Não foi possível ler o arquivo *{cv_file.name}*.", icon=":material/error:")
    elif job_text is None:
        st.info("Preencha a descrição da vaga.", icon=":material/counter_2:")
    elif not job_description_is_valid:
        st.error("A descrição da vaga é insuficiente.", icon=":material/error:")

    if not can_analyze:
        st.session_state.update(
            analysis_result=None,
            analysis_failed=False,
            analysis_in_progress=False,
        )
        analysis_result = None
    else:
        analysis_result = st.session_state.get("analysis_result")

    analysis_status = st.empty()

    if analysis_result is None:
        st.button(
            "Analisar aderência do CV",
            icon=":material/speed:",
            disabled=not can_analyze or st.session_state.get("analysis_in_progress", False),
            on_click=lambda: st.session_state.update(analysis_in_progress=True),
        )

        if can_analyze and st.session_state.get("analysis_in_progress"):
            with analysis_status.status("Analisando aderência do currículo...", expanded=False):
                analyze_cv_fit_score(cv_text, job_text)
            st.session_state.analysis_in_progress = False
            st.rerun()
        elif can_analyze:
            if st.session_state.get("analysis_failed"):
                analysis_status.info("Não foi possível concluir a análise. Tente novamente.", icon=":material/info:")
            else:
                analysis_status.success("Pronto para analisar aderência do CV.", icon=":material/verified:")
    else:
        score = analysis_result.get("fit_score")
        show_fit_score(score)

        insight_paragraphs = [
            analysis_result.get(field_name, "")
            for field_name in PARAGRAPH_FIELDS
        ]

        st.button(
            "Insights sobre o currículo",
            icon=":material/lightbulb:",
            on_click=show_insights,
            args=["\n\n".join(paragraph for paragraph in insight_paragraphs if paragraph)],
        )


@st.cache_data(ttl=3600, show_spinner=False)
def extract_cv_text(cv_file):
    with pdfplumber.open(cv_file) as pdf:
        page_texts = [page.extract_text() for page in pdf.pages]
        cv_text = "\n".join(page_text for page_text in page_texts if page_text).strip() or None
        return cv_text


def show_cv_text(cv_file, cv_text):
    @st.dialog(
        title=f"Texto do arquivo _{cv_file.name if cv_file else None}_",
        width="medium",
        icon=":material/text_snippet:",
    )
    def _dialog():
        st.markdown(cv_text)

    _dialog()


def analyze_cv_fit_score(cv_text, job_description):
    st.session_state.update(
        analysis_cv_text=cv_text,
        analysis_job_description=job_description,
    )

    try:
        analysis_result = get_cached_fit_score(cv_text, job_description)
    except Exception:
        st.session_state.update(analysis_result=None, analysis_failed=True)
        return

    st.session_state.update(analysis_result=analysis_result, analysis_failed=False)


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_fit_score(cv_text, job_description):
    model_fallbacks = (
        ("gemini", "gemini-3.5-flash-lite"),
        ("gemini", "gemini-3.1-flash-lite"),
        ("gemini", "gemini-2.5-flash-lite"),
        ("groq", "openai/gpt-oss-120b"),
        ("groq", "openai/gpt-oss-20b"),
        ("groq", "qwen/qwen3.8-27b"),
    )
    user_prompt = (
        f"<cv_text>{cv_text}</cv_text>\n"
        f"<job_description>{job_description}</job_description>"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for provider, model in model_fallbacks:
        try:
            if provider == "groq":
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "cv_fit_analysis",
                            "strict": True,
                            "schema": RESPONSE_SCHEMA,
                        },
                    },
                    max_tokens=5000,
                )
                response_text = response.choices[0].message.content
            else:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=RESPONSE_SCHEMA,
                    max_output_tokens=2048,
                    seed=42,
                )
                response = client.models.generate_content(
                    model=model,
                    contents=[user_prompt],
                    config=config,
                )
                response_text = response.text

            analysis_result = json.loads(response_text)
            for field in PARAGRAPH_FIELDS:
                analysis_result[field] = " ".join(analysis_result[field].split())

            score = calculate_fit_score(analysis_result["requirements"])
            analysis_result["fit_score"] = score
            return analysis_result
        except Exception:
            if (provider, model) == model_fallbacks[-1]:
                raise



def calculate_fit_score(requirements):
    match_values = {"strong": 1, "partial": 0.5, "absent": 0}
    total_weight = 0
    weighted_match = 0

    for requirement in requirements:
        weight = 2 if requirement["importance"] == "essential" else 1
        total_weight += weight
        weighted_match += weight * match_values[requirement["match"]]

    if total_weight == 0:
        return 0

    return round(100 * weighted_match / total_weight)


def show_fit_score(score):
    if score <= 30:
        score_label = "Baixo"
        color = "#e53935"
    elif score <= 50:
        score_label = "Regular"
        color = "#fb8c00"
    elif score <= 70:
        score_label = "Bom"
        color = "#fbc02d"
    else:
        score_label = "Excelente"
        color = "#43a047"

    st.markdown(
        f"""
        <style>
        [data-testid='stProgress'] [data-testid='stMarkdownContainer'] > p::before {{
            content: '{score}';
        }}
        [data-testid='stProgress'] [data-testid='stMarkdownContainer'] > p::after {{
            content: '{score_label}';
        }}
        [data-testid='stProgress'] [data-testid='stProgressBarTrack'] > div {{
            background-color: {color} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.progress(score, text="/100")


def show_insights(insights_text):
    @st.dialog(title="Insights sobre o currículo", width="medium", icon=":material/lightbulb:")
    def _dialog():
        st.markdown(insights_text)

    _dialog()


if __name__ == "__main__":
    main()
