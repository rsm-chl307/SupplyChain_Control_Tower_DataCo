"""Offline semantic/evidence validation; only this module issues review results."""
from dataclasses import dataclass,field
import hashlib,json,re,weakref
from src.ai_brief.contract import *
from src.ai_brief.builder import DraftBrief,build_draft

_REVIEWS={}

@dataclass(frozen=True)
class ValidatedBrief:
    canonical_json: bytes=field(repr=False)
    content_digest: str
    _draft: DraftBrief=field(repr=False)

    def verify(self):
        registered=_REVIEWS.get(id(self))
        if not registered or registered[0]() is not self or registered[1] != (self.canonical_json,self.content_digest) or registered[2] is not self._draft:
            raise BriefRejected('Review result is unissued or changed; validate again')
        self._draft._bundle.revalidate()
        if hashlib.sha256(self.canonical_json).hexdigest()!=self.content_digest:
            raise BriefRejected('Content digest changed')
        return json.loads(self.canonical_json)


def _privacy(value):
    bad=re.compile(r'(?i)(https?://|javascript:|<|>|@|[A-Za-z]:\\|/tmp/|/workspace/|(?:ignore|override).{0,40}(?:instruction|prompt)|system prompt|api[_ -]?key|password|secret|```)',re.S)
    def scan(v):
        if type(v) is str and bad.search(v):raise BriefRejected('Unsafe text or privacy marker; content not previewed')
        if type(v) is dict:
            for k,x in v.items():scan(k);scan(x)
        if type(v) is list:
            for x in v:scan(x)
    scan(value)


def validate_draft(draft: DraftBrief) -> ValidatedBrief:
    if type(draft) is not DraftBrief:raise BriefRejected('Offline DraftBrief required')
    b=draft.as_dict()
    if b.get('brief_status')!='DRAFT':raise BriefRejected('Only an unvalidated DRAFT can enter validation')
    validate_structure(b)
    _privacy(b)
    draft._bundle.revalidate()
    expected=build_draft(draft._bundle,max_records=draft.max_records).as_dict()
    # Comparison to a freshly source-backed projection detects changed values,
    # identities, grains, stock selections, units, reasons and privacy aliases.
    # No KPI is recalculated here; only existing deterministic views are reused.
    if canonical_bytes(b)!=canonical_bytes(expected):
        raise BriefRejected('Brief does not match its authorized evidence, selection or definitions')
    refs={s['source_ref_id']:s for s in b['source_manifest']}
    if len(refs)!=len(b['source_manifest']):raise BriefRejected('Duplicate source reference')
    for name in ['run_context','data_scope']:
        r=b[name]
        if r['source_ref'] not in refs or set(refs[r['source_ref']]['field_names'])!=set(r)-{'source_ref'}:
            raise BriefRejected('Context/scope provenance missing')
    for section in SECTIONS:
        s=b[section]
        if s['source_refs']!=[r['source_ref'] for r in s['records']]:raise BriefRejected('Section references disagree')
        for r in s['records']:
            ref=refs.get(r['source_ref'])
            if ref is None or set(ref['field_names'])!=set(r['values']):raise BriefRejected('Business field provenance missing')
    b['brief_status']='VALIDATED'
    validate_structure(b)
    raw=canonical_bytes(b)
    result=ValidatedBrief(raw,hashlib.sha256(raw).hexdigest(),draft)
    _REVIEWS[id(result)]=(weakref.ref(result,lambda _,key=id(result):_REVIEWS.pop(key,None)),(raw,result.content_digest),draft)
    return result


def resolve_source(review: ValidatedBrief,source_ref: str,field_name: str):
    """Local provenance lookup. No path or arbitrary source reads."""
    b=review.verify()
    source=next((r for r in b['source_manifest'] if r['source_ref_id']==source_ref),None)
    if source is None or field_name not in source['field_names']:raise BriefRejected('Unresolved source field')
    # Return exact displayed scalar and its hash-bound local locator. The source
    # snapshot/definition remain in the private bundle; no reverse ID map leaks.
    for key in ['run_context','data_scope']:
        if b[key]['source_ref']==source_ref:return b[key][field_name],source
    for key in SECTIONS:
        for record in b[key]['records']:
            if record['source_ref']==source_ref:return record['values'][field_name],source
    raise BriefRejected('Source reference has no projected value')
