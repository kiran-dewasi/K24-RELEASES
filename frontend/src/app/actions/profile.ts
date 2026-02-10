'use server'

import { createClient } from '@/lib/supabase/server' // Adjust path as needed
import { UserProfile, BusinessProfile } from '@/types'
import { revalidatePath } from 'next/cache'

export async function getUserProfile(userId: string) {
    const supabase = await createClient()

    const { data: profile, error } = await supabase
        .from('users_profile')
        .select('*')
        .eq('id', userId)
        .single()

    if (error) throw new Error(error.message)
    return profile as UserProfile
}

export async function updateUserProfile(userId: string, data: Partial<UserProfile>) {
    const supabase = await createClient()

    const { error } = await supabase
        .from('users_profile')
        .update(data)
        .eq('id', userId)

    if (error) throw new Error(error.message)
    revalidatePath('/profile')
}

export async function getBusinessProfile(userId: string) {
    const supabase = await createClient()

    const { data: business, error } = await supabase
        .from('business_profile')
        .select('*')
        .eq('owner_id', userId)
        .single()

    if (error && error.code !== 'PGRST116') throw new Error(error.message) // PGRST116 is "no rows returned"
    return business as BusinessProfile | null
}

export async function updateBusinessProfile(ownerId: string, data: Partial<BusinessProfile>) {
    const supabase = await createClient()

    // Check if exists
    const { data: existing } = await supabase
        .from('business_profile')
        .select('id')
        .eq('owner_id', ownerId)
        .single()

    let error;
    if (existing) {
        const res = await supabase
            .from('business_profile')
            .update(data)
            .eq('owner_id', ownerId)
        error = res.error
    } else {
        const res = await supabase
            .from('business_profile')
            .insert({ ...data, owner_id: ownerId })
        error = res.error
    }

    if (error) throw new Error(error.message)
    revalidatePath('/profile')
}
