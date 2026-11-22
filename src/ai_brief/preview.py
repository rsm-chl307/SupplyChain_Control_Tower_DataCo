"""Safe, exact-content offline Markdown preview, no UI or file writes."""
import json
from src.ai_brief.contract import BriefRejected,SECTIONS
from src.ai_brief.validation import ValidatedBrief

MAX_PREVIEW_BYTES=65536

def preview(review: ValidatedBrief) -> str:
    if type(review) is not ValidatedBrief:raise BriefRejected('Validator-issued Brief required')
    b=review.verify()
    parts=['# Offline AI Analysis Brief','',f"Digest: {review.content_digest}",'',
           'Local synthetic evidence only. No AI interpretation, provider call, or action execution.','']
    for key in SECTIONS:
        s=b[key];sel=s['selection']
        parts += ['## '+key,'',s['availability']+': '+s['reason'],'',
                  f"Selection: {sel['returned_rows']} of {sel['total_rows']} candidate records; truncated={sel['truncated']}.",'',
                  '| Record | Source reference |','|---|---|']
        for r in s['records']:parts.append('| '+r['kind']+' | '+r['source_ref']+' |')
        parts.append('')
    # The complete Brief is shown, not a separate lossy narrative. JSON encodes
    # string newlines and backslashes; privacy validation rejects HTML/links/fences.
    parts += ['## Exact validated content','', '```json',json.dumps(b,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False),'```','']
    text='\n'.join(parts)
    if len(text.encode())>MAX_PREVIEW_BYTES:raise BriefRejected('Preview exceeds 64 KiB; choose a smaller bounded selection')
    return text
