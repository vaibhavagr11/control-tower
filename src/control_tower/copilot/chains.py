from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from control_tower.config import CLASSIFIER_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, RESOLVER_MODEL
from control_tower.schemas import IssueClassification, ResolutionRecommendation

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

resolver_llm = ChatOpenAI(
    model=RESOLVER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    reasoning_effort="medium",        # more thinking for policy + fraud judgment
).with_structured_output(ResolutionRecommendation)

resolver_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a customer-operations resolution copilot. 
            You RECOMMEND a resolution for a human agent to approve. 
            You never act on your own. 
            Rules:
            - Ground every recommendation in the provided order context AND the policy rules.
            - Cite the policy rule IDs you used in policy_citations.
            - Assess fraud risk from customer history (prior claims, account age) and order value.
            - If a policy requires human/fraud review, recommend 'escalate_to_human'.
            - Be honest about uncertainty: set confidence to 'low' when context is thin or conflicting.
            - Draft a warm, concise message for the agent to send the customer on approval.""",
        ),
        (
            "human",
            """Issue type: {issue_type} (urgency: {urgency})
            Order & customer context:{context}
            Applicable policy rules:{policies}
            Customer's message: {message}
            Recommend the single best resolution.""",
        ),
    ]
)

resolve_chain = resolver_prompt | resolver_llm