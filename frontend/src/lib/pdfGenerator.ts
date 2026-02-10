import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface VoucherItem {
    description: string;
    quantity: number;
    rate: number;
    amount: number;
}

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number;
    narration: string;
    items?: VoucherItem[];
    tax_rate?: number;
    subtotal?: number;
}

export const generateProfessionalVoucherPDF = (voucher: Voucher) => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.width;

    // Colors
    const primaryBlue: [number, number, number] = [41, 98, 255];
    const lightBlue: [number, number, number] = [240, 245, 255];
    const darkGray: [number, number, number] = [51, 51, 51];
    const lightGray: [number, number, number] = [128, 128, 128];

    // === HEADER SECTION ===
    // Company Name (Left)
    doc.setFontSize(18);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(darkGray[0], darkGray[1], darkGray[2]);
    doc.text("Krishasales", 20, 25);

    // Company Details (Left)
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(lightGray[0], lightGray[1], lightGray[2]);
    doc.text("123, Business Park", 20, 32);
    doc.text("Greater South Avenue", 20, 37);
    doc.text("New Delhi - 110001", 20, 42);
    doc.text("India", 20, 47);

    // INVOICE Title (Right)
    doc.setFontSize(32);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(primaryBlue[0], primaryBlue[1], primaryBlue[2]);
    doc.text(voucher.voucher_type.toUpperCase(), pageWidth - 20, 30, { align: "right" });

    // === INVOICE DETAILS & SHIP TO SECTION ===
    const detailsY = 60;

    // Left Box - Invoice Details
    doc.setFillColor(lightBlue[0], lightBlue[1], lightBlue[2]);
    doc.rect(20, detailsY, 85, 35, "F");

    doc.setFontSize(9);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(darkGray[0], darkGray[1], darkGray[2]);

    doc.text("Invoice #:", 25, detailsY + 8);
    doc.text("Invoice Date:", 25, detailsY + 15);
    doc.text("Due Date:", 25, detailsY + 22);
    doc.text("Bill To:", 25, detailsY + 29);

    doc.setFont("helvetica", "normal");
    doc.text(voucher.voucher_number, 55, detailsY + 8);
    doc.text(voucher.date, 55, detailsY + 15);
    doc.text(voucher.date, 55, detailsY + 22);
    doc.text(voucher.party_name, 55, detailsY + 29);

    // Right Box - Ship To
    doc.setFillColor(lightBlue[0], lightBlue[1], lightBlue[2]);
    doc.rect(pageWidth - 85, detailsY, 65, 35, "F");

    doc.setFont("helvetica", "bold");
    doc.text("Ship To:", pageWidth - 80, detailsY + 8);

    doc.setFont("helvetica", "normal");
    doc.text(voucher.party_name, pageWidth - 80, detailsY + 15);
    doc.text("Address Line 1", pageWidth - 80, detailsY + 22);
    doc.text("City, State - PIN", pageWidth - 80, detailsY + 29);

    // === ITEMS TABLE ===
    const tableStartY = detailsY + 45;

    // Prepare table data
    const tableData = voucher.items && voucher.items.length > 0
        ? voucher.items.map((item, index) => [
            index + 1,
            item.description,
            item.quantity.toFixed(2),
            `₹${item.rate.toLocaleString('en-IN')}`,
            `₹${item.amount.toLocaleString('en-IN')}`
        ])
        : [[
            1,
            voucher.narration || "Payment/Receipt",
            "1.00",
            `₹${voucher.amount.toLocaleString('en-IN')}`,
            `₹${voucher.amount.toLocaleString('en-IN')}`
        ]];

    autoTable(doc, {
        startY: tableStartY,
        head: [['#', 'Item & Description', 'Qty', 'Rate', 'Amount']],
        body: tableData,
        theme: 'grid',
        headStyles: {
            fillColor: primaryBlue,
            textColor: [255, 255, 255],
            fontSize: 10,
            fontStyle: 'bold',
            halign: 'left'
        },
        columnStyles: {
            0: { cellWidth: 10, halign: 'center' },
            1: { cellWidth: 80 },
            2: { cellWidth: 20, halign: 'center' },
            3: { cellWidth: 30, halign: 'right' },
            4: { cellWidth: 35, halign: 'right' }
        },
        styles: {
            fontSize: 9,
            cellPadding: 5
        },
        margin: { left: 20, right: 20 }
    });

    // === SUMMARY SECTION ===
    const finalY = (doc as any).lastAutoTable.finalY + 10;
    const summaryX = pageWidth - 75;

    // Calculate values
    const subtotal = voucher.subtotal || voucher.amount;
    const taxRate = voucher.tax_rate || 0;
    const taxAmount = subtotal * (taxRate / 100);
    const total = subtotal + taxAmount;

    // Summary Box
    doc.setFillColor(250, 250, 250);
    doc.rect(summaryX - 5, finalY, 70, 35, "F");

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(darkGray[0], darkGray[1], darkGray[2]);

    doc.text("Sub Total:", summaryX, finalY + 8);
    doc.text(`₹${subtotal.toLocaleString('en-IN')}`, pageWidth - 25, finalY + 8, { align: "right" });

    if (taxRate > 0) {
        doc.text(`Tax Rate (${taxRate}%):`, summaryX, finalY + 15);
        doc.text(`₹${taxAmount.toLocaleString('en-IN')}`, pageWidth - 25, finalY + 15, { align: "right" });
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("Total:", summaryX, finalY + 22);
    doc.text(`₹${total.toLocaleString('en-IN')}`, pageWidth - 25, finalY + 22, { align: "right" });

    doc.setFillColor(primaryBlue[0], primaryBlue[1], primaryBlue[2]);
    doc.rect(summaryX - 5, finalY + 26, 70, 8, "F");
    doc.setTextColor(255, 255, 255);
    doc.text("Balance Due:", summaryX, finalY + 31);
    doc.text(`₹${total.toLocaleString('en-IN')}`, pageWidth - 25, finalY + 31, { align: "right" });

    // === TERMS & CONDITIONS ===
    doc.setFontSize(9);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(darkGray[0], darkGray[1], darkGray[2]);
    doc.text("Terms & Conditions:", 20, finalY + 50);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(lightGray[0], lightGray[1], lightGray[2]);
    const terms = doc.splitTextToSize(
        "Full payment is due upon receipt of this invoice. Late payments may incur additional charges or interest as per the applicable laws. This is a computer-generated document and does not require a physical signature.",
        pageWidth - 40
    );
    doc.text(terms, 20, finalY + 56);

    // === FOOTER ===
    doc.setFontSize(8);
    doc.setTextColor(lightGray[0], lightGray[1], lightGray[2]);
    doc.text("Generated by K24 Intelligent ERP System", pageWidth / 2, doc.internal.pageSize.height - 15, { align: "center" });
    doc.text(`GSTIN: 07AABCS1234Q1Z5 | PAN: AABCS1234Q`, pageWidth / 2, doc.internal.pageSize.height - 10, { align: "center" });

    // Save
    doc.save(`${voucher.voucher_type}_${voucher.voucher_number}.pdf`);
};

// Keep the audit report generator as is
export const generateAuditReportPDF = (logs: any[], stats: any) => {
    const doc = new jsPDF();

    // Header
    doc.setFontSize(20);
    doc.setTextColor(40, 40, 40);
    doc.text("AUDIT TRAIL REPORT", 105, 20, { align: "center" });

    doc.setFontSize(10);
    doc.text("MCA Compliance Report", 105, 27, { align: "center" });
    doc.text(`Generated: ${new Date().toLocaleString()}`, 105, 32, { align: "center" });

    doc.setLineWidth(0.5);
    doc.line(20, 36, 190, 36);

    // Summary Stats
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Compliance Summary", 20, 45);

    const summaryData = [
        ["High Value Transactions (>₹2L)", stats?.high_value_count || 0],
        ["Backdated Entries", stats?.backdated_count || 0],
        ["Weekend Entries", stats?.weekend_count || 0],
        ["Pending TDS Liability", `₹${(stats?.pending_tds || 0).toLocaleString('en-IN')}`]
    ];

    autoTable(doc, {
        startY: 50,
        head: [['Metric', 'Count']],
        body: summaryData,
        theme: 'grid',
        headStyles: { fillColor: [66, 139, 202] },
        margin: { left: 20, right: 20 }
    });

    // Audit Logs Table
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    const finalY = (doc as any).lastAutoTable.finalY || 90;
    doc.text("Detailed Audit Log", 20, finalY + 15);

    const auditData = logs.map(log => [
        new Date(log.timestamp).toLocaleString(),
        log.user_id,
        log.action,
        `${log.entity_type} #${log.entity_id}`,
        log.reason
    ]);

    autoTable(doc, {
        startY: finalY + 20,
        head: [['Timestamp', 'User', 'Action', 'Entity', 'Reason']],
        body: auditData,
        theme: 'striped',
        headStyles: { fillColor: [52, 73, 94] },
        styles: { fontSize: 8 },
        margin: { left: 20, right: 20 }
    });

    // Footer
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.text(
            `Page ${i} of ${pageCount}`,
            doc.internal.pageSize.width / 2,
            doc.internal.pageSize.height - 10,
            { align: 'center' }
        );
    }

    doc.save(`Audit_Report_${new Date().toISOString().split('T')[0]}.pdf`);
};
