/**
 * OIDC API Service
 * 
 * Handles OIDC workload identity federation with AWS, GCP, and Azure
 */

import { apiClient } from './client';

export interface AssumeRoleRequest {
    role_arn?: string;
    role_session_name?: string;
    duration_seconds?: number;
}

export interface AssumeRoleResponse {
    access_key_id: string;
    secret_access_key: string;
    session_token: string;
    expiration: string;
    region: string;
}

export interface GCPTokenRequest {
    service_account_email?: string;
    scope?: string;
}

export interface GCPTokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export interface AzureTokenRequest {
    scope?: string;
    resource?: string;
}

export interface AzureTokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    resource: string;
}

export const oidcApi = {
    /**
     * Assume AWS IAM Role using Web Identity Federation
     */
    async assumeAWSRole(request: AssumeRoleRequest = {}): Promise<AssumeRoleResponse> {
        return apiClient.request<AssumeRoleResponse>('/aws/assume-role', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    },

    /**
     * Get GCP access token via Workload Identity Federation
     */
    async getGCPToken(request: GCPTokenRequest = {}): Promise<GCPTokenResponse> {
        return apiClient.request<GCPTokenResponse>('/gcp/token', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    },

    /**
     * Get Azure access token via Federated Identity Credential
     */
    async getAzureToken(request: AzureTokenRequest = {}): Promise<AzureTokenResponse> {
        return apiClient.request<AzureTokenResponse>('/azure/token', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    },

    /**
     * Get JWKS (public keys) for token verification
     */
    async getJWKS(): Promise<any> {
        return apiClient.request('/.well-known/jwks.json', {
            method: 'GET'
        });
    },

    /**
     * Get OIDC configuration
     */
    async getOIDCConfig(): Promise<any> {
        return apiClient.request('/.well-known/openid-configuration', {
            method: 'GET'
        });
    }
};


