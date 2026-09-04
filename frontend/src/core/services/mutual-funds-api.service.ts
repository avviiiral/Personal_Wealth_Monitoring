import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, switchMap } from 'rxjs';

export interface MutualFundSummary {
  total_invested: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  pnl_percentage: number;
  number_of_holdings: number;
}

export interface MutualFundScheme {
  id: number;
  scheme_name: string;
  amc_name: string | null;
  scheme_code: string | null;
  isin_growth: string | null;
  isin_dividend: string | null;
  plan: string | null;
  option: string | null;
  category: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateMutualFundSchemeRequest {
  scheme_name: string;
  amc_name?: string | null;
  scheme_code?: string | null;
  isin_growth?: string | null;
  isin_dividend?: string | null;
  plan?: string | null;
  option?: string | null;
  category?: string | null;
}

export interface CreateMutualFundTransactionRequest {
  scheme: number;
  transaction_type: string;
  transaction_date: string;
  units: number;
  nav: number;
  amount: number;
  fees?: number;
  notes?: string | null;
}

export interface SIP {
  id: number;
  scheme: number;
  scheme_name: string;
  amount: number;
  frequency: string;
  frequency_display: string;
  start_date: string;
  end_date: string | null;
  next_installment_date: string | null;
  is_active: boolean;
  status: string;
  due_count: number;
  monthly_commitment: number;
  created_at: string;
  updated_at: string;
}

export interface CreateSIPRequest {
  scheme: number;
  amount: number;
  frequency: string;
  start_date: string;
  end_date?: string | null;
  next_installment_date?: string | null;
  is_active: boolean;
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

interface CsrfResponse {
  detail: string;
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

  // ==========================================================
  // CSRF
  // ==========================================================

  /**
   * Ask Django to create/set the csrftoken cookie.
   *
   * This MUST be called before any POST request because
   * Django's CSRF middleware checks the token before the
   * DRF view is executed.
   */
  private getCsrfToken(): Observable<CsrfResponse> {
    return this.http.get<CsrfResponse>(`${this.baseUrl}/csrf/`, this.requestOptions);
  }

  /**
   * Read Django's csrftoken cookie.
   */
  private readCsrfToken(): string | null {
    const cookies = document.cookie.split(';');

    for (const cookie of cookies) {
      const [name, ...valueParts] = cookie.trim().split('=');

      if (name === 'csrftoken') {
        return decodeURIComponent(valueParts.join('='));
      }
    }

    return null;
  }

  /**
   * Build headers required by Django CSRF protection.
   */
  private getCsrfHeaders(): HttpHeaders {
    const csrfToken = this.readCsrfToken();

    if (!csrfToken) {
      throw new Error('CSRF token was not found. Please refresh the page and try again.');
    }

    return new HttpHeaders({
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    });
  }

  // ==========================================================
  // SUMMARY
  // ==========================================================

  getSummary(): Observable<MutualFundSummary> {
    return this.http.get<MutualFundSummary>(`${this.baseUrl}/summary/`, this.requestOptions);
  }

  // ==========================================================
  // HOLDINGS
  // ==========================================================

  getHoldings(): Observable<ApiListResponse<MutualFundHolding>> {
    return this.http.get<ApiListResponse<MutualFundHolding>>(
      `${this.baseUrl}/holdings/`,
      this.requestOptions,
    );
  }

  // ==========================================================
  // TRANSACTIONS
  // ==========================================================

  getTransactions(): Observable<ApiListResponse<MutualFundTransaction>> {
    return this.http.get<ApiListResponse<MutualFundTransaction>>(
      `${this.baseUrl}/transactions/`,
      this.requestOptions,
    );
  }

  // ==========================================================
  // MUTUAL FUND SCHEMES
  // ==========================================================

  getSchemes(search = ''): Observable<ApiListResponse<MutualFundScheme>> {
    let params = new HttpParams();

    if (search.trim()) {
      params = params.set('search', search.trim());
    }

    return this.http.get<ApiListResponse<MutualFundScheme>>(`${this.baseUrl}/schemes/`, {
      ...this.requestOptions,
      params,
    });
  }

  // ==========================================================
  // CREATE MUTUAL FUND SCHEME
  // ==========================================================

  createScheme(payload: CreateMutualFundSchemeRequest): Observable<MutualFundScheme> {
    return this.getCsrfToken().pipe(
      switchMap(() => {
        const headers = this.getCsrfHeaders();

        return this.http.post<MutualFundScheme>(`${this.baseUrl}/schemes/`, payload, {
          ...this.requestOptions,
          headers,
        });
      }),
    );
  }

  // ==========================================================
  // CREATE MUTUAL FUND TRANSACTION
  // ==========================================================

  createTransaction(
    payload: CreateMutualFundTransactionRequest,
  ): Observable<MutualFundTransaction> {
    return this.getCsrfToken().pipe(
      switchMap(() => {
        const headers = this.getCsrfHeaders();

        return this.http.post<MutualFundTransaction>(
          `${this.baseUrl}/transactions/create/`,
          payload,
          {
            ...this.requestOptions,
            headers,
          },
        );
      }),
    );
  }

  // ==========================================================
  // CREATE SIP
  // ==========================================================

  createSIP(payload: CreateSIPRequest): Observable<SIP> {
    return this.getCsrfToken().pipe(
      switchMap(() => {
        const headers = this.getCsrfHeaders();

        return this.http.post<SIP>(`${this.baseUrl}/sips/create/`, payload, {
          ...this.requestOptions,
          headers,
        });
      }),
    );
  }
}
