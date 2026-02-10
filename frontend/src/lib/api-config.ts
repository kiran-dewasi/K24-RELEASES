/**
 * API Configuration (Legacy Compatibility Layer)
 * 
 * This file provides backward compatibility with existing components.
 * New code should import directly from './api.ts'
 * 
 * @deprecated Use imports from './api.ts' instead:
 *   import { apiRequest, api, API_CONFIG } from '@/lib/api';
 */

// Re-export everything from the new secure API client
export {
    apiRequest,
    api,
    API_CONFIG,
    apiClient,
    checkBackendStatus,
    startBackend
} from './api';

// Type exports for backward compatibility
export type { } from './api';
