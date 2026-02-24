// baileys-listener/listener.js
// K24 WhatsApp Message Handler with Smart Batching + Phone Routing

const makeWASocket = require('@whiskeysockets/baileys').default;
const { useMultiFileAuthState, DisconnectReason, downloadMediaMessage, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const pino = require('pino');
const http = require('http');

// Import batch handler for smart image grouping
const { batcher } = require('./batch-handler');

// Setup logging
const logger = pino(
    {
        transport: {
            target: 'pino-pretty',
            options: {
                colorize: true,
                translateTime: 'SYS:standard',
                ignore: 'pid,hostname'
            }
        }
    }
);


const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Authentication directory for Baileys multi-file auth state
// SESSION_DIR can be set in production (e.g. on Railway) to point to a persistent 
// volume or mounted directory to preserve WhatsApp session across deployments.
// If SESSION_DIR is not set, defaults to ./auth next to listener.js
const AUTH_DIR = process.env.SESSION_DIR || path.join(__dirname, 'auth');

// ============================================
// QR HTTP SERVER (for Railway / cloud envs)
// Serves the current QR at GET /qr as an HTML page with a scannable image
// ============================================
let latestQRDataUrl = null; // set each time a QR is generated

// Railway sets $PORT automatically — always use it first so the proxy can reach us.
// Falls back to QR_PORT (manual override) then 3000 for local dev.
const QR_PORT = parseInt(process.env.PORT || process.env.QR_PORT || '3000', 10);
const qrServer = http.createServer(async (req, res) => {
    if (req.url === '/qr' || req.url === '/') {
        if (!latestQRDataUrl) {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(`<html><body style="font-family:sans-serif;text-align:center;padding:40px">
                <h2>WhatsApp QR Code</h2>
                <p>No QR code available yet. The service may already be connected, or is still initializing.</p>
                <p><a href="/qr">Refresh</a></p>
            </body></html>`);
            return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`<html><body style="font-family:sans-serif;text-align:center;padding:40px">
            <h2>Scan this QR to connect WhatsApp</h2>
            <p style="color:#888">Generated at: ${new Date().toISOString()}</p>
            <img src="${latestQRDataUrl}" alt="WhatsApp QR" style="width:300px;height:300px" />
            <p><a href="/qr">Refresh</a></p>
        </body></html>`);
    } else if (req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'running', qrAvailable: !!latestQRDataUrl }));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});
qrServer.listen(QR_PORT, '0.0.0.0', () => {
    logger.info(`🌐 QR HTTP server listening on port ${QR_PORT} — visit /qr to scan`);
});


// ============================================
// PHONE ROUTING CACHE (24-hour sessions)
// ============================================
const routingCache = new Map(); // phone -> { userId, customerName, expiresAt }
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// LID-to-Phone resolution cache
// WhatsApp sometimes sends messages with LID (Linked ID) format instead of phone numbers
// This cache stores the mapping once we resolve it
const lidToPhoneCache = new Map(); // lid@lid -> phoneNumber

// Pending conflict resolutions: phone -> { matches, expiresAt }
const pendingConflicts = new Map();
const CONFLICT_TTL_MS = 5 * 60 * 1000; // 5 minutes to respond

/**
 * Identify which K24 user owns this phone number.
 * NOTE: The cloud backend does NOT expose /api/whatsapp/identify-user.
 * Tenant resolution is done server-side inside /api/whatsapp/cloud/incoming.
 * This function always returns 'unknown' so the listener skips client-side routing
 * and lets the cloud queue handle multi-tenancy.
 */
async function identifyUserByPhone(phone) {
    // Tenant resolution is handled by the cloud backend's incoming endpoint.
    // Return 'unknown' to skip local routing and proceed directly to cloud queue.
    return { status: 'unknown' };
}

/**
 * Handle conflict resolution when user sends a client code
 */
function resolveConflictByCode(phone, code) {
    const pending = pendingConflicts.get(phone);
    if (!pending || pending.expiresAt < Date.now()) {
        return { resolved: false, reason: 'No pending conflict or expired' };
    }

    // Find match by client_code
    const match = pending.matches.find(m =>
        m.client_code && m.client_code.toUpperCase() === code.toUpperCase()
    );

    if (match) {
        // Cache the resolution
        routingCache.set(phone, {
            userId: match.user_id,
            customerName: match.customer_name,
            expiresAt: Date.now() + CACHE_TTL_MS
        });
        pendingConflicts.delete(phone);
        return { resolved: true, userId: match.user_id, customerName: match.customer_name };
    }

    return { resolved: false, reason: 'No matching code found' };
}

// Ensure auth directory exists before initializing Baileys auth state
// This is critical for first-time setup and production deployments where the 
// directory may not exist yet (e.g. fresh Railway container)
if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
}

// The WhatsApp number this Baileys session is connected to (the "bot" number).
// Set once we connect. Can also be overridden via BOT_NUMBER env var.
let botNumber = process.env.BOT_NUMBER || null;

async function startBaileys() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    // ── FIX 1: Always fetch the latest WA Web version.
    // Using an outdated/bundled version causes WhatsApp to reject the WS
    // upgrade with HTTP 405. Fetching the live version solves this.
    let waVersion;
    try {
        const { version, isLatest } = await fetchLatestBaileysVersion();
        waVersion = version;
        logger.info(`✅ WA version fetched: ${version.join('.')} (isLatest: ${isLatest})`);
    } catch (e) {
        logger.warn(`⚠️ Could not fetch latest WA version (${e.message}). Using bundled fallback.`);
    }

    const sock = makeWASocket({
        version: waVersion,           // ← FIX 1: use real WA version
        auth: state,
        // ── FIX 2: Pass a silent pino logger to Baileys internals.
        // Passing the verbose app logger causes Baileys to flood stdout
        // and can interfere with QR display. Silent keeps noise out.
        logger: pino({ level: 'silent' }),
        printQRInTerminal: true,      // always print QR to stdout as fallback
        syncFullHistory: false,
        shouldSyncHistoryMessage: () => false,
        generateHighQualityLinkPreview: false,
        // ── FIX 3: Use a realistic browser string.
        // Non-standard version strings (like "1.0.0") cause 405 ws rejections.
        browser: ["K24 Agent", "Chrome", "120.0.0"],
        connectTimeoutMs: 60000,
        keepAliveIntervalMs: 10000,
    });

    // QR Code Handler (shows once on first run)
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        // ── Verbose connection logging for Railway logs
        logger.info(`[connection.update] connection=${connection ?? 'n/a'} | qr=${qr ? 'PRESENT' : 'absent'} | statusCode=${lastDisconnect?.error?.output?.statusCode ?? 'n/a'}`);

        if (qr) {
            logger.info('📱 QR CODE GENERATED — scan with WhatsApp now!');
            // Print ASCII QR to stdout (visible in Railway logs)
            try {
                console.log('\n');
                const qrAscii = await QRCode.toString(qr, { type: 'terminal', small: true });
                console.log(qrAscii);
                console.log('\n');
            } catch (e) {
                logger.warn('Could not render ASCII QR: ' + e.message);
            }
            // Also create a data URL QR so the /qr HTTP endpoint can serve it
            try {
                latestQRDataUrl = await QRCode.toDataURL(qr);
                logger.info(`🌐 QR also available at: http://<your-railway-url>/qr`);
            } catch (e) {
                logger.warn('Could not generate QR data URL: ' + e.message);
            }
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut && statusCode !== DisconnectReason.connectionReplaced;

            logger.error(`Connection closed. Status: ${statusCode}, Reconnecting: ${shouldReconnect}`);
            if (lastDisconnect?.error) {
                logger.error('Disconnect error message: ' + lastDisconnect.error.message);
            }

            if (statusCode === DisconnectReason.connectionReplaced) {
                logger.error('⚠️ Connection Replaced: Another session opened this WhatsApp account. Stopping.');
                process.exit(0);
            }

            if (shouldReconnect) {
                // Small delay before reconnecting to avoid hammering WA servers
                logger.info('⏳ Reconnecting in 5 seconds...');
                setTimeout(() => startBaileys(), 5000);
            }
        } else if (connection === 'open') {
            latestQRDataUrl = null; // Clear QR — we're connected
            logger.info('✅ WhatsApp Connected Successfully');
            // Extract the bot number (our own number) from sock.user.id
            // sock.user.id format: "<number>@s.whatsapp.net" or "<number>:<device>@s.whatsapp.net"
            const rawId = sock.user?.id || '';
            const extractedNumber = rawId.split('@')[0].split(':')[0];
            if (extractedNumber) {
                botNumber = extractedNumber;
                logger.info(`📱 Bot Number: +${botNumber}`);
            } else {
                logger.warn('⚠️ Could not extract bot number from sock.user.id: ' + rawId);
            }

            // Initialize the message batcher with socket and download function
            batcher.init(sock, downloadMediaMessage);
            logger.info('📦 Message batcher initialized for smart batching');
        }
    });

    // Credentials Handler
    sock.ev.on('creds.update', saveCreds);

    // MESSAGE HANDLER (The Core Logic)
    sock.ev.on('messages.upsert', async (m) => {
        try {
            const msg = m.messages[0];

            if (!msg.message) return; // Ignore if no message content

            // Ignore outgoing messages (only process incoming)
            if (msg.key.fromMe) return;

            // ============================================
            // LID-TO-PHONE RESOLUTION
            // WhatsApp sometimes sends messages with LID format instead of phone
            // We need to resolve LID to actual phone number
            // ============================================
            let remoteJid = msg.key.remoteJid;
            let senderNumber = '';
            const isLidFormat = remoteJid.endsWith('@lid');

            if (isLidFormat) {
                // This is LID format - need to resolve to phone
                logger.info(`🔄 LID detected: ${remoteJid}`);

                // Try to get phone from participant field or message context
                const participant = msg.key.participant;
                if (participant && participant.includes('@s.whatsapp.net')) {
                    senderNumber = participant.replace('@s.whatsapp.net', '');
                    logger.info(`✅ Resolved LID to phone via participant: ${senderNumber}`);
                } else {
                    // Try to get from Baileys store/contacts
                    try {
                        // Check if we have this LID in our local cache
                        const cachedPhone = lidToPhoneCache.get(remoteJid);
                        if (cachedPhone) {
                            senderNumber = cachedPhone;
                            logger.info(`✅ Resolved LID from cache: ${senderNumber}`);
                        } else {
                            // Check pushName for phone-like patterns or use LID as fallback
                            const pushName = msg.pushName || '';

                            // Last resort: extract numbers from LID (not ideal but prevents failure)
                            // The LID format is often a large number - we'll need user mapping
                            senderNumber = remoteJid.replace('@lid', '');
                            logger.warn(`⚠️ Could not resolve LID ${remoteJid}. Using LID as identifier.`);
                            logger.warn(`   pushName: ${pushName}`);
                            logger.warn(`   You may need to register this user's phone number.`);
                        }
                    } catch (e) {
                        logger.error(`Failed to resolve LID: ${e.message}`);
                        senderNumber = remoteJid.replace('@lid', '');
                    }
                }
            } else {
                // Standard phone format
                senderNumber = remoteJid.replace('@s.whatsapp.net', '');
            }

            const isGroupMsg = remoteJid.includes('@g.us');

            logger.info(`📬 Message from: ${senderNumber}${isLidFormat ? ' (LID)' : ''}`);

            // Ignore group messages (only handle 1-on-1)
            if (isGroupMsg) {
                logger.info('⏭️ Ignoring group message');
                return;
            }

            // ============================================
            // PHONE ROUTING: Identify which K24 user owns this customer
            // ============================================
            let resolvedUserId = null;
            let resolvedCustomerName = null;

            const normalizedPhone = senderNumber.startsWith('+') ? senderNumber : `+${senderNumber}`;

            // Check if this is a conflict resolution response (short code like "ABC123")
            const potentialCode = (msg.message?.conversation || msg.message?.extendedTextMessage?.text || '').trim();
            if (potentialCode.length <= 10 && pendingConflicts.has(normalizedPhone)) {
                const resolution = resolveConflictByCode(normalizedPhone, potentialCode);
                if (resolution.resolved) {
                    await sock.sendMessage(msg.key.remoteJid, {
                        text: `✅ Identified as *${resolution.customerName}*. Processing your message...`
                    });
                    resolvedUserId = resolution.userId;
                    resolvedCustomerName = resolution.customerName;
                    // Continue processing...
                } else {
                    await sock.sendMessage(msg.key.remoteJid, {
                        text: `❌ Code not recognized. Please try again or contact support.`
                    });
                    return;
                }
            } else {
                // Normal routing lookup
                const routeResult = await identifyUserByPhone(senderNumber);

                if (routeResult.status === 'found') {
                    resolvedUserId = routeResult.userId;
                    resolvedCustomerName = routeResult.customerName;
                    logger.info(`📍 Routed to User: ${resolvedUserId} (${resolvedCustomerName})`);

                } else if (routeResult.status === 'conflict') {
                    // Multiple users have this customer registered - ask for code
                    const codes = routeResult.matches
                        .filter(m => m.client_code)
                        .map(m => m.client_code)
                        .join(', ');

                    pendingConflicts.set(normalizedPhone, {
                        matches: routeResult.matches,
                        expiresAt: Date.now() + CONFLICT_TTL_MS
                    });

                    if (codes) {
                        await sock.sendMessage(msg.key.remoteJid, {
                            text: `⚠️ Multiple accounts found for this number.\n\nPlease reply with your *Client Code* (e.g., ${codes}) to continue.`
                        });
                    } else {
                        await sock.sendMessage(msg.key.remoteJid, {
                            text: `⚠️ Multiple accounts found for this number.\n\nPlease contact your K24 administrator to resolve this conflict.`
                        });
                    }
                    return;

                } else if (routeResult.status === 'unknown') {
                    // Phone not registered - continue with default processing (might be a new customer)
                    logger.info(`📍 Unknown phone ${senderNumber}. Processing as anonymous/new customer.`);
                }
                // If 'error', also continue with anonymous processing
            }

            let mediaData = null;
            let messageText = '';

            // Extract message content
            if (msg.message?.conversation) {
                messageText = msg.message.conversation;
            } else if (msg.message?.extendedTextMessage?.text) {
                messageText = msg.message.extendedTextMessage.text;
            } else if (msg.message?.imageMessage) {
                // ============ SMART BATCHING FOR IMAGES ============
                // Route images through the batcher for smart grouping
                logger.info('📸 Image detected. Routing to batcher...');

                // Check if this is a VERIFY command in the caption
                const caption = msg.message.imageMessage.caption || '';
                if (caption.trim().toUpperCase().startsWith("VERIFY")) {
                    // Handle verify immediately, don't batch
                    messageText = caption;
                } else {
                    // Add to batch - batcher will handle download and processing
                    const batchResult = await batcher.addMessage(msg);
                    logger.info(`📦 Batch result: ${JSON.stringify(batchResult)}`);
                    return; // Batcher will handle everything, exit here
                }
            } else if (msg.message?.documentMessage) {
                logger.info('📄 Document detected.');
                messageText = 'Document shared'; // Placeholder
            } else {
                logger.info('⏭️ Unsupported message type');
                return;
            }

            logger.info(`📝 Message Text: "${messageText}"`);

            // --- INTERCEPT VERIFICATION COMMAND ---
            if (messageText && messageText.trim().toUpperCase().startsWith("VERIFY")) {
                logger.info("🔐 Verification code detected. Intercepting...");

                const parts = messageText.trim().split(" ");
                const code = parts[1];

                if (!code) {
                    await sock.sendMessage(msg.key.remoteJid, { text: "⚠️ Please provide the 6-digit code. Example: VERIFY 123456" });
                    return;
                }

                try {
                    logger.info(`CONNECTING TO: ${BACKEND_URL}/api/whatsapp/verify-webhook`);

                    const response = await axios.post(`${BACKEND_URL}/api/whatsapp/verify-webhook`,
                        { sender_number: senderNumber, code: code },
                        { headers: { "X-Baileys-Secret": process.env.BAILEYS_SECRET || 'k24_baileys_secret' } }
                    );

                    const userName = response.data.user_name || "User";
                    await sock.sendMessage(msg.key.remoteJid, { text: `✅ Linked successfully to *${userName}*! \n\nYou can now ask me to record transactions, check reports, and more.` });
                    logger.info(`✅ Successfully verified user: ${userName}`);

                } catch (err) {
                    logger.error("❌ Verification failed:", err.message);
                    if (err.response) {
                        logger.error("Response:", err.response.data);
                    }
                    await sock.sendMessage(msg.key.remoteJid, { text: "❌ Invalid or expired code. Please generate a new one from the dashboard." });
                }

                return; // STOP execution here. Do not send to AI Agent.
            }
            // --------------------------------------

            // SEND TO BACKEND FOR PROCESSING (with resolved user context)
            await processMessageViaBackend(
                senderNumber,
                messageText,
                mediaData,
                sock,
                msg.key.remoteJid,
                resolvedUserId,
                resolvedCustomerName
            );

        } catch (error) {
            logger.error('❌ Error in message handler:', error);
        }
    });

    return sock;
}

async function processMessageViaBackend(senderNumber, messageText, mediaData, sock, remoteJid, resolvedUserId = null, resolvedCustomerName = null) {
    // ============================================
    // CLOUD QUEUE ARCHITECTURE
    // The Railway cloud backend only exposes /api/whatsapp/cloud/incoming.
    // It queues messages for the desktop app to poll and process.
    // There is no server-side AI agent on the cloud — processing is desktop-side.
    // ============================================
    try {
        const timestamp = Math.floor(Date.now() / 1000);
        const cloudPayload = {
            from_number: senderNumber,
            to_number: botNumber ? `+${botNumber}` : null,   // business/bot number for tenant resolution
            message_type: mediaData ? 'image' : 'text',
            text: messageText || null,
            timestamp: timestamp,
            raw_payload: resolvedUserId ? { resolved_user_id: resolvedUserId, resolved_customer_name: resolvedCustomerName } : null
        };

        if (!botNumber) {
            logger.warn('⚠️ Bot number not yet known — to_number will be null. Set BOT_NUMBER env var to fix.');
        }

        logger.info(`☁️ Queuing message to cloud: ${BACKEND_URL}/api/whatsapp/cloud/incoming`);

        const response = await axios.post(
            `${BACKEND_URL}/api/whatsapp/cloud/incoming`,
            cloudPayload,
            {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                },
                timeout: 15000 // 15 seconds — cloud queue should be fast
            }
        );

        if (response.status === 202) {
            logger.info(`☁️ Message queued successfully (202 Accepted). Desktop app will process it.`);
            // The cloud queue model: desktop polls and processes. No immediate reply from here.
            // If you want to send a WhatsApp acknowledgment, uncomment:
            // await sock.sendMessage(remoteJid, { text: '✅ Message received! Processing...' });
        } else {
            logger.warn(`☁️ Unexpected cloud response: ${response.status}`);
        }

    } catch (error) {
        logger.error('❌ Failed to queue message to cloud backend:');
        logger.error(`   URL: ${BACKEND_URL}/api/whatsapp/cloud/incoming`);
        logger.error(`   Error: ${error.message}`);
        if (error.response) {
            logger.error(`   HTTP Status: ${error.response.status}`);
            logger.error(`   Response: ${JSON.stringify(error.response.data)}`);
        } else if (error.code) {
            logger.error(`   Network error code: ${error.code}`);
        }
    }
}

// Start the listener
logger.info('🚀 Starting Baileys Listener with Smart Batching + Phone Routing...');
startBaileys().catch((err) => {
    logger.error('Fatal error:', err);
    process.exit(1);
});

process.on('SIGINT', async () => {
    logger.info('Shutting down gracefully...');
    logger.info('📦 Flushing pending batches...');
    await batcher.flushAllBatches();
    process.exit(0);
});
