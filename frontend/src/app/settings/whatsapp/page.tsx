"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Phone, User, Hash, FileText, Search, Loader2, Bot, CheckCircle, AlertCircle, Save } from "lucide-react";
import { api } from "@/lib/api";

interface CustomerMapping {
    id: string;
    customer_name: string;
    customer_phone: string;
    client_code?: string;
    notes?: string;
    is_active: number;
}

interface AddCustomerFormProps {
    onSubmit: (data: any) => Promise<void>;
    onCancel: () => void;
    isLoading: boolean;
}

function AddCustomerForm({ onSubmit, onCancel, isLoading }: AddCustomerFormProps) {
    const [formData, setFormData] = useState({
        customer_name: "",
        customer_phone: "",
        client_code: "",
        notes: ""
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        await onSubmit(formData);
    };

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
                <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <User size={24} /> New Customer Registration
                    </h2>
                    <p className="text-blue-100 text-sm mt-1">
                        Map a phone number to a customer for WhatsApp routing.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Customer Name *</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input
                                required
                                type="text"
                                placeholder="e.g. Acme Corp"
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                                value={formData.customer_name}
                                onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
                        <div className="relative">
                            <Phone className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input
                                required
                                type="text"
                                placeholder="+91 98765 43210"
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all font-mono"
                                value={formData.customer_phone}
                                onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">Format: +91XXXXXXXXXX</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Client Code</label>
                            <div className="relative">
                                <Hash className="absolute left-3 top-3 text-gray-400" size={18} />
                                <input
                                    type="text"
                                    placeholder="OPTIONAL"
                                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all uppercase"
                                    value={formData.client_code}
                                    onChange={(e) => setFormData({ ...formData, client_code: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                        <div className="relative">
                            <FileText className="absolute left-3 top-3 text-gray-400" size={18} />
                            <textarea
                                rows={2}
                                placeholder="Additional notes..."
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all resize-none"
                                value={formData.notes}
                                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                            disabled={isLoading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                        >
                            {isLoading ? <Loader2 className="animate-spin" size={18} /> : null}
                            {isLoading ? "Saving..." : "Save Mapping"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// ─── Bot Number Card ─────────────────────────────────────────────
function BotNumberCard() {
    const [botNumber, setBotNumber] = useState("");
    const [savedNumber, setSavedNumber] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
    const [errorMsg, setErrorMsg] = useState("");

    useEffect(() => {
        fetchBotNumber();
    }, []);

    const fetchBotNumber = async () => {
        setLoading(true);
        try {
            const res = await api.get("/api/whatsapp/bot-number");
            if (res.ok) {
                const data = await res.json();
                if (data.whatsapp_number) {
                    setBotNumber(data.whatsapp_number);
                    setSavedNumber(data.whatsapp_number);
                }
            }
        } catch (e) {
            console.error("Failed to fetch bot number:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!botNumber.trim()) return;
        setSaving(true);
        setStatus("idle");
        setErrorMsg("");
        try {
            const res = await api.put("/api/whatsapp/bot-number", { whatsapp_number: botNumber.trim()
            });
            if (res.ok) {
                const data = await res.json();
                setSavedNumber(data.whatsapp_number);
                setBotNumber(data.whatsapp_number);
                setStatus("success");
                setTimeout(() => setStatus("idle"), 3000);
            } else {
                const err = await res.json();
                setErrorMsg(err.detail || "Failed to save");
                setStatus("error");
            }
        } catch (e) {
            setErrorMsg("Network error. Please try again.");
            setStatus("error");
        } finally {
            setSaving(false);
        }
    };

    const isDirty = botNumber !== savedNumber;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-4">
                <div className="flex items-center gap-3 text-white">
                    <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                        <Bot size={22} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold">Your WhatsApp Bot Number</h2>
                        <p className="text-green-100 text-sm">
                            The number customers message to reach your AI assistant.
                        </p>
                    </div>
                </div>
            </div>

            <div className="p-6">
                {loading ? (
                    <div className="flex items-center gap-3 text-gray-400">
                        <Loader2 className="animate-spin" size={18} />
                        <span className="text-sm">Loading current number...</span>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                Bot Phone Number
                            </label>
                            <div className="flex gap-3">
                                <div className="relative flex-1">
                                    <Phone className="absolute left-3 top-3 text-gray-400" size={18} />
                                    <input
                                        type="text"
                                        placeholder="+91XXXXXXXXXX"
                                        value={botNumber}
                                        onChange={(e) => { setBotNumber(e.target.value); setStatus("idle"); }}
                                        className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-all"
                                    />
                                </div>
                                <button
                                    onClick={handleSave}
                                    disabled={saving || !isDirty || !botNumber.trim()}
                                    className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-sm"
                                >
                                    {saving
                                        ? <><Loader2 className="animate-spin" size={16} /> Saving...</>
                                        : <><Save size={16} /> Save</>
                                    }
                                </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-1.5">
                                Format: +91XXXXXXXXXX — Changes apply immediately in the cloud.
                            </p>
                        </div>

                        {status === "success" && (
                            <div className="flex items-center gap-2 text-green-600 text-sm bg-green-50 border border-green-200 rounded-lg px-4 py-2.5">
                                <CheckCircle size={16} />
                                <span>Bot number updated successfully! Cloud routing is live.</span>
                            </div>
                        )}
                        {status === "error" && (
                            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
                                <AlertCircle size={16} />
                                <span>{errorMsg}</span>
                            </div>
                        )}

                        {savedNumber && status === "idle" && (
                            <div className="flex items-center gap-2 text-gray-500 text-xs">
                                <CheckCircle size={13} className="text-green-500" />
                                <span>Currently registered: <span className="font-mono font-medium text-gray-700">{savedNumber}</span></span>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
// ─────────────────────────────────────────────────────────────────

export default function WhatsAppSettingsPage() {
    const [mappings, setMappings] = useState<CustomerMapping[]>([]);
    const [showAddForm, setShowAddForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        fetchMappings();
    }, []);

    const fetchMappings = async () => {
        try {
            const res = await api.get('/api/whatsapp/customers');
            if (res.ok) {
                const data = await res.json();
                setMappings(data.mappings || []);
            }
        } catch (error) {
            console.error("Failed to fetch mappings:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (formData: any) => {
        setSubmitting(true);
        try {
            const res = await api.post('/api/whatsapp/customers', formData);

            if (res.ok) {
                setShowAddForm(false);
                fetchMappings();
            } else {
                const err = await res.json();
                alert(err.detail || "Failed to add customer");
            }
        } catch (error) {
            alert("Error submitting form");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to remove this customer mapping?')) return;

        setMappings(prev => prev.filter(m => m.id !== id));

        try {
            await api.delete(`/api/whatsapp/customers/${id}`);
        } catch (error) {
            alert("Failed to delete");
            fetchMappings();
        }
    };

    const filteredMappings = mappings.filter(m =>
        m.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        m.customer_phone.includes(searchTerm)
    );

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">
            {/* Bot Number Card — register your bot number here */}
            <BotNumberCard />

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-2">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 tracking-tight">WhatsApp Customers</h1>
                    <p className="text-gray-500 mt-1">
                        Register phone numbers to automatically route WhatsApp messages to customers.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddForm(true)}
                    className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2.5 rounded-lg hover:shadow-lg hover:scale-105 transition-all duration-200 font-medium"
                >
                    <Plus size={20} />
                    Add Customer Phone
                </button>
            </div>

            {/* Search Bar */}
            {mappings.length > 0 && (
                <div className="relative max-w-md">
                    <Search className="absolute left-3 top-3 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search by name or phone..."
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all bg-white shadow-sm"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            )}

            {/* Add Form Modal */}
            {showAddForm && (
                <AddCustomerForm
                    onSubmit={handleAdd}
                    onCancel={() => setShowAddForm(false)}
                    isLoading={submitting}
                />
            )}

            {/* Mappings List */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                    <Loader2 className="animate-spin mb-4" size={40} />
                    <p>Loading customers...</p>
                </div>
            ) : mappings.length === 0 ? (
                <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center">
                    <div className="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Phone size={32} />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">No customers registered yet</h3>
                    <p className="text-gray-500 mb-6 max-w-md mx-auto">
                        Add your first customer phone number to start the automated WhatsApp routing engine.
                    </p>
                    <button
                        onClick={() => setShowAddForm(true)}
                        className="text-blue-600 font-medium hover:underline"
                    >
                        Register a phone number now &rarr;
                    </button>
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-gray-50/50 border-b border-gray-100">
                            <tr>
                                <th className="p-4 font-semibold text-gray-600 text-sm">Customer Name</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm">Phone Number</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm">Client Code</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm">Notes</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredMappings.map((mapping) => (
                                <tr key={mapping.id} className="hover:bg-blue-50/30 transition-colors group">
                                    <td className="p-4 font-medium text-gray-900">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                                                {mapping.customer_name.charAt(0).toUpperCase()}
                                            </div>
                                            {mapping.customer_name}
                                        </div>
                                    </td>
                                    <td className="p-4 text-gray-600 font-mono text-sm">{mapping.customer_phone}</td>
                                    <td className="p-4">
                                        {mapping.client_code ? (
                                            <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-medium border border-gray-200">
                                                {mapping.client_code}
                                            </span>
                                        ) : (
                                            <span className="text-gray-300 text-sm">-</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-gray-500 text-sm max-w-xs truncate">
                                        {mapping.notes || "-"}
                                    </td>
                                    <td className="p-4 text-right">
                                        <button
                                            onClick={() => handleDelete(mapping.id)}
                                            className="text-gray-400 hover:text-red-600 p-2 hover:bg-red-50 rounded transition-all opacity-0 group-hover:opacity-100"
                                            title="Delete Mapping"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {filteredMappings.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-gray-500">
                                        No matching customers found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
