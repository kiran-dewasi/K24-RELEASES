"use client";

import { CheckCircle2, Circle } from "lucide-react";

const events = [
    { date: "Today", title: "TDS Payment", desc: "For Contractors (94C)", status: "pending" },
    { date: "Nov 11", title: "GSTR-1 Due", desc: "Monthly Return", status: "upcoming" },
    { date: "Nov 20", title: "GSTR-3B Due", desc: "Summary Return", status: "upcoming" },
    { date: "Nov 30", title: "Advance Tax", desc: "Installment 3", status: "upcoming" },
];

export function ComplianceTimeline() {
    return (
        <div className="space-y-6">
            <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider mb-4">Upcoming Timeline</h3>
            <div className="relative border-l border-muted ml-3 space-y-8">
                {events.map((event, i) => (
                    <div key={i} className="relative pl-8">
                        {/* Dot */}
                        <div className={`absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background 
                            ${event.status === 'pending' ? 'bg-amber-500' : 'bg-muted-foreground/30'}`}
                        />

                        <div className="flex flex-col">
                            <span className={`text-xs font-bold ${event.date === 'Today' ? 'text-amber-600' : 'text-muted-foreground'}`}>{event.date}</span>
                            <span className="text-sm font-medium mt-0.5">{event.title}</span>
                            <span className="text-xs text-muted-foreground">{event.desc}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
