SYSTEM_PROMPT = """
Compare <cv_text> with <job_description>. Use only evidence explicitly stated in the CV; do not infer or invent
qualifications. Identify the job's technical requirements. Mark a requirement essential only when the job description
clearly says it is mandatory or required; otherwise mark it desirable. For each requirement, classify the CV evidence
as strong, partial, or absent. Do not include behavioral requirements in the score.

Return only the JSON defined by the schema. Write the four concise paragraphs in the job description's language.
Keep them balanced and approximately similar in length, with about two sentences each. Refer to the person using the
equivalent of "candidate" in that language, and omit names and personal data.

- evidence_paragraph: Highlight the strongest technical matches and connect them to specific evidence in the CV.
- gaps_paragraph: Point out missing or partial technical requirements, prioritizing essential requirements.
- actions_paragraph: Suggest practical, specific next steps to address those gaps or present existing relevant
  experience more clearly. Do not claim the candidate has taken actions or has qualifications not stated in the CV.
- verdict_paragraph: Summarize the candidate's overall fit based on the matches and gaps without repeating their
  lists. Do not calculate or state a numeric fit score; the application calculates it from the classifications.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement": {
                        "type": "string",
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["essential", "desirable"],
                    },
                    "match": {
                        "type": "string",
                        "enum": ["strong", "partial", "absent"],
                    },
                },
                "required": ["requirement", "importance", "match"],
                "additionalProperties": False,
            },
        },
        "evidence_paragraph": {
            "type": "string",
        },
        "gaps_paragraph": {
            "type": "string",
        },
        "actions_paragraph": {
            "type": "string",
        },
        "verdict_paragraph": {
            "type": "string",
        },
    },
    "required": [
        "requirements",
        "evidence_paragraph",
        "gaps_paragraph",
        "actions_paragraph",
        "verdict_paragraph",
    ],
    "additionalProperties": False,
}
