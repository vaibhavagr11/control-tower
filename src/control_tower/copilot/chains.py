from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
        MessagesPlaceholder("chat_history", optional= True),
        ("human", "Ticket message:\n{message}"),
    ]
)

# LCEL: prompt feeds the model; the model returns a validated IssueClassification.
classify_chain = classifier_prompt | classifier_llm

resolver_llm = ChatOpenAI(
    model=RESOLVER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    reasoning_effort="low",        
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
            - Be honest about uncertainty: set confidence to 'low' when context is thin or conflicting."""
        ),
        MessagesPlaceholder("chat_history", optional=True),
        (
            "human",
            """Issue type: {issue_type} (urgency: {urgency})
            Order & customer context:{context}
            Customer's past tickets: {customer_history}
            Applicable policy rules:{policies}
            Customer's message: {message}
            Recommend the single best resolution.""",
        ),
    ]
)

resolve_chain = resolver_prompt | resolver_llm

summarizer_llm = ChatOpenAI(
    model= CLASSIFIER_MODEL,
    api_key= OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    reasoning_effort="low",
)

summarizer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Summarize this customer support conversation in 1-2 short sentences.
            Preserve any specific facts, requests, or constraints the customer mentioned —
            don't just say "customer had an issue".""",
        ),
        ("human", "{conversation}"),
    ]
)

summarize_chain = summarizer_prompt | summarizer_llm

communicator_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are writing a customer-facing message on behalf of a support agent.
            Rules:
            - Warm, empathetic, concise — the customer is frustrated.
            - If action_taken is YES: past tense — the action is done. ("We've issued your refund")
            - If action_taken is NO: future tense — pending review. ("We'll get this sorted")
            - Never mention fraud checks, account flags, or internal review reasons.
            - If escalating, say a specialist will follow up — never say "escalate".
            - Use the customer's name if provided.
            - 2-3 sentences max.""",
        ),
        (
            "human",
            """Customer message: {message}
            Customer name: {customer_name}
            Issue type: {issue_type} (urgency: {urgency})
            Recommended action: {recommended_action}
            Rationale: {rationale}
            Action taken: {action_taken}
            Action details: {action_details}
            Write the customer-facing message.""",
        ),
    ]
)

communication_chain = communicator_prompt | ChatOpenAI(
    model=CLASSIFIER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

clarification_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a customer support agent who needs one specific piece of information
            before resolving a ticket. Generate ONE polite, specific clarifying question.
            Don't ask vague questions like "can you tell me more?" — ask for exactly
            what's missing. One sentence.""",
        ),
        (
            "human",
            """Issue type: {issue_type}
            Customer message: {message}
            What is the single most important missing piece of information?
            Ask the customer directly.""",
        ),
    ]
)

clarification_chain = clarification_prompt | ChatOpenAI(
    model=CLASSIFIER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)


simulate_response_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are simulating a real customer replying to a support message.
            Generate a brief, natural response — customers are sometimes specific,
            sometimes still a bit vague. 1-2 sentences.""",
        ),
        (
            "human",
            """Original customer message: {original_message}
            Support agent asked: {clarification_question}
            Generate a realistic customer reply:""",
        ),
    ]
)

simulate_response_chain = simulate_response_prompt | ChatOpenAI(
    model=CLASSIFIER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)