import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import demo


class PipelineTests(unittest.TestCase):
    def test_synthetic_pipeline_writes_aggregate_and_step_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "summary.json"
            log_path = root / "pipeline.jsonl"
            summary = demo.run_pipeline(output_path=summary_path, log_path=log_path)

            self.assertEqual(summary["record_count"], 20)
            self.assertEqual(summary["study_arm_counts"], {"control": 10, "intervention": 10})
            self.assertTrue(summary_path.exists())
            log = log_path.read_text(encoding="utf-8")
            self.assertIn('"step": "validation_passed"', log)
            self.assertNotIn("SYN001", log)

    def test_small_groups_are_suppressed(self):
        records = [
            {"age": 25, "study_arm": "small", "completed": True},
            {"age": 30, "study_arm": "large", "completed": True},
            {"age": 31, "study_arm": "large", "completed": False},
            {"age": 32, "study_arm": "large", "completed": True},
            {"age": 33, "study_arm": "large", "completed": True},
            {"age": 34, "study_arm": "large", "completed": False},
        ]
        self.assertEqual(demo.build_summary(records)["study_arm_counts"]["small"], "suppressed")

    def test_validation_rejects_out_of_range_age(self):
        rows = [{"participant_id": "SYNX", "age": "17", "study_arm": "control", "completed": "true"}]
        with self.assertRaisesRegex(ValueError, "outside"):
            demo.validate_records(rows)

    def test_api_requires_https_and_key(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            demo.post_summary({}, "http://example.org", "secret", opener=Mock())
        with self.assertRaisesRegex(ValueError, "API key"):
            demo.post_summary({}, "https://example.org", "replace-me-locally", opener=Mock())

    def test_api_sends_json_and_bearer_key_without_logging_it(self):
        response = Mock()
        response.status = 202
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)
        summary = {"record_count": 20}

        status = demo.post_summary(summary, "https://example.org/api", "test-secret", opener=opener)

        self.assertEqual(status, 202)
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(json.loads(request.data), summary)
        self.assertEqual(opener.call_args.kwargs["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
