export interface UserProfile {
    id: string;
    full_name: string | null;
    whatsapp_number: string | null;
    avatar_url: string | null;
    role: string;
    created_at: string;
}

export interface BusinessProfile {
    id: string;
    owner_id: string;
    company_name: string | null;
    gstin: string | null;
    address: string | null;
    tally_license_key: string | null;
    preferences: {
        auto_sync: boolean;
        notify_whatsapp: boolean;
    };
    created_at: string;
}

export interface Contact {
    id: string;
    business_id: string;
    name: string;
    phone: string | null;
    type: 'Sundry Debtor' | 'Sundry Creditor';
    current_balance: number;
    tally_ledger_name: string | null;
    created_at: string;
}
