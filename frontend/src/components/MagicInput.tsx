"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, ArrowRight, Check, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FollowUpCard, PartySelectorCard, ItemSelectorCard } from "@/components/chat/ChatCards";
import { api } from "@/lib/api";

interface DraftVoucher {
    party_name: string;
    voucher_type: string;
    amount: number;
    items: { name: string; quantity: number; rate?: number; amount: number }[];
}

export default function MagicInput({
    isFullPage = false,
    theme = "light",
    pageContext = {},
    allowEmbedded = false,
    suggestions = [],
    placeholder = "✨ Type your message..."
}: {
    isFullPage?: boolean;
    theme?: "light" | "dark" | "claude";
    pageContext?: any;
    allowEmbedded?: boolean;
    suggestions?: string[];
    placeholder?: string;
}) {
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    // Chat History State
    const [messages, setMessages] = useState<Array<{
        role: 'user' | 'assistant',
        content?: string,
        type?: 'text' | 'draft_voucher' | 'follow_up' | 'card' | 'navigation',
        data?: any
    }>>([]);

    const router = useRouter();
    const searchParams = useSearchParams();

    const isDark = theme === "dark";
    const isClaude = theme === "claude";

    let baseInputClass = "pl-10 h-14 text-lg shadow-lg border-purple-200 focus-visible:ring-purple-500";
    let iconColor = "text-purple-500";
    let buttonClass = "absolute right-2 top-2 bottom-2 bg-purple-600 hover:bg-purple-700";

    if (isDark) {
        baseInputClass = "pl-12 h-16 text-xl bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus-visible:ring-purple-500/50 focus-visible:border-purple-500/50 shadow-2xl backdrop-blur-xl";
        iconColor = "text-purple-400";
        buttonClass = "absolute right-3 top-3 bottom-3 bg-white text-black hover:bg-gray-200 rounded-lg px-4 transition-all";
    } else if (isClaude) {
        baseInputClass = "pl-4 h-[120px] text-lg bg-white border border-[#E6E1D6] text-[#282828] placeholder:text-[#888888] shadow-sm focus-visible:ring-2 focus-visible:ring-[#D96C46]/20 focus-visible:border-[#D96C46] rounded-2xl resize-none py-4 align-top";
        iconColor = "text-[#D96C46]";
        buttonClass = "absolute right-3 bottom-3 bg-[#D96C46] text-white hover:bg-[#C05A35] rounded-lg px-3 py-1.5 transition-all font-medium text-sm";
    } else {
        baseInputClass = "pl-12 h-16 text-lg bg-white border border-gray-200 text-gray-900 placeholder:text-gray-400 shadow-sm focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:border-transparent rounded-xl transition-all";
        iconColor = "text-gray-400";
        buttonClass = "absolute right-3 top-3 bottom-3 bg-gray-900 text-white hover:bg-gray-800 rounded-lg px-4 transition-all shadow-sm";
    }

    // Auto-trigger if query param exists
    useEffect(() => {
        if (isFullPage) {
            const q = searchParams.get("q");
            if (q && messages.length === 0) {
                // Add initial user message locally to show immediate feedback
                setMessages([{ role: 'user', content: q }]);
                handleMagic(q);
            }
        }
    }, [isFullPage, searchParams]);

    // Scroll to bottom on new message
    useEffect(() => {
        if (messages.length > 0) {
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }
    }, [messages]);

    // Generate or retrieve thread_id on mount
    const [threadId, setThreadId] = useState("");

    useEffect(() => {
        // 1. Check URL param first (Force New Chat)
        const urlThreadId = searchParams.get("thread_id");

        // 2. Check Storage
        let tid = localStorage.getItem("k24_thread_id");

        if (urlThreadId) {
            // If URL has ID, explicit switch
            tid = urlThreadId;
            localStorage.setItem("k24_thread_id", tid);
            // Reset messages if switching threads
            setMessages([]);
        } else if (!tid) {
            // New User
            tid = crypto.randomUUID();
            localStorage.setItem("k24_thread_id", tid);
        }

        setThreadId(tid);
    }, [searchParams]);

    const handleMagic = async (overrideInput?: string) => {
        const textToProcess = overrideInput || input;
        if (!textToProcess.trim()) return;

        // If on dashboard (not full page) and not embedded, redirect to chat page
        if (!isFullPage && !allowEmbedded) {
            router.push(`/chat?q=${encodeURIComponent(textToProcess)}`);
            return;
        }

        // Add user message locally
        if (!overrideInput) {
            setMessages(prev => [...prev, { role: 'user', content: textToProcess }]);
        }

        setInput("");
        setLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001'}/api/chat`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': process.env.NEXT_PUBLIC_API_KEY || 'k24-secret-key-123'
                },
                body: JSON.stringify({
                    thread_id: threadId || crypto.randomUUID(),
                    message: textToProcess
                }),
            });

            if (!response.ok) throw new Error(response.statusText);
            const res = response;

            // Create placeholder for assistant response
            const assistantMsgId = Date.now();
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "",
                type: 'text',
                data: { id: assistantMsgId } // Marker
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
                                    accumulatedContent = data.content; // Replace for now, or append if stream
                                    setMessages(prev => {
                                        const newArr = [...prev];
                                        // Update the last assistant message
                                        const lastIdx = newArr.length - 1;
                                        if (newArr[lastIdx].role === 'assistant') {
                                            newArr[lastIdx].content = accumulatedContent;
                                        }
                                        return newArr;
                                    });
                                }
                                else if (data.type === 'status') {
                                    // Could show status toast or micro-interaction
                                    console.log("Status:", data.content);
                                }
                            } catch (e) {
                                console.error("Error parsing SSE:", e);
                            }
                        }
                    }
                }
            }

        } catch (err) {
            console.error("Magic failed:", err);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "⚠️ Connection failed. Please check backend.",
                type: 'text'
            }]);
        } finally {
            setLoading(false);
            setTimeout(() => {
                const textarea = document.querySelector('textarea');
                if (textarea) textarea.focus();
            }, 100);
        }
    };

    const handleConfirmDraft = async (draft: DraftVoucher) => {
        try {
            const res = await api.post("/vouchers");
            const result = await res.json();

            if (res.ok) {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Success! Voucher Created. Ref: ${result.tally_response?.raw || "Synced"}`,
                    type: 'text'
                }]);
                // Trigger a refresh of the dashboard data
                // window.location.reload(); // Don't reload, just show success
            } else {
                alert(`Error: ${result.message}`);
            }
        } catch (err) {
            alert("Failed to connect to backend.");
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto mb-8">

            {/* Chat History */}
            <div className="space-y-6 mb-8">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

                        {/* User Message */}
                        {msg.role === 'user' && (
                            <div className="bg-[#F4F4F0] text-[#1A1A1A] px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] text-lg">
                                {msg.content}
                            </div>
                        )}

                        {/* Assistant Message */}
                        {msg.role === 'assistant' && (
                            <div className="w-full max-w-[90%] space-y-4">
                                {/* Text Content */}
                                {msg.content && (
                                    <div className="flex gap-3">
                                        <div className="mt-1 min-w-[24px]">
                                            <Sparkles className="h-6 w-6 text-[#D96C46]" />
                                        </div>
                                        <div className="text-[#1A1A1A] text-lg leading-relaxed pt-0.5">
                                            {msg.content}
                                        </div>
                                    </div>
                                )}

                                {/* Widgets / Cards */}
                                <div className="pl-9">
                                    {msg.type === 'draft_voucher' && msg.data && (
                                        <Card className="border-purple-200 shadow-md bg-white">
                                            <CardHeader className="bg-purple-50 pb-2">
                                                <CardTitle className="text-purple-900 text-base flex justify-between items-center">
                                                    <span>Confirm {msg.data.voucher_type}</span>
                                                    <span className="text-xs font-normal text-purple-700 bg-purple-100 px-2 py-1 rounded-full">Draft</span>
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent className="pt-4">
                                                <div className="grid grid-cols-2 gap-4 mb-4">
                                                    <div>
                                                        <label className="text-xs text-muted-foreground uppercase font-bold">Party</label>
                                                        <div className="text-base font-medium">{msg.data.party_name}</div>
                                                    </div>
                                                    <div className="text-right">
                                                        <label className="text-xs text-muted-foreground uppercase font-bold">Amount</label>
                                                        <div className="text-xl font-bold text-green-600">₹{msg.data.amount?.toLocaleString('en-IN')}</div>
                                                    </div>
                                                </div>
                                                {msg.data.items && (
                                                    <ul className="space-y-1 bg-gray-50 p-3 rounded-md">
                                                        {msg.data.items.map((item: any, i: number) => (
                                                            <li key={i} className="flex justify-between text-sm">
                                                                <span>{item.name} <span className="text-muted-foreground">x {item.quantity}</span></span>
                                                                <span>₹{(item.amount || 0).toLocaleString('en-IN')}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </CardContent>
                                            <CardFooter className="justify-end gap-2 pt-0 pb-4">
                                                <Button onClick={() => handleConfirmDraft(msg.data)} className="bg-green-600 hover:bg-green-700 text-white">
                                                    <Check className="mr-2 h-4 w-4" /> Approve & Save
                                                </Button>
                                            </CardFooter>
                                        </Card>
                                    )}

                                    {msg.type === 'follow_up' && msg.data && (
                                        <FollowUpCard
                                            question={msg.data.question || msg.content}
                                            missingSlots={msg.data.missing_slots}
                                            onResponse={(answer) => handleMagic(answer)}
                                        />
                                    )}

                                    {msg.type === 'card' && msg.data && (
                                        <Card className="border-blue-200 shadow-md bg-blue-50/30">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-blue-900 text-base">{msg.data.title || "Insight"}</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="grid grid-cols-2 gap-3">
                                                    {Object.entries(msg.data.data || {}).map(([key, value]) => (
                                                        <div key={key} className="bg-white p-2 rounded border border-blue-100">
                                                            <div className="text-[10px] text-muted-foreground uppercase font-bold">{key.replace(/_/g, ' ')}</div>
                                                            <div className="text-base font-bold text-blue-700">{String(value)}</div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="flex gap-3 animate-pulse">
                        <div className="mt-1 min-w-[24px]">
                            <Sparkles className="h-6 w-6 text-gray-300" />
                        </div>
                        <div className="h-4 w-24 bg-gray-200 rounded mt-2"></div>
                    </div>
                )}
            </div>

            {/* Input Area (Sticky Bottom or just at bottom of flow) */}
            <div className="relative">
                {!isClaude && (
                    <div className={`absolute inset-y-0 left-4 flex items-center pointer-events-none ${isDark ? 'left-5' : 'left-3'}`}>
                        <Sparkles className={`h-5 w-5 ${iconColor} animate-pulse`} />
                    </div>
                )}

                {isClaude ? (
                    <textarea
                        placeholder={placeholder}
                        className={`${baseInputClass} w-full transition-all duration-300`}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleMagic();
                            }
                        }}
                        disabled={loading}
                        suppressHydrationWarning
                    />
                ) : (
                    <Input
                        placeholder={placeholder}
                        className={`${baseInputClass} transition-all duration-300`}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleMagic()}
                        disabled={loading}
                        suppressHydrationWarning
                    />
                )}

                <Button
                    className={buttonClass}
                    onClick={() => handleMagic()}
                    disabled={loading}
                >
                    {loading ? (
                        <span className="animate-pulse">...</span>
                    ) : (
                        isClaude ? "Send" : <ArrowRight className="h-5 w-5" />
                    )}
                </Button>
            </div>

            {/* Suggestions (Only if no messages) */}
            {suggestions.length > 0 && messages.length === 0 && (
                <div className="mt-8 pb-24">
                    <div className="text-xs text-[#9B9B9B] mb-4 uppercase tracking-wider">
                        Suggestions
                    </div>
                    <div className="space-y-2">
                        {suggestions.map((suggestion, idx) => (
                            <button
                                key={idx}
                                onClick={() => {
                                    setInput(suggestion);
                                    const textarea = document.querySelector('textarea');
                                    if (textarea) textarea.focus();
                                }}
                                className="w-full text-left px-4 py-3 text-[14px] text-[#1A1A1A] bg-white hover:bg-[#F5F2EB] border border-[#E6E3DC] rounded-lg transition-colors"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
