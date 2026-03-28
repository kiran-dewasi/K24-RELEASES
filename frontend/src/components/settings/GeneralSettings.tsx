"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useUser } from "@/contexts/UserContext";
import { apiRequest } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

/** Extract initials from a full name */
function getInitials(name: string | undefined | null): string {
    if (!name) return "??";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
}

export function GeneralSettings() {
    const { user, loading, error, refreshUser } = useUser();
    const { toast } = useToast();
    const [fullName, setFullName] = useState("");
    const [mobile, setMobile] = useState("");
    const [saving, setSaving] = useState(false);

    // Business (Tenant) WhatsApp state
    const [businessWhatsappNumber, setBusinessWhatsappNumber] = useState("");
    const [savingBusiness, setSavingBusiness] = useState(false);

    // Sync controlled inputs when user data loads
    useEffect(() => {
        if (user) {
            setFullName(user.full_name || "");
            setMobile(user.whatsapp_number || "");
        }
    }, [user]);

    // Attempt to pre-fill business whatsapp number if read endpoint exists
    useEffect(() => {
        const fetchTenantConfig = async () => {
            try {
                const data = await apiRequest("/api/tenant/whatsapp-config", "GET");
                if (data && data.whatsapp_number) {
                    setBusinessWhatsappNumber(data.whatsapp_number);
                }
            } catch (err) {
                // Read endpoint might not exist yet, skip silently
            }
        };
        if (user && (user.role === "owner" || user.role === "admin")) {
            fetchTenantConfig();
        }
    }, [user]);

    const [saveSuccess, setSaveSuccess] = useState(false);

    const handleSave = async () => {
        try {
            setSaving(true);
            setSaveSuccess(false);

            // Verify token exists before trying
            const token = typeof window !== "undefined" ? localStorage.getItem("k24_token") : null;
            if (!token) {
                toast({
                    title: "Session expired",
                    description: "Please log in again to save changes.",
                    variant: "destructive",
                });
                setTimeout(() => { window.location.href = "/login"; }, 1500);
                return;
            }

            await apiRequest("/api/auth/profile", "PUT", {
                full_name: fullName,
                whatsapp_number: mobile,
            });

            await refreshUser();
            setSaveSuccess(true);
            toast({ title: "✓ Saved", description: "Your profile has been updated." });
            setTimeout(() => setSaveSuccess(false), 2500);

        } catch (err: any) {
            const msg: string = err?.message || "Failed to save settings";
            const isExpired = msg.toLowerCase().includes("unauthorized") || msg.includes("401");

            if (isExpired) {
                toast({
                    title: "Session expired",
                    description: "Your session has expired. Redirecting to login…",
                    variant: "destructive",
                });
                localStorage.removeItem("k24_token");
                localStorage.removeItem("k24_user");
                setTimeout(() => { window.location.href = "/login"; }, 1800);
            } else {
                toast({ title: "Error saving", description: msg, variant: "destructive" });
            }
        } finally {
            setSaving(false);
        }
    };

    const handleSaveBusinessConfig = async () => {
        try {
            setSavingBusiness(true);
            const token = typeof window !== "undefined" ? localStorage.getItem("k24_token") : null;
            if (!token) {
                toast({
                    title: "Session expired",
                    description: "Please log in again to save changes.",
                    variant: "destructive",
                });
                setTimeout(() => { window.location.href = "/login"; }, 1500);
                return;
            }

            await apiRequest("/api/tenant/whatsapp-config", "PUT", {
                whatsapp_number: businessWhatsappNumber,
                is_active: true,
            });

            toast({ title: "✓ Saved", description: "WhatsApp bot configuration updated." });
        } catch (err: any) {
            toast({
                title: "Error saving config",
                description: "Failed to save WhatsApp config: " + (err?.message || "Unknown error"),
                variant: "destructive",
            });
        } finally {
            setSavingBusiness(false);
        }
    };


    const handleCancel = () => {
        if (user) {
            setFullName(user.full_name || "");
            setMobile(user.whatsapp_number || "");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading profile…</span>
            </div>
        );
    }

    if (error && !user) {
        return (
            <div className="flex items-center justify-center py-20">
                <p className="text-sm text-destructive">{error}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Profile Details</CardTitle>
                    <CardDescription>Manage your personal information and preferences.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="flex items-center gap-6">
                        {/* Avatar — use initials fallback, no broken image src */}
                        <Avatar className="h-20 w-20">
                            <AvatarFallback className="text-xl bg-primary/10 text-primary">
                                {getInitials(fullName || user?.full_name)}
                            </AvatarFallback>
                        </Avatar>
                        <div className="space-y-1">
                            <p className="text-sm text-muted-foreground">Profile photo</p>
                            <Button variant="outline" size="sm" disabled title="Avatar upload coming soon">
                                Change Avatar
                            </Button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Full Name</Label>
                            <Input
                                id="name"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="Your full name"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input id="email" value={user?.email || ""} disabled />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="role">Role</Label>
                            <Input id="role" value={user?.role || ""} disabled className="bg-muted" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="mobile">Mobile / WhatsApp Number</Label>
                            <Input
                                id="mobile"
                                value={mobile}
                                onChange={(e) => setMobile(e.target.value)}
                                placeholder="+91 98765 43210"
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={handleCancel} disabled={saving}>
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    disabled={saving}
                    className={saveSuccess ? "bg-emerald-600 hover:bg-emerald-700 text-white transition-colors" : ""}
                >
                    {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {saving ? "Saving…" : saveSuccess ? "✓ Saved!" : "Save Changes"}
                </Button>
            </div>

            {user && (user.role === "owner" || user.role === "admin") && (
                <Card className="mt-8 border-l-4 border-l-blue-500">
                    <CardHeader>
                        <CardTitle>WhatsApp Bot Configuration</CardTitle>
                        <CardDescription>
                            Set the tenant-level Business WhatsApp Number that receives bot interactions and routes Tally data.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2 max-w-md">
                            <Label htmlFor="businessMobile">Business WhatsApp Number (Bot)</Label>
                            <Input
                                id="businessMobile"
                                value={businessWhatsappNumber}
                                onChange={(e) => setBusinessWhatsappNumber(e.target.value)}
                                placeholder="+91 98765 43210"
                            />
                        </div>
                        <Button
                            onClick={handleSaveBusinessConfig}
                            disabled={savingBusiness || !businessWhatsappNumber.trim()}
                        >
                            {savingBusiness && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {savingBusiness ? "Saving…" : "Save WhatsApp Config"}
                        </Button>
                    </CardContent>
                </Card>
            )}

        </div>
    );
}
