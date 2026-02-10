// baileys-listener/batch-handler.js
// Smart Message Batching for WhatsApp Bill Processing
// Detects burst messages, groups them, processes in parallel, sends ONE summary

const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const pino = require('pino');

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: {
            colorize: true,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname'
        }
    }
});

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const TEMP_DIR = path.join(__dirname, 'temp');

// Ensure temp directory exists
async function ensureTempDir() {
    try {
        await fs.mkdir(TEMP_DIR, { recursive: true });
    } catch (e) {
        // Already exists
    }
}
ensureTempDir();

class MessageBatcher {
    constructor(batchWindow = 8000) { // 8 second window
        this.batches = new Map(); // phoneNumber -> batch of messages
        this.batchWindow = batchWindow; // Wait time before processing
        this.timers = new Map(); // phoneNumber -> timer
        this.sock = null; // Will be set when main listener starts
        this.downloadFn = null; // Will be set to downloadMediaMessage
    }

    /**
     * Initialize with socket and download function
     */
    init(sock, downloadMediaMessage) {
        this.sock = sock;
        this.downloadFn = downloadMediaMessage;
        logger.info('📦 MessageBatcher initialized');
    }

    /**
     * Add message to batch, group by sender
     */
    async addMessage(message) {
        const sender = message.key.remoteJid; // Phone number@s.whatsapp.net or LID@lid

        // Extract sender number - handle both @s.whatsapp.net and @lid formats
        let senderNumber = '';
        if (sender.endsWith('@lid')) {
            // LID format - check if we have participant info
            const participant = message.key.participant;
            if (participant && participant.includes('@s.whatsapp.net')) {
                senderNumber = participant.replace('@s.whatsapp.net', '');
            } else {
                senderNumber = sender.replace('@lid', '');
            }
        } else {
            senderNumber = sender.replace('@s.whatsapp.net', '');
        }

        const messageType = message.message?.imageMessage ? 'image' : 'text';

        // Only batch images (bill photos)
        if (messageType !== 'image') {
            // Process text immediately (commands, queries)
            return { action: 'immediate', message };
        }

        // Initialize batch for this sender if not exists
        if (!this.batches.has(sender)) {
            this.batches.set(sender, []);
        }

        // Add to batch
        const batch = this.batches.get(sender);
        batch.push(message);

        logger.info(`📦 Batched: ${senderNumber} - ${batch.length} image(s)`);

        // Reset timer (restart countdown on each new message)
        if (this.timers.has(sender)) {
            clearTimeout(this.timers.get(sender));
        }

        // Set timer to process batch after window expires
        const timer = setTimeout(() => {
            this.processBatch(sender);
        }, this.batchWindow);

        this.timers.set(sender, timer);

        // Quick acknowledgment on first image
        if (batch.length === 1) {
            await this.sendQuickAck(sender);
        }

        return { action: 'batched', count: batch.length };
    }

    /**
     * Send quick acknowledgment on first image
     */
    async sendQuickAck(sender) {
        if (!this.sock) return;

        try {
            await this.sock.sendMessage(sender, {
                text: "📸 Received! Keep sending bills, I'll process them together in ~8 seconds..."
            });
        } catch (e) {
            logger.error('Failed to send quick ack:', e.message);
        }
    }

    /**
     * Process entire batch for a sender
     */
    async processBatch(sender) {
        const batch = this.batches.get(sender);

        if (!batch || batch.length === 0) return;

        // Extract sender number - handle both @s.whatsapp.net and @lid formats
        let senderNumber = '';
        if (sender.endsWith('@lid')) {
            // LID format - try to get phone from first message's participant
            const firstMsg = batch[0];
            const participant = firstMsg?.key?.participant;
            if (participant && participant.includes('@s.whatsapp.net')) {
                senderNumber = participant.replace('@s.whatsapp.net', '');
            } else {
                senderNumber = sender.replace('@lid', '');
            }
        } else {
            senderNumber = sender.replace('@s.whatsapp.net', '');
        }

        logger.info(`\n${'='.repeat(60)}`);
        logger.info(`🚀 PROCESSING BATCH`);
        logger.info(`   Sender: ${senderNumber}`);
        logger.info(`   Images: ${batch.length}`);
        logger.info('='.repeat(60));

        // Clear batch and timer
        this.batches.delete(sender);
        this.timers.delete(sender);

        // Send processing notification
        try {
            await this.sock.sendMessage(sender, {
                text: `⏳ Processing ${batch.length} bill(s)... This may take ~${Math.ceil(batch.length * 3)} seconds.`
            });
        } catch (e) {
            logger.error('Failed to send processing notification:', e.message);
        }

        try {
            // Download all images in parallel
            const downloadPromises = batch.map(async (msg, index) => {
                try {
                    const buffer = await this.downloadFn(
                        msg,
                        'buffer',
                        {},
                        {
                            logger,
                            reuploadRequest: this.sock.updateMediaMessage
                        }
                    );

                    const filename = `batch_${Date.now()}_${index}.jpg`;
                    const filepath = path.join(TEMP_DIR, filename);
                    await fs.writeFile(filepath, buffer);

                    logger.info(`✅ Downloaded image ${index + 1}/${batch.length}`);
                    return {
                        success: true,
                        filepath,
                        mimetype: msg.message?.imageMessage?.mimetype || 'image/jpeg'
                    };
                } catch (e) {
                    logger.error(`❌ Failed to download image ${index + 1}:`, e.message);
                    return { success: false, error: e.message };
                }
            });

            const downloadResults = await Promise.all(downloadPromises);

            // Filter successful downloads
            const successfulDownloads = downloadResults.filter(r => r.success);
            const failedDownloads = downloadResults.filter(r => !r.success);

            logger.info(`✅ Downloaded ${successfulDownloads.length}/${batch.length} images`);

            if (successfulDownloads.length === 0) {
                await this.sock.sendMessage(sender, {
                    text: `❌ Failed to download any images. Please try again.`
                });
                return;
            }

            // Forward to backend for parallel processing
            const result = await this.forwardToBackend(senderNumber, successfulDownloads);

            // Send summary response
            await this.sendSummaryResponse(sender, result, failedDownloads.length);

            // Cleanup temp files
            for (const download of successfulDownloads) {
                try {
                    await fs.unlink(download.filepath);
                } catch (e) {
                    // Ignore cleanup errors
                }
            }

        } catch (error) {
            logger.error('❌ Batch processing failed:', error);
            try {
                await this.sock.sendMessage(sender, {
                    text: `❌ Error processing batch: ${error.message}`
                });
            } catch (e) {
                logger.error('Failed to send error message:', e.message);
            }
        }
    }

    /**
     * Forward batch to K24 backend
     */
    async forwardToBackend(senderPhone, downloads) {
        try {
            logger.info(`📤 Sending ${downloads.length} images to backend...`);

            // Read files and convert to base64
            const imagesData = await Promise.all(
                downloads.map(async (d) => {
                    const buffer = await fs.readFile(d.filepath);
                    return {
                        buffer: buffer.toString('base64'),
                        mimetype: d.mimetype,
                        filepath: d.filepath
                    };
                })
            );

            // Call backend bulk processing endpoint
            const response = await axios.post(
                `${BACKEND_URL}/api/baileys/process-batch`,
                {
                    sender_phone: senderPhone,
                    images: imagesData,
                    batch_id: Date.now().toString()
                },
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Baileys-Secret': process.env.BAILEYS_SECRET || 'k24_baileys_secret'
                    },
                    timeout: 180000 // 3 minute timeout for batch
                }
            );

            logger.info(`✅ Backend response received`);
            return response.data;

        } catch (error) {
            logger.error('❌ Backend call failed:', error.message);
            if (error.response) {
                logger.error('Response:', error.response.data);
            }
            throw error;
        }
    }

    /**
     * Send formatted summary response with action-specific messaging
     */
    async sendSummaryResponse(sender, result, downloadFailures = 0) {
        if (!this.sock) return;

        try {
            if (result.status === 'success') {
                const { vouchers, stats, questions } = result;

                // Count by action type
                const autoPosted = vouchers.filter(v => v.action === 'auto_posted').length;
                const autoCreated = vouchers.filter(v => v.action === 'auto_created').length;
                const needsReview = vouchers.filter(v => v.action === 'needs_review').length;
                const needsClarification = stats.needs_clarification || 0;

                // Build summary message based on actions
                let summary = '';

                // ============ AUTO-POSTED (High Confidence) ============
                if (autoPosted > 0) {
                    summary += `✅ *Auto-Posted to Tally!*\n\n`;
                    summary += `📊 *${autoPosted} bill(s) auto-processed:*\n`;

                    vouchers.filter(v => v.action === 'auto_posted').slice(0, 5).forEach((v, i) => {
                        const partyName = v.party_name || v.party || 'Unknown';
                        const amount = v.total_amount || v.amount || 0;
                        const items = v.items_count || 0;
                        const confidence = Math.round((v.confidence || 0) * 100);
                        summary += `${i + 1}. ${partyName} - ₹${this.formatCurrency(amount)} (${items} items, ${confidence}%)\n`;
                    });

                    if (autoPosted > 5) {
                        summary += `... and ${autoPosted - 5} more\n`;
                    }
                    summary += `\n_No action needed - entries are live in Tally!_\n\n`;
                }

                // ============ AUTO-CREATED (Ready for review/post) ============
                if (autoCreated > 0) {
                    // Check if any have tally_error (meaning Tally was offline)
                    const tallyErrors = vouchers.filter(v => v.action === 'auto_created' && v.tally_error);

                    if (tallyErrors.length > 0) {
                        summary += `⚠️ *${autoCreated} Voucher(s) Created (Tally Offline)*\n\n`;
                    } else {
                        summary += `📋 *${autoCreated} Voucher(s) Ready!*\n\n`;
                    }

                    vouchers.filter(v => v.action === 'auto_created').slice(0, 5).forEach((v, i) => {
                        const partyName = v.party_name || v.party || 'Unknown';
                        const amount = v.total_amount || v.amount || 0;
                        summary += `${i + 1}. ${partyName} - ₹${this.formatCurrency(amount)}`;
                        if (v.tally_error) {
                            summary += ` ⚠️`;
                        }
                        summary += `\n`;
                    });

                    if (tallyErrors.length > 0) {
                        summary += `\n_⚠️ Tally is offline. Vouchers saved locally._\n`;
                        summary += `_Please start Tally and reply POST to sync._\n\n`;
                    } else {
                        summary += `\nReply:\n1️⃣ *Post all* to Tally\n2️⃣ *Review* on dashboard\n3️⃣ *Cancel*\n\n`;
                    }
                }

                // ============ NEEDS REVIEW (Medium Confidence) ============
                if (needsReview > 0) {
                    summary += `⚠️ *${needsReview} bill(s) need review:*\n`;

                    vouchers.filter(v => v.action === 'needs_review').slice(0, 3).forEach((v, i) => {
                        const partyName = v.party_name || v.party || 'Unknown';
                        const confidence = Math.round((v.confidence || 0) * 100);
                        summary += `• ${partyName} (${confidence}% confidence)\n`;
                    });

                    summary += `\n_Please review these on the dashboard before posting._\n\n`;
                }

                // ============ NEEDS CLARIFICATION (Low Confidence) ============
                if (needsClarification > 0 && questions && questions.length > 0) {
                    summary += `❓ *${needsClarification} bill(s) need clarification:*\n\n`;

                    questions.slice(0, 3).forEach((q, i) => {
                        summary += `${i + 1}. ${q.question}\n`;
                    });

                    summary += `\n_Reply with answers to process these bills._\n\n`;
                }

                // ============ STATS FOOTER ============
                if (stats.failed > 0 || downloadFailures > 0) {
                    summary += `\n⚠️ *Issues:*\n`;
                    if (stats.failed > 0) {
                        summary += `• Failed to process: ${stats.failed} bill(s)\n`;
                    }
                    if (downloadFailures > 0) {
                        summary += `• Download errors: ${downloadFailures}\n`;
                    }
                }

                // Add totals
                if (stats.total_amount > 0) {
                    summary += `\n💰 *Total Value:* ₹${this.formatCurrency(stats.total_amount)}`;
                    summary += `\n📦 *Total Items:* ${stats.total_items || 0}`;
                }

                await this.sock.sendMessage(sender, { text: summary });

            } else {
                // Error response
                const errorMsg = result.error || 'Unknown error occurred';
                await this.sock.sendMessage(sender, {
                    text: `❌ Batch processing failed:\n${errorMsg}\n\nPlease try again or contact support.`
                });
            }
        } catch (e) {
            logger.error('Failed to send summary response:', e.message);
        }
    }

    /**
     * Format currency with Indian locale
     */
    formatCurrency(amount) {
        return Number(amount).toLocaleString('en-IN', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    }

    /**
     * Check if a sender has pending batched messages
     */
    hasPendingBatch(sender) {
        return this.batches.has(sender) && this.batches.get(sender).length > 0;
    }

    /**
     * Force process any pending batches (for shutdown)
     */
    async flushAllBatches() {
        logger.info('🔄 Flushing all pending batches...');
        const senders = Array.from(this.batches.keys());

        for (const sender of senders) {
            if (this.timers.has(sender)) {
                clearTimeout(this.timers.get(sender));
            }
            await this.processBatch(sender);
        }
    }
}

// Create singleton instance
const batcher = new MessageBatcher(8000); // 8 second window

module.exports = { MessageBatcher, batcher };
