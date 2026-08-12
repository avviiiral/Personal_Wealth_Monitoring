import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, switchMap } from 'rxjs';

export interface SIPSummary {
  total_sips: number;
  active_sips: number;
  total_monthly_commitment: number;

  installments: {
    scheduled: number;
    executed: number;
    due: number;
    skipped: number;
    failed: number;
  };

  actual_sip_invested: number;
  pending_sip_amount: number;

  next_installment: {
    id: number;
    date: string;
    amount: number;
    sip_id: number;
  } | null;
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

export interface DueSIP {
  id: number;
  sip_id: number;
  scheme: string;
  amount: number;
  frequency: string;
  scheduled_date: string;
  next_installment_date: string | null;
  status: string;
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
export class SipApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/mutual-funds';

  private readonly requestOptions = {
    withCredentials: true,
  };

  /**
   * Get the Django CSRF cookie.
   *
   * This endpoint causes Django to set:
   *
   * csrftoken=<token>
   *
   * The token is then read from document.cookie
   * and sent as X-CSRFToken on POST requests.
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

  getSummary(): Observable<SIPSummary> {
    return this.http.get<SIPSummary>(`${this.baseUrl}/sips/summary/`, this.requestOptions);
  }

  getSips(): Observable<ApiListResponse<SIP>> {
    return this.http.get<ApiListResponse<SIP>>(`${this.baseUrl}/sips/`, this.requestOptions);
  }

  getDueSips(): Observable<ApiListResponse<DueSIP>> {
    return this.http.get<ApiListResponse<DueSIP>>(`${this.baseUrl}/sips/due/`, this.requestOptions);
  }

  /**
   * Execute one specific SIP installment.
   *
   * Flow:
   *
   * 1. GET /csrf/
   * 2. Django sets csrftoken cookie
   * 3. Read csrftoken from document.cookie
   * 4. Send X-CSRFToken header
   * 5. POST installment execution endpoint
   */
  executeInstallment(installmentId: number): Observable<any> {
    return this.getCsrfToken().pipe(
      switchMap(() => {
        const csrfToken = this.readCsrfToken();

        if (!csrfToken) {
          throw new Error('CSRF token was not found. Please refresh the page and try again.');
        }

        const headers = new HttpHeaders({
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        });

        return this.http.post(
          `${this.baseUrl}/sip-installments/${installmentId}/execute/`,
          {},
          {
            ...this.requestOptions,
            headers,
          },
        );
      }),
    );
  }
}
