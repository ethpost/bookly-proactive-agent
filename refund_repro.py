from app.models import ConversationState
from app.agents.supervisor import classify_customer_message
from app.agents.resolution_agent import handle_resolution_intent

state = ConversationState(
    scenario_id='delayed_birthday_gift_recovery',
    customer_id='CUST-1007',
    order_id='BK-1042',
    known_need_by='Saturday morning',
    active_agent='shipping',
    current_intent='delivery_feasibility',
    offered_options=['expedited_replacement','refund','escalation'],
    pending_confirmation=None,
    pending_recommendation=False,
    completed_actions=[],
    conversation_summary='',
    messages=[],
    refund_issued=False,
    expedited_replacement_created=False,
    escalation_created=False,
    preferred_channel='sms',
    order_value=34.98,
)
for msg in [
    'actually, just issue me a refund and I will go find something else',
    'confirm refund',
    'proceed with refund',
]:
    decision, trace = classify_cust    decision, trace = classify_cust    decision, trace = classify_cust    decision, tif    decision, trace = classify_cust on':
    decision, trace = classify_cust    decision, trace = cta    decision, trace = classify_cust    decision, trace = cta   t('    decision, tracending_co    decision, trace = classify_cust    decisionte.    decision, trace = cla'---')
