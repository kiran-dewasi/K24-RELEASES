import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.orchestrator import K24Orchestrator, DraftResponse
from backend.intent_recognizer import Intent, IntentType
from backend.context_manager import UserContext

class TestOrchestrator(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Setup patches
        self.patcher1 = patch('backend.orchestrator.IntentRecognizer')
        self.patcher2 = patch('backend.orchestrator.ContextManager')
        self.patcher3 = patch('backend.orchestrator.TallyConnector')
        
        self.MockIntent = self.patcher1.start()
        self.MockContext = self.patcher2.start()
        self.MockTally = self.patcher3.start()
        
        # Setup Orchestrator with mocks
        self.orch = K24Orchestrator(api_key="dummy")
        self.orch.intent_recognizer = AsyncMock()
        self.orch.context_manager = MagicMock()
        self.orch.tally = MagicMock()
        
        # Default context
        self.orch.context_manager.get_context.return_value = UserContext.create_default("test_user")

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()

    async def test_create_sale_draft_logic(self):
        """Test that 'Sale 5k to Sharma' creates a valid draft"""
        
        # Mock Intent: "Sale 5k to Sharma"
        mock_intent = Intent(
            action=IntentType.CREATE_SALE,
            entity="Sharma",
            parameters={"amount": 5000, "item": "Consulting"},
            confidence=0.9
        )
        self.orch.intent_recognizer.recognize.return_value = mock_intent
        
        # Execute
        response = await self.orch.process_message("test_user", "Sale 5k to Sharma")
        
        # Verify
        self.assertEqual(response['type'], 'draft_voucher')
        self.assertEqual(response['data']['party_name'], 'Sharma')
        self.assertEqual(response['data']['total_amount'], 5000)
        self.assertEqual(response['data']['voucher_type'], 'Sales')
        self.assertIn("Save?", response['message'])

    async def test_missing_party_clarification(self):
        """Test that missing party triggers clarification"""
        
        # Mock Intent: "Sale 5k" (No party)
        mock_intent = Intent(
            action=IntentType.CREATE_SALE,
            entity=None, 
            parameters={"amount": 5000},
            confidence=0.8
        )
        self.orch.intent_recognizer.recognize.return_value = mock_intent
        
        # Execute
        response = await self.orch.process_message("test_user", "Sale 5k")
        
        # Verify
        self.assertEqual(response['type'], 'clarification')
        self.assertIn("Party name?", response['message'])
        self.assertEqual(response['data']['missing_slot'], 'party')

    async def test_unknown_intent_handling(self):
        """Test graceful fallback for unknown intents"""
        
        mock_intent = Intent(
            action=IntentType.UNKNOWN,
            confidence=0.2
        )
        self.orch.intent_recognizer.recognize.return_value = mock_intent
        
        response = await self.orch.process_message("test_user", "blah blah")
        
        self.assertEqual(response['type'], 'clarification')
        self.assertIn("Unclear", response['message'])

if __name__ == '__main__':
    unittest.main()
