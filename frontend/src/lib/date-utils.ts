import { startOfDay, endOfDay, subDays, startOfWeek, endOfWeek, startOfMonth, endOfMonth, subMonths, startOfYear, endOfYear, addMonths } from "date-fns";

export type DateFilterType = 'today' | 'yesterday' | 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'this_quarter' | 'this_fy' | 'custom';

export interface DateRange {
    from: Date;
    to: Date;
}

export const getDateRange = (filter: DateFilterType, now: Date = new Date()): DateRange => {
    // Ensure "now" is treated as the reference point (local time)
    const current = new Date(now);

    switch (filter) {
        case 'today':
            return { from: startOfDay(current), to: endOfDay(current) };

        case 'yesterday': {
            const yest = subDays(current, 1);
            return { from: startOfDay(yest), to: endOfDay(yest) };
        }

        case 'this_week':
            // Mon - Sun
            return {
                from: startOfWeek(current, { weekStartsOn: 1 }),
                to: endOfWeek(current, { weekStartsOn: 1 })
            };

        case 'last_week': {
            const lastWeek = subDays(current, 7);
            return {
                from: startOfWeek(lastWeek, { weekStartsOn: 1 }),
                to: endOfWeek(lastWeek, { weekStartsOn: 1 })
            };
        }

        case 'this_month':
            return { from: startOfMonth(current), to: endOfMonth(current) };

        case 'last_month': {
            const lastMonth = subMonths(current, 1);
            return { from: startOfMonth(lastMonth), to: endOfMonth(lastMonth) };
        }

        case 'this_quarter': {
            // Indian FY Quarters: Q1(Apr-Jun), Q2(Jul-Sep), Q3(Oct-Dec), Q4(Jan-Mar)
            const month = current.getMonth(); // 0-11
            let qStartMonth = 0;
            let qYear = current.getFullYear();

            if (month >= 0 && month <= 2) { // Jan-Mar (Q4)
                qStartMonth = 0; // Jan
            } else if (month >= 3 && month <= 5) { // Apr-Jun (Q1)
                qStartMonth = 3;
            } else if (month >= 6 && month <= 8) { // Jul-Sep (Q2)
                qStartMonth = 6;
            } else { // Oct-Dec (Q3)
                qStartMonth = 9;
            }

            const qStart = new Date(qYear, qStartMonth, 1);
            const qEnd = endOfMonth(addMonths(qStart, 2));

            return { from: startOfDay(qStart), to: endOfDay(qEnd) };
        }

        case 'this_fy': {
            // Apr 1 of current FY year to Mar 31 of next year
            // If Jan-Mar 2026, FY is 2025-2026 -> Start Apr 1 2025
            // If Apr-Dec 2026, FY is 2026-2027 -> Start Apr 1 2026

            const month = current.getMonth();
            const year = current.getFullYear();

            let startYear = year;
            if (month < 3) { // Jan, Feb, Mar belong to previous calendar year's FY start
                startYear = year - 1;
            }

            const fyStart = new Date(startYear, 3, 1); // Apr 1
            const fyEnd = new Date(startYear + 1, 2, 31); // Mar 31

            return { from: startOfDay(fyStart), to: endOfDay(fyEnd) };
        }

        default:
            return { from: startOfDay(current), to: endOfDay(current) };
    }
};

export const formatDateForApi = (date: Date): string => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}${m}${d}`;
};

export const formatDateForDisplay = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
};
