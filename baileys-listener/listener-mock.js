// baileys-listener/listener-mock.js
// Mock listener for testing when WhatsApp Web is blocked by ISP

const axios = require('axios');
const pino = require('pino');

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

logger.info('🔧 MOCK LISTENER STARTED (for testing without real WhatsApp)');
logger.info('Send test messages from another terminal:');
logger.info('curl -X POST http://localhost:3001/test -H "Content-Type: application/json" -d \'{"message":"test"}\'');

// Mock express server for testing
const express = require('express');
const app = express();
app.use(express.json());

app.post('/test', async (req, res) => {
    const { message } = req.body;
    const senderPhone = '+919999999999';

    logger.info(`📬 Mock message from ${senderPhone}: "${message}"`);

    try {
        const response = await axios.post(
            `${BACKEND_URL}/api/baileys/process`,
            {
                sender_phone: senderPhone,
                message_text: message,
                media: null
            },
            {
                headers: {
                    'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                },
                timeout: 30000
            }
        );

        logger.info(`✅ Backend response:`, response.data);
        res.json(response.data);
    } catch (error) {
        logger.error('❌ Backend error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

app.listen(3001, () => {
    logger.info('🚀 Mock listener listening on http://localhost:3001');
    logger.info('For testing when ISP blocks WhatsApp Web');
});
