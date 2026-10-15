"""Exercise built wheel/sdist in fresh venvs outside the checkout. CI helper."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

def run(args,cwd,env,expected=0):
    proc=subprocess.run([str(a) for a in args],cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if proc.returncode != expected:
        raise RuntimeError(f'{args[0:3]} returned {proc.returncode}, expected {expected}:\n{proc.stdout}')
    return proc.stdout

def check(dist):
    env=dict(os.environ)
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    env['PYTHONNOUSERSITE']='1';env['PIP_DISABLE_PIP_VERSION_CHECK']='1'
    artifacts=sorted(dist.glob('*.whl'))+sorted(dist.glob('*.tar.gz'))
    if len(artifacts)!=2: raise RuntimeError('expected one wheel and one source archive')
    with tempfile.TemporaryDirectory(prefix='reachplan-distribution-') as temp:
        base=Path(temp)
        for i,artifact in enumerate(artifacts):
            root=base/str(i);root.mkdir();venv=root/'venv'
            run([sys.executable,'-m','venv',venv],root,env)
            py=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            if artifact.suffix=='.whl':
                run([py,'-m','pip','install','--no-index','--no-deps',artifact],root,env)
            else:
                run([py,'-m','pip','install','--no-deps',artifact],root,env)
                with tarfile.open(artifact) as tar:
                    names=tar.getnames()
                    for suffix in ('docs/contracts.md','tests/test_independent.py','examples/campaign/pipes.csv'):
                        if not any(n.endswith('/'+suffix) for n in names): raise RuntimeError('sdist missing '+suffix)
            module=run([py,'-I','-c','import reachplan; print(reachplan.__file__)'],root,env).strip()
            if not Path(module).resolve().is_relative_to(venv.resolve()): raise RuntimeError('source import leakage')
            run([py,'-I','-m','reachplan','example','demo'],root,env)
            args=[py,'-I','-m','reachplan','plan','--pipes','demo/pipes.csv','--passes','demo/passes.csv','--barriers','demo/barriers.csv','--since','2026-01-01','--as-of','2026-03-31','--out','result']
            run(args,root,env,expected=3)
            plan=json.loads((root/'result/plan.json').read_text())
            assert plan['totals']['unique_verified_length']=='160'
            assert plan['totals']['review_length']=='35'
            shutil.rmtree(root/'demo');(root/'result').rename(root/'relocated')
            run([py,'-I','-m','reachplan','verify','relocated'],root,env)
            with (root/'relocated/summary.csv').open('a') as stream: stream.write('tampered\n')
            run([py,'-I','-m','reachplan','verify','relocated'],root,env,expected=2)
            print(artifact.name+': fresh installation, example, status, relocation and tamper checks passed')

if __name__=='__main__': check(Path(sys.argv[1]).resolve())
