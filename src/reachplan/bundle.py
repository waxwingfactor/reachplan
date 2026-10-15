"""Portable, self-contained result bundles; verification recomputes all outputs."""
from __future__ import annotations
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
from .core import HEADERS, MAX_BYTES, InputError, compute

DEFAULT_BARRIERS = (','.join(HEADERS['barriers.csv'])+'\n').encode()

MAX_RESULT_BYTES = 100_000_000

def read_file(path: Path, limit: int = MAX_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise InputError(f"{path.name}: expected regular file, not symlink")
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data) > limit:
        raise InputError(f"{path.name}: exceeds {limit} bytes")
    return data

def load_inputs(pipes: Path, passes: Path, barriers: Path | None) -> dict[str, bytes]:
    return {'pipes.csv': read_file(pipes), 'passes.csv': read_file(passes),
            'barriers.csv': read_file(barriers) if barriers else DEFAULT_BARRIERS}

def json_bytes(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=True)+'\n').encode()

def csv_bytes(header, records) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(header)
    for record in records:
        # Prefix spreadsheet formula leaders in free text. JSON retains originals.
        writer.writerow(["'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in record])
    return stream.getvalue().encode('utf-8')

def md(value) -> str:
    return html.escape(str(value)).replace('\\', '\\\\').replace('|', '\\|').replace('`', '\\`').replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')

def render(plan: dict, inputs: dict[str, bytes]) -> dict[str, bytes]:
    fields = ['pipe_id','length','verified_pass_length','unique_verified_length','repeat_length','remaining_length','draft_target_length','review_length']
    summary = [[p[k] for k in fields] for p in plan['pipes']]
    setups, review = [], []
    for p in plan['pipes']:
        for s in p['setups']:
            for t in s['targets']:
                setups.append([p['pipe_id'],s['endpoint'],s['node'],t['start'],t['end'],t['length'],s['travel_from_endpoint'],s['status']])
        for t in p['review_intervals']:
            review.append([p['pipe_id'],t['start'],t['end'],t['length'],';'.join(p['review_reasons'])])
    c, totals = plan['campaign'], plan['totals']
    lines = ['# ReachPlan residual work plan', '',
        f"Campaign: {c['since']} through {c['as_of']} inclusive. All distances: **{c['unit']}**.", '',
        f"Result: **{plan['status']}**. These are geometric draft setups requiring field review.", '',
        '| Network length | Unique verified | Repeated pass length | Remaining | Draft targets | Needs review |',
        '| ---: | ---: | ---: | ---: | ---: | ---: |',
        '| '+' | '.join(totals[k] for k in ('length','unique_verified_length','repeat_length','remaining_length','draft_target_length','review_length'))+' |', '',
        'Verified means the input operator explicitly accepted that interval as cleaned. Attempted work contributes no coverage. Draft work never becomes verified automatically.', '',
        'Travel includes intervening already-cleaned distance. Current barriers stop travel from either end. The targets below are canonical chainage measured from the named from-node; travel is measured from the selected access node.', '']
    for p in plan['pipes']:
        lines += [f"## {p['pipe_id']}: {p['from_node']} → {p['to_node']}", '',
            f"Length {p['length']}; unique verified {p['unique_verified_length']}; remaining {p['remaining_length']} {c['unit']}.", '']
        for s in p['setups']:
            ranges = ', '.join(t['start']+'–'+t['end'] for t in s['targets'])
            lines += [f"- Draft setup at **{s['node']}** ({s['endpoint']}): target chainage **{ranges}**; target length {s['target_length']}; farthest travel from access {s['travel_from_endpoint']} {c['unit']}."]
        for t in p['review_intervals']:
            lines += [f"- **Review** chainage {t['start']}–{t['end']} ({t['length']} {c['unit']}): outside current geometric reach. Resolve access, reach or barriers before assigning work."]
        for b in p['barriers']:
            lines += [f"- Current barrier {b['barrier_id']} at {b['start']}–{b['end']}: {md(b['reason'])}."]
        if p['unverified_attempt_ids']:
            lines += ['- Review unverified attempts: '+', '.join(p['unverified_attempt_ids'])+'. They do not count as cleaned or automatically create a barrier.']
        if not p['setups'] and not p['review_intervals']:
            lines += ['No remaining target in this campaign.']
        lines += ['']
    lines += ['## Excluded records', '', '| Pass | Pipe | Reason |', '| --- | --- | --- |']
    for p in plan['excluded_passes']:
        lines.append(f"| {p['pass_id']} | {p['pipe_id']} | {p['reason']} |")
    lines += ['', '## Review and close out', '',
        'Check actual conditions, safe access, equipment suitability and current barriers using your approved procedures. This tool supplies no hydraulic, pressure, nozzle, traffic, confined-space, safety or regulatory determination.', '',
        'After work, append separate operator-verified extents to passes.csv. A responsible person may acknowledge an investigated attempt by changing it to reviewed_attempt with a review note; this adds no coverage. Generate a new bundle. Keep the old bundle. Keep the campaign start and advance the end date to include the actual follow-up date. Compare archived bundles using their stated date windows.', '',
        'The inputs/ directory contains exact input snapshots. plan.json contains canonical intervals, included/excluded record IDs and input SHA-256 hashes. Run reachplan verify on this directory after moving it; verification detects inconsistency, not authenticity.', '']
    result = {f'inputs/{n}': b for n,b in inputs.items()}
    result.update({'plan.json': json_bytes(plan), 'summary.csv': csv_bytes(fields,summary),
        'setups.csv': csv_bytes(['pipe_id','endpoint','node','target_start','target_end','target_length','travel_from_endpoint','status'],setups),
        'review.csv': csv_bytes(['pipe_id','start','end','length','reasons'],review), 'report.md': ('\n'.join(lines)).encode()})
    result['manifest.json'] = json_bytes({'schema_version':1,'sha256':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(result.items())}})
    return result

def publish(output: Path, files: dict[str, bytes]) -> None:
    """Validate/render before this call. Refuse existing destination, even empty.

    Stage bytes first, reserve destination exclusively, move files, manifest last.
    A process crash can leave an incomplete bundle; verify rejects it.
    """
    if output.exists() or output.is_symlink():
        raise InputError('output already exists; choose a new directory')
    if not output.parent.is_dir():
        raise InputError('output parent directory must exist')
    with tempfile.TemporaryDirectory(prefix='.reachplan-', dir=output.parent) as temp:
        stage = Path(temp)
        for name, data in files.items():
            path = stage/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        output.mkdir()  # exclusive reservation: never replace an existing directory
        try:
            names = sorted(files, key=lambda n:(n=='manifest.json',n))
            for name in names:
                target = output/name
                target.parent.mkdir(parents=True,exist_ok=True)
                os.replace(stage/name,target)
        except BaseException:
            shutil.rmtree(output)
            raise

def verify(bundle: Path) -> dict:
    if bundle.is_symlink() or not bundle.is_dir():
        raise InputError('bundle must be a regular directory, not symlink')
    # A closed file inventory prevents ignored extra results or linked inputs.
    expected = {'manifest.json','plan.json','summary.csv','setups.csv','review.csv','report.md',*(f'inputs/{n}' for n in HEADERS)}
    found = set()
    for p in bundle.rglob('*'):
        if p.is_symlink():
            raise InputError('bundle contains a symlink')
        if p.is_file(): found.add(p.relative_to(bundle).as_posix())
        elif not p.is_dir(): raise InputError('bundle contains a special file')
    if found != expected:
        raise InputError('bundle file inventory differs from the supported format')
    try:
        saved = json.loads(read_file(bundle/'plan.json', MAX_RESULT_BYTES))
        campaign = saved['campaign']
        inputs = {n:read_file(bundle/'inputs'/n) for n in HEADERS}
        recalculated = compute(inputs, campaign['since'], campaign['as_of'])
        rendered = render(recalculated, inputs)
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        raise InputError(f'bundle is invalid: {exc}') from exc
    for name, data in rendered.items():
        if read_file(bundle/name, MAX_RESULT_BYTES) != data:
            raise InputError(f'bundle verification failed: {name} does not match recomputed result')
    return recalculated
