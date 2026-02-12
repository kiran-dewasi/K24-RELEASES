// baileys-listener/listener.js
// K24 WhatsApp Message Handler with Smart Batching + Phone Routing

const makeWASocket = require('@whiskeysockets/baileys').default;
const { useMultiFileAuthState, DisconnectReason, downloadMediaMessage } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

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
const AUTH_DIR = process.env.SESSION_DIR || path.join(__dirname, 'auth');


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
 * Identify which K24 user owns this phone number
 * Returns: { status, userId, customerName } or { status: 'conflict', matches }
 */
async function identifyUserByPhone(phone) {
    // Normalize phone format
    const normalizedPhone = phone.startsWith('+') ? phone : `+${phone}`;

    // Check cache first
    const cached = routingCache.get(normalizedPhone);
    if (cached && cached.expiresAt > Date.now()) {
        logger.info(`[CACHE HIT] Phone ${normalizedPhone} -> User ${cached.userId}`);
        return { status: 'found', userId: cached.userId, customerName: cached.customerName };
    }

    // Query backend API
    try {
        const response = await axios.post(
            `${BACKEND_URL}/api/whatsapp/identify-user`,
            null,
            { params: { phone: normalizedPhone } }
        );

        const result = response.data;

        // Cache successful lookups
        if (result.status === 'found') {
            routingCache.set(normalizedPhone, {
                userId: result.user_id,
                customerName: result.customer_name,
                expiresAt: Date.now() + CACHE_TTL_MS
            });
            logger.info(`[CACHE SET] Phone ${normalizedPhone} -> User ${result.user_id}`);
        }

        return result;

    } catch (error) {
        logger.error(`[ROUTING ERROR] Failed to identify phone ${normalizedPhone}:`, error.message);
        return { status: 'error', message: error.message };
    }
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

// Ensure auth directory exists
if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
}

async function startBaileys() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    const sock = makeWASocket({
        auth: state,
        logger: logger,
        printQRInTerminal: false,
        syncFullHistory: false, // Prevent history sync crash
        shouldSyncHistoryMessage: () => false,
        generateHighQualityLinkPreview: false,
        browser: ["K24 Agent", "Chrome", "1.0.0"],
        // fetchLatestBaileysVersion: false, // Let it fetch latest
    });

    // QR Code Handler (shows once on first run)
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            logger.info('📱 Scan this QR code with WhatsApp:');
            // Save QR as ASCII
            console.log('\n');
            const qrAscii = await QRCode.toString(qr, { type: 'terminal', small: true });
            console.log(qrAscii);
            console.log('\n');
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut && statusCode !== DisconnectReason.connectionReplaced;

            logger.error(
                `Connection closed. Status: ${statusCode}, Reconnecting: ${shouldReconnect}`,
                lastDisconnect?.error
            );

            if (statusCode === DisconnectReason.connectionReplaced) {
                logger.error("⚠️ Connection Replaced: Another session (or terminal) opened this WhatsApp account. Stopping to avoid conflict loop.");
                process.exit(0); // Exit cleanly so we don't spam
            }

            if (shouldReconnect) {
                startBaileys();
            }
        } else if (connection === 'open') {
            logger.info('✅ WhatsApp Connected Successfully');
            logger.info(`Bot Number: ${sock.user.id}`);

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

            // --- SEND TO CLOUD WEBHOOK FOR QUEUEING ---
            try {
                const timestamp = msg.messageTimestamp ? parseInt(msg.messageTimestamp) : Math.floor(Date.now() / 1000);
                const cloudPayload = {
                    from_number: senderNumber,
                    message_type: "text",
                    text: messageText || null,
                    timestamp: timestamp
                };

                await axios.post(
                    `${BACKEND_URL}/api/whatsapp/cloud/incoming`,
                    cloudPayload,
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                        }
                    }
                );
                logger.info(`☁️ Cloud webhook: queued (status 202)`);
            } catch (cloudErr) {
                logger.error(`☁️ Cloud webhook failed: ${cloudErr.response?.status || cloudErr.message}`);
                // Don't stop processing - continue with existing flow
            }
            // --------------------------------------

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
    try {
        // ============================================
        // SMART QUERY ROUTING
        // Text queries go to /api/query/whatsapp for intelligent responses
        // Image processing still goes to /api/baileys/process
        // ============================================

        // If it's a text query (no media), try the smart query endpoint first
        if (messageText && !mediaData) {
            logger.info(`🧠 Routing text query to Smart Query API: "${messageText}"`);

            try {
                const queryResponse = await axios.post(
                    `${BACKEND_URL}/api/query/whatsapp`,
                    {
                        query: messageText,
                        context: {
                            sender_phone: senderNumber,
                            resolved_user_id: resolvedUserId,
                            resolved_customer_name: resolvedCustomerName
                        }
                    },
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                        },
                        timeout: 60000 // 1 minute for query processing
                    }
                );

                const result = queryResponse.data;

                if (result.success) {
                    // Send text response
                    await sock.sendMessage(remoteJid, {
                        text: result.message || '✅ Query processed'
                    });

                    // If there's a file to send (PDF/Excel)
                    if (result.has_file && result.file) {
                        logger.info(`📎 Sending file: ${result.file.filename}`);

                        const filePath = result.file.path;
                        const fileName = result.file.filename;
                        const fileType = result.file.type;

                        // Determine mimetype
                        let mimetype;
                        if (fileType === 'pdf') {
                            mimetype = 'application/pdf';
                        } else if (fileType === 'excel' || fileName.endsWith('.xlsx')) {
                            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                        } else {
                            mimetype = 'application/octet-stream';
                        }

                        // Check if file exists
                        if (fs.existsSync(filePath)) {
                            await sock.sendMessage(remoteJid, {
                                document: fs.readFileSync(filePath),
                                fileName: fileName,
                                mimetype: mimetype
                            });
                            logger.info(`✅ File sent successfully: ${fileName}`);
                        } else {
                            logger.error(`❌ File not found: ${filePath}`);
                            await sock.sendMessage(remoteJid, {
                                text: `⚠️ File generated but couldn't be sent. Please check the dashboard.`
                            });
                        }
                    }

                    logger.info(`✅ Smart Query processed successfully`);
                    return; // Exit after successful query processing
                }

            } catch (queryError) {
                // If query endpoint fails, fall through to legacy processing
                logger.warn(`⚠️ Smart Query failed, falling back to legacy: ${queryError.message}`);
            }
        }

        // ============================================
        // LEGACY PROCESSING (for images and fallback)
        // ============================================
        logger.info(`🔄 Sending to backend: ${BACKEND_URL}/api/baileys/process`);
        if (resolvedUserId) {
            logger.info(`📍 Routing to resolved user: ${resolvedUserId} (${resolvedCustomerName})`);
        }

        const payload = {
            sender_phone: senderNumber,
            message_text: messageText,
            media: mediaData,
            resolved_user_id: resolvedUserId,
            resolved_customer_name: resolvedCustomerName
        };

        const response = await axios.post(
            `${BACKEND_URL}/api/baileys/process`,
            payload,
            {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                },
                timeout: 120000 // 2 minutes
            }
        );

        const { status, reply_message, error } = response.data;

        if (status === 'success') {
            // Send success reply
            let cleanMessage = reply_message || '✅ Message processed successfully';
            // Clean up presentation (remove minus signs from amounts)
            cleanMessage = cleanMessage.replace(/\(-\)/g, '');
            cleanMessage = cleanMessage.replace(/-(\d)/g, '$1');

            logger.info(`✅ Processing successful. Sending reply...`);
            await sock.sendMessage(remoteJid, {
                text: cleanMessage
            });
        } else {
            // Send error reply
            logger.error(`❌ Processing failed: ${error}`);
            await sock.sendMessage(remoteJid, {
                text: `❌ Error: ${error}`
            });
        }
    } catch (error) {
        logger.error('❌ Error sending to backend:', error.message);
        if (error.response) {
            logger.error('Backend Response Data:', error.response.data);
            logger.error('Backend Status:', error.response.status);
        }

        // Send error message to user
        try {
            await sock.sendMessage(remoteJid, {
                text: '❌ Backend connection failed. Please try again later.'
            });
        } catch (e) {
            logger.error('Failed to send error message:', e.message);
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
