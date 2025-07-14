const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class WhatsAppModerationBot {
    constructor() {
        this.client = null;
        this.targetGroupId = null;
        this.targetGroupName = 'אורות ברזל התנדבויות ועזרה 🇮🇱❤️';
        this.adminIds = new Set();
        this.allMembers = new Set(); 
        this.pendingReviews = new Map(); 
        
        this.setupClient();
    }
    
    setupClient() {
        console.log('🤖 Uploading WhatsApp Bot...');
        
        this.client = new Client({
            authStrategy: new LocalAuth({
                clientId: 'orot-barzel-moderation-bot'
            }),
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu'
                ]
            }
        });
        
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        // QR Code for initial connection
        this.client.on('qr', (qr) => {
            console.log('Scan QR with WhatsApp:');
            qrcode.generate(qr, { small: true });
            console.log('Waitting for scanning ...');
        });
        
        // Client ready
        this.client.on('ready', async () => {
            console.log('WhatsApp Bot Ready for action!!');
            await this.initializeGroup();
            await this.sendStartupMessage();
        });
        
        // New message received
        this.client.on('message', async (message) => {
            await this.handleMessage(message);
        });
        
        // Message reaction (for admin feedback)
        this.client.on('message_reaction', async (reaction) => {
            await this.handleReaction(reaction);
        });
        
        // Member joins group
        this.client.on('group_join', async (notification) => {
            await this.handleGroupJoin(notification);
        });
        
        // Member leaves group  
        this.client.on('group_leave', async (notification) => {
            await this.handleGroupLeave(notification);
        });
        
        // Disconnection
        this.client.on('disconnected', (reason) => {
            console.log('WhatsApp Disconnected:', reason);
            console.log('Trying to reconnect...');
        });
        
        // Authentication failure
        this.client.on('auth_failure', (msg) => {
            console.error('Authentication failure:', msg);
        });
    }
    
    async initializeGroup() {
        try {
            console.log(`Searching group: "${this.targetGroupName}"`);
            
            const chats = await this.client.getChats();
            const targetGroup = chats.find(chat => 
                chat.isGroup && chat.name.includes(this.targetGroupName)
            );
            
            if (targetGroup) {
                this.targetGroupId = targetGroup.id._serialized;
                console.log(`Target group found:: ${targetGroup.name}`);
                console.log(`${targetGroup.participants.length} participants in group`);
                
                // FIX: Collect ALL participants, not just admins
                const participants = targetGroup.participants;
                for (const participant of participants) {
                    // Add to all members set
                    this.allMembers.add(participant.id._serialized);
                    
                    // Separately track admins
                    if (participant.isAdmin || participant.isSuperAdmin) {
                        this.adminIds.add(participant.id._serialized);
                        console.log(`Admin identified: ${participant.id.user}`);
                    } else {
                        console.log(`Member identified: ${participant.id.user}`);
                    }
                }
                
                console.log(`identified ${this.allMembers.size} Members including ${this.adminIds.size} Admins`);
                
                // Debug: Print member counts
                console.log(`Total Members: ${this.allMembers.size}`);
                console.log(`Admins: ${this.adminIds.size}`);
                console.log(`Members: ${this.allMembers.size - this.adminIds.size}`);
                
            } else {
                console.log(`No group found with the name"${this.targetGroupName}"`);
                console.log('Availability groups:');
                chats.filter(chat => chat.isGroup).forEach(chat => {
                    console.log(`  - ${chat.name}`);
                });
            }
        } catch (error) {
            console.error('Error initializing group::', error);
        }
    }
    
    async sendStartupMessage() {
        if (this.adminIds.size > 0) {
            const startupMsg = `🤖 **סוכן חמ"ל פיקוח פעיל!**

מחובר לקבוצת: ${this.targetGroupName}
מפקח על ${this.allMembers.size} חברים (כולל ${this.adminIds.size} מנהלים)


**איך זה עובד:**
• הסוכן בודק את כל ההודעות
• הודעות בעייתיות יסומנו/יימחקו
• יתקבלו התראות פרטיות כאשר ימצא חריגה
• ניתן להגיב להודעות עם פידבק - ✅❌⚠️🔄

הסוכן פעיל ומפקח על כל ההודעות!`;

            await this.notifyAdmins(startupMsg);
        }
    }
    
    async handleMessage(message) {
        // Check if message is from the target group
        if (!this.targetGroupId || message.from !== this.targetGroupId) {
            return; 
        }
        
        // Skip bot's own messages
        if (message.fromMe) {
            return;
        }
        
        // Skip system messages
        if (message.type === 'notification_template' || message.isStatus) {
            return;
        }
        
        // Only skip VERY short messages (1-2 characters), allow short but meaningful messages
        if (message.body && message.body.length < 2) {
            return;
        }
        
        // Log message details for debugging
        console.log(`\nAnalyzing new message from Orot Barzel group...`);
        console.log(`DEBUG: Message from group: ${message.from}`);
        console.log(`DEBUG: Target group: ${this.targetGroupId}`);
        console.log(`DEBUG: Sender: ${message.author || message.from}`);
        console.log(`DEBUG: Is admin: ${this.adminIds.has(message.author || message.from)}`);
        console.log(`DEBUG: Message body: "${message.body}"`);
        console.log(`DEBUG: All members size: ${this.allMembers.size}`);
        console.log(`DEBUG: Admin IDs: ${Array.from(this.adminIds).join(', ')}`);
        
        // Get the actual sender ID
        const senderId = message.author || message.from;
        
        // Check if sender is a member (should include ALL members, not just admins)
        if (!this.allMembers.has(senderId) && !senderId.endsWith('@g.us')) {
            console.log(`Message from unknown user ${senderId}`);
            // Still process the message but flag it
        }
        
        console.log(`New message from ${senderId}: "${message.body?.substring(0, 50) || '[מדיה]'}..."`);
        
        try {
            await this.processMessage(message);
        } catch (error) {
            console.error('Error processing message:', error);
            await this.notifyAdmins(`Error processing message from: ${senderId}: ${error.message}`);
        }
    }
    
    async processMessage(message) {
        const messageData = {
            id: message.id._serialized,
            userId: message.author || message.from,
            content: message.body || '[מדיה]',
            timestamp: new Date(message.timestamp * 1000),
            // Add message type for better processing
            messageType: message.type,
            hasMedia: message.hasMedia,
            isForwarded: message.isForwarded
        };
        
        // Handle different message types
        if (message.hasMedia) {
            try {
                const media = await message.downloadMedia();
                messageData.content = `[${media.mimetype}] ${message.body || 'קובץ מדיה'}`;
            } catch (error) {
                console.log('Unavle to download media', error.message);
                messageData.content = `[מדיה] ${message.body || 'קובץ מדיה'}`;
            }
        }
        
        console.log(`Sending for analysis: ${messageData.content.substring(0, 50)}...`);
        
        // Call Python moderation agent
        const result = await this.callModerationAgent(messageData);
        
        if (!result) {
            console.log('Unable to analyze message, defaulting to manual review');
            // Default to manual review for safety
            await this.flagForReview(message, {
                classification: "TECHNICAL_ERROR",
                confidence: 0.0,
                action: "FLAG_FOR_REVIEW",
                reasoning: "לא ניתן לנתח את ההודעה כראוי. יש לבדוק ידנית.",
            }, await this.getContactName(messageData.userId), messageData);
            return;
        }
        
        console.log(`Analysis result: ${result.classification} (${(result.confidence * 100).toFixed(1)}%)`);
        
        // Execute action based on result
        await this.executeAction(result, message, messageData);
    }
    
    async callModerationAgent(messageData) {
        return new Promise((resolve, reject) => {
            const pythonProcess = spawn('python', [
                'moderation_api.py',
                messageData.id,
                messageData.userId,
                messageData.content
            ], {
                cwd: process.cwd()
            });
            
            let result = '';
            let error = '';
            
            pythonProcess.stdout.on('data', (data) => {
                result += data.toString();
            });
            
            pythonProcess.stderr.on('data', (data) => {
                error += data.toString();
            });
            
            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    try {
                        const parsedResult = JSON.parse(result);
                        resolve(parsedResult);
                    } catch (e) {
                        console.error('JSON parsing error:', e);
                        console.error('Python response:', result);
                        resolve(null);
                    }
                } else {
                    console.error('Python process failed:', error);
                    resolve(null);
                }
            });
            
            // Timeout after 15 seconds
            setTimeout(() => {
                pythonProcess.kill();
                console.log('⏱️ Python process timeout');
                resolve(null);
            }, 15000);
        });
    }
    
    async executeAction(result, message, messageData) {
        const contact = await this.getContactName(messageData.userId);
        
        switch (result.action) {
            case 'DELETE_MESSAGE':
                await this.deleteMessage(message, result, contact);
                break;
                
            case 'FLAG_FOR_REVIEW':
                await this.flagForReview(message, result, contact, messageData);
                break;
                
            case 'APPROVE':
                console.log(`Message approved: ${messageData.content.substring(0, 30)}...`);
                // Check if it's a media content warning
                if (this.needsMediaWarning(messageData.content)) {
                    await this.sendMediaWarning(message);
                }
                break;
                
            default:
                console.log(`Unknown Action: ${result.action}`);
        }
    }
    
    async deleteMessage(message, result, contact) {
        try {
            // Try to delete the message
            await message.delete(true);
            console.log(`🗑️ Message was deleted: ${message.body?.substring(0, 30)}...`);
            
            // Notify admins
            const notificationMsg = `🚨 **הודעה נמחקה אוטומטית**

👤 **משתמש:** ${contact}
🏷️ **סיווג:** ${result.classification}
📊 **ביטחון:** ${(result.confidence * 100).toFixed(1)}%
💭 **סיבה:** ${result.reasoning}

📝 **תוכן שנמחק:**
"${message.body?.substring(0, 200)}${message.body?.length > 200 ? '...' : ''}"

⏰ **זמן:** ${new Date().toLocaleString('he-IL')}`;

            await this.notifyAdmins(notificationMsg);
            
        } catch (error) {
            console.error('❌ נכשל במחיקת הודעה:', error);
            
            // If delete failed, flag for manual review
            await this.flagForReview(message, {
                ...result,
                reasoning: `מחיקה אוטומטית נכשלה: ${error.message}. ${result.reasoning}`
            }, contact, { content: message.body });
        }
    }
    
    async flagForReview(message, result, contact, messageData) {
        const reviewId = `review_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Store for reaction handling
        this.pendingReviews.set(message.id._serialized, {
            reviewId,
            messageId: messageData.id,
            result,
            timestamp: new Date()
        });
        
        const reviewMsg = `⚠️ **הודעה מסומנת לבדיקה**

👤 **משתמש:** ${contact}
🏷️ **סיווג:** ${result.classification}
📊 **ביטחון:** ${(result.confidence * 100).toFixed(1)}%
💭 **נימוק:** ${result.reasoning}

📝 **תוכן ההודעה:**
"${messageData.content.substring(0, 300)}${messageData.content.length > 300 ? '...' : ''}"

**הגיבו להודעה זו בהתאם:**
✅ - אשר הודעה (הסוכן טעה)
❌ - מחק הודעה (הסוכן צדק)
⚠️ - מקרה מורכב
🔄 - נתח מחדש

🆔 Review ID: ${reviewId}
⏰ ${new Date().toLocaleString('he-IL')}`;

        await this.notifyAdmins(reviewMsg);
        
        console.log(`Message flagged for review: ${reviewId}`);
    }
    
    async handleReaction(reaction) {
        try {
            // Check if reaction is from admin
            if (!this.adminIds.has(reaction.senderId)) {
                return;
            }
            
            const messageId = reaction.msgId._serialized;
            const reactionEmoji = reaction.reaction;
            
            // Check if this is a review we're tracking
            if (!this.pendingReviews.has(messageId)) {
                return;
            }
            
            const reviewData = this.pendingReviews.get(messageId);
            console.log(`Admin reacted ${reactionEmoji} to review ${reviewData.reviewId}`);
            
            // Process the feedback
            await this.processFeedback(reviewData, reactionEmoji);
            
            // Remove from pending
            this.pendingReviews.delete(messageId);
            
        } catch (error) {
            console.error('Error handling reaction:', error);
        }
    }
    
    async processFeedback(reviewData, reaction) {
        const feedbackMapping = {
            '✅': 'CORRECT',
            '❌': 'INCORRECT',
            '⚠️': 'COMPLEX',
            '🔄': 'REANALYZE'
        };
        
        const feedbackType = feedbackMapping[reaction];
        if (!feedbackType) {
            console.log(`Unknown reaction: ${reaction}`);
            return;
        }
        
        // Send feedback to Python agent
        try {
            const feedbackProcess = spawn('python', [
                'process_feedback.py',
                reviewData.messageId,
                reaction
            ]);
            
            feedbackProcess.on('close', (code) => {
                if (code === 0) {
                    console.log(`Feedback sent successfully: ${reaction}`);
                } else {
                    console.error(`Error sending feedback: code ${code}`);
                }
            });
            
            // Acknowledge feedback
            const ackMsg = `👍 **פידבק התקבל**

🆔 Review: ${reviewData.reviewId}
📝 פעולה: ${this.getFeedbackDescription(reaction)}
🕐 זמן: ${new Date().toLocaleString('he-IL')}

הסוכן ילמד מהפידבק הזה!`;

            await this.notifyAdmins(ackMsg);
            
        } catch (error) {
            console.error('Error processing feedback:', error);
        }
    }
    
    getFeedbackDescription(reaction) {
        const descriptions = {
            '✅': 'הסוכן טעה - ההודעה תקינה',
            '❌': 'הסוכן צדק - ההודעה צריכה מחיקה',
            '⚠️': 'מקרה מורכב לדיון נוסף',
            '🔄': 'ניתוח מחדש נדרש'
        };
        return descriptions[reaction] || 'לא ידוע';
    }
    
    async handleGroupJoin(notification) {
        if (notification.chatId !== this.targetGroupId) {
            return;
        }
        
        // Add new members to tracking
        const newMembers = notification.recipientIds;
        for (const memberId of newMembers) {
            this.allMembers.add(memberId._serialized);
            console.log(`New member added to tracking: ${memberId.user}`);
        }
        
        const newMemberNames = newMembers.map(id => id.user);
        
        const joinMsg = `**חברים חדשים הצטרפו**

🆕 חברים: ${newMemberNames.join(', ')}
⏰ זמן: ${new Date().toLocaleString('he-IL')}
📊 סה"כ חברים: ${this.allMembers.size}

💡 **תזכורת לחברים החדשים:**
• קראו את תקנון הקבוצה
• היו זהירים עם שיתוף מידע רגיש
• לידיעתכם -ישנו בוט המפקח על ההודעות 

🤖 הבוט יתחיל לפקח על הודעותיהם`;

        await this.notifyAdmins(joinMsg);
        console.log(`New members: ${newMemberNames.join(', ')}`);
    }
    
    // FIX: Add handler for members leaving
    async handleGroupLeave(notification) {
        if (notification.chatId !== this.targetGroupId) {
            return;
        }
        
        const leftMembers = notification.recipientIds;
        for (const memberId of leftMembers) {
            this.allMembers.delete(memberId._serialized);
            this.adminIds.delete(memberId._serialized); // Remove from admins too if needed
            console.log(`Member removed from tracking: ${memberId.user}`);
        }
        
        console.log(`Active members ${this.allMembers.size}`);
    }
    
    needsMediaWarning(content) {
        const mediaKeywords = [
            'סרטון', 'סירטון', 'וידאו', 'תמונה', 'תמונות', 'צילום',
            'לייב', 'שידור', 'מהשטח', 'מהמקום', 'מהפעילות'
        ];
        
        return mediaKeywords.some(keyword => content.includes(keyword));
    }
    
    async sendMediaWarning(message) {
        try {
            await message.reply('🔔 *תזכורת אוטומטית:*נא לשים לב לתוכן המדיה שמשותף ולמיקום הצילום');
            console.log('Media warning sent successfully');
        } catch (error) {
            console.error('Failed to send media warning:', error);
        }
    }
    
    async getContactName(userId) {
        try {
            const contact = await this.client.getContactById(userId);
            return contact.pushname || contact.number || 'לא ידוע';
        } catch (error) {
            return userId.split('@')[0] || 'לא ידוע';
        }
    }
    
    async notifyAdmins(message) {
        for (const adminId of this.adminIds) {
            try {
                await this.client.sendMessage(adminId, message);
            } catch (error) {
                console.error(`נכשל בשליחה למנהל ${adminId}:`, error.message);
            }
        }
    }
    
    async sendDailyReport() {
        try {
            // Get stats from Python agent
            const statsProcess = spawn('python', ['get_daily_stats.py']);
            
            let statsResult = '';
            statsProcess.stdout.on('data', (data) => {
                statsResult += data.toString();
            });
            
            statsProcess.on('close', (code) => {
                if (code === 0) {
                    try {
                        const stats = JSON.parse(statsResult);
                        const reportMsg = this.generateDailyReport(stats);
                        this.notifyAdmins(reportMsg);
                    } catch (e) {
                        console.error('Error in parsing statistics:', e);
                    }
                }
            });
            
        } catch (error) {
            console.error('Error in daily report', error);
        }
    }
    
    generateDailyReport(stats) {
        return `**דוח יומי - סוכן חמ"ל**

**סטטיסטיקות היום:**
• 📨 הודעות שנותחו: ${stats.daily_messages || 0}
• ✅ הודעות שאושרו: ${stats.approved || 0}
• ⚠️ הודעות שסומנו: ${stats.flagged || 0}
• 🗑️ הודעות שנמחקו: ${stats.deleted || 0}

👥 **מעקב חברים:**
• סה"כ חברים פעילים: ${this.allMembers.size}
• מנהלים: ${this.adminIds.size}

 ** ביצועי סוכן חמ"ל:**
• דיוק כולל: ${stats.accuracy || 0}%
• שיפור משבוע שעבר: ${stats.improvement || 0}%

📅 **תאריך:** ${new Date().toLocaleDateString('he-IL')}
🕐 **זמן:** ${new Date().toLocaleTimeString('he-IL')}

🤖 ינעל שורלוק הסוכן ממשיך להשתפר!`;
    }
    
    async start() {
        console.log('⬆Uploading WhatsApp Moderation Bot...');
        await this.client.initialize();
        
        // Schedule daily report (every day at 08:00)
        setInterval(() => {
            const now = new Date();
            if (now.getHours() === 20 && now.getMinutes() === 0) {
                this.sendDailyReport();
            }
        }, 60000); // Check every minute
        
        console.log('Daily update set to 20:00');
    }
    
    async stop() {
        console.log('Stopping WhatsApp Bot...');
        await this.client.destroy();
    }
    
    // Utility methods
    async getGroupInfo() {
        if (!this.targetGroupId) return null;
        
        try {
            const group = await this.client.getChatById(this.targetGroupId);
            return {
                name: group.name,
                participants: group.participants.length,
                trackedMembers: this.allMembers.size,
                admins: this.adminIds.size,
                description: group.description
            };
        } catch (error) {
            console.error('Error reciving info in the group:', error);
            return null;
        }
    }
    
    // Add method to manually refresh member list
    async refreshMemberList() {
        try {
            if (!this.targetGroupId) return false;
            
            const group = await this.client.getChatById(this.targetGroupId);
            
            // Clear and rebuild member lists
            this.allMembers.clear();
            this.adminIds.clear();
            
            for (const participant of group.participants) {
                this.allMembers.add(participant.id._serialized);
                
                if (participant.isAdmin || participant.isSuperAdmin) {
                    this.adminIds.add(participant.id._serialized);
                }
            }
            
            console.log(`Members list is up-to-date: ${this.allMembers.size} Friends, ${this.adminIds.size} Admins`);
            return true;
            
        } catch (error) {
            console.error('Error refreshing members list:', error);
            return false;
        }
    }
}

// Export for use as module
module.exports = WhatsAppModerationBot;

// Run if called directly
if (require.main === module) {
    const bot = new WhatsAppModerationBot();
    
    // Start the bot
    bot.start().catch(console.error);
    
    // Graceful shutdown
    process.on('SIGINT', async () => {
        console.log('\nShutting down');
        await bot.stop();
        process.exit(0);
    });
    
    process.on('uncaughtException', (error) => {
        console.error('Unexpected error:', error);
    });
    
    process.on('unhandledRejection', (reason, promise) => {
        console.error('Promise not handled:  :', reason);
    });
}