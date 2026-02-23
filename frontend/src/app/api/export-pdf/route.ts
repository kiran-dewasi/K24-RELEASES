import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
const API_KEY =
    process.env.API_KEY || process.env.NEXT_PUBLIC_API_KEY || "k24-secret-key-123";

/**
 * GET /api/export-pdf?slug=sales-register&date_from=...&date_to=...
 *
 * Server-side proxy to backend /reports/{slug}/export
 * Runs in Node.js — no Tauri CSP / CORS restrictions.
 */
export async function GET(request: NextRequest) {
    const sp = request.nextUrl.searchParams;
    const slug = sp.get("slug");

    if (!slug) {
        return NextResponse.json({ error: "slug is required" }, { status: 400 });
    }

    // Forward every query param except "slug" to the backend
    const forward = new URLSearchParams();
    for (const [k, v] of sp.entries()) {
        if (k !== "slug") forward.set(k, v);
    }

    const backendUrl = `${BACKEND_URL}/reports/${slug}/export?${forward.toString()}`;

    let backendRes: Response;
    try {
        backendRes = await fetch(backendUrl, {
            headers: {
                "x-api-key": API_KEY,
            },
            // 30 s timeout — large reports can take a moment
            signal: AbortSignal.timeout(30_000),
        });
    } catch (err: any) {
        return NextResponse.json(
            { error: `Backend unreachable: ${err?.message}` },
            { status: 502 }
        );
    }

    if (!backendRes.ok) {
        const text = await backendRes.text().catch(() => "");
        return NextResponse.json(
            { error: `Backend error ${backendRes.status}: ${text}` },
            { status: backendRes.status }
        );
    }

    const pdfBytes = await backendRes.arrayBuffer();
    const date = new Date().toISOString().slice(0, 10);

    return new NextResponse(pdfBytes, {
        status: 200,
        headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": `attachment; filename="k24-${slug}-${date}.pdf"`,
            "Content-Length": String(pdfBytes.byteLength),
        },
    });
}
