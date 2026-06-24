from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from control_tower.config import CLASSIFIER_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from control_tower.schemas import IssueClassification

# The model "head" for classification: a fast reasoning model, forced to return
# an IssueClassification object instead of free text.
classifier_llm = ChatOpenAI(
    model=CLASSIFIER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    reasoning_effort="low",          # keep it fast/cheap for simple categorization
).with_structured_output(IssueClassification)

classifier_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You triage inbound e-commerce support tickets. 
            Classify the issue into exactly one category and rate its urgency. 
            Pick the single best-fit category; use 'other' only when nothing fits.""",
        ),
        ("human", "Ticket message:\n{message}"),
    ]
)

# LCEL: prompt feeds the model; the model returns a validated IssueClassification.
classify_chain = classifier_prompt | classifier_llm