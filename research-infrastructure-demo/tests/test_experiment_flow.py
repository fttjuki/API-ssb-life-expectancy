import unittest

import experiment_flow


class ExperimentFlowTests(unittest.TestCase):
    def test_only_consented_invitees_are_randomized(self):
        invitees = [
            {"invitee_code": "A", "consent": "yes"},
            {"invitee_code": "B", "consent": "no"},
            {"invitee_code": "C", "consent": "yes"},
        ]
        responses, summary = experiment_flow.run_experiment_flow(invitees, seed=1)
        self.assertEqual(summary["randomized"], 2)
        self.assertEqual(summary["not_consented"], 1)
        self.assertEqual(len(responses), 2)

    def test_randomization_is_reproducible_and_balanced(self):
        invitees = [{"invitee_code": f"I{i}", "consent": "yes"} for i in range(10)]
        first, _ = experiment_flow.run_experiment_flow(invitees, seed=42)
        second, _ = experiment_flow.run_experiment_flow(invitees, seed=42)
        self.assertEqual(first, second)
        arms = [row["assigned_arm"] for row in first]
        self.assertEqual(arms.count("control"), arms.count("intervention"))

    def test_small_experiment_arms_are_suppressed(self):
        invitees = [{"invitee_code": f"I{i}", "consent": "yes"} for i in range(4)]
        _, summary = experiment_flow.run_experiment_flow(invitees)
        self.assertEqual(summary["groups"]["control"], "suppressed")
        self.assertEqual(summary["groups"]["intervention"], "suppressed")

    def test_invalid_consent_is_rejected(self):
        invitees = [{"invitee_code": "I1", "consent": "maybe"}]
        with self.assertRaisesRegex(ValueError, "consent"):
            experiment_flow.run_experiment_flow(invitees)


if __name__ == "__main__":
    unittest.main()
