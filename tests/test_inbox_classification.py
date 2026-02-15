
import unittest
from src.outreach.inbox_monitor import InboxMonitor

class TestInboxClassification(unittest.TestCase):
    def setUp(self):
        self.monitor = InboxMonitor()
        # Ensure OpenAI is disabled for unit test to rely on Rules
        self.monitor.openai_client = None 

    def test_interest_keywords(self):
        subject = "Re: Discussion"
        body = "Hi, thanks for reaching out. I'd be interested in a demo. Let me know available times."
        classification = self.monitor.classify_reply_content(subject, body)
        self.assertEqual(classification, "interest")

    def test_opt_out_keywords(self):
        subject = "Unsubscribe"
        body = "Please remove me from your mailing list immediately."
        classification = self.monitor.classify_reply_content(subject, body)
        self.assertEqual(classification, "opt_out")

    def test_deferral_keywords(self):
        subject = "Automatic Reply"
        body = "I am currently out of office with limited access to email. Will reply upon return."
        classification = self.monitor.classify_reply_content(subject, body)
        self.assertEqual(classification, "deferral")
        
    def test_irrelevance_fallback(self):
        subject = "Re: Intro"
        body = "No thanks, we handle this in-house."
        classification = self.monitor.classify_reply_content(subject, body)
        self.assertEqual(classification, "irrelevance")

if __name__ == '__main__':
    unittest.main()
