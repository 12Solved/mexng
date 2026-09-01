"""run_dry() previously had no per-workflow error isolation (unlike run_db()),
so one bad workflow would abort the whole dry-run group (_dev_review.txt #13)."""
from mailextractor.app.processor.processor import run_dry


class _FakeWorkflow:
    def __init__(self, workflow_id, should_raise=False):
        self.workflow_id = workflow_id
        self.should_raise = should_raise
        self.ran = False

    def run(self, email, run_options=None):
        self.ran = True
        if self.should_raise:
            raise ValueError("boom")


class _FakeEmail:
    def __init__(self, id):
        self.id = id


def test_run_dry_isolates_workflow_failures():
    bad = _FakeWorkflow(1, should_raise=True)
    good = _FakeWorkflow(2)
    email = _FakeEmail(1)

    run_dry([(email, [bad, good])])  # must not raise

    assert bad.ran
    assert good.ran  # the failure of `bad` must not have skipped `good`
