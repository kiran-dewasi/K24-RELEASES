// baileys-listener/listener-diagnostic.js

const makeWASocket = require('baileys').default;
const { useMultiFileAuthState, DisconnectReason, Browsers } = require('baileys');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

const AUTH_DIR = path.join(__dirname, 'auth');

async function diagnose() {
    logger.info('🔍 STARTING BAILEYS DIAGNOSTIC');
    logger.info('====================================');

    // ============ STEP 1: Check Auth Directory ============
    logger.info('\n📁 STEP 1: Checking auth directory...');

    if (fs.existsSync(AUTH_DIR)) {
        const files = fs.readdirSync(AUTH_DIR);
        if (files.length === 0) {
            logger.info('⚠️ Auth directory EXISTS but is EMPTY (first run)');
            logger.info('   This is OK - QR will be generated');
        } else {
            logger.info(`✅ Auth directory has ${files.length} files`);
            logger.info('   Files:', files);
        }
    } else {
        logger.info('⚠️ Auth directory does NOT exist (creating...)');
        fs.mkdirSync(AUTH_DIR, { recursive: true });
    }

    // ============ STEP 2: Load Baileys ============
    logger.info('\n📦 STEP 2: Loading Baileys library...');

    try {
        const version = require('baileys/package.json').version;
        logger.info(`✅ Baileys version: ${version}`);
    } catch (e) {
        logger.error('❌ FAILED to load Baileys:', e.message);
        logger.error('   Fix: npm install baileys@latest');
        process.exit(1);
    }

    // ============ STEP 3: Initialize Auth State ============
    logger.info('\n🔑 STEP 3: Initializing auth state...');

    let state, saveCreds;
    try {
        const authResult = await useMultiFileAuthState(AUTH_DIR);
        state = authResult.state;
        saveCreds = authResult.saveCreds;
        logger.info('✅ Auth state initialized');
    } catch (e) {
        logger.error('❌ FAILED to init auth:', e.message);
        process.exit(1);
    }

    // ============ STEP 4: Create Socket Connection ============
    logger.info('\n🔌 STEP 4: Creating WhatsApp socket...');

    let sock;
    try {
        sock = makeWASocket({
            auth: state,
            logger: logger,
            printQRInTerminal: true,
            browser: Browsers.macOS('Desktop'), // Using macOS Desktop browser string
            syncFullHistory: false,
            shouldSyncHistoryMessage: () => false,
            maxRetries: 3, // Reduced from default (speeds up failure detection)
            retryRequestDelayMs: 100,
            generateHighQualityLinkPreview: false
        });
        logger.info('✅ Socket created');
    } catch (e) {
        logger.error('❌ FAILED to create socket:', e.message);
        process.exit(1);
    }

    // ============ STEP 5: Monitor Connection Events ============
    logger.info('\n📡 STEP 5: Listening for connection events...');
    logger.info('   (Watching for 30 seconds, then will report results)');

    let connectionStatus = {
        qrReceived: false,
        connected: false,
        authenticated: false,
        failureReason: null,
        lastError: null
    };

    const timeoutHandle = setTimeout(() => {
        logger.info('\n⏱️ DIAGNOSTIC TIMEOUT (30 seconds)');
        generateReport(connectionStatus);
        process.exit(0);
    }, 30000);

    // QR Code received
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            logger.info('✅ QR CODE RECEIVED (good sign - can reach WhatsApp servers)');
            connectionStatus.qrReceived = true;
            // Don't clear timeout - wait for actual connection
        }

        if (connection === 'open') {
            logger.info('✅ CONNECTED and AUTHENTICATED!');
            connectionStatus.connected = true;
            connectionStatus.authenticated = true;
            clearTimeout(timeoutHandle);
            generateReport(connectionStatus);
            process.exit(0);
        }

        if (connection === 'close') {
            const reason = lastDisconnect?.error?.output?.statusCode;
            const message = lastDisconnect?.error?.message || 'Unknown';

            logger.error(`❌ CONNECTION CLOSED`);
            logger.error(`   Status Code: ${reason}`);
            logger.error(`   Error: ${message}`);

            connectionStatus.failureReason = message;
            connectionStatus.lastError = lastDisconnect?.error;

            if (reason === DisconnectReason.loggedOut) {
                logger.error('   Reason: USER LOGGED OUT (intentional)');
            } else if (reason === DisconnectReason.connectionClosed) {
                logger.error('   Reason: WHATSAPP REJECTED CONNECTION');
            } else if (reason === DisconnectReason.connectionLost) {
                logger.error('   Reason: NETWORK CONNECTION LOST');
            } else if (reason === DisconnectReason.connectionReplaced) {
                logger.error('   Reason: CONNECTION REPLACED (logged in elsewhere)');
            } else if (reason === DisconnectReason.timedOut) {
                logger.error('   Reason: CONNECTION TIMEOUT');
            } else if (reason === 405) {
                logger.error('   Reason: METHOD NOT ALLOWED (Protocol Mismatch)');
            }

            clearTimeout(timeoutHandle);
            generateReport(connectionStatus);
            process.exit(0);
        }
    });

    // Credentials update
    sock.ev.on('creds.update', () => {
        logger.info('✅ Credentials updated (auth successful)');
        connectionStatus.authenticated = true;
    });

    logger.info('   Waiting for connection...\n');
}

function generateReport(status) {
    logger.info('\n\n📊 DIAGNOSTIC REPORT');
    logger.info('====================================');
    logger.info(`QR Code Received: ${status.qrReceived ? '✅' : '❌'}`);
    logger.info(`Connected: ${status.connected ? '✅' : '❌'}`);
    logger.info(`Authenticated: ${status.authenticated ? '✅' : '❌'}`);
    logger.info(`Failure Reason: ${status.failureReason || 'None'}`);

    logger.info('\n📋 DIAGNOSIS:');

    if (status.connected && status.authenticated) {
        logger.info('✅ BAILEYS IS WORKING PERFECTLY');
        logger.info('   Next: Use the normal listener.js');
    } else if (status.qrReceived && !status.connected) {
        logger.info('⚠️ QR Code was shown but authentication failed');
        logger.info('   Possible causes:');
        logger.info('   1. QR code not scanned correctly');
        logger.info('   2. Your WhatsApp account is already logged in elsewhere');
        logger.info('   3. WhatsApp blocked this device');
        logger.info('   Fix: Try logging out from WhatsApp Web on all devices');
    } else if (!status.qrReceived) {
        logger.info('❌ COULD NOT REACH WHATSAPP SERVERS');
        logger.info('   Possible causes:');
        logger.info('   1. ISP is blocking WhatsApp Web connections');
        logger.info('   2. Network firewall is blocking the connection');
        logger.info('   3. Baileys library is outdated or Protocol Mismatch');
        logger.info('   Fix: Try with a VPN or use official WhatsApp Business API');
    }

    logger.info('\n📝 NEXT STEPS:');
    logger.info('1. If ✅ All green: Baileys works. Use listener.js');
    logger.info('2. If ⚠️ QR but no auth: Logout WhatsApp Web, try again');
    logger.info('3. If ❌ No QR: Your ISP blocks WhatsApp Web (use VPN)');
}

diagnose().catch((err) => {
    logger.error('Fatal diagnostic error:', err);
    process.exit(1);
});

process.on('SIGINT', () => {
    logger.info('\nDiagnostic stopped by user');
    process.exit(0);
});
