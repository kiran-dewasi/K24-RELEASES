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

    // Sync controlled inputs when user data loads
    useEffect(() => {
        if (user) {
            setFullName(user.full_name || "");
            setMobile(user.whatsapp_number || "");
        }
    }, [user]);

    const handleSave = async () => {
        try {
            setSaving(true);
            await apiRequest("/api/auth/profile", "PUT", {
                full_name: fullName,
                whatsapp_number: mobile,
            });
            await refreshUser(); // refresh UserContext so Sidebar/Navbar reflect new name
            toast({ title: "Settings saved", description: "Your profile has been updated." });
        } catch (err: any) {
            console.error("Failed to save profile:", err);
            toast({ title: "Error", description: err?.message || "Failed to save settings", variant: "destructive" });
        } finally {
            setSaving(false);
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
                <Button onClick={handleSave} disabled={saving}>
                    {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {saving ? "Saving…" : "Save Changes"}
                </Button>
            </div>
        </div>
    );
}
