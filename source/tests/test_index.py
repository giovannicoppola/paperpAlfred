#!/usr/bin/env python3
"""Regression tests for the paperpAlfred indexer and search filters.

Each test pins a bug that previously either corrupted the index silently or
left the workflow permanently broken. Run with:

    python3 tests/test_index.py
"""

import copy
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(HERE)
FIXTURE = os.path.join(SOURCE, 'demo_library.json')
sys.path.insert(0, SOURCE)


def load_fixture():
    with open(FIXTURE) as f:
        return json.load(f)


class IndexTestCase(unittest.TestCase):
    """Builds an index in a scratch workflow-data folder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, 'home')
        os.makedirs(self.home)
        self.env = dict(os.environ,
                        HOME=self.home,
                        alfred_workflow_bundleid='test.paperpAlfred',
                        MAXRESULTS='99')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_library(self, records, name='library.json'):
        path = os.path.join(self.tmp, name)
        with open(path, 'w') as f:
            json.dump(records, f)
        return path

    def build(self, records):
        """Run createLibrary in a subprocess and return the resulting DB path."""
        path = self.write_library(records)
        db = os.path.join(self.tmp, 'index.db')
        subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, %r);'
             'from build_db import createLibrary;'
             'createLibrary(%r, %r)' % (SOURCE, path, db)],
            env=dict(self.env, PAPLIBRARY=path), check=True,
            capture_output=True, cwd=SOURCE)
        return db

    def run_filter(self, script, query, library=None, extra_env=None):
        """Run one of the Script Filters and return (parsed json, returncode)."""
        env = dict(self.env, PAPLIBRARY=library or '')
        env.update(extra_env or {})
        proc = subprocess.run([sys.executable, script, query],
                              env=env, capture_output=True, text=True, cwd=SOURCE)
        try:
            return json.loads(proc.stdout), proc
        except json.JSONDecodeError:
            return None, proc

    def rows(self, db, sql):
        conn = sqlite3.connect(db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()


class TestFlattening(IndexTestCase):

    def test_authorless_record_keeps_its_own_year(self):
        """A record with no authors used to inherit the previous record's year."""
        records = load_fixture()[:2]
        records[1]['author'] = []
        records[1]['published'] = {'year': '1999'}
        records[1]['title'] = 'AUTHORLESS'
        db = self.build(records)
        year, = self.rows(db, "SELECT year FROM papers WHERE title='AUTHORLESS'")[0]
        self.assertEqual(year, '1999')

    def test_authorless_first_record_does_not_abort_the_build(self):
        """This used to raise UnboundLocalError and kill the whole rebuild."""
        records = load_fixture()[:2]
        records[0]['author'] = []
        db = self.build(records)
        self.assertEqual(self.rows(db, "SELECT count(*) FROM papers")[0][0], 2)

    def test_library_with_no_folders_builds(self):
        """The long-standing 'fails if nothing is in a folder' bug."""
        records = load_fixture()
        for r in records:
            r['folders'] = []
            r.pop('foldersNamed', None)
        db = self.build(records)
        self.assertEqual(self.rows(db, "SELECT count(*) FROM Folders")[0][0], 0)
        self.assertEqual(self.rows(db, "SELECT count(*) FROM papers")[0][0], len(records))

    def test_record_missing_optional_keys_builds(self):
        records = load_fixture()[:1]
        for key in ('labels', 'labelsNamed', 'folders', 'foldersNamed',
                    'attachments', 'published', 'volume', 'issue', 'pages',
                    'journal', 'pmid', 'incomplete'):
            records[0].pop(key, None)
        db = self.build(records)
        self.assertEqual(self.rows(db, "SELECT count(*) FROM papers")[0][0], 1)

    def test_label_containing_a_comma_stays_one_label(self):
        """A comma in a name used to split it into two labels with wrong IDs."""
        records = load_fixture()[:1]
        records[0]['labelsNamed'] = ['Alzheimer, early onset']
        records[0]['labels'] = ['the-real-id']
        db = self.build(records)
        rows = self.rows(db, "SELECT label, LabelID FROM Labels")
        self.assertEqual(rows, [('Alzheimer, early onset', 'the-real-id')])

    def test_mismatched_name_and_id_arrays_do_not_crash(self):
        records = load_fixture()[:1]
        records[0]['labelsNamed'] = ['solo']
        records[0]['labels'] = ['id1', 'id2', 'id3']
        db = self.build(records)
        self.assertEqual(self.rows(db, "SELECT label FROM Labels"), [('solo',)])

    def test_repeated_author_name_keeps_the_separator(self):
        """Separators were chosen by comparing values to the last element."""
        records = load_fixture()[:1]
        records[0]['author'] = [
            {'formatted': 'Smith J', 'last': 'Smith'},
            {'formatted': 'Smith J', 'last': 'Smith'},
            {'formatted': 'Jones A', 'last': 'Jones'},
        ]
        db = self.build(records)
        ref, = self.rows(db, "SELECT fullReference FROM papers")[0]
        self.assertTrue(ref.startswith('Smith J, Smith J, Jones A.'), ref)

    def test_full_reference_uses_volume_not_issue(self):
        records = load_fixture()[:1]
        records[0]['volume'] = '329'
        records[0]['issue'] = '5995'
        records[0]['pages'] = '1068-1071'
        db = self.build(records)
        ref, = self.rows(db, "SELECT fullReference FROM papers")[0]
        self.assertIn('329(5995):1068-1071', ref)

    def test_single_author_byline_is_not_doubled(self):
        records = load_fixture()[:1]
        records[0]['author'] = [{'formatted': 'Dolgin E', 'last': 'Dolgin'}]
        db = self.build(records)
        subtitle, = self.rows(db, "SELECT subtitle FROM papers")[0]
        self.assertTrue(subtitle.startswith('Dolgin,'), subtitle)
        self.assertNotIn('Dolgin-Dolgin', subtitle)

    def test_glob_metacharacters_in_title_are_escaped(self):
        records = load_fixture()[:1]
        records[0]['title'] = '[Corrigendum] Effects of X'
        records[0]['attachments'] = [{'source_filename': 'scan.pdf', 'article_pdf': 1}]
        db = self.build(records)
        name, = self.rows(db, "SELECT fileName FROM papers")[0]
        self.assertIn('[[]', name)
        self.assertIn('[]]', name)

    def test_article_pdf_is_preferred_over_a_supplement(self):
        records = load_fixture()[:1]
        records[0]['attachments'] = [
            {'source_filename': 'supplement.pdf', 'gdrive_id': 'supp'},
            {'source_filename': '[article_pdf].pdf', 'filename': 'paper.pdf',
             'article_pdf': 1, 'gdrive_id': 'real'},
        ]
        db = self.build(records)
        name, gdrive = self.rows(db, "SELECT fileName, gdrive_id FROM papers")[0]
        self.assertEqual(name, 'paper.pdf')
        self.assertEqual(gdrive, 'real')

    def test_publication_type_named_total_does_not_corrupt_counts(self):
        records = load_fixture()[:1]
        records[0]['pubtype'] = 'Total'
        records[0].pop('kind', None)
        records[0]['labelsNamed'] = ['tagged']
        records[0]['labels'] = ['tid']
        db = self.build(records)
        total, = self.rows(db, "SELECT totalLabel FROM Labels")[0]
        self.assertEqual(total, '1')


class TestSearch(IndexTestCase):

    def setUp(self):
        super().setUp()
        self.library = self.write_library(load_fixture())

    def search(self, query, **kw):
        return self.run_filter('papers.py', query, library=self.library, **kw)

    def test_plain_search_returns_results(self):
        data, proc = self.search('aging')
        self.assertIsNotNone(data, proc.stderr)
        self.assertTrue(data['items'])

    def test_diacritics_fold(self):
        """FTS3's tokenizer could not match Muller against Müller."""
        records = load_fixture()[:1]
        records[0]['title'] = 'Über die Müller Studie'
        library = self.write_library(records, 'umlaut.json')
        data, proc = self.run_filter('papers.py', 'Muller', library=library)
        self.assertIsNotNone(data, proc.stderr)
        self.assertEqual(data['items'][0]['title'], 'Über die Müller Studie')

    def test_query_syntax_characters_do_not_crash(self):
        """Typing ( or " used to raise malformed MATCH expression."""
        for query in ['gene"', '(paren', '"unclosed', 'a AND', 'NEAR', 'x^y', '*']:
            with self.subTest(query=query):
                data, proc = self.search(query)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIsNotNone(data, proc.stderr)

    def test_trailing_space_is_harmless(self):
        data, proc = self.search('aging ')
        self.assertIsNotNone(data, proc.stderr)
        self.assertTrue(data['items'])

    def test_empty_query_shows_the_welcome_item(self):
        data, proc = self.search('')
        self.assertIsNotNone(data, proc.stderr)
        self.assertEqual(data['items'][0]['arg'], 'ShowHelpWindow')

    def test_blank_maxresults_falls_back_to_the_default(self):
        data, proc = self.search('aging', extra_env={'MAXRESULTS': ''})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIsNotNone(data, proc.stderr)

    def test_unset_library_shows_a_friendly_item(self):
        env = dict(self.env)
        env.pop('PAPLIBRARY', None)
        proc = subprocess.run([sys.executable, 'papers.py', 'aging'],
                              env=env, capture_output=True, text=True, cwd=SOURCE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Paperpile library not set', proc.stdout)

    def test_missing_library_file_shows_a_friendly_item(self):
        data, proc = self.run_filter('papers.py', 'aging',
                                     library='/nowhere/library.json')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Library file missing', data['items'][0]['title'])

    def test_ascending_flag_inverts_the_order(self):
        desc, _ = self.search('the')
        asc, _ = self.search('the --a')
        self.assertTrue(desc['items'] and asc['items'])
        self.assertNotEqual(desc['items'][0]['title'], asc['items'][0]['title'])

    def test_bare_ascending_flag_is_not_searched_for(self):
        data, proc = self.search('--a')
        self.assertIsNotNone(data, proc.stderr)
        self.assertEqual(data['items'][0]['arg'], 'ShowHelpWindow')

    def test_field_scoped_search(self):
        data, proc = self.search('year:2010')
        self.assertIsNotNone(data, proc.stderr)
        self.assertTrue(all('2010' in i['subtitle'] for i in data['items']))

    def test_label_scope_from_the_picker(self):
        label_id = load_fixture()[0]['labels'][0]
        data, proc = self.search('', extra_env={'mySource': 'label',
                                                'myLabelID': label_id})
        self.assertIsNotNone(data, proc.stderr)
        self.assertTrue(data['items'])


class TestPickers(IndexTestCase):

    def setUp(self):
        super().setUp()
        self.library = self.write_library(load_fixture())

    def test_pickers_build_the_index_on_a_fresh_install(self):
        """ppl/ppf/ppty used to raise 'no such table' before the first ppp."""
        for script in ('labels.py', 'folders.py', 'myTypes.py'):
            with self.subTest(script=script):
                shutil.rmtree(self.home, ignore_errors=True)
                os.makedirs(self.home)
                data, proc = self.run_filter(script, '', library=self.library)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(data['items'], proc.stderr)

    def test_picker_query_syntax_characters_do_not_crash(self):
        for script in ('labels.py', 'folders.py', 'myTypes.py'):
            with self.subTest(script=script):
                data, proc = self.run_filter(script, '(oops"', library=self.library)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_label_rows_carry_the_matching_id(self):
        data, proc = self.run_filter('labels.py', '', library=self.library)
        self.assertIsNotNone(data, proc.stderr)
        ids = {r['labels'][0] for r in load_fixture() if r.get('labels')}
        for item in data['items']:
            self.assertIn(item['variables']['myLabelID'],
                          ids | {r for rec in load_fixture()
                                 for r in rec.get('labels', [])})


class TestRebuildRecovery(IndexTestCase):

    def test_interrupted_rebuild_leaves_no_partial_index(self):
        """Alfred terminates the previous script on every keystroke. A killed
        rebuild used to leave a truncated DB that was never rebuilt again."""
        library = self.write_library(load_fixture() * 400)
        wf = os.path.join(
            self.home, 'Library/Caches/com.runningwithcrayons.Alfred',
            'Workflow Data/test.paperpAlfred')

        proc = subprocess.Popen([sys.executable, 'papers.py', 'ag'],
                                env=dict(self.env, PAPLIBRARY=library),
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, cwd=SOURCE)
        try:
            proc.wait(timeout=0.25)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        index = os.path.join(wf, 'index.db')
        timestamp = os.path.join(wf, 'timestamp.txt')
        # Either the rebuild finished, or it left nothing behind -- never a
        # timestamp claiming an index that is not there.
        if os.path.exists(timestamp):
            self.assertTrue(os.path.exists(index))

        # Whatever happened, the next run must recover on its own.
        data, proc2 = self.run_filter('papers.py', 'aging', library=library)
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertTrue(data['items'], proc2.stderr)

    def test_deleted_index_is_rebuilt_even_when_the_timestamp_matches(self):
        library = self.write_library(load_fixture())
        self.run_filter('papers.py', 'aging', library=library)
        wf = os.path.join(
            self.home, 'Library/Caches/com.runningwithcrayons.Alfred',
            'Workflow Data/test.paperpAlfred')
        os.remove(os.path.join(wf, 'index.db'))

        data, proc = self.run_filter('papers.py', 'aging', library=library)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(data['items'], proc.stderr)

    def test_truncated_index_is_rebuilt(self):
        library = self.write_library(load_fixture())
        self.run_filter('papers.py', 'aging', library=library)
        wf = os.path.join(
            self.home, 'Library/Caches/com.runningwithcrayons.Alfred',
            'Workflow Data/test.paperpAlfred')
        with open(os.path.join(wf, 'index.db'), 'w') as f:
            f.write('')

        data, proc = self.run_filter('papers.py', 'aging', library=library)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(data['items'], proc.stderr)

    def test_pickers_refresh_when_the_library_changes(self):
        records = load_fixture()
        library = self.write_library(records)
        self.run_filter('labels.py', '', library=library)

        extra = copy.deepcopy(records[0])
        extra['_id'] = 'brand-new'
        extra['labelsNamed'] = ['freshly-added']
        extra['labels'] = ['fresh-id']
        with open(library, 'w') as f:
            json.dump(records + [extra], f)
        os.utime(library, (0, 0))

        data, proc = self.run_filter('labels.py', '', library=library)
        self.assertIsNotNone(data, proc.stderr)
        self.assertIn('freshly-added',
                      [i['title'].rsplit(' (', 1)[0] for i in data['items']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
