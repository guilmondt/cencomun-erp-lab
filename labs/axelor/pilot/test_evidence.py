import json,tempfile,unittest
from pathlib import Path
from evidence import EvidenceRun
from snapshots import diff,digest
class EvidenceTests(unittest.TestCase):
 def test_failure_keeps_inputs_and_failed_comparison(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'result.json'
   with self.assertRaises(AssertionError):
    with EvidenceRun(path) as result:
     result.data={'before':{'counted':'164.00'},'after':{'counted':'163.00'}}
     result.check('immutable counted cash',False,result.data['after'],result.data['before'])
   saved=json.loads(path.read_text());self.assertEqual(saved['status'],'FAIL')
   self.assertEqual(saved['checks'][0]['actual'],{'counted':'163.00'})
   self.assertEqual(saved['data']['before'],{'counted':'164.00'})
 def test_same_count_with_changed_economic_field_is_not_equal(self):
  before={'MoveLine':[{'id':1,'debit':'36.00','account':{'id':9}}]}
  after={'MoveLine':[{'id':1,'debit':'35.99','account':{'id':9}}]}
  self.assertEqual(len(before['MoveLine']),len(after['MoveLine']))
  self.assertNotEqual(digest(before),digest(after));self.assertIn('MoveLine',diff(before,after))
if __name__=='__main__':unittest.main()
