"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { API_CONFIG } from "@/lib/api-config";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { FollowUpCard } from "@/components/chat/ChatCards";
import { useUser } from "@/contexts/UserContext";
import { useChat } from "@/contexts/ChatContext";
import ReactMarkdown from "react-markdown";
import {
    Sparkles, Send, Check, X, ArrowRight, Loader2,
    ChevronRight, PanelRight, PanelRightClose,
    ReceiptText, BarChart2, FileText, Zap,
    Clock, Copy, ThumbsUp, ThumbsDown, Plus, Hash,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
    id: number;
    role: "user" | "assistant";
    content: string;
    type?: "text" | "draft_voucher" | "follow_up" | "card" | "table";
    data?: any;
    timestamp: Date;
    steps?: string[];
    isStreaming?: boolean;
}

interface ArtifactItem {
    id: number;
    label: string;
    icon: React.ReactNode;
    content: React.ReactNode;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getGreeting() {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
}

function getFirstName(name: string | null | undefined) {
    if (!name) return "";
    return name.trim().split(/\s+/)[0];
}

const fmtTime = (d: Date) =>
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const inrFmt = (n: number) =>
    "₹" + (n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

const SUGGESTIONS = [
    { label: "Outstanding receivables", icon: <BarChart2 className="h-3.5 w-3.5" /> },
    { label: "Cashflow last 30 days", icon: <BarChart2 className="h-3.5 w-3.5" /> },
    { label: "Create sales invoice", icon: <ReceiptText className="h-3.5 w-3.5" /> },
    { label: "Top 5 customers by revenue", icon: <FileText className="h-3.5 w-3.5" /> },
];

const SLASH_COMMANDS = [
    { cmd: "/invoice", desc: "Create a new sales invoice", icon: <ReceiptText className="h-4 w-4 text-indigo-500" /> },
    { cmd: "/balance", desc: "Check party balance", icon: <BarChart2 className="h-4 w-4 text-emerald-500" /> },
    { cmd: "/report", desc: "Generate a financial report", icon: <FileText className="h-4 w-4 text-violet-500" /> },
    { cmd: "/gst", desc: "GST liability summary", icon: <BarChart2 className="h-4 w-4 text-orange-500" /> },
];

// ─── LocalStorage persistence ─────────────────────────────────────────────────

const STORAGE_KEY = "k24_chat_messages";

function loadMessages(threadId: string): Message[] {
    try {
        const raw = localStorage.getItem(`${STORAGE_KEY}_${threadId}`);
        if (!raw) return [];
        const parsed = JSON.parse(raw) as { role: "user" | "assistant"; content: string; timestamp: string; type?: string; data?: any }[];
        return parsed.map((m, i) => ({
            id: i,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp),
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            type: m.type as any,
            data: m.data,
        } as Message));
    } catch {
        return [];
    }
}

function saveMessages(threadId: string, messages: Message[]) {
    try {
        const toStore = messages
            .filter(m => !m.isStreaming)
            .map(m => ({
                role: m.role,
                content: m.content,
                timestamp: m.timestamp.toISOString(),
                type: m.type,
                data: m.data,
            }));
        localStorage.setItem(`${STORAGE_KEY}_${threadId}`, JSON.stringify(toStore));
    } catch {
        // ignore quota errors
    }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TypingDots() {
    return (
        <span className="inline-flex items-center gap-0.5 h-4">
            {[0, 1, 2].map(i => (
                <span key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400"
                    style={{ animation: `kbounce 1.2s ${i * 0.2}s infinite ease-in-out` }} />
            ))}
        </span>
    );
}

function StepIndicator({ steps }: { steps: string[] }) {
    return (
        <div className="mt-2 space-y-1.5">
            {steps.map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                    {i === steps.length - 1
                        ? <Loader2 className="h-3 w-3 animate-spin text-indigo-400 shrink-0" />
                        : <div className="h-3 w-3 rounded-full bg-emerald-400 shrink-0 flex items-center justify-center">
                            <Check className="h-2 w-2 text-white" />
                        </div>
                    }
                    <span className={i === steps.length - 1
                        ? "text-indigo-500 font-medium"
                        : "line-through text-slate-400"}>
                        {step}
                    </span>
                </div>
            ))}
        </div>
    );
}

function DraftVoucherArtifact({ data, onConfirm }: { data: any; onConfirm: (d: any) => void }) {
    return (
        <div className="space-y-4">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Type</p>
                    <p className="font-semibold text-slate-800 mt-0.5">{data.voucher_type}</p>
                </div>
                <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-[10px]">Draft</Badge>
            </div>
            <div className="h-px bg-slate-100" />
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Party</p>
                    <p className="font-semibold text-slate-800 mt-0.5">{data.party_name}</p>
                </div>
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Amount</p>
                    <p className="font-bold text-emerald-600 text-lg mt-0.5">{inrFmt(data.amount)}</p>
                </div>
            </div>
            {data.items?.length > 0 && (
                <div className="bg-slate-50 rounded-xl p-3 space-y-1.5">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Line Items</p>
                    {data.items.map((item: any, i: number) => (
                        <div key={i} className="flex justify-between text-sm">
                            <span className="text-slate-600">{item.name} <span className="text-slate-400">×{item.qty}</span></span>
                            <span className="font-medium text-slate-800">{inrFmt(item.amount)}</span>
                        </div>
                    ))}
                </div>
            )}
            <div className="flex gap-2 pt-2">
                <Button size="sm"
                    className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white gap-1.5 h-9 rounded-xl text-xs font-semibold"
                    onClick={() => onConfirm(data)}>
                    <Check className="h-3.5 w-3.5" /> Approve & Save
                </Button>
                <Button size="sm" variant="outline" className="h-9 rounded-xl px-3 text-xs text-slate-500">
                    <X className="h-3.5 w-3.5" />
                </Button>
            </div>
        </div>
    );
}

function EmptyState({ onSuggestion, userName }: { onSuggestion: (s: string) => void; userName: string }) {
    return (
        <div className="flex flex-col items-center justify-center h-full px-6 text-center select-none">
            <div className="relative mb-7">
                <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-xl shadow-indigo-200">
                    <Sparkles className="h-9 w-9 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 h-6 w-6 bg-emerald-400 rounded-full flex items-center justify-center border-2 border-white">
                    <Zap className="h-3 w-3 text-white fill-white" />
                </div>
            </div>

            <h2 className="text-[22px] font-bold text-slate-800 tracking-tight">
                {getGreeting()}{userName ? `, ${userName}` : ""}
            </h2>
            <p className="mt-1.5 text-slate-500 text-sm max-w-xs leading-relaxed">
                I'm KITTU, your financial intelligence layer.
                Ask me anything about your Tally data.
            </p>

            <div className="flex flex-wrap gap-2 justify-center mt-4">
                {["Query Tally data", "Draft invoices", "GST analysis", "Cash flow"].map(f => (
                    <span key={f} className="inline-flex items-center gap-1.5 text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-400" /> {f}
                    </span>
                ))}
            </div>

            <div className="grid grid-cols-2 gap-2.5 mt-7 w-full max-w-sm">
                {SUGGESTIONS.map((s, i) => (
                    <button key={i} onClick={() => onSuggestion(s.label)}
                        className="group text-left p-3.5 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all duration-200 shadow-sm hover:shadow-md">
                        <div className="flex items-center gap-2 text-indigo-500 mb-1.5">{s.icon}</div>
                        <p className="text-[12px] text-slate-600 font-medium leading-tight group-hover:text-slate-800">{s.label}</p>
                        <ChevronRight className="h-3 w-3 text-slate-300 mt-1 group-hover:text-indigo-400 transition-colors" />
                    </button>
                ))}
            </div>
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function KittuChat() {
    const { user } = useUser();
    const chat = useChat();
    const firstName = getFirstName(user?.full_name);

    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [showStage, setShowStage] = useState(false);
    const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
    const [activeArt, setActiveArt] = useState<number | null>(null);
    const [showSlash, setShowSlash] = useState(false);
    const [copied, setCopied] = useState<number | null>(null);

    // Track which thread's messages we currently have loaded
    const currentThreadRef = useRef<string>("");

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const searchParams = useSearchParams();

    // ── Load persisted messages when thread changes ──────────────────────────
    const loadThread = useCallback((threadId: string) => {
        if (currentThreadRef.current === threadId) return;
        currentThreadRef.current = threadId;
        const persisted = loadMessages(threadId);
        setMessages(persisted);
        setArtifacts([]);
        setActiveArt(null);
        setShowStage(false);
    }, []);

    // ── Initial load for active thread ────────────────────────────────────────
    useEffect(() => {
        loadThread(chat.activeThreadId);
    }, [chat.activeThreadId, loadThread]);

    // ── Listen for sidebar events ──────────────────────────────────────────
    useEffect(() => {
        const onNew = (e: Event) => {
            const id = (e as CustomEvent).detail?.id ?? chat.activeThreadId;
            currentThreadRef.current = id;
            setMessages([]);
            setArtifacts([]);
            setActiveArt(null);
            setShowStage(false);
            inputRef.current?.focus();
        };
        const onSelect = (e: Event) => {
            const id = (e as CustomEvent).detail?.id;
            if (id) {
                loadThread(id);
                inputRef.current?.focus();
            }
        };
        window.addEventListener("k24_new_thread", onNew);
        window.addEventListener("k24_select_thread", onSelect);
        return () => {
            window.removeEventListener("k24_new_thread", onNew);
            window.removeEventListener("k24_select_thread", onSelect);
        };
    }, [chat.activeThreadId, loadThread]);

    // ── Handle ?q= deep link ──────────────────────────────────────────────
    useEffect(() => {
        const q = searchParams.get("q");
        if (q) {
            setTimeout(() => handleSend(q), 300);
            const url = new URL(window.location.href);
            url.searchParams.delete("q");
            window.history.replaceState({}, "", url.toString());
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Auto-scroll ───────────────────────────────────────────────────────
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // ── Slash detection ───────────────────────────────────────────────────
    useEffect(() => {
        setShowSlash(input.startsWith("/") && input.length <= 20);
    }, [input]);

    // ── Send ──────────────────────────────────────────────────────────────
    const handleSend = useCallback(async (textOverride?: string) => {
        const text = (textOverride ?? input).trim();
        if (!text || loading) return;

        const threadId = chat.activeThreadId;
        setInput("");
        setShowSlash(false);

        const userMsg: Message = {
            id: Date.now(), role: "user", content: text, timestamp: new Date(),
        };

        const isFirst = messages.length === 0;
        const existing = chat.threads.find(t => t.id === threadId);

        setMessages(prev => {
            const updated = [...prev, userMsg];
            saveMessages(threadId, updated);
            return updated;
        });

        // Upsert thread OUTSIDE setMessages to avoid cross-component setState-during-render
        chat.upsertThread({
            id: threadId,
            title: isFirst ? text.slice(0, 50) + (text.length > 50 ? "…" : "") : (existing?.title ?? "Conversation"),
            preview: text.slice(0, 60) + (text.length > 60 ? "…" : ""),
            createdAt: existing?.createdAt ?? new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            messageCount: messages.length + 1,
        });

        setLoading(true);

        const aiId = Date.now() + 1;
        setMessages(prev => [...prev, {
            id: aiId, role: "assistant", content: "",
            timestamp: new Date(), steps: ["Connecting to KITTU…"], isStreaming: true,
        }]);

        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/api/chat`, {
                method: "POST",
                headers: API_CONFIG.getHeaders(),
                body: JSON.stringify({ thread_id: threadId, message: text }),
            });

            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            if (reader) {
                let buffer = "";
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() ?? ""; // keep incomplete line

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) continue;

                        // Support both "data: {...}" (SSE) and raw JSON (ndjson)
                        const jsonStr = trimmed.startsWith("data: ")
                            ? trimmed.slice(6)
                            : trimmed;

                        try {
                            const data = JSON.parse(jsonStr);

                            if (data.type === "status" || data.type === "thought") {
                                setMessages(prev => prev.map(m =>
                                    m.id === aiId
                                        ? { ...m, steps: [...(m.steps ?? []), data.content] }
                                        : m
                                ));
                            } else if (
                                data.type === "response" ||
                                data.type === "content" ||
                                data.type === "message"
                            ) {
                                setMessages(prev => {
                                    const updated = prev.map(m =>
                                        m.id === aiId
                                            ? { ...m, content: data.content, isStreaming: false, steps: undefined }
                                            : m
                                    );
                                    saveMessages(threadId, updated);
                                    return updated;
                                });
                                // Update thread preview OUTSIDE setMessages
                                const t = chat.threads.find(t => t.id === threadId);
                                if (t) {
                                    chat.upsertThread({
                                        ...t,
                                        preview: data.content.slice(0, 60),
                                        updatedAt: new Date().toISOString(),
                                    });
                                }
                            } else if (["draft_voucher", "card", "table"].includes(data.type)) {
                                const art: ArtifactItem = {
                                    id: Date.now(),
                                    label: data.type === "draft_voucher"
                                        ? `Draft ${data.data?.voucher_type ?? "Voucher"}`
                                        : data.data?.title ?? "Insight",
                                    icon: data.type === "draft_voucher"
                                        ? <ReceiptText className="h-3.5 w-3.5" />
                                        : <BarChart2 className="h-3.5 w-3.5" />,
                                    content: data.type === "draft_voucher"
                                        ? <DraftVoucherArtifact data={data.data} onConfirm={handleConfirmDraft} />
                                        : <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(data.data, null, 2)}</pre>,
                                };
                                setArtifacts(prev => [...prev, art]);
                                setActiveArt(art.id);
                                setShowStage(true);
                                setMessages(prev => {
                                    const updated = prev.map(m =>
                                        m.id === aiId
                                            ? { ...m, type: data.type as Message["type"], data: data.data, isStreaming: false }
                                            : m
                                    );
                                    saveMessages(threadId, updated);
                                    return updated;
                                });
                            } else if (data.type === "error") {
                                setMessages(prev => {
                                    const updated = prev.map(m =>
                                        m.id === aiId
                                            ? { ...m, content: `⚠️ ${data.content}`, isStreaming: false }
                                            : m
                                    );
                                    saveMessages(threadId, updated);
                                    return updated;
                                });
                            } else if (data.type === "approval_request") {
                                setMessages(prev => {
                                    const updated = prev.map(m =>
                                        m.id === aiId
                                            ? { ...m, content: data.content, isStreaming: false }
                                            : m
                                    );
                                    saveMessages(threadId, updated);
                                    return updated;
                                });
                            }
                        } catch { /* skip bad lines */ }
                    }
                }
            }
        } catch {
            setMessages(prev => {
                const updated = prev.map(m =>
                    m.id === aiId
                        ? { ...m, content: "⚠️ Couldn't reach the server. Is the backend running?", isStreaming: false }
                        : m
                );
                saveMessages(threadId, updated);
                return updated;
            });
        } finally {
            setLoading(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [input, loading, chat]);

    const handleConfirmDraft = async (draft: any) => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/vouchers`, {
                method: "POST", headers: API_CONFIG.getHeaders(),
                body: JSON.stringify(draft),
            });
            const result = await res.json();
            if (res.ok) {
                setMessages(prev => [...prev, {
                    id: Date.now(), role: "assistant", timestamp: new Date(),
                    content: `✅ Voucher saved! Ref: ${result.tally_response?.raw ?? "Synced to Tally"}`,
                }]);
            }
        } catch { /* handled */ }
    };

    const handleCopy = (id: number, text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    };

    const handleNewChat = () => {
        const id = chat.startNewThread();
        currentThreadRef.current = id;
        setMessages([]);
        setArtifacts([]);
        setActiveArt(null);
        setShowStage(false);
        inputRef.current?.focus();
        window.dispatchEvent(new CustomEvent("k24_new_thread", { detail: { id } }));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    // ── Render assistant message ───────────────────────────────────────────
    const renderAssistant = (msg: Message) => (
        <div className="space-y-3">
            {msg.isStreaming && msg.steps && <StepIndicator steps={msg.steps} />}

            {msg.content && (
                <div className="prose prose-sm prose-slate max-w-none text-slate-700 leading-relaxed">
                    <ReactMarkdown components={{
                        table: p => <table className="min-w-full border-collapse text-xs my-3 rounded-lg overflow-hidden" {...p} />,
                        th: p => <th className="bg-slate-100 text-slate-600 font-semibold px-3 py-2 text-left border border-slate-200" {...p} />,
                        td: p => <td className="border border-slate-100 px-3 py-1.5 text-slate-700" {...p} />,
                        strong: p => <strong className="font-semibold text-slate-800" {...p} />,
                        code: p => <code className="bg-slate-100 text-indigo-700 px-1.5 py-0.5 rounded text-[11px] font-mono" {...p} />,
                        ul: p => <ul className="list-none space-y-1 pl-0" {...p} />,
                        li: p => <li className="flex gap-2 text-sm before:content-['·'] before:text-indigo-400 before:font-bold" {...p} />,
                    }}>
                        {msg.content}
                    </ReactMarkdown>
                </div>
            )}

            {msg.isStreaming && !msg.content && (
                <div className="flex items-center gap-2 text-sm text-slate-400">
                    <TypingDots /> <span>Thinking…</span>
                </div>
            )}

            {msg.type === "follow_up" && msg.data && (
                <FollowUpCard
                    question={msg.data.question ?? msg.content}
                    missingSlots={msg.data.missing_slots ?? []}
                    onResponse={a => handleSend(a)}
                />
            )}

            {(msg.type === "draft_voucher" || msg.type === "card") && msg.data && (
                <button onClick={() => setShowStage(true)}
                    className="mt-1 inline-flex items-center gap-2 text-xs text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded-full border border-indigo-200 hover:bg-indigo-100 transition-colors">
                    <ReceiptText className="h-3 w-3" />
                    View in Artifacts panel
                    <ArrowRight className="h-3 w-3" />
                </button>
            )}
        </div>
    );

    // ─────────────────────────────────────────────────────────────────────────
    return (
        <div className="flex h-screen overflow-hidden bg-[#F8F9FC]">

            {/* ═══════════════════════════════════════════════
                CENTRE — Chat Area
             ═══════════════════════════════════════════════ */}
            <div className={`flex flex-col flex-1 min-w-0 transition-[margin-right] duration-300 ${showStage ? "mr-[380px]" : ""}`}>

                {/* Top bar */}
                <div className="h-11 px-4 flex items-center justify-between border-b border-slate-200/70 bg-white/80 backdrop-blur-sm shrink-0">
                    <div className="flex items-center gap-2.5">
                        <div className="h-6 w-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm">
                            <Sparkles className="h-3.5 w-3.5 text-white" />
                        </div>
                        <span className="text-sm font-semibold text-slate-700">KITTU</span>
                        <Badge variant="outline" className="text-[9px] h-4 px-1.5 border-indigo-200 text-indigo-600 bg-indigo-50 font-semibold tracking-wide">
                            AI
                        </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                        <button onClick={handleNewChat}
                            className="inline-flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-indigo-600 px-2.5 py-1 rounded-lg hover:bg-indigo-50 transition-colors font-medium">
                            <Plus className="h-3.5 w-3.5" /> New chat
                        </button>
                        {artifacts.length > 0 && (
                            <Badge className="bg-indigo-100 text-indigo-700 text-[10px] h-5 px-2 border-0">
                                {artifacts.length} artifact{artifacts.length > 1 ? "s" : ""}
                            </Badge>
                        )}
                        <button onClick={() => setShowStage(s => !s)}
                            className="h-7 w-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                            title={showStage ? "Hide artifacts" : "Show artifacts"}>
                            {showStage
                                ? <PanelRightClose className="h-4 w-4" />
                                : <PanelRight className="h-4 w-4" />}
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto">
                    {messages.length === 0 ? (
                        <EmptyState onSuggestion={s => handleSend(s)} userName={firstName} />
                    ) : (
                        <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
                            {messages.map(msg => (
                                <div key={msg.id}
                                    className={`flex gap-3 group ${msg.role === "user" ? "justify-end" : "justify-start"}`}>

                                    {msg.role === "assistant" && (
                                        <div className="shrink-0 mt-0.5 h-7 w-7 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm shadow-indigo-200">
                                            <Sparkles className="h-3.5 w-3.5 text-white" />
                                        </div>
                                    )}

                                    <div className={`flex flex-col max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                                        {msg.role === "user" ? (
                                            <div className="bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-md text-sm leading-relaxed shadow-sm shadow-indigo-200">
                                                {msg.content}
                                            </div>
                                        ) : (
                                            <div className="bg-white border border-slate-200/80 px-4 py-3 rounded-2xl rounded-tl-md shadow-sm w-full">
                                                {renderAssistant(msg)}
                                            </div>
                                        )}

                                        <div className={`flex items-center gap-2 mt-1.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                                            <span className="text-[10px] text-slate-400">{fmtTime(msg.timestamp)}</span>
                                            {msg.role === "assistant" && msg.content && !msg.isStreaming && (
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={() => handleCopy(msg.id, msg.content)}
                                                        className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                                                        {copied === msg.id
                                                            ? <Check className="h-3 w-3 text-emerald-500" />
                                                            : <Copy className="h-3 w-3" />}
                                                    </button>
                                                    <button className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                                                        <ThumbsUp className="h-3 w-3" />
                                                    </button>
                                                    <button className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                                                        <ThumbsDown className="h-3 w-3" />
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {msg.role === "user" && (
                                        <Avatar className="h-7 w-7 shrink-0 mt-0.5">
                                            <AvatarFallback className="bg-slate-200 text-slate-600 text-[10px] font-bold rounded-xl">
                                                {user?.full_name
                                                    ? user.full_name.split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase()
                                                    : "ME"}
                                            </AvatarFallback>
                                        </Avatar>
                                    )}
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Command Input */}
                <div className="shrink-0 px-4 pb-4 pt-2">
                    <div className="max-w-2xl mx-auto">
                        {showSlash && (
                            <div className="mb-2 bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">
                                <div className="px-3 pt-2.5 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">Commands</div>
                                {SLASH_COMMANDS.filter(c => c.cmd.startsWith(input)).map(c => (
                                    <button key={c.cmd}
                                        onClick={() => { setInput(c.cmd + " "); inputRef.current?.focus(); setShowSlash(false); }}
                                        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 transition-colors text-left">
                                        <div className="h-7 w-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">{c.icon}</div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-700">{c.cmd}</p>
                                            <p className="text-xs text-slate-400">{c.desc}</p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}

                        <div className="relative bg-white border border-slate-200 rounded-2xl shadow-lg focus-within:border-indigo-300 focus-within:shadow-xl focus-within:shadow-indigo-100/50 transition-all duration-200 overflow-hidden">
                            <div className="flex items-center gap-1 px-3 pt-2.5 pb-1">
                                <button onClick={() => { setInput("/"); inputRef.current?.focus(); }}
                                    className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-600 px-1.5 py-0.5 rounded-md hover:bg-indigo-50 transition-colors">
                                    <Hash className="h-3 w-3" /> Commands
                                </button>
                                <button onClick={handleNewChat}
                                    className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-600 px-1.5 py-0.5 rounded-md hover:bg-slate-100 transition-colors">
                                    <Plus className="h-3 w-3" /> New thread
                                </button>
                            </div>

                            <textarea
                                ref={inputRef}
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask KITTU anything about your finances… (/ for commands)"
                                disabled={loading}
                                rows={1}
                                className="w-full resize-none px-4 pb-3 text-sm text-slate-800 placeholder:text-slate-400 bg-transparent focus:outline-none disabled:opacity-50 leading-relaxed"
                                style={{ maxHeight: "120px", overflowY: "auto" }}
                                onInput={e => {
                                    const t = e.target as HTMLTextAreaElement;
                                    t.style.height = "auto";
                                    t.style.height = Math.min(t.scrollHeight, 120) + "px";
                                }}
                            />

                            <div className="flex items-center justify-between px-3 pb-2.5">
                                <div className="flex items-center gap-1.5">
                                    <Clock className="h-3 w-3 text-slate-300" />
                                    <span className="text-[10px] text-slate-300">⏎ send · ⇧⏎ newline</span>
                                </div>
                                <Button size="icon" onClick={() => handleSend()} disabled={!input.trim() || loading}
                                    className={`h-8 w-8 rounded-xl transition-all duration-200 ${input.trim() && !loading
                                        ? "bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-200"
                                        : "bg-slate-200 text-slate-400"
                                        }`}>
                                    {loading
                                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        : <Send className="h-3.5 w-3.5" />}
                                </Button>
                            </div>
                        </div>

                        <p className="text-center mt-2 text-[10px] text-slate-400">
                            KITTU uses AI — double-check important financial data.
                        </p>
                    </div>
                </div>
            </div>

            {/* ═══════════════════════════════════════════════
                RIGHT — Artifacts Stage (slide-in panel)
             ═══════════════════════════════════════════════ */}
            <div className={`fixed top-11 right-0 h-[calc(100vh-2.75rem)] w-[380px] bg-white border-l border-slate-200 flex flex-col shadow-2xl shadow-slate-900/5 transition-transform duration-300 ease-out z-20 ${showStage ? "translate-x-0" : "translate-x-full"
                }`}>
                <div className="h-11 px-4 flex items-center justify-between border-b border-slate-100 shrink-0">
                    <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded-md bg-violet-100 flex items-center justify-center">
                            <FileText className="h-3 w-3 text-violet-600" />
                        </div>
                        <span className="text-sm font-semibold text-slate-700">Artifacts</span>
                        {artifacts.length > 0 && (
                            <span className="text-[10px] text-slate-400">{artifacts.length} item{artifacts.length > 1 ? "s" : ""}</span>
                        )}
                    </div>
                    <button onClick={() => setShowStage(false)}
                        className="h-7 w-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {artifacts.length > 0 && (
                    <div className="flex gap-1 px-3 pt-2 overflow-x-auto shrink-0">
                        {artifacts.map(a => (
                            <button key={a.id} onClick={() => setActiveArt(a.id)}
                                className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-colors ${activeArt === a.id
                                    ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                                    : "text-slate-500 hover:bg-slate-100"
                                    }`}>
                                {a.icon} {a.label}
                            </button>
                        ))}
                    </div>
                )}

                <div className="flex-1 overflow-y-auto p-4">
                    {artifacts.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center gap-4">
                            <div className="h-16 w-16 rounded-2xl bg-slate-50 border-2 border-dashed border-slate-200 flex items-center justify-center">
                                <FileText className="h-7 w-7 text-slate-300" />
                            </div>
                            <div>
                                <p className="text-sm font-medium text-slate-500">No artifacts yet</p>
                                <p className="text-xs text-slate-400 mt-1 max-w-[200px]">
                                    Drafts, tables, and reports KITTU creates will appear here.
                                </p>
                            </div>
                        </div>
                    ) : (
                        artifacts
                            .filter(a => a.id === (activeArt ?? artifacts[0]?.id))
                            .map(a => <div key={a.id}>{a.content}</div>)
                    )}
                </div>
            </div>

            <style>{`@keyframes kbounce {
                0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
                40%           { transform: scale(1.0); opacity: 1.0; }
            }`}</style>
        </div>
    );
}
