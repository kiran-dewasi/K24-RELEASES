export interface DownloadFileOptions {
    slug: string;
    format: "pdf" | "excel";
    params?: Record<string, string | undefined>;
}

export async function downloadReportFile({ slug, format, params }: DownloadFileOptions): Promise<void> {
    const endpointSuffix = format === "pdf" ? "export" : "export-excel";
    const ext = format === "pdf" ? "pdf" : "xlsx";
    
    // We import apiClient specifically to handle getting raw responses and passing standard tokens
    const { apiClient } = await import("@/lib/api");

    let urlSuffix = `/reports/${slug}/${endpointSuffix}`;
    if (params) {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                queryParams.append(key, value);
            }
        });
        urlSuffix += `?${queryParams.toString()}`;
    }

    const res = await apiClient(urlSuffix);

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
