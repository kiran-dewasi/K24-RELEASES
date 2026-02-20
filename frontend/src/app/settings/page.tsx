"use client";

import { useState } from "react";
import {
    Settings,
    MessageSquare,
    Shield,
    CreditCard,
    User,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { GeneralSettings } from "@/components/settings/GeneralSettings";
import { WhatsAppSettings } from "@/components/settings/WhatsAppSettings";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";


export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState("general");

    const menuItems: {
        category: string;
        items: { id: string; label: string; icon: React.ElementType; component?: React.ComponentType; disabled?: boolean }[];
    }[] = [
            {
                category: "General",
                items: [
                    { id: "general", label: "Preferences", icon: Settings, component: GeneralSettings },
                    { id: "account", label: "Account", icon: User, disabled: true },
                ]
            },
            {
                category: "Integrations",
                items: [
                    { id: "whatsapp", label: "WhatsApp", icon: MessageSquare, component: WhatsAppSettings },
                ]
            },
            {
                category: "System",
                items: [
                    { id: "billing", label: "Billing & Plans", icon: CreditCard, disabled: true },
                    { id: "security", label: "Security", icon: Shield, disabled: true },
                ]
            }
        ];


    const ActiveComponent = menuItems
        .flatMap(cat => cat.items)
        .find(item => item.id === activeTab)?.component || GeneralSettings;

    return (
        <div className="flex flex-col h-[calc(100vh-100px)] max-w-[1600px] mx-auto pb-6">
            <div className="flex flex-col gap-2 mb-8 px-1">
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground text-lg">Manage your workspace preferences and integrations.</p>
            </div>

            <div className="flex flex-1 flex-col md:flex-row gap-8">
                {/* Sidebar */}
                <aside className="w-full md:w-64 flex-shrink-0 space-y-8">
                    {menuItems.map((group, groupIndex) => (
                        <div key={groupIndex} className="space-y-3">
                            <h4 className="px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                                {group.category}
                            </h4>
                            <div className="space-y-1">
                                {group.items.map((item) => (
                                    <Button
                                        key={item.id}
                                        variant="ghost"
                                        disabled={item.disabled}
                                        onClick={() => !item.disabled && setActiveTab(item.id)}
                                        className={cn(
                                            "w-full justify-start gap-3 px-3 py-6 md:py-4 h-auto text-base font-medium transition-all hover:pl-4",
                                            activeTab === item.id
                                                ? "bg-secondary/80 text-primary shadow-sm border-l-4 border-l-primary rounded-l-none rounded-r-md"
                                                : "text-muted-foreground hover:text-foreground hover:bg-transparent"
                                        )}
                                    >
                                        <item.icon className={cn("h-5 w-5", activeTab === item.id ? "text-primary" : "text-muted-foreground")} />
                                        {item.label}
                                        {item.disabled && <span className="ml-auto text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">Soon</span>}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    ))}
                </aside>

                {/* Content Area */}
                <main className="flex-1 overflow-y-auto pr-2 min-h-[500px]">
                    <div className="animate-in fade-in-50 slide-in-from-right-4 duration-500 ease-out">
                        {/* We wrap mostly in Card logic inside components, but here we provide a container */}
                        <ActiveComponent />
                    </div>
                </main>
            </div>
        </div>
    );
}
