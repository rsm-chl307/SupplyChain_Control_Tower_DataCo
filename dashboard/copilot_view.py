"""Local synthetic Decision Copilot view. Fake Provider only; no paid dispatch."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Timer
import streamlit as st

from dashboard.i18n import current_locale
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request, FakeProvider, ProviderResult, ProviderBlocked
from src.ai_copilot.response_contract import classify_response
from src.ai_copilot.approval import OwnerVerifier, ApprovalBlocked
from src.ai_copilot.execution_gate import LocalExecutionGate
from src.ai_copilot.ledger import LedgerBlocked


LABELS = {
    "title": ("Decision Copilot — local synthetic preview", "決策輔助 — 本機合成資料預覽"),
    "scope": ("Pinned synthetic fixture only. No paid provider, actions, or production Run access.",
              "僅使用固定合成測試資料。不呼叫付費供應商、不執行建議，也不存取正式 Run。"),
    "start": ("Create trusted synthetic Context", "建立受信任的合成 Context"),
    "scenario": ("Synthetic scenario", "合成情境"),
    "close": ("Close and remove synthetic Context", "關閉並移除合成 Context"),
    "prepare": ("Prepare Brief", "準備分析摘要"),
    "review": ("Exact validated Brief", "經驗證的完整分析摘要"),
    "request": ("Outbound request digest", "對外請求摘要值"),
    "owner": ("Separate local Owner approval", "獨立本機擁有者核准"),
    "password": ("Owner password", "擁有者密碼"),
    "approve": ("Approve exact request", "核准此筆精確請求"),
    "fake": ("Preview Fake Provider response", "預覽模擬供應商回應"),
    "status": ("Approval status", "核准狀態"),
    "ledger": ("Durable ledger status", "持久帳本狀態"),
    "unavailable": ("Local Owner configuration is unavailable; preview only.",
                    "本機擁有者設定不可用；僅能預覽。"),
    "blocked": ("Brief or context validation failed. Create a fresh trusted synthetic Context.",
                "分析摘要或 Context 驗證失敗。請重新建立受信任的合成 Context。"),
    "validated": ("Validated advisory preview — qualitative only", "經驗證的建議預覽 — 僅定性"),
    "invalid": ("Fake response failed validation; no advisory is displayed.",
                "模擬回應未通過驗證；不顯示建議。"),
    "review_required": ("Unstructured quantity requires human review; no advisory is displayed.",
                        "未結構化數量主張須由人工審核；不顯示建議。"),
}


def label(key: str) -> str:
    return LABELS[key][1 if current_locale() == 'zh-TW' else 0]


def local_owner_gate() -> LocalExecutionGate | None:
    """Default-deny local preview gate; environment flags are not identity."""
    if (os.environ.get('COPILOT_LOCAL_OWNER_MODE') != '1'
            or os.environ.get('STREAMLIT_SHARING_MODE')
            or st.get_option('server.address') not in {'127.0.0.1', 'localhost', '::1'}):
        return None
    path = os.environ.get('COPILOT_LEDGER_PATH')
    if not path or not Path(path).is_absolute():
        return None
    try:
        return LocalExecutionGate(path, OwnerVerifier.from_environment())
    except (ApprovalBlocked, LedgerBlocked, OSError, ValueError):
        return None


def fake_result(review) -> ProviderResult:
    """Fixed advisory text with a copied evidence slot; no calculation or tool."""
    brief = review.verify()
    ref = brief['run_context']['source_ref']
    capacity = brief['capacity_analysis']['records'][0]
    capacity_source = next(source for source in brief['source_manifest']
                           if source['source_ref_id'] == capacity['source_ref'])
    capacity_slot = {'source_ref_id': capacity['source_ref'], 'field_name': 'Capacity_Utilization',
                     'value': capacity['values']['Capacity_Utilization'], 'unit': 'ratio',
                     'grain': capacity_source['native_grain']}
    data = {
        'response_version': '1.0', 'brief_digest': review.content_digest,
        'executive_assessment': {'summary': 'Review the bounded synthetic evidence.',
                                 'principal_concern': 'Evidence requires human interpretation.',
                                 'evidence_refs': [ref]},
        'key_findings': [{'finding_id': 'F1', 'description': 'Capacity deserves review.',
                          'evidence_refs': [capacity['source_ref']],
                          'numerical_evidence': [capacity_slot],
                          'potential_operational_impact': 'Potential service pressure.',
                          'severity': 'Medium',
                          'severity_rationale': 'Published capacity evidence.'}],
        'root_cause_interpretation': {key: [] for key in
                                      ('observed_facts', 'system_identified_drivers',
                                       'ai_interpretations', 'unverified_hypotheses', 'missing_evidence')},
        'recommendations': [], 'decision_trade_offs': [], 'further_investigation': [],
        'limitations_and_confidence': {'data_completeness': 'Bounded synthetic evidence.',
                                       'evidence_quality': 'Validated published fixture.',
                                       'directly_supported_conclusions': [], 'inferences': [],
                                       'unsupported_questions': [], 'confidence': 'Limited',
                                       'confidence_rationale': 'Offline fixture only.'}}
    return ProviderResult('SUCCEEDED', json.dumps(data, sort_keys=True).encode())


def create_temporary_context(*, scenario: str = 'Baseline', cleanup_after_seconds: float = 305.0):
    """Own one pinned fixture Run; expire and remove it after Context expiry."""
    if cleanup_after_seconds <= 300:
        raise ValueError('Cleanup must follow Context expiry')
    harness = SyntheticHarness()
    try:
        context = harness.issue(scenario)
        timer = Timer(cleanup_after_seconds, harness.close)
        timer.daemon = True
        timer.start()
        return harness, context, timer
    except BaseException:
        harness.close()
        raise


def render_validated(response: dict) -> None:
    """Render only P1-validated content; numbers come from evidence slots."""
    st.success(label('validated'))
    assessment = response['executive_assessment']
    st.subheader('Assessment / 評估')
    st.text(assessment['summary'])
    st.text(assessment['principal_concern'])
    st.caption('Evidence / 依據: ' + ', '.join(assessment['evidence_refs']))
    for key, title in [('observed_facts', 'Observed facts / 已觀察事實'),
                       ('system_identified_drivers', 'Deterministic findings / 系統判定'),
                       ('ai_interpretations', 'AI interpretations / AI 解讀'),
                       ('unverified_hypotheses', 'Unverified hypotheses / 待驗證假設'),
                       ('missing_evidence', 'Missing evidence / 缺少證據')]:
        st.subheader(title)
        for item in response['root_cause_interpretation'][key]:
            st.text(item['text'])
            st.caption('Evidence / 依據: ' + ', '.join(item['evidence_refs']))
    st.subheader('Advisory findings / 建議性發現')
    for finding in response['key_findings']:
        st.caption('Finding / 發現: ' + finding['finding_id'])
        st.text(finding['description'])
        st.caption('Evidence / 依據: ' + ', '.join(finding['evidence_refs']))
        st.caption('Advisory severity / 建議性嚴重程度: ' + finding['severity'])
        st.text(finding['severity_rationale'])
        st.text(finding['potential_operational_impact'])
        for slot in finding['numerical_evidence']:
            st.json({key: slot[key] for key in ('source_ref_id', 'field_name', 'value', 'unit', 'grain')})
    if response['recommendations']:
        st.subheader('Recommendations for human review / 待人工審核建議')
        for item in response['recommendations']:
            st.caption(item['recommendation_id'] + ' · ' + item['priority'])
            for key in ('proposed_action', 'rationale', 'expected_impact', 'trade_offs',
                        'required_validation'):
                st.text(item[key])
            st.caption('Evidence / 依據: ' + ', '.join(item['evidence_refs']))
    if response['decision_trade_offs']:
        st.subheader('Decision trade-offs / 決策取捨')
        for item in response['decision_trade_offs']:
            st.text(item['description'])
            st.caption(item['comparability'] + ' · Evidence / 依據: ' + ', '.join(item['evidence_refs']))
    if response['further_investigation']:
        st.subheader('Further investigation / 後續查證')
        for item in response['further_investigation']:
            for key in ('question', 'reason', 'missing_evidence'):
                st.text(item[key])
    st.subheader('Limitations / 限制')
    limits = response['limitations_and_confidence']
    for key in ('data_completeness', 'evidence_quality'):
        st.text(limits[key])
    for key, title in [('directly_supported_conclusions', 'Direct support / 直接支持'),
                       ('inferences', 'Inferences / 推論')]:
        if limits[key]:
            st.subheader(title)
        for item in limits[key]:
            st.text(item['text'])
            st.caption('Evidence / 依據: ' + ', '.join(item['evidence_refs']))
    if limits['unsupported_questions']:
        st.subheader('Unsupported questions / 未獲支持問題')
        for item in limits['unsupported_questions']:
            st.text(item)
    st.caption('Confidence / 信心程度: ' + limits['confidence'])
    st.text(limits['confidence_rationale'])


def render() -> None:
    st.header(label('title'))
    st.info(label('scope'))
    scenario = st.selectbox(label('scenario'),
                            ['Baseline', 'Demand_Surge', 'Capacity_Disruption', 'Combined_Stress'],
                            key='copilot_synthetic_scenario')
    if st.button(label('start'), key='copilot_start'):
        previous = st.session_state.get('copilot_harness')
        if previous is not None:
            old_timer = st.session_state.get('copilot_cleanup_timer')
            if old_timer is not None:
                old_timer.cancel()
            previous.close()
        try:
            harness, context, timer = create_temporary_context(scenario=scenario)
            st.session_state['copilot_harness'] = harness
            st.session_state['copilot_context'] = context
            st.session_state['copilot_cleanup_timer'] = timer
            for key in ('copilot_outcome', 'copilot_request', 'copilot_approval_ref', 'copilot_result'):
                st.session_state.pop(key, None)
        except (OSError, ValueError, KeyError, TypeError):
            st.error(label('blocked'))
            return
    if st.session_state.get('copilot_harness') is not None and st.button(label('close'), key='copilot_close'):
        timer = st.session_state.pop('copilot_cleanup_timer', None)
        if timer is not None:
            timer.cancel()
        st.session_state['copilot_harness'].close()
        for key in ('copilot_harness', 'copilot_context', 'copilot_outcome',
                    'copilot_request', 'copilot_approval_ref', 'copilot_result'):
            st.session_state.pop(key, None)
        return
    harness = st.session_state.get('copilot_harness')
    context = st.session_state.get('copilot_context')
    if harness is None or context is None:
        return
    if context.scenario != scenario:
        for key in ('copilot_outcome', 'copilot_request', 'copilot_approval_ref', 'copilot_result'):
            st.session_state.pop(key, None)
        st.info(label('start'))
        return
    try:
        harness.verify(context)
    except (OSError, ValueError, KeyError, TypeError):
        st.session_state.pop('copilot_outcome', None)
        st.session_state.pop('copilot_request', None)
        st.session_state.pop('copilot_approval_ref', None)
        st.error(label('blocked'))
        return
    st.caption('Run ID: ' + context.run_id + ' · Scenario: ' + context.scenario)
    if st.button(label('prepare'), key='copilot_prepare'):
        st.session_state['copilot_outcome'] = prepare_brief(harness, context)
        for key in ('copilot_request', 'copilot_approval_ref', 'copilot_result'):
            st.session_state.pop(key, None)
    outcome = st.session_state.get('copilot_outcome')
    if outcome is None:
        return
    if outcome.status != 'VALIDATED' or outcome.review is None:
        st.error(label('blocked'))
        return
    try:
        brief = outcome.review.verify()
    except (ValueError, TypeError):
        st.error(label('blocked'))
        return
    st.subheader(label('review'))
    st.code(outcome.review.canonical_json.decode('utf-8'), language='json')
    st.caption('Brief SHA-256: ' + outcome.review.content_digest)
    st.json({key: {'availability': brief[key]['availability'],
                   'source_refs': [r['source_ref'] for r in brief[key]['records']],
                   'selection': brief[key]['selection']}
             for key in ('risk_analysis', 'capacity_analysis', 'scenario_comparison')})
    gate = local_owner_gate()
    # An explicitly configured test snapshot permits offline digest review only.
    model = os.environ.get('COPILOT_OFFLINE_TEST_SNAPSHOT')
    request = None
    if model:
        try:
            request = build_request(outcome.review, model_snapshot=model,
                                    max_output_tokens=500, timeout_seconds=10)
            st.subheader(label('request'))
            st.code(request.request_digest)
            st.caption('Model snapshot: ' + request.model_snapshot + ' · output limit: 500 · timeout: 10 s')
            st.caption('Production cost ceiling and pricing basis: UNSET. Paid reservation blocked.')
        except (ProviderBlocked, ValueError, TypeError):
            request = None
    if gate is None or request is None:
        st.info(label('unavailable'))
    else:
        st.subheader(label('owner'))
        st.caption(label('ledger') + ': ' + gate.ledger.status())
        reference = st.session_state.get('copilot_approval_ref')
        try:
            valid = gate.approval_status(outcome.review, request, reference)
        except (ApprovalBlocked, ValueError, TypeError):
            valid = False
        with st.form('copilot_owner_form', clear_on_submit=True):
            password = st.text_input(label('password'), type='password', key='copilot_owner_password')
            submitted = st.form_submit_button(label('approve'))
        if submitted:
            try:
                approved = gate.approve(outcome.review, request, password)
                st.session_state['copilot_approval_ref'] = approved.reference
                valid = True
            except (ApprovalBlocked, ValueError, TypeError):
                st.error(label('status') + ': REJECTED')
        st.caption(label('status') + ': ' + ('VALID' if valid else 'NOT APPROVED'))
    if st.button(label('fake'), key='copilot_fake'):
        # Fake Provider is the sole runtime implementation in P4.
        offline_request = request or build_request(outcome.review, model_snapshot='offline-fixture-only',
                                                   max_output_tokens=500, timeout_seconds=10)
        result = FakeProvider(fake_result(outcome.review)).execute(offline_request)
        st.session_state['copilot_result'] = classify_response(result.raw_response, outcome.review,
                                                                provider_status=result.status)
    result = st.session_state.get('copilot_result')
    if result is not None:
        if result.status == 'VALIDATED' and result.response is not None:
            render_validated(result.response)
        elif result.status == 'HUMAN_REVIEW_REQUIRED':
            st.warning(label('review_required'))
        else:
            st.error(label('invalid'))
