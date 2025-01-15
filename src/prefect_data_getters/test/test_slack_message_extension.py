import unittest

import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
import unittest

from datetime import datetime
from prefect_data_getters.stores.documents import SlackMessageDocument

from prefect_data_getters.stores.rag_man import MultiSourceSearcher, extend_slack_message
import  utilities.constants as C
class TestExample(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.ms = MultiSourceSearcher()
    def test_sample(self):
        async def atest():   
            docs = await self.ms.search(
                query="lat long",
                top_k=6,
                indexes=["slack_messages"],
                run_llm_reduction=False
            )

            self.assertGreater(len(docs), 0, "Search should return documents.")

            # Extend each Slack message with context
            for i, doc in enumerate(docs):
                self.assertIsNotNone(doc.page_content, f"Document {i+1} should have extended text.")
                print(f"Extended document {i+1}: {doc.page_content}")

        asyncio.run(atest())


        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
