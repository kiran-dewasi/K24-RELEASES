"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { API_CONFIG } from "@/lib/api-config";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sparkles, Send, User, SlidersHorizontal, Check, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FollowUpCard } from "@/components/chat/ChatCards";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ReactMarkdown from 'react-markdown';

// Types
interface Message {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    type?: 'text' | 'draft_voucher' | 'follow_up' | 'card' | 'table';
    data?: any;
    timestamp: Date;
}

const SUGGESTIONS = [
    "Show outstanding receivables",
    "Cashflow last 30 days",
    "Create a sales invoice for ABC Corp",
    "Top 5 customers by revenue"
];

export function KittuChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [threadId, setThreadId] = useState("");

    // Context Panel State
    const [showContext, setShowContext] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const searchParams = useSearchParams();

    // Initialize Thread
    useEffect(() => {
        let tid = searchParams.get("thread_id");
        if (!tid) {
            tid = localStorage.getItem("k24_thread_id");
            if (!tid) {
                tid = crypto.randomUUID();
                localStorage.setItem("k24_thread_id", tid);
            }
        }
        setThreadId(tid);

        // Check for query intent from other pages
        const pendingQuery = searchParams.get("q");
        if (pendingQuery && messages.length === 0) {
            handleSendMessage(pendingQuery);
            // Clean URL without reload
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.delete("q");
            window.history.replaceState({}, "", newUrl.toString());
        }
    }, [searchParams]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSendMessage = async (textOverride?: string) => {
        const text = textOverride || input;
        if (!text.trim() || loading) return;

        setInput("");

        // Add User Message
        const userMsg: Message = {
            id: Date.now(),
            role: 'user',
            content: text,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/api/chat`, {
                method: "POST",
                headers: API_CONFIG.getHeaders(),
                body: JSON.stringify({
                    thread_id: threadId,
                    message: text
                }),
            });

            if (!res.ok) throw new Error("Failed to fetch");

            // Placeholder for AI response
            const aiMsgId = Date.now() + 1;
            setMessages(prev => [...prev, {
                id: aiMsgId,
                role: 'assistant',
                content: "",
                timestamp: new Date(),
                type: 'text'
            }]);

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let accumulatedContent = "";

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));

                                if (data.type === 'response' || data.type === 'content') {
                                    accumulatedContent = data.content;
                                    setMessages(prev => prev.map(m =>
                                        m.id === aiMsgId ? { ...m, content: accumulatedContent } : m
                                    ));
                                } else if (data.type) {
                                    // Handle Rich Types (updates the type and data of the message)
                                    setMessages(prev => prev.map(m =>
                                        m.id === aiMsgId ? { ...m, type: data.type, data: data.data || data } : m
                                    ));
                                }
                            } catch (e) {
                                console.error("Error parsing stream", e);
                            }
                        }
                    }
                }
            }

        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                id: Date.now(),
                role: 'assistant',
                content: "I'm having trouble connecting to the server. Please try again.",
                timestamp: new Date()
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmDraft = async (draft: any) => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/vouchers`, {
                method: "POST",
                headers: API_CONFIG.getHeaders(),
                body: JSON.stringify(draft),
            });
            const result = await res.json();

            if (res.ok) {
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    role: 'assistant',
                    content: `Success! Voucher Created. Ref: ${result.tally_response?.raw || "Synced"}`,
                    type: 'text',
                    timestamp: new Date()
                }]);
            } else {
                alert(`Error: ${result.message}`);
            }
        } catch (err) {
            alert("Failed to connect to backend.");
        }
    };

    const renderMessageContent = (msg: Message) => {
        if (msg.role === 'user') return msg.content;

        // Assistant Content Logic
        return (
            <div className="space-y-4">
                {/* Text Content with Markdown Rendering */}
                {msg.content && (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown
                            components={{
                                // Custom table styling
                                table: ({ node, ...props }) => (
                                    <table className="min-w-full border-collapse border border-gray-200 dark:border-gray-700 my-2" {...props} />
                                ),
                                th: ({ node, ...props }) => (
                                    <th className="border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-left text-xs font-semibold" {...props} />
                                ),
                                td: ({ node, ...props }) => (
                                    <td className="border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm" {...props} />
                                ),
                                // Bold styling
                                strong: ({ node, ...props }) => (
                                    <strong className="font-semibold text-primary" {...props} />
                                ),
                                // List styling
                                ul: ({ node, ...props }) => (
                                    <ul className="list-disc list-inside space-y-1" {...props} />
                                ),
                                li: ({ node, ...props }) => (
                                    <li className="text-sm" {...props} />
                                ),
                                // Headers
                                h3: ({ node, ...props }) => (
                                    <h3 className="text-sm font-semibold mt-3 mb-1" {...props} />
                                ),
                            }}
                        >
                            {msg.content}
                        </ReactMarkdown>
                    </div>
                )}

                {/* RICH CONTENT HANDLERS */}

                {/* 1. Draft Voucher Card */}
                {msg.type === 'draft_voucher' && msg.data && (
                    <Card className="border-purple-200 shadow-sm bg-white overflow-hidden max-w-md">
                        <CardHeader className="bg-purple-50/50 pb-3 border-b border-purple-100">
                            <CardTitle className="text-purple-900 text-sm flex justify-between items-center font-semibold">
                                <span>Confirm {msg.data.voucher_type}</span>
                                <Badge variant="secondary" className="bg-purple-100 text-purple-700 hover:bg-purple-100">Draft</Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-4 space-y-3">
                            <div className="flex justify-between items-end">
                                <div>
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Party</p>
                                    <p className="text-base font-medium text-foreground">{msg.data.party_name}</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Amount</p>
                                    <p className="text-xl font-bold text-green-600">₹{msg.data.amount?.toLocaleString('en-IN')}</p>
                                </div>
                            </div>

                            {msg.data.items && msg.data.items.length > 0 && (
                                <div className="bg-muted/30 rounded-lg p-2 space-y-1 mt-2">
                                    {msg.data.items.map((item: any, i: number) => (
                                        <div key={i} className="flex justify-between text-sm">
                                            <span className="text-muted-foreground font-medium">{item.name} <span className="text-xs opacity-70">x {item.quantity}</span></span>
                                            <span>₹{(item.amount || 0).toLocaleString('en-IN')}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                        <CardFooter className="justify-between gap-2 pt-0 pb-3 px-4 bg-purple-50/20">
                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive">Cancel</Button>
                            <Button size="sm" onClick={() => handleConfirmDraft(msg.data)} className="bg-purple-600 hover:bg-purple-700 text-white gap-2">
                                <Check className="h-4 w-4" /> Approve & Save
                            </Button>
                        </CardFooter>
                    </Card>
                )}

                {/* 2. Follow Up Question */}
                {msg.type === 'follow_up' && msg.data && (
                    <div className="max-w-md">
                        <FollowUpCard
                            question={msg.data.question || msg.content}
                            missingSlots={msg.data.missing_slots}
                            onResponse={(answer) => handleSendMessage(answer)}
                        />
                    </div>
                )}

                {/* 3. Data Tables */}
                {msg.type === 'table' && msg.data && (
                    <Card className="max-w-xl border shadow-sm">
                        <CardHeader className="py-3 px-4 border-b bg-muted/20">
                            <CardTitle className="text-sm font-medium">{msg.data.title || "Data View"}</CardTitle>
                        </CardHeader>
                        <div className="overflow-x-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        {msg.data.columns?.map((col: string, i: number) => (
                                            <TableHead key={i} className="h-9 text-xs font-bold uppercase">{col}</TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {msg.data.rows?.map((row: any[], i: number) => (
                                        <TableRow key={i}>
                                            {row.map((cell: any, j: number) => (
                                                <TableCell key={j} className="py-2 text-sm">{cell}</TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </Card>
                )}
            </div>
        );
    };

    return (
        <div className="flex h-[calc(100vh-4rem)] bg-background">

            {/* MAIN CHAT AREA */}
            <div className="flex-1 flex flex-col relative w-full max-w-5xl mx-auto">

                {/* Scrollable Messages */}
                <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
                    {/* Welcome / Onboarding State */}
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-center space-y-6 animate-in fade-in zoom-in-95 duration-500">
                            <div className="h-20 w-20 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                                <Sparkles className="h-10 w-10 text-primary" />
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight">Good evening, Kiran</h2>
                            <p className="text-muted-foreground text-lg max-w-md">
                                I'm KITTU, your financial assistant. I can help you query Tally data, create invoices, or analyze your cashflow.
                            </p>
                        </div>
                    )}

                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {msg.role === 'assistant' && (
                                <Avatar className="h-8 w-8 border bg-background mt-1">
                                    <AvatarFallback><Sparkles className="h-4 w-4 text-primary" /></AvatarFallback>
                                </Avatar>
                            )}

                            <div className={`max-w-[85%] md:max-w-[75%] space-y-2`}>
                                <div
                                    className={`p-4 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed ${msg.role === 'user'
                                        ? 'bg-primary text-primary-foreground rounded-tr-none'
                                        : 'bg-card border text-card-foreground rounded-tl-none'
                                        }`}
                                >
                                    {renderMessageContent(msg)}
                                    {msg.content === "" && loading && <span className="animate-pulse">Thinking...</span>}
                                </div>
                                <div className={`text-[10px] text-muted-foreground ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>

                            {msg.role === 'user' && (
                                <Avatar className="h-8 w-8 border bg-muted mt-1">
                                    <AvatarFallback><User className="h-4 w-4" /></AvatarFallback>
                                </Avatar>
                            )}
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Bottom Input Area */}
                <div className="p-4 md:p-6 bg-background/80 backdrop-blur-sm border-t sticky bottom-0 z-10 w-full max-w-4xl mx-auto">

                    {/* Suggestions Chips */}
                    {messages.length === 0 && (
                        <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide">
                            {SUGGESTIONS.map((s, i) => (
                                <Button
                                    key={i}
                                    variant="outline"
                                    size="sm"
                                    className="whitespace-nowrap rounded-full bg-background hover:bg-muted"
                                    onClick={() => handleSendMessage(s)}
                                >
                                    {s}
                                </Button>
                            ))}
                        </div>
                    )}

                    <div className="relative flex items-center shadow-lg rounded-xl bg-card border focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
                            placeholder="Ask KITTU anything about your finances..."
                            className="h-14 pl-4 pr-14 border-none shadow-none text-base bg-transparent focus-visible:ring-0"
                            disabled={loading}
                        />
                        <Button
                            size="icon"
                            className="absolute right-2 h-10 w-10 shrink-0 rounded-lg"
                            onClick={() => handleSendMessage()}
                            disabled={!input.trim() || loading}
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="text-center mt-2">
                        <span className="text-[10px] text-muted-foreground">KITTU uses AI and may make mistakes. Double-check important financial data.</span>
                    </div>
                </div>
            </div>

            {/* RIGHT CONTEXT PANEL (Optional) */}
            {showContext && (
                <div className="hidden xl:flex w-80 flex-col border-l bg-muted/10 h-full p-4 space-y-6">
                    <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-sm flex items-center gap-2">
                            <SlidersHorizontal className="h-4 w-4" />
                            Context & Filters
                        </h3>
                    </div>

                    <div className="space-y-4">
                        <Card className="shadow-none border bg-background">
                            <CardContent className="p-3 space-y-3">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Active Company</label>
                                    <div className="text-sm font-semibold">Tally Demo Co.</div>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Financial Year</label>
                                    <div className="text-sm">Apr 2025 - Mar 2026</div>
                                </div>
                            </CardContent>
                        </Card>

                        <div className="space-y-3">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Quick Filters</label>
                            <div className="flex flex-wrap gap-2">
                                <Badge variant="secondary" className="cursor-pointer hover:bg-muted">Last 30 Days</Badge>
                                <Badge variant="outline" className="cursor-pointer hover:bg-muted dashed border-dashed text-muted-foreground">+ Add Filter</Badge>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
