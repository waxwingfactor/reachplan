import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from reachplan.bundle import load_inputs, publish, render, verify
from reachplan.cli import main
from reachplan.core import InputError, compute
from importlib.resources import files

class BundleLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = {n:files('reachplan').joinpath('data',n).read_bytes() for n in ('pipes.csv','passes.csv','barriers.csv')}

    def run_cli(self,args):
        stdout,stderr = io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code = main(args)
        return code,stdout.getvalue(),stderr.getvalue()

    def result(self):
        plan = compute(self.inputs,'2026-01-01','2026-03-31')
        out = self.root/'result'
        publish(out,render(plan,self.inputs))
        return plan,out

    def test_example_accounting_and_independent_relocation(self):
        plan,out = self.result()
        self.assertEqual(plan['totals']['unique_verified_length'],'160')
        self.assertEqual(plan['totals']['repeat_length'],'20')
        self.assertEqual(plan['totals']['draft_target_length'],'125')
        self.assertEqual(plan['totals']['review_length'],'35')
        moved = self.root/'moved'
        out.rename(moved)
        self.assertEqual(verify(moved),plan)
        self.assertNotIn(str(self.root),(moved/'plan.json').read_text())

    def test_all_outputs_and_inputs_are_checked(self):
        _,out = self.result()
        for path in list(out.rglob('*')):
            if path.is_file():
                original = path.read_bytes()
                path.write_bytes(original+b' ')
                with self.subTest(file=path.name),self.assertRaises(InputError): verify(out)
                path.write_bytes(original)
        verify(out)

    def test_missing_extra_and_linked_bundle_members(self):
        _,out = self.result()
        path = out/'summary.csv'
        original=path.read_bytes();path.unlink()
        with self.assertRaises(InputError): verify(out)
        path.write_bytes(original)
        (out/'extra.txt').write_text('unexpected')
        with self.assertRaises(InputError): verify(out)
        (out/'extra.txt').unlink()
        if hasattr(Path,'symlink_to'):
            try: (out/'linked').symlink_to(path)
            except OSError: return
            with self.assertRaises(InputError): verify(out)

    def test_existing_destination_refused_without_changes(self):
        plan,out = self.result()
        original = (out/'plan.json').read_bytes()
        with self.assertRaises(InputError): publish(out,{'bad':b'bad'})
        self.assertEqual((out/'plan.json').read_bytes(),original)
        empty=self.root/'empty';empty.mkdir()
        with self.assertRaises(InputError): publish(empty,render(plan,self.inputs))
        self.assertEqual(list(empty.iterdir()),[])

    def test_cli_example_plan_verify_and_closeout(self):
        demo = self.root/'demo';out=self.root/'out'
        self.assertEqual(self.run_cli(['example',str(demo)])[0],0)
        args=['plan','--pipes',str(demo/'pipes.csv'),'--passes',str(demo/'passes.csv'),'--barriers',str(demo/'barriers.csv'),'--since','2026-01-01','--as-of','2026-03-31','--out',str(out)]
        code,stdout,stderr=self.run_cli(args)
        self.assertEqual(code,3);self.assertIn('review_required',stdout);self.assertEqual(stderr,'')
        self.assertEqual(self.run_cli(['verify',str(out)])[0],0)
        self.assertEqual(self.run_cli(args)[0],2)
        # A draft is not completion: only newly accepted field extents change it.
        with (demo/'passes.csv').open('a') as stream:
            for i,p in enumerate(json.loads((out/'plan.json').read_text())['pipes']):
                stream.write(f"C{i},{p['pipe_id']},2026-03-31,from,0,{p['length']},verified,Constructed completed closeout\n")
        closed=self.root/'closed';args[-1]=str(closed)
        # Prior attempted work still requests review until explicitly corrected
        # by the data owner; coverage itself is complete.
        self.assertEqual(self.run_cli(args)[0],3)
        result=verify(closed)
        self.assertEqual(result['totals']['remaining_length'],'0')
        self.assertEqual(result['status'],'review_required')

    def test_header_only_barriers_and_missing_inputs(self):
        demo=self.root/'demo';self.run_cli(['example',str(demo)])
        loaded=load_inputs(demo/'pipes.csv',demo/'passes.csv',None)
        self.assertEqual(loaded['barriers.csv'],b'barrier_id,pipe_id,start,end,reason\n')
        with self.assertRaises(InputError): load_inputs(demo/'missing.csv',demo/'passes.csv',None)

    def test_invalid_input_creates_no_output(self):
        demo=self.root/'demo';self.run_cli(['example',str(demo)])
        (demo/'pipes.csv').write_text('wrong\n')
        out=self.root/'result'
        code,_,stderr=self.run_cli(['plan','--pipes',str(demo/'pipes.csv'),'--passes',str(demo/'passes.csv'),'--since','2026-01-01','--as-of','2026-03-31','--out',str(out)])
        self.assertEqual(code,2);self.assertIn('exact header',stderr);self.assertFalse(out.exists())

    def test_csv_formula_escape_and_markdown_escape(self):
        inputs=dict(self.inputs)
        inputs['barriers.csv']=b'barrier_id,pipe_id,start,end,reason\nB1,P300,30,35,=2+2 <script> [a] | x\n'
        data=render(compute(inputs,'2026-01-01','2026-03-31'),inputs)
        self.assertIn(b'&lt;script&gt;',data['report.md'])
        self.assertNotIn(b'<script>',data['report.md'])
        self.assertIn(b'\\[a\\]',data['report.md'])
        from reachplan.bundle import csv_bytes
        self.assertIn(b"'=SUM(1)",csv_bytes(['reason'],[['=SUM(1)']]))

if __name__=='__main__': unittest.main()

class RoundTripPrecision(unittest.TestCase):
    def test_targets_fit_the_input_precision_contract(self):
        from reachplan.core import number
        inputs={
            'pipes.csv':b'pipe_id,from_node,to_node,length,unit,from_access,to_access,from_reach,to_reach\nP,A,B,0.003,m,yes,yes,0.002,0.002\n',
            'passes.csv':b'pass_id,pipe_id,date,origin,start,end,status,notes\n',
            'barriers.csv':b'barrier_id,pipe_id,start,end,reason\n'}
        plan=compute(inputs,'2026-01-01','2026-01-31')
        for s in plan['pipes'][0]['setups']:
            for t in s['targets']:
                number(t['start'],'roundtrip start');number(t['end'],'roundtrip end')
        self.assertEqual(plan['totals']['draft_target_length'],'0.003')

class CloseoutReview(unittest.TestCase):
    def test_followup_dates_and_explicit_attempt_review(self):
        inputs={
            'pipes.csv':b'pipe_id,from_node,to_node,length,unit,from_access,to_access,from_reach,to_reach\nP,A,B,10,m,yes,yes,10,10\n',
            'passes.csv':b'pass_id,pipe_id,date,origin,start,end,status,notes\nR,P,2026-03-01,from,0,10,attempted,Unverified extent\nC,P,2026-04-01,from,0,10,verified,Accepted later\n',
            'barriers.csv':b'barrier_id,pipe_id,start,end,reason\n'}
        old=compute(inputs,'2026-01-01','2026-03-31')
        self.assertEqual(old['totals']['remaining_length'],'10')
        new=compute(inputs,'2026-01-01','2026-04-01')
        self.assertEqual(new['totals']['remaining_length'],'0')
        self.assertEqual(new['status'],'review_required')
        inputs['passes.csv']=inputs['passes.csv'].replace(b'attempted,Unverified extent',b'reviewed_attempt,Reviewed current constraints by responsible operator')
        final=compute(inputs,'2026-01-01','2026-04-01')
        self.assertEqual(final['status'],'coverage_complete')
        self.assertEqual(final['excluded_passes'][0]['reason'],'reviewed_attempt')
        inputs['passes.csv']=inputs['passes.csv'].replace(b'reviewed_attempt,Reviewed current constraints by responsible operator',b'reviewed_attempt,')
        with self.assertRaises(InputError): compute(inputs,'2026-01-01','2026-04-01')
