"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useUser } from "@/contexts/UserContext";
import { Loader2 } from "lucide-react";

/** Extract initials from a full name */
function getInitials(name: string | undefined | null): string {
    if (!name) return "??";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
}

export function GeneralSettings() {
    const { user, loading, error } = useUser();

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
                        <Avatar className="h-20 w-20">
                            <AvatarImage src="/avatars/01.png" alt={user?.username || "user"} />
                            <AvatarFallback className="text-xl bg-primary/10 text-primary">
                                {getInitials(user?.full_name)}
                            </AvatarFallback>
                        </Avatar>
                        <Button variant="outline" size="sm">Change Avatar</Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Full Name</Label>
                            <Input id="name" defaultValue={user?.full_name || ""} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input id="email" defaultValue={user?.email || ""} disabled />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="role">Role</Label>
                            <Input id="role" defaultValue={user?.role || ""} disabled className="bg-muted" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="mobile">Mobile Number</Label>
                            <Input id="mobile" defaultValue={user?.whatsapp_number || ""} />
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-end gap-2">
                <Button variant="ghost">Cancel</Button>
                <Button>Save Changes</Button>
            </div>
        </div>
    );
}
