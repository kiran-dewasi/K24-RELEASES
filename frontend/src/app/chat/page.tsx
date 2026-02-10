
import { Suspense } from "react";
import { KittuChat } from "@/components/chat/KittuChat";
import { Loader2 } from "lucide-react";

export default function ChatPage() {
    return (
        <div className="h-full flex flex-col">
            <Suspense fallback={
                <div className="h-full flex items-center justify-center">
                    <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
                </div>
            }>
                <KittuChat />
            </Suspense>
        </div>
    );
}
