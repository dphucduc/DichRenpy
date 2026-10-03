import io
import json
import pickle
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
import app as application
from renpy_tools import extract_rpa, parse_script, validate_translation

SCRIPT = '''define e = Character("Eileen")
label start:
    scene bg cafe
    e happy "Hello, [name]! {i}Welcome{/i}." with dissolve
    "It is raining."
    menu:
        "Stay":
            e "Good."
        "Leave":
            e "Goodbye."
screen test():
    text "Do not translate screen code"
init python:
    print("Not dialogue")
'''


def rpa_bytes(entries, version=3):
    key = 0x12345678 if version == 3 else 0
    header_size = 34 if version == 3 else 25
    data = b''
    index = {}
    for name, contents in entries.items():
        index[name] = [( (header_size+len(data)) ^ key, len(contents) ^ key, b'')]
        data += contents
    offset = header_size + len(data)
    header = (f'RPA-3.0 {offset:016x} {key:08x}\n' if version == 3 else f'RPA-2.0 {offset:016x}\n').encode()
    assert len(header) == header_size
    return header + data + zlib.compress(pickle.dumps(index, protocol=2))


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = application.DATA
        application.DATA = Path(self.tmp.name)
        self.client = application.app.test_client()

    def tearDown(self):
        application.DATA = self.previous
        self.tmp.cleanup()

    def upload(self, content=SCRIPT.encode(), filename='script.rpy'):
        result = self.client.post('/api/projects', data={'name':'Test game', 'files':(io.BytesIO(content),filename)})
        self.assertEqual(result.status_code, 201, result.json)
        return result.json

    def test_dialogue_parser_preserves_code(self):
        rows, names, warnings = parse_script(SCRIPT, 'script.rpy')
        self.assertEqual(len(rows), 6)
        self.assertEqual(names, {'e':'Eileen'})
        self.assertEqual(rows[0]['speaker'],'e')
        self.assertEqual(rows[2]['kind'],'Lựa chọn')
        self.assertFalse(warnings)

    def test_complete_gemini_web_workflow(self):
        p = self.upload()
        base = '/api/projects/' + p['id']
        result = self.client.put(base, json={'context':'Rainy reunion', 'relationships':'Eileen → bạn: mình/bạn',
            'rows':[{'id':p['rows'][0]['id'], 'listener':'Bạn'}]})
        self.assertEqual(result.status_code,200)
        ids = [r['id'] for r in p['rows']]
        prompt = self.client.post(base+'/prompt',json={'ids':ids})
        self.assertEqual(prompt.status_code,200)
        self.assertIn('Rainy reunion',prompt.json['prompt'])
        entries = [{'id':r['id'],'translation':('Chào [name]! {i}Mừng bạn đến{/i}.' if i==0 else 'Bản dịch '+str(i)), 'notes':''} for i,r in enumerate(p['rows'])]
        response = self.client.post(base+'/import',json={'text':'```json\n'+json.dumps({'translations':entries})+'\n```','ids':ids})
        self.assertEqual(response.status_code,200,response.json)
        exported = self.client.get(base+'/export')
        self.assertEqual(exported.status_code,200)
        with zipfile.ZipFile(io.BytesIO(exported.data)) as archive:
            source = archive.read('script.rpy').decode()
        self.assertIn('e happy "Chào [name]! {i}Mừng bạn đến{/i}." with dissolve',source)
        self.assertIn('text "Do not translate screen code"',source)
        self.assertIn('print("Not dialogue")',source)
        self.assertEqual(self.client.get(base).json['rows'][0]['listener'],'Bạn')

    def test_failed_import_is_atomic(self):
        p=self.upload(); ids=[r['id'] for r in p['rows']];base='/api/projects/'+p['id']
        entries=[{'id':r['id'],'translation':r['text']} for r in p['rows']]
        entries[-1]['translation']=''
        result=self.client.post(base+'/import',json={'text':json.dumps({'translations':entries}), 'ids':ids})
        self.assertEqual(result.status_code,400)
        self.assertTrue(all(not r['translation'] for r in self.client.get(base).json['rows']))
        entries=entries[:-1]
        result=self.client.post(base+'/import',json={'text':json.dumps({'translations':entries}), 'ids':ids})
        self.assertEqual(result.status_code,400)

    def test_tokens_and_quotes(self):
        with self.assertRaises(ValueError): validate_translation('Hello [name] {i}hi{/i}', 'Chào {i}bạn{/i}')
        with self.assertRaises(ValueError): validate_translation('{i}hi{/i}', '{/i}chào{i}')
        p=self.upload(b'label start:\n    "Hello"\n');row=p['rows'][0]
        result=self.client.put('/api/projects/'+p['id'],json={'rows':[{'id':row['id'],'translation':'Cô ấy nói "chào".\nRồi đi.'}]})
        self.assertEqual(result.status_code,200)
        result=self.client.get('/api/projects/'+p['id']+'/export')
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            source=archive.read('script.rpy').decode()
        rows,_,_=parse_script(source,'script.rpy')
        self.assertEqual(rows[0]['text'],'Cô ấy nói "chào".\nRồi đi.')

    def test_quoted_control_statements_are_not_dialogue(self):
        source = 'label start:\n    play music "song.ogg"\n    voice "line.ogg"\n    show text "An image"\n    jump expression "ending"\n    e "Actual dialogue"\n'
        rows, _, _ = parse_script(source, 'script.rpy')
        self.assertEqual([r['text'] for r in rows], ['Actual dialogue'])

    def test_rpa_2_and_3_extract_assets(self):
        for version in [2,3]:
            p=self.upload(rpa_bytes({'scripts/story.rpy':SCRIPT.encode(),'images/test.bin':b'asset'},version),'game.rpa')
            self.assertEqual(len(p['rows']),6)
            exported=self.client.get('/api/projects/'+p['id']+'/export?original=1')
            with zipfile.ZipFile(io.BytesIO(exported.data)) as archive:
                self.assertEqual(archive.read('images/test.bin'),b'asset')

    def test_rpa_rejects_traversal_and_pickle_code(self):
        result=self.client.post('/api/projects',data={'files':(io.BytesIO(rpa_bytes({'../escape.rpy':b'bad'})),'evil.rpa')})
        self.assertEqual(result.status_code,400)
        from renpy_tools import DataUnpickler
        with self.assertRaises(ValueError): DataUnpickler(io.BytesIO(pickle.dumps(Path))).load()

    def test_decompile_real_renpy_8_fixture(self):
        fixture=application.ROOT/'.tools/unrpyc/testcases/compiled/the_question-8.2/script.rpyc'
        self.assertTrue(fixture.exists(), 'Run scripts/setup.sh before testing')
        p=self.upload(fixture.read_bytes(),'script.rpyc')
        self.assertGreater(len(p['rows']),30)
        self.assertFalse(any('Không giải biên dịch' in w for w in p['warnings']))

    def test_rpa_to_rpyc_to_dialogue(self):
        fixture=application.ROOT/'.tools/unrpyc/testcases/compiled/the_question-8.2/script.rpyc'
        p=self.upload(rpa_bytes({'scripts/script.rpyc':fixture.read_bytes(),'images/asset.bin':b'example'}),'compiled-game.rpa')
        self.assertGreater(len(p['rows']),30)
        self.assertEqual(p['rows'][0]['file'],'scripts/script.rpy')
        exported=self.client.get('/api/projects/'+p['id']+'/export')
        with zipfile.ZipFile(io.BytesIO(exported.data)) as archive:
            self.assertIn('scripts/script.rpy',archive.namelist())
            self.assertNotIn('scripts/script.rpyc',archive.namelist())

    def test_home_and_persistence(self):
        self.assertEqual(self.client.get('/').status_code,200)
        p=self.upload()
        self.assertEqual(self.client.get('/api/projects').json[0]['id'],p['id'])
        self.assertEqual(self.client.get('/api/projects/not-a-uuid').status_code,400)


if __name__ == '__main__':
    unittest.main()
