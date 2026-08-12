import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface MutualFundSummary {
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  pnl_percentage: number;
  number_of_holdings: number;
}

export interface MutualFundHolding {
  id: number;
  scheme: number;
  scheme_name: string;
  scheme_code: string | null;
  amc_name: string | null;
  units: number;
  invested_value: number;
  average_nav: number;
  current_nav: number;
  current_value: number;
  unrealized_pnl: number;
  pnl_percentage: number;
  updated_at: string;
}

export interface MutualFundTransaction {
  id: number;
  scheme: number;
  scheme_name: string;
  transaction_type: string;
  transaction_type_display: string;
  transaction_date: string;
  units: number;
  nav: number;
  amount: number;
  fees: number;
  notes: string | null;
  created_at: string;
}

export interface ApiListResponse<T> {
  count: number;
  results: T[];
}

@Injectable({
  providedIn: 'root',
})
export class MutualFundsApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/mutual-funds';

  private readonly requestOptions = {
    withCredentials: true,
  };

  getSummary(): Observable<MutualFundSummary> {
    return this.http.get<MutualFundSummary>(`${this.baseUrl}/summary/`, this.requestOptions);
  }

  getHoldings(): Observable<ApiListResponse<MutualFundHolding>> {
    return this.http.get<ApiListResponse<MutualFundHolding>>(
      `${this.baseUrl}/holdings/`,
      this.requestOptions,
    );
  }

  getTransactions(): Observable<ApiListResponse<MutualFundTransaction>> {
    return this.http.get<ApiListResponse<MutualFundTransaction>>(
      `${this.baseUrl}/transactions/`,
      this.requestOptions,
    );
  }
}
