import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import { Download, Printer, Share2, Loader2 } from "lucide-react";
import { downloadReportFile } from "@/lib/fileDownload";
import { useState } from "react";

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number;
    narration: string;
}

interface TransactionDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    voucher: Voucher | null;
}

export default function TransactionDetailModal({ isOpen, onClose, voucher }: TransactionDetailModalProps) {
    const [exporting, setExporting] = useState(false);
    if (!voucher) return null;

    const generatePDF = async () => {
        setExporting(true);
        try {
            await downloadReportFile({
                slug: "voucher",
                format: "pdf",
                params: { id: voucher.voucher_number }
            });
            toast({
                title: "PDF Downloaded",
                description: `Invoice ${voucher.voucher_number} has been saved.`,
                duration: 3000,
            });
        } catch (err: any) {
            toast({
                title: "Export Failed",
                description: err?.message || "Failed to download PDF.",
                variant: "destructive",
            });
        } finally {
            setExporting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>{voucher.voucher_type} Details</DialogTitle>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* Header Info */}
                    <div className="flex justify-between items-start border-b pb-4">
                        <div>
                            <p className="text-sm text-muted-foreground">Voucher Number</p>
                            <p className="font-mono font-bold text-lg">{voucher.voucher_number}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-muted-foreground">Date</p>
                            <p className="font-medium">{voucher.date}</p>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="space-y-4">
                        <div>
                            <p className="text-sm text-muted-foreground">Party Name</p>
                            <p className="text-xl font-bold text-primary">{voucher.party_name}</p>
                        </div>

                        <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-muted-foreground mb-1">Amount</p>
                            <p className="text-3xl font-bold">
                                ₹{voucher.amount.toLocaleString('en-IN')}
                            </p>
                        </div>

                        <div>
                            <p className="text-sm text-muted-foreground">Narration</p>
                            <p className="italic text-gray-700">{voucher.narration || "No narration"}</p>
                        </div>
                    </div>
                </div>

                <DialogFooter className="sm:justify-between">
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => window.print()}>
                            <Printer className="h-4 w-4 mr-2" />
                            Print
                        </Button>
                        <Button variant="outline" size="sm">
                            <Share2 className="h-4 w-4 mr-2" />
                            Share
                        </Button>
                    </div>
                    <Button onClick={generatePDF} disabled={exporting} className="bg-blue-600 hover:bg-blue-700">
                        {exporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
                        Download PDF
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
