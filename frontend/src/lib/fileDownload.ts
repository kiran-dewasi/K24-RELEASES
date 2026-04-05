export interface DownloadFileOptions {
    slug: string;
    format: "pdf" | "excel";
    params?: Record<string, string | undefined>;
}

export async function downloadReportFile({ slug, format, params }: DownloadFileOptions): Promise<void> {
    const endpointSuffix = format === "pdf" ? "export" : "export-excel";
    const ext = format === "pdf" ? "pdf" : "xlsx";
    
    const backendBase = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8001';
    
    const url = new URL(`${backendBase}/reports/${slug}/${endpointSuffix}`);
    
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                url.searchParams.append(key, value);
            }
        });
    }

    const res = await fetch(url.toString(), {
        headers: { "x-api-key": process.env.NEXT_PUBLIC_API_KEY || "k24-secret-key-123" }
    });

    if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || errJson?.error || `HTTP ${res.status}`);
    }

    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objUrl;
    a.download = `${slug}-${new Date().toISOString().slice(0, 10)}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objUrl);
}
