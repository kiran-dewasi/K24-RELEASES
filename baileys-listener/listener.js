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

// Module-level socket reference — set once Baileys connects.
// Used by HTTP endpoints that need to query WhatsApp.
let activeSock = null;

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
        res.end(JSON.stringify({ status: 'running', qrAvailable: !!latestQRDataUrl, connected: !!activeSock }));

    } else if (req.url && req.url.startsWith('/resolve-contact')) {
        // GET /resolve-contact?phone=917339906200
        // Resolves a phone number to its WhatsApp JID (which may be a LID).
        // Use this when registering a customer to also capture their LID.
        const urlObj = new URL(req.url, `http://localhost`);
        const phone = urlObj.searchParams.get('phone');
        if (!phone) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing phone parameter' }));
            return;
        }
        if (!activeSock) {
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'WhatsApp not connected yet' }));
            return;
        }
        try {
            const normalizedPhone = phone.replace(/[^0-9]/g, '');
            const [result] = await activeSock.onWhatsApp(normalizedPhone);
            if (!result) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ phone: normalizedPhone, exists: false, jid: null, lid: null }));
                return;
            }
            // result.jid may be "917339906200@s.whatsapp.net" or "185628738236618@lid"
            const isLid = result.jid && result.jid.endsWith('@lid');
            const lidNumber = isLid ? result.jid.replace('@lid', '') : null;
            const response = {
                phone: normalizedPhone,
                exists: result.exists,
                jid: result.jid,
                lid: lidNumber,        // null if not a LID account
                isLidAccount: isLid    // true = store BOTH phone AND lid in customer_mappings
            };
            // Also cache it immediately
            if (isLid) {
                lidToPhoneCache.set(result.jid, normalizedPhone);
                lidToPhoneCache.set(lidNumber, normalizedPhone);
                logger.info(`📊 Cached LID via resolve-contact: ${lidNumber} → ${normalizedPhone}`);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(response));
        } catch (e) {
            logger.error('resolve-contact error: ' + e.message);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }

    } else if (req.url === '/lid-cache') {
        // GET /lid-cache — shows the current LID-to-phone cache contents (for debugging)
        const entries = {};
        lidToPhoneCache.forEach((phone, lid) => { entries[lid] = phone; });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ size: lidToPhoneCache.size, entries }));

    } else if (req.method === 'POST' && req.url === '/send-reply') {
        // POST /send-reply
        // Called by the desktop app after processing a queue message.
        // Sends the reply text back to the customer via WhatsApp.
        //
        // Body: { "to": "185628738236618", "text": "Your balance is ₹5000" }
        // Headers: X-Baileys-Secret: <shared secret>
        //
        // Security: same BAILEYS_SECRET used between cloud backend and listener.

        // Verify secret
        const secret = req.headers['x-baileys-secret'];
        if (secret !== (process.env.BAILEYS_SECRET || 'k24_baileys_secret')) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid secret' }));
            return;
        }

        if (!activeSock) {
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
            return;
        }

        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const { to, text } = JSON.parse(body);

                if (!to || !text) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Missing required fields: to, text' }));
                    return;
                }

                // Build the JID — handle both raw numbers and @lid / @s.whatsapp.net formats
                let jid = to;
                if (!jid.includes('@')) {
                    // Check if this is a known LID (in cache, its value IS the phone)
                    // OR if the number itself is in the LID cache as a key
                    // We just append the right suffix
                    // Numbers > 15 digits are likely LIDs (WhatsApp internal IDs)
                    const digits = jid.replace(/[^0-9]/g, '');
                    if (digits.length > 15) {
                        jid = `${digits}@lid`;
                    } else {
                        jid = `${digits}@s.whatsapp.net`;
                    }
                }

                logger.info(`📤 Sending reply to ${jid}: "${text.substring(0, 50)}..."`);
                await activeSock.sendMessage(jid, { text });
                logger.info(`✅ Reply sent to ${jid}`);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, to: jid }));
            } catch (e) {
                logger.error('send-reply error: ' + e.message);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: e.message }));
            }
        });

    } else if (req.method === 'POST' && req.url === '/send-file') {
        // POST /send-file
        // Called by the desktop poller when the AI generates an Excel/PDF export.
        // Decodes the base64 file data and sends it as a WhatsApp document.
        //
        // Body: { "to": "917...", "filename": "Sales.xlsx", "data_base64": "...", "mimetype": "application/...", "caption": "..." }
        // Headers: X-Baileys-Secret: <shared secret>

        const secret = req.headers['x-baileys-secret'];
        if (secret !== (process.env.BAILEYS_SECRET || 'k24_baileys_secret')) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid secret' }));
            return;
        }

        if (!activeSock) {
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
            return;
        }

        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const { to, filename, data_base64, mimetype, caption } = JSON.parse(body);

                if (!to || !filename || !data_base64) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Missing required fields: to, filename, data_base64' }));
                    return;
                }

                // Build JID (same logic as /send-reply)
                let jid = to;
                if (!jid.includes('@')) {
                    const digits = jid.replace(/[^0-9]/g, '');
                    jid = digits.length > 15 ? `${digits}@lid` : `${digits}@s.whatsapp.net`;
                }

                // Decode base64 → Buffer
                const fileBuffer = Buffer.from(data_base64, 'base64');
                const fileMime = mimetype || 'application/octet-stream';
                const fileSizeKB = Math.round(fileBuffer.length / 1024);

                logger.info(`📤 Sending file '${filename}' (${fileSizeKB}KB, ${fileMime}) to ${jid}`);

                await activeSock.sendMessage(jid, {
                    document: fileBuffer,
                    mimetype: fileMime,
                    fileName: filename,
                    caption: caption || filename,
                });

                logger.info(`✅ File '${filename}' sent to ${jid}`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, to: jid, filename, size_kb: fileSizeKB }));

            } catch (e) {
                logger.error('send-file error: ' + e.message);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: e.message }));
            }
        });

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
const lidToPhoneCache = new Map(); // "185628738236618@lid" -> "917339906200"

// ── Pre-populate from LID_PHONE_MAP env var (Railway override)
// Format: LID_PHONE_MAP="185628738236618=917339906200,123456=910000000"
if (process.env.LID_PHONE_MAP) {
    process.env.LID_PHONE_MAP.split(',').forEach(pair => {
        const [lid, phone] = pair.trim().split('=');
        if (lid && phone) {
            lidToPhoneCache.set(`${lid}@lid`, phone.trim());
            lidToPhoneCache.set(lid.trim(), phone.trim()); // also store bare LID
            logger.info(`📋 LID override loaded: ${lid} → ${phone}`);
        }
    });
}

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
        syncFullHistory: false,       // don't sync message history (we don't need old messages)
        generateHighQualityLinkPreview: false,
        // ── FIX 3: Use a realistic browser string.
        // Non-standard version strings (like "1.0.0") cause 405 ws rejections.
        browser: ["K24 Agent", "Chrome", "120.0.0"],
        connectTimeoutMs: 60000,
        keepAliveIntervalMs: 10000,
        markOnlineOnConnect: false,   // don't show as online when bot connects
    });
    // Make socket accessible to HTTP endpoints
    activeSock = sock;

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
            logger.info(`📱 Bot Number: +${sock.user?.id?.split('@')[0]?.split(':')[0] || 'unknown'}`);

            // Initialize the message batcher with socket and download function
            batcher.init(sock, downloadMediaMessage);
            logger.info('📦 Message batcher initialized for smart batching');

            // Trigger contact sync to populate LID-to-phone cache.
            // WhatsApp sends contacts.set shortly after connect — this just nudges it.
            try {
                const contacts = await sock.getOrderedContacts?.() ?? [];
                if (contacts.length > 0) {
                    buildLidCache(contacts);
                    logger.info(`📒 Pre-loaded ${contacts.length} contacts into LID cache`);
                }
            } catch (e) {
                // Not all Baileys versions expose getOrderedContacts — that's fine,
                // contacts.set will fire shortly and handle it
                logger.info('ℹ️ Contact pre-load skipped — waiting for contacts.set event');
            }
        }
    });

    // Credentials Handler
    sock.ev.on('creds.update', saveCreds);

    // ============================================
    // CONTACT SYNC — LID-TO-PHONE CACHE BUILDER
    // WhatsApp fires contacts.set on connect with the full contact list.
    // Each contact may have:
    //   id: "185628738236618@lid"  (the LID)
    //   lid: "185628738236618@lid" (same)
    //   notify: "Kiran"            (display name, not useful)
    // The phone number can come from:
    //   - the @s.whatsapp.net JID version of the same contact
    //   - a verifiedName or other field
    // Baileys also fires contacts.upsert for individual contact updates.
    // ============================================
    function buildLidCache(contacts) {
        let mapped = 0;
        for (const contact of contacts) {
            const id = contact.id || '';
            // If this contact has a real phone JID AND a lid field, map lid -> phone
            if (contact.lid && id.endsWith('@s.whatsapp.net')) {
                const phone = id.replace('@s.whatsapp.net', '');
                const lidKey = contact.lid.endsWith('@lid') ? contact.lid : `${contact.lid}@lid`;
                if (!lidToPhoneCache.has(lidKey)) {
                    lidToPhoneCache.set(lidKey, phone);
                    lidToPhoneCache.set(contact.lid.replace('@lid', ''), phone); // bare LID too
                    mapped++;
                }
            }
            // Also: if the contact ID itself is a LID, but has a phone field or verifiedName
            // some Baileys versions put the phone in contact.phone
            if (id.endsWith('@lid') && contact.phone) {
                const phone = contact.phone.replace(/[^0-9]/g, '');
                if (phone && !lidToPhoneCache.has(id)) {
                    lidToPhoneCache.set(id, phone);
                    lidToPhoneCache.set(id.replace('@lid', ''), phone);
                    mapped++;
                }
            }
        }
        if (mapped > 0) {
            logger.info(`📒 LID cache updated: ${mapped} new LID→phone mappings (total: ${lidToPhoneCache.size / 2})`);
        }
    }

    // contacts.set fires once on connect with the FULL contact list
    sock.ev.on('contacts.set', ({ contacts }) => {
        logger.info(`📲 contacts.set fired with ${contacts.length} contacts — building LID cache...`);

        // DEBUG: Log the raw fields of the first 5 contacts to see what WhatsApp actually sends
        // This tells us if the 'lid' field exists and what format it uses
        const sample = contacts.slice(0, 5);
        sample.forEach((c, i) => {
            logger.info(`🔬 Contact[${i}] raw fields: ${JSON.stringify(c)}`);
        });
        // Also log the first LID contact we find (if any)
        const lidContact = contacts.find(c => c.id && c.id.endsWith('@lid'));
        if (lidContact) {
            logger.info(`🔬 Sample LID contact: ${JSON.stringify(lidContact)}`);
        } else {
            logger.info(`🔬 No @lid contacts found in contacts.set payload`);
        }
        // Log how many contacts have a 'lid' field
        const withLid = contacts.filter(c => c.lid);
        logger.info(`🔬 Contacts with 'lid' field: ${withLid.length} / ${contacts.length}`);

        buildLidCache(contacts);
    });

    // contacts.upsert fires for incremental updates (new contacts, contact edits)
    sock.ev.on('contacts.upsert', (contacts) => {
        buildLidCache(contacts);
    });

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

                // Try 1: participant field (for group messages, not applicable here but keep)
                const participant = msg.key.participant;
                if (participant && participant.includes('@s.whatsapp.net')) {
                    senderNumber = participant.replace('@s.whatsapp.net', '');
                    logger.info(`✅ Resolved LID via participant: ${senderNumber}`);
                } else {
                    // Try 2: lidToPhoneCache (populated from contacts.set on connect)
                    const cachedPhone = lidToPhoneCache.get(remoteJid) || lidToPhoneCache.get(remoteJid.replace('@lid', ''));
                    if (cachedPhone) {
                        senderNumber = cachedPhone;
                        logger.info(`✅ Resolved LID from cache: ${remoteJid} → ${senderNumber}`);
                    } else {
                        // Try 3: sock.contacts (Baileys in-memory store)
                        const contactFromStore = sock.contacts?.[remoteJid];
                        if (contactFromStore?.phone) {
                            senderNumber = contactFromStore.phone.replace(/[^0-9]/g, '');
                            lidToPhoneCache.set(remoteJid, senderNumber); // cache it
                            logger.info(`✅ Resolved LID from sock.contacts: ${senderNumber}`);
                        } else {
                            // Last resort: use LID as identifier — will be 'unrouted' in queue
                            // but NOT dropped. Admin can then add the LID to customer mappings.
                            senderNumber = remoteJid.replace('@lid', '');
                            logger.warn(`⚠️ Could not resolve LID ${remoteJid} to phone.`);
                            logger.warn(`   Fix: Set LID_PHONE_MAP env var on Railway: LID_PHONE_MAP="${senderNumber}=<phone_number>"`);
                            logger.warn(`   Or wait for contacts.set to fire on next reconnect.`);
                        }
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
            message_type: mediaData ? 'image' : 'text',
            text: messageText || null,
            raw_payload: resolvedUserId ? { resolved_user_id: resolvedUserId, resolved_customer_name: resolvedCustomerName } : null
        };

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
