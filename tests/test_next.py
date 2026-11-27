import unittest

from test_core import Invalid, apply, build, feedback, get, md, validate_patch
from core import next_prompt


class GuidedVerification(unittest.TestCase):
    def test_next_advances_one_action(self):
        patch = build(get())
        first = next_prompt(patch)
        self.assertEqual((first['kind'], first['step_id'], first['action_index']), ('action', 'step_01', 1))
        apply(patch, feedback(patch))
        apply(patch, feedback(patch, 'step_02', 1))
        current = next_prompt(patch)
        self.assertEqual((current['step_id'], current['action_index']), ('step_02', 2))
        self.assertEqual(current['expected'], patch['steps'][1]['actions'][1]['expected'])

    def test_documentary_preview_cannot_advance(self):
        patch = build(get('vscode_127'))
        self.assertEqual(next_prompt(patch)['kind'], 'preview')
        with self.assertRaises(Invalid):
            apply(patch, feedback(patch, patch['steps'][0]['id'], actor='user'))

    def test_block_has_no_suggested_action(self):
        prompt = next_prompt(build(get('version_unknown')))
        self.assertEqual(prompt['kind'], 'evidence')
        self.assertNotIn('action', prompt)

    def test_failed_step_stops_subsequent_instructions(self):
        patch = build(get())
        apply(patch, feedback(patch, outcome='failure', met=False))
        self.assertEqual(next_prompt(patch)['kind'], 'stopped')
        for public in (True, False):
            self.assertNotIn(patch['steps'][1]['actions'][0]['action'], md(patch, public))

    def test_block_stops_subsequent_instructions(self):
        case = get()
        case['steps'][0]['conflict'] = True
        patch = build(case)
        self.assertNotIn(patch['steps'][1]['actions'][0]['action'], md(patch))

    def test_negative_goal_is_preserved_and_terminal(self):
        patch = build(get('unchanged'))
        apply(patch, feedback(patch, patch['steps'][0]['id']))
        self.assertEqual(next_prompt(patch)['kind'], 'goal')
        failure = feedback(patch, '__goal__', 0, outcome='failure', met=False)
        apply(patch, failure)
        self.assertEqual(validate_patch(patch)['final_confirmation'], failure)
        self.assertEqual((next_prompt(patch)['kind'], patch['status']), ('stopped', 'failed'))
        self.assertIn('未达成', md(patch, True))
        with self.assertRaises(Invalid):
            apply(patch, feedback(patch, '__goal__', 0))

    def test_ambiguous_goal_confirmation_rejected(self):
        patch = build(get('unchanged'))
        apply(patch, feedback(patch, patch['steps'][0]['id']))
        with self.assertRaises(Invalid):
            apply(patch, feedback(patch, '__goal__', 0, met=False))

    def test_whitespace_cannot_turn_unknown_into_known(self):
        case = get()
        case['environment']['version'] = ' unknown '
        for source in case['sources']:
            source['scope'] = case['environment']
        self.assertEqual(build(case)['status'], 'blocked')
