import ast,copy,hashlib,io,json,shutil,subprocess,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from evidence_index import FORMAT,build_index,load_index
from evidence_index import file_notices,recover_files
from repeat import assert_repeat
from repackage_repeat import repackage
from extract_log_evidence import extract
from run import REFERENCE,verify_bundle
from run import publish_complete_evidence

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'
BUSINESS_COMMIT='5660bc7cedc30c910811691c16b0ef1f067068a3'

class RepeatIndexRegression(unittest.TestCase):
    def tree(self,root):
        phases={}
        coverage={'reference':REFERENCE,'groups':[{**row,'status':'FAIL','complete':False,'observed_revision':2,'reason':'Synthetic refused probe','evidence':row['case']+'.json'} for row in verify_bundle(FIXTURES)['requirements']]}
        for phase in ('primary','repeat'):
            directory=root/phase;directory.mkdir();(directory/'coverage.json').write_text(json.dumps(coverage))
            for name in ('build-evidence','benchmark','CO00-gate','TAX01-W-gate','smoke'):(directory/(name+'.json')).write_text('{}')
            (directory/'build-evidence.json').write_text(json.dumps({'lab_commit':BUSINESS_COMMIT}))
            for row in coverage['groups']:(directory/(row['case']+'.json')).write_text(json.dumps({'case':row['case'],'reference':REFERENCE,'revision':2,'complete':False,'status':'FAIL','error':'Synthetic reviewer test; no ERP execution','full_probe':{'before':{'native_id':7},'response':{'error':'Causal refusal'},'after':{'native_id':7}}}))
            (directory/'raw.csv').write_text('operation,sample\nsearch,0\n');(directory/'native-console.log').write_text('Complete opaque diagnostic bytes\n')
            phases[phase]=(directory,directory/'smoke.json')
        restore=root/'restore.json';restore.write_text('{}');index=build_index(root,phases,restore);index.update(reference=REFERENCE,status='PASS')
        return index
    def test_index_only_pass_label_cannot_establish_repetition(self):
        with self.assertRaises(AssertionError):assert_repeat({'format':FORMAT,'reference':REFERENCE,'status':'PASS','phases':{}},FIXTURES)
    def test_all_case_files_and_opaque_evidence_are_loaded_before_native_assertions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);index=self.tree(root);payload,receipt=load_index(index,root)
            self.assertEqual(len(payload['primary']['groups']),34);self.assertEqual(len(payload['repeat']['groups']),34)
            self.assertEqual(payload['repeat']['groups']['CO00-NATIVE']['full_probe']['response']['error'],'Causal refusal')
            self.assertGreater(receipt['files_loaded'],80);self.assertTrue(receipt['all_hashes_verified'])
            self.assertNotIn('full_probe',json.dumps(index));self.assertLess(len(json.dumps(index)),50000)
            with patch('repeat.assert_repeat_contents',side_effect=AssertionError('Actual business assertion failed')) as validator:
                with self.assertRaisesRegex(AssertionError,'Actual business'):assert_repeat(index,FIXTURES,root)
                self.assertEqual(validator.call_args.args[0],payload)
    def test_size_hash_missing_or_external_path_rejects_complete_index(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);index=self.tree(root)
            for mutation in ('size','hash','missing','external','omitted_case'):
                changed=copy.deepcopy(index);entries=changed['phases']['repeat']['files'];entry=next(e for e in entries if e['path'].endswith('native-console.log'))
                if mutation=='size':entry['bytes']+=1
                if mutation=='hash':entry['sha256']='0'*64
                if mutation=='missing':entry['path']='repeat/missing.log'
                if mutation=='external':entry['path']='../outside.log'
                if mutation=='omitted_case':entries.remove(next(e for e in entries if e.get('role')=='group:CO00-NATIVE'))
                with self.subTest(mutation=mutation),self.assertRaises(AssertionError):assert_repeat(changed,FIXTURES,root)
    def test_final_derived_coverage_cannot_mutate_frozen_phase_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);index=self.tree(root);before,receipt=load_index(index,root)
            (root/'primary/coverage.json').write_text('{"final_derived_output":true}')
            after,other=load_index(index,root);self.assertEqual(before,after);self.assertEqual(receipt,other)
    def test_one_phase_cannot_reuse_the_primary_case_files_as_a_second_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);index=self.tree(root)
            index['phases']['repeat']=copy.deepcopy(index['phases']['primary'])
            with self.assertRaisesRegex(AssertionError,'Independent phases'):load_index(index,root)
    def test_legacy_repackaging_preserves_all_probes_and_original_before_reviewing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'evidence';root.mkdir();index=self.tree(root);payload,_=load_index(index,root)
            original={**payload,'case':'ISOLATED-FRESH-REPLAY','revision':2,'status':'FAIL','complete':False,'error':'Original observed refusal'}
            shutil.rmtree(root/'primary');shutil.rmtree(root/'repeat');(root/'restore.json').unlink()
            capsule=root/'isolated-repeat.json';raw=(json.dumps(original,indent=2)+'\n').encode();capsule.write_bytes(raw)
            # A full primary case already recovered from the same log must be
            # moved, not copied into both the flat and phase trees.
            (root/'CO00-NATIVE.json').write_text(json.dumps(original['primary']['groups']['CO00-NATIVE']))
            archive=Path(d)/'archive/full-original.json'
            with patch('repackage_repeat.assert_repeat_contents',side_effect=AssertionError('Native proof still fails')) as reviewer:
                result=repackage(capsule,root,archive,FIXTURES)
                self.assertEqual(reviewer.call_args.args[0],payload)
            self.assertEqual(archive.read_bytes(),raw);self.assertFalse((root/'CO00-NATIVE.json').exists())
            self.assertEqual(result['recovery']['legacy_capsule_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['recovery']['legacy_review']['error'],'Original observed refusal')
            self.assertEqual(result['status'],'FAIL');self.assertIn('Native proof still fails',result['error'])
            loaded,_=load_index(json.loads(capsule.read_bytes()),root);self.assertEqual(loaded,payload)
            self.assertNotIn('full_probe',capsule.read_text())
            self.assertEqual(len(list(root.rglob('CO00-NATIVE.json'))),2)
    def test_archive_inside_evidence_is_rejected_without_overwriting_capsule(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);capsule=root/'isolated-repeat.json';capsule.write_text('{"complete_original":true}')
            with self.assertRaisesRegex(AssertionError,'outside the Git evidence'):repackage(capsule,root,root/'duplicate.json',FIXTURES)
            self.assertEqual(capsule.read_text(),'{"complete_original":true}')
    def test_individual_file_fragments_recover_exact_bytes_without_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();index=self.tree(source);notices=list(file_notices(index,source))
            target=Path(d)/'target';paths=recover_files(notices,target,REFERENCE)
            expected,receipt=load_index(index,source);actual,checked=load_index(index,target)
            self.assertEqual(actual,expected);self.assertEqual(checked,receipt)
            self.assertEqual(len(paths),len(set(paths)));self.assertEqual(len(paths),receipt['files_loaded'])
            self.assertTrue(all('primary' not in n and 'repeat' not in n for n in notices))
    def test_missing_duplicate_corrupt_or_unsafe_fragments_do_not_become_files(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();index=self.tree(source);notices=list(file_notices(index,source))
            chosen=next(n for n in notices if n['complete_evidence_file'].endswith('native-console.log'))
            for mutation in ('missing','duplicate','hash','size','unsafe','truncated'):
                target=Path(d)/mutation;changed=copy.deepcopy(notices)
                item=next(n for n in changed if n['complete_evidence_file']==chosen['complete_evidence_file'])
                if mutation=='missing':changed.remove(item)
                if mutation=='duplicate':changed.append(copy.deepcopy(item))
                if mutation=='hash':item['content_sha256']='0'*64
                if mutation=='size':item['bytes']+=1
                if mutation=='unsafe':item['complete_evidence_file']='../outside.log'
                if mutation=='truncated':item['base64_fragment']=item['base64_fragment'][:10]
                recover_files(changed,target,REFERENCE)
                with self.subTest(mutation=mutation),self.assertRaises(AssertionError):load_index(index,target)
    def test_indexed_ci_does_not_print_the_legacy_case_tree_twice(self):
        with patch.dict('os.environ',{'CCM_INDEXED_EVIDENCE':'1'}),patch('builtins.print') as output:
            publish_complete_evidence({'case':'CO00-NATIVE','huge_probe':'Must remain in its file'})
            output.assert_not_called()
            publish_complete_evidence({'case':'ISOLATED-FRESH-REPLAY','format':FORMAT,'reference':REFERENCE})
            self.assertGreater(output.call_count,0)
    def test_log_recovers_both_phase_trees_and_rejects_the_forged_pass_label(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();index=self.tree(source)
            index.update(case='ISOLATED-FRESH-REPLAY',revision=2,complete=False)
            stream=io.StringIO()
            with redirect_stdout(stream):publish_complete_evidence(index)
            notices=[json.dumps(n) for n in file_notices(index,source)]+[line.split('::',2)[2] for line in stream.getvalue().splitlines()]
            log=Path(d)/'actions.log';log.write_text('\n'.join('job ##[notice]'+n for n in notices)+'\n')
            output=Path(d)/'review';result=extract(log,output,'synthetic',BUSINESS_COMMIT,FIXTURES)
            self.assertEqual(result['counts'],{'FAIL':34});self.assertEqual(result['repeat_review']['status'],'FAIL')
            self.assertTrue(result['repeat_review']['all_hashes_verified'])
            self.assertEqual(len(list(output.rglob('CO00-NATIVE.json'))),2)
            self.assertFalse((output/'CO00-NATIVE.json').exists())
    def test_complete_primary_phase_survives_an_absent_repeat_without_repeat_pass(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();index=self.tree(source)
            index={'format':FORMAT,'reference':REFERENCE,'case':'EVIDENCE-PHASE-primary','phases':{'primary':index['phases']['primary']}}
            stream=io.StringIO()
            with patch.dict('os.environ',{'CCM_INDEXED_EVIDENCE':'1'}),redirect_stdout(stream):publish_complete_evidence(index)
            notices=[json.dumps(n) for n in file_notices(index,source)]+[line.split('::',2)[2] for line in stream.getvalue().splitlines()]
            log=Path(d)/'actions.log';log.write_text('\n'.join('job ##[notice]'+n for n in notices)+'\n')
            output=Path(d)/'review';result=extract(log,output,'synthetic',BUSINESS_COMMIT,FIXTURES)
            self.assertEqual(result['counts'],{'FAIL':34});self.assertEqual(result['repeat_review']['status'],'UNRUN')
            self.assertTrue((output/'primary-phase-index.json').exists());self.assertFalse((output/'isolated-repeat.json').exists())
            self.assertEqual(len(list(output.rglob('CO00-NATIVE.json'))),1)
    def test_business_assertions_are_identical_to_the_active_execution_commit(self):
        repo=Path(__file__).resolve().parents[3]
        original=subprocess.check_output(['git','show',BUSINESS_COMMIT+':labs/axelor/core-test/repeat.py'],cwd=repo).decode()
        previous=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='assert_repeat')
        current=next(n for n in ast.parse(Path(__file__).with_name('repeat.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='assert_repeat_contents')
        # Only the verdict/reference precondition moves into the wrapper. Every
        # actual native assertion and benchmark reviewer remains byte-equivalent AST.
        self.assertEqual([ast.dump(n) for n in previous.body[1:]],[ast.dump(n) for n in current.body[1:]])
