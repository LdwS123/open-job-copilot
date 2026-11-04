"""CV pipeline: example data -> base CVs -> tailored CV -> ATS check. Uses a temp output folder."""
import os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'runner')


def run(*a, **env):
    e = dict(os.environ, JOB_CV_DATA=os.path.join(HERE, '..', 'cv_data.example.json'), **env)
    return subprocess.run([sys.executable, '-I', *a], cwd=RUN, env=e, capture_output=True, text=True)


class CvPipeline(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def test_base_cvs_fit_one_page_and_pass_ats(self):
        r = run('cvgen.py', JOB_CV_DIR=self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run('ats_check.py', self.out, JOB_CV_DIR=self.out)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('FAIL: 0', r.stdout)

    def test_tailor_keeps_only_true_keywords_and_matches_location(self):
        r = run('tailor.py', '--family', 'sdr_bdr', '--lang', 'EN', '--role', 'Sales Development Representative', '--company', 'Acme',
                '--city', 'Dublin', '--country', 'Ireland', '--keywords', 'outbound,HubSpot,Salesforce,cold calling', JOB_CV_DIR=self.out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('ATS CHECK PASS', r.stdout)
        self.assertIn('open to relocation to Dublin, Ireland', r.stdout)
        self.assertIn("'Salesforce'", r.stdout.split('DROPPED')[1])      # not in the example facts: dropped, never added
        self.assertNotIn('Salesforce', r.stdout.split('KEPT')[1].split('DROPPED')[0])
        self.assertTrue(os.path.exists(os.path.join(self.out, 'tailored')))

    def test_remote_and_home_city_lines(self):
        for city, want in (('Remote', 'open to remote work'), ('Paris', 'Paris, France |')):
            r = run('tailor.py', '--family', 'sdr_bdr', '--lang', 'EN', '--role', 'SDR', '--company', 'Beta', '--city', city,
                    '--country', 'France', '--keywords', 'outbound', JOB_CV_DIR=self.out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('LOCATION LINE Paris, France', r.stdout)
            if city == 'Remote':
                self.assertIn(want, r.stdout)


if __name__ == '__main__':
    unittest.main()
