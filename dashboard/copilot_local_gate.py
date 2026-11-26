"""Local-only Owner approval UI; excluded from the Cloud release source."""
from src.ai_copilot.approval import OwnerVerifier, ApprovalBlocked
from src.ai_copilot.execution_gate import LocalExecutionGate
from src.ai_copilot.ledger import LedgerBlocked
from src.ai_copilot.provider import build_request as build_local_request


def create_local_gate(path: str) -> LocalExecutionGate | None:
    try:
        return LocalExecutionGate(path, OwnerVerifier.from_environment())
    except (ApprovalBlocked, LedgerBlocked, OSError, ValueError):
        return None


def render_local_owner(st, gate: LocalExecutionGate, review, request, label) -> None:
    request = build_local_request(
        review, model_snapshot=request.model_snapshot,
        max_output_tokens=request.max_output_tokens,
        timeout_seconds=request.timeout_seconds,
    )
    st.subheader(label('owner'))
    st.caption(label('ledger') + ': ' + gate.ledger.status())
    reference = st.session_state.get('copilot_approval_ref')
    try:
        valid = gate.approval_status(review, request, reference)
    except (ApprovalBlocked, ValueError, TypeError):
        valid = False
    with st.form('copilot_owner_form', clear_on_submit=True):
        password = st.text_input(label('password'), type='password', key='copilot_owner_password')
        submitted = st.form_submit_button(label('approve'))
    if submitted:
        try:
            approved = gate.approve(review, request, password)
            st.session_state['copilot_approval_ref'] = approved.reference
            valid = True
        except (ApprovalBlocked, ValueError, TypeError):
            st.error(label('status') + ': REJECTED')
    st.caption(label('status') + ': ' + ('VALID' if valid else 'NOT APPROVED'))
