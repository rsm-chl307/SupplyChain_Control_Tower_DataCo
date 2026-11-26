"""Local synthetic Decision Copilot view. Fake Provider only; no paid dispatch."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Timer
import time
import streamlit as st

from dashboard.i18n import current_locale
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider_base import build_request, FakeProvider, ProviderResult, ProviderBlocked
from src.ai_copilot.cloud_access import (
    AccessConfigurationError, ai_access_authorized, authenticate_ai_access,
)
from src.ai_copilot.cloud_ai_service import CloudAIRejected, CloudAIService
from src.ai_copilot.cloud_question import CloudOpenAIProvider
from src.ai_copilot.credential_provider import credential_provider


LABELS = {
    "title": ("Decision Copilot — synthetic preview", "決策輔助 — 合成資料預覽"),
    "scope": ("Pinned synthetic fixture only. AI advice is non-executing; no production Run access.",
              "僅使用固定合成測試資料。AI 建議不會自行執行，也不存取正式 Run。"),
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
    "ai_password": ("AI Access Password", "AI 存取密碼"),
    "ai_unlock": ("Unlock AI preview", "解鎖 AI 預覽"),
    "ai_denied": ("AI access denied.", "AI 存取遭拒。"),
    "ai_locked": ("Too many attempts; this session is temporarily locked.", "嘗試次數過多；此工作階段暫時鎖定。"),
    "ai_unconfigured": ("AI access is not configured; planning remains available.", "尚未設定 AI 存取；規劃功能仍可使用。"),
    "ai_question": ("Supply chain question", "供應鏈問題"),
    "ai_ask": ("Ask Fake Provider", "詢問模擬供應商"),
    "ai_ask_live": ("Ask AI", "詢問 AI"),
    "ai_usage": ("Provider-reported usage", "供應商回報用量"),
    "ai_estimate": ("Estimated reservation (USD; not billed charge)", "預估保留成本（美元；非實際帳單）"),
    "ai_query_invalid": ("Question or context is invalid.", "問題或分析內容無效。"),
    "ai_input_limit": ("The AI request is too large; shorten the question or context.",
                       "AI 請求過大；請縮短問題或分析內容。"),
    "ai_output_limit": ("The AI response exceeded its output limit; no answer was accepted.",
                        "AI 回應超出輸出上限；系統未採納答案。"),
    "ai_config_error": ("AI configuration is unavailable; planning remains available.",
                        "AI 設定不可用；規劃功能仍可使用。"),
    "ai_rate_limited": ("AI request limit reached. Please wait before trying again.",
                        "已達 AI 請求限制，請稍後再試。"),
    "ai_budget_limited": ("AI usage limit reached for this session.", "此工作階段已達 AI 使用量上限。"),
    "ai_provider_failed": ("AI response was unavailable or uncertain; it was not retried.",
                           "AI 回應不可用或結果不明；系統未重試。"),
    "review_required": ("Unstructured quantity requires human review; no advisory is displayed.",
                        "未結構化數量主張須由人工審核；不顯示建議。"),
}


def label(key: str) -> str:
    return LABELS[key][1 if current_locale() == 'zh-TW' else 0]


def _ai_failure_label(code: str) -> str:
    if code in {'DUPLICATE_OR_TOO_FAST', 'RATE_LIMIT_EXCEEDED', 'PROVIDER_RATE_LIMIT'}:
        return label('ai_rate_limited')
    if code == 'USAGE_BUDGET_EXCEEDED':
        return label('ai_budget_limited')
    if code == 'ACCESS_DENIED':
        return label('ai_denied')
    if code == 'INPUT_LIMIT_EXCEEDED':
        return label('ai_input_limit')
    if code == 'OUTPUT_LIMIT_EXCEEDED':
        return label('ai_output_limit')
    if code in {'CONFIGURATION_UNAVAILABLE', 'MISSING_API_KEY', 'INVALID_CONFIGURATION'}:
        return label('ai_config_error')
    if code == 'CONTEXT_INVALID':
        return label('ai_query_invalid')
    return label('ai_provider_failed')


def ai_settings():
    """Resolve Cloud configuration only after a user submits the password."""
    return st.secrets


@st.cache_resource
def cloud_ai_service() -> CloudAIService:
    """Share only process-local limits; no credential or business data is cached."""
    return CloudAIService()


def cloud_question_execute(review, settings):
    """Select the backend provider explicitly; the default remains Fake."""
    if settings.get('AI_REAL_PROVIDER_ENABLED', False) is True:
        return CloudOpenAIProvider(
            credential_provider('streamlit_cloud', secrets=settings), review,
            enabled=True).execute
    return lambda bound: FakeProvider(fake_result(review, bound.question)).execute(
        bound.provider_request)


def _submit_ai_access() -> None:
    """Verify during the callback, then remove the password before rendering."""
    password = st.session_state.get('copilot_ai_password', '')
    now = time.time()
    st.session_state.pop('_ai_access_feedback', None)
    try:
        settings = ai_settings()
        allowed = authenticate_ai_access(password, settings, st.session_state, now=now)
    except AccessConfigurationError:
        st.session_state['_ai_access_feedback'] = 'ai_unconfigured'
        allowed = False
    finally:
        st.session_state.pop('copilot_ai_password', None)
    if allowed:
        st.session_state.pop('_ai_access_feedback', None)
    elif st.session_state.get('_ai_access_feedback') != 'ai_unconfigured':
        st.session_state['_ai_access_feedback'] = (
            'ai_locked' if st.session_state.get('_ai_access_locked_until', 0) > now else 'ai_denied'
        )


def _clear_expired_ai_context() -> None:
    """Remove prior advisory state when authentication is no longer valid."""
    timer = st.session_state.pop('copilot_cleanup_timer', None)
    if timer is not None:
        timer.cancel()
    harness = st.session_state.pop('copilot_harness', None)
    if harness is not None:
        try:
            harness.close()
        except (OSError, ValueError):
            pass
    for key in ('copilot_context', 'copilot_outcome', 'copilot_request',
                'copilot_approval_ref', 'copilot_result', 'copilot_chat', 'copilot_last_usage'):
        st.session_state.pop(key, None)


def _ai_access() -> bool:
    now = time.time()
    if ai_access_authorized(st.session_state, ai_settings(), now=now):
        return True
    if any(key in st.session_state for key in ('copilot_harness', 'copilot_chat', 'copilot_result')):
        _clear_expired_ai_context()
    st.session_state.pop('_ai_access_until', None)
    st.session_state.pop('_ai_access_grant', None)
    st.session_state.pop('_ai_access_nonce', None)
    if st.session_state.get('_ai_access_locked_until', 0) > now:
        st.warning(label('ai_locked'))
        return False
    feedback = st.session_state.pop('_ai_access_feedback', None)
    if feedback in {'ai_denied', 'ai_unconfigured'}:
        st.warning(label(feedback))
    with st.form('copilot_ai_access', clear_on_submit=True):
        st.text_input(label('ai_password'), type='password', key='copilot_ai_password')
        st.form_submit_button(label('ai_unlock'), on_click=_submit_ai_access)
    return False


def local_owner_gate() -> object | None:
    """Default-deny local preview gate; environment flags are not identity."""
    if (os.environ.get('COPILOT_LOCAL_OWNER_MODE') != '1'
            or os.environ.get('STREAMLIT_SHARING_MODE')
            or st.get_option('server.address') not in {'127.0.0.1', 'localhost', '::1'}):
        return None
    path = os.environ.get('COPILOT_LEDGER_PATH')
    if not path or not Path(path).is_absolute():
        return None
    try:
        from dashboard.copilot_local_gate import create_local_gate
    except ModuleNotFoundError:
        return None
    return create_local_gate(path)


def fake_result(review, question: str | None = None) -> ProviderResult:
    """Fixed advisory text with a copied evidence slot; no calculation or tool."""
    brief = review.verify()
    ref = brief['run_context']['source_ref']
    capacity = brief['capacity_analysis']['records'][0]
    capacity_source = next(source for source in brief['source_manifest']
                           if source['source_ref_id'] == capacity['source_ref'])
    capacity_slot = {'source_ref_id': capacity['source_ref'], 'field_name': 'Capacity_Utilization',
                     'value': capacity['values']['Capacity_Utilization'], 'unit': 'ratio',
                     'grain': capacity_source['native_grain']}
    topic = None
    if question is not None:
        lowered = question.lower()
        if any(word in lowered for word in ('capacity', 'bottleneck', '產能', '瓶頸')):
            topic = 'capacity_analysis'
        elif any(word in lowered for word in ('service', '服務')):
            topic = 'service_analysis'
        elif any(word in lowered for word in ('inventory', 'replenish', '庫存', '補貨')):
            topic = 'inventory_analysis'
        elif any(word in lowered for word in ('demand', '需求')):
            topic = 'risk_analysis'
        elif any(word in lowered for word in ('root cause', '根因')):
            topic = 'root_cause_evidence'
        elif any(word in lowered for word in ('scenario', '情境')):
            topic = 'scenario_comparison'
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
    if question is not None:
        section = brief.get(topic, {}) if topic else {}
        records = section.get('records', []) if isinstance(section, dict) else []
        if records:
            evidence_ref = records[0]['source_ref']
            data['executive_assessment'] = {
                'summary': 'The requested topic has bounded synthetic evidence for review.',
                'principal_concern': 'This Fake Provider cannot establish a business conclusion.',
                'evidence_refs': [evidence_ref],
            }
            data['key_findings'] = [{
                'finding_id': 'F1', 'description': 'Inspect the cited analytical record.',
                'evidence_refs': [evidence_ref], 'numerical_evidence': [],
                'potential_operational_impact': 'Further interpretation requires validated analysis.',
                'severity': 'Low', 'severity_rationale': 'Synthetic preview only.',
            }]
        else:
            data['executive_assessment'] = {
                'summary': 'The requested topic lacks sufficient validated evidence.',
                'principal_concern': 'No supported conclusion can be made.',
                'evidence_refs': [ref],
            }
            data['key_findings'] = []
            data['limitations_and_confidence']['unsupported_questions'] = [
                'The requested analysis is unavailable in this validated Brief.'
            ]
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
    if not _ai_access():
        return
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
            for key in ('copilot_outcome', 'copilot_request', 'copilot_approval_ref', 'copilot_result', 'copilot_chat', 'copilot_last_usage'):
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
                    'copilot_request', 'copilot_approval_ref', 'copilot_result', 'copilot_chat', 'copilot_last_usage'):
            st.session_state.pop(key, None)
        return
    harness = st.session_state.get('copilot_harness')
    context = st.session_state.get('copilot_context')
    if harness is None or context is None:
        return
    if context.scenario != scenario:
        for key in ('copilot_outcome', 'copilot_request', 'copilot_approval_ref', 'copilot_result', 'copilot_chat', 'copilot_last_usage'):
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
        for key in ('copilot_request', 'copilot_approval_ref', 'copilot_result', 'copilot_chat', 'copilot_last_usage'):
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
        from dashboard.copilot_local_gate import render_local_owner
        render_local_owner(st, gate, outcome.review, request, label)
    if st.button(label('fake'), key='copilot_fake'):
        st.session_state.pop('copilot_last_usage', None)
        try:
            answer = cloud_ai_service().ask(
                st.session_state, ai_settings(), outcome.review, 'Review synthetic evidence.',
                lambda bound: FakeProvider(fake_result(outcome.review)).execute(bound.provider_request))
            st.session_state['copilot_result'] = answer.outcome
        except CloudAIRejected as exc:
            st.session_state.pop('copilot_result', None)
            st.error(_ai_failure_label(exc.code))
    question = st.text_area(label('ai_question'), key='copilot_question', max_chars=500)
    settings = ai_settings()
    ask_label = 'ai_ask_live' if settings.get('AI_REAL_PROVIDER_ENABLED', False) is True else 'ai_ask'
    if st.button(label(ask_label), key='copilot_ask'):
        previous = st.session_state.get('copilot_chat', [])
        turns = tuple((item['question'], item['outcome'].response['executive_assessment']['summary'])
                      for item in previous[-3:] if item['outcome'].status == 'VALIDATED')
        try:
            answer = cloud_ai_service().ask(
                st.session_state, settings, outcome.review, question,
                cloud_question_execute(outcome.review, settings), prior_turns=turns)
            st.session_state['copilot_result'] = answer.outcome
            st.session_state['copilot_last_usage'] = {
                'model_id': answer.model_id,
                'provider_request_id': answer.provider_request_id,
                'provider_usage': answer.provider_usage,
                'estimated_usd_reserved': str(answer.estimated_usd_reserved)
                if answer.estimated_usd_reserved is not None else None,
            }
            st.session_state['copilot_chat'] = previous[-2:] + [
                {'question': question.strip(), 'digest': answer.request_digest, 'outcome': answer.outcome}
            ]
        except CloudAIRejected as exc:
            st.session_state.pop('copilot_result', None)
            st.session_state.pop('copilot_last_usage', None)
            st.error(_ai_failure_label(exc.code))
    for item in st.session_state.get('copilot_chat', []):
        st.caption('Question / 問題: ' + item['question'])
        if item['outcome'].status == 'VALIDATED':
            st.text(item['outcome'].response['executive_assessment']['summary'])
    result = st.session_state.get('copilot_result')
    accounting = st.session_state.get('copilot_last_usage')
    if result is not None and isinstance(accounting, dict):
        reported = accounting.get('provider_usage')
        if isinstance(reported, dict):
            st.caption(f"{label('ai_usage')}: input={reported['input_tokens']}, output={reported['output_tokens']}")
        if accounting.get('estimated_usd_reserved') is not None:
            st.caption(f"{label('ai_estimate')}: {accounting['estimated_usd_reserved']}")
    if result is not None:
        if result.status == 'VALIDATED' and result.response is not None:
            render_validated(result.response)
        elif result.status == 'HUMAN_REVIEW_REQUIRED':
            st.warning(label('review_required'))
        else:
            st.error(label('invalid'))
