import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PortfolioSummary {
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  pnl_percentage: number;
  number_of_holdings: number;
}

export interface Holding {
  id: number;
  asset: number;
  asset_name: string;
  asset_category: string;
  asset_category_display: string;
  symbol: string | null;
  quantity: number;
  average_cost: number;
  invested_value: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  pnl_percentage: number;
  updated_at: string;
}

export interface Transaction {
  id: number;
  asset: number;
  asset_name: string;
  transaction_type: string;
  transaction_type_display: string;
  transaction_date: string;
  quantity: number;
  price_per_unit: number;
  amount: number;
  fees: number;
  notes: string | null;
  created_at: string;
}

export interface PortfolioAsset {
  id: number;
  name: string;
  category: string;
  category_display: string;
  symbol: string | null;
  isin: string | null;
  institution: string | null;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiListResponse<T> {
  count: number;
  results: T[];
}

export interface CreateAssetRequest {
  name: string;
  category: string;
  symbol?: string | null;
  isin?: string | null;
  institution?: string | null;
  currency?: string;
}

export interface CreateTransactionRequest {
  asset: number;
  transaction_type: string;
  transaction_date: string;
  quantity: number;
  price_per_unit: number;
  amount: number;
  fees?: number;
  notes?: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class PortfolioApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/portfolio';

  private readonly requestOptions = {
    withCredentials: true,
  };

  // ==========================================================
  // SUMMARY
  // ==========================================================

  getSummary(): Observable<PortfolioSummary> {
    return this.http.get<PortfolioSummary>(`${this.baseUrl}/summary/`, this.requestOptions);
  }

  // ==========================================================
  // HOLDINGS
  // ==========================================================

  getHoldings(): Observable<ApiListResponse<Holding>> {
    return this.http.get<ApiListResponse<Holding>>(
      `${this.baseUrl}/holdings/`,
      this.requestOptions,
    );
  }

  // ==========================================================
  // TRANSACTIONS
  // ==========================================================

  getTransactions(): Observable<ApiListResponse<Transaction>> {
    return this.http.get<ApiListResponse<Transaction>>(
      `${this.baseUrl}/transactions/`,
      this.requestOptions,
    );
  }

  // ==========================================================
  // ASSETS
  // ==========================================================

  getAssets(): Observable<ApiListResponse<PortfolioAsset>> {
    return this.http.get<ApiListResponse<PortfolioAsset>>(
      `${this.baseUrl}/assets/`,
      this.requestOptions,
    );
  }

  // ==========================================================
  // CREATE ASSET
  // ==========================================================

  createAsset(payload: CreateAssetRequest): Observable<PortfolioAsset> {
    return this.http.post<PortfolioAsset>(`${this.baseUrl}/assets/`, payload, this.requestOptions);
  }

  // ==========================================================
  // CREATE TRANSACTION
  // ==========================================================

  createTransaction(payload: CreateTransactionRequest): Observable<Transaction> {
    return this.http.post<Transaction>(
      `${this.baseUrl}/transactions/`,
      payload,
      this.requestOptions,
    );
  }
}
