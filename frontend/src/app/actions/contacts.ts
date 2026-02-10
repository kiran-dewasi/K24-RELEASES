'use server'

import { createClient } from '@/lib/supabase/server' // Adjust path as needed
import { Contact } from '@/types'
import { revalidatePath } from 'next/cache'

export async function getContacts(businessId: string, search?: string, page: number = 1) {
    const supabase = await createClient()
    const pageSize = 10
    const from = (page - 1) * pageSize
    const to = from + pageSize - 1

    let query = supabase
        .from('contacts')
        .select('*', { count: 'exact' })
        .eq('business_id', businessId)
        .range(from, to)
        .order('created_at', { ascending: false })

    if (search) {
        query = query.ilike('name', `%${search}%`)
    }

    const { data, error, count } = await query

    if (error) throw new Error(error.message)
    return { data: data as Contact[], count }
}

export async function createContact(data: Omit<Contact, 'id' | 'created_at'>) {
    const supabase = await createClient()

    const { error } = await supabase
        .from('contacts')
        .insert(data)

    if (error) throw new Error(error.message)
    revalidatePath('/contacts')
}

export async function updateContact(id: string, data: Partial<Contact>) {
    const supabase = await createClient()

    const { error } = await supabase
        .from('contacts')
        .update(data)
        .eq('id', id)

    if (error) throw new Error(error.message)
    revalidatePath('/contacts')
}

export async function deleteContact(id: string) {
    const supabase = await createClient()

    const { error } = await supabase
        .from('contacts')
        .delete()
        .eq('id', id)

    if (error) throw new Error(error.message)
    revalidatePath('/contacts')
}
