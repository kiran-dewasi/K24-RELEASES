const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys')

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_test')

    console.log("Starting minimal connection test...");

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        browser: ["K24 Test", "Chrome", "1.0.0"]
    })

    sock.ev.on('creds.update', saveCreds)

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update

        if (qr) {
            console.log("QR Code received!");
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut
            console.log('connection closed due to ', lastDisconnect?.error, ', reconnecting ', shouldReconnect)
            // don't reconnect in test
            if (shouldReconnect) {
                console.log("Would reconnect here.");
                process.exit(1);
            }
        } else if (connection === 'open') {
            console.log('opened connection')
        }
    })
}

connectToWhatsApp()
