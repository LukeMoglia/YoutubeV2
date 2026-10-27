"""Persistent Codex image request/review bridge. No API keys or paid services.

Python enforces provenance/state; Codex supplies generation and actual visual
inspection. A JSON review is an attributed observation, not a vision algorithm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import uuid
from pathlib import Path

STYLE_HOME = Path(__file__).resolve().parent / 'style'
ACTIVE_VERSION_FILE = STYLE_HOME / 'active_version.txt'


def active_style_root():
    version = ACTIVE_VERSION_FILE.read_text(encoding='ascii').strip() if ACTIVE_VERSION_FILE.exists() else 'v1'
    if not re.fullmatch(r'[a-z0-9_-]+', version):
        raise ValueError('Invalid active style version pointer')
    root = (STYLE_HOME / version).resolve()
    if not root.is_relative_to(STYLE_HOME.resolve()):
        raise ValueError('Active style version must remain inside the versioned style library')
    return root


STYLE = active_style_root()
REGIONS = ('people_faces', 'clothing', 'foreground_props', 'architecture', 'distance', 'lighting')
CHECKS = ('linework', 'colour', 'shading', 'character_construction', 'backgrounds', 'finish',
          'identity', 'content', 'composition')
STYLE_SCORES = ('linework', 'face_construction', 'colour_regions', 'cel_shading', 'material_rendering', 'background_finish')
DRIFT_SCORES = ('linework', 'face_construction', 'colour_regions', 'cel_shading', 'material_rendering', 'background_finish')
ROLES = {'pov_scene': 'main', 'cost_scene': 'main', 'world_scene': 'supporting', 'object_scene': 'none'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def authority(root=STYLE):
    root = Path(root).resolve()
    if digest(root / 'manifest.json') != (root / 'manifest.sha256').read_text().strip():
        raise ValueError('Global manifest changed: publish a reviewed new version, never silently rehash.')
    m = read(root / 'manifest.json')
    for item in [{'path': m['bible'], 'sha256': m['bible_sha256']}] + m['references']:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or digest(path) != item['sha256']:
            raise ValueError('Canonical asset missing or modified: ' + item['path'])
    return m, digest(root / 'manifest.json')


def normalize(text):
    """Only normalize medium modifiers; retain raw source and a substitution log."""
    changes = []
    prefix = re.compile(r'^Clean 2D cartoon illustration,.*?cinematic composition\.?\s*', re.I | re.S)
    result, count = prefix.subn('', text, count=1)
    if count:
        changes.append('Removed legacy rendering prefix; replaced by complete canonical bible.')
    substitutions = [(r'\bultra[- ]detailed\b', 'clearly readable'),
                     (r'\bphotorealistic\b|\bphotographic rendering\b', 'illustrated'),
                     (r'\brealistic\b', 'physically plausible'),
                     (r'\bcinematic lighting\b', 'scene-appropriate illustrated lighting'),
                     (r'\bdramatic lighting\b', 'narratively emphatic illustrated lighting'),
                     (r'\b(?:watercolou?r|oil painting|3D render|anime rendering)\b', 'canonical outlined illustration')]
    for pattern, replacement in substitutions:
        count = 0
        def replace(match):
            nonlocal count
            # Preserve exclusions: "no photorealistic skin" must not become
            # "no illustrated skin". Restrict this check to the current clause.
            clause = re.split(r'[.;:\n]', result[:match.start()])[-1]
            if re.search(r'\b(no|not|never|without|avoid)\b', clause, re.I):
                return match.group(0)
            count += 1
            return replacement
        result = re.sub(pattern, replace, result, flags=re.I)
        if count:
            changes.append(f'{pattern} -> {replacement} ({count})')
    return result, changes


def age_layer(bank, level):
    layers = bank.get('protagonist_age_layers', {})
    group = f'level_{level}' if level >= 9 else f'level_{level if level % 2 else level-1}_{level+1 if level % 2 else level}'
    return layers.get(str(level), layers.get(f'level_{level}', layers.get(group, '')))


class Production:
    def __init__(self, folder, style=STYLE):
        self.folder = Path(folder).resolve()
        self.style = Path(style).resolve()
        self.manifest, self.style_hash = authority(self.style)
        self.script = read(self.folder / 'current_script.json')
        self.script_hash = digest(self.folder / 'current_script.json')
        self.work = self.folder / 'images/style_state'
        self.work.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.work / 'manifest.sqlite3', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS production (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS attempts (scene INTEGER, attempt INTEGER, state TEXT, data TEXT, PRIMARY KEY(scene,attempt))')
        self.db.execute('CREATE TABLE IF NOT EXISTS checkpoints (batch INTEGER PRIMARY KEY, state TEXT NOT NULL, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS checkpoint_history (id INTEGER PRIMARY KEY AUTOINCREMENT, batch INTEGER NOT NULL, data TEXT NOT NULL)')
        self.db.commit()

    def close(self):
        self.db.close()

    def batches(self):
        scenes = sorted(self.script['scenes'], key=lambda s: s['scene_number'])
        numbers = [s['scene_number'] for s in scenes]
        interval = int(self.manifest.get('checkpoint_interval', 0))
        if interval <= 0 or not numbers:
            return [numbers] if numbers else []
        first_for_style = {}
        for index, scene in enumerate(scenes):
            first_for_style.setdefault(scene['scene_style'], index + 1)
        # The first checkpoint is a calibration batch containing at least one
        # example of every scene class; later batches use the fixed interval.
        first_size = min(len(numbers), max(interval, max(first_for_style.values(), default=1)))
        result = [numbers[:first_size]]
        for start in range(first_size, len(numbers), interval):
            result.append(numbers[start:start + interval])
        return result

    def batch_for_scene(self, number):
        for batch, numbers in enumerate(self.batches(), start=1):
            if number in numbers:
                return batch
        raise ValueError(f'Unknown scene number {number}')

    def checkpoint_bytes_match(self, data):
        if data.get('style_sha256') != self.style_hash:
            return False
        expected_refs = {r['id']: r['sha256'] for r in self.manifest['references']}
        if data.get('reference_hashes') != expected_refs:
            return False
        image_hashes = data.get('image_hashes', {})
        batch = data.get('review', {}).get('batch')
        batches = self.batches()
        if type(batch) is not int or not 1 <= batch <= len(batches):
            return False
        expected_numbers = {str(number) for number in batches[batch - 1]}
        if set(image_hashes) != expected_numbers:
            return False
        for raw_number, expected_hash in image_hashes.items():
            path = self.folder / 'images/approved' / f'scene_{int(raw_number):03d}.png'
            if not path.is_file() or digest(path) != expected_hash:
                return False
        return bool(data.get('image_hashes'))

    def checkpoint_template(self, batch):
        batches = self.batches()
        if not 1 <= batch <= len(batches):
            raise ValueError(f'Batch must be between 1 and {len(batches)}')
        numbers = batches[batch - 1]
        snapshots = {}
        per_scene_scores = {name: [] for name in DRIFT_SCORES}
        for number in numbers:
            data = self.latest(number)
            approved = self.folder / 'images/approved' / f'scene_{number:03d}.png'
            if not data or data['state'] != 'approved' or not approved.is_file():
                raise ValueError(f'Batch {batch} is not ready: scene {number} needs a current individual approval')
            if digest(approved) != data['image_sha256']:
                raise ValueError(f'Batch {batch} scene {number} changed after approval')
            snapshots[str(number)] = data['image_sha256']
            scores = data.get('review', {}).get('style_scores', {})
            for name in DRIFT_SCORES:
                score = scores.get(name, {}).get('score')
                if type(score) is int:
                    per_scene_scores[name].append(score)
        work = self.work / 'batch_reviews'
        sheet = work / f'batch_{batch:03d}_contact.png'
        reference_sheet = work / f'batch_{batch:03d}_authority.png'
        contact_sheet([self.folder / 'images/approved' / f'scene_{n:03d}.png' for n in numbers], sheet)
        contact_sheet([self.style / r['path'] for r in self.manifest['references']], reference_sheet)
        reference_hashes = {r['id']: r['sha256'] for r in self.manifest['references']}
        means = {name: round(sum(values) / len(values), 3) if values else None
                 for name, values in per_scene_scores.items()}
        template = dict(production_id=self.scope()['production_id'], batch=batch, scene_numbers=numbers,
                        image_hashes=snapshots, style_sha256=self.style_hash,
                        reference_hashes=reference_hashes,
                        contact_sheet=str(sheet.resolve()), authority_sheet=str(reference_sheet.resolve()),
                        prior_style_score_means=means, evaluator='', method='actual_contact_sheet_and_pixels_viewed',
                        full_resolution_comparisons_viewed=False, verdict='uncertain',
                        drift_scores={k: dict(score=None, observation='') for k in DRIFT_SCORES},
                        unexpected_subjects=[], unexpected_period_cues=[], unexpected_props=[],
                        observation='', rework_scenes=[])
        path = work / f'batch_{batch:03d}_review_template.json'
        save(path, template)
        template['template_path'] = str(path.resolve())
        return template

    def checkpoint(self, batch, review):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            expected = self.checkpoint_template(batch)
            for key in ('production_id', 'batch', 'scene_numbers', 'image_hashes', 'style_sha256', 'reference_hashes'):
                if review.get(key) != expected[key]:
                    raise ValueError('Batch review provenance mismatch: ' + key)
            if (review.get('method') != 'actual_contact_sheet_and_pixels_viewed'
                    or review.get('full_resolution_comparisons_viewed') is not True
                    or not review.get('evaluator', '').strip()):
                raise ValueError('A batch audit requires attributed contact-sheet and pixel inspection')
            verdict = review.get('verdict')
            if verdict not in ('pass', 'fail', 'uncertain') or not review.get('observation', '').strip():
                raise ValueError('Batch audit needs a verdict and specific observations')
            passed = verdict == 'pass'
            for name in DRIFT_SCORES:
                metric = review.get('drift_scores', {}).get(name, {})
                score = metric.get('score')
                if type(score) is not int or score not in (0, 1, 2) or not metric.get('observation', '').strip():
                    raise ValueError('Every batch drift dimension needs an observed score of 0, 1 or 2')
                if score == 2:
                    passed = False
            if any(review.get(k) for k in ('unexpected_subjects', 'unexpected_period_cues', 'unexpected_props')):
                passed = False
            rework = review.get('rework_scenes', [])
            if not isinstance(rework, list) or any(type(n) is not int or n not in expected['scene_numbers'] for n in rework):
                raise ValueError('Rework scenes must be scene numbers inside the audited batch')
            if passed and rework:
                raise ValueError('A passing batch audit cannot also name scenes for rework')
            if not passed and not rework:
                raise ValueError('A failed or uncertain batch audit must identify scenes to rework')
            prior = self.db.execute('SELECT data FROM checkpoints WHERE batch=?', (batch,)).fetchone()
            if prior:
                self.db.execute('INSERT INTO checkpoint_history(batch,data) VALUES(?,?)', (batch, prior['data']))
            payload = dict(review=review, image_hashes=expected['image_hashes'],
                           reference_hashes=expected['reference_hashes'], style_sha256=self.style_hash)
            state = 'approved' if passed else 'failed'
            self.db.execute('INSERT OR REPLACE INTO checkpoints(batch,state,data) VALUES(?,?,?)',
                            (batch, state, encoded(payload)))
            return dict(batch=batch, state=state, rework_scenes=rework)

    def reopen_audited_scene(self, number, reason):
        batch = self.batch_for_scene(number)
        row = self.db.execute('SELECT state,data FROM checkpoints WHERE batch=?', (batch,)).fetchone()
        if not row or row['state'] != 'failed':
            raise ValueError('Scene rework requires a failed batch audit')
        audit = json.loads(row['data'])['review']
        if number not in audit.get('rework_scenes', []):
            raise ValueError('Scene was not named for rework by the failed batch audit')
        data = self.latest(number)
        if not data or data['state'] != 'approved' or not reason.strip():
            raise ValueError('Rework needs an approved scene and a specific correction')
        data['correction'] = 'Cross-scene drift audit: ' + reason.strip()
        data['replacement_authorized'] = True
        with self.db:
            self.put(data, 'rework')
        return dict(scene=number, state='rework_authorized', attempt=data['attempt'])

    def verify(self):
        invalid = [r for r in self.status() if r['state'] != 'approved']
        if invalid:
            raise ValueError(f'Style gate: {len(invalid)} scenes lack a current visual pass; first: {invalid[:5]}')
        if self.scope().get('review_contract', 1) >= 2:
            for batch, numbers in enumerate(self.batches(), start=1):
                row = self.db.execute('SELECT state,data FROM checkpoints WHERE batch=?', (batch,)).fetchone()
                if not row or row['state'] != 'approved' or not self.checkpoint_bytes_match(json.loads(row['data'])):
                    raise ValueError(f'Style gate: batch {batch} ({numbers[0]}–{numbers[-1]}) lacks a current approved drift audit')
        return True

    def init(self, max_attempts=3):
        if not 1 <= max_attempts <= 10:
            raise ValueError('max_attempts must be 1..10')
        numbers = [s['scene_number'] for s in self.script['scenes']]
        if len(set(numbers)) != len(numbers) or any(type(n) is not int or n < 1 for n in numbers):
            raise ValueError('Scene numbers must be unique positive integers')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT data FROM production').fetchone()
            if row:
                return self.scope()
            data = dict(production_id=str(uuid.uuid4()), root=str(self.folder), script_sha256=self.script_hash,
                        style_version=self.manifest['version'], style_sha256=self.style_hash,
                        style_root=str(self.style), review_contract=self.manifest.get('review_contract', 1),
                        checkpoint_interval=int(self.manifest.get('checkpoint_interval', 0)),
                        max_attempts=max_attempts)
            self.db.execute('INSERT INTO production VALUES(1,?)', (encoded(data),))
            return data

    def scope(self):
        row = self.db.execute('SELECT data FROM production').fetchone()
        if not row:
            raise ValueError('Run init with an explicit production folder first')
        data = json.loads(row['data'])
        if (data['root'], data['script_sha256'], data['style_sha256']) != (str(self.folder), self.script_hash, self.style_hash):
            raise ValueError('Production moved, script changed or global style changed; create an explicit new production, do not reuse approvals')
        if data.get('style_root', str(self.style)) != str(self.style):
            raise ValueError('Production style library path changed; preserve the recorded style version')
        if digest(self.folder / 'current_script.json') != self.script_hash:
            raise ValueError('Script changed during this operation')
        authority(self.style)
        return data

    def latest(self, number):
        row = self.db.execute('SELECT * FROM attempts WHERE scene=? ORDER BY attempt DESC LIMIT 1', (number,)).fetchone()
        if not row:
            return None
        data = json.loads(row['data'])
        data['state'] = row['state']
        return data

    def put(self, data, state):
        data['state'] = state
        self.db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?)',
                        (data['scene'], data['attempt'], state, encoded(data)))

    def prepare(self, number):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            scope = self.scope()
            batch = self.batch_for_scene(number)
            if batch > 1:
                row = self.db.execute('SELECT state,data FROM checkpoints WHERE batch=?', (batch - 1,)).fetchone()
                if not row or row['state'] != 'approved':
                    raise ValueError(f'Batch {batch - 1} contact-sheet audit must pass before batch {batch} can start')
                checkpoint = json.loads(row['data'])
                if not self.checkpoint_bytes_match(checkpoint):
                    raise ValueError(f'Batch {batch - 1} changed after its drift audit; re-audit before continuing')
            previous = self.latest(number)
            if previous and previous['state'] in ('prepared', 'pending', 'approved'):
                self.validate_request(previous)
                if previous['state'] == 'approved':
                    path = self.folder / f'images/approved/scene_{number:03d}.png'
                    if not path.exists() or digest(path) != previous['image_sha256']:
                        raise ValueError('Approved image changed; do not skip or silently regenerate')
                return previous  # resume without duplicating a generation
            attempt = previous['attempt'] + 1 if previous else 1
            if attempt > scope['max_attempts']:
                raise ValueError('Bounded attempt limit reached; scene requires attention')
            scene = next((s for s in self.script['scenes'] if s['scene_number'] == number), None)
            if scene is None or ROLES.get(scene['scene_style']) != scene['character']:
                raise ValueError('Missing scene or inconsistent scene classification')
            role = scene['character']
            refs = []
            for name in self.manifest['routes'][role]:
                item = next(r for r in self.manifest['references'] if r['id'] == name)
                refs.append(dict(id=name, role=item['role'], path=str(self.style / item['path']), sha256=item['sha256']))
            bank = self.script['character_bank']
            shot, changes = normalize(scene['image_prompt'])
            production_context = self.script.get('production_context', {})
            scene_context = dict(topic=self.script['topic'], production_id=scope['production_id'],
                                 world=production_context.get('world', self.script['topic']),
                                 period=production_context.get('period', 'Only the period stated in this production and the current scene.'),
                                 setting=production_context.get('setting', self.script['topic']),
                                 required_visual_elements=production_context.get('required_visual_elements', []),
                                 excluded_visual_elements=production_context.get('excluded_visual_elements', [
                                     'Any unrelated period, setting, costume, technology, character, architecture, symbol or prop not required by this video or scene.'
                                 ]),
                                 continuity=production_context.get('continuity', {}))
            visible_names = scene.get('secondary_character_ids')
            if not isinstance(visible_names, list):
                visible_names = []
                scene_text = f"{scene.get('voiceover', '')}\n{scene.get('image_prompt', '')}"
                for name in bank.get('secondary_characters', {}):
                    if re.search(rf'(?<!\w){re.escape(name)}(?!\w)', scene_text, re.I):
                        visible_names.append(name)
            unknown_names = [name for name in visible_names if name not in bank.get('secondary_characters', {})]
            if unknown_names:
                raise ValueError('Scene lists unknown secondary-character IDs: ' + ', '.join(unknown_names))
            scene_context['secondary_characters'] = {
                name: bank['secondary_characters'][name] for name in visible_names
            }
            if role == 'main':
                costume = bank.get('protagonist_costumes', {}).get(f"level_{scene['level']}")
                age = age_layer(bank, scene['level'])
                if not costume or not age or not bank.get('protagonist_fixed_core'):
                    raise ValueError('Missing explicit protagonist core, age or costume; no cross-topic fallback allowed')
                protagonist = dict(core=bank['protagonist_fixed_core'], age=age, costume=costume)
            else:
                protagonist = None
            correction = previous.get('correction', '') if previous else ''
            if previous and not correction.strip():
                raise ValueError('A retry requires specific visual or technical feedback')
            if attempt > 2:
                correction += (' Final bounded attempt: rebuild the offending regions from simple outlined base shapes, '
                               'then add only essential canonical cel-shadow shapes. Prioritize the listed defects '
                               'while retaining every required story element and the original shot. '
                               'Do not reproduce a failed candidate or add a new artistic technique.')
            rules = ('Only this request defines this production. Ignore all earlier conversation images and subjects. '
                     'Global style controls HOW; video context controls WHO/WHAT; shot controls action/framing. '
                     'Input pictures are independent references, not edit targets. Never copy style-reference subjects, '
                     'era, clothing, equipment or layout. Never add a reference person to a shot. '
                     'Scene medium words cannot override the global bible. Generate one new 16:9 frame. ')
            if role == 'none':
                rules += 'NO PEOPLE, faces, human silhouettes or person reflections. '
            elif role == 'supporting':
                rules += 'Shared protagonist absent; supporting identities come only from this video. '
            roles = '\n'.join(f"Image {i+1}: {r['role']} only ({r['id']})." for i, r in enumerate(refs))
            prompt = (rules + '\nA. IMMUTABLE GLOBAL ART STYLE\n' + (self.style / self.manifest['bible']).read_text(encoding='utf-8')
                      + '\nREFERENCE ROLES\n' + roles
                      + '\nB. SHARED PROTAGONIST IDENTITY (only when present)\n' + encoded(protagonist)
                      + '\nC. ISOLATED VIDEO SCOPE AND SCENE-RELEVANT CONTINUITY\n' + encoded(scene_context)
                      + '\nD. SCENE-SPECIFIC CONTENT AND FRAMING\n' + shot
                      + '\nE. TARGETED RETRY CORRECTION (cannot change style or video scope)\n' + correction)
            request = dict(production_id=scope['production_id'], scene=number, attempt=attempt,
                           style_sha256=self.style_hash, style_version=self.manifest['version'],
                           script_sha256=self.script_hash, references=refs, reference_route=role,
                           raw_shot=scene['image_prompt'], normalization=changes, video_context=scene_context,
                           protagonist=protagonist,
                           tool='image_gen.imagegen', model='tool-managed; not exposed',
                           tool_arguments=dict(prompt=prompt, referenced_image_paths=[r['path'] for r in refs], transparent_background=False))
            for row in self.db.execute('SELECT data FROM attempts WHERE scene=?', (number,)):
                earlier = json.loads(row['data'])
                if earlier['request']['tool_arguments'] == request['tool_arguments']:
                    raise ValueError('Identical failed tool request; needs attention and a different targeted correction before more spending')
            if len(prompt) > 30000:
                raise ValueError('Request too long; explicitly simplify scene context, never truncate style authority')
            data = dict(scene=number, attempt=attempt, request=request, request_sha256=fingerprint(request))
            self.put(data, 'prepared')
        save(self.work / f'request_{number:03d}_{attempt:02d}.json', data)
        return data

    def claim(self, number, worker):
        """Single durable dispatch claim; no automatic lease expiry or duplicate spend."""
        if not worker.strip():
            raise ValueError('A worker/session identifier is required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            data = self.latest(number)
            if not data or data['state'] != 'prepared':
                raise ValueError('Only a prepared request may be dispatched')
            self.validate_request(data)
            if data.get('dispatch_owner'):
                raise ValueError('Already dispatched; locate its output or record a technical failure before retrying')
            data['dispatch_owner'] = worker
            self.put(data, 'prepared')
            return data

    def validate_request(self, data):
        scope = self.scope()
        req = data['request']
        if (fingerprint(req) != data['request_sha256'] or req['production_id'] != scope['production_id']
                or req.get('style_sha256') != self.style_hash or req.get('script_sha256') != self.script_hash
                or req.get('style_version') != self.manifest['version']):
            raise ValueError('Request provenance mismatch')
        scene = next((s for s in self.script['scenes'] if s['scene_number'] == req.get('scene')), None)
        if not scene or req.get('raw_shot') != scene.get('image_prompt'):
            raise ValueError('Request scene no longer matches the active script')
        role = ROLES.get(scene.get('scene_style'))
        expected_ids = self.manifest['routes'].get(role, [])
        references = req.get('references', [])
        if req.get('reference_route') != role or [r.get('id') for r in references] != expected_ids:
            raise ValueError('Reference route does not match the active scene class')
        expected_paths = []
        for ref, ref_id in zip(references, expected_ids):
            item = next((r for r in self.manifest['references'] if r['id'] == ref_id), None)
            if not item:
                raise ValueError('Route names an unknown canonical reference')
            expected_path = (self.style / item['path']).resolve()
            if (ref.get('role') != item['role'] or Path(ref.get('path', '')).resolve() != expected_path
                    or ref.get('sha256') != item['sha256'] or digest(expected_path) != item['sha256']):
                raise ValueError('Reference bytes changed')
            expected_paths.append(str(expected_path))
        tool_args = req.get('tool_arguments', {})
        if tool_args.get('referenced_image_paths') != expected_paths:
            raise ValueError('Tool reference paths do not match the approved route')
        bible = (self.style / self.manifest['bible']).read_text(encoding='utf-8-sig')
        if bible not in tool_args.get('prompt', ''):
            raise ValueError('Request omitted or altered the immutable style bible')

    def ingest(self, number, source, tool_receipt):
        from PIL import Image
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            data = self.latest(number)
            if not data or data['state'] != 'prepared':
                raise ValueError('Prepare a request before ingesting; pending attempts must be reviewed first')
            self.validate_request(data)
            source = Path(source).resolve()
            with Image.open(source) as im:
                im.verify()
            with Image.open(source) as im:
                if im.format != 'PNG' or abs(im.width / im.height - 16/9) > .03:
                    raise ValueError('Expected a genuine PNG at approximately 16:9')
            if not tool_receipt.strip():
                raise ValueError('Record the actual tool output identifier or legacy-audit provenance')
            target = self.work / f"candidate_{number:03d}_{data['attempt']:02d}.png"
            if target.exists() and digest(target) != digest(source):
                raise ValueError('Candidate collision; never overwrite an earlier tool output')
            if source != target:
                shutil.copy2(source, target)
            data.update(candidate=str(target), image_sha256=digest(target), tool_receipt=tool_receipt)
            self.put(data, 'pending')
            pending = self.folder / 'images/pending' / f'scene_{number:03d}.png'
            pending.parent.mkdir(parents=True, exist_ok=True)
            if not pending.exists():
                shutil.copy2(target, pending)
        return self.review_template(number)

    def review_template(self, number):
        data = self.latest(number)
        if not data or data['state'] != 'pending':
            raise ValueError('No pending candidate')
        return dict(production_id=data['request']['production_id'], request_sha256=data['request_sha256'],
                    image_sha256=data['image_sha256'], style_sha256=self.style_hash,
                    inspected_reference_hashes=[r['sha256'] for r in data['request']['references']],
                    evaluator='', method='actual_images_viewed', full_resolution_viewed=False,
                    checks={k: dict(verdict='uncertain', observation='') for k in CHECKS},
                    regions={k: '' for k in REGIONS}, correction='',
                    style_scores={k: dict(score=None, observation='') for k in STYLE_SCORES},
                    content_isolation=dict(unexpected_subjects=[], unexpected_period_cues=[], unexpected_props=[], observation=''))

    def review(self, number, review, replace_approved=False):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            data = self.latest(number)
            if not data or data['state'] != 'pending':
                raise ValueError('No pending attempt to review')
            self.validate_request(data)
            expected = self.review_template(number)
            for key in ('production_id', 'request_sha256', 'image_sha256', 'style_sha256', 'inspected_reference_hashes'):
                if review.get(key) != expected[key]:
                    raise ValueError('Review provenance mismatch: ' + key)
            if digest(data['candidate']) != data['image_sha256']:
                raise ValueError('Candidate changed after inspection')
            if (review.get('method') != 'actual_images_viewed' or review.get('full_resolution_viewed') is not True
                    or not review.get('evaluator', '').strip()):
                raise ValueError('Actual full-resolution visual inspection must be attributed')
            verdicts = []
            for name in CHECKS:
                check = review.get('checks', {}).get(name, {})
                verdict = check.get('verdict')
                if verdict not in ('pass', 'fail', 'uncertain', 'not_applicable') or not check.get('observation', '').strip():
                    raise ValueError('Missing explicit visual observation: ' + name)
                if verdict == 'not_applicable' and name not in ('identity', 'character_construction', 'backgrounds'):
                    raise ValueError('Required style dimension cannot be waived: ' + name)
                if verdict == 'not_applicable' and name in ('identity', 'character_construction') and data['request'].get('protagonist'):
                    raise ValueError('Main-character construction and identity cannot be waived')
                verdicts.append(verdict)
            if any(not review.get('regions', {}).get(r, '').strip() for r in REGIONS):
                raise ValueError('Every region needs an observation or explicit absence reason')
            passed = all(v in ('pass', 'not_applicable') for v in verdicts)
            scope_contract = self.scope().get('review_contract', 1)
            if scope_contract >= 2:
                scores = review.get('style_scores', {})
                for name in STYLE_SCORES:
                    metric = scores.get(name, {})
                    score = metric.get('score')
                    if type(score) is not int or score not in (0, 1, 2) or not metric.get('observation', '').strip():
                        raise ValueError('Every style score needs an observed value of 0, 1 or 2')
                    if score == 2:
                        passed = False
                leakage = review.get('content_isolation', {})
                if not leakage.get('observation', '').strip():
                    raise ValueError('Content-isolation review needs a specific observation')
                if any(leakage.get(k) for k in ('unexpected_subjects', 'unexpected_period_cues', 'unexpected_props')):
                    passed = False
            data['review'] = review
            if not passed and not review.get('correction', '').strip():
                raise ValueError('Failure/uncertainty needs a targeted correction')
            data['correction'] = review.get('correction', '')
            stem = f'scene_{number:03d}.png'
            approved = self.folder / 'images/approved' / stem
            if passed:
                approved.parent.mkdir(parents=True, exist_ok=True)
                if approved.exists() and digest(approved) != data['image_sha256']:
                    if not replace_approved and not data.get('replacement_authorized'):
                        raise ValueError('Existing approved artwork preserved; explicit --replace-approved authorization required')
                    archive = self.work / ('previous_approved_' + stem + '.' + digest(approved) + '.png')
                    shutil.copy2(approved, archive)
                shutil.copy2(data['candidate'], approved)
                data['replacement_authorized'] = False
                state = 'approved'
            else:
                rejected = self.folder / 'images/style_rejected' / f"scene_{number:03d}_v1_attempt{data['attempt']:02d}.png"
                rejected.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(data['candidate'], rejected)
                state = 'needs_attention' if data['attempt'] >= self.scope()['max_attempts'] else 'rejected'
            self.put(data, state)
            save(self.work / f"review_{number:03d}_{data['attempt']:02d}.json", review)
            pending = self.folder / 'images/pending' / stem
            if pending.exists() and digest(pending) == data['image_sha256']:
                pending.unlink()
            self.sync_legacy()
            return dict(scene=number, state=state, attempt=data['attempt'])

    def technical_failure(self, number, reason):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            data = self.latest(number)
            if not data or data['state'] != 'prepared' or not reason.strip():
                raise ValueError('Technical failure requires a prepared attempt and a reason')
            self.validate_request(data)
            data['correction'] = 'Technical recovery: ' + reason
            state = 'needs_attention' if data['attempt'] >= self.scope()['max_attempts'] else 'technical_failure'
            self.put(data, state)
            self.sync_legacy()

    def sync_legacy(self):
        # Merge unresolved old rejections; never erase another scene's failure.
        rejection_path = self.folder / 'images/rejected.txt'
        rejected = set(int(x) for x in rejection_path.read_text().splitlines() if x.strip().isdigit()) if rejection_path.exists() else set()
        checked_path = self.folder / 'images/style_checked.txt'
        checked = set(checked_path.read_text().splitlines()) if checked_path.exists() else set()
        for scene in self.script['scenes']:
            n = scene['scene_number']; data = self.latest(n)
            if not data:
                continue
            if data['state'] == 'approved':
                rejected.discard(n); checked.add(f'scene_{n:03d}.png')
            else:
                checked.discard(f'scene_{n:03d}.png')
                if data['state'] in ('rejected', 'technical_failure', 'needs_attention'):
                    rejected.add(n)
        rejection_path.write_text(''.join(f'{n}\n' for n in sorted(rejected)), encoding='utf-8')
        checked_path.write_text(''.join(f'{n}\n' for n in sorted(checked)), encoding='utf-8')

    def status(self):
        self.scope()
        result = []
        for scene in self.script['scenes']:
            n = scene['scene_number']; data = self.latest(n)
            state = data['state'] if data else ('legacy_unverified' if (self.folder / f'images/approved/scene_{n:03d}.png').exists() else 'missing')
            if data:
                self.validate_request(data)
                if state == 'approved':
                    path = self.folder / f'images/approved/scene_{n:03d}.png'
                    if not path.exists() or digest(path) != data['image_sha256']:
                        state = 'approval_bytes_changed'
            result.append(dict(scene=n, state=state, attempt=data['attempt'] if data else 0))
        return result


def verify_for_assembly(folder):
    """Existing un-enrolled projects remain usable; enrolled projects fail closed."""
    if not (Path(folder) / 'images/style_state/manifest.sqlite3').exists():
        return
    db_path = Path(folder) / 'images/style_state/manifest.sqlite3'
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute('SELECT data FROM production WHERE id=1').fetchone()
    finally:
        connection.close()
    if not row:
        raise ValueError('Style state exists without a production authority manifest')
    scope = json.loads(row[0])
    style_path = Path(scope.get('style_root', str(STYLE))).resolve()
    if not style_path.is_relative_to(STYLE_HOME.resolve()):
        raise ValueError('Recorded style library is outside the repository authority')
    production = Production(folder, style=style_path)
    try:
        production.verify()
    finally:
        production.close()


def contact_sheet(paths, output):
    from PIL import Image, ImageDraw, ImageOps
    paths = [Path(p) for p in paths]
    if not paths:
        raise ValueError('No images supplied')
    sheet = Image.new('RGB', (960, ((len(paths)+2)//3)*206), '#eeeeee')
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        with Image.open(path) as im:
            thumb = ImageOps.contain(im.convert('RGB'), (312, 176))
        x, y = (i % 3)*320, (i//3)*206
        sheet.paste(thumb, (x, y)); draw.text((x+4, y+178), path.name[:45], fill='black')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path)
    parser.add_argument('--style-root', type=Path, default=STYLE)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--max-attempts', type=int, default=3)
    for name in ('prepare', 'review-template'):
        sub.add_parser(name).add_argument('scene', type=int)
    ingest = sub.add_parser('ingest'); ingest.add_argument('scene', type=int); ingest.add_argument('image', type=Path); ingest.add_argument('--receipt', required=True)
    review = sub.add_parser('review'); review.add_argument('scene', type=int); review.add_argument('review_json', type=Path); review.add_argument('--replace-approved', action='store_true')
    failure = sub.add_parser('technical-failure'); failure.add_argument('scene', type=int); failure.add_argument('reason')
    claim = sub.add_parser('claim'); claim.add_argument('scene', type=int); claim.add_argument('worker')
    sub.add_parser('status'); sub.add_parser('verify')
    sub.add_parser('checkpoint-template').add_argument('batch', type=int)
    checkpoint = sub.add_parser('checkpoint'); checkpoint.add_argument('batch', type=int); checkpoint.add_argument('review_json', type=Path)
    reopen = sub.add_parser('reopen'); reopen.add_argument('scene', type=int); reopen.add_argument('reason')
    sheet = sub.add_parser('contact-sheet'); sheet.add_argument('output'); sheet.add_argument('images', nargs='+')
    args = parser.parse_args()
    if args.command == 'contact-sheet':
        contact_sheet(args.images, args.output); return
    if not args.production:
        parser.error('--production is mandatory; workers never read the global current-video pointer')
    p = Production(args.production, style=args.style_root)
    try:
        if args.command == 'init': result = p.init(args.max_attempts)
        elif args.command == 'prepare': result = p.prepare(args.scene)
        elif args.command == 'ingest': result = p.ingest(args.scene, args.image, args.receipt)
        elif args.command == 'review-template': result = p.review_template(args.scene)
        elif args.command == 'review': result = p.review(args.scene, read(args.review_json), args.replace_approved)
        elif args.command == 'technical-failure': result = p.technical_failure(args.scene, args.reason)
        elif args.command == 'claim': result = p.claim(args.scene, args.worker)
        elif args.command == 'verify': p.verify(); result = {'verified': True}
        elif args.command == 'checkpoint-template': result = p.checkpoint_template(args.batch)
        elif args.command == 'checkpoint': result = p.checkpoint(args.batch, read(args.review_json))
        elif args.command == 'reopen': result = p.reopen_audited_scene(args.scene, args.reason)
        else: result = p.status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        p.close()


if __name__ == '__main__':
    main()
