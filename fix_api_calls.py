import re
from pathlib import Path

fixes = {
    'frontend/src/components/DashboardStats.tsx': [
        (r'import \{ API_CONFIG, apiClient \} from "@/lib/api-config";', 'import { api } from "@/lib/api";'),
        (r'const \[sRes, stRes, pRes\] = await Promise\.all\(\[\s*apiClient\("/api/dashboard/stats"\),\s*apiClient\("/api/dashboard/stock-summary"\),\s*apiClient\("/api/dashboard/party-analysis"\),\s*\]\);.*?if \(pRes\.ok\) setPartyStats\(await pRes\.json\(\)\);',
         '''const [statsData, stockData, partyData] = await Promise.all([
                api.get("/api/dashboard/stats"),
                api.get("/api/dashboard/stock-summary"),
                api.get("/api/dashboard/party-analysis"),
            ]);

            setStats(statsData);
            if (statsData.cash === 0 && statsData.receivables === 0 && statsData.payables === 0) {
                setTimeout(() => setRefreshKey(k => k + 1), 4000);
            }
            setStockStats(stockData);
            setPartyStats(partyData);''', re.DOTALL),
    ],
    'frontend/src/components/invoices/InvoiceStats.tsx': [
        (r'import \{ apiClient \} from "@/lib/api-config";', 'import { api } from "@/lib/api";'),
        (r'const statsRes = await apiClient\("/api/dashboard/stats"\);.*?const cashflowData = cfRes\.ok \? await cfRes\.json\(\) : \[\];',
         '''const [dashStats, cashflowData] = await Promise.all([
                    api.get("/api/dashboard/stats").catch(() => null),
                    api.get("/api/dashboard/cashflow").catch(() => [])
                ]);''', re.DOTALL),
    ],
}

for file_path, replacements in fixes.items():
    p = Path(file_path)
    if p.exists():
        content = p.read_text(encoding='utf-8')
        for pattern, replacement, *flags in replacements:
            flag = flags[0] if flags else 0
            content = re.sub(pattern, replacement, content, flags=flag)
        p.write_text(content, encoding='utf-8')
        print(f"Fixed: {file_path}")
