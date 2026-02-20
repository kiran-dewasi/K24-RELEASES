'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
    ArrowLeft, Package, TrendingUp, TrendingDown, Users,
    DollarSign, Activity, BarChart3, RefreshCcw, AlertCircle, Loader2
} from 'lucide-react';
import Link from 'next/link';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
);

// Component for Stat Cards
const StatCard = ({ title, value, subtext, icon: Icon, colorClass }: any) => (
    <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-2">
            <div className={`p-2.5 rounded-xl ${colorClass} bg-opacity-10 text-opacity-100`}>
                <Icon size={22} className={colorClass.replace('bg-', 'text-')} />
            </div>
            {subtext && <span className="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-1 rounded-full">{subtext}</span>}
        </div>
        <div className="mt-3">
            <h3 className="text-2xl font-bold text-gray-900 tracking-tight">{value}</h3>
            <p className="text-sm text-gray-500 font-medium">{title}</p>
        </div>
    </div>
);




function Item360Content() {
    const searchParams = useSearchParams();
    const itemId = searchParams.get('id') || '';
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (itemId && itemId !== 'default') {
            fetchItemDetails();
        }
    }, [itemId]);

    const fetchItemDetails = async () => {
        try {
            setLoading(true);
            const res = await fetch(`/api/items/${itemId}/360`);
            if (!res.ok) throw new Error('Item not found');
            const jsonData = await res.json();
            setData(jsonData);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (itemId === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select an item to view details.</div>;
    }

    if (loading) return (
        <div className="min-h-screen bg-gray-50/50 flex items-center justify-center">
            <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-gray-500 font-medium">Loading Item Intelligence...</p>
            </div>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-gray-50/50 flex flex-col items-center justify-center text-center p-4">
            <AlertCircle className="h-16 w-16 text-red-300 mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Item Not Found</h1>
            <p className="text-gray-500 mb-8 max-w-md">We couldn't locate this item in the inventory. It might have been deleted or not synced yet.</p>
            <Link href="/items" className="bg-blue-600 text-white px-6 py-2.5 rounded-xl hover:bg-blue-700 transition font-medium shadow-lg shadow-blue-600/20">
                Back to Inventory
            </Link>
        </div>
    );

    const { item, stock_summary, insights, profit_analysis, top_customers, purchase_history, sales_history, rate_trends } = data;

    // Chart Data Preparation
    const chartData = {
        labels: rate_trends?.map((t: any) => t.month) || [],
        datasets: [
            {
                label: 'Avg Rate (₹)',
                data: rate_trends?.map((t: any) => t.avg_rate) || [],
                backgroundColor: 'rgba(59, 130, 246, 0.5)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1,
                borderRadius: 4,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        plugins: {
            legend: { display: false },
            title: { display: false },
        },
        scales: {
            y: { beginAtZero: true, grid: { display: false } },
            x: { grid: { display: false } }
        }
    };

    return (
        <div className="min-h-screen bg-gray-50/50 p-6 md:p-8">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Navigation & Header */}
                <div>
                    <Link href="/items" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-800 mb-6 transition-colors group">
                        <ArrowLeft size={16} className="mr-1 group-hover:-translate-x-1 transition-transform" /> Back to Inventory
                    </Link>

                    <div className="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div className="flex items-center gap-5">
                            <div className="h-20 w-20 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl flex items-center justify-center text-blue-600 shadow-inner">
                                <Package size={36} />
                            </div>
                            <div>
                                <h1 className="text-3xl font-bold text-gray-900 tracking-tight">{item.name}</h1>
                                <div className="flex flex-wrap items-center gap-3 mt-2">
                                    <span className="px-2.5 py-1 rounded-lg bg-gray-100 text-gray-600 text-xs font-semibold tracking-wide border border-gray-200">
                                        SKU: {item.sku || 'N/A'}
                                    </span>
                                    <span className="px-2.5 py-1 rounded-lg bg-gray-100 text-gray-600 text-xs font-semibold tracking-wide border border-gray-200">
                                        HSN: {item.hsn_code || 'N/A'}
                                    </span>
                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-bold tracking-wide flex items-center gap-1.5 border ${stock_summary.current_stock > 0
                                        ? 'bg-green-50 text-green-700 border-green-100'
                                        : 'bg-red-50 text-red-700 border-red-100'
                                        }`}>
                                        <div className={`w-2 h-2 rounded-full ${stock_summary.current_stock > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
                                        {stock_summary.current_stock > 0 ? 'IN STOCK' : 'OUT OF STOCK'}
                                    </span>
                                    {insights.fast_moving && (
                                        <span className="px-2.5 py-1 rounded-lg bg-orange-50 text-orange-700 text-xs font-bold tracking-wide border border-orange-100 flex items-center gap-1">
                                            🔥 Fast Moving
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 w-full md:w-auto">
                            <button className="flex-1 md:flex-none px-5 py-2.5 border border-gray-200 rounded-xl hover:bg-gray-50 transition font-medium text-gray-700 shadow-sm">
                                Edit Item
                            </button>
                            <button
                                onClick={fetchItemDetails}
                                className="flex-1 md:flex-none bg-blue-600 text-white px-5 py-2.5 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-600/20 font-medium flex items-center justify-center gap-2"
                            >
                                <RefreshCcw size={18} /> Sync
                            </button>
                        </div>
                    </div>
                </div>

                {/* High-Level KPIs */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    <StatCard
                        title="Current Stock"
                        value={`${stock_summary.current_stock} ${stock_summary.unit}`}
                        icon={Package}
                        colorClass="bg-blue-600"
                        subtext={`Val: ₹${(stock_summary.current_stock * item.sales_rate).toLocaleString()}`}
                    />
                    <StatCard
                        title="Sales Rate"
                        value={`₹${item.sales_rate?.toLocaleString()}`}
                        icon={TrendingUp}
                        colorClass="bg-green-600"
                        subtext={`per ${stock_summary.unit}`}
                    />
                    <StatCard
                        title="Purchase Rate"
                        value={`₹${item.purchase_rate?.toLocaleString()}`}
                        icon={TrendingDown}
                        colorClass="bg-orange-500"
                        subtext={`per ${stock_summary.unit}`}
                    />
                    <StatCard
                        title="Profit Margin"
                        value={`${profit_analysis.profit_margin_percent}%`}
                        icon={DollarSign}
                        colorClass={profit_analysis.profit_margin_percent > 20 ? "bg-emerald-500" : "bg-yellow-500"}
                        subtext={`₹${profit_analysis.profit_per_unit}/unit`}
                    />
                    <StatCard
                        title="Movements"
                        value={stock_summary.total_movements}
                        icon={Activity}
                        colorClass="bg-purple-600"
                        subtext={`${stock_summary.total_inward} In / ${stock_summary.total_outward} Out`}
                    />
                </div>

                {/* Stock Insights Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                                <BarChart3 size={20} />
                            </div>
                            <h3 className="font-bold text-gray-900">Stock Days</h3>
                        </div>
                        <p className="text-3xl font-bold text-gray-900 mt-2">
                            {insights.stock_days < 999 ? Math.round(insights.stock_days) : '∞'}
                            <span className="text-sm text-gray-500 font-normal ml-1">days</span>
                        </p>
                        <p className="text-sm text-gray-500 mt-1">Estimated time until stockout</p>

                        <div className="w-full bg-gray-100 h-1.5 rounded-full mt-4 overflow-hidden">
                            <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${Math.min(insights.stock_days, 100)}%` }}></div>
                        </div>
                    </div>

                    <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-cyan-50 text-cyan-600 rounded-lg">
                                <RefreshCcw size={20} />
                            </div>
                            <h3 className="font-bold text-gray-900">Turnover Ratio</h3>
                        </div>
                        <p className="text-3xl font-bold text-gray-900 mt-2">
                            {insights.turnover_ratio?.toFixed(2) || '0.00'}
                            <span className="text-sm text-gray-500 font-normal ml-1">x</span>
                        </p>
                        <p className="text-sm text-gray-500 mt-1">Inventory turnover per year</p>
                    </div>

                    <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
                                <Activity size={20} />
                            </div>
                            <h3 className="font-bold text-gray-900">Stock Health</h3>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                            <p className={`text-2xl font-bold ${insights.reorder_alert ? 'text-red-500' : 'text-green-600'}`}>
                                {insights.reorder_alert ? 'Reorder Required' : 'Healthy'}
                            </p>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                            {insights.reorder_alert ? 'Stock level is below 20% threshold' : 'Optimal stock levels maintained'}
                        </p>
                    </div>
                </div>


                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* Purchase History */}
                    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <TrendingDown size={20} className="text-orange-500" />
                            Purchase History
                        </h3>

                        <div className="space-y-4">
                            {purchase_history?.length > 0 ? purchase_history.map((log: any, idx: number) => (
                                <div key={idx} className="flex justify-between items-center p-3 rounded-xl hover:bg-orange-50/50 transition border border-transparent hover:border-orange-100">
                                    <div className="flex gap-4 items-center">
                                        <div className="h-10 w-10 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center font-bold text-xs shrink-0">
                                            IN
                                        </div>
                                        <div>
                                            <p className="font-semibold text-gray-900 line-clamp-1">{log.supplier || 'N/A'}</p>
                                            <div className="flex gap-2 text-xs text-gray-500 mt-0.5">
                                                <span>{new Date(log.date).toLocaleDateString()}</span>
                                                <span>•</span>
                                                <span>{log.voucher_number}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="font-bold text-orange-600">
                                            +{log.quantity}
                                        </p>
                                        <p className="text-xs text-gray-400">@ ₹{log.rate?.toLocaleString()}</p>
                                    </div>
                                </div>
                            )) : (
                                <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                    No purchase history found
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Sales History */}
                    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <TrendingUp size={20} className="text-green-500" />
                            Sales History
                        </h3>

                        <div className="space-y-4">
                            {sales_history?.length > 0 ? sales_history.map((log: any, idx: number) => (
                                <div key={idx} className="flex justify-between items-center p-3 rounded-xl hover:bg-green-50/50 transition border border-transparent hover:border-green-100">
                                    <div className="flex gap-4 items-center">
                                        <div className="h-10 w-10 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-bold text-xs shrink-0">
                                            OUT
                                        </div>
                                        <div>
                                            <p className="font-semibold text-gray-900 line-clamp-1">{log.customer || 'N/A'}</p>
                                            <div className="flex gap-2 text-xs text-gray-500 mt-0.5">
                                                <span>{new Date(log.date).toLocaleDateString()}</span>
                                                <span>•</span>
                                                <span>{log.voucher_number}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="font-bold text-green-600">
                                            -{log.quantity}
                                        </p>
                                        <p className="text-xs text-gray-400">@ ₹{log.rate?.toLocaleString()}</p>
                                    </div>
                                </div>
                            )) : (
                                <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                    No sales history found
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Top Buyers */}
                    <div className="lg:col-span-2 bg-white rounded-3xl border border-gray-100 shadow-sm p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <Users size={20} className="text-gray-400" />
                            Top Buyers
                        </h3>

                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100">
                                        <th className="pb-3 pl-2">Customer</th>
                                        <th className="pb-3 text-right">Qty</th>
                                        <th className="pb-3 text-right">Value</th>
                                        <th className="pb-3 text-right">Txns</th>
                                        <th className="pb-3 text-right pr-2">Avg Rate</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50">
                                    {top_customers?.map((cust: any, i: number) => (
                                        <tr key={i} className="hover:bg-gray-50 transition-colors group">
                                            <td className="py-3 pl-2">
                                                <Link href={`/customers/${cust.customer_id}`} className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                                                    {cust.customer_name}
                                                </Link>
                                            </td>
                                            <td className="py-3 text-right text-gray-600">{cust.total_quantity}</td>
                                            <td className="py-3 text-right font-medium text-gray-900">₹{cust.total_value?.toLocaleString()}</td>
                                            <td className="py-3 text-right text-gray-600">{cust.transaction_count}</td>
                                            <td className="py-3 text-right text-gray-600 pr-2">₹{cust.avg_rate?.toFixed(0)}</td>
                                        </tr>
                                    ))}
                                    {!top_customers?.length && (
                                        <tr>
                                            <td colSpan={5} className="text-center py-8 text-gray-400">No top customers data</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Rate Trends */}
                    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">Pricing Trend</h3>
                        <div className="h-64 flex flex-col justify-end">
                            {rate_trends?.length > 0 ? (
                                <Bar options={chartOptions} data={chartData} />
                            ) : (
                                <div className="flex items-center justify-center h-full text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                    No trend data
                                </div>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}

export default function Item360Page() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gray-50/50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            </div>
        }>
            <Item360Content />
        </Suspense>
    );
}

