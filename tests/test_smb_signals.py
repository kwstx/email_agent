import unittest
import json
from src.scoring.detector import AgentSignalDetector

class TestSMBSignals(unittest.TestCase):
    def setUp(self):
        self.detector = AgentSignalDetector()

    def test_smb_scenario(self):
        # Scenario 1: A perfect SMB match
        smb_content = """
        We are a fast-growing team and recently closed our Series A.
        Our mission is to build the next generation of AI agents.
        Meet the Founders at our upcoming event or Book a Demo today!
        --- CAREERS ---
        We are looking for our First Engineering Hire and a Founding Designer.
        """
        
        analysis = self.detector.analyze_text(smb_content)
        self.assertGreaterEqual(analysis['total_score'], 10)
        self.assertTrue(any("SMB_INDICATOR" in s for s in analysis['signals']))
        self.assertTrue(any(r['category'] == "SMB_FILTRATION" for r in analysis['reasoning']))
        self.assertEqual(analysis['tier'], "high_priority")

    def test_enterprise_scenario(self):
        # Scenario 2: Large Enterprise
        ent_content = """
        We are a Fortune 500 company with a global presence across 50 countries.
        Our ESG Report for 2023 is now available on our Investor Relations page.
        With over 10,000+ employees, we lead the multi-national market.
        Please contact our Procurement department for vendor inquiries.
        """
        
        analysis = self.detector.analyze_text(ent_content)
        self.assertLess(analysis['total_score'], 0)
        self.assertIn("ENTERPRISE_DISQUALIFIER", analysis['signals'])
        self.assertEqual(analysis['tier'], "disqualified")

    def test_mixed_scenario(self):
        # Scenario 3: Mixed
        mixed_content = """
        Fortune 500 company investing in autonomous workflows.
        We use OpenAI API and LangChain at scale.
        Check our Investor Relations for more.
        """
        analysis = self.detector.analyze_text(mixed_content)
        self.assertLess(analysis['total_score'], 0)
        self.assertEqual(analysis['tier'], "disqualified")

if __name__ == "__main__":
    unittest.main()
