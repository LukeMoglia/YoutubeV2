import concurrent.futures
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from style_pipeline import Production, STYLE, authority, digest, normalize, save, verify_for_assembly


class StylePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def production(self, name='roman', count=4):
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        styles = [('pov_scene', 'main'), ('world_scene', 'supporting'), ('object_scene', 'none'), ('cost_scene', 'main')]
        scenes = [dict(scene_number=n, level=1, scene_style=styles[(n-1)%4][0], character=styles[(n-1)%4][1],
                       image_prompt=f'{name} unique prop {n}; cinematic framing; realistic placement') for n in range(1, count+1)]
        save(folder / 'current_script.json', dict(topic=name, character_bank=dict(
            protagonist_fixed_core='local warm tan bald protagonist', protagonist_age_layers={'level_1_2': 'young smooth face'},
            protagonist_costumes={'level_1': name + ' wardrobe'}, secondary_characters={name: name+' distinct person'}), scenes=scenes))
        p = Production(folder); p.init(); self.addCleanup(p.close)
        return p

    def candidate(self, p, n=1):
        p.prepare(n)
        path = self.root / 'fixture.png'
        Image.new('RGB', (320, 180), 'grey').save(path)
        return p.ingest(n, path, 'SYNTHETIC TEST FIXTURE, NOT VISUAL EVIDENCE')

    def review(self, p, n=1, verdict='pass'):
        r = self.candidate(p, n)
        r.update(evaluator='unit-test mock, not a vision evaluation', full_resolution_viewed=True)
        for value in r['checks'].values():
            value.update(verdict=verdict, observation='Synthetic state-machine fixture only; no artistic claim.')
        r['regions'] = {k: 'Synthetic region observation' for k in r['regions']}
        if verdict != 'pass': r['correction'] = 'Simplify observed excessive texture in foreground.'
        return r

    def test_300_requests_two_parallel_productions_and_resume(self):
        a = self.production('roman', 300); b = self.production('submarine', 300)
        def run(folder):
            p = Production(folder)
            try:
                for n in range(1, 301):
                    d = p.prepare(n); req = d['request']
                    self.assertEqual(req['style_sha256'], p.style_hash)
                    self.assertIn((STYLE/'STYLE_BIBLE.md').read_text(encoding='utf-8'), req['tool_arguments']['prompt'])
                    self.assertFalse(req['tool_arguments']['transparent_background'])
                    self.assertEqual(req['tool_arguments']['referenced_image_paths'], [r['path'] for r in req['references']])
                    self.assertEqual('identity' in [r['id'] for r in req['references']], n % 4 in (1, 0))
                    other = 'submarine' if folder.name == 'roman' else 'roman'
                    self.assertNotIn(other, json.dumps(req['video_context']))
                    if n in (1, 100, 200, 300):
                        p.close(); p = Production(folder)
                        self.assertEqual(d['request_sha256'], p.prepare(n)['request_sha256'])
                        p.technical_failure(n, 'Simulated interrupted tool; original output confirmed absent')
                        retry = p.prepare(n)
                        self.assertEqual(retry['attempt'], 2)
                        self.assertEqual(retry['request']['references'], req['references'])
                        self.assertNotEqual(retry['request']['tool_arguments']['prompt'], req['tool_arguments']['prompt'])
                        p.close(); p = Production(folder)
                        self.assertEqual(retry['request_sha256'], p.prepare(n)['request_sha256'])
                return p.scope()['production_id']
            finally: p.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            ids = list(pool.map(run, [a.folder, b.folder]))
        self.assertNotEqual(*ids)

    def test_concurrent_prepare_same_scene_is_idempotent(self):
        p = self.production()
        def run(_):
            worker = Production(p.folder)
            try: return worker.prepare(1)['request_sha256']
            finally: worker.close()
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            hashes = list(pool.map(run, range(4)))
        self.assertEqual(len(set(hashes)), 1)
        self.assertEqual(p.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0], 1)

    def test_visual_gate_uncertain_retries_and_bound(self):
        p = self.production()
        first_hash = None
        for attempt in range(1, 4):
            review = self.review(p, verdict='uncertain')
            d = p.latest(1)
            if first_hash: self.assertNotEqual(first_hash, d['request_sha256'])
            first_hash = d['request_sha256']
            result = p.review(1, review)
            self.assertEqual(result['state'], 'needs_attention' if attempt == 3 else 'rejected')
        with self.assertRaisesRegex(ValueError, 'limit'): p.prepare(1)
        self.assertFalse((p.folder / 'images/approved/scene_001.png').exists())
        self.assertEqual(len(list((p.folder / 'images/style_rejected').glob('*.png'))), 3)

    def test_review_requires_pixels_provenance_and_observations(self):
        p = self.production()
        r = self.candidate(p)
        with self.assertRaises(ValueError): p.review(1, r)
        r.update(evaluator='test', full_resolution_viewed=True)
        r['image_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'provenance'): p.review(1, r)

    def test_approval_tampering_blocks_assembly(self):
        p = self.production(count=1)
        r = self.review(p); p.review(1, r)
        verify_for_assembly(p.folder)
        (p.folder / 'images/approved/scene_001.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Style gate'): verify_for_assembly(p.folder)

    def test_preserve_preexisting_approved(self):
        p = self.production()
        target = p.folder / 'images/approved/scene_001.png'; target.parent.mkdir(parents=True)
        Image.new('RGB', (320,180), 'red').save(target)
        before = digest(target)
        r = self.review(p)
        with self.assertRaisesRegex(ValueError, 'preserved'): p.review(1, r)
        self.assertEqual(digest(target), before)
        p.review(1, r, replace_approved=True)
        self.assertEqual(len(list(p.work.glob('previous_approved*'))), 1)

    def test_script_and_copied_folder_fail_closed(self):
        p = self.production()
        copied = self.root / 'copied'; shutil.copytree(p.folder, copied)
        q = Production(copied)
        try:
            with self.assertRaisesRegex(ValueError, 'moved'): q.scope()
        finally: q.close()
        s = json.loads((p.folder/'current_script.json').read_text()); s['topic']='changed'; save(p.folder/'current_script.json',s)
        with self.assertRaises(ValueError): p.prepare(1)

    def test_global_reference_tampering_detected(self):
        style = self.root / 'style'; shutil.copytree(STYLE, style)
        (style/'references/objects.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'modified'): authority(style)

    def test_normalization_keeps_story_and_logs_changes(self):
        text, log = normalize('Clean 2D cartoon illustration, arbitrary soft shading, cinematic composition. A realistic brass medal in dramatic lighting.')
        self.assertIn('brass medal', text); self.assertNotIn('realistic', text)
        self.assertEqual(len(log), 3)

    def test_normalization_preserves_negative_constraints(self):
        text, log = normalize('No photorealistic skin. Avoid oil painting. Realistic watch placement.')
        self.assertIn('No photorealistic skin', text)
        self.assertIn('Avoid oil painting', text)
        self.assertIn('physically plausible watch placement', text)

    def test_dispatch_claim_cannot_be_reused(self):
        p = self.production(); p.prepare(1); p.claim(1, 'worker-A')
        with self.assertRaisesRegex(ValueError, 'Already dispatched'): p.claim(1, 'worker-B')

    def test_main_identity_checks_cannot_be_waived(self):
        p = self.production(); r = self.review(p)
        r['checks']['identity']['verdict'] = 'not_applicable'
        with self.assertRaisesRegex(ValueError, 'cannot be waived'): p.review(1, r)

    def test_technical_failure_is_bounded_and_preserves_rejections(self):
        p = self.production()
        (p.folder/'images/rejected.txt').write_text('99\n')
        for _ in range(3):
            p.prepare(1); p.technical_failure(1, 'tool unavailable; retry after availability recovery')
        self.assertEqual(p.latest(1)['state'], 'needs_attention')
        self.assertIn('99', (p.folder/'images/rejected.txt').read_text())

    def test_finalizer_preserves_local_bank_and_no_roman_fallback(self):
        file = Path(__file__).resolve().parents[2]/'POV niche/finalize_pov_script.py'
        spec = importlib.util.spec_from_file_location('finalizer', file)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        p = self.production('submarine')
        scene = p.script['scenes'][0]
        module.expand_compact_image_prompt(p.script, scene)
        self.assertIn('local warm tan bald protagonist', scene['image_prompt'])
        self.assertIn('young smooth face', scene['image_prompt'])
        self.assertNotIn('Roman', scene['image_prompt'])
        scene['image_prompt']='simple shot'; p.script['character_bank']['protagonist_costumes']={}
        with self.assertRaises(ValueError): module.expand_compact_image_prompt(p.script, scene)


if __name__ == '__main__': unittest.main()
