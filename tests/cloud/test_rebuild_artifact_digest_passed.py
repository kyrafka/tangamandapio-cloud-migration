import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
REBUILD = ROOT / "iac" / "cloudformation" / "rebuild.sh"


class RebuildArtifactDigestTests(unittest.TestCase):
    def test_capacity_update_passes_the_uploaded_artifact_digest(self):
        script = REBUILD.read_text(encoding="utf-8")
        final_update = script.rsplit("BOOTSTRAP_MODE=false", 1)[-1]
        self.assertIn('APPLICATION_ARTIFACT_KEY="$ARTIFACT_KEY"', final_update)
        self.assertIn('APPLICATION_ARTIFACT_REVISION="$REVISION"', final_update)
        self.assertIn('APPLICATION_ARTIFACT_SHA256="$ARTIFACT_SHA256"', final_update)


if __name__ == "__main__":
    unittest.main()
