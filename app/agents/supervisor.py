from app.services.openai_client import OpenAIClient, parse_json_response
from app.services.trace import new_trace
from app.models import ConversationState


def classify_customer_message(message: str, state: ConversationState) -> tuple[dict, dict]:
    traces = []
    system_prompt = (
        "You are the Bookly supervisor agent. Route customer support conversation intents "
        "for a delayed order scenario. Return only valid JSON with the schema described. "
        "Do not include analysis or system details in the output."
    )
    user_prompt = (
        f"Customer message: \"{message}\"\n"
        f"Order ID: {state.order_id}. Need-by: {state.known_need_by}. "
        f"Active agent: {state.active_agent}. Current intent: {state.current_intent}. "
        f"Pending confirmation: {bool(state.pending_confirmation)}. "
        f"Conversation summary: {state.conversation_summary}. "
        "Decide intent, next_agent, next_action, and whether a clarification is required. "
        "If the customer asks for a human, route to escalation. "
        "If the customer explicitly requests a refund, route to resolution and choose refund-related actions. "
        "If the customer explicitly requests an expedited replacement or says they want to proceed, route to resolution and choose replacement-related actions. "
        "If the customer asks about confidence, timing, or likelihood of expedited shipping without accepting it, route to shipping and provide a status update. "
        "If the customer asks for available options or asks about delivery feasibility, route to shipping. "
        "If the customer asks for similar or alternative items that can arrive by the need-by date, route to recommendation. "
        "If the customer asks for more details about a suggested recommendation, route to product. "
        "If the customer asks about policy, route to policy. "
        "If the message is unclear, ask for clarification."
    )
    examples = """
    Example 1:
    Customer message: "ok, what are my available options?"
    Output:
    {"intent":"delivery_feasibility","confidence":0.9,"next_agent":"shipping","next_action":"estimate_delivery_options","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":null},"decision_summary":"Customer asked for delivery options; route to ShippingAgent."}

    Example 2:
    Customer message: "I would like an expedited replacement. When is the earliest I can expect expedited shipping?"
    Output:
    {"intent":"accept_expedited_shipping","confidence":0.95,"next_agent":"resolution","next_action":"offer_expedited_replacement","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"accept_replacement"},"decision_summary":"Customer asked for expedited replacement; route to ResolutionAgent."}

    Example 2b:
    Customer message: "How confident are we that expedited shipping will arrive by Saturday night?"
    Output:
    {"intent":"delivery_feasibility","confidence":0.85,"next_agent":"shipping","next_action":"answer_from_tracking","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":null},"decision_summary":"Customer is asking about expedited shipping confidence; route to ShippingAgent."}

    Example 3:
    Customer message: "that is too late. can I just get a refund instead?"
    Output:
    {"intent":"request_refund","confidence":0.95,"next_agent":"resolution","next_action":"check_refund_eligibility","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"refund"},"decision_summary":"Customer asked for a refund; route to ResolutionAgent."}

    Example 4:
    Customer message: "refund"
    Output:
    {"intent":"request_refund","confidence":0.95,"next_agent":"resolution","next_action":"check_refund_eligibility","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"refund"},"decision_summary":"Customer requested refund; route to ResolutionAgent."}

    Example 5:
    Customer message: "give me a refund"
    Output:
    {"intent":"request_refund","confidence":0.95,"next_agent":"resolution","next_action":"check_refund_eligibility","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"refund"},"decision_summary":"Customer explicitly asked for refund; route to ResolutionAgent."}

    Example 5b:
    Customer message: "if I choose a replacement, do I have to pay the price difference?"
    Output:
    {"intent":"ask_policy","confidence":0.95,"next_agent":"policy","next_action":"answer_policy","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"ask_policy"},"decision_summary":"Customer asked about replacement cost and upcharge; route to PolicyAgent."}

    Example 5c:
    Customer message: "tell me more about the first option"
    Output:
    {"intent":"ask_product_details","confidence":0.9,"next_agent":"product","next_action":"explain_product_details","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"explain_product_details"},"decision_summary":"Customer asked for more details about a recommended product; route to ProductAgent."}

    Example 6:
    Customer message: "yes, let's proceed with expedited shipment"
    Output:
    {"intent":"accept_expedited_shipping","confidence":0.95,"next_agent":"resolution","next_action":"offer_expedited_replacement","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"accept_replacement"},"decision_summary":"Customer confirmed expedited replacement; route to ResolutionAgent."}

    Example 7:
    Customer message: "can you recommend something similar that can arrive on time?"
    Output:
    {"intent":"recommend_similar_items","confidence":0.9,"next_agent":"recommendation","next_action":"recommend_similar_items","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"recommend_similar_items"},"decision_summary":"Customer asked for a similar on-time alternative; route to RecommendationAgent."}

    Example 8:
    Customer message: "I'd rather get a replacement item that can still make it by Saturday instead of a refund."
    Output:
    {"intent":"recommend_similar_items","confidence":0.9,"next_agent":"recommendation","next_action":"recommend_similar_items","requires_clarification":false,"clarifying_question":null,"extracted_fields":{"need_by":null,"requested_action":"recommend_similar_items"},"decision_summary":"Customer requested an on-time alternative instead of a refund; route to RecommendationAgent."}
    """
    schema = {
        "intent": "delivery_status | delivery_feasibility | accept_expedited_shipping | request_refund | confirm_refund | recommend_similar_items | ask_policy | ask_product_details | request_escalation | anger_or_dissatisfaction | change_mind | unclear",
        "confidence": 0.0,
        "next_agent": "shipping | resolution | recommendation | policy | product | escalation | supervisor",
        "next_action": "answer_from_tracking | estimate_delivery_options | offer_expedited_replacement | check_refund_eligibility | request_refund_confirmation | issue_refund | upgrade_shipping | recommend_similar_items | answer_policy | explain_product_details | create_escalation | ask_clarifying_question | close_conversation",
        "requires_clarification": False,
        "clarifying_question": None,
        "extracted_fields": {
            "need_by": None,
            "requested_action": None,
        },
        "decision_summary": "short summary suitable for trace display"
    }

    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": examples},
        {
            "role": "assistant",
            "content": (
                "Return only JSON object with keys: intent, confidence, next_agent, next_action, "
                "requires_clarification, clarifying_question, extracted_fields, decision_summary."
            ),
        },
    ]

    client = OpenAIClient()
    raw_response = client.chat(prompt, temperature=0.45)
    try:
        parsed = parse_json_response(raw_response)
    except Exception:
        parsed = {
            "intent": "unclear",
            "confidence": 0.0,
            "next_agent": "supervisor",
            "next_action": "ask_clarifying_question",
            "requires_clarification": True,
            "clarifying_question": "Can you tell me a bit more about what you'd like us to do for this order?",
            "extracted_fields": {"need_by": None, "requested_action": None},
            "decision_summary": "Could not classify the customer message cleanly.",
        }

    # Deterministic fallback rules when the model is unclear or low-confidence
    low_confidence = parsed.get("confidence", 0) < 0.25
    unclear_intent = parsed.get("intent") in (None, "unclear")
    if low_confidence or unclear_intent:
        text = message.lower()
        rule = {}
        if "refund" in text or "money" in text or "charge" in text:
            rule = {
                "intent": "request_refund",
                "confidence": 0.7,
                "next_agent": "resolution",
                "next_action": "check_refund_eligibility",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "refund"},
                "decision_summary": "Customer requests a refund; route to ResolutionAgent.",
            }
        elif any(k in text for k in ("human", "person", "representative", "agent", "talk to")):
            rule = {
                "intent": "request_escalation",
                "confidence": 0.9,
                "next_agent": "escalation",
                "next_action": "create_escalation",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "escalation"},
                "decision_summary": "Customer asked for a human; escalate.",
            }
        elif any(k in text for k in ("why", "delayed", "status", "where is", "what happened")):
            rule = {
                "intent": "delivery_status",
                "confidence": 0.8,
                "next_agent": "shipping",
                "next_action": "answer_from_tracking",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": None},
                "decision_summary": "Customer asks about delivery status; route to ShippingAgent.",
            }
        elif any(k in text for k in ("how confident", "confidence", "likely", "what are the chances", "chance", "will it arrive", "arrive by")) and any(k in text for k in ("replacement", "expedited", "expedited shipment", "expedited shipping")):
            rule = {
                "intent": "delivery_feasibility",
                "confidence": 0.85,
                "next_agent": "shipping",
                "next_action": "answer_from_tracking",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": None},
                "decision_summary": "Customer is asking how confident expedited shipping is; route to ShippingAgent for timing and next-step validation.",
            }
        elif "options" in text or "what are my" in text or "what can" in text:
            rule = {
                "intent": "delivery_feasibility",
                "confidence": 0.8,
                "next_agent": "shipping",
                "next_action": "estimate_delivery_options",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": None},
                "decision_summary": "Customer asked for options; ask ShippingAgent to estimate delivery options.",
            }
        elif any(k in text for k in ("upcharge", "pay the difference", "difference in cost", "will i have to pay", "do i have to pay", "replacement cost", "more expensive replacement", "additional cost", "price difference", "cost difference", "discount", "store credit", "promotion", "compensation")):
            rule = {
                "intent": "ask_policy",
                "confidence": 0.9,
                "next_agent": "policy",
                "next_action": "answer_policy",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "ask_policy"},
                "decision_summary": "Customer is asking about upcharge or compensation; route to PolicyAgent.",
            }
        elif any(k in text for k in ("recommend", "similar", "alternative", "instead of refund", "instead of a refund", "instead of a replacement", "arrive on time", "same gift", "other option", "other item")):
            rule = {
                "intent": "recommend_similar_items",
                "confidence": 0.9,
                "next_agent": "recommendation",
                "next_action": "recommend_similar_items",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "recommend_similar_items"},
                "decision_summary": "Customer asked for a similar on-time alternative; route to RecommendationAgent.",
            }
        elif any(k in text for k in ("proceed", "go ahead", "yes", "ok", "okay")) and any(k in text for k in ("replacement", "expedited", "expedited shipment", "expedited shipping")):
            rule = {
                "intent": "accept_expedited_shipping",
                "confidence": 0.95,
                "next_agent": "resolution",
                "next_action": "offer_expedited_replacement",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "accept_replacement"},
                "decision_summary": "Customer agreed to proceed with expedited replacement; route to ResolutionAgent.",
            }
        elif any(k in text for k in ("recommend", "similar", "alternative", "instead of refund", "instead of a refund", "instead of a replacement", "arrive on time", "same gift", "other option", "other item")):
            rule = {
                "intent": "recommend_similar_items",
                "confidence": 0.9,
                "next_agent": "recommendation",
                "next_action": "recommend_similar_items",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "recommend_similar_items"},
                "decision_summary": "Customer asked for a similar on-time alternative; route to RecommendationAgent.",
            }
        elif "confirm" in text and "refund" in text or (parsed.get("intent") == "confirm_refund"):
            rule = {
                "intent": "confirm_refund",
                "confidence": 0.9,
                "next_agent": "resolution",
                "next_action": "issue_refund",
                "requires_clarification": False,
                "clarifying_question": None,
                "extracted_fields": {"need_by": None, "requested_action": "confirm_refund"},
                "decision_summary": "Customer confirmed refund; instruct ResolutionAgent to issue refund if pending.",
            }
        else:
            rule = {
                "intent": "unclear",
                "confidence": 0.0,
                "next_agent": "supervisor",
                "next_action": "ask_clarifying_question",
                "requires_clarification": True,
                "clarifying_question": "Can you tell me a bit more about what you'd like us to do for this order?",
                "extracted_fields": {"need_by": None, "requested_action": None},
                "decision_summary": "Could not determine intent; asking for clarification.",
            }

        # Apply deterministic rule override
        parsed.update(rule)

    # Additional keyword-based overrides to prevent incorrect shipping-only routing
    text = message.lower()
    # If a recommendation was offered previously and the customer replies affirmatively,
    # prioritize routing to the RecommendationAgent for a smooth handoff.
    if state.pending_recommendation:
        if any(k in text for k in ("yes", "sure", "please", "recommend", "similar", "alternatives", "alternative", "instead of refund", "arrive on time", "show alternatives", "recommend something")):
            parsed.update({
                "intent": "recommend_similar_items",
                "confidence": max(parsed.get("confidence", 0), 0.9),
                "next_agent": "recommendation",
                "next_action": "recommend_similar_items",
                "requires_clarification": False,
                "decision_summary": "Customer accepted recommendation offer; routing to RecommendationAgent.",
            })
        # If the customer explicitly declines, clear the pending flag and continue normal routing
        elif any(k in text for k in ("no", "not now", "no thanks", "don\'t")):
            state.pending_recommendation = False
    if state.active_agent == "recommendation" and any(k in text for k in ("tell me more", "more about", "details", "what's included", "what is the size", "dimensions", "color", "material", "brand", "how big", "how many", "is it sturdy", "can you describe", "product detail", "details on")):
        parsed.update({
            "intent": "ask_product_details",
            "confidence": 0.9,
            "next_agent": "product",
            "next_action": "explain_product_details",
            "requires_clarification": False,
            "clarifying_question": None,
            "extracted_fields": {"need_by": None, "requested_action": "explain_product_details"},
            "decision_summary": "Customer is asking for more details about a recommended product; routing to ProductAgent.",
        })
    if "refund" in text and parsed.get("next_agent") != "resolution":
        parsed.update({
            "intent": "request_refund",
            "confidence": max(parsed.get("confidence", 0), 0.8),
            "next_agent": "resolution",
            "next_action": "check_refund_eligibility",
            "requires_clarification": False,
            "decision_summary": "Keyword override: customer mentions refund; routing to ResolutionAgent.",
        })
    if any(k in text for k in ("human", "person", "representative", "agent", "talk to")) and parsed.get("next_agent") != "escalation":
        parsed.update({
            "intent": "request_escalation",
            "confidence": 0.95,
            "next_agent": "escalation",
            "next_action": "create_escalation",
            "requires_clarification": False,
            "decision_summary": "Keyword override: customer requested a human; escalate.",
        })
    if any(k in text for k in ("recommend", "similar", "alternative", "instead of refund", "instead of a refund", "instead of a replacement", "arrive on time", "same gift", "other option", "other item")) and parsed.get("next_agent") != "recommendation":
        parsed.update({
            "intent": "recommend_similar_items",
            "confidence": max(parsed.get("confidence", 0), 0.9),
            "next_agent": "recommendation",
            "next_action": "recommend_similar_items",
            "requires_clarification": False,
            "decision_summary": "Keyword override: customer asked for a similar on-time alternative; routing to RecommendationAgent.",
        })
    if any(k in text for k in ("options", "what are my", "what can", "what are the")) and parsed.get("next_agent") != "shipping":
        parsed.update({
            "intent": "delivery_feasibility",
            "confidence": max(parsed.get("confidence", 0), 0.8),
            "next_agent": "shipping",
            "next_action": "estimate_delivery_options",
            "requires_clarification": False,
            "decision_summary": "Keyword override: customer asked for options; routing to ShippingAgent.",
        })
    if any(k in text for k in ("replacement", "expedited", "expedited shipment", "expedited shipping")) and parsed.get("next_agent") != "resolution":
        if any(k in text for k in ("proceed", "go ahead", "yes", "ok", "okay", "sounds good", "please do", "confirm")):
            parsed.update({
                "intent": "accept_expedited_shipping",
                "confidence": 0.95,
                "next_agent": "resolution",
                "next_action": "offer_expedited_replacement",
                "requires_clarification": False,
                "decision_summary": "Keyword override: customer is explicitly confirming expedited replacement; route to ResolutionAgent.",
            })
        elif any(k in text for k in ("how confident", "confidence", "likely", "what are the chances", "chance", "will it arrive", "arrive by")):
            parsed.update({
                "intent": "delivery_feasibility",
                "confidence": 0.85,
                "next_agent": "shipping",
                "next_action": "answer_from_tracking",
                "requires_clarification": False,
                "clarifying_question": None,
                "decision_summary": "Customer is asking about expedited shipping confidence; route to ShippingAgent.",
            })
    if state.active_agent == "shipping" and any(k in text for k in ("proceed", "go ahead", "yes", "ok", "okay", "sounds good")) and not state.pending_recommendation:
        parsed.update({
            "intent": "accept_expedited_shipping",
            "confidence": 0.95,
            "next_agent": "resolution",
            "next_action": "offer_expedited_replacement",
            "requires_clarification": False,
            "decision_summary": "Context override: customer accepted the expedited option after shipping details; route to ResolutionAgent.",
        })
    if state.pending_confirmation and state.pending_confirmation.get("action") == "issue_refund" and any(k in text for k in ("refund", "confirm refund", "proceed with refund", "please refund", "issue me a refund", "yes", "confirm", "absolutely", "please do", "go ahead")):
        parsed.update({
            "intent": "confirm_refund",
            "confidence": 0.95,
            "next_agent": "resolution",
            "next_action": "issue_refund",
            "requires_clarification": False,
            "decision_summary": "Pending refund confirmation detected; route to ResolutionAgent to issue refund.",
        })
    elif state.pending_confirmation and any(k in text for k in ("yes", "confirm", "absolutely", "please do", "go ahead")):
        parsed.update({
            "intent": "confirm_refund",
            "confidence": 0.95,
            "next_agent": "resolution",
            "next_action": "issue_refund",
            "requires_clarification": False,
            "decision_summary": "Pending refund confirmation detected; route to ResolutionAgent to issue refund.",
        })

    traces.append(
        new_trace(
            type="intent_classification",
            agent="SupervisorAgent",
            title="Customer message classified",
            summary=parsed.get("decision_summary", "Supervisor classified the customer request."),
            inputs={"message": message, "state": state.dict()},
            outputs=parsed,
        )
    )

    return parsed, traces[0].dict()
