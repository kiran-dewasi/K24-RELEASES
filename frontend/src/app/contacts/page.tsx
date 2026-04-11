"use client";

import { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Phone, Mail, FileText, User, Briefcase, Plus, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Contact {
    id: number;
    name: string;
    group: string;
    type: string; // Customer, Supplier, Other
    phone: string | null;
    email: string | null;
    gstin: string | null;
    total_sales: number;
    total_purchases: number;
    outstanding: number;
    last_transaction: string | null;
}

export default function ContactsPage() {
    const router = useRouter();
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [selectedContact, setSelectedContact] = useState<Contact | null>(null);

    useEffect(() => {
        fetchContacts();
    }, []);

    const fetchContacts = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem("k24_token");
            const headers: Record<string, string> = { "x-api-key": "k24-secret-key-123" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const data = await apiRequest(`/contacts/detailed`);
            setContacts(data);
            if (data.length > 0) {
                setSelectedContact(data[0]);
            }
        } catch (error) {
            console.error("Error fetching contacts", error);
        } finally {
            setLoading(false);
        }
    };

    const filteredContacts = contacts.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        (c.email && c.email.toLowerCase().includes(search.toLowerCase()))
    );

    const formatCurrency = (amount: number) => {
        return `₹${Math.abs(amount).toLocaleString('en-IN')}`;
    };

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (contacts.length === 0) {
        return (
            <div className="flex bg-gray-50 h-screen items-center justify-center p-4">
                <Card className="max-w-md w-full text-center p-8">
                    <div className="flex justify-center mb-4">
                        <div className="bg-blue-100 p-4 rounded-full">
                            <User className="h-8 w-8 text-blue-600" />
                        </div>
                    </div>
                    <h2 className="text-2xl font-bold mb-2">No contacts yet</h2>
                    <p className="text-muted-foreground mb-6">
                        Sync your data from Tally via the Agent, or add contacts manually to get started.
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Button variant="outline" onClick={fetchContacts}>Refresh</Button>
                        <Button className="bg-blue-600 hover:bg-blue-700">
                            Run Tally Sync
                        </Button>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-gray-50 overflow-hidden">
            {/* Left Column: List */}
            <div className="w-1/3 border-r bg-white flex flex-col z-10 shadow-sm max-w-md">
                <div className="p-4 border-b space-y-4">
                    <div className="flex justify-between items-center">
                        <h1 className="text-xl font-bold">Contacts</h1>
                        <Button size="sm" variant="outline" className="h-8 w-8 p-0">
                            <Plus className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
                        <Input
                            placeholder="Search contacts..."
                            className="pl-9"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {filteredContacts.map(contact => (
                        <div
                            key={contact.id}
                            onClick={() => setSelectedContact(contact)}
                            className={`p-4 border-b cursor-pointer hover:bg-gray-50 transition-colors ${selectedContact?.id === contact.id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''}`}
                        >
                            <div className="flex justify-between items-start mb-1">
                                <h3 className={`font-medium ${selectedContact?.id === contact.id ? 'text-blue-700' : 'text-gray-900'}`}>
                                    {contact.name}
                                </h3>
                                {contact.type === 'Customer' && <Badge variant="outline" className="text-green-600 border-green-200">Cust</Badge>}
                                {contact.type === 'Supplier' && <Badge variant="outline" className="text-amber-600 border-amber-200">Supp</Badge>}
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground truncate max-w-[120px]">{contact.group}</span>
                                <span className={contact.outstanding > 0 ? "text-green-600 font-medium" : contact.outstanding < 0 ? "text-red-600 font-medium" : "text-gray-500"}>
                                    {contact.outstanding > 0 ? "Rx: " : contact.outstanding < 0 ? "Py: " : ""}
                                    {formatCurrency(contact.outstanding)}
                                </span>
                            </div>
                        </div>
                    ))}

                    {filteredContacts.length === 0 && (
                        <div className="p-8 text-center text-muted-foreground">
                            No matching contacts found.
                        </div>
                    )}
                </div>
            </div>

            {/* Right Column: Details */}
            <div className="flex-1 overflow-y-auto p-8">
                {selectedContact ? (
                    <div className="max-w-4xl mx-auto space-y-6">
                        {/* Header */}
                        <div className="flex justify-between items-start">
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold text-xl">
                                        {selectedContact.name.charAt(0)}
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold">{selectedContact.name}</h2>
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <Briefcase className="h-4 w-4" />
                                            <span>{selectedContact.group}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    variant="default"
                                    className="bg-blue-600 hover:bg-blue-700"
                                    onClick={() => router.push(`/customers?id=${selectedContact.id}`)}
                                >
                                    <ExternalLink className="mr-2 h-4 w-4" />
                                    View 360° Profile
                                </Button>
                                <Button variant="outline">
                                    <Phone className="mr-2 h-4 w-4" />
                                    Call
                                </Button>
                                <Button className="bg-green-600 hover:bg-green-700">
                                    <MessageCircleIcon className="mr-2 h-4 w-4" />
                                    WhatsApp
                                </Button>
                            </div>
                        </div>

                        {/* Quick Stats Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Card>
                                <CardContent className="p-4 pt-6">
                                    <p className="text-sm font-medium text-muted-foreground mb-1">Total Sales</p>
                                    <p className="text-xl font-bold text-blue-600">{formatCurrency(selectedContact.total_sales)}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 pt-6">
                                    <p className="text-sm font-medium text-muted-foreground mb-1">Total Purchases</p>
                                    <p className="text-xl font-bold text-amber-600">{formatCurrency(selectedContact.total_purchases)}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 pt-6">
                                    <p className="text-sm font-medium text-muted-foreground mb-1">Current Balance</p>
                                    <p className={`text-xl font-bold ${selectedContact.outstanding >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {formatCurrency(selectedContact.outstanding)} {selectedContact.outstanding >= 0 ? "Dr" : "Cr"}
                                    </p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 pt-6">
                                    <p className="text-sm font-medium text-muted-foreground mb-1">Last Activity</p>
                                    <div className="flex flex-col">
                                        <span className="font-bold">
                                            {selectedContact.last_transaction ? new Date(selectedContact.last_transaction).toLocaleDateString() : "Never"}
                                        </span>
                                        {selectedContact.last_transaction && (
                                            <span className="text-xs text-muted-foreground">Last Txn</span>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Contact Details Card */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Contact Information</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                        <label className="text-sm text-muted-foreground">Email Address</label>
                                        <div className="flex items-center gap-2">
                                            <Mail className="h-4 w-4 text-gray-400" />
                                            <span className="font-medium">{selectedContact.email || "—"}</span>
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-sm text-muted-foreground">Phone Number</label>
                                        <div className="flex items-center gap-2">
                                            <Phone className="h-4 w-4 text-gray-400" />
                                            <span className="font-medium">{selectedContact.phone || "—"}</span>
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-sm text-muted-foreground">GSTIN</label>
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-4 w-4 text-gray-400" />
                                            <span className="font-medium">{selectedContact.gstin || "—"}</span>
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Recent Activity Placeholder */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Recent Transactions</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-center py-8 text-muted-foreground text-sm">
                                    Transaction history will appear here once you start syncing detailed vouchers.
                                </div>
                            </CardContent>
                        </Card>

                    </div>
                ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                        Select a contact to view details
                    </div>
                )}
            </div>
        </div>
    );
}

function MessageCircleIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
    )
}
